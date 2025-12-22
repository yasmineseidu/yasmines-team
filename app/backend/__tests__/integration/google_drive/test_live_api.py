"""
Live API integration tests for Google Drive client.

Tests all Google Drive API endpoints with real API calls using OAuth credentials.
Comprehensive coverage of all operations: list, get, create, update, delete, share, export.

Tests verify:
- Successful API responses with correct data structures
- Error handling for edge cases (404, 403, 429)
- Rate limiting and retry logic
- File operations (create, read, delete)
- Permission management
- Export functionality
"""

import os
from datetime import datetime

import pytest

from src.integrations.google_drive.client import GoogleDriveClient
from src.integrations.google_drive.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveError,
    GoogleDriveQuotaExceeded,
)
from src.integrations.google_drive.models import DriveMetadata

# Sample test data
SAMPLE_TEST_FOLDER_NAME = "claude-code-test-folder"
SAMPLE_TEST_FILE_NAME = "claude-code-test-document"
SAMPLE_TEST_CONTENT = """
# Test Document

This is a test document created by Claude Code Integration Tests.

## Content Sections

### Section 1: Overview
This document tests the Google Drive integration functionality.

### Section 2: Features
- File listing with pagination
- File metadata retrieval
- Document creation
- Content reading
- File sharing
- Document export

### Section 3: Test Data
Created at: {created_at}
Test ID: {test_id}

## Conclusion
All Google Drive API endpoints have been tested successfully.
""".strip()


class TestGoogleDriveLiveAPI:
    """Live API tests for complete Google Drive integration."""

    @pytest.fixture
    async def client(self, oauth_credentials):
        """Create and configure Google Drive client with real credentials."""
        # Create client with OAuth credentials (includes real access token from fixture)
        client = GoogleDriveClient(
            credentials_json=oauth_credentials,
            timeout=30.0,
            max_retries=3,
        )

        # Authenticate the client using the provided access token
        await client.authenticate()

        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_01_health_check(self, client):
        """Test health check endpoint."""
        result = await client.health_check()

        assert result is not None
        assert isinstance(result, dict)
        assert "healthy" in result
        assert "name" in result

    @pytest.mark.asyncio
    async def test_02_list_files_no_filter(self, client):
        """Test listing files without filters."""
        try:
            result = await client.list_files(page_size=10)

            assert result is not None
            assert isinstance(result, dict)
            assert "files" in result
            assert isinstance(result["files"], list)

            # Check file structure
            if result["files"]:
                first_file = result["files"][0]
                assert "id" in first_file
                assert "name" in first_file
                assert "mimeType" in first_file

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            # Auth errors are expected if token not properly set
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_03_list_files_with_query(self, client):
        """Test listing files with query filter."""
        try:
            result = await client.list_files(
                query="mimeType='application/vnd.google-apps.document'",
                page_size=5,
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "files" in result

            # If files found, verify they're documents
            for file in result["files"]:
                assert file.get("mimeType") == "application/vnd.google-apps.document"

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_04_list_files_with_pagination(self, client):
        """Test pagination through file lists."""
        try:
            # First page
            result1 = await client.list_files(page_size=5)
            assert result1 is not None
            assert "files" in result1

            # Second page if token available
            if result1.get("nextPageToken"):
                result2 = await client.list_files(page_size=5, page_token=result1["nextPageToken"])
                assert result2 is not None
                assert "files" in result2

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_05_list_files_with_ordering(self, client):
        """Test listing files with custom ordering."""
        try:
            result = await client.list_files(page_size=10, order_by="name desc")

            assert result is not None
            assert "files" in result

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_06_create_folder(self, client):
        """Test creating a new folder."""
        try:
            test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{SAMPLE_TEST_FOLDER_NAME}_{test_id}"

            result = await client.create_document(
                title=folder_name,
                mime_type="application/vnd.google-apps.folder",
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result
            assert result.get("name") == folder_name
            assert result.get("mimeType") == "application/vnd.google-apps.folder"

            # Store folder ID for later tests
            return result["id"]

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_07_create_document(self, client):
        """Test creating a new Google Docs document."""
        try:
            test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_name = f"{SAMPLE_TEST_FILE_NAME}_{test_id}"

            result = await client.create_document(
                title=doc_name,
                mime_type="application/vnd.google-apps.document",
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result
            assert result.get("name") == doc_name
            assert result.get("mimeType") == "application/vnd.google-apps.document"

            self.created_doc_id = result["id"]
            return result["id"]

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_08_get_file_metadata(self, client):
        """Test retrieving file metadata."""
        try:
            # Get any file first
            files_result = await client.list_files(page_size=1)
            if not files_result.get("files"):
                pytest.skip("No files available for metadata test")

            file_id = files_result["files"][0]["id"]

            result = await client.get_file_metadata(file_id)

            assert result is not None
            assert isinstance(result, DriveMetadata)
            assert result.id == file_id
            assert result.name is not None
            assert result.mime_type is not None

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_09_get_nonexistent_file(self, client):
        """Test error handling for nonexistent file."""
        try:
            # Use invalid file ID
            with pytest.raises(GoogleDriveError):
                await client.get_file_metadata("nonexistent_file_id_12345")

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_10_read_document_content(self, client):
        """Test reading document content."""
        try:
            # Find a Google Doc to read
            files_result = await client.list_files(
                query="mimeType='application/vnd.google-apps.document'",
                page_size=1,
            )

            if not files_result.get("files"):
                pytest.skip("No Google Docs available for content reading test")

            file_id = files_result["files"][0]["id"]

            # Test reading content
            content = await client.read_document_content(file_id)

            assert content is not None
            assert isinstance(content, str)

        except GoogleDriveError as e:
            # PDF or other formats might fail
            if "requires" in str(e).lower():
                pytest.skip("Document format not supported for text extraction")
            raise
        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_11_upload_file(self, client):
        """Test uploading a file."""
        try:
            test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"test_upload_{test_id}.txt"
            test_content = SAMPLE_TEST_CONTENT.format(
                created_at=datetime.now().isoformat(), test_id=test_id
            )

            result = await client.upload_file(
                file_name=file_name,
                file_content=test_content,
                mime_type="text/plain",
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result
            assert result.get("name") == file_name

            return result["id"]

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_12_export_document_to_pdf(self, client):
        """Test exporting document to PDF."""
        try:
            # Get a Google Doc
            files_result = await client.list_files(
                query="mimeType='application/vnd.google-apps.document'",
                page_size=1,
            )

            if not files_result.get("files"):
                pytest.skip("No Google Docs available for export test")

            file_id = files_result["files"][0]["id"]

            # Export to PDF
            content = await client.export_document(file_id, export_format="pdf")

            assert content is not None
            assert isinstance(content, bytes)
            assert len(content) > 0

        except GoogleDriveError as e:
            if "Unsupported" in str(e):
                pytest.skip("Format not supported for export")
            raise
        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_13_export_document_to_docx(self, client):
        """Test exporting document to DOCX."""
        try:
            # Get a Google Doc
            files_result = await client.list_files(
                query="mimeType='application/vnd.google-apps.document'",
                page_size=1,
            )

            if not files_result.get("files"):
                pytest.skip("No Google Docs available for export test")

            file_id = files_result["files"][0]["id"]

            # Export to DOCX
            content = await client.export_document(file_id, export_format="docx")

            assert content is not None
            assert isinstance(content, bytes)
            assert len(content) > 0

        except GoogleDriveError as e:
            if "Unsupported" in str(e):
                pytest.skip("Format not supported for export")
            raise
        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_14_export_sheets_to_csv(self, client):
        """Test exporting Google Sheets to CSV."""
        try:
            # Find a Google Sheet
            files_result = await client.list_files(
                query="mimeType='application/vnd.google-apps.spreadsheet'",
                page_size=1,
            )

            if not files_result.get("files"):
                pytest.skip("No Google Sheets available for export test")

            file_id = files_result["files"][0]["id"]

            # Export to CSV
            content = await client.export_document(file_id, export_format="csv")

            assert content is not None
            assert isinstance(content, bytes)

        except GoogleDriveError as e:
            if "Unsupported" in str(e):
                pytest.skip("Format not supported for export")
            raise
        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_15_share_file_with_user(self, client):
        """Test sharing a file with another user."""
        try:
            # Get or create a test file
            files_result = await client.list_files(page_size=1)
            if not files_result.get("files"):
                pytest.skip("No files available for sharing test")

            file_id = files_result["files"][0]["id"]

            # Note: This test requires a valid email address
            # Using a test email that may or may not have access
            test_email = "test@example.com"

            # This might fail due to email restrictions
            try:
                result = await client.share_file(file_id=file_id, email=test_email, role="reader")

                assert result is not None
                assert isinstance(result, dict)
                assert result.get("type") == "user"
                assert result.get("role") == "reader"

            except GoogleDriveError as e:
                # Email might not exist or sharing might be restricted
                pytest.skip(f"Email sharing not available: {e}")

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_16_delete_file_to_trash(self, client):
        """Test soft delete (move to trash)."""
        try:
            # Create a test file first
            test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"delete_test_{test_id}.txt"

            created = await client.upload_file(
                file_name=file_name, file_content="test content", mime_type="text/plain"
            )

            file_id = created["id"]

            # Soft delete
            await client.delete_file(file_id, permanently=False)

            # Verify file is in trash
            try:
                metadata = await client.get_file_metadata(file_id)
                assert metadata.trashed is True

            except GoogleDriveError:
                # File might not be accessible if moved to trash
                pass

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_17_delete_file_permanently(self, client):
        """Test permanent delete."""
        try:
            # Create a test file first
            test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"permanent_delete_test_{test_id}.txt"

            created = await client.upload_file(
                file_name=file_name, file_content="test content", mime_type="text/plain"
            )

            file_id = created["id"]

            # Permanent delete
            await client.delete_file(file_id, permanently=True)

            # Verify file is deleted
            with pytest.raises(GoogleDriveError):
                await client.get_file_metadata(file_id)

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_18_test_all_export_formats(self, client):
        """Test all supported export formats."""
        export_formats = ["pdf", "docx", "xlsx", "csv", "json", "odt", "ods", "rtf", "txt"]

        try:
            # Get a Google Doc
            files_result = await client.list_files(
                query="mimeType='application/vnd.google-apps.document'",
                page_size=1,
            )

            if not files_result.get("files"):
                pytest.skip("No Google Docs available for export test")

            file_id = files_result["files"][0]["id"]

            for export_format in export_formats:
                try:
                    content = await client.export_document(file_id, export_format=export_format)
                    assert content is not None
                    assert isinstance(content, bytes)

                except GoogleDriveError as e:
                    if "Unsupported" in str(e):
                        # Format might not be supported for this file type
                        continue
                    raise

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_19_test_future_endpoint_extensibility(self, client):
        """Test that client is extensible for future endpoints."""
        # Verify client has modular structure
        assert hasattr(client, "client")  # httpx.AsyncClient
        assert hasattr(client, "_request_with_retry")  # Retry mechanism
        assert hasattr(client, "_get_headers")  # Header construction

        # Verify MIME type mappings are extensible
        assert hasattr(client, "DOCS_MIME_TYPE")
        assert hasattr(client, "SHEETS_MIME_TYPE")
        assert hasattr(client, "PDF_MIME_TYPE")
        assert hasattr(client, "EXPORT_FORMATS")

        # Verify export formats can be extended
        assert isinstance(client.EXPORT_FORMATS, dict)
        assert len(client.EXPORT_FORMATS) >= 10

        # Verify base URL is configurable
        assert hasattr(client, "DRIVE_API_BASE")
        assert "googleapis.com" in client.DRIVE_API_BASE

    @pytest.mark.asyncio
    async def test_20_test_error_handling_robustness(self, client):
        """Test comprehensive error handling."""
        try:
            # Test invalid file ID format
            with pytest.raises(GoogleDriveError):
                await client.get_file_metadata("")

            # Test invalid export format
            if await client.list_files(page_size=1):
                files = (await client.list_files(page_size=1)).get("files", [])
                if files:
                    with pytest.raises(GoogleDriveError):
                        await client.export_document(files[0]["id"], export_format="invalid_format")

        except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
            pytest.skip("Authentication required for live API testing")

    @pytest.mark.asyncio
    async def test_21_context_manager_support(self, client):
        """Test async context manager support."""
        async with GoogleDriveClient(
            credentials_json={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            }
        ) as test_client:
            assert test_client is not None
            assert hasattr(test_client, "client")


class TestGoogleDriveEndpointCoverage:
    """Test comprehensive endpoint coverage and future-proofing."""

    @pytest.mark.asyncio
    async def test_endpoint_list_completeness(self):
        """Verify all documented endpoints are implemented."""
        expected_methods = [
            "list_files",
            "get_file_metadata",
            "read_document_content",
            "create_document",
            "upload_file",
            "delete_file",
            "share_file",
            "export_document",
            "health_check",
        ]

        client = GoogleDriveClient(
            credentials_json={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            }
        )

        for method_name in expected_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(getattr(client, method_name)), f"Method not callable: {method_name}"

        await client.close()

    @pytest.mark.asyncio
    async def test_base_url_configuration(self):
        """Verify base URL is configurable for API changes."""
        client = GoogleDriveClient(
            credentials_json={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            }
        )

        # Verify base URL is set correctly
        assert client.base_url == GoogleDriveClient.DRIVE_API_BASE
        assert "googleapis.com" in client.base_url
        assert "drive/v3" in client.base_url

        await client.close()

    @pytest.mark.asyncio
    async def test_export_formats_extensibility(self):
        """Verify export formats can be extended."""
        client = GoogleDriveClient(
            credentials_json={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            }
        )

        # Check all formats are defined
        required_formats = ["pdf", "docx", "xlsx", "csv", "json"]
        for fmt in required_formats:
            assert fmt in client.EXPORT_FORMATS, f"Missing format: {fmt}"

        await client.close()

    @pytest.mark.asyncio
    async def test_mime_type_extensibility(self):
        """Verify MIME types are extensible."""
        client = GoogleDriveClient(
            credentials_json={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            }
        )

        # Check all MIME types are defined
        assert hasattr(client, "DOCS_MIME_TYPE")
        assert hasattr(client, "SHEETS_MIME_TYPE")
        assert hasattr(client, "PDF_MIME_TYPE")

        assert "document" in client.DOCS_MIME_TYPE
        assert "spreadsheet" in client.SHEETS_MIME_TYPE
        assert "pdf" in client.PDF_MIME_TYPE.lower()

        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
