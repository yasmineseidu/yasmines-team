"""Unit tests for Muraena integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.muraena import (
    MuraenaClient,
    MuraenaContactResult,
    MuraenaCreditsInfo,
)


class TestMuraenaClientInitialization:
    """Tests for MuraenaClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = MuraenaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct Muraena API base URL."""
        client = MuraenaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.muraena.ai/api/v1"

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = MuraenaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "muraena"


class TestMuraenaClientHeaders:
    """Tests for MuraenaClient headers."""

    def test_headers_include_api_key(self) -> None:
        """Headers should include X-API-Key."""
        client = MuraenaClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["X-API-Key"] == "test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include correct Content-Type."""
        client = MuraenaClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"


class TestFindContact:
    """Tests for MuraenaClient.find_contact()."""

    @pytest.fixture
    def client(self) -> MuraenaClient:
        """Create client fixture."""
        return MuraenaClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_contact_success(self, client: MuraenaClient) -> None:
        """find_contact should return result on success."""
        mock_response = {
            "results": [
                {
                    "email": "john@company.com",
                    "phone": "+1234567890",
                    "first_name": "John",
                    "last_name": "Smith",
                    "title": "CEO",
                    "company": "Company Inc",
                    "linkedin_url": "https://linkedin.com/in/johnsmith",
                    "email_verified": True,
                }
            ]
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_contact(
                first_name="John", last_name="Smith", company="Company Inc"
            )

            assert result.email == "john@company.com"
            assert result.phone == "+1234567890"
            assert result.found is True
            assert result.is_verified is True

    @pytest.mark.asyncio
    async def test_find_contact_not_found(self, client: MuraenaClient) -> None:
        """find_contact should return empty result when not found."""
        mock_response = {"results": []}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_contact(
                first_name="Unknown", last_name="Person", domain="unknown.com"
            )

            assert result.email is None
            assert result.found is False

    @pytest.mark.asyncio
    async def test_find_contact_raises_on_missing_name(self, client: MuraenaClient) -> None:
        """find_contact should raise ValueError if first_name is missing."""
        with pytest.raises(ValueError, match="first_name is required"):
            await client.find_contact(first_name="", last_name="Smith", company="Inc")

    @pytest.mark.asyncio
    async def test_find_contact_raises_on_missing_identifiers(self, client: MuraenaClient) -> None:
        """find_contact should raise ValueError if no identifiers provided."""
        with pytest.raises(ValueError, match="Either company, domain, or linkedin_url is required"):
            await client.find_contact(first_name="John", last_name="Smith")


class TestSearchByLinkedIn:
    """Tests for MuraenaClient.search_by_linkedin()."""

    @pytest.fixture
    def client(self) -> MuraenaClient:
        """Create client fixture."""
        return MuraenaClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_by_linkedin_success(self, client: MuraenaClient) -> None:
        """search_by_linkedin should return result."""
        mock_response = {
            "results": [
                {
                    "email": "john@company.com",
                    "first_name": "John",
                    "last_name": "Smith",
                }
            ]
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.search_by_linkedin("https://linkedin.com/in/johnsmith")

            assert result.email == "john@company.com"

    @pytest.mark.asyncio
    async def test_search_by_linkedin_raises_on_invalid_url(self, client: MuraenaClient) -> None:
        """search_by_linkedin should raise ValueError for invalid URL."""
        with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
            await client.search_by_linkedin("https://example.com/profile")


class TestVerifyEmail:
    """Tests for MuraenaClient.verify_email()."""

    @pytest.fixture
    def client(self) -> MuraenaClient:
        """Create client fixture."""
        return MuraenaClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_valid(self, client: MuraenaClient) -> None:
        """verify_email should return valid result."""
        mock_response = {"valid": True, "deliverable": True, "status": "valid"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("john@company.com")

            assert result.is_valid is True
            assert result.is_deliverable is True


class TestGetCredits:
    """Tests for MuraenaClient.get_credits()."""

    @pytest.fixture
    def client(self) -> MuraenaClient:
        """Create client fixture."""
        return MuraenaClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_credits_success(self, client: MuraenaClient) -> None:
        """get_credits should return credits info."""
        mock_response = {"credits": 1000, "plan": "Business"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_credits()

            assert result.credits_remaining == 1000
            assert result.plan_name == "Business"


class TestHealthCheck:
    """Tests for MuraenaClient.health_check()."""

    @pytest.fixture
    def client(self) -> MuraenaClient:
        """Create client fixture."""
        return MuraenaClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: MuraenaClient) -> None:
        """health_check should return healthy status on success."""
        mock_credits = MuraenaCreditsInfo(credits_remaining=100, plan_name="Pro", raw_response={})

        with patch.object(client, "get_credits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_credits
            result = await client.health_check()

            assert result["healthy"] is True


class TestContactResultProperties:
    """Tests for MuraenaContactResult properties."""

    def test_found_true(self) -> None:
        """found should be True when email exists."""
        result = MuraenaContactResult(
            email="test@example.com",
            phone=None,
            first_name="Test",
            last_name="User",
            title=None,
            company=None,
            linkedin_url=None,
            is_verified=False,
            raw_response={},
        )
        assert result.found is True

    def test_has_phone_true(self) -> None:
        """has_phone should be True when phone exists."""
        result = MuraenaContactResult(
            email="test@example.com",
            phone="+1234567890",
            first_name="Test",
            last_name="User",
            title=None,
            company=None,
            linkedin_url=None,
            is_verified=False,
            raw_response={},
        )
        assert result.has_phone is True
