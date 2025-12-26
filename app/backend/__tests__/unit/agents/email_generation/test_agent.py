"""Unit tests for Email Generation Agent."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.email_generation.agent import (
    DirectEmailGenerator,
    EmailGenerationAgent,
)
from src.agents.email_generation.schemas import (
    EmailGenerationResult,
    TierConfig,
)


class TestEmailGenerationAgentInitialization:
    """Tests for agent initialization."""

    def test_agent_initializes_with_defaults(self) -> None:
        """Test agent initializes with default values."""
        agent = EmailGenerationAgent()
        assert agent.name == "email_generation_agent"
        assert agent.description == "Generates personalized cold emails using AI"

    def test_agent_has_tier_configs(self) -> None:
        """Test agent has tier configurations."""
        agent = EmailGenerationAgent()
        assert "A" in agent.tier_configs
        assert "B" in agent.tier_configs
        assert "C" in agent.tier_configs

    def test_tier_configs_are_valid(self) -> None:
        """Test tier configurations are valid TierConfig objects."""
        agent = EmailGenerationAgent()
        assert isinstance(agent.tier_configs["A"], TierConfig)
        assert agent.tier_configs["A"].quality_threshold == 70
        assert agent.tier_configs["B"].quality_threshold == 60
        assert agent.tier_configs["C"].quality_threshold == 50


class TestEmailGenerationAgentSystemPrompt:
    """Tests for system prompt."""

    def test_system_prompt_exists(self) -> None:
        """Test system prompt is defined."""
        agent = EmailGenerationAgent()
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 100

    def test_system_prompt_mentions_frameworks(self) -> None:
        """Test system prompt mentions email frameworks."""
        agent = EmailGenerationAgent()
        prompt = agent.system_prompt
        assert "PAS" in prompt or "Pain-Agitate-Solution" in prompt
        assert "AIDA" in prompt

    def test_system_prompt_mentions_quality(self) -> None:
        """Test system prompt mentions quality requirements."""
        agent = EmailGenerationAgent()
        prompt = agent.system_prompt
        assert "70" in prompt  # Tier A threshold
        assert "60" in prompt  # Tier B threshold
        assert "50" in prompt  # Tier C threshold

    def test_system_prompt_mentions_avoid_patterns(self) -> None:
        """Test system prompt mentions patterns to avoid."""
        agent = EmailGenerationAgent()
        prompt = agent.system_prompt
        assert "AVOID" in prompt
        assert "hope this email finds you well" in prompt.lower()


class TestEmailGenerationAgentStatsReset:
    """Tests for statistics reset."""

    def test_stats_reset_on_init(self) -> None:
        """Test stats are reset on initialization."""
        agent = EmailGenerationAgent()
        assert agent._stats["total_generated"] == 0
        assert agent._stats["tier_a_generated"] == 0
        assert len(agent._stats["quality_scores"]) == 0

    def test_reset_stats_clears_all(self) -> None:
        """Test _reset_stats clears all statistics."""
        agent = EmailGenerationAgent()
        # Simulate some stats
        agent._stats["total_generated"] = 100
        agent._stats["quality_scores"] = [75, 80, 85]

        # Reset
        agent._reset_stats()

        assert agent._stats["total_generated"] == 0
        assert len(agent._stats["quality_scores"]) == 0


class TestEmailGenerationAgentStatsUpdate:
    """Tests for statistics update from responses."""

    def test_update_stats_from_quality_score(self) -> None:
        """Test stats update from quality score response."""
        agent = EmailGenerationAgent()
        data = {"quality_score": 75.0}

        agent._update_stats_from_response(data)

        assert 75.0 in agent._stats["quality_scores"]

    def test_update_stats_from_email_response(self) -> None:
        """Test stats update from email response."""
        agent = EmailGenerationAgent()
        data = {"email_id": "email-123", "framework": "pas"}

        agent._update_stats_from_response(data)

        assert agent._stats["total_generated"] == 1
        assert agent._stats["framework_usage"].get("pas") == 1

    def test_update_stats_from_tier_breakdown(self) -> None:
        """Test stats update from tier breakdown."""
        agent = EmailGenerationAgent()
        data = {
            "tier_a_generated": 10,
            "tier_b_generated": 20,
            "tier_c_generated": 30,
        }

        agent._update_stats_from_response(data)

        assert agent._stats["tier_a_generated"] == 10
        assert agent._stats["tier_b_generated"] == 20
        assert agent._stats["tier_c_generated"] == 30

    def test_update_stats_from_library_save(self) -> None:
        """Test stats update from library save."""
        agent = EmailGenerationAgent()
        data = {"saved": True, "line_id": "line-123"}

        agent._update_stats_from_response(data)

        assert agent._stats["lines_saved_to_library"] == 1


class TestEmailGenerationAgentJSONExtraction:
    """Tests for JSON extraction from responses."""

    def test_extract_json_valid(self) -> None:
        """Test extracting valid JSON."""
        text = 'Some text {"key": "value", "number": 42} more text'
        result = EmailGenerationAgent._extract_json_data(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_no_json(self) -> None:
        """Test extracting when no JSON present."""
        text = "This is just plain text without JSON"
        result = EmailGenerationAgent._extract_json_data(text)
        assert result is None

    def test_extract_json_invalid(self) -> None:
        """Test extracting invalid JSON."""
        text = "Some text {invalid json} more text"
        result = EmailGenerationAgent._extract_json_data(text)
        assert result is None

    def test_extract_json_nested(self) -> None:
        """Test extracting nested JSON."""
        text = '{"outer": {"inner": "value"}, "list": [1, 2, 3]}'
        result = EmailGenerationAgent._extract_json_data(text)
        assert result is not None
        assert result["outer"]["inner"] == "value"
        assert result["list"] == [1, 2, 3]


class TestDirectEmailGeneratorInitialization:
    """Tests for DirectEmailGenerator initialization."""

    def test_direct_generator_initializes(self) -> None:
        """Test direct generator initializes."""
        generator = DirectEmailGenerator()
        assert generator.name == "direct_email_generator"


class TestEmailGenerationResult:
    """Tests for EmailGenerationResult from agent."""

    def test_result_to_dict_complete(self) -> None:
        """Test result to_dict includes all fields."""
        result = EmailGenerationResult(
            success=True,
            campaign_id="campaign-123",
            total_generated=100,
            tier_a_generated=20,
            tier_b_generated=30,
            tier_c_generated=50,
            avg_quality_score=75.5,
            quality_distribution={
                "excellent_85plus": 15,
                "good_70_84": 40,
                "acceptable_55_69": 35,
                "below_55": 10,
            },
            framework_usage={
                "pas": 20,
                "bab": 30,
                "aida": 40,
                "question": 10,
            },
            regeneration_stats={
                "attempted": 25,
                "improved": 20,
            },
            lines_saved_to_library=12,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["campaign_id"] == "campaign-123"
        assert data["total_generated"] == 100
        assert data["tier_breakdown"]["tier_a"] == 20
        assert data["tier_breakdown"]["tier_b"] == 30
        assert data["tier_breakdown"]["tier_c"] == 50
        assert data["avg_quality_score"] == 75.5
        assert data["quality_distribution"]["excellent_85plus"] == 15
        assert data["framework_usage"]["pas"] == 20
        assert data["regeneration_stats"]["attempted"] == 25
        assert data["lines_saved_to_library"] == 12


class TestEmailGenerationAgentGenerateEmails:
    """Tests for generate_emails method."""

    @pytest.mark.asyncio
    async def test_generate_emails_handles_no_leads(self) -> None:
        """Test agent handles campaign with no leads gracefully."""
        agent = EmailGenerationAgent()

        # Mock the query function to return immediately
        with patch("src.agents.email_generation.agent.query") as mock_query:
            # Create an async generator that yields nothing
            async def empty_generator():
                return
                yield  # Makes this a generator

            mock_query.return_value = empty_generator()

            result = await agent.generate_emails("campaign-123")

            assert isinstance(result, EmailGenerationResult)
            assert result.campaign_id == "campaign-123"

    @pytest.mark.asyncio
    async def test_generate_emails_handles_exception(self) -> None:
        """Test agent handles exceptions gracefully."""
        agent = EmailGenerationAgent()

        with patch("src.agents.email_generation.agent.query") as mock_query:
            mock_query.side_effect = Exception("API error")

            result = await agent.generate_emails("campaign-123")

            assert result.success is False
            assert result.error == "API error"


class TestDirectEmailGeneratorBatch:
    """Tests for DirectEmailGenerator batch processing."""

    @pytest.fixture
    def sample_leads(self) -> list[dict[str, Any]]:
        """Create sample leads."""
        return [
            {
                "id": "lead-1",
                "first_name": "John",
                "last_name": "Doe",
                "title": "VP",
                "company_name": "Acme",
                "lead_tier": "A",
            },
            {
                "id": "lead-2",
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "Director",
                "company_name": "Tech Inc",
                "lead_tier": "B",
            },
        ]

    @pytest.fixture
    def sample_persona(self) -> dict[str, Any]:
        """Create sample persona context."""
        return {
            "challenges": ["lead gen"],
            "goals": ["grow pipeline"],
            "messaging_tone": "professional",
        }

    @pytest.fixture
    def sample_niche(self) -> dict[str, Any]:
        """Create sample niche context."""
        return {
            "pain_points": ["slow sales"],
            "value_propositions": ["faster deals"],
        }

    @pytest.mark.asyncio
    async def test_generate_batch_processes_leads(
        self,
        sample_leads: list[dict[str, Any]],
        sample_persona: dict[str, Any],
        sample_niche: dict[str, Any],
    ) -> None:
        """Test batch processing processes leads."""
        generator = DirectEmailGenerator()

        # Mock generate_email_impl (the internal implementation)
        with patch(
            "src.agents.email_generation.agent.generate_email_impl",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = {
                "content": [{"type": "text", "text": '{"email_id": "test"}'}],
                "is_error": False,
            }

            await generator.generate_batch(
                leads=sample_leads,
                persona_context=sample_persona,
                niche_context=sample_niche,
                campaign_id="campaign-123",
                concurrency=2,
            )

            # Should have called generate for each lead
            assert mock_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_batch_handles_errors(
        self,
        sample_leads: list[dict[str, Any]],
        sample_persona: dict[str, Any],
        sample_niche: dict[str, Any],
    ) -> None:
        """Test batch processing handles errors gracefully."""
        generator = DirectEmailGenerator()

        with patch(
            "src.agents.email_generation.agent.generate_email_impl",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = {
                "content": [{"type": "text", "text": "Error"}],
                "is_error": True,
            }

            results = await generator.generate_batch(
                leads=sample_leads,
                persona_context=sample_persona,
                niche_context=sample_niche,
                campaign_id="campaign-123",
            )

            # Should return empty list when all fail
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_generate_batch_respects_concurrency(
        self,
        sample_persona: dict[str, Any],
        sample_niche: dict[str, Any],
    ) -> None:
        """Test batch processing respects concurrency limit."""
        generator = DirectEmailGenerator()

        # Create many leads
        many_leads = [
            {
                "id": f"lead-{i}",
                "first_name": "Test",
                "last_name": "User",
                "title": "Title",
                "company_name": "Company",
                "lead_tier": "C",
            }
            for i in range(10)
        ]

        call_count = 0
        max_concurrent = 0
        current_concurrent = 0

        async def mock_generate(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal call_count, max_concurrent, current_concurrent
            call_count += 1
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            # Simulate some work
            import asyncio

            await asyncio.sleep(0.01)
            current_concurrent -= 1
            return {
                "content": [{"type": "text", "text": '{"email_id": "test"}'}],
                "is_error": False,
            }

        with patch(
            "src.agents.email_generation.agent.generate_email_impl",
            side_effect=mock_generate,
        ):
            await generator.generate_batch(
                leads=many_leads,
                persona_context=sample_persona,
                niche_context=sample_niche,
                campaign_id="campaign-123",
                concurrency=3,
            )

            assert call_count == 10
            # Max concurrent should not exceed limit
            assert max_concurrent <= 3
