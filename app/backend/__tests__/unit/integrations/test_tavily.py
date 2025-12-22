"""Unit tests for Tavily integration client."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.base import IntegrationError
from src.integrations.tavily import (
    TavilyAnswer,
    TavilyClient,
    TavilyError,
    TavilyImage,
    TavilySearchDepth,
    TavilySearchResponse,
    TavilySearchResult,
    TavilyTimeRange,
    TavilyTopic,
)


class TestTavilyClientInitialization:
    """Tests for TavilyClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have tavily name."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.name == "tavily"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.base_url == "https://api.tavily.com"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        api_key = "tvly-test-key-123"  # pragma: allowlist secret
        client = TavilyClient(api_key=api_key)
        assert client.api_key == api_key

    def test_has_default_timeout(self) -> None:
        """Client should have default timeout."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.timeout == 30.0

    def test_has_default_max_retries(self) -> None:
        """Client should have default max retries."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_has_default_caching_enabled(self) -> None:
        """Client should have caching enabled by default."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.enable_caching is True

    def test_has_default_cache_ttl(self) -> None:
        """Client should have default cache TTL of 24 hours."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret
        assert client.cache_ttl == 86400

    def test_can_customize_timeout(self) -> None:
        """Client should allow custom timeout."""
        client = TavilyClient(api_key="tvly-test", timeout=60.0)  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_can_disable_caching(self) -> None:
        """Client should allow disabling cache."""
        client = TavilyClient(
            api_key="tvly-test",  # pragma: allowlist secret
            enable_caching=False,
        )
        assert client.enable_caching is False

    def test_can_customize_cache_ttl(self) -> None:
        """Client should allow custom cache TTL."""
        client = TavilyClient(
            api_key="tvly-test",  # pragma: allowlist secret
            cache_ttl=3600,
        )
        assert client.cache_ttl == 3600


class TestTavilyClientSearch:
    """Tests for TavilyClient.search()."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient instance."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.fixture
    def mock_search_response(self) -> dict:
        """Mock search API response."""
        return {
            "query": "AI trends 2024",
            "results": [
                {
                    "title": "AI Trends for 2024",
                    "url": "https://example.com/ai-trends",
                    "content": "Top AI trends include...",
                    "score": 0.95,
                    "favicon": "https://example.com/favicon.ico",
                    "published_date": "2024-01-15",
                },
                {
                    "title": "Machine Learning Advances",
                    "url": "https://example.com/ml-advances",
                    "content": "Latest ML breakthroughs...",
                    "score": 0.88,
                },
            ],
            "answer": "AI trends for 2024 include...",
            "images": [
                "https://example.com/image1.jpg",
                {"url": "https://example.com/image2.jpg", "description": "AI visualization"},
            ],
            "response_time": 1.23,
            "request_id": "req-123",
            "search_parameters": {"search_depth": "basic"},
        }

    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, client: TavilyClient, mock_search_response: dict
    ) -> None:
        """search() should return parsed results."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_search_response

            result = await client.search("AI trends 2024")

            assert isinstance(result, TavilySearchResponse)
            assert result.query == "AI trends 2024"
            assert len(result.results) == 2
            assert result.results[0].title == "AI Trends for 2024"
            assert result.results[0].score == 0.95
            assert result.answer is not None
            assert result.answer.text == "AI trends for 2024 include..."
            assert len(result.images) == 2

    @pytest.mark.asyncio
    async def test_search_sends_correct_payload(self, client: TavilyClient) -> None:
        """search() should send correct request payload."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"results": [], "response_time": 0.5}

            await client.search(
                "test query",
                topic=TavilyTopic.NEWS,
                search_depth=TavilySearchDepth.ADVANCED,
                max_results=10,
                include_images=True,
            )

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs["json"]

            assert payload["query"] == "test query"
            assert payload["topic"] == "news"
            assert payload["search_depth"] == "advanced"
            assert payload["max_results"] == 10
            assert payload["include_images"] is True

    @pytest.mark.asyncio
    async def test_search_with_time_range(self, client: TavilyClient) -> None:
        """search() should handle time range filter."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"results": [], "response_time": 0.5}

            await client.search("test", time_range=TavilyTimeRange.WEEK)

            payload = mock_post.call_args.kwargs["json"]
            assert payload["time_range"] == "week"

    @pytest.mark.asyncio
    async def test_search_with_date_range(self, client: TavilyClient) -> None:
        """search() should handle date range filters."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"results": [], "response_time": 0.5}

            await client.search("test", start_date="2024-01-01", end_date="2024-12-31")

            payload = mock_post.call_args.kwargs["json"]
            assert payload["start_date"] == "2024-01-01"
            assert payload["end_date"] == "2024-12-31"

    @pytest.mark.asyncio
    async def test_search_with_domain_filters(self, client: TavilyClient) -> None:
        """search() should handle domain filters."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"results": [], "response_time": 0.5}

            await client.search(
                "test",
                include_domains=["example.com", "test.com"],
                exclude_domains=["spam.com"],
            )

            payload = mock_post.call_args.kwargs["json"]
            assert payload["include_domains"] == ["example.com", "test.com"]
            assert payload["exclude_domains"] == ["spam.com"]

    @pytest.mark.asyncio
    async def test_search_validates_query(self, client: TavilyClient) -> None:
        """search() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_search_validates_max_results(self, client: TavilyClient) -> None:
        """search() should raise ValueError for invalid max_results."""
        with pytest.raises(ValueError, match="max_results must be between 0 and 20"):
            await client.search("test", max_results=25)

    @pytest.mark.asyncio
    async def test_search_validates_include_domains_limit(self, client: TavilyClient) -> None:
        """search() should raise ValueError for too many include_domains."""
        domains = [f"domain{i}.com" for i in range(301)]
        with pytest.raises(ValueError, match="include_domains maximum is 300 domains"):
            await client.search("test", include_domains=domains)

    @pytest.mark.asyncio
    async def test_search_validates_exclude_domains_limit(self, client: TavilyClient) -> None:
        """search() should raise ValueError for too many exclude_domains."""
        domains = [f"domain{i}.com" for i in range(151)]
        with pytest.raises(ValueError, match="exclude_domains maximum is 150 domains"):
            await client.search("test", exclude_domains=domains)

    @pytest.mark.asyncio
    async def test_search_raises_tavily_error_on_failure(self, client: TavilyClient) -> None:
        """search() should raise TavilyError on API failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(TavilyError, match="Search failed"):
                await client.search("test")


class TestTavilyClientCaching:
    """Tests for TavilyClient caching functionality."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient with caching enabled."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.fixture
    def mock_response(self) -> dict:
        """Mock API response."""
        return {
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Content",
                    "score": 0.9,
                }
            ],
            "response_time": 0.5,
        }

    @pytest.mark.asyncio
    async def test_caches_search_results(self, client: TavilyClient, mock_response: dict) -> None:
        """search() should cache results."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # First call should hit API
            result1 = await client.search("test query")
            assert mock_post.call_count == 1

            # Second call should use cache
            result2 = await client.search("test query")
            assert mock_post.call_count == 1  # Still only 1 call

            assert result1.query == result2.query
            assert len(result1.results) == len(result2.results)

    @pytest.mark.asyncio
    async def test_different_queries_not_cached_together(
        self, client: TavilyClient, mock_response: dict
    ) -> None:
        """search() should cache different queries separately."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.search("query 1")
            await client.search("query 2")

            assert mock_post.call_count == 2  # Two different queries

    @pytest.mark.asyncio
    async def test_cache_respects_ttl(self, client: TavilyClient, mock_response: dict) -> None:
        """search() should expire cache after TTL."""
        # Set short TTL for testing
        client.cache_ttl = 1  # 1 second

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # First call
            await client.search("test")
            assert mock_post.call_count == 1

            # Second call immediately - should use cache
            await client.search("test")
            assert mock_post.call_count == 1

            # Manually expire cache entry
            cache_key = list(client._cache.keys())[0]
            result, _ = client._cache[cache_key]
            client._cache[cache_key] = (result, datetime.now() - timedelta(seconds=2))

            # Third call after expiry - should hit API
            await client.search("test")
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_disabled_always_hits_api(self, mock_response: dict) -> None:
        """search() should not cache when caching disabled."""
        client = TavilyClient(
            api_key="tvly-test",  # pragma: allowlist secret
            enable_caching=False,
        )

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.search("test")
            await client.search("test")

            assert mock_post.call_count == 2  # Both calls hit API

    def test_clear_cache_returns_count(self, client: TavilyClient) -> None:
        """clear_cache() should return number of cleared entries."""
        # Manually add some cache entries
        client._cache["key1"] = (TavilySearchResponse(query="test1"), datetime.now())
        client._cache["key2"] = (TavilySearchResponse(query="test2"), datetime.now())

        count = client.clear_cache()
        assert count == 2
        assert len(client._cache) == 0


class TestTavilyClientExtract:
    """Tests for TavilyClient.extract()."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient instance."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_extract_sends_urls(self, client: TavilyClient) -> None:
        """extract() should send URLs to API."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"results": {}}

            urls = ["https://example.com/page1", "https://example.com/page2"]
            await client.extract(urls)

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs["json"]
            assert payload["urls"] == urls

    @pytest.mark.asyncio
    async def test_extract_validates_empty_urls(self, client: TavilyClient) -> None:
        """extract() should raise ValueError for empty URLs list."""
        with pytest.raises(ValueError, match="urls list cannot be empty"):
            await client.extract([])

    @pytest.mark.asyncio
    async def test_extract_validates_max_urls(self, client: TavilyClient) -> None:
        """extract() should raise ValueError for too many URLs."""
        urls = [f"https://example.com/page{i}" for i in range(21)]
        with pytest.raises(ValueError, match="Maximum 20 URLs per request"):
            await client.extract(urls)


class TestTavilyClientResearch:
    """Tests for TavilyClient.research()."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient instance."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_research_uses_advanced_depth(self, client: TavilyClient) -> None:
        """research() should use advanced search depth."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = TavilySearchResponse(query="test")

            await client.research("AI trends")

            # Should be called 5 times (default max_iterations)
            assert mock_search.call_count == 5
            call_kwargs = mock_search.call_args.kwargs
            assert call_kwargs["search_depth"] == TavilySearchDepth.ADVANCED

    @pytest.mark.asyncio
    async def test_research_uses_max_iterations(self, client: TavilyClient) -> None:
        """research() should call search() max_iterations times."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = TavilySearchResponse(
                query="test",
                results=[
                    TavilySearchResult(
                        title="Test Result",
                        url=f"https://example.com/{i}",
                        content="Test content",
                        score=0.9,
                    )
                    for i in range(3)
                ],
            )

            await client.research("AI trends", max_iterations=3)

            # Should be called exactly max_iterations times
            assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_research_aggregates_results(self, client: TavilyClient) -> None:
        """research() should aggregate unique results from all iterations."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            # Return different results for each iteration
            def mock_search_side_effect(*args, **kwargs):
                iteration = mock_search.call_count
                return TavilySearchResponse(
                    query="test",
                    results=[
                        TavilySearchResult(
                            title=f"Result {iteration}-{i}",
                            url=f"https://example.com/{iteration}-{i}",
                            content=f"Content {iteration}-{i}",
                            score=0.9 - (i * 0.1),
                        )
                        for i in range(2)
                    ],
                )

            mock_search.side_effect = mock_search_side_effect

            result = await client.research("AI trends", max_iterations=3)

            # Should aggregate all unique results (3 iterations * 2 results = 6)
            assert len(result.results) == 6
            assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_research_deduplicates_by_url(self, client: TavilyClient) -> None:
        """research() should deduplicate results by URL."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            # Return same URL in multiple iterations
            mock_search.return_value = TavilySearchResponse(
                query="test",
                results=[
                    TavilySearchResult(
                        title="Duplicate Result",
                        url="https://example.com/same",
                        content="Same content",
                        score=0.9,
                    )
                ],
            )

            result = await client.research("AI trends", max_iterations=3)

            # Should only have one unique result despite 3 iterations
            assert len(result.results) == 1
            assert result.results[0].url == "https://example.com/same"
            assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_research_validates_max_iterations(self, client: TavilyClient) -> None:
        """research() should validate max_iterations range."""
        with pytest.raises(ValueError, match="max_iterations must be between 1 and 10"):
            await client.research("test", max_iterations=15)

        with pytest.raises(ValueError, match="max_iterations must be between 1 and 10"):
            await client.research("test", max_iterations=0)


class TestTavilyClientHealthCheck:
    """Tests for TavilyClient.health_check()."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient instance."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: TavilyClient) -> None:
        """health_check() should return healthy status on success."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = TavilySearchResponse(query="test")

            result = await client.health_check()

            assert result["name"] == "tavily"
            assert result["healthy"] is True
            assert result["base_url"] == "https://api.tavily.com"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: TavilyClient) -> None:
        """health_check() should return unhealthy status on failure."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = TavilyError("Connection failed")

            result = await client.health_check()

            assert result["name"] == "tavily"
            assert result["healthy"] is False
            assert "error" in result


class TestTavilyClientCallEndpoint:
    """Tests for TavilyClient.call_endpoint()."""

    @pytest.fixture
    def client(self) -> TavilyClient:
        """Create TavilyClient instance."""
        return TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: TavilyClient) -> None:
        """call_endpoint() should call endpoint directly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"result": "success"}

            result = await client.call_endpoint("/custom", method="GET")

            assert result == {"result": "success"}
            mock_request.assert_called_once_with(method="GET", endpoint="/custom")

    @pytest.mark.asyncio
    async def test_call_endpoint_raises_tavily_error(self, client: TavilyClient) -> None:
        """call_endpoint() should raise TavilyError on failure."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(TavilyError, match="API call failed"):
                await client.call_endpoint("/custom")


class TestTavilyClientContextManager:
    """Tests for TavilyClient context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_clears_cache_on_exit(self) -> None:
        """Context manager should clear cache on exit."""
        client = TavilyClient(api_key="tvly-test")  # pragma: allowlist secret

        # Add cache entry
        client._cache["test"] = (TavilySearchResponse(query="test"), datetime.now())

        async with client:
            assert len(client._cache) == 1

        # Cache should be cleared after exit
        assert len(client._cache) == 0


class TestTavilyDataClasses:
    """Tests for Tavily dataclasses."""

    def test_tavily_search_result_creation(self) -> None:
        """TavilySearchResult should be created correctly."""
        result = TavilySearchResult(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            score=0.95,
            favicon="https://example.com/favicon.ico",
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.content == "Test content"
        assert result.score == 0.95
        assert result.favicon == "https://example.com/favicon.ico"

    def test_tavily_answer_creation(self) -> None:
        """TavilyAnswer should be created correctly."""
        answer = TavilyAnswer(text="Answer text", answer_type="advanced")

        assert answer.text == "Answer text"
        assert answer.answer_type == "advanced"

    def test_tavily_image_creation(self) -> None:
        """TavilyImage should be created correctly."""
        image = TavilyImage(url="https://example.com/image.jpg", description="Test image")

        assert image.url == "https://example.com/image.jpg"
        assert image.description == "Test image"

    def test_tavily_search_response_defaults(self) -> None:
        """TavilySearchResponse should have correct defaults."""
        response = TavilySearchResponse(query="test")

        assert response.query == "test"
        assert response.results == []
        assert response.answer is None
        assert response.images == []
        assert response.response_time == 0.0
        assert response.credits_used == 1
        assert response.request_id is None
