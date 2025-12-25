"""
Phase 3 Orchestrator - Email Verification & Enrichment Pipeline.

Chains together Phase 3 agents and handles database persistence:
1. Email Verification Agent (3.1) - Waterfall email finding + verification
2. Waterfall Enrichment Agent (3.2) - Tier-based data enrichment
3. Verification Finalizer Agent (3.3) - Quality report + export + human gate

This orchestrator:
- Manages the data flow between agents
- Persists results to the database after each agent
- Handles failures gracefully with proper rollback
- Provides checkpoint/resume capability
- Supports configurable budgets and thresholds
- Triggers human gate for Phase 4 approval
- Implements circuit breaker pattern for email providers
- Implements retry logic with exponential backoff

Usage:
    async with get_session() as session:
        orchestrator = Phase3Orchestrator(session)
        result = await orchestrator.run(
            campaign_id="...",
        )
        print(f"Ready leads: {result.total_ready}")

Per LEARN-007: Agents are pure functions. The orchestrator handles all persistence.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.circuit_breaker import CircuitBreakerRegistry
from src.agents.exceptions import (
    AgentExecutionError,
    CircuitBreakerError,
)
from src.agents.retry_utils import with_agent_retry
from src.database.repositories import (
    CampaignRepository,
    LeadRepository,
    NicheRepository,
    WorkflowCheckpointRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class Phase3Config:
    """Configuration for Phase 3 orchestration."""

    # Email verification settings
    max_email_providers: int = 7  # Stop after this many provider attempts
    email_verification_enabled: bool = True  # Verify emails with Reoon
    email_budget_usd: float = 100.0  # Max spend on email finding

    # Enrichment settings
    enrichment_budget_usd: float = 200.0  # Max spend on enrichment
    tier_a_enrichment_depth: str = "full"  # full, standard, basic
    tier_b_enrichment_depth: str = "standard"
    tier_c_enrichment_depth: str = "basic"

    # Provider waterfall order (for email finding)
    # Order: Tomba → Muraena → Voila Norbert → Nimbler → Icypeas → Anymailfinder → Findymail
    email_provider_order: list[str] = field(
        default_factory=lambda: [
            "tomba",
            "muraena",
            "norbert",  # Voila Norbert
            "nimbler",
            "icypeas",
            "anymailfinder",
            "findymail",
        ]
    )

    # Email verification provider order
    # Reoon first, then MailVerify for catchall emails
    verification_provider_order: list[str] = field(
        default_factory=lambda: [
            "reoon",  # Primary verifier
            "mailverify",  # Secondary + catchall verification
        ]
    )

    # Catchall emails require special verification
    catchall_verification_provider: str = "mailverify"

    # Enrichment provider order
    enrichment_provider_order: list[str] = field(
        default_factory=lambda: [
            "web_search",  # Free first
            "clearbit",
            "apollo",
            "builtwith",
        ]
    )

    # Thresholds
    min_emails_for_enrichment: int = 500
    min_enriched_for_finalization: int = 500
    min_ready_for_approval: int = 100  # Tier A leads minimum

    # Circuit breaker settings
    circuit_breaker_threshold: int = 5  # Failures before opening
    circuit_breaker_timeout_seconds: int = 300  # Recovery timeout

    # Batch processing
    batch_size: int = 100  # Process leads in batches
    parallel_workers: int = 5  # Concurrent API calls

    # Human gate settings
    auto_approve_phase4: bool = False  # Require human approval by default
    approval_timeout_hours: int = 24

    # Slack notifications
    send_slack_notifications: bool = True
    slack_channel: str = "#cold-email-alerts"

    @classmethod
    def pilot_config(cls) -> "Phase3Config":
        """Configuration for pilot campaigns with lower thresholds."""
        return cls(
            email_budget_usd=20.0,
            enrichment_budget_usd=50.0,
            min_emails_for_enrichment=50,
            min_enriched_for_finalization=50,
            min_ready_for_approval=10,
            batch_size=50,
            parallel_workers=3,
        )


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class EmailVerificationResult:
    """Result from Email Verification Agent (3.1)."""

    total_processed: int = 0
    emails_found: int = 0
    emails_verified: int = 0
    emails_invalid: int = 0
    emails_not_found: int = 0
    total_cost_usd: float = 0.0
    provider_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class EnrichmentResult:
    """Result from Waterfall Enrichment Agent (3.2)."""

    total_processed: int = 0
    total_enriched: int = 0
    tier_a_enriched: int = 0
    tier_b_enriched: int = 0
    tier_c_enriched: int = 0
    total_cost_usd: float = 0.0
    provider_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    enrichment_fields: dict[str, int] = field(default_factory=dict)  # field -> count
    errors: list[str] = field(default_factory=list)


@dataclass
class Phase3Result:
    """Result of Phase 3 orchestration."""

    # Identifiers
    campaign_id: str
    workflow_id: str

    # Status
    status: str = "completed"  # completed, stopped, failed, pending_approval

    # Email Verification results (3.1)
    total_leads_processed: int = 0
    emails_found: int = 0
    emails_verified: int = 0
    email_verification_cost: float = 0.0

    # Enrichment results (3.2)
    total_enriched: int = 0
    tier_a_enriched: int = 0
    tier_b_enriched: int = 0
    tier_c_enriched: int = 0
    enrichment_cost: float = 0.0

    # Finalization results (3.3)
    total_ready: int = 0
    tier_a_ready: int = 0
    tier_b_ready: int = 0
    verified_sheet_url: str | None = None
    quality_report_url: str | None = None

    # Costs
    total_cost_usd: float = 0.0

    # Human gate
    pending_approval: bool = False
    approval_requested_at: datetime | None = None

    # Metadata
    execution_time_ms: int = 0
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    stopped_at_agent: str | None = None
    error: str | None = None
    agent_errors: dict[str, str] = field(default_factory=dict)  # Agent-specific errors


# =============================================================================
# Phase 3 Orchestrator
# =============================================================================


class Phase3Orchestrator:
    """
    Orchestrates the complete Phase 3 email verification & enrichment pipeline.

    Manages the flow:
    Email Verification (3.1) → Waterfall Enrichment (3.2) → Verification Finalizer (3.3)

    Handles:
    - Waterfall email finding with multiple providers
    - Cost-optimized enrichment based on lead tier
    - Provider circuit breakers for reliability
    - Checkpoint/resume for long-running operations
    - Human gate triggering at completion
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Phase3Config | None = None,
    ) -> None:
        """
        Initialize orchestrator with database session.

        Args:
            session: SQLAlchemy async session for database operations
            config: Optional configuration (defaults to standard settings)
        """
        self.session = session
        self.config = config or Phase3Config()

        # Initialize repositories
        self.campaign_repo = CampaignRepository(session)
        self.lead_repo = LeadRepository(session)
        self.niche_repo = NicheRepository(session)
        self.checkpoint_repo = WorkflowCheckpointRepository(session)

        # Initialize circuit breaker registry for email providers
        self._circuit_breakers = CircuitBreakerRegistry()
        self._init_circuit_breakers()

    def _init_circuit_breakers(self) -> None:
        """Initialize circuit breakers for all email providers."""
        # Email finder providers (waterfall order from config)
        # Tomba → Muraena → Voila Norbert → Nimbler → Icypeas → Anymailfinder → Findymail
        for provider in self.config.email_provider_order:
            self._circuit_breakers.register(
                name=f"email_finder_{provider}",
                failure_threshold=self.config.circuit_breaker_threshold,
                recovery_timeout_seconds=self.config.circuit_breaker_timeout_seconds,
            )

        # Email verification providers
        # Reoon (primary) → MailVerify (secondary + catchall)
        for provider in self.config.verification_provider_order:
            self._circuit_breakers.register(
                name=f"email_verifier_{provider}",
                failure_threshold=self.config.circuit_breaker_threshold,
                recovery_timeout_seconds=self.config.circuit_breaker_timeout_seconds,
            )

        # Enrichment providers
        for provider in ["clearbit", "apollo", "zoominfo"]:
            self._circuit_breakers.register(
                name=f"enrichment_{provider}",
                failure_threshold=self.config.circuit_breaker_threshold,
                recovery_timeout_seconds=self.config.circuit_breaker_timeout_seconds,
            )

        logger.debug(f"Initialized {len(self._circuit_breakers._breakers)} circuit breakers")

    def get_circuit_breaker_states(self) -> dict[str, Any]:
        """Get current state of all circuit breakers."""
        return self._circuit_breakers.get_all_states()

    def get_open_circuits(self) -> list[str]:
        """Get list of open (blocked) circuits."""
        return self._circuit_breakers.get_open_circuits()

    async def run(
        self,
        campaign_id: str,
        resume_from: str | None = None,
        force_continue: bool = False,
        workflow_id: str | None = None,
    ) -> Phase3Result:
        """
        Execute complete Phase 3 pipeline.

        Steps:
        1. Run Email Verification Agent → find & verify emails
        2. Check threshold → stop if below min_emails_for_enrichment
        3. Run Waterfall Enrichment Agent → enrich lead data
        4. Check threshold → stop if below min_enriched_for_finalization
        5. Run Verification Finalizer Agent → quality report + export
        6. Check threshold → stop if below min_ready_for_approval
        7. Trigger human gate for Phase 4 approval

        Args:
            campaign_id: Campaign UUID
            resume_from: Optional agent ID to resume from
            force_continue: If True, continue even if thresholds not met
            workflow_id: Optional workflow ID (generated if not provided)

        Returns:
            Phase3Result with outcomes and quality report URL
        """
        start_time = time.time()
        workflow_id = workflow_id or str(uuid4())
        result = Phase3Result(campaign_id=campaign_id, workflow_id=workflow_id)

        # Create or update checkpoint
        await self._create_checkpoint(
            workflow_id=workflow_id,
            campaign_id=campaign_id,
            agent_id="phase3_start",
            status="in_progress",
        )

        # =================================================================
        # Step 1: Email Verification Agent (3.1)
        # =================================================================
        if not resume_from or resume_from == "email_verification":
            logger.info(f"Phase 3 Step 1: Email verification for campaign {campaign_id}")

            await self._update_checkpoint(
                workflow_id=workflow_id,
                agent_id="email_verification",
                status="in_progress",
            )

            try:
                email_result = await self._run_email_verification_with_retry(
                    campaign_id=campaign_id,
                )

                result.total_leads_processed = email_result.total_processed
                result.emails_found = email_result.emails_found
                result.emails_verified = email_result.emails_verified
                result.email_verification_cost = email_result.total_cost_usd

                # Persist to campaign
                await self.campaign_repo.update_email_verification_results(
                    campaign_id=campaign_id,
                    emails_found=result.emails_found,
                    emails_verified=result.emails_verified,
                    verification_cost=result.email_verification_cost,
                )
                await self.campaign_repo.log_action(
                    campaign_id=campaign_id,
                    action="emails_verified",
                    actor="email_verification_agent",
                    details={
                        "emails_found": result.emails_found,
                        "emails_verified": result.emails_verified,
                        "cost": result.email_verification_cost,
                    },
                )
                await self.campaign_repo.commit()

                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="email_verification",
                    status="completed",
                    output_data={"emails_verified": result.emails_verified},
                )

            except CircuitBreakerError as e:
                logger.error(f"Email Verification blocked by circuit breaker: {e}")
                result.agent_errors["email_verification"] = f"Circuit breaker open: {e}"
                result.status = "failed"
                result.stopped_at_agent = "email_verification"
                result.error = f"Email providers unavailable: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="email_verification",
                    status="failed",
                    error_message=str(e),
                )
                return result
            except AgentExecutionError as e:
                logger.error(f"Email Verification Agent failed: {e}")
                result.agent_errors["email_verification"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "email_verification"
                result.error = f"Email Verification failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="email_verification",
                    status="failed",
                    error_message=str(e),
                )
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Email Verification: {e}")
                result.agent_errors["email_verification"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "email_verification"
                result.error = f"Email Verification failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="email_verification",
                    status="failed",
                    error_message=str(e),
                )
                return result

            # Check threshold
            if (
                result.emails_verified < self.config.min_emails_for_enrichment
                and not force_continue
            ):
                logger.warning(
                    f"Only {result.emails_verified} verified emails, "
                    f"need {self.config.min_emails_for_enrichment}. Stopping."
                )
                result.status = "stopped"
                result.stopped_at_agent = "email_verification"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return result

        # =================================================================
        # Step 2: Waterfall Enrichment Agent (3.2)
        # =================================================================
        if not resume_from or resume_from in ["email_verification", "waterfall_enrichment"]:
            logger.info(f"Phase 3 Step 2: Enrichment for campaign {campaign_id}")

            await self._update_checkpoint(
                workflow_id=workflow_id,
                agent_id="waterfall_enrichment",
                status="in_progress",
            )

            try:
                enrichment_result = await self._run_waterfall_enrichment_with_retry(
                    campaign_id=campaign_id,
                )

                result.total_enriched = enrichment_result.total_enriched
                result.tier_a_enriched = enrichment_result.tier_a_enriched
                result.tier_b_enriched = enrichment_result.tier_b_enriched
                result.tier_c_enriched = enrichment_result.tier_c_enriched
                result.enrichment_cost = enrichment_result.total_cost_usd

                # Persist to campaign
                await self.campaign_repo.update_enrichment_results(
                    campaign_id=campaign_id,
                    total_enriched=result.total_enriched,
                    enrichment_cost=result.enrichment_cost,
                )
                await self.campaign_repo.log_action(
                    campaign_id=campaign_id,
                    action="leads_enriched",
                    actor="waterfall_enrichment_agent",
                    details={
                        "total_enriched": result.total_enriched,
                        "tier_a": result.tier_a_enriched,
                        "tier_b": result.tier_b_enriched,
                        "tier_c": result.tier_c_enriched,
                        "cost": result.enrichment_cost,
                    },
                )
                await self.campaign_repo.commit()

                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="waterfall_enrichment",
                    status="completed",
                    output_data={"total_enriched": result.total_enriched},
                )

            except CircuitBreakerError as e:
                logger.error(f"Waterfall Enrichment blocked by circuit breaker: {e}")
                result.agent_errors["waterfall_enrichment"] = f"Circuit breaker open: {e}"
                result.status = "failed"
                result.stopped_at_agent = "waterfall_enrichment"
                result.error = f"Enrichment providers unavailable: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="waterfall_enrichment",
                    status="failed",
                    error_message=str(e),
                )
                return result
            except AgentExecutionError as e:
                logger.error(f"Waterfall Enrichment Agent failed: {e}")
                result.agent_errors["waterfall_enrichment"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "waterfall_enrichment"
                result.error = f"Waterfall Enrichment failed: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="waterfall_enrichment",
                    status="failed",
                    error_message=str(e),
                )
                return result
            except Exception as e:
                logger.error(f"Unexpected error in Waterfall Enrichment: {e}")
                result.agent_errors["waterfall_enrichment"] = str(e)
                result.status = "failed"
                result.stopped_at_agent = "waterfall_enrichment"
                result.error = f"Waterfall Enrichment failed unexpectedly: {e}"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                await self.campaign_repo.rollback()
                await self._update_checkpoint(
                    workflow_id=workflow_id,
                    agent_id="waterfall_enrichment",
                    status="failed",
                    error_message=str(e),
                )
                return result

            # Check threshold
            if (
                result.total_enriched < self.config.min_enriched_for_finalization
                and not force_continue
            ):
                logger.warning(
                    f"Only {result.total_enriched} enriched leads, "
                    f"need {self.config.min_enriched_for_finalization}. Stopping."
                )
                result.status = "stopped"
                result.stopped_at_agent = "waterfall_enrichment"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return result

        # =================================================================
        # Step 3: Verification Finalizer Agent (3.3)
        # =================================================================
        logger.info(f"Phase 3 Step 3: Finalization for campaign {campaign_id}")

        await self._update_checkpoint(
            workflow_id=workflow_id,
            agent_id="verification_finalizer",
            status="in_progress",
        )

        try:
            finalizer_result = await self._run_verification_finalizer_with_retry(
                campaign_id=campaign_id,
            )

            result.total_ready = finalizer_result["total_ready"]
            result.tier_a_ready = finalizer_result["tier_a_ready"]
            result.tier_b_ready = finalizer_result["tier_b_ready"]
            result.verified_sheet_url = finalizer_result.get("sheet_url")
            result.quality_report_url = finalizer_result.get("quality_report_url")

            # Persist to campaign
            await self.campaign_repo.update_verification_results(
                campaign_id=campaign_id,
                total_ready=result.total_ready,
                verified_sheet_url=result.verified_sheet_url or "",
            )
            await self.campaign_repo.log_action(
                campaign_id=campaign_id,
                action="verification_completed",
                actor="verification_finalizer_agent",
                details={
                    "total_ready": result.total_ready,
                    "tier_a_ready": result.tier_a_ready,
                    "tier_b_ready": result.tier_b_ready,
                    "sheet_url": result.verified_sheet_url,
                },
            )
            await self.campaign_repo.commit()

            await self._update_checkpoint(
                workflow_id=workflow_id,
                agent_id="verification_finalizer",
                status="completed",
                output_data={
                    "total_ready": result.total_ready,
                    "sheet_url": result.verified_sheet_url,
                },
            )

        except AgentExecutionError as e:
            logger.error(f"Verification Finalizer Agent failed: {e}")
            result.agent_errors["verification_finalizer"] = str(e)
            result.status = "failed"
            result.stopped_at_agent = "verification_finalizer"
            result.error = f"Verification Finalizer failed: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.campaign_repo.rollback()
            await self._update_checkpoint(
                workflow_id=workflow_id,
                agent_id="verification_finalizer",
                status="failed",
                error_message=str(e),
            )
            return result
        except Exception as e:
            logger.error(f"Unexpected error in Verification Finalizer: {e}")
            result.agent_errors["verification_finalizer"] = str(e)
            result.status = "failed"
            result.stopped_at_agent = "verification_finalizer"
            result.error = f"Verification Finalizer failed unexpectedly: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.campaign_repo.rollback()
            await self._update_checkpoint(
                workflow_id=workflow_id,
                agent_id="verification_finalizer",
                status="failed",
                error_message=str(e),
            )
            return result

        # =================================================================
        # Step 4: Calculate totals and trigger human gate
        # =================================================================
        result.total_cost_usd = result.email_verification_cost + result.enrichment_cost

        # Check if we have enough leads for approval
        if result.tier_a_ready < self.config.min_ready_for_approval and not force_continue:
            logger.warning(
                f"Only {result.tier_a_ready} Tier A ready leads, "
                f"need {self.config.min_ready_for_approval}. Flagging for review."
            )
            # Don't stop, but flag for human review

        # Trigger human gate (unless auto-approve is enabled)
        if not self.config.auto_approve_phase4:
            result.pending_approval = True
            result.approval_requested_at = datetime.now(UTC)
            result.status = "pending_approval"

            await self._trigger_human_gate(
                campaign_id=campaign_id,
                workflow_id=workflow_id,
                total_ready=result.total_ready,
                tier_a_ready=result.tier_a_ready,
                tier_b_ready=result.tier_b_ready,
                sheet_url=result.verified_sheet_url,
            )

            logger.info(
                f"Phase 3 completed, pending approval for campaign {campaign_id}. "
                f"Ready: {result.total_ready} leads (Tier A: {result.tier_a_ready})"
            )
        else:
            result.status = "completed"
            logger.info(
                f"Phase 3 completed (auto-approved) for campaign {campaign_id}. "
                f"Ready: {result.total_ready} leads"
            )

        result.execution_time_ms = int((time.time() - start_time) * 1000)

        # Update final checkpoint
        await self._update_checkpoint(
            workflow_id=workflow_id,
            agent_id="phase3_complete",
            status=result.status,
            output_data={
                "total_ready": result.total_ready,
                "total_cost_usd": result.total_cost_usd,
            },
        )

        return result

    # =========================================================================
    # Agent Runners (Placeholder implementations - agents not yet built)
    # =========================================================================

    async def _run_email_verification(
        self,
        campaign_id: str,
    ) -> EmailVerificationResult:
        """
        Run Email Verification Agent (3.1) and persist results.

        Uses waterfall pattern to find emails:
        Tomba → Hunter → Findymail → Icypeas → Muraena → Norbert → Apollo

        Then verifies emails with Reoon.

        Returns:
            EmailVerificationResult with found/verified counts and costs
        """
        logger.info(f"Running Email Verification Agent for campaign {campaign_id}")

        # TODO: Wire to real EmailVerificationAgent when implemented
        # For now, return placeholder that simulates the expected behavior

        # Get leads that need email finding (have LinkedIn URL but no email)
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            needs_email=True,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        total_processed = len(leads) if leads else 0

        # PLACEHOLDER: Simulate email finding results
        # Real implementation will call:
        # agent = EmailVerificationAgent(config=self.config)
        # result = await agent.run(campaign_id=campaign_id, leads=leads_data)

        logger.warning(
            f"Email Verification Agent not yet implemented. "
            f"Returning placeholder for {total_processed} leads."
        )

        return EmailVerificationResult(
            total_processed=total_processed,
            emails_found=0,  # Placeholder
            emails_verified=0,  # Placeholder
            emails_invalid=0,
            emails_not_found=total_processed,
            total_cost_usd=0.0,
            provider_breakdown={},
            errors=["Agent not implemented - placeholder result"],
        )

    async def _run_waterfall_enrichment(
        self,
        campaign_id: str,
    ) -> EnrichmentResult:
        """
        Run Waterfall Enrichment Agent (3.2) and persist results.

        Tier-based enrichment depth:
        - Tier A: Full enrichment (all providers)
        - Tier B: Standard enrichment (web + Clearbit)
        - Tier C: Basic enrichment (web search only)

        Returns:
            EnrichmentResult with enrichment counts and costs
        """
        logger.info(f"Running Waterfall Enrichment Agent for campaign {campaign_id}")

        # TODO: Wire to real WaterfallEnrichmentAgent when implemented
        # For now, return placeholder that simulates the expected behavior

        # Get leads with verified emails
        leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            has_verified_email=True,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        total_processed = len(leads) if leads else 0

        # Count by tier
        tier_a_count = 0
        tier_b_count = 0
        tier_c_count = 0

        if leads:
            for lead in leads:
                tier = getattr(lead, "tier", None)
                if tier == "A":
                    tier_a_count += 1
                elif tier == "B":
                    tier_b_count += 1
                else:
                    tier_c_count += 1

        # PLACEHOLDER: Simulate enrichment results
        # Real implementation will call:
        # agent = WaterfallEnrichmentAgent(config=self.config)
        # result = await agent.run(campaign_id=campaign_id, leads=leads_data)

        logger.warning(
            f"Waterfall Enrichment Agent not yet implemented. "
            f"Returning placeholder for {total_processed} leads."
        )

        return EnrichmentResult(
            total_processed=total_processed,
            total_enriched=0,  # Placeholder
            tier_a_enriched=0,
            tier_b_enriched=0,
            tier_c_enriched=0,
            total_cost_usd=0.0,
            provider_breakdown={},
            enrichment_fields={},
            errors=["Agent not implemented - placeholder result"],
        )

    async def _run_verification_finalizer(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Run Verification Finalizer Agent (3.3) and persist results.

        Generates quality report, exports verified leads to Sheets,
        and prepares for Phase 4 human gate.

        Returns:
            Dictionary with total_ready, sheet_url, quality_report_url
        """
        logger.info(f"Running Verification Finalizer Agent for campaign {campaign_id}")

        # TODO: Wire to real VerificationFinalizerAgent when implemented
        # For now, return placeholder that simulates the expected behavior

        # Get leads that are ready (have verified email + enrichment)
        tier_a_leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            tier="A",
            has_verified_email=True,
            is_enriched=True,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        tier_b_leads = await self.lead_repo.get_campaign_leads(
            campaign_id=campaign_id,
            tier="B",
            has_verified_email=True,
            is_enriched=True,
            exclude_status=["invalid", "duplicate", "cross_campaign_duplicate"],
        )

        tier_a_count = len(tier_a_leads) if tier_a_leads else 0
        tier_b_count = len(tier_b_leads) if tier_b_leads else 0
        total_ready = tier_a_count + tier_b_count

        # PLACEHOLDER: Simulate finalizer results
        # Real implementation will call:
        # agent = VerificationFinalizerAgent()
        # result = await agent.run(campaign_id=campaign_id, tier_a_leads=..., tier_b_leads=...)

        logger.warning(
            f"Verification Finalizer Agent not yet implemented. "
            f"Returning placeholder for {total_ready} ready leads."
        )

        return {
            "total_ready": total_ready,
            "tier_a_ready": tier_a_count,
            "tier_b_ready": tier_b_count,
            "sheet_url": None,  # Placeholder
            "quality_report_url": None,  # Placeholder
            "summary": {"error": "Agent not implemented - placeholder result"},
        }

    # =========================================================================
    # Checkpoint Management
    # =========================================================================

    async def _create_checkpoint(
        self,
        workflow_id: str,
        campaign_id: str,
        agent_id: str,
        status: str,
    ) -> None:
        """Create initial checkpoint for workflow."""
        await self.checkpoint_repo.create_checkpoint(
            workflow_id=workflow_id,
            workflow_type="phase3_orchestrator",
            agent_id=agent_id,
            step_id="start",
            status=status,
            campaign_id=campaign_id,
        )
        await self.checkpoint_repo.commit()

    async def _update_checkpoint(
        self,
        workflow_id: str,
        agent_id: str,
        status: str,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update checkpoint with agent progress."""
        await self.checkpoint_repo.update_checkpoint(
            workflow_id=workflow_id,
            agent_id=agent_id,
            status=status,
            output_data=output_data,
            error_message=error_message,
        )
        await self.checkpoint_repo.commit()

    # =========================================================================
    # Human Gate
    # =========================================================================

    async def _trigger_human_gate(
        self,
        campaign_id: str,
        workflow_id: str,
        total_ready: int,
        tier_a_ready: int,
        tier_b_ready: int,
        sheet_url: str | None,
    ) -> None:
        """
        Trigger human approval gate for Phase 4.

        Sends Slack notification with approval buttons:
        - Approve Full: Proceed with all A+B leads
        - Tier A Only: Proceed with only Tier A leads
        - Need More: Request re-enrichment

        Args:
            campaign_id: Campaign UUID
            workflow_id: Workflow UUID
            total_ready: Total leads ready for personalization
            tier_a_ready: Tier A leads ready
            tier_b_ready: Tier B leads ready
            sheet_url: Google Sheets URL with lead data
        """
        logger.info(
            f"Triggering human gate for Phase 4 approval. "
            f"Campaign: {campaign_id}, Ready: {total_ready} leads"
        )

        if not self.config.send_slack_notifications:
            logger.info("Slack notifications disabled, skipping human gate trigger")
            return

        # TODO: Integrate with Slack client when available
        # For now, just log the approval request

        # Real implementation will call:
        # await slack_client.send_approval_request(
        #     channel=self.config.slack_channel,
        #     campaign_id=campaign_id,
        #     workflow_id=workflow_id,
        #     message=f"Phase 3 Complete: {total_ready} leads ready for personalization",
        #     buttons=[
        #         {"text": "Approve Full (A+B)", "action": "approve_full", "value": workflow_id},
        #         {"text": "Tier A Only", "action": "approve_tier_a", "value": workflow_id},
        #         {"text": "Need More", "action": "request_more", "value": workflow_id},
        #     ],
        #     attachments=[
        #         {"title": "Lead Summary", "fields": [
        #             {"title": "Tier A", "value": str(tier_a_ready), "short": True},
        #             {"title": "Tier B", "value": str(tier_b_ready), "short": True},
        #             {"title": "Total", "value": str(total_ready), "short": True},
        #         ]},
        #         {"title": "Lead List", "value": sheet_url or "Not available"},
        #     ],
        # )

        logger.warning(
            "Slack integration not yet implemented. "
            f"Human gate triggered for campaign {campaign_id} with {total_ready} leads."
        )

    # =========================================================================
    # Retry Wrappers
    # =========================================================================

    @with_agent_retry(agent_id="email_verification", max_attempts=3)
    async def _run_email_verification_with_retry(
        self,
        campaign_id: str,
    ) -> "EmailVerificationResult":
        """Email Verification with retry logic."""
        return await self._run_email_verification(campaign_id)

    @with_agent_retry(agent_id="waterfall_enrichment", max_attempts=3)
    async def _run_waterfall_enrichment_with_retry(
        self,
        campaign_id: str,
    ) -> "EnrichmentResult":
        """Waterfall Enrichment with retry logic."""
        return await self._run_waterfall_enrichment(campaign_id)

    @with_agent_retry(agent_id="verification_finalizer", max_attempts=3)
    async def _run_verification_finalizer_with_retry(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Verification Finalizer with retry logic."""
        return await self._run_verification_finalizer(campaign_id)


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_phase3_pipeline(
    session: AsyncSession,
    campaign_id: str,
    config: Phase3Config | None = None,
    **kwargs: Any,
) -> Phase3Result:
    """
    Convenience function to run Phase 3 pipeline.

    Args:
        session: Database session
        campaign_id: Campaign UUID
        config: Optional Phase3Config
        **kwargs: Additional arguments

    Returns:
        Phase3Result
    """
    orchestrator = Phase3Orchestrator(session, config)
    return await orchestrator.run(
        campaign_id=campaign_id,
        **kwargs,
    )
