"""
Instantly.ai API integration client.

Provides cold email automation and campaign management capabilities
for outreach at scale. Supports campaign creation, lead management,
email sending, and comprehensive analytics.

API Documentation: https://developer.instantly.ai/api/v2
API Version: V2
Base URL: https://api.instantly.ai/api/v2

Features:
- Campaign creation, management, and analytics
- Lead management with bulk operations
- Email template management
- A/B testing support
- Domain warmup management
- Bounce and unsubscribe handling
- Real-time campaign metrics (opens, clicks, replies)

Rate Limits:
- Soft throttle at ~100 req/min
- No hard limit, system auto-scales

Authentication:
- Bearer token via API key from Instantly dashboard
- API V2 requires Growth plan or above

Example:
    >>> from src.integrations.instantly import InstantlyClient
    >>> client = InstantlyClient(api_key="your-api-key")
    >>> campaign = await client.create_campaign(
    ...     name="Q1 Outreach",
    ...     campaign_schedule={"schedules": [...]}
    ... )
    >>> print(campaign.id)
"""

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class CampaignStatus(int, Enum):
    """Campaign status codes from Instantly API."""

    DRAFT = 0
    ACTIVE = 1
    PAUSED = 2
    COMPLETED = 3
    RUNNING_SUBSEQUENCES = 4
    ACCOUNT_SUSPENDED = -99
    ACCOUNTS_UNHEALTHY = -1
    BOUNCE_PROTECT = -2


class LeadInterestStatus(str, Enum):
    """Lead interest status values."""

    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    MEETING_BOOKED = "meeting_booked"
    MEETING_COMPLETED = "meeting_completed"
    CLOSED = "closed"
    OUT_OF_OFFICE = "out_of_office"
    WRONG_PERSON = "wrong_person"


@dataclass
class Campaign:
    """Campaign entity from Instantly API."""

    id: str
    name: str
    status: CampaignStatus
    workspace_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if campaign is actively sending."""
        return self.status == CampaignStatus.ACTIVE

    @property
    def is_paused(self) -> bool:
        """Check if campaign is paused."""
        return self.status == CampaignStatus.PAUSED

    @property
    def is_healthy(self) -> bool:
        """Check if campaign status is healthy (not suspended/unhealthy)."""
        return self.status.value >= 0


@dataclass
class Lead:
    """Lead entity from Instantly API."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    website: str | None = None
    phone: str | None = None
    interest_status: LeadInterestStatus | None = None
    campaign_id: str | None = None
    list_id: str | None = None
    custom_variables: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str | None:
        """Get full name if first and last name are available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name


@dataclass
class CampaignAnalytics:
    """Campaign analytics data from Instantly API."""

    campaign_id: str
    total_leads: int = 0
    contacted: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    emails_replied: int = 0
    emails_bounced: int = 0
    unsubscribed: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def open_rate(self) -> float:
        """Calculate email open rate as percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_opened / self.emails_sent) * 100

    @property
    def click_rate(self) -> float:
        """Calculate email click rate as percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_clicked / self.emails_sent) * 100

    @property
    def reply_rate(self) -> float:
        """Calculate email reply rate as percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_replied / self.emails_sent) * 100

    @property
    def bounce_rate(self) -> float:
        """Calculate email bounce rate as percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_bounced / self.emails_sent) * 100


@dataclass
class BulkAddResult:
    """Result from bulk lead add operation."""

    created_count: int
    updated_count: int
    failed_count: int
    created_leads: list[str]
    failed_leads: list[dict[str, Any]]
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate of bulk add operation."""
        total = self.created_count + self.updated_count + self.failed_count
        if total == 0:
            return 0.0
        return ((self.created_count + self.updated_count) / total) * 100


@dataclass
class BackgroundJob:
    """Background job status from Instantly API."""

    job_id: str
    status: str
    progress: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status.lower() == "completed"

    @property
    def is_running(self) -> bool:
        """Check if job is still running."""
        return self.status.lower() in ("running", "processing", "pending")


class InstantlyError(IntegrationError):
    """Exception raised for Instantly API errors."""

    pass


class InstantlyClient(BaseIntegrationClient):
    """
    Async client for Instantly.ai API V2.

    Provides comprehensive cold email campaign management including
    campaign CRUD, lead management, email sending, and analytics.

    Attributes:
        API_VERSION: Current API version (V2).
        BASE_URL: Base URL for API requests.

    Note:
        - Soft rate limit: ~100 req/min
        - Requires Growth plan or above for API V2
        - Bearer token authentication
    """

    API_VERSION = "V2"
    BASE_URL = "https://api.instantly.ai/api/v2"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Instantly client.

        Args:
            api_key: Instantly API key from dashboard.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="instantly",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client (API {self.API_VERSION})")

    # -------------------------------------------------------------------------
    # Campaign Management
    # -------------------------------------------------------------------------

    async def create_campaign(
        self,
        name: str,
        campaign_schedule: dict[str, Any],
        **kwargs: Any,
    ) -> Campaign:
        """
        Create a new email campaign.

        Args:
            name: Campaign name.
            campaign_schedule: Schedule configuration with timing, days, timezone.
            **kwargs: Additional campaign parameters.

        Returns:
            Campaign object with created campaign details.

        Raises:
            InstantlyError: If campaign creation fails.

        Example:
            >>> campaign = await client.create_campaign(
            ...     name="Q1 Outreach",
            ...     campaign_schedule={
            ...         "schedules": [{
            ...             "timing": {"from": "09:00", "to": "17:00"},
            ...             "days": {"monday": True, "tuesday": True, ...},
            ...             "timezone": "America/New_York"
            ...         }]
            ...     }
            ... )
        """
        payload = {
            "name": name,
            "campaign_schedule": campaign_schedule,
            **kwargs,
        }

        try:
            response = await self.post("/campaigns", json=payload)
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] create_campaign failed: {e}",
                extra={"campaign_name": name},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def list_campaigns(
        self,
        limit: int = 100,
        starting_after: str | None = None,
        search: str | None = None,
        status: CampaignStatus | None = None,
        tag_ids: list[str] | None = None,
    ) -> list[Campaign]:
        """
        List campaigns with filtering and pagination.

        Args:
            limit: Maximum campaigns to return (1-100).
            starting_after: Pagination cursor for next page.
            search: Search by campaign name.
            status: Filter by campaign status.
            tag_ids: Filter by tag IDs.

        Returns:
            List of Campaign objects.

        Raises:
            InstantlyError: If listing fails.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}

        if starting_after:
            params["starting_after"] = starting_after
        if search:
            params["search"] = search
        if status is not None:
            params["status"] = status.value
        if tag_ids:
            params["tag_ids"] = ",".join(tag_ids)

        try:
            response = await self.get("/campaigns", params=params)
            campaigns_data = response.get("items", response.get("data", []))

            return [self._parse_campaign(c) for c in campaigns_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] list_campaigns failed: {e}")
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_campaign(self, campaign_id: str) -> Campaign:
        """
        Get a single campaign by ID.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Campaign object with full details.

        Raises:
            InstantlyError: If campaign not found or request fails.
        """
        try:
            response = await self.get(f"/campaigns/{campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def update_campaign(
        self,
        campaign_id: str,
        **kwargs: Any,
    ) -> Campaign:
        """
        Update a campaign.

        Args:
            campaign_id: Campaign UUID.
            **kwargs: Fields to update (name, campaign_schedule, etc.).

        Returns:
            Updated Campaign object.

        Raises:
            InstantlyError: If update fails.
        """
        try:
            response = await self.patch(f"/campaigns/{campaign_id}", json=kwargs)
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] update_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def delete_campaign(self, campaign_id: str) -> bool:
        """
        Delete a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            True if deletion was successful.

        Raises:
            InstantlyError: If deletion fails.
        """
        try:
            await self.delete(f"/campaigns/{campaign_id}")
            logger.info(f"[{self.name}] Deleted campaign {campaign_id}")
            return True

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] delete_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def activate_campaign(self, campaign_id: str) -> Campaign:
        """
        Activate (start or resume) a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Updated Campaign object with active status.

        Raises:
            InstantlyError: If activation fails.
        """
        try:
            response = await self.post(f"/campaigns/{campaign_id}/activate")
            logger.info(f"[{self.name}] Activated campaign {campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] activate_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def pause_campaign(self, campaign_id: str) -> Campaign:
        """
        Pause an active campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Updated Campaign object with paused status.

        Raises:
            InstantlyError: If pausing fails.
        """
        try:
            response = await self.post(f"/campaigns/{campaign_id}/pause")
            logger.info(f"[{self.name}] Paused campaign {campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] pause_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def duplicate_campaign(self, campaign_id: str) -> Campaign:
        """
        Duplicate an existing campaign.

        Args:
            campaign_id: Campaign UUID to duplicate.

        Returns:
            New Campaign object (copy of original).

        Raises:
            InstantlyError: If duplication fails.
        """
        try:
            response = await self.post(f"/campaigns/{campaign_id}/duplicate")
            logger.info(f"[{self.name}] Duplicated campaign {campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] duplicate_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Lead Management
    # -------------------------------------------------------------------------

    async def create_lead(
        self,
        email: str,
        campaign_id: str | None = None,
        list_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        website: str | None = None,
        phone: str | None = None,
        custom_variables: dict[str, Any] | None = None,
    ) -> Lead:
        """
        Create a new lead.

        Must provide either campaign_id or list_id.

        Args:
            email: Lead's email address.
            campaign_id: Campaign to add lead to.
            list_id: Lead list to add lead to.
            first_name: Lead's first name.
            last_name: Lead's last name.
            company_name: Lead's company name.
            website: Lead's website URL.
            phone: Lead's phone number.
            custom_variables: Additional custom fields.

        Returns:
            Lead object with created lead details.

        Raises:
            InstantlyError: If lead creation fails.
            ValueError: If neither campaign_id nor list_id provided.
        """
        if not campaign_id and not list_id:
            raise ValueError("Either campaign_id or list_id must be provided")

        payload: dict[str, Any] = {"email": email}

        if campaign_id:
            payload["campaign"] = campaign_id
        if list_id:
            payload["list_id"] = list_id
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if company_name:
            payload["company_name"] = company_name
        if website:
            payload["website"] = website
        if phone:
            payload["phone"] = phone
        if custom_variables:
            payload["custom_variables"] = custom_variables

        try:
            response = await self.post("/leads", json=payload)
            return self._parse_lead(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] create_lead failed: {e}",
                extra={"email": email},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def list_leads(
        self,
        campaign_id: str | None = None,
        list_id: str | None = None,
        search: str | None = None,
        limit: int = 100,
        starting_after: str | None = None,
    ) -> list[Lead]:
        """
        List leads with filtering and pagination.

        Args:
            campaign_id: Filter by campaign.
            list_id: Filter by lead list.
            search: Search by email or name.
            limit: Maximum leads to return (1-100).
            starting_after: Pagination cursor for next page.

        Returns:
            List of Lead objects.

        Raises:
            InstantlyError: If listing fails.
        """
        payload: dict[str, Any] = {"limit": min(limit, 100)}

        if campaign_id:
            payload["campaign"] = campaign_id
        if list_id:
            payload["list_id"] = list_id
        if search:
            payload["search"] = search
        if starting_after:
            payload["starting_after"] = starting_after

        try:
            response = await self.post("/leads/list", json=payload)
            leads_data = response.get("items", response.get("data", []))

            return [self._parse_lead(lead) for lead in leads_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] list_leads failed: {e}")
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_lead(self, lead_id: str) -> Lead:
        """
        Get a single lead by ID.

        Args:
            lead_id: Lead UUID.

        Returns:
            Lead object with full details.

        Raises:
            InstantlyError: If lead not found or request fails.
        """
        try:
            response = await self.get(f"/leads/{lead_id}")
            return self._parse_lead(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_lead failed: {e}",
                extra={"lead_id": lead_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def update_lead(
        self,
        lead_id: str,
        **kwargs: Any,
    ) -> Lead:
        """
        Update a lead.

        Args:
            lead_id: Lead UUID.
            **kwargs: Fields to update (first_name, last_name, etc.).

        Returns:
            Updated Lead object.

        Raises:
            InstantlyError: If update fails.
        """
        try:
            response = await self.patch(f"/leads/{lead_id}", json=kwargs)
            return self._parse_lead(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] update_lead failed: {e}",
                extra={"lead_id": lead_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def delete_lead(self, lead_id: str) -> bool:
        """
        Delete a lead.

        Args:
            lead_id: Lead UUID.

        Returns:
            True if deletion was successful.

        Raises:
            InstantlyError: If deletion fails.
        """
        try:
            await self.delete(f"/leads/{lead_id}")
            logger.info(f"[{self.name}] Deleted lead {lead_id}")
            return True

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] delete_lead failed: {e}",
                extra={"lead_id": lead_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def bulk_add_leads(
        self,
        leads: list[dict[str, Any]],
        campaign_id: str | None = None,
        list_id: str | None = None,
    ) -> BulkAddResult:
        """
        Bulk add up to 1000 leads at once.

        Args:
            leads: List of lead data dictionaries (each with email, optional names).
            campaign_id: Campaign to add leads to.
            list_id: Lead list to add leads to.

        Returns:
            BulkAddResult with created/failed counts.

        Raises:
            InstantlyError: If bulk add fails.
            ValueError: If leads list exceeds 1000 or no destination provided.
        """
        if len(leads) > 1000:
            raise ValueError("Maximum 1000 leads per bulk add operation")
        if not campaign_id and not list_id:
            raise ValueError("Either campaign_id or list_id must be provided")

        payload: dict[str, Any] = {"leads": leads}

        if campaign_id:
            payload["campaign"] = campaign_id
        if list_id:
            payload["list_id"] = list_id

        try:
            response = await self.post("/leads/add", json=payload)

            return BulkAddResult(
                created_count=response.get("created_count", 0),
                updated_count=response.get("updated_count", 0),
                failed_count=response.get("failed_count", 0),
                created_leads=response.get("created_leads", []),
                failed_leads=response.get("failed_leads", []),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] bulk_add_leads failed: {e}",
                extra={"lead_count": len(leads)},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def update_lead_interest_status(
        self,
        lead_email: str,
        interest_status: LeadInterestStatus,
    ) -> BackgroundJob:
        """
        Update the interest status of a lead.

        Args:
            lead_email: Lead's email address.
            interest_status: New interest status value.

        Returns:
            BackgroundJob tracking the update operation.

        Raises:
            InstantlyError: If update fails.
        """
        payload = {
            "lead_email": lead_email,
            "interest_value": interest_status.value,
        }

        try:
            response = await self.post("/leads/update-interest-status", json=payload)

            return BackgroundJob(
                job_id=response.get("job_id", response.get("id", "")),
                status=response.get("status", "pending"),
                progress=response.get("progress", 0),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] update_lead_interest_status failed: {e}",
                extra={"lead_email": lead_email},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def move_leads(
        self,
        lead_ids: list[str],
        destination_campaign_id: str | None = None,
        destination_list_id: str | None = None,
    ) -> BackgroundJob:
        """
        Move leads between campaigns or lists.

        Args:
            lead_ids: List of lead UUIDs to move.
            destination_campaign_id: Target campaign.
            destination_list_id: Target lead list.

        Returns:
            BackgroundJob tracking the move operation.

        Raises:
            InstantlyError: If move fails.
            ValueError: If no destination provided.
        """
        if not destination_campaign_id and not destination_list_id:
            raise ValueError(
                "Either destination_campaign_id or destination_list_id must be provided"
            )

        payload: dict[str, Any] = {"lead_ids": lead_ids}

        if destination_campaign_id:
            payload["destination_campaign"] = destination_campaign_id
        if destination_list_id:
            payload["destination_list_id"] = destination_list_id

        try:
            response = await self.post("/leads/move", json=payload)

            return BackgroundJob(
                job_id=response.get("job_id", response.get("id", "")),
                status=response.get("status", "pending"),
                progress=response.get("progress", 0),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] move_leads failed: {e}",
                extra={"lead_count": len(lead_ids)},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    async def get_campaign_analytics(
        self,
        campaign_id: str | None = None,
    ) -> CampaignAnalytics | list[CampaignAnalytics]:
        """
        Get analytics for a campaign or all campaigns.

        Args:
            campaign_id: Specific campaign ID, or None for all campaigns.

        Returns:
            CampaignAnalytics for single campaign, or list for all.

        Raises:
            InstantlyError: If analytics retrieval fails.
        """
        params: dict[str, Any] = {}
        if campaign_id:
            params["id"] = campaign_id

        try:
            response = await self.get("/campaigns/analytics", params=params)

            if campaign_id:
                return self._parse_analytics(response, campaign_id)

            analytics_data = response.get("items", response.get("data", []))
            return [
                self._parse_analytics(a, a.get("campaign_id", a.get("id", "")))
                for a in analytics_data
            ]

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign_analytics failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_campaign_analytics_overview(
        self,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get high-level analytics overview for campaigns.

        Args:
            campaign_id: Specific campaign ID, or None for all campaigns.

        Returns:
            Dictionary with analytics overview data.

        Raises:
            InstantlyError: If analytics retrieval fails.
        """
        params: dict[str, Any] = {}
        if campaign_id:
            params["id"] = campaign_id

        try:
            return await self.get("/campaigns/analytics/overview", params=params)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign_analytics_overview failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_campaign_daily_analytics(
        self,
        campaign_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get daily time-series analytics for campaigns.

        Args:
            campaign_id: Specific campaign ID, or None for all campaigns.
            start_date: Start date (YYYY-MM-DD format).
            end_date: End date (YYYY-MM-DD format).

        Returns:
            List of daily analytics data points.

        Raises:
            InstantlyError: If analytics retrieval fails.
        """
        params: dict[str, Any] = {}
        if campaign_id:
            params["campaign_id"] = campaign_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            response = await self.get("/campaigns/analytics/daily", params=params)
            result: list[dict[str, Any]] = response.get("items", response.get("data", []))
            return result

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign_daily_analytics failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Health Check & Utility
    # -------------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """
        Check Instantly API connectivity by fetching campaigns.

        Returns:
            Health check status with campaign count.
        """
        try:
            campaigns = await self.list_campaigns(limit=1)
            return {
                "name": self.name,
                "healthy": True,
                "api_version": self.API_VERSION,
                "campaigns_accessible": len(campaigns) >= 0,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
                "api_version": self.API_VERSION,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling new endpoints that may be released
        in the future without requiring code changes.

        Args:
            endpoint: Endpoint path (e.g., "/v2/new-endpoint").
            method: HTTP method (default: "GET").
            **kwargs: Request parameters (json, params, etc.).

        Returns:
            API response as dictionary.

        Raises:
            InstantlyError: If API request fails.

        Example:
            >>> result = await client.call_endpoint(
            ...     "/new-feature",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
        """
        try:
            return await self._request_with_retry(method, endpoint, **kwargs)
        except IntegrationError as e:
            raise InstantlyError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _parse_campaign(self, data: dict[str, Any]) -> Campaign:
        """Parse raw API response into Campaign dataclass."""
        status_value = data.get("status", 0)
        try:
            status = CampaignStatus(status_value)
        except ValueError:
            status = CampaignStatus.DRAFT

        created_at = None
        if data.get("created_at"):
            with contextlib.suppress(ValueError, AttributeError):
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        updated_at = None
        if data.get("updated_at"):
            with contextlib.suppress(ValueError, AttributeError):
                updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        return Campaign(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=status,
            workspace_id=data.get("workspace_id"),
            created_at=created_at,
            updated_at=updated_at,
            raw_response=data,
        )

    def _parse_lead(self, data: dict[str, Any]) -> Lead:
        """Parse raw API response into Lead dataclass."""
        interest_status = None
        if data.get("interest_status"):
            with contextlib.suppress(ValueError):
                interest_status = LeadInterestStatus(data["interest_status"])

        created_at = None
        if data.get("created_at"):
            with contextlib.suppress(ValueError, AttributeError):
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        return Lead(
            id=data.get("id", ""),
            email=data.get("email", ""),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            company_name=data.get("company_name"),
            website=data.get("website"),
            phone=data.get("phone"),
            interest_status=interest_status,
            campaign_id=data.get("campaign_id", data.get("campaign")),
            list_id=data.get("list_id"),
            custom_variables=data.get("custom_variables", {}),
            created_at=created_at,
            raw_response=data,
        )

    def _parse_analytics(self, data: dict[str, Any], campaign_id: str) -> CampaignAnalytics:
        """Parse raw API response into CampaignAnalytics dataclass."""
        return CampaignAnalytics(
            campaign_id=campaign_id,
            total_leads=data.get("total_leads", 0),
            contacted=data.get("contacted", 0),
            emails_sent=data.get("emails_sent", data.get("sent", 0)),
            emails_opened=data.get("emails_opened", data.get("opened", 0)),
            emails_clicked=data.get("emails_clicked", data.get("clicked", 0)),
            emails_replied=data.get("emails_replied", data.get("replied", 0)),
            emails_bounced=data.get("emails_bounced", data.get("bounced", 0)),
            unsubscribed=data.get("unsubscribed", 0),
            raw_response=data,
        )
