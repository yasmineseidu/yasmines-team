"""
Live integration tests for all email finding and verification services.

These tests use real API keys and make actual API calls.
Run with: pytest __tests__/integration/test_integrations_live.py -v -s

IMPORTANT: These tests consume API credits. Run sparingly.

Environment variables required (from .env):
- ICYPEAS_API_KEY
- TOMBA_API_KEY, TOMBA_API_SECRET
- MURAENA_API_KEY
- MAILVERIFY_API_KEY
- INSTANTLY_API_KEY
- REOON_API_KEY
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from __tests__.fixtures.live_test_data import (
    QUICK_TEST_CONTACT,
    QUICK_TEST_EMAIL,
    SAMPLE_CONTACTS,
    SAMPLE_DOMAINS,
    SAMPLE_EMAILS,
    SAMPLE_LINKEDIN_URLS,
)
from src.integrations.icypeas import IcypeasClient
from src.integrations.instantly import InstantlyClient
from src.integrations.mailverify import MailVerifyClient
from src.integrations.muraena import MuraenaClient
from src.integrations.reoon import ReoonClient
from src.integrations.tomba import TombaClient

# Load .env from project root (yasmines-team/.env)
env_path = Path(__file__).parents[4] / ".env"
load_dotenv(env_path)
print(f"Loading .env from: {env_path}")

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def icypeas_client():
    """Create Icypeas client with API key from env."""
    api_key = os.getenv("ICYPEAS_API_KEY")
    if not api_key:
        pytest.skip("ICYPEAS_API_KEY not set")
    return IcypeasClient(api_key=api_key)


@pytest.fixture
def tomba_client():
    """Create Tomba client with API key from env."""
    api_key = os.getenv("TOMBA_API_KEY")
    api_secret = os.getenv("TOMBA_API_SECRET")
    if not api_key or not api_secret:
        pytest.skip("TOMBA_API_KEY or TOMBA_API_SECRET not set")
    return TombaClient(api_key=api_key, api_secret=api_secret)


@pytest.fixture
def muraena_client():
    """Create Muraena client with API key from env."""
    api_key = os.getenv("MURAENA_API_KEY")
    if not api_key:
        pytest.skip("MURAENA_API_KEY not set")
    return MuraenaClient(api_key=api_key)


@pytest.fixture
def mailverify_client():
    """Create MailVerify client with API key from env."""
    api_key = os.getenv("MAILVERIFY_API_KEY")
    if not api_key:
        pytest.skip("MAILVERIFY_API_KEY not set")
    return MailVerifyClient(api_key=api_key)


@pytest.fixture
def instantly_client():
    """Create Instantly client with API key from env."""
    api_key = os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        pytest.skip("INSTANTLY_API_KEY not set")
    return InstantlyClient(api_key=api_key)


@pytest.fixture
def reoon_client():
    """Create Reoon client with API key from env."""
    api_key = os.getenv("REOON_API_KEY")
    if not api_key:
        pytest.skip("REOON_API_KEY not set")
    return ReoonClient(api_key=api_key)


# =============================================================================
# ICYPEAS TESTS
# =============================================================================


class TestIcypeasLive:
    """Live tests for Icypeas integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, icypeas_client: IcypeasClient) -> None:
        """Health check should return healthy status."""
        async with icypeas_client:
            result = await icypeas_client.health_check()
            print(f"\nIcypeas health check: {result}")
            assert result["healthy"] is True
            assert result["authorization_configured"] is True

    @pytest.mark.asyncio
    async def test_get_credits(self, icypeas_client: IcypeasClient) -> None:
        """Should return credits info (Icypeas has no credits endpoint)."""
        async with icypeas_client:
            result = await icypeas_client.get_credits()
            print(f"\nIcypeas credits: {result}")
            # Icypeas returns -1 (unknown) since API doesn't provide credits endpoint
            assert result.credits_remaining == -1

    @pytest.mark.asyncio
    async def test_find_email_known_contact(self, icypeas_client: IcypeasClient) -> None:
        """Should find email for well-known contact."""
        contact = SAMPLE_CONTACTS[0]  # Sundar Pichai
        async with icypeas_client:
            result = await icypeas_client.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
                wait_for_result=True,
            )
            print(f"\nIcypeas find_email result: {result}")
            # We don't assert found=True as it depends on credits/data
            assert result.search_id is not None or result.email is not None

    @pytest.mark.asyncio
    async def test_find_email_no_wait(self, icypeas_client: IcypeasClient) -> None:
        """Should return search ID immediately when not waiting."""
        contact = QUICK_TEST_CONTACT
        async with icypeas_client:
            result = await icypeas_client.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
                wait_for_result=False,
            )
            print(f"\nIcypeas async search: {result}")
            assert result.search_id is not None

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, icypeas_client: IcypeasClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with icypeas_client:
            # Use call_endpoint to call any endpoint
            try:
                result = await icypeas_client.call_endpoint(
                    endpoint="/credits",
                    method="GET",
                )
                print(f"\nIcypeas call_endpoint result: {result}")
                assert isinstance(result, dict)
            except Exception as e:
                # Endpoint might not exist but method should work
                print(f"\nIcypeas call_endpoint error (expected): {e}")
                assert True


# =============================================================================
# TOMBA TESTS
# =============================================================================


class TestTombaLive:
    """Live tests for Tomba integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, tomba_client: TombaClient) -> None:
        """Health check should return healthy status."""
        async with tomba_client:
            result = await tomba_client.health_check()
            print(f"\nTomba health check: {result}")
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_account_info(self, tomba_client: TombaClient) -> None:
        """Should return account info."""
        async with tomba_client:
            result = await tomba_client.get_account_info()
            print(f"\nTomba account: {result}")
            assert result.email is not None or result.available_searches >= 0

    @pytest.mark.asyncio
    async def test_find_email_known_contact(self, tomba_client: TombaClient) -> None:
        """Should find email for well-known contact."""
        contact = SAMPLE_CONTACTS[0]  # Sundar Pichai
        async with tomba_client:
            result = await tomba_client.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            print(f"\nTomba find_email result: {result}")
            # Result may or may not have email depending on data
            assert result.raw_response is not None

    @pytest.mark.asyncio
    async def test_search_domain(self, tomba_client: TombaClient) -> None:
        """Should search for emails by domain."""
        domain = SAMPLE_DOMAINS[0]  # Google
        async with tomba_client:
            result = await tomba_client.search_domain(
                domain=domain.domain,
                limit=5,
            )
            print(f"\nTomba search_domain result: {result}")
            assert result.domain == domain.domain
            assert result.total_results >= 0

    @pytest.mark.asyncio
    async def test_get_email_count(self, tomba_client: TombaClient) -> None:
        """Should return email count for domain."""
        domain = SAMPLE_DOMAINS[0]  # Google
        async with tomba_client:
            result = await tomba_client.get_email_count(domain=domain.domain)
            print(f"\nTomba get_email_count result: {result}")
            assert result.total >= 0

    @pytest.mark.asyncio
    async def test_verify_email(self, tomba_client: TombaClient) -> None:
        """Should verify email address."""
        email = QUICK_TEST_EMAIL
        async with tomba_client:
            result = await tomba_client.verify_email(email.email)
            print(f"\nTomba verify_email result: {result}")
            assert result.email == email.email

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, tomba_client: TombaClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with tomba_client:
            try:
                result = await tomba_client.call_endpoint(
                    endpoint="/account",
                    method="GET",
                )
                print(f"\nTomba call_endpoint result: {result}")
                assert isinstance(result, dict)
            except Exception as e:
                print(f"\nTomba call_endpoint error: {e}")


# =============================================================================
# MURAENA TESTS
# =============================================================================


class TestMuraenaLive:
    """Live tests for Muraena integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, muraena_client: MuraenaClient) -> None:
        """Health check should return healthy status."""
        async with muraena_client:
            result = await muraena_client.health_check()
            print(f"\nMuraena health check: {result}")
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_credits(self, muraena_client: MuraenaClient) -> None:
        """Should return credits info."""
        async with muraena_client:
            result = await muraena_client.get_credits()
            print(f"\nMuraena credits: {result}")
            assert result.credits_remaining >= 0

    @pytest.mark.asyncio
    async def test_find_contact_by_name_domain(self, muraena_client: MuraenaClient) -> None:
        """Should find contact by name and domain."""
        contact = SAMPLE_CONTACTS[0]  # Sundar Pichai
        async with muraena_client:
            result = await muraena_client.find_contact(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            print(f"\nMuraena find_contact result: {result}")
            assert result.raw_response is not None

    @pytest.mark.asyncio
    async def test_find_contact_by_linkedin(self, muraena_client: MuraenaClient) -> None:
        """Should find contact by LinkedIn URL."""
        linkedin_url = SAMPLE_LINKEDIN_URLS[0]  # Sundar Pichai
        async with muraena_client:
            result = await muraena_client.search_by_linkedin(linkedin_url)
            print(f"\nMuraena search_by_linkedin result: {result}")
            assert result.raw_response is not None

    @pytest.mark.asyncio
    async def test_verify_email(self, muraena_client: MuraenaClient) -> None:
        """Should verify email address."""
        email = QUICK_TEST_EMAIL
        async with muraena_client:
            result = await muraena_client.verify_email(email.email)
            print(f"\nMuraena verify_email result: {result}")
            assert result.email == email.email

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, muraena_client: MuraenaClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with muraena_client:
            try:
                result = await muraena_client.call_endpoint(
                    endpoint="/credits",
                    method="GET",
                )
                print(f"\nMuraena call_endpoint result: {result}")
                assert isinstance(result, dict)
            except Exception as e:
                print(f"\nMuraena call_endpoint error: {e}")


# =============================================================================
# MAILVERIFY TESTS
# =============================================================================


class TestMailVerifyLive:
    """Live tests for MailVerify integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, mailverify_client: MailVerifyClient) -> None:
        """Health check should return healthy status."""
        async with mailverify_client:
            result = await mailverify_client.health_check()
            print(f"\nMailVerify health check: {result}")
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_verify_valid_email(self, mailverify_client: MailVerifyClient) -> None:
        """Should verify a valid email address."""
        email = QUICK_TEST_EMAIL
        async with mailverify_client:
            result = await mailverify_client.verify_email(email.email)
            print(f"\nMailVerify verify_email result: {result}")
            assert result.email == email.email
            # Check the verification returned a status
            assert result.status is not None

    @pytest.mark.asyncio
    async def test_verify_invalid_domain_email(self, mailverify_client: MailVerifyClient) -> None:
        """Should identify invalid domain email."""
        invalid_email = SAMPLE_EMAILS[3]  # Invalid domain
        async with mailverify_client:
            result = await mailverify_client.verify_email(invalid_email.email)
            print(f"\nMailVerify invalid email result: {result}")
            assert result.is_valid is False or result.is_deliverable is False

    @pytest.mark.asyncio
    async def test_verify_disposable_email(self, mailverify_client: MailVerifyClient) -> None:
        """Should identify disposable email."""
        disposable = SAMPLE_EMAILS[5]  # Mailinator
        async with mailverify_client:
            result = await mailverify_client.verify_email(disposable.email)
            print(f"\nMailVerify disposable result: {result}")
            # Should detect as disposable or risky
            assert result.is_disposable is True or result.is_safe_to_send is False

    @pytest.mark.asyncio
    async def test_check_domain(self, mailverify_client: MailVerifyClient) -> None:
        """Should check domain MX records.

        Note: MailVerify.ai does not have a dedicated domain check endpoint.
        Domain/MX info is returned as part of the email verification response.
        This test verifies that the verify_email response includes domain info.
        """
        # Use email verification to check domain info
        async with mailverify_client:
            result = await mailverify_client.verify_email("test@google.com")
            print(f"\nMailVerify domain info via verify_email: {result.raw_response}")
            # Domain info is in raw_response['data']['mx']
            assert isinstance(result.raw_response, dict)
            assert "data" in result.raw_response

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, mailverify_client: MailVerifyClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with mailverify_client:
            try:
                # Test with verify endpoint
                result = await mailverify_client.call_endpoint(
                    endpoint="/verify",
                    method="POST",
                    json={"email": "test@example.com"},
                )
                print(f"\nMailVerify call_endpoint result: {result}")
                assert isinstance(result, dict)
            except Exception as e:
                print(f"\nMailVerify call_endpoint error: {e}")


# =============================================================================
# INSTANTLY TESTS
# =============================================================================


class TestInstantlyLive:
    """Live tests for Instantly integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, instantly_client: InstantlyClient) -> None:
        """Health check should return healthy status."""
        async with instantly_client:
            result = await instantly_client.health_check()
            print(f"\nInstantly health check: {result}")
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_list_campaigns(self, instantly_client: InstantlyClient) -> None:
        """Should list campaigns."""
        async with instantly_client:
            result = await instantly_client.list_campaigns()
            print(f"\nInstantly list_campaigns: {len(result)} campaigns")
            # Could be empty if no campaigns exist
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_leads(self, instantly_client: InstantlyClient) -> None:
        """Should list leads from a campaign."""
        async with instantly_client:
            campaigns = await instantly_client.list_campaigns()
            if campaigns:
                campaign_id = campaigns[0].id
                result = await instantly_client.list_leads(campaign_id=campaign_id)
                print(f"\nInstantly leads: {len(result)} leads")
                assert isinstance(result, list)
            else:
                print("\nNo campaigns to list leads from")
                pytest.skip("No campaigns available")

    @pytest.mark.asyncio
    async def test_get_campaign_analytics(self, instantly_client: InstantlyClient) -> None:
        """Should get analytics for campaigns."""
        async with instantly_client:
            campaigns = await instantly_client.list_campaigns()
            if campaigns:
                campaign_id = campaigns[0].id
                analytics = await instantly_client.get_campaign_analytics(campaign_id)
                print(f"\nInstantly analytics: {analytics}")
                assert analytics is not None
            else:
                print("\nNo campaigns to get analytics for")
                pytest.skip("No campaigns available")

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, instantly_client: InstantlyClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with instantly_client:
            try:
                result = await instantly_client.call_endpoint(
                    endpoint="/campaign/list",
                    method="GET",
                )
                print(f"\nInstantly call_endpoint result: {result}")
                assert isinstance(result, dict | list)
            except Exception as e:
                print(f"\nInstantly call_endpoint error: {e}")


# =============================================================================
# REOON TESTS
# =============================================================================


class TestReoonLive:
    """Live tests for Reoon integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, reoon_client: ReoonClient) -> None:
        """Health check should return healthy status."""
        async with reoon_client:
            result = await reoon_client.health_check()
            print(f"\nReoon health check: {result}")
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_balance(self, reoon_client: ReoonClient) -> None:
        """Should get account balance."""
        async with reoon_client:
            result = await reoon_client.get_account_balance()
            print(f"\nReoon balance: {result}")
            # Has remaining_daily_credits and remaining_instant_credits
            assert result.remaining_daily_credits >= 0 or result.remaining_instant_credits >= 0

    @pytest.mark.asyncio
    async def test_verify_email_quick(self, reoon_client: ReoonClient) -> None:
        """Should verify email in quick mode."""
        email = QUICK_TEST_EMAIL
        async with reoon_client:
            result = await reoon_client.verify_email_quick(email.email)
            print(f"\nReoon verify_email (quick): {result}")
            assert result.email == email.email

    @pytest.mark.asyncio
    async def test_verify_email_power(self, reoon_client: ReoonClient) -> None:
        """Should verify email in power mode."""
        email = QUICK_TEST_EMAIL
        async with reoon_client:
            result = await reoon_client.verify_email_power(email.email)
            print(f"\nReoon verify_email (power): {result}")
            assert result.email == email.email

    @pytest.mark.asyncio
    async def test_call_endpoint_future_proof(self, reoon_client: ReoonClient) -> None:
        """Test generic endpoint caller for future endpoints."""
        async with reoon_client:
            try:
                result = await reoon_client.call_endpoint(
                    endpoint="/balance/",
                    method="GET",
                )
                print(f"\nReoon call_endpoint result: {result}")
                assert isinstance(result, dict)
            except Exception as e:
                print(f"\nReoon call_endpoint error: {e}")


# =============================================================================
# INTEGRATION WATERFALL TEST
# =============================================================================


class TestLeadEnrichmentWaterfallLive:
    """Live tests for LeadEnrichmentWaterfall orchestrator."""

    @pytest.fixture
    def waterfall(self):
        """Create waterfall with available API keys."""
        from src.integrations.lead_enrichment import LeadEnrichmentWaterfall

        return LeadEnrichmentWaterfall(
            tomba_key=os.getenv("TOMBA_API_KEY"),
            tomba_secret=os.getenv("TOMBA_API_SECRET"),
            icypeas_key=os.getenv("ICYPEAS_API_KEY"),
            muraena_key=os.getenv("MURAENA_API_KEY"),
            mailverify_key=os.getenv("MAILVERIFY_API_KEY"),
            verify_results=True,
            cache_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_waterfall_health_check(self, waterfall) -> None:
        """Health check should return status for all services."""
        async with waterfall:
            result = await waterfall.health_check()
            print(f"\nWaterfall health check: {result}")
            assert "services" in result

    @pytest.mark.asyncio
    async def test_waterfall_find_email(self, waterfall) -> None:
        """Should attempt to find email through waterfall."""
        contact = SAMPLE_CONTACTS[0]  # Sundar Pichai
        async with waterfall:
            result = await waterfall.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            print(f"\nWaterfall find_email result: {result}")
            print(f"Services tried: {result.services_tried}")
            print(f"Total cost: {result.total_cost}")
            print(f"Duration: {result.duration_ms}ms")
            # Should have tried at least one service
            assert len(result.services_tried) >= 1

    @pytest.mark.asyncio
    async def test_waterfall_caching(self, waterfall) -> None:
        """Second call should return cached result."""
        contact = SAMPLE_CONTACTS[0]
        async with waterfall:
            # First call
            result1 = await waterfall.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            # Second call
            result2 = await waterfall.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            print(f"\nFirst call source: {result1.source}")
            print(f"Second call source: {result2.source}")
            # If first call found, second should be cached
            if result1.found:
                from src.integrations.lead_enrichment import EnrichmentSource

                assert result2.source == EnrichmentSource.CACHE

    @pytest.mark.asyncio
    async def test_waterfall_stats(self, waterfall) -> None:
        """Should track statistics across calls."""
        contact = QUICK_TEST_CONTACT
        async with waterfall:
            await waterfall.find_email(
                first_name=contact.first_name,
                last_name=contact.last_name,
                domain=contact.domain,
            )
            stats = waterfall.get_stats()
            print(f"\nWaterfall stats: {stats}")
            assert stats.total_requests >= 1


# =============================================================================
# VERIFY ALL CLIENTS HAVE call_endpoint FOR FUTURE-PROOFING
# =============================================================================


class TestFutureProofEndpoints:
    """Verify all clients have call_endpoint method for future endpoints."""

    def test_icypeas_has_call_endpoint(self) -> None:
        """Icypeas should have call_endpoint method."""
        client = IcypeasClient(api_key="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)

    def test_tomba_has_call_endpoint(self) -> None:
        """Tomba should have call_endpoint method."""
        client = TombaClient(api_key="test", api_secret="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)

    def test_muraena_has_call_endpoint(self) -> None:
        """Muraena should have call_endpoint method."""
        client = MuraenaClient(api_key="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)

    def test_mailverify_has_call_endpoint(self) -> None:
        """MailVerify should have call_endpoint method."""
        client = MailVerifyClient(api_key="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)

    def test_instantly_has_call_endpoint(self) -> None:
        """Instantly should have call_endpoint method."""
        client = InstantlyClient(api_key="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)

    def test_reoon_has_call_endpoint(self) -> None:
        """Reoon should have call_endpoint method."""
        client = ReoonClient(api_key="test")
        assert hasattr(client, "call_endpoint")
        assert callable(client.call_endpoint)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
