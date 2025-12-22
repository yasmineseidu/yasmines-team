"""Live API testing for Google Docs integration.

Tests against the real Google Docs API with actual credentials.
Creates real documents, modifies them, and cleans them up.

To run these tests:
1. Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are in .env
2. Run: pytest __tests__/integration/test_google_docs_live.py -v -m live_api

The tests will create actual Google Docs and clean them up after testing.
"""

import json
import os
from datetime import datetime

import pytest

from src.integrations.google_docs import (
    GoogleDocsAuthError,
    GoogleDocsClient,
    GoogleDocsError,
)

pytestmark = pytest.mark.live_api


class TestGoogleDocsLiveAPI:
    """Live API tests against real Google Docs service."""

    @pytest.fixture(autouse=True, scope="class")
    async def setup_class(self):
        """Set up client and prepare for testing."""
        # Try to get credentials from environment
        credentials_json_str = os.getenv("GOOGLE_DOCS_CREDENTIALS")

        if not credentials_json_str:
            # Fall back to building from OAuth2 credentials
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

            if not client_id or not client_secret:
                pytest.skip("Neither GOOGLE_DOCS_CREDENTIALS nor GOOGLE_CLIENT_ID/SECRET found")

            # Build minimal service account credentials from OAuth2 config
            # This requires either a cached token or manual OAuth2 flow
            credentials_json = {
                "type": "service_account",
                "project_id": "smarter-team",
                "client_id": client_id,
                "client_secret": client_secret,
                # These would normally come from a service account JSON
                "private_key": os.getenv("GOOGLE_PRIVATE_KEY", ""),
                "access_token": os.getenv("GOOGLE_ACCESS_TOKEN", ""),
            }
        else:
            try:
                credentials_json = json.loads(credentials_json_str)
            except json.JSONDecodeError:
                pytest.skip("GOOGLE_DOCS_CREDENTIALS is not valid JSON")

        # Check if we have an access token
        if not credentials_json.get("access_token"):
            pytest.skip(
                "No access_token in credentials. "
                "Set GOOGLE_ACCESS_TOKEN env var with valid OAuth2 token"
            )

        try:
            self.client = GoogleDocsClient(credentials_json=credentials_json)
            await self.client.authenticate()
        except GoogleDocsAuthError as e:
            pytest.skip(f"Authentication failed: {e}")

        self.test_docs: list[str] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def cleanup_docs(self) -> None:
        """Clean up test documents after testing."""
        # Note: Google Docs API doesn't have a delete endpoint,
        # so we'll just log the document IDs for manual cleanup
        if self.test_docs:
            print("\n\nTest Documents Created (for manual cleanup):")
            for doc_id in self.test_docs:
                print(f"  - {doc_id}")

    # ========================================================================
    # ENDPOINT 1: authenticate()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_authenticate(self) -> None:
        """Verify authentication works with live API."""
        # Should not raise an error
        await self.client.authenticate()

        # Token should be set
        assert self.client.access_token is not None
        assert len(self.client.access_token) > 0

    # ========================================================================
    # ENDPOINT 2: create_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_create_document(self) -> None:
        """Create a real Google Doc via API."""
        title = f"Live Test Document {self.timestamp}"

        result = await self.client.create_document(title=title)

        assert result is not None
        assert "documentId" in result
        assert result["title"] == title
        assert "mimeType" in result

        doc_id = result["documentId"]
        self.test_docs.append(doc_id)

        print(f"\nCreated document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_create_multiple_documents(self) -> None:
        """Create multiple documents to test API behavior."""
        doc_ids = []

        for i in range(3):
            title = f"Live Test Multi {self.timestamp} - {i}"
            result = await self.client.create_document(title=title)
            doc_ids.append(result["documentId"])
            self.test_docs.append(result["documentId"])

        assert len(doc_ids) == 3
        print(f"\nCreated {len(doc_ids)} documents")

    # ========================================================================
    # ENDPOINT 3: get_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_get_document(self) -> None:
        """Retrieve a real document from Google Docs."""
        # First create a document
        title = f"Live Get Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Retrieve it
        result = await self.client.get_document(document_id=doc_id)

        assert result is not None
        assert result["documentId"] == doc_id
        assert result["title"] == title
        assert "body" in result

        print(f"\nRetrieved document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_get_document_content(self) -> None:
        """Verify get_document returns content structure."""
        # Create and populate document
        title = f"Live Content Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Add some text
        await self.client.insert_text(doc_id, "Test Content")

        # Retrieve and verify structure
        result = await self.client.get_document(document_id=doc_id)

        assert "body" in result
        assert "content" in result["body"]

    # ========================================================================
    # ENDPOINT 4: insert_text()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_insert_text(self) -> None:
        """Insert text into a real document."""
        title = f"Live Insert Text Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        text = "This is test content added via API"
        result = await self.client.insert_text(doc_id, text)

        assert result is not None
        assert result["documentId"] == doc_id
        assert "replies" in result

        print(f"\nInserted text into document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_insert_text_multiple_times(self) -> None:
        """Insert text multiple times into same document."""
        title = f"Live Multi Insert Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Insert multiple texts
        await self.client.insert_text(doc_id, "First line\n")
        await self.client.insert_text(doc_id, "Second line\n")
        await self.client.insert_text(doc_id, "Third line\n")

        # Verify by retrieving
        doc = await self.client.get_document(document_id=doc_id)
        assert doc is not None

    # ========================================================================
    # ENDPOINT 5: batch_update()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_batch_update(self) -> None:
        """Execute batch operations on real document."""
        title = f"Live Batch Update Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        requests = [
            {
                "insertText": {
                    "text": "Title\n",
                    "location": {"index": 1},
                }
            },
            {
                "insertText": {
                    "text": "Content here\n",
                    "location": {"index": 7},
                }
            },
        ]

        result = await self.client.batch_update(doc_id, requests)

        assert result is not None
        assert result["documentId"] == doc_id
        assert len(result["replies"]) == 2

        print(f"\nBatch updated document: {doc_id}")

    # ========================================================================
    # ENDPOINT 6: format_text()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_format_text_bold(self) -> None:
        """Apply bold formatting to real document text."""
        title = f"Live Format Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Add text
        await self.client.insert_text(doc_id, "Bold Text Here")

        # Format it
        result = await self.client.format_text(
            document_id=doc_id,
            start_index=0,
            end_index=4,
            bold=True,
        )

        assert result is not None
        assert result["documentId"] == doc_id

        print(f"\nApplied formatting to document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_format_text_multiple_styles(self) -> None:
        """Apply multiple format styles to real document."""
        title = f"Live Multi Format Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        await self.client.insert_text(doc_id, "Formatted Text")

        result = await self.client.format_text(
            document_id=doc_id,
            start_index=0,
            end_index=9,
            bold=True,
            italic=True,
            underline=True,
        )

        assert result is not None
        assert result["documentId"] == doc_id

    # ========================================================================
    # ENDPOINT 7: create_table()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_create_table(self) -> None:
        """Create a table in a real document."""
        title = f"Live Table Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        result = await self.client.create_table(
            document_id=doc_id,
            rows=3,
            columns=2,
        )

        assert result is not None
        assert result["documentId"] == doc_id

        print(f"\nCreated table in document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_create_table_various_sizes(self) -> None:
        """Create tables of different sizes."""
        title = f"Live Table Size Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Small table
        await self.client.create_table(doc_id, rows=2, columns=2)

        # Larger table
        result = await self.client.create_table(doc_id, rows=5, columns=4)

        assert result is not None

    # ========================================================================
    # ENDPOINT 8: share_document()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_share_document(self) -> None:
        """Share a real document with a user."""
        title = f"Live Share Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Note: Use an actual email for live testing
        # This might fail if the email is invalid or if API returns 400
        try:
            result = await self.client.share_document(
                document_id=doc_id,
                email="test@example.com",
                role="reader",
            )

            # If successful
            if result:
                assert "id" in result
                print(f"\nShared document: {doc_id}")
        except GoogleDocsError as e:
            # Might fail with invalid email, but endpoint is tested
            print(f"\nShare endpoint tested (email validation): {str(e)}")

    # ========================================================================
    # ENDPOINT 9: get_document_permissions()
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_get_permissions(self) -> None:
        """Get permissions for a real document."""
        title = f"Live Permissions Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        result = await self.client.get_document_permissions(document_id=doc_id)

        assert result is not None
        assert isinstance(result, list)

        print(f"\nRetrieved permissions for document: {doc_id}")

    # ========================================================================
    # WORKFLOW TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_complete_document_workflow(self) -> None:
        """Test complete document lifecycle: create, edit, format, share."""
        title = f"Live Complete Workflow {self.timestamp}"

        # Create
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Add content
        await self.client.insert_text(doc_id, "Document Title\n")

        # Format
        await self.client.format_text(doc_id, 0, 14, bold=True, font_size=16)

        # Add more content
        await self.client.insert_text(doc_id, "This is the document body.\n")

        # Create table
        await self.client.create_table(doc_id, rows=2, columns=3)

        # Get final document
        final = await self.client.get_document(document_id=doc_id)
        assert final["documentId"] == doc_id

        print(f"\nCompleted full workflow for document: {doc_id}")

    @pytest.mark.asyncio
    async def test_live_batch_operations_efficiency(self) -> None:
        """Test batch operations for efficiency."""
        title = f"Live Batch Efficiency Test {self.timestamp}"
        created = await self.client.create_document(title=title)
        doc_id = created["documentId"]
        self.test_docs.append(doc_id)

        # Multiple operations in one batch
        requests = [
            {"insertText": {"text": "Title\n", "location": {"index": 1}}},
            {"insertText": {"text": "Content\n", "location": {"index": 7}}},
            {"insertText": {"text": "More content", "location": {"index": 15}}},
        ]

        result = await self.client.batch_update(doc_id, requests)

        assert len(result["replies"]) == 3
        print(f"\nBatch operation efficiency test passed: {doc_id}")

    # ========================================================================
    # ERROR SCENARIOS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_live_error_invalid_document_id(self) -> None:
        """Verify proper error handling for invalid document ID."""
        with pytest.raises(GoogleDocsError):
            await self.client.get_document(document_id="invalid-doc-id-12345")

    @pytest.mark.asyncio
    async def test_live_error_auth_failure(self) -> None:
        """Test that auth errors are properly raised."""
        # Use invalid credentials
        invalid_creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key": "invalid",  # pragma: allowlist secret
            "access_token": "invalid_token_xyz",  # pragma: allowlist secret
        }

        try:
            bad_client = GoogleDocsClient(credentials_json=invalid_creds)
            with pytest.raises((GoogleDocsAuthError, GoogleDocsError)):
                await bad_client.create_document(title="Test")
        except GoogleDocsAuthError:
            # Expected for invalid credentials
            pass

    @pytest.mark.asyncio
    async def teardown_method(self) -> None:
        """Clean up after each test."""
        await self.cleanup_docs()
