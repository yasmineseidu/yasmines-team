"""Live API tests for Perplexity AI integration.

These tests use real API keys and make actual API calls.
Run with: uv run pytest __tests__/integration/test_perplexity_live.py -v -m live_api
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.perplexity import (
    PerplexityCitation,
    PerplexityClient,
    PerplexityConversation,
    PerplexityError,
    PerplexityModel,
    PerplexityResponse,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        pytest.skip("PERPLEXITY_API_KEY not found in environment")
    return key


@pytest.fixture
def client(api_key: str) -> PerplexityClient:
    """Create PerplexityClient with real API key."""
    return PerplexityClient(api_key=api_key)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveResearch:
    """Live API tests for research functionality."""

    async def test_research_returns_response(self, client: PerplexityClient) -> None:
        """research() should return a valid response with content."""
        result = await client.research(
            "What is Python programming language?",
            max_tokens=100,
        )

        assert isinstance(result, PerplexityResponse)
        assert result.id is not None
        assert result.model == "sonar"
        assert result.content != ""
        assert "Python" in result.content or "python" in result.content.lower()

    async def test_research_returns_citations(self, client: PerplexityClient) -> None:
        """research() should return citations when web search is performed."""
        result = await client.research(
            "What are the latest AI trends in 2024?",
            max_tokens=200,
        )

        assert isinstance(result, PerplexityResponse)
        assert result.content != ""
        # Citations should be present for web search queries
        assert len(result.citations) > 0
        for citation in result.citations:
            assert isinstance(citation, PerplexityCitation)
            assert citation.url.startswith("http")

    async def test_research_with_sonar_pro(self, client: PerplexityClient) -> None:
        """research() should work with sonar-pro model."""
        result = await client.research(
            "Explain quantum computing in simple terms",
            model=PerplexityModel.SONAR_PRO,
            max_tokens=150,
        )

        assert isinstance(result, PerplexityResponse)
        assert result.model == "sonar-pro"
        assert result.content != ""

    async def test_research_tracks_usage(self, client: PerplexityClient) -> None:
        """research() should track token usage."""
        result = await client.research(
            "What is machine learning?",
            max_tokens=50,
        )

        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveChat:
    """Live API tests for chat functionality."""

    async def test_chat_returns_response(self, client: PerplexityClient) -> None:
        """chat() should return a valid response."""
        result = await client.chat("Hello, how are you?")

        assert isinstance(result, PerplexityResponse)
        assert result.content != ""

    async def test_chat_with_conversation_context(self, client: PerplexityClient) -> None:
        """chat() should maintain conversation context."""
        conv = PerplexityConversation(system_prompt="You are a helpful assistant. Be concise.")

        # First message
        result1 = await client.chat(
            "My name is Alice. Remember my name.",
            conversation=conv,
            max_tokens=50,
        )
        assert result1.content != ""

        # Follow-up that references first message
        result2 = await client.chat(
            "What is my name?",
            conversation=conv,
            max_tokens=50,
        )
        assert "Alice" in result2.content

    async def test_chat_with_search_disabled(self, client: PerplexityClient) -> None:
        """chat() should work with search disabled."""
        result = await client.chat(
            "What is 2 + 2?",
            search_disabled=True,
            max_tokens=30,
        )

        assert isinstance(result, PerplexityResponse)
        assert "4" in result.content


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveSpecializedSearch:
    """Live API tests for specialized search modes."""

    async def test_research_with_system_prompt(self, client: PerplexityClient) -> None:
        """research_with_system_prompt() should include custom instructions."""
        result = await client.research_with_system_prompt(
            "What are the best practices for API design?",
            "You are a software architect. Answer in bullet points.",
            max_tokens=150,
        )

        assert isinstance(result, PerplexityResponse)
        assert result.content != ""
        # Response should be formatted as requested
        assert "-" in result.content or "•" in result.content or "*" in result.content

    async def test_academic_search(self, client: PerplexityClient) -> None:
        """academic_search() should return academic sources."""
        result = await client.academic_search(
            "machine learning in healthcare research",
            max_tokens=150,
        )

        assert isinstance(result, PerplexityResponse)
        assert result.content != ""


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveHealthCheck:
    """Live API tests for health check."""

    async def test_health_check_passes(self, client: PerplexityClient) -> None:
        """health_check() should return healthy status."""
        result = await client.health_check()

        assert result["name"] == "perplexity"
        assert result["healthy"] is True
        assert result["base_url"] == "https://api.perplexity.ai"
        assert result["default_model"] == "sonar"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveErrorHandling:
    """Live API tests for error handling."""

    async def test_invalid_api_key_raises_error(self) -> None:
        """Should raise PerplexityError for invalid API key."""
        client = PerplexityClient(api_key="pplx-invalid-key-12345")  # pragma: allowlist secret

        with pytest.raises(PerplexityError):
            await client.research("test query")


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveCallEndpoint:
    """Live API tests for direct endpoint calls."""

    async def test_call_endpoint_directly(self, client: PerplexityClient) -> None:
        """call_endpoint() should allow direct API calls."""
        result = await client.call_endpoint(
            "/chat/completions",
            method="POST",
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 10,
            },
        )

        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]


@pytest.mark.asyncio
@pytest.mark.live_api
class TestPerplexityLiveContextManager:
    """Live API tests for context manager usage."""

    async def test_context_manager_usage(self, api_key: str) -> None:
        """Client should work as context manager."""
        async with PerplexityClient(api_key=api_key) as client:
            result = await client.research("What is AI?", max_tokens=50)
            assert result.content != ""
