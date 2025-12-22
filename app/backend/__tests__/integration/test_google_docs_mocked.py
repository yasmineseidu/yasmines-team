"""Integration tests for Google Docs API with mocked HTTP responses.

These tests verify the complete integration workflow of the GoogleDocsClient
by mocking HTTP responses at the base client level. This allows testing
the full integration logic without needing valid API credentials.

All 9 endpoints are tested with:
- Success scenarios
- Edge cases
- Error handling
- Complete workflows
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.base import IntegrationError
from src.integrations.google_docs import (
    GoogleDocsAuthError,
    GoogleDocsClient,
    GoogleDocsError,
    GoogleDocsRateLimitError,
)


class TestGoogleDocsIntegrationMocked:
    """Integration tests with mocked HTTP responses."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Initialize client with test credentials."""
        test_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "test-key",  # pragma: allowlist secret
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "access_token": "test_access_token_xyz",  # pragma: allowlist secret
        }
        self.client = GoogleDocsClient(credentials_json=test_credentials)

    # ========================================================================
    # ENDPOINT 1: authenticate()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_authenticate_success(self) -> None:
        """Verify authenticate() sets access token from credentials."""
        # Token should already be set from __init__
        assert self.client.access_token == "test_access_token_xyz"

    @pytest.mark.asyncio
    async def test_authenticate_idempotent(self) -> None:
        """Verify authenticate() can be called multiple times safely."""
        await self.client.authenticate()
        token1 = self.client.access_token

        await self.client.authenticate()
        token2 = self.client.access_token

        assert token1 == token2

    # ========================================================================
    # ENDPOINT 2: create_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_document_success(self) -> None:
        """Verify create_document() creates document and returns metadata."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            # Mock Drive API response
            mock_post.return_value = {
                "id": "doc-123",
                "name": "Test Document",
                "mimeType": "application/vnd.google-apps.document",
            }

            result = await self.client.create_document(title="Test Document")

            assert result["documentId"] == "doc-123"
            assert result["title"] == "Test Document"
            assert result["mimeType"] == "application/vnd.google-apps.document"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document_response_schema(self) -> None:
        """Verify create_document() response has correct schema."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "doc-456",
                "name": "Schema Test",
                "mimeType": "application/vnd.google-apps.document",
            }

            result = await self.client.create_document(title="Schema Test")

            expected_keys = {"documentId", "title", "mimeType"}
            assert all(key in result for key in expected_keys)

    @pytest.mark.asyncio
    async def test_create_document_with_folder(self) -> None:
        """Verify create_document() accepts parent folder ID."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "doc-789"}

            await self.client.create_document(title="Folder Test", parent_folder_id="folder-123")

            # Verify folder ID was passed in request
            call_kwargs = mock_post.call_args[1]
            assert "folder-123" in call_kwargs["json"]["parents"]

    @pytest.mark.asyncio
    async def test_create_document_error_handling(self) -> None:
        """Verify create_document() handles auth errors."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Unauthorized", status_code=401)

            with pytest.raises(GoogleDocsAuthError):
                await self.client.create_document(title="Test")

    # ========================================================================
    # ENDPOINT 3: get_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_document_success(self) -> None:
        """Verify get_document() retrieves document content."""
        with patch.object(self.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "documentId": "doc-123",
                "title": "Test Document",
                "body": {"content": []},
            }

            result = await self.client.get_document(document_id="doc-123")

            assert result["documentId"] == "doc-123"
            assert result["title"] == "Test Document"
            assert "body" in result

    @pytest.mark.asyncio
    async def test_get_document_not_found(self) -> None:
        """Verify get_document() handles 404 errors."""
        with patch.object(self.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Not Found", status_code=404)

            with pytest.raises(GoogleDocsError) as exc_info:
                await self.client.get_document(document_id="nonexistent")

            assert "not found" in str(exc_info.value).lower()

    # ========================================================================
    # ENDPOINT 4: insert_text()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_insert_text_success(self) -> None:
        """Verify insert_text() inserts text at position."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}]}

            result = await self.client.insert_text(document_id="doc-123", text="Hello World")

            assert result["documentId"] == "doc-123"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_text_at_index(self) -> None:
        """Verify insert_text() respects index parameter."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}]}

            await self.client.insert_text(document_id="doc-123", text="Inserted", index=42)

            # Verify index was passed correctly
            call_kwargs = mock_post.call_args[1]
            request = call_kwargs["json"]["requests"][0]
            assert request["insertText"]["location"]["index"] == 42

    @pytest.mark.asyncio
    async def test_insert_text_multiple_calls(self) -> None:
        """Verify insert_text() can be called multiple times."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}]}

            await self.client.insert_text(document_id="doc-123", text="First")
            await self.client.insert_text(document_id="doc-123", text="Second")

            assert mock_post.call_count == 2

    # ========================================================================
    # ENDPOINT 5: batch_update()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_batch_update_success(self) -> None:
        """Verify batch_update() executes multiple operations."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}, {}]}

            requests = [
                {"insertText": {"text": "Hello", "location": {"index": 1}}},
                {"insertText": {"text": " World", "location": {"index": 6}}},
            ]

            result = await self.client.batch_update(document_id="doc-123", requests=requests)

            assert len(result["replies"]) == 2
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_error_message(self) -> None:
        """Verify batch_update() error includes operation count."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Failed")

            requests = [
                {"insertText": {"text": "a", "location": {"index": 1}}},
                {"insertText": {"text": "b", "location": {"index": 2}}},
                {"insertText": {"text": "c", "location": {"index": 3}}},
            ]

            with pytest.raises(GoogleDocsError) as exc_info:
                await self.client.batch_update(document_id="doc-123", requests=requests)

            assert "3 operations" in str(exc_info.value)

    # ========================================================================
    # ENDPOINT 6: format_text()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_format_text_bold(self) -> None:
        """Verify format_text() applies bold formatting."""
        with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await self.client.format_text(
                document_id="doc-123", start_index=0, end_index=5, bold=True
            )

            # Verify batch_update was called with style request
            call_args = mock.call_args
            requests = call_args[0][1]
            assert "updateTextStyle" in requests[0]
            assert requests[0]["updateTextStyle"]["textStyle"]["bold"] is True

    @pytest.mark.asyncio
    async def test_format_text_multiple_styles(self) -> None:
        """Verify format_text() supports multiple styles simultaneously."""
        with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await self.client.format_text(
                document_id="doc-123",
                start_index=0,
                end_index=10,
                bold=True,
                italic=True,
                underline=True,
            )

            call_args = mock.call_args
            requests = call_args[0][1]
            style = requests[0]["updateTextStyle"]["textStyle"]

            assert style["bold"] is True
            assert style["italic"] is True
            assert style["underline"] is True

    @pytest.mark.asyncio
    async def test_format_text_with_color(self) -> None:
        """Verify format_text() applies text color."""
        with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            color = {"red": 1.0, "green": 0.0, "blue": 0.0}
            await self.client.format_text(
                document_id="doc-123", start_index=0, end_index=5, text_color=color
            )

            call_args = mock.call_args
            requests = call_args[0][1]
            style = requests[0]["updateTextStyle"]["textStyle"]

            assert style["foregroundColor"] == color

    # ========================================================================
    # ENDPOINT 7: create_table()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_table_success(self) -> None:
        """Verify create_table() inserts table."""
        with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            await self.client.create_table(document_id="doc-123", rows=3, columns=2)

            call_args = mock.call_args
            requests = call_args[0][1]
            assert requests[0]["insertTable"]["rows"] == 3
            assert requests[0]["insertTable"]["columns"] == 2

    @pytest.mark.asyncio
    async def test_create_table_various_sizes(self) -> None:
        """Verify create_table() works with different dimensions."""
        with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock:
            mock.return_value = {"replies": [{}]}

            # Test 10x5 table
            await self.client.create_table(document_id="doc-123", rows=10, columns=5)

            call_args = mock.call_args
            requests = call_args[0][1]
            assert requests[0]["insertTable"]["rows"] == 10
            assert requests[0]["insertTable"]["columns"] == 5

    # ========================================================================
    # ENDPOINT 8: share_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_share_document_reader(self) -> None:
        """Verify share_document() shares with reader role."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "perm-123"}

            result = await self.client.share_document(
                document_id="doc-123", email="user@example.com", role="reader"
            )

            assert result["id"] == "perm-123"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_document_writer(self) -> None:
        """Verify share_document() shares with writer role."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "perm-456"}

            result = await self.client.share_document(
                document_id="doc-123", email="collaborator@example.com", role="writer"
            )

            assert result["id"] == "perm-456"

    @pytest.mark.asyncio
    async def test_share_document_error(self) -> None:
        """Verify share_document() handles errors."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Forbidden", status_code=403)

            with pytest.raises(GoogleDocsError):
                await self.client.share_document(document_id="doc-123", email="user@example.com")

    # ========================================================================
    # ENDPOINT 9: get_document_permissions()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_document_permissions_success(self) -> None:
        """Verify get_document_permissions() returns permission list."""
        with patch.object(self.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "permissions": [
                    {"kind": "drive#permission", "id": "perm-1", "type": "user", "role": "owner"}
                ]
            }

            result = await self.client.get_document_permissions(document_id="doc-123")

            assert len(result) == 1
            assert result[0]["type"] == "user"
            assert result[0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_get_document_permissions_multiple(self) -> None:
        """Verify get_document_permissions() returns all permissions."""
        with patch.object(self.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "permissions": [
                    {"id": "p1", "type": "user", "role": "owner"},
                    {"id": "p2", "type": "user", "role": "writer"},
                    {"id": "p3", "type": "user", "role": "reader"},
                ]
            }

            result = await self.client.get_document_permissions(document_id="doc-123")

            assert len(result) == 3

    # ========================================================================
    # WORKFLOW TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_complete_document_workflow(self) -> None:
        """Test complete workflow: create, add content, format, share."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            # Step 1: Create document
            mock_post.return_value = {"id": "doc-123"}
            doc = await self.client.create_document(title="Workflow Test")
            doc_id = doc["documentId"]

            # Step 2: Insert text
            with patch.object(self.client, "batch_update", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = {"replies": [{}]}

                await self.client.insert_text(doc_id, "Document Content")
                await self.client.format_text(doc_id, 0, 8, bold=True)

                assert mock_batch.call_count == 2

            # Step 3: Share document
            mock_post.return_value = {"id": "perm-123"}
            await self.client.share_document(doc_id, "user@example.com")

            assert mock_post.call_count >= 2

    @pytest.mark.asyncio
    async def test_batch_document_operations(self) -> None:
        """Test batch operations: multiple updates in single request."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"documentId": "doc-123", "replies": [{}, {}, {}]}

            requests = [
                {"insertText": {"text": "Title\n", "location": {"index": 1}}},
                {
                    "updateTextStyle": {
                        "range": {"startIndex": 1, "endIndex": 6},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                },
                {"insertText": {"text": "Content here", "location": {"index": 7}}},
            ]

            result = await self.client.batch_update("doc-123", requests)

            assert len(result["replies"]) == 3
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self) -> None:
        """Test rate limit error is properly raised."""
        with patch.object(self.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Rate limited", status_code=429)

            with pytest.raises(GoogleDocsRateLimitError):
                await self.client.create_document(title="Test")

    @pytest.mark.asyncio
    async def test_headers_include_auth(self) -> None:
        """Verify request headers include Bearer token."""
        headers = self.client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_access_token_xyz"
        assert headers["Content-Type"] == "application/json"
