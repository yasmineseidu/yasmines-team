"""
Unit tests for Reoon Email Verifier integration client.

Tests cover:
- Client initialization
- Single email verification (Quick and Power modes)
- Bulk verification task creation and status
- Account balance checking
- Error handling (401, 402, 429, network errors)
- Health check functionality
- Dataclass properties and computed values

Coverage target: >90%
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations import (
    AuthenticationError,
    PaymentRequiredError,
    RateLimitError,
)
from src.integrations.reoon import (
    ReoonAccountBalance,
    ReoonBulkTaskResult,
    ReoonBulkTaskStatus,
    ReoonBulkVerificationStatus,
    ReoonClient,
    ReoonError,
    ReoonVerificationMode,
    ReoonVerificationResult,
    ReoonVerificationStatus,
)


class TestReoonClientInitialization:
    """Tests for ReoonClient initialization."""

    def test_client_has_correct_name(self) -> None:
        """Client should have 'reoon' as name."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "reoon"

    def test_client_has_correct_base_url(self) -> None:
        """Client should use correct API base URL."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://emailverifier.reoon.com/api/v1"

    def test_client_default_timeout_is_120_seconds(self) -> None:
        """Client should have 120s default timeout for power mode."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 120.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = ReoonClient(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 retries by default."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = ReoonClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = ReoonClient(api_key="my-secret-key")  # pragma: allowlist secret
        assert client.api_key == "my-secret-key"  # pragma: allowlist secret


class TestReoonClientHeaders:
    """Tests for HTTP headers configuration."""

    def test_headers_do_not_include_bearer_token(self) -> None:
        """Headers should NOT include Bearer token (Reoon uses query param)."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert "Authorization" not in headers

    def test_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestAddApiKeyToParams:
    """Tests for API key parameter handling."""

    def test_adds_api_key_to_empty_params(self) -> None:
        """Should add API key to empty params."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        params = client._add_api_key_to_params(None)
        assert params["key"] == "test-key"

    def test_adds_api_key_to_existing_params(self) -> None:
        """Should add API key to existing params."""
        client = ReoonClient(api_key="test-key")  # pragma: allowlist secret
        params = client._add_api_key_to_params({"email": "test@example.com"})
        assert params["key"] == "test-key"
        assert params["email"] == "test@example.com"


class TestVerifyEmailQuick:
    """Tests for verify_email_quick method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_quick_success(self, client: ReoonClient) -> None:
        """Should verify email in quick mode successfully."""
        mock_response = {
            "email": "test@example.com",
            "status": "valid",
            "overall_score": 75,
            "is_safe_to_send": True,
            "is_valid_syntax": True,
            "is_disposable": False,
            "is_role_account": False,
            "can_connect_smtp": False,
            "has_inbox_full": False,
            "is_catch_all": False,
            "is_deliverable": True,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": True,
            "mx_records": ["mx.example.com"],
            "username": "test",
            "domain": "example.com",
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.verify_email_quick("test@example.com")

            assert isinstance(result, ReoonVerificationResult)
            assert result.email == "test@example.com"
            assert result.status == ReoonVerificationStatus.VALID
            assert result.overall_score == 75
            assert result.verification_mode == ReoonVerificationMode.QUICK

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["mode"] == "quick"
            assert call_args[1]["params"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_email_quick_empty_email_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for empty email."""
        with pytest.raises(ValueError, match="email is required"):
            await client.verify_email_quick("")

    @pytest.mark.asyncio
    async def test_verify_email_quick_invalid_format_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for invalid email format."""
        with pytest.raises(ValueError, match="Invalid email format"):
            await client.verify_email_quick("notanemail")


class TestVerifyEmailPower:
    """Tests for verify_email_power method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_verify_email_power_success(self, client: ReoonClient) -> None:
        """Should verify email in power mode successfully."""
        mock_response = {
            "email": "real@company.com",
            "status": "safe",
            "overall_score": 95,
            "is_safe_to_send": True,
            "is_valid_syntax": True,
            "is_disposable": False,
            "is_role_account": False,
            "can_connect_smtp": True,
            "has_inbox_full": False,
            "is_catch_all": False,
            "is_deliverable": True,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": True,
            "mx_records": ["mail.company.com"],
            "username": "real",
            "domain": "company.com",
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.verify_email_power("real@company.com")

            assert isinstance(result, ReoonVerificationResult)
            assert result.email == "real@company.com"
            assert result.status == ReoonVerificationStatus.SAFE
            assert result.overall_score == 95
            assert result.verification_mode == ReoonVerificationMode.POWER
            assert result.can_connect_smtp is True

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["mode"] == "power"

    @pytest.mark.asyncio
    async def test_verify_email_power_disposable(self, client: ReoonClient) -> None:
        """Should correctly identify disposable email."""
        mock_response = {
            "email": "temp@mailinator.com",
            "status": "disposable",
            "overall_score": 10,
            "is_safe_to_send": False,
            "is_valid_syntax": True,
            "is_disposable": True,
            "is_role_account": False,
            "can_connect_smtp": True,
            "has_inbox_full": False,
            "is_catch_all": True,
            "is_deliverable": True,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": True,
            "mx_records": ["mx.mailinator.com"],
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.verify_email_power("temp@mailinator.com")

            assert result.status == ReoonVerificationStatus.DISPOSABLE
            assert result.is_disposable is True
            assert result.should_not_send is True


class TestCreateBulkVerificationTask:
    """Tests for create_bulk_verification_task method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_create_bulk_task_success(self, client: ReoonClient) -> None:
        """Should create bulk verification task successfully."""
        mock_response = {
            "status": "success",
            "task_id": "task-123-abc",
            "count_submitted": 100,
            "count_duplicates_removed": 5,
            "count_rejected_emails": 2,
            "count_processing": 93,
        }

        emails = [f"test{i}@example.com" for i in range(15)]

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.create_bulk_verification_task(
                emails=emails,
                name="Test Batch",
            )

            assert isinstance(result, ReoonBulkTaskResult)
            assert result.task_id == "task-123-abc"
            assert result.count_submitted == 100
            assert result.is_created is True

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "key" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_create_bulk_task_too_few_emails_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for fewer than 10 emails."""
        emails = [f"test{i}@example.com" for i in range(5)]

        with pytest.raises(ValueError, match="at least 10 emails"):
            await client.create_bulk_verification_task(emails=emails)

    @pytest.mark.asyncio
    async def test_create_bulk_task_too_many_emails_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for more than 50,000 emails."""
        emails = [f"test{i}@example.com" for i in range(50001)]

        with pytest.raises(ValueError, match="Maximum 50,000"):
            await client.create_bulk_verification_task(emails=emails)

    @pytest.mark.asyncio
    async def test_create_bulk_task_empty_list_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for empty email list."""
        with pytest.raises(ValueError, match="emails list is required"):
            await client.create_bulk_verification_task(emails=[])

    @pytest.mark.asyncio
    async def test_create_bulk_task_truncates_name(self, client: ReoonClient) -> None:
        """Should truncate name to 25 characters."""
        mock_response = {
            "status": "success",
            "task_id": "task-123",
            "count_submitted": 15,
            "count_duplicates_removed": 0,
            "count_rejected_emails": 0,
            "count_processing": 15,
        }

        emails = [f"test{i}@example.com" for i in range(15)]

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.create_bulk_verification_task(
                emails=emails,
                name="This is a very long task name that exceeds the limit",
            )

            call_args = mock_post.call_args
            assert len(call_args[1]["json"]["name"]) <= 25


class TestGetBulkVerificationStatus:
    """Tests for get_bulk_verification_status method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_status_running(self, client: ReoonClient) -> None:
        """Should get running task status."""
        mock_response = {
            "task_id": "task-123",
            "name": "Test Batch",
            "status": "running",
            "count_total": 100,
            "count_checked": 50,
            "progress_percentage": 50.0,
            "results": {},
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_bulk_verification_status("task-123")

            assert isinstance(result, ReoonBulkVerificationStatus)
            assert result.status == ReoonBulkTaskStatus.RUNNING
            assert result.is_running is True
            assert result.is_completed is False
            assert result.progress_percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_status_completed(self, client: ReoonClient) -> None:
        """Should get completed task status with results."""
        mock_response = {
            "task_id": "task-123",
            "name": "Test Batch",
            "status": "completed",
            "count_total": 100,
            "count_checked": 100,
            "progress_percentage": 100.0,
            "results": {
                "test@example.com": {"status": "safe", "overall_score": 95},
            },
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_bulk_verification_status("task-123")

            assert result.is_completed is True
            assert result.is_running is False
            assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_get_status_empty_task_id_raises(self, client: ReoonClient) -> None:
        """Should raise ValueError for empty task_id."""
        with pytest.raises(ValueError, match="task_id is required"):
            await client.get_bulk_verification_status("")


class TestGetAccountBalance:
    """Tests for get_account_balance method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_balance_success(self, client: ReoonClient) -> None:
        """Should get account balance successfully."""
        mock_response = {
            "api_status": "active",
            "remaining_daily_credits": 500,
            "remaining_instant_credits": 1000,
            "status": "success",
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_account_balance()

            assert isinstance(result, ReoonAccountBalance)
            assert result.remaining_daily_credits == 500
            assert result.remaining_instant_credits == 1000
            assert result.total_remaining_credits == 1500
            assert result.has_credits is True


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: ReoonClient) -> None:
        """Should return healthy status when API works."""
        mock_balance = ReoonAccountBalance(
            remaining_daily_credits=500,
            remaining_instant_credits=1000,
            api_status="active",
        )

        with patch.object(
            client, "get_account_balance", new_callable=AsyncMock
        ) as mock_get_balance:
            mock_get_balance.return_value = mock_balance

            health = await client.health_check()

            assert health["name"] == "reoon"
            assert health["healthy"] is True
            assert health["has_credits"] is True
            assert health["remaining_credits"] == 1500

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: ReoonClient) -> None:
        """Should return unhealthy status on error."""
        with patch.object(
            client, "get_account_balance", new_callable=AsyncMock
        ) as mock_get_balance:
            mock_get_balance.side_effect = Exception("Connection failed")

            health = await client.health_check()

            assert health["name"] == "reoon"
            assert health["healthy"] is False
            assert "error" in health


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error(self, client: ReoonClient) -> None:
        """Should raise ReoonError on 401."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = AuthenticationError(
                message="Invalid API key",
                response_data={"error": "Unauthorized"},
            )

            with pytest.raises(ReoonError) as exc_info:
                await client.verify_email_quick("test@example.com")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_payment_required_error(self, client: ReoonClient) -> None:
        """Should raise ReoonError on 402."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = PaymentRequiredError(
                message="Insufficient credits",
            )

            with pytest.raises(ReoonError) as exc_info:
                await client.verify_email_power("test@example.com")

            assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client: ReoonClient) -> None:
        """Should raise ReoonError on 429."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = RateLimitError(
                message="Rate limit exceeded",
                retry_after=60,
            )

            with pytest.raises(ReoonError):
                await client.verify_email_quick("test@example.com")


class TestCallEndpoint:
    """Tests for call_endpoint method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: ReoonClient) -> None:
        """Should make GET request with API key in params."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint("/custom-endpoint")

            assert result == {"data": "test"}
            call_args = mock_request.call_args
            assert call_args[1]["params"]["key"] == "test-key"

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: ReoonClient) -> None:
        """Should make POST request with API key in body."""
        mock_response = {"created": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint(
                "/new-feature",
                method="POST",
                json={"param": "value"},
            )

            assert result == {"created": True}
            call_args = mock_request.call_args
            assert call_args[1]["json"]["key"] == "test-key"
            assert call_args[1]["json"]["param"] == "value"


class TestAsyncContextManager:
    """Tests for async context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close client on exit."""
        async with ReoonClient(api_key="test-key") as client:  # pragma: allowlist secret
            # Force client creation
            _ = client.client
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None or client._client.is_closed


class TestVerificationResultProperties:
    """Tests for ReoonVerificationResult dataclass properties."""

    def test_is_safe_true_for_safe_status(self) -> None:
        """is_safe should be True for safe status."""
        result = ReoonVerificationResult(
            email="test@example.com",
            status=ReoonVerificationStatus.SAFE,
            overall_score=95,
            is_safe_to_send=True,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=True,
            has_inbox_full=False,
            is_catch_all=False,
            is_deliverable=True,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.example.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.is_safe is True

    def test_is_safe_false_when_not_safe_to_send(self) -> None:
        """is_safe should be False when is_safe_to_send is False."""
        result = ReoonVerificationResult(
            email="test@example.com",
            status=ReoonVerificationStatus.SAFE,
            overall_score=95,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=True,
            has_inbox_full=False,
            is_catch_all=False,
            is_deliverable=True,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.example.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.is_safe is False

    def test_is_risky_for_catch_all(self) -> None:
        """is_risky should be True for catch_all status."""
        result = ReoonVerificationResult(
            email="test@example.com",
            status=ReoonVerificationStatus.CATCH_ALL,
            overall_score=60,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=True,
            has_inbox_full=False,
            is_catch_all=True,
            is_deliverable=True,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.example.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.is_risky is True

    def test_is_risky_for_unknown(self) -> None:
        """is_risky should be True for unknown status."""
        result = ReoonVerificationResult(
            email="test@example.com",
            status=ReoonVerificationStatus.UNKNOWN,
            overall_score=40,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=False,
            has_inbox_full=False,
            is_catch_all=False,
            is_deliverable=False,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.example.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.is_risky is True

    def test_should_not_send_for_invalid(self) -> None:
        """should_not_send should be True for invalid status."""
        result = ReoonVerificationResult(
            email="test@example.com",
            status=ReoonVerificationStatus.INVALID,
            overall_score=0,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=False,
            has_inbox_full=False,
            is_catch_all=False,
            is_deliverable=False,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=False,
            mx_records=[],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.should_not_send is True

    def test_should_not_send_for_disposable(self) -> None:
        """should_not_send should be True for disposable status."""
        result = ReoonVerificationResult(
            email="temp@mailinator.com",
            status=ReoonVerificationStatus.DISPOSABLE,
            overall_score=10,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=True,
            is_role_account=False,
            can_connect_smtp=True,
            has_inbox_full=False,
            is_catch_all=True,
            is_deliverable=True,
            is_disabled=False,
            is_spamtrap=False,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.mailinator.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.should_not_send is True

    def test_should_not_send_for_spamtrap(self) -> None:
        """should_not_send should be True for spamtrap status."""
        result = ReoonVerificationResult(
            email="trap@spamtrap.com",
            status=ReoonVerificationStatus.SPAMTRAP,
            overall_score=0,
            is_safe_to_send=False,
            is_valid_syntax=True,
            is_disposable=False,
            is_role_account=False,
            can_connect_smtp=True,
            has_inbox_full=False,
            is_catch_all=False,
            is_deliverable=True,
            is_disabled=False,
            is_spamtrap=True,
            is_free_email=False,
            mx_accepts_mail=True,
            mx_records=["mx.spamtrap.com"],
            verification_mode=ReoonVerificationMode.POWER,
        )
        assert result.should_not_send is True


class TestAccountBalanceProperties:
    """Tests for ReoonAccountBalance dataclass properties."""

    def test_total_remaining_credits(self) -> None:
        """total_remaining_credits should sum daily and instant credits."""
        balance = ReoonAccountBalance(
            remaining_daily_credits=500,
            remaining_instant_credits=1000,
            api_status="active",
        )
        assert balance.total_remaining_credits == 1500

    def test_has_credits_true(self) -> None:
        """has_credits should be True when credits available."""
        balance = ReoonAccountBalance(
            remaining_daily_credits=500,
            remaining_instant_credits=0,
            api_status="active",
        )
        assert balance.has_credits is True

    def test_has_credits_false(self) -> None:
        """has_credits should be False when no credits."""
        balance = ReoonAccountBalance(
            remaining_daily_credits=0,
            remaining_instant_credits=0,
            api_status="active",
        )
        assert balance.has_credits is False


class TestBulkTaskResultProperties:
    """Tests for ReoonBulkTaskResult dataclass properties."""

    def test_is_created_true(self) -> None:
        """is_created should be True for success status with task_id."""
        result = ReoonBulkTaskResult(
            task_id="task-123",
            status="success",
            count_submitted=100,
            count_duplicates_removed=5,
            count_rejected_emails=0,
            count_processing=95,
        )
        assert result.is_created is True

    def test_is_created_false_no_task_id(self) -> None:
        """is_created should be False when no task_id."""
        result = ReoonBulkTaskResult(
            task_id="",
            status="success",
            count_submitted=100,
            count_duplicates_removed=0,
            count_rejected_emails=100,
            count_processing=0,
        )
        assert result.is_created is False

    def test_is_created_false_error_status(self) -> None:
        """is_created should be False for error status."""
        result = ReoonBulkTaskResult(
            task_id="task-123",
            status="error",
            count_submitted=0,
            count_duplicates_removed=0,
            count_rejected_emails=0,
            count_processing=0,
        )
        assert result.is_created is False


class TestBulkVerificationStatusProperties:
    """Tests for ReoonBulkVerificationStatus dataclass properties."""

    def test_is_completed_true(self) -> None:
        """is_completed should be True for completed status."""
        status = ReoonBulkVerificationStatus(
            task_id="task-123",
            name="Test",
            status=ReoonBulkTaskStatus.COMPLETED,
            count_total=100,
            count_checked=100,
            progress_percentage=100.0,
            results={},
        )
        assert status.is_completed is True

    def test_is_running_for_waiting(self) -> None:
        """is_running should be True for waiting status."""
        status = ReoonBulkVerificationStatus(
            task_id="task-123",
            name="Test",
            status=ReoonBulkTaskStatus.WAITING,
            count_total=100,
            count_checked=0,
            progress_percentage=0.0,
            results={},
        )
        assert status.is_running is True

    def test_is_running_for_running(self) -> None:
        """is_running should be True for running status."""
        status = ReoonBulkVerificationStatus(
            task_id="task-123",
            name="Test",
            status=ReoonBulkTaskStatus.RUNNING,
            count_total=100,
            count_checked=50,
            progress_percentage=50.0,
            results={},
        )
        assert status.is_running is True

    def test_is_failed_for_file_not_found(self) -> None:
        """is_failed should be True for file_not_found status."""
        status = ReoonBulkVerificationStatus(
            task_id="task-123",
            name="Test",
            status=ReoonBulkTaskStatus.FILE_NOT_FOUND,
            count_total=0,
            count_checked=0,
            progress_percentage=0.0,
            results={},
        )
        assert status.is_failed is True

    def test_is_failed_for_error(self) -> None:
        """is_failed should be True for error status."""
        status = ReoonBulkVerificationStatus(
            task_id="task-123",
            name="Test",
            status=ReoonBulkTaskStatus.ERROR,
            count_total=0,
            count_checked=0,
            progress_percentage=0.0,
            results={},
        )
        assert status.is_failed is True


class TestVerificationStatusEnum:
    """Tests for ReoonVerificationStatus enum values."""

    def test_status_values(self) -> None:
        """Status enum should have correct string values."""
        assert ReoonVerificationStatus.SAFE.value == "safe"
        assert ReoonVerificationStatus.VALID.value == "valid"
        assert ReoonVerificationStatus.INVALID.value == "invalid"
        assert ReoonVerificationStatus.DISABLED.value == "disabled"
        assert ReoonVerificationStatus.DISPOSABLE.value == "disposable"
        assert ReoonVerificationStatus.INBOX_FULL.value == "inbox_full"
        assert ReoonVerificationStatus.CATCH_ALL.value == "catch_all"
        assert ReoonVerificationStatus.ROLE_ACCOUNT.value == "role_account"
        assert ReoonVerificationStatus.SPAMTRAP.value == "spamtrap"
        assert ReoonVerificationStatus.UNKNOWN.value == "unknown"


class TestVerificationModeEnum:
    """Tests for ReoonVerificationMode enum values."""

    def test_mode_values(self) -> None:
        """Verification mode enum should have correct string values."""
        assert ReoonVerificationMode.QUICK.value == "quick"
        assert ReoonVerificationMode.POWER.value == "power"


class TestBulkTaskStatusEnum:
    """Tests for ReoonBulkTaskStatus enum values."""

    def test_status_values(self) -> None:
        """Bulk task status enum should have correct string values."""
        assert ReoonBulkTaskStatus.WAITING.value == "waiting"
        assert ReoonBulkTaskStatus.RUNNING.value == "running"
        assert ReoonBulkTaskStatus.COMPLETED.value == "completed"
        assert ReoonBulkTaskStatus.FILE_NOT_FOUND.value == "file_not_found"
        assert ReoonBulkTaskStatus.FILE_LOADING_ERROR.value == "file_loading_error"
        assert ReoonBulkTaskStatus.ERROR.value == "error"


class TestParseVerificationResult:
    """Tests for _parse_verification_result method."""

    @pytest.fixture
    def client(self) -> ReoonClient:
        """Create client for testing."""
        return ReoonClient(api_key="test-key")  # pragma: allowlist secret

    def test_parse_with_string_mx_records(self, client: ReoonClient) -> None:
        """Should handle MX records as string."""
        data = {
            "email": "test@example.com",
            "status": "safe",
            "overall_score": 95,
            "is_safe_to_send": True,
            "is_valid_syntax": True,
            "is_disposable": False,
            "is_role_account": False,
            "can_connect_smtp": True,
            "has_inbox_full": False,
            "is_catch_all": False,
            "is_deliverable": True,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": True,
            "mx_records": "mx.example.com",  # String instead of list
        }

        result = client._parse_verification_result(data, ReoonVerificationMode.POWER)

        assert result.mx_records == ["mx.example.com"]

    def test_parse_with_empty_mx_records(self, client: ReoonClient) -> None:
        """Should handle empty MX records."""
        data = {
            "email": "test@example.com",
            "status": "invalid",
            "overall_score": 0,
            "is_safe_to_send": False,
            "is_valid_syntax": True,
            "is_disposable": False,
            "is_role_account": False,
            "can_connect_smtp": False,
            "has_inbox_full": False,
            "is_catch_all": False,
            "is_deliverable": False,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": False,
            "mx_records": "",  # Empty string
        }

        result = client._parse_verification_result(data, ReoonVerificationMode.POWER)

        assert result.mx_records == []

    def test_parse_with_unknown_status(self, client: ReoonClient) -> None:
        """Should default to UNKNOWN for unrecognized status."""
        data = {
            "email": "test@example.com",
            "status": "some_new_status",  # Unrecognized
            "overall_score": 50,
            "is_safe_to_send": False,
            "is_valid_syntax": True,
            "is_disposable": False,
            "is_role_account": False,
            "can_connect_smtp": False,
            "has_inbox_full": False,
            "is_catch_all": False,
            "is_deliverable": False,
            "is_disabled": False,
            "is_spamtrap": False,
            "is_free_email": False,
            "mx_accepts_mail": True,
            "mx_records": [],
        }

        result = client._parse_verification_result(data, ReoonVerificationMode.QUICK)

        assert result.status == ReoonVerificationStatus.UNKNOWN
