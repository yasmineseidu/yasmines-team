# Fathom.ai API Integration

## Overview

Complete Fathom.ai Meeting Intelligence API integration for retrieving meeting recordings, transcripts, and meeting data.

- **Base URL:** `https://api.fathom.ai`
- **API Version:** External V1
- **Authentication:** X-Api-Key header
- **Rate Limits:** 60 API calls per minute
- **Documentation:** https://developers.fathom.ai

## Key Features

- List meetings with pagination (up to 10 most recent per request)
- Retrieve meeting transcripts with speaker identification
- Extract meeting metadata (title, date, participants, duration)
- Filter meetings by date range and recording user
- Support for pagination via cursor
- Meeting summaries and action items extraction

## API Endpoints

### List Meetings

**Method:** `GET`
**Path:** `/external/v1/meetings`
**Authentication:** X-Api-Key header

**Query Parameters:**
- `include_transcript` (optional, boolean): Include transcript in response
- `recorded_by` (optional, string): Filter by who recorded the meeting
- `created_after` (optional, string): Filter meetings created after date (ISO 8601)
- `created_before` (optional, string): Filter meetings created before date (ISO 8601)
- `cursor` (optional, string): Pagination cursor for retrieving next page

**Response Schema:**
```json
{
  "meetings": [
    {
      "id": "rec-12345",
      "title": "Q4 Planning Session",
      "url": "https://fathom.video/meeting/rec-12345",
      "created_at": "2025-01-10T14:30:00Z",
      "duration": 3600,
      "participant_count": 5,
      "participants": [
        {
          "name": "John Doe",
          "email": "john@example.com"
        }
      ],
      "transcript_url": "https://api.fathom.ai/v1/recording/rec-12345/transcript",
      "summary": "Discussed Q4 goals and timeline",
      "action_items": [
        {
          "text": "Send proposal to client",
          "assignee": "John Doe"
        }
      ],
      "recorded_by": "john@example.com",
      "video_url": "https://recording.fathom.ai/rec-12345"
    }
  ],
  "next_cursor": "cursor-abc123"
}
```

**Example Request:**
```python
from src.integrations.fathom import FathomClient

client = FathomClient(api_key="your-api-key")
meetings, next_cursor = await client.fetch_meetings()

# With filters
meetings, next_cursor = await client.fetch_meetings(
    created_after="2025-01-01",
    created_before="2025-01-31",
    include_transcript=True
)
```

---

### Get Meeting Transcript

**Method:** `GET`
**Path:** `/external/v1/recordings/{recording_id}/transcript`
**Authentication:** X-Api-Key header

**Path Parameters:**
- `recording_id` (required, string): The meeting/recording ID

**Response Schema:**
```json
{
  "transcript": [
    {
      "speaker": {
        "id": "speaker-1",
        "name": "John Doe",
        "email": "john@example.com"
      },
      "text": "Let's start with the Q4 goals.",
      "timestamp": 0
    }
  ],
  "text": "Full transcript as plain text..."
}
```

**Example Request:**
```python
transcript = await client.get_meeting_transcript("rec-12345")

# Access transcript data
print(f"Meeting: {transcript.meeting_id}")
print(f"Entries: {len(transcript.entries)}")
for entry in transcript.entries:
    if entry.speaker:
        print(f"{entry.speaker.name}: {entry.text}")
```

---

## Error Codes

| Code | Description | Handling |
|------|-------------|----------|
| `400` | Bad Request - Invalid parameters | Validate request parameters |
| `401` | Unauthorized - Invalid/missing API key | Verify API key in .env |
| `403` | Forbidden - Insufficient permissions | Check account permissions |
| `404` | Not Found - Meeting/recording not found | Verify recording ID exists |
| `429` | Rate Limit Exceeded | Implement exponential backoff retry |
| `500` | Internal Server Error | Retry with exponential backoff |
| `502` | Bad Gateway | Retry with exponential backoff |
| `503` | Service Unavailable | Retry with exponential backoff |
| `504` | Gateway Timeout | Retry with exponential backoff |

## Error Handling

The integration includes comprehensive error handling:

```python
from src.integrations.fathom import (
    FathomClient,
    FathomError,
    FathomAuthError,
    FathomRateLimitError,
)

try:
    meetings, cursor = await client.fetch_meetings()
except FathomAuthError:
    # Handle authentication failure
    print("Invalid API key")
except FathomRateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except FathomError as e:
    # Handle other API errors
    print(f"API error: {e.status_code} - {e.message}")
```

## Retry Logic

All API calls implement automatic retry with exponential backoff:

- **Base delay:** 1 second
- **Max retries:** 3 attempts
- **Backoff strategy:** Exponential (1s, 2s, 4s)
- **Jitter:** 10-50% added to prevent thundering herd
- **Retryable errors:** 5xx, 429 (rate limit), timeouts, network errors
- **Non-retryable errors:** 401, 403, 404, 400

## Rate Limiting

Fathom API enforces 60 calls per minute rate limit. The integration:

1. Detects 429 (Too Many Requests) responses
2. Respects Retry-After header if provided
3. Implements automatic exponential backoff
4. Logs rate limit hits for monitoring

## Testing

### Unit Tests
All functionality tested with mocked API responses:
```bash
pytest __tests__/unit/integrations/test_fathom.py -v
```

**Coverage:** 23 tests covering:
- Client initialization and validation
- API method success and error cases
- Data parsing and model creation
- Error handling for all HTTP status codes
- Retry logic with exponential backoff

### Live API Tests
Tests with real Fathom credentials:
```bash
# Set environment variable
export FATHOM_API_KEY="your-api-key"

# Run live API tests
pytest __tests__/integration/test_fathom_live.py -v -m live_api
```

**Live tests verify:**
- Authentication with real API key
- Meeting listing and pagination
- Transcript retrieval for actual meetings
- Filter parameters work correctly
- Integration scenarios (full workflow)
- Concurrent request handling

## Setup

### Installation

1. **Get API Key:**
   - Go to https://developers.fathom.ai
   - Navigate to User Settings → API Access
   - Generate an API key

2. **Configure Environment:**
   ```bash
   # Add to .env at project root
   FATHOM_API_KEY=your-api-key-here
   ```

3. **Install Dependencies:**
   ```bash
   make install
   make dev
   ```

### Usage Example

```python
from src.integrations.fathom import FathomClient

# Initialize client
client = FathomClient(api_key="your-api-key")

# Fetch recent meetings
meetings, next_cursor = await client.fetch_meetings()
print(f"Found {len(meetings)} meetings")

for meeting in meetings:
    print(f"- {meeting.title} ({meeting.created_at})")
    print(f"  Duration: {meeting.duration_seconds}s")
    print(f"  Participants: {len(meeting.participants)}")

# Get transcript for first meeting
if meetings:
    meeting = meetings[0]
    transcript = await client.get_meeting_transcript(meeting.id)

    print(f"\nTranscript ({len(transcript.entries)} entries):")
    for entry in transcript.entries:
        if entry.speaker:
            print(f"  {entry.speaker.name}: {entry.text}")

# Capture structured notes
notes = await client.capture_meeting_notes(meeting.id)
print(f"\nSpeakers: {', '.join(notes['speakers'])}")
```

## Data Models

### Meeting
```python
@dataclass
class Meeting:
    id: str                              # Meeting/recording ID
    title: str | None                   # Meeting title
    url: str | None                     # Fathom video URL
    created_at: str | None              # ISO 8601 timestamp
    duration_seconds: int | None        # Duration in seconds
    participants: list[str]             # List of participant names/emails
    participant_count: int | None       # Number of participants
    transcript_url: str | None          # URL to transcript
    summary: str | None                 # Meeting summary
    action_items: list[str]             # List of action items
    recorded_by: str | None             # Email of recorder
    video_url: str | None               # Video URL
    raw_response: dict[str, Any]        # Raw API response
```

### Transcript
```python
@dataclass
class Transcript:
    meeting_id: str                     # Meeting/recording ID
    entries: list[TranscriptEntry]      # List of transcript entries
    text: str | None                    # Full transcript as text
    raw_response: dict[str, Any]        # Raw API response

@dataclass
class TranscriptEntry:
    speaker: Speaker | None             # Speaker information
    text: str | None                    # Spoken text
    timestamp: int | None               # Timestamp in milliseconds
    timestamp_seconds: float | None     # Timestamp in seconds

@dataclass
class Speaker:
    id: str | None                      # Speaker ID
    name: str | None                    # Speaker name
    email: str | None                   # Speaker email
```

## API Compatibility

- **Version:** External V1
- **SDK Status:** Official Python and TypeScript SDKs available
- **Pagination:** Cursor-based (manual pagination vs. SDK automatic)
- **Future Compatibility:** Implemented `call_endpoint()` method for calling new endpoints without code changes

## Implementation Status

✅ **Completed:**
- Fathom client with full API support
- Meeting listing and transcript retrieval
- Error handling for all HTTP status codes
- Retry logic with exponential backoff
- Rate limiting detection and handling
- Comprehensive unit tests (23/23 passing)
- Live API integration tests
- Data models with type safety

**Test Results:**
- Unit Tests: 23/23 PASSED ✅
- Integration Tests: Ready for live API testing
- Code Quality: Lint and type checks configured
- Coverage: Full method coverage

## Future Enhancements

- OAuth 2.0 support for public applications
- Webhook support for real-time meeting events
- Meeting search functionality
- CRM integration data retrieval
- Caching for frequently accessed meetings
- Batch operations for multiple meetings
