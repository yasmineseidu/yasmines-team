"""
Unit tests for Findymail integration client.

Tests cover:
- Client initialization and configuration
- HTTP headers and authentication
- Email finding from name and domain
- Email finding from LinkedIn URL
- Phone finding from LinkedIn URL
- Email verification
- Error handling and edge cases
- Response parsing
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations import (
    FindymailClient,
    FindymailEmailResult,
    FindymailEmailStatus,
    FindymailError,
    FindymailPhoneResult,
    FindymailVerificationResult,
)


class TestFindymailClientInitialization:
    """Tests for FindymailClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct Findymail API URL."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://app.findymail.com/api"

    def test_client_default_timeout(self) -> None:
        """Client should have 60s default timeout."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = FindymailClient(
            api_key="test-key",  # pragma: allowlist secret
            timeout=120.0,
        )
        assert client.timeout == 120.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 default max retries."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = FindymailClient(
            api_key="test-key",  # pragma: allowlist secret
            max_retries=5,
        )
        assert client.max_retries == 5

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "findymail"


class TestFindymailClientHeaders:
    """Tests for HTTP headers configuration."""

    def test_headers_include_bearer_token(self) -> None:
        """Headers should include Bearer token authorization."""
        client = FindymailClient(api_key="my-api-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer my-api-key"  # pragma: allowlist secret

    def test_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include JSON accept header."""
        client = FindymailClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestFindWorkEmail:
    """Tests for find_work_email method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_email_success(self, client: FindymailClient) -> None:
        """Should find email with name and domain."""
        mock_response = {
            "email": "jane.smith@techcompany.com",
            "status": "verified",
            "first_name": "Jane",
            "last_name": "Smith",
            "domain": "techcompany.com",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_work_email(
                full_name="Jane Smith",
                domain="techcompany.com",
            )

            assert isinstance(result, FindymailEmailResult)
            assert result.email == "jane.smith@techcompany.com"
            assert result.status == FindymailEmailStatus.VERIFIED
            assert result.is_valid is True
            assert result.is_usable is True

            mock_request.assert_called_once_with(
                method="POST",
                endpoint="/search/name",
                json={"name": "Jane Smith", "domain": "techcompany.com"},
                headers=client._get_headers(),
            )

    @pytest.mark.asyncio
    async def test_find_email_not_found(self, client: FindymailClient) -> None:
        """Should handle email not found."""
        mock_response = {
            "email": None,
            "status": "not_found",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_work_email(
                full_name="Unknown Person",
                domain="nonexistent.com",
            )

            assert result.email is None
            assert result.status == FindymailEmailStatus.NOT_FOUND
            assert result.is_valid is False
            assert result.is_usable is False

    @pytest.mark.asyncio
    async def test_find_email_catch_all(self, client: FindymailClient) -> None:
        """Should handle catch-all email."""
        mock_response = {
            "email": "contact@catchall.com",
            "status": "catch_all",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_work_email(
                full_name="Test User",
                domain="catchall.com",
            )

            assert result.email == "contact@catchall.com"
            assert result.status == FindymailEmailStatus.CATCH_ALL
            assert result.is_valid is False
            assert result.is_usable is True

    @pytest.mark.asyncio
    async def test_find_email_strips_whitespace(self, client: FindymailClient) -> None:
        """Should strip whitespace from inputs."""
        mock_response = {"email": "test@domain.com", "status": "valid"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.find_work_email(
                full_name="  Jane Smith  ",
                domain="  DOMAIN.COM  ",
            )

            call_args = mock_request.call_args
            assert call_args[1]["json"]["name"] == "Jane Smith"
            assert call_args[1]["json"]["domain"] == "domain.com"

    @pytest.mark.asyncio
    async def test_find_email_requires_full_name(self, client: FindymailClient) -> None:
        """Should require full_name parameter."""
        with pytest.raises(ValueError, match="full_name is required"):
            await client.find_work_email(full_name="", domain="example.com")

    @pytest.mark.asyncio
    async def test_find_email_requires_domain(self, client: FindymailClient) -> None:
        """Should require domain parameter."""
        with pytest.raises(ValueError, match="domain is required"):
            await client.find_work_email(full_name="Jane Smith", domain="")


class TestFindEmailByDomain:
    """Tests for find_email_by_domain method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_by_domain_success(self, client: FindymailClient) -> None:
        """Should find email using domain endpoint."""
        mock_response = {
            "email": "john@startup.io",
            "status": "valid",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_email_by_domain(
                name="John Doe",
                domain="startup.io",
            )

            assert result.email == "john@startup.io"
            assert result.status == FindymailEmailStatus.VALID
            mock_request.assert_called_once_with(
                method="POST",
                endpoint="/search/domain",
                json={"name": "John Doe", "domain": "startup.io"},
                headers=client._get_headers(),
            )

    @pytest.mark.asyncio
    async def test_find_by_domain_requires_name(self, client: FindymailClient) -> None:
        """Should require name parameter."""
        with pytest.raises(ValueError, match="name is required"):
            await client.find_email_by_domain(name="", domain="example.com")

    @pytest.mark.asyncio
    async def test_find_by_domain_requires_domain(self, client: FindymailClient) -> None:
        """Should require domain parameter."""
        with pytest.raises(ValueError, match="domain is required"):
            await client.find_email_by_domain(name="John", domain="")


class TestFindEmailFromLinkedIn:
    """Tests for find_email_from_linkedin method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_from_linkedin_success(self, client: FindymailClient) -> None:
        """Should find email from LinkedIn URL."""
        mock_response = {
            "email": "sarah@company.com",
            "status": "verified",
            "first_name": "Sarah",
            "last_name": "Jones",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_email_from_linkedin(
                linkedin_url="https://linkedin.com/in/sarahjones"
            )

            assert result.email == "sarah@company.com"
            assert result.status == FindymailEmailStatus.VERIFIED
            mock_request.assert_called_once_with(
                method="POST",
                endpoint="/search/linkedin",
                json={"linkedin_url": "https://linkedin.com/in/sarahjones"},
                headers=client._get_headers(),
            )

    @pytest.mark.asyncio
    async def test_find_from_linkedin_requires_url(self, client: FindymailClient) -> None:
        """Should require linkedin_url parameter."""
        with pytest.raises(ValueError, match="linkedin_url is required"):
            await client.find_email_from_linkedin(linkedin_url="")

    @pytest.mark.asyncio
    async def test_find_from_linkedin_validates_url(self, client: FindymailClient) -> None:
        """Should validate LinkedIn URL format."""
        with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
            await client.find_email_from_linkedin(linkedin_url="https://facebook.com/profile")

    @pytest.mark.asyncio
    async def test_find_from_linkedin_strips_whitespace(self, client: FindymailClient) -> None:
        """Should strip whitespace from URL."""
        mock_response = {"email": "test@test.com", "status": "valid"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.find_email_from_linkedin(linkedin_url="  https://linkedin.com/in/user  ")

            call_args = mock_request.call_args
            assert call_args[1]["json"]["linkedin_url"] == "https://linkedin.com/in/user"


class TestFindPhoneFromLinkedIn:
    """Tests for find_phone_from_linkedin method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_phone_success(self, client: FindymailClient) -> None:
        """Should find phone from LinkedIn URL."""
        mock_response = {
            "phone": "+1-555-123-4567",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_phone_from_linkedin(
                linkedin_url="https://linkedin.com/in/johndoe"
            )

            assert isinstance(result, FindymailPhoneResult)
            assert result.phone == "+1-555-123-4567"
            assert result.found is True
            assert result.linkedin_url == "https://linkedin.com/in/johndoe"

    @pytest.mark.asyncio
    async def test_find_phone_not_found(self, client: FindymailClient) -> None:
        """Should handle phone not found."""
        mock_response = {
            "phone": None,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.find_phone_from_linkedin(
                linkedin_url="https://linkedin.com/in/private"
            )

            assert result.phone is None
            assert result.found is False

    @pytest.mark.asyncio
    async def test_find_phone_requires_url(self, client: FindymailClient) -> None:
        """Should require linkedin_url parameter."""
        with pytest.raises(ValueError, match="linkedin_url is required"):
            await client.find_phone_from_linkedin(linkedin_url="")

    @pytest.mark.asyncio
    async def test_find_phone_validates_url(self, client: FindymailClient) -> None:
        """Should validate LinkedIn URL format."""
        with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
            await client.find_phone_from_linkedin(linkedin_url="https://twitter.com/user")


class TestVerifyEmail:
    """Tests for verify_email method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_success(self, client: FindymailClient) -> None:
        """Should verify email successfully."""
        mock_response = {
            "status": "verified",
            "deliverable": True,
            "catch_all": False,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.verify_email("test@example.com")

            assert isinstance(result, FindymailVerificationResult)
            assert result.email == "test@example.com"
            assert result.status == FindymailEmailStatus.VERIFIED
            assert result.is_deliverable is True
            assert result.is_catch_all is False
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid(self, client: FindymailClient) -> None:
        """Should handle invalid email."""
        mock_response = {
            "status": "invalid",
            "deliverable": False,
            "catch_all": False,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.verify_email("invalid@nonexistent.com")

            assert result.status == FindymailEmailStatus.INVALID
            assert result.is_deliverable is False
            assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_verify_email_catch_all(self, client: FindymailClient) -> None:
        """Should handle catch-all domain."""
        mock_response = {
            "status": "catch_all",
            "deliverable": True,
            "catch_all": True,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.verify_email("anyone@catchall.com")

            assert result.status == FindymailEmailStatus.CATCH_ALL
            assert result.is_catch_all is True

    @pytest.mark.asyncio
    async def test_verify_email_requires_email(self, client: FindymailClient) -> None:
        """Should require email parameter."""
        with pytest.raises(ValueError, match="email is required"):
            await client.verify_email("")

    @pytest.mark.asyncio
    async def test_verify_email_validates_format(self, client: FindymailClient) -> None:
        """Should validate email format."""
        with pytest.raises(ValueError, match="Invalid email format"):
            await client.verify_email("not-an-email")

    @pytest.mark.asyncio
    async def test_verify_email_normalizes(self, client: FindymailClient) -> None:
        """Should normalize email to lowercase."""
        mock_response = {"status": "valid", "deliverable": True, "catch_all": False}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.verify_email("  TEST@EXAMPLE.COM  ")

            assert result.email == "test@example.com"
            call_args = mock_request.call_args
            assert call_args[1]["json"]["email"] == "test@example.com"


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, client: FindymailClient) -> None:
        """Should return health status."""
        health = await client.health_check()

        assert health["name"] == "findymail"
        assert health["healthy"] is True
        assert health["base_url"] == "https://app.findymail.com/api"


class TestCallEndpoint:
    """Tests for call_endpoint method."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_with_get(self, client: FindymailClient) -> None:
        """Should call endpoint with GET method."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint("/test", method="GET")

            assert result == mock_response
            mock_request.assert_called_once()
            assert mock_request.call_args[1]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_call_endpoint_with_post(self, client: FindymailClient) -> None:
        """Should call endpoint with POST method and JSON body."""
        mock_response = {"result": "success"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint(
                "/test",
                method="POST",
                json={"key": "value"},
            )

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[1]["json"] == {"key": "value"}


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> FindymailClient:
        """Create client for testing."""
        return FindymailClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_email_raises_findymail_error(self, client: FindymailClient) -> None:
        """Should raise FindymailError on API failure."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = IntegrationError(
                message="API error",
                status_code=500,
            )

            with pytest.raises(FindymailError) as exc_info:
                await client.find_work_email(
                    full_name="Test User",
                    domain="test.com",
                )

            assert "Failed to find email" in str(exc_info.value)
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_verify_email_raises_findymail_error(self, client: FindymailClient) -> None:
        """Should raise FindymailError on verification failure."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = IntegrationError(
                message="Rate limited",
                status_code=429,
            )

            with pytest.raises(FindymailError) as exc_info:
                await client.verify_email("test@example.com")

            assert "Failed to verify email" in str(exc_info.value)
            assert exc_info.value.status_code == 429


class TestEmailResultProperties:
    """Tests for FindymailEmailResult properties."""

    def test_verified_email_is_valid(self) -> None:
        """Verified email should be valid."""
        result = FindymailEmailResult(
            email="test@test.com",
            status=FindymailEmailStatus.VERIFIED,
            first_name=None,
            last_name=None,
            domain=None,
            raw_response={},
        )
        assert result.is_valid is True
        assert result.is_usable is True

    def test_valid_email_is_valid(self) -> None:
        """Valid email should be valid."""
        result = FindymailEmailResult(
            email="test@test.com",
            status=FindymailEmailStatus.VALID,
            first_name=None,
            last_name=None,
            domain=None,
            raw_response={},
        )
        assert result.is_valid is True
        assert result.is_usable is True

    def test_catch_all_email_is_usable(self) -> None:
        """Catch-all email should be usable but not valid."""
        result = FindymailEmailResult(
            email="test@test.com",
            status=FindymailEmailStatus.CATCH_ALL,
            first_name=None,
            last_name=None,
            domain=None,
            raw_response={},
        )
        assert result.is_valid is False
        assert result.is_usable is True

    def test_invalid_email_not_usable(self) -> None:
        """Invalid email should not be usable."""
        result = FindymailEmailResult(
            email="bad@test.com",
            status=FindymailEmailStatus.INVALID,
            first_name=None,
            last_name=None,
            domain=None,
            raw_response={},
        )
        assert result.is_valid is False
        assert result.is_usable is False

    def test_not_found_not_usable(self) -> None:
        """Not found should not be usable."""
        result = FindymailEmailResult(
            email=None,
            status=FindymailEmailStatus.NOT_FOUND,
            first_name=None,
            last_name=None,
            domain=None,
            raw_response={},
        )
        assert result.is_valid is False
        assert result.is_usable is False


class TestVerificationResultProperties:
    """Tests for FindymailVerificationResult properties."""

    def test_verified_deliverable_is_valid(self) -> None:
        """Verified and deliverable should be valid."""
        result = FindymailVerificationResult(
            email="test@test.com",
            status=FindymailEmailStatus.VERIFIED,
            is_deliverable=True,
            is_catch_all=False,
            raw_response={},
        )
        assert result.is_valid is True

    def test_verified_not_deliverable_not_valid(self) -> None:
        """Verified but not deliverable should not be valid."""
        result = FindymailVerificationResult(
            email="test@test.com",
            status=FindymailEmailStatus.VERIFIED,
            is_deliverable=False,
            is_catch_all=False,
            raw_response={},
        )
        assert result.is_valid is False

    def test_invalid_not_valid(self) -> None:
        """Invalid status should not be valid."""
        result = FindymailVerificationResult(
            email="test@test.com",
            status=FindymailEmailStatus.INVALID,
            is_deliverable=False,
            is_catch_all=False,
            raw_response={},
        )
        assert result.is_valid is False


class TestPhoneResultProperties:
    """Tests for FindymailPhoneResult properties."""

    def test_phone_found(self) -> None:
        """Should report found when phone exists."""
        result = FindymailPhoneResult(
            phone="+1-555-123-4567",
            linkedin_url="https://linkedin.com/in/user",
            raw_response={},
        )
        assert result.found is True

    def test_phone_not_found(self) -> None:
        """Should report not found when phone is None."""
        result = FindymailPhoneResult(
            phone=None,
            linkedin_url="https://linkedin.com/in/user",
            raw_response={},
        )
        assert result.found is False


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close client on exit."""
        async with FindymailClient(
            api_key="test-key"  # pragma: allowlist secret
        ) as client:
            # Force client creation
            _ = client.client
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None
