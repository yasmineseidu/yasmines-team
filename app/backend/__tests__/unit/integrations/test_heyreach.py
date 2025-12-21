"""Unit tests for HeyReach LinkedIn Automation integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.base import IntegrationError
from src.integrations.heyreach import (
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    HeyReachClient,
    HeyReachError,
    Lead,
    LeadStatus,
    SocialActionType,
)

# Test API key constant (not a real secret)
TEST_API_KEY = "test-api-key"  # pragma: allowlist secret


class TestHeyReachClientInitialization:
    """Tests for HeyReachClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have correct integration name."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.name == "heyreach"

    def test_has_correct_base_url(self) -> None:
        """Client should use correct HeyReach API base URL."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.base_url == "https://api.heyreach.io/api/public"

    def test_has_correct_api_version(self) -> None:
        """Client should have correct API version."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.API_VERSION == "V1"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.api_key == TEST_API_KEY

    def test_default_timeout(self) -> None:
        """Client should have default 30s timeout."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = HeyReachClient(api_key=TEST_API_KEY, timeout=60.0)
        assert client.timeout == 60.0

    def test_default_max_retries(self) -> None:
        """Client should have default 3 retries."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        assert client.max_retries == 3

    def test_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = HeyReachClient(api_key=TEST_API_KEY, max_retries=5)
        assert client.max_retries == 5


class TestHeyReachClientHeaders:
    """Tests for HeyReachClient headers."""

    def test_get_headers_uses_x_api_key(self) -> None:
        """Headers should use X-API-KEY instead of Bearer token."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        headers = client._get_headers()

        assert "X-API-KEY" in headers
        assert headers["X-API-KEY"] == "test-api-key"

    def test_get_headers_has_content_type(self) -> None:
        """Headers should include Content-Type."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"

    def test_get_headers_has_accept(self) -> None:
        """Headers should include Accept."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        headers = client._get_headers()

        assert headers["Accept"] == "application/json"

    def test_no_authorization_bearer_header(self) -> None:
        """Headers should not have Bearer Authorization."""
        client = HeyReachClient(api_key=TEST_API_KEY)
        headers = client._get_headers()

        assert "Authorization" not in headers


class TestHeyReachClientCheckApiKey:
    """Tests for check_api_key method."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_check_api_key_success(self, client: HeyReachClient) -> None:
        """Should return True for valid API key."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"success": True, "data": True}

            result = await client.check_api_key()

            assert result is True
            mock_get.assert_called_once_with("/auth/CheckApiKey")

    @pytest.mark.asyncio
    async def test_check_api_key_failure(self, client: HeyReachClient) -> None:
        """Should return False for invalid API key."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"success": False, "data": False}

            result = await client.check_api_key()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_api_key_raises_on_error(self, client: HeyReachClient) -> None:
        """Should raise HeyReachError on API error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Auth failed", status_code=401)

            with pytest.raises(HeyReachError) as exc_info:
                await client.check_api_key()

            assert exc_info.value.status_code == 401


class TestHeyReachClientHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: HeyReachClient) -> None:
        """Should return healthy status when API key is valid."""
        with patch.object(client, "check_api_key", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            result = await client.health_check()

            assert result["name"] == "heyreach"
            assert result["healthy"] is True
            assert result["api_key_valid"] is True
            assert result["api_version"] == "V1"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: HeyReachClient) -> None:
        """Should return unhealthy status on error."""
        with patch.object(client, "check_api_key", new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Connection failed")

            result = await client.health_check()

            assert result["name"] == "heyreach"
            assert result["healthy"] is False
            assert "error" in result


class TestHeyReachClientCampaigns:
    """Tests for campaign management methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, client: HeyReachClient) -> None:
        """Should return list of campaigns."""
        mock_response = {
            "items": [
                {
                    "id": "campaign-1",
                    "name": "Q1 Outreach",
                    "status": "ACTIVE",
                    "createdAt": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "campaign-2",
                    "name": "Q2 Outreach",
                    "status": "DRAFT",
                },
            ]
        }

        # list_campaigns now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            campaigns = await client.list_campaigns(limit=50, offset=0)

            assert len(campaigns) == 2
            assert campaigns[0].id == "campaign-1"
            assert campaigns[0].name == "Q1 Outreach"
            assert campaigns[0].status == CampaignStatus.ACTIVE
            assert campaigns[1].status == CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_list_campaigns_with_items_wrapper(self, client: HeyReachClient) -> None:
        """Should handle response wrapped in items key."""
        mock_response = {
            "items": [{"id": "campaign-1", "name": "Test", "status": "ACTIVE"}],
            "total": 1,
        }

        # list_campaigns now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            campaigns = await client.list_campaigns()

            assert len(campaigns) == 1
            assert campaigns[0].id == "campaign-1"

    @pytest.mark.asyncio
    async def test_list_campaigns_raises_on_error(self, client: HeyReachClient) -> None:
        """Should raise HeyReachError on API error."""
        # list_campaigns now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Failed", status_code=500)

            with pytest.raises(HeyReachError):
                await client.list_campaigns()

    @pytest.mark.asyncio
    async def test_get_campaign_success(self, client: HeyReachClient) -> None:
        """Should return single campaign details."""
        mock_response = {
            "id": "campaign-1",
            "name": "Q1 Outreach",
            "status": "ACTIVE",
            "description": "Test campaign",
            "campaignAccountIds": ["acc-1", "acc-2"],
        }

        # get_campaign now uses /campaign/GetById with query param
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            campaign = await client.get_campaign("campaign-1")

            assert campaign.id == "campaign-1"
            assert campaign.description == "Test campaign"
            assert campaign.account_ids == ["acc-1", "acc-2"]
            mock_get.assert_called_once_with(
                "/campaign/GetById", params={"campaignId": "campaign-1"}
            )

    @pytest.mark.asyncio
    async def test_get_active_campaigns(self, client: HeyReachClient) -> None:
        """Should return only active campaigns."""
        with patch.object(client, "list_campaigns", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                Campaign(id="1", name="Active", status=CampaignStatus.ACTIVE),
                Campaign(id="2", name="Paused", status=CampaignStatus.PAUSED),
                Campaign(id="3", name="Draft", status=CampaignStatus.DRAFT),
            ]

            active = await client.get_active_campaigns()

            assert len(active) == 1
            assert active[0].id == "1"

    @pytest.mark.asyncio
    async def test_create_campaign_success(self, client: HeyReachClient) -> None:
        """Should create new campaign."""
        mock_response = {
            "id": "new-campaign",
            "name": "New Campaign",
            "status": "DRAFT",
            "description": "Test description",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            campaign = await client.create_campaign(
                name="New Campaign",
                description="Test description",
            )

            assert campaign.id == "new-campaign"
            assert campaign.name == "New Campaign"
            assert campaign.status == CampaignStatus.DRAFT
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_campaign_success(self, client: HeyReachClient) -> None:
        """Should pause active campaign."""
        mock_response = {"id": "campaign-1", "name": "Test", "status": "PAUSED"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            campaign = await client.pause_campaign("campaign-1")

            assert campaign.status == CampaignStatus.PAUSED
            mock_post.assert_called_once_with(
                "/campaign/Pause", params={"campaignId": "campaign-1"}
            )

    @pytest.mark.asyncio
    async def test_resume_campaign_success(self, client: HeyReachClient) -> None:
        """Should resume paused campaign."""
        mock_response = {"id": "campaign-1", "name": "Test", "status": "ACTIVE"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            campaign = await client.resume_campaign("campaign-1")

            assert campaign.status == CampaignStatus.ACTIVE
            mock_post.assert_called_once_with(
                "/campaign/Resume", params={"campaignId": "campaign-1"}
            )


class TestHeyReachClientLeads:
    """Tests for lead management methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_add_leads_to_campaign_success(self, client: HeyReachClient) -> None:
        """Should add leads to campaign successfully."""
        mock_response = {
            "success": True,
            "addedCount": 2,
            "failedCount": 0,
            "failedLeads": [],
        }

        leads = [
            {
                "firstName": "John",
                "lastName": "Doe",
                "profileUrl": "https://linkedin.com/in/johndoe",
            },
            {
                "firstName": "Jane",
                "lastName": "Smith",
                "profileUrl": "https://linkedin.com/in/janesmith",
            },
        ]

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.add_leads_to_campaign("campaign-1", leads)

            assert result.success is True
            assert result.added_count == 2
            assert result.failed_count == 0
            mock_post.assert_called_once_with(
                "/campaign/AddLeadsToCampaignV2",
                json={"campaignId": "campaign-1", "leads": leads},
            )

    @pytest.mark.asyncio
    async def test_add_leads_to_campaign_with_failures(self, client: HeyReachClient) -> None:
        """Should handle partial failures in bulk add."""
        mock_response = {
            "success": True,
            "addedCount": 1,
            "failedCount": 1,
            "failedLeads": [{"email": "invalid@email", "reason": "Invalid LinkedIn URL"}],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.add_leads_to_campaign("campaign-1", [{"email": "test@test.com"}])

            assert result.success is True
            assert result.added_count == 1
            assert result.failed_count == 1
            assert len(result.failed_leads) == 1

    @pytest.mark.asyncio
    async def test_get_campaign_leads_success(self, client: HeyReachClient) -> None:
        """Should retrieve leads from campaign."""
        mock_response = {
            "items": [
                {
                    "id": "lead-1",
                    "firstName": "John",
                    "lastName": "Doe",
                    "profileUrl": "https://linkedin.com/in/johndoe",
                    "companyName": "Acme Inc",
                    "position": "CEO",
                    "status": "contacted",
                },
            ]
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            leads = await client.get_campaign_leads("campaign-1", page=1, limit=50)

            assert len(leads) == 1
            assert leads[0].first_name == "John"
            assert leads[0].full_name == "John Doe"
            assert leads[0].linkedin_url == "https://linkedin.com/in/johndoe"
            assert leads[0].status == LeadStatus.CONTACTED

    @pytest.mark.asyncio
    async def test_get_lead_details_success(self, client: HeyReachClient) -> None:
        """Should retrieve lead details by LinkedIn URL."""
        mock_response = {
            "id": "lead-1",
            "firstName": "John",
            "lastName": "Doe",
            "profileUrl": "https://linkedin.com/in/johndoe",
            "emailAddress": "john@example.com",
            "summary": "CEO at Acme",
            "customUserFields": [{"name": "industry", "value": "Technology"}],
        }

        # get_lead_details now uses POST /lead/GetLead
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            lead = await client.get_lead_details("https://linkedin.com/in/johndoe")

            assert lead.first_name == "John"
            assert lead.email == "john@example.com"
            assert lead.summary == "CEO at Acme"
            assert lead.custom_fields["industry"] == "Technology"

    @pytest.mark.asyncio
    async def test_update_lead_status_success(self, client: HeyReachClient) -> None:
        """Should update lead status."""
        mock_response = {
            "id": "lead-1",
            "firstName": "John",
            "status": "connected",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            lead = await client.update_lead_status("lead-1", LeadStatus.CONNECTED)

            assert lead.status == LeadStatus.CONNECTED
            mock_post.assert_called_once_with(
                "/lead/UpdateStatus",
                json={"leadId": "lead-1", "status": "connected"},
            )


class TestHeyReachClientLists:
    """Tests for list management methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_list_all_lists_success(self, client: HeyReachClient) -> None:
        """Should retrieve all lead lists."""
        mock_response = {
            "items": [
                {"id": "list-1", "name": "CEO List", "type": "lead", "leadCount": 100},
                {"id": "list-2", "name": "Company List", "type": "company", "leadCount": 50},
            ]
        }

        # list_all_lists now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            lists = await client.list_all_lists()

            assert len(lists) == 2
            assert lists[0].id == "list-1"
            assert lists[0].name == "CEO List"
            assert lists[0].list_type == "lead"
            assert lists[0].lead_count == 100

    @pytest.mark.asyncio
    async def test_create_empty_list_success(self, client: HeyReachClient) -> None:
        """Should create empty lead list."""
        mock_response = {"id": "new-list", "name": "New List", "type": "lead", "leadCount": 0}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            lead_list = await client.create_empty_list("New List", list_type="lead")

            assert lead_list.id == "new-list"
            assert lead_list.name == "New List"
            assert lead_list.lead_count == 0
            mock_post.assert_called_once_with(
                "/list/CreateEmptyList", json={"name": "New List", "type": "lead"}
            )

    @pytest.mark.asyncio
    async def test_add_leads_to_list_success(self, client: HeyReachClient) -> None:
        """Should add leads to list."""
        mock_response = {"success": True, "addedCount": 5, "failedCount": 0}

        leads = [{"firstName": "Test", "profileUrl": "https://linkedin.com/in/test"}]

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.add_leads_to_list(123, leads)

            assert result.success is True
            assert result.added_count == 5


class TestHeyReachClientMessaging:
    """Tests for messaging methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_send_message_success(self, client: HeyReachClient) -> None:
        """Should send message to lead."""
        mock_response = {"messageId": "msg-123", "status": "sent"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.send_message("lead-1", "Hello, nice to connect!")

            assert result["messageId"] == "msg-123"
            mock_post.assert_called_once_with(
                "/message/Send",
                json={"leadId": "lead-1", "message": "Hello, nice to connect!"},
            )

    @pytest.mark.asyncio
    async def test_send_message_with_template(self, client: HeyReachClient) -> None:
        """Should send message using template."""
        mock_response = {"messageId": "msg-123"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.send_message("lead-1", "Hello!", template_id="template-1")

            mock_post.assert_called_once_with(
                "/message/Send",
                json={
                    "leadId": "lead-1",
                    "message": "Hello!",
                    "templateId": "template-1",
                },
            )

    @pytest.mark.asyncio
    async def test_get_templates_success(self, client: HeyReachClient) -> None:
        """Should retrieve message templates."""
        mock_response = {
            "items": [
                {
                    "id": "template-1",
                    "name": "Introduction",
                    "content": "Hi {{firstName}}, nice to connect!",
                    "type": "connection",
                    "variables": ["firstName"],
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            templates = await client.get_templates()

            assert len(templates) == 1
            assert templates[0].id == "template-1"
            assert templates[0].name == "Introduction"
            assert "firstName" in templates[0].variables

    @pytest.mark.asyncio
    async def test_get_conversations_success(self, client: HeyReachClient) -> None:
        """Should retrieve conversations."""
        mock_response = {
            "items": [
                {
                    "id": "conv-1",
                    "leadId": "lead-1",
                    "linkedinUrl": "https://linkedin.com/in/johndoe",
                    "lastMessage": "Thanks for connecting!",
                    "messageCount": 3,
                },
            ]
        }

        # get_conversations now uses POST /inbox/GetConversationsV2
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            conversations = await client.get_conversations()

            assert len(conversations) == 1
            assert conversations[0].lead_id == "lead-1"
            assert conversations[0].message_count == 3


class TestHeyReachClientSocialActions:
    """Tests for social action methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_perform_social_action_like(self, client: HeyReachClient) -> None:
        """Should perform like action."""
        mock_response = {
            "id": "action-1",
            "type": "like",
            "status": "scheduled",
            "targetUrl": "https://linkedin.com/posts/123",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            action = await client.perform_social_action(
                SocialActionType.LIKE,
                "https://linkedin.com/posts/123",
            )

            assert action.id == "action-1"
            assert action.action_type == SocialActionType.LIKE
            assert action.status == "scheduled"

    @pytest.mark.asyncio
    async def test_perform_social_action_with_lead(self, client: HeyReachClient) -> None:
        """Should perform action with lead association."""
        mock_response = {"id": "action-1", "type": "follow", "status": "completed"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.perform_social_action(
                SocialActionType.FOLLOW,
                "https://linkedin.com/in/johndoe",
                lead_id="lead-1",
            )

            mock_post.assert_called_once_with(
                "/social/Action",
                json={
                    "action": "follow",
                    "targetUrl": "https://linkedin.com/in/johndoe",
                    "leadId": "lead-1",
                },
            )


class TestHeyReachClientAnalytics:
    """Tests for analytics methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_get_campaign_analytics_success(self, client: HeyReachClient) -> None:
        """Should retrieve campaign analytics."""
        mock_response = {
            "totalLeads": 100,
            "contacted": 80,
            "replied": 20,
            "connected": 15,
            "responseRate": 25.0,
            "connectionRate": 18.75,
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            analytics = await client.get_campaign_analytics("campaign-1")

            assert analytics.campaign_id == "campaign-1"
            assert analytics.total_leads == 100
            assert analytics.contacted == 80
            assert analytics.replied == 20
            assert analytics.connected == 15
            assert analytics.response_rate == 25.0
            mock_get.assert_called_once_with("/analytics/campaign/campaign-1")

    @pytest.mark.asyncio
    async def test_campaign_analytics_engagement_rate(self) -> None:
        """Should calculate engagement rate correctly."""
        analytics = CampaignAnalytics(
            campaign_id="test",
            total_leads=100,
            contacted=80,
            replied=20,
            connected=15,
        )

        # (20 + 15) / 80 * 100 = 43.75%
        assert analytics.engagement_rate == 43.75

    @pytest.mark.asyncio
    async def test_campaign_analytics_engagement_rate_zero_contacted(self) -> None:
        """Should handle zero contacted in engagement rate."""
        analytics = CampaignAnalytics(
            campaign_id="test",
            total_leads=100,
            contacted=0,
        )

        assert analytics.engagement_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_overall_stats_success(self, client: HeyReachClient) -> None:
        """Should retrieve overall account stats."""
        # get_overall_stats now fetches campaigns first to get IDs
        mock_campaigns_response = {
            "items": [
                {
                    "id": "campaign-1",
                    "name": "Test",
                    "status": "ACTIVE",
                    "campaignAccountIds": ["acc-1"],
                },
            ]
        }
        mock_stats_response = {
            "overallStats": {
                "profileViews": 100,
                "messagesSent": 50,
                "connectionsSent": 25,
            },
            "byDayStats": {},
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            # First call is list_campaigns, second call is get_overall_stats
            mock_post.side_effect = [
                mock_campaigns_response,
                mock_campaigns_response,
                mock_stats_response,
            ]

            stats = await client.get_overall_stats()

            assert "overallStats" in stats
            assert stats["overallStats"]["profileViews"] == 100


class TestHeyReachClientCallEndpoint:
    """Tests for dynamic endpoint calling."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: HeyReachClient) -> None:
        """Should call endpoint with GET method."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"data": "response"}

            result = await client.call_endpoint("/new-endpoint", method="GET")

            assert result["data"] == "response"
            mock_request.assert_called_once_with("GET", "/new-endpoint")

    @pytest.mark.asyncio
    async def test_call_endpoint_post_with_json(self, client: HeyReachClient) -> None:
        """Should call endpoint with POST and JSON body."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"success": True}

            result = await client.call_endpoint(
                "/new-endpoint",
                method="POST",
                json={"key": "value"},
            )

            assert result["success"] is True
            mock_request.assert_called_once_with("POST", "/new-endpoint", json={"key": "value"})

    @pytest.mark.asyncio
    async def test_call_endpoint_raises_heyreach_error(self, client: HeyReachClient) -> None:
        """Should raise HeyReachError on failure."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = IntegrationError("Failed", status_code=500)

            with pytest.raises(HeyReachError) as exc_info:
                await client.call_endpoint("/bad-endpoint")

            assert exc_info.value.status_code == 500


class TestCampaignDataclass:
    """Tests for Campaign dataclass."""

    def test_is_active_true(self) -> None:
        """Should return True when status is ACTIVE."""
        campaign = Campaign(id="1", name="Test", status=CampaignStatus.ACTIVE)
        assert campaign.is_active is True

    def test_is_active_false(self) -> None:
        """Should return False when status is not ACTIVE."""
        campaign = Campaign(id="1", name="Test", status=CampaignStatus.PAUSED)
        assert campaign.is_active is False

    def test_is_paused_true(self) -> None:
        """Should return True when status is PAUSED."""
        campaign = Campaign(id="1", name="Test", status=CampaignStatus.PAUSED)
        assert campaign.is_paused is True

    def test_is_draft_true(self) -> None:
        """Should return True when status is DRAFT."""
        campaign = Campaign(id="1", name="Test", status=CampaignStatus.DRAFT)
        assert campaign.is_draft is True


class TestLeadDataclass:
    """Tests for Lead dataclass."""

    def test_full_name_both_names(self) -> None:
        """Should return full name when both names present."""
        lead = Lead(first_name="John", last_name="Doe")
        assert lead.full_name == "John Doe"

    def test_full_name_first_only(self) -> None:
        """Should return first name only when last name missing."""
        lead = Lead(first_name="John")
        assert lead.full_name == "John"

    def test_full_name_last_only(self) -> None:
        """Should return last name when first name missing."""
        lead = Lead(last_name="Doe")
        assert lead.full_name == "Doe"

    def test_full_name_none(self) -> None:
        """Should return None when no names present."""
        lead = Lead()
        assert lead.full_name is None

    def test_profile_url_alias(self) -> None:
        """Should return linkedin_url from profile_url property."""
        lead = Lead(linkedin_url="https://linkedin.com/in/test")
        assert lead.profile_url == "https://linkedin.com/in/test"


class TestParseMethods:
    """Tests for parsing methods."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    def test_parse_campaign_with_timestamps(self, client: HeyReachClient) -> None:
        """Should parse campaign with timestamps."""
        data = {
            "id": "123",
            "name": "Test Campaign",
            "status": "ACTIVE",
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-20T15:45:00Z",
        }

        campaign = client._parse_campaign(data)

        assert campaign.id == "123"
        assert campaign.created_at is not None
        assert campaign.updated_at is not None

    def test_parse_campaign_invalid_status(self, client: HeyReachClient) -> None:
        """Should default to DRAFT for invalid status."""
        data = {"id": "123", "name": "Test", "status": "UNKNOWN_STATUS"}

        campaign = client._parse_campaign(data)

        assert campaign.status == CampaignStatus.DRAFT

    def test_parse_lead_with_custom_fields(self, client: HeyReachClient) -> None:
        """Should parse lead with custom fields."""
        data = {
            "id": "lead-1",
            "firstName": "John",
            "customUserFields": [
                {"name": "industry", "value": "Tech"},
                {"name": "company_size", "value": "50-100"},
            ],
        }

        lead = client._parse_lead(data)

        assert lead.custom_fields["industry"] == "Tech"
        assert lead.custom_fields["company_size"] == "50-100"

    def test_parse_lead_alternative_field_names(self, client: HeyReachClient) -> None:
        """Should handle alternative field names (snake_case)."""
        data = {
            "id": "lead-1",
            "first_name": "John",
            "last_name": "Doe",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "company_name": "Acme",
        }

        lead = client._parse_lead(data)

        assert lead.first_name == "John"
        assert lead.last_name == "Doe"
        assert lead.linkedin_url == "https://linkedin.com/in/johndoe"
        assert lead.company_name == "Acme"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> HeyReachClient:
        """Create client for testing."""
        return HeyReachClient(api_key=TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_raises_heyreach_error_on_auth_failure(self, client: HeyReachClient) -> None:
        """Should raise HeyReachError with status code on auth failure."""
        # list_campaigns now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError(
                "Unauthorized", status_code=401, response_data={"error": "Invalid key"}
            )

            with pytest.raises(HeyReachError) as exc_info:
                await client.list_campaigns()

            assert exc_info.value.status_code == 401
            assert "Invalid key" in str(exc_info.value.response_data)

    @pytest.mark.asyncio
    async def test_raises_heyreach_error_on_rate_limit(self, client: HeyReachClient) -> None:
        """Should raise HeyReachError on rate limit."""
        # list_campaigns now uses POST
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Rate limited", status_code=429)

            with pytest.raises(HeyReachError) as exc_info:
                await client.list_campaigns()

            assert exc_info.value.status_code == 429


class TestHeyReachError:
    """Tests for HeyReachError exception."""

    def test_inherits_from_integration_error(self) -> None:
        """HeyReachError should inherit from IntegrationError."""
        error = HeyReachError("Test error")
        assert isinstance(error, IntegrationError)

    def test_stores_status_code(self) -> None:
        """Should store status code."""
        error = HeyReachError("Test error", status_code=400)
        assert error.status_code == 400

    def test_stores_response_data(self) -> None:
        """Should store response data."""
        error = HeyReachError("Test error", response_data={"detail": "Bad request"})
        assert error.response_data["detail"] == "Bad request"
