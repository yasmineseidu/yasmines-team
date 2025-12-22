"""Unit tests for LinkedIn error handling and resilience."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.linkedin import (
    LinkedInAuthError,
    LinkedInClient,
    LinkedInError,
    LinkedInForbiddenError,
    LinkedInNotFoundError,
    LinkedInRateLimitError,
    LinkedInValidationError,
)

# ============================================================================
# EXCEPTION TESTS
# ============================================================================


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_linkedin_error_is_integration_error(self) -> None:
        """LinkedInError should inherit from IntegrationError."""
        from src.integrations.base import IntegrationError

        error = LinkedInError("Test error")
        assert isinstance(error, IntegrationError)

    def test_linkedin_auth_error_has_401_status(self) -> None:
        """LinkedInAuthError should have status 401."""
        error = LinkedInAuthError("Auth failed")
        assert error.status_code == 401

    def test_linkedin_rate_limit_error_has_429_status(self) -> None:
        """LinkedInRateLimitError should have status 429."""
        error = LinkedInRateLimitError("Rate limited")
        assert error.status_code == 429

    def test_linkedin_rate_limit_error_stores_retry_after(self) -> None:
        """LinkedInRateLimitError should store retry_after value."""
        error = LinkedInRateLimitError("Rate limited", retry_after=60)
        assert error.retry_after == 60

    def test_linkedin_forbidden_error_has_403_status(self) -> None:
        """LinkedInForbiddenError should have status 403."""
        error = LinkedInForbiddenError("Access denied")
        assert error.status_code == 403

    def test_linkedin_not_found_error_has_404_status(self) -> None:
        """LinkedInNotFoundError should have status 404."""
        error = LinkedInNotFoundError("Not found")
        assert error.status_code == 404

    def test_linkedin_validation_error_has_400_status(self) -> None:
        """LinkedInValidationError should have status 400."""
        error = LinkedInValidationError("Invalid request")
        assert error.status_code == 400

    def test_exception_stores_response_data(self) -> None:
        """Exceptions should store response data."""
        error = LinkedInError(
            "Test error",
            status_code=500,
            response_data={"error": "details"},
        )
        assert error.response_data == {"error": "details"}

    def test_exception_str_includes_status_code(self) -> None:
        """Exception string should include status code."""
        error = LinkedInError("Test error", status_code=500)
        assert "500" in str(error)


# ============================================================================
# HTTP RESPONSE HANDLING
# ============================================================================


class TestResponseHandling:
    """Tests for HTTP response handling."""

    @pytest.mark.asyncio
    async def test_handles_401_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInAuthError for 401 responses."""
        response = MagicMock()
        response.status_code = 401
        response.text = '{"message": "Invalid token"}'
        response.json.return_value = {"message": "Invalid token"}

        with pytest.raises(LinkedInAuthError) as exc_info:
            await client._handle_response(response)

        assert "authentication failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_403_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInForbiddenError for 403 responses."""
        response = MagicMock()
        response.status_code = 403
        response.text = '{"message": "Access denied"}'
        response.json.return_value = {"message": "Access denied"}

        with pytest.raises(LinkedInForbiddenError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handles_404_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInNotFoundError for 404 responses."""
        response = MagicMock()
        response.status_code = 404
        response.text = '{"message": "Resource not found"}'
        response.json.return_value = {"message": "Resource not found"}

        with pytest.raises(LinkedInNotFoundError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handles_429_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInRateLimitError for 429 responses."""
        response = MagicMock()
        response.status_code = 429
        response.text = '{"message": "Rate limit exceeded"}'
        response.json.return_value = {"message": "Rate limit exceeded"}
        response.headers = {"Retry-After": "60"}

        with pytest.raises(LinkedInRateLimitError) as exc_info:
            await client._handle_response(response)

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_handles_429_without_retry_after(self, client: LinkedInClient) -> None:
        """Should handle 429 without Retry-After header."""
        response = MagicMock()
        response.status_code = 429
        response.text = "{}"
        response.json.return_value = {}
        response.headers = {}

        with pytest.raises(LinkedInRateLimitError) as exc_info:
            await client._handle_response(response)

        assert exc_info.value.retry_after is None

    @pytest.mark.asyncio
    async def test_handles_400_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInValidationError for 400 responses."""
        response = MagicMock()
        response.status_code = 400
        response.text = '{"message": "Invalid request"}'
        response.json.return_value = {"message": "Invalid request"}

        with pytest.raises(LinkedInValidationError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handles_500_response(self, client: LinkedInClient) -> None:
        """Should raise LinkedInError for 500 responses."""
        response = MagicMock()
        response.status_code = 500
        response.text = '{"message": "Internal server error"}'
        response.json.return_value = {"message": "Internal server error"}

        with pytest.raises(LinkedInError) as exc_info:
            await client._handle_response(response)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_handles_empty_response_body(self, client: LinkedInClient) -> None:
        """Should handle responses with empty body."""
        response = MagicMock()
        response.status_code = 200
        response.text = ""
        response.json.return_value = {}

        result = await client._handle_response(response)
        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self, client: LinkedInClient) -> None:
        """Should handle responses with invalid JSON."""
        response = MagicMock()
        response.status_code = 500
        response.text = "Not JSON"
        response.json.side_effect = Exception("JSON decode error")

        with pytest.raises(LinkedInError):
            await client._handle_response(response)


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================


class TestRetryLogic:
    """Tests for retry logic and resilience."""

    @pytest.mark.asyncio
    async def test_retries_on_5xx_errors(self, client: LinkedInClient) -> None:
        """Should retry on server errors."""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = MagicMock()
                response.status_code = 500
                response.text = '{"message": "Server error"}'
                response.json.return_value = {"message": "Server error"}
                return response
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"success": True}
            return response

        with patch.object(
            client.client, "request", new_callable=AsyncMock, side_effect=mock_request
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get("/test")

        assert result == {"success": True}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self, client: LinkedInClient) -> None:
        """Should retry on rate limit errors."""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = MagicMock()
                response.status_code = 429
                response.text = "{}"
                response.json.return_value = {}
                response.headers = {"Retry-After": "1"}
                return response
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"success": True}
            return response

        with patch.object(
            client.client, "request", new_callable=AsyncMock, side_effect=mock_request
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get("/test")

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, client: LinkedInClient) -> None:
        """Should retry on timeout errors."""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Connection timed out")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"success": True}
            return response

        with patch.object(
            client.client, "request", new_callable=AsyncMock, side_effect=mock_request
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get("/test")

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_retries_on_network_error(self, client: LinkedInClient) -> None:
        """Should retry on network errors."""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.NetworkError("Connection failed")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"success": True}
            return response

        with patch.object(
            client.client, "request", new_callable=AsyncMock, side_effect=mock_request
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get("/test")

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_does_not_retry_on_4xx_errors(self, client: LinkedInClient) -> None:
        """Should not retry on client errors (except 429)."""
        response = MagicMock()
        response.status_code = 400
        response.text = '{"message": "Bad request"}'
        response.json.return_value = {"message": "Bad request"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with pytest.raises(LinkedInValidationError):
                await client.get("/test")

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_fails(self, client: LinkedInClient) -> None:
        """Should fail after exhausting retries."""
        response = MagicMock()
        response.status_code = 500
        response.text = '{"message": "Server error"}'
        response.json.return_value = {"message": "Server error"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LinkedInError):
                    await client.get("/test")


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_recovers_from_transient_auth_error(self, client: LinkedInClient) -> None:
        """Client should be usable after recovering from auth error."""
        from __tests__.integrations.linkedin.conftest import MOCK_PROFILE_RESPONSE

        call_count = 0

        async def mock_get(endpoint):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LinkedInAuthError("Token expired")
            return MOCK_PROFILE_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock, side_effect=mock_get):
            # First call fails
            with pytest.raises(LinkedInAuthError):
                await client.get_my_profile()

            # Client can still make subsequent calls
            profile = await client.get_my_profile()
            assert profile.first_name == "Test"

    @pytest.mark.asyncio
    async def test_error_logging(self, client: LinkedInClient) -> None:
        """Should log errors appropriately."""
        import logging

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            response = MagicMock()
            response.status_code = 500
            response.text = '{"message": "Server error"}'
            response.json.return_value = {"message": "Server error"}
            mock_request.return_value = response

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch.object(logging.getLogger("src.integrations.base"), "error") as mock_log:
                    with pytest.raises(LinkedInError):
                        await client.get("/test")

                    # Should have logged the error
                    assert mock_log.called


# ============================================================================
# SPECIFIC ERROR SCENARIO TESTS
# ============================================================================


class TestSpecificErrorScenarios:
    """Tests for specific LinkedIn API error scenarios."""

    @pytest.mark.asyncio
    async def test_handles_oauth_scope_error(self, client: LinkedInClient) -> None:
        """Should handle OAuth scope permission errors."""
        response = MagicMock()
        response.status_code = 403
        response.text = '{"message": "Not enough permissions to access"}'
        response.json.return_value = {"message": "Not enough permissions to access: Member Profile"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with pytest.raises(LinkedInForbiddenError) as exc_info:
                await client.get("/userinfo")

            assert "forbidden" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_expired_token(self, client: LinkedInClient) -> None:
        """Should handle expired access token."""
        response = MagicMock()
        response.status_code = 401
        response.text = '{"message": "Access token has expired"}'
        response.json.return_value = {"message": "Access token has expired"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with pytest.raises(LinkedInAuthError):
                await client.get("/userinfo")

    @pytest.mark.asyncio
    async def test_handles_deleted_resource(self, client: LinkedInClient) -> None:
        """Should handle accessing deleted resources."""
        response = MagicMock()
        response.status_code = 404
        response.text = '{"message": "Resource has been deleted"}'
        response.json.return_value = {"message": "Resource has been deleted"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with pytest.raises(LinkedInNotFoundError):
                await client.get("/posts/deleted123")

    @pytest.mark.asyncio
    async def test_handles_connection_limit(self, client: LinkedInClient) -> None:
        """Should handle connection request limits."""
        response = MagicMock()
        response.status_code = 400
        response.text = '{"message": "Weekly invitation limit reached"}'
        response.json.return_value = {"message": "Weekly invitation limit reached"}

        with patch.object(client.client, "request", new_callable=AsyncMock, return_value=response):
            with pytest.raises(LinkedInValidationError):
                await client.post("/invitations", json={})
