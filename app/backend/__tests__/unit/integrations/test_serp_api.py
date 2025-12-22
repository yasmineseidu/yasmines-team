"""Unit tests for SerpApi integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.serp_api_fixtures import (
    SAMPLE_ACCOUNT_INFO_RESPONSE,
    SAMPLE_ADS_ONLY_RESPONSE,
    SAMPLE_EMPTY_RESPONSE,
    SAMPLE_IMAGE_SEARCH_RESPONSE,
    SAMPLE_LOCAL_SEARCH_RESPONSE,
    SAMPLE_NEWS_SEARCH_RESPONSE,
    SAMPLE_SHOPPING_SEARCH_RESPONSE,
    SAMPLE_VIDEO_SEARCH_RESPONSE,
    SAMPLE_WEB_SEARCH_RESPONSE,
)
from src.integrations.base import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
)
from src.integrations.serp_api import (
    SerpApiClient,
    SerpApiEngine,
    SerpApiError,
    SerpApiSearchType,
    SerpApiTimeFilter,
)


class TestSerpApiClientInitialization:
    """Tests for SerpApiClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have correct name."""
        client = SerpApiClient(api_key="test-key")
        assert client.name == "serpapi"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = SerpApiClient(api_key="test-key")
        assert client.base_url == "https://serpapi.com"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        client = SerpApiClient(api_key="my-api-key")  # pragma: allowlist secret
        assert client.api_key == "my-api-key"  # pragma: allowlist secret

    def test_default_timeout(self) -> None:
        """Client should have default timeout of 60 seconds."""
        client = SerpApiClient(api_key="test-key")
        assert client.timeout == 60.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = SerpApiClient(api_key="test-key", timeout=120.0)
        assert client.timeout == 120.0

    def test_default_max_retries(self) -> None:
        """Client should have default max retries of 3."""
        client = SerpApiClient(api_key="test-key")
        assert client.max_retries == 3

    def test_default_engine(self) -> None:
        """Client should default to Google search engine."""
        client = SerpApiClient(api_key="test-key")
        assert client.default_engine == SerpApiEngine.GOOGLE

    def test_custom_default_engine(self) -> None:
        """Client should accept custom default engine."""
        client = SerpApiClient(api_key="test-key", default_engine=SerpApiEngine.BING)
        assert client.default_engine == SerpApiEngine.BING


class TestSerpApiClientSearch:
    """Tests for SerpApiClient.search() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_success(self, client: SerpApiClient) -> None:
        """search() should return parsed results on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI startups 2024")

            assert result.query == "AI startups 2024"
            assert result.search_engine == SerpApiEngine.GOOGLE
            assert result.search_type == SerpApiSearchType.SEARCH
            assert len(result.organic_results) == 3
            assert result.organic_results[0].title == "Top 10 AI Startups to Watch in 2024"
            assert result.organic_results[0].position == 1

    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(self, client: SerpApiClient) -> None:
        """search() should pass custom parameters correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            await client.search(
                "test query",
                num=20,
                start=10,
                country="uk",
                language="en",
                location="London, UK",
            )

            call_args = mock_get.call_args
            params = call_args.kwargs["params"]
            assert params["q"] == "test query"
            assert params["num"] == 20
            assert params["start"] == 10
            assert params["gl"] == "uk"
            assert params["hl"] == "en"
            assert params["location"] == "London, UK"

    @pytest.mark.asyncio
    async def test_search_with_time_filter(self, client: SerpApiClient) -> None:
        """search() should handle time filter parameter."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            await client.search("test", time_filter=SerpApiTimeFilter.PAST_WEEK)

            call_args = mock_get.call_args
            params = call_args.kwargs["params"]
            assert params["tbs"] == "qdr:w"

    @pytest.mark.asyncio
    async def test_search_parses_knowledge_graph(self, client: SerpApiClient) -> None:
        """search() should parse knowledge graph correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI")

            assert result.knowledge_graph is not None
            assert result.knowledge_graph.title == "Artificial Intelligence"
            assert result.knowledge_graph.type == "Technology"

    @pytest.mark.asyncio
    async def test_search_parses_answer_box(self, client: SerpApiClient) -> None:
        """search() should parse answer box correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI")

            assert result.answer_box is not None
            assert "AI startups are companies" in (result.answer_box.snippet or "")

    @pytest.mark.asyncio
    async def test_search_parses_ads(self, client: SerpApiClient) -> None:
        """search() should parse ads correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI")

            assert len(result.ads_results) == 1
            assert "Free Demo" in result.ads_results[0].title

    @pytest.mark.asyncio
    async def test_search_parses_related_searches(self, client: SerpApiClient) -> None:
        """search() should parse related searches correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI")

            assert len(result.related_searches) == 4
            assert result.related_searches[0].query == "AI companies to invest in 2024"

    @pytest.mark.asyncio
    async def test_search_parses_people_also_ask(self, client: SerpApiClient) -> None:
        """search() should parse People Also Ask correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.search("AI")

            assert len(result.people_also_ask) == 2
            assert "invest" in result.people_also_ask[0].question.lower()

    @pytest.mark.asyncio
    async def test_search_raises_on_empty_query(self, client: SerpApiClient) -> None:
        """search() should raise ValueError on empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_search_raises_on_whitespace_query(self, client: SerpApiClient) -> None:
        """search() should raise ValueError on whitespace-only query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("   ")

    @pytest.mark.asyncio
    async def test_search_raises_on_invalid_num(self, client: SerpApiClient) -> None:
        """search() should raise ValueError on invalid num parameter."""
        with pytest.raises(ValueError, match="num must be between"):
            await client.search("test", num=0)
        with pytest.raises(ValueError, match="num must be between"):
            await client.search("test", num=101)

    @pytest.mark.asyncio
    async def test_search_raises_on_negative_start(self, client: SerpApiClient) -> None:
        """search() should raise ValueError on negative start."""
        with pytest.raises(ValueError, match="start must be >= 0"):
            await client.search("test", start=-1)

    @pytest.mark.asyncio
    async def test_search_raises_serp_api_error_on_failure(self, client: SerpApiClient) -> None:
        """search() should raise SerpApiError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("API error", status_code=500)
            with pytest.raises(SerpApiError, match="Web search failed"):
                await client.search("test")


class TestSerpApiClientSearchImages:
    """Tests for SerpApiClient.search_images() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_images_success(self, client: SerpApiClient) -> None:
        """search_images() should return parsed images on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_IMAGE_SEARCH_RESPONSE
            result = await client.search_images("AI robot")

            assert result.query == "AI robot"
            assert result.search_type == SerpApiSearchType.IMAGES
            assert len(result.images) == 3
            assert result.images[0].title == "Humanoid AI Robot"
            assert result.images[1].is_product is True

    @pytest.mark.asyncio
    async def test_search_images_with_filters(self, client: SerpApiClient) -> None:
        """search_images() should handle image filters."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_IMAGE_SEARCH_RESPONSE
            await client.search_images(
                "robot",
                image_size="large",
                image_type="photo",
                image_color="color",
            )

            call_args = mock_get.call_args
            params = call_args.kwargs["params"]
            assert params["imgsz"] == "large"
            assert params["imgtype"] == "photo"
            assert params["imgc"] == "color"


class TestSerpApiClientSearchNews:
    """Tests for SerpApiClient.search_news() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_news_success(self, client: SerpApiClient) -> None:
        """search_news() should return parsed news on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_NEWS_SEARCH_RESPONSE
            result = await client.search_news("AI news")

            assert result.query == "AI news"
            assert result.search_type == SerpApiSearchType.NEWS
            assert len(result.news) == 3
            assert "GPT-5" in result.news[0].title
            assert result.news[0].source == "AI News Daily"

    @pytest.mark.asyncio
    async def test_search_news_with_time_filter(self, client: SerpApiClient) -> None:
        """search_news() should handle time filter."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_NEWS_SEARCH_RESPONSE
            await client.search_news("test", time_filter=SerpApiTimeFilter.PAST_DAY)

            call_args = mock_get.call_args
            params = call_args.kwargs["params"]
            assert params["tbs"] == "qdr:d"


class TestSerpApiClientSearchShopping:
    """Tests for SerpApiClient.search_shopping() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_shopping_success(self, client: SerpApiClient) -> None:
        """search_shopping() should return parsed shopping results on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_SHOPPING_SEARCH_RESPONSE
            result = await client.search_shopping("robot vacuum")

            assert result.query == "robot vacuum"
            assert result.search_type == SerpApiSearchType.SHOPPING
            assert len(result.shopping) == 3
            assert "Roborock" in result.shopping[0].title
            assert result.shopping[0].extracted_price == 1099.99
            assert result.shopping[0].rating == 4.7


class TestSerpApiClientSearchVideos:
    """Tests for SerpApiClient.search_videos() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_videos_success(self, client: SerpApiClient) -> None:
        """search_videos() should return video results."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_VIDEO_SEARCH_RESPONSE
            result = await client.search_videos("AI tutorial")

            assert result.query == "AI tutorial"
            assert result.search_type == SerpApiSearchType.VIDEOS
            assert len(result.organic_results) == 2


class TestSerpApiClientSearchLocal:
    """Tests for SerpApiClient.search_local() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_local_success(self, client: SerpApiClient) -> None:
        """search_local() should return local results on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_LOCAL_SEARCH_RESPONSE
            result = await client.search_local("coffee shops", location="San Francisco")

            assert result.query == "coffee shops"
            assert result.search_type == SerpApiSearchType.MAPS
            assert len(result.local_results) == 2
            assert result.local_results[0].title == "Blue Bottle Coffee"
            assert result.local_results[0].rating == 4.6
            assert result.local_results[0].latitude == 37.7823

    @pytest.mark.asyncio
    async def test_search_local_with_coordinates(self, client: SerpApiClient) -> None:
        """search_local() should handle GPS coordinates."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_LOCAL_SEARCH_RESPONSE
            await client.search_local(
                "coffee",
                latitude=37.7749,
                longitude=-122.4194,
            )

            call_args = mock_get.call_args
            params = call_args.kwargs["params"]
            assert "@37.7749,-122.4194,14z" in params["ll"]


class TestSerpApiClientConvenienceMethods:
    """Tests for SerpApiClient convenience methods."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_organic_results(self, client: SerpApiClient) -> None:
        """get_organic_results() should return only organic results."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            results = await client.get_organic_results("AI")

            assert len(results) == 3
            assert all(hasattr(r, "position") for r in results)

    @pytest.mark.asyncio
    async def test_get_paid_results(self, client: SerpApiClient) -> None:
        """get_paid_results() should return only ad results."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            results = await client.get_paid_results("AI")

            assert len(results) == 1
            assert "Free Demo" in results[0].title

    @pytest.mark.asyncio
    async def test_get_related_searches(self, client: SerpApiClient) -> None:
        """get_related_searches() should return related searches."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            results = await client.get_related_searches("AI")

            assert len(results) == 4


class TestSerpApiClientPagination:
    """Tests for SerpApiClient.paginate_results() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_paginate_results_success(self, client: SerpApiClient) -> None:
        """paginate_results() should aggregate results from multiple pages."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            # Create a mock response using the parsing function
            from src.integrations.serp_api import SerpApiOrganicResult, SerpApiSearchResponse

            page_result = SerpApiSearchResponse(
                query="AI",
                search_engine=SerpApiEngine.GOOGLE,
                search_type=SerpApiSearchType.SEARCH,
                organic_results=[
                    SerpApiOrganicResult(
                        position=i,
                        title=f"Result {i}",
                        link=f"https://example.com/{i}",
                        snippet=f"Snippet {i}",
                    )
                    for i in range(1, 11)  # 10 results per page
                ],
            )
            mock_search.return_value = page_result
            result = await client.paginate_results("AI", pages=2)

            # Should have made 2 requests
            assert mock_search.call_count == 2
            # Should have aggregated results (10 from first + 10 from second)
            assert len(result.organic_results) == 20

    @pytest.mark.asyncio
    async def test_paginate_results_stops_on_empty(self, client: SerpApiClient) -> None:
        """paginate_results() should stop when no more results."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            from src.integrations.serp_api import SerpApiOrganicResult, SerpApiSearchResponse

            # First page has results
            page1_result = SerpApiSearchResponse(
                query="AI",
                search_engine=SerpApiEngine.GOOGLE,
                search_type=SerpApiSearchType.SEARCH,
                organic_results=[
                    SerpApiOrganicResult(
                        position=i,
                        title=f"Result {i}",
                        link=f"https://example.com/{i}",
                        snippet=f"Snippet {i}",
                    )
                    for i in range(1, 6)  # Only 5 results (less than requested 10)
                ],
            )
            mock_search.return_value = page1_result
            result = await client.paginate_results("AI", pages=3, results_per_page=10)

            # Should stop after first page (fewer results than requested)
            assert mock_search.call_count == 1
            assert len(result.organic_results) == 5

    @pytest.mark.asyncio
    async def test_paginate_results_invalid_pages(self, client: SerpApiClient) -> None:
        """paginate_results() should raise on invalid pages parameter."""
        with pytest.raises(ValueError, match="pages must be >= 1"):
            await client.paginate_results("test", pages=0)


class TestSerpApiClientHealthCheck:
    """Tests for SerpApiClient.health_check() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: SerpApiClient) -> None:
        """health_check() should return healthy status on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_WEB_SEARCH_RESPONSE
            result = await client.health_check()

            assert result["name"] == "serpapi"
            assert result["healthy"] is True
            assert result["base_url"] == "https://serpapi.com"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: SerpApiClient) -> None:
        """health_check() should return unhealthy status on failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Connection failed")
            result = await client.health_check()

            assert result["name"] == "serpapi"
            assert result["healthy"] is False
            assert "error" in result


class TestSerpApiClientAccountInfo:
    """Tests for SerpApiClient.get_account_info() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, client: SerpApiClient) -> None:
        """get_account_info() should return account information."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_ACCOUNT_INFO_RESPONSE
            result = await client.get_account_info()

            assert result["account_email"] == "user@example.com"
            assert result["plan_name"] == "Developer"
            assert result["plan_searches_left"] == 4850


class TestSerpApiClientCallEndpoint:
    """Tests for SerpApiClient.call_endpoint() method."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: SerpApiClient) -> None:
        """call_endpoint() should handle GET requests."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": "test"}
            result = await client.call_endpoint("/custom", method="GET")

            assert result["data"] == "test"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: SerpApiClient) -> None:
        """call_endpoint() should handle POST requests."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"status": "ok"}
            result = await client.call_endpoint("/custom", method="POST", json={})

            assert result["status"] == "ok"
            mock_post.assert_called_once()


class TestSerpApiClientErrorHandling:
    """Tests for SerpApiClient error handling."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error_propagates(self, client: SerpApiClient) -> None:
        """Authentication errors should propagate correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = AuthenticationError("Invalid API key")
            with pytest.raises(SerpApiError, match="Web search failed"):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagates(self, client: SerpApiClient) -> None:
        """Rate limit errors should propagate correctly."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = RateLimitError("Rate limit exceeded")
            with pytest.raises(SerpApiError, match="Web search failed"):
                await client.search("test")


class TestSerpApiClientEmptyResponses:
    """Tests for SerpApiClient handling of empty responses."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create test client instance."""
        return SerpApiClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_empty_organic_results(self, client: SerpApiClient) -> None:
        """search() should handle empty organic results."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_EMPTY_RESPONSE
            result = await client.search("xyzzy nonsense")

            assert len(result.organic_results) == 0
            assert result.search_info is not None
            assert result.search_info.total_results == 0

    @pytest.mark.asyncio
    async def test_ads_only_response(self, client: SerpApiClient) -> None:
        """search() should handle response with only ads."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SAMPLE_ADS_ONLY_RESPONSE
            result = await client.search("commercial query")

            assert len(result.organic_results) == 0
            # Should have ads from both "ads" and "top_ads" keys
            assert len(result.ads_results) == 2


class TestSerpApiClientHeaders:
    """Tests for SerpApiClient header handling."""

    def test_get_headers_no_auth_header(self) -> None:
        """SerpApi uses query param auth, not header auth."""
        client = SerpApiClient(api_key="test-key")
        headers = client._get_headers()

        # Should NOT have Authorization header (uses query param)
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestSerpApiClientBuildParams:
    """Tests for SerpApiClient._build_params() method."""

    def test_build_params_basic(self) -> None:
        """_build_params() should include required parameters."""
        client = SerpApiClient(api_key="test-key")
        params = client._build_params("test query")

        assert params["api_key"] == "test-key"  # pragma: allowlist secret
        assert params["engine"] == "google"
        assert params["q"] == "test query"
        assert params["output"] == "json"

    def test_build_params_strips_query(self) -> None:
        """_build_params() should strip whitespace from query."""
        client = SerpApiClient(api_key="test-key")
        params = client._build_params("  test query  ")

        assert params["q"] == "test query"

    def test_build_params_with_custom_engine(self) -> None:
        """_build_params() should use custom engine."""
        client = SerpApiClient(api_key="test-key")
        params = client._build_params("test", engine=SerpApiEngine.BING)

        assert params["engine"] == "bing"

    def test_build_params_with_enum_values(self) -> None:
        """_build_params() should convert enum values."""
        client = SerpApiClient(api_key="test-key")
        params = client._build_params(
            "test",
            engine=SerpApiEngine.YAHOO,
            tbs=SerpApiTimeFilter.PAST_MONTH,
        )

        assert params["engine"] == "yahoo"
        assert params["tbs"] == "qdr:m"
