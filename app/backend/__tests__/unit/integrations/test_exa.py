"""Unit tests for Exa API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.exa_fixtures import (
    SAMPLE_COMPANY_SEARCH_RESPONSE,
    SAMPLE_CONTENTS_RESPONSE,
    SAMPLE_EMPTY_RESPONSE,
    SAMPLE_FIND_SIMILAR_RESPONSE,
    SAMPLE_NEWS_SEARCH_RESPONSE,
    SAMPLE_RESEARCH_SEARCH_RESPONSE,
    SAMPLE_SEARCH_RESPONSE,
)
from src.integrations.base import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
)
from src.integrations.exa import (
    ExaCategory,
    ExaClient,
    ExaError,
    ExaSearchType,
)


class TestExaClientInitialization:
    """Tests for ExaClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have correct name."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "exa"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.exa.ai"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        client = ExaClient(api_key="my-exa-key")  # pragma: allowlist secret
        assert client.api_key == "my-exa-key"  # pragma: allowlist secret

    def test_default_timeout(self) -> None:
        """Client should have default timeout of 60 seconds."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = ExaClient(api_key="test-key", timeout=120.0)  # pragma: allowlist secret
        assert client.timeout == 120.0

    def test_default_max_retries(self) -> None:
        """Client should have default max retries of 3."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_caching_enabled_by_default(self) -> None:
        """Client should have caching enabled by default."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        assert client.enable_caching is True

    def test_caching_can_be_disabled(self) -> None:
        """Client should allow disabling caching."""
        client = ExaClient(api_key="test-key", enable_caching=False)  # pragma: allowlist secret
        assert client.enable_caching is False


class TestExaClientHeaders:
    """Tests for ExaClient header handling."""

    def test_uses_x_api_key_header(self) -> None:
        """Client should use x-api-key header for authentication."""
        client = ExaClient(api_key="my-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["x-api-key"] == "my-key"  # pragma: allowlist secret
        assert "Authorization" not in headers

    def test_content_type_json(self) -> None:
        """Headers should include Content-Type: application/json."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"


class TestExaClientSearch:
    """Tests for ExaClient.search() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_success(self, client: ExaClient) -> None:
        """search() should return parsed results on success."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.search("AI agent startups")

            assert result.query == "AI agent startups"
            assert result.search_type == ExaSearchType.AUTO
            assert len(result.results) == 3
            assert result.results[0].title == "Top AI Agent Startups Revolutionizing Enterprise"
            assert result.results[0].score == 0.95
            assert result.results[0].id == "exa_id_001"

    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(self, client: ExaClient) -> None:
        """search() should pass custom parameters correctly."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            await client.search(
                "test query",
                search_type=ExaSearchType.NEURAL,
                num_results=20,
                include_domains=["example.com", "test.com"],
                exclude_domains=["spam.com"],
                use_autoprompt=True,
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["query"] == "test query"
            assert payload["type"] == "neural"
            assert payload["numResults"] == 20
            assert payload["includeDomains"] == ["example.com", "test.com"]
            assert payload["excludeDomains"] == ["spam.com"]
            assert payload["useAutoprompt"] is True

    @pytest.mark.asyncio
    async def test_search_parses_autoprompt(self, client: ExaClient) -> None:
        """search() should parse autoprompt information."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.search("AI agents")

            assert result.autoprompt is not None
            assert result.autoprompt.original_query == "AI agents"
            assert (
                result.autoprompt.transformed_query == "companies building AI agents for enterprise"
            )

    @pytest.mark.asyncio
    async def test_search_parses_cost_credits(self, client: ExaClient) -> None:
        """search() should parse cost credits."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.search("test")

            assert result.cost_credits == 0.1

    @pytest.mark.asyncio
    async def test_search_parses_highlights(self, client: ExaClient) -> None:
        """search() should parse highlights from results."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.search("test")

            assert len(result.results[0].highlights) == 2
            assert "AI agents are automating" in result.results[0].highlights[0]
            assert len(result.results[0].highlight_scores) == 2

    @pytest.mark.asyncio
    async def test_search_with_date_filters(self, client: ExaClient) -> None:
        """search() should handle date filter parameters."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            await client.search(
                "test",
                start_published_date="2024-01-01",
                end_published_date="2024-12-31",
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["startPublishedDate"] == "2024-01-01"
            assert payload["endPublishedDate"] == "2024-12-31"

    @pytest.mark.asyncio
    async def test_search_with_category(self, client: ExaClient) -> None:
        """search() should handle category parameter."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            await client.search("test", category=ExaCategory.COMPANY)

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["category"] == "company"

    @pytest.mark.asyncio
    async def test_search_raises_on_empty_query(self, client: ExaClient) -> None:
        """search() should raise ValueError on empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_search_raises_on_invalid_num_results(self, client: ExaClient) -> None:
        """search() should raise ValueError on invalid num_results."""
        with pytest.raises(ValueError, match="num_results must be between"):
            await client.search("test", num_results=0)
        with pytest.raises(ValueError, match="num_results must be between"):
            await client.search("test", num_results=101)

    @pytest.mark.asyncio
    async def test_search_raises_exa_error_on_failure(self, client: ExaClient) -> None:
        """search() should raise ExaError on API failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("API error", status_code=500)
            with pytest.raises(ExaError, match="Search failed"):
                await client.search("test")


class TestExaClientFindSimilar:
    """Tests for ExaClient.find_similar() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_similar_success(self, client: ExaClient) -> None:
        """find_similar() should return similar content."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_FIND_SIMILAR_RESPONSE
            result = await client.find_similar("https://example.com/article")

            assert "similar:" in result.query
            assert result.search_type == ExaSearchType.NEURAL
            assert len(result.results) == 3
            assert result.results[0].score == 0.93

    @pytest.mark.asyncio
    async def test_find_similar_with_exclude_source_domain(self, client: ExaClient) -> None:
        """find_similar() should exclude source domain by default."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_FIND_SIMILAR_RESPONSE
            await client.find_similar("https://example.com/article")

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["excludeSourceDomain"] is True

    @pytest.mark.asyncio
    async def test_find_similar_include_source_domain(self, client: ExaClient) -> None:
        """find_similar() should allow including source domain."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_FIND_SIMILAR_RESPONSE
            await client.find_similar(
                "https://example.com/article",
                exclude_source_domain=False,
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["excludeSourceDomain"] is False

    @pytest.mark.asyncio
    async def test_find_similar_raises_on_empty_url(self, client: ExaClient) -> None:
        """find_similar() should raise ValueError on empty URL."""
        with pytest.raises(ValueError, match="url is required"):
            await client.find_similar("")


class TestExaClientGetContents:
    """Tests for ExaClient.get_contents() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_contents_success(self, client: ExaClient) -> None:
        """get_contents() should return document contents."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_CONTENTS_RESPONSE
            result = await client.get_contents(["exa_id_001", "exa_id_002"])

            assert len(result.results) == 2
            assert result.results[0].id == "exa_id_001"
            assert "Full article text" in (result.results[0].text or "")
            assert len(result.results[0].highlights) == 2

    @pytest.mark.asyncio
    async def test_get_contents_with_options(self, client: ExaClient) -> None:
        """get_contents() should pass content options correctly."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_CONTENTS_RESPONSE
            await client.get_contents(
                ["exa_id_001"],
                text=True,
                highlights=True,
                summary=True,
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["contents"]["text"] is True
            assert payload["contents"]["highlights"] is True
            assert payload["contents"]["summary"] is True

    @pytest.mark.asyncio
    async def test_get_contents_raises_on_empty_ids(self, client: ExaClient) -> None:
        """get_contents() should raise ValueError on empty IDs list."""
        with pytest.raises(ValueError, match="ids list cannot be empty"):
            await client.get_contents([])


class TestExaClientSearchAndContents:
    """Tests for ExaClient.search_and_contents() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_and_contents_success(self, client: ExaClient) -> None:
        """search_and_contents() should search and return content together."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.search_and_contents(
                "AI agents",
                text=True,
                highlights=True,
            )

            assert len(result.results) > 0
            # Verify contents options were included in request
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["contents"]["text"] is True
            assert payload["contents"]["highlights"] is True


class TestExaClientConvenienceMethods:
    """Tests for ExaClient convenience methods."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_companies(self, client: ExaClient) -> None:
        """search_companies() should use company category."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_COMPANY_SEARCH_RESPONSE
            result = await client.search_companies("AI healthcare startups")

            assert len(result.results) == 3
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["category"] == "company"
            assert payload["useAutoprompt"] is True

    @pytest.mark.asyncio
    async def test_search_research_papers(self, client: ExaClient) -> None:
        """search_research_papers() should use research paper category."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_RESEARCH_SEARCH_RESPONSE
            result = await client.search_research_papers("LLM agents")

            assert len(result.results) == 2
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["category"] == "research paper"

    @pytest.mark.asyncio
    async def test_search_news(self, client: ExaClient) -> None:
        """search_news() should use news category."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_NEWS_SEARCH_RESPONSE
            result = await client.search_news("AI regulation")

            assert len(result.results) == 2
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["category"] == "news"


class TestExaClientHealthCheck:
    """Tests for ExaClient.health_check() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: ExaClient) -> None:
        """health_check() should return healthy status on success."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE
            result = await client.health_check()

            assert result["name"] == "exa"
            assert result["healthy"] is True
            assert result["base_url"] == "https://api.exa.ai"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: ExaClient) -> None:
        """health_check() should return unhealthy status on failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Connection failed")
            result = await client.health_check()

            assert result["name"] == "exa"
            assert result["healthy"] is False
            assert "error" in result


class TestExaClientCaching:
    """Tests for ExaClient caching functionality."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance with caching."""
        return ExaClient(api_key="test-api-key", enable_caching=True)  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_caches_search_results(self, client: ExaClient) -> None:
        """search() should cache results."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_SEARCH_RESPONSE

            # First call - should hit API
            result1 = await client.search("cached query")
            assert mock_post.call_count == 1

            # Second call with same query - should use cache
            result2 = await client.search("cached query")
            assert mock_post.call_count == 1  # Still 1, cache hit

            # Results should be the same
            assert result1.query == result2.query
            assert len(result1.results) == len(result2.results)

    def test_clear_cache(self) -> None:
        """clear_cache() should remove all cached entries."""
        client = ExaClient(api_key="test-key")  # pragma: allowlist secret
        # Simulate some cached entries
        client._cache["key1"] = ("result1", None)  # type: ignore[assignment]
        client._cache["key2"] = ("result2", None)  # type: ignore[assignment]

        count = client.clear_cache()
        assert count == 2
        assert len(client._cache) == 0


class TestExaClientErrorHandling:
    """Tests for ExaClient error handling."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_authentication_error_propagates(self, client: ExaClient) -> None:
        """Authentication errors should propagate correctly."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = AuthenticationError("Invalid API key")
            with pytest.raises(ExaError, match="Search failed"):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagates(self, client: ExaClient) -> None:
        """Rate limit errors should propagate correctly."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RateLimitError("Rate limit exceeded")
            with pytest.raises(ExaError, match="Search failed"):
                await client.search("test")


class TestExaClientEmptyResponses:
    """Tests for ExaClient handling of empty responses."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_empty_search_results(self, client: ExaClient) -> None:
        """search() should handle empty results."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_EMPTY_RESPONSE
            result = await client.search("obscure query with no results")

            assert len(result.results) == 0
            assert result.cost_credits == 0.01


class TestExaClientCallEndpoint:
    """Tests for ExaClient.call_endpoint() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: ExaClient) -> None:
        """call_endpoint() should handle POST requests."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"status": "ok"}
            result = await client.call_endpoint("/custom", method="POST", json={})

            assert result["status"] == "ok"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: ExaClient) -> None:
        """call_endpoint() should handle GET requests."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": "test"}
            result = await client.call_endpoint("/custom", method="GET")

            assert result["data"] == "test"
            mock_get.assert_called_once()


class TestExaClientFindSimilarAndContents:
    """Tests for ExaClient.find_similar_and_contents() method."""

    @pytest.fixture
    def client(self) -> ExaClient:
        """Create test client instance."""
        return ExaClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_find_similar_and_contents_success(self, client: ExaClient) -> None:
        """find_similar_and_contents() should return similar content with text."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = SAMPLE_FIND_SIMILAR_RESPONSE
            result = await client.find_similar_and_contents(
                "https://example.com/article",
                text=True,
                highlights=True,
            )

            assert len(result.results) > 0
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["contents"]["text"] is True
            assert payload["contents"]["highlights"] is True

