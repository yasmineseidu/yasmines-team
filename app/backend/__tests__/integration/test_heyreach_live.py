"""
Live API tests for HeyReach LinkedIn Automation integration.

These tests run against the REAL HeyReach API using actual API keys.
All tests MUST pass 100%. No exceptions.

Requirements:
- HEYREACH_API_KEY must be set in .env at project root
- Tests are READ-ONLY where possible to avoid modifying real data

Available Endpoints (verified working):
- GET  /auth/CheckApiKey - Validate API key
- POST /campaign/GetAll - List all campaigns
- GET  /campaign/GetById?campaignId=X - Get campaign details
- POST /campaign/Pause?campaignId=X - Pause campaign
- POST /campaign/Resume?campaignId=X - Resume campaign
- POST /campaign/AddLeadsToCampaignV2 - Add leads to campaign
- POST /lead/GetLead - Get lead details
- POST /list/GetAll - List all lead lists
- POST /list/CreateEmptyList - Create empty list
- POST /inbox/GetConversationsV2 - Get conversations
- POST /stats/GetOverallStats - Get overall statistics

Unavailable Endpoints (404 in API):
- /campaign/Create - Not available
- /campaign/GetLeads - Not available
- /lead/UpdateStatus - Not available
- /message/Send - Not available
- /templates/GetAll - Not available
- /social/Action - Not available
- /analytics/campaign/{id} - Not available
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.heyreach import (
    Campaign,
    CampaignStatus,
    Conversation,
    HeyReachClient,
    HeyReachError,
    LeadList,
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
# AUTHENTICATION TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAuthenticationLive:
    """Live tests for authentication."""

    async def test_check_api_key_valid(self, client: HeyReachClient) -> None:
        """Test API key validation with real API."""
        is_valid = await client.check_api_key()

        assert is_valid is True
        print("✓ API key validation: PASS")

    async def test_health_check_success(self, client: HeyReachClient) -> None:
        """Test health check with real API."""
        health = await client.health_check()

        assert isinstance(health, dict)
        assert health["name"] == "heyreach"
        assert health["healthy"] is True
        assert health["api_version"] == "V1"
        assert health["api_key_valid"] is True

        print("✓ Health check: API is healthy")

    async def test_invalid_api_key_returns_false(self) -> None:
        """Test invalid API key returns False or raises error."""
        invalid_client = HeyReachClient(
            api_key="invalid-key-12345"  # pragma: allowlist secret
        )

        # Invalid key should either return False or raise error
        try:
            result = await invalid_client.check_api_key()
            # If no error, should return False
            assert result is False
        except HeyReachError:
            # Raising error is also acceptable
            pass

        print("✓ Invalid API key handling: PASS")


# =============================================================================
# CAMPAIGN ENDPOINT TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestCampaignEndpointsLive:
    """Live tests for campaign endpoints."""

    async def test_list_campaigns_success(self, client: HeyReachClient) -> None:
        """Test listing campaigns with real API."""
        campaigns = await client.list_campaigns(limit=10)

        assert isinstance(campaigns, list)
        for campaign in campaigns:
            assert isinstance(campaign, Campaign)
            assert campaign.id is not None
            assert campaign.name is not None
            assert isinstance(campaign.status, CampaignStatus)

        print(f"✓ List campaigns: Retrieved {len(campaigns)} campaigns")

    async def test_list_campaigns_with_pagination(self, client: HeyReachClient) -> None:
        """Test listing campaigns with pagination."""
        campaigns_page1 = await client.list_campaigns(limit=5, offset=0)
        assert isinstance(campaigns_page1, list)

        print(f"✓ List campaigns pagination: {len(campaigns_page1)} campaigns")

    async def test_get_active_campaigns(self, client: HeyReachClient) -> None:
        """Test getting only active campaigns."""
        active_campaigns = await client.get_active_campaigns()

        assert isinstance(active_campaigns, list)
        for campaign in active_campaigns:
            assert campaign.status == CampaignStatus.ACTIVE

        print(f"✓ Get active campaigns: {len(active_campaigns)} active campaigns")

    async def test_get_single_campaign(self, client: HeyReachClient) -> None:
        """Test getting a single campaign by ID."""
        campaigns = await client.list_campaigns(limit=1)

        if not campaigns:
            pytest.skip("No campaigns available to test get_campaign")

        campaign = await client.get_campaign(campaigns[0].id)

        assert isinstance(campaign, Campaign)
        assert campaign.id == campaigns[0].id

        print(f"✓ Get campaign: Retrieved campaign '{campaign.name}'")


# =============================================================================
# LIST MANAGEMENT TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestListManagementLive:
    """Live tests for list management."""

    async def test_list_all_lists(self, client: HeyReachClient) -> None:
        """Test listing all lead lists."""
        lists = await client.list_all_lists()

        assert isinstance(lists, list)
        for lead_list in lists:
            assert isinstance(lead_list, LeadList)
            assert lead_list.id is not None
            assert lead_list.name is not None

        print(f"✓ List all lists: Retrieved {len(lists)} lists")


# =============================================================================
# CONVERSATION TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestConversationsLive:
    """Live tests for conversation endpoints."""

    async def test_get_conversations(self, client: HeyReachClient) -> None:
        """Test getting conversations."""
        conversations = await client.get_conversations(limit=10)

        assert isinstance(conversations, list)
        for conv in conversations:
            assert isinstance(conv, Conversation)

        print(f"✓ Get conversations: Retrieved {len(conversations)} conversations")


# =============================================================================
# ANALYTICS TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAnalyticsLive:
    """Live tests for analytics endpoints."""

    async def test_get_overall_stats(self, client: HeyReachClient) -> None:
        """Test getting overall account stats."""
        stats = await client.get_overall_stats()

        assert isinstance(stats, dict)
        # Stats should contain overallStats or byDayStats
        assert "overallStats" in stats or "byDayStats" in stats

        print("✓ Get overall stats: Retrieved account statistics")


# =============================================================================
# FUTURE-PROOF ENDPOINT TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFutureProofDesign:
    """Tests for future-proof call_endpoint method."""

    async def test_call_endpoint_auth_check(self, client: HeyReachClient) -> None:
        """Test call_endpoint with auth check."""
        result = await client.call_endpoint("/auth/CheckApiKey", method="GET")

        assert isinstance(result, dict)
        print("✓ call_endpoint (GET /auth/CheckApiKey): Future-proof method works")

    async def test_call_endpoint_campaigns(self, client: HeyReachClient) -> None:
        """Test call_endpoint with campaigns list."""
        result = await client.call_endpoint(
            "/campaign/GetAll",
            method="POST",
            json={},
        )

        assert isinstance(result, dict)
        print("✓ call_endpoint (POST /campaign/GetAll): Future-proof method works")


# =============================================================================
# ERROR HANDLING TESTS - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestErrorHandlingLive:
    """Live tests for error handling."""

    async def test_get_nonexistent_campaign_raises_error(self, client: HeyReachClient) -> None:
        """Test getting non-existent campaign raises error."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(HeyReachError):
            await client.get_campaign(fake_id)

        print("✓ Error handling: Non-existent campaign raises HeyReachError")


# =============================================================================
# COMPREHENSIVE SUMMARY TEST - MUST PASS 100%
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
async def test_all_endpoints_summary() -> None:
    """
    Summary test to verify all endpoint categories work.
    ALL endpoints must pass 100%. No exceptions.
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
        print(f"Health Check FAILED: {e}")

    # Test 2: API Key Validation
    try:
        is_valid = await client.check_api_key()
        results["API Key Validation"] = is_valid
    except Exception as e:
        results["API Key Validation"] = False
        print(f"API Key Validation FAILED: {e}")

    # Test 3: Campaign Operations
    try:
        campaigns = await client.list_campaigns(limit=1)
        results["Campaign List"] = True
        if campaigns:
            await client.get_campaign(campaigns[0].id)
            results["Get Campaign"] = True
    except Exception as e:
        results["Campaign List"] = False
        print(f"Campaign List FAILED: {e}")

    # Test 4: Active Campaigns
    try:
        await client.get_active_campaigns()
        results["Active Campaigns"] = True
    except Exception as e:
        results["Active Campaigns"] = False
        print(f"Active Campaigns FAILED: {e}")

    # Test 5: List Management
    try:
        await client.list_all_lists()
        results["List Management"] = True
    except Exception as e:
        results["List Management"] = False
        print(f"List Management FAILED: {e}")

    # Test 6: Conversations
    try:
        await client.get_conversations()
        results["Conversations"] = True
    except Exception as e:
        results["Conversations"] = False
        print(f"Conversations FAILED: {e}")

    # Test 7: Overall Stats
    try:
        await client.get_overall_stats()
        results["Overall Stats"] = True
    except Exception as e:
        results["Overall Stats"] = False
        print(f"Overall Stats FAILED: {e}")

    # Test 8: Future-Proof call_endpoint
    try:
        await client.call_endpoint("/auth/CheckApiKey", method="GET")
        results["Future-Proof call_endpoint"] = True
    except Exception as e:
        results["Future-Proof call_endpoint"] = False
        print(f"Future-Proof call_endpoint FAILED: {e}")

    await client.close()

    # Print Summary
    print("\nResults:")
    all_passed = True
    for endpoint, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {endpoint}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    assert all_passed, "Some endpoints failed - see details above"
    print("\n*** ALL ENDPOINTS PASSED 100% ***")
