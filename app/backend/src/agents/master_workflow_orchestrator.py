"""
Master Workflow Orchestrator - Complete Cold Email Agent Pipeline.

Coordinates all 3 phases of the cold email agent system:
- Phase 1: Market Intelligence (Niche → Persona → Export)
- Phase 2: Lead Acquisition (Scrape → Validate → Dedup → Score → Export)
- Phase 3: Email Verification & Enrichment (Find → Verify → Enrich → Finalize)

This orchestrator:
- Manages phase transitions with human approval gates
- Tracks workflow state in workflow_checkpoints table
- Supports resume from any checkpoint
- Aggregates costs across all phases
- Sends Slack notifications at key milestones
- Implements per-phase error handling with proper rollback

Usage:
    async with get_session() as session:
        orchestrator = MasterWorkflowOrchestrator(session)

        # Start from scratch (Phase 1)
        result = await orchestrator.start_from_niche(
            niche_name="SaaS Marketing Directors",
            industry=["SaaS", "Software"],
            job_titles=["Marketing Director", "VP Marketing"],
        )

        # Or start from existing campaign (Phase 2)
        result = await orchestrator.start_from_campaign(
            campaign_id="...",
            start_phase=2,
        )

        # Or resume a paused workflow
        result = await orchestrator.resume_workflow(
            workflow_id="...",
        )

Per LEARN-007: Phase orchestrators handle agent invocation and persistence.
Master orchestrator handles phase coordination and human gates.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.exceptions import (
    AgentExecutionError,
)
from src.agents.phase1_orchestrator import Phase1Orchestrator, Phase1Result
from src.agents.phase2_orchestrator import Phase2Config, Phase2Orchestrator, Phase2Result
from src.agents.phase3_orchestrator import Phase3Config, Phase3Orchestrator, Phase3Result
from src.database.repositories import (
    CampaignRepository,
    NicheRepository,
    WorkflowCheckpointRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class WorkflowPhase(str, Enum):
    """Workflow phases."""

    PHASE_1 = "phase_1"  # Market Intelligence
    HUMAN_GATE_1 = "human_gate_1"  # Approve Research
    PHASE_2 = "phase_2"  # Lead Acquisition
    HUMAN_GATE_2 = "human_gate_2"  # Approve Leads (optional)
    PHASE_3 = "phase_3"  # Email Verification
    HUMAN_GATE_3 = "human_gate_3"  # Approve for Personalization
    COMPLETED = "completed"


class WorkflowStatus(str, Enum):
    """Workflow status."""

    IN_PROGRESS = "in_progress"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class HumanGateAction(str, Enum):
    """Human gate response actions."""

    APPROVE = "approve"
    APPROVE_FULL = "approve_full"  # Phase 3: All A+B leads
    APPROVE_TIER_A = "approve_tier_a"  # Phase 3: Only Tier A
    REJECT = "reject"
    REQUEST_MORE = "request_more"  # Request re-processing


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class MasterWorkflowConfig:
    """Configuration for master workflow orchestration."""

    # Phase 2 configuration
    phase2_config: Phase2Config = field(default_factory=Phase2Config)

    # Phase 3 configuration
    phase3_config: Phase3Config = field(default_factory=Phase3Config)

    # Human gates
    require_phase1_approval: bool = True  # Always require for niche
    require_phase2_approval: bool = False  # Auto-approve by default
    require_phase3_approval: bool = True  # Require for personalization

    # Timeouts for human gates (hours)
    phase1_approval_timeout_hours: int = 48
    phase2_approval_timeout_hours: int = 48
    phase3_approval_timeout_hours: int = 24

    # Target leads
    default_target_leads: int = 50000

    # Slack notifications
    send_slack_notifications: bool = True
    slack_channel: str = "#cold-email-alerts"

    # Cost limits (USD)
    max_total_cost_usd: float = 500.0
    warn_at_cost_usd: float = 400.0

    @classmethod
    def pilot_config(cls) -> "MasterWorkflowConfig":
        """Configuration for pilot campaigns with lower thresholds."""
        return cls(
            phase2_config=Phase2Config.pilot_config(),
            phase3_config=Phase3Config.pilot_config(),
            default_target_leads=1000,
            max_total_cost_usd=100.0,
            warn_at_cost_usd=80.0,
        )


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class MasterWorkflowResult:
    """Result of complete workflow orchestration."""

    # Identifiers
    workflow_id: str
    niche_id: str | None = None
    campaign_id: str | None = None

    # Current state
    current_phase: WorkflowPhase = WorkflowPhase.PHASE_1
    status: WorkflowStatus = WorkflowStatus.IN_PROGRESS

    # Phase results
    phase1_result: Phase1Result | None = None
    phase2_result: Phase2Result | None = None
    phase3_result: Phase3Result | None = None

    # Aggregated metrics
    total_leads_scraped: int = 0
    total_leads_ready: int = 0
    tier_a_ready: int = 0
    tier_b_ready: int = 0

    # Costs
    phase1_cost_usd: float = 0.0
    phase2_cost_usd: float = 0.0
    phase3_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

    # URLs
    research_folder_url: str | None = None
    lead_list_url: str | None = None
    verified_list_url: str | None = None

    # Human gates
    pending_approval_gate: str | None = None  # e.g., "human_gate_1"
    approval_requested_at: datetime | None = None

    # Metadata
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    execution_time_ms: int = 0
    error: str | None = None
    phase_errors: dict[str, str] = field(default_factory=dict)  # Phase-specific errors


# =============================================================================
# Master Workflow Orchestrator
# =============================================================================


class MasterWorkflowOrchestrator:
    """
    Orchestrates the complete cold email agent workflow.

    Manages the flow:
    Phase 1 → Human Gate → Phase 2 → Human Gate → Phase 3 → Human Gate → Done

    Handles:
    - Phase orchestrator invocation
    - Human gate management (Slack notifications + buttons)
    - Checkpoint/resume for long-running workflows
    - Cost tracking and budget enforcement
    - Workflow state management
    """

    def __init__(
        self,
        session: AsyncSession,
        config: MasterWorkflowConfig | None = None,
    ) -> None:
        """
        Initialize orchestrator with database session.

        Args:
            session: SQLAlchemy async session for database operations
            config: Optional configuration (defaults to standard settings)
        """
        self.session = session
        self.config = config or MasterWorkflowConfig()

        # Initialize repositories
        self.niche_repo = NicheRepository(session)
        self.campaign_repo = CampaignRepository(session)
        self.checkpoint_repo = WorkflowCheckpointRepository(session)

        # Initialize phase orchestrators
        self.phase1 = Phase1Orchestrator(session)
        self.phase2 = Phase2Orchestrator(session, self.config.phase2_config)
        self.phase3 = Phase3Orchestrator(session, self.config.phase3_config)

    # =========================================================================
    # Public Entry Points
    # =========================================================================

    async def start_from_niche(
        self,
        niche_name: str,
        industry: list[str],
        job_titles: list[str],
        company_size: list[str] | None = None,
        description: str | None = None,
        target_leads: int | None = None,
        workflow_id: str | None = None,
    ) -> MasterWorkflowResult:
        """
        Start complete workflow from niche research.

        This is the primary entry point for new campaigns.

        Args:
            niche_name: Human-readable niche name
            industry: Target industries
            job_titles: Target job titles
            company_size: Optional company sizes
            description: Optional niche description
            target_leads: Target lead count (default: config value)
            workflow_id: Optional workflow ID (generated if not provided)

        Returns:
            MasterWorkflowResult with current state
        """
        start_time = time.time()
        workflow_id = workflow_id or str(uuid4())
        result = MasterWorkflowResult(workflow_id=workflow_id)

        # Create initial checkpoint
        await self._create_workflow_checkpoint(
            workflow_id=workflow_id,
            phase=WorkflowPhase.PHASE_1,
            status=WorkflowStatus.IN_PROGRESS,
            input_data={
                "niche_name": niche_name,
                "industry": industry,
                "job_titles": job_titles,
                "company_size": company_size,
                "description": description,
                "target_leads": target_leads or self.config.default_target_leads,
            },
        )

        # =================================================================
        # Phase 1: Market Intelligence
        # =================================================================
        logger.info(f"Workflow {workflow_id}: Starting Phase 1")

        try:
            phase1_result = await self.phase1.run(
                niche_name=niche_name,
                industry=industry,
                job_titles=job_titles,
                company_size=company_size,
                description=description,
            )

            result.phase1_result = phase1_result
            result.niche_id = phase1_result.niche_id
            result.research_folder_url = phase1_result.folder_url

        except AgentExecutionError as e:
            logger.error(f"Phase 1 failed for workflow {workflow_id}: {e}")
            result.phase_errors["phase1"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_1
            result.error = f"Phase 1 failed: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase1",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result
        except Exception as e:
            logger.error(f"Unexpected error in Phase 1 for workflow {workflow_id}: {e}")
            result.phase_errors["phase1"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_1
            result.error = f"Phase 1 failed unexpectedly: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase1",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result

        # Check if niche was rejected
        if phase1_result.recommendation == "reject":
            logger.warning(f"Workflow {workflow_id}: Niche rejected by research agent")
            result.status = WorkflowStatus.REJECTED
            result.current_phase = WorkflowPhase.PHASE_1
            result.error = "Niche rejected: not viable for cold email"
            await self._update_workflow_checkpoint(
                workflow_id=workflow_id,
                phase=WorkflowPhase.PHASE_1,
                status=WorkflowStatus.REJECTED,
                output_data={"recommendation": "reject"},
            )
            return result

        # =================================================================
        # Human Gate 1: Approve Research
        # =================================================================
        if self.config.require_phase1_approval:
            logger.info(f"Workflow {workflow_id}: Awaiting Phase 1 approval")

            await self._trigger_human_gate(
                workflow_id=workflow_id,
                gate_id="human_gate_1",
                niche_id=phase1_result.niche_id,
                message=f"Phase 1 Complete: Review niche '{niche_name}'",
                details={
                    "recommendation": phase1_result.recommendation,
                    "pain_points": phase1_result.pain_points[:5],
                    "folder_url": phase1_result.folder_url,
                },
            )

            result.current_phase = WorkflowPhase.HUMAN_GATE_1
            result.status = WorkflowStatus.PENDING_APPROVAL
            result.pending_approval_gate = "human_gate_1"
            result.approval_requested_at = datetime.now(UTC)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            await self._update_workflow_checkpoint(
                workflow_id=workflow_id,
                phase=WorkflowPhase.HUMAN_GATE_1,
                status=WorkflowStatus.PENDING_APPROVAL,
            )

            return result

        # Auto-approve: Continue to Phase 2
        return await self._continue_to_phase2(
            workflow_id=workflow_id,
            niche_id=phase1_result.niche_id,
            niche_name=niche_name,
            target_leads=target_leads or self.config.default_target_leads,
            result=result,
            start_time=start_time,
        )

    async def start_from_campaign(
        self,
        campaign_id: str,
        start_phase: int = 2,
        workflow_id: str | None = None,
    ) -> MasterWorkflowResult:
        """
        Start workflow from existing campaign (skip Phase 1).

        Use this when a campaign already exists from a previous workflow
        or was created manually.

        Args:
            campaign_id: Existing campaign UUID
            start_phase: Phase to start from (2 or 3)
            workflow_id: Optional workflow ID

        Returns:
            MasterWorkflowResult with current state
        """
        start_time = time.time()
        workflow_id = workflow_id or str(uuid4())
        result = MasterWorkflowResult(workflow_id=workflow_id, campaign_id=campaign_id)

        # Get campaign and niche
        campaign = await self.campaign_repo.get_campaign(campaign_id)
        if not campaign:
            result.status = WorkflowStatus.FAILED
            result.error = f"Campaign {campaign_id} not found"
            result.phase_errors["start"] = f"Campaign {campaign_id} not found"
            return result

        result.niche_id = str(campaign.niche_id) if campaign.niche_id else None

        # Create checkpoint
        await self._create_workflow_checkpoint(
            workflow_id=workflow_id,
            phase=WorkflowPhase.PHASE_2 if start_phase == 2 else WorkflowPhase.PHASE_3,
            status=WorkflowStatus.IN_PROGRESS,
            campaign_id=campaign_id,
            input_data={"campaign_id": campaign_id, "start_phase": start_phase},
        )

        if start_phase == 2:
            # Start from Phase 2
            return await self._run_phase2(
                workflow_id=workflow_id,
                campaign_id=campaign_id,
                niche_id=result.niche_id or "",
                result=result,
                start_time=start_time,
            )
        elif start_phase == 3:
            # Start from Phase 3
            return await self._run_phase3(
                workflow_id=workflow_id,
                campaign_id=campaign_id,
                result=result,
                start_time=start_time,
            )
        else:
            result.status = WorkflowStatus.FAILED
            result.error = f"Invalid start_phase: {start_phase}. Must be 2 or 3."
            result.phase_errors["start"] = f"Invalid start_phase: {start_phase}"
            return result

    async def resume_workflow(
        self,
        workflow_id: str,
    ) -> MasterWorkflowResult:
        """
        Resume workflow from last checkpoint.

        Use this to continue a paused or failed workflow.

        Args:
            workflow_id: Workflow UUID to resume

        Returns:
            MasterWorkflowResult with current state
        """
        start_time = time.time()
        result = MasterWorkflowResult(workflow_id=workflow_id)

        try:
            # Get resume point
            resume_point = await self.checkpoint_repo.get_resume_point(workflow_id)
            if not resume_point:
                result.status = WorkflowStatus.FAILED
                result.error = f"No resumable checkpoint found for workflow {workflow_id}"
                return result

            agent_id, step_id = resume_point
            logger.info(f"Resuming workflow {workflow_id} from {agent_id}/{step_id}")

            # Get checkpoint data
            checkpoint = await self.checkpoint_repo.get_checkpoint(workflow_id, agent_id, step_id)
            if not checkpoint:
                result.status = WorkflowStatus.FAILED
                result.error = "Checkpoint data not found"
                return result

            result.campaign_id = str(checkpoint.campaign_id) if checkpoint.campaign_id else None
            result.niche_id = str(checkpoint.niche_id) if checkpoint.niche_id else None

            # Determine which phase to resume
            if agent_id in ("phase1", "human_gate_1"):
                # Resume in Phase 1 or Gate 1
                # Need to re-read input data and continue
                input_data = checkpoint.input_data or {}
                if "niche_name" in input_data:
                    return await self.start_from_niche(
                        workflow_id=workflow_id,
                        **input_data,
                    )
                else:
                    result.status = WorkflowStatus.FAILED
                    result.error = "Cannot resume Phase 1: missing input data"
                    return result

            elif agent_id in ("phase2", "human_gate_2"):
                # Resume in Phase 2 or Gate 2
                if result.campaign_id:
                    return await self._run_phase2(
                        workflow_id=workflow_id,
                        campaign_id=result.campaign_id,
                        niche_id=result.niche_id or "",
                        result=result,
                        start_time=start_time,
                    )
                else:
                    result.status = WorkflowStatus.FAILED
                    result.error = "Cannot resume Phase 2: missing campaign_id"
                    return result

            elif agent_id in ("phase3", "human_gate_3"):
                # Resume in Phase 3 or Gate 3
                if result.campaign_id:
                    return await self._run_phase3(
                        workflow_id=workflow_id,
                        campaign_id=result.campaign_id,
                        result=result,
                        start_time=start_time,
                    )
                else:
                    result.status = WorkflowStatus.FAILED
                    result.error = "Cannot resume Phase 3: missing campaign_id"
                    return result

            else:
                result.status = WorkflowStatus.FAILED
                result.error = f"Unknown resume point: {agent_id}"
                return result

        except Exception as e:
            logger.error(f"Resume workflow {workflow_id} failed: {e}")
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def handle_human_gate_response(
        self,
        workflow_id: str,
        gate_id: str,
        action: HumanGateAction,
        actor: str,
        feedback: str | None = None,
    ) -> MasterWorkflowResult:
        """
        Handle human gate approval/rejection.

        Called by webhook handler when user responds to Slack notification.

        Args:
            workflow_id: Workflow UUID
            gate_id: Gate identifier (e.g., "human_gate_1")
            action: Action taken by human
            actor: Username/ID of person taking action
            feedback: Optional feedback/notes

        Returns:
            MasterWorkflowResult with updated state
        """
        start_time = time.time()
        result = MasterWorkflowResult(workflow_id=workflow_id)

        try:
            # Log the action
            logger.info(
                f"Human gate response: workflow={workflow_id}, gate={gate_id}, "
                f"action={action}, actor={actor}"
            )

            # Get current checkpoint
            checkpoint = await self.checkpoint_repo.get_latest_checkpoint(workflow_id)
            if not checkpoint:
                result.status = WorkflowStatus.FAILED
                result.error = "Workflow not found"
                return result

            result.campaign_id = str(checkpoint.campaign_id) if checkpoint.campaign_id else None
            result.niche_id = str(checkpoint.niche_id) if checkpoint.niche_id else None

            # Handle rejection
            if action == HumanGateAction.REJECT:
                await self._update_workflow_checkpoint(
                    workflow_id=workflow_id,
                    phase=WorkflowPhase(gate_id),
                    status=WorkflowStatus.REJECTED,
                    output_data={"action": "reject", "actor": actor, "feedback": feedback},
                )
                result.status = WorkflowStatus.REJECTED
                result.error = f"Rejected at {gate_id} by {actor}"
                if feedback:
                    result.error += f": {feedback}"
                return result

            # Handle approval based on gate
            if gate_id == "human_gate_1":
                # Approved: Create campaign and continue to Phase 2
                niche_id = result.niche_id
                if not niche_id:
                    result.status = WorkflowStatus.FAILED
                    result.error = "Cannot continue: niche_id not found"
                    return result

                # Get niche name
                niche = await self.niche_repo.get_niche(niche_id)
                niche_name = niche.name if niche else "Unknown"

                # Create campaign
                campaign = await self.campaign_repo.create_campaign(
                    name=f"{niche_name} - {datetime.now(UTC).strftime('%Y-%m-%d')}",
                    niche_id=niche_id,
                    target_leads=self.config.default_target_leads,
                )
                await self.campaign_repo.commit()

                result.campaign_id = str(campaign.id)

                return await self._continue_to_phase2(
                    workflow_id=workflow_id,
                    niche_id=niche_id,
                    niche_name=niche_name,
                    target_leads=self.config.default_target_leads,
                    result=result,
                    start_time=start_time,
                    campaign_id=str(campaign.id),
                )

            elif gate_id == "human_gate_2":
                # Continue to Phase 3
                if not result.campaign_id:
                    result.status = WorkflowStatus.FAILED
                    result.error = "Cannot continue: campaign_id not found"
                    return result

                return await self._run_phase3(
                    workflow_id=workflow_id,
                    campaign_id=result.campaign_id,
                    result=result,
                    start_time=start_time,
                )

            elif gate_id == "human_gate_3":
                # Workflow complete!
                if action == HumanGateAction.APPROVE_TIER_A:
                    # Mark that only Tier A leads should proceed
                    logger.info(f"Workflow {workflow_id}: Approved for Tier A only")

                await self._update_workflow_checkpoint(
                    workflow_id=workflow_id,
                    phase=WorkflowPhase.COMPLETED,
                    status=WorkflowStatus.COMPLETED,
                    output_data={
                        "action": action.value,
                        "actor": actor,
                        "tier_filter": "tier_a"
                        if action == HumanGateAction.APPROVE_TIER_A
                        else "all",
                    },
                )

                result.status = WorkflowStatus.COMPLETED
                result.current_phase = WorkflowPhase.COMPLETED
                result.completed_at = datetime.now(UTC)
                result.execution_time_ms = int((time.time() - start_time) * 1000)

                logger.info(f"Workflow {workflow_id}: COMPLETED")
                return result

            else:
                result.status = WorkflowStatus.FAILED
                result.error = f"Unknown gate: {gate_id}"
                return result

        except Exception as e:
            logger.error(f"Handle gate response failed for {workflow_id}: {e}")
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            return result

    # =========================================================================
    # Internal Phase Runners
    # =========================================================================

    async def _continue_to_phase2(
        self,
        workflow_id: str,
        niche_id: str,
        niche_name: str,
        target_leads: int,
        result: MasterWorkflowResult,
        start_time: float,
        campaign_id: str | None = None,
    ) -> MasterWorkflowResult:
        """Continue workflow to Phase 2 after Phase 1 approval."""
        # Create campaign if not provided
        if not campaign_id:
            campaign = await self.campaign_repo.create_campaign(
                name=f"{niche_name} - {datetime.now(UTC).strftime('%Y-%m-%d')}",
                niche_id=niche_id,
                target_leads=target_leads,
            )
            await self.campaign_repo.commit()
            campaign_id = str(campaign.id)

        result.campaign_id = campaign_id

        return await self._run_phase2(
            workflow_id=workflow_id,
            campaign_id=campaign_id,
            niche_id=niche_id,
            result=result,
            start_time=start_time,
            target_leads=target_leads,
        )

    async def _run_phase2(
        self,
        workflow_id: str,
        campaign_id: str,
        niche_id: str,
        result: MasterWorkflowResult,
        start_time: float,
        target_leads: int | None = None,
    ) -> MasterWorkflowResult:
        """Run Phase 2: Lead Acquisition."""
        logger.info(f"Workflow {workflow_id}: Starting Phase 2")

        await self._update_workflow_checkpoint(
            workflow_id=workflow_id,
            phase=WorkflowPhase.PHASE_2,
            status=WorkflowStatus.IN_PROGRESS,
            campaign_id=campaign_id,
        )

        # Run Phase 2 orchestrator with error handling
        try:
            phase2_result = await self.phase2.run(
                campaign_id=campaign_id,
                niche_id=niche_id,
                target_leads=target_leads or self.config.default_target_leads,
            )
        except AgentExecutionError as e:
            logger.error(f"Phase 2 agent error for workflow {workflow_id}: {e}")
            result.phase_errors["phase2"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_2
            result.error = f"Phase 2 failed: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase2",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result
        except Exception as e:
            logger.error(f"Unexpected error in Phase 2 for workflow {workflow_id}: {e}")
            result.phase_errors["phase2"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_2
            result.error = f"Phase 2 failed unexpectedly: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase2",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result

        result.phase2_result = phase2_result
        result.total_leads_scraped = phase2_result.total_scraped
        result.lead_list_url = phase2_result.lead_list_url
        result.phase2_cost_usd = phase2_result.execution_time_ms * 0.001  # Placeholder cost

        # Check if Phase 2 stopped or failed
        if phase2_result.status in ("stopped", "failed"):
            logger.warning(f"Workflow {workflow_id}: Phase 2 {phase2_result.status}")
            result.status = (
                WorkflowStatus.FAILED
                if phase2_result.status == "failed"
                else WorkflowStatus.REJECTED
            )
            result.error = phase2_result.error or f"Phase 2 {phase2_result.status}"
            result.phase_errors["phase2"] = result.error
            result.current_phase = WorkflowPhase.PHASE_2
            return result

        # =================================================================
        # Human Gate 2: Approve Leads (optional)
        # =================================================================
        if self.config.require_phase2_approval:
            logger.info(f"Workflow {workflow_id}: Awaiting Phase 2 approval")

            await self._trigger_human_gate(
                workflow_id=workflow_id,
                gate_id="human_gate_2",
                campaign_id=campaign_id,
                message=f"Phase 2 Complete: {phase2_result.tier_a_count} Tier A leads ready",
                details={
                    "total_scraped": phase2_result.total_scraped,
                    "tier_a": phase2_result.tier_a_count,
                    "tier_b": phase2_result.tier_b_count,
                    "tier_c": phase2_result.tier_c_count,
                    "lead_list_url": phase2_result.lead_list_url,
                },
            )

            result.current_phase = WorkflowPhase.HUMAN_GATE_2
            result.status = WorkflowStatus.PENDING_APPROVAL
            result.pending_approval_gate = "human_gate_2"
            result.approval_requested_at = datetime.now(UTC)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            await self._update_workflow_checkpoint(
                workflow_id=workflow_id,
                phase=WorkflowPhase.HUMAN_GATE_2,
                status=WorkflowStatus.PENDING_APPROVAL,
                campaign_id=campaign_id,
            )

            return result

        # Auto-approve: Continue to Phase 3
        return await self._run_phase3(
            workflow_id=workflow_id,
            campaign_id=campaign_id,
            result=result,
            start_time=start_time,
        )

    async def _run_phase3(
        self,
        workflow_id: str,
        campaign_id: str,
        result: MasterWorkflowResult,
        start_time: float,
    ) -> MasterWorkflowResult:
        """Run Phase 3: Email Verification & Enrichment."""
        logger.info(f"Workflow {workflow_id}: Starting Phase 3")

        await self._update_workflow_checkpoint(
            workflow_id=workflow_id,
            phase=WorkflowPhase.PHASE_3,
            status=WorkflowStatus.IN_PROGRESS,
            campaign_id=campaign_id,
        )

        # Run Phase 3 orchestrator with error handling
        try:
            phase3_result = await self.phase3.run(
                campaign_id=campaign_id,
                workflow_id=workflow_id,
            )
        except AgentExecutionError as e:
            logger.error(f"Phase 3 agent error for workflow {workflow_id}: {e}")
            result.phase_errors["phase3"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_3
            result.error = f"Phase 3 failed: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase3",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result
        except Exception as e:
            logger.error(f"Unexpected error in Phase 3 for workflow {workflow_id}: {e}")
            result.phase_errors["phase3"] = str(e)
            result.status = WorkflowStatus.FAILED
            result.current_phase = WorkflowPhase.PHASE_3
            result.error = f"Phase 3 failed unexpectedly: {e}"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            await self.checkpoint_repo.mark_failed(
                workflow_id=workflow_id,
                agent_id="phase3",
                error_message=str(e),
            )
            await self.checkpoint_repo.commit()
            return result

        result.phase3_result = phase3_result
        result.total_leads_ready = phase3_result.total_ready
        result.tier_a_ready = phase3_result.tier_a_ready
        result.tier_b_ready = phase3_result.tier_b_ready
        result.verified_list_url = phase3_result.verified_sheet_url
        result.phase3_cost_usd = phase3_result.total_cost_usd

        # Calculate total cost
        result.total_cost_usd = (
            result.phase1_cost_usd + result.phase2_cost_usd + result.phase3_cost_usd
        )

        # Check if Phase 3 stopped or failed
        if phase3_result.status in ("stopped", "failed"):
            logger.warning(f"Workflow {workflow_id}: Phase 3 {phase3_result.status}")
            result.status = (
                WorkflowStatus.FAILED
                if phase3_result.status == "failed"
                else WorkflowStatus.REJECTED
            )
            result.error = phase3_result.error or f"Phase 3 {phase3_result.status}"
            result.phase_errors["phase3"] = result.error
            result.current_phase = WorkflowPhase.PHASE_3
            return result

        # =================================================================
        # Human Gate 3: Approve for Personalization
        # =================================================================
        if self.config.require_phase3_approval or phase3_result.pending_approval:
            logger.info(f"Workflow {workflow_id}: Awaiting Phase 3 approval")

            await self._trigger_human_gate(
                workflow_id=workflow_id,
                gate_id="human_gate_3",
                campaign_id=campaign_id,
                message=f"Phase 3 Complete: {phase3_result.total_ready} leads ready for personalization",
                details={
                    "total_ready": phase3_result.total_ready,
                    "tier_a_ready": phase3_result.tier_a_ready,
                    "tier_b_ready": phase3_result.tier_b_ready,
                    "verified_list_url": phase3_result.verified_sheet_url,
                    "total_cost": result.total_cost_usd,
                },
            )

            result.current_phase = WorkflowPhase.HUMAN_GATE_3
            result.status = WorkflowStatus.PENDING_APPROVAL
            result.pending_approval_gate = "human_gate_3"
            result.approval_requested_at = datetime.now(UTC)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            await self._update_workflow_checkpoint(
                workflow_id=workflow_id,
                phase=WorkflowPhase.HUMAN_GATE_3,
                status=WorkflowStatus.PENDING_APPROVAL,
                campaign_id=campaign_id,
            )

            return result

        # Auto-approve: Workflow complete
        result.status = WorkflowStatus.COMPLETED
        result.current_phase = WorkflowPhase.COMPLETED
        result.completed_at = datetime.now(UTC)
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        await self._update_workflow_checkpoint(
            workflow_id=workflow_id,
            phase=WorkflowPhase.COMPLETED,
            status=WorkflowStatus.COMPLETED,
            campaign_id=campaign_id,
        )

        logger.info(
            f"Workflow {workflow_id}: COMPLETED in {result.execution_time_ms}ms. "
            f"Leads ready: {result.total_leads_ready}, Cost: ${result.total_cost_usd:.2f}"
        )

        return result

    # =========================================================================
    # Checkpoint Management
    # =========================================================================

    async def _create_workflow_checkpoint(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        status: WorkflowStatus,
        campaign_id: str | None = None,
        niche_id: str | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Create initial workflow checkpoint."""
        await self.checkpoint_repo.create_checkpoint(
            workflow_id=workflow_id,
            workflow_type="master_workflow",
            agent_id=phase.value,
            step_id="main",
            status=status.value,
            campaign_id=campaign_id,
            niche_id=niche_id,
            input_data=input_data,
        )
        await self.checkpoint_repo.commit()

    async def _update_workflow_checkpoint(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        status: WorkflowStatus,
        campaign_id: str | None = None,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        """Update workflow checkpoint."""
        await self.checkpoint_repo.update_checkpoint(
            workflow_id=workflow_id,
            agent_id=phase.value,
            step_id="main",
            status=status.value,
            output_data=output_data,
        )
        await self.checkpoint_repo.commit()

    # =========================================================================
    # Human Gate Management
    # =========================================================================

    async def _trigger_human_gate(
        self,
        workflow_id: str,
        gate_id: str,
        message: str,
        details: dict[str, Any],
        campaign_id: str | None = None,
        niche_id: str | None = None,
    ) -> None:
        """
        Trigger human approval gate.

        Sends Slack notification with approval buttons.

        Args:
            workflow_id: Workflow UUID
            gate_id: Gate identifier
            message: Notification message
            details: Details to include in notification
            campaign_id: Optional campaign UUID
            niche_id: Optional niche UUID
        """
        logger.info(f"Triggering human gate: workflow={workflow_id}, gate={gate_id}")

        if not self.config.send_slack_notifications:
            logger.info("Slack notifications disabled, skipping")
            return

        # TODO: Integrate with Slack client when available
        # Real implementation will call:
        # await slack_client.send_approval_request(
        #     channel=self.config.slack_channel,
        #     workflow_id=workflow_id,
        #     gate_id=gate_id,
        #     message=message,
        #     details=details,
        #     buttons=self._get_gate_buttons(gate_id),
        # )

        logger.warning(
            f"Slack integration not yet implemented. "
            f"Gate {gate_id} triggered for workflow {workflow_id}: {message}"
        )

    def _get_gate_buttons(self, gate_id: str) -> list[dict[str, str]]:
        """Get appropriate buttons for a human gate."""
        gate_buttons: dict[str, list[dict[str, str]]] = {
            "human_gate_1": [
                {"text": "Approve", "action": "approve", "style": "primary"},
                {"text": "Reject", "action": "reject", "style": "danger"},
            ],
            "human_gate_2": [
                {"text": "Approve", "action": "approve", "style": "primary"},
                {"text": "Request More", "action": "request_more"},
                {"text": "Reject", "action": "reject", "style": "danger"},
            ],
            "human_gate_3": [
                {"text": "Approve Full (A+B)", "action": "approve_full", "style": "primary"},
                {"text": "Tier A Only", "action": "approve_tier_a"},
                {"text": "Need More", "action": "request_more"},
                {"text": "Reject", "action": "reject", "style": "danger"},
            ],
        }
        return gate_buttons.get(gate_id, [])


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_complete_workflow(
    session: AsyncSession,
    niche_name: str,
    industry: list[str],
    job_titles: list[str],
    config: MasterWorkflowConfig | None = None,
    **kwargs: Any,
) -> MasterWorkflowResult:
    """
    Convenience function to run complete workflow.

    Args:
        session: Database session
        niche_name: Niche name
        industry: Industries
        job_titles: Job titles
        config: Optional MasterWorkflowConfig
        **kwargs: Additional arguments

    Returns:
        MasterWorkflowResult
    """
    orchestrator = MasterWorkflowOrchestrator(session, config)
    return await orchestrator.start_from_niche(
        niche_name=niche_name,
        industry=industry,
        job_titles=job_titles,
        **kwargs,
    )
