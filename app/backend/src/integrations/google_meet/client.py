"""Google Meet API client with domain-wide delegation support.

Provides comprehensive access to Google Meet REST API v2:
- Spaces: Create and manage meeting rooms
- Conference Records: Access historical meeting data
- Participants: View who joined meetings
- Recordings: Access meeting recordings
- Transcripts: Access meeting transcripts

Follows the domain-wide delegation pattern documented in SELF-HEALING.md.
"""

import asyncio
import json
import logging
from typing import Any

import httpx

from src.integrations.google_meet.exceptions import (
    GoogleMeetAPIError,
    GoogleMeetAuthError,
    GoogleMeetConfigError,
    GoogleMeetNotFoundError,
    GoogleMeetPermissionError,
    GoogleMeetQuotaExceeded,
    GoogleMeetRateLimitError,
    GoogleMeetValidationError,
)
from src.integrations.google_meet.models import (
    ConferenceRecord,
    ConferenceRecordsListResponse,
    Participant,
    ParticipantSession,
    ParticipantSessionsListResponse,
    ParticipantsListResponse,
    Recording,
    RecordingsListResponse,
    Space,
    SpaceAccessType,
    Transcript,
    TranscriptEntriesListResponse,
    TranscriptEntry,
    TranscriptsListResponse,
)

logger = logging.getLogger(__name__)


class GoogleMeetClient:
    """Google Meet API client with domain-wide delegation support.

    This client supports three authentication methods:
    1. Service account credentials (credentials_json/credentials_str)
    2. Pre-obtained access token (access_token)
    3. Domain-wide delegation (credentials + delegated_user)

    When using domain-wide delegation, only the single broad scope is requested
    to avoid the "unauthorized_client" error that occurs when requesting
    multiple scopes when only some are authorized in the Admin Console.

    Example usage:
        # With domain-wide delegation (access user's meetings)
        client = GoogleMeetClient(
            credentials_json=service_account_creds,
            delegated_user="user@example.com"
        )
        await client.authenticate()
        space = await client.create_space()

        # With service account only (for your own resources)
        client = GoogleMeetClient(credentials_json=service_account_creds)
        await client.authenticate()
    """

    BASE_URL = "https://meet.googleapis.com"

    # Scopes for Google Meet API
    # For domain-wide delegation, use the broader scope
    DELEGATION_SCOPE = "https://www.googleapis.com/auth/meetings.space.created"

    # Default scopes when not using delegation
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/meetings.space.created",
        "https://www.googleapis.com/auth/meetings.space.readonly",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        access_token: str | None = None,
        delegated_user: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Google Meet client.

        Args:
            credentials_json: Service account credentials as a dictionary.
            credentials_str: Service account credentials as a JSON string.
            access_token: Pre-obtained OAuth2 access token.
            delegated_user: Email of user to impersonate via domain-wide delegation.
                           When set, uses single scope to avoid authorization errors.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.credentials_json = credentials_json
        self.credentials_str = credentials_str
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

        # Parse credentials string if provided
        if credentials_str and not credentials_json:
            try:
                self.credentials_json = json.loads(credentials_str)
            except json.JSONDecodeError as e:
                raise GoogleMeetConfigError(f"Invalid credentials JSON: {e}") from e

        # Validate we have some form of credentials
        if not any([self.credentials_json, self.access_token]):
            raise GoogleMeetConfigError(
                "Must provide either credentials_json, credentials_str, or access_token"
            )

    async def __aenter__(self) -> "GoogleMeetClient":
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def authenticate(self) -> None:
        """Authenticate and initialize the HTTP client."""
        if not self.access_token and self.credentials_json:
            await self._authenticate_service_account()

        if not self.access_token:
            raise GoogleMeetAuthError("No valid access token available")

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        logger.info("Google Meet client authenticated successfully")

    async def _authenticate_service_account(self) -> None:
        """Authenticate using service account credentials.

        IMPORTANT: When using domain-wide delegation (delegated_user is set),
        we request only the single broad scope that's authorized in the
        Google Workspace Admin Console. Requesting multiple scopes when only
        some are authorized causes authentication to fail entirely.
        """
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        # KEY PATTERN: Use single scope for domain-wide delegation
        # See ~/.claude/context/SELF-HEALING.md for details
        if self.delegated_user:
            scopes = [self.DELEGATION_SCOPE]
            logger.info(
                f"Using domain-wide delegation for: {self.delegated_user} "
                f"with scope: {self.DELEGATION_SCOPE}"
            )
        else:
            scopes = self.DEFAULT_SCOPES

        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scopes,
            )

            # Apply delegation if specified
            if self.delegated_user:
                credentials = credentials.with_subject(self.delegated_user)

            request = Request()
            credentials.refresh(request)
            self.access_token = credentials.token

        except Exception as e:
            error_msg = str(e)
            if "unauthorized_client" in error_msg.lower():
                raise GoogleMeetAuthError(
                    f"Domain-wide delegation failed. Ensure the scope "
                    f"'{self.DELEGATION_SCOPE}' is authorized in the Google "
                    f"Workspace Admin Console for this service account. "
                    f"Original error: {error_msg}"
                ) from e
            raise GoogleMeetAuthError(f"Service account authentication failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Google Meet API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Response data as dictionary.

        Raises:
            GoogleMeetAPIError: On API errors.
            GoogleMeetNotFoundError: When resource is not found.
            GoogleMeetRateLimitError: When rate limited.
        """
        if not self._client:
            raise GoogleMeetAuthError("Client not authenticated. Call authenticate() first.")

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json_data,
                )

                if response.status_code == 204:
                    return {}

                # Handle error responses
                if response.status_code >= 400:
                    await self._handle_error_response(response)

                return response.json() if response.text else {}

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GoogleMeetAPIError(
                    f"Request failed after {self.max_retries} retries: {e}"
                ) from e

        raise GoogleMeetAPIError(f"Request failed: {last_error}") from last_error

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text

        if response.status_code == 401:
            raise GoogleMeetAuthError(error_message)
        elif response.status_code == 403:
            if "quota" in error_message.lower():
                raise GoogleMeetQuotaExceeded(error_message)
            raise GoogleMeetPermissionError(error_message)
        elif response.status_code == 404:
            raise GoogleMeetNotFoundError(error_message)
        elif response.status_code == 400:
            raise GoogleMeetValidationError(error_message)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise GoogleMeetRateLimitError(
                error_message,
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise GoogleMeetAPIError(error_message, status_code=response.status_code)

    # =========================================================================
    # SPACE OPERATIONS
    # =========================================================================

    async def create_space(
        self,
        access_type: SpaceAccessType | None = None,
    ) -> Space:
        """Create a new meeting space.

        A space is a reusable meeting room. The meeting URI and code
        remain stable, allowing users to rejoin the same room.

        Args:
            access_type: Who can join the meeting (OPEN, TRUSTED, RESTRICTED).

        Returns:
            The created Space with meeting URI and code.
        """
        body: dict[str, Any] = {}

        if access_type:
            body["config"] = {"accessType": access_type.value}

        data = await self._request("POST", "/v2/spaces", json_data=body)
        return Space.model_validate(data)

    async def get_space(self, space_name: str) -> Space:
        """Get a meeting space by its resource name.

        Args:
            space_name: Resource name (e.g., "spaces/abc123").

        Returns:
            The Space details.
        """
        # Ensure proper format
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        data = await self._request("GET", f"/v2/{space_name}")
        return Space.model_validate(data)

    async def update_space(
        self,
        space_name: str,
        access_type: SpaceAccessType | None = None,
    ) -> Space:
        """Update a meeting space configuration.

        Args:
            space_name: Resource name (e.g., "spaces/abc123").
            access_type: New access type for the space.

        Returns:
            The updated Space.
        """
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        body: dict[str, Any] = {}
        update_mask_parts = []

        if access_type:
            body["config"] = {"accessType": access_type.value}
            update_mask_parts.append("config.accessType")

        params = {}
        if update_mask_parts:
            params["updateMask"] = ",".join(update_mask_parts)

        data = await self._request("PATCH", f"/v2/{space_name}", params=params, json_data=body)
        return Space.model_validate(data)

    async def end_active_conference(self, space_name: str) -> None:
        """End the active conference in a space.

        This forces all participants to leave the meeting.

        Args:
            space_name: Resource name (e.g., "spaces/abc123").
        """
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        await self._request("POST", f"/v2/{space_name}:endActiveConference")

    # =========================================================================
    # CONFERENCE RECORD OPERATIONS
    # =========================================================================

    async def list_conference_records(
        self,
        page_size: int = 25,
        page_token: str | None = None,
        filter_str: str | None = None,
    ) -> ConferenceRecordsListResponse:
        """List conference records (past meetings).

        Args:
            page_size: Maximum number of records to return (max 250).
            page_token: Token for pagination.
            filter_str: Filter expression (e.g., "space.name=spaces/abc123").

        Returns:
            List of conference records with pagination info.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token
        if filter_str:
            params["filter"] = filter_str

        data = await self._request("GET", "/v2/conferenceRecords", params=params)
        return ConferenceRecordsListResponse.model_validate(data)

    async def get_conference_record(self, conference_record_name: str) -> ConferenceRecord:
        """Get a conference record by its resource name.

        Args:
            conference_record_name: Resource name (e.g., "conferenceRecords/abc123").

        Returns:
            The conference record details.
        """
        if not conference_record_name.startswith("conferenceRecords/"):
            conference_record_name = f"conferenceRecords/{conference_record_name}"

        data = await self._request("GET", f"/v2/{conference_record_name}")
        return ConferenceRecord.model_validate(data)

    # =========================================================================
    # PARTICIPANT OPERATIONS
    # =========================================================================

    async def list_participants(
        self,
        conference_record_name: str,
        page_size: int = 100,
        page_token: str | None = None,
        filter_str: str | None = None,
    ) -> ParticipantsListResponse:
        """List participants of a conference.

        Args:
            conference_record_name: Parent conference record name.
            page_size: Maximum number to return (max 250).
            page_token: Pagination token.
            filter_str: Filter expression.

        Returns:
            List of participants.
        """
        if not conference_record_name.startswith("conferenceRecords/"):
            conference_record_name = f"conferenceRecords/{conference_record_name}"

        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token
        if filter_str:
            params["filter"] = filter_str

        data = await self._request(
            "GET", f"/v2/{conference_record_name}/participants", params=params
        )
        return ParticipantsListResponse.model_validate(data)

    async def get_participant(self, participant_name: str) -> Participant:
        """Get a participant by resource name.

        Args:
            participant_name: Full resource name.

        Returns:
            Participant details.
        """
        data = await self._request("GET", f"/v2/{participant_name}")
        return Participant.model_validate(data)

    async def list_participant_sessions(
        self,
        participant_name: str,
        page_size: int = 100,
        page_token: str | None = None,
        filter_str: str | None = None,
    ) -> ParticipantSessionsListResponse:
        """List sessions for a participant (join/leave events).

        Args:
            participant_name: Parent participant resource name.
            page_size: Maximum number to return.
            page_token: Pagination token.
            filter_str: Filter expression.

        Returns:
            List of participant sessions.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token
        if filter_str:
            params["filter"] = filter_str

        data = await self._request(
            "GET", f"/v2/{participant_name}/participantSessions", params=params
        )
        return ParticipantSessionsListResponse.model_validate(data)

    async def get_participant_session(self, session_name: str) -> ParticipantSession:
        """Get a participant session by resource name.

        Args:
            session_name: Full resource name.

        Returns:
            Participant session details.
        """
        data = await self._request("GET", f"/v2/{session_name}")
        return ParticipantSession.model_validate(data)

    # =========================================================================
    # RECORDING OPERATIONS
    # =========================================================================

    async def list_recordings(
        self,
        conference_record_name: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> RecordingsListResponse:
        """List recordings for a conference.

        Args:
            conference_record_name: Parent conference record name.
            page_size: Maximum number to return.
            page_token: Pagination token.

        Returns:
            List of recordings.
        """
        if not conference_record_name.startswith("conferenceRecords/"):
            conference_record_name = f"conferenceRecords/{conference_record_name}"

        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("GET", f"/v2/{conference_record_name}/recordings", params=params)
        return RecordingsListResponse.model_validate(data)

    async def get_recording(self, recording_name: str) -> Recording:
        """Get a recording by resource name.

        Args:
            recording_name: Full resource name.

        Returns:
            Recording details including Drive file info.
        """
        data = await self._request("GET", f"/v2/{recording_name}")
        return Recording.model_validate(data)

    # =========================================================================
    # TRANSCRIPT OPERATIONS
    # =========================================================================

    async def list_transcripts(
        self,
        conference_record_name: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> TranscriptsListResponse:
        """List transcripts for a conference.

        Args:
            conference_record_name: Parent conference record name.
            page_size: Maximum number to return.
            page_token: Pagination token.

        Returns:
            List of transcripts.
        """
        if not conference_record_name.startswith("conferenceRecords/"):
            conference_record_name = f"conferenceRecords/{conference_record_name}"

        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token

        data = await self._request(
            "GET", f"/v2/{conference_record_name}/transcripts", params=params
        )
        return TranscriptsListResponse.model_validate(data)

    async def get_transcript(self, transcript_name: str) -> Transcript:
        """Get a transcript by resource name.

        Args:
            transcript_name: Full resource name.

        Returns:
            Transcript details including Docs file info.
        """
        data = await self._request("GET", f"/v2/{transcript_name}")
        return Transcript.model_validate(data)

    async def list_transcript_entries(
        self,
        transcript_name: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> TranscriptEntriesListResponse:
        """List transcript entries (individual speaker turns).

        Args:
            transcript_name: Parent transcript resource name.
            page_size: Maximum number to return (max 250).
            page_token: Pagination token.

        Returns:
            List of transcript entries.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 250)}
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("GET", f"/v2/{transcript_name}/entries", params=params)
        return TranscriptEntriesListResponse.model_validate(data)

    async def get_transcript_entry(self, entry_name: str) -> TranscriptEntry:
        """Get a transcript entry by resource name.

        Args:
            entry_name: Full resource name.

        Returns:
            Transcript entry with speaker and text.
        """
        data = await self._request("GET", f"/v2/{entry_name}")
        return TranscriptEntry.model_validate(data)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def get_all_conference_records(
        self,
        filter_str: str | None = None,
        max_records: int | None = None,
    ) -> list[ConferenceRecord]:
        """Get all conference records with automatic pagination.

        Args:
            filter_str: Optional filter expression.
            max_records: Maximum total records to fetch (None for all).

        Returns:
            List of all conference records.
        """
        all_records: list[ConferenceRecord] = []
        page_token: str | None = None

        while True:
            response = await self.list_conference_records(
                page_size=250,
                page_token=page_token,
                filter_str=filter_str,
            )

            all_records.extend(response.conference_records)

            if max_records and len(all_records) >= max_records:
                return all_records[:max_records]

            if not response.next_page_token:
                break

            page_token = response.next_page_token

        return all_records

    async def get_all_participants(
        self,
        conference_record_name: str,
        max_participants: int | None = None,
    ) -> list[Participant]:
        """Get all participants with automatic pagination.

        Args:
            conference_record_name: Conference record to get participants for.
            max_participants: Maximum to fetch (None for all).

        Returns:
            List of all participants.
        """
        all_participants: list[Participant] = []
        page_token: str | None = None

        while True:
            response = await self.list_participants(
                conference_record_name,
                page_size=250,
                page_token=page_token,
            )

            all_participants.extend(response.participants)

            if max_participants and len(all_participants) >= max_participants:
                return all_participants[:max_participants]

            if not response.next_page_token:
                break

            page_token = response.next_page_token

        return all_participants

    async def generic_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a generic API request for future-proofing.

        Allows calling any Google Meet API endpoint, even ones not yet
        wrapped by this client.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            endpoint: API endpoint path (e.g., "/v2/spaces").
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Raw response data.
        """
        return await self._request(method, endpoint, params, json_data)
