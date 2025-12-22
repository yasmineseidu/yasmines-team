"""Test fixtures for Google Calendar integration.

Provides sample data, credentials, and expected response schemas for comprehensive testing.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

# Current timestamp for dynamic test data
NOW = datetime.now(UTC)
TOMORROW = NOW + timedelta(days=1)
NEXT_WEEK = NOW + timedelta(weeks=1)

# Sample test data
SAMPLE_DATA = {
    # Calendar identifiers
    "calendar_id": "primary",
    "secondary_calendar_id": "test-calendar-123@group.calendar.google.com",
    # Event identifiers
    "event_id": "event-abc-123",
    "recurring_event_id": "recurring-event-456",
    # Event details
    "event_title": "Test Meeting",
    "event_description": "This is a test event created by automated tests",
    "event_location": "Conference Room A",
    # Attendees
    "attendee_email": "attendee@example.com",
    "organizer_email": "organizer@example.com",
    # Quick add texts
    "quick_add_texts": [
        "Meeting tomorrow at 2pm",
        "Lunch with John next Tuesday at noon",
        "All-day event next Friday",
        "Team sync 3pm for 30 minutes",
    ],
    # Date ranges
    "time_min": NOW.isoformat(),
    "time_max": NEXT_WEEK.isoformat(),
    # Pagination
    "page_size": 10,
    "max_results": 100,
}

# Mock service account credentials for testing
MOCK_SERVICE_ACCOUNT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "key-id-456",
    "private_key": "MOCK_PRIVATE_KEY_FOR_TESTING_ONLY",  # pragma: allowlist secret
    "client_email": "test-service@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789012345678901",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test-service%40test-project-123.iam.gserviceaccount.com",
}

# Invalid credentials for testing error handling
INVALID_CREDENTIALS = {
    "missing_type": {"project_id": "test"},
    "wrong_type": {"type": "invalid_type"},
    "missing_fields": {"type": "service_account"},
    "invalid_json": "not a valid json",
}

# Expected response schemas (field structure and types)
RESPONSE_SCHEMAS = {
    "calendar": {
        "id": str,
        "summary": str,
        "timeZone": str,
        "primary": bool,
    },
    "calendar_list": {
        "id": str,
        "summary": str,
        "accessRole": str,
        "primary": bool,
    },
    "event": {
        "id": str,
        "summary": str,
        "start": dict,
        "end": dict,
        "status": str,
    },
    "event_with_attendees": {
        "id": str,
        "summary": str,
        "start": dict,
        "end": dict,
        "attendees": list,
    },
    "event_list": {
        "items": list,
        "nextPageToken": str,  # Optional
    },
    "health_check": {
        "name": str,
        "healthy": bool,
        "message": str,
    },
}

# Sample API responses
SAMPLE_RESPONSES = {
    "calendar": {
        "id": "primary",
        "summary": "Test Calendar",
        "description": "A test calendar for automated testing",
        "timeZone": "America/New_York",
        "location": "Test Location",
        "primary": True,
        "accessRole": "owner",
    },
    "calendar_list_item": {
        "id": "primary",
        "summary": "Primary Calendar",
        "summaryOverride": None,
        "description": "Main calendar",
        "timeZone": "America/New_York",
        "colorId": "1",
        "backgroundColor": "#ac725e",
        "foregroundColor": "#ffffff",
        "accessRole": "owner",
        "primary": True,
        "selected": True,
        "hidden": False,
        "deleted": False,
    },
    "calendar_list": {
        "kind": "calendar#calendarList",
        "items": [
            {
                "id": "primary",
                "summary": "Primary Calendar",
                "accessRole": "owner",
                "primary": True,
                "selected": True,
                "timeZone": "America/New_York",
            },
            {
                "id": "secondary@group.calendar.google.com",
                "summary": "Secondary Calendar",
                "accessRole": "writer",
                "primary": False,
                "selected": True,
                "timeZone": "America/New_York",
            },
        ],
    },
    "event": {
        "id": "event-abc-123",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=abc123",
        "created": "2025-12-22T10:00:00.000Z",
        "updated": "2025-12-22T11:00:00.000Z",
        "summary": "Test Meeting",
        "description": "Test event description",
        "location": "Conference Room A",
        "creator": {"email": "organizer@example.com"},
        "organizer": {"email": "organizer@example.com"},
        "start": {"dateTime": "2025-12-23T14:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": "2025-12-23T15:00:00Z", "timeZone": "UTC"},
        "attendees": [
            {
                "email": "attendee@example.com",
                "responseStatus": "needsAction",
                "optional": False,
            }
        ],
        "iCalUID": "event-abc-123@google.com",
        "sequence": 0,
    },
    "event_all_day": {
        "id": "event-allday-456",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=allday456",
        "summary": "All Day Event",
        "start": {"date": "2025-12-25"},
        "end": {"date": "2025-12-26"},
    },
    "event_list": {
        "kind": "calendar#events",
        "summary": "Primary Calendar",
        "timeZone": "America/New_York",
        "items": [
            {
                "id": "event-1",
                "summary": "Event 1",
                "start": {"dateTime": "2025-12-23T09:00:00Z"},
                "end": {"dateTime": "2025-12-23T10:00:00Z"},
                "status": "confirmed",
            },
            {
                "id": "event-2",
                "summary": "Event 2",
                "start": {"dateTime": "2025-12-23T14:00:00Z"},
                "end": {"dateTime": "2025-12-23T15:00:00Z"},
                "status": "confirmed",
            },
        ],
        "nextPageToken": "token-for-next-page",
    },
    "quick_add_event": {
        "id": "quick-add-789",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=quick789",
        "summary": "Meeting tomorrow at 2pm",
        "start": {"dateTime": "2025-12-23T14:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": "2025-12-23T15:00:00Z", "timeZone": "UTC"},
    },
    "health_check": {
        "name": "google_calendar",
        "healthy": True,
        "message": "Google Calendar API is accessible",
    },
    "health_check_unhealthy": {
        "name": "google_calendar",
        "healthy": False,
        "message": "Not authenticated",
    },
}

# Error responses
ERROR_RESPONSES = {
    "not_found": {
        "error": {
            "code": 404,
            "message": "Not Found",
            "errors": [{"domain": "global", "reason": "notFound", "message": "Not Found"}],
        }
    },
    "unauthorized": {
        "error": {
            "code": 401,
            "message": "Invalid Credentials",
            "errors": [
                {
                    "domain": "global",
                    "reason": "authError",
                    "message": "Invalid Credentials",
                }
            ],
        }
    },
    "rate_limited": {
        "error": {
            "code": 429,
            "message": "Rate Limit Exceeded",
            "errors": [
                {
                    "domain": "usageLimits",
                    "reason": "rateLimitExceeded",
                    "message": "Rate Limit Exceeded",
                }
            ],
        }
    },
    "quota_exceeded": {
        "error": {
            "code": 403,
            "message": "Calendar usage limit exceeded.",
            "errors": [
                {
                    "domain": "usageLimits",
                    "reason": "quotaExceeded",
                    "message": "Calendar usage limit exceeded.",
                }
            ],
        }
    },
}

# Event creation test data
EVENT_CREATE_DATA = {
    "valid_event": {
        "summary": "Test Meeting",
        "description": "A test meeting event",
        "location": "Conference Room B",
        "start": {
            "dateTime": TOMORROW.replace(hour=14, minute=0, second=0, microsecond=0).isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": TOMORROW.replace(hour=15, minute=0, second=0, microsecond=0).isoformat(),
            "timeZone": "UTC",
        },
        "attendees": ["attendee@example.com"],
    },
    "all_day_event": {
        "summary": "All Day Event",
        "start": {"date": TOMORROW.strftime("%Y-%m-%d")},
        "end": {"date": (TOMORROW + timedelta(days=1)).strftime("%Y-%m-%d")},
    },
    "event_with_conference": {
        "summary": "Video Call",
        "start": {
            "dateTime": TOMORROW.replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": TOMORROW.replace(hour=11, minute=0, second=0, microsecond=0).isoformat(),
            "timeZone": "UTC",
        },
        "conferenceData": {"conferenceId": "meet-xyz"},
    },
}

# Invalid event data for validation testing
INVALID_EVENT_DATA = {
    "empty_summary": {
        "summary": "",
        "start": {"dateTime": TOMORROW.isoformat()},
        "end": {"dateTime": (TOMORROW + timedelta(hours=1)).isoformat()},
    },
    "summary_too_long": {
        "summary": "x" * 300,  # Exceeds 255 character limit
        "start": {"dateTime": TOMORROW.isoformat()},
        "end": {"dateTime": (TOMORROW + timedelta(hours=1)).isoformat()},
    },
    "end_before_start": {
        "summary": "Invalid Event",
        "start": {"dateTime": TOMORROW.isoformat()},
        "end": {"dateTime": (TOMORROW - timedelta(hours=1)).isoformat()},
    },
    "missing_start": {
        "summary": "Missing Start",
        "end": {"dateTime": TOMORROW.isoformat()},
    },
    "missing_end": {
        "summary": "Missing End",
        "start": {"dateTime": TOMORROW.isoformat()},
    },
}


def get_test_credentials() -> dict[str, Any]:
    """Load test credentials from environment.

    Returns:
        Dictionary with service account credentials

    Raises:
        ValueError: If credentials not found in environment
    """
    creds_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
    if creds_json:
        # Check if it's a file path or JSON string
        if creds_json.startswith("{"):
            # It's JSON
            try:
                return json.loads(creds_json)
            except json.JSONDecodeError as err:
                raise ValueError("GOOGLE_CALENDAR_CREDENTIALS_JSON is not valid JSON") from err
        else:
            # It's a file path - try multiple locations
            cred_paths = [
                creds_json,  # As-is from env
                os.path.join(os.getcwd(), creds_json),  # Relative to cwd
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    creds_json.replace("app/backend/", ""),
                ),  # Without duplicate prefix
            ]
            for path in cred_paths:
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)
            raise ValueError(f"Credentials file not found at: {cred_paths}")

    creds_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")
    if creds_path and os.path.exists(creds_path):
        with open(creds_path, encoding="utf-8") as f:
            return json.load(f)

    raise ValueError(
        "No Google Calendar credentials found. Set GOOGLE_CALENDAR_CREDENTIALS_JSON "
        "or GOOGLE_CALENDAR_CREDENTIALS_PATH in .env"
    )


def has_test_credentials() -> bool:
    """Check if test credentials are available.

    Returns:
        True if credentials are available, False otherwise
    """
    try:
        get_test_credentials()
        return True
    except ValueError:
        return False


# List of all endpoints to test
ENDPOINTS_TO_TEST = [
    {
        "name": "list_calendars",
        "method": "GET",
        "description": "List all accessible calendars",
        "required_auth": True,
    },
    {
        "name": "get_calendar",
        "method": "GET",
        "description": "Get specific calendar details",
        "required_auth": True,
    },
    {
        "name": "list_events",
        "method": "GET",
        "description": "List events with filtering and pagination",
        "required_auth": True,
    },
    {
        "name": "get_event",
        "method": "GET",
        "description": "Get specific event details",
        "required_auth": True,
    },
    {
        "name": "create_event",
        "method": "POST",
        "description": "Create new calendar event",
        "required_auth": True,
    },
    {
        "name": "update_event",
        "method": "PATCH",
        "description": "Update existing event",
        "required_auth": True,
    },
    {
        "name": "delete_event",
        "method": "DELETE",
        "description": "Delete calendar event",
        "required_auth": True,
    },
    {
        "name": "quick_add_event",
        "method": "POST",
        "description": "Create event from natural language",
        "required_auth": True,
    },
    {
        "name": "health_check",
        "method": "GET",
        "description": "Check API connectivity",
        "required_auth": False,
    },
    {
        "name": "authenticate",
        "method": "POST",
        "description": "Authenticate with service account",
        "required_auth": False,
    },
]

# Error scenarios for testing
ERROR_SCENARIOS = {
    "invalid_calendar_id": {
        "calendar_id": "invalid-calendar-id-that-does-not-exist",
        "expected_error": "Calendar not found",
        "status_code": 404,
    },
    "invalid_event_id": {
        "event_id": "invalid-event-id-that-does-not-exist",
        "expected_error": "Event not found",
        "status_code": 404,
    },
    "invalid_credentials": {
        "credentials": {"type": "invalid"},
        "expected_error": "Invalid credentials",
        "status_code": 401,
    },
    "quota_exceeded": {
        "expected_error": "Quota exceeded",
        "status_code": 403,
    },
    "rate_limited": {
        "expected_error": "Rate limited",
        "status_code": 429,
    },
    "permission_denied": {
        "expected_error": "Permission denied",
        "status_code": 403,
    },
}
