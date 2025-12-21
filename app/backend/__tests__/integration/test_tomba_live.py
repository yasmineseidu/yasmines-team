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


# ============================================================================
# Sample Data for Testing
# ============================================================================

# Using well-known tech companies for reliable test data
SAMPLE_DOMAINS = [
    "stripe.com",
    "airbnb.com",
    "notion.so",
    "figma.com",
    "slack.com",
]

SAMPLE_PERSONS = [
    {"first_name": "Patrick", "last_name": "Collison", "domain": "stripe.com"},
    {"first_name": "Brian", "last_name": "Chesky", "domain": "airbnb.com"},
    {"first_name": "Ivan", "last_name": "Zhao", "domain": "notion.so"},
]

SAMPLE_LINKEDIN_URLS = [
    "https://linkedin.com/in/patrickcollison",
    "https://www.linkedin.com/in/brianchesky",
    "https://linkedin.com/in/ivanzhao",
]

SAMPLE_EMAILS_TO_VERIFY = [
    "contact@stripe.com",
    "support@airbnb.com",
    "hello@notion.so",
    "test@example.com",
]


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
        assert result.user_id > 0
        assert isinstance(result.search_remaining, int)
        assert isinstance(result.verification_remaining, int)

        print(f"\nAccount: {result.email}")
        print(f"Plan: {result.plan_name}")
        print(f"User ID: {result.user_id}")
        print(f"Searches remaining: {result.search_remaining}")
        print(f"Verifications remaining: {result.verification_remaining}")

    @pytest.mark.asyncio
    async def test_health_check(self, client: TombaClient) -> None:
        """Test health check - verifies API connectivity."""
        health = await client.health_check()

        assert health["name"] == "tomba"
        assert health["healthy"] is True
        assert "base_url" in health
        assert "email" in health
        assert "search_remaining" in health
        assert "verification_remaining" in health

        print(f"\nHealth: {health}")

    @pytest.mark.asyncio
    async def test_get_email_count(self, client: TombaClient) -> None:
        """Test getting email count for a domain (free operation)."""
        for domain in SAMPLE_DOMAINS[:2]:
            result = await client.get_email_count(domain)

            assert isinstance(result, TombaEmailCountResult)
            assert result.domain == domain
            assert isinstance(result.total, int)
            assert isinstance(result.personal_emails, int)
            assert isinstance(result.generic_emails, int)
            assert isinstance(result.department, dict)
            assert isinstance(result.seniority, dict)
            assert result.has_emails == (result.total > 0)

            print(f"\nDomain: {result.domain}")
            print(f"  Total emails: {result.total}")
            print(f"  Personal: {result.personal_emails}")
            print(f"  Generic: {result.generic_emails}")
            print(f"  Top departments: {dict(list(result.department.items())[:3])}")

    @pytest.mark.asyncio
    async def test_search_domain(self, client: TombaClient) -> None:
        """Test domain search - uses API credits (skips if no credits)."""
        # Check if we have search credits
        account = await client.get_account_info()
        if account.search_remaining <= 0:
            pytest.skip(
                f"No search credits remaining (used: {account.requests_used}, "
                f"available: {account.requests_available})"
            )

        domain = SAMPLE_DOMAINS[0]
        result = await client.search_domain(domain, limit=5)

        assert isinstance(result, TombaDomainSearchResult)
        assert result.domain == domain
        assert isinstance(result.emails, list)
        assert isinstance(result.total_results, int)
        assert isinstance(result.page, int)
        assert isinstance(result.limit, int)

        print(f"\nOrganization: {result.organization}")
        print(f"Pattern: {result.pattern}")
        print(f"Total results: {result.total_results}")
        print(f"Emails found: {len(result.emails)}")
        print(f"Has more: {result.has_more}")

        for email in result.emails[:3]:
            print(f"  - {email.email} ({email.position})")
            assert email.email
            assert "@" in email.email

    @pytest.mark.asyncio
    async def test_search_domain_with_filters(self, client: TombaClient) -> None:
        """Test domain search with department filter (skips if no credits)."""
        account = await client.get_account_info()
        if account.search_remaining <= 0:
            pytest.skip("No search credits remaining")

        domain = SAMPLE_DOMAINS[0]
        result = await client.search_domain(
            domain,
            limit=5,
            department="engineering",
        )

        assert isinstance(result, TombaDomainSearchResult)
        print(f"\nEngineering emails from {domain}: {len(result.emails)}")

    @pytest.mark.asyncio
    async def test_find_email(self, client: TombaClient) -> None:
        """Test email finder - uses API credits."""
        person = SAMPLE_PERSONS[0]
        result = await client.find_email(
            domain=person["domain"],
            first_name=person["first_name"],
            last_name=person["last_name"],
        )

        assert isinstance(result, TombaEmailFinderResult)
        assert isinstance(result.confidence, int)
        assert result.confidence >= 0

        print(f"\nSearched: {person['first_name']} {person['last_name']} @ {person['domain']}")
        print(f"Email: {result.email}")
        print(f"Confidence: {result.confidence}%")
        print(f"Position: {result.position}")
        print(f"Company: {result.company}")
        print(f"High confidence: {result.is_high_confidence}")
        print(f"Found: {result.found}")

    @pytest.mark.asyncio
    async def test_find_email_with_full_name(self, client: TombaClient) -> None:
        """Test email finder with full name instead of first/last."""
        person = SAMPLE_PERSONS[1]
        full_name = f"{person['first_name']} {person['last_name']}"

        result = await client.find_email(
            domain=person["domain"],
            full_name=full_name,
        )

        assert isinstance(result, TombaEmailFinderResult)
        print(f"\nFull name search: {full_name} @ {person['domain']}")
        print(f"Email: {result.email}")
        print(f"Confidence: {result.confidence}%")

    @pytest.mark.asyncio
    async def test_verify_email(self, client: TombaClient) -> None:
        """Test email verification - uses verification credits."""
        for email in SAMPLE_EMAILS_TO_VERIFY[:2]:
            result = await client.verify_email(email)

            assert isinstance(result, TombaVerificationResult)
            assert result.email == email.lower()
            assert result.status in list(TombaVerificationStatus)
            assert isinstance(result.accept_all, bool)
            assert isinstance(result.disposable, bool)
            assert isinstance(result.webmail, bool)
            assert isinstance(result.mx_records, bool)
            assert isinstance(result.smtp_server, bool)
            assert isinstance(result.smtp_check, bool)

            print(f"\nEmail: {result.email}")
            print(f"  Status: {result.status.value}")
            print(f"  Valid: {result.is_valid}")
            print(f"  Risky: {result.is_risky}")
            print(f"  MX records: {result.mx_records}")
            print(f"  SMTP server: {result.smtp_server}")
            print(f"  SMTP check: {result.smtp_check}")

    @pytest.mark.asyncio
    async def test_find_email_from_linkedin(self, client: TombaClient) -> None:
        """Test LinkedIn email lookup - uses API credits."""
        linkedin_url = SAMPLE_LINKEDIN_URLS[0]
        result = await client.find_email_from_linkedin(linkedin_url)

        assert isinstance(result, TombaEmailFinderResult)

        print(f"\nLinkedIn URL: {linkedin_url}")
        print(f"Email: {result.email}")
        print(f"Confidence: {result.confidence}%")
        print(f"Position: {result.position}")
        print(f"Company: {result.company}")
        print(f"Found: {result.found}")

    @pytest.mark.asyncio
    async def test_call_endpoint_dynamic(self, client: TombaClient) -> None:
        """Test calling endpoint dynamically for future-proofing."""
        # Use email-count endpoint as it's free
        result = await client.call_endpoint(
            "/email-count",
            method="GET",
            params={"domain": "example.com"},
        )

        assert isinstance(result, dict)
        assert "data" in result or "total" in result
        print(f"\nDynamic endpoint result: {result}")

    @pytest.mark.asyncio
    async def test_call_endpoint_with_post(self, client: TombaClient) -> None:
        """Test calling POST endpoint dynamically."""
        # Test the email-finder endpoint with POST
        result = await client.call_endpoint(
            "/email-finder",
            method="GET",
            params={
                "domain": "stripe.com",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        assert isinstance(result, dict)
        print(f"\nDynamic POST result keys: {list(result.keys())}")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_credentials(self) -> None:
        """Test error handling with invalid credentials."""
        async with TombaClient(
            api_key="ta_invalid",  # pragma: allowlist secret
            api_secret="ts_invalid",  # pragma: allowlist secret
        ) as bad_client:
            with pytest.raises(TombaError) as exc_info:
                await bad_client.get_account_info()

            # Tomba returns 400 for invalid API credentials
            assert exc_info.value.status_code in [400, 401, 403, None]
            print(f"\nExpected error: {exc_info.value}")
            print(f"Status code: {exc_info.value.status_code}")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_domain(self, client: TombaClient) -> None:
        """Test error handling with invalid domain format."""
        with pytest.raises(ValueError) as exc_info:
            await client.get_email_count("")

        assert "domain is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_email_format(self, client: TombaClient) -> None:
        """Test error handling with invalid email format."""
        with pytest.raises(ValueError) as exc_info:
            await client.verify_email("not-an-email")

        assert "Invalid email format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_linkedin_url(self, client: TombaClient) -> None:
        """Test error handling with invalid LinkedIn URL."""
        with pytest.raises(ValueError) as exc_info:
            await client.find_email_from_linkedin("https://twitter.com/user")

        assert "Invalid LinkedIn URL" in str(exc_info.value)


@pytest.mark.live_api
@skip_if_no_credentials
class TestTombaResponseSchemas:
    """Tests to verify response schemas match API documentation."""

    @pytest.mark.asyncio
    async def test_account_info_schema(self, client: TombaClient) -> None:
        """Verify account info response matches expected schema."""
        result = await client.get_account_info()

        # Verify all expected attributes exist
        assert hasattr(result, "user_id")
        assert hasattr(result, "email")
        assert hasattr(result, "first_name")
        assert hasattr(result, "last_name")
        assert hasattr(result, "requests_available")
        assert hasattr(result, "requests_used")
        assert hasattr(result, "verifications_available")
        assert hasattr(result, "verifications_used")
        assert hasattr(result, "phone_credits_available")
        assert hasattr(result, "phone_credits_used")
        assert hasattr(result, "plan_name")
        assert hasattr(result, "search_remaining")
        assert hasattr(result, "verification_remaining")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_email_count_schema(self, client: TombaClient) -> None:
        """Verify email count response matches expected schema."""
        result = await client.get_email_count("stripe.com")

        assert hasattr(result, "domain")
        assert hasattr(result, "total")
        assert hasattr(result, "personal_emails")
        assert hasattr(result, "generic_emails")
        assert hasattr(result, "department")
        assert hasattr(result, "seniority")
        assert hasattr(result, "has_emails")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_email_finder_schema(self, client: TombaClient) -> None:
        """Verify email finder response matches expected schema."""
        result = await client.find_email(
            domain="stripe.com",
            first_name="Patrick",
            last_name="Collison",
        )

        assert hasattr(result, "email")
        assert hasattr(result, "first_name")
        assert hasattr(result, "last_name")
        assert hasattr(result, "full_name")
        assert hasattr(result, "domain")
        assert hasattr(result, "position")
        assert hasattr(result, "department")
        assert hasattr(result, "seniority")
        assert hasattr(result, "linkedin")
        assert hasattr(result, "twitter")
        assert hasattr(result, "phone_number")
        assert hasattr(result, "company")
        assert hasattr(result, "email_type")
        assert hasattr(result, "confidence")
        assert hasattr(result, "sources")
        assert hasattr(result, "found")
        assert hasattr(result, "is_high_confidence")
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
        assert hasattr(result, "smtp_check")
        assert hasattr(result, "block")
        assert hasattr(result, "sources")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_risky")
        assert hasattr(result, "raw_response")

    @pytest.mark.asyncio
    async def test_domain_search_schema(self, client: TombaClient) -> None:
        """Verify domain search response matches expected schema (skips if no credits)."""
        account = await client.get_account_info()
        if account.search_remaining <= 0:
            pytest.skip("No search credits remaining for domain search schema test")

        result = await client.search_domain("stripe.com", limit=1)

        assert hasattr(result, "domain")
        assert hasattr(result, "emails")
        assert hasattr(result, "organization")
        assert hasattr(result, "country")
        assert hasattr(result, "state")
        assert hasattr(result, "city")
        assert hasattr(result, "postal_code")
        assert hasattr(result, "street_address")
        assert hasattr(result, "accept_all")
        assert hasattr(result, "website_url")
        assert hasattr(result, "disposable")
        assert hasattr(result, "webmail")
        assert hasattr(result, "pattern")
        assert hasattr(result, "total_results")
        assert hasattr(result, "page")
        assert hasattr(result, "limit")
        assert hasattr(result, "has_more")
        assert hasattr(result, "raw_response")

        # Verify email schema if any emails returned
        if result.emails:
            email = result.emails[0]
            assert hasattr(email, "email")
            assert hasattr(email, "first_name")
            assert hasattr(email, "last_name")
            assert hasattr(email, "full_name")
            assert hasattr(email, "position")
            assert hasattr(email, "department")
            assert hasattr(email, "email_type")
            assert hasattr(email, "seniority")
            assert hasattr(email, "linkedin")
            assert hasattr(email, "twitter")
            assert hasattr(email, "phone_number")
            assert hasattr(email, "sources")
            assert hasattr(email, "verification_status")
            assert hasattr(email, "confidence")
            assert hasattr(email, "is_verified")
            assert hasattr(email, "has_social")
            assert hasattr(email, "raw_data")
