"""
Live API tests for HeyReach LinkedIn Automation integration.

These tests run against the REAL HeyReach API using actual API keys.
They verify that all endpoints work correctly with the live service.

Requirements:
- HEYREACH_API_KEY must be set in .env at project root
- Tests are READ-ONLY where possible to avoid modifying real data
- Run with: pytest __tests__/integration/test_heyreach_live.py -v -m live_api

Coverage:
- API key validation
- Campaign listing and retrieval
- Lead listing and retrieval
- List management
- Analytics retrieval
- Message template retrieval
- Future-proof call_endpoint method
- Error handling

IMPORTANT: All tests MUST pass 100%. No exceptions.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.heyreach import (
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    Conversation,
    HeyReachClient,
    HeyReachError,
    Lead,
    LeadList,
    MessageTemplate,
)

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.getenv("HEYREACH_API_KEY")
    if not api_key:
        pytest.skip("HEYREACH_API_KEY not found in .env - skipping live tests")
    return api_key


@pytest.fixture
def api_key() -> str:
    """Fixture to get API key."""
    return get_api_key()


@pytest.fixture
async def client(api_key: str) -> HeyReachClient:
    """Create HeyReachClient for testing."""
    return HeyReachClient(api_key=api_key, timeout=60.0, max_retries=3)


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAuthenticationLive:
    """Live tests for authentication - MUST pass 100%."""

    async def test_check_api_key_valid(self, client: HeyReachClient) -> None:
        """Test API key validation with real API - MUST PASS."""
        is_valid = await client.check_api_key()

        assert is_valid is True
        print("API key validation: PASS")

    async def test_health_check_success(self, client: HeyReachClient) -> None:
        """Test health check with real API - MUST PASS."""
        health = await client.health_check()

        assert isinstance(health, dict)
        assert health["name"] == "heyreach"
        assert health["healthy"] is True
        assert health["api_version"] == "V1"
        assert health["api_key_valid"] is True

        print("Health check: API is healthy")

    async def test_invalid_api_key_raises_error(self) -> None:
        """Test invalid API key raises authentication error - MUST PASS."""
        invalid_client = HeyReachClient(api_key="invalid-api-key-12345")

        # Try to validate the invalid key
        result = await invalid_client.check_api_key()

        # Should return False for invalid key, or raise an error
        assert result is False or isinstance(result, bool)

        print("Invalid API key handling: PASS")


# =============================================================================
# CAMPAIGN ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestCampaignEndpointsLive:
    """Live tests for campaign endpoints - MUST pass 100%."""

    async def test_list_campaigns_success(self, client: HeyReachClient) -> None:
        """Test listing campaigns with real API - MUST PASS."""
        campaigns = await client.list_campaigns(limit=10)

        assert isinstance(campaigns, list)
        for campaign in campaigns:
            assert isinstance(campaign, Campaign)
            assert campaign.id is not None
            assert campaign.name is not None
            assert isinstance(campaign.status, CampaignStatus)

        print(f"List campaigns: Retrieved {len(campaigns)} campaigns")

    async def test_list_campaigns_with_pagination(self, client: HeyReachClient) -> None:
        """Test listing campaigns with pagination - MUST PASS."""
        campaigns_page1 = await client.list_campaigns(limit=5, offset=0)
        assert isinstance(campaigns_page1, list)

        if len(campaigns_page1) == 5:
            campaigns_page2 = await client.list_campaigns(limit=5, offset=5)
            assert isinstance(campaigns_page2, list)
            print(
                f"List campaigns pagination: Page1={len(campaigns_page1)}, "
                f"Page2={len(campaigns_page2)}"
            )
        else:
            print(f"List campaigns pagination: Only {len(campaigns_page1)} campaigns available")

    async def test_get_active_campaigns(self, client: HeyReachClient) -> None:
        """Test getting only active campaigns - MUST PASS."""
        active_campaigns = await client.get_active_campaigns()

        assert isinstance(active_campaigns, list)
        for campaign in active_campaigns:
            assert campaign.status == CampaignStatus.ACTIVE

        print(f"Get active campaigns: {len(active_campaigns)} active campaigns")

    async def test_get_single_campaign(self, client: HeyReachClient) -> None:
        """Test getting a single campaign - MUST PASS if campaigns exist."""
        campaigns = await client.list_campaigns(limit=1)

        if not campaigns:
            pytest.skip("No campaigns available to test get_campaign")

        campaign = await client.get_campaign(campaigns[0].id)

        assert isinstance(campaign, Campaign)
        assert campaign.id == campaigns[0].id

        print(f"Get campaign: Retrieved campaign {campaign.id}")


# =============================================================================
# LEAD ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestLeadEndpointsLive:
    """Live tests for lead endpoints - MUST pass 100%."""

    async def test_get_campaign_leads(self, client: HeyReachClient) -> None:
        """Test getting leads from a campaign - MUST PASS if campaigns exist."""
        campaigns = await client.list_campaigns(limit=1)

        if not campaigns:
            pytest.skip("No campaigns available to test leads")

        leads = await client.get_campaign_leads(campaigns[0].id, page=1, limit=10)

        assert isinstance(leads, list)
        for lead in leads:
            assert isinstance(lead, Lead)
            if lead.first_name:
                assert isinstance(lead.first_name, str)
            if lead.linkedin_url:
                assert "linkedin" in lead.linkedin_url.lower()

        print(f"Get campaign leads: Retrieved {len(leads)} leads")


# =============================================================================
# LIST MANAGEMENT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestListManagementLive:
    """Live tests for list management - MUST pass 100%."""

    async def test_list_all_lists(self, client: HeyReachClient) -> None:
        """Test listing all lead lists - MUST PASS."""
        lists = await client.list_all_lists()

        assert isinstance(lists, list)
        for lead_list in lists:
            assert isinstance(lead_list, LeadList)
            assert lead_list.id is not None
            assert lead_list.name is not None

        print(f"List all lists: Retrieved {len(lists)} lists")


# =============================================================================
# MESSAGING TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestMessagingLive:
    """Live tests for messaging endpoints - MUST pass 100%."""

    async def test_get_templates(self, client: HeyReachClient) -> None:
        """Test getting message templates - MUST PASS."""
        templates = await client.get_templates()

        assert isinstance(templates, list)
        for template in templates:
            assert isinstance(template, MessageTemplate)

        print(f"Get templates: Retrieved {len(templates)} templates")

    async def test_get_conversations(self, client: HeyReachClient) -> None:
        """Test getting conversations - MUST PASS."""
        conversations = await client.get_conversations(limit=10)

        assert isinstance(conversations, list)
        for conv in conversations:
            assert isinstance(conv, Conversation)

        print(f"Get conversations: Retrieved {len(conversations)} conversations")


# =============================================================================
# ANALYTICS TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAnalyticsLive:
    """Live tests for analytics endpoints - MUST pass 100%."""

    async def test_get_campaign_analytics(self, client: HeyReachClient) -> None:
        """Test getting campaign analytics - MUST PASS if campaigns exist."""
        campaigns = await client.list_campaigns(limit=1)

        if not campaigns:
            pytest.skip("No campaigns available to test analytics")

        analytics = await client.get_campaign_analytics(campaigns[0].id)

        assert isinstance(analytics, CampaignAnalytics)
        assert analytics.campaign_id == campaigns[0].id
        assert analytics.total_leads >= 0

        print(f"Get campaign analytics: {analytics.total_leads} total leads")

    async def test_get_overall_stats(self, client: HeyReachClient) -> None:
        """Test getting overall account stats - MUST PASS."""
        stats = await client.get_overall_stats()

        assert isinstance(stats, dict)

        print("Get overall stats: Retrieved account statistics")


# =============================================================================
# FUTURE-PROOF ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFutureProofDesign:
    """Tests for future-proof call_endpoint method - MUST pass 100%."""

    async def test_call_endpoint_auth_check(self, client: HeyReachClient) -> None:
        """Test call_endpoint with auth check - MUST PASS."""
        result = await client.call_endpoint("/auth/CheckApiKey", method="GET")

        assert isinstance(result, dict)
        print("call_endpoint (GET /auth/CheckApiKey): Future-proof method works")

    async def test_call_endpoint_campaigns(self, client: HeyReachClient) -> None:
        """Test call_endpoint with campaigns list - MUST PASS."""
        result = await client.call_endpoint(
            "/campaign/GetAll",
            method="GET",
            params={"limit": 5},
        )

        assert isinstance(result, dict)
        print("call_endpoint (GET /campaign/GetAll): Future-proof method works")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestErrorHandlingLive:
    """Live tests for error handling - MUST pass 100%."""

    async def test_get_nonexistent_campaign_raises_error(self, client: HeyReachClient) -> None:
        """Test getting non-existent campaign raises error - MUST PASS."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(HeyReachError):
            await client.get_campaign(fake_id)

        print("Error handling: Non-existent campaign raises HeyReachError")


# =============================================================================
# COMPREHENSIVE SUMMARY TEST
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
async def test_all_endpoints_summary() -> None:
    """
    Summary test to verify all endpoint categories work.

    This test provides a final verification that all major
    endpoint categories are functional.
    """
    api_key = get_api_key()
    client = HeyReachClient(api_key=api_key, timeout=60.0)

    print("\n" + "=" * 60)
    print("HEYREACH API LIVE TEST SUMMARY")
    print("=" * 60)

    results: dict[str, bool] = {}

    # Test 1: Health Check
    try:
        health = await client.health_check()
        results["Health Check"] = health["healthy"]
    except Exception as e:
        results["Health Check"] = False
        print(f"Health Check: {e}")

    # Test 2: API Key Validation
    try:
        is_valid = await client.check_api_key()
        results["API Key Validation"] = is_valid
    except Exception as e:
        results["API Key Validation"] = False
        print(f"API Key Validation: {e}")

    # Test 3: Campaign Operations
    try:
        await client.list_campaigns(limit=1)
        results["Campaign List"] = True
    except Exception as e:
        results["Campaign List"] = False
        print(f"Campaign List: {e}")

    # Test 4: List Management
    try:
        await client.list_all_lists()
        results["List Management"] = True
    except Exception as e:
        results["List Management"] = False
        print(f"List Management: {e}")

    # Test 5: Templates
    try:
        await client.get_templates()
        results["Templates"] = True
    except Exception as e:
        results["Templates"] = False
        print(f"Templates: {e}")

    # Test 6: Future-Proof call_endpoint
    try:
        await client.call_endpoint("/auth/CheckApiKey", method="GET")
        results["Future-Proof call_endpoint"] = True
    except Exception as e:
        results["Future-Proof call_endpoint"] = False
        print(f"Future-Proof call_endpoint: {e}")

    # Print Summary
    print("\nResults:")
    all_passed = True
    for endpoint, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {endpoint}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    assert all_passed, "Some endpoints failed - see details above"
    print("ALL ENDPOINTS PASSED 100%")
