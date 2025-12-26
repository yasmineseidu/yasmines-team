"""Unit tests for Lead Research Agent.

Tests the LeadResearchAgent class:
- Initialization
- research_single_lead
- research_campaign
- Cost tracking
- Tier-based research depth
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agents.lead_research.agent import (
    LeadResearchAgent,
)
from src.agents.lead_research.schemas import (
    COST_CONTROLS,
    TIER_CONFIGS,
    LeadData,
    LeadResearchInput,
    LeadTier,
    ResearchDepth,
)


class TestLeadResearchAgentInitialization:
    """Tests for agent initialization."""

    def test_initializes_with_correct_name(self) -> None:
        """Test agent has correct name."""
        agent = LeadResearchAgent()
        assert agent.name == "lead_research_agent"

    def test_initializes_rate_limiters(self) -> None:
        """Test rate limiters are initialized for each service."""
        agent = LeadResearchAgent()

        assert "tavily" in agent._rate_limiters
        assert "serper" in agent._rate_limiters
        assert "perplexity" in agent._rate_limiters

    def test_initializes_circuit_breakers(self) -> None:
        """Test circuit breakers are initialized for each service."""
        agent = LeadResearchAgent()

        assert "tavily" in agent._circuit_breakers
        assert "serper" in agent._circuit_breakers
        assert "perplexity" in agent._circuit_breakers

    def test_initializes_mcp_server(self) -> None:
        """Test MCP server is initialized with tools."""
        agent = LeadResearchAgent()
        assert agent._mcp_server is not None

    def test_initializes_cost_tracking(self) -> None:
        """Test cost tracking is initialized to zero."""
        agent = LeadResearchAgent()

        assert agent._total_cost == Decimal("0.0")
        assert agent._cost_by_tier["tier_a"] == Decimal("0.0")
        assert agent._cost_by_tier["tier_b"] == Decimal("0.0")
        assert agent._cost_by_tier["tier_c"] == Decimal("0.0")


class TestLeadResearchAgentSystemPrompt:
    """Tests for system prompt."""

    def test_system_prompt_contains_tier_info(self) -> None:
        """Test system prompt describes tier-based research."""
        agent = LeadResearchAgent()

        assert "Tier A" in agent.system_prompt
        assert "Tier B" in agent.system_prompt
        assert "Tier C" in agent.system_prompt

    def test_system_prompt_mentions_personalization(self) -> None:
        """Test system prompt mentions personalization goal."""
        agent = LeadResearchAgent()

        assert "personalization" in agent.system_prompt.lower()
        assert "email" in agent.system_prompt.lower()


class TestResearchSingleLead:
    """Tests for research_single_lead method."""

    @pytest.fixture
    def agent(self) -> LeadResearchAgent:
        """Create agent fixture."""
        return LeadResearchAgent()

    @pytest.fixture
    def tier_a_lead(self) -> LeadData:
        """Create Tier A lead fixture."""
        return LeadData(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            title="CEO",
            headline="Building the future of AI",
            linkedin_url="https://linkedin.com/in/johndoe",
            company_name="TechCorp",
            lead_score=90,
            lead_tier=LeadTier.A,
        )

    @pytest.fixture
    def tier_c_lead(self) -> LeadData:
        """Create Tier C lead fixture."""
        return LeadData(
            id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            title="Manager",
            headline="Sales Manager",
            linkedin_url="https://linkedin.com/in/janesmith",
            company_name="SalesCo",
            lead_score=50,
            lead_tier=LeadTier.C,
        )

    @pytest.mark.asyncio
    async def test_tier_a_uses_deep_research(
        self, agent: LeadResearchAgent, tier_a_lead: LeadData
    ) -> None:
        """Test Tier A leads get deep research."""
        # Mock all the search methods
        with (
            patch.object(
                agent, "_search_linkedin_posts", new_callable=AsyncMock
            ) as mock_linkedin,
            patch.object(agent, "_search_profile", new_callable=AsyncMock) as mock_profile,
            patch.object(agent, "_search_articles", new_callable=AsyncMock) as mock_articles,
            patch.object(agent, "_search_podcasts", new_callable=AsyncMock) as mock_podcasts,
        ):
            mock_linkedin.return_value = {"posts": [], "cost": 0.001}
            mock_profile.return_value = {"profile": {}, "cost": 0.001}
            mock_articles.return_value = {"articles": [], "cost": 0.001}
            mock_podcasts.return_value = {"podcasts": [], "cost": 0.001}

            result = await agent.research_single_lead(tier_a_lead)

        assert result.research_depth == ResearchDepth.DEEP
        mock_linkedin.assert_called_once()
        mock_profile.assert_called_once()
        mock_articles.assert_called_once()
        mock_podcasts.assert_called_once()

    @pytest.mark.asyncio
    async def test_tier_c_uses_basic_research(
        self, agent: LeadResearchAgent, tier_c_lead: LeadData
    ) -> None:
        """Test Tier C leads get basic research (headline only)."""
        with patch.object(
            agent, "_research_headline_only", new_callable=AsyncMock
        ) as mock_headline:
            mock_headline.return_value = {
                "profile": {"headline": "Sales Manager", "keywords": ["sales"]},
                "cost": 0,
            }

            result = await agent.research_single_lead(tier_c_lead)

        assert result.research_depth == ResearchDepth.BASIC
        mock_headline.assert_called_once()
        # Should be zero cost for basic research
        assert result.research_cost == Decimal("0")

    @pytest.mark.asyncio
    async def test_tracks_cost_per_lead(
        self, agent: LeadResearchAgent, tier_a_lead: LeadData
    ) -> None:
        """Test cost tracking per lead."""
        with (
            patch.object(
                agent, "_search_linkedin_posts", new_callable=AsyncMock
            ) as mock_linkedin,
            patch.object(agent, "_search_profile", new_callable=AsyncMock) as mock_profile,
            patch.object(agent, "_search_articles", new_callable=AsyncMock) as mock_articles,
            patch.object(agent, "_search_podcasts", new_callable=AsyncMock) as mock_podcasts,
        ):
            mock_linkedin.return_value = {"posts": [], "cost": 0.01}
            mock_profile.return_value = {"profile": {}, "cost": 0.01}
            mock_articles.return_value = {"articles": [], "cost": 0.01}
            mock_podcasts.return_value = {"podcasts": [], "cost": 0.01}

            result = await agent.research_single_lead(tier_a_lead)

        assert result.research_cost > Decimal("0")
        assert agent._total_cost > Decimal("0")

    @pytest.mark.asyncio
    async def test_uses_fallback_when_no_angles(
        self, agent: LeadResearchAgent, tier_a_lead: LeadData
    ) -> None:
        """Test fallback to company research when no angles found."""
        company_research = {
            "personalization_angle": "Your company's AI innovation",
        }

        with (
            patch.object(
                agent, "_search_linkedin_posts", new_callable=AsyncMock
            ) as mock_linkedin,
            patch.object(agent, "_search_profile", new_callable=AsyncMock) as mock_profile,
            patch.object(agent, "_search_articles", new_callable=AsyncMock) as mock_articles,
            patch.object(agent, "_search_podcasts", new_callable=AsyncMock) as mock_podcasts,
        ):
            # Return empty results to trigger fallback
            mock_linkedin.return_value = {"posts": [], "cost": 0.001}
            mock_profile.return_value = {"profile": {}, "cost": 0.001}
            mock_articles.return_value = {"articles": [], "cost": 0.001}
            mock_podcasts.return_value = {"podcasts": [], "cost": 0.001}

            result = await agent.research_single_lead(
                tier_a_lead, company_research=company_research
            )

        # Should have fallback angle
        fallback_angles = [a for a in result.angles if a.is_fallback]
        assert len(fallback_angles) >= 1


class TestResearchCampaign:
    """Tests for research_campaign method."""

    @pytest.fixture
    def agent(self) -> LeadResearchAgent:
        """Create agent fixture."""
        return LeadResearchAgent()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_leads(self, agent: LeadResearchAgent) -> None:
        """Test returns empty result when no leads found."""
        input_data = LeadResearchInput(campaign_id=uuid4())

        with patch.object(agent, "_get_leads_for_research", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            result = await agent.research_campaign(input_data)

        assert result.total_researched == 0
        assert result.research_cost == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_processes_leads_by_tier(self, agent: LeadResearchAgent) -> None:
        """Test leads are processed by tier."""
        input_data = LeadResearchInput(campaign_id=uuid4())

        tier_a_lead = LeadData(
            id=uuid4(),
            first_name="A",
            last_name="Lead",
            lead_tier=LeadTier.A,
        )
        tier_b_lead = LeadData(
            id=uuid4(),
            first_name="B",
            last_name="Lead",
            lead_tier=LeadTier.B,
        )

        with (
            patch.object(
                agent, "_get_leads_for_research", new_callable=AsyncMock
            ) as mock_get,
            patch.object(
                agent, "_process_tier_parallel", new_callable=AsyncMock
            ) as mock_process,
        ):
            mock_get.return_value = [tier_a_lead, tier_b_lead]
            mock_process.return_value = []

            await agent.research_campaign(input_data)

        # Should be called for each tier with leads
        assert mock_process.call_count >= 2


class TestCostTracking:
    """Tests for cost tracking."""

    @pytest.fixture
    def agent(self) -> LeadResearchAgent:
        """Create agent fixture."""
        return LeadResearchAgent()

    def test_check_lead_budget_allows_when_under(self, agent: LeadResearchAgent) -> None:
        """Test budget check allows when under limit."""
        agent._total_cost = Decimal("10.00")

        assert agent._check_lead_budget(LeadTier.A) is True

    def test_check_lead_budget_blocks_when_over(self, agent: LeadResearchAgent) -> None:
        """Test budget check blocks when over limit."""
        agent._total_cost = COST_CONTROLS["max_per_campaign"]

        assert agent._check_lead_budget(LeadTier.A) is False

    def test_update_cost_updates_all_trackers(self, agent: LeadResearchAgent) -> None:
        """Test cost update updates all tracking fields."""
        lead_id = str(uuid4())
        cost = Decimal("0.05")

        agent._update_cost(LeadTier.A, cost, lead_id)

        assert agent._total_cost == cost
        assert agent._cost_by_tier["tier_a"] == cost
        assert agent._cost_by_lead[lead_id] == cost


class TestTierConfigs:
    """Tests for tier configurations."""

    def test_tier_a_config(self) -> None:
        """Test Tier A configuration."""
        config = TIER_CONFIGS[LeadTier.A]

        assert config.depth == ResearchDepth.DEEP
        assert config.queries == 5
        assert config.max_cost == Decimal("0.15")
        assert "linkedin_posts" in config.include
        assert "podcasts" in config.include

    def test_tier_b_config(self) -> None:
        """Test Tier B configuration."""
        config = TIER_CONFIGS[LeadTier.B]

        assert config.depth == ResearchDepth.STANDARD
        assert config.queries == 3
        assert config.max_cost == Decimal("0.05")
        assert "linkedin_posts" in config.include
        assert "podcasts" not in config.include

    def test_tier_c_config(self) -> None:
        """Test Tier C configuration."""
        config = TIER_CONFIGS[LeadTier.C]

        assert config.depth == ResearchDepth.BASIC
        assert config.queries == 1
        assert config.max_cost == Decimal("0.01")
        assert "headline_analysis" in config.include


class TestLeadData:
    """Tests for LeadData schema."""

    def test_full_name_property(self) -> None:
        """Test full_name property."""
        lead = LeadData(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
        )

        assert lead.full_name == "John Doe"

    def test_full_name_handles_missing_parts(self) -> None:
        """Test full_name with missing parts."""
        lead = LeadData(
            id=uuid4(),
            first_name="John",
            last_name=None,
        )

        assert lead.full_name == "John"

    def test_get_tier_config(self) -> None:
        """Test get_tier_config method."""
        lead = LeadData(
            id=uuid4(),
            lead_tier=LeadTier.A,
        )

        config = lead.get_tier_config()

        assert config.depth == ResearchDepth.DEEP

    def test_get_tier_config_defaults_to_c(self) -> None:
        """Test get_tier_config defaults to C when no tier."""
        lead = LeadData(
            id=uuid4(),
            lead_tier=None,
        )

        config = lead.get_tier_config()

        assert config.depth == ResearchDepth.BASIC
