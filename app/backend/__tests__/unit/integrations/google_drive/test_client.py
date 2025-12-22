"""Unit tests for Google Drive API client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.google_drive.client import GoogleDriveClient
from src.integrations.google_drive.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveError,
    GoogleDriveQuotaExceeded,
    GoogleDriveRateLimitError,
)
from src.integrations.google_drive.models import DriveMetadata


class TestGoogleDriveClientInitialization:
    """Tests for GoogleDriveClient initialization."""

    def test_client_initialization_with_credentials_dict(self, credentials):
        """Client should initialize with credentials dictionary."""
        client = GoogleDriveClient(credentials_json=credentials)
        assert client.name == "google_drive"
        assert client.credentials_json == credentials
        assert client.base_url == GoogleDriveClient.DRIVE_API_BASE

    def test_client_initialization_with_credentials_string(self, credentials_json_str):
        """Client should initialize and parse JSON string credentials."""
        client = GoogleDriveClient(credentials_str=credentials_json_str)
        assert isinstance(client.credentials_json, dict)
        assert client.credentials_json["project_id"] == "test-project"

    def test_client_initialization_with_access_token(self):
        """Client should initialize with pre-obtained access token."""
        client = GoogleDriveClient(access_token="existing_token_123")
        assert client.access_token == "existing_token_123"

    def test_client_initialization_raises_without_credentials(self):
        """Client should raise error without credentials or token."""
        with patch.dict("os.environ", {}, clear=True), pytest.raises(GoogleDriveAuthError):
            GoogleDriveClient()

    def test_client_initialization_with_custom_timeout(self, credentials):
        """Client should accept custom timeout value."""
        client = GoogleDriveClient(credentials_json=credentials, timeout=60.0)
        assert client.timeout == 60.0

    def test_client_initialization_with_custom_max_retries(self, credentials):
        """Client should accept custom max retries."""
        client = GoogleDriveClient(credentials_json=credentials, max_retries=5)
        assert client.max_retries == 5


class TestGoogleDriveClientAuthentication:
    """Tests for Google Drive API client authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_with_access_token(self, google_drive_client):
        """Should authenticate when access_token is provided."""
        google_drive_client.access_token = None
        google_drive_client.credentials_json["access_token"] = "new_token"

        await google_drive_client.authenticate()

        assert google_drive_client.access_token == "new_token"

    @pytest.mark.asyncio
    async def test_authenticate_raises_without_credentials(self, google_drive_client):
        """Should raise error if credentials incomplete."""
        google_drive_client.credentials_json = {"type": "service_account"}
        google_drive_client.access_token = None

        with pytest.raises(GoogleDriveAuthError):
            await google_drive_client.authenticate()

    @pytest.mark.asyncio
    async def test_get_headers_includes_bearer_token(self, google_drive_client):
        """Headers should include Authorization with bearer token."""
        headers = google_drive_client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_headers_raises_without_token(self, google_drive_client):
        """Should raise error if trying to get headers without token."""
        google_drive_client.access_token = None

        with pytest.raises(GoogleDriveAuthError):
            google_drive_client._get_headers()


class TestGoogleDriveClientListFiles:
    """Tests for list_files method."""

    @pytest.mark.asyncio
    async def test_list_files_success(self, google_drive_client, file_list_response):
        """Should list files with correct parameters."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=file_list_response,
        ):
            result = await google_drive_client.list_files(page_size=10)

            assert len(result["files"]) == 2
            assert result["files"][0]["id"] == "file1"
            assert result["files"][1]["id"] == "file2"

    @pytest.mark.asyncio
    async def test_list_files_with_query(self, google_drive_client, file_list_response):
        """Should filter files with query parameter."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=file_list_response,
        ) as mock_request:
            await google_drive_client.list_files(query="name contains 'proposal'")

            # Verify query was passed to request
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["q"] == "name contains 'proposal'"

    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, google_drive_client, file_list_response):
        """Should handle pagination tokens."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=file_list_response,
        ) as mock_request:
            await google_drive_client.list_files(page_token="token123")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["pageToken"] == "token123"

    @pytest.mark.asyncio
    async def test_list_files_error_handling(self, google_drive_client):
        """Should handle errors from list_files."""
        with (
            patch.object(
                google_drive_client,
                "_request_with_retry",
                new_callable=AsyncMock,
                side_effect=GoogleDriveError("API error"),
            ),
            pytest.raises(GoogleDriveError),
        ):
            await google_drive_client.list_files()


class TestGoogleDriveClientFileMetadata:
    """Tests for get_file_metadata method."""

    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self, google_drive_client, file_metadata):
        """Should retrieve file metadata."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=file_metadata,
        ):
            result = await google_drive_client.get_file_metadata("file123")

            assert isinstance(result, DriveMetadata)
            assert result.id == "file123"
            assert result.name == "Test Document"
            assert result.shared is True

    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, google_drive_client):
        """Should handle 404 not found."""
        with (
            patch.object(
                google_drive_client,
                "_request_with_retry",
                new_callable=AsyncMock,
                side_effect=GoogleDriveError("File not found"),
            ),
            pytest.raises(GoogleDriveError),
        ):
            await google_drive_client.get_file_metadata("nonexistent")


class TestGoogleDriveClientCreateDocument:
    """Tests for create_document method."""

    @pytest.mark.asyncio
    async def test_create_document_success(self, google_drive_client, created_file):
        """Should create new document."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=created_file,
        ) as mock_request:
            result = await google_drive_client.create_document("Test Document")

            assert result["id"] == "new_file_123"
            assert result["name"] == "New Document"

            # Verify request parameters
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["name"] == "Test Document"
            assert call_kwargs["json"]["mimeType"] == "application/vnd.google-apps.document"

    @pytest.mark.asyncio
    async def test_create_document_with_parent(self, google_drive_client, created_file):
        """Should create document in specified folder."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=created_file,
        ) as mock_request:
            await google_drive_client.create_document("Test", parent_folder_id="folder123")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["parents"] == ["folder123"]

    @pytest.mark.asyncio
    async def test_create_document_with_different_type(self, google_drive_client, created_file):
        """Should create different document types."""
        sheets_mime = "application/vnd.google-apps.spreadsheet"

        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=created_file,
        ) as mock_request:
            await google_drive_client.create_document("Sheet", mime_type=sheets_mime)

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["mimeType"] == sheets_mime


class TestGoogleDriveClientDeleteFile:
    """Tests for delete_file method."""

    @pytest.mark.asyncio
    async def test_delete_file_to_trash(self, google_drive_client):
        """Should move file to trash by default."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
        ) as mock_request:
            await google_drive_client.delete_file("file123", permanently=False)

            # Should use PATCH to trash
            assert mock_request.call_args[0][0] == "PATCH"
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["trashed"] is True

    @pytest.mark.asyncio
    async def test_delete_file_permanently(self, google_drive_client):
        """Should permanently delete file when specified."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
        ) as mock_request:
            await google_drive_client.delete_file("file123", permanently=True)

            # Should use DELETE for permanent deletion
            assert mock_request.call_args[0][0] == "DELETE"


class TestGoogleDriveClientShareFile:
    """Tests for share_file method."""

    @pytest.mark.asyncio
    async def test_share_file_with_user(self, google_drive_client, permission):
        """Should share file with user."""
        with patch.object(
            google_drive_client,
            "_request_with_retry",
            new_callable=AsyncMock,
            return_value=permission,
        ) as mock_request:
            result = await google_drive_client.share_file(
                "file123", email="user@example.com", role="reader"
            )

            assert result["type"] == "user"
            assert result["role"] == "reader"

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["type"] == "user"
            assert call_kwargs["json"]["role"] == "reader"
            assert call_kwargs["json"]["emailAddress"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_share_file_different_roles(self, google_drive_client, permission):
        """Should handle different permission roles."""
        roles = ["owner", "writer", "commenter", "reader"]

        for role in roles:
            with patch.object(
                google_drive_client,
                "_request_with_retry",
                new_callable=AsyncMock,
                return_value=permission,
            ) as mock_request:
                await google_drive_client.share_file("file123", email="user@example.com", role=role)

                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["json"]["role"] == role


class TestGoogleDriveClientExport:
    """Tests for export_document method."""

    @pytest.mark.asyncio
    async def test_export_document_invalid_format(self, google_drive_client):
        """Should raise error for unsupported format."""
        with pytest.raises(GoogleDriveError, match="Unsupported export format"):
            await google_drive_client.export_document("file123", "invalid")

    def test_export_formats_defined(self, google_drive_client):
        """Should have all standard export formats defined."""
        expected_formats = {"pdf", "docx", "xlsx", "csv", "json", "odt", "ods", "rtf", "txt", "zip"}
        actual_formats = set(google_drive_client.EXPORT_FORMATS.keys())
        assert expected_formats == actual_formats


class TestGoogleDriveClientErrorHandling:
    """Tests for error handling and retry logic."""

    def test_rate_limit_error_type(self, google_drive_client):
        """GoogleDriveRateLimitError should be properly defined."""
        error = GoogleDriveRateLimitError("Rate limited", retry_after=60)
        assert error.status_code == 429
        assert error.retry_after == 60

    def test_quota_exceeded_error_type(self, google_drive_client):
        """GoogleDriveQuotaExceeded should be properly defined."""
        error = GoogleDriveQuotaExceeded("Quota exceeded")
        assert error.status_code == 403
        assert "quota" in error.message.lower()

    def test_auth_error_type(self, google_drive_client):
        """GoogleDriveAuthError should be properly defined."""
        error = GoogleDriveAuthError("Auth failed")
        assert error.status_code == 401

    @pytest.mark.asyncio
    async def test_health_check_success(self, google_drive_client):
        """Should return healthy status when authenticated and connected."""
        with patch.object(
            google_drive_client,
            "list_files",
            new_callable=AsyncMock,
        ):
            result = await google_drive_client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "google_drive"

    @pytest.mark.asyncio
    async def test_health_check_not_authenticated(self):
        """Should return unhealthy status when not authenticated."""
        client = GoogleDriveClient(access_token="test")
        client.access_token = None

        result = await client.health_check()

        assert result["healthy"] is False
        assert "Not authenticated" in result["message"]


class TestGoogleDriveClientContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_async_with_statement(self, credentials):
        """Should work as async context manager."""
        async with GoogleDriveClient(credentials_json=credentials) as client:
            assert client is not None
            assert not client._client.is_closed if client._client else True

    @pytest.mark.asyncio
    async def test_close_method(self, google_drive_client):
        """Should properly close HTTP client."""
        # Create a real client with a mock httpx client
        test_client = AsyncMock()
        test_client.is_closed = False
        test_client.aclose = AsyncMock()

        google_drive_client._client = test_client

        await google_drive_client.close()

        assert google_drive_client._client is None
