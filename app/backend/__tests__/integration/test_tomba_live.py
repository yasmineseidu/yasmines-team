"""
Live API tests for Tomba integration.

These tests use real API keys from .env and make actual API calls.
Run with: pytest __tests__/integration/test_tomba_live.py -v -m live_api

Requirements:
- TOMBA_API_KEY must be set in .env at project root
- TOMBA_API_SECRET must be set in .env at project root
- Tests consume real API credits

Note: These tests are skipped if API keys are not configured.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations import (
    TombaAccountInfo,
    TombaClient,
    TombaDomainSearchResult,
    TombaEmailCountResult,
    TombaEmailFinderResult,
    TombaError,
    TombaVerificationResult,
    TombaVerificationStatus,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")

# Get API credentials
API_KEY = os.getenv("TOMBA_API_KEY", "")
API_SECRET = os.getenv("TOMBA_API_SECRET", "")

# Skip all tests if API credentials are not configured
skip_if_no_credentials = pytest.mark.skipif(
    not API_KEY or not API_SECRET or API_KEY == "..." or API_SECRET == "...",
    reason="TOMBA_API_KEY and TOMBA_API_SECRET not configured in .env",
)


@pytest.fixture
def api_credentials() -> tuple[str, str]:
    """Get API credentials from environment."""
    if not API_KEY or not API_SECRET or API_KEY == "..." or API_SECRET == "...":
        pytest.skip("TOMBA_API_KEY and TOMBA_API_SECRET not configured")
    return API_KEY, API_SECRET


@pytest.fixture
async def client(api_credentials: tuple[str, str]) -> TombaClient:
    """Create client with real API credentials."""
    api_key, api_secret = api_credentials
    async with TombaClient(api_key=api_key, api_secret=api_secret) as c:
        yield c


# Sample data for testing
SAMPLE_DOMAIN = "stripe.com"
SAMPLE_PERSON = {
    "first_name": "Patrick",
    "last_name": "Collison",
    "domain": "stripe.com",
}
SAMPLE_LINKEDIN_URL = "https://linkedin.com/in/patrickcollison"
SAMPLE_EMAIL_TO_VERIFY = "contact@stripe.com"


@pytest.mark.live_api
@skip_if_no_credentials
class TestTombaLiveAPI:
    """Live API tests with real API keys."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, client: TombaClient) -> None:
        """Test getting account info - verifies API connectivity."""
        result = await client.get_account_info()

        assert isinstance(result, TombaAccountInfo)
        assert result.email  # Should have an email
        print(f"\nAccount: {result.email}")
        print(f"Plan: {result.plan_name}")
        print(f"Searches remaining: {result.search_remaining}")
        print(f"Verifications remaining: {result.verification_remaining}")

    @pytest.mark.asyncio
    async def test_health_check(self, client: TombaClient) -> None:
        """Test health check - verifies API connectivity."""
        health = await client.health_check()

        assert health["name"] == "tomba"
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_email_count(self, client: TombaClient) -> None:
        """Test getting email count for a domain (free operation)."""
        result = await client.get_email_count(SAMPLE_DOMAIN)

        assert isinstance(result, TombaEmailCountResult)
        print(f"\nDomain: {result.domain}")
        print(f"Total emails: {result.total}")
        print(f"Personal: {result.personal_emails}")
        print(f"Generic: {result.generic_emails}")
        print(f"Departments: {result.department}")

    @pytest.mark.asyncio
    async def test_search_domain(self, client: TombaClient) -> None:
        """Test domain search - uses API credits."""
        result = await client.search_domain(SAMPLE_DOMAIN, limit=5)

        assert isinstance(result, TombaDomainSearchResult)
        assert result.domain == SAMPLE_DOMAIN

        print(f"\nOrganization: {result.organization}")
        print(f"Pattern: {result.pattern}")
        print(f"Total results: {result.total_results}")
        print(f"Emails found: {len(result.emails)}")

        for email in result.emails[:3]:
            print(f"  - {email.email} ({email.position})")

    @pytest.mark.asyncio
    async def test_find_email(self, client: TombaClient) -> None:
        """Test email finder - uses API credits."""
        result = await client.find_email(
            domain=SAMPLE_PERSON["domain"],
            first_name=SAMPLE_PERSON["first_name"],
            last_name=SAMPLE_PERSON["last_name"],
        )

        assert isinstance(result, TombaEmailFinderResult)

        print(f"\nEmail: {result.email}")
        print(f"Confidence: {result.confidence}%")
        print(f"Position: {result.position}")
        print(f"High confidence: {result.is_high_confidence}")

    @pytest.mark.asyncio
    async def test_verify_email(self, client: TombaClient) -> None:
        """Test email verification - uses verification credits."""
        result = await client.verify_email(SAMPLE_EMAIL_TO_VERIFY)

        assert isinstance(result, TombaVerificationResult)
        assert result.email == SAMPLE_EMAIL_TO_VERIFY.lower()
        assert result.status in list(TombaVerificationStatus)

        print(f"\nEmail: {result.email}")
        print(f"Status: {result.status.value}")
        print(f"Valid: {result.is_valid}")
        print(f"Risky: {result.is_risky}")
        print(f"MX records: {result.mx_records}")
        print(f"SMTP check: {result.smtp_check}")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_credentials(self) -> None:
        """Test error handling with invalid credentials."""
        async with TombaClient(
            api_key="ta_invalid",  # pragma: allowlist secret
            api_secret="ts_invalid",  # pragma: allowlist secret
        ) as bad_client:
            with pytest.raises(TombaError) as exc_info:
                await bad_client.get_account_info()

            assert exc_info.value.status_code in [401, 403, None]


@pytest.mark.live_api
@skip_if_no_credentials
class TestTombaResponseSchemas:
    """Tests to verify response schemas match API documentation."""

    @pytest.mark.asyncio
    async def test_account_info_schema(self, client: TombaClient) -> None:
        """Verify account info response matches expected schema."""
        result = await client.get_account_info()

        assert hasattr(result, "user_id")
        assert hasattr(result, "email")
        assert hasattr(result, "requests_available")
        assert hasattr(result, "requests_used")
        assert hasattr(result, "search_remaining")
        assert hasattr(result, "verification_remaining")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_email_count_schema(self, client: TombaClient) -> None:
        """Verify email count response matches expected schema."""
        result = await client.get_email_count("example.com")

        assert hasattr(result, "domain")
        assert hasattr(result, "total")
        assert hasattr(result, "personal_emails")
        assert hasattr(result, "generic_emails")
        assert hasattr(result, "department")
        assert hasattr(result, "seniority")
        assert hasattr(result, "has_emails")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_domain_search_schema(self, client: TombaClient) -> None:
        """Verify domain search response matches expected schema."""
        result = await client.search_domain("example.com", limit=1)

        assert hasattr(result, "domain")
        assert hasattr(result, "emails")
        assert hasattr(result, "organization")
        assert hasattr(result, "total_results")
        assert hasattr(result, "page")
        assert hasattr(result, "limit")
        assert hasattr(result, "has_more")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_verification_schema(self, client: TombaClient) -> None:
        """Verify email verification response matches expected schema."""
        result = await client.verify_email("test@example.com")

        assert hasattr(result, "email")
        assert hasattr(result, "status")
        assert hasattr(result, "result")
        assert hasattr(result, "accept_all")
        assert hasattr(result, "disposable")
        assert hasattr(result, "webmail")
        assert hasattr(result, "mx_records")
        assert hasattr(result, "smtp_server")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_risky")
        assert hasattr(result, "raw_response")
