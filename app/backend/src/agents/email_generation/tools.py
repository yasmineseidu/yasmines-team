"""
SDK MCP Tools for Email Generation Agent.

Provides tools for:
- Loading campaign context (leads, research, personas)
- Generating personalized emails via LLM
- Scoring email quality
- Saving emails to database
- Updating lead status

All tools return SDK-compliant format: {"content": [...], "is_error": bool}
Per LEARN-029: Tools must return this exact format.

Integration Resilience:
- Anthropic API calls use AsyncAnthropic with retry and rate limiting
- Per LEARN-030: Module-level singleton for rate limiter
- Per LEARN-002: Tenacity retry uses tuple syntax for exception types
"""

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import tool

# Lazy import for anthropic to allow tests to run without it installed
if TYPE_CHECKING:
    import anthropic

from src.agents.email_generation.frameworks import (
    build_generation_prompt,
    select_framework_for_tier,
)
from src.agents.email_generation.quality_scorer import get_quality_scorer
from src.agents.email_generation.schemas import (
    EmailFramework,
    GeneratedEmail,
    LeadContext,
    LeadTier,
    PersonalizationLevel,
)

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiter (Module-level Singleton per LEARN-030)
# =============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for Anthropic API.

    Anthropic limits:
    - Tier 1: 50 RPM (requests per minute)
    - Tier 2: 1000 RPM
    - Tier 3: 2000 RPM

    Default configured for Tier 1 with safety margin.
    """

    def __init__(self, rate: float = 40.0, capacity: float = 50.0) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Tokens added per second (default: 40/60 = 0.67 per second for 40 RPM)
            capacity: Maximum tokens in bucket
        """
        self._rate = rate / 60.0  # Convert to per-second
        self._capacity = capacity
        self._tokens = capacity
        self._last_update = (
            asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0
        )
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1 for one API call)
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # Refill tokens based on time elapsed
            elapsed = now - self._last_update
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_update = now

            # Wait if not enough tokens
            if self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self._rate
                # Add jitter to prevent thundering herd (per best practices)
                wait_time += random.uniform(0.1, 0.5)
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s for tokens")
                await asyncio.sleep(wait_time)
                self._tokens = tokens  # Reset after wait

            self._tokens -= tokens


# Module-level singleton (per LEARN-030)
_anthropic_rate_limiter: TokenBucketRateLimiter | None = None


def _get_anthropic_rate_limiter() -> TokenBucketRateLimiter:
    """Get or create the Anthropic rate limiter singleton."""
    global _anthropic_rate_limiter
    if _anthropic_rate_limiter is None:
        _anthropic_rate_limiter = TokenBucketRateLimiter(rate=40.0, capacity=50.0)
    return _anthropic_rate_limiter


# Module-level singleton for async client (per LEARN-030)
_anthropic_client: "AsyncAnthropic | None" = None


def _get_anthropic_client(api_key: str) -> "anthropic.AsyncAnthropic":
    """
    Get or create the AsyncAnthropic client singleton.

    Args:
        api_key: Anthropic API key

    Returns:
        AsyncAnthropic client instance
    """
    import anthropic as anthropic_module

    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic_module.AsyncAnthropic(api_key=api_key)
    return _anthropic_client


# =============================================================================
# Retry-wrapped Anthropic API Call
# =============================================================================


def _get_anthropic_retryable_exceptions() -> tuple[type[Exception], ...]:
    """Get retryable exception types from anthropic module."""
    import anthropic as anthropic_module

    return (
        anthropic_module.RateLimitError,
        anthropic_module.APIConnectionError,
        anthropic_module.InternalServerError,
    )


async def _call_anthropic_with_retry(
    client: "anthropic.AsyncAnthropic",
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    max_retries: int = 3,
) -> str:
    """
    Call Anthropic API with retry and rate limiting.

    Args:
        client: AsyncAnthropic client
        prompt: User message content
        model: Model to use
        max_tokens: Maximum response tokens
        temperature: Sampling temperature
        max_retries: Maximum retry attempts

    Returns:
        Response text from the model

    Raises:
        anthropic.APIError: If all retries fail
    """
    import anthropic as anthropic_module

    retryable_exceptions = _get_anthropic_retryable_exceptions()
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            # Acquire rate limit token
            rate_limiter = _get_anthropic_rate_limiter()
            await rate_limiter.acquire()

            logger.debug(
                f"Calling Anthropic API (attempt {attempt + 1}/{max_retries}) "
                f"with model={model}, max_tokens={max_tokens}"
            )

            message = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                text: str = message.content[0].text
                return text
            return ""

        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = (2**attempt) + random.uniform(0.1, 1.0)
                logger.warning(
                    f"Anthropic API error (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait_time:.2f}s"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Anthropic API failed after {max_retries} attempts: {e}")
                raise

    # Should never reach here, but for type safety
    if last_exception:
        raise last_exception
    raise anthropic_module.APIError(message="Unknown error", request=None, body=None)


# =============================================================================
# Tool: Load Campaign Context
# =============================================================================


@tool(  # type: ignore[misc]
    name="load_campaign_context",
    description="Load campaign context including leads, niche, and personas",
    input_schema={
        "campaign_id": str,
    },
)
async def load_campaign_context(args: dict[str, Any]) -> dict[str, Any]:
    """
    Load campaign context including leads, niche, and personas.

    Args:
        args: Dictionary with campaign_id.

    Returns:
        SDK-compliant response with campaign context data.
    """
    campaign_id = args.get("campaign_id")
    if not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: campaign_id is required"}],
            "is_error": True,
        }

    try:
        # Create database session inside tool (per LEARN-003)
        from src.database.connection import get_session
        from src.database.repositories.campaign_repository import CampaignRepository
        from src.database.repositories.lead_repository import LeadRepository
        from src.database.repositories.niche_repository import NicheRepository
        from src.database.repositories.persona_repository import PersonaRepository

        async with get_session() as session:
            campaign_repo = CampaignRepository(session)
            lead_repo = LeadRepository(session)
            niche_repo = NicheRepository(session)
            persona_repo = PersonaRepository(session)

            # Get campaign
            campaign = await campaign_repo.get_campaign(campaign_id)
            if not campaign:
                return {
                    "content": [{"type": "text", "text": f"Campaign {campaign_id} not found"}],
                    "is_error": True,
                }

            # Get niche
            niche_data: dict[str, Any] = {}
            if campaign.niche_id:
                niche = await niche_repo.get_niche(str(campaign.niche_id))
                if niche:
                    niche_data = niche.to_dict()

            # Get personas for niche
            personas: list[dict[str, Any]] = []
            if campaign.niche_id:
                persona_list = await persona_repo.get_personas_by_niche(str(campaign.niche_id))
                personas = [p.to_dict() for p in persona_list]

            # Get leads ready for email generation (verified email, scored, not yet generated)
            # Use existing get_campaign_leads with filters
            leads = await lead_repo.get_campaign_leads(
                campaign_id=campaign_id,
                status=["scored", "verified", "ready"],
                exclude_status=["duplicate", "invalid", "cross_campaign_duplicate"],
            )
            leads_by_tier: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
            for lead in leads:
                tier = getattr(lead, "lead_tier", None) or "C"
                lead_dict = lead.to_dict()
                leads_by_tier[tier].append(lead_dict)

            result = {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "niche": niche_data,
                "personas": personas,
                "total_leads": len(leads),
                "leads_by_tier": {
                    "A": len(leads_by_tier["A"]),
                    "B": len(leads_by_tier["B"]),
                    "C": len(leads_by_tier["C"]),
                },
                "leads": leads_by_tier,
            }

            logger.info(
                f"Loaded context for campaign {campaign_id}: "
                f"{len(leads)} leads, {len(personas)} personas"
            )

            return {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "is_error": False,
            }

    except Exception as e:
        logger.exception(f"Error loading campaign context: {e}")
        return {
            "content": [{"type": "text", "text": f"Error loading context: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool: Generate Email
# =============================================================================


async def generate_email_impl(args: dict[str, Any]) -> dict[str, Any]:
    """
    Internal implementation of email generation.

    This function is called by both the SDK tool and DirectEmailGenerator.

    Args:
        args: Dictionary with lead details and context.

    Returns:
        SDK-compliant response with generated email.
    """
    lead_id = args.get("lead_id")
    campaign_id = args.get("campaign_id")
    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    title = args.get("title", "")
    company_name = args.get("company_name", "")
    lead_tier = args.get("lead_tier", "C")
    persona_challenges = args.get("persona_challenges", "")
    persona_goals = args.get("persona_goals", "")
    messaging_tone = args.get("messaging_tone", "conversational but professional")
    framework = args.get("framework")
    lead_research_json = args.get("lead_research_json")
    company_research_json = args.get("company_research_json")
    company_research_id = args.get("company_research_id")
    lead_research_id = args.get("lead_research_id")

    if not lead_id or not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: lead_id and campaign_id are required"}],
            "is_error": True,
        }

    try:
        # Get API key (prefer backup to avoid SDK conflict per LEARN-001)
        api_key = os.environ.get("ANTHROPIC_API_KEY_BACKUP") or os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            return {
                "content": [{"type": "text", "text": "ANTHROPIC_API_KEY not configured"}],
                "is_error": True,
            }

        # Parse research data
        lead_research = json.loads(lead_research_json) if lead_research_json else None
        company_research = json.loads(company_research_json) if company_research_json else None

        # Determine framework
        tier = lead_tier.upper() if lead_tier else "C"
        email_framework = (
            EmailFramework(framework.lower()) if framework else select_framework_for_tier(tier)
        )

        # Determine personalization level
        personalization_map = {
            "A": PersonalizationLevel.HYPER_PERSONALIZED,
            "B": PersonalizationLevel.PERSONALIZED,
            "C": PersonalizationLevel.SEMI_PERSONALIZED,
        }
        personalization_level = personalization_map.get(
            tier, PersonalizationLevel.SEMI_PERSONALIZED
        )

        # Determine max words
        max_words_map = {"A": 150, "B": 120, "C": 100}
        max_words = max_words_map.get(tier, 100)

        # Build lead context
        lead_context = {
            "first_name": first_name,
            "last_name": last_name,
            "title": title,
            "company_name": company_name,
            "lead_tier": tier,
        }

        # Build persona context
        persona_context = {
            "challenges": [c.strip() for c in persona_challenges.split(",") if c.strip()],
            "goals": [g.strip() for g in persona_goals.split(",") if g.strip()],
            "messaging_tone": messaging_tone,
        }

        # Build niche context (simplified)
        niche_context = {
            "pain_points": persona_context["challenges"],
            "value_propositions": [],
        }

        # Build prompt
        prompt = build_generation_prompt(
            framework=email_framework,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
            lead_research=lead_research,
            company_research=company_research,
            max_words=max_words,
            personalization_level=personalization_level.value,
        )

        # Call Claude API with retry and rate limiting (using AsyncAnthropic)
        client = _get_anthropic_client(api_key)
        response_text = await _call_anthropic_with_retry(
            client=client,
            prompt=prompt,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.7,
        )

        # Extract JSON from response (per LEARN-016: JSON parsing returns Any)
        email_data: dict[str, Any] = {}
        try:
            # Try to find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                email_data = json.loads(json_str)
        except json.JSONDecodeError as je:
            logger.warning(f"Failed to parse JSON from response: {je}")
            # Fallback: create structured email from text
            email_data = {
                "subject_line": f"Quick question for {first_name}",
                "opening_line": response_text[:100] if response_text else "",
                "body": response_text[:500] if response_text else "",
                "cta": "Would you be open to a quick chat?",
                "full_email": response_text[:600] if response_text else "",
            }

        # Create GeneratedEmail object
        generated = GeneratedEmail(
            lead_id=lead_id,
            campaign_id=campaign_id,
            subject_line=email_data.get("subject_line", "")[:255],
            opening_line=email_data.get("opening_line", ""),
            body=email_data.get("body", ""),
            cta=email_data.get("cta", ""),
            full_email=email_data.get("full_email", ""),
            framework=email_framework,
            personalization_level=personalization_level,
            company_research_id=company_research_id,
            lead_research_id=lead_research_id,
            generation_prompt=prompt[:2000],  # Truncate for storage
        )

        # Score the email
        lead_ctx = LeadContext(
            lead_id=lead_id,
            first_name=first_name,
            last_name=last_name,
            title=title,
            company_name=company_name,
            company_domain=None,
            lead_tier=LeadTier(tier),
            lead_score=0,
            lead_research=lead_research,
            company_research=company_research,
        )

        scorer = get_quality_scorer()
        quality_score = scorer.score_email(generated, lead_ctx)
        generated.score_breakdown = quality_score
        generated.quality_score = quality_score.total_score

        result = {
            "lead_id": lead_id,
            "email": generated.to_dict(),
            "quality_score": quality_score.total_score,
            "score_breakdown": quality_score.to_dict(),
            "framework": email_framework.value,
        }

        logger.info(
            f"Generated email for {first_name} {last_name}: "
            f"score={quality_score.total_score:.0f}, framework={email_framework.value}"
        )

        return {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "is_error": False,
        }

    except Exception as e:
        # Import anthropic for exception type checking
        try:
            import anthropic as anthropic_module

            if isinstance(e, anthropic_module.RateLimitError):
                logger.warning(f"Rate limit hit after retries for lead {lead_id}: {e}")
                return {
                    "content": [{"type": "text", "text": f"Rate limit exceeded: {e}"}],
                    "is_error": True,
                }
            elif isinstance(e, anthropic_module.APIConnectionError):
                logger.error(f"API connection error for lead {lead_id}: {e}")
                return {
                    "content": [{"type": "text", "text": f"API connection error: {e}"}],
                    "is_error": True,
                }
            elif isinstance(e, anthropic_module.APIError):
                logger.error(f"Anthropic API error for lead {lead_id}: {e}")
                return {
                    "content": [{"type": "text", "text": f"API error: {e}"}],
                    "is_error": True,
                }
        except ImportError:
            pass  # anthropic not installed, fall through to generic handler

        logger.exception(f"Error generating email for lead {lead_id}: {e}")
        return {
            "content": [{"type": "text", "text": f"Error generating email: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="generate_email",
    description="Generate a personalized cold email for a lead using Claude",
    input_schema={
        "lead_id": str,
        "campaign_id": str,
        "first_name": str,
        "last_name": str,
        "title": str,
        "company_name": str,
        "lead_tier": str,
        "persona_challenges": str,
        "persona_goals": str,
        "messaging_tone": str,
        "framework": str,
        "lead_research_json": str,
        "company_research_json": str,
        "company_research_id": str,
        "lead_research_id": str,
    },
)
async def generate_email(args: dict[str, Any]) -> dict[str, Any]:
    """SDK tool wrapper for email generation. Calls generate_email_impl."""
    return await generate_email_impl(args)


# =============================================================================
# Tool: Score Email Quality
# =============================================================================


@tool(  # type: ignore[misc]
    name="score_email_quality",
    description="Score an email's quality across multiple dimensions",
    input_schema={
        "subject_line": str,
        "opening_line": str,
        "body": str,
        "cta": str,
        "full_email": str,
        "first_name": str,
        "last_name": str,
        "title": str,
        "company_name": str,
        "lead_tier": str,
    },
)
async def score_email_quality(args: dict[str, Any]) -> dict[str, Any]:
    """
    Score an email's quality across multiple dimensions.

    Args:
        args: Dictionary with email content and lead context.

    Returns:
        SDK-compliant response with quality score breakdown.
    """
    subject_line = args.get("subject_line", "")
    opening_line = args.get("opening_line", "")
    body = args.get("body", "")
    cta = args.get("cta", "")
    full_email = args.get("full_email", "")
    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    title = args.get("title", "")
    company_name = args.get("company_name", "")
    lead_tier = args.get("lead_tier", "C")

    try:
        # Create temporary email object for scoring
        email = GeneratedEmail(
            lead_id="temp",
            campaign_id="temp",
            subject_line=subject_line,
            opening_line=opening_line,
            body=body,
            cta=cta,
            full_email=full_email,
            framework=EmailFramework.PAS,  # Default
            personalization_level=PersonalizationLevel.PERSONALIZED,
        )

        # Create lead context
        tier = lead_tier.upper() if lead_tier else "C"
        lead_ctx = LeadContext(
            lead_id="temp",
            first_name=first_name,
            last_name=last_name,
            title=title,
            company_name=company_name,
            company_domain=None,
            lead_tier=LeadTier(tier),
            lead_score=0,
        )

        # Score
        scorer = get_quality_scorer()
        quality_score = scorer.score_email(email, lead_ctx)

        # Get threshold for tier
        threshold_map = {"A": 70, "B": 60, "C": 50}
        threshold = threshold_map.get(tier, 50)

        result = {
            "total_score": quality_score.total_score,
            "breakdown": quality_score.to_dict(),
            "threshold": threshold,
            "should_regenerate": quality_score.total_score < threshold,
            "suggestions": scorer.get_improvement_suggestions(quality_score),
        }

        return {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "is_error": False,
        }

    except Exception as e:
        logger.exception(f"Error scoring email: {e}")
        return {
            "content": [{"type": "text", "text": f"Error scoring email: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool: Save Generated Email
# =============================================================================


@tool(  # type: ignore[misc]
    name="save_generated_email",
    description="Save a generated email to the database",
    input_schema={
        "lead_id": str,
        "campaign_id": str,
        "subject_line": str,
        "opening_line": str,
        "body": str,
        "cta": str,
        "full_email": str,
        "framework_used": str,
        "personalization_level": str,
        "quality_score": int,
        "score_breakdown_json": str,
        "generation_prompt": str,
        "company_research_id": str,
        "lead_research_id": str,
    },
)
async def save_generated_email(args: dict[str, Any]) -> dict[str, Any]:
    """
    Save a generated email to the database.

    Args:
        args: Dictionary with email content and metadata.

    Returns:
        SDK-compliant response with saved email ID.
    """
    lead_id = args.get("lead_id")
    campaign_id = args.get("campaign_id")
    subject_line = args.get("subject_line", "")
    opening_line = args.get("opening_line", "")
    body = args.get("body", "")
    cta = args.get("cta", "")
    full_email = args.get("full_email", "")
    framework_used = args.get("framework_used", "pas")
    personalization_level = args.get("personalization_level", "personalized")
    quality_score = args.get("quality_score", 0)
    score_breakdown_json = args.get("score_breakdown_json", "{}")
    generation_prompt = args.get("generation_prompt", "")
    company_research_id = args.get("company_research_id")
    lead_research_id = args.get("lead_research_id")

    if not lead_id or not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: lead_id and campaign_id are required"}],
            "is_error": True,
        }

    try:
        from sqlalchemy import text

        from src.database.connection import get_session

        async with get_session() as session:
            # Parse score breakdown
            score_breakdown = json.loads(score_breakdown_json) if score_breakdown_json else {}

            # Create email record
            email_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            # Insert into generated_emails table
            insert_sql = text("""
                INSERT INTO generated_emails (
                    id, lead_id, campaign_id, subject_line, opening_line,
                    body, cta, full_email, framework_used, personalization_level,
                    quality_score, score_breakdown, generation_prompt,
                    generation_model, company_research_id, lead_research_id,
                    generated_at, created_at, updated_at
                ) VALUES (
                    :id, :lead_id, :campaign_id, :subject_line, :opening_line,
                    :body, :cta, :full_email, :framework_used, :personalization_level,
                    :quality_score, :score_breakdown, :generation_prompt,
                    :generation_model, :company_research_id, :lead_research_id,
                    :generated_at, :created_at, :updated_at
                ) RETURNING id
            """)

            await session.execute(
                insert_sql,
                {
                    "id": email_id,
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "subject_line": subject_line[:255],
                    "opening_line": opening_line,
                    "body": body,
                    "cta": cta,
                    "full_email": full_email,
                    "framework_used": framework_used,
                    "personalization_level": personalization_level,
                    "quality_score": quality_score,
                    "score_breakdown": json.dumps(score_breakdown),
                    "generation_prompt": generation_prompt[:5000],
                    "generation_model": "claude-sonnet-4-20250514",
                    "company_research_id": company_research_id,
                    "lead_research_id": lead_research_id,
                    "generated_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            # Update lead with generated_email_id
            update_sql = text("""
                UPDATE leads
                SET generated_email_id = :email_id,
                    email_generation_status = 'generated',
                    updated_at = :updated_at
                WHERE id = :lead_id
            """)

            await session.execute(
                update_sql,
                {
                    "email_id": email_id,
                    "lead_id": lead_id,
                    "updated_at": now,
                },
            )

            await session.commit()

            logger.info(f"Saved email {email_id} for lead {lead_id}")

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "email_id": email_id,
                                "lead_id": lead_id,
                                "status": "saved",
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

    except Exception as e:
        logger.exception(f"Error saving email: {e}")
        return {
            "content": [{"type": "text", "text": f"Error saving email: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool: Update Campaign Stats
# =============================================================================


@tool(  # type: ignore[misc]
    name="update_campaign_email_stats",
    description="Update campaign with email generation statistics",
    input_schema={
        "campaign_id": str,
        "total_generated": int,
        "tier_a_generated": int,
        "tier_b_generated": int,
        "tier_c_generated": int,
        "avg_quality_score": float,
    },
)
async def update_campaign_email_stats(args: dict[str, Any]) -> dict[str, Any]:
    """
    Update campaign with email generation statistics.

    Args:
        args: Dictionary with campaign_id and generation statistics.

    Returns:
        SDK-compliant response with update status.
    """
    campaign_id = args.get("campaign_id")
    total_generated = args.get("total_generated", 0)
    tier_a_generated = args.get("tier_a_generated", 0)
    tier_b_generated = args.get("tier_b_generated", 0)
    tier_c_generated = args.get("tier_c_generated", 0)
    avg_quality_score = args.get("avg_quality_score", 0.0)

    if not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: campaign_id is required"}],
            "is_error": True,
        }

    try:
        from sqlalchemy import text

        from src.database.connection import get_session

        async with get_session() as session:
            now = datetime.now(UTC)

            # Build personalization summary
            summary = {
                "tier_a_generated": tier_a_generated,
                "tier_b_generated": tier_b_generated,
                "tier_c_generated": tier_c_generated,
                "total_generated": total_generated,
                "avg_quality_score": avg_quality_score,
                "completed_at": now.isoformat(),
            }

            update_sql = text("""
                UPDATE campaigns
                SET total_emails_generated = :total_generated,
                    avg_email_quality = :avg_quality,
                    personalization_summary = :summary,
                    status = 'emails_generated',
                    updated_at = :updated_at
                WHERE id = :campaign_id
            """)

            await session.execute(
                update_sql,
                {
                    "total_generated": total_generated,
                    "avg_quality": avg_quality_score,
                    "summary": json.dumps(summary),
                    "updated_at": now,
                    "campaign_id": campaign_id,
                },
            )

            await session.commit()

            logger.info(
                f"Updated campaign {campaign_id} stats: "
                f"{total_generated} emails, avg score {avg_quality_score:.1f}"
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "campaign_id": campaign_id,
                                "status": "updated",
                                "total_generated": total_generated,
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

    except Exception as e:
        logger.exception(f"Error updating campaign stats: {e}")
        return {
            "content": [{"type": "text", "text": f"Error updating stats: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool: Save to Personalization Library
# =============================================================================


@tool(  # type: ignore[misc]
    name="save_to_personalization_library",
    description="Save a high-quality opening line to the personalization library",
    input_schema={
        "lead_id": str,
        "campaign_id": str,
        "opening_line": str,
        "quality_score": int,
        "industry": str,
    },
)
async def save_to_personalization_library(args: dict[str, Any]) -> dict[str, Any]:
    """
    Save a high-quality opening line to the personalization library.

    Args:
        args: Dictionary with lead_id, opening_line, quality_score, and industry.

    Returns:
        SDK-compliant response with save status.
    """
    lead_id = args.get("lead_id")
    campaign_id = args.get("campaign_id")
    opening_line = args.get("opening_line", "")
    quality_score = args.get("quality_score", 0)
    industry = args.get("industry", "")

    if not lead_id or not campaign_id or not opening_line:
        return {
            "content": [
                {"type": "text", "text": "Error: lead_id, campaign_id, and opening_line required"}
            ],
            "is_error": True,
        }

    try:
        from sqlalchemy import text

        from src.database.connection import get_session

        # Only save high-quality lines (80+)
        if quality_score < 80:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "saved": False,
                                "reason": f"Score {quality_score} below threshold 80",
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

        async with get_session() as session:
            line_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            insert_sql = text("""
                INSERT INTO personalization_library (
                    id, lead_id, campaign_id, personalization_line,
                    confidence_score, industry, is_active, created_at
                ) VALUES (
                    :id, :lead_id, :campaign_id, :line,
                    :score, :industry, true, :created_at
                ) RETURNING id
            """)

            await session.execute(
                insert_sql,
                {
                    "id": line_id,
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "line": opening_line[:500],
                    "score": quality_score,
                    "industry": industry,
                    "created_at": now,
                },
            )

            await session.commit()

            logger.info(f"Saved opening line {line_id} to library (score: {quality_score})")

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "saved": True,
                                "line_id": line_id,
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

    except Exception as e:
        logger.exception(f"Error saving to library: {e}")
        return {
            "content": [{"type": "text", "text": f"Error saving to library: {e}"}],
            "is_error": True,
        }
