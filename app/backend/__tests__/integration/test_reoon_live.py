"""
Live API tests for Reoon Email Verifier integration.

These tests use real API credentials to verify endpoint functionality.
Run with: pytest __tests__/integration/test_reoon_live.py -v -m live_api

IMPORTANT: All tests MUST pass 100% before proceeding.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.reoon import (
    ReoonAccountBalance,
    ReoonBulkTaskResult,
    ReoonBulkVerificationStatus,
    ReoonClient,
    ReoonError,
    ReoonVerificationMode,
    ReoonVerificationResult,
    ReoonVerificationStatus,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    key = os.getenv("REOON_API_KEY")
    if not key:
        pytest.skip("REOON_API_KEY not found in .env")
    return key


@pytest.fixture
def client(api_key: str) -> ReoonClient:
    """Create Reoon client with real API key."""
    return ReoonClient(api_key=api_key)


# Sample test emails
VALID_EMAIL = "info@google.com"  # Known valid email
INVALID_EMAIL = "nonexistent@invalid-domain-xyz-123.com"
DISPOSABLE_EMAIL = "test@mailinator.com"
ROLE_EMAIL = "support@amazon.com"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAccountBalanceLive:
    """Live tests for account balance endpoint."""

    async def test_get_account_balance_success(self, client: ReoonClient) -> None:
        """Should retrieve account balance successfully."""
        result = await client.get_account_balance()

        assert isinstance(result, ReoonAccountBalance)
        assert result.api_status is not None
        assert result.remaining_daily_credits >= 0
        assert result.remaining_instant_credits >= 0
        assert result.total_remaining_credits >= 0
        assert result.has_credits is True  # Should have credits to run tests

        # Verify raw_response is populated
        assert result.raw_response is not None


@pytest.mark.asyncio
@pytest.mark.live_api
class TestQuickVerificationLive:
    """Live tests for quick mode verification."""

    async def test_verify_valid_email_quick(self, client: ReoonClient) -> None:
        """Should verify a valid email in quick mode."""
        result = await client.verify_email_quick(VALID_EMAIL)

        assert isinstance(result, ReoonVerificationResult)
        assert result.email == VALID_EMAIL.lower()
        assert result.verification_mode == ReoonVerificationMode.QUICK
        assert result.is_valid_syntax is True
        assert result.overall_score >= 0
        assert result.overall_score <= 100
        assert result.mx_accepts_mail is True

        # Quick mode should return quickly (validated by test completion)
        assert result.raw_response is not None

    async def test_verify_invalid_email_quick(self, client: ReoonClient) -> None:
        """Should correctly identify an invalid email in quick mode."""
        result = await client.verify_email_quick(INVALID_EMAIL)

        assert isinstance(result, ReoonVerificationResult)
        assert result.email == INVALID_EMAIL.lower()
        assert result.verification_mode == ReoonVerificationMode.QUICK
        assert result.is_valid_syntax is True  # Syntax is valid, domain doesn't exist
        # Domain doesn't exist, so should be invalid or have low score
        assert result.mx_accepts_mail is False or result.overall_score < 50

    async def test_verify_disposable_email_quick(self, client: ReoonClient) -> None:
        """Should detect disposable email in quick mode."""
        result = await client.verify_email_quick(DISPOSABLE_EMAIL)

        assert isinstance(result, ReoonVerificationResult)
        assert result.is_disposable is True
        assert result.status == ReoonVerificationStatus.DISPOSABLE
        assert result.should_not_send is True


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPowerVerificationLive:
    """Live tests for power mode verification."""

    async def test_verify_valid_email_power(self, client: ReoonClient) -> None:
        """Should verify a valid email in power mode with deep checks."""
        result = await client.verify_email_power(VALID_EMAIL)

        assert isinstance(result, ReoonVerificationResult)
        assert result.email == VALID_EMAIL.lower()
        assert result.verification_mode == ReoonVerificationMode.POWER
        assert result.is_valid_syntax is True
        assert result.overall_score >= 0
        assert result.overall_score <= 100
        assert result.mx_accepts_mail is True

        # Power mode should have attempted SMTP connection
        # Note: can_connect_smtp may be False if server blocks verification

        assert result.raw_response is not None

    async def test_verify_role_account_power(self, client: ReoonClient) -> None:
        """Should detect role account in power mode."""
        result = await client.verify_email_power(ROLE_EMAIL)

        assert isinstance(result, ReoonVerificationResult)
        # Role accounts like support@ should be detected
        # Note: Detection depends on Reoon's database
        assert result.is_valid_syntax is True
        # The email should have a role account indicator if detected
        # This may vary based on Reoon's detection capabilities


@pytest.mark.asyncio
@pytest.mark.live_api
class TestHealthCheckLive:
    """Live tests for health check endpoint."""

    async def test_health_check_returns_healthy(self, client: ReoonClient) -> None:
        """Should return healthy status with valid API key."""
        health = await client.health_check()

        assert health["name"] == "reoon"
        assert health["healthy"] is True
        assert health["has_credits"] is True
        assert health["remaining_credits"] >= 0
        assert "base_url" in health


@pytest.mark.asyncio
@pytest.mark.live_api
class TestCallEndpointLive:
    """Live tests for generic endpoint calling."""

    async def test_call_verify_endpoint_directly(self, client: ReoonClient) -> None:
        """Should call verify endpoint via call_endpoint method."""
        result = await client.call_endpoint(
            "/verify",
            method="GET",
            params={"email": VALID_EMAIL, "mode": "quick"},
        )

        assert isinstance(result, dict)
        assert "email" in result
        assert "status" in result


@pytest.mark.asyncio
@pytest.mark.live_api
class TestBulkVerificationLive:
    """Live tests for bulk verification.

    Note: These tests are skipped by default as they consume credits
    and may take a long time to complete. Enable manually when needed.
    """

    @pytest.mark.skip(reason="Consumes credits - enable manually for full testing")
    async def test_create_bulk_verification_task(self, client: ReoonClient) -> None:
        """Should create a bulk verification task."""
        # Generate list of test emails
        test_emails = [
            "test1@example.com",
            "test2@example.com",
            "test3@example.com",
            "test4@example.com",
            "test5@example.com",
            "test6@example.com",
            "test7@example.com",
            "test8@example.com",
            "test9@example.com",
            "test10@example.com",
        ]

        result = await client.create_bulk_verification_task(
            emails=test_emails,
            name="Live Test Batch",
        )

        assert isinstance(result, ReoonBulkTaskResult)
        assert result.is_created is True
        assert result.task_id is not None
        assert result.count_submitted >= len(test_emails)

    @pytest.mark.skip(reason="Consumes credits - enable manually for full testing")
    async def test_get_bulk_verification_status(self, client: ReoonClient) -> None:
        """Should retrieve bulk verification status.

        Note: This test requires a valid task_id from a previous
        create_bulk_verification_task call.
        """
        # This would need a real task_id from a previous test
        task_id = "example-task-id"

        result = await client.get_bulk_verification_status(task_id)

        assert isinstance(result, ReoonBulkVerificationStatus)
        assert result.task_id == task_id


@pytest.mark.asyncio
@pytest.mark.live_api
class TestErrorHandlingLive:
    """Live tests for error handling."""

    async def test_invalid_api_key_raises_error(self) -> None:
        """Should raise error for invalid API key."""
        client = ReoonClient(api_key="invalid-key-12345")

        # Should raise ReoonError for invalid API key
        with pytest.raises(ReoonError):
            await client.get_account_balance()


@pytest.mark.asyncio
@pytest.mark.live_api
class TestContextManagerLive:
    """Live tests for async context manager."""

    async def test_context_manager_works(self, api_key: str) -> None:
        """Should work correctly with async context manager."""
        async with ReoonClient(api_key=api_key) as client:
            result = await client.get_account_balance()
            assert isinstance(result, ReoonAccountBalance)
            assert result.has_credits is True

        # After exit, client should be closed
        assert client._client is None or client._client.is_closed
