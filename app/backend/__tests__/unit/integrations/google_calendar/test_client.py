"""Unit tests for Google Calendar client."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import fixtures
from __tests__.fixtures.google_calendar_fixtures import (
    ERROR_RESPONSES,
    EVENT_CREATE_DATA,
    MOCK_SERVICE_ACCOUNT_CREDENTIALS,
    SAMPLE_RESPONSES,
)
from src.integrations.google_calendar.client import GoogleCalendarClient
from src.integrations.google_calendar.exceptions import (
    GoogleCalendarAPIError,
    GoogleCalendarAuthError,
    GoogleCalendarConfigError,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaExceeded,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)
from src.integrations.google_calendar.models import Calendar, CalendarEvent, CalendarList


class TestGoogleCalendarClientInitialization:
    """Tests for GoogleCalendarClient initialization."""

    def test_init_with_credentials_json(self) -> None:
        """Should initialize with credentials_json parameter."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.name == "google_calendar"
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS
        assert client.access_token is None

    def test_init_with_credentials_str(self) -> None:
        """Should initialize with credentials_str parameter."""
        import json

        creds_str = json.dumps(MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client = GoogleCalendarClient(credentials_str=creds_str)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS

    def test_init_with_access_token(self) -> None:
        """Should initialize with pre-obtained access token."""
        client = GoogleCalendarClient(access_token="test-token-123")
        assert client.access_token == "test-token-123"
        assert client.credentials_json == {}

    def test_init_with_invalid_json_str_raises(self) -> None:
        """Should raise error for invalid JSON string."""
        with pytest.raises(GoogleCalendarConfigError) as exc_info:
            GoogleCalendarClient(credentials_str="not valid json")
        assert "Invalid JSON" in str(exc_info.value)

    def test_init_without_credentials_raises(self) -> None:
        """Should raise error when no credentials provided."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(GoogleCalendarConfigError) as exc_info,
        ):
            GoogleCalendarClient()
        assert "Credentials required" in str(exc_info.value)

    def test_init_validates_service_account_credentials(self) -> None:
        """Should validate service account credentials structure."""
        incomplete_creds = {"type": "service_account", "project_id": "test"}
        with pytest.raises(GoogleCalendarConfigError) as exc_info:
            GoogleCalendarClient(credentials_json=incomplete_creds)
        assert "Missing required credential fields" in str(exc_info.value)

    def test_init_sets_default_timeout(self) -> None:
        """Should set default timeout of 30 seconds."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.timeout == 30.0

    def test_init_sets_default_max_retries(self) -> None:
        """Should set default max_retries of 3."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.max_retries == 3

    def test_init_custom_timeout_and_retries(self) -> None:
        """Should accept custom timeout and retry settings."""
        client = GoogleCalendarClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            timeout=60.0,
            max_retries=5,
            retry_base_delay=2.0,
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0


class TestGoogleCalendarClientAuthentication:
    """Tests for authentication methods."""

    @pytest.fixture
    def client(self) -> GoogleCalendarClient:
        """Create client instance for tests."""
        return GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

    @pytest.mark.asyncio
    async def test_authenticate_service_account_success(self, client: GoogleCalendarClient) -> None:
        """Should authenticate successfully with service account."""
        mock_credentials = MagicMock()
        mock_credentials.token = "test-access-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        assert client.access_token == "test-access-token"

    @pytest.mark.asyncio
    async def test_authenticate_with_access_token_credentials(self) -> None:
        """Should use access token from credentials if provided."""
        creds_with_token = {"access_token": "pre-obtained-token"}
        client = GoogleCalendarClient(credentials_json=creds_with_token)

        await client.authenticate()

        assert client.access_token == "pre-obtained-token"

    @pytest.mark.asyncio
    async def test_authenticate_without_credentials_raises(self) -> None:
        """Should raise error when authenticating without credentials."""
        client = GoogleCalendarClient(access_token="temp-token")
        client.credentials_json = {}

        with pytest.raises(GoogleCalendarAuthError) as exc_info:
            await client.authenticate()
        assert "No credentials provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_headers_requires_authentication(self, client: GoogleCalendarClient) -> None:
        """Should raise error when getting headers without authentication."""
        with pytest.raises(GoogleCalendarAuthError) as exc_info:
            client._get_headers()
        assert "Not authenticated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_headers_returns_bearer_token(self, client: GoogleCalendarClient) -> None:
        """Should return proper Authorization header after authentication."""
        client.access_token = "test-token"
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestGoogleCalendarClientCalendarOperations:
    """Tests for calendar listing and retrieval."""

    @pytest.fixture
    def authenticated_client(self) -> GoogleCalendarClient:
        """Create authenticated client instance."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client.access_token = "test-token"
        return client

    @pytest.mark.asyncio
    async def test_list_calendars_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should list calendars successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = SAMPLE_RESPONSES["calendar_list"]

            calendars = await authenticated_client.list_calendars()

            assert len(calendars) == 2
            assert isinstance(calendars[0], CalendarList)
            assert calendars[0].id == "primary"
            assert calendars[0].access_role == "owner"

    @pytest.mark.asyncio
    async def test_list_calendars_with_pagination(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should handle pagination when listing calendars."""
        page1 = {
            "items": [{"id": "cal-1", "summary": "Cal 1", "accessRole": "owner", "primary": True}],
            "nextPageToken": "token-123",
        }
        page2 = {
            "items": [{"id": "cal-2", "summary": "Cal 2", "accessRole": "writer", "primary": False}]
        }

        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [page1, page2]

            calendars = await authenticated_client.list_calendars()

            assert len(calendars) == 2
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_get_calendar_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should get calendar details successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = SAMPLE_RESPONSES["calendar"]

            calendar = await authenticated_client.get_calendar("primary")

            assert isinstance(calendar, Calendar)
            assert calendar.id == "primary"
            assert calendar.summary == "Test Calendar"

    @pytest.mark.asyncio
    async def test_get_calendar_not_found(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should raise NotFoundError for non-existent calendar."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = GoogleCalendarNotFoundError(
                resource_type="calendar", resource_id="non-existent"
            )

            with pytest.raises(GoogleCalendarNotFoundError) as exc_info:
                await authenticated_client.get_calendar("non-existent")
            assert "calendar" in str(exc_info.value).lower()


class TestGoogleCalendarClientEventOperations:
    """Tests for event CRUD operations."""

    @pytest.fixture
    def authenticated_client(self) -> GoogleCalendarClient:
        """Create authenticated client instance."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client.access_token = "test-token"
        return client

    @pytest.mark.asyncio
    async def test_list_events_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should list events successfully."""
        # Create response without nextPageToken to avoid pagination loop
        event_list_response = {
            "kind": "calendar#events",
            "summary": "Primary Calendar",
            "timeZone": "America/New_York",
            "items": SAMPLE_RESPONSES["event_list"]["items"],
            # No nextPageToken - single page result
        }

        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = event_list_response

            events = await authenticated_client.list_events(calendar_id="primary")

            assert len(events) == 2
            assert isinstance(events[0], CalendarEvent)
            assert events[0].id == "event-1"

    @pytest.mark.asyncio
    async def test_list_events_with_date_range(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should filter events by date range."""
        now = datetime.now(UTC)
        time_min = now
        time_max = now + timedelta(days=7)

        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"items": []}

            await authenticated_client.list_events(
                calendar_id="primary", time_min=time_min, time_max=time_max
            )

            # Verify params include time filters
            call_args = mock_request.call_args
            assert "params" in call_args.kwargs
            params = call_args.kwargs["params"]
            assert "timeMin" in params
            assert "timeMax" in params

    @pytest.mark.asyncio
    async def test_list_events_with_search_query(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should filter events by search query."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"items": []}

            await authenticated_client.list_events(calendar_id="primary", query="meeting")

            call_args = mock_request.call_args
            params = call_args.kwargs["params"]
            assert params.get("q") == "meeting"

    @pytest.mark.asyncio
    async def test_get_event_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should get event details successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = SAMPLE_RESPONSES["event"]

            event = await authenticated_client.get_event("primary", "event-abc-123")

            assert isinstance(event, CalendarEvent)
            assert event.id == "event-abc-123"
            assert event.summary == "Test Meeting"

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should raise NotFoundError for non-existent event."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = GoogleCalendarNotFoundError(
                resource_type="event", resource_id="non-existent"
            )

            with pytest.raises(GoogleCalendarNotFoundError) as exc_info:
                await authenticated_client.get_event("primary", "non-existent")
            assert "event" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_event_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should create event successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = SAMPLE_RESPONSES["event"]

            event = await authenticated_client.create_event(
                calendar_id="primary", event=EVENT_CREATE_DATA["valid_event"]
            )

            assert isinstance(event, CalendarEvent)
            assert event.id == "event-abc-123"

    @pytest.mark.asyncio
    async def test_create_event_validates_times(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should validate that start time is before end time."""
        now = datetime.now(UTC)
        invalid_event = {
            "summary": "Invalid Event",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now - timedelta(hours=1)).isoformat()},
        }

        with pytest.raises(GoogleCalendarValidationError) as exc_info:
            await authenticated_client.create_event(calendar_id="primary", event=invalid_event)
        assert "start time must be before end time" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_event_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should update event successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                **SAMPLE_RESPONSES["event"],
                "summary": "Updated Meeting",
            }

            event = await authenticated_client.update_event(
                calendar_id="primary",
                event_id="event-abc-123",
                event={"summary": "Updated Meeting"},
            )

            assert event.summary == "Updated Meeting"

    @pytest.mark.asyncio
    async def test_delete_event_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should delete event successfully."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {}

            # Should not raise
            await authenticated_client.delete_event(calendar_id="primary", event_id="event-abc-123")

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_quick_add_event_success(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should create event from natural language."""
        with patch.object(
            authenticated_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = SAMPLE_RESPONSES["quick_add_event"]

            event = await authenticated_client.quick_add_event(
                calendar_id="primary", text="Meeting tomorrow at 2pm"
            )

            assert isinstance(event, CalendarEvent)
            assert event.id == "quick-add-789"

    @pytest.mark.asyncio
    async def test_quick_add_event_empty_text_raises(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should raise validation error for empty text."""
        with pytest.raises(GoogleCalendarValidationError) as exc_info:
            await authenticated_client.quick_add_event(calendar_id="primary", text="")
        assert "cannot be empty" in str(exc_info.value).lower()


class TestGoogleCalendarClientErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.fixture
    def authenticated_client(self) -> GoogleCalendarClient:
        """Create authenticated client instance."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client.access_token = "test-token"
        return client

    @pytest.mark.asyncio
    async def test_handles_401_error(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should raise AuthError for 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = ERROR_RESPONSES["unauthorized"]

        # Force client initialization, then patch its request method
        _ = authenticated_client.client
        with patch.object(
            authenticated_client._client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(GoogleCalendarAuthError):
                await authenticated_client.list_calendars()

    @pytest.mark.asyncio
    async def test_handles_404_error(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should raise NotFoundError for 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = ERROR_RESPONSES["not_found"]

        # Force client initialization, then patch its request method
        _ = authenticated_client.client
        with patch.object(
            authenticated_client._client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(GoogleCalendarNotFoundError):
                await authenticated_client.get_calendar("non-existent")

    @pytest.mark.asyncio
    async def test_handles_429_rate_limit(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should raise RateLimitError for 429 response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = ERROR_RESPONSES["rate_limited"]

        # Force client initialization, then patch its request method
        _ = authenticated_client.client
        with patch.object(
            authenticated_client._client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(GoogleCalendarRateLimitError) as exc_info:
                await authenticated_client.list_calendars()
            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_handles_403_quota_exceeded(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should raise QuotaExceeded for quota-related 403 response."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = ERROR_RESPONSES["quota_exceeded"]

        # Force client initialization, then patch its request method
        _ = authenticated_client.client
        with patch.object(
            authenticated_client._client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(GoogleCalendarQuotaExceeded):
                await authenticated_client.list_calendars()


class TestGoogleCalendarClientHealthCheck:
    """Tests for health check functionality."""

    @pytest.fixture
    def authenticated_client(self) -> GoogleCalendarClient:
        """Create authenticated client instance."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client.access_token = "test-token"
        return client

    @pytest.mark.asyncio
    async def test_health_check_success(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should return healthy status when API is accessible."""
        with patch.object(
            authenticated_client, "list_calendars", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            result = await authenticated_client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "google_calendar"

    @pytest.mark.asyncio
    async def test_health_check_not_authenticated(self) -> None:
        """Should return unhealthy status when not authenticated."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        # Not calling authenticate()

        result = await client.health_check()

        assert result["healthy"] is False
        assert "Not authenticated" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_api_error(self, authenticated_client: GoogleCalendarClient) -> None:
        """Should return unhealthy status on API error."""
        with patch.object(
            authenticated_client, "list_calendars", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = GoogleCalendarAPIError("API error")

            result = await authenticated_client.health_check()

            assert result["healthy"] is False


class TestGoogleCalendarClientContextManager:
    """Tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close HTTP client when exiting context."""
        async with GoogleCalendarClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS
        ) as client:
            # Access the client to initialize it
            _ = client.client

        assert client._client is None or client._client.is_closed

    @pytest.mark.asyncio
    async def test_close_handles_none_client(self) -> None:
        """Should handle closing when client was never initialized."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        await client.close()  # Should not raise


class TestGoogleCalendarClientValidation:
    """Tests for input validation."""

    @pytest.fixture
    def authenticated_client(self) -> GoogleCalendarClient:
        """Create authenticated client instance."""
        client = GoogleCalendarClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client.access_token = "test-token"
        return client

    def test_validate_event_times_missing_start(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should raise validation error for missing start time."""
        event_data = {"end": {"dateTime": "2025-12-25T10:00:00Z"}}

        with pytest.raises(GoogleCalendarValidationError) as exc_info:
            authenticated_client._validate_event_times(event_data)
        assert "start time is required" in str(exc_info.value).lower()

    def test_validate_event_times_missing_end(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should raise validation error for missing end time."""
        event_data = {"start": {"dateTime": "2025-12-25T10:00:00Z"}}

        with pytest.raises(GoogleCalendarValidationError) as exc_info:
            authenticated_client._validate_event_times(event_data)
        assert "end time is required" in str(exc_info.value).lower()

    def test_validate_event_times_invalid_format(
        self, authenticated_client: GoogleCalendarClient
    ) -> None:
        """Should raise validation error for invalid datetime format."""
        event_data = {
            "start": {"dateTime": "not-a-date"},
            "end": {"dateTime": "2025-12-25T10:00:00Z"},
        }

        with pytest.raises(GoogleCalendarValidationError) as exc_info:
            authenticated_client._validate_event_times(event_data)
        assert "invalid datetime format" in str(exc_info.value).lower()
