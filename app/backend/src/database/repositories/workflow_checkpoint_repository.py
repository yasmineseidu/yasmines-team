"""
Workflow Checkpoint Repository - Data access layer for workflow checkpoints.

Provides CRUD operations for workflow_checkpoints table.
Used by Phase 1, 2, and 3 orchestrators for checkpoint/resume capability.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import WorkflowCheckpointModel

logger = logging.getLogger(__name__)


class WorkflowCheckpointRepository:
    """
    Repository for workflow checkpoint database operations.

    Provides methods to create, read, update checkpoints for
    long-running agent workflows.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Checkpoint CRUD
    # =========================================================================

    async def create_checkpoint(
        self,
        workflow_id: str,
        workflow_type: str,
        agent_id: str,
        step_id: str,
        status: str = "in_progress",
        campaign_id: str | UUID | None = None,
        niche_id: str | UUID | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> WorkflowCheckpointModel:
        """
        Create a new workflow checkpoint.

        Args:
            workflow_id: Unique workflow identifier
            workflow_type: Type of workflow (e.g., 'phase1_orchestrator')
            agent_id: Current agent identifier
            step_id: Current step within agent
            status: Checkpoint status
            campaign_id: Optional campaign UUID
            niche_id: Optional niche UUID
            input_data: Optional input data to store

        Returns:
            Created WorkflowCheckpointModel instance
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        checkpoint = WorkflowCheckpointModel(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            agent_id=agent_id,
            step_id=step_id,
            status=status,
            campaign_id=campaign_id,
            niche_id=niche_id,
            input_data=input_data or {},
        )
        self.session.add(checkpoint)
        await self.session.flush()
        await self.session.refresh(checkpoint)

        logger.info(f"Created checkpoint: {workflow_id}/{agent_id}/{step_id}")
        return checkpoint

    async def get_checkpoint(
        self,
        workflow_id: str,
        agent_id: str,
        step_id: str,
    ) -> WorkflowCheckpointModel | None:
        """
        Get checkpoint by workflow_id, agent_id, and step_id.

        Args:
            workflow_id: Workflow identifier
            agent_id: Agent identifier
            step_id: Step identifier

        Returns:
            WorkflowCheckpointModel or None if not found
        """
        result = await self.session.execute(
            select(WorkflowCheckpointModel).where(
                and_(
                    WorkflowCheckpointModel.workflow_id == workflow_id,
                    WorkflowCheckpointModel.agent_id == agent_id,
                    WorkflowCheckpointModel.step_id == step_id,
                )
            )
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_latest_checkpoint(
        self,
        workflow_id: str,
    ) -> WorkflowCheckpointModel | None:
        """
        Get the most recent checkpoint for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Most recent WorkflowCheckpointModel or None
        """
        result = await self.session.execute(
            select(WorkflowCheckpointModel)
            .where(WorkflowCheckpointModel.workflow_id == workflow_id)
            .order_by(WorkflowCheckpointModel.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_workflow_checkpoints(
        self,
        workflow_id: str,
    ) -> list[WorkflowCheckpointModel]:
        """
        Get all checkpoints for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of WorkflowCheckpointModel instances
        """
        result = await self.session.execute(
            select(WorkflowCheckpointModel)
            .where(WorkflowCheckpointModel.workflow_id == workflow_id)
            .order_by(WorkflowCheckpointModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_campaign_checkpoints(
        self,
        campaign_id: str | UUID,
    ) -> list[WorkflowCheckpointModel]:
        """
        Get all checkpoints for a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            List of WorkflowCheckpointModel instances
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        result = await self.session.execute(
            select(WorkflowCheckpointModel)
            .where(WorkflowCheckpointModel.campaign_id == campaign_id)
            .order_by(WorkflowCheckpointModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_checkpoint(
        self,
        workflow_id: str,
        agent_id: str,
        status: str,
        step_id: str = "main",
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        items_processed: int | None = None,
        items_total: int | None = None,
    ) -> WorkflowCheckpointModel | None:
        """
        Update an existing checkpoint or create new one.

        Args:
            workflow_id: Workflow identifier
            agent_id: Agent identifier
            status: New status
            step_id: Step identifier (default 'main')
            output_data: Optional output data to store
            error_message: Optional error message
            items_processed: Optional items processed count
            items_total: Optional total items count

        Returns:
            Updated WorkflowCheckpointModel or None
        """
        # Try to get existing checkpoint
        checkpoint = await self.get_checkpoint(workflow_id, agent_id, step_id)

        if checkpoint:
            # Update existing
            update_data: dict[str, Any] = {
                "status": status,
                "updated_at": datetime.now(UTC),
            }

            if output_data is not None:
                update_data["output_data"] = output_data
            if error_message is not None:
                update_data["error_message"] = error_message
            if items_processed is not None:
                update_data["items_processed"] = items_processed
            if items_total is not None:
                update_data["items_total"] = items_total
            if status == "completed":
                update_data["completed_at"] = datetime.now(UTC)

            await self.session.execute(
                update(WorkflowCheckpointModel)
                .where(WorkflowCheckpointModel.id == checkpoint.id)
                .values(**update_data)
            )
            await self.session.refresh(checkpoint)

            logger.info(f"Updated checkpoint: {workflow_id}/{agent_id}/{step_id} -> {status}")
            return checkpoint
        else:
            # Create new checkpoint
            return await self.create_checkpoint(
                workflow_id=workflow_id,
                workflow_type="unknown",  # Will be set by orchestrator
                agent_id=agent_id,
                step_id=step_id,
                status=status,
                input_data=output_data,  # Store output as input for next step
            )

    async def mark_completed(
        self,
        workflow_id: str,
        agent_id: str,
        step_id: str = "main",
        output_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Mark a checkpoint as completed.

        Args:
            workflow_id: Workflow identifier
            agent_id: Agent identifier
            step_id: Step identifier
            output_data: Optional output data
        """
        await self.update_checkpoint(
            workflow_id=workflow_id,
            agent_id=agent_id,
            step_id=step_id,
            status="completed",
            output_data=output_data,
        )

    async def mark_failed(
        self,
        workflow_id: str,
        agent_id: str,
        error_message: str,
        step_id: str = "main",
    ) -> None:
        """
        Mark a checkpoint as failed.

        Args:
            workflow_id: Workflow identifier
            agent_id: Agent identifier
            error_message: Error description
            step_id: Step identifier
        """
        await self.update_checkpoint(
            workflow_id=workflow_id,
            agent_id=agent_id,
            step_id=step_id,
            status="failed",
            error_message=error_message,
        )

    # =========================================================================
    # Query Helpers
    # =========================================================================

    async def get_in_progress_workflows(
        self,
        workflow_type: str | None = None,
    ) -> list[WorkflowCheckpointModel]:
        """
        Get all in-progress workflow checkpoints.

        Args:
            workflow_type: Optional filter by workflow type

        Returns:
            List of in-progress checkpoints
        """
        query = select(WorkflowCheckpointModel).where(
            WorkflowCheckpointModel.status == "in_progress"
        )

        if workflow_type:
            query = query.where(WorkflowCheckpointModel.workflow_type == workflow_type)

        result = await self.session.execute(
            query.order_by(WorkflowCheckpointModel.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_failed_workflows(
        self,
        workflow_type: str | None = None,
    ) -> list[WorkflowCheckpointModel]:
        """
        Get all failed workflow checkpoints.

        Args:
            workflow_type: Optional filter by workflow type

        Returns:
            List of failed checkpoints
        """
        query = select(WorkflowCheckpointModel).where(WorkflowCheckpointModel.status == "failed")

        if workflow_type:
            query = query.where(WorkflowCheckpointModel.workflow_type == workflow_type)

        result = await self.session.execute(
            query.order_by(WorkflowCheckpointModel.updated_at.desc())
        )
        return list(result.scalars().all())

    async def can_resume(self, workflow_id: str) -> bool:
        """
        Check if a workflow can be resumed.

        A workflow can be resumed if it has an in_progress or failed checkpoint.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if resumable, False otherwise
        """
        latest = await self.get_latest_checkpoint(workflow_id)
        if not latest:
            return False
        return latest.status in ("in_progress", "failed")

    async def get_resume_point(
        self,
        workflow_id: str,
    ) -> tuple[str, str] | None:
        """
        Get the agent_id and step_id to resume from.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Tuple of (agent_id, step_id) or None if not resumable
        """
        latest = await self.get_latest_checkpoint(workflow_id)
        if not latest or latest.status == "completed":
            return None
        return (latest.agent_id, latest.step_id)

    # =========================================================================
    # Transaction Helpers
    # =========================================================================

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
