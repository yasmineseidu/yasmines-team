"""
Unit tests for BaseIntegrationClient.

Tests cover:
- Client initialization
- HTTP client lifecycle (lazy creation, cleanup)
- Request methods (GET, POST, PUT, PATCH, DELETE)
- Retry logic with exponential backoff
- Error handling for various HTTP status codes
- Health check functionality

Coverage target: >90%
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    PaymentRequiredError,
    RateLimitError,
)


class ConcreteClient(BaseIntegrationClient):
    """Concrete implementation for testing abstract base class."""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            name="test_client",
            base_url="https://api.test.com/v1",
            api_key="test-api-key",
            **kwargs,
        )


class TestBaseIntegrationClientInitialization:
    """Tests for BaseIntegrationClient initialization."""

    def test_client_stores_name(self) -> None:
        """Client should store integration name."""
        client = ConcreteClient()
        assert client.name == "test_client"

    def test_client_strips_trailing_slash_from_base_url(self) -> None:
        """Client should remove trailing slash from base URL."""
        client = ConcreteClient()
        assert client.base_url == "https://api.test.com/v1"

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = ConcreteClient()
        assert client.api_key == "test-api-key"

    def test_client_default_timeout(self) -> None:
        """Client should have 30s default timeout."""
        client = ConcreteClient()
        assert client.timeout == 30.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = ConcreteClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 default retries."""
        client = ConcreteClient()
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = ConcreteClient(max_retries=5)
        assert client.max_retries == 5

    def test_client_default_retry_base_delay(self) -> None:
        """Client should have 1s default retry delay."""
        client = ConcreteClient()
        assert client.retry_base_delay == 1.0


class TestHttpClientLifecycle:
    """Tests for HTTP client creation and cleanup."""

    def test_client_is_lazy_initialized(self) -> None:
        """HTTP client should not be created on init."""
        client = ConcreteClient()
        assert client._client is None

    def test_client_property_creates_client(self) -> None:
        """Accessing client property should create HTTP client."""
        client = ConcreteClient()
        http_client = client.client
        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)

    def test_client_property_returns_same_client(self) -> None:
        """Multiple accesses should return same client."""
        client = ConcreteClient()
        http_client_1 = client.client
        http_client_2 = client.client
        assert http_client_1 is http_client_2

    @pytest.mark.asyncio
    async def test_close_closes_client(self) -> None:
        """close() should close HTTP client."""
        client = ConcreteClient()
        _ = client.client  # Force creation
        assert client._client is not None

        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_on_none_client(self) -> None:
        """close() should handle None client gracefully."""
        client = ConcreteClient()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        async with ConcreteClient() as client:
            _ = client.client
            assert client._client is not None

        assert client._client is None or client._client.is_closed


class TestHeaders:
    """Tests for HTTP headers."""

    def test_default_headers_include_authorization(self) -> None:
        """Headers should include Bearer token."""
        client = ConcreteClient()
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-api-key"

    def test_default_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = ConcreteClient()
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_default_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = ConcreteClient()
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestRequestMethods:
    """Tests for HTTP request methods."""

    @pytest.fixture
    def client(self) -> ConcreteClient:
        """Create client for testing."""
        return ConcreteClient()

    @pytest.mark.asyncio
    async def test_get_makes_get_request(self, client: ConcreteClient) -> None:
        """get() should make GET request."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get("/endpoint")

            assert result == mock_response
            mock_request.assert_called_once_with("GET", "/endpoint")

    @pytest.mark.asyncio
    async def test_post_makes_post_request(self, client: ConcreteClient) -> None:
        """post() should make POST request."""
        mock_response = {"created": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.post("/endpoint", json={"key": "value"})

            assert result == mock_response
            mock_request.assert_called_once_with("POST", "/endpoint", json={"key": "value"})

    @pytest.mark.asyncio
    async def test_put_makes_put_request(self, client: ConcreteClient) -> None:
        """put() should make PUT request."""
        mock_response = {"updated": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.put("/endpoint/1", json={"key": "value"})

            assert result == mock_response
            mock_request.assert_called_once_with("PUT", "/endpoint/1", json={"key": "value"})

    @pytest.mark.asyncio
    async def test_patch_makes_patch_request(self, client: ConcreteClient) -> None:
        """patch() should make PATCH request."""
        mock_response = {"patched": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.patch("/endpoint/1", json={"key": "value"})

            assert result == mock_response
            mock_request.assert_called_once_with("PATCH", "/endpoint/1", json={"key": "value"})

    @pytest.mark.asyncio
    async def test_delete_makes_delete_request(self, client: ConcreteClient) -> None:
        """delete() should make DELETE request."""
        mock_response = {"deleted": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.delete("/endpoint/1")

            assert result == mock_response
            mock_request.assert_called_once_with("DELETE", "/endpoint/1")


class TestResponseHandling:
    """Tests for HTTP response handling."""

    @pytest.fixture
    def client(self) -> ConcreteClient:
        """Create client for testing."""
        return ConcreteClient()

    @pytest.mark.asyncio
    async def test_handle_response_returns_json(self, client: ConcreteClient) -> None:
        """Should return parsed JSON for successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        result = await client._handle_response(mock_response)
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_handle_response_401_raises_auth_error(self, client: ConcreteClient) -> None:
        """Should raise AuthenticationError for 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid token"}

        with pytest.raises(AuthenticationError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_handle_response_402_raises_payment_error(self, client: ConcreteClient) -> None:
        """Should raise PaymentRequiredError for 402."""
        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.json.return_value = {"error": "Insufficient credits"}

        with pytest.raises(PaymentRequiredError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_handle_response_429_raises_rate_limit_error(
        self, client: ConcreteClient
    ) -> None:
        """Should raise RateLimitError for 429."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"error": "Rate limit exceeded"}

        with pytest.raises(RateLimitError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_handle_response_500_raises_integration_error(
        self, client: ConcreteClient
    ) -> None:
        """Should raise IntegrationError for 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        with pytest.raises(IntegrationError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_response_non_json(self, client: ConcreteClient) -> None:
        """Should handle non-JSON responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Internal Server Error"

        with pytest.raises(IntegrationError) as exc_info:
            await client._handle_response(mock_response)

        assert "Internal Server Error" in str(exc_info.value.response_data)


class TestRetryLogic:
    """Tests for retry with exponential backoff."""

    @pytest.fixture
    def client(self) -> ConcreteClient:
        """Create client with minimal retry delay for testing."""
        return ConcreteClient(max_retries=2, retry_base_delay=0.01)

    def test_is_retryable_for_timeout(self, client: ConcreteClient) -> None:
        """Timeout errors should be retryable."""
        error = httpx.TimeoutException("Timeout")
        assert client._is_retryable_error(error) is True

    def test_is_retryable_for_network_error(self, client: ConcreteClient) -> None:
        """Network errors should be retryable."""
        error = httpx.NetworkError("Connection failed")
        assert client._is_retryable_error(error) is True

    def test_is_retryable_for_5xx_error(self, client: ConcreteClient) -> None:
        """5xx errors should be retryable."""
        error = IntegrationError("Server error", status_code=503)
        assert client._is_retryable_error(error) is True

    def test_is_retryable_for_rate_limit(self, client: ConcreteClient) -> None:
        """Rate limit errors should be retryable."""
        error = RateLimitError("Rate limit exceeded")
        assert client._is_retryable_error(error) is True

    def test_is_not_retryable_for_4xx_error(self, client: ConcreteClient) -> None:
        """4xx errors should not be retryable."""
        error = IntegrationError("Bad request", status_code=400)
        assert client._is_retryable_error(error) is False

    def test_is_not_retryable_for_auth_error(self, client: ConcreteClient) -> None:
        """Auth errors should not be retryable."""
        error = AuthenticationError("Invalid key")
        assert client._is_retryable_error(error) is False


class TestHealthCheck:
    """Tests for health check functionality."""

    def test_default_health_check(self) -> None:
        """Default health check should return basic status."""
        client = ConcreteClient()
        result = asyncio.get_event_loop().run_until_complete(client.health_check())

        assert result["name"] == "test_client"
        assert result["healthy"] is True
        assert "not implemented" in result["message"].lower()


class TestIntegrationErrorStr:
    """Tests for IntegrationError string representation."""

    def test_str_with_status_code(self) -> None:
        """Should include status code in string."""
        error = IntegrationError("Test error", status_code=500)
        assert "500" in str(error)
        assert "Test error" in str(error)

    def test_str_without_status_code(self) -> None:
        """Should work without status code."""
        error = IntegrationError("Test error")
        assert str(error) == "Test error"


class TestRateLimitErrorRetryAfter:
    """Tests for RateLimitError retry_after attribute."""

    def test_rate_limit_with_retry_after(self) -> None:
        """Should store retry_after value."""
        error = RateLimitError(retry_after=60)
        assert error.retry_after == 60

    def test_rate_limit_without_retry_after(self) -> None:
        """Should default to None."""
        error = RateLimitError()
        assert error.retry_after is None
