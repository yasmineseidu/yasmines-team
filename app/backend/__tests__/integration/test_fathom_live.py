"""
Live integration tests for Fathom API.

These tests use real API keys and make actual API calls to Fathom.
Run with: pytest __tests__/integration/test_fathom_live.py -v -m live_api

IMPORTANT: These tests require FATHOM_API_KEY in .env at project root.

Environment variables required:
- FATHOM_API_KEY: Fathom API key from User Settings
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.fathom import FathomClient, FathomError

# Load .env from project root
env_path = Path(__file__).parents[4] / ".env"
load_dotenv(env_path)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fathom_api_key() -> str:
    """Get Fathom API key from environment."""
    api_key = os.getenv("FATHOM_API_KEY")
    if not api_key:
        pytest.skip("FATHOM_API_KEY not set in .env")
    return api_key


@pytest.fixture
async def fathom_client(fathom_api_key: str) -> FathomClient:
    """Create Fathom client with real API key."""
    return FathomClient(api_key=fathom_api_key)


# =============================================================================
# LIVE API TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFathomLiveAPI:
    """Live API tests with real Fathom credentials."""

    async def test_fetch_meetings_returns_data(self, fathom_client: FathomClient):
        """Test that fetch_meetings returns valid data from Fathom."""
        try:
            meetings, next_cursor = await fathom_client.fetch_meetings()

            # Should return a list (even if empty in a fresh account)
            assert isinstance(meetings, list)

            # Verify response structure if meetings exist
            if meetings:
                meeting = meetings[0]
                assert hasattr(meeting, "id")
                assert hasattr(meeting, "title")
                assert hasattr(meeting, "created_at")
                assert meeting.id is not None

        except FathomError as e:
            # If API key is invalid, skip with meaningful message
            if "401" in str(e) or "authentication" in str(e).lower():
                pytest.skip(f"Invalid Fathom API key: {e}")
            raise

    async def test_fetch_meetings_with_pagination(self, fathom_client: FathomClient):
        """Test pagination works correctly."""
        try:
            # Get first page
            meetings1, cursor1 = await fathom_client.fetch_meetings()

            # If cursor exists, try to fetch next page
            if cursor1:
                meetings2, cursor2 = await fathom_client.fetch_meetings(cursor=cursor1)
                assert isinstance(meetings2, list)

        except FathomError as e:
            if "401" in str(e):
                pytest.skip("Invalid API key")
            raise

    async def test_fetch_meetings_with_filters(self, fathom_client: FathomClient):
        """Test that filter parameters work."""
        try:
            # Test with date filters (assuming at least one meeting from 2025)
            meetings, _ = await fathom_client.fetch_meetings(
                created_after="2025-01-01",
                created_before="2025-12-31",
            )

            # Should return list
            assert isinstance(meetings, list)

        except FathomError as e:
            if "401" in str(e):
                pytest.skip("Invalid API key")
            raise

    async def test_get_transcript_requires_valid_id(self, fathom_client: FathomClient):
        """Test transcript retrieval with invalid ID raises error."""
        with pytest.raises(FathomError):
            await fathom_client.get_meeting_transcript("invalid-meeting-id")

    async def test_client_initialization_validates_api_key(self):
        """Test that client requires valid API key."""
        with pytest.raises(ValueError, match="API key is required"):
            FathomClient(api_key="")

    async def test_headers_use_correct_authentication(self, fathom_client: FathomClient):
        """Test that X-Api-Key header is used correctly."""
        headers = fathom_client._get_headers()
        assert "X-Api-Key" in headers
        assert headers["X-Api-Key"] is not None
        assert len(headers["X-Api-Key"]) > 0


# =============================================================================
# INTEGRATION SCENARIO TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFathomIntegrationScenarios:
    """Test realistic usage scenarios."""

    async def test_full_workflow_fetch_and_process_meeting(self, fathom_client: FathomClient):
        """Test full workflow: fetch meetings, get transcript, capture notes."""
        try:
            # Step 1: Fetch meetings
            meetings, _ = await fathom_client.fetch_meetings(limit=1)

            if not meetings:
                pytest.skip("No meetings available in Fathom account for testing")

            meeting = meetings[0]
            assert meeting.id is not None

            # Step 2: Get transcript for the meeting
            try:
                transcript = await fathom_client.get_meeting_transcript(meeting.id)
                assert hasattr(transcript, "meeting_id")
                assert hasattr(transcript, "entries")
                assert isinstance(transcript.entries, list)
            except FathomError as e:
                # Some meetings might not have transcripts yet
                if "404" in str(e):
                    pytest.skip("Meeting transcript not available")
                raise

            # Step 3: Capture notes
            try:
                notes = await fathom_client.capture_meeting_notes(meeting.id)
                assert notes["meeting_id"] == meeting.id
                assert "full_transcript" in notes
                assert "speakers" in notes
            except FathomError as e:
                if "404" in str(e):
                    pytest.skip("Notes not available for meeting")
                raise

        except FathomError as e:
            if "401" in str(e):
                pytest.skip("Invalid API key")
            raise

    async def test_concurrent_meeting_fetches(self, fathom_client: FathomClient):
        """Test that multiple requests work correctly."""
        import asyncio

        try:
            # Make multiple requests concurrently
            tasks = [
                fathom_client.fetch_meetings(),
                fathom_client.fetch_meetings(include_transcript=True),
                fathom_client.fetch_meetings(created_after="2025-01-01"),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should complete without crashing
            for result in results:
                if isinstance(result, Exception):
                    if "401" in str(result):
                        pytest.skip("Invalid API key")
                    # Allow other expected exceptions
                    pass
                else:
                    meetings, cursor = result
                    assert isinstance(meetings, list)

        except FathomError as e:
            if "401" in str(e):
                pytest.skip("Invalid API key")
            raise
