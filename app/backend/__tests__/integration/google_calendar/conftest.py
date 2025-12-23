"""Pytest configuration and fixtures for Google Calendar integration tests.

Provides fixtures for service account authentication and test data configuration.
"""

import json
import os
from datetime import UTC

import pytest
from dotenv import load_dotenv

# Load .env file from backend root (3 levels up: google_calendar -> integration -> __tests__ -> backend)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))


@pytest.fixture(scope="session")
def google_calendar_credentials_path() -> str:
    """Get Google Calendar credentials JSON path from environment."""
    return os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_JSON",
        "config/credentials/google-service-account.json",  # Relative to backend root
    )


@pytest.fixture(scope="session")
def google_calendar_credentials(google_calendar_credentials_path: str) -> dict:
    """Load Google Calendar service account credentials.

    Returns:
        dict: Service account credentials JSON

    Raises:
        pytest.skip: If credentials file not found
    """
    # Resolve backend root (4 dirname calls from conftest.py)
    # conftest.py -> google_calendar/ -> integration/ -> __tests__/ -> backend/
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    # Try multiple path resolution strategies
    paths_to_try = []

    if os.path.isabs(google_calendar_credentials_path):
        paths_to_try.append(google_calendar_credentials_path)
    else:
        # Try relative to backend root first
        paths_to_try.append(os.path.join(backend_root, google_calendar_credentials_path))
        # Try stripping "app/backend/" prefix if present (for project-root relative paths)
        if google_calendar_credentials_path.startswith("app/backend/"):
            stripped_path = google_calendar_credentials_path[len("app/backend/") :]
            paths_to_try.append(os.path.join(backend_root, stripped_path))
        # Try as-is from current directory
        paths_to_try.append(google_calendar_credentials_path)

    # Find the first path that exists
    full_path = None
    for path in paths_to_try:
        if os.path.exists(path):
            full_path = path
            break

    if not full_path:
        pytest.skip(
            f"Google Calendar credentials file not found.\n"
            f"Tried paths: {paths_to_try}\n\n"
            "To run live API tests:\n"
            "1. Create a service account in Google Cloud Console\n"
            "2. Enable Google Calendar API\n"
            "3. Download JSON key file\n"
            "4. Set GOOGLE_CALENDAR_CREDENTIALS_JSON in .env"
        )

    with open(full_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def delegated_user() -> str | None:
    """Get delegated user email for domain-wide delegation."""
    return os.getenv("GOOGLE_DELEGATED_USER")


@pytest.fixture
def sample_event_data() -> dict:
    """Fixture providing sample event data for testing."""
    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    start_time = now + timedelta(days=1, hours=10)
    end_time = start_time + timedelta(hours=1)

    return {
        "summary": "Claude Code Integration Test Event",
        "description": "This event was created by automated integration tests.",
        "location": "Virtual Meeting Room",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        },
    }


@pytest.fixture
def sample_all_day_event_data() -> dict:
    """Fixture providing sample all-day event data."""
    from datetime import datetime, timedelta

    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%d")

    return {
        "summary": "Claude Code All-Day Test Event",
        "description": "All-day event created by automated tests.",
        "start": {"date": tomorrow},
        "end": {"date": day_after},
    }


@pytest.fixture
def sample_event_with_attendees() -> dict:
    """Fixture providing sample event data with attendees."""
    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    start_time = now + timedelta(days=2, hours=14)
    end_time = start_time + timedelta(hours=30)

    return {
        "summary": "Claude Code Team Meeting Test",
        "description": "Meeting event with attendees for integration testing.",
        "location": "Conference Room A",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        },
        "attendees": [
            {"email": "test-attendee@example.com"},
        ],
    }


@pytest.fixture
def quick_add_texts() -> list[str]:
    """Fixture providing sample quick-add text strings."""
    return [
        "Meeting tomorrow at 2pm",
        "Team sync next Monday at 10am for 1 hour",
        "Lunch with client Friday at noon",
        "Project deadline next Friday",
    ]


@pytest.fixture
def calendar_scopes() -> list[str]:
    """Fixture providing Google Calendar API scopes."""
    return [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]


@pytest.fixture
def rate_limit_config() -> dict:
    """Fixture providing rate limit configuration for Google Calendar."""
    return {
        "queries_per_day": 1_000_000,
        "queries_per_100_seconds": 1000,
        "max_retries": 3,
        "initial_backoff_seconds": 1,
        "max_backoff_seconds": 32,
    }


@pytest.fixture
def supported_endpoints() -> list[dict]:
    """Fixture providing all supported Google Calendar API endpoints."""
    return [
        {
            "name": "health_check",
            "method": "GET",
            "description": "Check API connectivity",
            "requires_auth": True,
        },
        {
            "name": "list_calendars",
            "method": "GET",
            "description": "List all accessible calendars",
            "requires_auth": True,
        },
        {
            "name": "get_calendar",
            "method": "GET",
            "description": "Get specific calendar details",
            "requires_auth": True,
        },
        {
            "name": "list_events",
            "method": "GET",
            "description": "List events with filtering and pagination",
            "requires_auth": True,
        },
        {
            "name": "get_event",
            "method": "GET",
            "description": "Get specific event details",
            "requires_auth": True,
        },
        {
            "name": "create_event",
            "method": "POST",
            "description": "Create new calendar event",
            "requires_auth": True,
        },
        {
            "name": "update_event",
            "method": "PATCH",
            "description": "Update existing event",
            "requires_auth": True,
        },
        {
            "name": "delete_event",
            "method": "DELETE",
            "description": "Delete calendar event",
            "requires_auth": True,
        },
        {
            "name": "quick_add_event",
            "method": "POST",
            "description": "Create event from natural language",
            "requires_auth": True,
        },
    ]
