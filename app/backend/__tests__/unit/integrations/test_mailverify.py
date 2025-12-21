"""Unit tests for MailVerify integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.mailverify import (
    MailVerifyBulkResult,
    MailVerifyClient,
    MailVerifyResult,
    MailVerifyStatus,
)


class TestMailVerifyClientInitialization:
    """Tests for MailVerifyClient initialization."""

    def test_client_initializes_with_api_key(self) -> None:
        """Client should initialize with API key."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_client_uses_correct_base_url(self) -> None:
        """Client should use correct MailVerify API base URL."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.mailverify.ai/v1"

    def test_client_default_timeout(self) -> None:
        """Client should have default timeout of 30 seconds."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 30.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = MailVerifyClient(api_key="test-key", timeout=60.0)  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_name(self) -> None:
        """Client should have correct name."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "mailverify"


class TestMailVerifyClientHeaders:
    """Tests for MailVerifyClient headers."""

    def test_headers_include_api_key(self) -> None:
        """Headers should include X-API-Key."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["X-API-Key"] == "test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include correct Content-Type."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestVerifyEmail:
    """Tests for MailVerifyClient.verify_email()."""

    @pytest.fixture
    def client(self) -> MailVerifyClient:
        """Create client fixture."""
        return MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_valid(self, client: MailVerifyClient) -> None:
        """verify_email should return valid result."""
        mock_response = {
            "status": "valid",
            "valid": True,
            "deliverable": True,
            "catch_all": False,
            "disposable": False,
            "spam_trap": False,
            "domain": "company.com",
            "mx_records": ["mx1.company.com", "mx2.company.com"],
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("john@company.com")

            assert result.is_valid is True
            assert result.is_deliverable is True
            assert result.status == MailVerifyStatus.VALID
            assert result.is_safe_to_send is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid(self, client: MailVerifyClient) -> None:
        """verify_email should return invalid result."""
        mock_response = {
            "status": "invalid",
            "valid": False,
            "deliverable": False,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("fake@invalid.com")

            assert result.is_valid is False
            assert result.is_deliverable is False
            assert result.status == MailVerifyStatus.INVALID

    @pytest.mark.asyncio
    async def test_verify_email_disposable(self, client: MailVerifyClient) -> None:
        """verify_email should detect disposable email."""
        mock_response = {
            "status": "disposable",
            "valid": True,
            "deliverable": True,
            "disposable": True,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("temp@tempmail.com")

            assert result.is_disposable is True
            assert result.is_safe_to_send is False

    @pytest.mark.asyncio
    async def test_verify_email_spam_trap(self, client: MailVerifyClient) -> None:
        """verify_email should detect spam trap."""
        mock_response = {
            "status": "spam_trap",
            "valid": True,
            "deliverable": True,
            "spam_trap": True,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("trap@spamtrap.com")

            assert result.is_spam_trap is True
            assert result.is_safe_to_send is False

    @pytest.mark.asyncio
    async def test_verify_email_catch_all(self, client: MailVerifyClient) -> None:
        """verify_email should detect catch-all domain."""
        mock_response = {
            "status": "catch_all",
            "valid": True,
            "deliverable": True,
            "catch_all": True,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("any@catchall.com")

            assert result.is_catch_all is True
            assert result.is_risky is True

    @pytest.mark.asyncio
    async def test_verify_email_raises_on_empty(self, client: MailVerifyClient) -> None:
        """verify_email should raise ValueError for empty email."""
        with pytest.raises(ValueError, match="email is required"):
            await client.verify_email("")

    @pytest.mark.asyncio
    async def test_verify_email_raises_on_invalid_format(self, client: MailVerifyClient) -> None:
        """verify_email should raise ValueError for invalid email format."""
        with pytest.raises(ValueError, match="Invalid email format"):
            await client.verify_email("not-an-email")

    @pytest.mark.asyncio
    async def test_verify_email_normalizes_email(self, client: MailVerifyClient) -> None:
        """verify_email should normalize email to lowercase."""
        mock_response = {"status": "valid", "valid": True, "deliverable": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_email("  JOHN@Company.COM  ")

            assert result.email == "john@company.com"


class TestVerifyBulk:
    """Tests for MailVerifyClient.verify_bulk()."""

    @pytest.fixture
    def client(self) -> MailVerifyClient:
        """Create client fixture."""
        return MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_bulk_success(self, client: MailVerifyClient) -> None:
        """verify_bulk should return bulk result."""
        mock_response = {
            "job_id": "bulk-123",
            "status": "completed",
            "total": 2,
            "processed": 2,
            "valid_count": 1,
            "invalid_count": 1,
            "risky_count": 0,
            "results": [
                {"email": "john@company.com", "status": "valid", "valid": True},
                {"email": "fake@invalid.com", "status": "invalid", "valid": False},
            ],
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_bulk(["john@company.com", "fake@invalid.com"])

            assert result.job_id == "bulk-123"
            assert result.total_emails == 2
            assert result.valid_count == 1
            assert result.is_complete is True
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_verify_bulk_with_webhook(self, client: MailVerifyClient) -> None:
        """verify_bulk should accept webhook URL."""
        mock_response = {
            "job_id": "bulk-456",
            "status": "processing",
            "total": 5,
            "processed": 0,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.verify_bulk(
                ["test@example.com"] * 5,
                webhook_url="https://example.com/webhook",
            )

            assert result.job_id == "bulk-456"
            assert result.status == "processing"

    @pytest.mark.asyncio
    async def test_verify_bulk_raises_on_empty(self, client: MailVerifyClient) -> None:
        """verify_bulk should raise ValueError for empty list."""
        with pytest.raises(ValueError, match="emails list is required"):
            await client.verify_bulk([])

    @pytest.mark.asyncio
    async def test_verify_bulk_filters_invalid_emails(self, client: MailVerifyClient) -> None:
        """verify_bulk should filter out invalid email formats."""
        with pytest.raises(ValueError, match="No valid emails provided"):
            await client.verify_bulk(["not-an-email", "also-not-email"])


class TestGetBulkStatus:
    """Tests for MailVerifyClient.get_bulk_status()."""

    @pytest.fixture
    def client(self) -> MailVerifyClient:
        """Create client fixture."""
        return MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_bulk_status_success(self, client: MailVerifyClient) -> None:
        """get_bulk_status should return job status."""
        mock_response = {
            "job_id": "bulk-123",
            "status": "completed",
            "total": 10,
            "processed": 10,
            "valid_count": 8,
            "invalid_count": 2,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.get_bulk_status("bulk-123")

            assert result.job_id == "bulk-123"
            assert result.is_complete is True
            assert result.valid_rate == 0.8

    @pytest.mark.asyncio
    async def test_get_bulk_status_raises_on_missing_id(self, client: MailVerifyClient) -> None:
        """get_bulk_status should raise ValueError if job_id missing."""
        with pytest.raises(ValueError, match="job_id is required"):
            await client.get_bulk_status("")


class TestCheckDomain:
    """Tests for MailVerifyClient.check_domain()."""

    @pytest.fixture
    def client(self) -> MailVerifyClient:
        """Create client fixture."""
        return MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_check_domain_success(self, client: MailVerifyClient) -> None:
        """check_domain should return domain info."""
        mock_response = {
            "domain": "company.com",
            "has_mx": True,
            "mx_records": ["mx1.company.com"],
            "is_catch_all": False,
        }

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.check_domain("company.com")

            assert result["domain"] == "company.com"
            assert result["has_mx"] is True

    @pytest.mark.asyncio
    async def test_check_domain_raises_on_empty(self, client: MailVerifyClient) -> None:
        """check_domain should raise ValueError for empty domain."""
        with pytest.raises(ValueError, match="domain is required"):
            await client.check_domain("")

    @pytest.mark.asyncio
    async def test_check_domain_raises_on_invalid_format(self, client: MailVerifyClient) -> None:
        """check_domain should raise ValueError for invalid domain."""
        with pytest.raises(ValueError, match="Invalid domain format"):
            await client.check_domain("nodot")


class TestHealthCheck:
    """Tests for MailVerifyClient.health_check()."""

    @pytest.fixture
    def client(self) -> MailVerifyClient:
        """Create client fixture."""
        return MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: MailVerifyClient) -> None:
        """health_check should return healthy status."""
        result = await client.health_check()

        assert result["healthy"] is True
        assert result["name"] == "mailverify"
        assert result["base_url"] == "https://api.mailverify.ai/v1"


class TestMailVerifyResultProperties:
    """Tests for MailVerifyResult properties."""

    def test_is_safe_to_send_true(self) -> None:
        """is_safe_to_send should be True for valid, deliverable email."""
        result = MailVerifyResult(
            email="test@company.com",
            status=MailVerifyStatus.VALID,
            is_valid=True,
            is_deliverable=True,
            is_catch_all=False,
            is_disposable=False,
            is_spam_trap=False,
            domain="company.com",
            mx_records=["mx.company.com"],
            raw_response={},
        )
        assert result.is_safe_to_send is True

    def test_is_safe_to_send_false_disposable(self) -> None:
        """is_safe_to_send should be False for disposable email."""
        result = MailVerifyResult(
            email="test@tempmail.com",
            status=MailVerifyStatus.DISPOSABLE,
            is_valid=True,
            is_deliverable=True,
            is_catch_all=False,
            is_disposable=True,
            is_spam_trap=False,
            domain="tempmail.com",
            mx_records=[],
            raw_response={},
        )
        assert result.is_safe_to_send is False

    def test_is_safe_to_send_false_spam_trap(self) -> None:
        """is_safe_to_send should be False for spam trap."""
        result = MailVerifyResult(
            email="trap@spamtrap.com",
            status=MailVerifyStatus.SPAM_TRAP,
            is_valid=True,
            is_deliverable=True,
            is_catch_all=False,
            is_disposable=False,
            is_spam_trap=True,
            domain="spamtrap.com",
            mx_records=[],
            raw_response={},
        )
        assert result.is_safe_to_send is False

    def test_is_risky_true_catch_all(self) -> None:
        """is_risky should be True for catch-all domain."""
        result = MailVerifyResult(
            email="any@catchall.com",
            status=MailVerifyStatus.VALID,
            is_valid=True,
            is_deliverable=True,
            is_catch_all=True,
            is_disposable=False,
            is_spam_trap=False,
            domain="catchall.com",
            mx_records=[],
            raw_response={},
        )
        assert result.is_risky is True

    def test_is_risky_true_risky_status(self) -> None:
        """is_risky should be True for risky status."""
        result = MailVerifyResult(
            email="test@risky.com",
            status=MailVerifyStatus.RISKY,
            is_valid=True,
            is_deliverable=True,
            is_catch_all=False,
            is_disposable=False,
            is_spam_trap=False,
            domain="risky.com",
            mx_records=[],
            raw_response={},
        )
        assert result.is_risky is True


class TestMailVerifyBulkResultProperties:
    """Tests for MailVerifyBulkResult properties."""

    def test_is_complete_true(self) -> None:
        """is_complete should be True when processed equals total."""
        result = MailVerifyBulkResult(
            job_id="123",
            status="completed",
            total_emails=10,
            processed=10,
            valid_count=8,
            invalid_count=2,
            risky_count=0,
            results=[],
            raw_response={},
        )
        assert result.is_complete is True

    def test_is_complete_false(self) -> None:
        """is_complete should be False when still processing."""
        result = MailVerifyBulkResult(
            job_id="123",
            status="processing",
            total_emails=10,
            processed=5,
            valid_count=4,
            invalid_count=1,
            risky_count=0,
            results=[],
            raw_response={},
        )
        assert result.is_complete is False

    def test_valid_rate_calculation(self) -> None:
        """valid_rate should calculate correct percentage."""
        result = MailVerifyBulkResult(
            job_id="123",
            status="completed",
            total_emails=100,
            processed=100,
            valid_count=75,
            invalid_count=25,
            risky_count=0,
            results=[],
            raw_response={},
        )
        assert result.valid_rate == 0.75

    def test_valid_rate_zero_division(self) -> None:
        """valid_rate should handle zero total emails."""
        result = MailVerifyBulkResult(
            job_id="123",
            status="completed",
            total_emails=0,
            processed=0,
            valid_count=0,
            invalid_count=0,
            risky_count=0,
            results=[],
            raw_response={},
        )
        assert result.valid_rate == 0.0


class TestMailVerifyStatus:
    """Tests for MailVerifyStatus enum."""

    def test_status_values(self) -> None:
        """Should have all expected status values."""
        assert MailVerifyStatus.VALID == "valid"
        assert MailVerifyStatus.INVALID == "invalid"
        assert MailVerifyStatus.RISKY == "risky"
        assert MailVerifyStatus.UNKNOWN == "unknown"
        assert MailVerifyStatus.CATCH_ALL == "catch_all"
        assert MailVerifyStatus.DISPOSABLE == "disposable"
        assert MailVerifyStatus.SPAM_TRAP == "spam_trap"


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        client = MailVerifyClient(api_key="test-key")  # pragma: allowlist secret

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass
            mock_close.assert_called_once()
