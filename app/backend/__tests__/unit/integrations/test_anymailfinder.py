"""
Unit tests for Anymailfinder integration client.

Tests cover:
- Client initialization
- Email finding (person, decision maker, company)
- Email verification
- Account info retrieval
- Error handling (401, 402, 429, network errors)
- Retry logic with exponential backoff
- Health check functionality

Coverage target: >90%
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations import (
    AnymailfinderClient,
    AnymailfinderError,
    AuthenticationError,
    EmailResult,
    EmailStatus,
    PaymentRequiredError,
    RateLimitError,
    VerificationResult,
)


class TestAnymailfinderClientInitialization:
    """Tests for AnymailfinderClient initialization."""

    def test_client_has_correct_name(self) -> None:
        """Client should have 'anymailfinder' as name."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "anymailfinder"

    def test_client_has_correct_base_url(self) -> None:
        """Client should use v5.1 API base URL."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.anymailfinder.com/v5.1"

    def test_client_has_correct_api_version(self) -> None:
        """Client should report v5.1 API version."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        assert client.API_VERSION == "v5.1"

    def test_client_default_timeout_is_180_seconds(self) -> None:
        """Client should have 180s timeout for SMTP verification."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 180.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = AnymailfinderClient(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 retries by default."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = AnymailfinderClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = AnymailfinderClient(api_key="my-secret-key")  # pragma: allowlist secret
        assert client.api_key == "my-secret-key"  # pragma: allowlist secret


class TestAnymailfinderClientHeaders:
    """Tests for HTTP headers configuration."""

    def test_headers_include_api_key(self) -> None:
        """Headers should include API key in Authorization."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestFindPersonEmail:
    """Tests for find_person_email method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(
            api_key="test-key"  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_find_email_with_first_and_last_name(self, client: AnymailfinderClient) -> None:
        """Should find email with first and last name."""
        mock_response = {
            "email": "john.doe@microsoft.com",
            "email_status": "valid",
            "valid_email": "john.doe@microsoft.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_person_email(
                first_name="John",
                last_name="Doe",
                domain="microsoft.com",
            )

            assert isinstance(result, EmailResult)
            assert result.email == "john.doe@microsoft.com"
            assert result.email_status == EmailStatus.VALID
            assert result.is_valid is True

            mock_post.assert_called_once_with(
                "/find-email/person",
                json={
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "microsoft.com",
                },
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_find_email_with_full_name(self, client: AnymailfinderClient) -> None:
        """Should find email with full name."""
        mock_response = {
            "email": "john.doe@microsoft.com",
            "email_status": "valid",
            "valid_email": "john.doe@microsoft.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_person_email(
                full_name="John Doe",
                domain="microsoft.com",
            )

            assert result.email == "john.doe@microsoft.com"
            mock_post.assert_called_once_with(
                "/find-email/person",
                json={"full_name": "John Doe", "domain": "microsoft.com"},
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_find_email_with_company_name(self, client: AnymailfinderClient) -> None:
        """Should find email with company name instead of domain."""
        mock_response = {
            "email": "john.doe@microsoft.com",
            "email_status": "valid",
            "valid_email": "john.doe@microsoft.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_person_email(
                first_name="John",
                last_name="Doe",
                company_name="Microsoft Corporation",
            )

            assert result.email == "john.doe@microsoft.com"
            mock_post.assert_called_once_with(
                "/find-email/person",
                json={
                    "first_name": "John",
                    "last_name": "Doe",
                    "company_name": "Microsoft Corporation",
                },
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_find_email_risky_result(self, client: AnymailfinderClient) -> None:
        """Should handle risky email status."""
        mock_response = {
            "email": "john.doe@example.com",
            "email_status": "risky",
            "valid_email": None,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_person_email(
                first_name="John",
                last_name="Doe",
                domain="example.com",
            )

            assert result.email_status == EmailStatus.RISKY
            assert result.is_valid is False
            assert result.is_usable is True

    @pytest.mark.asyncio
    async def test_find_email_not_found_result(self, client: AnymailfinderClient) -> None:
        """Should handle not found status."""
        mock_response = {
            "email": None,
            "email_status": "not_found",
            "valid_email": None,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_person_email(
                first_name="Unknown",
                last_name="Person",
                domain="nocompany.com",
            )

            assert result.email is None
            assert result.email_status == EmailStatus.NOT_FOUND
            assert result.is_valid is False
            assert result.is_usable is False

    @pytest.mark.asyncio
    async def test_find_email_with_webhook_url(self, client: AnymailfinderClient) -> None:
        """Should include webhook URL in headers."""
        mock_response = {
            "email": "john.doe@microsoft.com",
            "email_status": "valid",
            "valid_email": "john.doe@microsoft.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.find_person_email(
                first_name="John",
                last_name="Doe",
                domain="microsoft.com",
                webhook_url="https://myapp.com/webhook",
            )

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"] == {"x-webhook-url": "https://myapp.com/webhook"}

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_name(self, client: AnymailfinderClient) -> None:
        """Should raise ValueError if name is missing."""
        with pytest.raises(ValueError, match="first_name and last_name"):
            await client.find_person_email(domain="microsoft.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_domain(self, client: AnymailfinderClient) -> None:
        """Should raise ValueError if domain is missing."""
        with pytest.raises(ValueError, match="domain or company_name"):
            await client.find_person_email(first_name="John", last_name="Doe")


class TestFindDecisionMakerEmail:
    """Tests for find_decision_maker_email method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(
            api_key="test-key"  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_find_decision_maker_success(self, client: AnymailfinderClient) -> None:
        """Should find decision maker email."""
        mock_response = {
            "email": "ceo@startup.com",
            "email_status": "valid",
            "valid_email": "ceo@startup.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.find_decision_maker_email(
                domain="startup.com",
                job_title="CEO",
            )

            assert result.email == "ceo@startup.com"
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_find_decision_maker_with_all_params(self, client: AnymailfinderClient) -> None:
        """Should include all optional parameters."""
        mock_response = {
            "email": "vp.eng@startup.com",
            "email_status": "valid",
            "valid_email": "vp.eng@startup.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.find_decision_maker_email(
                domain="startup.com",
                job_title="VP Engineering",
                department="Engineering",
                seniority="VP",
            )

            mock_post.assert_called_once_with(
                "/find-email/decision-maker",
                json={
                    "domain": "startup.com",
                    "job_title": "VP Engineering",
                    "department": "Engineering",
                    "seniority": "VP",
                },
                headers=None,
            )


class TestFindCompanyEmails:
    """Tests for find_company_emails method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(
            api_key="test-key"  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_find_company_emails_success(self, client: AnymailfinderClient) -> None:
        """Should find multiple company emails."""
        mock_response = {
            "domain": "microsoft.com",
            "emails": [
                {
                    "email": "john.doe@microsoft.com",
                    "email_status": "valid",
                    "valid_email": "john.doe@microsoft.com",
                },
                {
                    "email": "jane.smith@microsoft.com",
                    "email_status": "valid",
                    "valid_email": "jane.smith@microsoft.com",
                },
            ],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await client.find_company_emails(domain="microsoft.com")

            assert len(results) == 2
            assert all(isinstance(r, EmailResult) for r in results)
            assert results[0].email == "john.doe@microsoft.com"
            assert results[1].email == "jane.smith@microsoft.com"

    @pytest.mark.asyncio
    async def test_find_company_emails_with_limit(self, client: AnymailfinderClient) -> None:
        """Should include limit parameter."""
        mock_response = {"domain": "example.com", "emails": []}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.find_company_emails(domain="example.com", limit=10)

            mock_post.assert_called_once_with(
                "/find-email/company",
                json={"domain": "example.com", "limit": 10},
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_find_company_emails_empty_result(self, client: AnymailfinderClient) -> None:
        """Should handle empty results."""
        mock_response = {"domain": "unknown.com", "emails": []}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await client.find_company_emails(domain="unknown.com")

            assert results == []


class TestVerifyEmail:
    """Tests for verify_email method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_valid(self, client: AnymailfinderClient) -> None:
        """Should verify valid email."""
        mock_response = {"email_status": "valid"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.verify_email("test@example.com")

            assert isinstance(result, VerificationResult)
            assert result.email == "test@example.com"
            assert result.email_status == EmailStatus.VALID
            assert result.is_valid is True
            assert result.is_deliverable is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid(self, client: AnymailfinderClient) -> None:
        """Should handle invalid email."""
        mock_response = {"email_status": "invalid"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.verify_email("invalid@nonexistent.com")

            assert result.email_status == EmailStatus.INVALID
            assert result.is_valid is False
            assert result.is_deliverable is False

    @pytest.mark.asyncio
    async def test_verify_email_risky(self, client: AnymailfinderClient) -> None:
        """Should handle risky email (catch-all)."""
        mock_response = {"email_status": "risky"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.verify_email("catchall@company.com")

            assert result.email_status == EmailStatus.RISKY
            assert result.is_valid is False
            assert result.is_deliverable is True


class TestGetAccountInfo:
    """Tests for get_account_info method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, client: AnymailfinderClient) -> None:
        """Should get account info."""
        mock_response = {
            "email": "user@company.com",
            "credits_remaining": 1000,
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            account = await client.get_account_info()

            assert account.email == "user@company.com"
            assert account.credits_remaining == 1000

            mock_get.assert_called_once_with("/account")


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: AnymailfinderClient) -> None:
        """Should return healthy status when API works."""
        mock_response = {
            "email": "user@company.com",
            "credits_remaining": 100,
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            health = await client.health_check()

            assert health["name"] == "anymailfinder"
            assert health["healthy"] is True
            assert health["credits_remaining"] == 100
            assert health["api_version"] == "v5.1"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: AnymailfinderClient) -> None:
        """Should return unhealthy status on error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            health = await client.health_check()

            assert health["name"] == "anymailfinder"
            assert health["healthy"] is False
            assert "error" in health


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error(self, client: AnymailfinderClient) -> None:
        """Should raise AnymailfinderError on 401."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = AuthenticationError(
                message="Invalid API key",
                response_data={"error": "Unauthorized"},
            )

            with pytest.raises(AnymailfinderError) as exc_info:
                await client.find_person_email(
                    first_name="John",
                    last_name="Doe",
                    domain="example.com",
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_payment_required_error(self, client: AnymailfinderClient) -> None:
        """Should raise AnymailfinderError on 402."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = PaymentRequiredError(
                message="Insufficient credits",
            )

            with pytest.raises(AnymailfinderError) as exc_info:
                await client.find_person_email(
                    first_name="John",
                    last_name="Doe",
                    domain="example.com",
                )

            assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client: AnymailfinderClient) -> None:
        """Should raise AnymailfinderError on 429."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RateLimitError(
                message="Rate limit exceeded",
                retry_after=60,
            )

            with pytest.raises(AnymailfinderError):
                await client.verify_email("test@example.com")


class TestCallEndpoint:
    """Tests for call_endpoint method."""

    @pytest.fixture
    def client(self) -> AnymailfinderClient:
        """Create client for testing."""
        return AnymailfinderClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: AnymailfinderClient) -> None:
        """Should make GET request to custom endpoint."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint("/custom-endpoint")

            assert result == {"data": "test"}
            mock_request.assert_called_once_with("GET", "/custom-endpoint")

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: AnymailfinderClient) -> None:
        """Should make POST request to custom endpoint."""
        mock_response = {"created": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint(
                "/new-feature",
                method="POST",
                json={"param": "value"},
            )

            assert result == {"created": True}
            mock_request.assert_called_once_with("POST", "/new-feature", json={"param": "value"})


class TestAsyncContextManager:
    """Tests for async context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close client on exit."""
        async with AnymailfinderClient(
            api_key="test-key"  # pragma: allowlist secret
        ) as client:
            # Force client creation
            _ = client.client
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None or client._client.is_closed


class TestEmailResultProperties:
    """Tests for EmailResult dataclass properties."""

    def test_is_valid_true_for_valid_status(self) -> None:
        """is_valid should be True for valid status."""
        result = EmailResult(
            email="test@example.com",
            email_status=EmailStatus.VALID,
            valid_email="test@example.com",
            raw_response={},
        )
        assert result.is_valid is True

    def test_is_valid_false_for_other_statuses(self) -> None:
        """is_valid should be False for non-valid statuses."""
        for status in [EmailStatus.RISKY, EmailStatus.NOT_FOUND, EmailStatus.BLACKLISTED]:
            result = EmailResult(
                email=None,
                email_status=status,
                valid_email=None,
                raw_response={},
            )
            assert result.is_valid is False

    def test_is_usable_true_for_valid_and_risky(self) -> None:
        """is_usable should be True for valid and risky."""
        for status in [EmailStatus.VALID, EmailStatus.RISKY]:
            result = EmailResult(
                email="test@example.com",
                email_status=status,
                valid_email=None,
                raw_response={},
            )
            assert result.is_usable is True

    def test_is_usable_false_for_not_found(self) -> None:
        """is_usable should be False for not_found."""
        result = EmailResult(
            email=None,
            email_status=EmailStatus.NOT_FOUND,
            valid_email=None,
            raw_response={},
        )
        assert result.is_usable is False


class TestVerificationResultProperties:
    """Tests for VerificationResult dataclass properties."""

    def test_is_valid_true_for_valid_status(self) -> None:
        """is_valid should be True for valid status."""
        result = VerificationResult(
            email="test@example.com",
            email_status=EmailStatus.VALID,
            raw_response={},
        )
        assert result.is_valid is True

    def test_is_deliverable_true_for_valid_and_risky(self) -> None:
        """is_deliverable should be True for valid and risky."""
        for status in [EmailStatus.VALID, EmailStatus.RISKY]:
            result = VerificationResult(
                email="test@example.com",
                email_status=status,
                raw_response={},
            )
            assert result.is_deliverable is True

    def test_is_deliverable_false_for_invalid(self) -> None:
        """is_deliverable should be False for invalid."""
        result = VerificationResult(
            email="test@example.com",
            email_status=EmailStatus.INVALID,
            raw_response={},
        )
        assert result.is_deliverable is False
