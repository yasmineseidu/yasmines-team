"""
Unit tests for Lead List Builder Agent.

Tests cover:
- Agent initialization
- Lead scraping workflow
- Direct scraping fallback
- Error handling
- Result formatting
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.lead_list_builder import (
    LeadListBuilderAgent,
    LeadListBuilderResult,
)
from src.integrations.apify import ApifyError, ApifyLead, ApifyScrapeResult

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def agent() -> LeadListBuilderAgent:
    """Create test agent instance."""
    return LeadListBuilderAgent(apify_token="test_token_12345")


@pytest.fixture
def mock_apify_result() -> ApifyScrapeResult:
    """Create mock Apify scrape result."""
    leads = [
        ApifyLead(
            first_name="John",
            last_name="Smith",
            email="john@company.com",
            linkedin_url="https://linkedin.com/in/john",
            title="VP Engineering",
            company_name="TechCorp",
            source="linkedin",
        ),
        ApifyLead(
            first_name="Jane",
            last_name="Doe",
            email="jane@startup.io",
            linkedin_url="https://linkedin.com/in/jane",
            title="CTO",
            company_name="Startup.io",
            source="linkedin",
        ),
    ]

    return ApifyScrapeResult(
        run_id="run_123",
        actor_id="linkedin-scraper",
        status="SUCCEEDED",
        dataset_id="dataset_456",
        leads=leads,
        total_items=2,
        cost_usd=2.50,
        duration_secs=120,
    )


@pytest.fixture
def campaign_id() -> str:
    """Test campaign ID."""
    return "campaign_abc123"


@pytest.fixture
def niche_id() -> str:
    """Test niche ID."""
    return "niche_xyz789"


# =============================================================================
# Initialization Tests
# =============================================================================


class TestLeadListBuilderAgentInitialization:
    """Tests for agent initialization."""

    def test_initializes_with_apify_token(self) -> None:
        """Test agent initializes with Apify token."""
        agent = LeadListBuilderAgent(apify_token="test_token")
        assert agent.apify_token == "test_token"

    def test_initializes_with_default_model(self) -> None:
        """Test agent uses default Claude model."""
        agent = LeadListBuilderAgent(apify_token="test_token")
        assert "claude" in agent.model.lower()

    def test_has_correct_name(self) -> None:
        """Test agent has correct name."""
        agent = LeadListBuilderAgent(apify_token="test_token")
        assert agent.name == "lead_list_builder"

    def test_reads_token_from_env(self) -> None:
        """Test reads Apify token from environment."""
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "env_token_123"}):
            agent = LeadListBuilderAgent()
            assert agent.apify_token == "env_token_123"

    def test_warns_on_missing_token(self) -> None:
        """Test warns when no Apify token provided."""
        with (
            patch.dict("os.environ", {"APIFY_API_TOKEN": ""}, clear=True),
            patch("src.agents.lead_list_builder.agent.logger") as mock_logger,
        ):
            LeadListBuilderAgent(apify_token="")
            mock_logger.warning.assert_called()


# =============================================================================
# System Prompt Tests
# =============================================================================


class TestSystemPrompt:
    """Tests for system prompt."""

    def test_system_prompt_contains_tools(self, agent: LeadListBuilderAgent) -> None:
        """Test system prompt mentions available tools."""
        prompt = agent.system_prompt
        assert "scrape_linkedin_leads" in prompt or "LinkedIn" in prompt
        assert "scrape_apollo_leads" in prompt or "Apollo" in prompt

    def test_system_prompt_contains_strategy(self, agent: LeadListBuilderAgent) -> None:
        """Test system prompt contains strategy."""
        prompt = agent.system_prompt
        assert "LinkedIn" in prompt  # Primary source
        assert "Apollo" in prompt  # Supplement


# =============================================================================
# Run Method Tests
# =============================================================================


class TestAgentRun:
    """Tests for agent run method."""

    @pytest.mark.asyncio
    async def test_run_returns_result(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test run returns LeadListBuilderResult."""
        with patch.object(agent, "_direct_scrape") as mock_scrape:
            mock_scrape.return_value = {
                "leads": [{"first_name": "John"}],
                "linkedin_count": 1,
                "apollo_count": 0,
                "total_cost": 1.0,
                "runs": [],
                "errors": [],
            }

            # Skip Claude SDK query for unit test
            with patch("src.agents.lead_list_builder.agent.query") as mock_query:
                mock_query.return_value = MagicMock(messages=[])

                result = await agent.run(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                    target_leads=100,
                )

        assert isinstance(result, LeadListBuilderResult)
        assert result.target_leads == 100

    @pytest.mark.asyncio
    async def test_run_with_persona_criteria(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test run with persona criteria."""
        with patch.object(agent, "_direct_scrape") as mock_scrape:
            mock_scrape.return_value = {
                "leads": [{"first_name": "John", "title": "VP"}],
                "linkedin_count": 1,
                "apollo_count": 0,
                "total_cost": 2.0,
                "runs": [],
                "errors": [],
            }

            with patch("src.agents.lead_list_builder.agent.query") as mock_query:
                mock_query.return_value = MagicMock(messages=[])

                result = await agent.run(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                    target_leads=50,
                    job_titles=["VP", "Director"],
                    industries=["Technology", "Software"],
                    company_sizes=["51-200", "201-500"],
                )

        assert result.target_leads == 50

    @pytest.mark.asyncio
    async def test_run_handles_errors(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test run handles errors gracefully."""
        with patch.object(agent, "_direct_scrape") as mock_scrape:
            mock_scrape.side_effect = Exception("Scraping failed")

            with patch("src.agents.lead_list_builder.agent.query") as mock_query:
                mock_query.side_effect = Exception("Claude API error")

                result = await agent.run(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                    target_leads=100,
                )

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_run_tracks_execution_time(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test run tracks execution time."""
        with patch.object(agent, "_direct_scrape") as mock_scrape:
            mock_scrape.return_value = {
                "leads": [],
                "linkedin_count": 0,
                "apollo_count": 0,
                "total_cost": 0,
                "runs": [],
                "errors": [],
            }

            with patch("src.agents.lead_list_builder.agent.query") as mock_query:
                mock_query.return_value = MagicMock(messages=[])

                result = await agent.run(
                    campaign_id=campaign_id,
                    niche_id=niche_id,
                    target_leads=100,
                )

        assert result.execution_time_ms >= 0
        assert result.started_at is not None
        assert result.completed_at is not None


# =============================================================================
# Direct Scraping Tests
# =============================================================================


class TestDirectScrape:
    """Tests for direct scraping fallback."""

    @pytest.mark.asyncio
    async def test_direct_scrape_linkedin_success(
        self,
        agent: LeadListBuilderAgent,
        mock_apify_result: ApifyScrapeResult,
    ) -> None:
        """Test direct LinkedIn scraping."""
        mock_client = MagicMock()
        mock_client.scrape_linkedin_leads = AsyncMock(return_value=mock_apify_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.agents.lead_list_builder.agent.ApifyLeadScraperClient",
            return_value=mock_client,
        ):
            result = await agent._direct_scrape(
                target_leads=100,
                job_titles=["VP", "Director"],
                seniority_levels=["VP", "Director"],
                industries=["Technology"],
                company_sizes=["51-200"],
                locations=["San Francisco"],
                linkedin_search_url="https://linkedin.com/search",
            )

        assert result["linkedin_count"] == 2
        assert len(result["leads"]) == 2

    @pytest.mark.asyncio
    async def test_direct_scrape_sales_navigator(
        self,
        mock_apify_result: ApifyScrapeResult,
    ) -> None:
        """Test Sales Navigator scraping with session cookie."""
        agent = LeadListBuilderAgent(
            apify_token="test_token",
            linkedin_session_cookie="li_at_cookie",
        )

        mock_client = MagicMock()
        mock_client.scrape_linkedin_sales_navigator = AsyncMock(return_value=mock_apify_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.agents.lead_list_builder.agent.ApifyLeadScraperClient",
            return_value=mock_client,
        ):
            result = await agent._direct_scrape(
                target_leads=100,
                job_titles=["VP"],
                seniority_levels=[],
                industries=[],
                company_sizes=[],
                locations=[],
            )

        mock_client.scrape_linkedin_sales_navigator.assert_called_once()
        assert result["linkedin_count"] == 2

    @pytest.mark.asyncio
    async def test_direct_scrape_supplements_with_apollo(
        self,
        agent: LeadListBuilderAgent,
    ) -> None:
        """Test Apollo supplementation when LinkedIn doesn't return enough."""
        linkedin_result = ApifyScrapeResult(
            run_id="run_li",
            actor_id="linkedin",
            status="SUCCEEDED",
            leads=[ApifyLead(first_name="John", source="linkedin")],
            total_items=1,
            cost_usd=1.0,
        )

        apollo_result = ApifyScrapeResult(
            run_id="run_ap",
            actor_id="apollo",
            status="SUCCEEDED",
            leads=[ApifyLead(first_name="Jane", source="apollo")],
            total_items=1,
            cost_usd=0.5,
        )

        mock_client = MagicMock()
        mock_client.scrape_linkedin_leads = AsyncMock(return_value=linkedin_result)
        mock_client.scrape_apollo_leads = AsyncMock(return_value=apollo_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.agents.lead_list_builder.agent.ApifyLeadScraperClient",
            return_value=mock_client,
        ):
            result = await agent._direct_scrape(
                target_leads=100,  # Need more than 1
                job_titles=["VP"],
                seniority_levels=[],
                industries=["Tech"],
                company_sizes=[],
                locations=[],
            )

        assert result["linkedin_count"] == 1
        assert result["apollo_count"] == 1
        assert len(result["leads"]) == 2

    @pytest.mark.asyncio
    async def test_direct_scrape_handles_linkedin_error(
        self,
        agent: LeadListBuilderAgent,
    ) -> None:
        """Test handling LinkedIn scraping error."""
        mock_client = MagicMock()
        mock_client.scrape_linkedin_leads = AsyncMock(
            side_effect=ApifyError("LinkedIn scraping failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.agents.lead_list_builder.agent.ApifyLeadScraperClient",
            return_value=mock_client,
        ):
            result = await agent._direct_scrape(
                target_leads=100,
                job_titles=["VP"],
                seniority_levels=[],
                industries=[],
                company_sizes=[],
                locations=[],
            )

        assert len(result["errors"]) > 0
        assert result["errors"][0]["source"] == "linkedin"


# =============================================================================
# Task Prompt Tests
# =============================================================================


class TestBuildTaskPrompt:
    """Tests for task prompt building."""

    def test_build_task_prompt_with_criteria(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test prompt includes persona criteria."""
        prompt = agent._build_task_prompt(
            niche_id=niche_id,
            campaign_id=campaign_id,
            target_leads=1000,
            job_titles=["VP", "Director"],
            seniority_levels=["VP", "Director"],
            industries=["Technology", "Software"],
            company_sizes=["51-200", "201-500"],
            locations=["San Francisco", "New York"],
            linkedin_search_url=None,
        )

        assert campaign_id in prompt
        assert "1000" in prompt
        assert "VP" in prompt
        assert "Technology" in prompt

    def test_build_task_prompt_with_search_url(
        self,
        agent: LeadListBuilderAgent,
        campaign_id: str,
        niche_id: str,
    ) -> None:
        """Test prompt includes pre-built search URL."""
        search_url = "https://linkedin.com/sales/search/people?filter=abc"
        prompt = agent._build_task_prompt(
            niche_id=niche_id,
            campaign_id=campaign_id,
            target_leads=500,
            job_titles=None,
            seniority_levels=None,
            industries=None,
            company_sizes=None,
            locations=None,
            linkedin_search_url=search_url,
        )

        assert search_url in prompt


# =============================================================================
# Result Data Class Tests
# =============================================================================


class TestLeadListBuilderResult:
    """Tests for LeadListBuilderResult data class."""

    def test_to_dict(self) -> None:
        """Test result to_dict conversion."""
        result = LeadListBuilderResult(
            success=True,
            status="completed",
            leads=[{"first_name": "John"}],
            total_scraped=1,
            target_leads=100,
            linkedin_leads=1,
            apollo_leads=0,
            total_cost_usd=2.50,
            execution_time_ms=5000,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["total_scraped"] == 1
        assert data["total_cost_usd"] == 2.50

    def test_default_values(self) -> None:
        """Test default values."""
        result = LeadListBuilderResult()

        assert result.success is True
        assert result.status == "completed"
        assert result.leads == []
        assert result.errors == []

    def test_partial_status(self) -> None:
        """Test partial status when not enough leads."""
        result = LeadListBuilderResult(
            status="partial",
            total_scraped=50,
            target_leads=1000,
            warnings=["Only scraped 50/1000 leads"],
        )

        assert result.status == "partial"
        assert len(result.warnings) > 0

    def test_failed_status(self) -> None:
        """Test failed status with errors."""
        result = LeadListBuilderResult(
            success=False,
            status="failed",
            total_scraped=0,
            errors=[{"type": "ApifyError", "message": "Scraping failed"}],
        )

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) > 0
