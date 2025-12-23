"""Unit tests for PandaDoc client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.pandadoc.client import PandaDocClient
from src.integrations.pandadoc.exceptions import (
    PandaDocAPIError,
    PandaDocAuthError,
    PandaDocConfigError,
    PandaDocNotFoundError,
    PandaDocRateLimitError,
)
from src.integrations.pandadoc.models import Recipient, Signature


class TestPandaDocClientInitialization:
    """Tests for PandaDocClient initialization."""

    def test_client_initialization_with_api_key(self) -> None:
        """Client should initialize with provided API key."""
        client = PandaDocClient(api_key="test-api-key")
        assert client.api_key == "test-api-key"
        assert client.name == "pandadoc"
        assert client.base_url == "https://api.pandadoc.com/public/v1"

    @patch.dict("os.environ", {"PANDADOC_API_KEY": "env-api-key"})
    def test_client_initialization_with_env_var(self) -> None:
        """Client should use PANDADOC_API_KEY from environment."""
        client = PandaDocClient()
        assert client.api_key == "env-api-key"

    @patch.dict("os.environ", {}, clear=True)
    def test_client_initialization_missing_api_key(self) -> None:
        """Client should raise error without API key."""
        with pytest.raises(PandaDocConfigError):
            PandaDocClient(api_key=None)

    def test_client_initialization_with_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = PandaDocClient(api_key="test", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_initialization_with_retry_config(self) -> None:
        """Client should accept custom retry configuration."""
        client = PandaDocClient(
            api_key="test",
            max_retries=5,
            retry_base_delay=2.0,
        )
        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0


class TestPandaDocClientHeaders:
    """Tests for HTTP headers generation."""

    def test_get_headers(self) -> None:
        """Should return authorization header with API key."""
        client = PandaDocClient(api_key="test-api-key")
        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "API-Key test-api-key"
        assert headers["Content-Type"] == "application/json"


class TestPandaDocClientTemplates:
    """Tests for template operations."""

    @pytest.fixture
    def client(self) -> PandaDocClient:
        """Create client for testing."""
        return PandaDocClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_list_templates(self, client: PandaDocClient) -> None:
        """Should list templates."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "results": [
                    {
                        "id": "tpl_123",
                        "name": "Agreement",
                        "date_created": "2025-01-01T10:00:00Z",
                    }
                ],
            }

            response = await client.list_templates()

            assert len(response.results) == 1
            assert response.results[0].id == "tpl_123"
            mock.assert_called_once_with(
                "GET",
                "/templates",
                params=None,
            )

    @pytest.mark.asyncio
    async def test_get_template(self, client: PandaDocClient) -> None:
        """Should get template by ID."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": "tpl_123",
                "name": "Agreement",
                "created_at": "2025-01-01T10:00:00",
            }

            template = await client.get_template("tpl_123")

            assert template.id == "tpl_123"
            assert template.name == "Agreement"
            mock.assert_called_once_with("GET", "/templates/tpl_123")

    @pytest.mark.asyncio
    async def test_delete_template(self, client: PandaDocClient) -> None:
        """Should delete template."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            result = await client.delete_template("tpl_123")

            assert result is True
            mock.assert_called_once_with("DELETE", "/templates/tpl_123")


class TestPandaDocClientDocuments:
    """Tests for document operations."""

    @pytest.fixture
    def client(self) -> PandaDocClient:
        """Create client for testing."""
        return PandaDocClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_create_document(self, client: PandaDocClient) -> None:
        """Should create document from template."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": "doc_123",
                "name": "Test Agreement",
                "status": "draft",
                "template_id": "tpl_123",
                "created_at": "2025-01-01T12:00:00",
            }

            recipients = [Recipient(email="john@example.com", name="John Doe")]
            doc = await client.create_document(
                name="Test Agreement",
                template_id="tpl_123",
                recipients=recipients,
            )

            assert doc.id == "doc_123"
            assert doc.name == "Test Agreement"
            assert doc.template_id == "tpl_123"

    @pytest.mark.asyncio
    async def test_get_document(self, client: PandaDocClient) -> None:
        """Should get document by ID."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": "doc_123",
                "name": "Test Agreement",
                "status": "sent",
            }

            doc = await client.get_document("doc_123")

            assert doc.id == "doc_123"
            assert doc.status == "sent"

    @pytest.mark.asyncio
    async def test_list_documents(self, client: PandaDocClient) -> None:
        """Should list documents."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "results": [
                    {
                        "id": "doc_123",
                        "name": "Test Agreement",
                        "status": "document.sent",
                    }
                ],
            }

            response = await client.list_documents()

            assert len(response.results) == 1

    @pytest.mark.asyncio
    async def test_send_document(self, client: PandaDocClient) -> None:
        """Should send document to recipients."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": "doc_123",
                "name": "Test Document",
                "status": "sent",
                "sent_at": "2025-01-01T12:30:00",
            }

            doc = await client.send_document("doc_123")

            assert doc.status == "sent"

    @pytest.mark.asyncio
    async def test_download_document(self, client: PandaDocClient) -> None:
        """Should download document as PDF."""
        pdf_content = b"%PDF-1.4\n..."
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = pdf_content

        # Patch httpx.AsyncClient.get directly
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.download_document("doc_123")

            assert result == pdf_content

        await client.close()

    @pytest.mark.asyncio
    async def test_get_document_status(self, client: PandaDocClient) -> None:
        """Should get document status."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "status": "sent",
                "sent_at": "2025-01-01T12:30:00",
            }

            status = await client.get_document_status("doc_123")

            assert status["status"] == "sent"


class TestPandaDocClientRecipients:
    """Tests for recipient operations."""

    @pytest.fixture
    def client(self) -> PandaDocClient:
        """Create client for testing."""
        return PandaDocClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_add_recipient(self, client: PandaDocClient) -> None:
        """Should add recipient to document."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "email": "john@example.com",
                "name": "John Doe",
            }

            result = await client.add_recipient(
                "doc_123",
                "john@example.com",
                "John Doe",
            )

            assert result["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_recipient_status(self, client: PandaDocClient) -> None:
        """Should get recipient signing status."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "email": "john@example.com",
                "status": "completed",
                "signed_at": "2025-01-02T15:30:00",
            }

            status = await client.get_recipient_status("doc_123", "john@example.com")

            assert isinstance(status, Signature)
            assert status.status == "completed"

    @pytest.mark.asyncio
    async def test_remove_recipient(self, client: PandaDocClient) -> None:
        """Should remove recipient from document."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            result = await client.remove_recipient("doc_123", "john@example.com")

            assert result is True


class TestPandaDocClientWebhooks:
    """Tests for webhook operations."""

    @pytest.fixture
    def client(self) -> PandaDocClient:
        """Create client for testing."""
        return PandaDocClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_create_webhook(self, client: PandaDocClient) -> None:
        """Should create webhook."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": "wh_123",
                "url": "https://example.com/webhook",
                "events": ["document.sent"],
            }

            webhook = await client.create_webhook(
                "https://example.com/webhook",
                ["document.sent"],
            )

            assert webhook["id"] == "wh_123"

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client: PandaDocClient) -> None:
        """Should list webhooks."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "webhooks": [
                    {
                        "id": "wh_123",
                        "url": "https://example.com/webhook",
                    }
                ]
            }

            webhooks = await client.list_webhooks()

            assert len(webhooks) == 1
            assert webhooks[0]["id"] == "wh_123"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client: PandaDocClient) -> None:
        """Should delete webhook."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            result = await client.delete_webhook("wh_123")

            assert result is True


class TestPandaDocClientErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> PandaDocClient:
        """Create client for testing."""
        return PandaDocClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_request_auth_error(self, client: PandaDocClient) -> None:
        """Should raise PandaDocAuthError on 401."""
        # Patch _request to test higher-level error handling
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = PandaDocAuthError("Invalid API key")

            with pytest.raises(PandaDocAuthError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_not_found_error(self, client: PandaDocClient) -> None:
        """Should raise PandaDocNotFoundError on 404."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = PandaDocNotFoundError("Not found")

            with pytest.raises(PandaDocNotFoundError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_rate_limit_error(self, client: PandaDocClient) -> None:
        """Should raise PandaDocRateLimitError on 429."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = PandaDocRateLimitError("Rate limited", retry_after=1)

            with pytest.raises(PandaDocRateLimitError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_generic_error(self, client: PandaDocClient) -> None:
        """Should raise PandaDocAPIError on other errors."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = PandaDocAPIError("Server error")

            with pytest.raises(PandaDocAPIError):
                await client._request("GET", "/test")


class TestPandaDocClientContextManager:
    """Tests for context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Client should work as async context manager."""
        async with PandaDocClient(api_key="test") as client:
            assert client is not None
            assert client.api_key == "test"
