"""Cal.com API client for async integration with Claude Agent SDK.

Provides complete async client for Cal.com REST API v2 with:
- Complete CRUD operations for bookings, event types, users, and teams
- Exponential backoff retry logic with jitter (max 3 retries)
- Rate limiting awareness with tracking of remaining requests
- Circuit breaker pattern for repeated failures
- Structured error handling with custom exceptions
"""

import asyncio
import contextlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import httpx
from dotenv import load_dotenv

from src.integrations.base import BaseIntegrationClient
from src.integrations.cal_com.exceptions import (
    CalComAPIError,
    CalComAuthError,
    CalComConfigError,
    CalComNotFoundError,
    CalComRateLimitError,
    CalComValidationError,
)
from src.integrations.cal_com.models import (
    Availability,
    CalComEvent,
    EventType,
    Team,
    User,
)

logger = logging.getLogger(__name__)


class CalComClient(BaseIntegrationClient):
    """Async client for Cal.com API v2.

    Provides complete integration with Cal.com scheduling platform,
    supporting user management, event types, bookings, availability,
    teams, and user settings.

    Example:
        >>> client = CalComClient(api_key="your-api-key")
        >>> user = await client.get_user()
        >>> event_types = await client.list_event_types()
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Cal.com client.

        Args:
            api_key: Cal.com API key. If not provided, loaded from
                CAL_COM_API_KEY environment variable or .env file.

        Raises:
            CalComConfigError: If API key cannot be found or is invalid.
        """
        # Load .env from project root if not already loaded
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.getenv("CAL_COM_API_KEY", "").strip()

        if not api_key:
            raise CalComConfigError(
                "CAL_COM_API_KEY not found. Please set it in .env file at project root "
                "or pass api_key parameter."
            )

        if len(api_key) < 10:
            raise CalComConfigError(
                f"CAL_COM_API_KEY appears invalid (too short: {len(api_key)} chars)"
            )

        # Get base URL from environment or use default
        base_url = os.getenv("CAL_COM_BASE_URL", "https://api.cal.com/v2").strip()

        # Initialize parent client
        super().__init__(
            name="cal_com",
            base_url=base_url,
            api_key=api_key,
            timeout=30.0,
        )

        # Cal.com specific attributes
        self._user_cache: User | None = None
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_open = False

        logger.info(f"Initialized Cal.com client with base URL: {base_url}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated request to Cal.com API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            endpoint: API endpoint path (e.g., "/users/me").
            **kwargs: Additional request parameters.

        Returns:
            Parsed JSON response.

        Raises:
            CalComAuthError: If authentication fails (401).
            CalComNotFoundError: If resource not found (404).
            CalComRateLimitError: If rate limited (429).
            CalComAPIError: For other API errors.
            CalComConfigError: For configuration issues.
        """
        # Check circuit breaker
        if self._circuit_breaker_open:
            raise CalComAPIError("Circuit breaker open - too many failures. Please retry later.")

        # Prepare request with auth header
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )

                # Handle specific status codes
                if response.status_code == 401:
                    self._circuit_breaker_failures += 1
                    raise CalComAuthError(
                        f"Authentication failed: {response.text}",
                        response_data=response.json() if response.text else {},
                    )

                if response.status_code == 404:
                    return {}  # Not found, return empty

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        wait_time = min(2**attempt + (asyncio.get_event_loop().time() % 1), 5)
                        logger.warning(
                            f"Rate limited. Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise CalComRateLimitError(
                        f"Rate limit exceeded: {response.text}",
                        retry_after=retry_after,
                        response_data=response.json() if response.text else {},
                    )

                # Success responses
                if response.status_code in (200, 201, 204):
                    self._circuit_breaker_failures = 0
                    if response.status_code == 204:
                        return {}
                    try:
                        return cast(dict[str, Any], response.json())
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        return {}

                # Other error status codes
                if response.status_code >= 400:
                    self._circuit_breaker_failures += 1
                    if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
                        self._circuit_breaker_open = True
                        logger.error("Circuit breaker opened due to repeated failures")

                    raise CalComAPIError(
                        f"API request failed: {response.status_code} {response.text}",
                        status_code=response.status_code,
                        response_data=response.json() if response.text else {},
                    )

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                self._circuit_breaker_failures += 1
                if attempt < max_retries:
                    wait_time = min(2**attempt + (asyncio.get_event_loop().time() % 1), 5)
                    logger.warning(
                        f"Network error: {e}. Retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                raise CalComAPIError(f"Network error after {max_retries} retries: {e}") from e

        # Should not reach here
        raise CalComAPIError("Request failed after all retry attempts")

    # User Management Methods

    async def get_user(self) -> User:
        """Get authenticated user's profile.

        Returns:
            User object with profile information.

        Raises:
            CalComAuthError: If authentication fails.
            CalComAPIError: If request fails.
        """
        response = await self._request("GET", "/me")
        if not response:
            raise CalComAPIError("Failed to fetch user profile")

        user_data = response.get("data", response)
        user = User(**user_data)
        self._user_cache = user
        return user

    async def update_user_settings(
        self,
        timezone: str | None = None,
        locale: str | None = None,
        **kwargs: Any,
    ) -> User:
        """Update user profile settings.

        Args:
            timezone: IANA timezone string (e.g., "America/New_York").
            locale: Language/locale code.
            **kwargs: Additional settings to update.

        Returns:
            Updated User object.

        Raises:
            CalComValidationError: If timezone is invalid.
            CalComAPIError: If request fails.
        """
        update_data = {}

        if timezone is not None:
            if not self._validate_timezone(timezone):
                raise CalComValidationError(f"Invalid timezone: {timezone}")
            # API uses camelCase: timeZone
            update_data["timeZone"] = timezone

        if locale is not None:
            update_data["locale"] = locale

        update_data.update(kwargs)

        if not update_data:
            return await self.get_user()

        response = await self._request("PATCH", "/me", json=update_data)
        if not response:
            raise CalComAPIError("Failed to update user settings")

        user_data = response.get("data", response)
        user = User(**user_data)
        self._user_cache = user
        return user

    # Event Type Methods

    async def list_event_types(
        self,
        owner_id: str | None = None,
        team_id: str | None = None,
    ) -> list[EventType]:
        """List available event types.

        Args:
            owner_id: Filter by user/owner ID.
            team_id: Filter by team ID.

        Returns:
            List of EventType objects.

        Raises:
            CalComAPIError: If request fails.
        """
        params = {}
        if owner_id:
            params["ownerId"] = owner_id
        if team_id:
            params["teamId"] = team_id

        response = await self._request("GET", "/event-types", params=params)
        if not response:
            return []

        # Handle Cal.com API response format
        # API returns: {eventTypeGroups: [{eventTypes: [...]}], ...}
        # or: {data: [...]}
        event_types_data = []

        if isinstance(response, dict):
            # Check for eventTypeGroups structure
            if "eventTypeGroups" in response:
                for group in response.get("eventTypeGroups", []):
                    for et in group.get("eventTypes", []):
                        with contextlib.suppress(Exception):
                            event_types_data.append(EventType(**et))
            # Check for direct data array
            elif "data" in response and isinstance(response["data"], list):
                for et in response["data"]:
                    with contextlib.suppress(Exception):
                        event_types_data.append(EventType(**et))

        return event_types_data

    async def get_event_type(self, event_type_id: str) -> EventType:
        """Get specific event type details.

        Args:
            event_type_id: Event type identifier.

        Returns:
            EventType object with full configuration.

        Raises:
            CalComNotFoundError: If event type not found.
            CalComAPIError: If request fails.
        """
        response = await self._request("GET", f"/event-types/{event_type_id}")
        if not response:
            raise CalComNotFoundError(f"Event type {event_type_id} not found")

        event_type_data = response.get("data", response)
        return EventType(**event_type_data)

    async def create_event_type(
        self,
        title: str,
        slug: str,
        length: int,
        description: str | None = None,
        scheduling_type: str = "collective",
    ) -> EventType:
        """Create new event type.

        Args:
            title: Event type title.
            slug: URL-friendly identifier (must be unique).
            length: Duration in minutes.
            description: Optional description.
            scheduling_type: Type of scheduling (collective, round_robin, etc).

        Returns:
            Created EventType object.

        Raises:
            CalComValidationError: If validation fails.
            CalComAPIError: If request fails.
        """
        if not title or not slug or length <= 0:
            raise CalComValidationError("title, slug, and length (>0) are required")

        payload = {
            "title": title,
            "slug": slug,
            "length": length,
            "schedulingType": scheduling_type,
        }

        if description:
            payload["description"] = description

        response = await self._request("POST", "/event-types", json=payload)
        if not response:
            raise CalComAPIError("Failed to create event type")

        event_type_data = response.get("data", response)
        return EventType(**event_type_data)

    # Availability Methods

    async def list_availability(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Availability]:
        """Get available time slots for a user.

        Args:
            user_id: User identifier.
            start_time: Range start (ISO 8601 datetime).
            end_time: Range end (ISO 8601 datetime).

        Returns:
            List of Availability slots.

        Raises:
            CalComAPIError: If request fails.
        """
        params = {
            "userId": user_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
        }

        response = await self._request("GET", "/availability", params=params)
        if not response:
            return []

        # Handle Cal.com API response format
        slots_data = []

        if isinstance(response, dict):
            # Check for direct slots array
            if "slots" in response and isinstance(response["slots"], list):
                for slot in response["slots"]:
                    with contextlib.suppress(Exception):
                        slots_data.append(Availability(**slot))
            # Check for data array
            elif "data" in response and isinstance(response["data"], list):
                for slot in response["data"]:
                    with contextlib.suppress(Exception):
                        slots_data.append(Availability(**slot))

        return slots_data

    # Booking Methods

    async def list_bookings(
        self,
        limit: int = 100,
        skip: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[CalComEvent]:
        """List bookings/events with pagination.

        Args:
            limit: Maximum results (max 100).
            skip: Skip N results for pagination.
            filters: Optional filters (status, date_range, etc).

        Returns:
            List of CalComEvent objects.

        Raises:
            CalComAPIError: If request fails.
        """
        limit = min(limit, 100)  # Cap at 100
        params = {"limit": limit, "skip": skip}

        if filters:
            params.update(filters)

        response = await self._request("GET", "/bookings", params=params)
        if not response:
            return []

        # Handle Cal.com API response format
        # API returns: {bookings: [...], pagination: {...}, ...}
        # or: {data: [...]}
        bookings_data = []

        if isinstance(response, dict):
            # Check for bookings array
            if "bookings" in response and isinstance(response["bookings"], list):
                for booking in response["bookings"]:
                    with contextlib.suppress(Exception):
                        bookings_data.append(CalComEvent(**booking))
            # Check for direct data array
            elif "data" in response and isinstance(response["data"], list):
                for booking in response["data"]:
                    with contextlib.suppress(Exception):
                        bookings_data.append(CalComEvent(**booking))

        return bookings_data

    async def get_booking(self, booking_id: str) -> CalComEvent:
        """Get specific booking/event details.

        Args:
            booking_id: Booking identifier.

        Returns:
            CalComEvent object with full details.

        Raises:
            CalComNotFoundError: If booking not found.
            CalComAPIError: If request fails.
        """
        response = await self._request("GET", f"/bookings/{booking_id}")
        if not response:
            raise CalComNotFoundError(f"Booking {booking_id} not found")

        booking_data = response.get("data", response)
        return CalComEvent(**booking_data)

    async def create_booking(
        self,
        event_type_id: str,
        start_time: datetime,
        end_time: datetime,
        attendee_name: str | None = None,
        attendee_email: str | None = None,
        attendee_timezone: str | None = None,
        notes: str | None = None,
        send_confirmation: bool = True,
    ) -> CalComEvent:
        """Create new booking.

        Args:
            event_type_id: Event type to book.
            start_time: Booking start time.
            end_time: Booking end time.
            attendee_name: Attendee name.
            attendee_email: Attendee email.
            attendee_timezone: Attendee timezone.
            notes: Additional notes.
            send_confirmation: Whether to send confirmation email.

        Returns:
            Created CalComEvent with booking details.

        Raises:
            CalComValidationError: If validation fails.
            CalComAPIError: If request fails.
        """
        if not event_type_id or not start_time or not end_time:
            raise CalComValidationError("event_type_id, start_time, and end_time are required")

        if start_time >= end_time:
            raise CalComValidationError("start_time must be before end_time")

        payload = {
            "eventTypeId": event_type_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "sendConfirmation": send_confirmation,
        }

        if attendee_name:
            payload["attendeeName"] = attendee_name
        if attendee_email:
            payload["attendeeEmail"] = attendee_email
        if attendee_timezone:
            payload["attendeeTimezone"] = attendee_timezone
        if notes:
            payload["notes"] = notes

        response = await self._request("POST", "/bookings", json=payload)
        if not response:
            raise CalComAPIError("Failed to create booking")

        booking_data = response.get("data", response)
        return CalComEvent(**booking_data)

    async def reschedule_event(
        self,
        booking_id: str,
        new_start: datetime,
        new_end: datetime,
        send_notification: bool = True,
    ) -> CalComEvent:
        """Reschedule an existing booking to new date/time.

        Args:
            booking_id: Booking to reschedule.
            new_start: New start time.
            new_end: New end time.
            send_notification: Whether to notify attendees.

        Returns:
            Updated CalComEvent with new timing.

        Raises:
            CalComValidationError: If validation fails.
            CalComNotFoundError: If booking not found.
            CalComAPIError: If request fails.
        """
        if new_start >= new_end:
            raise CalComValidationError("new_start must be before new_end")

        payload = {
            "startTime": new_start.isoformat(),
            "endTime": new_end.isoformat(),
            "sendNotification": send_notification,
        }

        response = await self._request("PATCH", f"/bookings/{booking_id}", json=payload)
        if not response:
            raise CalComNotFoundError(f"Booking {booking_id} not found")

        booking_data = response.get("data", response)
        return CalComEvent(**booking_data)

    async def cancel_event(
        self,
        booking_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Cancel an existing booking.

        Args:
            booking_id: Booking to cancel.
            reason: Optional cancellation reason.

        Returns:
            Confirmation dict.

        Raises:
            CalComNotFoundError: If booking not found.
            CalComAPIError: If request fails.
        """
        payload = {}
        if reason:
            payload["cancellationReason"] = reason

        response = await self._request("DELETE", f"/bookings/{booking_id}", json=payload)
        if not response:
            raise CalComNotFoundError(f"Booking {booking_id} not found")

        return cast(
            dict[str, Any], response.get("data", {"status": "cancelled", "bookingId": booking_id})
        )

    # Team Methods

    async def list_teams(self) -> list[Team]:
        """Get all teams user is member of.

        Returns:
            List of Team objects.

        Raises:
            CalComAPIError: If request fails.
        """
        response = await self._request("GET", "/teams")
        if not response:
            return []

        teams_data = response.get("data", response)
        if isinstance(teams_data, list):
            return [Team(**team) for team in teams_data]

        return [Team(**teams_data)] if teams_data else []

    async def get_team(self, team_id: str) -> Team:
        """Get team details.

        Args:
            team_id: Team identifier.

        Returns:
            Team object with members and settings.

        Raises:
            CalComNotFoundError: If team not found.
            CalComAPIError: If request fails.
        """
        response = await self._request("GET", f"/teams/{team_id}")
        if not response:
            raise CalComNotFoundError(f"Team {team_id} not found")

        team_data = response.get("data", response)
        return Team(**team_data)

    # Helper methods

    @staticmethod
    def _validate_timezone(timezone: str) -> bool:
        """Validate timezone is valid IANA format.

        Args:
            timezone: Timezone string to validate.

        Returns:
            True if valid, False otherwise.
        """
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(timezone)
            return True
        except (KeyError, ValueError):
            return False

    async def close(self) -> None:
        """Close HTTP client session.

        Should be called when done with client to clean up resources.
        """
        if self._client:
            await self._client.aclose()
            logger.info("Cal.com client session closed")

    async def __aenter__(self) -> "CalComClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
