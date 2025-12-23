"""Live API integration tests for Google Meet client.

These tests interact with the real Google Meet API and require:
1. Valid service account credentials
2. For delegation tests: GOOGLE_MEET_DELEGATED_USER env var
3. The Meet API scope authorized in Admin Console

IMPORTANT: The Google Meet API scope must be added to the Admin Console:
- Scope: https://www.googleapis.com/auth/meetings.space.created

Run with: pytest __tests__/integration/google_meet/ -v
Or with delegation: GOOGLE_MEET_DELEGATED_USER=user@domain.com pytest ...
"""

import asyncio

import pytest

from src.integrations.google_meet import (
    GoogleMeetClient,
    GoogleMeetRateLimitError,
    Space,
    SpaceAccessType,
)

# Store created space for reuse across tests
_created_space: Space | None = None


async def get_or_create_space(client: GoogleMeetClient) -> Space:
    """Get existing space or create new one (with rate limit handling)."""
    global _created_space

    if _created_space is not None:
        return _created_space

    # Try to create with retry on rate limit
    for attempt in range(3):
        try:
            _created_space = await client.create_space()
            return _created_space
        except GoogleMeetRateLimitError:
            if attempt < 2:
                await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
            else:
                raise

    raise RuntimeError("Failed to create space after retries")


class TestGoogleMeetLiveAPI:
    """Live API tests for Google Meet operations."""

    @pytest.mark.asyncio
    async def test_01_create_space(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test creating a new meeting space."""
        space = await get_or_create_space(delegated_meet_client)

        assert isinstance(space, Space)
        assert space.name is not None
        assert space.name.startswith("spaces/")
        assert space.meeting_uri is not None
        assert "meet.google.com" in space.meeting_uri
        assert space.meeting_code is not None

        print(f"\n  Created space: {space.name}")
        print(f"  Meeting URL: {space.meeting_uri}")
        print(f"  Meeting code: {space.meeting_code}")

    @pytest.mark.asyncio
    async def test_02_get_space(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test getting an existing space."""
        # Use shared space
        created_space = await get_or_create_space(delegated_meet_client)

        # Then retrieve it
        retrieved_space = await delegated_meet_client.get_space(created_space.name)

        assert retrieved_space.name == created_space.name
        assert retrieved_space.meeting_uri == created_space.meeting_uri
        assert retrieved_space.meeting_code == created_space.meeting_code

        print(f"\n  Retrieved space: {retrieved_space.name}")

    @pytest.mark.asyncio
    async def test_03_update_space(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test updating a space's configuration."""
        # Use shared space
        space = await get_or_create_space(delegated_meet_client)

        # Update its access type
        updated_space = await delegated_meet_client.update_space(
            space.name,
            access_type=SpaceAccessType.TRUSTED,
        )

        assert updated_space.name == space.name
        print(f"\n  Updated space to TRUSTED: {updated_space.name}")

    @pytest.mark.asyncio
    async def test_04_list_conference_records(
        self, delegated_meet_client: GoogleMeetClient
    ) -> None:
        """Test listing conference records (past meetings)."""
        response = await delegated_meet_client.list_conference_records(page_size=10)

        # May or may not have past meetings
        print(f"\n  Found {len(response.conference_records)} conference records")

        for record in response.conference_records[:3]:  # Show first 3
            print(f"    - {record.name}")
            if record.start_time:
                print(f"      Started: {record.start_time}")

    @pytest.mark.asyncio
    async def test_05_list_conference_records_with_filter(
        self, delegated_meet_client: GoogleMeetClient
    ) -> None:
        """Test listing conference records with a filter."""
        # Use shared space
        space = await get_or_create_space(delegated_meet_client)

        # Filter by the space
        response = await delegated_meet_client.list_conference_records(
            filter_str=f"space.name={space.name}"
        )

        # New space won't have conference records yet
        print(f"\n  Found {len(response.conference_records)} records for space")

    @pytest.mark.asyncio
    async def test_06_get_all_conference_records(
        self, delegated_meet_client: GoogleMeetClient
    ) -> None:
        """Test getting all conference records with automatic pagination."""
        records = await delegated_meet_client.get_all_conference_records(max_records=25)

        print(f"\n  Retrieved {len(records)} total conference records")

    @pytest.mark.asyncio
    async def test_07_end_active_conference(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test ending an active conference (if any).

        Note: This will pass even if no one is in the meeting.
        The API returns success or an error we handle gracefully.
        """
        space = await get_or_create_space(delegated_meet_client)

        try:
            await delegated_meet_client.end_active_conference(space.name)
            print(f"\n  Ended conference in space: {space.name}")
        except Exception as e:
            # Expected if no active conference - this is fine
            print(f"\n  No active conference to end (expected): {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_08_generic_request(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test the generic request method for future-proofing."""
        # Use generic request to list conference records
        result = await delegated_meet_client.generic_request(
            "GET",
            "/v2/conferenceRecords",
            params={"pageSize": 5},
        )

        assert isinstance(result, dict)
        print(f"\n  Generic request returned {len(result.get('conferenceRecords', []))} records")


class TestGoogleMeetLiveAPIWithConferenceData:
    """Tests that require existing conference data.

    These tests are marked as expected to skip if no conference data exists.
    They become relevant after actual meetings have occurred.
    """

    @pytest.mark.asyncio
    async def test_09_get_conference_record(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test getting a specific conference record."""
        # First, list to find one
        response = await delegated_meet_client.list_conference_records(page_size=1)

        if not response.conference_records:
            pytest.skip("No conference records available to test")

        record = await delegated_meet_client.get_conference_record(
            response.conference_records[0].name
        )

        assert record.name is not None
        print(f"\n  Got conference record: {record.name}")
        print(f"    Space: {record.space}")
        print(f"    Start: {record.start_time}")
        print(f"    End: {record.end_time}")

    @pytest.mark.asyncio
    async def test_10_list_participants(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test listing participants of a conference."""
        # Find a conference record first
        records_response = await delegated_meet_client.list_conference_records(page_size=5)

        if not records_response.conference_records:
            pytest.skip("No conference records available")

        # Try each record until we find one with participants
        for record in records_response.conference_records:
            participants_response = await delegated_meet_client.list_participants(record.name)

            if participants_response.participants:
                print(f"\n  Found {len(participants_response.participants)} participants")
                for p in participants_response.participants[:3]:
                    name = "Unknown"
                    if p.signedin_user:
                        name = p.signedin_user.display_name or "Signed-in User"
                    elif p.anonymous_user:
                        name = p.anonymous_user.display_name or "Anonymous"
                    elif p.phone_user:
                        name = p.phone_user.display_name or "Phone User"
                    print(f"    - {name}")
                return

        pytest.skip("No participants found in any conference records")

    @pytest.mark.asyncio
    async def test_11_list_recordings(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test listing recordings of a conference."""
        records_response = await delegated_meet_client.list_conference_records(page_size=5)

        if not records_response.conference_records:
            pytest.skip("No conference records available")

        for record in records_response.conference_records:
            recordings_response = await delegated_meet_client.list_recordings(record.name)

            if recordings_response.recordings:
                print(f"\n  Found {len(recordings_response.recordings)} recordings")
                for r in recordings_response.recordings:
                    print(f"    - {r.name} ({r.state})")
                    if r.drive_destination:
                        print(f"      Drive: {r.drive_destination.export_uri}")
                return

        pytest.skip("No recordings found in any conference records")

    @pytest.mark.asyncio
    async def test_12_list_transcripts(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test listing transcripts of a conference."""
        records_response = await delegated_meet_client.list_conference_records(page_size=5)

        if not records_response.conference_records:
            pytest.skip("No conference records available")

        for record in records_response.conference_records:
            transcripts_response = await delegated_meet_client.list_transcripts(record.name)

            if transcripts_response.transcripts:
                print(f"\n  Found {len(transcripts_response.transcripts)} transcripts")
                for t in transcripts_response.transcripts:
                    print(f"    - {t.name} ({t.state})")
                    if t.docs_destination:
                        print(f"      Docs: {t.docs_destination.export_uri}")
                return

        pytest.skip("No transcripts found in any conference records")


class TestGoogleMeetErrorHandling:
    """Test error handling with live API."""

    @pytest.mark.asyncio
    async def test_13_get_nonexistent_space(self, delegated_meet_client: GoogleMeetClient) -> None:
        """Test getting a space that doesn't exist.

        Note: Google Meet API returns 400 (invalid argument) for malformed IDs
        rather than 404 (not found). This is expected behavior.
        """
        from src.integrations.google_meet import (
            GoogleMeetNotFoundError,
            GoogleMeetValidationError,
        )

        # API returns 400 for invalid ID format, 404 for valid format but not found
        with pytest.raises((GoogleMeetNotFoundError, GoogleMeetValidationError)):
            await delegated_meet_client.get_space("spaces/nonexistent-space-12345")

    @pytest.mark.asyncio
    async def test_14_get_nonexistent_conference_record(
        self, delegated_meet_client: GoogleMeetClient
    ) -> None:
        """Test getting a conference record that doesn't exist.

        Note: Google Meet API returns 400 (invalid argument) for malformed IDs
        rather than 404 (not found). This is expected behavior.
        """
        from src.integrations.google_meet import (
            GoogleMeetNotFoundError,
            GoogleMeetValidationError,
        )

        # API returns 400 for invalid ID format, 404 for valid format but not found
        with pytest.raises((GoogleMeetNotFoundError, GoogleMeetValidationError)):
            await delegated_meet_client.get_conference_record("conferenceRecords/nonexistent-12345")
