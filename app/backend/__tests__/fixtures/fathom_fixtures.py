"""Test fixtures and sample data for Fathom API integration tests."""

# Sample data for API testing
SAMPLE_DATA = {
    "meeting_id": "rec-12345",
    "recording_id": "rec-12345",
    "include_transcript": True,
    "recorded_by": None,
    "created_after": "2025-01-01",
    "created_before": "2025-12-31",
    "cursor": None,
}

# Expected response schemas for validation
RESPONSE_SCHEMAS = {
    "meeting": {
        "id": str,
        "title": (str, type(None)),
        "url": (str, type(None)),
        "created_at": (str, type(None)),
        "duration_seconds": (int, type(None)),
        "participants": list,
        "participant_count": (int, type(None)),
    },
    "transcript": {
        "meeting_id": str,
        "entries": list,
        "text": (str, type(None)),
    },
    "transcript_entry": {
        "speaker": (dict, type(None)),
        "text": (str, type(None)),
        "timestamp": (int, type(None)),
        "timestamp_seconds": (float, type(None)),
    },
    "notes": {
        "meeting_id": str,
        "transcript_entries": int,
        "full_transcript": str,
        "speakers": list,
    },
}

# Sample API responses for testing
SAMPLE_RESPONSES = {
    "meetings_list": {
        "meetings": [
            {
                "id": "rec-12345",
                "title": "Q4 Planning Session",
                "url": "https://fathom.video/meeting/rec-12345",
                "created_at": "2025-01-10T14:30:00Z",
                "duration": 3600,
                "participant_count": 5,
                "participants": [
                    {"name": "John Doe", "email": "john@example.com"},
                    {"name": "Jane Smith", "email": "jane@example.com"},
                ],
                "transcript_url": "https://api.fathom.ai/v1/recording/rec-12345/transcript",
                "summary": "Discussed Q4 goals and timeline",
                "action_items": [
                    {"text": "Send proposal to client", "assignee": "John Doe"},
                    {"text": "Review budget report", "assignee": "Jane Smith"},
                ],
                "recorded_by": "john@example.com",
                "video_url": "https://recording.fathom.ai/rec-12345",
            }
        ],
        "next_cursor": "cursor-abc123",
    },
    "transcript": {
        "transcript": [
            {
                "speaker": {
                    "id": "speaker-1",
                    "name": "John Doe",
                    "email": "john@example.com",
                },
                "text": "Let's start with the Q4 goals.",
                "timestamp": 0,
            },
            {
                "speaker": {
                    "id": "speaker-2",
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                },
                "text": "I think we should focus on revenue growth.",
                "timestamp": 5000,
            },
            {
                "speaker": {
                    "id": "speaker-1",
                    "name": "John Doe",
                    "email": "john@example.com",
                },
                "text": "Agreed. Let's set a 15% growth target.",
                "timestamp": 12000,
            },
        ],
        "text": "John: Let's start with the Q4 goals.\n"
        "Jane: I think we should focus on revenue growth.\n"
        "John: Agreed. Let's set a 15% growth target.",
    },
}

# Test scenarios: valid inputs + expected outcomes
TEST_SCENARIOS = {
    "fetch_meetings_basic": {
        "description": "Fetch recent meetings without filters",
        "parameters": {},
        "expected_fields": ["meetings", "next_cursor"],
        "should_pass": True,
    },
    "fetch_meetings_with_dates": {
        "description": "Fetch meetings with date range filters",
        "parameters": {
            "created_after": "2025-01-01",
            "created_before": "2025-12-31",
        },
        "expected_fields": ["meetings", "next_cursor"],
        "should_pass": True,
    },
    "fetch_meetings_with_transcript": {
        "description": "Fetch meetings including transcripts",
        "parameters": {"include_transcript": True},
        "expected_fields": ["meetings", "next_cursor"],
        "should_pass": True,
    },
    "fetch_meetings_pagination": {
        "description": "Fetch next page with cursor",
        "parameters": {"cursor": "cursor-abc123"},
        "expected_fields": ["meetings", "next_cursor"],
        "should_pass": True,
    },
    "get_transcript_valid": {
        "description": "Get transcript for valid meeting ID",
        "parameters": {"recording_id": "rec-12345"},
        "expected_fields": ["meeting_id", "entries", "text"],
        "should_pass": True,
    },
    "get_transcript_invalid": {
        "description": "Get transcript with invalid meeting ID",
        "parameters": {"recording_id": "invalid-id"},
        "expected_exception": "FathomError",
        "should_pass": False,
    },
    "capture_notes_valid": {
        "description": "Capture notes for valid meeting",
        "parameters": {"recording_id": "rec-12345"},
        "expected_fields": ["meeting_id", "transcript_entries", "full_transcript", "speakers"],
        "should_pass": True,
    },
}

# Edge cases for comprehensive testing
EDGE_CASES = {
    "empty_string_input": "",
    "special_characters": "meeting-with-special-chars_123!@#",
    "very_long_id": "rec-" + "0" * 1000,
    "null_cursor": None,
    "invalid_date_format": "2025/01/01",  # Wrong format
    "future_date": "2099-12-31",
}
