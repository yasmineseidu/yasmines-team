"""
HeyReach LinkedIn Automation API integration client.

Provides LinkedIn automation capabilities including connection requests,
message sequences, and profile engagement tracking. Complements LinkedIn API
for broader reach in outreach campaigns.

API Documentation: https://documenter.getpostman.com/view/23808049/2sA2xb5F75
API Version: V1
Base URL: https://api.heyreach.io/api/public

Features:
- Campaign creation, management, and analytics
- Lead/list management with bulk operations
- Connection request automation
- Message sequence creation and scheduling
- Profile engagement tracking
- A/B testing support
- Response rate monitoring

Rate Limits:
- 300 requests per minute maximum

Authentication:
- X-API-KEY header with API key from HeyReach dashboard

Example:
    >>> from src.integrations.heyreach import HeyReachClient
    >>> client = HeyReachClient(api_key="your-api-key")
    >>> campaigns = await client.list_campaigns()
    >>> print([c.name for c in campaigns])
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


class CampaignStatus(str, Enum):
    """Campaign status values from HeyReach API."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class LeadStatus(str, Enum):
    """Lead status values in HeyReach campaigns."""

    PENDING = "pending"
    CONTACTED = "contacted"
    REPLIED = "replied"
    CONNECTED = "connected"
    NOT_INTERESTED = "not_interested"
    BOUNCED = "bounced"


class SocialActionType(str, Enum):
    """Social action types for LinkedIn engagement."""

    LIKE = "like"
    FOLLOW = "follow"
    VIEW = "view"


@dataclass
class Campaign:
    """Campaign entity from HeyReach API."""

    id: str
    name: str
    status: CampaignStatus
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    account_ids: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if campaign is actively running."""
        return self.status == CampaignStatus.ACTIVE

    @property
    def is_paused(self) -> bool:
        """Check if campaign is paused."""
        return self.status == CampaignStatus.PAUSED

    @property
    def is_draft(self) -> bool:
        """Check if campaign is in draft mode."""
        return self.status == CampaignStatus.DRAFT


@dataclass
class Lead:
    """Lead entity from HeyReach API."""

    id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    company_name: str | None = None
    position: str | None = None
    location: str | None = None
    summary: str | None = None
    about: str | None = None
    status: LeadStatus | None = None
    campaign_id: str | None = None
    list_id: str | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str | None:
        """Get full name if first and last name are available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name

    @property
    def profile_url(self) -> str | None:
        """Alias for linkedin_url for consistency."""
        return self.linkedin_url


@dataclass
class LeadList:
    """Lead list entity from HeyReach API."""

    id: str
    name: str
    list_type: str = "lead"  # "lead" or "company"
    lead_count: int = 0
    created_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignAnalytics:
    """Campaign analytics data from HeyReach API."""

    campaign_id: str
    total_leads: int = 0
    contacted: int = 0
    replied: int = 0
    connected: int = 0
    response_rate: float = 0.0
    connection_rate: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def engagement_rate(self) -> float:
        """Calculate overall engagement rate."""
        if self.contacted == 0:
            return 0.0
        return ((self.replied + self.connected) / self.contacted) * 100


@dataclass
class MessageTemplate:
    """Message template from HeyReach API."""

    id: str
    name: str
    content: str
    template_type: str | None = None
    variables: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialAction:
    """Social action result from HeyReach API."""

    id: str
    action_type: SocialActionType
    status: str
    target_url: str
    scheduled_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkAddResult:
    """Result from bulk lead add operation."""

    success: bool
    added_count: int
    failed_count: int = 0
    failed_leads: list[dict[str, Any]] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """LinkedIn conversation from HeyReach API."""

    id: str
    lead_id: str | None = None
    linkedin_url: str | None = None
    last_message: str | None = None
    last_message_at: datetime | None = None
    message_count: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)


class HeyReachError(IntegrationError):
    """Exception raised for HeyReach API errors."""

    pass


class HeyReachClient(BaseIntegrationClient):
    """
    Async client for HeyReach LinkedIn Automation API.

    Provides comprehensive LinkedIn campaign management including
    connection automation, messaging sequences, and engagement tracking.

    Attributes:
        API_VERSION: Current API version.
        BASE_URL: Base URL for API requests.

    Note:
        - Rate limit: 300 requests per minute
        - Requires HeyReach subscription
        - X-API-KEY header authentication
    """

    API_VERSION = "V1"
    BASE_URL = "https://api.heyreach.io/api/public"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize HeyReach client.

        Args:
            api_key: HeyReach API key from dashboard.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="heyreach",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client (API {self.API_VERSION})")

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for HeyReach API requests.

        HeyReach uses X-API-KEY header instead of Bearer token.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # -------------------------------------------------------------------------
    # Authentication & Health
    # -------------------------------------------------------------------------

    async def check_api_key(self) -> bool:
        """
        Validate the API key is working.

        Returns:
            True if API key is valid.

        Raises:
            HeyReachError: If validation fails.
        """
        try:
            response = await self.get("/auth/CheckApiKey")
            return response.get("success", response.get("data", False)) is True

        except IntegrationError as e:
            logger.error(f"[{self.name}] check_api_key failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check HeyReach API connectivity.

        Returns:
            Health check status with API validation result.
        """
        try:
            is_valid = await self.check_api_key()
            return {
                "name": self.name,
                "healthy": is_valid,
                "api_version": self.API_VERSION,
                "api_key_valid": is_valid,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
                "api_version": self.API_VERSION,
            }

    # -------------------------------------------------------------------------
    # Campaign Management
    # -------------------------------------------------------------------------

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Campaign]:
        """
        List all campaigns with pagination.

        Args:
            limit: Maximum campaigns to return.
            offset: Pagination offset.

        Returns:
            List of Campaign objects.

        Raises:
            HeyReachError: If listing fails.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = await self.get("/campaign/GetAll", params=params)
            campaigns_data = self._extract_list_data(response)

            return [self._parse_campaign(c) for c in campaigns_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] list_campaigns failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_campaign(self, campaign_id: str) -> Campaign:
        """
        Get detailed information about a specific campaign.

        Args:
            campaign_id: Campaign ID.

        Returns:
            Campaign object with full details.

        Raises:
            HeyReachError: If campaign not found or request fails.
        """
        try:
            response = await self.get(f"/campaign/{campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_active_campaigns(self) -> list[Campaign]:
        """
        Get all active campaigns with LinkedIn senders.

        Returns:
            List of active Campaign objects.

        Raises:
            HeyReachError: If request fails.
        """
        try:
            campaigns = await self.list_campaigns(limit=100)
            return [c for c in campaigns if c.is_active]

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_active_campaigns failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def create_campaign(
        self,
        name: str,
        description: str | None = None,
        **kwargs: Any,
    ) -> Campaign:
        """
        Create a new LinkedIn campaign.

        Args:
            name: Campaign name.
            description: Campaign description.
            **kwargs: Additional campaign parameters (settings, etc.).

        Returns:
            Campaign object with created campaign details.

        Raises:
            HeyReachError: If campaign creation fails.
        """
        payload: dict[str, Any] = {"name": name}

        if description:
            payload["description"] = description

        payload.update(kwargs)

        try:
            response = await self.post("/campaign/Create", json=payload)
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] create_campaign failed: {e}",
                extra={"campaign_name": name},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def pause_campaign(self, campaign_id: str) -> Campaign:
        """
        Pause an active campaign.

        Args:
            campaign_id: Campaign ID to pause.

        Returns:
            Updated Campaign object with paused status.

        Raises:
            HeyReachError: If pausing fails.
        """
        try:
            response = await self.post("/campaign/pause", json={"campaignId": campaign_id})
            logger.info(f"[{self.name}] Paused campaign {campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] pause_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def resume_campaign(self, campaign_id: str) -> Campaign:
        """
        Resume a paused campaign.

        Args:
            campaign_id: Campaign ID to resume.

        Returns:
            Updated Campaign object with active status.

        Raises:
            HeyReachError: If resuming fails.
        """
        try:
            response = await self.post("/campaign/resume", json={"campaignId": campaign_id})
            logger.info(f"[{self.name}] Resumed campaign {campaign_id}")
            return self._parse_campaign(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] resume_campaign failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Lead Management
    # -------------------------------------------------------------------------

    async def add_leads_to_campaign(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
    ) -> BulkAddResult:
        """
        Add leads to an active campaign.

        Note: Campaign must be ACTIVE or PAUSED for leads to be added.
        Adding leads to a paused campaign will activate it.

        Args:
            campaign_id: Campaign ID to add leads to.
            leads: List of lead dictionaries with fields:
                - firstName: First name (optional)
                - lastName: Last name (optional)
                - email: Email address (optional)
                - linkedinUrl/profileUrl: LinkedIn profile URL (optional)
                - company/companyName: Company name (optional)
                - position: Job title (optional)
                - customUserFields: List of {name, value} dicts (optional)

        Returns:
            BulkAddResult with success status and counts.

        Raises:
            HeyReachError: If adding leads fails.

        Example:
            >>> leads = [
            ...     {
            ...         "firstName": "John",
            ...         "lastName": "Doe",
            ...         "profileUrl": "https://linkedin.com/in/johndoe",
            ...         "companyName": "Acme Inc",
            ...         "position": "CEO"
            ...     }
            ... ]
            >>> result = await client.add_leads_to_campaign("campaign-123", leads)
        """
        payload = {
            "campaignId": campaign_id,
            "leads": leads,
        }

        try:
            response = await self.post("/campaign/AddLeadsToListV2", json=payload)

            return BulkAddResult(
                success=response.get("success", True),
                added_count=response.get("addedCount", len(leads)),
                failed_count=response.get("failedCount", 0),
                failed_leads=response.get("failedLeads", []),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] add_leads_to_campaign failed: {e}",
                extra={"campaign_id": campaign_id, "lead_count": len(leads)},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_campaign_leads(
        self,
        campaign_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[Lead]:
        """
        Retrieve leads from a campaign with pagination.

        Args:
            campaign_id: Campaign ID to get leads from.
            page: Page number (1-based).
            limit: Leads per page.

        Returns:
            List of Lead objects.

        Raises:
            HeyReachError: If retrieval fails.
        """
        payload = {
            "campaignId": campaign_id,
            "page": page,
            "limit": limit,
        }

        try:
            response = await self.post("/campaign/GetLeads", json=payload)
            leads_data = self._extract_list_data(response)

            return [self._parse_lead(lead) for lead in leads_data]

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign_leads failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_lead_details(self, linkedin_url: str) -> Lead:
        """
        Get detailed lead profile information.

        Args:
            linkedin_url: LinkedIn profile URL.

        Returns:
            Lead object with full details.

        Raises:
            HeyReachError: If lead not found or request fails.
        """
        params = {"linkedinUrl": linkedin_url}

        try:
            response = await self.get("/lead/GetDetails", params=params)
            return self._parse_lead(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_lead_details failed: {e}",
                extra={"linkedin_url": linkedin_url},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def update_lead_status(
        self,
        lead_id: str,
        status: LeadStatus,
    ) -> Lead:
        """
        Update a lead's status.

        Args:
            lead_id: Lead ID.
            status: New lead status.

        Returns:
            Updated Lead object.

        Raises:
            HeyReachError: If update fails.
        """
        payload = {
            "leadId": lead_id,
            "status": status.value,
        }

        try:
            response = await self.post("/lead/UpdateStatus", json=payload)
            return self._parse_lead(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] update_lead_status failed: {e}",
                extra={"lead_id": lead_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # List Management
    # -------------------------------------------------------------------------

    async def list_all_lists(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LeadList]:
        """
        Retrieve all lead lists with pagination.

        Args:
            limit: Maximum lists to return.
            offset: Pagination offset.

        Returns:
            List of LeadList objects.

        Raises:
            HeyReachError: If retrieval fails.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = await self.get("/list/GetAll", params=params)
            lists_data = self._extract_list_data(response)

            return [self._parse_list(lst) for lst in lists_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] list_all_lists failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def create_empty_list(
        self,
        name: str,
        list_type: str = "lead",
    ) -> LeadList:
        """
        Create a new empty lead or company list.

        Args:
            name: List name.
            list_type: Type of list ("lead" or "company").

        Returns:
            LeadList object with created list details.

        Raises:
            HeyReachError: If creation fails.
        """
        payload = {
            "name": name,
            "type": list_type,
        }

        try:
            response = await self.post("/list/CreateEmpty", json=payload)
            return self._parse_list(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] create_empty_list failed: {e}",
                extra={"list_name": name},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def add_leads_to_list(
        self,
        list_id: int,
        leads: list[dict[str, Any]],
    ) -> BulkAddResult:
        """
        Add leads to a list.

        Args:
            list_id: List ID to add leads to.
            leads: List of lead dictionaries.

        Returns:
            BulkAddResult with success status.

        Raises:
            HeyReachError: If adding leads fails.
        """
        payload = {
            "listId": list_id,
            "leads": leads,
        }

        try:
            response = await self.post("/list/AddLeadsToListV2", json=payload)

            return BulkAddResult(
                success=response.get("success", True),
                added_count=response.get("addedCount", len(leads)),
                failed_count=response.get("failedCount", 0),
                failed_leads=response.get("failedLeads", []),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] add_leads_to_list failed: {e}",
                extra={"list_id": list_id, "lead_count": len(leads)},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Messaging
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        lead_id: str,
        message: str,
        template_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a direct message to a lead.

        Args:
            lead_id: Lead ID to message.
            message: Message content.
            template_id: Optional template ID to use.

        Returns:
            Response with message ID.

        Raises:
            HeyReachError: If sending fails.
        """
        payload: dict[str, Any] = {
            "leadId": lead_id,
            "message": message,
        }

        if template_id:
            payload["templateId"] = template_id

        try:
            response = await self.post("/message/Send", json=payload)
            logger.info(f"[{self.name}] Sent message to lead {lead_id}")
            return response

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] send_message failed: {e}",
                extra={"lead_id": lead_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_templates(self) -> list[MessageTemplate]:
        """
        Retrieve all message templates.

        Returns:
            List of MessageTemplate objects.

        Raises:
            HeyReachError: If retrieval fails.
        """
        try:
            response = await self.get("/templates/GetAll")
            templates_data = self._extract_list_data(response)

            return [self._parse_template(t) for t in templates_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_templates failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[Conversation]:
        """
        Retrieve LinkedIn conversations with filtering.

        Args:
            limit: Maximum conversations to return.
            offset: Pagination offset.
            **filters: Additional filters (campaign_id, etc.).

        Returns:
            List of Conversation objects.

        Raises:
            HeyReachError: If retrieval fails.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            **filters,
        }

        try:
            response = await self.get("/conversations/GetAll", params=params)
            conversations_data = self._extract_list_data(response)

            return [self._parse_conversation(c) for c in conversations_data]

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_conversations failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Social Actions
    # -------------------------------------------------------------------------

    async def perform_social_action(
        self,
        action: SocialActionType,
        target_url: str,
        lead_id: str | None = None,
    ) -> SocialAction:
        """
        Perform a social engagement action on LinkedIn.

        Args:
            action: Type of action (like, follow, view).
            target_url: LinkedIn URL to perform action on.
            lead_id: Optional lead ID to associate action with.

        Returns:
            SocialAction object with result.

        Raises:
            HeyReachError: If action fails.
        """
        payload: dict[str, Any] = {
            "action": action.value,
            "targetUrl": target_url,
        }

        if lead_id:
            payload["leadId"] = lead_id

        try:
            response = await self.post("/social/Action", json=payload)
            return self._parse_social_action(response)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] perform_social_action failed: {e}",
                extra={"action": action.value, "target_url": target_url},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    async def get_campaign_analytics(self, campaign_id: str) -> CampaignAnalytics:
        """
        Get detailed campaign performance metrics.

        Args:
            campaign_id: Campaign ID to get analytics for.

        Returns:
            CampaignAnalytics object with metrics.

        Raises:
            HeyReachError: If retrieval fails.
        """
        try:
            response = await self.get(f"/analytics/campaign/{campaign_id}")
            return self._parse_analytics(response, campaign_id)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_campaign_analytics failed: {e}",
                extra={"campaign_id": campaign_id},
            )
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_overall_stats(self) -> dict[str, Any]:
        """
        Get comprehensive account-wide analytics.

        Returns:
            Dictionary with overall statistics.

        Raises:
            HeyReachError: If retrieval fails.
        """
        try:
            return await self.get("/analytics/overall")

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_overall_stats failed: {e}")
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Future-Proof Endpoint
    # -------------------------------------------------------------------------

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
            endpoint: Endpoint path (e.g., "/new-feature").
            method: HTTP method (default: "GET").
            **kwargs: Request parameters (json, params, etc.).

        Returns:
            API response as dictionary.

        Raises:
            HeyReachError: If API request fails.

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
            raise HeyReachError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _extract_list_data(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract list data from API response.

        HeyReach API may return data directly as a list or wrapped in
        items/data keys. This method normalizes the response.

        Args:
            response: API response dictionary.

        Returns:
            List of data dictionaries.
        """
        # Response structure varies - may have items, data, or be the list itself
        if "items" in response:
            return list(response["items"])
        if "data" in response:
            return list(response["data"])
        # Fallback - return empty list
        return []

    def _parse_campaign(self, data: dict[str, Any]) -> Campaign:
        """Parse raw API response into Campaign dataclass."""
        status_value = data.get("status", "DRAFT")
        try:
            status = CampaignStatus(status_value)
        except ValueError:
            status = CampaignStatus.DRAFT

        created_at = None
        if data.get("createdAt") or data.get("created_at"):
            timestamp = data.get("createdAt") or data.get("created_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    created_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        updated_at = None
        if data.get("updatedAt") or data.get("updated_at"):
            timestamp = data.get("updatedAt") or data.get("updated_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    updated_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return Campaign(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            status=status,
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
            account_ids=data.get("campaignAccountIds", data.get("account_ids", [])),
            raw_response=data,
        )

    def _parse_lead(self, data: dict[str, Any]) -> Lead:
        """Parse raw API response into Lead dataclass."""
        status = None
        if data.get("status"):
            with contextlib.suppress(ValueError):
                status = LeadStatus(data["status"])

        created_at = None
        if data.get("createdAt") or data.get("created_at"):
            timestamp = data.get("createdAt") or data.get("created_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    created_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        # Handle custom fields from different formats
        custom_fields: dict[str, Any] = {}
        if data.get("customUserFields"):
            for field_data in data["customUserFields"]:
                if isinstance(field_data, dict):
                    custom_fields[field_data.get("name", "")] = field_data.get("value")
        elif data.get("custom_fields"):
            custom_fields = data["custom_fields"]

        return Lead(
            id=str(data.get("id", "")) if data.get("id") else None,
            first_name=data.get("firstName", data.get("first_name")),
            last_name=data.get("lastName", data.get("last_name")),
            email=data.get("emailAddress", data.get("email")),
            linkedin_url=data.get("profileUrl", data.get("linkedinUrl", data.get("linkedin_url"))),
            company_name=data.get("companyName", data.get("company_name", data.get("company"))),
            position=data.get("position"),
            location=data.get("location"),
            summary=data.get("summary"),
            about=data.get("about"),
            status=status,
            campaign_id=str(data.get("campaignId", data.get("campaign_id", ""))) or None,
            list_id=str(data.get("listId", data.get("list_id", ""))) or None,
            custom_fields=custom_fields,
            created_at=created_at,
            raw_response=data,
        )

    def _parse_list(self, data: dict[str, Any]) -> LeadList:
        """Parse raw API response into LeadList dataclass."""
        created_at = None
        if data.get("createdAt") or data.get("created_at"):
            timestamp = data.get("createdAt") or data.get("created_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    created_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return LeadList(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            list_type=data.get("type", "lead"),
            lead_count=data.get("leadCount", data.get("lead_count", 0)),
            created_at=created_at,
            raw_response=data,
        )

    def _parse_analytics(self, data: dict[str, Any], campaign_id: str) -> CampaignAnalytics:
        """Parse raw API response into CampaignAnalytics dataclass."""
        return CampaignAnalytics(
            campaign_id=campaign_id,
            total_leads=data.get("totalLeads", data.get("total_leads", 0)),
            contacted=data.get("contacted", 0),
            replied=data.get("replied", 0),
            connected=data.get("connected", 0),
            response_rate=data.get("responseRate", data.get("response_rate", 0.0)),
            connection_rate=data.get("connectionRate", data.get("connection_rate", 0.0)),
            raw_response=data,
        )

    def _parse_template(self, data: dict[str, Any]) -> MessageTemplate:
        """Parse raw API response into MessageTemplate dataclass."""
        return MessageTemplate(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            content=data.get("content", ""),
            template_type=data.get("type"),
            variables=data.get("variables", []),
            raw_response=data,
        )

    def _parse_social_action(self, data: dict[str, Any]) -> SocialAction:
        """Parse raw API response into SocialAction dataclass."""
        action_type = SocialActionType.VIEW
        if data.get("type") or data.get("action"):
            with contextlib.suppress(ValueError):
                action_type = SocialActionType(data.get("type") or data.get("action"))

        scheduled_at = None
        if data.get("scheduledAt") or data.get("scheduled_at"):
            timestamp = data.get("scheduledAt") or data.get("scheduled_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    scheduled_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return SocialAction(
            id=str(data.get("id", "")),
            action_type=action_type,
            status=data.get("status", "pending"),
            target_url=data.get("targetUrl", data.get("target_url", "")),
            scheduled_at=scheduled_at,
            raw_response=data,
        )

    def _parse_conversation(self, data: dict[str, Any]) -> Conversation:
        """Parse raw API response into Conversation dataclass."""
        last_message_at = None
        if data.get("lastMessageAt") or data.get("last_message_at"):
            timestamp = data.get("lastMessageAt") or data.get("last_message_at")
            with contextlib.suppress(ValueError, AttributeError, TypeError):
                if isinstance(timestamp, str):
                    last_message_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return Conversation(
            id=str(data.get("id", "")),
            lead_id=str(data.get("leadId", data.get("lead_id", ""))) or None,
            linkedin_url=data.get("linkedinUrl", data.get("linkedin_url")),
            last_message=data.get("lastMessage", data.get("last_message")),
            last_message_at=last_message_at,
            message_count=data.get("messageCount", data.get("message_count", 0)),
            raw_response=data,
        )
