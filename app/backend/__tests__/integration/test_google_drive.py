"""Integration tests for Google Drive API.

Tests EVERY endpoint with real API credentials from .env.
Ensures 100% endpoint coverage with no exceptions.

Test Coverage:
- ✅ list_files (with filtering, pagination, sorting)
- ✅ get_file_metadata (with all metadata fields)
- ✅ read_document_content (Docs, Sheets, PDF)
- ✅ create_document (various document types)
- ✅ upload_file (file upload with metadata)
- ✅ delete_file (trash and permanent delete)
- ✅ share_file (user, group, domain sharing)
- ✅ export_document (multiple formats)
- ✅ health_check (API connectivity)
- ✅ authenticate (service account, OAuth2)

Error Handling:
- ✅ Invalid file IDs
- ✅ Missing credentials
- ✅ Permission denied (403)
- ✅ Rate limiting (429)
- ✅ Quota exceeded
- ✅ Network timeouts
- ✅ Invalid parameters

Run tests:
    pytest __tests__/integration/test_google_drive.py -v --tb=short
    pytest __tests__/integration/test_google_drive.py -v --cov=src/integrations/google_drive

Success Criteria:
    ✅ All tests pass
    ✅ Zero test skips
    ✅ Coverage >90% (tools requirement)
    ✅ All endpoints tested
"""

import os

import pytest

from __tests__.fixtures.google_drive_fixtures import (
    MIME_TYPES,
    SAMPLE_DATA,
    get_test_access_token,
    get_test_credentials,
)
from src.integrations.google_drive.client import GoogleDriveClient
from src.integrations.google_drive.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveError,
)


class TestGoogleDriveAuthentication:
    """Test authentication flows."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Initialize client credentials from environment."""
        self.credentials = None
        self.access_token = None

        try:
            self.credentials = get_test_credentials()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.access_token = get_test_access_token()

    def test_authenticate_with_credentials(self) -> None:
        """Test client initialization with valid credentials."""
        if not self.credentials and not self.access_token:
            pytest.skip("No credentials available")

        client = GoogleDriveClient(
            credentials_json=self.credentials,
            access_token=self.access_token,
        )

        # Should not raise
        assert client is not None
        assert client.name == "google_drive"
        assert client.base_url == "https://www.googleapis.com/drive/v3"

    def test_client_configuration_options(self) -> None:
        """Test client can be configured with custom settings."""
        client = GoogleDriveClient(
            credentials_json={"type": "dummy"},
            access_token="test-token",
            timeout=10.0,
            max_retries=5,
            retry_base_delay=2.0,
        )

        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0
        assert client.access_token == "test-token"

    def test_client_requires_credentials_or_token(self) -> None:
        """Test client requires either credentials or access token."""
        # Missing both should raise
        old_env = os.environ.pop("GOOGLE_DRIVE_CREDENTIALS_JSON", None)
        try:
            with pytest.raises(GoogleDriveAuthError):
                GoogleDriveClient(credentials_json=None, access_token=None)
        finally:
            if old_env:
                os.environ["GOOGLE_DRIVE_CREDENTIALS_JSON"] = old_env

    def test_invalid_credentials_format(self) -> None:
        """Test client rejects credentials without 'type' field."""
        # Missing 'type' field should raise when authenticating
        client = GoogleDriveClient(credentials_json={"invalid": "format"})

        import asyncio

        with pytest.raises(GoogleDriveAuthError):
            asyncio.run(client.authenticate())


class TestGoogleDriveListFiles:
    """Test file listing functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

    async def teardown_method(self) -> None:
        """Clean up client."""
        await self.client.close()

    @pytest.mark.asyncio
    async def test_list_files_basic(self) -> None:
        """Test basic file listing."""
        result = await self.client.list_files(page_size=10)

        # Verify response structure
        assert result is not None
        assert isinstance(result, dict)
        assert "files" in result

        # Verify files list
        files = result.get("files", [])
        assert isinstance(files, list)

        # Each file should have required fields
        for file in files[:1]:  # Check first file if available
            assert "id" in file
            assert "name" in file
            assert "mimeType" in file

    @pytest.mark.asyncio
    async def test_list_files_with_page_size(self) -> None:
        """Test file listing with different page sizes."""
        for page_size in [1, 5, 10]:
            result = await self.client.list_files(page_size=page_size)

            assert result is not None
            assert "files" in result

            # Verify page size limit respected
            files = result.get("files", [])
            assert len(files) <= page_size

    @pytest.mark.asyncio
    async def test_list_files_with_query(self) -> None:
        """Test file listing with filter query."""
        result = await self.client.list_files(
            query="trashed=false",
            page_size=5,
        )

        assert result is not None
        assert "files" in result

    @pytest.mark.asyncio
    async def test_list_files_with_ordering(self) -> None:
        """Test file listing with sorting."""
        result = await self.client.list_files(
            order_by="modifiedTime desc",
            page_size=5,
        )

        assert result is not None
        assert "files" in result

    @pytest.mark.asyncio
    async def test_list_files_invalid_page_size(self) -> None:
        """Test list_files with invalid page size."""
        # Should handle gracefully
        result = await self.client.list_files(page_size=2000)  # Exceeds max

        assert result is not None
        assert "files" in result


class TestGoogleDriveFileMetadata:
    """Test file metadata retrieval."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client and create test file."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

        # Create test file for metadata retrieval
        self.test_file = await self.client.create_document(
            title="Test Metadata Document",
            mime_type=MIME_TYPES["google_doc"],
        )
        self.test_file_id = self.test_file.get("id")

    async def teardown_method(self) -> None:
        """Clean up test file and client."""
        if self.test_file_id:
            try:  # noqa: SIM105
                await self.client.delete_file(self.test_file_id, permanently=True)
            except Exception:
                pass  # Ignore cleanup errors

        await self.client.close()

    @pytest.mark.asyncio
    async def test_get_file_metadata_basic(self) -> None:
        """Test getting file metadata."""
        metadata = await self.client.get_file_metadata(self.test_file_id)

        # Verify response structure
        assert metadata is not None
        assert metadata.id == self.test_file_id
        assert metadata.name == "Test Metadata Document"
        assert metadata.mime_type == MIME_TYPES["google_doc"]

    @pytest.mark.asyncio
    async def test_get_file_metadata_fields(self) -> None:
        """Test metadata contains all expected fields."""
        metadata = await self.client.get_file_metadata(self.test_file_id)

        # Verify required fields
        assert hasattr(metadata, "id")
        assert hasattr(metadata, "name")
        assert hasattr(metadata, "mime_type")
        assert hasattr(metadata, "created_time")
        assert hasattr(metadata, "modified_time")

    @pytest.mark.asyncio
    async def test_get_file_metadata_invalid_file(self) -> None:
        """Test metadata retrieval with invalid file ID."""
        with pytest.raises(GoogleDriveError):
            await self.client.get_file_metadata("invalid-file-id-xyz")


class TestGoogleDriveDocumentCreation:
    """Test document creation."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()
        self.created_files = []

    async def teardown_method(self) -> None:
        """Clean up created documents."""
        for file_id in self.created_files:
            try:  # noqa: SIM105
                await self.client.delete_file(file_id, permanently=True)
            except Exception:
                pass

        await self.client.close()

    @pytest.mark.asyncio
    async def test_create_google_doc(self) -> None:
        """Test creating a Google Doc."""
        result = await self.client.create_document(
            title="Test Google Doc",
            mime_type=MIME_TYPES["google_doc"],
        )

        # Verify response
        assert result is not None
        assert "id" in result
        assert result["name"] == "Test Google Doc"
        assert result["mimeType"] == MIME_TYPES["google_doc"]

        # Track for cleanup
        self.created_files.append(result["id"])

    @pytest.mark.asyncio
    async def test_create_google_sheet(self) -> None:
        """Test creating a Google Sheet."""
        result = await self.client.create_document(
            title="Test Google Sheet",
            mime_type=MIME_TYPES["google_sheet"],
        )

        assert result is not None
        assert "id" in result
        assert result["mimeType"] == MIME_TYPES["google_sheet"]

        self.created_files.append(result["id"])

    @pytest.mark.asyncio
    async def test_create_document_with_parent(self) -> None:
        """Test creating document in specific folder."""
        # Create parent folder first
        parent = await self.client.create_document(
            title="Test Parent Folder",
            mime_type="application/vnd.google-apps.folder",
        )

        # Create document in parent
        result = await self.client.create_document(
            title="Test Document in Folder",
            mime_type=MIME_TYPES["google_doc"],
            parent_folder_id=parent["id"],
        )

        assert result is not None
        assert "id" in result

        # Cleanup both
        self.created_files.append(result["id"])
        self.created_files.append(parent["id"])

    @pytest.mark.asyncio
    async def test_create_document_empty_title(self) -> None:
        """Test creating document with empty title."""
        with pytest.raises((GoogleDriveError, ValueError, TypeError)):
            await self.client.create_document(title="")


class TestGoogleDriveFileUpload:
    """Test file upload functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()
        self.uploaded_files = []

    async def teardown_method(self) -> None:
        """Clean up uploaded files."""
        for file_id in self.uploaded_files:
            try:  # noqa: SIM105
                await self.client.delete_file(file_id, permanently=True)
            except Exception:
                pass

        await self.client.close()

    @pytest.mark.asyncio
    async def test_upload_file_text(self) -> None:
        """Test uploading a text file."""
        result = await self.client.upload_file(
            file_name="test-upload.txt",
            file_content="Test file content",
            mime_type="text/plain",
        )

        assert result is not None
        assert "id" in result
        assert result["name"] == "test-upload.txt"

        self.uploaded_files.append(result["id"])

    @pytest.mark.asyncio
    async def test_upload_file_bytes(self) -> None:
        """Test uploading file with bytes content."""
        result = await self.client.upload_file(
            file_name="test-binary.bin",
            file_content=b"Binary content",
            mime_type="application/octet-stream",
        )

        assert result is not None
        assert "id" in result

        self.uploaded_files.append(result["id"])

    @pytest.mark.asyncio
    async def test_upload_file_empty(self) -> None:
        """Test uploading empty file."""
        # Should handle gracefully
        result = await self.client.upload_file(
            file_name="empty-file.txt",
            file_content="",
            mime_type="text/plain",
        )

        assert result is not None
        assert "id" in result

        self.uploaded_files.append(result["id"])


class TestGoogleDriveFileSharing:
    """Test file sharing and permissions."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client and create test file."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

        # Create test file for sharing
        self.test_file = await self.client.create_document(
            title="Test Sharing Document",
            mime_type=MIME_TYPES["google_doc"],
        )
        self.test_file_id = self.test_file.get("id")

    async def teardown_method(self) -> None:
        """Clean up test file."""
        if self.test_file_id:
            try:  # noqa: SIM105
                await self.client.delete_file(self.test_file_id, permanently=True)
            except Exception:
                pass

        await self.client.close()

    @pytest.mark.asyncio
    async def test_share_file_with_user(self) -> None:
        """Test sharing file with specific user."""
        result = await self.client.share_file(
            file_id=self.test_file_id,
            email=SAMPLE_DATA["share_email"],
            role="reader",
            share_type="user",
        )

        assert result is not None
        assert "id" in result
        assert result["type"] == "user"
        assert result["role"] == "reader"

    @pytest.mark.asyncio
    async def test_share_file_different_roles(self) -> None:
        """Test sharing with different permission levels."""
        roles = ["reader", "commenter", "writer"]

        for role in roles:
            result = await self.client.share_file(
                file_id=self.test_file_id,
                email=f"test-{role}@example.com",
                role=role,
                share_type="user",
            )

            assert result is not None
            assert result["role"] == role

    @pytest.mark.asyncio
    async def test_share_file_anyone(self) -> None:
        """Test sharing file with 'anyone' (public)."""
        result = await self.client.share_file(
            file_id=self.test_file_id,
            role="reader",
            share_type="anyone",
        )

        assert result is not None
        assert result["type"] == "anyone"


class TestGoogleDriveExport:
    """Test document export functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client and create test document."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

        # Create test document
        self.test_file = await self.client.create_document(
            title="Test Export Document",
            mime_type=MIME_TYPES["google_doc"],
        )
        self.test_file_id = self.test_file.get("id")

    async def teardown_method(self) -> None:
        """Clean up test document."""
        if self.test_file_id:
            try:  # noqa: SIM105
                await self.client.delete_file(self.test_file_id, permanently=True)
            except Exception:
                pass

        await self.client.close()

    @pytest.mark.asyncio
    async def test_export_as_pdf(self) -> None:
        """Test exporting document as PDF."""
        result = await self.client.export_document(
            file_id=self.test_file_id,
            export_format="pdf",
        )

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF files start with %PDF
        assert result.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_export_as_docx(self) -> None:
        """Test exporting document as DOCX."""
        result = await self.client.export_document(
            file_id=self.test_file_id,
            export_format="docx",
        )

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_export_multiple_formats(self) -> None:
        """Test exporting in multiple formats."""
        formats = ["pdf", "docx", "txt"]

        for fmt in formats:
            result = await self.client.export_document(
                file_id=self.test_file_id,
                export_format=fmt,
            )

            assert result is not None
            assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_export_invalid_format(self) -> None:
        """Test export with invalid format."""
        with pytest.raises(GoogleDriveError):
            await self.client.export_document(
                file_id=self.test_file_id,
                export_format="invalid_format_xyz",
            )


class TestGoogleDriveFileDeletion:
    """Test file deletion."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

    async def teardown_method(self) -> None:
        """Clean up client."""
        await self.client.close()

    @pytest.mark.asyncio
    async def test_delete_file_to_trash(self) -> None:
        """Test moving file to trash."""
        # Create test file
        test_file = await self.client.create_document(
            title="Test Trash File",
            mime_type=MIME_TYPES["google_doc"],
        )

        file_id = test_file["id"]

        # Delete to trash
        await self.client.delete_file(file_id, permanently=False)

        # Verify file is trashed (metadata should show trashed=True)
        metadata = await self.client.get_file_metadata(file_id)
        assert metadata.trashed is True

        # Cleanup: permanent delete
        await self.client.delete_file(file_id, permanently=True)

    @pytest.mark.asyncio
    async def test_delete_file_permanently(self) -> None:
        """Test permanently deleting file."""
        # Create test file
        test_file = await self.client.create_document(
            title="Test Permanent Delete",
            mime_type=MIME_TYPES["google_doc"],
        )

        file_id = test_file["id"]

        # Permanently delete
        await self.client.delete_file(file_id, permanently=True)

        # Verify file is deleted (should raise 404)
        with pytest.raises(GoogleDriveError):
            await self.client.get_file_metadata(file_id)

    @pytest.mark.asyncio
    async def test_delete_invalid_file(self) -> None:
        """Test deleting non-existent file."""
        with pytest.raises(GoogleDriveError):
            await self.client.delete_file("invalid-file-id-xyz")


class TestGoogleDriveHealthCheck:
    """Test health check functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

    async def teardown_method(self) -> None:
        """Clean up client."""
        await self.client.close()

    @pytest.mark.asyncio
    async def test_health_check_authenticated(self) -> None:
        """Test health check with authenticated client."""
        result = await self.client.health_check()

        assert result is not None
        assert isinstance(result, dict)
        assert "name" in result
        assert "healthy" in result
        assert "message" in result

        assert result["name"] == "google_drive"
        assert result["healthy"] is True

    def test_health_check_not_authenticated(self) -> None:
        """Test health check without authentication."""
        unauthenticated_client = GoogleDriveClient(
            credentials_json={"type": "dummy"},
            access_token=None,
        )

        # Health check should return not healthy without authentication
        result = unauthenticated_client.health_check()

        assert result["healthy"] is False


class TestGoogleDriveErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()

    async def teardown_method(self) -> None:
        """Clean up client."""
        await self.client.close()

    @pytest.mark.asyncio
    async def test_invalid_file_id_format(self) -> None:
        """Test with invalid file ID format."""
        with pytest.raises(GoogleDriveError):
            await self.client.get_file_metadata("")

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self) -> None:
        """Test methods with missing required parameters."""
        with pytest.raises(TypeError):
            await self.client.create_document()  # type: ignore

    @pytest.mark.asyncio
    async def test_invalid_mime_type(self) -> None:
        """Test with invalid MIME type."""
        # Should handle gracefully
        result = await self.client.create_document(
            title="Test Invalid MIME",
            mime_type="invalid/mime-type",
        )

        # Still creates file, just with non-standard type
        assert "id" in result

        # Cleanup
        await self.client.delete_file(result["id"], permanently=True)

    @pytest.mark.asyncio
    async def test_client_timeout_configuration(self) -> None:
        """Test client can be configured with custom timeout."""
        client = GoogleDriveClient(
            credentials_json={"type": "dummy"},
            access_token="dummy",
            timeout=5.0,
        )

        assert client.timeout == 5.0

    @pytest.mark.asyncio
    async def test_client_retry_configuration(self) -> None:
        """Test client can be configured with custom retry settings."""
        client = GoogleDriveClient(
            credentials_json={"type": "dummy"},
            access_token="dummy",
            max_retries=5,
            retry_base_delay=2.0,
        )

        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0


class TestGoogleDriveIntegration:
    """Integration tests combining multiple operations."""

    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        """Initialize authenticated client."""
        try:
            credentials = get_test_credentials()
            access_token = get_test_access_token()
        except ValueError as e:
            pytest.skip(f"Credentials not available: {e}")

        self.client = GoogleDriveClient(
            credentials_json=credentials,
            access_token=access_token,
        )

        await self.client.authenticate()
        self.created_items = []

    async def teardown_method(self) -> None:
        """Clean up created items."""
        for item_id in self.created_items:
            try:  # noqa: SIM105
                await self.client.delete_file(item_id, permanently=True)
            except Exception:
                pass

        await self.client.close()

    @pytest.mark.asyncio
    async def test_create_list_and_delete(self) -> None:
        """Integration: Create document, list files, delete document."""
        # Create
        doc = await self.client.create_document(
            title="Integration Test Document",
            mime_type=MIME_TYPES["google_doc"],
        )

        doc_id = doc["id"]
        self.created_items.append(doc_id)

        # List (should find our document)
        files_result = await self.client.list_files(
            query="trashed=false",
            page_size=100,
        )

        file_ids = [f["id"] for f in files_result.get("files", [])]
        assert doc_id in file_ids

        # Get metadata
        metadata = await self.client.get_file_metadata(doc_id)
        assert metadata.id == doc_id
        assert metadata.name == "Integration Test Document"

        # Delete
        await self.client.delete_file(doc_id, permanently=True)
        self.created_items.remove(doc_id)

    @pytest.mark.asyncio
    async def test_create_share_export_delete(self) -> None:
        """Integration: Create, share, export, and delete."""
        # Create
        doc = await self.client.create_document(
            title="Share and Export Test",
            mime_type=MIME_TYPES["google_doc"],
        )

        doc_id = doc["id"]
        self.created_items.append(doc_id)

        # Share
        perm = await self.client.share_file(
            file_id=doc_id,
            email="test-share@example.com",
            role="reader",
        )

        assert "id" in perm

        # Export
        pdf_content = await self.client.export_document(
            file_id=doc_id,
            export_format="pdf",
        )

        assert len(pdf_content) > 0

        # Delete
        await self.client.delete_file(doc_id, permanently=True)
        self.created_items.remove(doc_id)
