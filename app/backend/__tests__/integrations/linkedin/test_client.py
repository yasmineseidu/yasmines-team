"""Unit tests for LinkedIn client initialization and authentication."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.linkedin import (
    LinkedInAuthError,
    LinkedInClient,
)

# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestClientInitialization:
    """Tests for client initialization."""

    def test_client_initializes_with_credentials_dict(self, valid_credentials: dict) -> None:
        """Client should initialize successfully with credentials dict."""
        client = LinkedInClient(credentials_json=valid_credentials)
        assert client.name == "linkedin"
        assert client.access_token == "test_access_token_xyz"
        assert client.client_id == "test_client_id"
        assert client.base_url == "https://api.linkedin.com/v2"

    def test_client_initializes_with_credentials_string(self, valid_credentials: dict) -> None:
        """Client should initialize with credentials as JSON string."""
        creds_str = json.dumps(valid_credentials)
        client = LinkedInClient(credentials_json=creds_str)
        assert client.access_token == "test_access_token_xyz"

    def test_client_initializes_with_direct_token(self, valid_access_token: str) -> None:
        """Client should initialize with direct access token."""
        client = LinkedInClient(access_token=valid_access_token)
        assert client.access_token == valid_access_token
        assert client.name == "linkedin"

    def test_client_initializes_without_credentials(self) -> None:
        """Client should initialize even without credentials (will fail on auth)."""
        client = LinkedInClient()
        assert client.access_token == ""

    def test_client_raises_error_with_invalid_json_string(self) -> None:
        """Client should raise error if credentials JSON is malformed."""
        with pytest.raises(LinkedInAuthError, match="Invalid credentials JSON"):
            LinkedInClient(credentials_json="not valid json")

    def test_client_sets_timeout_and_retries(self, valid_credentials: dict) -> None:
        """Client should respect timeout and retry settings."""
        client = LinkedInClient(
            credentials_json=valid_credentials,
            timeout=60.0,
            max_retries=5,
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================


class TestAuthentication:
    """Tests for OAuth2 authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, client: LinkedInClient) -> None:
        """Authenticate should set member_id on success."""
        from __tests__.integrations.linkedin.conftest import MOCK_PROFILE_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_PROFILE_RESPONSE

            await client.authenticate()

            assert client.member_id == "user123"
            mock_get.assert_called_once_with("/userinfo")

    @pytest.mark.asyncio
    async def test_authenticate_fails_without_token(self) -> None:
        """Authenticate should raise error if no access token."""
        client = LinkedInClient()

        with pytest.raises(LinkedInAuthError, match="No access token provided"):
            await client.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_propagates_auth_error(self, client: LinkedInClient) -> None:
        """Authenticate should propagate auth errors from API."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = LinkedInAuthError("Invalid token")

            with pytest.raises(LinkedInAuthError, match="Invalid token"):
                await client.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_wraps_generic_errors(self, client: LinkedInClient) -> None:
        """Authenticate should wrap generic errors in LinkedInAuthError."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")

            with pytest.raises(LinkedInAuthError, match="Failed to authenticate with LinkedIn"):
                await client.authenticate()


class TestTokenRefresh:
    """Tests for OAuth2 token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: LinkedInClient) -> None:
        """Refresh token should update access_token."""
        client.refresh_token = "test_refresh_token"

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
            mock_post.return_value = mock_response

            new_token = await client.refresh_access_token()

            assert new_token == "new_access_token"
            assert client.access_token == "new_access_token"
            assert client.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_fails_without_refresh_token(self, client: LinkedInClient) -> None:
        """Refresh should fail if no refresh token available."""
        client.refresh_token = ""

        with pytest.raises(LinkedInAuthError, match="No refresh token available"):
            await client.refresh_access_token()

    @pytest.mark.asyncio
    async def test_refresh_token_fails_without_client_credentials(
        self, valid_access_token: str
    ) -> None:
        """Refresh should fail if client credentials not set."""
        client = LinkedInClient(access_token=valid_access_token)
        client.refresh_token = "test_refresh_token"
        client.client_id = ""
        client.client_secret = ""

        with pytest.raises(
            LinkedInAuthError, match="Client credentials required for token refresh"
        ):
            await client.refresh_access_token()


# ============================================================================
# HEADER TESTS
# ============================================================================


class TestHeaders:
    """Tests for request headers."""

    def test_get_headers_includes_authorization(self, client: LinkedInClient) -> None:
        """Headers should include Bearer authorization."""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_access_token_xyz"

    def test_get_headers_includes_content_type(self, client: LinkedInClient) -> None:
        """Headers should include Content-Type."""
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_includes_linkedin_version(self, client: LinkedInClient) -> None:
        """Headers should include LinkedIn API version headers."""
        headers = client._get_headers()
        assert "X-Restli-Protocol-Version" in headers
        assert "LinkedIn-Version" in headers


# ============================================================================
# CONTEXT MANAGER TESTS
# ============================================================================


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self, valid_credentials: dict) -> None:
        """Context manager should close client on exit."""
        async with LinkedInClient(credentials_json=valid_credentials) as client:
            assert client is not None
            # Create the HTTP client
            _ = client.client

        # After exit, client should be closed
        assert client._client is None or client._client.is_closed

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, client: LinkedInClient) -> None:
        """Closing multiple times should not raise errors."""
        # Create HTTP client
        _ = client.client

        await client.close()
        await client.close()  # Should not raise


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: LinkedInClient) -> None:
        """Health check should return healthy status on success."""
        from __tests__.integrations.linkedin.conftest import MOCK_PROFILE_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_PROFILE_RESPONSE

            result = await client.health_check()

            assert result["name"] == "linkedin"
            assert result["healthy"] is True
            assert "authenticated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_no_token(self) -> None:
        """Health check should return unhealthy if no token configured."""
        client = LinkedInClient()

        result = await client.health_check()

        assert result["name"] == "linkedin"
        assert result["healthy"] is False
        assert "No access token" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_auth_failure(self, client: LinkedInClient) -> None:
        """Health check should return unhealthy on auth failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = LinkedInAuthError("Token expired")

            result = await client.health_check()

            assert result["healthy"] is False
            assert "Authentication failed" in result["message"]
