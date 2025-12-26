"""
Unit tests for Company Research Agent.

Tests the main agent class with mocked dependencies.
Coverage target: >85%
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.company_research.agent import CompanyResearchAgent
from src.agents.company_research.schemas import (
    CompanyResearchInput,
    CompanyResearchOutput,
    CompanyToResearch,
    CostTracker,
    ExtractedFact,
    ResearchResult,
)


class TestCostTracker:
    """Tests for CostTracker dataclass."""

    def test_add_cost(self) -> None:
        """Test adding cost to tracker."""
        tracker = CostTracker()
        tracker.add_cost("serper_search", 0.001)
        tracker.add_cost("serper_search", 0.001)

        assert tracker.total_cost == 0.002
        assert tracker.cost_by_tool["serper_search"] == 0.002

    def test_add_cost_multiple_tools(self) -> None:
        """Test adding cost for multiple tools."""
        tracker = CostTracker()
        tracker.add_cost("serper_search", 0.001)
        tracker.add_cost("perplexity_search", 0.005)

        assert tracker.total_cost == 0.006
        assert tracker.cost_by_tool["serper_search"] == 0.001
        assert tracker.cost_by_tool["perplexity_search"] == 0.005

    def test_can_continue_under_budget(self) -> None:
        """Test can_continue when under budget."""
        tracker = CostTracker(max_per_campaign=100.0)
        tracker.total_cost = 50.0

        assert tracker.can_continue() is True
        assert tracker.can_continue(company_cost_estimate=40.0) is True

    def test_can_continue_over_budget(self) -> None:
        """Test can_continue when over budget."""
        tracker = CostTracker(max_per_campaign=100.0)
        tracker.total_cost = 99.0

        assert tracker.can_continue(company_cost_estimate=5.0) is False

    def test_is_at_alert_threshold(self) -> None:
        """Test alert threshold detection."""
        tracker = CostTracker(max_per_campaign=100.0, alert_at_percent=0.80)
        tracker.total_cost = 79.0

        assert tracker.is_at_alert_threshold() is False

        tracker.total_cost = 81.0
        assert tracker.is_at_alert_threshold() is True

    def test_get_remaining_budget(self) -> None:
        """Test getting remaining budget."""
        tracker = CostTracker(max_per_campaign=100.0)
        tracker.total_cost = 25.0

        assert tracker.get_remaining_budget() == 75.0


class TestCompanyResearchAgentInitialization:
    """Tests for CompanyResearchAgent initialization."""

    def test_default_initialization(self) -> None:
        """Test agent initializes with defaults."""
        agent = CompanyResearchAgent()

        assert agent.name == "company_research_agent"
        assert agent.use_claude is False
        assert agent.max_concurrent_companies == 20
        assert agent.session_id is not None

    def test_custom_initialization(self) -> None:
        """Test agent initializes with custom values."""
        agent = CompanyResearchAgent(
            use_claude=True,
            max_concurrent_companies=10,
        )

        assert agent.use_claude is True
        assert agent.max_concurrent_companies == 10

    def test_has_system_prompt(self) -> None:
        """Test agent has system prompt property."""
        agent = CompanyResearchAgent()

        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 100

    def test_has_tools_list(self) -> None:
        """Test agent has tools list property."""
        agent = CompanyResearchAgent()

        assert agent.tools is not None
        assert len(agent.tools) > 0


class TestCompanyResearchAgentRun:
    """Tests for CompanyResearchAgent.run() method."""

    @pytest.fixture
    def agent(self) -> CompanyResearchAgent:
        """Create agent fixture."""
        return CompanyResearchAgent(max_concurrent_companies=5)

    @pytest.fixture
    def sample_campaign_id(self) -> UUID:
        """Create sample campaign ID fixture."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_run_with_no_companies_returns_failure(
        self,
        agent: CompanyResearchAgent,
        sample_campaign_id: UUID,
    ) -> None:
        """Test run returns failure when no companies found."""
        with patch.object(agent, "_get_unique_companies", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            result = await agent.run(sample_campaign_id)

            assert result.success is False
            assert "No companies found" in str(result.error_message)

    @pytest.mark.asyncio
    async def test_run_with_companies_calls_research(
        self,
        agent: CompanyResearchAgent,
        sample_campaign_id: UUID,
    ) -> None:
        """Test run researches companies when found."""
        companies = [
            CompanyToResearch(
                lead_id=uuid4(),
                company_name="Acme Corp",
                company_domain="acme.com",
            ),
        ]

        mock_result = ResearchResult(
            company_domain="acme.com",
            company_name="Acme Corp",
            success=True,
            facts=[],
        )

        with patch.object(agent, "_get_unique_companies", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = companies

            with patch.object(
                agent, "_research_companies_parallel", new_callable=AsyncMock
            ) as mock_research:
                mock_research.return_value = [mock_result]

                with patch.object(
                    agent, "_save_research_results", new_callable=AsyncMock
                ) as mock_save:
                    mock_save.return_value = 1

                    result = await agent.run(sample_campaign_id)

                    mock_research.assert_called_once_with(companies)
                    mock_save.assert_called_once()
                    assert result.success is True
                    assert result.companies_researched == 1

    @pytest.mark.asyncio
    async def test_run_calculates_metrics(
        self,
        agent: CompanyResearchAgent,
        sample_campaign_id: UUID,
    ) -> None:
        """Test run calculates correct metrics."""
        companies = [
            CompanyToResearch(
                lead_id=uuid4(),
                company_name="Acme Corp",
                company_domain="acme.com",
            ),
            CompanyToResearch(
                lead_id=uuid4(),
                company_name="TechCo",
                company_domain="techco.com",
            ),
        ]

        results = [
            ResearchResult(
                company_domain="acme.com",
                company_name="Acme Corp",
                success=True,
                has_recent_news=True,
                has_funding=True,
                relevance_score=0.8,
                facts=[
                    ExtractedFact(
                        fact_text="Test fact",
                        category="news",
                        source_type="web",
                        total_score=0.7,
                    ),
                ],
            ),
            ResearchResult(
                company_domain="techco.com",
                company_name="TechCo",
                success=False,
                error_message="API error",
            ),
        ]

        with patch.object(agent, "_get_unique_companies", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = companies

            with patch.object(
                agent, "_research_companies_parallel", new_callable=AsyncMock
            ) as mock_research:
                mock_research.return_value = results

                with patch.object(
                    agent, "_save_research_results", new_callable=AsyncMock
                ) as mock_save:
                    mock_save.return_value = 1

                    result = await agent.run(sample_campaign_id)

                    assert result.total_companies == 2
                    assert result.companies_researched == 1
                    assert result.companies_failed == 1
                    assert result.facts_extracted == 1

    @pytest.mark.asyncio
    async def test_run_handles_exception(
        self,
        agent: CompanyResearchAgent,
        sample_campaign_id: UUID,
    ) -> None:
        """Test run handles exceptions gracefully."""
        with patch.object(agent, "_get_unique_companies", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            result = await agent.run(sample_campaign_id)

            assert result.success is False
            assert "Database connection failed" in str(result.error_message)


class TestResearchSingleCompany:
    """Tests for _research_single_company method."""

    @pytest.fixture
    def agent(self) -> CompanyResearchAgent:
        """Create agent fixture."""
        return CompanyResearchAgent()

    @pytest.fixture
    def sample_company(self) -> CompanyToResearch:
        """Create sample company fixture."""
        return CompanyToResearch(
            lead_id=uuid4(),
            company_name="Acme Corp",
            company_domain="acme.com",
        )

    @pytest.mark.asyncio
    async def test_calls_all_search_tools(
        self,
        agent: CompanyResearchAgent,
        sample_company: CompanyToResearch,
    ) -> None:
        """Test that all search tools are called."""
        mock_result = {
            "data": {
                "results": [],
                "result_count": 0,
                "cost": 0.001,
                "tool_used": "serper_search",
            },
        }

        with patch(
            "src.agents.company_research.agent.search_company_news_tool",
            new_callable=AsyncMock,
        ) as mock_news:
            mock_news.return_value = mock_result

            with patch(
                "src.agents.company_research.agent.search_company_funding_tool",
                new_callable=AsyncMock,
            ) as mock_funding:
                mock_funding.return_value = mock_result

                with patch(
                    "src.agents.company_research.agent.search_company_hiring_tool",
                    new_callable=AsyncMock,
                ) as mock_hiring:
                    mock_hiring.return_value = mock_result

                    with patch(
                        "src.agents.company_research.agent.search_company_tech_tool",
                        new_callable=AsyncMock,
                    ) as mock_tech:
                        mock_tech.return_value = mock_result

                        with patch(
                            "src.agents.company_research.agent.extract_and_score_facts_tool",
                            new_callable=AsyncMock,
                        ) as mock_extract:
                            mock_extract.return_value = {"data": {"facts": []}}

                            with patch(
                                "src.agents.company_research.agent.aggregate_company_research_tool",
                                new_callable=AsyncMock,
                            ) as mock_aggregate:
                                mock_aggregate.return_value = {
                                    "data": {
                                        "headline": "Test",
                                        "summary": "Test",
                                        "primary_hook": "Test hook",
                                        "relevance_score": 0.7,
                                        "has_recent_news": True,
                                        "has_funding": False,
                                        "has_hiring": False,
                                        "has_product_launch": False,
                                        "facts": [],
                                        "personalization_hooks": {},
                                        "source_urls": [],
                                        "total_cost": 0.004,
                                        "tools_used": ["serper_search"],
                                    },
                                }

                                result = await agent._research_single_company(sample_company)

                                mock_news.assert_called_once()
                                mock_funding.assert_called_once()
                                mock_hiring.assert_called_once()
                                mock_tech.assert_called_once()
                                assert result.success is True

    @pytest.mark.asyncio
    async def test_handles_tool_exception(
        self,
        agent: CompanyResearchAgent,
        sample_company: CompanyToResearch,
    ) -> None:
        """Test handling of tool exceptions."""
        with patch(
            "src.agents.company_research.agent.search_company_news_tool",
            new_callable=AsyncMock,
        ) as mock_news:
            mock_news.side_effect = Exception("API error")

            with patch(
                "src.agents.company_research.agent.search_company_funding_tool",
                new_callable=AsyncMock,
            ) as mock_funding:
                mock_funding.return_value = {"data": {"results": [], "cost": 0}}

                with patch(
                    "src.agents.company_research.agent.search_company_hiring_tool",
                    new_callable=AsyncMock,
                ) as mock_hiring:
                    mock_hiring.return_value = {"data": {"results": [], "cost": 0}}

                    with patch(
                        "src.agents.company_research.agent.search_company_tech_tool",
                        new_callable=AsyncMock,
                    ) as mock_tech:
                        mock_tech.return_value = {"data": {"results": [], "cost": 0}}

                        with patch(
                            "src.agents.company_research.agent.extract_and_score_facts_tool",
                            new_callable=AsyncMock,
                        ) as mock_extract:
                            mock_extract.return_value = {"data": {"facts": []}}

                            with patch(
                                "src.agents.company_research.agent.aggregate_company_research_tool",
                                new_callable=AsyncMock,
                            ) as mock_aggregate:
                                mock_aggregate.return_value = {
                                    "data": {
                                        "headline": None,
                                        "summary": None,
                                        "primary_hook": None,
                                        "relevance_score": 0,
                                        "has_recent_news": False,
                                        "has_funding": False,
                                        "has_hiring": False,
                                        "has_product_launch": False,
                                        "facts": [],
                                        "personalization_hooks": {},
                                        "source_urls": [],
                                        "total_cost": 0,
                                        "tools_used": [],
                                    },
                                }

                                # Should not raise, should handle gracefully
                                result = await agent._research_single_company(sample_company)
                                # Result might succeed or fail depending on aggregate behavior
                                assert result is not None


class TestCompanyResearchSchemas:
    """Tests for Company Research schemas."""

    def test_company_to_research_defaults(self) -> None:
        """Test CompanyToResearch default values."""
        company = CompanyToResearch(
            lead_id=uuid4(),
            company_name="Test",
            company_domain="test.com",
        )

        assert company.company_linkedin_url is None
        assert company.company_industry is None
        assert company.lead_count == 1

    def test_research_result_defaults(self) -> None:
        """Test ResearchResult default values."""
        result = ResearchResult(
            company_domain="test.com",
            company_name="Test",
        )

        assert result.research_id is None
        assert result.success is True
        assert result.facts == []
        assert result.research_cost == 0.0

    def test_extracted_fact_defaults(self) -> None:
        """Test ExtractedFact default values."""
        fact = ExtractedFact(
            fact_text="Test fact",
            category="news",
            source_type="web",
        )

        assert fact.recency_score == 0.0
        assert fact.total_score == 0.0
        assert fact.context_notes is None

    def test_company_research_input_defaults(self) -> None:
        """Test CompanyResearchInput default values."""
        input_schema = CompanyResearchInput(campaign_id=uuid4())

        assert input_schema.research_depth == "standard"
        assert input_schema.max_companies == 1000
        assert input_schema.max_cost_per_company == 0.10
        assert input_schema.max_total_cost == 100.0

    def test_company_research_output_defaults(self) -> None:
        """Test CompanyResearchOutput default values."""
        output = CompanyResearchOutput(campaign_id=uuid4())

        assert output.total_companies == 0
        assert output.success is True
        assert output.research_cost == 0.0
        assert output.personalization_hooks == {}
