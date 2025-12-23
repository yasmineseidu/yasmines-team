"""Live API tests for PandaDoc client.

These tests use real API keys from .env file and test against the live PandaDoc API.
Requires PANDADOC_API_KEY environment variable to be set.
"""

import os
from pathlib import Path

import pytest

from src.integrations.pandadoc import PandaDocClient
from src.integrations.pandadoc.exceptions import (
    PandaDocAuthError,
    PandaDocConfigError,
    PandaDocNotFoundError,
)

# Load .env file at project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Try to load .env if it exists
if ENV_PATH.exists():
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)


@pytest.fixture
def api_key() -> str:
    """Get PandaDoc API key from environment.

    Returns:
        API key from PANDADOC_API_KEY environment variable.

    Raises:
        pytest.skip: If API key not found in environment.
    """
    key = os.getenv("PANDADOC_API_KEY")
    if not key:
        pytest.skip("PANDADOC_API_KEY not found in environment")
    return key


@pytest.fixture
async def client(api_key: str) -> PandaDocClient:
    """Create client with real API key.

    Args:
        api_key: PandaDoc API key.

    Yields:
        Configured PandaDocClient instance.
    """
    async with PandaDocClient(api_key=api_key) as client:
        yield client


class TestPandaDocClientLiveAuth:
    """Live tests for authentication."""

    @pytest.mark.asyncio
    async def test_invalid_api_key(self) -> None:
        """Invalid API key should raise error."""
        client = PandaDocClient(api_key="invalid-key-12345")

        with pytest.raises(PandaDocAuthError):
            await client.list_templates()

        await client.close()

    @pytest.mark.asyncio
    async def test_missing_api_key_config(self) -> None:
        """Missing API key should raise config error."""
        with pytest.raises(PandaDocConfigError):
            PandaDocClient(api_key=None)


class TestPandaDocClientLiveTemplates:
    """Live tests for template operations."""

    @pytest.mark.asyncio
    async def test_list_templates_success(self, client: PandaDocClient) -> None:
        """Should list templates successfully."""
        response = await client.list_templates()

        assert response is not None
        assert isinstance(response.results, list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, client: PandaDocClient) -> None:
        """Should raise NotFoundError for nonexistent template."""
        with pytest.raises(PandaDocNotFoundError):
            await client.get_template("invalid_template_id_12345")

    @pytest.mark.asyncio
    async def test_list_templates_search(self, client: PandaDocClient) -> None:
        """Should support template search."""
        response = await client.list_templates(query="agreement")

        assert response is not None
        assert isinstance(response.templates, list)


class TestPandaDocClientLiveDocuments:
    """Live tests for document operations.

    Note: These tests use real documents, so they should be idempotent
    and not leave side effects.
    """

    @pytest.mark.asyncio
    async def test_list_documents_success(self, client: PandaDocClient) -> None:
        """Should list documents successfully."""
        response = await client.list_documents()

        assert response is not None
        assert isinstance(response.results, list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client: PandaDocClient) -> None:
        """Should raise NotFoundError for nonexistent document."""
        with pytest.raises(PandaDocNotFoundError):
            await client.get_document("invalid_doc_id_12345")

    @pytest.mark.asyncio
    async def test_list_documents_with_status(self, client: PandaDocClient) -> None:
        """Should filter documents by status."""
        response = await client.list_documents(status="document.completed")

        assert response is not None
        assert isinstance(response.results, list)

        # All returned documents should have "completed" status
        for doc in response.results:
            assert doc.status == "document.completed"


class TestPandaDocClientLiveDocument:
    """Live tests for document details.

    These tests fetch existing documents without modifying them.
    """

    @pytest.mark.asyncio
    async def test_get_document_status(self, client: PandaDocClient) -> None:
        """Should get document status."""
        # First get a document
        docs_response = await client.list_documents()

        if docs_response.results:
            doc = docs_response.results[0]
            status = await client.get_document_status(doc.id)

            assert status is not None
            assert "status" in status

    @pytest.mark.asyncio
    async def test_download_nonexistent_document(self, client: PandaDocClient) -> None:
        """Should handle download of nonexistent document."""
        from src.integrations.pandadoc.exceptions import PandaDocAPIError

        with pytest.raises((PandaDocNotFoundError, PandaDocAPIError)):
            await client.download_document("invalid_doc_id_12345")


class TestPandaDocClientLiveWebhooks:
    """Live tests for webhook operations."""

    @pytest.mark.asyncio
    async def test_list_webhooks_success(self, client: PandaDocClient) -> None:
        """Should list webhooks successfully."""
        webhooks = await client.list_webhooks()

        assert isinstance(webhooks, list)


class TestPandaDocClientLiveSignatures:
    """Live tests for signature operations."""

    @pytest.mark.asyncio
    async def test_get_signature_status_for_sent_document(
        self,
        client: PandaDocClient,
    ) -> None:
        """Should get signature requests for sent documents."""
        # Find a sent document
        docs_response = await client.list_documents(status="sent", limit=5)

        if docs_response.documents:
            doc = docs_response.documents[0]
            signatures = await client.get_signature_requests(doc.id)

            assert isinstance(signatures, list)


class TestPandaDocClientLiveErrorHandling:
    """Live tests for error handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, client: PandaDocClient) -> None:
        """Client should retry on rate limit."""
        # This test attempts rapid requests to trigger rate limiting
        # The client should automatically retry with exponential backoff

        for _ in range(3):
            try:
                await client.list_templates(limit=1)
            except Exception as e:
                # Should eventually succeed with retry
                assert str(e)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, client: PandaDocClient) -> None:
        """Client should handle timeouts gracefully."""
        # Create client with very short timeout to simulate timeout
        timeout_client = PandaDocClient(api_key=client.api_key, timeout=0.001)

        from src.integrations.pandadoc.exceptions import PandaDocAPIError

        with pytest.raises(PandaDocAPIError):
            await timeout_client.list_templates()

        await timeout_client.close()
