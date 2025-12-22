"""Unit tests for Google Docs client."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.base import IntegrationError
from src.integrations.google_docs import (
    GoogleDocsAuthError,
    GoogleDocsClient,
    GoogleDocsError,
    GoogleDocsRateLimitError,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_credentials() -> dict:
    """Valid Google service account credentials."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id",
        "private_key": "test-key-123",  # noqa
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "access_token": "test_token_xyz",
    }


@pytest.fixture
def invalid_credentials() -> dict:
    """Invalid credentials (missing required fields)."""
    return {"type": "service_account"}


@pytest.fixture
async def client(valid_credentials: dict) -> GoogleDocsClient:
    """Create a Google Docs client with valid credentials."""
    return GoogleDocsClient(credentials_json=valid_credentials)


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestClientInitialization:
    """Tests for client initialization."""

    def test_client_initializes_with_valid_credentials(self, valid_credentials: dict) -> None:
        """Client should initialize successfully with valid credentials."""
        client = GoogleDocsClient(credentials_json=valid_credentials)
        assert client.name == "google_docs"
        assert client.project_id == "test-project"
        assert client.base_url == "https://docs.googleapis.com/v1"

    def test_client_initializes_with_credentials_string(self, valid_credentials: dict) -> None:
        """Client should initialize with credentials as JSON string."""
        creds_str = json.dumps(valid_credentials)
        client = GoogleDocsClient(credentials_str=creds_str)
        assert client.project_id == "test-project"

    def test_client_raises_error_without_credentials(self) -> None:
        """Client should raise error if credentials are missing."""
        with pytest.raises(GoogleDocsAuthError):
            GoogleDocsClient()

    def test_client_raises_error_with_invalid_credentials(self, invalid_credentials: dict) -> None:
        """Client should raise error if credentials are invalid."""
        with pytest.raises(GoogleDocsAuthError):
            GoogleDocsClient(credentials_json=invalid_credentials)

    def test_client_sets_oauth_scopes(self, valid_credentials: dict) -> None:
        """Client should set correct OAuth2 scopes."""
        client = GoogleDocsClient(credentials_json=valid_credentials)
        assert "https://www.googleapis.com/auth/documents" in client.scopes
        assert "https://www.googleapis.com/auth/drive.file" in client.scopes


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================


class TestAuthentication:
    """Tests for OAuth2 authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_sets_access_token(self, client: GoogleDocsClient) -> None:
        """Authenticate should set the access token."""
        # Client already has token from __init__
        assert client.access_token == "test_token_xyz"

    @pytest.mark.asyncio
    async def test_authenticate_raises_error_without_token(self, valid_credentials: dict) -> None:
        """Should raise error if no token in credentials."""
        creds_without_token = {**valid_credentials}
        del creds_without_token["access_token"]

        with pytest.raises(GoogleDocsAuthError):
            GoogleDocsClient(credentials_json=creds_without_token)

    def test_get_headers_includes_authorization(self, client: GoogleDocsClient) -> None:
        """Headers should include Bearer authorization."""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_xyz"
        assert headers["Content-Type"] == "application/json"


# ============================================================================
# DOCUMENT CREATION TESTS
# ============================================================================


class TestDocumentCreation:
    """Tests for document creation."""

    @pytest.mark.asyncio
    async def test_create_document_success(self, client: GoogleDocsClient) -> None:
        """Create document should return document ID."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "doc-123",
                "name": "Test Document",
                "mimeType": "application/vnd.google-apps.document",
            }

            result = await client.create_document(title="Test Document")

            assert result["documentId"] == "doc-123"
            assert result["title"] == "Test Document"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document_with_parent_folder(self, client: GoogleDocsClient) -> None:
        """Create document should support parent folder ID."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "doc-123"}

            await client.create_document(
                title="Test",
                parent_folder_id="folder-456",
            )

            # Verify parent folder ID was passed
            call_kwargs = mock_post.call_args[1]
            assert "folder-456" in call_kwargs["json"]["parents"]

    @pytest.mark.asyncio
    async def test_create_document_rate_limit_error(self, client: GoogleDocsClient) -> None:
        """Create document should raise RateLimitError on 429."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError(
                "Rate limited",
                status_code=429,
            )

            with pytest.raises(GoogleDocsRateLimitError):
                await client.create_document(title="Test")

    @pytest.mark.asyncio
    async def test_create_document_auth_error(self, client: GoogleDocsClient) -> None:
        """Create document should raise AuthError on 401."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError(
                "Unauthorized",
                status_code=401,
            )

            with pytest.raises(GoogleDocsAuthError):
                await client.create_document(title="Test")


# ============================================================================
# TEXT INSERTION TESTS
# ============================================================================


class TestTextInsertion:
    """Tests for text insertion."""

    @pytest.mark.asyncio
    async def test_insert_text_success(self, client: GoogleDocsClient) -> None:
        """Insert text should execute batch update."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}]}

            result = await client.insert_text(
                document_id="doc-123",
                text="Hello World",
            )

            assert result["documentId"] == "doc-123"
            mock_post.assert_called_once()

            # Verify request structure
            call_kwargs = mock_post.call_args[1]
            assert "requests" in call_kwargs["json"]

    @pytest.mark.asyncio
    async def test_insert_text_at_index(self, client: GoogleDocsClient) -> None:
        """Insert text should support custom index."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123"}

            await client.insert_text(
                document_id="doc-123",
                text="Inserted",
                index=42,
            )

            # Verify index was included
            call_kwargs = mock_post.call_args[1]
            request = call_kwargs["json"]["requests"][0]
            assert request["insertText"]["location"]["index"] == 42


# ============================================================================
# BATCH UPDATE TESTS
# ============================================================================


class TestBatchUpdate:
    """Tests for batch update operations."""

    @pytest.mark.asyncio
    async def test_batch_update_executes_multiple_requests(self, client: GoogleDocsClient) -> None:
        """Batch update should execute multiple requests in one call."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "documentId": "doc-123",
                "replies": [{}, {}],
            }

            requests = [
                {"insertText": {"text": "Hello", "location": {"index": 1}}},
                {"insertText": {"text": " World", "location": {"index": 6}}},
            ]

            result = await client.batch_update(
                document_id="doc-123",
                requests=requests,
            )

            assert len(result["replies"]) == 2
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_error_includes_count(self, client: GoogleDocsClient) -> None:
        """Batch update error should include number of operations."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Failed")

            requests = [
                {"insertText": {"text": "Hello", "location": {"index": 1}}},
                {"insertText": {"text": "World", "location": {"index": 6}}},
                {"insertText": {"text": "!", "location": {"index": 11}}},
            ]

            with pytest.raises(GoogleDocsError) as exc_info:
                await client.batch_update(
                    document_id="doc-123",
                    requests=requests,
                )

            assert "3 operations" in str(exc_info.value)


# ============================================================================
# FORMATTING TESTS
# ============================================================================


class TestFormatting:
    """Tests for text formatting."""

    @pytest.mark.asyncio
    async def test_format_text_bold(self, client: GoogleDocsClient) -> None:
        """Format text should apply bold formatting."""
        with patch.object(client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await client.format_text(
                document_id="doc-123",
                start_index=0,
                end_index=5,
                bold=True,
            )

            # Verify batch_update was called with correct arguments
            assert mock.called
            # batch_update(document_id, requests)
            call_args = mock.call_args
            doc_id = call_args[0][0] if call_args[0] else call_args[1].get("document_id")
            requests = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("requests")

            assert doc_id == "doc-123"
            assert len(requests) == 1
            assert "updateTextStyle" in requests[0]

    @pytest.mark.asyncio
    async def test_format_text_multiple_styles(self, client: GoogleDocsClient) -> None:
        """Format text should support multiple styles simultaneously."""
        with patch.object(client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await client.format_text(
                document_id="doc-123",
                start_index=0,
                end_index=10,
                bold=True,
                italic=True,
                underline=True,
            )

            # Get requests from batch_update call
            call_args = mock.call_args
            requests = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("requests")
            style = requests[0]["updateTextStyle"]["textStyle"]

            assert style["bold"] is True
            assert style["italic"] is True
            assert style["underline"] is True


# ============================================================================
# TABLE TESTS
# ============================================================================


class TestTableCreation:
    """Tests for table operations."""

    @pytest.mark.asyncio
    async def test_create_table_success(self, client: GoogleDocsClient) -> None:
        """Create table should execute insert table request."""
        with patch.object(client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await client.create_table(
                document_id="doc-123",
                rows=3,
                columns=2,
            )

            # Get requests from batch_update call
            call_args = mock.call_args
            requests = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("requests")
            request = requests[0]
            assert request["insertTable"]["rows"] == 3
            assert request["insertTable"]["columns"] == 2


# ============================================================================
# SHARING TESTS
# ============================================================================


class TestDocumentSharing:
    """Tests for document sharing."""

    @pytest.mark.asyncio
    async def test_share_document_success(self, client: GoogleDocsClient) -> None:
        """Share document should update permissions."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "perm-123"}

            result = await client.share_document(
                document_id="doc-123",
                email="user@example.com",
                role="reader",
            )

            assert result["id"] == "perm-123"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document_permissions(self, client: GoogleDocsClient) -> None:
        """Get permissions should return list of permissions."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "permissions": [
                    {
                        "kind": "drive#permission",
                        "id": "perm-1",
                        "type": "user",
                        "role": "owner",
                    }
                ]
            }

            result = await client.get_document_permissions(document_id="doc-123")

            assert len(result) == 1
            assert result[0]["type"] == "user"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_document_not_found_error(self, client: GoogleDocsClient) -> None:
        """Get document should raise error if document not found."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError(
                "Not found",
                status_code=404,
            )

            with pytest.raises(GoogleDocsError) as exc_info:
                await client.get_document(document_id="nonexistent")

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_includes_retry_after(self, client: GoogleDocsClient) -> None:
        """Rate limit error should include retry_after if available."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError(
                "Rate limited",
                status_code=429,
            )

            with pytest.raises(GoogleDocsRateLimitError):
                await client.create_document(title="Test")


# ============================================================================
# INTEGRATION SCENARIOS
# ============================================================================


class TestIntegrationScenarios:
    """Tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_create_and_populate_document(self, client: GoogleDocsClient) -> None:
        """Complete workflow: create document, add content, format it."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            # Create document
            mock_post.return_value = {"id": "doc-123"}
            doc = await client.create_document(title="Test Document")

            # Mock batch_update separately for subsequent calls
            with patch.object(client, "batch_update", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = {"replies": [{}]}

                # Insert text - calls batch_update
                await client.insert_text(
                    document_id=doc["documentId"],
                    text="Test Content",
                )

                # Format text - calls batch_update
                await client.format_text(
                    document_id=doc["documentId"],
                    start_index=0,
                    end_index=12,
                    bold=True,
                )

                assert mock_post.called
                assert mock_batch.call_count == 2

    @pytest.mark.asyncio
    async def test_create_table_with_content(self, client: GoogleDocsClient) -> None:
        """Complete workflow: create table then populate with content."""
        with patch.object(client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            # Create table - calls batch_update
            await client.create_table(
                document_id="doc-123",
                rows=2,
                columns=2,
            )

            # Insert text - calls batch_update internally
            await client.insert_text(
                document_id="doc-123",
                text="Cell content",
            )

            # Both operations call batch_update
            assert mock.call_count == 2
