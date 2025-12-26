"""Lead Research Agent - Phase 4, Agent 4.2.

Conducts individual research on leads using LinkedIn posts, articles,
and web presence for hyper-personalized email opening lines.

Research depth varies by lead tier:
- Tier A (Deep): 5 queries, max $0.15/lead, include LinkedIn posts, articles, podcasts, talks
- Tier B (Standard): 3 queries, max $0.05/lead, include LinkedIn posts, articles
- Tier C (Basic): 1 query, max $0.01/lead, headline analysis only

Uses Claude Agent SDK with SDK MCP tools for in-process execution.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

from claude_agent_sdk import create_sdk_mcp_server
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.agents.lead_research.fact_extractor import (
    create_fallback_angle,
    extract_facts_from_research,
    rank_angles_from_facts,
)
from src.agents.lead_research.schemas import (
    COST_CONTROLS,
    LeadData,
    LeadResearchInput,
    LeadResearchOutput,
    LeadTier,
    ResearchDepth,
    ResearchResult,
)
from src.agents.lead_research.tools import LEAD_RESEARCH_TOOLS
from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class LeadResearchAgentError(Exception):
    """Exception raised for lead research agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RateLimitExceededError(LeadResearchAgentError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, service: str, retry_after: int | None = None) -> None:
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after}s"
        super().__init__(message, {"service": service, "retry_after": retry_after})


class BudgetExceededError(LeadResearchAgentError):
    """Raised when research budget is exceeded."""

    def __init__(self, budget: Decimal, spent: Decimal) -> None:
        message = f"Budget exceeded: ${spent:.2f} of ${budget:.2f}"
        super().__init__(message, {"budget": float(budget), "spent": float(spent)})


# =============================================================================
# Lead Research Agent
# =============================================================================


class LeadResearchAgent:
    """
    Agent for conducting lead research for personalization.

    Uses tiered research depth based on lead score:
    - Tier A: Deep research with LinkedIn posts, articles, podcasts
    - Tier B: Standard research with LinkedIn posts and articles
    - Tier C: Basic headline analysis

    Attributes:
        name: Agent identifier.
        campaign_id: Current campaign being processed.
        cost_tracker: Tracks research costs.
        rate_limiters: Per-service rate limiters.
        circuit_breakers: Per-service circuit breakers.
    """

    def __init__(self) -> None:
        """Initialize the Lead Research Agent."""
        self.name = "lead_research_agent"
        self.campaign_id: UUID | None = None

        # Cost tracking
        self._total_cost = Decimal("0.0")
        self._cost_by_tier: dict[str, Decimal] = {
            "tier_a": Decimal("0.0"),
            "tier_b": Decimal("0.0"),
            "tier_c": Decimal("0.0"),
        }
        self._cost_by_lead: dict[str, Decimal] = {}

        # Rate limiters per service
        self._rate_limiters: dict[str, TokenBucketRateLimiter] = {
            "tavily": TokenBucketRateLimiter(rate_limit=100, rate_window=60, service_name="tavily"),
            "serper": TokenBucketRateLimiter(rate_limit=100, rate_window=60, service_name="serper"),
            "perplexity": TokenBucketRateLimiter(
                rate_limit=50, rate_window=60, service_name="perplexity"
            ),
        }

        # Circuit breakers per service
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            "tavily": CircuitBreaker(
                failure_threshold=3, recovery_timeout=60.0, service_name="tavily"
            ),
            "serper": CircuitBreaker(
                failure_threshold=3, recovery_timeout=60.0, service_name="serper"
            ),
            "perplexity": CircuitBreaker(
                failure_threshold=2, recovery_timeout=120.0, service_name="perplexity"
            ),
        }

        # SDK MCP server with tools
        self._mcp_server = create_sdk_mcp_server(
            name="lead_research",
            version="2.1.0",
            tools=LEAD_RESEARCH_TOOLS,
        )

        logger.info(f"Initialized {self.name} agent")

    @property
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        return """You are a Lead Research Agent specialized in finding personalization opportunities.

Your task is to research individual leads to find hooks for personalized email opening lines.

Research Strategy by Tier:
- Tier A (Deep): Search LinkedIn posts, articles, podcasts, talks. Use 5 queries max.
- Tier B (Standard): Search LinkedIn posts and articles. Use 3 queries max.
- Tier C (Basic): Analyze headline only. Use 1 query max.

For each lead:
1. Use the appropriate search tools based on tier
2. Extract specific facts (recent posts, articles, achievements)
3. Identify personalization hooks that could work as email openers
4. Prioritize recent activity (within 60 days)

Output should include:
- Key facts found about the lead
- Recommended personalization hooks (opening line ideas)
- Relevance score (how useful for email personalization)

Be cost-conscious - start with free/cheap tools before using expensive ones.
If no specific hooks are found, flag for fallback to company-level personalization."""

    async def research_campaign(
        self,
        input_data: LeadResearchInput,
        db_session: Any = None,
    ) -> LeadResearchOutput:
        """
        Research all leads in a campaign.

        Args:
            input_data: Input parameters including campaign_id.
            db_session: Optional database session for persistence.

        Returns:
            LeadResearchOutput with research summary.

        Raises:
            LeadResearchAgentError: If research fails.
            BudgetExceededError: If budget is exceeded.
        """
        self.campaign_id = input_data.campaign_id
        start_time = time.time()

        logger.info(f"Starting lead research for campaign {self.campaign_id}")

        # Initialize counters
        total_researched = 0
        tier_breakdown = {"tier_a": 0, "tier_b": 0, "tier_c": 0}
        facts_extracted = 0
        opening_lines_generated = 0
        fallback_count = 0

        # Reset cost tracking
        self._total_cost = Decimal("0.0")
        self._cost_by_tier = {
            "tier_a": Decimal("0.0"),
            "tier_b": Decimal("0.0"),
            "tier_c": Decimal("0.0"),
        }

        # Get leads to research (mock for now - would use repository)
        leads = await self._get_leads_for_research(input_data.campaign_id, db_session)

        if not leads:
            logger.warning(f"No leads found for campaign {self.campaign_id}")
            return LeadResearchOutput(
                total_researched=0,
                tier_breakdown=tier_breakdown,
                facts_extracted=0,
                avg_hooks_per_lead=0.0,
                opening_lines_generated=0,
                research_cost=Decimal("0.0"),
                cost_by_tier={k: Decimal("0.0") for k in tier_breakdown},
                fallback_to_company_research=0,
            )

        # Group leads by tier for parallel processing
        leads_by_tier: dict[str, list[LeadData]] = {"A": [], "B": [], "C": []}
        for lead in leads:
            tier = lead.lead_tier.value if lead.lead_tier else "C"
            leads_by_tier[tier].append(lead)

        # Process each tier in parallel (respecting concurrency limits)
        all_results: list[ResearchResult] = []

        # Process Tier A (max 10 concurrent)
        if leads_by_tier["A"]:
            tier_a_results = await self._process_tier_parallel(
                leads_by_tier["A"], LeadTier.A, max_concurrent=10
            )
            all_results.extend(tier_a_results)
            tier_breakdown["tier_a"] = len(tier_a_results)

        # Process Tier B (max 20 concurrent)
        if leads_by_tier["B"]:
            tier_b_results = await self._process_tier_parallel(
                leads_by_tier["B"], LeadTier.B, max_concurrent=20
            )
            all_results.extend(tier_b_results)
            tier_breakdown["tier_b"] = len(tier_b_results)

        # Process Tier C (max 30 concurrent)
        if leads_by_tier["C"]:
            tier_c_results = await self._process_tier_parallel(
                leads_by_tier["C"], LeadTier.C, max_concurrent=30
            )
            all_results.extend(tier_c_results)
            tier_breakdown["tier_c"] = len(tier_c_results)

        # Aggregate results
        for result in all_results:
            total_researched += 1
            facts_extracted += len(result.facts)
            opening_lines_generated += len(result.angles)

            # Check for fallback usage
            if result.angles and any(a.is_fallback for a in result.angles):
                fallback_count += 1

        # Calculate averages
        avg_hooks = opening_lines_generated / total_researched if total_researched > 0 else 0.0

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Completed lead research for campaign {self.campaign_id}: "
            f"{total_researched} leads, {facts_extracted} facts, "
            f"${self._total_cost:.2f} cost, {processing_time_ms}ms"
        )

        return LeadResearchOutput(
            total_researched=total_researched,
            tier_breakdown=tier_breakdown,
            facts_extracted=facts_extracted,
            avg_hooks_per_lead=round(avg_hooks, 2),
            opening_lines_generated=opening_lines_generated,
            research_cost=self._total_cost,
            cost_by_tier=dict(self._cost_by_tier),
            fallback_to_company_research=fallback_count,
            processing_time_ms=processing_time_ms,
        )

    async def research_single_lead(
        self,
        lead: LeadData,
        company_research: dict[str, Any] | None = None,
    ) -> ResearchResult:
        """
        Research a single lead.

        Args:
            lead: Lead data to research.
            company_research: Optional company research for fallback.

        Returns:
            ResearchResult with facts and angles.
        """
        tier_config = lead.get_tier_config()
        lead_id = str(lead.id)

        logger.debug(
            f"Researching lead {lead_id}: {lead.full_name}, "
            f"tier={lead.lead_tier}, depth={tier_config.depth}"
        )

        # Check budget
        if not self._check_lead_budget(lead.lead_tier or LeadTier.C):
            logger.warning(f"Budget exceeded for lead {lead_id}")
            return self._create_empty_result(lead, tier_config.depth)

        # Collect research data
        research_data: dict[str, Any] = {
            "linkedin_posts": [],
            "articles": [],
            "podcasts": [],
            "profile": {},
        }
        lead_cost = Decimal("0.0")

        # Research based on tier
        if tier_config.depth == ResearchDepth.BASIC:
            # Basic: Headline analysis only (no API calls)
            result = await self._research_headline_only(lead)
            research_data["profile"] = result.get("profile", {})
            lead_cost += Decimal(str(result.get("cost", 0)))

        elif tier_config.depth == ResearchDepth.STANDARD:
            # Standard: LinkedIn posts + articles
            linkedin_result = await self._search_linkedin_posts(lead)
            research_data["linkedin_posts"] = linkedin_result.get("posts", [])
            lead_cost += Decimal(str(linkedin_result.get("cost", 0)))

            if "articles" in tier_config.include:
                articles_result = await self._search_articles(lead)
                research_data["articles"] = articles_result.get("articles", [])
                lead_cost += Decimal(str(articles_result.get("cost", 0)))

        else:  # DEEP
            # Deep: All sources including podcasts
            linkedin_result = await self._search_linkedin_posts(lead)
            research_data["linkedin_posts"] = linkedin_result.get("posts", [])
            lead_cost += Decimal(str(linkedin_result.get("cost", 0)))

            profile_result = await self._search_profile(lead)
            research_data["profile"] = profile_result.get("profile", {})
            lead_cost += Decimal(str(profile_result.get("cost", 0)))

            articles_result = await self._search_articles(lead)
            research_data["articles"] = articles_result.get("articles", [])
            lead_cost += Decimal(str(articles_result.get("cost", 0)))

            if "podcasts" in tier_config.include:
                podcasts_result = await self._search_podcasts(lead)
                research_data["podcasts"] = podcasts_result.get("podcasts", [])
                lead_cost += Decimal(str(podcasts_result.get("cost", 0)))

        # Update cost tracking
        self._update_cost(lead.lead_tier or LeadTier.C, lead_cost, lead_id)

        # Extract facts and generate angles
        facts = extract_facts_from_research(research_data, lead_id)
        angles = rank_angles_from_facts(facts, lead_id)

        # Add fallback if no angles found
        if not angles and company_research:
            fallback = create_fallback_angle(lead_id, company_research)
            if fallback:
                angles.append(fallback)

        # Calculate quality score
        quality_score = self._calculate_quality_score(facts, angles)

        return ResearchResult(
            lead_id=lead.id,
            research_depth=tier_config.depth,
            profile_headline=research_data.get("profile", {}).get("headline"),
            recent_activity=research_data.get("profile", {}).get("about"),
            key_interests=[],
            linkedin_posts=[],  # Simplified for output
            articles=research_data.get("articles", []),
            podcasts=research_data.get("podcasts", []),
            primary_hook=angles[0].angle_text if angles else None,
            summary=f"Found {len(facts)} facts for {lead.full_name}",
            primary_source_url=research_data.get("profile", {}).get("url"),
            relevance_score=quality_score,
            quality_score=quality_score,
            research_cost=lead_cost,
            queries_used=tier_config.queries,
            facts=[],  # Facts are stored separately
            angles=angles,
        )

    # =========================================================================
    # Private Methods: Research Helpers
    # =========================================================================

    async def _process_tier_parallel(
        self,
        leads: list[LeadData],
        tier: LeadTier,
        max_concurrent: int,
    ) -> list[ResearchResult]:
        """Process leads of a tier in parallel."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def research_with_semaphore(lead: LeadData) -> ResearchResult:
            async with semaphore:
                return await self.research_single_lead(lead)

        tasks = [research_with_semaphore(lead) for lead in leads]
        gather_results: list[ResearchResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        # Filter out exceptions
        valid_results: list[ResearchResult] = []
        for i, result in enumerate(gather_results):
            if isinstance(result, BaseException):
                logger.error(f"Failed to research lead {leads[i].id}: {result}")
            elif isinstance(result, ResearchResult):
                valid_results.append(result)

        return valid_results

    @retry(
        retry=retry_if_exception_type((RateLimitExceededError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _search_linkedin_posts(self, lead: LeadData) -> dict[str, Any]:
        """Search for LinkedIn posts with retry."""
        from src.agents.lead_research.tools import search_linkedin_posts_tool

        # Check circuit breaker
        if not self._circuit_breakers["tavily"].can_proceed():
            logger.warning("Tavily circuit breaker open, skipping LinkedIn posts search")
            return {"posts": [], "cost": 0}

        # Acquire rate limit
        await self._rate_limiters["tavily"].acquire()

        try:
            # Use .handler to call SDK MCP tool
            result = await search_linkedin_posts_tool.handler(
                {
                    "first_name": lead.first_name or "",
                    "last_name": lead.last_name or "",
                    "title": lead.title or "",
                    "company_name": lead.company_name or "",
                    "max_results": 5,
                }
            )

            if result.get("is_error"):
                self._circuit_breakers["tavily"].record_failure()
                return {"posts": [], "cost": 0}

            self._circuit_breakers["tavily"].record_success()
            data: dict[str, Any] = result.get("data", {"posts": [], "cost": 0.001})
            return data

        except Exception as e:
            self._circuit_breakers["tavily"].record_failure()
            logger.error(f"LinkedIn posts search failed: {e}")
            return {"posts": [], "cost": 0}

    @retry(
        retry=retry_if_exception_type((RateLimitExceededError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _search_profile(self, lead: LeadData) -> dict[str, Any]:
        """Search for LinkedIn profile with retry."""
        from src.agents.lead_research.tools import search_linkedin_profile_tool

        if not self._circuit_breakers["serper"].can_proceed():
            return {"profile": {}, "cost": 0}

        await self._rate_limiters["serper"].acquire()

        try:
            # Use .handler to call SDK MCP tool
            result = await search_linkedin_profile_tool.handler(
                {
                    "first_name": lead.first_name or "",
                    "last_name": lead.last_name or "",
                    "title": lead.title or "",
                    "company_name": lead.company_name or "",
                }
            )

            if result.get("is_error"):
                self._circuit_breakers["serper"].record_failure()
                return {"profile": {}, "cost": 0}

            self._circuit_breakers["serper"].record_success()
            data: dict[str, Any] = result.get("data", {"profile": {}, "cost": 0.001})
            return data

        except Exception as e:
            self._circuit_breakers["serper"].record_failure()
            logger.error(f"Profile search failed: {e}")
            return {"profile": {}, "cost": 0}

    @retry(
        retry=retry_if_exception_type((RateLimitExceededError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _search_articles(self, lead: LeadData) -> dict[str, Any]:
        """Search for articles authored by lead."""
        from src.agents.lead_research.tools import search_articles_authored_tool

        if not self._circuit_breakers["tavily"].can_proceed():
            return {"articles": [], "cost": 0}

        await self._rate_limiters["tavily"].acquire()

        try:
            # Use .handler to call SDK MCP tool
            result = await search_articles_authored_tool.handler(
                {
                    "first_name": lead.first_name or "",
                    "last_name": lead.last_name or "",
                    "title": lead.title or "",
                    "max_results": 3,
                }
            )

            if result.get("is_error"):
                self._circuit_breakers["tavily"].record_failure()
                return {"articles": [], "cost": 0}

            self._circuit_breakers["tavily"].record_success()
            data: dict[str, Any] = result.get("data", {"articles": [], "cost": 0.001})
            return data

        except Exception as e:
            self._circuit_breakers["tavily"].record_failure()
            logger.error(f"Article search failed: {e}")
            return {"articles": [], "cost": 0}

    @retry(
        retry=retry_if_exception_type((RateLimitExceededError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _search_podcasts(self, lead: LeadData) -> dict[str, Any]:
        """Search for podcast appearances (Tier A only)."""
        from src.agents.lead_research.tools import search_podcast_appearances_tool

        if not self._circuit_breakers["tavily"].can_proceed():
            return {"podcasts": [], "cost": 0}

        await self._rate_limiters["tavily"].acquire()

        try:
            # Use .handler to call SDK MCP tool
            result = await search_podcast_appearances_tool.handler(
                {
                    "first_name": lead.first_name or "",
                    "last_name": lead.last_name or "",
                    "title": lead.title or "",
                    "max_results": 3,
                }
            )

            if result.get("is_error"):
                self._circuit_breakers["tavily"].record_failure()
                return {"podcasts": [], "cost": 0}

            self._circuit_breakers["tavily"].record_success()
            data: dict[str, Any] = result.get("data", {"podcasts": [], "cost": 0.001})
            return data

        except Exception as e:
            self._circuit_breakers["tavily"].record_failure()
            logger.error(f"Podcast search failed: {e}")
            return {"podcasts": [], "cost": 0}

    async def _research_headline_only(self, lead: LeadData) -> dict[str, Any]:
        """Basic headline analysis (no API calls)."""
        from src.agents.lead_research.tools import analyze_headline_tool

        # Use .handler to call SDK MCP tool
        result = await analyze_headline_tool.handler(
            {
                "first_name": lead.first_name or "",
                "last_name": lead.last_name or "",
                "title": lead.title or "",
                "headline": lead.headline or "",
                "company_name": lead.company_name or "",
            }
        )

        tool_data: dict[str, Any] = result.get("data", {})
        return {
            "profile": {
                "headline": lead.title,
                "about": lead.headline,
                "keywords": tool_data.get("keywords", []),
                "hooks": tool_data.get("hooks", []),
            },
            "cost": tool_data.get("cost", 0),
        }

    # =========================================================================
    # Private Methods: Cost and Budget
    # =========================================================================

    def _check_lead_budget(self, tier: LeadTier) -> bool:
        """Check if we have budget for this lead's tier."""
        max_campaign: Decimal = COST_CONTROLS["max_per_campaign"]  # type: ignore[assignment]
        if self._total_cost >= max_campaign:
            return False

        tier_key = f"max_per_lead_{tier.value.lower()}"
        max_per_lead: Decimal = COST_CONTROLS.get(tier_key, Decimal("0.01"))  # type: ignore[assignment]

        # Check if adding max cost would exceed budget
        if self._total_cost + max_per_lead > max_campaign:
            return False

        # Check alert threshold
        alert_percent: int = COST_CONTROLS.get("alert_at_percent", 80)  # type: ignore[assignment]
        cost_percent = (self._total_cost / max_campaign) * 100
        if cost_percent >= Decimal(alert_percent):
            logger.warning(f"Research cost at {cost_percent:.1f}% of budget")

        return True

    def _update_cost(self, tier: LeadTier, cost: Decimal, lead_id: str) -> None:
        """Update cost tracking."""
        self._total_cost += cost
        tier_key = f"tier_{tier.value.lower()}"
        self._cost_by_tier[tier_key] = self._cost_by_tier.get(tier_key, Decimal("0.0")) + cost
        self._cost_by_lead[lead_id] = cost

    def _calculate_quality_score(
        self,
        facts: list[Any],
        angles: list[Any],
    ) -> float:
        """Calculate overall quality score for research."""
        if not facts and not angles:
            return 0.0

        # Base score from number of facts
        fact_score = min(1.0, len(facts) * 0.2)

        # Bonus for high-scoring facts
        if facts:
            avg_fact_score = sum(f.total_score for f in facts) / len(facts)
            fact_score = (fact_score + avg_fact_score) / 2

        # Bonus for multiple angles
        angle_score = min(1.0, len(angles) * 0.25)

        # Combine scores
        quality = fact_score * 0.6 + angle_score * 0.4

        return round(quality, 4)

    def _create_empty_result(self, lead: LeadData, depth: ResearchDepth) -> ResearchResult:
        """Create an empty result for skipped leads."""
        return ResearchResult(
            lead_id=lead.id,
            research_depth=depth,
            relevance_score=0.0,
            quality_score=0.0,
            research_cost=Decimal("0.0"),
            queries_used=0,
        )

    async def _get_leads_for_research(
        self,
        campaign_id: UUID,
        db_session: Any = None,
    ) -> list[LeadData]:
        """
        Get leads for research from database.

        This is a placeholder - actual implementation would use repository.
        """
        # In production, this would query the database
        # For now, return empty list (tests will mock this)
        logger.debug(f"Getting leads for campaign {campaign_id}")
        return []
