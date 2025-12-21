"""
Unit tests for Tomba integration client.

Tests cover all TombaClient functionality including:
- Client initialization with dual-key authentication
- Domain search operations
- Email finder operations
- Email verification
- LinkedIn email lookup
- Email count
- Error handling
- Dataclass properties

Run with: pytest __tests__/unit/integrations/test_tomba.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.tomba_fixtures import (
    create_account_info_response,
    create_domain_search_empty_response,
    create_domain_search_response,
    create_email_count_response,
    create_email_finder_not_found_response,
    create_email_finder_response,
    create_linkedin_email_response,
    create_verification_invalid_response,
    create_verification_response,
)
from src.integrations import (
    IntegrationError,
    TombaAccountInfo,
    TombaClient,
    TombaDomainSearchResult,
    TombaEmail,
    TombaEmailCountResult,
    TombaEmailFinderResult,
    TombaEmailType,
    TombaError,
    TombaVerificationResult,
    TombaVerificationStatus,
)

# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestTombaClientInitialization:
    """Tests for TombaClient initialization."""

    def test_initialization_with_required_params(self) -> None:
        """Test client initializes with API key and secret."""
        client = TombaClient(
            api_key="ta_test_key",  # pragma: allowlist secret
            api_secret="ts_test_secret",  # pragma: allowlist secret
        )
        assert client.api_key == "ta_test_key"  # pragma: allowlist secret
        assert client.api_secret == "ts_test_secret"  # pragma: allowlist secret
        assert client.name == "tomba"
        assert client.BASE_URL == "https://api.tomba.io/v1"

    def test_initialization_with_custom_timeout(self) -> None:
        """Test client initializes with custom timeout."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
            timeout=120.0,
        )
        assert client.timeout == 120.0

    def test_initialization_with_custom_retries(self) -> None:
        """Test client initializes with custom max_retries."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
            max_retries=5,
        )
        assert client.max_retries == 5

    def test_default_timeout_is_60_seconds(self) -> None:
        """Test default timeout is 60 seconds."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        )
        assert client.timeout == 60.0

    def test_default_max_retries_is_3(self) -> None:
        """Test default max_retries is 3."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        )
        assert client.max_retries == 3


# ============================================================================
# Header Tests
# ============================================================================


class TestTombaClientHeaders:
    """Tests for Tomba API headers with dual-key authentication."""

    def test_headers_include_dual_auth_keys(self) -> None:
        """Test headers include both X-Tomba-Key and X-Tomba-Secret."""
        client = TombaClient(
            api_key="ta_my_key",  # pragma: allowlist secret
            api_secret="ts_my_secret",  # pragma: allowlist secret
        )
        headers = client._get_headers()

        assert headers["X-Tomba-Key"] == "ta_my_key"  # pragma: allowlist secret
        assert headers["X-Tomba-Secret"] == "ts_my_secret"  # pragma: allowlist secret

    def test_headers_include_content_type(self) -> None:
        """Test headers include Content-Type."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        )
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Test headers include Accept."""
        client = TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        )
        headers = client._get_headers()

        assert headers["Accept"] == "application/json"


# ============================================================================
# Account Info Tests
# ============================================================================


class TestTombaGetAccountInfo:
    """Tests for get_account_info method."""

    @pytest.mark.asyncio
    async def test_get_account_info_success(self) -> None:
        """Test successful account info retrieval."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_account_info_response(
                    email="user@example.com",
                    search_available=100,
                    search_used=25,
                )

                result = await client.get_account_info()

                assert isinstance(result, TombaAccountInfo)
                assert result.email == "user@example.com"
                assert result.search_remaining == 75
                mock_request.assert_called_once_with(
                    method="GET",
                    endpoint="/me",
                )

    @pytest.mark.asyncio
    async def test_get_account_info_search_remaining(self) -> None:
        """Test search_remaining property calculation."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_account_info_response(
                    search_available=100,
                    search_used=75,
                )

                result = await client.get_account_info()

                assert result.search_remaining == 25

    @pytest.mark.asyncio
    async def test_get_account_info_verification_remaining(self) -> None:
        """Test verification_remaining property calculation."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_account_info_response(
                    verifications_available=200,
                    verifications_used=150,
                )

                result = await client.get_account_info()

                assert result.verification_remaining == 50

    @pytest.mark.asyncio
    async def test_get_account_info_api_error(self) -> None:
        """Test error handling for account info retrieval."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.side_effect = IntegrationError(
                    message="Unauthorized",
                    status_code=401,
                )

                with pytest.raises(TombaError) as exc_info:
                    await client.get_account_info()

                assert "Failed to get account info" in str(exc_info.value)


# ============================================================================
# Domain Search Tests
# ============================================================================


class TestTombaDomainSearch:
    """Tests for search_domain method."""

    @pytest.mark.asyncio
    async def test_search_domain_success(self) -> None:
        """Test successful domain search."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response(domain="stripe.com")

                result = await client.search_domain("stripe.com")

                assert isinstance(result, TombaDomainSearchResult)
                assert result.domain == "stripe.com"
                assert len(result.emails) == 2
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_domain_with_pagination(self) -> None:
        """Test domain search with pagination parameters."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response()

                await client.search_domain("stripe.com", page=2, limit=50)

                mock_request.assert_called_once()
                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["page"] == 2
                assert call_kwargs["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_search_domain_limit_capped_at_100(self) -> None:
        """Test that limit is capped at API maximum of 100."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response()

                await client.search_domain("stripe.com", limit=500)

                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["limit"] == 100

    @pytest.mark.asyncio
    async def test_search_domain_with_department_filter(self) -> None:
        """Test domain search with department filter."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response()

                await client.search_domain("stripe.com", department="engineering")

                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_search_domain_with_email_type_filter(self) -> None:
        """Test domain search with email type filter."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response()

                await client.search_domain(
                    "stripe.com",
                    email_type=TombaEmailType.PERSONAL,
                )

                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["type"] == "personal"

    @pytest.mark.asyncio
    async def test_search_domain_empty_result(self) -> None:
        """Test domain search with no emails found."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_empty_response()

                result = await client.search_domain("nonexistent.com")

                assert result.total_results == 0
                assert len(result.emails) == 0

    @pytest.mark.asyncio
    async def test_search_domain_has_more_property(self) -> None:
        """Test has_more property for pagination."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_domain_search_response(
                    total=50,
                )

                result = await client.search_domain("stripe.com")

                assert result.has_more is True

    @pytest.mark.asyncio
    async def test_search_domain_empty_domain_raises_error(self) -> None:
        """Test that empty domain raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.search_domain("")

            assert "domain is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_domain_whitespace_domain_raises_error(self) -> None:
        """Test that whitespace-only domain raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.search_domain("   ")

            assert "domain is required" in str(exc_info.value)


# ============================================================================
# Email Finder Tests
# ============================================================================


class TestTombaEmailFinder:
    """Tests for find_email method."""

    @pytest.mark.asyncio
    async def test_find_email_with_first_last_name(self) -> None:
        """Test finding email with first and last name."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_finder_response()

                result = await client.find_email(
                    domain="stripe.com",
                    first_name="John",
                    last_name="Doe",
                )

                assert isinstance(result, TombaEmailFinderResult)
                assert result.email == "john.doe@stripe.com"
                assert result.found is True

    @pytest.mark.asyncio
    async def test_find_email_with_full_name(self) -> None:
        """Test finding email with full name."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_finder_response()

                result = await client.find_email(
                    domain="stripe.com",
                    full_name="John Doe",
                )

                assert result.found is True
                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["first_name"] == "John"
                assert call_kwargs["params"]["last_name"] == "Doe"

    @pytest.mark.asyncio
    async def test_find_email_high_confidence(self) -> None:
        """Test is_high_confidence property."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_finder_response(
                    confidence=95,
                )

                result = await client.find_email(
                    domain="stripe.com",
                    full_name="John Doe",
                )

                assert result.is_high_confidence is True

    @pytest.mark.asyncio
    async def test_find_email_low_confidence(self) -> None:
        """Test is_high_confidence is False for low confidence."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_finder_response(
                    confidence=50,
                )

                result = await client.find_email(
                    domain="stripe.com",
                    full_name="John Doe",
                )

                assert result.is_high_confidence is False

    @pytest.mark.asyncio
    async def test_find_email_not_found(self) -> None:
        """Test finding email when not found."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_finder_not_found_response()

                result = await client.find_email(
                    domain="nonexistent.com",
                    full_name="Nobody Here",
                )

                assert result.found is False
                assert result.email is None

    @pytest.mark.asyncio
    async def test_find_email_missing_domain_raises_error(self) -> None:
        """Test that missing domain raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.find_email(
                    domain="",
                    full_name="John Doe",
                )

            assert "domain is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_email_missing_name_raises_error(self) -> None:
        """Test that missing name parameters raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.find_email(domain="stripe.com")

            assert "full_name or both first_name and last_name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_email_partial_name_raises_error(self) -> None:
        """Test that only first_name without last_name raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.find_email(
                    domain="stripe.com",
                    first_name="John",
                )

            assert "full_name or both first_name and last_name" in str(exc_info.value)


# ============================================================================
# Email Verification Tests
# ============================================================================


class TestTombaEmailVerification:
    """Tests for verify_email method."""

    @pytest.mark.asyncio
    async def test_verify_email_valid(self) -> None:
        """Test successful email verification."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_verification_response(
                    email="john.doe@stripe.com",
                    status="valid",
                )

                result = await client.verify_email("john.doe@stripe.com")

                assert isinstance(result, TombaVerificationResult)
                assert result.is_valid is True
                assert result.status == TombaVerificationStatus.VALID

    @pytest.mark.asyncio
    async def test_verify_email_invalid(self) -> None:
        """Test verification of invalid email."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_verification_invalid_response()

                result = await client.verify_email("invalid@nonexistent.com")

                assert result.is_valid is False
                assert result.status == TombaVerificationStatus.INVALID

    @pytest.mark.asyncio
    async def test_verify_email_is_risky_accept_all(self) -> None:
        """Test is_risky property for accept_all domains."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_verification_response(
                    accept_all=True,
                )

                result = await client.verify_email("test@catchall.com")

                assert result.is_risky is True

    @pytest.mark.asyncio
    async def test_verify_email_is_risky_disposable(self) -> None:
        """Test is_risky property for disposable emails."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_verification_response(
                    disposable=True,
                )

                result = await client.verify_email("test@tempmail.com")

                assert result.is_risky is True

    @pytest.mark.asyncio
    async def test_verify_email_normalizes_to_lowercase(self) -> None:
        """Test that email is normalized to lowercase."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_verification_response()

                result = await client.verify_email("John.Doe@Stripe.COM")

                assert result.email == "john.doe@stripe.com"

    @pytest.mark.asyncio
    async def test_verify_email_empty_raises_error(self) -> None:
        """Test that empty email raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.verify_email("")

            assert "email is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_email_invalid_format_raises_error(self) -> None:
        """Test that invalid email format raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.verify_email("not-an-email")

            assert "Invalid email format" in str(exc_info.value)


# ============================================================================
# LinkedIn Email Finder Tests
# ============================================================================


class TestTombaLinkedInFinder:
    """Tests for find_email_from_linkedin method."""

    @pytest.mark.asyncio
    async def test_find_email_from_linkedin_success(self) -> None:
        """Test successful LinkedIn email lookup."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_linkedin_email_response(
                    email="john.doe@stripe.com",
                    linkedin_url="https://linkedin.com/in/johndoe",
                )

                result = await client.find_email_from_linkedin("https://linkedin.com/in/johndoe")

                assert isinstance(result, TombaEmailFinderResult)
                assert result.email == "john.doe@stripe.com"
                assert result.found is True

    @pytest.mark.asyncio
    async def test_find_email_from_linkedin_with_www(self) -> None:
        """Test LinkedIn URL with www prefix."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_linkedin_email_response()

                await client.find_email_from_linkedin("https://www.linkedin.com/in/johndoe")

                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_email_from_linkedin_empty_raises_error(self) -> None:
        """Test that empty URL raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.find_email_from_linkedin("")

            assert "linkedin_url is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_email_from_linkedin_invalid_url_raises_error(self) -> None:
        """Test that non-LinkedIn URL raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.find_email_from_linkedin("https://twitter.com/johndoe")

            assert "Invalid LinkedIn URL" in str(exc_info.value)


# ============================================================================
# Email Count Tests
# ============================================================================


class TestTombaEmailCount:
    """Tests for get_email_count method."""

    @pytest.mark.asyncio
    async def test_get_email_count_success(self) -> None:
        """Test successful email count retrieval."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_count_response(
                    domain="stripe.com",
                    total=150,
                    personal=120,
                    generic=30,
                )

                result = await client.get_email_count("stripe.com")

                assert isinstance(result, TombaEmailCountResult)
                assert result.total == 150
                assert result.personal_emails == 120
                assert result.generic_emails == 30
                assert result.has_emails is True

    @pytest.mark.asyncio
    async def test_get_email_count_no_emails(self) -> None:
        """Test email count when no emails found."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_count_response(
                    total=0,
                    personal=0,
                    generic=0,
                )

                result = await client.get_email_count("nonexistent.com")

                assert result.has_emails is False

    @pytest.mark.asyncio
    async def test_get_email_count_includes_department_breakdown(self) -> None:
        """Test email count includes department breakdown."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_email_count_response()

                result = await client.get_email_count("stripe.com")

                assert "engineering" in result.department
                assert "sales" in result.department

    @pytest.mark.asyncio
    async def test_get_email_count_empty_domain_raises_error(self) -> None:
        """Test that empty domain raises ValueError."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with pytest.raises(ValueError) as exc_info:
                await client.get_email_count("")

            assert "domain is required" in str(exc_info.value)


# ============================================================================
# Health Check Tests
# ============================================================================


class TestTombaHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test successful health check."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = create_account_info_response()

                result = await client.health_check()

                assert result["name"] == "tomba"
                assert result["healthy"] is True
                assert "search_remaining" in result
                assert "verification_remaining" in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        """Test health check when API fails."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.side_effect = IntegrationError(
                    message="Unauthorized",
                    status_code=401,
                )

                result = await client.health_check()

                assert result["name"] == "tomba"
                assert result["healthy"] is False
                assert "error" in result


# ============================================================================
# Call Endpoint Tests
# ============================================================================


class TestTombaCallEndpoint:
    """Tests for call_endpoint method."""

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self) -> None:
        """Test calling endpoint directly."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = {"data": "test"}

                result = await client.call_endpoint("/test", method="GET")

                assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_call_endpoint_with_params(self) -> None:
        """Test calling endpoint with parameters."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.return_value = {"data": "test"}

                await client.call_endpoint(
                    "/test",
                    method="GET",
                    params={"domain": "stripe.com"},
                )

                call_kwargs = mock_request.call_args[1]
                assert call_kwargs["params"]["domain"] == "stripe.com"

    @pytest.mark.asyncio
    async def test_call_endpoint_error(self) -> None:
        """Test error handling for endpoint call."""
        async with TombaClient(
            api_key="ta_key",  # pragma: allowlist secret
            api_secret="ts_secret",  # pragma: allowlist secret
        ) as client:
            with patch.object(
                client,
                "_request_with_retry",
                new_callable=AsyncMock,
            ) as mock_request:
                mock_request.side_effect = IntegrationError(
                    message="Not found",
                    status_code=404,
                )

                with pytest.raises(TombaError) as exc_info:
                    await client.call_endpoint("/nonexistent")

                assert "API call failed" in str(exc_info.value)


# ============================================================================
# Dataclass Property Tests
# ============================================================================


class TestTombaEmailDataclass:
    """Tests for TombaEmail dataclass properties."""

    def test_is_verified_true(self) -> None:
        """Test is_verified returns True for valid status."""
        email = TombaEmail(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            position="Engineer",
            department="engineering",
            email_type=TombaEmailType.PERSONAL,
            seniority="senior",
            linkedin="https://linkedin.com/in/test",
            twitter="@test",
            phone_number="+1-555-123-4567",
            sources=[],
            verification_status=TombaVerificationStatus.VALID,
            confidence=95,
            raw_data={},
        )
        assert email.is_verified is True

    def test_is_verified_false(self) -> None:
        """Test is_verified returns False for invalid status."""
        email = TombaEmail(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            position=None,
            department=None,
            email_type=TombaEmailType.PERSONAL,
            seniority=None,
            linkedin=None,
            twitter=None,
            phone_number=None,
            sources=[],
            verification_status=TombaVerificationStatus.INVALID,
            confidence=0,
            raw_data={},
        )
        assert email.is_verified is False

    def test_has_social_true(self) -> None:
        """Test has_social returns True when LinkedIn present."""
        email = TombaEmail(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            position=None,
            department=None,
            email_type=TombaEmailType.PERSONAL,
            seniority=None,
            linkedin="https://linkedin.com/in/test",
            twitter=None,
            phone_number=None,
            sources=[],
            verification_status=None,
            confidence=None,
            raw_data={},
        )
        assert email.has_social is True

    def test_has_social_false(self) -> None:
        """Test has_social returns False when no social links."""
        email = TombaEmail(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            position=None,
            department=None,
            email_type=TombaEmailType.PERSONAL,
            seniority=None,
            linkedin=None,
            twitter=None,
            phone_number=None,
            sources=[],
            verification_status=None,
            confidence=None,
            raw_data={},
        )
        assert email.has_social is False


class TestTombaEnums:
    """Tests for Tomba enums."""

    def test_email_type_values(self) -> None:
        """Test TombaEmailType enum values."""
        assert TombaEmailType.PERSONAL.value == "personal"
        assert TombaEmailType.GENERIC.value == "generic"
        assert TombaEmailType.UNKNOWN.value == "unknown"

    def test_verification_status_values(self) -> None:
        """Test TombaVerificationStatus enum values."""
        assert TombaVerificationStatus.VALID.value == "valid"
        assert TombaVerificationStatus.INVALID.value == "invalid"
        assert TombaVerificationStatus.ACCEPT_ALL.value == "accept_all"
        assert TombaVerificationStatus.WEBMAIL.value == "webmail"
        assert TombaVerificationStatus.DISPOSABLE.value == "disposable"
        assert TombaVerificationStatus.UNKNOWN.value == "unknown"
