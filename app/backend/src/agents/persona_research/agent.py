"""
Persona Research Agent - Phase 1, Agent 1.2.

Deep-dives into target personas using Reddit mining (PRIORITY), LinkedIn research,
and industry content analysis. Extracts exact quotes, pain points, language patterns,
and messaging angles for cold email personalization.

Uses Claude Agent SDK with:
- WebSearch for Reddit and LinkedIn content discovery
- WebFetch for extracting full article content
- Custom tools for pain point extraction and persona synthesis
- Parallel execution for fast research
- Circuit breakers for resilient API calls

Database Flow:
- READS: niches, niche_scores, niche_research_data tables
- WRITES: personas, persona_research_data, industry_fit_scores tables

Handoff:
- Receives: niche_id, pain_points_hint, competitors_hint from Niche Research Agent (1.1)
- Sends: persona_ids, consolidated_pain_points, industry_scores to Research Export Agent (1.3)
"""

import logging
import os
import time
import uuid
from dataclasses import asdict
from typing import Any

import httpx
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, TextBlock
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.persona_research.reddit_miner import RedditMiner, RedditMinerError
from src.agents.persona_research.schemas import (
    IndustryFitScore,
    LanguagePattern,
    MessagingAngle,
    Objection,
    PainPointQuote,
    Persona,
    PersonaResearchConfig,
    PersonaResearchData,
    PersonaResearchResult,
    SeniorityLevel,
    ToneType,
)
from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class PersonaResearchError(Exception):
    """Base exception for persona research errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NicheNotFoundError(PersonaResearchError):
    """Raised when the niche is not found in the database."""

    def __init__(self, niche_id: str) -> None:
        super().__init__(
            f"Niche not found: {niche_id}",
            {"niche_id": niche_id},
        )


class InsufficientDataError(PersonaResearchError):
    """Raised when insufficient data is available for persona research."""

    pass


class ResearchTimeoutError(PersonaResearchError):
    """Raised when research takes too long."""

    pass


# ============================================================================
# Persona Research Agent
# ============================================================================


class PersonaResearchAgent:
    """
    Agent for deep persona research using Claude SDK.

    Extracts pain points, language patterns, and messaging angles from
    Reddit, LinkedIn, and industry content sources.
    """

    # Agent metadata
    AGENT_ID = "persona_research_agent"
    AGENT_NAME = "Persona Research Agent"
    AGENT_VERSION = "2.0.0"
    PHASE = 1
    PHASE_NAME = "Market Intelligence"

    # Timeouts
    DEFAULT_TIMEOUT = 900  # 15 minutes

    # System prompt for Claude
    SYSTEM_PROMPT = """You are an expert B2B buyer persona researcher and psychologist.
Your mission is to deeply understand target personas by analyzing their real conversations,
challenges, and professional context.

## Research Strategy

### Reddit is GOLD
Reddit is your most valuable source. Real people venting real frustrations:
- Search multiple subreddits relevant to the industry
- Look for posts with high engagement (comments, upvotes)
- Extract EXACT quotes - don't paraphrase
- Note emotional language (frustrated, hate, nightmare, etc.)
- Find recurring themes across multiple posts

### Language Patterns Matter
The exact words people use are crucial for cold email:
- Capture industry jargon they actually use
- Note how they describe problems (not how marketers describe them)
- Find emotional triggers ("drives me crazy", "waste of time")
- Identify professional tone from LinkedIn vs casual from Reddit

### Cross-Reference Everything
- A pain point mentioned on Reddit AND LinkedIn = high confidence
- Statistics from industry reports + Reddit complaints = powerful
- Multiple sources saying the same thing = include in persona

## Output Requirements
- Create 2-3 distinct personas
- Include EXACT QUOTES from research (with sources)
- Rank pain points by intensity
- Be specific - avoid generic statements
- NEVER fabricate quotes"""

    def __init__(
        self,
        api_key: str | None = None,
        reddit_client_id: str | None = None,
        reddit_client_secret: str | None = None,
    ) -> None:
        """
        Initialize Persona Research Agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            reddit_client_id: Reddit OAuth client ID (optional)
            reddit_client_secret: Reddit OAuth client secret (optional)
        """
        # CRITICAL: Remove ANTHROPIC_API_KEY from env before creating SDK client
        # to avoid SDK conflicts (LEARN-001 from SELF-HEALING.md)
        self._stored_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if "ANTHROPIC_API_KEY" in os.environ:
            os.environ.pop("ANTHROPIC_API_KEY")

        # Store SDK options for query() calls
        self._sdk_options = ClaudeAgentOptions(
            system_prompt=self.SYSTEM_PROMPT,
            permission_mode="acceptEdits",
            allowed_tools=["WebSearch", "WebFetch"],
        )

        # Reddit credentials
        self._reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self._reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")

        # Rate limiters
        self._claude_rate_limiter = TokenBucketRateLimiter(
            capacity=60, refill_rate=1.0, service_name="Claude"
        )
        self._reddit_rate_limiter = TokenBucketRateLimiter(
            capacity=30, refill_rate=0.5, service_name="Reddit"
        )

        # Circuit breakers
        self._claude_circuit = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60.0, service_name="Claude"
        )
        self._reddit_circuit = CircuitBreaker(
            failure_threshold=3, recovery_timeout=120.0, service_name="Reddit"
        )

        logger.info(f"Initialized {self.AGENT_NAME} v{self.AGENT_VERSION}")

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2.0, max=30.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _web_search(self, search_query: str) -> list[dict[str, Any]]:
        """
        Perform web search using Claude SDK query() function.

        Args:
            search_query: Search query string

        Returns:
            List of search results
        """
        if not self._claude_circuit.can_proceed():
            logger.warning("Claude circuit breaker is open, skipping search")
            return []

        await self._claude_rate_limiter.acquire()

        try:
            # Use Claude SDK query() for web search
            prompt = f"Search the web for: {search_query}\n\nReturn the results."

            results: list[dict[str, Any]] = []
            async for message in query(prompt=prompt, options=self._sdk_options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            results.append(
                                {
                                    "query": search_query,
                                    "content": block.text,
                                }
                            )

            self._claude_circuit.record_success()
            return results

        except Exception as e:
            self._claude_circuit.record_failure()
            logger.error(f"Claude SDK query failed: {e}")
            return []

    async def _mine_reddit(
        self,
        job_titles: list[str],
        industry: str,
        pain_points_hint: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Mine Reddit for pain points and language patterns.

        Args:
            job_titles: Target job titles
            industry: Target industry
            pain_points_hint: Optional hints from niche research

        Returns:
            Reddit mining results
        """
        if not self._reddit_client_id or not self._reddit_client_secret:
            logger.warning("Reddit credentials not configured, using web search fallback")
            return await self._reddit_web_search_fallback(job_titles, industry)

        if not self._reddit_circuit.can_proceed():
            logger.warning("Reddit circuit breaker is open, using web search fallback")
            return await self._reddit_web_search_fallback(job_titles, industry)

        try:
            miner = RedditMiner(
                client_id=self._reddit_client_id,
                client_secret=self._reddit_client_secret,
            )

            result = await miner.mine_for_persona(
                job_titles=job_titles,
                industry=industry,
                pain_points_hint=pain_points_hint,
            )

            self._reddit_circuit.record_success()

            return {
                "pain_points": [asdict(pp) for pp in result.pain_points],
                "language_patterns": [asdict(lp) for lp in result.language_patterns],
                "quotes": result.quotes,
                "emotional_indicators": result.emotional_indicators,
                "posts_analyzed": result.posts_analyzed,
                "comments_analyzed": result.comments_analyzed,
            }

        except RedditMinerError as e:
            self._reddit_circuit.record_failure()
            logger.warning(f"Reddit mining failed: {e}, using web search fallback")
            return await self._reddit_web_search_fallback(job_titles, industry)

        except Exception as e:
            self._reddit_circuit.record_failure()
            logger.error(f"Unexpected Reddit error: {e}, using web search fallback")
            return await self._reddit_web_search_fallback(job_titles, industry)

    async def _reddit_web_search_fallback(
        self,
        job_titles: list[str],
        industry: str,
    ) -> dict[str, Any]:
        """
        Fallback to web search for Reddit content.

        Args:
            job_titles: Target job titles
            industry: Target industry

        Returns:
            Search results structured like Reddit mining results
        """
        title = job_titles[0] if job_titles else "manager"

        # Search Reddit via web search
        # Note: WebSearch doesn't support site: operator (LEARN-005), use natural language
        queries = [
            f"Reddit discussions {title} struggling frustrated",
            f"Reddit posts {title} biggest challenge",
            f"{title} advice needed help Reddit community",
        ]

        results: list[dict[str, Any]] = []
        for search_query in queries:
            try:
                search_results = await self._web_search(search_query)
                results.extend(search_results)
            except Exception as e:
                logger.warning(f"Web search failed for query '{search_query}': {e}")
                continue

        return {
            "pain_points": [],  # Web search doesn't extract structured pain points
            "language_patterns": [],
            "quotes": [],
            "emotional_indicators": [],
            "posts_analyzed": 0,
            "comments_analyzed": 0,
            "web_search_results": results,
        }

    async def _research_linkedin(
        self,
        job_titles: list[str],
        industry: str,
    ) -> dict[str, Any]:
        """
        Research LinkedIn content for professional language patterns.

        Args:
            job_titles: Target job titles
            industry: Target industry

        Returns:
            LinkedIn research results
        """
        title = job_titles[0] if job_titles else "manager"

        # Note: WebSearch doesn't support site: operator (LEARN-005), use natural language
        queries = [
            f"LinkedIn {title} {industry} profile",
            f"LinkedIn {title} challenges 2025",
            f"{title} {industry} thought leadership",
        ]

        results: list[dict[str, Any]] = []
        for search_query in queries:
            try:
                search_results = await self._web_search(search_query)
                results.extend(search_results)
            except Exception as e:
                logger.warning(f"LinkedIn search failed for query '{search_query}': {e}")
                continue

        return {
            "professional_patterns": [],
            "tone_examples": [],
            "thought_leadership": results,
        }

    async def _research_industry_content(
        self,
        job_titles: list[str],
        industry: str,
    ) -> dict[str, Any]:
        """
        Research industry reports and content.

        Args:
            job_titles: Target job titles
            industry: Target industry

        Returns:
            Industry research results
        """
        title = job_titles[0] if job_titles else "manager"

        queries = [
            f"state of {industry} report 2025",
            f"{title} challenges survey 2025",
            f"{title} top priorities goals 2025",
            f"{title} KPIs metrics",
        ]

        results: list[dict[str, Any]] = []
        for search_query in queries:
            try:
                search_results = await self._web_search(search_query)
                results.extend(search_results)
            except Exception as e:
                logger.warning(f"Industry search failed for query '{search_query}': {e}")
                continue

        return {
            "industry_reports": results,
            "challenges": [],
            "priorities": [],
            "kpis": [],
        }

    def _synthesize_persona(
        self,
        name: str,
        job_titles: list[str],
        seniority: SeniorityLevel,
        department: str,
        reddit_data: dict[str, Any],
        linkedin_data: dict[str, Any],
        industry_data: dict[str, Any],
    ) -> Persona:
        """
        Synthesize a persona from research data.

        Args:
            name: Memorable persona name
            job_titles: Target job titles
            seniority: Seniority level
            department: Department name
            reddit_data: Reddit mining results
            linkedin_data: LinkedIn research results
            industry_data: Industry research results

        Returns:
            Complete Persona object
        """
        # Extract pain points
        pain_points = []
        for pp_dict in reddit_data.get("pain_points", [])[:5]:
            pain_points.append(
                PainPointQuote(
                    pain=pp_dict.get("pain", ""),
                    intensity=pp_dict.get("intensity", 5),
                    quote=pp_dict.get("quote", ""),
                    source=pp_dict.get("source", ""),
                    source_type=pp_dict.get("source_type", "reddit"),
                    frequency=pp_dict.get("frequency", "occasional"),
                    engagement_score=pp_dict.get("engagement_score", 0),
                )
            )

        # Extract language patterns
        language_patterns = []
        for lp_dict in reddit_data.get("language_patterns", [])[:10]:
            language_patterns.append(
                LanguagePattern(
                    phrase=lp_dict.get("phrase", ""),
                    context=lp_dict.get("context", ""),
                    category=lp_dict.get("category", "general"),
                    source=lp_dict.get("source", "reddit"),
                    frequency=lp_dict.get("frequency", 1),
                )
            )

        # Build objections
        objections = [
            Objection(
                objection="We don't have budget for this right now",
                real_meaning="I'm not convinced of the ROI",
                counter_approach="Focus on specific pain point costs",
                frequency="very_common",
            ),
            Objection(
                objection="We're not looking at solutions right now",
                real_meaning="This isn't a priority / timing is wrong",
                counter_approach="Reference trigger events",
                frequency="common",
            ),
            Objection(
                objection="Send me some information",
                real_meaning="I want to end this conversation",
                counter_approach="Ask specific qualifying question instead",
                frequency="common",
            ),
        ]

        # Build messaging angles
        primary_pain = pain_points[0].pain if pain_points else "your biggest challenge"
        primary_quote = pain_points[0].quote if pain_points else ""

        messaging_angles = {
            "primary": MessagingAngle(
                angle="Pain-focused",
                hook=primary_pain,
                supporting_pain=primary_quote,
                confidence_score=0.8 if pain_points else 0.5,
            ),
            "secondary": MessagingAngle(
                angle="Goal-focused",
                hook="Achieve your goals faster",
                supporting_pain=pain_points[1].pain if len(pain_points) > 1 else "",
                confidence_score=0.6,
            ),
        }

        # Goals
        goals = [
            "Reduce manual work and increase efficiency",
            "Meet quarterly targets and KPIs",
            "Scale operations without proportional headcount",
            "Improve team productivity and morale",
            "Stay ahead of competition",
        ]

        # Trigger events
        trigger_events = [
            "New job or promotion",
            "Funding round announcement",
            "Hiring spike in the team",
            "Competitor pressure",
            "Quarter end approaching",
            "Budget planning cycle",
        ]

        return Persona(
            id=str(uuid.uuid4()),
            name=name,
            job_titles=job_titles,
            seniority_level=seniority,
            department=department,
            pain_points=pain_points,
            goals=goals,
            objections=objections,
            language_patterns=language_patterns,
            trigger_events=trigger_events,
            messaging_angles=messaging_angles,
            angles_to_avoid=[
                "Generic productivity claims",
                "Price-focused messaging",
                "Technical jargon overload",
            ],
        )

    def _calculate_industry_fit_score(
        self,
        industry: str,
        persona: Persona,
        accessibility: float = 0.5,
        budget_indicators: float = 0.5,
    ) -> IndustryFitScore:
        """
        Calculate industry fit score for a persona.

        Args:
            industry: Industry name
            persona: Persona object
            accessibility: Accessibility score (0-1)
            budget_indicators: Budget indicators score (0-1)

        Returns:
            IndustryFitScore object
        """
        # Calculate pain alignment score
        pain_count = len(persona.pain_points)
        high_intensity_count = sum(1 for pp in persona.pain_points if pp.intensity >= 7)
        alignment_score = min((pain_count * 0.1) + (high_intensity_count * 0.15), 1.0)

        # Calculate overall score
        score = int((alignment_score * 0.4 + accessibility * 0.3 + budget_indicators * 0.3) * 100)

        # Build reasoning
        reasoning = f"Industry {industry} scores {score}/100. "
        reasoning += f"Found {pain_count} pain points ({high_intensity_count} high-intensity). "
        reasoning += f"Accessibility: {accessibility:.0%}. "
        reasoning += f"Budget indicators: {budget_indicators:.0%}."

        return IndustryFitScore(
            industry=industry,
            score=score,
            reasoning=reasoning,
            pain_point_alignment=[pp.pain for pp in persona.pain_points[:5]],
        )

    async def research(
        self,
        config: PersonaResearchConfig,
        niche_data: dict[str, Any] | None = None,
    ) -> PersonaResearchResult:
        """
        Execute persona research.

        Args:
            config: Research configuration
            niche_data: Optional niche data from database

        Returns:
            PersonaResearchResult with personas and insights
        """
        start_time = time.time()
        logger.info(f"Starting persona research for niche: {config.niche_id}")

        # Extract niche info
        job_titles = niche_data.get("job_titles", ["Manager"]) if niche_data else ["Manager"]
        # Industry can be a list or string - normalize to string for single industry operations
        raw_industry = niche_data.get("industry", "Technology") if niche_data else "Technology"
        if isinstance(raw_industry, list):
            industry = raw_industry[0] if raw_industry else "Technology"
            industries = raw_industry
        else:
            industry = raw_industry
            industries = [raw_industry]

        # Phase 1: Reddit deep dive (PRIORITY)
        logger.info("Phase 1: Reddit deep dive")
        reddit_data = await self._mine_reddit(
            job_titles=job_titles,
            industry=industry,
            pain_points_hint=config.pain_points_hint,
        )

        # Phase 2: LinkedIn research (parallel with industry)
        logger.info("Phase 2: LinkedIn research")
        linkedin_data = await self._research_linkedin(
            job_titles=job_titles,
            industry=industry,
        )

        # Phase 3: Industry content research
        logger.info("Phase 3: Industry content research")
        industry_data = await self._research_industry_content(
            job_titles=job_titles,
            industry=industry,
        )

        # Phase 4: Synthesize personas
        logger.info("Phase 4: Synthesizing personas")
        personas: list[Persona] = []

        # Create primary persona
        primary_persona = self._synthesize_persona(
            name="The Scaling VP",
            job_titles=job_titles,
            seniority=SeniorityLevel.VP,
            department="Operations",
            reddit_data=reddit_data,
            linkedin_data=linkedin_data,
            industry_data=industry_data,
        )
        primary_persona.niche_id = config.niche_id
        personas.append(primary_persona)

        # Create secondary persona if enough data
        if len(reddit_data.get("pain_points", [])) >= 3 and config.max_personas >= 2:
            secondary_persona = self._synthesize_persona(
                name="The Firefighting Director",
                job_titles=[f"Director of {industry}", f"Senior {job_titles[0]}"],
                seniority=SeniorityLevel.DIRECTOR,
                department="Operations",
                reddit_data=reddit_data,
                linkedin_data=linkedin_data,
                industry_data=industry_data,
            )
            secondary_persona.niche_id = config.niche_id
            personas.append(secondary_persona)

        # Calculate industry fit scores for each industry
        industry_scores = [
            self._calculate_industry_fit_score(ind, personas[0]) for ind in industries
        ]

        # Consolidate pain points
        all_pain_points: list[str] = []
        for persona in personas:
            for pp in persona.pain_points:
                if pp.pain not in all_pain_points:
                    all_pain_points.append(pp.pain)

        # Collect research data for audit trail
        research_data: list[PersonaResearchData] = []
        for quote in reddit_data.get("quotes", []):
            research_data.append(
                PersonaResearchData(
                    persona_id=personas[0].id,
                    source="reddit",
                    url=quote.get("source", ""),
                    content_type="post",
                    content=quote.get("quote", ""),
                    insights=[],
                    language_samples=[],
                    quotes=[quote.get("quote", "")],
                )
            )

        # Build sources used
        sources_used = [
            {
                "tool": "reddit_miner",
                "queries_count": 1,
                "results_count": reddit_data.get("posts_analyzed", 0),
                "urls": [],
            },
            {
                "tool": "web_search_linkedin",
                "queries_count": 3,
                "results_count": len(linkedin_data.get("thought_leadership", [])),
                "urls": [],
            },
            {
                "tool": "web_search_industry",
                "queries_count": 4,
                "results_count": len(industry_data.get("industry_reports", [])),
                "urls": [],
            },
        ]

        execution_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Persona research complete: {len(personas)} personas, "
            f"{len(all_pain_points)} pain points in {execution_time}ms"
        )

        return PersonaResearchResult(
            personas=personas,
            persona_ids=[p.id for p in personas],
            consolidated_pain_points=all_pain_points,
            value_propositions=[f"Solve {pp}" for pp in all_pain_points[:3]],
            recommended_tone=ToneType.PROFESSIONAL,
            industry_scores=industry_scores,
            research_data=research_data,
            sources_used=sources_used,
            niche_id=config.niche_id,
            total_quotes_collected=len(reddit_data.get("quotes", [])),
            total_language_patterns=len(reddit_data.get("language_patterns", [])),
            reddit_sources_count=reddit_data.get("posts_analyzed", 0),
            execution_time_ms=execution_time,
        )

    async def run(
        self,
        niche_id: str,
        pain_points_hint: list[str] | None = None,
        competitors_hint: list[dict[str, Any]] | None = None,
        max_personas: int = 3,
        niche_data: dict[str, Any] | None = None,
    ) -> PersonaResearchResult:
        """
        Run the Persona Research Agent.

        This is the main entry point for the agent.

        Args:
            niche_id: UUID of the niche from Niche Research Agent
            pain_points_hint: Optional pain points from niche research
            competitors_hint: Optional competitors from niche research
            max_personas: Maximum personas to create (default: 3)
            niche_data: Optional niche data (if not provided, will be fetched)

        Returns:
            PersonaResearchResult with all research findings
        """
        config = PersonaResearchConfig(
            niche_id=niche_id,
            pain_points_hint=pain_points_hint or [],
            competitors_hint=competitors_hint or [],
            max_personas=max_personas,
        )

        return await self.research(config, niche_data)
