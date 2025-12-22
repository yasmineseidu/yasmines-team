"""
Google Calendar API integration client for event and calendar management.

Provides async access to Google Calendar REST API v3 including:
- OAuth2 service account authentication
- Calendar listing and management
- Event CRUD operations (create, read, update, delete)
- Quick add events from natural language
- Comprehensive error handling and retry logic

Rate Limits (per user):
- 1,000,000 queries per day
- 1,000 requests per 100 seconds per user
- 429 = Too many requests (rate limited)
- 403 = Quota exceeded or permission denied

Example:
    >>> from src.integrations.google_calendar.client import GoogleCalendarClient
    >>> client = GoogleCalendarClient(credentials_json={...})
    >>> await client.authenticate()
    >>> calendars = await client.list_calendars()
    >>> events = await client.list_events(calendar_id="primary")
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import Any, cast

import httpx

from src.integrations.google_calendar.exceptions import (
    GoogleCalendarAPIError,
    GoogleCalendarAuthError,
    GoogleCalendarConfigError,
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaExceeded,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)
from src.integrations.google_calendar.models import (
    Calendar,
    CalendarEvent,
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarList,
    CalendarListResponse,
    EventsListResponse,
)

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    Async client for Google Calendar API v3.

    Supports calendar listing, event CRUD operations, and quick add
    with comprehensive error handling and exponential backoff retry logic.

    Attributes:
        credentials_json: OAuth2 service account credentials
        access_token: Current OAuth2 access token
        scopes: OAuth2 scopes for Calendar access
    """

    # Google Calendar API endpoints
    CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # Required OAuth2 scopes
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        credentials_path: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize Google Calendar client.

        Args:
            credentials_json: OAuth2 service account credentials as dict
            credentials_str: OAuth2 service account credentials as JSON string
            credentials_path: Path to service account credentials JSON file
            access_token: Pre-obtained OAuth2 access token (optional)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)

        Raises:
            GoogleCalendarConfigError: If credentials are invalid or missing
        """
        # Load credentials from various sources
        if credentials_str and not credentials_json:
            try:
                credentials_json = json.loads(credentials_str)
            except json.JSONDecodeError as e:
                raise GoogleCalendarConfigError(f"Invalid JSON in credentials string: {e}") from e

        if credentials_path and not credentials_json:
            credentials_json = self._load_credentials_from_path(credentials_path)

        if not credentials_json and not access_token:
            # Try to load from environment variable
            env_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
            if env_path:
                credentials_json = self._load_credentials_from_path(env_path)
            else:
                raise GoogleCalendarConfigError(
                    "Credentials required. Provide credentials_json, credentials_str, "
                    "credentials_path, or set GOOGLE_CALENDAR_CREDENTIALS_JSON environment variable."
                )

        self.name = "google_calendar"
        self.base_url = self.CALENDAR_API_BASE
        self.credentials_json = credentials_json or {}
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None
        self.scopes = self.DEFAULT_SCOPES

        # Validate credentials structure if provided
        if self.credentials_json:
            self._validate_credentials(self.credentials_json)

        logger.info("Initialized Google Calendar client")

    def _load_credentials_from_path(self, path: str) -> dict[str, Any]:
        """
        Load credentials from a file path.

        Supports both absolute and relative paths.

        Args:
            path: Path to the credentials JSON file

        Returns:
            Parsed credentials dictionary

        Raises:
            GoogleCalendarConfigError: If file not found or invalid JSON
        """
        # Handle relative paths - try relative to project root if not found
        if not os.path.isabs(path) and not os.path.exists(path):
            # Try relative to project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            )
            path = os.path.join(project_root, path)

        if not os.path.exists(path):
            raise GoogleCalendarConfigError(f"Credentials file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                credentials = json.load(f)
            logger.info(f"Loaded credentials from: {path}")
            return cast(dict[str, Any], credentials)
        except json.JSONDecodeError as e:
            raise GoogleCalendarConfigError(f"Invalid JSON in credentials file: {e}") from e
        except OSError as e:
            raise GoogleCalendarConfigError(f"Failed to read credentials file: {e}") from e

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate service account credentials structure.

        Args:
            credentials: Credentials dictionary to validate

        Raises:
            GoogleCalendarConfigError: If required fields are missing
        """
        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
        ]

        if credentials.get("type") != "service_account":
            logger.warning(
                "Credentials type is not 'service_account'. "
                "Some authentication flows may not work."
            )
            return

        missing = [f for f in required_fields if f not in credentials]
        if missing:
            raise GoogleCalendarConfigError(
                f"Missing required credential fields: {', '.join(missing)}"
            )

        logger.debug("Credentials validation passed")

    @property
    def client(self) -> httpx.AsyncClient:
        """
        Lazy HTTP client creation with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """
        Get request headers with OAuth2 bearer token.

        Returns:
            Dictionary with Authorization and Content-Type headers

        Raises:
            GoogleCalendarAuthError: If not authenticated
        """
        if not self.access_token:
            raise GoogleCalendarAuthError("Not authenticated. Call authenticate() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def authenticate(self) -> None:
        """
        Authenticate with Google using service account credentials.

        Obtains OAuth2 access token using JWT flow for service accounts.

        Raises:
            GoogleCalendarAuthError: If authentication fails
        """
        try:
            if not self.credentials_json:
                raise GoogleCalendarAuthError("No credentials provided")

            cred_type = self.credentials_json.get("type")

            if cred_type == "service_account":
                await self._authenticate_service_account()
            elif "access_token" in self.credentials_json:
                self.access_token = self.credentials_json["access_token"]
            else:
                raise GoogleCalendarAuthError(
                    f"Unsupported credential type: {cred_type}. "
                    "Expected 'service_account' or credentials with access_token."
                )

            logger.info("Successfully authenticated with Google Calendar API")

        except GoogleCalendarAuthError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleCalendarAuthError(f"Failed to authenticate: {e}") from e

    async def _authenticate_service_account(self) -> None:
        """
        Authenticate using service account credentials.

        Implements JWT bearer token flow for service account authentication.

        Raises:
            GoogleCalendarAuthError: If JWT generation or token exchange fails
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            # Create credentials from service account JSON
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_json,
                scopes=self.DEFAULT_SCOPES,
            )

            # Refresh to get access token
            request = Request()
            credentials.refresh(request)
            self.access_token = credentials.token

            logger.info("Service account authenticated successfully")

        except ImportError as e:
            raise GoogleCalendarAuthError(
                "google-auth library required for service account authentication. "
                "Install with: pip install google-auth"
            ) from e
        except Exception as e:
            raise GoogleCalendarAuthError(f"Service account auth failed: {e}") from e

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Implements truncated exponential backoff with jitter for rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: Full URL for the request
            headers: Custom headers (merged with default headers)
            **kwargs: Additional arguments for httpx request

        Returns:
            Parsed JSON response

        Raises:
            GoogleCalendarAPIError: After all retries exhausted
            GoogleCalendarNotFoundError: If resource not found (404)
            GoogleCalendarAuthError: If authentication fails (401)
            GoogleCalendarQuotaExceeded: If quota exceeded (403)
            GoogleCalendarRateLimitError: If rate limited (429)
        """
        if headers is None:
            headers = {}
        headers.update(self._get_headers())

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )

                # Handle response
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_response": response.text}

                # Handle specific HTTP status codes
                if response.status_code == 401:
                    raise GoogleCalendarAuthError(
                        f"Authentication failed: {data.get('error', {}).get('message', 'Unknown')}"
                    )

                if response.status_code == 403:
                    error_msg = data.get("error", {})
                    if isinstance(error_msg, dict):
                        error_reason = error_msg.get("message", "")
                    else:
                        error_reason = str(error_msg)

                    if "quota" in error_reason.lower() or "limit" in error_reason.lower():
                        raise GoogleCalendarQuotaExceeded(f"Quota exceeded: {error_reason}")
                    raise GoogleCalendarAPIError(
                        f"Permission denied: {error_reason}", status_code=403
                    )

                if response.status_code == 404:
                    error_msg = data.get("error", {}).get("message", "Resource not found")
                    raise GoogleCalendarNotFoundError(message=error_msg)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise GoogleCalendarRateLimitError(
                        message=f"Rate limited: {data.get('error', 'Too many requests')}",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    error_msg = data.get("error", {})
                    if isinstance(error_msg, dict):
                        error_message = error_msg.get("message", "Unknown error")
                    else:
                        error_message = str(error_msg)
                    raise GoogleCalendarAPIError(
                        f"API error ({response.status_code}): {error_message}",
                        status_code=response.status_code,
                    )

                return cast(dict[str, Any], data)

            except (
                GoogleCalendarAuthError,
                GoogleCalendarNotFoundError,
                GoogleCalendarQuotaExceeded,
            ):
                # Don't retry auth, not found, or quota errors
                raise
            except Exception as error:
                last_error = error

                # Check if retryable
                is_retryable = isinstance(
                    error,
                    httpx.TimeoutException | httpx.NetworkError | GoogleCalendarRateLimitError,
                )

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[google_calendar] Request failed: {error}",
                        extra={
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Exponential backoff with jitter
                delay = self.retry_base_delay * (2**attempt)
                jitter = random.uniform(0, delay * 0.1)  # 0-10% jitter
                delay += jitter

                logger.warning(
                    f"[google_calendar] Request failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {error}",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "delay": delay,
                    },
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise GoogleCalendarAPIError(f"Request failed after {self.max_retries} retries")

    # =========================================================================
    # Calendar List Operations
    # =========================================================================

    async def list_calendars(
        self,
        page_size: int = 100,
        page_token: str | None = None,
        show_deleted: bool = False,
        show_hidden: bool = False,
    ) -> list[CalendarList]:
        """
        List all calendars accessible by the service account.

        Args:
            page_size: Number of calendars to return per page (max 250)
            page_token: Token for pagination
            show_deleted: Include deleted calendars
            show_hidden: Include hidden calendars

        Returns:
            List of CalendarList objects

        Raises:
            GoogleCalendarAPIError: If request fails
        """
        try:
            params: dict[str, Any] = {
                "maxResults": min(page_size, 250),
                "showDeleted": str(show_deleted).lower(),
                "showHidden": str(show_hidden).lower(),
            }

            if page_token:
                params["pageToken"] = page_token

            calendars: list[CalendarList] = []
            next_token = page_token

            # Handle pagination to get all calendars
            while True:
                if next_token:
                    params["pageToken"] = next_token

                response = await self._request_with_retry(
                    "GET",
                    f"{self.CALENDAR_API_BASE}/users/me/calendarList",
                    params=params,
                )

                parsed = CalendarListResponse(**response)
                calendars.extend(parsed.items)

                next_token = parsed.next_page_token
                if not next_token:
                    break

            logger.info(f"Listed {len(calendars)} calendars")
            return calendars

        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            raise GoogleCalendarAPIError(f"Failed to list calendars: {e}") from e

    async def get_calendar(self, calendar_id: str) -> Calendar:
        """
        Get details of a specific calendar.

        Args:
            calendar_id: Calendar ID or 'primary' for the primary calendar

        Returns:
            Calendar object with full details

        Raises:
            GoogleCalendarNotFoundError: If calendar not found
            GoogleCalendarAPIError: If request fails
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}",
            )

            logger.info(f"Retrieved calendar: {calendar_id}")
            return Calendar(**response)

        except GoogleCalendarNotFoundError:
            raise GoogleCalendarNotFoundError(
                resource_type="calendar", resource_id=calendar_id
            ) from None
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to get calendar: {e}")
            raise GoogleCalendarAPIError(f"Failed to get calendar: {e}") from e

    # =========================================================================
    # Event Operations
    # =========================================================================

    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 100,
        page_token: str | None = None,
        query: str | None = None,
        order_by: str = "startTime",
        single_events: bool = True,
        show_deleted: bool = False,
    ) -> list[CalendarEvent]:
        """
        List events from a calendar.

        Args:
            calendar_id: Calendar ID or 'primary' (default)
            time_min: Lower bound for event start time
            time_max: Upper bound for event start time
            max_results: Maximum events to return (max 2500)
            page_token: Token for pagination
            query: Free-text search query
            order_by: Order by 'startTime' or 'updated'
            single_events: Expand recurring events (required for orderBy)
            show_deleted: Include cancelled events

        Returns:
            List of CalendarEvent objects

        Raises:
            GoogleCalendarAPIError: If request fails
            GoogleCalendarNotFoundError: If calendar not found
        """
        try:
            params: dict[str, Any] = {
                "maxResults": min(max_results, 2500),
                "orderBy": order_by,
                "singleEvents": str(single_events).lower(),
                "showDeleted": str(show_deleted).lower(),
            }

            if time_min:
                params["timeMin"] = time_min.isoformat() + "Z"
            if time_max:
                params["timeMax"] = time_max.isoformat() + "Z"
            if query:
                params["q"] = query
            if page_token:
                params["pageToken"] = page_token

            events: list[CalendarEvent] = []
            next_token = page_token

            # Handle pagination
            while True:
                if next_token:
                    params["pageToken"] = next_token

                response = await self._request_with_retry(
                    "GET",
                    f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                    params=params,
                )

                parsed = EventsListResponse(**response)
                events.extend(parsed.items)

                next_token = parsed.next_page_token
                if not next_token or len(events) >= max_results:
                    break

            logger.info(f"Listed {len(events)} events from calendar: {calendar_id}")
            return events[:max_results]

        except GoogleCalendarNotFoundError:
            raise GoogleCalendarNotFoundError(
                resource_type="calendar", resource_id=calendar_id
            ) from None
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            raise GoogleCalendarAPIError(f"Failed to list events: {e}") from e

    async def get_event(
        self,
        calendar_id: str,
        event_id: str,
    ) -> CalendarEvent:
        """
        Get details of a specific event.

        Args:
            calendar_id: Calendar ID or 'primary'
            event_id: Event ID

        Returns:
            CalendarEvent object with full details

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarAPIError: If request fails
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            )

            logger.info(f"Retrieved event: {event_id}")
            return CalendarEvent(**response)

        except GoogleCalendarNotFoundError:
            raise GoogleCalendarNotFoundError(resource_type="event", resource_id=event_id) from None
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to get event: {e}")
            raise GoogleCalendarAPIError(f"Failed to get event: {e}") from e

    async def create_event(
        self,
        calendar_id: str,
        event: CalendarEventCreate | dict[str, Any],
        send_notifications: bool = True,
    ) -> CalendarEvent:
        """
        Create a new event in a calendar.

        Args:
            calendar_id: Calendar ID or 'primary'
            event: Event data (CalendarEventCreate or dict)
            send_notifications: Send notifications to attendees

        Returns:
            Created CalendarEvent with generated ID

        Raises:
            GoogleCalendarValidationError: If event data is invalid
            GoogleCalendarAPIError: If request fails
        """
        try:
            # Convert to dict if needed
            if isinstance(event, CalendarEventCreate):
                event_data = event.model_dump(by_alias=True, exclude_none=True)
            else:
                event_data = event

            # Validate start/end times
            self._validate_event_times(event_data)

            # Convert attendees list of emails to proper format
            if (
                "attendees" in event_data
                and isinstance(event_data["attendees"], list)
                and event_data["attendees"]
                and isinstance(event_data["attendees"][0], str)
            ):
                event_data["attendees"] = [{"email": email} for email in event_data["attendees"]]

            params = {"sendNotifications": str(send_notifications).lower()}

            response = await self._request_with_retry(
                "POST",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                params=params,
                json=event_data,
            )

            created_event = CalendarEvent(**response)
            logger.info(f"Created event: {created_event.id}")
            return created_event

        except GoogleCalendarValidationError:
            raise
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise GoogleCalendarAPIError(f"Failed to create event: {e}") from e

    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: CalendarEventUpdate | dict[str, Any],
        send_notifications: bool = True,
    ) -> CalendarEvent:
        """
        Update an existing event.

        Supports partial updates - only provided fields will be updated.

        Args:
            calendar_id: Calendar ID or 'primary'
            event_id: Event ID to update
            event: Updated event data
            send_notifications: Send notifications to attendees

        Returns:
            Updated CalendarEvent

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarValidationError: If event data is invalid
            GoogleCalendarAPIError: If request fails
        """
        try:
            # Convert to dict if needed
            if isinstance(event, CalendarEventUpdate):
                event_data = event.model_dump(by_alias=True, exclude_none=True)
            else:
                event_data = {k: v for k, v in event.items() if v is not None}

            # Validate times if both start and end are provided
            if "start" in event_data or "end" in event_data:
                # Get existing event to merge times if needed
                if "start" not in event_data or "end" not in event_data:
                    existing = await self.get_event(calendar_id, event_id)
                    if "start" not in event_data:
                        event_data["start"] = existing.start.model_dump(by_alias=True)
                    if "end" not in event_data:
                        event_data["end"] = existing.end.model_dump(by_alias=True)

                self._validate_event_times(event_data)

            # Convert attendees list of emails to proper format
            if (
                "attendees" in event_data
                and isinstance(event_data["attendees"], list)
                and event_data["attendees"]
                and isinstance(event_data["attendees"][0], str)
            ):
                event_data["attendees"] = [{"email": email} for email in event_data["attendees"]]

            params = {"sendNotifications": str(send_notifications).lower()}

            response = await self._request_with_retry(
                "PATCH",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                params=params,
                json=event_data,
            )

            updated_event = CalendarEvent(**response)
            logger.info(f"Updated event: {event_id}")
            return updated_event

        except GoogleCalendarNotFoundError:
            raise GoogleCalendarNotFoundError(resource_type="event", resource_id=event_id) from None
        except GoogleCalendarValidationError:
            raise
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            raise GoogleCalendarAPIError(f"Failed to update event: {e}") from e

    async def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        send_notifications: bool = True,
    ) -> None:
        """
        Delete an event from a calendar.

        Args:
            calendar_id: Calendar ID or 'primary'
            event_id: Event ID to delete
            send_notifications: Send cancellation notices to attendees

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarAPIError: If request fails
        """
        try:
            params = {"sendNotifications": str(send_notifications).lower()}

            await self._request_with_retry(
                "DELETE",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                params=params,
            )

            logger.info(f"Deleted event: {event_id}")

        except GoogleCalendarNotFoundError:
            raise GoogleCalendarNotFoundError(resource_type="event", resource_id=event_id) from None
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            raise GoogleCalendarAPIError(f"Failed to delete event: {e}") from e

    async def quick_add_event(
        self,
        calendar_id: str,
        text: str,
        send_notifications: bool = True,
    ) -> CalendarEvent:
        """
        Create an event from natural language text.

        Google Calendar parses the text to extract event details.
        Examples:
        - "Meeting tomorrow at 2pm"
        - "Lunch with John next Tuesday at noon for 1 hour"
        - "All-day event next Friday"

        Args:
            calendar_id: Calendar ID or 'primary'
            text: Natural language event description
            send_notifications: Send notifications to attendees

        Returns:
            Created CalendarEvent

        Raises:
            GoogleCalendarValidationError: If text cannot be parsed
            GoogleCalendarAPIError: If request fails
        """
        try:
            if not text or not text.strip():
                raise GoogleCalendarValidationError("Event text cannot be empty", field="text")

            params = {
                "text": text.strip(),
                "sendNotifications": str(send_notifications).lower(),
            }

            response = await self._request_with_retry(
                "POST",
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/quickAdd",
                params=params,
            )

            created_event = CalendarEvent(**response)
            logger.info(f"Quick-added event: {created_event.id} from text: {text[:50]}...")
            return created_event

        except GoogleCalendarValidationError:
            raise
        except GoogleCalendarError:
            raise
        except Exception as e:
            logger.error(f"Failed to quick-add event: {e}")
            raise GoogleCalendarAPIError(f"Failed to quick-add event: {e}") from e

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_event_times(self, event_data: dict[str, Any]) -> None:
        """
        Validate that event start time is before end time.

        Args:
            event_data: Event data dictionary

        Raises:
            GoogleCalendarValidationError: If times are invalid
        """
        start = event_data.get("start", {})
        end = event_data.get("end", {})

        start_dt = start.get("dateTime") or start.get("date")
        end_dt = end.get("dateTime") or end.get("date")

        if not start_dt:
            raise GoogleCalendarValidationError("Event start time is required", field="start")
        if not end_dt:
            raise GoogleCalendarValidationError("Event end time is required", field="end")

        # Parse and compare times
        try:
            if isinstance(start_dt, str):
                start_parsed = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            else:
                start_parsed = start_dt

            if isinstance(end_dt, str):
                end_parsed = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
            else:
                end_parsed = end_dt

            if start_parsed >= end_parsed:
                raise GoogleCalendarValidationError(
                    "Event start time must be before end time", field="start"
                )
        except ValueError as e:
            raise GoogleCalendarValidationError(
                f"Invalid datetime format: {e}", field="start"
            ) from e

    # =========================================================================
    # Health Check & Cleanup
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check Google Calendar API connectivity and authentication.

        Returns:
            Health check status dict

        Raises:
            GoogleCalendarAPIError: If health check fails
        """
        try:
            if not self.access_token:
                return {
                    "name": "google_calendar",
                    "healthy": False,
                    "message": "Not authenticated",
                }

            # Simple list call to verify auth
            await self.list_calendars(page_size=1)

            return {
                "name": "google_calendar",
                "healthy": True,
                "message": "Google Calendar API is accessible",
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "name": "google_calendar",
                "healthy": False,
                "message": f"Health check failed: {e}",
            }

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("[google_calendar] HTTP client closed")

    async def __aenter__(self) -> "GoogleCalendarClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        await self.close()
