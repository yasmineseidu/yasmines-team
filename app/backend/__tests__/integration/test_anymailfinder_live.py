"""
Live API tests for Anymailfinder integration.

These tests use real API keys from .env and make actual API calls.
Run with: pytest __tests__/integration/test_anymailfinder_live.py -v -m live_api

Requirements:
- ANYMAILFINDER_API_KEY must be set in .env at project root
- Tests consume real API credits (only 1 credit for valid emails)

Note: These tests are skipped if API key is not configured.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations import (
    AnymailfinderClient,
    AnymailfinderError,
    EmailResult,
    EmailStatus,
    VerificationResult,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")

# Get API key
API_KEY = os.getenv("ANYMAILFINDER_API_KEY", "")

# Skip all tests if API key is not configured or is placeholder
skip_if_no_api_key = pytest.mark.skipif(
    not API_KEY or API_KEY == "..." or API_KEY.startswith("..."),
    reason="ANYMAILFINDER_API_KEY not configured in .env",
)


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    if not API_KEY or API_KEY == "..." or API_KEY.startswith("..."):
        pytest.skip("ANYMAILFINDER_API_KEY not configured")
    return API_KEY


@pytest.fixture
async def client(api_key: str) -> AnymailfinderClient:
    """Create client with real API key."""
    async with AnymailfinderClient(api_key=api_key) as c:
        yield c


# Sample data for testing
SAMPLE_PERSON_SEARCH = {
    "first_name": "Satya",
    "last_name": "Nadella",
    "domain": "microsoft.com",
}

SAMPLE_COMPANY_SEARCH = {
    "domain": "microsoft.com",
}

SAMPLE_EMAIL_TO_VERIFY = "satya@microsoft.com"


@pytest.mark.live_api
@skip_if_no_api_key
class TestAnymailfinderLiveAPI:
    """Live API tests with real API keys."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, client: AnymailfinderClient) -> None:
        """Test getting account info - verifies API key works."""
        account = await client.get_account_info()

        assert account.email is not None
        assert isinstance(account.credits_remaining, int)
        assert account.credits_remaining >= 0

    @pytest.mark.asyncio
    async def test_health_check(self, client: AnymailfinderClient) -> None:
        """Test health check - verifies API connectivity."""
        health = await client.health_check()

        assert health["name"] == "anymailfinder"
        assert health["healthy"] is True
        assert "credits_remaining" in health
        assert health["api_version"] == "v5.1"

    @pytest.mark.asyncio
    async def test_find_person_email(self, client: AnymailfinderClient) -> None:
        """Test finding a person's email - uses 1 credit if found."""
        result = await client.find_person_email(
            first_name=SAMPLE_PERSON_SEARCH["first_name"],
            last_name=SAMPLE_PERSON_SEARCH["last_name"],
            domain=SAMPLE_PERSON_SEARCH["domain"],
        )

        assert isinstance(result, EmailResult)
        assert result.email_status in [
            EmailStatus.VALID,
            EmailStatus.RISKY,
            EmailStatus.NOT_FOUND,
            EmailStatus.BLACKLISTED,
        ]

        # Log result for debugging
        print(f"\nEmail found: {result.email}")
        print(f"Status: {result.email_status}")
        print(f"Is usable: {result.is_usable}")

    @pytest.mark.asyncio
    async def test_find_person_email_with_full_name(self, client: AnymailfinderClient) -> None:
        """Test finding email with full name instead of first/last."""
        result = await client.find_person_email(
            full_name="Satya Nadella",
            domain="microsoft.com",
        )

        assert isinstance(result, EmailResult)
        assert result.email_status in [
            EmailStatus.VALID,
            EmailStatus.RISKY,
            EmailStatus.NOT_FOUND,
            EmailStatus.BLACKLISTED,
        ]

    @pytest.mark.asyncio
    async def test_verify_email(self, client: AnymailfinderClient) -> None:
        """Test email verification - uses 0.2 credits."""
        result = await client.verify_email(SAMPLE_EMAIL_TO_VERIFY)

        assert isinstance(result, VerificationResult)
        assert result.email == SAMPLE_EMAIL_TO_VERIFY
        assert result.email_status in [
            EmailStatus.VALID,
            EmailStatus.RISKY,
            EmailStatus.INVALID,
        ]

        # Log result for debugging
        print(f"\nEmail verified: {result.email}")
        print(f"Status: {result.email_status}")
        print(f"Is deliverable: {result.is_deliverable}")

    @pytest.mark.asyncio
    async def test_find_person_email_not_found(self, client: AnymailfinderClient) -> None:
        """Test with unlikely person - should return not_found (free)."""
        result = await client.find_person_email(
            first_name="Zzzznonexistent",
            last_name="Personthatdoesnotexist",
            domain="microsofttestnonexistent123456.com",
        )

        assert isinstance(result, EmailResult)
        # Should be not_found for non-existent domain
        # Note: This won't consume credits

    @pytest.mark.asyncio
    async def test_call_endpoint_dynamic(self, client: AnymailfinderClient) -> None:
        """Test calling endpoint dynamically for future-proofing."""
        # Use account endpoint as it's lightweight
        result = await client.call_endpoint("/account", method="GET")

        assert isinstance(result, dict)
        assert "email" in result or "credits_remaining" in result

    @pytest.mark.asyncio
    async def test_error_handling_invalid_api_key(self) -> None:
        """Test error handling with invalid API key."""
        async with AnymailfinderClient(
            api_key="invalid-key"  # pragma: allowlist secret
        ) as bad_client:
            with pytest.raises(AnymailfinderError) as exc_info:
                await bad_client.get_account_info()

            assert exc_info.value.status_code in [401, 403, None]


@pytest.mark.live_api
@skip_if_no_api_key
class TestAnymailfinderResponseSchemas:
    """Tests to verify response schemas match API documentation."""

    @pytest.mark.asyncio
    async def test_find_person_email_response_schema(self, client: AnymailfinderClient) -> None:
        """Verify find_person_email response matches expected schema."""
        result = await client.find_person_email(
            first_name="John",
            last_name="Doe",
            domain="example.com",
        )

        # Verify EmailResult structure
        assert hasattr(result, "email")
        assert hasattr(result, "email_status")
        assert hasattr(result, "valid_email")
        assert hasattr(result, "raw_response")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_usable")

        # Verify raw_response contains expected fields
        raw = result.raw_response
        assert "email_status" in raw

    @pytest.mark.asyncio
    async def test_verify_email_response_schema(self, client: AnymailfinderClient) -> None:
        """Verify verify_email response matches expected schema."""
        result = await client.verify_email("test@example.com")

        # Verify VerificationResult structure
        assert hasattr(result, "email")
        assert hasattr(result, "email_status")
        assert hasattr(result, "raw_response")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_deliverable")

    @pytest.mark.asyncio
    async def test_account_info_response_schema(self, client: AnymailfinderClient) -> None:
        """Verify get_account_info response matches expected schema."""
        account = await client.get_account_info()

        # Verify AccountInfo structure
        assert hasattr(account, "email")
        assert hasattr(account, "credits_remaining")
        assert hasattr(account, "raw_response")

        # Verify types
        assert isinstance(account.email, str)
        assert isinstance(account.credits_remaining, int)
