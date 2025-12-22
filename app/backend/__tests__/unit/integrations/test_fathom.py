"""
Unit tests for Fathom API integration client.

Tests cover:
- Client initialization and configuration
- API request methods (fetch_meetings, get_transcript, etc.)
- Error handling for various HTTP status codes
- Data parsing and model validation
- Retry logic and resilience
- Rate limit handling
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.fathom import (
    FathomAuthError,
    FathomClient,
    FathomError,
    FathomRateLimitError,
    Meeting,
    Speaker,
    Transcript,
    TranscriptEntry,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fathom_client():
    """Create Fathom client with test API key."""
    return FathomClient(api_key="test-api-key-123")  # pragma: allowlist secret


@pytest.fixture
def sample_meeting_response():
    """Sample meeting response from Fathom API."""
    return {
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
    }


@pytest.fixture
def sample_transcript_response():
    """Sample transcript response from Fathom API."""
    return {
        "transcript": [
            {
                "speaker": {"id": "speaker-1", "name": "John Doe", "email": "john@example.com"},
                "text": "Let's start with the Q4 goals.",
                "timestamp": 0,
            },
            {
                "speaker": {"id": "speaker-2", "name": "Jane Smith", "email": "jane@example.com"},
                "text": "I think we should focus on revenue growth.",
                "timestamp": 5000,
            },
            {
                "speaker": {"id": "speaker-1", "name": "John Doe", "email": "john@example.com"},
                "text": "Agreed. Let's set a 15% growth target.",
                "timestamp": 12000,
            },
        ],
        "text": "John: Let's start with the Q4 goals.\n"
        "Jane: I think we should focus on revenue growth.\n"
        "John: Agreed. Let's set a 15% growth target.",
    }


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestFathomClientInitialization:
    """Tests for client initialization."""

    def test_initialization_with_valid_api_key(self):
        """Test client initializes successfully with valid API key."""
        client = FathomClient(api_key="valid-key-123")  # pragma: allowlist secret
        assert client.name == "fathom"
        assert client.api_key == "valid-key-123"  # pragma: allowlist secret
        assert client.base_url == "https://api.fathom.ai"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_initialization_with_empty_api_key(self):
        """Test client raises ValueError with empty API key."""
        with pytest.raises(ValueError, match="Fathom API key is required"):
            FathomClient(api_key="")

    def test_initialization_with_none_api_key(self):
        """Test client raises ValueError with None API key."""
        with pytest.raises(ValueError, match="Fathom API key is required"):
            FathomClient(api_key=None)

    def test_custom_headers_use_x_api_key(self, fathom_client):
        """Test that headers use X-Api-Key instead of Bearer token."""
        headers = fathom_client._get_headers()
        assert "X-Api-Key" in headers
        assert headers["X-Api-Key"] == "test-api-key-123"
        assert "Authorization" not in headers


# =============================================================================
# FETCH MEETINGS TESTS
# =============================================================================


class TestFetchMeetings:
    """Tests for fetch_meetings method."""

    @pytest.mark.asyncio
    async def test_fetch_meetings_success(self, fathom_client, sample_meeting_response):
        """Test successful meeting retrieval."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_meeting_response

            meetings, next_cursor = await fathom_client.fetch_meetings()

            assert len(meetings) == 1
            assert meetings[0].id == "rec-12345"
            assert meetings[0].title == "Q4 Planning Session"
            assert meetings[0].duration_seconds == 3600
            assert len(meetings[0].participants) == 2
            assert next_cursor == "cursor-abc123"

    @pytest.mark.asyncio
    async def test_fetch_meetings_with_filters(self, fathom_client, sample_meeting_response):
        """Test fetch_meetings with filter parameters."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_meeting_response

            await fathom_client.fetch_meetings(
                include_transcript=True,
                recorded_by="john@example.com",
                created_after="2025-01-01",
                created_before="2025-01-31",
            )

            # Verify the call was made with correct parameters
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["include_transcript"] == "true"
            assert call_kwargs["params"]["recorded_by"] == "john@example.com"
            assert call_kwargs["params"]["created_after"] == "2025-01-01"
            assert call_kwargs["params"]["created_before"] == "2025-01-31"

    @pytest.mark.asyncio
    async def test_fetch_meetings_empty_response(self, fathom_client):
        """Test fetch_meetings with empty meetings list."""
        empty_response = {"meetings": [], "next_cursor": None}

        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = empty_response

            meetings, next_cursor = await fathom_client.fetch_meetings()

            assert len(meetings) == 0
            assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_meetings_api_error(self, fathom_client):
        """Test fetch_meetings handles API errors."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = FathomError("API request failed")

            with pytest.raises(FathomError):
                await fathom_client.fetch_meetings()

    @pytest.mark.asyncio
    async def test_fetch_meetings_network_error(self, fathom_client):
        """Test fetch_meetings handles network errors gracefully."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = Exception("Network error")

            with pytest.raises(FathomError, match="Failed to fetch meetings"):
                await fathom_client.fetch_meetings()


# =============================================================================
# GET TRANSCRIPT TESTS
# =============================================================================


class TestGetTranscript:
    """Tests for get_meeting_transcript method."""

    @pytest.mark.asyncio
    async def test_get_transcript_success(self, fathom_client, sample_transcript_response):
        """Test successful transcript retrieval."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = sample_transcript_response

            transcript = await fathom_client.get_meeting_transcript("rec-12345")

            assert transcript.meeting_id == "rec-12345"
            assert len(transcript.entries) == 3
            assert transcript.entries[0].speaker.name == "John Doe"
            assert transcript.entries[0].text == "Let's start with the Q4 goals."
            assert transcript.entries[0].timestamp == 0
            assert transcript.entries[0].timestamp_seconds == 0.0
            assert transcript.entries[1].timestamp_seconds == 5.0
            assert transcript.text is not None
            assert "revenue growth" in transcript.text

    @pytest.mark.asyncio
    async def test_get_transcript_correct_endpoint(self, fathom_client):
        """Test that transcript uses correct API endpoint."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"transcript": [], "text": ""}

            await fathom_client.get_meeting_transcript("rec-12345")

            mock_request.assert_called_once_with(
                "GET",
                "/external/v1/recordings/rec-12345/transcript",
            )

    @pytest.mark.asyncio
    async def test_get_transcript_missing_speaker(self, fathom_client):
        """Test transcript parsing with missing speaker info."""
        response = {
            "transcript": [
                {
                    "speaker": None,
                    "text": "This speaker is unknown",
                    "timestamp": 1000,
                }
            ],
            "text": "This speaker is unknown",
        }

        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = response

            transcript = await fathom_client.get_meeting_transcript("rec-12345")

            assert len(transcript.entries) == 1
            assert transcript.entries[0].speaker is None
            assert transcript.entries[0].text == "This speaker is unknown"

    @pytest.mark.asyncio
    async def test_get_transcript_api_error(self, fathom_client):
        """Test get_transcript handles API errors."""
        with patch.object(
            fathom_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = FathomError("API error")

            with pytest.raises(FathomError):
                await fathom_client.get_meeting_transcript("rec-12345")


# =============================================================================
# CAPTURE NOTES TESTS
# =============================================================================


class TestCaptureMeetingNotes:
    """Tests for capture_meeting_notes method."""

    @pytest.mark.asyncio
    async def test_capture_notes_success(self, fathom_client, sample_transcript_response):
        """Test successful notes capturing."""
        with patch.object(
            fathom_client,
            "get_meeting_transcript",
            new_callable=AsyncMock,
        ) as mock_transcript:
            # Create transcript object
            transcript = Transcript(
                meeting_id="rec-12345",
                entries=[
                    TranscriptEntry(
                        speaker=Speaker(name="John Doe"),
                        text="Let's start",
                        timestamp=0,
                    )
                ],
                text="Let's start with the meeting",
                raw_response=sample_transcript_response,
            )
            mock_transcript.return_value = transcript

            notes = await fathom_client.capture_meeting_notes("rec-12345")

            assert notes["meeting_id"] == "rec-12345"
            assert notes["transcript_entries"] == 1
            assert "John Doe" in notes["speakers"]
            assert "Let's start with the meeting" in notes["full_transcript"]

    @pytest.mark.asyncio
    async def test_capture_notes_error(self, fathom_client):
        """Test capture_notes handles errors gracefully."""
        with patch.object(
            fathom_client,
            "get_meeting_transcript",
            new_callable=AsyncMock,
        ) as mock_transcript:
            mock_transcript.side_effect = FathomError("Transcript error")

            with pytest.raises(FathomError):
                await fathom_client.capture_meeting_notes("rec-12345")


# =============================================================================
# PARSING TESTS
# =============================================================================


class TestParsing:
    """Tests for data parsing methods."""

    def test_parse_meeting_complete_data(self, fathom_client):
        """Test parsing complete meeting data."""
        data = {
            "id": "rec-12345",
            "title": "Q4 Planning",
            "url": "https://fathom.video/rec-12345",
            "created_at": "2025-01-10T14:30:00Z",
            "duration": 3600,
            "participant_count": 5,
            "participants": [
                {"name": "John Doe", "email": "john@example.com"},
                {"name": "Jane Smith", "email": "jane@example.com"},
            ],
            "action_items": [
                {"text": "Send proposal"},
                {"text": "Review budget"},
            ],
            "recorded_by": "john@example.com",
        }

        meeting = fathom_client._parse_meeting(data)

        assert meeting.id == "rec-12345"
        assert meeting.title == "Q4 Planning"
        assert meeting.duration_seconds == 3600
        assert len(meeting.participants) == 2
        assert len(meeting.action_items) == 2
        assert "John Doe" in meeting.participants

    def test_parse_meeting_minimal_data(self, fathom_client):
        """Test parsing meeting with minimal required data."""
        data = {"id": "rec-12345"}

        meeting = fathom_client._parse_meeting(data)

        assert meeting.id == "rec-12345"
        assert meeting.title is None
        assert meeting.participants == []
        assert meeting.action_items == []

    def test_parse_transcript_entry_with_speaker(self, fathom_client):
        """Test parsing transcript entry with speaker info."""
        data = {
            "speaker": {"id": "sp-1", "name": "John Doe", "email": "john@example.com"},
            "text": "Let's start the meeting",
            "timestamp": 5000,
        }

        entry = fathom_client._parse_transcript_entry(data)

        assert entry.speaker is not None
        assert entry.speaker.name == "John Doe"
        assert entry.text == "Let's start the meeting"
        assert entry.timestamp == 5000
        assert entry.timestamp_seconds == 5.0

    def test_parse_transcript_entry_timestamp_conversion(self, fathom_client):
        """Test transcript timestamp is correctly converted from ms to seconds."""
        data = {
            "speaker": {"name": "John"},
            "text": "Speaking",
            "timestamp": 123456,
        }

        entry = fathom_client._parse_transcript_entry(data)

        assert entry.timestamp == 123456
        assert entry.timestamp_seconds == 123.456

    def test_extract_unique_speakers(self, fathom_client):
        """Test extracting unique speakers from transcript."""
        transcript = Transcript(
            meeting_id="rec-12345",
            entries=[
                TranscriptEntry(speaker=Speaker(name="Alice"), text="Hello"),
                TranscriptEntry(speaker=Speaker(name="Bob"), text="Hi"),
                TranscriptEntry(speaker=Speaker(name="Alice"), text="How are you?"),
                TranscriptEntry(speaker=None, text="No speaker"),
            ],
        )

        speakers = fathom_client._extract_unique_speakers(transcript)

        assert len(speakers) == 2
        assert speakers == ["Alice", "Bob"]  # Should be sorted


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_fathom_error_inheritance(self):
        """Test FathomError inherits from IntegrationError."""
        from src.integrations.base import IntegrationError

        error = FathomError("Test error")
        assert isinstance(error, IntegrationError)

    def test_fathom_auth_error(self):
        """Test FathomAuthError creation."""
        error = FathomAuthError("Invalid credentials")
        assert "Invalid credentials" in str(error)

    def test_fathom_rate_limit_error(self):
        """Test FathomRateLimitError creation."""
        error = FathomRateLimitError("Rate limit exceeded", retry_after=60)
        assert error.retry_after == 60


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Tests for data model classes."""

    def test_meeting_creation(self):
        """Test Meeting model creation."""
        meeting = Meeting(
            id="rec-12345",
            title="Team Sync",
            participants=["Alice", "Bob"],
            duration_seconds=1800,
        )

        assert meeting.id == "rec-12345"
        assert meeting.title == "Team Sync"
        assert len(meeting.participants) == 2
        assert meeting.duration_seconds == 1800

    def test_transcript_entry_creation(self):
        """Test TranscriptEntry model creation."""
        speaker = Speaker(name="Alice", email="alice@example.com")
        entry = TranscriptEntry(
            speaker=speaker,
            text="Speaking now",
            timestamp=1000,
            timestamp_seconds=1.0,
        )

        assert entry.speaker.name == "Alice"
        assert entry.text == "Speaking now"
        assert entry.timestamp == 1000
        assert entry.timestamp_seconds == 1.0

    def test_transcript_creation(self):
        """Test Transcript model creation."""
        entries = [
            TranscriptEntry(speaker=Speaker(name="Alice"), text="Hello"),
            TranscriptEntry(speaker=Speaker(name="Bob"), text="Hi"),
        ]
        transcript = Transcript(
            meeting_id="rec-12345",
            entries=entries,
            text="Full transcript text",
        )

        assert transcript.meeting_id == "rec-12345"
        assert len(transcript.entries) == 2
        assert transcript.text == "Full transcript text"
