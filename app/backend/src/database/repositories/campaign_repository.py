"""
Campaign Repository - Data access layer for Phase 2 campaigns.

Provides CRUD operations for campaigns, dedup_logs, and cross_campaign_dedup_logs.
Used by Phase 2 agents for lead acquisition.
"""

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    CampaignAuditLogModel,
    CampaignModel,
    CrossCampaignDedupLogModel,
    DedupLogModel,
    NicheModel,
)

logger = logging.getLogger(__name__)


class CampaignRepository:
    """
    Repository for campaign-related database operations.

    Provides methods to create, read, update campaigns and their
    associated dedup logs.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Campaign CRUD
    # =========================================================================

    async def create_campaign(
        self,
        name: str,
        niche_id: str | UUID,
        target_leads: int = 50000,
        description: str | None = None,
    ) -> CampaignModel:
        """
        Create a new campaign.

        Args:
            name: Campaign name
            niche_id: Parent niche UUID
            target_leads: Target number of leads
            description: Optional description

        Returns:
            Created CampaignModel instance
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        campaign = CampaignModel(
            name=name,
            niche_id=niche_id,
            target_leads=target_leads,
            description=description,
            status="building",
        )
        self.session.add(campaign)
        await self.session.flush()
        await self.session.refresh(campaign)

        logger.info(f"Created campaign: {campaign.id} - {name}")
        return campaign

    async def get_campaign(self, campaign_id: str | UUID) -> CampaignModel | None:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign UUID

        Returns:
            CampaignModel or None if not found
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        result = await self.session.execute(
            select(CampaignModel).where(CampaignModel.id == campaign_id)
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_campaign_with_niche(self, campaign_id: str | UUID) -> dict[str, Any] | None:
        """
        Get campaign with associated niche data.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Dictionary with campaign and niche data
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return None

        niche = None
        if campaign.niche_id:
            result = await self.session.execute(
                select(NicheModel).where(NicheModel.id == campaign.niche_id)
            )
            niche = result.scalar_one_or_none()

        return {
            "campaign": campaign.to_dict(),
            "niche": niche.to_dict() if niche else None,
        }

    async def update_campaign(
        self,
        campaign_id: str | UUID,
        **updates: Any,
    ) -> CampaignModel | None:
        """
        Update campaign fields.

        Args:
            campaign_id: Campaign UUID
            **updates: Fields to update

        Returns:
            Updated CampaignModel or None if not found
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return None

        for key, value in updates.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        await self.session.flush()
        await self.session.refresh(campaign)

        logger.info(f"Updated campaign: {campaign_id}")
        return campaign

    async def update_campaign_status(
        self,
        campaign_id: str | UUID,
        status: str,
        **additional_updates: Any,
    ) -> CampaignModel | None:
        """
        Update campaign status with optional additional fields.

        Args:
            campaign_id: Campaign UUID
            status: New status value
            **additional_updates: Additional fields to update

        Returns:
            Updated CampaignModel or None
        """
        return await self.update_campaign(
            campaign_id,
            status=status,
            **additional_updates,
        )

    # =========================================================================
    # Phase 2 Agent Updates
    # =========================================================================

    async def update_scraping_results(
        self,
        campaign_id: str | UUID,
        total_scraped: int,
        scraping_cost: float,
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.1 (Lead List Builder).

        Args:
            campaign_id: Campaign UUID
            total_scraped: Number of leads scraped
            scraping_cost: Total cost of scraping

        Returns:
            Updated campaign
        """
        return await self.update_campaign(
            campaign_id,
            total_leads_scraped=total_scraped,
            scraping_cost=scraping_cost,
            status="leads_scraped",
        )

    async def update_validation_results(
        self,
        campaign_id: str | UUID,
        total_valid: int,
        total_invalid: int,
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.2 (Data Validation).

        Args:
            campaign_id: Campaign UUID
            total_valid: Number of valid leads
            total_invalid: Number of invalid leads

        Returns:
            Updated campaign
        """
        from datetime import datetime

        return await self.update_campaign(
            campaign_id,
            total_leads_valid=total_valid,
            total_leads_invalid=total_invalid,
            validation_completed_at=datetime.now(UTC),
            status="validated",
        )

    async def update_dedup_results(
        self,
        campaign_id: str | UUID,
        total_duplicates: int,
        unique_leads: int,
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.3 (Duplicate Detection).

        Args:
            campaign_id: Campaign UUID
            total_duplicates: Number of duplicates found
            unique_leads: Number of unique leads remaining

        Returns:
            Updated campaign
        """
        from datetime import datetime

        return await self.update_campaign(
            campaign_id,
            total_duplicates_found=total_duplicates,
            total_leads_unique=unique_leads,
            dedup_completed_at=datetime.now(UTC),
            status="deduplicated",
        )

    async def update_cross_dedup_results(
        self,
        campaign_id: str | UUID,
        total_cross_duplicates: int,
        remaining_leads: int,
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.4 (Cross-Campaign Dedup).

        Args:
            campaign_id: Campaign UUID
            total_cross_duplicates: Number of cross-campaign duplicates
            remaining_leads: Number of leads available

        Returns:
            Updated campaign
        """
        from datetime import datetime

        return await self.update_campaign(
            campaign_id,
            total_cross_duplicates=total_cross_duplicates,
            total_leads_available=remaining_leads,
            cross_dedup_completed_at=datetime.now(UTC),
            status="cross_deduplicated",
        )

    async def update_scoring_results(
        self,
        campaign_id: str | UUID,
        leads_scored: int,
        avg_score: float,
        tier_a: int,
        tier_b: int,
        tier_c: int,
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.5 (Lead Scoring).

        Args:
            campaign_id: Campaign UUID
            leads_scored: Total leads scored
            avg_score: Average lead score
            tier_a: Count of Tier A leads
            tier_b: Count of Tier B leads
            tier_c: Count of Tier C leads

        Returns:
            Updated campaign
        """
        from datetime import datetime

        return await self.update_campaign(
            campaign_id,
            leads_scored=leads_scored,
            avg_lead_score=avg_score,
            leads_tier_a=tier_a,
            leads_tier_b=tier_b,
            leads_tier_c=tier_c,
            scoring_completed_at=datetime.now(UTC),
            status="scored",
        )

    async def update_import_results(
        self,
        campaign_id: str | UUID,
        lead_list_url: str,
        import_summary: dict[str, Any],
    ) -> CampaignModel | None:
        """
        Update campaign after Agent 2.6 (Import Finalizer).

        Args:
            campaign_id: Campaign UUID
            lead_list_url: Google Sheets URL
            import_summary: Summary of import

        Returns:
            Updated campaign
        """
        from datetime import datetime

        return await self.update_campaign(
            campaign_id,
            lead_list_url=lead_list_url,
            import_summary=import_summary,
            import_completed_at=datetime.now(UTC),
            status="import_complete",
        )

    # =========================================================================
    # Phase 3 Agent Updates
    # =========================================================================

    async def update_email_verification_results(
        self,
        campaign_id: str | UUID,
        emails_found: int,
        emails_verified: int,
        verification_cost: float,
    ) -> CampaignModel | None:
        """
        Update campaign after Phase 3 Email Verification (Agent 3.1).

        Args:
            campaign_id: Campaign UUID
            emails_found: Number of emails found via waterfall
            emails_verified: Number of emails verified
            verification_cost: Total cost of verification

        Returns:
            Updated campaign
        """
        # Note: CampaignModel needs email verification fields added
        # For now, store in import_summary as extension
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return None

        import_summary = campaign.import_summary or {}
        import_summary["phase3_email_verification"] = {
            "emails_found": emails_found,
            "emails_verified": emails_verified,
            "verification_cost": verification_cost,
        }

        return await self.update_campaign(
            campaign_id,
            import_summary=import_summary,
        )

    async def update_enrichment_results(
        self,
        campaign_id: str | UUID,
        total_enriched: int,
        enrichment_cost: float,
    ) -> CampaignModel | None:
        """
        Update campaign after Phase 3 Waterfall Enrichment (Agent 3.2).

        Args:
            campaign_id: Campaign UUID
            total_enriched: Number of leads enriched
            enrichment_cost: Total cost of enrichment

        Returns:
            Updated campaign
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return None

        import_summary = campaign.import_summary or {}
        import_summary["phase3_enrichment"] = {
            "total_enriched": total_enriched,
            "enrichment_cost": enrichment_cost,
        }

        return await self.update_campaign(
            campaign_id,
            import_summary=import_summary,
        )

    async def update_verification_results(
        self,
        campaign_id: str | UUID,
        tier_a_ready: int,
        tier_b_ready: int,
        tier_c_ready: int,
        total_ready: int,
        quality_report: dict[str, Any] | None = None,
    ) -> CampaignModel | None:
        """
        Update campaign after Phase 3 Verification Finalizer (Agent 3.3).

        Args:
            campaign_id: Campaign UUID
            tier_a_ready: Tier A leads ready
            tier_b_ready: Tier B leads ready
            tier_c_ready: Tier C leads ready
            total_ready: Total leads ready for Phase 4
            quality_report: Optional quality report summary

        Returns:
            Updated campaign
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return None

        import_summary = campaign.import_summary or {}
        import_summary["phase3_verification"] = {
            "tier_a_ready": tier_a_ready,
            "tier_b_ready": tier_b_ready,
            "tier_c_ready": tier_c_ready,
            "total_ready": total_ready,
            "quality_report": quality_report or {},
        }

        return await self.update_campaign(
            campaign_id,
            import_summary=import_summary,
            status="verified" if total_ready > 0 else campaign.status,
        )

    # =========================================================================
    # Dedup Logs
    # =========================================================================

    async def create_dedup_log(
        self,
        campaign_id: str | UUID,
        total_checked: int,
        exact_duplicates: int,
        fuzzy_duplicates: int,
        total_merged: int,
        details: dict[str, Any] | None = None,
    ) -> DedupLogModel:
        """
        Create dedup log entry (Agent 2.3).

        Args:
            campaign_id: Campaign UUID
            total_checked: Total leads checked
            exact_duplicates: Exact duplicates found
            fuzzy_duplicates: Fuzzy duplicates found
            total_merged: Total merged
            details: Detection details

        Returns:
            Created DedupLogModel
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        log = DedupLogModel(
            campaign_id=campaign_id,
            total_checked=total_checked,
            exact_duplicates=exact_duplicates,
            fuzzy_duplicates=fuzzy_duplicates,
            total_merged=total_merged,
            detection_details=details or {},
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)

        logger.info(f"Created dedup log for campaign: {campaign_id}")
        return log

    async def create_cross_campaign_dedup_log(
        self,
        campaign_id: str | UUID,
        total_checked: int,
        previously_contacted: int,
        bounced_excluded: int,
        unsubscribed_excluded: int,
        suppression_list_excluded: int,
        remaining_leads: int,
        lookback_days: int = 90,
        details: dict[str, Any] | None = None,
    ) -> CrossCampaignDedupLogModel:
        """
        Create cross-campaign dedup log entry (Agent 2.4).

        Args:
            campaign_id: Campaign UUID
            total_checked: Total leads checked
            previously_contacted: Excluded due to recent contact
            bounced_excluded: Excluded due to bounce
            unsubscribed_excluded: Excluded due to unsubscribe
            suppression_list_excluded: Excluded from suppression list
            remaining_leads: Remaining leads after exclusions
            lookback_days: Days to look back
            details: Detection details

        Returns:
            Created CrossCampaignDedupLogModel
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        log = CrossCampaignDedupLogModel(
            campaign_id=campaign_id,
            total_checked=total_checked,
            previously_contacted=previously_contacted,
            bounced_excluded=bounced_excluded,
            unsubscribed_excluded=unsubscribed_excluded,
            suppression_list_excluded=suppression_list_excluded,
            remaining_leads=remaining_leads,
            lookback_days=lookback_days,
            detection_details=details or {},
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)

        logger.info(f"Created cross-campaign dedup log for campaign: {campaign_id}")
        return log

    # =========================================================================
    # Audit Logs
    # =========================================================================

    async def log_action(
        self,
        campaign_id: str | UUID,
        action: str,
        actor: str,
        actor_type: str = "agent",
        details: dict[str, Any] | None = None,
    ) -> CampaignAuditLogModel:
        """
        Log an action on a campaign.

        Args:
            campaign_id: Campaign UUID
            action: Action taken
            actor: Who/what took the action
            actor_type: 'agent', 'user', or 'system'
            details: Additional details

        Returns:
            Created audit log entry
        """
        if isinstance(campaign_id, str):
            campaign_id = UUID(campaign_id)

        log = CampaignAuditLogModel(
            campaign_id=campaign_id,
            action=action,
            actor=actor,
            actor_type=actor_type,
            details=details or {},
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)

        return log

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
