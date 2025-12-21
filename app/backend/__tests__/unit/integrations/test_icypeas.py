"""Unit tests for Icypeas integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.icypeas import (
    IcypeasClient,
    IcypeasCreditsInfo,
    IcypeasEmailResult,
    IcypeasSearchStatus,
)


class TestIcypeasClientInitialization:
    """Tests for IcypeasClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct Icypeas API base URL."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://app.icypeas.com/api"

    def test_client_default_timeout(self) -> None:
        """Client should have default timeout of 60 seconds."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_default_poll_interval(self) -> None:
        """Client should have default poll interval of 1 second."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        assert client.poll_interval == 1.0

    def test_client_custom_poll_interval(self) -> None:
        """Client should accept custom poll interval."""
        client = IcypeasClient(api_key="test-key", poll_interval=2.0)  # pragma: allowlist secret
        assert client.poll_interval == 2.0

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "icypeas"


class TestIcypeasClientHeaders:
    """Tests for IcypeasClient headers."""

    def test_headers_include_authorization(self) -> None:
        """Headers should include Authorization with API key."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include correct Content-Type."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"


class TestFindEmail:
    """Tests for IcypeasClient.find_email()."""

    @pytest.fixture
    def client(self) -> IcypeasClient:
        """Create client fixture."""
        return IcypeasClient(
            api_key="test-key",  # pragma: allowlist secret
            poll_interval=0.01,
            max_poll_attempts=2,
        )

    @pytest.mark.asyncio
    async def test_find_email_success(self, client: IcypeasClient) -> None:
        """find_email should return result on success."""
        search_response = {
            "success": True,
            "item": {"_id": "search-123", "status": "SCHEDULED"},
        }
        poll_response = {
            "item": {
                "_id": "search-123",
                "status": "DEBITED",
                "emails": [{"email": "john@company.com", "certainty": 0.95}],
                "firstname": "John",
                "lastname": "Doe",
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [search_response, poll_response]
            result = await client.find_email(
                first_name="John", last_name="Doe", domain="company.com"
            )

            assert result.email == "john@company.com"
            assert result.certainty == 0.95
            assert result.found is True

    @pytest.mark.asyncio
    async def test_find_email_no_wait(self, client: IcypeasClient) -> None:
        """find_email should return immediately when wait_for_result=False."""
        search_response = {
            "success": True,
            "item": {"_id": "search-123", "status": "SCHEDULED"},
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = search_response
            result = await client.find_email(
                first_name="John",
                last_name="Doe",
                domain="company.com",
                wait_for_result=False,
            )

            assert result.search_id == "search-123"
            assert result.is_processing is True

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_first_name(self, client: IcypeasClient) -> None:
        """find_email should raise ValueError if first_name is missing."""
        with pytest.raises(ValueError, match="first_name is required"):
            await client.find_email(first_name="", last_name="Doe", domain="company.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_last_name(self, client: IcypeasClient) -> None:
        """find_email should raise ValueError if last_name is missing."""
        with pytest.raises(ValueError, match="last_name is required"):
            await client.find_email(first_name="John", last_name="", domain="company.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_domain_and_company(
        self, client: IcypeasClient
    ) -> None:
        """find_email should raise ValueError if both domain and company are missing."""
        with pytest.raises(ValueError, match="Either domain or company is required"):
            await client.find_email(first_name="John", last_name="Doe")


class TestGetSearchResult:
    """Tests for IcypeasClient.get_search_result()."""

    @pytest.fixture
    def client(self) -> IcypeasClient:
        """Create client fixture."""
        return IcypeasClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_search_result_success(self, client: IcypeasClient) -> None:
        """get_search_result should return result."""
        mock_response = {
            "item": {
                "_id": "search-123",
                "status": "DEBITED",
                "emails": [{"email": "john@company.com", "certainty": 0.9}],
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_search_result("search-123")

            assert result.email == "john@company.com"
            assert result.status == IcypeasSearchStatus.DEBITED

    @pytest.mark.asyncio
    async def test_get_search_result_raises_on_missing_id(self, client: IcypeasClient) -> None:
        """get_search_result should raise ValueError if search_id is missing."""
        with pytest.raises(ValueError, match="search_id is required"):
            await client.get_search_result("")


class TestVerifyEmail:
    """Tests for IcypeasClient.verify_email()."""

    @pytest.fixture
    def client(self) -> IcypeasClient:
        """Create client fixture."""
        return IcypeasClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_valid(self, client: IcypeasClient) -> None:
        """verify_email should return valid result."""
        mock_response = {"valid": True, "deliverable": True, "status": "valid"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("john@company.com")

            assert result.is_valid is True
            assert result.is_deliverable is True

    @pytest.mark.asyncio
    async def test_verify_email_raises_on_invalid_format(self, client: IcypeasClient) -> None:
        """verify_email should raise ValueError for invalid email format."""
        with pytest.raises(ValueError, match="Invalid email format"):
            await client.verify_email("invalid-email")


class TestGetCredits:
    """Tests for IcypeasClient.get_credits()."""

    @pytest.fixture
    def client(self) -> IcypeasClient:
        """Create client fixture."""
        return IcypeasClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_credits_success(self, client: IcypeasClient) -> None:
        """get_credits should return credits info."""
        mock_response = {"credits": 500}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_credits()

            assert result.credits_remaining == 500
            assert result.has_credits is True


class TestHealthCheck:
    """Tests for IcypeasClient.health_check()."""

    @pytest.fixture
    def client(self) -> IcypeasClient:
        """Create client fixture."""
        return IcypeasClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: IcypeasClient) -> None:
        """health_check should return healthy status on success."""
        mock_credits = IcypeasCreditsInfo(credits_remaining=100, raw_response={})

        with patch.object(client, "get_credits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_credits
            result = await client.health_check()

            assert result["healthy"] is True
            assert result["credits_remaining"] == 100

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: IcypeasClient) -> None:
        """health_check should return unhealthy status on failure."""
        with patch.object(client, "get_credits", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            result = await client.health_check()

            assert result["healthy"] is False


class TestEmailResultProperties:
    """Tests for IcypeasEmailResult properties."""

    def test_found_true(self) -> None:
        """found should be True when email exists and status is DEBITED."""
        result = IcypeasEmailResult(
            email="test@example.com",
            certainty=0.9,
            first_name="Test",
            last_name="User",
            domain="example.com",
            status=IcypeasSearchStatus.DEBITED,
            search_id="123",
            raw_response={},
        )
        assert result.found is True

    def test_found_false_no_email(self) -> None:
        """found should be False when email is None."""
        result = IcypeasEmailResult(
            email=None,
            certainty=0.0,
            first_name="Test",
            last_name="User",
            domain="example.com",
            status=IcypeasSearchStatus.DEBITED,
            search_id="123",
            raw_response={},
        )
        assert result.found is False

    def test_is_high_confidence_true(self) -> None:
        """is_high_confidence should be True when certainty >= 0.8."""
        result = IcypeasEmailResult(
            email="test@example.com",
            certainty=0.85,
            first_name=None,
            last_name=None,
            domain=None,
            status=IcypeasSearchStatus.DEBITED,
            search_id=None,
            raw_response={},
        )
        assert result.is_high_confidence is True

    def test_is_processing_true(self) -> None:
        """is_processing should be True for IN_PROGRESS status."""
        result = IcypeasEmailResult(
            email=None,
            certainty=0.0,
            first_name=None,
            last_name=None,
            domain=None,
            status=IcypeasSearchStatus.IN_PROGRESS,
            search_id="123",
            raw_response={},
        )
        assert result.is_processing is True


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        client = IcypeasClient(api_key="test-key")  # pragma: allowlist secret

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass
            mock_close.assert_called_once()
