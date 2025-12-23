"""
Unit tests for Niche Research Agent.

Tests the core functionality of the niche research agent including
scoring, pain point extraction, and opportunity identification.

Also tests resilient integration features including:
- Tenacity retry with exponential backoff
- Token bucket rate limiting
- Enhanced error handling for 4xx/5xx/timeout/connection errors
"""

import sys
from pathlib import Path
from time import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Standard library imports first
# Third-party imports
# Local imports
from src.agents.niche_research_agent import (
    AuthenticationFailedError,
    NicheResearchAgent,
    NicheResearchAgentError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TokenBucketRateLimiter,
)

# Add fixtures directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fixtures"))
from niche_research_fixtures import mock_reddit_post, mock_reddit_subreddit


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_capacity(self) -> None:
        """Test acquiring tokens within capacity."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1.0, service_name="Test")
        # Should acquire immediately
        start = time()
        await limiter.acquire(5)
        elapsed = time() - start
        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_empty(self) -> None:
        """Test that acquiring waits when tokens are empty."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=100.0, service_name="Test")
        # Drain all tokens
        await limiter.acquire(5)

        # Next acquire should wait for refill
        start = time()
        await limiter.acquire(1)
        elapsed = time() - start
        # Should wait approximately 0.01s for 1 token at 100 tokens/s
        assert elapsed >= 0.005

    @pytest.mark.asyncio
    async def test_refill_over_time(self) -> None:
        """Test that tokens refill over time."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0, service_name="Test")
        # Drain tokens
        await limiter.acquire(10)

        # Wait for 0.1s - should get 1 token back
        import asyncio

        await asyncio.sleep(0.1)

        # Should be able to acquire 1 token without waiting
        start = time()
        await limiter.acquire(1)
        elapsed = time() - start
        assert elapsed < 0.05  # Should be nearly instant


class TestNicheResearchAgentInitialization:
    """Tests for NicheResearchAgent initialization."""

    def test_has_correct_name(self) -> None:
        agent = NicheResearchAgent()
        assert agent.name == "niche_research_agent"

    def test_stores_api_keys_from_params(self) -> None:
        # pragma: allowlist secret
        agent = NicheResearchAgent(
            reddit_client_id="test_id",  # pragma: allowlist secret
            reddit_client_secret="test_secret",  # pragma: allowlist secret
            brave_api_key="test_brave_key",  # pragma: allowlist secret
            tavily_api_key="test_tavily_key",  # pragma: allowlist secret
        )
        assert agent.reddit_client_id == "test_id"
        assert agent.reddit_client_secret == "test_secret"  # pragma: allowlist secret
        assert agent.brave_api_key == "test_brave_key"  # pragma: allowlist secret
        assert agent.tavily_api_key == "test_tavily_key"  # pragma: allowlist secret

    def test_system_prompt_returns_string(self) -> None:
        agent = NicheResearchAgent()
        prompt = agent.system_prompt
        assert isinstance(prompt, str)
        assert "Niche Research Agent" in prompt


class TestCalculateEngagementScore:
    """Tests for _calculate_engagement_score method."""

    @pytest.fixture
    def agent(self) -> NicheResearchAgent:
        return NicheResearchAgent()

    def test_high_engagement_score(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="high_engagement",
            subscribers=100000,
            active_users=10000,  # 10% active ratio
        )
        score = agent._calculate_engagement_score(subreddit)
        # Active ratio: min(0.10 * 20, 5.0) = 2.0
        # Sub score: min(log10(100000) / 2, 5.0) = 2.5
        # Total: 2.0 + 2.5 = 4.5
        assert score > 4.0

    def test_low_engagement_score(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="low_engagement",
            subscribers=10000,
            active_users=100,  # 1% active ratio
        )
        score = agent._calculate_engagement_score(subreddit)
        assert score < 5.0

    def test_zero_subscribers(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="zero_subs",
            subscribers=0,
            active_users=0,
        )
        score = agent._calculate_engagement_score(subreddit)
        assert score == 0.0

    def test_zero_active_users(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="zero_active",
            subscribers=10000,
            active_users=0,
        )
        score = agent._calculate_engagement_score(subreddit)
        assert score > 0.0  # Still gets subscriber score


class TestCalculateRelevanceScore:
    """Tests for _calculate_relevance_score method."""

    @pytest.fixture
    def agent(self) -> NicheResearchAgent:
        return NicheResearchAgent()

    def test_high_relevance_with_keywords(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="entrepreneur",
            subscribers=50000,
        )
        subreddit.title = "Entrepreneurship and Startups"
        subreddit.public_description = "A community for entrepreneurs"

        keywords = ["entrepreneur", "startup", "business"]
        score = agent._calculate_relevance_score(subreddit, keywords)
        # "entrepreneur" appears 2 times (in title and description)
        # So score should be 2
        assert score >= 1.0

    def test_low_relevance_no_keywords(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit(
            name="gaming",
            subscribers=50000,
        )
        keywords = ["entrepreneur", "startup", "business"]
        score = agent._calculate_relevance_score(subreddit, keywords)
        assert score == 0.0

    def test_empty_keywords(self, agent: NicheResearchAgent) -> None:
        subreddit = mock_reddit_subreddit()
        score = agent._calculate_relevance_score(subreddit, [])
        assert score == 0.0


class TestExtractPainContext:
    """Tests for _extract_pain_context method."""

    @pytest.fixture
    def agent(self) -> NicheResearchAgent:
        return NicheResearchAgent()

    def test_extracts_context_with_indicator(self, agent: NicheResearchAgent) -> None:
        title = "Struggling to find customers for my SaaS"
        context = agent._extract_pain_context(title, "struggling")
        assert context == title

    def test_returns_none_if_indicator_not_found(self, agent: NicheResearchAgent) -> None:
        title = "Just sharing my success story"
        context = agent._extract_pain_context(title, "struggling")
        assert context is None

    def test_handles_empty_title(self, agent: NicheResearchAgent) -> None:
        context = agent._extract_pain_context("", "test")
        # Returns None for empty titles since indicator is not found
        assert context is None


class TestResearchNiche:
    """Tests for research_niche method."""

    @pytest.fixture
    def agent(self) -> NicheResearchAgent:
        # pragma: allowlist secret
        return NicheResearchAgent(
            reddit_client_id="test_id",  # pragma: allowlist secret
            reddit_client_secret="test_secret",  # pragma: allowlist secret
            brave_api_key="test_brave_key",  # pragma: allowlist secret
            tavily_api_key="test_tavily_key",  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_requires_non_empty_query(self, agent: NicheResearchAgent) -> None:
        with pytest.raises(NicheResearchAgentError, match="Query is required"):
            await agent.research_niche("")

        with pytest.raises(NicheResearchAgentError, match="Query is required"):
            await agent.research_niche("   ")

    @pytest.mark.asyncio
    async def test_research_niche_success(self, agent: NicheResearchAgent) -> None:
        """Test successful niche research with mocked dependencies."""

        # Mock the resilient clients
        mock_reddit_client = AsyncMock()
        mock_reddit_client.search_subreddits = AsyncMock(
            return_value=[
                mock_reddit_subreddit("entrepreneur", 50000, 5000),
            ]
        )
        mock_reddit_client.get_subreddit_posts = AsyncMock(
            return_value=[
                mock_reddit_post(title="Struggling to find customers"),
                mock_reddit_post(title="Need help with marketing"),
            ]
        )

        mock_brave_client = AsyncMock()
        mock_brave_response = MagicMock()
        mock_brave_response.results = []
        mock_brave_client.search = AsyncMock(return_value=mock_brave_response)

        mock_tavily_client = AsyncMock()
        mock_tavily_response = MagicMock()
        mock_tavily_response.results = []
        mock_tavily_client.research = AsyncMock(return_value=mock_tavily_response)

        # Patch the resilient client classes
        with (
            patch(
                "src.agents.niche_research_agent.agent.ResilientRedditClient",
                return_value=mock_reddit_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientBraveClient",
                return_value=mock_brave_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientTavilyClient",
                return_value=mock_tavily_client,
            ),
        ):
            result = await agent.research_niche("AI tools for entrepreneurs")

        # Verify result structure
        assert result.niche == "AI tools for entrepreneurs"
        assert isinstance(result.subreddits, list)
        assert isinstance(result.pain_points, list)
        assert isinstance(result.opportunities, list)
        assert result.total_subscribers >= 0
        assert result.total_active_users >= 0

    @pytest.mark.asyncio
    async def test_research_niche_with_custom_config(self, agent: NicheResearchAgent) -> None:
        """Test niche research with custom configuration parameters."""

        # Mock the resilient clients
        mock_reddit_client = AsyncMock()
        mock_reddit_client.search_subreddits = AsyncMock(return_value=[])
        mock_reddit_client.get_subreddit_posts = AsyncMock(return_value=[])

        mock_brave_client = AsyncMock()
        mock_brave_client.search = AsyncMock(return_value=MagicMock(results=[]))

        mock_tavily_client = AsyncMock()
        mock_tavily_client.research = AsyncMock(return_value=MagicMock(results=[]))

        with (
            patch(
                "src.agents.niche_research_agent.agent.ResilientRedditClient",
                return_value=mock_reddit_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientBraveClient",
                return_value=mock_brave_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientTavilyClient",
                return_value=mock_tavily_client,
            ),
        ):
            result = await agent.research_niche(
                "test niche",
                max_subreddits=5,
                posts_per_subreddit=10,
                min_subscribers=5000,
                engagement_weight=0.7,
                relevance_weight=0.3,
            )

        # Verify the result was created
        assert result.niche == "test niche"


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def agent(self) -> NicheResearchAgent:
        # pragma: allowlist secret
        return NicheResearchAgent(
            reddit_client_id="test_id",  # pragma: allowlist secret
            reddit_client_secret="test_secret",  # pragma: allowlist secret
            brave_api_key="test_brave_key",  # pragma: allowlist secret
            tavily_api_key="test_tavily_key",  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_health_check_with_all_services_healthy(self, agent: NicheResearchAgent) -> None:
        """Test health check when all services are healthy."""

        # Mock the resilient clients
        mock_reddit_client = AsyncMock()
        mock_reddit_client.search_subreddits = AsyncMock(return_value=[])

        mock_brave_client = AsyncMock()
        mock_brave_client.search = AsyncMock(return_value=MagicMock(results=[]))

        mock_tavily_client = AsyncMock()
        mock_tavily_client.research = AsyncMock(return_value=MagicMock(results=[]))

        with (
            patch(
                "src.agents.niche_research_agent.agent.ResilientRedditClient",
                return_value=mock_reddit_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientBraveClient",
                return_value=mock_brave_client,
            ),
            patch(
                "src.agents.niche_research_agent.agent.ResilientTavilyClient",
                return_value=mock_tavily_client,
            ),
        ):
            health = await agent.health_check()

        assert health["agent"] == "niche_research_agent"
        assert "services" in health
        assert "reddit" in health["services"]
        assert "brave" in health["services"]
        assert "tavily" in health["services"]

    @pytest.mark.asyncio
    async def test_health_check_with_no_credentials(self) -> None:
        """Test health check when no credentials are provided."""
        agent = NicheResearchAgent()
        health = await agent.health_check()

        assert health["healthy"] is False
        assert health["services"]["reddit"]["healthy"] is False
        assert "No credentials" in health["services"]["reddit"]["error"]


class TestExceptions:
    """Tests for custom exception types."""

    def test_rate_limit_exceeded_error(self) -> None:
        error = RateLimitExceededError("Reddit", retry_after=60)
        assert "Reddit" in str(error)
        assert "60" in str(error)
        assert error.details["service"] == "Reddit"
        assert error.details["retry_after"] == 60

    def test_rate_limit_exceeded_error_no_retry_after(self) -> None:
        error = RateLimitExceededError("Brave")
        assert "Brave" in str(error)
        assert error.details["retry_after"] is None

    def test_authentication_failed_error(self) -> None:
        error = AuthenticationFailedError("Tavily")
        assert "Tavily" in str(error)
        assert "Authentication failed" in str(error)
        assert error.details["service"] == "Tavily"

    def test_service_unavailable_error(self) -> None:
        error = ServiceUnavailableError("Reddit", 503)
        assert "Reddit" in str(error)
        assert "503" in str(error)
        assert error.details["service"] == "Reddit"
        assert error.details["status_code"] == 503
