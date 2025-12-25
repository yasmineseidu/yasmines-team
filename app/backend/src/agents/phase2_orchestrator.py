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
- Implements retry logic with exponential backoff

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
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.cross_campaign_dedup.agent import CrossCampaignDedupAgent
from src.agents.data_validation.agent import DataValidationAgent
from src.agents.duplicate_detection.agent import DuplicateDetectionAgent
from src.agents.exceptions import (
    AgentExecutionError,
)
from src.agents.import_finalizer.agent import ImportFinalizerAgent
from src.agents.lead_list_builder import LeadListBuilderAgent
from src.agents.lead_scoring.agent import LeadScoringAgent
from src.agents.retry_utils import with_agent_retry
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
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    stopped_at_agent: str | None = None
    error: str | None = None
    agent_errors: dict[str, str] = field(default_factory=dict)  # Agent-specific errors


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
        start_time = time.time()
        result = Phase2Result(campaign_id=campaign_id, niche_id=niche_id)

        # =================================================================
        # Step 1: Lead List Builder Agent (2.1)
        # =================================================================
        if not resume_from or resume_from == "lead_list_builder":
            logger.info(f"Phase 2 Step 1: Building lead list for campaign {campaign_id}")

            try:
                scrape_result = await self._run_lead_list_builder_with_retry(
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

            except AgentExecutionError as e:
                logger.error(f"Lead List Builder Agent failed: {e}")
                result.agent_errors["lead_list_builder"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "lead_list_builder"
                result.error = f"Lead List Builder failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Lead List Builder: {e}")
                result.agent_errors["lead_list_builder"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "lead_list_builder"
                result.error = f"Lead List Builder failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result

            # Check threshold
            if result.total_scraped < self.config.min_leads_for_validation and not force_continue:
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

            try:
                validation_result = await self._run_data_validation_with_retry(
                    campaign_id=campaign_id,
                )

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

            except AgentExecutionError as e:
                logger.error(f"Data Validation Agent failed: {e}")
                result.agent_errors["data_validation"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "data_validation"
                result.error = f"Data Validation failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Data Validation: {e}")
                result.agent_errors["data_validation"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "data_validation"
                result.error = f"Data Validation failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result

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

            try:
                dedup_result = await self._run_duplicate_detection_with_retry(
                    campaign_id=campaign_id,
                )

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

            except AgentExecutionError as e:
                logger.error(f"Duplicate Detection Agent failed: {e}")
                result.agent_errors["duplicate_detection"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "duplicate_detection"
                result.error = f"Duplicate Detection failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Duplicate Detection: {e}")
                result.agent_errors["duplicate_detection"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "duplicate_detection"
                result.error = f"Duplicate Detection failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result

            # Check threshold
            if result.unique_leads < self.config.min_leads_for_cross_dedup and not force_continue:
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

            try:
                cross_dedup_result = await self._run_cross_campaign_dedup_with_retry(
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

            except AgentExecutionError as e:
                logger.error(f"Cross-Campaign Dedup Agent failed: {e}")
                result.agent_errors["cross_campaign_dedup"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "cross_campaign_dedup"
                result.error = f"Cross-Campaign Dedup failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Cross-Campaign Dedup: {e}")
                result.agent_errors["cross_campaign_dedup"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "cross_campaign_dedup"
                result.error = f"Cross-Campaign Dedup failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result

            # Check threshold
            if result.available_leads < self.config.min_leads_for_scoring and not force_continue:
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

            try:
                scoring_result = await self._run_lead_scoring_with_retry(
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

            except AgentExecutionError as e:
                logger.error(f"Lead Scoring Agent failed: {e}")
                result.agent_errors["lead_scoring"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "lead_scoring"
                result.error = f"Lead Scoring failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Lead Scoring: {e}")
                result.agent_errors["lead_scoring"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "lead_scoring"
                result.error = f"Lead Scoring failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                return result

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

        try:
            import_result = await self._run_import_finalizer_with_retry(
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

        except AgentExecutionError as e:
            logger.error(f"Import Finalizer Agent failed: {e}")
            result.agent_errors["import_finalizer"] = str(e)
            result.status = "failed"
            result.stopped_at_agent = "import_finalizer"
            result.error = f"Import Finalizer failed: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.campaign_repo.rollback()
            return result
        except Exception as e:
            logger.error(f"Unexpected error in Import Finalizer: {e}")
            result.agent_errors["import_finalizer"] = str(e)
            result.status = "failed"
            result.stopped_at_agent = "import_finalizer"
            result.error = f"Import Finalizer failed unexpectedly: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.campaign_repo.rollback()
            return result

        result.status = "completed"
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Phase 2 completed for campaign {campaign_id} in {result.execution_time_ms}ms. "
            f"Leads: {result.available_leads}, Tier A: {result.tier_a_count}, "
            f"Sheet: {result.lead_list_url}"
        )

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
            "primary_actor_leads": result.primary_actor_leads,
            "fallback_actor_leads": result.fallback_actor_leads,
            "apify_runs": result.apify_runs,
            "errors": result.errors,
        }

    async def _run_data_validation(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Run Data Validation Agent (2.2) and persist results.

        Validates lead data quality, normalizes fields, and marks invalid leads.

        Returns:
            Dictionary with total_valid, total_invalid, validation_rate
        """
        logger.info(f"Running Data Validation Agent for campaign {campaign_id}")

        # Get leads from database (status='new' from Lead List Builder)
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            status="new",
        )

        if not leads:
            logger.warning(f"No leads found for validation in campaign {campaign_id}")
            return {"total_valid": 0, "total_invalid": 0, "validation_rate": 0.0}

        # Convert to dict format for agent
        leads_data = [lead.to_dict() for lead in leads]

        # Run the agent (pure function - no side effects)
        agent = DataValidationAgent()
        result = await agent.run(campaign_id=campaign_id, leads=leads_data)

        # Persist validation results to database (orchestrator handles persistence)
        if result.batch_results:
            for batch in result.batch_results:
                for lead_result in batch.results:
                    await self.lead_repo.update_lead_validation(
                        lead_id=lead_result.lead_id,
                        is_valid=lead_result.is_valid,
                        validation_errors=lead_result.errors,
                    )

        logger.info(
            f"Data Validation complete: {result.total_valid}/{result.total_processed} valid "
            f"({result.validation_rate:.1%})"
        )

        return {
            "total_valid": result.total_valid,
            "total_invalid": result.total_invalid,
            "validation_rate": result.validation_rate,
            "needs_enrichment": result.needs_enrichment,
            "error_breakdown": result.error_breakdown,
        }

    async def _run_duplicate_detection(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Run Duplicate Detection Agent (2.3) and persist results.

        Detects exact (LinkedIn URL, email) and fuzzy (name+company) duplicates
        within the campaign, merges duplicates keeping the most complete record.

        Returns:
            Dictionary with total_duplicates, unique_leads, etc.
        """
        logger.info(f"Running Duplicate Detection Agent for campaign {campaign_id}")

        # Get valid leads from database
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            status="valid",
        )

        if not leads:
            logger.warning(f"No valid leads for dedup in campaign {campaign_id}")
            return {
                "total_checked": 0,
                "total_duplicates": 0,
                "exact_duplicates": 0,
                "fuzzy_duplicates": 0,
                "total_merged": 0,
                "unique_leads": 0,
                "details": {},
            }

        # Convert to dict format for agent
        leads_data = [lead.to_dict() for lead in leads]

        # Run the agent (pure function - no side effects)
        agent = DuplicateDetectionAgent()
        result = await agent.run(campaign_id=campaign_id, leads=leads_data)

        # Persist dedup results to database (orchestrator handles persistence)
        # TODO: Implement update_lead method in LeadRepository for merged data
        # Primary record updates are handled via mark_as_duplicate relationship
        _ = result.primary_updates  # Acknowledged but not persisted yet

        # Mark duplicates with duplicate_of reference
        for update in result.duplicate_updates:
            await self.lead_repo.mark_as_duplicate(
                lead_id=update["lead_id"],
                duplicate_of=update["duplicate_of"],
            )

        logger.info(
            f"Duplicate Detection complete: {result.total_merged} duplicates merged, "
            f"{result.unique_leads} unique leads (rate={result.duplicate_rate:.1%})"
        )

        return {
            "total_checked": result.total_checked,
            "total_duplicates": result.total_merged,
            "exact_duplicates": result.exact_duplicates,
            "fuzzy_duplicates": result.fuzzy_duplicates,
            "total_merged": result.total_merged,
            "unique_leads": result.unique_leads,
            "duplicate_rate": result.duplicate_rate,
            "details": {
                "duplicate_groups": result.duplicate_groups,
                "merge_results": result.merge_results,
            },
        }

    async def _run_cross_campaign_dedup(
        self,
        campaign_id: str,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """
        Run Cross-Campaign Dedup Agent (2.4) and persist results.

        Checks leads against historical campaigns to exclude:
        - Previously contacted leads
        - Bounced emails
        - Unsubscribed contacts
        - Suppression list entries
        - Fuzzy matches with historical leads

        Returns:
            Dictionary with total_excluded, remaining_leads, etc.
        """
        logger.info(f"Running Cross-Campaign Dedup Agent for campaign {campaign_id}")

        # Get unique leads (not invalid, not duplicate)
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            exclude_status=["invalid", "duplicate"],
        )

        if not leads:
            logger.warning(f"No leads for cross-campaign dedup in campaign {campaign_id}")
            return {
                "total_checked": 0,
                "previously_contacted": 0,
                "bounced_excluded": 0,
                "unsubscribed_excluded": 0,
                "suppression_list_excluded": 0,
                "total_excluded": 0,
                "remaining_leads": 0,
                "details": {},
            }

        # Convert to dict format for agent
        leads_data = [lead.to_dict() for lead in leads]

        # Get historical leads from other campaigns within lookback period
        # TODO: Implement get_historical_leads in LeadRepository
        historical_data: list[dict[str, Any]] = []  # Placeholder until method exists

        # Get suppression list
        suppression_list = await self.lead_repo.get_suppression_list()

        # Run the agent (pure function - no side effects)
        agent = CrossCampaignDedupAgent(
            lookback_days=lookback_days,
            fuzzy_threshold=0.85,
        )
        result = await agent.run(
            campaign_id=campaign_id,
            leads=leads_data,
            historical_data=historical_data,
            suppression_list=suppression_list,
        )

        # Persist exclusion results to database (orchestrator handles persistence)
        for exclusion in result.exclusions:
            await self.lead_repo.mark_cross_campaign_duplicate(
                lead_id=exclusion.lead_id,
                exclusion_reason=exclusion.exclusion_reason,
                excluded_due_to_campaign=exclusion.excluded_due_to_campaign,
            )

        logger.info(
            f"Cross-Campaign Dedup complete: {len(result.exclusions)} excluded, "
            f"{result.remaining_leads} remaining "
            f"(contacted={result.previously_contacted}, bounced={result.bounced_excluded}, "
            f"unsub={result.unsubscribed_excluded}, suppression={result.suppression_list_excluded})"
        )

        return {
            "total_checked": result.total_checked,
            "previously_contacted": result.previously_contacted,
            "bounced_excluded": result.bounced_excluded,
            "unsubscribed_excluded": result.unsubscribed_excluded,
            "suppression_list_excluded": result.suppression_list_excluded,
            "fuzzy_match_excluded": result.fuzzy_match_excluded,
            "total_excluded": len(result.exclusions),
            "remaining_leads": result.remaining_leads,
            "details": {
                "passed_lead_ids": result.passed_lead_ids,
                "lookback_days": result.lookback_days,
            },
        }

    async def _run_lead_scoring(
        self,
        campaign_id: str,
        niche_id: str,
    ) -> dict[str, Any]:
        """
        Run Lead Scoring Agent (2.5) and persist results.

        Scores leads based on:
        - Job Title Match (30%)
        - Seniority Match (20%)
        - Company Size Match (15%)
        - Industry Fit (20%)
        - Location Match (10%)
        - Data Completeness (5%)

        Returns:
            Dictionary with total_scored, avg_score, tier counts
        """
        logger.info(f"Running Lead Scoring Agent for campaign {campaign_id}")

        # Get available leads (not invalid, not duplicate, not cross-campaign duplicate)
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        if not leads:
            logger.warning(f"No leads for scoring in campaign {campaign_id}")
            return {
                "total_scored": 0,
                "avg_score": 0.0,
                "tier_a_count": 0,
                "tier_b_count": 0,
                "tier_c_count": 0,
                "tier_d_count": 0,
            }

        # Convert to dict format for agent
        leads_data = [lead.to_dict() for lead in leads]

        # Build scoring context from niche and personas
        niche = await self.niche_repo.get_niche(niche_id)
        personas = await self.persona_repo.get_personas_by_niche(niche_id)
        industry_fit_scores = await self.niche_repo.get_industry_fit_scores(niche_id)

        scoring_context = {
            "niche": {
                "id": niche_id,
                "name": niche.name if niche else "",
                "industry": niche.industry if niche else [],
            },
            "personas": [
                {
                    "id": str(p.id),
                    "job_titles": p.job_titles or [],
                    "seniority_levels": p.seniority_levels or [],
                    "company_sizes": p.company_sizes or [],
                    "industries": p.industries or [],
                    "locations": p.locations or [],
                }
                for p in personas
            ],
            "industry_fit_scores": industry_fit_scores or {},
            "target_locations": niche.target_locations if niche else [],
        }

        # Run the agent (pure function - no side effects)
        agent = LeadScoringAgent()
        result = await agent.run(
            campaign_id=campaign_id,
            leads=leads_data,
            scoring_context=scoring_context,
        )

        # Persist scoring results to database (orchestrator handles persistence)
        for score in result.lead_scores:
            await self.lead_repo.update_lead_score(
                lead_id=score["lead_id"],
                score=score["score"],
                tier=score["tier"],
                breakdown=score["breakdown"],
                persona_tags=score.get("persona_tags", []),
            )

        logger.info(
            f"Lead Scoring complete: {result.total_scored} scored, "
            f"avg={result.avg_score:.1f}, "
            f"A={result.tier_a_count}, B={result.tier_b_count}, "
            f"C={result.tier_c_count}, D={result.tier_d_count}"
        )

        return {
            "total_scored": result.total_scored,
            "avg_score": result.avg_score,
            "tier_a_count": result.tier_a_count,
            "tier_b_count": result.tier_b_count,
            "tier_c_count": result.tier_c_count,
            "tier_d_count": result.tier_d_count,
            "score_distribution": result.score_distribution,
        }

    async def _run_import_finalizer(
        self,
        campaign_id: str,
        export_to_sheets: bool = True,
    ) -> dict[str, Any]:
        """
        Run Import Finalizer Agent (2.6) and persist results.

        Generates summary reports, exports leads to Google Sheets,
        and prepares for human approval gate.

        Returns:
            Dictionary with sheet_url, summary
        """
        logger.info(f"Running Import Finalizer Agent for campaign {campaign_id}")

        # Get campaign data
        campaign = await self.campaign_repo.get_campaign(campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return {"sheet_url": None, "summary": {"error": "Campaign not found"}}

        campaign_data = campaign.to_dict()

        # Get niche data
        niche = await self.niche_repo.get_niche(campaign.niche_id) if campaign.niche_id else None
        niche_data = niche.to_dict() if niche else None

        # Get all valid leads and filter by tier
        all_leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )
        tier_a_leads = [lead for lead in all_leads if getattr(lead, "tier", None) == "A"]
        tier_b_leads = [lead for lead in all_leads if getattr(lead, "tier", None) == "B"]

        # Convert to dict format for agent
        tier_a_data = [lead.to_dict() for lead in tier_a_leads]
        tier_b_data = [lead.to_dict() for lead in tier_b_leads]
        all_leads_data = [lead.to_dict() for lead in all_leads]

        # Run the agent (pure function - no side effects)
        agent = ImportFinalizerAgent()
        result = await agent.run(
            campaign_id=campaign_id,
            campaign_data=campaign_data,
            niche_data=niche_data,
            tier_a_leads=tier_a_data,
            tier_b_leads=tier_b_data,
            all_leads=all_leads_data,
        )

        if result.success:
            logger.info(
                f"Import Finalizer complete: sheet_url={result.sheet_url}, "
                f"Tier A={len(tier_a_data)}, Tier B={len(tier_b_data)}, Total={len(all_leads_data)}"
            )
        else:
            logger.warning(f"Import Finalizer completed with errors: {result.errors}")

        return {
            "sheet_url": result.sheet_url,
            "sheet_id": result.sheet_id,
            "summary": result.summary.to_dict() if result.summary else {},
            "success": result.success,
            "warnings": result.warnings,
            "errors": result.errors,
        }

    # =========================================================================
    # Retry Wrappers
    # =========================================================================

    @with_agent_retry(agent_id="lead_list_builder", max_attempts=3)
    async def _run_lead_list_builder_with_retry(
        self,
        campaign_id: str,
        niche_id: str,
        target_leads: int,
    ) -> dict[str, Any]:
        """Lead List Builder with retry logic."""
        return await self._run_lead_list_builder(campaign_id, niche_id, target_leads)

    @with_agent_retry(agent_id="data_validation", max_attempts=3)
    async def _run_data_validation_with_retry(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Data Validation with retry logic."""
        return await self._run_data_validation(campaign_id)

    @with_agent_retry(agent_id="duplicate_detection", max_attempts=3)
    async def _run_duplicate_detection_with_retry(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Duplicate Detection with retry logic."""
        return await self._run_duplicate_detection(campaign_id)

    @with_agent_retry(agent_id="cross_campaign_dedup", max_attempts=3)
    async def _run_cross_campaign_dedup_with_retry(
        self,
        campaign_id: str,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """Cross-Campaign Dedup with retry logic."""
        return await self._run_cross_campaign_dedup(campaign_id, lookback_days)

    @with_agent_retry(agent_id="lead_scoring", max_attempts=3)
    async def _run_lead_scoring_with_retry(
        self,
        campaign_id: str,
        niche_id: str,
    ) -> dict[str, Any]:
        """Lead Scoring with retry logic."""
        return await self._run_lead_scoring(campaign_id, niche_id)

    @with_agent_retry(agent_id="import_finalizer", max_attempts=3)
    async def _run_import_finalizer_with_retry(
        self,
        campaign_id: str,
        export_to_sheets: bool = True,
    ) -> dict[str, Any]:
        """Import Finalizer with retry logic."""
        return await self._run_import_finalizer(campaign_id, export_to_sheets)


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
