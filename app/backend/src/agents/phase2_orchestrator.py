"""
Phase 2 Orchestrator - Lead Acquisition Pipeline.

Chains together Phase 2 agents and handles database persistence:
1. Lead List Builder Agent (2.1) - Scrape leads from Apify/LinkedIn
2. Data Validation Agent (2.2) - Validate lead data quality
3. Duplicate Detection Agent (2.3) - Find within-campaign duplicates
4. Cross-Campaign Dedup Agent (2.4) - Check against historical data
5. Lead Scoring Agent (2.5) - Score leads against personas
6. Import Finalizer Agent (2.6) - Export to Sheets, trigger approval

This orchestrator:
- Manages the data flow between agents
- Persists results to the database after each agent
- Handles failures gracefully with proper rollback
- Provides checkpoint/resume capability
- Supports configurable handoff thresholds

Usage:
    async with get_session() as session:
        orchestrator = Phase2Orchestrator(session)
        result = await orchestrator.run(
            campaign_id="...",
            niche_id="...",
        )
        print(f"Lead list: {result.lead_list_url}")

Per LEARN-007: Agents are pure functions. The orchestrator handles all persistence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lead_list_builder import LeadListBuilderAgent
from src.database.repositories import (
    CampaignRepository,
    LeadRepository,
    NicheRepository,
    PersonaRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class Phase2Config:
    """Configuration for Phase 2 orchestration."""

    # Handoff thresholds (configurable per campaign)
    min_leads_for_validation: int = 1000
    min_leads_for_dedup: int = 1000
    min_leads_for_cross_dedup: int = 1000
    min_leads_for_scoring: int = 1000
    min_leads_for_import: int = 1000
    min_tier_a_for_approval: int = 100

    # Cross-campaign dedup settings
    lookback_days: int = 90
    exclude_bounced: bool = True
    exclude_unsubscribed: bool = True

    # Export settings
    export_to_sheets: bool = True
    send_slack_notification: bool = True

    # For small/pilot campaigns
    @classmethod
    def pilot_config(cls) -> "Phase2Config":
        """Configuration for pilot campaigns with lower thresholds."""
        return cls(
            min_leads_for_validation=100,
            min_leads_for_dedup=100,
            min_leads_for_cross_dedup=100,
            min_leads_for_scoring=100,
            min_leads_for_import=100,
            min_tier_a_for_approval=10,
        )


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class Phase2Result:
    """Result of Phase 2 orchestration."""

    # Identifiers
    campaign_id: str
    niche_id: str

    # Status
    status: str = "completed"  # completed, stopped, failed

    # Agent results
    total_scraped: int = 0
    total_valid: int = 0
    total_invalid: int = 0
    total_duplicates: int = 0
    unique_leads: int = 0
    total_cross_duplicates: int = 0
    available_leads: int = 0
    total_scored: int = 0
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_c_count: int = 0
    avg_score: float = 0.0

    # Export (if successful)
    lead_list_url: str | None = None
    import_summary: dict[str, Any] = field(default_factory=dict)

    # Metadata
    execution_time_ms: int = 0
    completed_at: datetime = field(default_factory=datetime.now)
    stopped_at_agent: str | None = None
    error: str | None = None


# =============================================================================
# Phase 2 Orchestrator
# =============================================================================


class Phase2Orchestrator:
    """
    Orchestrates the complete Phase 2 lead acquisition pipeline.

    Manages the flow:
    Lead List Builder (2.1) → Data Validation (2.2) → Duplicate Detection (2.3)
    → Cross-Campaign Dedup (2.4) → Lead Scoring (2.5) → Import Finalizer (2.6)

    Handles:
    - Agent invocation with proper parameters
    - Database persistence after each agent
    - Handoff data between agents
    - Configurable thresholds for small campaigns
    - Failure handling and rollback
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Phase2Config | None = None,
    ) -> None:
        """
        Initialize orchestrator with database session.

        Args:
            session: SQLAlchemy async session for database operations
            config: Optional configuration (defaults to standard thresholds)
        """
        self.session = session
        self.config = config or Phase2Config()

        # Initialize repositories
        self.campaign_repo = CampaignRepository(session)
        self.lead_repo = LeadRepository(session)
        self.niche_repo = NicheRepository(session)
        self.persona_repo = PersonaRepository(session)

    async def run(
        self,
        campaign_id: str,
        niche_id: str,
        target_leads: int = 50000,
        resume_from: str | None = None,
        force_continue: bool = False,
    ) -> Phase2Result:
        """
        Execute complete Phase 2 pipeline.

        Steps:
        1. Run Lead List Builder Agent → save leads to DB
        2. Check threshold → stop if below min_leads_for_validation
        3. Run Data Validation Agent → update leads
        4. Check threshold → stop if below min_leads_for_dedup
        5. Run Duplicate Detection Agent → merge duplicates
        6. Check threshold → stop if below min_leads_for_cross_dedup
        7. Run Cross-Campaign Dedup Agent → exclude contacts
        8. Check threshold → stop if below min_leads_for_scoring
        9. Run Lead Scoring Agent → score leads
        10. Check threshold → stop if below min_tier_a_for_approval
        11. Run Import Finalizer Agent → export to Sheets
        12. Return lead list URL for human approval

        Args:
            campaign_id: Campaign UUID
            niche_id: Niche UUID (for persona matching)
            target_leads: Target number of leads to scrape
            resume_from: Optional agent ID to resume from
            force_continue: If True, continue even if thresholds not met

        Returns:
            Phase2Result with outcomes and lead list URL
        """
        import time

        start_time = time.time()
        result = Phase2Result(campaign_id=campaign_id, niche_id=niche_id)

        try:
            # =================================================================
            # Step 1: Lead List Builder Agent (2.1)
            # =================================================================
            if not resume_from or resume_from == "lead_list_builder":
                logger.info(f"Phase 2 Step 1: Building lead list for campaign {campaign_id}")

                scrape_result = await self._run_lead_list_builder(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                    target_leads=target_leads,
                )

                result.total_scraped = scrape_result["total_scraped"]

                # Persist results
                await self.campaign_repo.update_scraping_results(
                    campaign_id=campaign_id,
                    total_scraped=result.total_scraped,
                    scraping_cost=scrape_result.get("cost", 0),
                )
                await self.campaign_repo.log_action(
                    campaign_id=campaign_id,
                    action="leads_scraped",
                    actor="lead_list_builder_agent",
                    details={"total_scraped": result.total_scraped},
                )
                await self.campaign_repo.commit()

                # Check threshold
                if (
                    result.total_scraped < self.config.min_leads_for_validation
                    and not force_continue
                ):
                    logger.warning(
                        f"Only {result.total_scraped} leads scraped, "
                        f"need {self.config.min_leads_for_validation}. Stopping."
                    )
                    result.status = "stopped"
                    result.stopped_at_agent = "lead_list_builder"
                    result.execution_time_ms = int((time.time() - start_time) * 1000)
                    return result

            # =================================================================
            # Step 2: Data Validation Agent (2.2)
            # =================================================================
            if not resume_from or resume_from in ["lead_list_builder", "data_validation"]:
                logger.info(f"Phase 2 Step 2: Validating leads for campaign {campaign_id}")

                validation_result = await self._run_data_validation(campaign_id=campaign_id)

                result.total_valid = validation_result["total_valid"]
                result.total_invalid = validation_result["total_invalid"]

                # Persist results
                await self.campaign_repo.update_validation_results(
                    campaign_id=campaign_id,
                    total_valid=result.total_valid,
                    total_invalid=result.total_invalid,
                )
                await self.campaign_repo.log_action(
                    campaign_id=campaign_id,
                    action="leads_validated",
                    actor="data_validation_agent",
                    details={
                        "total_valid": result.total_valid,
                        "total_invalid": result.total_invalid,
                    },
                )
                await self.campaign_repo.commit()

                # Check threshold
                if result.total_valid < self.config.min_leads_for_dedup and not force_continue:
                    logger.warning(
                        f"Only {result.total_valid} valid leads, "
                        f"need {self.config.min_leads_for_dedup}. Stopping."
                    )
                    result.status = "stopped"
                    result.stopped_at_agent = "data_validation"
                    result.execution_time_ms = int((time.time() - start_time) * 1000)
                    return result

            # =================================================================
            # Step 3: Duplicate Detection Agent (2.3)
            # =================================================================
            if not resume_from or resume_from in [
                "lead_list_builder",
                "data_validation",
                "duplicate_detection",
            ]:
                logger.info(f"Phase 2 Step 3: Detecting duplicates for campaign {campaign_id}")

                dedup_result = await self._run_duplicate_detection(campaign_id=campaign_id)

                result.total_duplicates = dedup_result["total_duplicates"]
                result.unique_leads = dedup_result["unique_leads"]

                # Persist results
                await self.campaign_repo.update_dedup_results(
                    campaign_id=campaign_id,
                    total_duplicates=result.total_duplicates,
                    unique_leads=result.unique_leads,
                )
                await self.campaign_repo.create_dedup_log(
                    campaign_id=campaign_id,
                    total_checked=dedup_result.get("total_checked", 0),
                    exact_duplicates=dedup_result.get("exact_duplicates", 0),
                    fuzzy_duplicates=dedup_result.get("fuzzy_duplicates", 0),
                    total_merged=dedup_result.get("total_merged", 0),
                    details=dedup_result.get("details", {}),
                )
                await self.campaign_repo.commit()

                # Check threshold
                if (
                    result.unique_leads < self.config.min_leads_for_cross_dedup
                    and not force_continue
                ):
                    logger.warning(
                        f"Only {result.unique_leads} unique leads, "
                        f"need {self.config.min_leads_for_cross_dedup}. Stopping."
                    )
                    result.status = "stopped"
                    result.stopped_at_agent = "duplicate_detection"
                    result.execution_time_ms = int((time.time() - start_time) * 1000)
                    return result

            # =================================================================
            # Step 4: Cross-Campaign Dedup Agent (2.4)
            # =================================================================
            if not resume_from or resume_from in [
                "lead_list_builder",
                "data_validation",
                "duplicate_detection",
                "cross_campaign_dedup",
            ]:
                logger.info(f"Phase 2 Step 4: Cross-campaign dedup for campaign {campaign_id}")

                cross_dedup_result = await self._run_cross_campaign_dedup(
                    campaign_id=campaign_id,
                    lookback_days=self.config.lookback_days,
                )

                result.total_cross_duplicates = cross_dedup_result["total_excluded"]
                result.available_leads = cross_dedup_result["remaining_leads"]

                # Persist results
                await self.campaign_repo.update_cross_dedup_results(
                    campaign_id=campaign_id,
                    total_cross_duplicates=result.total_cross_duplicates,
                    remaining_leads=result.available_leads,
                )
                await self.campaign_repo.create_cross_campaign_dedup_log(
                    campaign_id=campaign_id,
                    total_checked=cross_dedup_result.get("total_checked", 0),
                    previously_contacted=cross_dedup_result.get("previously_contacted", 0),
                    bounced_excluded=cross_dedup_result.get("bounced_excluded", 0),
                    unsubscribed_excluded=cross_dedup_result.get("unsubscribed_excluded", 0),
                    suppression_list_excluded=cross_dedup_result.get(
                        "suppression_list_excluded", 0
                    ),
                    remaining_leads=result.available_leads,
                    lookback_days=self.config.lookback_days,
                    details=cross_dedup_result.get("details", {}),
                )
                await self.campaign_repo.commit()

                # Check threshold
                if (
                    result.available_leads < self.config.min_leads_for_scoring
                    and not force_continue
                ):
                    logger.warning(
                        f"Only {result.available_leads} available leads, "
                        f"need {self.config.min_leads_for_scoring}. Stopping."
                    )
                    result.status = "stopped"
                    result.stopped_at_agent = "cross_campaign_dedup"
                    result.execution_time_ms = int((time.time() - start_time) * 1000)
                    return result

            # =================================================================
            # Step 5: Lead Scoring Agent (2.5)
            # =================================================================
            if not resume_from or resume_from in [
                "lead_list_builder",
                "data_validation",
                "duplicate_detection",
                "cross_campaign_dedup",
                "lead_scoring",
            ]:
                logger.info(f"Phase 2 Step 5: Scoring leads for campaign {campaign_id}")

                scoring_result = await self._run_lead_scoring(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                )

                result.total_scored = scoring_result["total_scored"]
                result.avg_score = scoring_result["avg_score"]
                result.tier_a_count = scoring_result["tier_a_count"]
                result.tier_b_count = scoring_result["tier_b_count"]
                result.tier_c_count = scoring_result["tier_c_count"]

                # Persist results
                await self.campaign_repo.update_scoring_results(
                    campaign_id=campaign_id,
                    leads_scored=result.total_scored,
                    avg_score=result.avg_score,
                    tier_a=result.tier_a_count,
                    tier_b=result.tier_b_count,
                    tier_c=result.tier_c_count,
                )
                await self.campaign_repo.commit()

                # Check threshold
                if result.tier_a_count < self.config.min_tier_a_for_approval and not force_continue:
                    logger.warning(
                        f"Only {result.tier_a_count} Tier A leads, "
                        f"need {self.config.min_tier_a_for_approval}. Stopping."
                    )
                    result.status = "stopped"
                    result.stopped_at_agent = "lead_scoring"
                    result.execution_time_ms = int((time.time() - start_time) * 1000)
                    return result

            # =================================================================
            # Step 6: Import Finalizer Agent (2.6)
            # =================================================================
            logger.info(f"Phase 2 Step 6: Finalizing import for campaign {campaign_id}")

            import_result = await self._run_import_finalizer(
                campaign_id=campaign_id,
                export_to_sheets=self.config.export_to_sheets,
            )

            result.lead_list_url = import_result.get("sheet_url")
            result.import_summary = import_result.get("summary", {})

            # Persist results
            await self.campaign_repo.update_import_results(
                campaign_id=campaign_id,
                lead_list_url=result.lead_list_url or "",
                import_summary=result.import_summary,
            )
            await self.campaign_repo.log_action(
                campaign_id=campaign_id,
                action="import_completed",
                actor="import_finalizer_agent",
                details=result.import_summary,
            )
            await self.campaign_repo.commit()

            result.status = "completed"
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Phase 2 completed for campaign {campaign_id} in {result.execution_time_ms}ms. "
                f"Leads: {result.available_leads}, Tier A: {result.tier_a_count}, "
                f"Sheet: {result.lead_list_url}"
            )

            return result

        except Exception as e:
            logger.error(f"Phase 2 failed for campaign {campaign_id}: {e}")
            await self.campaign_repo.rollback()
            result.status = "failed"
            result.error = str(e)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    # =========================================================================
    # Agent Runners (Placeholder implementations - agents not yet built)
    # =========================================================================

    async def _run_lead_list_builder(
        self,
        campaign_id: str,
        niche_id: str,
        target_leads: int,
    ) -> dict[str, Any]:
        """
        Run Lead List Builder Agent (2.1) and persist leads.

        Uses the LeadListBuilderAgent to scrape leads from LinkedIn/Apollo.io,
        then bulk inserts them into the database.

        Args:
            campaign_id: Campaign UUID.
            niche_id: Niche UUID for persona lookup.
            target_leads: Number of leads to scrape.

        Returns:
            Dictionary with total_scraped, cost
        """
        logger.info(f"Running Lead List Builder for {target_leads} leads")

        # Get niche and persona data for targeting
        niche = await self.niche_repo.get_niche(niche_id)
        personas = await self.persona_repo.get_personas_by_niche(niche_id)

        # Extract persona criteria
        job_titles: list[str] = []
        seniority_levels: list[str] = []
        industries: list[str] = []
        company_sizes: list[str] = []

        if niche:
            industries = niche.industry or []

        for persona in personas:
            job_titles.extend(persona.job_titles or [])
            seniority_levels.extend(persona.seniority_levels or [])
            company_sizes.extend(persona.company_sizes or [])
            industries.extend(persona.industries or [])

        # Deduplicate criteria
        job_titles = list(set(job_titles))
        seniority_levels = list(set(seniority_levels))
        industries = list(set(industries))
        company_sizes = list(set(company_sizes))

        # Run the agent (pure function - no side effects)
        agent = LeadListBuilderAgent()
        result = await agent.run(
            niche_id=niche_id,
            campaign_id=campaign_id,
            target_leads=target_leads,
            job_titles=job_titles,
            seniority_levels=seniority_levels,
            industries=industries,
            company_sizes=company_sizes,
        )

        # Persist leads to database (orchestrator handles persistence per LEARN-007)
        if result.leads:
            await self.lead_repo.bulk_create_leads(
                campaign_id=campaign_id,
                leads_data=result.leads,
            )
            logger.info(f"Persisted {len(result.leads)} leads to database")

        return {
            "total_scraped": result.total_scraped,
            "cost": result.total_cost_usd,
            "linkedin_leads": result.linkedin_leads,
            "apollo_leads": result.apollo_leads,
            "apify_runs": result.apify_runs,
            "errors": result.errors,
        }

    async def _run_data_validation(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Run Data Validation Agent (2.2) and persist results.

        TODO: Implement when Agent 2.2 is built.

        Returns:
            Dictionary with total_valid, total_invalid
        """
        # Placeholder - will be replaced when agent is implemented
        logger.info(f"[PLACEHOLDER] Would run Data Validation for campaign {campaign_id}")

        # Get lead count from DB
        total = await self.lead_repo.count_campaign_leads(campaign_id)

        return {
            "total_valid": total,
            "total_invalid": 0,
        }

    async def _run_duplicate_detection(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Run Duplicate Detection Agent (2.3) and persist results.

        TODO: Implement when Agent 2.3 is built.

        Returns:
            Dictionary with total_duplicates, unique_leads, etc.
        """
        # Placeholder - will be replaced when agent is implemented
        logger.info(f"[PLACEHOLDER] Would run Duplicate Detection for campaign {campaign_id}")

        total = await self.lead_repo.count_campaign_leads(
            campaign_id,
            exclude_status="invalid",
        )

        return {
            "total_checked": total,
            "total_duplicates": 0,
            "exact_duplicates": 0,
            "fuzzy_duplicates": 0,
            "total_merged": 0,
            "unique_leads": total,
            "details": {},
        }

    async def _run_cross_campaign_dedup(
        self,
        campaign_id: str,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """
        Run Cross-Campaign Dedup Agent (2.4) and persist results.

        TODO: Implement when Agent 2.4 is built.

        Returns:
            Dictionary with total_excluded, remaining_leads, etc.
        """
        # Placeholder - will be replaced when agent is implemented
        logger.info(f"[PLACEHOLDER] Would run Cross-Campaign Dedup for campaign {campaign_id}")

        total = await self.lead_repo.count_campaign_leads(
            campaign_id,
            exclude_status=["invalid", "duplicate"],
        )

        return {
            "total_checked": total,
            "previously_contacted": 0,
            "bounced_excluded": 0,
            "unsubscribed_excluded": 0,
            "suppression_list_excluded": 0,
            "total_excluded": 0,
            "remaining_leads": total,
            "details": {},
        }

    async def _run_lead_scoring(
        self,
        campaign_id: str,
        niche_id: str,
    ) -> dict[str, Any]:
        """
        Run Lead Scoring Agent (2.5) and persist results.

        TODO: Implement when Agent 2.5 is built.

        Returns:
            Dictionary with total_scored, avg_score, tier counts
        """
        # Placeholder - will be replaced when agent is implemented
        logger.info(f"[PLACEHOLDER] Would run Lead Scoring for campaign {campaign_id}")

        total = await self.lead_repo.count_campaign_leads(
            campaign_id,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        return {
            "total_scored": total,
            "avg_score": 0.0,
            "tier_a_count": 0,
            "tier_b_count": 0,
            "tier_c_count": 0,
        }

    async def _run_import_finalizer(
        self,
        campaign_id: str,
        export_to_sheets: bool = True,
    ) -> dict[str, Any]:
        """
        Run Import Finalizer Agent (2.6) and persist results.

        TODO: Implement when Agent 2.6 is built.

        Returns:
            Dictionary with sheet_url, summary
        """
        # Placeholder - will be replaced when agent is implemented
        logger.info(f"[PLACEHOLDER] Would run Import Finalizer for campaign {campaign_id}")

        return {
            "sheet_url": None,
            "summary": {
                "status": "placeholder",
                "message": "Agent not yet implemented",
            },
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_phase2_pipeline(
    session: AsyncSession,
    campaign_id: str,
    niche_id: str,
    config: Phase2Config | None = None,
    **kwargs: Any,
) -> Phase2Result:
    """
    Convenience function to run Phase 2 pipeline.

    Args:
        session: Database session
        campaign_id: Campaign UUID
        niche_id: Niche UUID
        config: Optional Phase2Config
        **kwargs: Additional arguments

    Returns:
        Phase2Result
    """
    orchestrator = Phase2Orchestrator(session, config)
    return await orchestrator.run(
        campaign_id=campaign_id,
        niche_id=niche_id,
        **kwargs,
    )
