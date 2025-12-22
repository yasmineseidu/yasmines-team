"""Unit tests for Brave Search API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.brave_fixtures import (
    MOCK_EMPTY_RESPONSE,
    MOCK_IMAGES_SEARCH_RESPONSE,
    MOCK_NEWS_SEARCH_RESPONSE,
    MOCK_SUGGEST_RESPONSE,
    MOCK_VIDEOS_SEARCH_RESPONSE,
    MOCK_WEB_SEARCH_RESPONSE,
    MOCK_WEB_SEARCH_SIMPLE,
    create_web_search_response,
)
from src.integrations.brave import (
    BraveClient,
    BraveError,
    BraveFaq,
    BraveFreshness,
    BraveImageResult,
    BraveInfobox,
    BraveNewsResult,
    BraveSafesearch,
    BraveSearchResponse,
    BraveSearchType,
    BraveSuggestResponse,
    BraveVideoResult,
    BraveWebResult,
)


class TestBraveClientInitialization:
    """Tests for BraveClient initialization."""

    def test_client_has_correct_name(self) -> None:
        """Client should have name 'brave'."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "brave"

    def test_client_has_correct_base_url(self) -> None:
        """Client should use Brave Search API base URL."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.search.brave.com/res/v1"

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = BraveClient(api_key="test-api-key")  # pragma: allowlist secret
        assert client.api_key == "test-api-key"  # pragma: allowlist secret

    def test_client_has_default_timeout(self) -> None:
        """Client should have default 30s timeout."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 30.0

    def test_client_accepts_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = BraveClient(api_key="test-key", timeout=60.0)  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_has_default_max_retries(self) -> None:
        """Client should have default 3 max retries."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_accepts_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = BraveClient(api_key="test-key", max_retries=5)  # pragma: allowlist secret
        assert client.max_retries == 5

    def test_client_caching_enabled_by_default(self) -> None:
        """Client should have caching enabled by default."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.enable_caching is True

    def test_client_caching_can_be_disabled(self) -> None:
        """Client should allow disabling cache."""
        client = BraveClient(api_key="test-key", enable_caching=False)  # pragma: allowlist secret
        assert client.enable_caching is False

    def test_client_default_cache_ttl(self) -> None:
        """Client should have 24 hour default cache TTL."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        assert client.cache_ttl == 86400

    def test_client_accepts_custom_cache_ttl(self) -> None:
        """Client should accept custom cache TTL."""
        client = BraveClient(api_key="test-key", cache_ttl=3600)  # pragma: allowlist secret
        assert client.cache_ttl == 3600


class TestBraveClientHeaders:
    """Tests for BraveClient header generation."""

    def test_headers_include_subscription_token(self) -> None:
        """Headers should include X-Subscription-Token."""
        client = BraveClient(api_key="my-api-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["X-Subscription-Token"] == "my-api-key"

    def test_headers_include_accept_json(self) -> None:
        """Headers should include Accept: application/json."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"

    def test_headers_include_accept_encoding(self) -> None:
        """Headers should include Accept-Encoding: gzip."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept-Encoding"] == "gzip"


class TestBraveClientWebSearch:
    """Tests for BraveClient.search() web search."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_search_returns_response(self, client: BraveClient) -> None:
        """search() should return BraveSearchResponse."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE
            result = await client.search("test query")

            assert isinstance(result, BraveSearchResponse)
            assert result.query == "test query"
            assert result.search_type == BraveSearchType.WEB

    @pytest.mark.asyncio
    async def test_search_parses_web_results(self, client: BraveClient) -> None:
        """search() should parse web results correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE
            result = await client.search("simple search")

            assert len(result.results) == 3
            assert all(isinstance(r, BraveWebResult) for r in result.results)
            assert result.results[0].title == "Result 1 for simple search"
            assert "example1.com" in result.results[0].url

    @pytest.mark.asyncio
    async def test_search_parses_infobox(self, client: BraveClient) -> None:
        """search() should parse infobox correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_RESPONSE
            result = await client.search("AI companies")

            assert result.infobox is not None
            assert isinstance(result.infobox, BraveInfobox)
            assert "AI companies" in result.infobox.title

    @pytest.mark.asyncio
    async def test_search_parses_faqs(self, client: BraveClient) -> None:
        """search() should parse FAQs correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_RESPONSE
            result = await client.search("AI companies")

            assert len(result.faqs) > 0
            assert all(isinstance(f, BraveFaq) for f in result.faqs)

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self, client: BraveClient) -> None:
        """search() should handle empty results gracefully."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_EMPTY_RESPONSE
            result = await client.search("no results query")

            assert len(result.results) == 0
            assert result.infobox is None

    @pytest.mark.asyncio
    async def test_search_validates_empty_query(self, client: BraveClient) -> None:
        """search() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_search_validates_whitespace_query(self, client: BraveClient) -> None:
        """search() should raise ValueError for whitespace-only query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("   ")

    @pytest.mark.asyncio
    async def test_search_validates_count_too_low(self, client: BraveClient) -> None:
        """search() should raise ValueError for count < 1."""
        with pytest.raises(ValueError, match="count must be between 1 and 20"):
            await client.search("test", count=0)

    @pytest.mark.asyncio
    async def test_search_validates_count_too_high(self, client: BraveClient) -> None:
        """search() should raise ValueError for count > 20."""
        with pytest.raises(ValueError, match="count must be between 1 and 20"):
            await client.search("test", count=25)

    @pytest.mark.asyncio
    async def test_search_validates_offset_negative(self, client: BraveClient) -> None:
        """search() should raise ValueError for negative offset."""
        with pytest.raises(ValueError, match="offset must be between 0 and 9"):
            await client.search("test", offset=-1)

    @pytest.mark.asyncio
    async def test_search_validates_offset_too_high(self, client: BraveClient) -> None:
        """search() should raise ValueError for offset > 9."""
        with pytest.raises(ValueError, match="offset must be between 0 and 9"):
            await client.search("test", offset=10)

    @pytest.mark.asyncio
    async def test_search_passes_correct_params(self, client: BraveClient) -> None:
        """search() should pass correct query parameters."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE
            await client.search(
                "test query",
                count=5,
                offset=2,
                country="gb",
                language="de",
                safesearch=BraveSafesearch.STRICT,
                freshness=BraveFreshness.WEEK,
            )

            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            params = call_kwargs["params"]

            assert params["q"] == "test query"
            assert params["count"] == 5
            assert params["offset"] == 2
            assert params["country"] == "gb"
            assert params["search_lang"] == "de"
            assert params["safesearch"] == "strict"
            assert params["freshness"] == "pw"

    @pytest.mark.asyncio
    async def test_search_raises_brave_error_on_failure(self, client: BraveClient) -> None:
        """search() should raise BraveError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            from src.integrations.base import IntegrationError

            mock_get.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(BraveError) as exc_info:
                await client.search("test")

            assert "Web search failed" in str(exc_info.value)


class TestBraveClientNewsSearch:
    """Tests for BraveClient.search_news() news search."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_news_search_returns_response(self, client: BraveClient) -> None:
        """search_news() should return BraveSearchResponse."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_NEWS_SEARCH_RESPONSE
            result = await client.search_news("tech news")

            assert isinstance(result, BraveSearchResponse)
            assert result.search_type == BraveSearchType.NEWS

    @pytest.mark.asyncio
    async def test_news_search_parses_results(self, client: BraveClient) -> None:
        """search_news() should parse news results correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_NEWS_SEARCH_RESPONSE
            result = await client.search_news("tech news")

            assert len(result.news_results) == 5
            assert all(isinstance(r, BraveNewsResult) for r in result.news_results)

    @pytest.mark.asyncio
    async def test_news_search_validates_query(self, client: BraveClient) -> None:
        """search_news() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search_news("")

    @pytest.mark.asyncio
    async def test_news_search_validates_count(self, client: BraveClient) -> None:
        """search_news() should raise ValueError for invalid count."""
        with pytest.raises(ValueError, match="count must be between 1 and 20"):
            await client.search_news("test", count=0)

    @pytest.mark.asyncio
    async def test_news_search_calls_correct_endpoint(self, client: BraveClient) -> None:
        """search_news() should call /news/search endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_NEWS_SEARCH_RESPONSE
            await client.search_news("test")

            mock_get.assert_called_once()
            assert mock_get.call_args[0][0] == "/news/search"


class TestBraveClientImagesSearch:
    """Tests for BraveClient.search_images() image search."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_images_search_returns_response(self, client: BraveClient) -> None:
        """search_images() should return BraveSearchResponse."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_IMAGES_SEARCH_RESPONSE
            result = await client.search_images("nature photos")

            assert isinstance(result, BraveSearchResponse)
            assert result.search_type == BraveSearchType.IMAGES

    @pytest.mark.asyncio
    async def test_images_search_parses_results(self, client: BraveClient) -> None:
        """search_images() should parse image results correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_IMAGES_SEARCH_RESPONSE
            result = await client.search_images("nature photos")

            assert len(result.image_results) == 5
            assert all(isinstance(r, BraveImageResult) for r in result.image_results)

    @pytest.mark.asyncio
    async def test_images_search_validates_query(self, client: BraveClient) -> None:
        """search_images() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search_images("")

    @pytest.mark.asyncio
    async def test_images_search_validates_count(self, client: BraveClient) -> None:
        """search_images() should raise ValueError for count > 150."""
        with pytest.raises(ValueError, match="count must be between 1 and 150"):
            await client.search_images("test", count=200)

    @pytest.mark.asyncio
    async def test_images_search_calls_correct_endpoint(self, client: BraveClient) -> None:
        """search_images() should call /images/search endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_IMAGES_SEARCH_RESPONSE
            await client.search_images("test")

            mock_get.assert_called_once()
            assert mock_get.call_args[0][0] == "/images/search"


class TestBraveClientVideosSearch:
    """Tests for BraveClient.search_videos() video search."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_videos_search_returns_response(self, client: BraveClient) -> None:
        """search_videos() should return BraveSearchResponse."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_VIDEOS_SEARCH_RESPONSE
            result = await client.search_videos("tutorials")

            assert isinstance(result, BraveSearchResponse)
            assert result.search_type == BraveSearchType.VIDEOS

    @pytest.mark.asyncio
    async def test_videos_search_parses_results(self, client: BraveClient) -> None:
        """search_videos() should parse video results correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_VIDEOS_SEARCH_RESPONSE
            result = await client.search_videos("tutorials")

            assert len(result.video_results) == 5
            assert all(isinstance(r, BraveVideoResult) for r in result.video_results)

    @pytest.mark.asyncio
    async def test_videos_search_validates_query(self, client: BraveClient) -> None:
        """search_videos() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search_videos("")

    @pytest.mark.asyncio
    async def test_videos_search_validates_count(self, client: BraveClient) -> None:
        """search_videos() should raise ValueError for count > 50."""
        with pytest.raises(ValueError, match="count must be between 1 and 50"):
            await client.search_videos("test", count=60)

    @pytest.mark.asyncio
    async def test_videos_search_calls_correct_endpoint(self, client: BraveClient) -> None:
        """search_videos() should call /videos/search endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_VIDEOS_SEARCH_RESPONSE
            await client.search_videos("test")

            mock_get.assert_called_once()
            assert mock_get.call_args[0][0] == "/videos/search"


class TestBraveClientSuggest:
    """Tests for BraveClient.suggest() autocomplete."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_suggest_returns_response(self, client: BraveClient) -> None:
        """suggest() should return BraveSuggestResponse."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_SUGGEST_RESPONSE
            result = await client.suggest("python")

            assert isinstance(result, BraveSuggestResponse)
            assert result.query == "python"

    @pytest.mark.asyncio
    async def test_suggest_parses_suggestions(self, client: BraveClient) -> None:
        """suggest() should parse suggestions correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_SUGGEST_RESPONSE
            result = await client.suggest("python")

            assert len(result.suggestions) == 5
            assert all(isinstance(s, str) for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_suggest_validates_query(self, client: BraveClient) -> None:
        """suggest() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.suggest("")

    @pytest.mark.asyncio
    async def test_suggest_calls_correct_endpoint(self, client: BraveClient) -> None:
        """suggest() should call /suggest/search endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_SUGGEST_RESPONSE
            await client.suggest("test")

            mock_get.assert_called_once()
            assert mock_get.call_args[0][0] == "/suggest/search"


class TestBraveClientCaching:
    """Tests for BraveClient caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_stores_results(self) -> None:
        """Client should cache search results."""
        client = BraveClient(api_key="test-key", enable_caching=True)  # pragma: allowlist secret

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE

            # First call should hit API
            await client.search("test")
            assert mock_get.call_count == 1

            # Second call should use cache
            await client.search("test")
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_disabled_hits_api_each_time(self) -> None:
        """Client with caching disabled should hit API each time."""
        client = BraveClient(api_key="test-key", enable_caching=False)  # pragma: allowlist secret

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE

            await client.search("test")
            await client.search("test")

            assert mock_get.call_count == 2

    def test_clear_cache_returns_count(self) -> None:
        """clear_cache() should return number of entries cleared."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        # Manually add cache entries
        from datetime import datetime

        client._cache["key1"] = (MOCK_WEB_SEARCH_SIMPLE, datetime.now())  # type: ignore
        client._cache["key2"] = (MOCK_NEWS_SEARCH_RESPONSE, datetime.now())  # type: ignore

        count = client.clear_cache()
        assert count == 2
        assert len(client._cache) == 0


class TestBraveClientHealthCheck:
    """Tests for BraveClient.health_check()."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_on_success(self, client: BraveClient) -> None:
        """health_check() should return healthy=True on success."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = BraveSearchResponse(
                query="test", search_type=BraveSearchType.WEB
            )
            result = await client.health_check()

            assert result["name"] == "brave"
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_failure(self, client: BraveClient) -> None:
        """health_check() should return healthy=False on failure."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = BraveError("API error")
            result = await client.health_check()

            assert result["name"] == "brave"
            assert result["healthy"] is False
            assert "error" in result


class TestBraveClientCallEndpoint:
    """Tests for BraveClient.call_endpoint() direct API access."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_call_endpoint_returns_response(self, client: BraveClient) -> None:
        """call_endpoint() should return raw API response."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"custom": "response"}
            result = await client.call_endpoint("/custom/endpoint")

            assert result == {"custom": "response"}

    @pytest.mark.asyncio
    async def test_call_endpoint_raises_brave_error(self, client: BraveClient) -> None:
        """call_endpoint() should raise BraveError on failure."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            from src.integrations.base import IntegrationError

            mock_request.side_effect = IntegrationError("Request failed", status_code=500)

            with pytest.raises(BraveError) as exc_info:
                await client.call_endpoint("/failing/endpoint")

            assert "API call failed" in str(exc_info.value)


class TestBraveClientContextManager:
    """Tests for BraveClient async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_clears_cache_on_exit(self) -> None:
        """Context manager should clear cache on exit."""
        client = BraveClient(api_key="test-key")  # pragma: allowlist secret
        from datetime import datetime

        client._cache["key1"] = (MOCK_WEB_SEARCH_SIMPLE, datetime.now())  # type: ignore

        with patch.object(client, "close", new_callable=AsyncMock):
            async with client:
                assert len(client._cache) == 1

        assert len(client._cache) == 0


class TestBraveDataclasses:
    """Tests for Brave Search dataclass structures."""

    def test_web_result_dataclass(self) -> None:
        """BraveWebResult should have correct default values."""
        result = BraveWebResult(
            title="Test",
            url="https://example.com",
            description="Description",
        )
        assert result.age is None
        assert result.family_friendly is True
        assert result.extra_snippets == []

    def test_news_result_dataclass(self) -> None:
        """BraveNewsResult should have correct fields."""
        result = BraveNewsResult(
            title="News",
            url="https://news.com",
            description="News description",
            source="news.com",
        )
        assert result.age is None
        assert result.thumbnail_url is None

    def test_image_result_dataclass(self) -> None:
        """BraveImageResult should have correct fields."""
        result = BraveImageResult(
            title="Image",
            url="https://img.com/img.jpg",
            thumbnail_url="https://img.com/thumb.jpg",
            source="source.com",
            page_url="https://source.com/page",
        )
        assert result.width is None
        assert result.height is None

    def test_video_result_dataclass(self) -> None:
        """BraveVideoResult should have correct fields."""
        result = BraveVideoResult(
            title="Video",
            url="https://video.com",
            description="Video description",
            thumbnail_url="https://video.com/thumb.jpg",
        )
        assert result.duration is None
        assert result.views is None

    def test_infobox_dataclass(self) -> None:
        """BraveInfobox should have correct fields."""
        infobox = BraveInfobox(
            title="Company",
            description="A company description",
            type="organization",
        )
        assert infobox.attributes == {}
        assert infobox.url is None

    def test_faq_dataclass(self) -> None:
        """BraveFaq should have correct fields."""
        faq = BraveFaq(
            question="What is it?",
            answer="It is a thing.",
        )
        assert faq.url is None
        assert faq.title is None


class TestBraveEnums:
    """Tests for Brave Search enum values."""

    def test_safesearch_enum_values(self) -> None:
        """BraveSafesearch should have correct values."""
        assert BraveSafesearch.OFF.value == "off"
        assert BraveSafesearch.MODERATE.value == "moderate"
        assert BraveSafesearch.STRICT.value == "strict"

    def test_freshness_enum_values(self) -> None:
        """BraveFreshness should have correct values."""
        assert BraveFreshness.DAY.value == "pd"
        assert BraveFreshness.WEEK.value == "pw"
        assert BraveFreshness.MONTH.value == "pm"
        assert BraveFreshness.YEAR.value == "py"

    def test_search_type_enum_values(self) -> None:
        """BraveSearchType should have correct values."""
        assert BraveSearchType.WEB.value == "web"
        assert BraveSearchType.NEWS.value == "news"
        assert BraveSearchType.IMAGES.value == "images"
        assert BraveSearchType.VIDEOS.value == "videos"
        assert BraveSearchType.SUGGEST.value == "suggest"


class TestBraveWebResponseParsing:
    """Tests for web response parsing edge cases."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_parses_mixed_news_in_web_results(self, client: BraveClient) -> None:
        """Web search should include news mixed into results."""
        response = create_web_search_response(query="mixed", num_results=2, include_news=True)
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = response
            result = await client.search("mixed")

            assert len(result.results) == 2
            assert len(result.news_results) == 1

    @pytest.mark.asyncio
    async def test_parses_mixed_videos_in_web_results(self, client: BraveClient) -> None:
        """Web search should include videos mixed into results."""
        response = create_web_search_response(query="mixed", num_results=2, include_videos=True)
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = response
            result = await client.search("mixed")

            assert len(result.results) == 2
            assert len(result.video_results) == 1

    @pytest.mark.asyncio
    async def test_handles_missing_infobox(self, client: BraveClient) -> None:
        """Web search should handle missing infobox gracefully."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_WEB_SEARCH_SIMPLE
            result = await client.search("test")

            assert result.infobox is None

    @pytest.mark.asyncio
    async def test_handles_infobox_without_attributes(self, client: BraveClient) -> None:
        """Web search should handle infobox without attributes."""
        response = {
            "query": {"original": "test"},
            "web": {"results": []},
            "infobox": {
                "results": [
                    {
                        "title": "Test",
                        "description": "Description",
                        "type": "entity",
                    }
                ]
            },
        }
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = response
            result = await client.search("test")

            assert result.infobox is not None
            assert result.infobox.attributes == {}


class TestBraveSuggestResponseParsing:
    """Tests for suggest response parsing edge cases."""

    @pytest.fixture
    def client(self) -> BraveClient:
        """Create a BraveClient instance for testing."""
        return BraveClient(
            api_key="test-key",  # pragma: allowlist secret
            enable_caching=False,
        )

    @pytest.mark.asyncio
    async def test_parses_dict_format_suggest_response(self, client: BraveClient) -> None:
        """suggest() should handle dict format response."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": ["suggestion 1", "suggestion 2"]}
            result = await client.suggest("test")

            assert result.suggestions == ["suggestion 1", "suggestion 2"]

    @pytest.mark.asyncio
    async def test_parses_empty_suggestions(self, client: BraveClient) -> None:
        """suggest() should handle empty suggestions."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": []}
            result = await client.suggest("test")

            assert result.suggestions == []

    @pytest.mark.asyncio
    async def test_handles_missing_results_key(self, client: BraveClient) -> None:
        """suggest() should handle missing results key."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"query": "test"}
            result = await client.suggest("test")

            assert result.suggestions == []
