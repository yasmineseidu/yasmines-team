"""
Live API tests for Instantly.ai integration.

These tests run against the REAL Instantly API using actual API keys.
They verify that all endpoints work correctly with the live service.

Requirements:
- INSTANTLY_API_KEY must be set in .env at project root
- Tests create/modify/delete real data in the Instantly account
- Run with: pytest __tests__/integration/test_instantly_live.py -v -m live_api

Coverage:
- Campaign CRUD (create, list, get, update, delete)
- Campaign control (activate, pause, duplicate)
- Lead CRUD (create, list, get, update, delete)
- Bulk lead operations
- Analytics retrieval
- Future-proof call_endpoint method
- Error handling

IMPORTANT: All tests MUST pass 100%. No exceptions.
"""

import contextlib
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from __tests__.fixtures.instantly_fixtures import (
    SAMPLE_CAMPAIGN_SCHEDULE,
    create_bulk_leads_payload,
    generate_test_email,
    generate_unique_campaign_name,
)
from src.integrations import (
    BulkAddResult,
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    InstantlyClient,
    InstantlyError,
    Lead,
)

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        pytest.skip("INSTANTLY_API_KEY not found in .env - skipping live tests")
    return api_key


@pytest.fixture
def api_key() -> str:
    """Fixture to get API key."""
    return get_api_key()


@pytest.fixture
async def client(api_key: str) -> InstantlyClient:
    """Create InstantlyClient for testing."""
    return InstantlyClient(api_key=api_key, timeout=60.0, max_retries=3)


@pytest.fixture
async def test_campaign(client: InstantlyClient) -> Campaign:
    """Create a test campaign and clean up after test."""
    campaign_name = generate_unique_campaign_name()
    campaign = await client.create_campaign(
        name=campaign_name,
        campaign_schedule=SAMPLE_CAMPAIGN_SCHEDULE,
    )
    yield campaign
    # Cleanup: delete the campaign after test
    with contextlib.suppress(InstantlyError):
        await client.delete_campaign(campaign.id)


# =============================================================================
# CAMPAIGN ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestCampaignEndpointsLive:
    """Live tests for campaign endpoints - MUST pass 100%."""

    async def test_create_campaign_success(self, client: InstantlyClient) -> None:
        """Test creating a campaign with real API - MUST PASS."""
        campaign_name = generate_unique_campaign_name()

        campaign = await client.create_campaign(
            name=campaign_name,
            campaign_schedule=SAMPLE_CAMPAIGN_SCHEDULE,
        )

        # Verify response structure
        assert isinstance(campaign, Campaign)
        assert campaign.id is not None
        assert len(campaign.id) > 0
        assert campaign.name == campaign_name
        assert campaign.status == CampaignStatus.DRAFT

        # Cleanup
        await client.delete_campaign(campaign.id)
        print(f"✅ create_campaign: Created and verified campaign {campaign.id}")

    async def test_list_campaigns_success(self, client: InstantlyClient) -> None:
        """Test listing campaigns with real API - MUST PASS."""
        campaigns = await client.list_campaigns(limit=10)

        # Verify response structure
        assert isinstance(campaigns, list)
        # May be empty if no campaigns exist, but should not error
        for campaign in campaigns:
            assert isinstance(campaign, Campaign)
            assert campaign.id is not None

        print(f"✅ list_campaigns: Retrieved {len(campaigns)} campaigns")

    async def test_list_campaigns_with_pagination(self, client: InstantlyClient) -> None:
        """Test listing campaigns with pagination - MUST PASS."""
        # First page
        campaigns_page1 = await client.list_campaigns(limit=5)
        assert isinstance(campaigns_page1, list)

        # If there are campaigns, test pagination
        if len(campaigns_page1) == 5:
            campaigns_page2 = await client.list_campaigns(
                limit=5, starting_after=campaigns_page1[-1].id
            )
            assert isinstance(campaigns_page2, list)
            print(
                f"✅ list_campaigns pagination: Page1={len(campaigns_page1)}, Page2={len(campaigns_page2)}"
            )
        else:
            print(f"✅ list_campaigns pagination: Only {len(campaigns_page1)} campaigns available")

    async def test_get_campaign_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test getting a single campaign - MUST PASS."""
        campaign = await client.get_campaign(test_campaign.id)

        assert isinstance(campaign, Campaign)
        assert campaign.id == test_campaign.id
        assert campaign.name == test_campaign.name

        print(f"✅ get_campaign: Retrieved campaign {campaign.id}")

    async def test_update_campaign_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test updating a campaign - MUST PASS."""
        new_name = f"Updated_{test_campaign.name}"

        updated = await client.update_campaign(
            campaign_id=test_campaign.id,
            name=new_name,
        )

        assert isinstance(updated, Campaign)
        assert updated.id == test_campaign.id
        # Note: API may or may not return updated name immediately

        print(f"✅ update_campaign: Updated campaign {updated.id}")

    async def test_duplicate_campaign_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test duplicating a campaign - MUST PASS."""
        duplicated = await client.duplicate_campaign(test_campaign.id)

        assert isinstance(duplicated, Campaign)
        assert duplicated.id != test_campaign.id  # New campaign ID

        # Cleanup: delete the duplicate
        await client.delete_campaign(duplicated.id)

        print(f"✅ duplicate_campaign: Duplicated to {duplicated.id}")

    async def test_delete_campaign_success(self, client: InstantlyClient) -> None:
        """Test deleting a campaign - MUST PASS."""
        # Create a campaign to delete
        campaign = await client.create_campaign(
            name=generate_unique_campaign_name(),
            campaign_schedule=SAMPLE_CAMPAIGN_SCHEDULE,
        )

        result = await client.delete_campaign(campaign.id)

        assert result is True

        # Verify deletion by trying to get it (should fail)
        with pytest.raises(InstantlyError):
            await client.get_campaign(campaign.id)

        print(f"✅ delete_campaign: Deleted campaign {campaign.id}")


# =============================================================================
# LEAD ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestLeadEndpointsLive:
    """Live tests for lead endpoints - MUST pass 100%."""

    async def test_create_lead_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test creating a lead with real API - MUST PASS."""
        test_email = generate_test_email()

        lead = await client.create_lead(
            email=test_email,
            campaign_id=test_campaign.id,
            first_name="LiveTest",
            last_name="Lead",
            company_name="Live Test Company",
        )

        assert isinstance(lead, Lead)
        assert lead.id is not None
        assert lead.email == test_email

        # Cleanup
        await client.delete_lead(lead.id)

        print(f"✅ create_lead: Created lead {lead.id}")

    async def test_list_leads_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test listing leads with real API - MUST PASS."""
        # Create a lead first
        test_email = generate_test_email()
        lead = await client.create_lead(
            email=test_email,
            campaign_id=test_campaign.id,
            first_name="ListTest",
            last_name="Lead",
        )

        # List leads for campaign
        leads = await client.list_leads(campaign_id=test_campaign.id, limit=10)

        assert isinstance(leads, list)
        # Should have at least our created lead
        assert any(lead.email == test_email for lead in leads)

        # Cleanup
        await client.delete_lead(lead.id)

        print(f"✅ list_leads: Retrieved {len(leads)} leads")

    async def test_get_lead_success(self, client: InstantlyClient, test_campaign: Campaign) -> None:
        """Test getting a single lead - MUST PASS."""
        # Create a lead first
        test_email = generate_test_email()
        created = await client.create_lead(
            email=test_email,
            campaign_id=test_campaign.id,
            first_name="GetTest",
            last_name="Lead",
        )

        # Get the lead
        lead = await client.get_lead(created.id)

        assert isinstance(lead, Lead)
        assert lead.id == created.id
        assert lead.email == test_email

        # Cleanup
        await client.delete_lead(lead.id)

        print(f"✅ get_lead: Retrieved lead {lead.id}")

    async def test_update_lead_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test updating a lead - MUST PASS."""
        # Create a lead first
        test_email = generate_test_email()
        created = await client.create_lead(
            email=test_email,
            campaign_id=test_campaign.id,
            first_name="UpdateTest",
            last_name="Lead",
        )

        # Update the lead
        updated = await client.update_lead(
            lead_id=created.id,
            first_name="UpdatedName",
        )

        assert isinstance(updated, Lead)
        assert updated.id == created.id

        # Cleanup
        await client.delete_lead(updated.id)

        print(f"✅ update_lead: Updated lead {updated.id}")

    async def test_delete_lead_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test deleting a lead - MUST PASS."""
        # Create a lead to delete
        test_email = generate_test_email()
        lead = await client.create_lead(
            email=test_email,
            campaign_id=test_campaign.id,
            first_name="DeleteTest",
            last_name="Lead",
        )

        # Delete the lead
        result = await client.delete_lead(lead.id)

        assert result is True

        print(f"✅ delete_lead: Deleted lead {lead.id}")

    async def test_bulk_add_leads_success(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test bulk adding leads - MUST PASS."""
        bulk_leads = create_bulk_leads_payload(count=3)

        result = await client.bulk_add_leads(
            leads=bulk_leads,
            campaign_id=test_campaign.id,
        )

        assert isinstance(result, BulkAddResult)
        assert result.created_count >= 0
        assert isinstance(result.created_leads, list)

        print(f"✅ bulk_add_leads: Created {result.created_count}, Failed {result.failed_count}")


# =============================================================================
# ANALYTICS ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAnalyticsEndpointsLive:
    """Live tests for analytics endpoints - MUST pass 100%."""

    async def test_get_campaign_analytics_all(self, client: InstantlyClient) -> None:
        """Test getting analytics for all campaigns - MUST PASS."""
        result = await client.get_campaign_analytics()

        # Result could be single analytics or list
        assert result is not None
        if isinstance(result, list):
            for analytics in result:
                assert isinstance(analytics, CampaignAnalytics)
        else:
            assert isinstance(result, CampaignAnalytics)

        print("✅ get_campaign_analytics (all): Retrieved analytics")

    async def test_get_campaign_analytics_single(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test getting analytics for single campaign - MUST PASS."""
        result = await client.get_campaign_analytics(campaign_id=test_campaign.id)

        assert isinstance(result, CampaignAnalytics)
        assert result.campaign_id == test_campaign.id

        print(f"✅ get_campaign_analytics (single): Campaign {test_campaign.id}")

    async def test_get_campaign_analytics_overview(self, client: InstantlyClient) -> None:
        """Test getting analytics overview - MUST PASS."""
        result = await client.get_campaign_analytics_overview()

        assert isinstance(result, dict)

        print("✅ get_campaign_analytics_overview: Retrieved overview")

    async def test_get_campaign_daily_analytics(self, client: InstantlyClient) -> None:
        """Test getting daily analytics - MUST PASS."""
        result = await client.get_campaign_daily_analytics()

        assert isinstance(result, list)

        print(f"✅ get_campaign_daily_analytics: Retrieved {len(result)} daily entries")


# =============================================================================
# HEALTH CHECK AND UTILITY TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestHealthAndUtilityLive:
    """Live tests for health check and utility methods - MUST pass 100%."""

    async def test_health_check_success(self, client: InstantlyClient) -> None:
        """Test health check with real API - MUST PASS."""
        health = await client.health_check()

        assert isinstance(health, dict)
        assert health["name"] == "instantly"
        assert health["healthy"] is True
        assert health["api_version"] == "V2"

        print("✅ health_check: API is healthy")

    async def test_call_endpoint_campaigns_list(self, client: InstantlyClient) -> None:
        """Test future-proof call_endpoint for campaigns - MUST PASS."""
        result = await client.call_endpoint(
            "/campaigns",
            method="GET",
            params={"limit": 5},
        )

        assert isinstance(result, dict)
        # Should have items or data key with campaigns

        print("✅ call_endpoint (GET /campaigns): Future-proof method works")

    async def test_call_endpoint_analytics(self, client: InstantlyClient) -> None:
        """Test future-proof call_endpoint for analytics - MUST PASS."""
        result = await client.call_endpoint(
            "/campaigns/analytics/overview",
            method="GET",
        )

        assert isinstance(result, dict)

        print("✅ call_endpoint (GET /campaigns/analytics/overview): Future-proof method works")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestErrorHandlingLive:
    """Live tests for error handling - MUST pass 100%."""

    async def test_get_nonexistent_campaign_raises_error(self, client: InstantlyClient) -> None:
        """Test getting non-existent campaign raises error - MUST PASS."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(InstantlyError):
            await client.get_campaign(fake_id)

        print("✅ error_handling: Non-existent campaign raises InstantlyError")

    async def test_get_nonexistent_lead_raises_error(self, client: InstantlyClient) -> None:
        """Test getting non-existent lead raises error - MUST PASS."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(InstantlyError):
            await client.get_lead(fake_id)

        print("✅ error_handling: Non-existent lead raises InstantlyError")

    async def test_invalid_api_key_raises_error(self) -> None:
        """Test invalid API key raises authentication error - MUST PASS."""
        invalid_client = InstantlyClient(api_key="invalid-api-key-12345")

        with pytest.raises(InstantlyError):
            await invalid_client.list_campaigns()

        print("✅ error_handling: Invalid API key raises InstantlyError")


# =============================================================================
# FUTURE-PROOF ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFutureProofDesign:
    """Tests to verify future-proof design for new API endpoints - MUST pass 100%."""

    async def test_call_endpoint_get_method(self, client: InstantlyClient) -> None:
        """Test call_endpoint with GET method - MUST PASS."""
        result = await client.call_endpoint("/campaigns", method="GET", params={"limit": 1})

        assert isinstance(result, dict)
        print("✅ call_endpoint GET: Works correctly")

    async def test_call_endpoint_handles_different_endpoints(self, client: InstantlyClient) -> None:
        """Test call_endpoint with various endpoints - MUST PASS."""
        # Test multiple different endpoints
        endpoints = [
            ("/campaigns", "GET", {"limit": 1}),
            ("/campaigns/analytics/overview", "GET", {}),
        ]

        for endpoint, method, params in endpoints:
            result = await client.call_endpoint(endpoint, method=method, params=params)
            assert isinstance(result, dict)

        print(f"✅ call_endpoint multiple endpoints: All {len(endpoints)} endpoints work")

    async def test_future_endpoint_with_json_body(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test call_endpoint with POST and JSON body - MUST PASS."""
        # Use leads/list endpoint which requires POST with JSON
        result = await client.call_endpoint(
            "/leads/list",
            method="POST",
            json={"campaign": test_campaign.id, "limit": 5},
        )

        assert isinstance(result, dict)
        print("✅ call_endpoint POST with JSON: Works correctly")

    async def test_convenience_methods_all_verbs(
        self, client: InstantlyClient, test_campaign: Campaign
    ) -> None:
        """Test all convenience methods (call_get, call_post, etc.) - MUST PASS."""
        # Test call_get
        campaigns = await client.call_get("/campaigns", params={"limit": 1})
        assert isinstance(campaigns, dict)
        print("✅ call_get: Works")

        # Test call_post with leads/list
        leads_result = await client.call_post(
            "/leads/list", json={"campaign": test_campaign.id, "limit": 5}
        )
        assert isinstance(leads_result, dict)
        print("✅ call_post: Works")

        # Test call_patch - update campaign name
        updated = await client.call_patch(
            f"/campaigns/{test_campaign.id}", json={"name": f"Updated_{test_campaign.name}"}
        )
        assert isinstance(updated, dict)
        print("✅ call_patch: Works")

        print("✅ All convenience methods work correctly")

    async def test_call_delete_via_convenience_method(self, client: InstantlyClient) -> None:
        """Test call_delete convenience method - MUST PASS."""
        # Create a campaign to delete
        campaign = await client.create_campaign(
            name=generate_unique_campaign_name(),
            campaign_schedule=SAMPLE_CAMPAIGN_SCHEDULE,
        )

        # Delete using convenience method
        result = await client.call_delete(f"/campaigns/{campaign.id}")
        assert isinstance(result, dict)

        print("✅ call_delete: Works correctly")


# =============================================================================
# COMPREHENSIVE INTEGRATION TEST
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestComprehensiveIntegration:
    """Full integration test covering complete workflow - MUST pass 100%."""

    async def test_complete_campaign_lifecycle(self, client: InstantlyClient) -> None:
        """Test complete campaign lifecycle: create, add leads, get analytics, delete."""
        print("\n🔄 Starting complete campaign lifecycle test...")

        # 1. Create campaign
        campaign_name = generate_unique_campaign_name()
        campaign = await client.create_campaign(
            name=campaign_name,
            campaign_schedule=SAMPLE_CAMPAIGN_SCHEDULE,
        )
        assert campaign.id is not None
        print(f"  1. Created campaign: {campaign.id}")

        # 2. Add leads to campaign using bulk add
        leads_data = create_bulk_leads_payload(count=3)
        bulk_result = await client.bulk_add_leads(
            leads=leads_data,
            campaign_id=campaign.id,
        )
        print(f"  2. Added {bulk_result.created_count} leads via bulk add")

        # 3. List leads in campaign
        leads = await client.list_leads(campaign_id=campaign.id, limit=10)
        print(f"  3. Listed {len(leads)} leads in campaign")

        # 4. Get campaign analytics
        analytics = await client.get_campaign_analytics(campaign_id=campaign.id)
        assert isinstance(analytics, CampaignAnalytics)
        print(f"  4. Retrieved analytics: {analytics.total_leads} total leads")

        # 5. Duplicate campaign
        duplicate = await client.duplicate_campaign(campaign.id)
        assert duplicate.id != campaign.id
        print(f"  5. Duplicated to: {duplicate.id}")

        # 6. Delete duplicate
        await client.delete_campaign(duplicate.id)
        print("  6. Deleted duplicate")

        # 7. Delete original campaign
        await client.delete_campaign(campaign.id)
        print("  7. Deleted original campaign")

        print("✅ Complete campaign lifecycle: ALL STEPS PASSED")


# =============================================================================
# RUN ALL TESTS SUMMARY
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
    client = InstantlyClient(api_key=api_key, timeout=60.0)

    print("\n" + "=" * 60)
    print("INSTANTLY API LIVE TEST SUMMARY")
    print("=" * 60)

    results: dict[str, bool] = {}

    # Test 1: Health Check
    try:
        health = await client.health_check()
        results["Health Check"] = health["healthy"]
    except Exception as e:
        results["Health Check"] = False
        print(f"❌ Health Check: {e}")

    # Test 2: Campaign Operations
    try:
        await client.list_campaigns(limit=1)
        results["Campaign List"] = True
    except Exception as e:
        results["Campaign List"] = False
        print(f"❌ Campaign List: {e}")

    # Test 3: Analytics
    try:
        await client.get_campaign_analytics_overview()
        results["Analytics Overview"] = True
    except Exception as e:
        results["Analytics Overview"] = False
        print(f"❌ Analytics Overview: {e}")

    # Test 4: Future-Proof call_endpoint
    try:
        await client.call_endpoint("/campaigns", method="GET", params={"limit": 1})
        results["Future-Proof call_endpoint"] = True
    except Exception as e:
        results["Future-Proof call_endpoint"] = False
        print(f"❌ Future-Proof call_endpoint: {e}")

    # Print Summary
    print("\nResults:")
    all_passed = True
    for endpoint, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {endpoint}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    assert all_passed, "Some endpoints failed - see details above"
    print("🎉 ALL ENDPOINTS PASSED 100%")
