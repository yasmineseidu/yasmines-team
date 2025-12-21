"""
Unit tests for Instantly integration client.

Tests cover:
- Client initialization
- Campaign management (CRUD, activate, pause, duplicate)
- Lead management (CRUD, bulk add, move, interest status)
- Analytics retrieval
- Error handling (401, 402, 429, network errors)
- Health check functionality
- Dataclass properties and computed values

Coverage target: >90%
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations import (
    AuthenticationError,
    BackgroundJob,
    BulkAddResult,
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    InstantlyClient,
    InstantlyError,
    Lead,
    LeadInterestStatus,
    PaymentRequiredError,
    RateLimitError,
)


class TestInstantlyClientInitialization:
    """Tests for InstantlyClient initialization."""

    def test_client_has_correct_name(self) -> None:
        """Client should have 'instantly' as name."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "instantly"

    def test_client_has_correct_base_url(self) -> None:
        """Client should use V2 API base URL."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.instantly.ai/api/v2"

    def test_client_has_correct_api_version(self) -> None:
        """Client should report V2 API version."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.API_VERSION == "V2"

    def test_client_default_timeout_is_30_seconds(self) -> None:
        """Client should have 30s default timeout."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 30.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = InstantlyClient(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 retries by default."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = InstantlyClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = InstantlyClient(api_key="my-secret-key")  # pragma: allowlist secret
        assert client.api_key == "my-secret-key"  # pragma: allowlist secret


class TestInstantlyClientHeaders:
    """Tests for HTTP headers configuration."""

    def test_headers_include_bearer_token(self) -> None:
        """Headers should include Bearer token in Authorization."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = InstantlyClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestCreateCampaign:
    """Tests for create_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_create_campaign_success(self, client: InstantlyClient) -> None:
        """Should create campaign successfully."""
        mock_response = {
            "id": "camp-123",
            "name": "Q1 Outreach",
            "status": 0,
            "workspace_id": "ws-456",
            "created_at": "2025-01-15T10:00:00Z",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.create_campaign(
                name="Q1 Outreach",
                campaign_schedule={"schedules": []},
            )

            assert isinstance(result, Campaign)
            assert result.id == "camp-123"
            assert result.name == "Q1 Outreach"
            assert result.status == CampaignStatus.DRAFT

            mock_post.assert_called_once_with(
                "/campaigns",
                json={
                    "name": "Q1 Outreach",
                    "campaign_schedule": {"schedules": []},
                },
            )

    @pytest.mark.asyncio
    async def test_create_campaign_with_extra_params(self, client: InstantlyClient) -> None:
        """Should pass extra parameters to campaign creation."""
        mock_response = {
            "id": "camp-123",
            "name": "Test",
            "status": 0,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.create_campaign(
                name="Test",
                campaign_schedule={"schedules": []},
                custom_field="value",
            )

            call_args = mock_post.call_args
            assert call_args[1]["json"]["custom_field"] == "value"


class TestListCampaigns:
    """Tests for list_campaigns method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, client: InstantlyClient) -> None:
        """Should list campaigns successfully."""
        mock_response = {
            "items": [
                {"id": "camp-1", "name": "Campaign 1", "status": 1},
                {"id": "camp-2", "name": "Campaign 2", "status": 2},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await client.list_campaigns()

            assert len(results) == 2
            assert all(isinstance(c, Campaign) for c in results)
            assert results[0].status == CampaignStatus.ACTIVE
            assert results[1].status == CampaignStatus.PAUSED

    @pytest.mark.asyncio
    async def test_list_campaigns_with_filters(self, client: InstantlyClient) -> None:
        """Should apply filters to campaign listing."""
        mock_response = {"items": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.list_campaigns(
                limit=50,
                search="outreach",
                status=CampaignStatus.ACTIVE,
            )

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["limit"] == 50
            assert params["search"] == "outreach"
            assert params["status"] == 1

    @pytest.mark.asyncio
    async def test_list_campaigns_limit_capped_at_100(self, client: InstantlyClient) -> None:
        """Should cap limit at 100."""
        mock_response = {"items": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.list_campaigns(limit=500)

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["limit"] == 100


class TestGetCampaign:
    """Tests for get_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_campaign_success(self, client: InstantlyClient) -> None:
        """Should get single campaign by ID."""
        mock_response = {
            "id": "camp-123",
            "name": "My Campaign",
            "status": 1,
            "updated_at": "2025-01-15T12:00:00Z",
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_campaign("camp-123")

            assert result.id == "camp-123"
            assert result.name == "My Campaign"
            assert result.is_active is True

            mock_get.assert_called_once_with("/campaigns/camp-123")


class TestUpdateCampaign:
    """Tests for update_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_update_campaign_success(self, client: InstantlyClient) -> None:
        """Should update campaign successfully."""
        mock_response = {
            "id": "camp-123",
            "name": "Updated Name",
            "status": 1,
        }

        with patch.object(client, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = mock_response

            result = await client.update_campaign(
                campaign_id="camp-123",
                name="Updated Name",
            )

            assert result.name == "Updated Name"
            mock_patch.assert_called_once_with(
                "/campaigns/camp-123",
                json={"name": "Updated Name"},
            )


class TestDeleteCampaign:
    """Tests for delete_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_delete_campaign_success(self, client: InstantlyClient) -> None:
        """Should delete campaign successfully."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {}

            result = await client.delete_campaign("camp-123")

            assert result is True
            mock_delete.assert_called_once_with("/campaigns/camp-123")


class TestActivateCampaign:
    """Tests for activate_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_activate_campaign_success(self, client: InstantlyClient) -> None:
        """Should activate campaign successfully."""
        mock_response = {
            "id": "camp-123",
            "name": "Campaign",
            "status": 1,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.activate_campaign("camp-123")

            assert result.status == CampaignStatus.ACTIVE
            mock_post.assert_called_once_with("/campaigns/camp-123/activate")


class TestPauseCampaign:
    """Tests for pause_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_pause_campaign_success(self, client: InstantlyClient) -> None:
        """Should pause campaign successfully."""
        mock_response = {
            "id": "camp-123",
            "name": "Campaign",
            "status": 2,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.pause_campaign("camp-123")

            assert result.status == CampaignStatus.PAUSED
            mock_post.assert_called_once_with("/campaigns/camp-123/pause")


class TestDuplicateCampaign:
    """Tests for duplicate_campaign method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_duplicate_campaign_success(self, client: InstantlyClient) -> None:
        """Should duplicate campaign successfully."""
        mock_response = {
            "id": "camp-456",
            "name": "Campaign (Copy)",
            "status": 0,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.duplicate_campaign("camp-123")

            assert result.id == "camp-456"
            mock_post.assert_called_once_with("/campaigns/camp-123/duplicate")


class TestCreateLead:
    """Tests for create_lead method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_create_lead_success(self, client: InstantlyClient) -> None:
        """Should create lead successfully."""
        mock_response = {
            "id": "lead-123",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Inc",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.create_lead(
                email="john@example.com",
                campaign_id="camp-123",
                first_name="John",
                last_name="Doe",
                company_name="Acme Inc",
            )

            assert isinstance(result, Lead)
            assert result.email == "john@example.com"
            assert result.full_name == "John Doe"

    @pytest.mark.asyncio
    async def test_create_lead_with_list_id(self, client: InstantlyClient) -> None:
        """Should create lead with list_id."""
        mock_response = {
            "id": "lead-123",
            "email": "john@example.com",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.create_lead(
                email="john@example.com",
                list_id="list-456",
            )

            call_args = mock_post.call_args
            assert call_args[1]["json"]["list_id"] == "list-456"

    @pytest.mark.asyncio
    async def test_create_lead_raises_without_destination(self, client: InstantlyClient) -> None:
        """Should raise ValueError without campaign_id or list_id."""
        with pytest.raises(ValueError, match="campaign_id or list_id"):
            await client.create_lead(email="john@example.com")


class TestListLeads:
    """Tests for list_leads method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_list_leads_success(self, client: InstantlyClient) -> None:
        """Should list leads successfully."""
        mock_response = {
            "items": [
                {"id": "lead-1", "email": "john@example.com"},
                {"id": "lead-2", "email": "jane@example.com"},
            ]
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await client.list_leads(campaign_id="camp-123")

            assert len(results) == 2
            assert all(isinstance(lead, Lead) for lead in results)

    @pytest.mark.asyncio
    async def test_list_leads_with_filters(self, client: InstantlyClient) -> None:
        """Should apply filters to lead listing."""
        mock_response = {"items": []}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.list_leads(
                campaign_id="camp-123",
                search="john",
                limit=50,
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["campaign"] == "camp-123"
            assert payload["search"] == "john"
            assert payload["limit"] == 50


class TestGetLead:
    """Tests for get_lead method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_lead_success(self, client: InstantlyClient) -> None:
        """Should get single lead by ID."""
        mock_response = {
            "id": "lead-123",
            "email": "john@example.com",
            "interest_status": "interested",
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_lead("lead-123")

            assert result.id == "lead-123"
            assert result.interest_status == LeadInterestStatus.INTERESTED


class TestUpdateLead:
    """Tests for update_lead method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_update_lead_success(self, client: InstantlyClient) -> None:
        """Should update lead successfully."""
        mock_response = {
            "id": "lead-123",
            "email": "john@example.com",
            "first_name": "Johnny",
        }

        with patch.object(client, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = mock_response

            result = await client.update_lead(
                lead_id="lead-123",
                first_name="Johnny",
            )

            assert result.first_name == "Johnny"


class TestDeleteLead:
    """Tests for delete_lead method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_delete_lead_success(self, client: InstantlyClient) -> None:
        """Should delete lead successfully."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {}

            result = await client.delete_lead("lead-123")

            assert result is True


class TestBulkAddLeads:
    """Tests for bulk_add_leads method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_bulk_add_leads_success(self, client: InstantlyClient) -> None:
        """Should bulk add leads successfully."""
        mock_response = {
            "created_count": 3,
            "updated_count": 0,
            "failed_count": 0,
            "created_leads": ["lead-1", "lead-2", "lead-3"],
            "failed_leads": [],
        }

        leads = [
            {"email": "john@example.com"},
            {"email": "jane@example.com"},
            {"email": "bob@example.com"},
        ]

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.bulk_add_leads(leads, campaign_id="camp-123")

            assert isinstance(result, BulkAddResult)
            assert result.created_count == 3
            assert result.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_bulk_add_leads_exceeds_limit(self, client: InstantlyClient) -> None:
        """Should raise ValueError for more than 1000 leads."""
        leads = [{"email": f"user{i}@example.com"} for i in range(1001)]

        with pytest.raises(ValueError, match="Maximum 1000"):
            await client.bulk_add_leads(leads, campaign_id="camp-123")

    @pytest.mark.asyncio
    async def test_bulk_add_leads_no_destination(self, client: InstantlyClient) -> None:
        """Should raise ValueError without destination."""
        leads = [{"email": "john@example.com"}]

        with pytest.raises(ValueError, match="campaign_id or list_id"):
            await client.bulk_add_leads(leads)


class TestUpdateLeadInterestStatus:
    """Tests for update_lead_interest_status method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_update_interest_status_success(self, client: InstantlyClient) -> None:
        """Should update lead interest status."""
        mock_response = {
            "job_id": "job-123",
            "status": "pending",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.update_lead_interest_status(
                lead_email="john@example.com",
                interest_status=LeadInterestStatus.MEETING_BOOKED,
            )

            assert isinstance(result, BackgroundJob)
            assert result.job_id == "job-123"


class TestMoveLeads:
    """Tests for move_leads method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_move_leads_success(self, client: InstantlyClient) -> None:
        """Should move leads successfully."""
        mock_response = {
            "job_id": "job-456",
            "status": "processing",
            "progress": 0,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.move_leads(
                lead_ids=["lead-1", "lead-2"],
                destination_campaign_id="camp-456",
            )

            assert isinstance(result, BackgroundJob)
            assert result.is_running is True

    @pytest.mark.asyncio
    async def test_move_leads_no_destination(self, client: InstantlyClient) -> None:
        """Should raise ValueError without destination."""
        with pytest.raises(ValueError, match="destination_campaign_id or destination_list_id"):
            await client.move_leads(lead_ids=["lead-1"])


class TestGetCampaignAnalytics:
    """Tests for get_campaign_analytics method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_analytics_single_campaign(self, client: InstantlyClient) -> None:
        """Should get analytics for single campaign."""
        mock_response = {
            "total_leads": 100,
            "contacted": 80,
            "emails_sent": 200,
            "emails_opened": 50,
            "emails_clicked": 20,
            "emails_replied": 10,
            "emails_bounced": 5,
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_campaign_analytics("camp-123")

            assert isinstance(result, CampaignAnalytics)
            assert result.total_leads == 100
            assert result.open_rate == 25.0
            assert result.reply_rate == 5.0

    @pytest.mark.asyncio
    async def test_get_analytics_all_campaigns(self, client: InstantlyClient) -> None:
        """Should get analytics for all campaigns."""
        mock_response = {
            "items": [
                {"campaign_id": "camp-1", "emails_sent": 100, "emails_opened": 25},
                {"campaign_id": "camp-2", "emails_sent": 200, "emails_opened": 50},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await client.get_campaign_analytics()

            assert isinstance(results, list)
            assert len(results) == 2


class TestGetCampaignAnalyticsOverview:
    """Tests for get_campaign_analytics_overview method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_overview_success(self, client: InstantlyClient) -> None:
        """Should get analytics overview."""
        mock_response = {"total_sent": 1000, "total_replied": 50}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_campaign_analytics_overview()

            assert result["total_sent"] == 1000


class TestGetCampaignDailyAnalytics:
    """Tests for get_campaign_daily_analytics method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_daily_analytics_success(self, client: InstantlyClient) -> None:
        """Should get daily analytics."""
        mock_response = {
            "items": [
                {"date": "2025-01-15", "sent": 50, "opened": 10},
                {"date": "2025-01-16", "sent": 60, "opened": 15},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_campaign_daily_analytics(
                campaign_id="camp-123",
                start_date="2025-01-15",
                end_date="2025-01-16",
            )

            assert len(result) == 2


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: InstantlyClient) -> None:
        """Should return healthy status when API works."""
        mock_response = {"items": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            health = await client.health_check()

            assert health["name"] == "instantly"
            assert health["healthy"] is True
            assert health["api_version"] == "V2"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: InstantlyClient) -> None:
        """Should return unhealthy status on error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            health = await client.health_check()

            assert health["name"] == "instantly"
            assert health["healthy"] is False
            assert "error" in health


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error(self, client: InstantlyClient) -> None:
        """Should raise InstantlyError on 401."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = AuthenticationError(
                message="Invalid API key",
                response_data={"error": "Unauthorized"},
            )

            with pytest.raises(InstantlyError) as exc_info:
                await client.create_campaign(
                    name="Test",
                    campaign_schedule={"schedules": []},
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_payment_required_error(self, client: InstantlyClient) -> None:
        """Should raise InstantlyError on 402."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = PaymentRequiredError(
                message="Subscription required",
            )

            with pytest.raises(InstantlyError) as exc_info:
                await client.create_lead(
                    email="john@example.com",
                    campaign_id="camp-123",
                )

            assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client: InstantlyClient) -> None:
        """Should raise InstantlyError on 429."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = RateLimitError(
                message="Rate limit exceeded",
                retry_after=60,
            )

            with pytest.raises(InstantlyError):
                await client.list_campaigns()


class TestCallEndpoint:
    """Tests for call_endpoint method."""

    @pytest.fixture
    def client(self) -> InstantlyClient:
        """Create client for testing."""
        return InstantlyClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: InstantlyClient) -> None:
        """Should make GET request to custom endpoint."""
        mock_response = {"data": "test"}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint("/custom-endpoint")

            assert result == {"data": "test"}
            mock_request.assert_called_once_with("GET", "/custom-endpoint")

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: InstantlyClient) -> None:
        """Should make POST request to custom endpoint."""
        mock_response = {"created": True}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.call_endpoint(
                "/new-feature",
                method="POST",
                json={"param": "value"},
            )

            assert result == {"created": True}
            mock_request.assert_called_once_with("POST", "/new-feature", json={"param": "value"})


class TestAsyncContextManager:
    """Tests for async context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close client on exit."""
        async with InstantlyClient(api_key="test-key") as client:  # pragma: allowlist secret
            # Force client creation
            _ = client.client
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None or client._client.is_closed


class TestCampaignProperties:
    """Tests for Campaign dataclass properties."""

    def test_is_active_true_for_active_status(self) -> None:
        """is_active should be True for active status."""
        campaign = Campaign(
            id="camp-123",
            name="Test",
            status=CampaignStatus.ACTIVE,
        )
        assert campaign.is_active is True

    def test_is_active_false_for_other_statuses(self) -> None:
        """is_active should be False for non-active statuses."""
        for status in [CampaignStatus.DRAFT, CampaignStatus.PAUSED, CampaignStatus.COMPLETED]:
            campaign = Campaign(
                id="camp-123",
                name="Test",
                status=status,
            )
            assert campaign.is_active is False

    def test_is_paused_true_for_paused_status(self) -> None:
        """is_paused should be True for paused status."""
        campaign = Campaign(
            id="camp-123",
            name="Test",
            status=CampaignStatus.PAUSED,
        )
        assert campaign.is_paused is True

    def test_is_healthy_true_for_positive_statuses(self) -> None:
        """is_healthy should be True for non-negative status codes."""
        for status in [CampaignStatus.DRAFT, CampaignStatus.ACTIVE, CampaignStatus.PAUSED]:
            campaign = Campaign(
                id="camp-123",
                name="Test",
                status=status,
            )
            assert campaign.is_healthy is True

    def test_is_healthy_false_for_negative_statuses(self) -> None:
        """is_healthy should be False for negative status codes."""
        for status in [
            CampaignStatus.ACCOUNT_SUSPENDED,
            CampaignStatus.ACCOUNTS_UNHEALTHY,
            CampaignStatus.BOUNCE_PROTECT,
        ]:
            campaign = Campaign(
                id="camp-123",
                name="Test",
                status=status,
            )
            assert campaign.is_healthy is False


class TestLeadProperties:
    """Tests for Lead dataclass properties."""

    def test_full_name_with_both_names(self) -> None:
        """full_name should combine first and last names."""
        lead = Lead(
            id="lead-123",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        )
        assert lead.full_name == "John Doe"

    def test_full_name_with_only_first_name(self) -> None:
        """full_name should return first name if last is missing."""
        lead = Lead(
            id="lead-123",
            email="john@example.com",
            first_name="John",
        )
        assert lead.full_name == "John"

    def test_full_name_with_only_last_name(self) -> None:
        """full_name should return last name if first is missing."""
        lead = Lead(
            id="lead-123",
            email="john@example.com",
            last_name="Doe",
        )
        assert lead.full_name == "Doe"

    def test_full_name_none_if_both_missing(self) -> None:
        """full_name should be None if both names are missing."""
        lead = Lead(
            id="lead-123",
            email="john@example.com",
        )
        assert lead.full_name is None


class TestCampaignAnalyticsProperties:
    """Tests for CampaignAnalytics dataclass properties."""

    def test_open_rate_calculation(self) -> None:
        """open_rate should calculate percentage correctly."""
        analytics = CampaignAnalytics(
            campaign_id="camp-123",
            emails_sent=100,
            emails_opened=25,
        )
        assert analytics.open_rate == 25.0

    def test_open_rate_zero_if_no_emails_sent(self) -> None:
        """open_rate should be 0 if no emails sent."""
        analytics = CampaignAnalytics(
            campaign_id="camp-123",
            emails_sent=0,
            emails_opened=0,
        )
        assert analytics.open_rate == 0.0

    def test_click_rate_calculation(self) -> None:
        """click_rate should calculate percentage correctly."""
        analytics = CampaignAnalytics(
            campaign_id="camp-123",
            emails_sent=100,
            emails_clicked=10,
        )
        assert analytics.click_rate == 10.0

    def test_reply_rate_calculation(self) -> None:
        """reply_rate should calculate percentage correctly."""
        analytics = CampaignAnalytics(
            campaign_id="camp-123",
            emails_sent=200,
            emails_replied=6,
        )
        assert analytics.reply_rate == 3.0

    def test_bounce_rate_calculation(self) -> None:
        """bounce_rate should calculate percentage correctly."""
        analytics = CampaignAnalytics(
            campaign_id="camp-123",
            emails_sent=100,
            emails_bounced=2,
        )
        assert analytics.bounce_rate == 2.0


class TestBulkAddResultProperties:
    """Tests for BulkAddResult dataclass properties."""

    def test_success_rate_calculation(self) -> None:
        """success_rate should calculate percentage correctly."""
        result = BulkAddResult(
            created_count=80,
            updated_count=10,
            failed_count=10,
            created_leads=[],
            failed_leads=[],
        )
        assert result.success_rate == 90.0

    def test_success_rate_zero_if_no_leads(self) -> None:
        """success_rate should be 0 if no leads processed."""
        result = BulkAddResult(
            created_count=0,
            updated_count=0,
            failed_count=0,
            created_leads=[],
            failed_leads=[],
        )
        assert result.success_rate == 0.0


class TestBackgroundJobProperties:
    """Tests for BackgroundJob dataclass properties."""

    def test_is_completed_true(self) -> None:
        """is_completed should be True for completed status."""
        job = BackgroundJob(
            job_id="job-123",
            status="completed",
            progress=100,
        )
        assert job.is_completed is True

    def test_is_completed_false(self) -> None:
        """is_completed should be False for other statuses."""
        job = BackgroundJob(
            job_id="job-123",
            status="running",
            progress=50,
        )
        assert job.is_completed is False

    def test_is_running_true(self) -> None:
        """is_running should be True for running/processing/pending."""
        for status in ["running", "processing", "pending"]:
            job = BackgroundJob(
                job_id="job-123",
                status=status,
                progress=50,
            )
            assert job.is_running is True

    def test_is_running_false(self) -> None:
        """is_running should be False for completed/failed."""
        job = BackgroundJob(
            job_id="job-123",
            status="completed",
            progress=100,
        )
        assert job.is_running is False


class TestCampaignStatusEnum:
    """Tests for CampaignStatus enum values."""

    def test_status_values(self) -> None:
        """Status enum should have correct integer values."""
        assert CampaignStatus.DRAFT.value == 0
        assert CampaignStatus.ACTIVE.value == 1
        assert CampaignStatus.PAUSED.value == 2
        assert CampaignStatus.COMPLETED.value == 3
        assert CampaignStatus.RUNNING_SUBSEQUENCES.value == 4
        assert CampaignStatus.ACCOUNT_SUSPENDED.value == -99
        assert CampaignStatus.ACCOUNTS_UNHEALTHY.value == -1
        assert CampaignStatus.BOUNCE_PROTECT.value == -2


class TestLeadInterestStatusEnum:
    """Tests for LeadInterestStatus enum values."""

    def test_status_values(self) -> None:
        """Interest status enum should have correct string values."""
        assert LeadInterestStatus.INTERESTED.value == "interested"
        assert LeadInterestStatus.NOT_INTERESTED.value == "not_interested"
        assert LeadInterestStatus.MEETING_BOOKED.value == "meeting_booked"
        assert LeadInterestStatus.MEETING_COMPLETED.value == "meeting_completed"
        assert LeadInterestStatus.CLOSED.value == "closed"
        assert LeadInterestStatus.OUT_OF_OFFICE.value == "out_of_office"
        assert LeadInterestStatus.WRONG_PERSON.value == "wrong_person"
