"""Unit tests for Cal.com client."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.cal_com.client import CalComClient
from src.integrations.cal_com.exceptions import (
    CalComAPIError,
    CalComAuthError,
    CalComConfigError,
    CalComNotFoundError,
    CalComRateLimitError,
    CalComValidationError,
)


class TestCalComClientInitialization:
    """Test client initialization and configuration."""

    def test_init_with_api_key_parameter(self) -> None:
        """Test initialization with API key parameter."""
        client = CalComClient(api_key="test_key_123")
        assert client.name == "cal_com"
        assert client.api_key == "test_key_123"
        assert client.base_url == "https://api.cal.com/v2"

    def test_init_without_api_key_raises_error(self) -> None:
        """Test initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CalComConfigError, match="CAL_COM_API_KEY not found"):
                CalComClient()

    def test_init_with_invalid_api_key_raises_error(self) -> None:
        """Test initialization with too-short API key raises error."""
        with pytest.raises(CalComConfigError, match="appears invalid"):
            CalComClient(api_key="short")

    def test_init_with_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        with patch.dict("os.environ", {"CAL_COM_BASE_URL": "https://custom.cal.com/v1"}):
            client = CalComClient(api_key="test_key_123")
            assert client.base_url == "https://custom.cal.com/v1"

    @pytest.mark.asyncio
    async def test_context_manager_usage(self) -> None:
        """Test using client as async context manager."""
        async with CalComClient(api_key="test_key_123") as client:
            assert isinstance(client, CalComClient)


class TestCalComClientUserMethods:
    """Test user-related methods."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_get_user_success(self, client: CalComClient) -> None:
        """Test successful get_user request."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "user_123",
                "email": "test@example.com",
                "name": "Test User",
                "username": "testuser",
                "timezone": "UTC",
                "locale": "en-US",
                "created_at": "2024-01-01T00:00:00Z",
            }

            user = await client.get_user()

            assert user.id == "user_123"
            assert user.email == "test@example.com"
            assert user.name == "Test User"
            mock_request.assert_called_once_with("GET", "/users/me")

    @pytest.mark.asyncio
    async def test_get_user_failure(self, client: CalComClient) -> None:
        """Test get_user with API error."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            with pytest.raises(CalComAPIError):
                await client.get_user()

    @pytest.mark.asyncio
    async def test_update_user_settings_timezone(self, client: CalComClient) -> None:
        """Test updating user timezone."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "user_123",
                "email": "test@example.com",
                "name": "Test User",
                "username": "testuser",
                "timezone": "America/New_York",
                "locale": "en-US",
                "created_at": "2024-01-01T00:00:00Z",
            }

            user = await client.update_user_settings(timezone="America/New_York")

            assert user.timezone == "America/New_York"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_settings_invalid_timezone(self, client: CalComClient) -> None:
        """Test update with invalid timezone."""
        with pytest.raises(CalComValidationError, match="Invalid timezone"):
            await client.update_user_settings(timezone="Invalid/Timezone")


class TestCalComClientEventTypeMethods:
    """Test event type methods."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_list_event_types_success(self, client: CalComClient) -> None:
        """Test listing event types."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {
                    "id": "evt_1",
                    "title": "1:1",
                    "slug": "1-1",
                    "length": 30,
                    "owner_id": "user_123",
                    "is_active": True,
                    "scheduling_type": "collective",
                },
                {
                    "id": "evt_2",
                    "title": "Group",
                    "slug": "group",
                    "length": 60,
                    "owner_id": "user_123",
                    "is_active": True,
                    "scheduling_type": "round_robin",
                },
            ]

            event_types = await client.list_event_types()

            assert len(event_types) == 2
            assert event_types[0].title == "1:1"
            assert event_types[1].title == "Group"

    @pytest.mark.asyncio
    async def test_get_event_type_success(self, client: CalComClient) -> None:
        """Test getting specific event type."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "evt_123",
                "title": "1:1 Meeting",
                "slug": "1-1-meeting",
                "description": "One-on-one",
                "length": 30,
                "owner_id": "user_123",
                "is_active": True,
                "scheduling_type": "collective",
            }

            event_type = await client.get_event_type("evt_123")

            assert event_type.id == "evt_123"
            assert event_type.length == 30

    @pytest.mark.asyncio
    async def test_get_event_type_not_found(self, client: CalComClient) -> None:
        """Test get event type when not found."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            with pytest.raises(CalComNotFoundError):
                await client.get_event_type("evt_999")

    @pytest.mark.asyncio
    async def test_create_event_type_success(self, client: CalComClient) -> None:
        """Test creating event type."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "evt_new",
                "title": "New Event",
                "slug": "new-event",
                "length": 45,
                "owner_id": "user_123",
                "is_active": True,
                "scheduling_type": "collective",
            }

            event_type = await client.create_event_type(
                title="New Event",
                slug="new-event",
                length=45,
            )

            assert event_type.id == "evt_new"
            assert event_type.title == "New Event"

    @pytest.mark.asyncio
    async def test_create_event_type_validation_error(self, client: CalComClient) -> None:
        """Test create event type with invalid data."""
        with pytest.raises(CalComValidationError):
            await client.create_event_type(
                title="",
                slug="event",
                length=30,
            )

        with pytest.raises(CalComValidationError):
            await client.create_event_type(
                title="Event",
                slug="event",
                length=0,
            )


class TestCalComClientAvailabilityMethods:
    """Test availability-related methods."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_list_availability_success(self, client: CalComClient) -> None:
        """Test listing availability slots."""
        now = datetime.now()
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {
                    "user_id": "user_123",
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=1)).isoformat(),
                    "is_available": True,
                },
            ]

            availability = await client.list_availability(
                "user_123",
                now,
                now + timedelta(days=7),
            )

            assert len(availability) == 1
            assert availability[0].is_available


class TestCalComClientBookingMethods:
    """Test booking-related methods."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_list_bookings_success(self, client: CalComClient) -> None:
        """Test listing bookings."""
        now = datetime.now()
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {
                    "id": "booking_1",
                    "title": "Meeting",
                    "description": "Team sync",
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=1)).isoformat(),
                    "location": "Zoom",
                    "organizer_id": "user_123",
                    "attendees": ["user@example.com"],
                    "event_type_id": "evt_123",
                    "calendar_id": "cal_123",
                    "status": "confirmed",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
            ]

            bookings = await client.list_bookings(limit=50)

            assert len(bookings) == 1
            assert bookings[0].title == "Meeting"

    @pytest.mark.asyncio
    async def test_get_booking_success(self, client: CalComClient) -> None:
        """Test getting specific booking."""
        now = datetime.now()
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "booking_123",
                "title": "1:1 Meeting",
                "description": "Check-in",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
                "location": "Zoom",
                "organizer_id": "user_123",
                "attendees": ["attendee@example.com"],
                "event_type_id": "evt_123",
                "calendar_id": "cal_123",
                "status": "confirmed",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            booking = await client.get_booking("booking_123")

            assert booking.id == "booking_123"
            assert len(booking.attendees) == 1

    @pytest.mark.asyncio
    async def test_create_booking_success(self, client: CalComClient) -> None:
        """Test creating booking."""
        now = datetime.now()
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=3)

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "booking_new",
                "title": "New Booking",
                "description": None,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "location": None,
                "organizer_id": "user_123",
                "attendees": ["attendee@example.com"],
                "event_type_id": "evt_123",
                "calendar_id": None,
                "status": "confirmed",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            booking = await client.create_booking(
                event_type_id="evt_123",
                start_time=start,
                end_time=end,
                attendee_email="attendee@example.com",
            )

            assert booking.id == "booking_new"
            assert booking.status == "confirmed"

    @pytest.mark.asyncio
    async def test_create_booking_validation_error(self, client: CalComClient) -> None:
        """Test create booking validation."""
        now = datetime.now()

        with pytest.raises(CalComValidationError):
            await client.create_booking(
                event_type_id="",
                start_time=now,
                end_time=now + timedelta(hours=1),
            )

        with pytest.raises(CalComValidationError):
            await client.create_booking(
                event_type_id="evt_123",
                start_time=now,
                end_time=now - timedelta(hours=1),  # end before start
            )

    @pytest.mark.asyncio
    async def test_reschedule_event_success(self, client: CalComClient) -> None:
        """Test rescheduling event."""
        now = datetime.now()
        new_start = now + timedelta(days=1)
        new_end = now + timedelta(days=1, hours=1)

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "booking_123",
                "title": "Rescheduled Meeting",
                "description": None,
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
                "location": "Zoom",
                "organizer_id": "user_123",
                "attendees": ["attendee@example.com"],
                "event_type_id": "evt_123",
                "calendar_id": "cal_123",
                "status": "confirmed",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            booking = await client.reschedule_event(
                "booking_123",
                new_start,
                new_end,
            )

            assert booking.start_time == new_start

    @pytest.mark.asyncio
    async def test_cancel_event_success(self, client: CalComClient) -> None:
        """Test canceling event."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "cancelled", "bookingId": "booking_123"}

            result = await client.cancel_event("booking_123", reason="User request")

            assert result["status"] == "cancelled"


class TestCalComClientTeamMethods:
    """Test team-related methods."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_list_teams_success(self, client: CalComClient) -> None:
        """Test listing teams."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [
                {
                    "id": "team_1",
                    "name": "Engineering",
                    "slug": "engineering",
                    "logo": None,
                    "bio": None,
                    "members": ["user_123", "user_124"],
                },
            ]

            teams = await client.list_teams()

            assert len(teams) == 1
            assert teams[0].name == "Engineering"

    @pytest.mark.asyncio
    async def test_get_team_success(self, client: CalComClient) -> None:
        """Test getting team details."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": "team_123",
                "name": "Engineering Team",
                "slug": "engineering-team",
                "logo": "https://example.com/logo.png",
                "bio": "Our engineers",
                "members": ["user_123", "user_124", "user_125"],
            }

            team = await client.get_team("team_123")

            assert team.id == "team_123"
            assert len(team.members) == 3


class TestCalComClientErrorHandling:
    """Test error handling and retry logic."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_request_with_auth_error(self, client: CalComClient) -> None:
        """Test handling 401 authentication error."""
        with patch.object(client, "_http_client", new_callable=AsyncMock) as mock_http:
            response = MagicMock()
            response.status_code = 401
            response.text = "Unauthorized"
            response.json.return_value = {"error": "Invalid API key"}
            mock_http.request = AsyncMock(return_value=response)

            with pytest.raises(CalComAuthError):
                await client._request("GET", "/users/me")

    @pytest.mark.asyncio
    async def test_request_with_not_found_error(self, client: CalComClient) -> None:
        """Test handling 404 not found."""
        with patch.object(client, "_http_client", new_callable=AsyncMock) as mock_http:
            response = MagicMock()
            response.status_code = 404
            response.text = "Not found"
            response.json.return_value = {"error": "Not found"}
            mock_http.request = AsyncMock(return_value=response)

            # 404 returns empty dict, doesn't raise
            result = await client._request("GET", "/events/not_exist")
            assert result == {}

    @pytest.mark.asyncio
    async def test_request_with_rate_limit_error(self, client: CalComClient) -> None:
        """Test handling 429 rate limit."""
        with patch.object(client, "_http_client", new_callable=AsyncMock) as mock_http:
            response = MagicMock()
            response.status_code = 429
            response.text = "Too many requests"
            response.json.return_value = {"error": "Rate limited"}
            response.headers = {"Retry-After": "60"}
            mock_http.request = AsyncMock(return_value=response)

            with pytest.raises(CalComRateLimitError):
                await client._request("GET", "/bookings")

    @pytest.mark.asyncio
    async def test_request_with_server_error(self, client: CalComClient) -> None:
        """Test handling 500 server error."""
        with patch.object(client, "_http_client", new_callable=AsyncMock) as mock_http:
            response = MagicMock()
            response.status_code = 500
            response.text = "Server error"
            response.json.return_value = {"error": "Internal error"}
            mock_http.request = AsyncMock(return_value=response)

            with pytest.raises(CalComAPIError):
                await client._request("GET", "/bookings")

    @pytest.mark.asyncio
    async def test_request_with_timeout_retry(self, client: CalComClient) -> None:
        """Test retry on timeout."""
        with patch.object(client, "_http_client", new_callable=AsyncMock) as mock_http:
            # First call times out, second succeeds
            timeout_response = httpx.TimeoutException("timeout")
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"data": "success"}
            mock_http.request = AsyncMock(side_effect=[timeout_response, success_response])

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._request("GET", "/bookings")
                assert result == {"data": "success"}


class TestCalComClientCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.fixture
    def client(self) -> CalComClient:
        """Create test client."""
        return CalComClient(api_key="test_key_123")

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, client: CalComClient) -> None:
        """Test circuit breaker opens after repeated failures."""
        # Simulate circuit breaker opening
        client._circuit_breaker_failures = 5
        client._circuit_breaker_open = True

        with pytest.raises(CalComAPIError, match="Circuit breaker open"):
            await client._request("GET", "/bookings")


class TestCalComClientHelpers:
    """Test helper methods."""

    def test_validate_timezone_valid(self) -> None:
        """Test timezone validation with valid timezones."""
        assert CalComClient._validate_timezone("America/New_York")
        assert CalComClient._validate_timezone("Europe/London")
        assert CalComClient._validate_timezone("Asia/Tokyo")
        assert CalComClient._validate_timezone("UTC")

    def test_validate_timezone_invalid(self) -> None:
        """Test timezone validation with invalid timezones."""
        assert not CalComClient._validate_timezone("Invalid/Timezone")
        assert not CalComClient._validate_timezone("Not a timezone")
