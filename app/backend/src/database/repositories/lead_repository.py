"""
Lead Repository - Data access layer for Phase 2 leads.

Provides CRUD and bulk operations for leads.
Used by Phase 2 agents for lead acquisition.
"""

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import LeadModel, SuppressionListModel

logger = logging.getLogger(__name__)


class LeadRepository:
    """
    Repository for lead-related database operations.

    Provides methods to create, read, update, and bulk operate on leads.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Lead CRUD
    # =========================================================================

    async def create_lead(
        self,
        campaign_id: str | UUID,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        linkedin_url: str | None = None,
        title: str | None = None,
        company_name: str | None = None,
        **additional_fields: Any,
    ) -> LeadModel:
        """
        Create a new lead.

        Args:
            campaign_id: Campaign UUID
            first_name: First name
            last_name: Last name
            email: Email address
            linkedin_url: LinkedIn profile URL
            title: Job title
            company_name: Company name
            **additional_fields: Additional lead fields

        Returns:
            Created LeadModel instance
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        lead = LeadModel(
            campaign_id=campaign_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            linkedin_url=linkedin_url,
            title=title,
            company_name=company_name,
            status="new",
            **additional_fields,
        )
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)

        return lead

    async def bulk_create_leads(
        self,
        campaign_id: str | UUID,
        leads_data: list[dict[str, Any]],
    ) -> int:
        """
        Bulk create leads for a campaign.

        Args:
            campaign_id: Campaign UUID
            leads_data: List of lead dictionaries

        Returns:
            Number of leads created
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        leads = []
        for data in leads_data:
            lead = LeadModel(
                campaign_id=campaign_id,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                email=data.get("email"),
                linkedin_url=data.get("linkedin_url"),
                title=data.get("title") or data.get("job_title"),
                company_name=data.get("company_name"),
                company_domain=data.get("company_domain"),
                company_size=data.get("company_size"),
                company_industry=data.get("company_industry") or data.get("industry"),
                location=data.get("location"),
                city=data.get("city"),
                state=data.get("state"),
                country=data.get("country"),
                seniority=data.get("seniority"),
                department=data.get("department"),
                source=data.get("source"),
                source_url=data.get("source_url"),
                status="new",
            )
            leads.append(lead)

        self.session.add_all(leads)
        await self.session.flush()

        logger.info(f"Bulk created {len(leads)} leads for campaign: {campaign_id}")
        return len(leads)

    async def get_lead(self, lead_id: str | UUID) -> LeadModel | None:
        """
        Get lead by ID.

        Args:
            lead_id: Lead UUID

        Returns:
            LeadModel or None if not found
        """
        if isinstance(lead_id, str):
            lead_id = UUID(lead_id)

        result = await self.session.execute(select(LeadModel).where(LeadModel.id == lead_id))
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_campaign_leads(
        self,
        campaign_id: str | UUID,
        status: str | list[str] | None = None,
        exclude_status: str | list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LeadModel]:
        """
        Get leads for a campaign with optional filters.

        Args:
            campaign_id: Campaign UUID
            status: Filter by status(es)
            exclude_status: Exclude leads with these status(es)
            limit: Max results to return
            offset: Offset for pagination

        Returns:
            List of LeadModel instances
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        query = select(LeadModel).where(LeadModel.campaign_id == campaign_id)

        if status:
            if isinstance(status, str):
                query = query.where(LeadModel.status == status)
            else:
                query = query.where(LeadModel.status.in_(status))

        if exclude_status:
            if isinstance(exclude_status, str):
                query = query.where(LeadModel.status != exclude_status)
            else:
                query = query.where(~LeadModel.status.in_(exclude_status))

        query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_campaign_leads(
        self,
        campaign_id: str | UUID,
        status: str | list[str] | None = None,
        exclude_status: str | list[str] | None = None,
    ) -> int:
        """
        Count leads for a campaign with optional filters.

        Args:
            campaign_id: Campaign UUID
            status: Filter by status(es)
            exclude_status: Exclude leads with these status(es)

        Returns:
            Count of matching leads
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        query = select(func.count(LeadModel.id)).where(LeadModel.campaign_id == campaign_id)

        if status:
            if isinstance(status, str):
                query = query.where(LeadModel.status == status)
            else:
                query = query.where(LeadModel.status.in_(status))

        if exclude_status:
            if isinstance(exclude_status, str):
                query = query.where(LeadModel.status != exclude_status)
            else:
                query = query.where(~LeadModel.status.in_(exclude_status))

        result = await self.session.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # Phase 2: Validation (Agent 2.2)
    # =========================================================================

    async def update_lead_validation(
        self,
        lead_id: str | UUID,
        is_valid: bool,
        validation_errors: list[str] | None = None,
    ) -> LeadModel | None:
        """
        Update lead validation status.

        Args:
            lead_id: Lead UUID
            is_valid: Whether lead is valid
            validation_errors: List of validation errors

        Returns:
            Updated lead
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        lead.validation_status = "valid" if is_valid else "invalid"
        lead.validation_errors = validation_errors or []
        lead.status = "validated" if is_valid else "invalid"

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def bulk_update_validation(
        self,
        lead_ids: list[str | UUID],
        is_valid: bool,
        validation_errors: list[str] | None = None,
    ) -> int:
        """
        Bulk update lead validation status.

        Args:
            lead_ids: List of lead UUIDs
            is_valid: Whether leads are valid
            validation_errors: List of validation errors

        Returns:
            Number of leads updated
        """
        uuids = [UUID(lid) if isinstance(lid, str) else lid for lid in lead_ids]

        stmt = (
            update(LeadModel)
            .where(LeadModel.id.in_(uuids))
            .values(
                validation_status="valid" if is_valid else "invalid",
                validation_errors=validation_errors or [],
                status="validated" if is_valid else "invalid",
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount

    # =========================================================================
    # Phase 2: Deduplication (Agent 2.3)
    # =========================================================================

    async def mark_as_duplicate(
        self,
        lead_id: str | UUID,
        duplicate_of: str | UUID,
    ) -> LeadModel | None:
        """
        Mark lead as duplicate of another lead.

        Args:
            lead_id: Lead UUID to mark as duplicate
            duplicate_of: Primary lead UUID

        Returns:
            Updated lead
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        if isinstance(duplicate_of, str):
            duplicate_of = UUID(duplicate_of)

        lead.duplicate_of = duplicate_of
        lead.status = "duplicate"

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def bulk_mark_duplicates(
        self,
        duplicate_pairs: list[tuple[str | UUID, str | UUID]],
    ) -> int:
        """
        Bulk mark leads as duplicates.

        Args:
            duplicate_pairs: List of (duplicate_id, primary_id) tuples

        Returns:
            Number of leads marked as duplicates
        """
        count = 0
        for dup_id, primary_id in duplicate_pairs:
            if isinstance(dup_id, str):
                dup_id = UUID(dup_id)
            if isinstance(primary_id, str):
                primary_id = UUID(primary_id)

            stmt = (
                update(LeadModel)
                .where(LeadModel.id == dup_id)
                .values(
                    duplicate_of=primary_id,
                    status="duplicate",
                )
            )
            result = await self.session.execute(stmt)
            count += result.rowcount

        await self.session.flush()
        return count

    async def merge_lead_data(
        self,
        primary_id: str | UUID,
        merged_lead_ids: list[str | UUID],
    ) -> LeadModel | None:
        """
        Merge data from duplicate leads into primary.

        Args:
            primary_id: Primary lead UUID
            merged_lead_ids: UUIDs of leads merged into primary

        Returns:
            Updated primary lead
        """
        lead = await self.get_lead(primary_id)
        if not lead:
            return None

        merged_ids = [str(lid) for lid in merged_lead_ids]
        lead.merged_from = merged_ids

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    # =========================================================================
    # Phase 2: Cross-Campaign Dedup (Agent 2.4)
    # =========================================================================

    async def mark_cross_campaign_duplicate(
        self,
        lead_id: str | UUID,
        exclusion_reason: str,
        excluded_due_to_campaign: str | UUID | None = None,
    ) -> LeadModel | None:
        """
        Mark lead as cross-campaign duplicate.

        Args:
            lead_id: Lead UUID
            exclusion_reason: Reason for exclusion
            excluded_due_to_campaign: Campaign that caused exclusion

        Returns:
            Updated lead
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        lead.exclusion_reason = exclusion_reason
        lead.status = "cross_campaign_duplicate"

        if excluded_due_to_campaign:
            if isinstance(excluded_due_to_campaign, str):
                excluded_due_to_campaign = UUID(excluded_due_to_campaign)
            lead.excluded_due_to_campaign = excluded_due_to_campaign

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def bulk_mark_cross_duplicates(
        self,
        exclusions: list[dict[str, Any]],
    ) -> int:
        """
        Bulk mark leads as cross-campaign duplicates.

        Args:
            exclusions: List of dicts with lead_id, exclusion_reason, excluded_due_to_campaign

        Returns:
            Number of leads excluded
        """
        count = 0
        for exc in exclusions:
            lead_id = exc["lead_id"]
            if isinstance(lead_id, str):
                lead_id = UUID(lead_id)

            values = {
                "exclusion_reason": exc.get("exclusion_reason", "cross_campaign_duplicate"),
                "status": "cross_campaign_duplicate",
            }

            if exc.get("excluded_due_to_campaign"):
                campaign_id = exc["excluded_due_to_campaign"]
                if isinstance(campaign_id, str):
                    campaign_id = UUID(campaign_id)
                values["excluded_due_to_campaign"] = campaign_id

            stmt = update(LeadModel).where(LeadModel.id == lead_id).values(**values)
            result = await self.session.execute(stmt)
            count += result.rowcount

        await self.session.flush()
        return count

    async def get_suppression_list(self) -> list[str]:
        """
        Get all suppressed emails.

        Returns:
            List of suppressed email addresses
        """
        result = await self.session.execute(select(SuppressionListModel.email))
        return [row[0] for row in result.all()]

    async def check_historical_contacts(
        self,
        campaign_id: str | UUID,
        lookback_days: int = 90,
    ) -> list[dict[str, Any]]:
        """
        Find leads that were contacted in other campaigns recently.

        Args:
            campaign_id: Current campaign UUID (to exclude)
            lookback_days: Days to look back

        Returns:
            List of leads with contact history
        """
        from datetime import datetime, timedelta

        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        cutoff_date = datetime.now(UTC) - timedelta(days=lookback_days)

        # Get leads from other campaigns that were contacted recently
        result = await self.session.execute(
            select(LeadModel).where(
                and_(
                    LeadModel.campaign_id != campaign_id,
                    or_(
                        LeadModel.last_contacted_at > cutoff_date,
                        LeadModel.email_status.in_(["bounced", "unsubscribed", "complained"]),
                    ),
                )
            )
        )
        leads = result.scalars().all()

        return [
            {
                "linkedin_url": lead.linkedin_url,
                "email": lead.email,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "company_name": lead.company_name,
                "campaign_id": str(lead.campaign_id),
                "email_status": lead.email_status,
                "last_contacted_at": lead.last_contacted_at,
            }
            for lead in leads
        ]

    # =========================================================================
    # Phase 2: Scoring (Agent 2.5)
    # =========================================================================

    async def update_lead_score(
        self,
        lead_id: str | UUID,
        score: int,
        tier: str,
        breakdown: dict[str, Any],
        persona_tags: list[str] | None = None,
    ) -> LeadModel | None:
        """
        Update lead scoring.

        Args:
            lead_id: Lead UUID
            score: Total score (0-100)
            tier: Lead tier (A, B, C, D)
            breakdown: Score breakdown by component
            persona_tags: Matched persona tags

        Returns:
            Updated lead
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        lead.lead_score = score
        lead.lead_tier = tier
        lead.score_breakdown = breakdown
        lead.persona_tags = persona_tags or []
        lead.status = "scored"

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def bulk_update_scores(
        self,
        scores: list[dict[str, Any]],
    ) -> int:
        """
        Bulk update lead scores.

        Args:
            scores: List of dicts with lead_id, score, tier, breakdown, persona_tags

        Returns:
            Number of leads updated
        """
        count = 0
        for s in scores:
            lead_id = s["lead_id"]
            if isinstance(lead_id, str):
                lead_id = UUID(lead_id)

            stmt = (
                update(LeadModel)
                .where(LeadModel.id == lead_id)
                .values(
                    lead_score=s["score"],
                    lead_tier=s["tier"],
                    score_breakdown=s.get("breakdown", {}),
                    persona_tags=s.get("persona_tags", []),
                    status="scored",
                )
            )
            result = await self.session.execute(stmt)
            count += result.rowcount

        await self.session.flush()
        return count

    async def get_tier_counts(
        self,
        campaign_id: str | UUID,
    ) -> dict[str, int]:
        """
        Get count of leads by tier for a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Dictionary with tier counts
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        result = await self.session.execute(
            select(LeadModel.lead_tier, func.count(LeadModel.id))
            .where(LeadModel.campaign_id == campaign_id)
            .group_by(LeadModel.lead_tier)
        )

        counts = {"A": 0, "B": 0, "C": 0, "D": 0, None: 0}
        for tier, count in result.all():
            counts[tier] = count

        return counts

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
