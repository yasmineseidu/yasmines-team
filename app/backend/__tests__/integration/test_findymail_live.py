"""
Live API tests for Findymail integration.

These tests use real API keys from .env and make actual API calls.
Run with: pytest __tests__/integration/test_findymail_live.py -v -m live_api

Requirements:
- FINDYMAIL_API_KEY must be set in .env at project root
- Tests consume real API credits (1 credit per found email)

Note: These tests are skipped if API key is not configured.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations import (
    FindymailClient,
    FindymailEmailResult,
    FindymailEmailStatus,
    FindymailError,
    FindymailVerificationResult,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")

# Get API key
API_KEY = os.getenv("FINDYMAIL_API_KEY", "")

# Skip all tests if API key is not configured or is placeholder
skip_if_no_api_key = pytest.mark.skipif(
    not API_KEY or API_KEY == "..." or API_KEY.startswith("..."),
    reason="FINDYMAIL_API_KEY not configured in .env",
)


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    if not API_KEY or API_KEY == "..." or API_KEY.startswith("..."):
        pytest.skip("FINDYMAIL_API_KEY not configured")
    return API_KEY


@pytest.fixture
async def client(api_key: str) -> FindymailClient:
    """Create client with real API key."""
    async with FindymailClient(api_key=api_key) as c:
        yield c


# Sample data for testing
SAMPLE_TECH_PERSON = {
    "full_name": "Satya Nadella",
    "domain": "microsoft.com",
}

SAMPLE_LINKEDIN_URL = "https://linkedin.com/in/satyanadella"

SAMPLE_EMAIL_TO_VERIFY = "satya@microsoft.com"


@pytest.mark.live_api
@skip_if_no_api_key
class TestFindymailLiveAPI:
    """Live API tests with real API keys."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: FindymailClient) -> None:
        """Test health check - verifies API connectivity."""
        health = await client.health_check()

        assert health["name"] == "findymail"
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_find_work_email(self, client: FindymailClient) -> None:
        """Test finding work email - uses 1 credit if found."""
        result = await client.find_work_email(
            full_name=SAMPLE_TECH_PERSON["full_name"],
            domain=SAMPLE_TECH_PERSON["domain"],
        )

        assert isinstance(result, FindymailEmailResult)
        assert result.status in [
            FindymailEmailStatus.VERIFIED,
            FindymailEmailStatus.VALID,
            FindymailEmailStatus.NOT_FOUND,
            FindymailEmailStatus.CATCH_ALL,
        ]

        # Log result for debugging
        print(f"\nEmail found: {result.email}")
        print(f"Status: {result.status}")
        print(f"Is usable: {result.is_usable}")

    @pytest.mark.asyncio
    async def test_find_email_not_found(self, client: FindymailClient) -> None:
        """Test with unlikely person - should return not_found (free)."""
        result = await client.find_work_email(
            full_name="Zzzznonexistent Personthatdoesnotexist",
            domain="microsofttestnonexistent123456.com",
        )

        assert isinstance(result, FindymailEmailResult)
        # Should be not_found for non-existent domain
        # Note: This won't consume credits

    @pytest.mark.asyncio
    async def test_verify_email(self, client: FindymailClient) -> None:
        """Test email verification - uses 1 credit."""
        result = await client.verify_email(SAMPLE_EMAIL_TO_VERIFY)

        assert isinstance(result, FindymailVerificationResult)
        assert result.email == SAMPLE_EMAIL_TO_VERIFY.lower()
        assert result.status in [
            FindymailEmailStatus.VERIFIED,
            FindymailEmailStatus.VALID,
            FindymailEmailStatus.INVALID,
            FindymailEmailStatus.CATCH_ALL,
        ]

        # Log result for debugging
        print(f"\nEmail verified: {result.email}")
        print(f"Status: {result.status}")
        print(f"Is deliverable: {result.is_deliverable}")

    @pytest.mark.asyncio
    async def test_call_endpoint_dynamic(self, client: FindymailClient) -> None:
        """Test calling endpoint dynamically for future-proofing."""
        # Use verify endpoint as it's lightweight
        result = await client.call_endpoint(
            "/verify",
            method="POST",
            json={"email": "test@example.com"},
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_api_key(self) -> None:
        """Test error handling with invalid API key."""
        async with FindymailClient(
            api_key="invalid-key"  # pragma: allowlist secret
        ) as bad_client:
            with pytest.raises(FindymailError) as exc_info:
                await bad_client.find_work_email(
                    full_name="Test User",
                    domain="test.com",
                )

            assert exc_info.value.status_code in [401, 403, None]


@pytest.mark.live_api
@skip_if_no_api_key
class TestFindymailResponseSchemas:
    """Tests to verify response schemas match API documentation."""

    @pytest.mark.asyncio
    async def test_find_work_email_response_schema(self, client: FindymailClient) -> None:
        """Verify find_work_email response matches expected schema."""
        result = await client.find_work_email(
            full_name="John Doe",
            domain="example.com",
        )

        # Verify FindymailEmailResult structure
        assert hasattr(result, "email")
        assert hasattr(result, "status")
        assert hasattr(result, "first_name")
        assert hasattr(result, "last_name")
        assert hasattr(result, "domain")
        assert hasattr(result, "raw_response")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_usable")

    @pytest.mark.asyncio
    async def test_verify_email_response_schema(self, client: FindymailClient) -> None:
        """Verify verify_email response matches expected schema."""
        result = await client.verify_email("test@example.com")

        # Verify FindymailVerificationResult structure
        assert hasattr(result, "email")
        assert hasattr(result, "status")
        assert hasattr(result, "is_deliverable")
        assert hasattr(result, "is_catch_all")
        assert hasattr(result, "raw_response")
        assert hasattr(result, "is_valid")
