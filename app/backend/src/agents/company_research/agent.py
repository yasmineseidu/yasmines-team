"""
Company Research Agent.

Phase 4 agent that conducts deep research on target companies using web search,
news, and public data for email personalization. Uses tiered tool strategy
(FREE -> CHEAP -> MODERATE) and parallel batch processing.

Follows Claude Agent SDK patterns per SDK_PATTERNS.md.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.agents.company_research.prompts import COMPANY_RESEARCH_SYSTEM_PROMPT
from src.agents.company_research.schemas import (
    CompanyResearchOutput,
    CompanyToResearch,
    CostTracker,
    ExtractedFact,
    ResearchResult,
)
from src.agents.company_research.tools import (
    COMPANY_RESEARCH_TOOLS,
    aggregate_company_research_tool,
    extract_and_score_facts_tool,
    search_company_funding_tool,
    search_company_hiring_tool,
    search_company_news_tool,
    search_company_tech_tool,
)

logger = logging.getLogger(__name__)


class CompanyResearchAgent:
    """
    Company Research Agent for Phase 4.

    Conducts deep research on target companies using web search, news,
    and public data. Gathers company context for email personalization.

    Database Flow:
    - Reads from: leads table (unique companies by campaign_id)
    - Writes to: company_research_data, extracted_facts tables
    - Updates: leads table with company_research_id reference

    Attributes:
        name: Agent identifier
        use_claude: Whether to use Claude for orchestration vs direct path
        max_concurrent_companies: Parallel processing limit
        session_id: Unique session identifier
    """

    def __init__(
        self,
        use_claude: bool = False,
        max_concurrent_companies: int = 20,
    ) -> None:
        """
        Initialize the Company Research Agent.

        Args:
            use_claude: If True, use Claude SDK for orchestration.
                       If False, use direct execution path (more efficient).
            max_concurrent_companies: Max companies to research in parallel.
        """
        self.name = "company_research_agent"
        self.use_claude = use_claude
        self.max_concurrent_companies = max_concurrent_companies
        self.session_id = str(uuid4())

        # Cost tracking
        self.cost_tracker = CostTracker()

        # Circuit breaker trip count
        self.circuit_breaker_trips = 0

        logger.info(
            f"Initialized {self.name} (use_claude={use_claude}, "
            f"max_concurrent={max_concurrent_companies})"
        )

    async def run(
        self,
        campaign_id: UUID,
        research_depth: str = "standard",
        max_companies: int = 1000,
        max_cost_per_company: float = 0.10,
        max_total_cost: float = 100.0,
    ) -> CompanyResearchOutput:
        """
        Run company research for a campaign.

        Args:
            campaign_id: Campaign UUID to research companies for.
            research_depth: Research depth (minimal, standard, deep).
            max_companies: Maximum number of companies to research.
            max_cost_per_company: Maximum cost per company.
            max_total_cost: Maximum total cost for the campaign.

        Returns:
            CompanyResearchOutput with research results and metrics.
        """
        start_time = time.time()

        # Initialize cost tracker
        self.cost_tracker = CostTracker(
            max_per_campaign=max_total_cost,
            max_per_company=max_cost_per_company,
        )

        logger.info(
            f"Starting company research for campaign {campaign_id} "
            f"(depth={research_depth}, max_companies={max_companies})"
        )

        try:
            # Step 1: Get unique companies from leads
            companies = await self._get_unique_companies(campaign_id, max_companies)

            if not companies:
                logger.warning(f"No companies found for campaign {campaign_id}")
                return CompanyResearchOutput(
                    campaign_id=campaign_id,
                    total_companies=0,
                    success=False,
                    error_message="No companies found for campaign",
                )

            total_companies = len(companies)
            logger.info(f"Found {total_companies} unique companies to research")

            # Step 2: Research companies in parallel batches
            results = await self._research_companies_parallel(companies)

            # Step 3: Save results to database
            await self._save_research_results(campaign_id, results)

            # Step 4: Calculate final metrics
            duration_seconds = time.time() - start_time

            companies_researched = sum(1 for r in results if r.success)
            companies_failed = sum(1 for r in results if not r.success)
            facts_extracted = sum(len(r.facts) for r in results)
            hooks_generated = sum(
                len(r.personalization_hooks) for r in results if r.personalization_hooks
            )

            # Aggregate hook counts by category
            personalization_hooks: dict[str, int] = {
                "news": 0,
                "funding": 0,
                "hiring": 0,
                "product": 0,
            }
            for result in results:
                if result.has_recent_news:
                    personalization_hooks["news"] += 1
                if result.has_funding:
                    personalization_hooks["funding"] += 1
                if result.has_hiring:
                    personalization_hooks["hiring"] += 1
                if result.has_product_launch:
                    personalization_hooks["product"] += 1

            # Calculate averages
            avg_fact_score = 0.0
            avg_relevance_score = 0.0
            if results:
                fact_scores = [f.total_score for r in results for f in r.facts if f.total_score]
                if fact_scores:
                    avg_fact_score = sum(fact_scores) / len(fact_scores)
                relevance_scores = [r.relevance_score for r in results if r.relevance_score]
                if relevance_scores:
                    avg_relevance_score = sum(relevance_scores) / len(relevance_scores)

            output = CompanyResearchOutput(
                campaign_id=campaign_id,
                total_companies=total_companies,
                companies_researched=companies_researched,
                companies_failed=companies_failed,
                facts_extracted=facts_extracted,
                hooks_generated=hooks_generated,
                personalization_hooks=personalization_hooks,
                research_cost=self.cost_tracker.total_cost,
                cost_by_tool=self.cost_tracker.cost_by_tool,
                avg_fact_score=round(avg_fact_score, 4),
                avg_relevance_score=round(avg_relevance_score, 4),
                circuit_breaker_trips=self.circuit_breaker_trips,
                success=True,
                duration_seconds=round(duration_seconds, 2),
            )

            logger.info(
                f"Company research complete: {companies_researched}/{total_companies} companies, "
                f"{facts_extracted} facts, ${self.cost_tracker.total_cost:.2f} cost, "
                f"{duration_seconds:.1f}s"
            )

            return output

        except Exception as e:
            logger.error(f"Company research failed: {e}")
            return CompanyResearchOutput(
                campaign_id=campaign_id,
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def _get_unique_companies(
        self,
        campaign_id: UUID,
        max_companies: int,
    ) -> list[CompanyToResearch]:
        """
        Get unique companies from leads table.

        Args:
            campaign_id: Campaign UUID.
            max_companies: Maximum companies to return.

        Returns:
            List of companies to research.
        """
        # Import inside method to avoid circular imports
        from sqlalchemy import func, select

        from src.database.connection import get_session
        from src.database.models import LeadModel

        companies: list[CompanyToResearch] = []

        async with get_session() as session:
            # Query for unique companies with valid emails
            stmt = (
                select(
                    LeadModel.id,
                    LeadModel.company_name,
                    LeadModel.company_domain,
                    LeadModel.company_linkedin_url,
                    LeadModel.company_industry,
                    LeadModel.company_size,
                    func.count(LeadModel.id).label("lead_count"),
                    func.max(LeadModel.lead_score).label("max_lead_score"),
                )
                .where(
                    LeadModel.campaign_id == campaign_id,
                    LeadModel.email_status == "valid",
                    LeadModel.company_domain.isnot(None),
                )
                .group_by(
                    LeadModel.id,
                    LeadModel.company_name,
                    LeadModel.company_domain,
                    LeadModel.company_linkedin_url,
                    LeadModel.company_industry,
                    LeadModel.company_size,
                )
                .order_by(func.max(LeadModel.lead_score).desc())
                .limit(max_companies)
            )

            result = await session.execute(stmt)
            rows = result.all()

            for row in rows:
                if row.company_domain and row.company_name:
                    companies.append(
                        CompanyToResearch(
                            lead_id=row.id,
                            company_name=row.company_name,
                            company_domain=row.company_domain,
                            company_linkedin_url=row.company_linkedin_url,
                            company_industry=row.company_industry,
                            company_size=row.company_size,
                            lead_count=row.lead_count or 1,
                            max_lead_score=row.max_lead_score,
                        )
                    )

        return companies

    async def _research_companies_parallel(
        self,
        companies: list[CompanyToResearch],
    ) -> list[ResearchResult]:
        """
        Research companies in parallel with concurrency limit.

        Args:
            companies: List of companies to research.

        Returns:
            List of research results.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_companies)
        results: list[ResearchResult] = []

        async def research_with_semaphore(company: CompanyToResearch) -> ResearchResult:
            async with semaphore:
                # Check budget before researching
                if not self.cost_tracker.can_continue():
                    logger.warning(f"Budget exhausted, skipping {company.company_name}")
                    return ResearchResult(
                        company_domain=company.company_domain,
                        company_name=company.company_name,
                        success=False,
                        error_message="Budget exhausted",
                    )

                return await self._research_single_company(company)

        # Create tasks for all companies
        tasks = [research_with_semaphore(c) for c in companies]

        # Execute with progress logging
        for completed, coro in enumerate(asyncio.as_completed(tasks), start=1):
            result = await coro
            results.append(result)
            if completed % 50 == 0:
                logger.info(
                    f"Progress: {completed}/{len(companies)} companies "
                    f"(cost: ${self.cost_tracker.total_cost:.2f})"
                )

                # Check alert threshold
                if self.cost_tracker.is_at_alert_threshold():
                    logger.warning(
                        f"Alert: At 80% budget threshold "
                        f"(${self.cost_tracker.total_cost:.2f}/"
                        f"${self.cost_tracker.max_per_campaign:.2f})"
                    )

        return results

    async def _research_single_company(
        self,
        company: CompanyToResearch,
    ) -> ResearchResult:
        """
        Research a single company using all search tools.

        Args:
            company: Company to research.

        Returns:
            ResearchResult with findings.
        """
        try:
            # Run all search types in parallel
            search_args = {
                "company_name": company.company_name,
                "company_domain": company.company_domain,
                "max_results": 5,
            }

            # Run all search tools in parallel
            raw_results: tuple[Any, ...] = await asyncio.gather(
                search_company_news_tool(search_args),
                search_company_funding_tool(search_args),
                search_company_hiring_tool(search_args),
                search_company_tech_tool(search_args),
                return_exceptions=True,
            )

            # Handle any exceptions
            def safe_result(r: Any) -> dict[str, Any]:
                if isinstance(r, Exception):
                    return {"is_error": True, "data": {}}
                return dict(r)

            news_result: dict[str, Any] = safe_result(raw_results[0])
            funding_result: dict[str, Any] = safe_result(raw_results[1])
            hiring_result: dict[str, Any] = safe_result(raw_results[2])
            tech_result: dict[str, Any] = safe_result(raw_results[3])

            # Collect all search results for fact extraction
            all_results: list[dict[str, Any]] = []

            for result, category in [
                (news_result, "news"),
                (funding_result, "funding"),
                (hiring_result, "hiring"),
                (tech_result, "product"),
            ]:
                if not result.get("is_error") and result.get("data", {}).get("results"):
                    for r in result["data"]["results"]:
                        r["category"] = category
                        all_results.append(r)

            # Track costs
            for result in [news_result, funding_result, hiring_result, tech_result]:
                if result.get("data", {}).get("cost"):
                    cost = result["data"]["cost"]
                    tool = result["data"].get("tool_used", "unknown")
                    self.cost_tracker.add_cost(tool, cost)

            # Extract and score facts
            facts_result: Any = await extract_and_score_facts_tool(
                {
                    "company_name": company.company_name,
                    "company_domain": company.company_domain,
                    "search_results": all_results,
                }
            )

            extracted_facts: list[dict[str, Any]] = []
            if not facts_result.get("is_error"):
                extracted_facts = facts_result.get("data", {}).get("facts", [])

            # Aggregate results
            aggregate_result: Any = await aggregate_company_research_tool(
                {
                    "company_name": company.company_name,
                    "company_domain": company.company_domain,
                    "news_results": news_result,
                    "funding_results": funding_result,
                    "hiring_results": hiring_result,
                    "tech_results": tech_result,
                    "extracted_facts": extracted_facts,
                }
            )

            if aggregate_result.get("is_error"):
                return ResearchResult(
                    company_domain=company.company_domain,
                    company_name=company.company_name,
                    success=False,
                    error_message=str(aggregate_result.get("content", [{}])[0].get("text")),
                )

            data = aggregate_result.get("data", {})

            # Convert extracted facts to dataclass
            fact_objects = []
            for f in data.get("facts", []):
                fact_objects.append(
                    ExtractedFact(
                        fact_text=f.get("fact_text", ""),
                        category=f.get("category", "news"),
                        source_type=f.get("source_type", "web_search"),
                        source_url=f.get("source_url"),
                        recency_days=f.get("recency_days"),
                        recency_score=f.get("recency_score", 0),
                        specificity_score=f.get("specificity_score", 0),
                        business_relevance_score=f.get("business_relevance_score", 0),
                        emotional_hook_score=f.get("emotional_hook_score", 0),
                        total_score=f.get("total_score", 0),
                    )
                )

            source_urls = data.get("source_urls", [])
            return ResearchResult(
                company_domain=company.company_domain,
                company_name=company.company_name,
                headline=data.get("headline"),
                summary=data.get("summary"),
                content={"aggregated": data},
                primary_source_url=source_urls[0] if source_urls else None,
                source_urls=source_urls,
                relevance_score=data.get("relevance_score", 0),
                key_insights=[],
                personalization_hooks=list(data.get("personalization_hooks", {}).keys()),
                primary_hook=data.get("primary_hook"),
                has_recent_news=data.get("has_recent_news", False),
                has_funding=data.get("has_funding", False),
                has_hiring=data.get("has_hiring", False),
                has_product_launch=data.get("has_product_launch", False),
                facts=fact_objects,
                research_cost=data.get("total_cost", 0),
                tools_used=data.get("tools_used", []),
                success=True,
            )

        except Exception as e:
            logger.error(f"Error researching {company.company_name}: {e}")
            return ResearchResult(
                company_domain=company.company_domain,
                company_name=company.company_name,
                success=False,
                error_message=str(e),
            )

    async def _save_research_results(
        self,
        campaign_id: UUID,
        results: list[ResearchResult],
    ) -> int:
        """
        Save research results to database.

        Args:
            campaign_id: Campaign UUID.
            results: List of research results.

        Returns:
            Number of results saved.
        """
        # Import inside method to avoid circular imports
        from src.database.connection import get_session
        from src.database.models import CompanyResearchDataModel, ExtractedFactsModel

        saved_count = 0

        async with get_session() as session:
            for result in results:
                if not result.success:
                    continue

                try:
                    # Create company research record
                    research = CompanyResearchDataModel(
                        campaign_id=campaign_id,
                        company_domain=result.company_domain,
                        company_name=result.company_name,
                        research_type="company_overview",
                        data_source="web_search",
                        headline=result.headline,
                        summary=result.summary,
                        content=result.content,
                        primary_source_url=result.primary_source_url,
                        source_urls=result.source_urls,
                        relevance_score=result.relevance_score,
                        key_insights=result.key_insights,
                        personalization_hooks=result.personalization_hooks,
                        primary_hook=result.primary_hook,
                        has_recent_news=result.has_recent_news,
                        has_funding=result.has_funding,
                        has_hiring=result.has_hiring,
                        has_product_launch=result.has_product_launch,
                        research_cost=result.research_cost,
                        tools_used=result.tools_used,
                        researched_at=datetime.now(UTC),
                    )
                    session.add(research)
                    await session.flush()

                    # Create extracted facts records
                    for fact in result.facts:
                        fact_record = ExtractedFactsModel(
                            company_research_id=research.id,
                            session_id=self.session_id,
                            fact_text=fact.fact_text,
                            source_type=fact.source_type,
                            source_url=fact.source_url,
                            recency_days=fact.recency_days,
                            category=fact.category,
                            recency_score=fact.recency_score,
                            specificity_score=fact.specificity_score,
                            business_relevance_score=fact.business_relevance_score,
                            emotional_hook_score=fact.emotional_hook_score,
                            total_score=fact.total_score,
                        )
                        session.add(fact_record)

                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error saving research for {result.company_domain}: {e}")
                    continue

            await session.commit()

        logger.info(f"Saved {saved_count} research results to database")
        return saved_count

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return COMPANY_RESEARCH_SYSTEM_PROMPT

    @property
    def tools(self) -> list[Any]:
        """Get the list of tools for this agent."""
        return COMPANY_RESEARCH_TOOLS
