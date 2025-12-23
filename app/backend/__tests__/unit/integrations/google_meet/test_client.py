"""Unit tests for Google Meet client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from __tests__.fixtures.google_meet_fixtures import (
    ERROR_RESPONSES,
    MOCK_SERVICE_ACCOUNT_CREDENTIALS,
    PAGINATED_RESPONSES,
    SAMPLE_RESPONSES,
)
from src.integrations.google_meet.client import GoogleMeetClient
from src.integrations.google_meet.exceptions import (
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
    Participant,
    Recording,
    Space,
    SpaceAccessType,
    Transcript,
    TranscriptEntry,
)


class TestGoogleMeetClientInitialization:
    """Tests for GoogleMeetClient initialization."""

    def test_init_with_credentials_json(self) -> None:
        """Should initialize with credentials_json parameter."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS
        assert client.access_token is None
        assert client.delegated_user is None

    def test_init_with_credentials_str(self) -> None:
        """Should initialize with credentials_str parameter."""
        creds_str = json.dumps(MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client = GoogleMeetClient(credentials_str=creds_str)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS

    def test_init_with_access_token(self) -> None:
        """Should initialize with pre-obtained access token."""
        client = GoogleMeetClient(access_token="test-token-123")
        assert client.access_token == "test-token-123"
        assert client.credentials_json is None

    def test_init_with_delegated_user(self) -> None:
        """Should initialize with delegated_user for domain-wide delegation."""
        client = GoogleMeetClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            delegated_user="user@example.com",
        )
        assert client.delegated_user == "user@example.com"

    def test_init_with_invalid_json_str_raises(self) -> None:
        """Should raise error for invalid JSON string."""
        with pytest.raises(GoogleMeetConfigError) as exc_info:
            GoogleMeetClient(credentials_str="not valid json")
        assert "Invalid credentials JSON" in str(exc_info.value)

    def test_init_without_credentials_raises(self) -> None:
        """Should raise error when no credentials provided."""
        with pytest.raises(GoogleMeetConfigError) as exc_info:
            GoogleMeetClient()
        assert "Must provide either" in str(exc_info.value)

    def test_init_sets_default_timeout(self) -> None:
        """Should set default timeout of 30 seconds."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.timeout == 30.0

    def test_init_sets_default_max_retries(self) -> None:
        """Should set default max_retries of 3."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.max_retries == 3

    def test_init_custom_timeout_and_retries(self) -> None:
        """Should accept custom timeout and retry settings."""
        client = GoogleMeetClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            timeout=60.0,
            max_retries=5,
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5


class TestGoogleMeetClientAuthentication:
    """Tests for authentication methods."""

    @pytest.fixture
    def client(self) -> GoogleMeetClient:
        """Create client instance for tests."""
        return GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

    @pytest.mark.asyncio
    async def test_authenticate_service_account_success(self, client: GoogleMeetClient) -> None:
        """Should authenticate successfully with service account."""
        mock_credentials = MagicMock()
        mock_credentials.token = "test-access-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        assert client.access_token == "test-access-token"
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_delegation_uses_single_scope(self) -> None:
        """Should use single scope when delegated_user is set."""
        client = GoogleMeetClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            delegated_user="user@example.com",
        )

        mock_credentials = MagicMock()
        mock_credentials.token = "delegated-token"
        mock_credentials.with_subject = MagicMock(return_value=mock_credentials)

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

            # Verify single scope was used
            call_args = mock_creds.call_args
            scopes = call_args.kwargs.get("scopes", call_args[1].get("scopes"))
            assert len(scopes) == 1
            assert scopes[0] == client.DELEGATION_SCOPE

            # Verify delegation was applied
            mock_credentials.with_subject.assert_called_once_with("user@example.com")

    @pytest.mark.asyncio
    async def test_authenticate_without_delegation_uses_multiple_scopes(
        self, client: GoogleMeetClient
    ) -> None:
        """Should use multiple scopes when no delegation."""
        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

            call_args = mock_creds.call_args
            scopes = call_args.kwargs.get("scopes", call_args[1].get("scopes"))
            assert len(scopes) == len(client.DEFAULT_SCOPES)

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Should work as async context manager."""
        mock_credentials = MagicMock()
        mock_credentials.token = "context-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                async with GoogleMeetClient(
                    credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS
                ) as client:
                    assert client.access_token == "context-token"
                    assert client._client is not None

    @pytest.mark.asyncio
    async def test_close_clears_client(self, client: GoogleMeetClient) -> None:
        """Should clear HTTP client on close."""
        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        assert client._client is not None
        await client.close()
        assert client._client is None


class TestGoogleMeetClientSpaceOperations:
    """Tests for space (meeting room) operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_create_space_success(self, authenticated_client: GoogleMeetClient) -> None:
        """Should create a new meeting space."""
        mock_response = httpx.Response(
            200,
            json=SAMPLE_RESPONSES["space"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        space = await authenticated_client.create_space()

        assert isinstance(space, Space)
        assert space.name == "spaces/abc123"
        assert space.meeting_uri == "https://meet.google.com/abc-defg-hij"
        assert space.meeting_code == "abc-defg-hij"

    @pytest.mark.asyncio
    async def test_create_space_with_access_type(
        self, authenticated_client: GoogleMeetClient
    ) -> None:
        """Should create space with specified access type."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["space"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        space = await authenticated_client.create_space(access_type=SpaceAccessType.TRUSTED)

        assert isinstance(space, Space)
        # Verify the request body contained access type
        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["json"]["config"]["accessType"] == "TRUSTED"

    @pytest.mark.asyncio
    async def test_get_space_success(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get space by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["space"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        space = await authenticated_client.get_space("spaces/abc123")

        assert isinstance(space, Space)
        assert space.name == "spaces/abc123"

    @pytest.mark.asyncio
    async def test_get_space_adds_prefix(self, authenticated_client: GoogleMeetClient) -> None:
        """Should add 'spaces/' prefix if missing."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["space"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.get_space("abc123")

        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["url"] == "/v2/spaces/abc123"

    @pytest.mark.asyncio
    async def test_update_space_success(self, authenticated_client: GoogleMeetClient) -> None:
        """Should update space configuration."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["space_with_conference"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        space = await authenticated_client.update_space(
            "spaces/abc123",
            access_type=SpaceAccessType.TRUSTED,
        )

        assert isinstance(space, Space)
        call_args = authenticated_client._client.request.call_args
        assert "updateMask" in call_args.kwargs["params"]

    @pytest.mark.asyncio
    async def test_end_active_conference(self, authenticated_client: GoogleMeetClient) -> None:
        """Should end active conference in a space."""
        mock_response = httpx.Response(204, content=b"")
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.end_active_conference("spaces/abc123")

        call_args = authenticated_client._client.request.call_args
        assert ":endActiveConference" in call_args.kwargs["url"]


class TestGoogleMeetClientConferenceRecordOperations:
    """Tests for conference record operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_list_conference_records(self, authenticated_client: GoogleMeetClient) -> None:
        """Should list conference records."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["conference_records_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        response = await authenticated_client.list_conference_records()

        assert len(response.conference_records) == 2
        assert all(isinstance(r, ConferenceRecord) for r in response.conference_records)

    @pytest.mark.asyncio
    async def test_list_conference_records_with_filter(
        self, authenticated_client: GoogleMeetClient
    ) -> None:
        """Should pass filter to API."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["conference_records_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.list_conference_records(filter_str="space.name=spaces/abc123")

        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["params"]["filter"] == "space.name=spaces/abc123"

    @pytest.mark.asyncio
    async def test_get_conference_record(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get conference record by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["conference_record"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        record = await authenticated_client.get_conference_record("conferenceRecords/conf-123")

        assert isinstance(record, ConferenceRecord)
        assert record.name == "conferenceRecords/conf-123"
        assert record.space == "spaces/abc123"

    @pytest.mark.asyncio
    async def test_get_all_conference_records_pagination(
        self, authenticated_client: GoogleMeetClient
    ) -> None:
        """Should handle pagination automatically."""
        page1_response = httpx.Response(200, json=PAGINATED_RESPONSES["conference_records_page1"])
        page2_response = httpx.Response(200, json=PAGINATED_RESPONSES["conference_records_page2"])

        authenticated_client._client.request = AsyncMock(
            side_effect=[page1_response, page2_response]
        )

        records = await authenticated_client.get_all_conference_records()

        assert len(records) == 15
        assert authenticated_client._client.request.call_count == 2


class TestGoogleMeetClientParticipantOperations:
    """Tests for participant operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_list_participants(self, authenticated_client: GoogleMeetClient) -> None:
        """Should list participants of a conference."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["participants_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        response = await authenticated_client.list_participants("conferenceRecords/conf-123")

        assert len(response.participants) == 2
        assert response.total_size == 2

    @pytest.mark.asyncio
    async def test_get_participant(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get participant by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["participant_signed_in"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        participant = await authenticated_client.get_participant(
            "conferenceRecords/conf-123/participants/part-001"
        )

        assert isinstance(participant, Participant)
        assert participant.signedin_user is not None
        assert participant.signedin_user.display_name == "John Doe"

    @pytest.mark.asyncio
    async def test_get_all_participants_pagination(
        self, authenticated_client: GoogleMeetClient
    ) -> None:
        """Should handle pagination for participants."""
        page1_response = httpx.Response(200, json=PAGINATED_RESPONSES["participants_page1"])
        page2_response = httpx.Response(200, json=PAGINATED_RESPONSES["participants_page2"])

        authenticated_client._client.request = AsyncMock(
            side_effect=[page1_response, page2_response]
        )

        participants = await authenticated_client.get_all_participants("conferenceRecords/conf-123")

        assert len(participants) == 15


class TestGoogleMeetClientRecordingOperations:
    """Tests for recording operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_list_recordings(self, authenticated_client: GoogleMeetClient) -> None:
        """Should list recordings for a conference."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["recordings_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        response = await authenticated_client.list_recordings("conferenceRecords/conf-123")

        assert len(response.recordings) == 1

    @pytest.mark.asyncio
    async def test_get_recording(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get recording by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["recording"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        recording = await authenticated_client.get_recording(
            "conferenceRecords/conf-123/recordings/rec-001"
        )

        assert isinstance(recording, Recording)
        assert recording.state.value == "FILE_GENERATED"
        assert recording.drive_destination is not None


class TestGoogleMeetClientTranscriptOperations:
    """Tests for transcript operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_list_transcripts(self, authenticated_client: GoogleMeetClient) -> None:
        """Should list transcripts for a conference."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["transcripts_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        response = await authenticated_client.list_transcripts("conferenceRecords/conf-123")

        assert len(response.transcripts) == 1

    @pytest.mark.asyncio
    async def test_get_transcript(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get transcript by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["transcript"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        transcript = await authenticated_client.get_transcript(
            "conferenceRecords/conf-123/transcripts/trans-001"
        )

        assert isinstance(transcript, Transcript)
        assert transcript.docs_destination is not None

    @pytest.mark.asyncio
    async def test_list_transcript_entries(self, authenticated_client: GoogleMeetClient) -> None:
        """Should list transcript entries."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["transcript_entries_list"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        response = await authenticated_client.list_transcript_entries(
            "conferenceRecords/conf-123/transcripts/trans-001"
        )

        assert len(response.transcript_entries) == 2

    @pytest.mark.asyncio
    async def test_get_transcript_entry(self, authenticated_client: GoogleMeetClient) -> None:
        """Should get transcript entry by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["transcript_entry"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        entry = await authenticated_client.get_transcript_entry(
            "conferenceRecords/conf-123/transcripts/trans-001/entries/entry-001"
        )

        assert isinstance(entry, TranscriptEntry)
        assert "Hello everyone" in entry.text


class TestGoogleMeetClientErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_not_found_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise NotFoundError for 404."""
        mock_response = httpx.Response(
            404,
            json=ERROR_RESPONSES["not_found"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetNotFoundError):
            await authenticated_client.get_space("spaces/nonexistent")

    @pytest.mark.asyncio
    async def test_permission_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise PermissionError for 403."""
        mock_response = httpx.Response(
            403,
            json=ERROR_RESPONSES["permission_denied"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetPermissionError):
            await authenticated_client.get_space("spaces/abc123")

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise QuotaExceeded for quota errors."""
        mock_response = httpx.Response(
            403,
            json=ERROR_RESPONSES["quota_exceeded"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetQuotaExceeded):
            await authenticated_client.list_conference_records()

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise RateLimitError for 429."""
        mock_response = httpx.Response(
            429,
            json=ERROR_RESPONSES["rate_limited"],
            headers={"Retry-After": "60"},
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetRateLimitError) as exc_info:
            await authenticated_client.create_space()
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_validation_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise ValidationError for 400."""
        mock_response = httpx.Response(
            400,
            json=ERROR_RESPONSES["invalid_argument"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetValidationError):
            await authenticated_client.get_space("invalid")

    @pytest.mark.asyncio
    async def test_auth_error(self, authenticated_client: GoogleMeetClient) -> None:
        """Should raise AuthError for 401."""
        mock_response = httpx.Response(
            401,
            json=ERROR_RESPONSES["unauthorized"],
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleMeetAuthError):
            await authenticated_client.create_space()

    @pytest.mark.asyncio
    async def test_request_without_auth_raises(self) -> None:
        """Should raise error when making request without authentication."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        with pytest.raises(GoogleMeetAuthError) as exc_info:
            await client.create_space()
        assert "not authenticated" in str(exc_info.value).lower()


class TestGoogleMeetClientGenericRequest:
    """Tests for generic request method."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleMeetClient:
        """Create authenticated client for tests."""
        client = GoogleMeetClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_generic_request_get(self, authenticated_client: GoogleMeetClient) -> None:
        """Should make generic GET request."""
        mock_response = httpx.Response(200, json={"custom": "response"})
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.generic_request(
            "GET",
            "/v2/custom/endpoint",
            params={"key": "value"},
        )

        assert result == {"custom": "response"}

    @pytest.mark.asyncio
    async def test_generic_request_post(self, authenticated_client: GoogleMeetClient) -> None:
        """Should make generic POST request with body."""
        mock_response = httpx.Response(200, json={"created": True})
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.generic_request(
            "POST",
            "/v2/custom/endpoint",
            json_data={"field": "value"},
        )

        assert result == {"created": True}
        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["json"] == {"field": "value"}


class TestGoogleMeetModels:
    """Tests for Pydantic models."""

    def test_space_model_parsing(self) -> None:
        """Should parse space response correctly."""
        space = Space.model_validate(SAMPLE_RESPONSES["space"])

        assert space.name == "spaces/abc123"
        assert space.meeting_uri == "https://meet.google.com/abc-defg-hij"
        assert space.meeting_code == "abc-defg-hij"
        assert space.config.access_type == SpaceAccessType.OPEN

    def test_space_with_active_conference(self) -> None:
        """Should parse space with active conference."""
        space = Space.model_validate(SAMPLE_RESPONSES["space_with_conference"])

        assert space.active_conference is not None
        assert space.active_conference.conference_record == "conferenceRecords/conf-123"

    def test_conference_record_model_parsing(self) -> None:
        """Should parse conference record correctly."""
        record = ConferenceRecord.model_validate(SAMPLE_RESPONSES["conference_record"])

        assert record.name == "conferenceRecords/conf-123"
        assert record.space == "spaces/abc123"
        assert record.start_time is not None
        assert record.end_time is not None

    def test_participant_signed_in_user(self) -> None:
        """Should parse signed-in participant."""
        participant = Participant.model_validate(SAMPLE_RESPONSES["participant_signed_in"])

        assert participant.signedin_user is not None
        assert participant.signedin_user.display_name == "John Doe"
        assert participant.anonymous_user is None
        assert participant.phone_user is None

    def test_participant_anonymous_user(self) -> None:
        """Should parse anonymous participant."""
        participant = Participant.model_validate(SAMPLE_RESPONSES["participant_anonymous"])

        assert participant.anonymous_user is not None
        assert participant.anonymous_user.display_name == "Anonymous User"
        assert participant.signedin_user is None

    def test_participant_phone_user(self) -> None:
        """Should parse phone participant."""
        participant = Participant.model_validate(SAMPLE_RESPONSES["participant_phone"])

        assert participant.phone_user is not None
        assert "+1 555-123-4567" in participant.phone_user.display_name

    def test_recording_model_parsing(self) -> None:
        """Should parse recording correctly."""
        recording = Recording.model_validate(SAMPLE_RESPONSES["recording"])

        assert recording.state.value == "FILE_GENERATED"
        assert recording.drive_destination is not None
        assert "drive-file-123" in recording.drive_destination.export_uri

    def test_transcript_model_parsing(self) -> None:
        """Should parse transcript correctly."""
        transcript = Transcript.model_validate(SAMPLE_RESPONSES["transcript"])

        assert transcript.state.value == "FILE_GENERATED"
        assert transcript.docs_destination is not None

    def test_transcript_entry_model_parsing(self) -> None:
        """Should parse transcript entry correctly."""
        entry = TranscriptEntry.model_validate(SAMPLE_RESPONSES["transcript_entry"])

        assert "Hello everyone" in entry.text
        assert entry.language_code == "en-US"
