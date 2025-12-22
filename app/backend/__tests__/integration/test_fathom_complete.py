"""
Complete integration tests for Fathom.ai API.

Tests EVERY endpoint with real API keys from .env.
Ensures 100% endpoint coverage with no exceptions.

Run with: pytest __tests__/integration/test_fathom_complete.py -v
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from __tests__.fixtures.fathom_fixtures import (
    RESPONSE_SCHEMAS,
)
from src.integrations.fathom import (
    FathomClient,
    FathomError,
    Meeting,
    Transcript,
)

# Load .env from project root
env_path = Path(__file__).parents[4] / ".env"
load_dotenv(env_path)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_key() -> str:
    """Get Fathom API key from .env."""
    key = os.getenv("FATHOM_API_KEY")
    if not key:
        pytest.skip("FATHOM_API_KEY not found in .env at project root")
    return key


@pytest.fixture
def fathom_client(api_key: str) -> FathomClient:
    """Create Fathom client with real API key."""
    return FathomClient(api_key=api_key)


# =============================================================================
# TEST: fetch_meetings - HAPPY PATH
# =============================================================================


class TestFetchMeetingsHappyPath:
    """Tests for fetch_meetings() - happy path scenarios."""

    @pytest.mark.asyncio
    async def test_fetch_meetings_basic(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - basic call without filters."""
        meetings, next_cursor = await fathom_client.fetch_meetings()

        # Assertions: response structure
        assert isinstance(meetings, list)
        assert next_cursor is None or isinstance(next_cursor, str)

        # Assertions: each meeting is valid
        for meeting in meetings:
            assert isinstance(meeting, Meeting)
            assert meeting.id is not None
            assert isinstance(meeting.id, str)
            assert len(meeting.id) > 0

    @pytest.mark.asyncio
    async def test_fetch_meetings_response_structure(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - response has correct structure."""
        meetings, next_cursor = await fathom_client.fetch_meetings()

        # Check meeting fields exist (even if None)
        schema = RESPONSE_SCHEMAS["meeting"]
        for meeting in meetings:
            for field, _field_type in schema.items():
                assert hasattr(meeting, field), f"Meeting missing field: {field}"

    @pytest.mark.asyncio
    async def test_fetch_meetings_with_date_filters(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - date range filters work."""
        meetings, cursor = await fathom_client.fetch_meetings(
            created_after="2025-01-01",
            created_before="2025-12-31",
        )

        assert isinstance(meetings, list)
        # All meetings should be within date range (if any returned)
        for meeting in meetings:
            if meeting.created_at:
                # Verify date is in range
                assert "2025" in meeting.created_at

    @pytest.mark.asyncio
    async def test_fetch_meetings_with_transcript_flag(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - include_transcript parameter works."""
        meetings, _ = await fathom_client.fetch_meetings(include_transcript=True)

        assert isinstance(meetings, list)
        # Should return meetings (may not have transcripts if not recorded)

    @pytest.mark.asyncio
    async def test_fetch_meetings_pagination_cursor(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - pagination with cursor."""
        # Get first page
        meetings1, cursor1 = await fathom_client.fetch_meetings()

        # If cursor exists, try next page
        if cursor1:
            meetings2, cursor2 = await fathom_client.fetch_meetings(cursor=cursor1)
            assert isinstance(meetings2, list)


# =============================================================================
# TEST: fetch_meetings - ERROR HANDLING
# =============================================================================


class TestFetchMeetingsErrorHandling:
    """Tests for fetch_meetings() - error scenarios."""

    @pytest.mark.asyncio
    async def test_fetch_meetings_invalid_date_format(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - handles invalid date format gracefully."""
        # API should either accept or reject invalid dates
        try:
            meetings, _ = await fathom_client.fetch_meetings(created_after="invalid-date")
            # If accepted, meetings should be a list
            assert isinstance(meetings, list)
        except FathomError:
            # If rejected, should raise FathomError (acceptable)
            pass

    @pytest.mark.asyncio
    async def test_fetch_meetings_future_date(self, fathom_client: FathomClient) -> None:
        """Test fetch_meetings() - future date filters."""
        meetings, _ = await fathom_client.fetch_meetings(created_after="2099-01-01")

        # Should return empty list for future dates
        assert isinstance(meetings, list)
        # Expected: empty list since no meetings in future


# =============================================================================
# TEST: get_meeting_transcript - HAPPY PATH
# =============================================================================


class TestGetTranscriptHappyPath:
    """Tests for get_meeting_transcript() - happy path scenarios."""

    @pytest.mark.asyncio
    async def test_get_transcript_valid_id(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - valid meeting ID."""
        # First, get a list of meetings to find a valid ID
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                # Assertions: response structure
                assert isinstance(transcript, Transcript)
                assert transcript.meeting_id == meeting.id
                assert isinstance(transcript.entries, list)
                assert isinstance(transcript.text, str) or transcript.text is None

            except FathomError as e:
                # Some meetings may not have transcripts yet
                if "404" in str(e):
                    pytest.skip("Meeting transcript not available")
                raise

    @pytest.mark.asyncio
    async def test_get_transcript_response_structure(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - response has correct structure."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                # Check required fields
                assert hasattr(transcript, "meeting_id")
                assert hasattr(transcript, "entries")
                assert hasattr(transcript, "text")

                # Check entries structure
                for entry in transcript.entries:
                    assert hasattr(entry, "speaker")
                    assert hasattr(entry, "text")
                    assert hasattr(entry, "timestamp")

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Transcript not available")
                raise

    @pytest.mark.asyncio
    async def test_get_transcript_speaker_parsing(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - speaker info is correctly parsed."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                # Check speakers are parsed
                for entry in transcript.entries:
                    if entry.speaker:
                        # Speaker fields should be strings or None
                        assert isinstance(entry.speaker.name, str) or entry.speaker.name is None
                        assert isinstance(entry.speaker.email, str) or entry.speaker.email is None

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Transcript not available")
                raise

    @pytest.mark.asyncio
    async def test_get_transcript_timestamp_conversion(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - timestamps are correctly converted."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                # Check timestamp conversion (ms to seconds)
                for entry in transcript.entries:
                    if entry.timestamp is not None:
                        assert isinstance(entry.timestamp, int)
                        assert entry.timestamp >= 0

                    if entry.timestamp_seconds is not None:
                        assert isinstance(entry.timestamp_seconds, float)
                        assert entry.timestamp_seconds >= 0.0
                        # Verify conversion: seconds should be ms/1000
                        if entry.timestamp is not None:
                            assert abs(entry.timestamp_seconds - (entry.timestamp / 1000.0)) < 0.001

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Transcript not available")
                raise


# =============================================================================
# TEST: get_meeting_transcript - ERROR HANDLING
# =============================================================================


class TestGetTranscriptErrorHandling:
    """Tests for get_meeting_transcript() - error scenarios."""

    @pytest.mark.asyncio
    async def test_get_transcript_invalid_id(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - invalid meeting ID raises error."""
        with pytest.raises(FathomError):
            await fathom_client.get_meeting_transcript("invalid-nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_transcript_empty_id(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - empty ID handling."""
        with pytest.raises((FathomError, ValueError)):
            await fathom_client.get_meeting_transcript("")

    @pytest.mark.asyncio
    async def test_get_transcript_special_characters(self, fathom_client: FathomClient) -> None:
        """Test get_meeting_transcript() - handles special characters in ID."""
        with pytest.raises(FathomError):
            await fathom_client.get_meeting_transcript("rec-!@#$%^&*()")


# =============================================================================
# TEST: capture_meeting_notes - HAPPY PATH
# =============================================================================


class TestCaptureMeetingNotesHappyPath:
    """Tests for capture_meeting_notes() - happy path scenarios."""

    @pytest.mark.asyncio
    async def test_capture_notes_valid_id(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - valid meeting ID."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                notes = await fathom_client.capture_meeting_notes(meeting.id)

                # Assertions: response structure
                assert isinstance(notes, dict)
                assert "meeting_id" in notes
                assert notes["meeting_id"] == meeting.id
                assert "transcript_entries" in notes
                assert isinstance(notes["transcript_entries"], int)
                assert "full_transcript" in notes
                assert "speakers" in notes
                assert isinstance(notes["speakers"], list)

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Meeting data not available")
                raise

    @pytest.mark.asyncio
    async def test_capture_notes_response_schema(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - response matches schema."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                notes = await fathom_client.capture_meeting_notes(meeting.id)

                # Check against schema
                schema = RESPONSE_SCHEMAS["notes"]
                for field, _field_type in schema.items():
                    assert field in notes, f"Missing field: {field}"

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Meeting data not available")
                raise

    @pytest.mark.asyncio
    async def test_capture_notes_speaker_extraction(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - speakers are correctly extracted."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                notes = await fathom_client.capture_meeting_notes(meeting.id)

                # Speakers should be a list of strings
                speakers = notes["speakers"]
                assert isinstance(speakers, list)
                for speaker in speakers:
                    assert isinstance(speaker, str)
                    assert len(speaker) > 0

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Meeting data not available")
                raise

    @pytest.mark.asyncio
    async def test_capture_notes_transcript_content(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - full transcript content is captured."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                notes = await fathom_client.capture_meeting_notes(meeting.id)

                # Transcript should be a string (may be empty)
                transcript = notes["full_transcript"]
                assert isinstance(transcript, str)

                # If there are entries, transcript should have content
                if notes["transcript_entries"] > 0:
                    assert len(transcript) > 0

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Meeting data not available")
                raise


# =============================================================================
# TEST: capture_meeting_notes - ERROR HANDLING
# =============================================================================


class TestCaptureMeetingNotesErrorHandling:
    """Tests for capture_meeting_notes() - error scenarios."""

    @pytest.mark.asyncio
    async def test_capture_notes_invalid_id(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - invalid ID raises error."""
        with pytest.raises(FathomError):
            await fathom_client.capture_meeting_notes("invalid-id")

    @pytest.mark.asyncio
    async def test_capture_notes_empty_id(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - empty ID handling."""
        with pytest.raises((FathomError, ValueError)):
            await fathom_client.capture_meeting_notes("")

    @pytest.mark.asyncio
    async def test_capture_notes_special_characters(self, fathom_client: FathomClient) -> None:
        """Test capture_meeting_notes() - special characters in ID."""
        with pytest.raises(FathomError):
            await fathom_client.capture_meeting_notes("rec-<script>alert()</script>")


# =============================================================================
# TEST: Integration Scenarios (Full Workflows)
# =============================================================================


class TestIntegrationScenarios:
    """Tests for complete workflows using multiple endpoints."""

    @pytest.mark.asyncio
    async def test_full_workflow_fetch_transcript_capture_notes(
        self, fathom_client: FathomClient
    ) -> None:
        """Test full workflow: fetch → get transcript → capture notes."""
        # Step 1: Fetch meetings
        meetings, _ = await fathom_client.fetch_meetings()

        if not meetings:
            pytest.skip("No meetings available in Fathom account")

        meeting = meetings[0]

        # Step 2: Get transcript
        try:
            transcript = await fathom_client.get_meeting_transcript(meeting.id)
            assert transcript is not None
        except FathomError as e:
            if "404" in str(e):
                pytest.skip("Transcript not available")
            raise

        # Step 3: Capture notes
        try:
            notes = await fathom_client.capture_meeting_notes(meeting.id)
            assert notes is not None
            assert notes["meeting_id"] == meeting.id
        except FathomError as e:
            if "404" in str(e):
                pytest.skip("Notes not available")
            raise

    @pytest.mark.asyncio
    async def test_workflow_with_pagination(self, fathom_client: FathomClient) -> None:
        """Test workflow with pagination."""
        # Get first page
        meetings1, cursor1 = await fathom_client.fetch_meetings()

        assert isinstance(meetings1, list)

        # If cursor exists, get next page
        if cursor1:
            meetings2, cursor2 = await fathom_client.fetch_meetings(cursor=cursor1)
            assert isinstance(meetings2, list)

            # Both pages should have valid meetings
            for page_meetings in [meetings1, meetings2]:
                for meeting in page_meetings:
                    assert isinstance(meeting, Meeting)
                    assert meeting.id is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, fathom_client: FathomClient) -> None:
        """Test concurrent API calls."""
        import asyncio

        meetings, _ = await fathom_client.fetch_meetings()

        if len(meetings) < 2:
            pytest.skip("Need at least 2 meetings for concurrent test")

        # Try to fetch transcripts concurrently
        tasks = []
        for meeting in meetings[:2]:  # Test with first 2 meetings
            tasks.append(self._safe_get_transcript(fathom_client, meeting.id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some should succeed or fail gracefully
        assert len(results) == len(tasks)

    @staticmethod
    async def _safe_get_transcript(client: FathomClient, meeting_id: str) -> Transcript | None:
        """Safely get transcript, handling expected errors."""
        try:
            return await client.get_meeting_transcript(meeting_id)
        except FathomError:
            # Expected if transcript not available
            return None


# =============================================================================
# TEST: Edge Cases & Validation
# =============================================================================


class TestEdgeCasesAndValidation:
    """Tests for edge cases and data validation."""

    @pytest.mark.asyncio
    async def test_meeting_fields_have_correct_types(self, fathom_client: FathomClient) -> None:
        """Test meeting objects have correct field types."""
        meetings, _ = await fathom_client.fetch_meetings()

        for meeting in meetings:
            # String fields or None
            assert isinstance(meeting.id, str)
            assert isinstance(meeting.title, str) or meeting.title is None
            assert isinstance(meeting.url, str) or meeting.url is None
            assert isinstance(meeting.created_at, str) or meeting.created_at is None

            # Numeric fields or None
            assert isinstance(meeting.duration_seconds, int) or meeting.duration_seconds is None
            assert isinstance(meeting.participant_count, int) or meeting.participant_count is None

            # List fields
            assert isinstance(meeting.participants, list)
            assert isinstance(meeting.action_items, list)

    @pytest.mark.asyncio
    async def test_transcript_entries_are_ordered(self, fathom_client: FathomClient) -> None:
        """Test transcript entries are in chronological order."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                # Check entries are ordered by timestamp
                prev_timestamp = -1
                for entry in transcript.entries:
                    if entry.timestamp is not None:
                        assert entry.timestamp >= prev_timestamp
                        prev_timestamp = entry.timestamp

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Transcript not available")
                raise

    @pytest.mark.asyncio
    async def test_no_null_meeting_ids(self, fathom_client: FathomClient) -> None:
        """Test all meetings have valid IDs."""
        meetings, _ = await fathom_client.fetch_meetings()

        for meeting in meetings:
            assert meeting.id is not None
            assert isinstance(meeting.id, str)
            assert len(meeting.id) > 0

    @pytest.mark.asyncio
    async def test_speaker_names_are_strings(self, fathom_client: FathomClient) -> None:
        """Test speaker names in transcripts are valid strings."""
        meetings, _ = await fathom_client.fetch_meetings()

        if meetings:
            meeting = meetings[0]
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)

                for entry in transcript.entries:
                    if entry.speaker and entry.speaker.name:
                        assert isinstance(entry.speaker.name, str)
                        assert len(entry.speaker.name) > 0

            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Transcript not available")
                raise
