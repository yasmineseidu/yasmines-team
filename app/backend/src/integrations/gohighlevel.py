"""
GoHighLevel CRM API integration client.

Provides unified CRM, funnel management, and marketing automation for:
- Contact management (CRUD operations)
- Lead management and pipeline tracking
- Email and SMS campaigns
- Opportunity/deal management
- Custom fields and tagging
- Webhooks and automation

API Documentation: https://marketplace.gohighlevel.com/docs/
Base URL: https://rest.gohighlevel.com/v1

Rate Limits:
- 200,000 API requests per day per location/company resource
- Exponential backoff on 429 (Too Many Requests)

Authentication:
- Bearer token (OAuth 2.0 or API key)
- X-GHL-Token header for Location-based access
- Per-location token management

Example:
    >>> from src.integrations.gohighlevel import GoHighLevelClient
    >>> client = GoHighLevelClient(
    ...     api_key="your_api_key",  # pragma: allowlist secret
    ...     location_id="location_123"
    ... )
    >>> contact = await client.create_contact(
    ...     first_name="John",
    ...     last_name="Doe",
    ...     email="john@example.com"
    ... )
    >>> print(contact.id)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class GoHighLevelError(IntegrationError):
    """Base exception for GoHighLevel API errors."""

    pass


class GoHighLevelAuthError(GoHighLevelError, AuthenticationError):
    """Authentication error for GoHighLevel API."""

    pass


class GoHighLevelRateLimitError(GoHighLevelError, RateLimitError):
    """Rate limit exceeded for GoHighLevel API."""

    pass


class ContactSource(str, Enum):
    """Contact source types in GoHighLevel."""

    API = "api"
    FORM = "form"
    IMPORT = "import"
    MANUAL = "manual"
    PHONE = "phone"
    FACEBOOK = "facebook"
    GOOGLE = "google"


class ContactStatus(str, Enum):
    """Contact status in GoHighLevel."""

    LEAD = "lead"
    CUSTOMER = "customer"
    OPPORTUNITY = "opportunity"
    UNRESPONSIVE = "unresponsive"
    ARCHIVE = "archive"


class DealStatus(str, Enum):
    """Deal/Opportunity status."""

    OPEN = "open"
    WON = "won"
    LOST = "lost"
    PENDING = "pending"


class CampaignType(str, Enum):
    """Campaign types in GoHighLevel."""

    EMAIL = "email"
    SMS = "sms"
    FACEBOOK = "facebook"
    CALL = "call"
    AUTOMATION = "automation"


@dataclass
class Contact:
    """GoHighLevel Contact."""

    id: str
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    source: str | None = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    website: str | None = None
    timezone: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Deal:
    """GoHighLevel Deal/Opportunity."""

    id: str
    name: str
    value: float | None = None
    status: str | None = None
    contact_id: str | None = None
    stage: str | None = None
    probability: int | None = None
    expected_close_date: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignStatus:
    """Campaign status information."""

    id: str
    name: str
    type: str
    status: str
    contacts_count: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookResponse:
    """Webhook configuration response."""

    id: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class GoHighLevelClient(BaseIntegrationClient):
    """
    Async client for GoHighLevel CRM API.

    Provides complete CRM functionality including contact management,
    deal/opportunity tracking, campaigns, and automation.

    Attributes:
        api_key: API key or OAuth token for authentication
        location_id: Location ID for location-specific operations
        api_version: API version (default: v1)
    """

    API_BASE_URL = "https://rest.gohighlevel.com/v1"

    def __init__(
        self,
        api_key: str,
        location_id: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize GoHighLevel client.

        Args:
            api_key: GoHighLevel API key or OAuth token
            location_id: Location ID for this client
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_base_delay: Base delay for exponential backoff

        Raises:
            ValueError: If api_key or location_id is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        if not location_id or not location_id.strip():
            raise ValueError("Location ID cannot be empty")

        super().__init__(
            name="gohighlevel",
            base_url=self.API_BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )
        self.location_id = location_id.strip()
        logger.info(f"Initialized GoHighLevel client for location {self.location_id}")

    def _get_headers(self) -> dict[str, str]:
        """
        Get default headers for GoHighLevel API requests.

        Uses Authorization Bearer token header and X-GHL-Token for location.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-GHL-Token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_contact(
        self,
        first_name: str,
        last_name: str = "",
        email: str | None = None,
        phone: str | None = None,
        source: str = "api",
        status: str = "lead",
        tags: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Contact:
        """
        Create a new contact.

        Args:
            first_name: Contact first name (required)
            last_name: Contact last name
            email: Contact email address
            phone: Contact phone number
            source: Contact source (default: api)
            status: Contact status (default: lead)
            tags: List of tags
            custom_fields: Custom field values
            **kwargs: Additional parameters

        Returns:
            Created contact object

        Raises:
            GoHighLevelError: If contact creation fails
        """
        data: dict[str, Any] = {
            "firstName": first_name,
            "lastName": last_name,
            "source": source,
            "status": status,
        }

        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone
        if tags:
            data["tags"] = tags
        if custom_fields:
            data["customFields"] = custom_fields

        data.update(kwargs)

        try:
            response = await self.post(f"/contacts/?locationId={self.location_id}", json=data)
            logger.info(f"Created contact: {response.get('id')}")
            return self._parse_contact(response)
        except Exception as e:
            logger.error(f"Failed to create contact: {e}")
            raise GoHighLevelError(f"Failed to create contact: {e}") from e

    async def get_contact(self, contact_id: str) -> Contact:
        """
        Retrieve a contact by ID.

        Args:
            contact_id: Contact ID

        Returns:
            Contact object

        Raises:
            GoHighLevelError: If contact not found or request fails
        """
        try:
            response = await self.get(f"/contacts/{contact_id}/?locationId={self.location_id}")
            return self._parse_contact(response)
        except Exception as e:
            logger.error(f"Failed to get contact {contact_id}: {e}")
            raise GoHighLevelError(f"Failed to get contact {contact_id}: {e}") from e

    async def update_contact(self, contact_id: str, **kwargs: Any) -> Contact:
        """
        Update a contact.

        Args:
            contact_id: Contact ID
            **kwargs: Fields to update (e.g., firstName, email, phone)

        Returns:
            Updated contact object

        Raises:
            GoHighLevelError: If update fails
        """
        try:
            response = await self.put(
                f"/contacts/{contact_id}/?locationId={self.location_id}",
                json=kwargs,
            )
            logger.info(f"Updated contact: {contact_id}")
            return self._parse_contact(response)
        except Exception as e:
            logger.error(f"Failed to update contact {contact_id}: {e}")
            raise GoHighLevelError(f"Failed to update contact {contact_id}: {e}") from e

    async def delete_contact(self, contact_id: str) -> bool:
        """
        Delete a contact.

        Args:
            contact_id: Contact ID

        Returns:
            True if deletion successful

        Raises:
            GoHighLevelError: If deletion fails
        """
        try:
            await self.delete(f"/contacts/{contact_id}/?locationId={self.location_id}")
            logger.info(f"Deleted contact: {contact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete contact {contact_id}: {e}")
            raise GoHighLevelError(f"Failed to delete contact {contact_id}: {e}") from e

    async def list_contacts(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        List contacts with pagination.

        Args:
            limit: Maximum contacts to return (1-200)
            offset: Offset for pagination
            search: Search query
            status: Filter by status
            **kwargs: Additional filters

        Returns:
            Dictionary with contacts list and metadata

        Raises:
            GoHighLevelError: If listing fails
        """
        params: dict[str, Any] = {
            "locationId": self.location_id,
            "limit": min(limit, 200),
            "offset": offset,
        }

        if search:
            params["search"] = search
        if status:
            params["status"] = status

        params.update(kwargs)

        try:
            response = await self.get("/contacts/", params=params)
            # Parse contacts in response
            contacts_data = response.get("contacts", [])
            parsed_contacts = [self._parse_contact(c) for c in contacts_data]
            return {
                "contacts": parsed_contacts,
                "total": response.get("total", len(parsed_contacts)),
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"Failed to list contacts: {e}")
            raise GoHighLevelError(f"Failed to list contacts: {e}") from e

    async def add_tag(self, contact_id: str, tag: str) -> Contact:
        """
        Add a tag to a contact.

        Args:
            contact_id: Contact ID
            tag: Tag to add

        Returns:
            Updated contact object

        Raises:
            GoHighLevelError: If tagging fails
        """
        try:
            response = await self.post(
                f"/contacts/{contact_id}/tags?locationId={self.location_id}",
                json={"tag": tag},
            )
            logger.info(f"Added tag '{tag}' to contact {contact_id}")
            return self._parse_contact(response)
        except Exception as e:
            logger.error(f"Failed to add tag to contact {contact_id}: {e}")
            raise GoHighLevelError(f"Failed to add tag to contact {contact_id}: {e}") from e

    async def remove_tag(self, contact_id: str, tag: str) -> Contact:
        """
        Remove a tag from a contact.

        Args:
            contact_id: Contact ID
            tag: Tag to remove

        Returns:
            Updated contact object

        Raises:
            GoHighLevelError: If untagging fails
        """
        try:
            response = await self.delete(
                f"/contacts/{contact_id}/tags/{tag}?locationId={self.location_id}"
            )
            logger.info(f"Removed tag '{tag}' from contact {contact_id}")
            return self._parse_contact(response)
        except Exception as e:
            logger.error(f"Failed to remove tag from contact {contact_id}: {e}")
            raise GoHighLevelError(f"Failed to remove tag from contact {contact_id}: {e}") from e

    async def create_deal(
        self,
        name: str,
        contact_id: str | None = None,
        value: float | None = None,
        status: str = "open",
        stage: str | None = None,
        expected_close_date: str | None = None,
        **kwargs: Any,
    ) -> Deal:
        """
        Create a new deal/opportunity.

        Args:
            name: Deal name
            contact_id: Associated contact ID
            value: Deal value
            status: Deal status (default: open)
            stage: Deal stage
            expected_close_date: Expected close date (ISO format)
            **kwargs: Additional parameters

        Returns:
            Created deal object

        Raises:
            GoHighLevelError: If deal creation fails
        """
        data: dict[str, Any] = {
            "name": name,
            "status": status,
        }

        if contact_id:
            data["contactId"] = contact_id
        if value is not None:
            data["value"] = value
        if stage:
            data["stage"] = stage
        if expected_close_date:
            data["expectedCloseDate"] = expected_close_date

        data.update(kwargs)

        try:
            response = await self.post(f"/deals/?locationId={self.location_id}", json=data)
            logger.info(f"Created deal: {response.get('id')}")
            return self._parse_deal(response)
        except Exception as e:
            logger.error(f"Failed to create deal: {e}")
            raise GoHighLevelError(f"Failed to create deal: {e}") from e

    async def get_deal(self, deal_id: str) -> Deal:
        """
        Retrieve a deal by ID.

        Args:
            deal_id: Deal ID

        Returns:
            Deal object

        Raises:
            GoHighLevelError: If deal not found or request fails
        """
        try:
            response = await self.get(f"/deals/{deal_id}/?locationId={self.location_id}")
            return self._parse_deal(response)
        except Exception as e:
            logger.error(f"Failed to get deal {deal_id}: {e}")
            raise GoHighLevelError(f"Failed to get deal {deal_id}: {e}") from e

    async def update_deal(self, deal_id: str, **kwargs: Any) -> Deal:
        """
        Update a deal.

        Args:
            deal_id: Deal ID
            **kwargs: Fields to update

        Returns:
            Updated deal object

        Raises:
            GoHighLevelError: If update fails
        """
        try:
            response = await self.put(
                f"/deals/{deal_id}/?locationId={self.location_id}",
                json=kwargs,
            )
            logger.info(f"Updated deal: {deal_id}")
            return self._parse_deal(response)
        except Exception as e:
            logger.error(f"Failed to update deal {deal_id}: {e}")
            raise GoHighLevelError(f"Failed to update deal {deal_id}: {e}") from e

    async def delete_deal(self, deal_id: str) -> bool:
        """
        Delete a deal.

        Args:
            deal_id: Deal ID

        Returns:
            True if deletion successful

        Raises:
            GoHighLevelError: If deletion fails
        """
        try:
            await self.delete(f"/deals/{deal_id}/?locationId={self.location_id}")
            logger.info(f"Deleted deal: {deal_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete deal {deal_id}: {e}")
            raise GoHighLevelError(f"Failed to delete deal {deal_id}: {e}") from e

    async def list_deals(
        self,
        limit: int = 100,
        offset: int = 0,
        contact_id: str | None = None,
        status: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        List deals with pagination.

        Args:
            limit: Maximum deals to return
            offset: Offset for pagination
            contact_id: Filter by contact
            status: Filter by status
            **kwargs: Additional filters

        Returns:
            Dictionary with deals list and metadata

        Raises:
            GoHighLevelError: If listing fails
        """
        params: dict[str, Any] = {
            "locationId": self.location_id,
            "limit": min(limit, 200),
            "offset": offset,
        }

        if contact_id:
            params["contactId"] = contact_id
        if status:
            params["status"] = status

        params.update(kwargs)

        try:
            response = await self.get("/deals/", params=params)
            deals_data = response.get("deals", [])
            parsed_deals = [self._parse_deal(d) for d in deals_data]
            return {
                "deals": parsed_deals,
                "total": response.get("total", len(parsed_deals)),
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"Failed to list deals: {e}")
            raise GoHighLevelError(f"Failed to list deals: {e}") from e

    async def send_email(
        self,
        contact_id: str,
        subject: str,
        body: str,
        from_email: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send email to a contact.

        Args:
            contact_id: Contact ID to send to
            subject: Email subject
            body: Email body (HTML)
            from_email: From email address
            **kwargs: Additional parameters

        Returns:
            Email send response

        Raises:
            GoHighLevelError: If email send fails
        """
        data: dict[str, Any] = {
            "contactId": contact_id,
            "subject": subject,
            "body": body,
        }

        if from_email:
            data["fromEmail"] = from_email

        data.update(kwargs)

        try:
            response = await self.post(f"/emails/?locationId={self.location_id}", json=data)
            logger.info(f"Sent email to contact {contact_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise GoHighLevelError(f"Failed to send email: {e}") from e

    async def send_sms(
        self,
        contact_id: str,
        message: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send SMS to a contact.

        Args:
            contact_id: Contact ID to send to
            message: SMS message text
            **kwargs: Additional parameters

        Returns:
            SMS send response

        Raises:
            GoHighLevelError: If SMS send fails
        """
        data: dict[str, Any] = {
            "contactId": contact_id,
            "message": message,
        }

        data.update(kwargs)

        try:
            response = await self.post(f"/sms/?locationId={self.location_id}", json=data)
            logger.info(f"Sent SMS to contact {contact_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            raise GoHighLevelError(f"Failed to send SMS: {e}") from e

    async def get_me(self) -> dict[str, Any]:
        """
        Get information about the authenticated user/location.

        Returns:
            User/location information

        Raises:
            GoHighLevelError: If request fails
        """
        try:
            response = await self.get(f"/locations/{self.location_id}/")
            logger.info("Retrieved user/location info")
            return response
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise GoHighLevelError(f"Failed to get user info: {e}") from e

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling endpoints that may be released in the future
        without requiring code changes to the client.

        Args:
            endpoint: Endpoint path (e.g., "/contacts", "/deals/123/update")
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            **kwargs: Request parameters (json, params, data, etc.)

        Returns:
            API response as dictionary

        Example:
            >>> # Call new endpoint that doesn't have specific method yet
            >>> result = await client.call_endpoint(
            ...     "/new-feature",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
            >>> # Call with query parameters
            >>> result = await client.call_endpoint(
            ...     "/contacts",
            ...     method="GET",
            ...     params={"status": "lead", "limit": 50}
            ... )
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        method = method.upper()

        try:
            if method == "GET":
                return await self.get(f"{endpoint}?locationId={self.location_id}", **kwargs)
            elif method == "POST":
                return await self.post(f"{endpoint}?locationId={self.location_id}", **kwargs)
            elif method == "PUT":
                return await self.put(f"{endpoint}?locationId={self.location_id}", **kwargs)
            elif method == "DELETE":
                return await self.delete(f"{endpoint}?locationId={self.location_id}", **kwargs)
            elif method == "PATCH":
                return await self.patch(f"{endpoint}?locationId={self.location_id}", **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except Exception as e:
            logger.error(f"API call to {endpoint} failed: {e}")
            raise GoHighLevelError(f"Failed to call endpoint {endpoint}: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check integration health/connectivity.

        Returns:
            Health check response with status

        Raises:
            GoHighLevelError: If health check fails
        """
        try:
            response = await self.get_me()
            location_name = response.get("name", "Unknown")
            return {
                "name": self.name,
                "healthy": True,
                "message": f"GoHighLevel location '{location_name}' is online",
                "location_id": self.location_id,
                "location_name": location_name,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "message": f"Health check failed: {e}",
                "error": str(e),
            }

    def _parse_contact(self, data: dict[str, Any]) -> Contact:
        """Parse API response into Contact object."""
        # Handle both 'contact' and direct response formats
        contact_data = data.get("contact", data)

        return Contact(
            id=contact_data.get("id", ""),
            first_name=contact_data.get("firstName", ""),
            last_name=contact_data.get("lastName"),
            email=contact_data.get("email"),
            phone=contact_data.get("phone"),
            status=contact_data.get("status"),
            source=contact_data.get("source"),
            tags=contact_data.get("tags", []),
            custom_fields=contact_data.get("customFields", {}),
            address=contact_data.get("address"),
            city=contact_data.get("city"),
            state=contact_data.get("state"),
            postal_code=contact_data.get("postalCode"),
            website=contact_data.get("website"),
            timezone=contact_data.get("timezone"),
            created_at=contact_data.get("createdAt"),
            updated_at=contact_data.get("updatedAt"),
            raw=contact_data,
        )

    def _parse_deal(self, data: dict[str, Any]) -> Deal:
        """Parse API response into Deal object."""
        # Handle both 'deal' and direct response formats
        deal_data = data.get("deal", data)

        return Deal(
            id=deal_data.get("id", ""),
            name=deal_data.get("name", ""),
            value=deal_data.get("value"),
            status=deal_data.get("status"),
            contact_id=deal_data.get("contactId"),
            stage=deal_data.get("stage"),
            probability=deal_data.get("probability"),
            expected_close_date=deal_data.get("expectedCloseDate"),
            created_at=deal_data.get("createdAt"),
            updated_at=deal_data.get("updatedAt"),
            raw=deal_data,
        )
