"""
Unit tests for Apify integration client.

Tests cover:
- Client initialization
- Actor run operations
- Dataset retrieval
- Lead parsing
- Error handling
- Rate limiting
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.apify import (
    ApifyActorId,
    ApifyAuthenticationError,
    ApifyError,
    ApifyLead,
    ApifyLeadScraperClient,
    ApifyRateLimitError,
    ApifyScrapeResult,
    ApifyTimeoutError,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_token() -> str:
    """Test API token."""
    return "test_apify_token_12345"


@pytest.fixture
def client(api_token: str) -> ApifyLeadScraperClient:
    """Create test client instance."""
    return ApifyLeadScraperClient(api_token=api_token)


@pytest.fixture
def linkedin_run_response() -> dict:
    """Sample LinkedIn actor run response."""
    return {
        "id": "run_abc123",
        "actId": "curious_coder~linkedin-search-export",
        "status": "SUCCEEDED",
        "defaultDatasetId": "dataset_xyz789",
        "startedAt": "2025-01-15T10:00:00.000Z",
        "finishedAt": "2025-01-15T10:05:30.000Z",
        "usage": {
            "COMPUTE_UNITS": 0.5,
            "TOTAL_USD": 2.50,
        },
    }


@pytest.fixture
def linkedin_dataset_items() -> list[dict]:
    """Sample LinkedIn dataset items."""
    return [
        {
            "firstName": "John",
            "lastName": "Smith",
            "fullName": "John Smith",
            "email": "john.smith@techcorp.com",
            "linkedinUrl": "https://linkedin.com/in/johnsmith",
            "linkedinId": "johnsmith123",
            "jobTitle": "VP of Engineering",
            "seniority": "VP",
            "companyName": "TechCorp Inc",
            "companyDomain": "techcorp.com",
            "industry": "Technology",
            "location": "San Francisco, CA",
        },
        {
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane.doe@startup.io",
            "linkedinUrl": "https://linkedin.com/in/janedoe",
            "jobTitle": "CTO",
            "companyName": "Startup.io",
            "industry": "Software",
        },
    ]


# =============================================================================
# Initialization Tests
# =============================================================================


class TestApifyLeadScraperClientInitialization:
    """Tests for client initialization."""

    def test_initializes_with_api_token(self, api_token: str) -> None:
        """Test client initializes with API token."""
        client = ApifyLeadScraperClient(api_token=api_token)
        assert client.api_token == api_token

    def test_raises_on_missing_token(self) -> None:
        """Test raises error when no token provided."""
        with (
            patch.dict("os.environ", {"APIFY_API_TOKEN": ""}, clear=True),
            pytest.raises(ApifyAuthenticationError),
        ):
            ApifyLeadScraperClient(api_token="")

    def test_reads_token_from_env(self) -> None:
        """Test reads API token from environment variable."""
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "env_token_123"}):
            client = ApifyLeadScraperClient()
            assert client.api_token == "env_token_123"

    def test_has_default_timeout(self, client: ApifyLeadScraperClient) -> None:
        """Test client has default timeout."""
        assert client.timeout_secs == 600

    def test_has_default_poll_interval(self, client: ApifyLeadScraperClient) -> None:
        """Test client has default poll interval."""
        assert client.poll_interval_secs == 10

    def test_has_rate_limiter(self, client: ApifyLeadScraperClient) -> None:
        """Test client has rate limiter."""
        assert client._rate_limiter is not None
        assert client._rate_limiter.capacity == 100


# =============================================================================
# Actor Run Tests
# =============================================================================


class TestRunActor:
    """Tests for run_actor method."""

    @pytest.mark.asyncio
    async def test_run_actor_success(
        self,
        client: ApifyLeadScraperClient,
        linkedin_run_response: dict,
    ) -> None:
        """Test successful actor run."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=linkedin_run_response)

        with patch.object(client.client, "actor", return_value=mock_actor_client):
            result = await client.run_actor(
                actor_id=ApifyActorId.LINKEDIN_SEARCH_SCRAPER,
                run_input={"searchUrl": "https://linkedin.com/search"},
            )

        assert result.run_id == "run_abc123"
        assert result.status == "SUCCEEDED"
        assert result.dataset_id == "dataset_xyz789"
        assert result.cost_usd == 2.50
        assert result.compute_units == 0.5

    @pytest.mark.asyncio
    async def test_run_actor_failed_status(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test actor run with FAILED status raises error."""
        failed_response = {
            "id": "run_failed123",
            "status": "FAILED",
            "defaultDatasetId": None,
        }

        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=failed_response)

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            pytest.raises(ApifyError) as exc_info,
        ):
            await client.run_actor(
                actor_id="test-actor",
                run_input={},
            )

        assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_run_actor_timeout_status(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test actor run with TIMED-OUT status raises timeout error."""
        timeout_response = {
            "id": "run_timeout123",
            "status": "TIMED-OUT",
            "defaultDatasetId": None,
        }

        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=timeout_response)

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            pytest.raises(ApifyTimeoutError),
        ):
            await client.run_actor(
                actor_id="test-actor",
                run_input={},
            )

    @pytest.mark.asyncio
    async def test_run_actor_none_response(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test actor run with None response raises error."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=None)

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            pytest.raises(ApifyError) as exc_info,
        ):
            await client.run_actor(
                actor_id="test-actor",
                run_input={},
            )

        assert "returned None" in str(exc_info.value)


# =============================================================================
# Dataset Retrieval Tests
# =============================================================================


class TestGetDatasetItems:
    """Tests for dataset retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_dataset_items_success(
        self,
        client: ApifyLeadScraperClient,
        linkedin_dataset_items: list[dict],
    ) -> None:
        """Test successful dataset item retrieval."""
        mock_dataset_client = MagicMock()
        mock_list_result = MagicMock()
        mock_list_result.items = linkedin_dataset_items
        mock_dataset_client.list_items = AsyncMock(return_value=mock_list_result)

        with patch.object(client.client, "dataset", return_value=mock_dataset_client):
            items = await client.get_dataset_items("dataset_xyz789")

        assert len(items) == 2
        assert items[0]["firstName"] == "John"
        assert items[1]["firstName"] == "Jane"

    @pytest.mark.asyncio
    async def test_get_dataset_items_with_limit(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test dataset retrieval with limit."""
        mock_dataset_client = MagicMock()
        mock_list_result = MagicMock()
        mock_list_result.items = [{"firstName": "John"}]
        mock_dataset_client.list_items = AsyncMock(return_value=mock_list_result)

        with patch.object(client.client, "dataset", return_value=mock_dataset_client):
            items = await client.get_dataset_items("dataset_xyz789", limit=1)

        mock_dataset_client.list_items.assert_called_once_with(limit=1, offset=0)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_iterate_dataset_items_pagination(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test dataset iteration with pagination."""
        # First batch
        batch1 = [{"id": i} for i in range(1000)]
        # Second batch (partial, indicates end)
        batch2 = [{"id": i} for i in range(1000, 1500)]

        mock_dataset_client = MagicMock()
        mock_list_result1 = MagicMock()
        mock_list_result1.items = batch1
        mock_list_result2 = MagicMock()
        mock_list_result2.items = batch2

        mock_dataset_client.list_items = AsyncMock(
            side_effect=[mock_list_result1, mock_list_result2]
        )

        with patch.object(client.client, "dataset", return_value=mock_dataset_client):
            items = await client.iterate_dataset_items("dataset_xyz789")

        assert len(items) == 1500


# =============================================================================
# Lead Scraping Tests
# =============================================================================


class TestScrapeLinkedInLeads:
    """Tests for LinkedIn lead scraping."""

    @pytest.mark.asyncio
    async def test_scrape_linkedin_leads_success(
        self,
        client: ApifyLeadScraperClient,
        linkedin_run_response: dict,
        linkedin_dataset_items: list[dict],
    ) -> None:
        """Test successful LinkedIn lead scraping."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=linkedin_run_response)

        mock_dataset_client = MagicMock()
        mock_list_result = MagicMock()
        mock_list_result.items = linkedin_dataset_items
        mock_dataset_client.list_items = AsyncMock(return_value=mock_list_result)

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            patch.object(client.client, "dataset", return_value=mock_dataset_client),
        ):
            result = await client.scrape_linkedin_leads(
                search_url="https://linkedin.com/sales/search/people",
                max_leads=1000,
            )

        assert result.total_items == 2
        assert len(result.leads) == 2
        assert result.leads[0].first_name == "John"
        assert result.leads[0].company_name == "TechCorp Inc"

    @pytest.mark.asyncio
    async def test_scrape_linkedin_sales_navigator(
        self,
        client: ApifyLeadScraperClient,
        linkedin_run_response: dict,
        linkedin_dataset_items: list[dict],
    ) -> None:
        """Test Sales Navigator scraping with session cookie."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(return_value=linkedin_run_response)

        mock_dataset_client = MagicMock()
        mock_list_result = MagicMock()
        mock_list_result.items = linkedin_dataset_items
        mock_dataset_client.list_items = AsyncMock(return_value=mock_list_result)

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            patch.object(client.client, "dataset", return_value=mock_dataset_client),
        ):
            result = await client.scrape_linkedin_sales_navigator(
                search_url="https://linkedin.com/sales/search/people",
                max_leads=500,
                session_cookie="li_at_cookie_value",
            )

        assert len(result.leads) == 2
        mock_actor_client.call.assert_called_once()


# =============================================================================
# Lead Parsing Tests
# =============================================================================


class TestLeadParsing:
    """Tests for lead parsing methods."""

    def test_parse_linkedin_lead_full_data(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test parsing LinkedIn lead with full data."""
        item = {
            "firstName": "John",
            "lastName": "Smith",
            "fullName": "John Smith",
            "email": "john@company.com",
            "linkedinUrl": "https://linkedin.com/in/johnsmith",
            "linkedinId": "johnsmith123",
            "headline": "VP of Engineering",
            "jobTitle": "VP of Engineering",
            "seniority": "VP",
            "department": "Engineering",
            "companyName": "TechCorp",
            "companyLinkedinUrl": "https://linkedin.com/company/techcorp",
            "companyDomain": "techcorp.com",
            "companySize": "201-500",
            "industry": "Technology",
            "location": "San Francisco, CA",
            "city": "San Francisco",
            "state": "California",
            "country": "United States",
        }

        lead = client._parse_linkedin_lead(item)

        assert lead.first_name == "John"
        assert lead.last_name == "Smith"
        assert lead.email == "john@company.com"
        assert lead.title == "VP of Engineering"
        assert lead.company_name == "TechCorp"
        assert lead.source == "linkedin"

    def test_parse_linkedin_lead_minimal_data(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test parsing LinkedIn lead with minimal data."""
        item = {
            "fullName": "Alice Johnson",
            "linkedinUrl": "https://linkedin.com/in/alice",
        }

        lead = client._parse_linkedin_lead(item)

        assert lead.first_name == "Alice"
        assert lead.last_name == "Johnson"
        assert lead.full_name == "Alice Johnson"
        assert lead.linkedin_url == "https://linkedin.com/in/alice"

    def test_parse_linkedin_lead_alternate_field_names(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test parsing with alternate field name variations."""
        item = {
            "first_name": "Bob",
            "last_name": "Williams",
            "name": "Bob Williams",
            "profileUrl": "https://linkedin.com/in/bob",
            "title": "Director of Sales",
            "company": "SalesCorp",
        }

        lead = client._parse_linkedin_lead(item)

        assert lead.first_name == "Bob"
        assert lead.title == "Director of Sales"
        assert lead.company_name == "SalesCorp"

    def test_parse_apollo_lead(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test parsing Apollo.io lead."""
        item = {
            "first_name": "Charlie",
            "last_name": "Brown",
            "name": "Charlie Brown",
            "email": "charlie@healthtech.org",
            "linkedin_url": "https://linkedin.com/in/charlie",
            "title": "CEO",
            "seniority": "CXO",
            "organization": {
                "name": "HealthTech Org",
                "primary_domain": "healthtech.org",
                "estimated_num_employees": "100-250",
                "industry": "Healthcare",
            },
            "city": "Boston",
            "state": "Massachusetts",
            "country": "United States",
        }

        lead = client._parse_apollo_lead(item)

        assert lead.first_name == "Charlie"
        assert lead.email == "charlie@healthtech.org"
        assert lead.company_name == "HealthTech Org"
        assert lead.company_industry == "Healthcare"
        assert lead.source == "apollo"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_authentication_error(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test authentication error handling."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(side_effect=Exception("401 Unauthorized"))

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            pytest.raises(ApifyAuthenticationError),
        ):
            await client.run_actor(actor_id="test", run_input={})

    @pytest.mark.asyncio
    async def test_rate_limit_error(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test rate limit error handling."""
        mock_actor_client = MagicMock()
        mock_actor_client.call = AsyncMock(side_effect=Exception("429 rate limit exceeded"))

        with (
            patch.object(client.client, "actor", return_value=mock_actor_client),
            pytest.raises((ApifyRateLimitError, ApifyError)),
        ):
            await client.run_actor(actor_id="test", run_input={})


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Tests for health check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test successful health check."""
        mock_user_client = MagicMock()
        mock_user_client.get = AsyncMock(return_value={"id": "user_123", "username": "testuser"})

        with patch.object(client.client, "user", return_value=mock_user_client):
            result = await client.health_check()

        assert result["healthy"] is True
        assert result["name"] == "apify"
        assert result["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self,
        client: ApifyLeadScraperClient,
    ) -> None:
        """Test health check failure."""
        mock_user_client = MagicMock()
        mock_user_client.get = AsyncMock(side_effect=Exception("Connection error"))

        with patch.object(client.client, "user", return_value=mock_user_client):
            result = await client.health_check()

        assert result["healthy"] is False
        assert "error" in result


# =============================================================================
# Data Class Tests
# =============================================================================


class TestApifyLead:
    """Tests for ApifyLead data class."""

    def test_to_dict(self) -> None:
        """Test lead to_dict conversion."""
        lead = ApifyLead(
            first_name="John",
            last_name="Smith",
            email="john@company.com",
            linkedin_url="https://linkedin.com/in/john",
            title="VP Engineering",
            company_name="TechCorp",
            source="linkedin",
        )

        result = lead.to_dict()

        assert result["first_name"] == "John"
        assert result["email"] == "john@company.com"
        assert result["source"] == "linkedin"

    def test_default_values(self) -> None:
        """Test default values for ApifyLead."""
        lead = ApifyLead()

        assert lead.source == "apify"
        assert lead.raw_data == {}
        assert lead.first_name is None


class TestApifyScrapeResult:
    """Tests for ApifyScrapeResult data class."""

    def test_to_dict(self) -> None:
        """Test scrape result to_dict conversion."""
        result = ApifyScrapeResult(
            run_id="run_123",
            actor_id="test-actor",
            status="SUCCEEDED",
            dataset_id="dataset_456",
            total_items=100,
            cost_usd=5.0,
        )

        data = result.to_dict()

        assert data["run_id"] == "run_123"
        assert data["status"] == "SUCCEEDED"
        assert data["cost_usd"] == 5.0
        assert data["leads_count"] == 0  # No leads added yet

    def test_default_values(self) -> None:
        """Test default values for ApifyScrapeResult."""
        result = ApifyScrapeResult(
            run_id="run_123",
            actor_id="test-actor",
            status="RUNNING",
        )

        assert result.leads == []
        assert result.total_items == 0
        assert result.cost_usd == 0.0
