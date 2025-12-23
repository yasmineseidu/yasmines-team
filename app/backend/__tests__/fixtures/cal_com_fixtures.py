"""Test fixtures for Cal.com integration."""

from datetime import datetime, timedelta
from typing import Any

import pytest

# Test API key
TEST_API_KEY = "test_cal_com_api_key_12345"  # pragma: allowlist secret
TEST_BASE_URL = "https://api.cal.com/v2"


# Mock User Data
MOCK_USER_DATA = {
    "data": {
        "id": "user_123",
        "email": "test@example.com",
        "name": "Test User",
        "username": "testuser",
        "timezone": "America/New_York",
        "locale": "en-US",
        "created_at": "2024-01-01T00:00:00Z",
    }
}

# Mock Event Type Data
MOCK_EVENT_TYPE_DATA = {
    "data": {
        "id": "evt_type_123",
        "title": "1:1 Meeting",
        "slug": "1-1-meeting",
        "description": "One-on-one consultation",
        "length": 30,
        "owner_id": "user_123",
        "is_active": True,
        "scheduling_type": "collective",
    }
}

MOCK_EVENT_TYPES_LIST = {
    "data": [
        {
            "id": "evt_type_123",
            "title": "1:1 Meeting",
            "slug": "1-1-meeting",
            "description": "One-on-one consultation",
            "length": 30,
            "owner_id": "user_123",
            "is_active": True,
            "scheduling_type": "collective",
        },
        {
            "id": "evt_type_124",
            "title": "Group Session",
            "slug": "group-session",
            "description": "Group meeting",
            "length": 60,
            "owner_id": "user_123",
            "is_active": True,
            "scheduling_type": "round_robin",
        },
    ]
}

# Mock Availability Data
MOCK_AVAILABILITY_DATA = {
    "data": [
        {
            "user_id": "user_123",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "is_available": True,
        },
        {
            "user_id": "user_123",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "is_available": True,
        },
    ]
}

# Mock Booking Data
MOCK_BOOKING_DATA = {
    "data": {
        "id": "booking_123",
        "title": "Team Sync",
        "description": "Weekly team meeting",
        "start_time": (datetime.now() + timedelta(hours=2)).isoformat(),
        "end_time": (datetime.now() + timedelta(hours=3)).isoformat(),
        "location": "Zoom",
        "organizer_id": "user_123",
        "attendees": ["attendee@example.com"],
        "event_type_id": "evt_type_123",
        "calendar_id": "cal_123",
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
}

MOCK_BOOKINGS_LIST = {
    "data": [
        {
            "id": "booking_123",
            "title": "Team Sync",
            "description": "Weekly team meeting",
            "start_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "end_time": (datetime.now() + timedelta(hours=3)).isoformat(),
            "location": "Zoom",
            "organizer_id": "user_123",
            "attendees": ["attendee@example.com"],
            "event_type_id": "evt_type_123",
            "calendar_id": "cal_123",
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": "booking_124",
            "title": "Client Call",
            "description": "Sales consultation",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "location": "Google Meet",
            "organizer_id": "user_123",
            "attendees": ["client@example.com"],
            "event_type_id": "evt_type_124",
            "calendar_id": "cal_123",
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
    ]
}

# Mock Team Data
MOCK_TEAM_DATA = {
    "data": {
        "id": "team_123",
        "name": "Engineering Team",
        "slug": "engineering-team",
        "logo": "https://example.com/logo.png",
        "bio": "Our engineering team",
        "members": ["user_123", "user_124", "user_125"],
    }
}

MOCK_TEAMS_LIST = {
    "data": [
        {
            "id": "team_123",
            "name": "Engineering Team",
            "slug": "engineering-team",
            "logo": "https://example.com/logo.png",
            "bio": "Our engineering team",
            "members": ["user_123", "user_124", "user_125"],
        },
        {
            "id": "team_124",
            "name": "Sales Team",
            "slug": "sales-team",
            "logo": "https://example.com/logo2.png",
            "bio": "Our sales team",
            "members": ["user_123", "user_126"],
        },
    ]
}

# Mock Error Responses
MOCK_UNAUTHORIZED = {
    "status_code": 401,
    "json_data": {"error": "Unauthorized"},
    "text": "Invalid API key",
}

MOCK_NOT_FOUND = {
    "status_code": 404,
    "json_data": {"error": "Not found"},
    "text": "Resource not found",
}

MOCK_RATE_LIMIT = {
    "status_code": 429,
    "json_data": {"error": "Too many requests"},
    "text": "Rate limit exceeded",
    "headers": {"Retry-After": "60"},
}

MOCK_SERVER_ERROR = {
    "status_code": 500,
    "json_data": {"error": "Internal server error"},
    "text": "Server error",
}


@pytest.fixture
def mock_api_key() -> str:
    """Provide test API key."""
    return TEST_API_KEY


@pytest.fixture
def mock_base_url() -> str:
    """Provide test base URL."""
    return TEST_BASE_URL


@pytest.fixture
def mock_user_data() -> dict[str, Any]:
    """Provide mock user profile data."""
    return MOCK_USER_DATA.copy()


@pytest.fixture
def mock_event_type_data() -> dict[str, Any]:
    """Provide mock event type data."""
    return MOCK_EVENT_TYPE_DATA.copy()


@pytest.fixture
def mock_event_types_list() -> dict[str, Any]:
    """Provide mock event types list."""
    return MOCK_EVENT_TYPES_LIST.copy()


@pytest.fixture
def mock_availability_data() -> dict[str, Any]:
    """Provide mock availability data."""
    return MOCK_AVAILABILITY_DATA.copy()


@pytest.fixture
def mock_booking_data() -> dict[str, Any]:
    """Provide mock booking data."""
    return MOCK_BOOKING_DATA.copy()


@pytest.fixture
def mock_bookings_list() -> dict[str, Any]:
    """Provide mock bookings list."""
    return MOCK_BOOKINGS_LIST.copy()


@pytest.fixture
def mock_team_data() -> dict[str, Any]:
    """Provide mock team data."""
    return MOCK_TEAM_DATA.copy()


@pytest.fixture
def mock_teams_list() -> dict[str, Any]:
    """Provide mock teams list."""
    return MOCK_TEAMS_LIST.copy()


@pytest.fixture
def mock_unauthorized_response() -> dict[str, Any]:
    """Provide mock unauthorized response."""
    return MOCK_UNAUTHORIZED.copy()


@pytest.fixture
def mock_not_found_response() -> dict[str, Any]:
    """Provide mock not found response."""
    return MOCK_NOT_FOUND.copy()


@pytest.fixture
def mock_rate_limit_response() -> dict[str, Any]:
    """Provide mock rate limit response."""
    return MOCK_RATE_LIMIT.copy()


@pytest.fixture
def mock_server_error_response() -> dict[str, Any]:
    """Provide mock server error response."""
    return MOCK_SERVER_ERROR.copy()
