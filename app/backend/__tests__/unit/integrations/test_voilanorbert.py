"""Unit tests for VoilaNorbert integration client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.integrations.base import AuthenticationError, PaymentRequiredError, RateLimitError
from src.integrations.voilanorbert import (
    VoilaNorbertAccountInfo,
    VoilaNorbertClient,
    VoilaNorbertEmailResult,
    VoilaNorbertEmailStatus,
    VoilaNorbertVerificationResult,
)


class TestVoilaNorbertClientInitialization:
    """Tests for VoilaNorbertClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct VoilaNorbert API base URL."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.voilanorbert.com/2018-01-08"

    def test_client_default_timeout(self) -> None:
        """Client should have default timeout of 60 seconds."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = VoilaNorbertClient(api_key="test-key", timeout=120.0)  # pragma: allowlist secret
        assert client.timeout == 120.0

    def test_client_default_max_retries(self) -> None:
        """Client should have default max retries of 3."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = VoilaNorbertClient(api_key="test-key", max_retries=5)  # pragma: allowlist secret
        assert client.max_retries == 5

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "voilanorbert"


class TestVoilaNorbertClientHeaders:
    """Tests for VoilaNorbertClient headers."""

    def test_headers_include_content_type(self) -> None:
        """Headers should include correct Content-Type."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"

    def test_get_auth_returns_basic_auth(self) -> None:
        """Auth should be HTTP Basic Auth."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret
        auth = client._get_auth()
        assert isinstance(auth, httpx.BasicAuth)


class TestFindEmail:
    """Tests for VoilaNorbertClient.find_email()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_email_success(self, client: VoilaNorbertClient) -> None:
        """find_email should return result on success."""
        mock_response = {
            "email": {"email": "john@company.com", "score": 100},
            "first_name": "John",
            "last_name": "Smith",
            "company": "Company Inc",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_email(full_name="John Smith", domain="company.com")

            assert result.email == "john@company.com"
            assert result.score == 100
            assert result.found is True
            assert result.is_verified is True

    @pytest.mark.asyncio
    async def test_find_email_not_found(self, client: VoilaNorbertClient) -> None:
        """find_email should return NOT_FOUND status when email not found."""
        mock_response = {"email": None, "searching": False}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_email(full_name="Unknown Person", domain="unknown.com")

            assert result.email is None
            assert result.status == VoilaNorbertEmailStatus.NOT_FOUND
            assert result.found is False

    @pytest.mark.asyncio
    async def test_find_email_with_company(self, client: VoilaNorbertClient) -> None:
        """find_email should work with company name instead of domain."""
        mock_response = {
            "email": {"email": "john@company.com", "score": 80},
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_email(full_name="John Smith", company="Company Inc")

            assert result.email == "john@company.com"
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert "company" in call_kwargs["data"]

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_name(self, client: VoilaNorbertClient) -> None:
        """find_email should raise ValueError if name is missing."""
        with pytest.raises(ValueError, match="full_name is required"):
            await client.find_email(full_name="", domain="company.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_domain_and_company(
        self, client: VoilaNorbertClient
    ) -> None:
        """find_email should raise ValueError if both domain and company are missing."""
        with pytest.raises(ValueError, match="Either domain or company is required"):
            await client.find_email(full_name="John Smith")


class TestSearchDomain:
    """Tests for VoilaNorbertClient.search_domain()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_domain_success(self, client: VoilaNorbertClient) -> None:
        """search_domain should return list of results."""
        mock_response = {
            "contacts": [
                {"email": {"email": "john@company.com", "score": 100}},
                {"email": {"email": "jane@company.com", "score": 80}},
            ]
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search_domain("company.com")

            assert len(results) == 2
            assert results[0].email == "john@company.com"
            assert results[1].email == "jane@company.com"

    @pytest.mark.asyncio
    async def test_search_domain_empty_result(self, client: VoilaNorbertClient) -> None:
        """search_domain should return empty list if no contacts found."""
        mock_response = {"contacts": []}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search_domain("empty.com")

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_domain_raises_on_empty_domain(self, client: VoilaNorbertClient) -> None:
        """search_domain should raise ValueError if domain is empty."""
        with pytest.raises(ValueError, match="domain is required"):
            await client.search_domain("")


class TestVerifyEmail:
    """Tests for VoilaNorbertClient.verify_email()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_valid(self, client: VoilaNorbertClient) -> None:
        """verify_email should return valid result."""
        upload_response = {"token": "verify-token-123"}
        status_response = {
            "result": {
                "valid": True,
                "deliverable": True,
                "catch_all": False,
                "status": "valid",
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [upload_response, status_response]
            result = await client.verify_email("john@company.com")

            assert result.is_valid is True
            assert result.is_deliverable is True
            assert result.is_catch_all is False

    @pytest.mark.asyncio
    async def test_verify_email_raises_on_invalid_format(self, client: VoilaNorbertClient) -> None:
        """verify_email should raise ValueError for invalid email format."""
        with pytest.raises(ValueError, match="Invalid email format"):
            await client.verify_email("invalid-email")


class TestGetAccountInfo:
    """Tests for VoilaNorbertClient.get_account_info()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, client: VoilaNorbertClient) -> None:
        """get_account_info should return account details."""
        mock_response = {
            "email": "user@example.com",
            "credits": 1000,
            "plan": {"name": "Pro"},
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_account_info()

            assert result.email == "user@example.com"
            assert result.credits_remaining == 1000
            assert result.plan_name == "Pro"
            assert result.has_credits is True


class TestHealthCheck:
    """Tests for VoilaNorbertClient.health_check()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: VoilaNorbertClient) -> None:
        """health_check should return healthy status on success."""
        mock_account = VoilaNorbertAccountInfo(
            email="test@example.com",
            credits_remaining=100,
            plan_name="Pro",
            raw_response={},
        )

        with patch.object(client, "get_account_info", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            result = await client.health_check()

            assert result["healthy"] is True
            assert result["credits_remaining"] == 100

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: VoilaNorbertClient) -> None:
        """health_check should return unhealthy status on failure."""
        with patch.object(client, "get_account_info", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            result = await client.health_check()

            assert result["healthy"] is False
            assert "error" in result


class TestErrorHandling:
    """Tests for VoilaNorbertClient error handling."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error_is_raised(self, client: VoilaNorbertClient) -> None:
        """Client should raise AuthenticationError on 401."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = AuthenticationError(message="Invalid API key")

            with pytest.raises(AuthenticationError):
                await client.find_email(full_name="John Smith", domain="company.com")

    @pytest.mark.asyncio
    async def test_payment_required_error_is_raised(self, client: VoilaNorbertClient) -> None:
        """Client should raise PaymentRequiredError on 402."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = PaymentRequiredError(message="Insufficient credits")

            with pytest.raises(PaymentRequiredError):
                await client.find_email(full_name="John Smith", domain="company.com")

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_raised(self, client: VoilaNorbertClient) -> None:
        """Client should raise RateLimitError on 429."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RateLimitError(
                message="Rate limit exceeded",
                status_code=429,
                retry_after=60,
            )

            with pytest.raises(RateLimitError):
                await client.find_email(full_name="John Smith", domain="company.com")


class TestCallEndpoint:
    """Tests for VoilaNorbertClient.call_endpoint()."""

    @pytest.fixture
    def client(self) -> VoilaNorbertClient:
        """Create client fixture."""
        return VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: VoilaNorbertClient) -> None:
        """call_endpoint should return response for valid endpoint."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.call_endpoint("/custom/endpoint", method="POST")

            assert result == mock_response


class TestEmailResultProperties:
    """Tests for VoilaNorbertEmailResult properties."""

    def test_found_true_when_email_exists(self) -> None:
        """found should be True when email exists and status is FOUND."""
        result = VoilaNorbertEmailResult(
            email="test@example.com",
            status=VoilaNorbertEmailStatus.FOUND,
            score=100,
            first_name="Test",
            last_name="User",
            company="Test Inc",
            raw_response={},
        )
        assert result.found is True

    def test_found_false_when_email_missing(self) -> None:
        """found should be False when email is None."""
        result = VoilaNorbertEmailResult(
            email=None,
            status=VoilaNorbertEmailStatus.NOT_FOUND,
            score=0,
            first_name="Test",
            last_name="User",
            company="Test Inc",
            raw_response={},
        )
        assert result.found is False

    def test_is_high_confidence_true(self) -> None:
        """is_high_confidence should be True when score >= 80."""
        result = VoilaNorbertEmailResult(
            email="test@example.com",
            status=VoilaNorbertEmailStatus.FOUND,
            score=80,
            first_name=None,
            last_name=None,
            company=None,
            raw_response={},
        )
        assert result.is_high_confidence is True

    def test_is_high_confidence_false(self) -> None:
        """is_high_confidence should be False when score < 80."""
        result = VoilaNorbertEmailResult(
            email="test@example.com",
            status=VoilaNorbertEmailStatus.FOUND,
            score=50,
            first_name=None,
            last_name=None,
            company=None,
            raw_response={},
        )
        assert result.is_high_confidence is False

    def test_is_verified_true(self) -> None:
        """is_verified should be True when score == 100."""
        result = VoilaNorbertEmailResult(
            email="test@example.com",
            status=VoilaNorbertEmailStatus.FOUND,
            score=100,
            first_name=None,
            last_name=None,
            company=None,
            raw_response={},
        )
        assert result.is_verified is True


class TestVerificationResultProperties:
    """Tests for VoilaNorbertVerificationResult properties."""

    def test_is_safe_to_send_true(self) -> None:
        """is_safe_to_send should be True when valid, deliverable, and not catch-all."""
        result = VoilaNorbertVerificationResult(
            email="test@example.com",
            is_valid=True,
            is_deliverable=True,
            is_catch_all=False,
            status="valid",
            raw_response={},
        )
        assert result.is_safe_to_send is True

    def test_is_safe_to_send_false_catch_all(self) -> None:
        """is_safe_to_send should be False when catch-all."""
        result = VoilaNorbertVerificationResult(
            email="test@example.com",
            is_valid=True,
            is_deliverable=True,
            is_catch_all=True,
            status="catch_all",
            raw_response={},
        )
        assert result.is_safe_to_send is False


class TestAccountInfoProperties:
    """Tests for VoilaNorbertAccountInfo properties."""

    def test_has_credits_true(self) -> None:
        """has_credits should be True when credits > 0."""
        info = VoilaNorbertAccountInfo(
            email="test@example.com",
            credits_remaining=100,
            plan_name="Pro",
            raw_response={},
        )
        assert info.has_credits is True

    def test_has_credits_false(self) -> None:
        """has_credits should be False when credits == 0."""
        info = VoilaNorbertAccountInfo(
            email="test@example.com",
            credits_remaining=0,
            plan_name="Free",
            raw_response={},
        )
        assert info.has_credits is False


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        client = VoilaNorbertClient(api_key="test-key")  # pragma: allowlist secret

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass
            mock_close.assert_called_once()
