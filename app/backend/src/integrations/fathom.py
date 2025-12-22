"""
Fathom.ai Meeting Intelligence API integration client.

Provides meeting transcription, notetaking, and meeting data extraction
for retrieving meeting recordings, transcripts, and summaries.

API Documentation: https://developers.fathom.ai
API Version: External V1
Base URL: https://api.fathom.ai

Features:
- List meetings with pagination (10 most recent by default)
- Retrieve meeting transcripts with speaker identification
- Extract meeting metadata (title, date, participants, duration)
- Filter meetings by date range, recorded_by, etc.
- Support for pagination via cursor
- Meeting summaries and action items

Rate Limits:
- 60 API calls per minute across all API keys

Authentication:
- API Key in X-Api-Key header
- OAuth 2.0 for public apps

Example:
    >>> from src.integrations.fathom import FathomClient
    >>> client = FathomClient(api_key="your-api-key")
    >>> meetings = await client.fetch_meetings()
    >>> for meeting in meetings:
    ...     print(f"{meeting.title} - {meeting.created_at}")
    >>> transcript = await client.get_meeting_transcript(meeting.id)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class FathomError(IntegrationError):
    """Fathom API-specific error."""

    pass


class FathomAuthError(AuthenticationError):
    """Fathom authentication error."""

    pass


class FathomRateLimitError(RateLimitError):
    """Fathom rate limit error."""

    pass


@dataclass
class Speaker:
    """A speaker in a meeting."""

    id: str | None = None
    name: str | None = None
    email: str | None = None


@dataclass
class TranscriptEntry:
    """A single entry in a meeting transcript."""

    speaker: Speaker | None = None
    text: str | None = None
    timestamp: int | None = None  # Milliseconds from start
    timestamp_seconds: float | None = None  # Derived from timestamp


@dataclass
class Meeting:
    """A meeting from Fathom API."""

    id: str
    title: str | None = None
    url: str | None = None
    created_at: str | None = None
    duration_seconds: int | None = None
    participants: list[str] = field(default_factory=list)
    participant_count: int | None = None
    transcript_url: str | None = None
    summary: str | None = None
    action_items: list[str] = field(default_factory=list)
    recorded_by: str | None = None
    video_url: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcript:
    """A complete meeting transcript."""

    meeting_id: str
    entries: list[TranscriptEntry] = field(default_factory=list)
    text: str | None = None  # Full transcript as text
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class FathomResponse:
    """Generic Fathom API response wrapper."""

    data: Any = None
    success: bool = True
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class FathomClient(BaseIntegrationClient):
    """Async client for Fathom.ai API."""

    def __init__(self, api_key: str) -> None:
        """Initialize Fathom client.

        Args:
            api_key: Fathom API key from user settings.

        Raises:
            ValueError: If api_key is empty.
        """
        if not api_key:
            raise ValueError("Fathom API key is required")

        super().__init__(
            name="fathom",
            base_url="https://api.fathom.ai",
            api_key=api_key,
            timeout=30.0,
            max_retries=3,
            retry_base_delay=1.0,
        )
        logger.info(f"Initialized {self.name} client")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Fathom API requests.

        Fathom uses X-Api-Key header instead of Bearer token.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def fetch_meetings(
        self,
        include_transcript: bool = False,
        recorded_by: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        cursor: str | None = None,
    ) -> tuple[list[Meeting], str | None]:
        """Fetch meetings from Fathom.

        Args:
            include_transcript: Include transcript in response.
            recorded_by: Filter by who recorded the meeting.
            created_after: Filter meetings created after this date (ISO 8601).
            created_before: Filter meetings created before this date (ISO 8601).
            cursor: Pagination cursor for retrieving next page.

        Returns:
            Tuple of (list of meetings, next_cursor for pagination).

        Raises:
            FathomError: If API request fails.
        """
        params: dict[str, Any] = {}
        if include_transcript:
            params["include_transcript"] = "true"
        if recorded_by:
            params["recorded_by"] = recorded_by
        if created_after:
            params["created_after"] = created_after
        if created_before:
            params["created_before"] = created_before
        if cursor:
            params["cursor"] = cursor

        try:
            response = await self._request_with_retry(
                "GET",
                "/external/v1/meetings",
                params=params,
            )

            meetings = []
            if isinstance(response.get("meetings"), list):
                for meeting_data in response["meetings"]:
                    meeting = self._parse_meeting(meeting_data)
                    meetings.append(meeting)

            next_cursor = response.get("next_cursor")

            logger.info(f"Fetched {len(meetings)} meetings from Fathom")
            return meetings, next_cursor

        except Exception as e:
            error_msg = f"Failed to fetch meetings: {e}"
            logger.error(error_msg)
            if isinstance(e, FathomError):
                raise
            raise FathomError(error_msg) from e

    async def get_meeting_transcript(
        self,
        recording_id: str,
    ) -> Transcript:
        """Get transcript for a meeting.

        Args:
            recording_id: The recording/meeting ID.

        Returns:
            Transcript object with entries.

        Raises:
            FathomError: If API request fails.
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"/external/v1/recordings/{recording_id}/transcript",
            )

            entries = []
            if isinstance(response.get("transcript"), list):
                for entry_data in response["transcript"]:
                    entry = self._parse_transcript_entry(entry_data)
                    entries.append(entry)

            # Also extract full text transcript if available
            text_transcript = response.get("text")

            transcript = Transcript(
                meeting_id=recording_id,
                entries=entries,
                text=text_transcript,
                raw_response=response,
            )

            logger.info(
                f"Fetched transcript for meeting {recording_id} " f"with {len(entries)} entries"
            )
            return transcript

        except Exception as e:
            error_msg = f"Failed to fetch transcript for {recording_id}: {e}"
            logger.error(error_msg)
            if isinstance(e, FathomError):
                raise
            raise FathomError(error_msg) from e

    async def capture_meeting_notes(
        self,
        recording_id: str,
    ) -> dict[str, Any]:
        """Capture structured notes from a meeting recording.

        Extracts transcript and attempts to parse summaries and action items.

        Args:
            recording_id: The recording/meeting ID.

        Returns:
            Dictionary with structured notes (summary, action items, etc).

        Raises:
            FathomError: If API request fails.
        """
        try:
            # Get transcript
            transcript = await self.get_meeting_transcript(recording_id)

            # Build notes structure
            notes = {
                "meeting_id": recording_id,
                "transcript_entries": len(transcript.entries),
                "full_transcript": transcript.text or "",
                "speakers": self._extract_unique_speakers(transcript),
                "raw_response": transcript.raw_response,
            }

            logger.info(f"Captured notes for meeting {recording_id}")
            return notes

        except Exception as e:
            error_msg = f"Failed to capture notes for {recording_id}: {e}"
            logger.error(error_msg)
            if isinstance(e, FathomError):
                raise
            raise FathomError(error_msg) from e

    def _parse_meeting(self, data: dict[str, Any]) -> Meeting:
        """Parse meeting data from API response.

        Args:
            data: Raw meeting data from API.

        Returns:
            Parsed Meeting object.
        """
        # Extract participants
        participants = []
        if isinstance(data.get("participants"), list):
            participants = [p.get("name", p.get("email", "Unknown")) for p in data["participants"]]

        # Extract action items
        action_items = []
        if isinstance(data.get("action_items"), list):
            action_items = [item.get("text", str(item)) for item in data["action_items"]]

        return Meeting(
            id=data.get("id", ""),
            title=data.get("title"),
            url=data.get("url"),
            created_at=data.get("created_at"),
            duration_seconds=data.get("duration"),
            participants=participants,
            participant_count=data.get("participant_count"),
            transcript_url=data.get("transcript_url"),
            summary=data.get("summary"),
            action_items=action_items,
            recorded_by=data.get("recorded_by"),
            video_url=data.get("video_url"),
            raw_response=data,
        )

    def _parse_transcript_entry(self, data: dict[str, Any]) -> TranscriptEntry:
        """Parse transcript entry from API response.

        Args:
            data: Raw transcript entry data.

        Returns:
            Parsed TranscriptEntry object.
        """
        # Parse speaker info
        speaker_data = data.get("speaker")
        speaker = None
        if speaker_data:
            speaker = Speaker(
                id=speaker_data.get("id"),
                name=speaker_data.get("name"),
                email=speaker_data.get("email"),
            )

        # Calculate timestamp_seconds from timestamp in milliseconds
        timestamp = data.get("timestamp")
        timestamp_seconds = None
        if timestamp is not None:
            timestamp_seconds = timestamp / 1000.0

        return TranscriptEntry(
            speaker=speaker,
            text=data.get("text"),
            timestamp=timestamp,
            timestamp_seconds=timestamp_seconds,
        )

    def _extract_unique_speakers(self, transcript: Transcript) -> list[str]:
        """Extract unique speaker names from transcript.

        Args:
            transcript: The transcript to analyze.

        Returns:
            List of unique speaker names.
        """
        speakers = set()
        for entry in transcript.entries:
            if entry.speaker and entry.speaker.name:
                speakers.add(entry.speaker.name)
        return sorted(speakers)
