"""Unit tests for Lead Research Agent SDK MCP tools.

Tests SDK MCP tools for lead research:
- search_linkedin_posts
- search_linkedin_profile
- search_articles_authored
- search_podcast_appearances
- analyze_headline

Note: The @tool decorator wraps functions in SdkMcpTool objects.
To test them directly, we access the .handler attribute which is the async function.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.lead_research.tools import (
    LEAD_RESEARCH_TOOLS,
    analyze_headline_tool,
    search_articles_authored_tool,
    search_linkedin_posts_tool,
    search_linkedin_profile_tool,
    search_podcast_appearances_tool,
)

# Access the handler functions from SdkMcpTool objects
# The @tool decorator wraps the function in SdkMcpTool, so we need to access .handler
_search_linkedin_posts = search_linkedin_posts_tool.handler
_search_linkedin_profile = search_linkedin_profile_tool.handler
_search_articles_authored = search_articles_authored_tool.handler
_search_podcast_appearances = search_podcast_appearances_tool.handler
_analyze_headline = analyze_headline_tool.handler


class TestSearchLinkedInPostsTool:
    """Tests for search_linkedin_posts_tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_name_missing(self) -> None:
        """Test that tool returns error when first_name/last_name missing."""
        result = await _search_linkedin_posts({"first_name": "", "last_name": "", "max_results": 5})

        assert result["is_error"] is True
        assert "required" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_api_key_missing(self) -> None:
        """Test that tool returns error when TAVILY_API_KEY not set."""
        with patch.dict("os.environ", {"TAVILY_API_KEY": ""}, clear=False):
            result = await _search_linkedin_posts(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "CEO",
                    "company_name": "Acme Corp",
                    "max_results": 5,
                }
            )

        assert result["is_error"] is True
        assert "not configured" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_success_returns_posts_data(self) -> None:
        """Test successful search returns posts data."""
        # Mock Tavily result
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(
                content="Great post about AI",
                url="https://linkedin.com/posts/123",
                title="AI Thoughts",
                score=0.9,
            ),
            MagicMock(
                content="Non-LinkedIn result",
                url="https://example.com/article",
                title="Other Article",
                score=0.8,
            ),
        ]

        with (
            patch.dict(
                "os.environ",
                {"TAVILY_API_KEY": "test-key"},  # pragma: allowlist secret
                clear=False,
            ),
            patch("src.integrations.tavily.TavilyClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await _search_linkedin_posts(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "CEO",
                    "company_name": "Acme",
                    "max_results": 5,
                }
            )

        assert "is_error" not in result or result.get("is_error") is False
        assert "data" in result
        assert "posts" in result["data"]
        # Only LinkedIn posts should be included
        assert len(result["data"]["posts"]) == 1
        assert "linkedin" in result["data"]["posts"][0]["url"]


class TestSearchLinkedInProfileTool:
    """Tests for search_linkedin_profile_tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_name_missing(self) -> None:
        """Test error when name missing."""
        result = await _search_linkedin_profile({"first_name": "", "last_name": ""})

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_success_returns_profile_data(self) -> None:
        """Test successful profile search."""
        mock_result = MagicMock()
        mock_result.organic_results = [
            MagicMock(
                link="https://linkedin.com/in/johndoe",
                title="John Doe - CEO at Acme",
                snippet="Experienced leader in tech...",
            ),
        ]

        with (
            patch.dict(
                "os.environ",
                {"SERPER_API_KEY": "test-key"},  # pragma: allowlist secret
                clear=False,
            ),
            patch("src.integrations.serper.SerperClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await _search_linkedin_profile(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "CEO",
                    "company_name": "Acme",
                }
            )

        assert "is_error" not in result or result.get("is_error") is False
        assert "data" in result
        assert result["data"]["profile"]["url"] == "https://linkedin.com/in/johndoe"


class TestSearchArticlesAuthoredTool:
    """Tests for search_articles_authored_tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_name_missing(self) -> None:
        """Test error when name missing."""
        result = await _search_articles_authored(
            {"first_name": "", "last_name": "", "max_results": 3}
        )

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_filters_out_linkedin_results(self) -> None:
        """Test that LinkedIn results are filtered out."""
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(
                title="Article on TechCrunch",
                url="https://techcrunch.com/article/123",
                content="Great article about...",
                score=0.9,
            ),
            MagicMock(
                title="LinkedIn Post",
                url="https://linkedin.com/posts/123",
                content="LinkedIn content...",
                score=0.8,
            ),
        ]

        with (
            patch.dict(
                "os.environ",
                {"TAVILY_API_KEY": "test-key"},  # pragma: allowlist secret
                clear=False,
            ),
            patch("src.integrations.tavily.TavilyClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await _search_articles_authored(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "CEO",
                    "max_results": 3,
                }
            )

        assert "is_error" not in result or result.get("is_error") is False
        # LinkedIn result should be filtered out
        assert len(result["data"]["articles"]) == 1
        assert "techcrunch" in result["data"]["articles"][0]["url"]


class TestSearchPodcastAppearancesTool:
    """Tests for search_podcast_appearances_tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_name_missing(self) -> None:
        """Test error when name missing."""
        result = await _search_podcast_appearances(
            {"first_name": "", "last_name": "", "max_results": 3}
        )

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_filters_for_podcast_keywords(self) -> None:
        """Test that only podcast-related results are returned."""
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(
                title="John Doe on The Podcast Show - Episode 42",
                url="https://podcasts.example.com/episode/42",
                content="Interview with John...",
                score=0.9,
            ),
            MagicMock(
                title="Random Article",
                url="https://example.com/article",
                content="Not a podcast...",
                score=0.8,
            ),
        ]

        with (
            patch.dict(
                "os.environ",
                {"TAVILY_API_KEY": "test-key"},  # pragma: allowlist secret
                clear=False,
            ),
            patch("src.integrations.tavily.TavilyClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await _search_podcast_appearances(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "CEO",
                    "max_results": 3,
                }
            )

        assert "is_error" not in result or result.get("is_error") is False
        # Only podcast result should be included
        assert len(result["data"]["podcasts"]) == 1
        assert "podcast" in result["data"]["podcasts"][0]["title"].lower()


class TestAnalyzeHeadlineTool:
    """Tests for analyze_headline_tool."""

    @pytest.mark.asyncio
    async def test_extracts_role_keywords(self) -> None:
        """Test extraction of role-based keywords."""
        result = await _analyze_headline(
            {
                "first_name": "John",
                "last_name": "Doe",
                "title": "CEO",
                "headline": "Leading AI innovation at TechCorp",
                "company_name": "TechCorp",
            }
        )

        assert "is_error" not in result or result.get("is_error") is False
        assert "ceo" in result["data"]["keywords"]
        assert "ai" in result["data"]["keywords"]

    @pytest.mark.asyncio
    async def test_generates_hooks_from_role(self) -> None:
        """Test generation of hooks from role."""
        result = await _analyze_headline(
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "Founder",
                "headline": "Building the future of healthcare",
                "company_name": "HealthTech",
            }
        )

        assert "is_error" not in result or result.get("is_error") is False
        assert len(result["data"]["hooks"]) > 0
        # Should have a hook about building/founding
        hook_text = " ".join(result["data"]["hooks"])
        assert "building" in hook_text.lower() or "company" in hook_text.lower()

    @pytest.mark.asyncio
    async def test_zero_cost_for_headline_analysis(self) -> None:
        """Test that headline analysis has zero API cost."""
        result = await _analyze_headline(
            {
                "first_name": "John",
                "last_name": "Doe",
                "title": "Manager",
                "headline": "Sales Manager",
                "company_name": "Acme",
            }
        )

        assert result["data"]["cost"] == 0.0


class TestLeadResearchToolsList:
    """Tests for LEAD_RESEARCH_TOOLS list."""

    def test_tools_list_contents(self) -> None:
        """Test that LEAD_RESEARCH_TOOLS contains expected tools."""
        tool_functions = LEAD_RESEARCH_TOOLS

        assert len(tool_functions) == 5
        assert search_linkedin_posts_tool in tool_functions
        assert search_linkedin_profile_tool in tool_functions
        assert search_articles_authored_tool in tool_functions
        assert search_podcast_appearances_tool in tool_functions
        assert analyze_headline_tool in tool_functions

    def test_tools_have_callable_handlers(self) -> None:
        """Test that all tools have callable handlers."""
        for tool in LEAD_RESEARCH_TOOLS:
            # SdkMcpTool objects have a handler attribute that is callable
            assert hasattr(tool, "handler")
            assert callable(tool.handler)

    def test_tools_have_required_attributes(self) -> None:
        """Test that all tools have required SdkMcpTool attributes."""
        for tool in LEAD_RESEARCH_TOOLS:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "input_schema")
            assert hasattr(tool, "handler")
