"""Unit tests for Nimbler integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.nimbler import (
    NimblerClient,
    NimblerCompanyResult,
    NimblerContactResult,
)


class TestNimblerClientInitialization:
    """Tests for NimblerClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct Nimbler API base URL."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.nimbler.com/v1"

    def test_client_default_timeout(self) -> None:
        """Client should have default timeout of 60 seconds."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = NimblerClient(api_key="test-key", timeout=120.0)  # pragma: allowlist secret
        assert client.timeout == 120.0

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "nimbler"


class TestNimblerClientHeaders:
    """Tests for NimblerClient headers."""

    def test_headers_include_bearer_token(self) -> None:
        """Headers should include Bearer authorization."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include correct Content-Type."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestEnrichContact:
    """Tests for NimblerClient.enrich_contact()."""

    @pytest.fixture
    def client(self) -> NimblerClient:
        """Create client fixture."""
        return NimblerClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_enrich_contact_with_email(self, client: NimblerClient) -> None:
        """enrich_contact should return result when using email."""
        mock_response = {
            "data": {
                "contact": {
                    "email": "john@company.com",
                    "mobile_phone": "+1234567890",
                    "first_name": "John",
                    "last_name": "Smith",
                    "title": "CEO",
                    "company": "Company Inc",
                }
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.enrich_contact(email="john@company.com")

            assert result.email == "john@company.com"
            assert result.mobile_phone == "+1234567890"
            assert result.first_name == "John"
            assert result.found is True

    @pytest.mark.asyncio
    async def test_enrich_contact_with_linkedin(self, client: NimblerClient) -> None:
        """enrich_contact should return result when using LinkedIn URL."""
        mock_response = {
            "contact": {
                "email": "jane@company.com",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.enrich_contact(linkedin_url="https://linkedin.com/in/janesmith")

            assert result.email == "jane@company.com"
            assert result.found is True

    @pytest.mark.asyncio
    async def test_enrich_contact_with_name_and_company(self, client: NimblerClient) -> None:
        """enrich_contact should return result when using name+company."""
        mock_response = {
            "data": {
                "contact": {
                    "email": "john@company.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "company_name": "Company Inc",
                }
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.enrich_contact(
                first_name="John", last_name="Smith", company="Company Inc"
            )

            assert result.email == "john@company.com"
            assert result.found is True

    @pytest.mark.asyncio
    async def test_enrich_contact_not_found(self, client: NimblerClient) -> None:
        """enrich_contact should return empty result when contact not found."""
        mock_response = {"data": {"contact": {}}}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.enrich_contact(email="unknown@company.com")

            assert result.email is None
            assert result.found is False

    @pytest.mark.asyncio
    async def test_enrich_contact_raises_on_missing_identifiers(
        self, client: NimblerClient
    ) -> None:
        """enrich_contact should raise ValueError if no identifiers provided."""
        with pytest.raises(
            ValueError,
            match="Either email, linkedin_url, or \\(first_name \\+ last_name \\+ company\\) is required",
        ):
            await client.enrich_contact()

    @pytest.mark.asyncio
    async def test_enrich_contact_raises_on_empty_email(self, client: NimblerClient) -> None:
        """enrich_contact should raise ValueError if email is empty."""
        with pytest.raises(ValueError):
            await client.enrich_contact(email="")

    @pytest.mark.asyncio
    async def test_enrich_contact_raises_on_partial_name(self, client: NimblerClient) -> None:
        """enrich_contact should raise ValueError if only first_name provided."""
        with pytest.raises(ValueError):
            await client.enrich_contact(first_name="John")


class TestFindMobile:
    """Tests for NimblerClient.find_mobile()."""

    @pytest.fixture
    def client(self) -> NimblerClient:
        """Create client fixture."""
        return NimblerClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_mobile_success(self, client: NimblerClient) -> None:
        """find_mobile should return result with mobile phone."""
        mock_response = {
            "data": {
                "contact": {
                    "mobile_phone": "+1234567890",
                    "first_name": "John",
                    "last_name": "Smith",
                }
            }
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.find_mobile(linkedin_url="https://linkedin.com/in/johnsmith")

            assert result.mobile_phone == "+1234567890"
            assert result.has_mobile is True

    @pytest.mark.asyncio
    async def test_find_mobile_raises_on_missing_identifiers(self, client: NimblerClient) -> None:
        """find_mobile should raise ValueError if no identifiers provided."""
        with pytest.raises(ValueError):
            await client.find_mobile()


class TestLookupCompany:
    """Tests for NimblerClient.lookup_company()."""

    @pytest.fixture
    def client(self) -> NimblerClient:
        """Create client fixture."""
        return NimblerClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_lookup_company_by_domain(self, client: NimblerClient) -> None:
        """lookup_company should return company info by domain."""
        mock_response = {
            "name": "Company Inc",
            "domain": "company.com",
            "industry": "Technology",
            "size": "100-500",
            "location": "San Francisco, CA",
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.lookup_company(domain="company.com")

            assert result.name == "Company Inc"
            assert result.domain == "company.com"
            assert result.industry == "Technology"
            assert result.found is True

    @pytest.mark.asyncio
    async def test_lookup_company_by_name(self, client: NimblerClient) -> None:
        """lookup_company should return company info by name."""
        mock_response = {"company_name": "Acme Corp", "domain": "acme.com"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.lookup_company(company_name="Acme Corp")

            assert result.name == "Acme Corp"
            assert result.found is True

    @pytest.mark.asyncio
    async def test_lookup_company_not_found(self, client: NimblerClient) -> None:
        """lookup_company should return empty result when not found."""
        mock_response = {}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.lookup_company(domain="unknown.com")

            assert result.name is None
            assert result.found is False

    @pytest.mark.asyncio
    async def test_lookup_company_raises_on_missing_params(self, client: NimblerClient) -> None:
        """lookup_company should raise ValueError if no params provided."""
        with pytest.raises(ValueError, match="Either domain or company_name is required"):
            await client.lookup_company()


class TestHealthCheck:
    """Tests for NimblerClient.health_check()."""

    @pytest.fixture
    def client(self) -> NimblerClient:
        """Create client fixture."""
        return NimblerClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: NimblerClient) -> None:
        """health_check should return healthy status."""
        result = await client.health_check()

        assert result["healthy"] is True
        assert result["name"] == "nimbler"
        assert result["base_url"] == "https://api.nimbler.com/v1"


class TestContactResultProperties:
    """Tests for NimblerContactResult properties."""

    def test_found_true_with_email(self) -> None:
        """found should be True when email exists."""
        result = NimblerContactResult(
            email="test@example.com",
            personal_email=None,
            mobile_phone=None,
            direct_phone=None,
            first_name="Test",
            last_name="User",
            title=None,
            company=None,
            linkedin_url=None,
            location=None,
            skills=[],
            raw_response={},
        )
        assert result.found is True

    def test_found_true_with_mobile(self) -> None:
        """found should be True when mobile_phone exists."""
        result = NimblerContactResult(
            email=None,
            personal_email=None,
            mobile_phone="+1234567890",
            direct_phone=None,
            first_name="Test",
            last_name="User",
            title=None,
            company=None,
            linkedin_url=None,
            location=None,
            skills=[],
            raw_response={},
        )
        assert result.found is True

    def test_found_false(self) -> None:
        """found should be False when no email or mobile."""
        result = NimblerContactResult(
            email=None,
            personal_email=None,
            mobile_phone=None,
            direct_phone=None,
            first_name="Test",
            last_name="User",
            title=None,
            company=None,
            linkedin_url=None,
            location=None,
            skills=[],
            raw_response={},
        )
        assert result.found is False

    def test_has_mobile_true(self) -> None:
        """has_mobile should be True when mobile_phone exists."""
        result = NimblerContactResult(
            email=None,
            personal_email=None,
            mobile_phone="+1234567890",
            direct_phone=None,
            first_name=None,
            last_name=None,
            title=None,
            company=None,
            linkedin_url=None,
            location=None,
            skills=[],
            raw_response={},
        )
        assert result.has_mobile is True

    def test_has_personal_email_true(self) -> None:
        """has_personal_email should be True when personal_email exists."""
        result = NimblerContactResult(
            email=None,
            personal_email="personal@gmail.com",
            mobile_phone=None,
            direct_phone=None,
            first_name=None,
            last_name=None,
            title=None,
            company=None,
            linkedin_url=None,
            location=None,
            skills=[],
            raw_response={},
        )
        assert result.has_personal_email is True


class TestCompanyResultProperties:
    """Tests for NimblerCompanyResult properties."""

    def test_found_true(self) -> None:
        """found should be True when name exists."""
        result = NimblerCompanyResult(
            name="Company Inc",
            domain="company.com",
            industry=None,
            size=None,
            location=None,
            linkedin_url=None,
            raw_response={},
        )
        assert result.found is True

    def test_found_false(self) -> None:
        """found should be False when name is None."""
        result = NimblerCompanyResult(
            name=None,
            domain=None,
            industry=None,
            size=None,
            location=None,
            linkedin_url=None,
            raw_response={},
        )
        assert result.found is False


class TestParseContactResult:
    """Tests for NimblerClient._parse_contact_result()."""

    @pytest.fixture
    def client(self) -> NimblerClient:
        """Create client fixture."""
        return NimblerClient(api_key="test-key")  # pragma: allowlist secret

    def test_parse_nested_response(self, client: NimblerClient) -> None:
        """Should handle nested data.contact structure."""
        response = {
            "data": {
                "contact": {
                    "email": "test@company.com",
                    "mobile": "+1234567890",
                }
            }
        }
        result = client._parse_contact_result(response)
        assert result.email == "test@company.com"
        assert result.mobile_phone == "+1234567890"

    def test_parse_flat_response(self, client: NimblerClient) -> None:
        """Should handle flat response structure."""
        response = {
            "email": "test@company.com",
            "work_email": "work@company.com",
        }
        result = client._parse_contact_result(response)
        assert result.email == "test@company.com"

    def test_parse_skills_array(self, client: NimblerClient) -> None:
        """Should handle skills as array."""
        response = {"skills": ["Python", "JavaScript", "SQL"]}
        result = client._parse_contact_result(response)
        assert result.skills == ["Python", "JavaScript", "SQL"]

    def test_parse_skills_string(self, client: NimblerClient) -> None:
        """Should handle skills as comma-separated string."""
        response = {"skills": "Python, JavaScript, SQL"}
        result = client._parse_contact_result(response)
        assert result.skills == ["Python", "JavaScript", "SQL"]


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        client = NimblerClient(api_key="test-key")  # pragma: allowlist secret

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass
            mock_close.assert_called_once()
