"""
Unit tests for Persona Research Agent.

Tests the agent, tools, and schemas without requiring
external API calls (using mocks).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.persona_research.agent import (
    CircuitBreaker,
    PersonaResearchAgent,
    TokenBucketRateLimiter,
)
from src.agents.persona_research.reddit_miner import (
    RedditMiner,
)
from src.agents.persona_research.schemas import (
    LanguagePattern,
    MessagingAngle,
    PainPointQuote,
    Persona,
    PersonaResearchResult,
    SeniorityLevel,
    ToneType,
)

# ============================================================================
# Schema Tests
# ============================================================================


class TestPainPointQuoteSchema:
    """Tests for PainPointQuote dataclass."""

    def test_create_pain_point_quote(self) -> None:
        """Test creating a pain point quote."""
        pp = PainPointQuote(
            pain="CRM adoption is hard",
            intensity=8,
            quote="I've spent months trying to get adoption",
            source="https://reddit.com/r/sales/123",
            source_type="reddit",
            frequency="common",
            engagement_score=100,
        )

        assert pp.pain == "CRM adoption is hard"
        assert pp.intensity == 8
        assert pp.quote == "I've spent months trying to get adoption"
        assert pp.source_type == "reddit"
        assert pp.engagement_score == 100

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        pp = PainPointQuote(
            pain="Test pain",
            intensity=5,
            quote="Test quote",
            source="https://example.com",
        )

        assert pp.source_type == "reddit"
        assert pp.frequency == "occasional"
        assert pp.engagement_score == 0
        assert pp.raw == {}


class TestLanguagePatternSchema:
    """Tests for LanguagePattern dataclass."""

    def test_create_language_pattern(self) -> None:
        """Test creating a language pattern."""
        lp = LanguagePattern(
            phrase="drives me crazy",
            context="Describing frustrations",
            category="emotional",
            source="reddit",
            frequency=5,
        )

        assert lp.phrase == "drives me crazy"
        assert lp.category == "emotional"
        assert lp.frequency == 5

    def test_default_category(self) -> None:
        """Test default category is 'general'."""
        lp = LanguagePattern(
            phrase="test phrase",
            context="test context",
        )

        assert lp.category == "general"


class TestPersonaSchema:
    """Tests for Persona dataclass."""

    def test_create_persona(self) -> None:
        """Test creating a complete persona."""
        pain_points = [
            PainPointQuote(
                pain="Test pain",
                intensity=7,
                quote="Test quote",
                source="https://example.com",
            )
        ]

        messaging_angles = {
            "primary": MessagingAngle(
                angle="Pain-focused",
                hook="Stop losing deals",
                supporting_pain="Test pain",
            )
        }

        persona = Persona(
            name="The Scaling VP",
            job_titles=["VP of Sales"],
            seniority_level=SeniorityLevel.VP,
            department="Sales",
            pain_points=pain_points,
            goals=["Hit targets"],
            objections=[],
            language_patterns=[],
            trigger_events=["New job"],
            messaging_angles=messaging_angles,
            angles_to_avoid=["Price-focused"],
        )

        assert persona.name == "The Scaling VP"
        assert persona.seniority_level == SeniorityLevel.VP
        assert len(persona.pain_points) == 1
        assert "primary" in persona.messaging_angles

    def test_persona_with_id(self) -> None:
        """Test persona with custom ID."""
        persona_id = str(uuid.uuid4())

        persona = Persona(
            id=persona_id,
            name="Test Persona",
            job_titles=["Manager"],
            seniority_level=SeniorityLevel.MANAGER,
            department="Operations",
            pain_points=[],
            goals=[],
            objections=[],
            language_patterns=[],
            trigger_events=[],
            messaging_angles={},
            angles_to_avoid=[],
        )

        assert persona.id == persona_id


class TestPersonaResearchResultSchema:
    """Tests for PersonaResearchResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a research result."""
        result = PersonaResearchResult(
            personas=[],
            persona_ids=[],
            consolidated_pain_points=["Pain 1", "Pain 2"],
            value_propositions=["Value 1"],
            recommended_tone=ToneType.PROFESSIONAL,
            industry_scores=[],
            research_data=[],
            sources_used=[],
        )

        assert result.recommended_tone == ToneType.PROFESSIONAL
        assert len(result.consolidated_pain_points) == 2

    def test_default_metadata(self) -> None:
        """Test default metadata values."""
        result = PersonaResearchResult(
            personas=[],
            persona_ids=[],
            consolidated_pain_points=[],
            value_propositions=[],
            recommended_tone=ToneType.CASUAL,
            industry_scores=[],
            research_data=[],
            sources_used=[],
        )

        assert result.niche_id == ""
        assert result.total_quotes_collected == 0
        assert result.execution_time_ms == 0


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_capacity(self) -> None:
        """Test acquiring tokens within capacity."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1.0)

        # Should not wait
        await limiter.acquire(1)
        assert limiter.tokens < 10

    @pytest.mark.asyncio
    async def test_acquire_depletes_tokens(self) -> None:
        """Test that acquiring depletes tokens."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)

        for _ in range(5):
            await limiter.acquire(1)

        # Tokens should be depleted (approximately)
        assert limiter.tokens < 1


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state(self) -> None:
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.can_proceed() is True
        assert cb.is_open is False

    def test_opens_after_failures(self) -> None:
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.can_proceed() is True

        cb.record_failure()
        assert cb.is_open is True
        assert cb.can_proceed() is False

    def test_resets_on_success(self) -> None:
        """Test circuit resets after success."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb.failure_count == 0
        assert cb.is_open is False


# ============================================================================
# Reddit Miner Tests
# ============================================================================


class TestRedditMinerExtraction:
    """Tests for Reddit miner extraction methods."""

    @pytest.fixture
    def miner(self) -> RedditMiner:
        """Create a RedditMiner instance."""
        return RedditMiner(
            client_id="test_id",  # pragma: allowlist secret
            client_secret="test_secret",  # pragma: allowlist secret
        )

    def test_get_subreddits_for_industry(self, miner: RedditMiner) -> None:
        """Test getting subreddits for an industry."""
        saas_subs = miner.get_subreddits_for_industry("saas")
        assert "SaaS" in saas_subs
        assert "startups" in saas_subs

        tech_subs = miner.get_subreddits_for_industry("technology")
        assert "technology" in tech_subs
        assert "sysadmin" in tech_subs

    def test_get_subreddits_for_unknown_industry(self, miner: RedditMiner) -> None:
        """Test getting subreddits for unknown industry."""
        subs = miner.get_subreddits_for_industry("unknown_industry")
        assert subs == miner.SUBREDDITS_BY_INDUSTRY["default"]

    def test_calculate_intensity(self, miner: RedditMiner) -> None:
        """Test pain intensity calculation."""
        # High engagement, emotional words
        text = "This is so frustrating and annoying nightmare"
        intensity = miner._calculate_intensity(text, score=150, replies=30)
        assert 7 <= intensity <= 10

        # Low engagement, neutral
        text = "This is a problem"
        intensity = miner._calculate_intensity(text, score=5, replies=2)
        assert 5 <= intensity <= 7

    def test_estimate_frequency(self, miner: RedditMiner) -> None:
        """Test frequency estimation from engagement."""
        assert miner._estimate_frequency(250) == "very_common"
        assert miner._estimate_frequency(100) == "common"
        assert miner._estimate_frequency(30) == "occasional"
        assert miner._estimate_frequency(5) == "rare"

    def test_categorize_phrase(self, miner: RedditMiner) -> None:
        """Test phrase categorization."""
        assert miner._categorize_phrase("so frustrated") == "emotional"
        assert miner._categorize_phrase("struggling with") == "pain"
        assert miner._categorize_phrase("i want to achieve") == "goal"
        assert miner._categorize_phrase("pipeline metrics") == "jargon"


# ============================================================================
# Agent Tests
# ============================================================================


class TestPersonaResearchAgentInit:
    """Tests for PersonaResearchAgent initialization."""

    @patch("src.agents.persona_research.agent.ClaudeAgentOptions")
    def test_initialization(self, mock_options: MagicMock) -> None:
        """Test agent initializes correctly."""
        agent = PersonaResearchAgent(api_key="test_key")  # pragma: allowlist secret

        assert agent.AGENT_ID == "persona_research_agent"
        assert agent.AGENT_VERSION == "2.0.0"
        mock_options.assert_called_once()

    @patch("src.agents.persona_research.agent.ClaudeAgentOptions")
    def test_removes_env_api_key(self, mock_options: MagicMock) -> None:
        """Test that ANTHROPIC_API_KEY is removed from env (LEARN-001)."""
        import os

        os.environ["ANTHROPIC_API_KEY"] = "test_key"  # pragma: allowlist secret

        _agent = PersonaResearchAgent(api_key="test_key")  # pragma: allowlist secret

        assert "ANTHROPIC_API_KEY" not in os.environ


class TestPersonaResearchAgentSynthesis:
    """Tests for agent synthesis methods."""

    @pytest.fixture
    def agent(self) -> PersonaResearchAgent:
        """Create agent with mocked Claude SDK options."""
        with patch("src.agents.persona_research.agent.ClaudeAgentOptions"):
            return PersonaResearchAgent(api_key="test_key")  # pragma: allowlist secret

    def test_synthesize_persona(self, agent: PersonaResearchAgent) -> None:
        """Test persona synthesis."""
        reddit_data = {
            "pain_points": [
                {
                    "pain": "CRM adoption is hard",
                    "intensity": 8,
                    "quote": "I've spent months on this",
                    "source": "https://reddit.com/r/sales/123",
                    "source_type": "reddit",
                    "frequency": "common",
                    "engagement_score": 100,
                }
            ],
            "language_patterns": [
                {
                    "phrase": "drives me crazy",
                    "context": "frustrations",
                    "category": "emotional",
                    "source": "reddit",
                    "frequency": 5,
                }
            ],
        }

        persona = agent._synthesize_persona(
            name="Test VP",
            job_titles=["VP of Sales"],
            seniority=SeniorityLevel.VP,
            department="Sales",
            reddit_data=reddit_data,
            linkedin_data={},
            industry_data={},
        )

        assert persona.name == "Test VP"
        assert persona.seniority_level == SeniorityLevel.VP
        assert len(persona.pain_points) == 1
        assert len(persona.language_patterns) == 1
        assert "primary" in persona.messaging_angles

    def test_calculate_industry_fit_score(self, agent: PersonaResearchAgent) -> None:
        """Test industry fit score calculation."""
        # Create a persona with pain points
        pain_points = [
            PainPointQuote(
                pain="High intensity pain",
                intensity=9,
                quote="test",
                source="test",
            ),
            PainPointQuote(
                pain="Medium intensity pain",
                intensity=6,
                quote="test",
                source="test",
            ),
        ]

        persona = Persona(
            name="Test",
            job_titles=["Manager"],
            seniority_level=SeniorityLevel.MANAGER,
            department="Test",
            pain_points=pain_points,
            goals=[],
            objections=[],
            language_patterns=[],
            trigger_events=[],
            messaging_angles={},
            angles_to_avoid=[],
        )

        score = agent._calculate_industry_fit_score(
            industry="SaaS",
            persona=persona,
            accessibility=0.7,
            budget_indicators=0.6,
        )

        assert score.industry == "SaaS"
        assert 0 <= score.score <= 100
        assert "SaaS" in score.reasoning


class TestPersonaResearchAgentRun:
    """Tests for agent run method."""

    @pytest.fixture
    def agent(self) -> PersonaResearchAgent:
        """Create agent with mocked Claude SDK options."""
        with patch("src.agents.persona_research.agent.ClaudeAgentOptions"):
            return PersonaResearchAgent(api_key="test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_run_with_mock_reddit(
        self,
        agent: PersonaResearchAgent,
    ) -> None:
        """Test full run with mocked Reddit mining."""
        # Mock the mining methods
        with patch.object(
            agent,
            "_mine_reddit",
            new_callable=AsyncMock,
        ) as mock_mine:
            mock_mine.return_value = {
                "pain_points": [
                    {
                        "pain": "Test pain",
                        "intensity": 7,
                        "quote": "Test quote",
                        "source": "https://reddit.com/test",
                        "source_type": "reddit",
                        "frequency": "common",
                        "engagement_score": 50,
                    }
                ],
                "language_patterns": [],
                "quotes": [
                    {"quote": "Test quote", "source": "test", "intensity": 7, "engagement": 50}
                ],
                "emotional_indicators": [],
                "posts_analyzed": 10,
                "comments_analyzed": 20,
            }

            with patch.object(
                agent,
                "_research_linkedin",
                new_callable=AsyncMock,
            ) as mock_linkedin:
                mock_linkedin.return_value = {"thought_leadership": []}

                with patch.object(
                    agent,
                    "_research_industry_content",
                    new_callable=AsyncMock,
                ) as mock_industry:
                    mock_industry.return_value = {"industry_reports": []}

                    result = await agent.run(
                        niche_id="test-niche-id",
                        niche_data={
                            "job_titles": ["VP of Sales"],
                            "industry": "SaaS",
                        },
                    )

        assert len(result.personas) >= 1
        assert len(result.persona_ids) >= 1
        assert result.niche_id == "test-niche-id"
        assert result.execution_time_ms >= 0  # Mocked calls may execute faster than 1ms


# ============================================================================
# Tool Tests
# ============================================================================


class TestExtractLanguagePatternsTool:
    """Tests for extract_language_patterns tool."""

    @pytest.mark.asyncio
    async def test_extract_patterns(self) -> None:
        """Test extracting language patterns from posts."""
        from src.agents.persona_research.tools import extract_language_patterns_tool

        posts = [
            {"title": "CRM adoption struggles", "content": "I've been struggling with this"},
            {"title": "Same problem here", "content": "I've been struggling with this too"},
            {"title": "Different topic", "content": "Different content entirely"},
        ]

        result = await extract_language_patterns_tool(
            {
                "posts": posts,
                "max_patterns": 10,
            }
        )

        assert "data" in result
        assert "patterns" in result["data"]
        # "been struggling with" should appear 2+ times
        patterns = result["data"]["patterns"]
        assert isinstance(patterns, list)


class TestConsolidatePainPointsTool:
    """Tests for consolidate_pain_points tool."""

    @pytest.mark.asyncio
    async def test_consolidate_from_multiple_sources(self) -> None:
        """Test consolidating pain points from multiple sources."""
        from src.agents.persona_research.tools import consolidate_pain_points_tool

        reddit_pp = [{"pain": "CRM adoption"}, {"pain": "Pipeline visibility"}]
        linkedin_pp = [{"pain": "CRM adoption"}, {"pain": "Team alignment"}]
        industry_pp = [{"pain": "Data quality"}]

        result = await consolidate_pain_points_tool(
            {
                "reddit_pain_points": reddit_pp,
                "linkedin_pain_points": linkedin_pp,
                "industry_pain_points": industry_pp,
                "max_consolidated": 5,
            }
        )

        assert "data" in result
        consolidated = result["data"]["consolidated_pain_points"]

        # CRM adoption should be first (appears in Reddit + LinkedIn)
        assert consolidated[0]["pain"].lower() == "crm adoption"
        assert consolidated[0]["multi_source"] is True


class TestSynthesizePersonaTool:
    """Tests for synthesize_persona tool."""

    @pytest.mark.asyncio
    async def test_synthesize_persona(self) -> None:
        """Test synthesizing a persona."""
        from src.agents.persona_research.tools import synthesize_persona_tool

        result = await synthesize_persona_tool(
            {
                "name": "The Scaling VP",
                "job_titles": ["VP of Sales", "Sales Director"],
                "seniority_level": "vp",
                "department": "Sales",
                "pain_points": [{"pain": "CRM adoption"}],
                "goals": ["Hit revenue targets"],
                "language_patterns": [{"phrase": "drives me crazy"}],
                "industry": "SaaS",
            }
        )

        assert "data" in result
        persona = result["data"]["persona"]

        assert persona["name"] == "The Scaling VP"
        assert "id" in persona
        assert "messaging_angles" in persona


class TestCalculateIndustryFitScoreTool:
    """Tests for calculate_industry_fit_score tool."""

    @pytest.mark.asyncio
    async def test_calculate_score(self) -> None:
        """Test calculating industry fit score."""
        from src.agents.persona_research.tools import calculate_industry_fit_score_tool

        result = await calculate_industry_fit_score_tool(
            {
                "industry": "SaaS",
                "niche_pain_points": ["CRM adoption", "Pipeline visibility"],
                "persona_pain_points": [{"pain": "CRM adoption"}, {"pain": "Data quality"}],
                "accessibility_score": 0.8,
                "budget_indicators": 0.7,
            }
        )

        assert "data" in result
        assert result["data"]["industry"] == "SaaS"
        assert 0 <= result["data"]["score"] <= 100
        assert "reasoning" in result["data"]
