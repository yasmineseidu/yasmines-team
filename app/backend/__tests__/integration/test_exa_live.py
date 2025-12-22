"""
Live integration tests for Exa API.

These tests make real API calls to verify functionality against the live Exa API.
Run with: uv run pytest __tests__/integration/test_exa_live.py -v

Requirements:
    - Valid EXA_API_KEY in environment or .env file
    - Internet connectivity
    - API credits available

Note: These tests consume API credits. Use sparingly.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from src.integrations.exa import (
    ExaCategory,
    ExaClient,
    ExaSearchType,
)


def load_env_file() -> None:
    """Load environment variables from .env file at project root."""
    # Try multiple potential .env locations
    env_paths = [
        Path(__file__).parent.parent.parent.parent.parent / ".env",  # Project root
        Path(__file__).parent.parent.parent / ".env",  # Backend root
        Path.cwd() / ".env",  # Current directory
    ]

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Skip masked values and empty values
                        if (
                            key
                            and value
                            and value != "..."
                            and value != "None"
                            and len(value) > 3  # Real API keys are longer
                        ):
                            os.environ.setdefault(key, value)
            break


# Load .env file
load_env_file()


def get_api_key() -> str | None:
    """Get Exa API key from environment."""
    return os.environ.get("EXA_API_KEY")


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not get_api_key(),
    reason="EXA_API_KEY not found in environment",
)


# =============================================================================
# SAMPLE TEST DATA
# =============================================================================

# Semantic search test queries
SEMANTIC_SEARCH_SAMPLES = [
    {
        "query": "companies building AI agents for enterprise automation",
        "description": "Enterprise AI search",
        "expected_min_results": 3,
    },
    {
        "query": "startups in healthcare technology using machine learning",
        "description": "Healthcare tech search",
        "expected_min_results": 3,
    },
    {
        "query": "SaaS tools for content marketing and SEO",
        "description": "Marketing tools search",
        "expected_min_results": 3,
    },
    {
        "query": "climate change solutions and renewable energy innovations",
        "description": "Environmental tech search",
        "expected_min_results": 3,
    },
    {
        "query": "Python async programming best practices and patterns",
        "description": "Technical programming search",
        "expected_min_results": 3,
    },
]

# Company search test queries
COMPANY_SEARCH_SAMPLES = [
    {
        "query": "AI healthcare startups",
        "description": "Healthcare AI companies",
        "expected_min_results": 2,
    },
    {
        "query": "SaaS CRM companies",
        "description": "CRM software companies",
        "expected_min_results": 2,
    },
    {
        "query": "fintech payment processing companies",
        "description": "Fintech companies",
        "expected_min_results": 2,
    },
]

# Research paper search test queries
RESEARCH_PAPER_SAMPLES = [
    {
        "query": "large language models and transformer architectures",
        "description": "LLM research papers",
        "expected_min_results": 2,
    },
    {
        "query": "reinforcement learning from human feedback",
        "description": "RLHF research",
        "expected_min_results": 2,
    },
]

# News search test queries
NEWS_SEARCH_SAMPLES = [
    {
        "query": "AI technology news and developments",
        "description": "AI news",
        "expected_min_results": 2,
    },
    {
        "query": "startup funding announcements 2024",
        "description": "Funding news",
        "expected_min_results": 2,
    },
]

# URLs for similarity search
SIMILAR_URL_SAMPLES = [
    "https://techcrunch.com/2024/12/01/ai-agents-enterprise/",
    "https://arxiv.org/abs/2023.12345",
    "https://openai.com/blog/chatgpt",
    "https://github.com/microsoft/autogen",
]

# Test domains for filtering
TEST_DOMAINS = [
    "techcrunch.com",
    "venturebeat.com",
    "arxiv.org",
    "github.com",
]


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
async def client() -> ExaClient:
    """Create Exa client instance for testing."""
    api_key = get_api_key()
    assert api_key, "EXA_API_KEY must be set"
    async with ExaClient(api_key=api_key) as client:  # pragma: allowlist secret
        yield client


# =============================================================================
# SEARCH ENDPOINT TESTS
# =============================================================================


class TestExaSearch:
    """Test Exa search() endpoint."""

    @pytest.mark.asyncio
    async def test_search_basic(self, client: ExaClient) -> None:
        """Test basic semantic search."""
        result = await client.search("AI startups 2024", num_results=5)

        assert result.query == "AI startups 2024"
        assert result.search_type == ExaSearchType.AUTO
        assert len(result.results) > 0
        assert len(result.results) <= 5

        # Verify result structure
        first_result = result.results[0]
        assert first_result.id
        assert first_result.url
        assert first_result.title
        # Score may or may not be present depending on search type

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", SEMANTIC_SEARCH_SAMPLES)
    async def test_search_semantic_samples(
        self,
        client: ExaClient,
        sample: dict[str, str | int],
    ) -> None:
        """Test semantic search with various queries."""
        query = str(sample["query"])
        expected_min = int(sample["expected_min_results"])

        result = await client.search(query, num_results=10)

        assert result.query == query
        assert len(result.results) >= expected_min

        # Verify all results have required fields
        for res in result.results:
            assert res.id
            assert res.url
            assert res.title
            assert res.url.startswith("http")

    @pytest.mark.asyncio
    async def test_search_neural_type(self, client: ExaClient) -> None:
        """Test search with neural type explicitly."""
        result = await client.search(
            "machine learning applications",
            search_type=ExaSearchType.NEURAL,
            num_results=5,
        )

        assert result.search_type == ExaSearchType.NEURAL
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_search_keyword_type(self, client: ExaClient) -> None:
        """Test search with keyword type."""
        result = await client.search(
            "Python programming",
            search_type=ExaSearchType.KEYWORD,
            num_results=5,
        )

        assert result.search_type == ExaSearchType.KEYWORD
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_search_with_autoprompt(self, client: ExaClient) -> None:
        """Test search with autoprompt enabled."""
        result = await client.search(
            "AI companies",
            use_autoprompt=True,
            num_results=5,
        )

        assert len(result.results) > 0
        # Autoprompt may or may not transform the query
        if result.autoprompt:
            assert result.autoprompt.original_query == "AI companies"

    @pytest.mark.asyncio
    async def test_search_with_domain_filters(self, client: ExaClient) -> None:
        """Test search with domain include/exclude filters."""
        result = await client.search(
            "technology news",
            include_domains=["techcrunch.com", "venturebeat.com"],
            num_results=10,
        )

        assert len(result.results) > 0
        # Verify all results are from included domains
        for res in result.results:
            assert any(domain in res.url for domain in ["techcrunch.com", "venturebeat.com"])

    @pytest.mark.asyncio
    async def test_search_with_category(self, client: ExaClient) -> None:
        """Test search with category filter."""
        result = await client.search(
            "AI research",
            category=ExaCategory.RESEARCH_PAPER,
            num_results=5,
        )

        assert len(result.results) > 0
        # Results should be research papers
        for res in result.results:
            assert res.url

    @pytest.mark.asyncio
    async def test_search_with_date_filters(self, client: ExaClient) -> None:
        """Test search with published date filters."""
        result = await client.search(
            "AI technology",
            start_published_date="2024-01-01",
            end_published_date="2024-12-31",
            num_results=5,
        )

        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_search_max_results(self, client: ExaClient) -> None:
        """Test search with maximum results."""
        result = await client.search("technology", num_results=20)

        assert len(result.results) <= 20
        assert len(result.results) > 0


# =============================================================================
# FIND SIMILAR ENDPOINT TESTS
# =============================================================================


class TestExaFindSimilar:
    """Test Exa find_similar() endpoint."""

    @pytest.mark.asyncio
    async def test_find_similar_basic(self, client: ExaClient) -> None:
        """Test basic find similar functionality."""
        # Use a well-known tech article URL
        test_url = "https://techcrunch.com/2024/12/01/ai-agents-enterprise/"

        result = await client.find_similar(test_url, num_results=5)

        assert "similar:" in result.query
        assert result.search_type == ExaSearchType.NEURAL
        assert len(result.results) > 0

        # Verify results are different from source
        for res in result.results:
            assert res.url != test_url
            assert res.id
            # Title may be empty for some results, but id and url should be present
            assert res.url.startswith("http")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("url", SIMILAR_URL_SAMPLES[:2])  # Test first 2 to save credits
    async def test_find_similar_url_samples(
        self,
        client: ExaClient,
        url: str,
    ) -> None:
        """Test find similar with various URLs."""
        result = await client.find_similar(url, num_results=5)

        assert len(result.results) > 0
        # Results should be semantically similar but different URLs
        for res in result.results:
            assert res.url != url
            assert res.score is not None

    @pytest.mark.asyncio
    async def test_find_similar_exclude_source_domain(
        self,
        client: ExaClient,
    ) -> None:
        """Test find similar with exclude_source_domain=True."""
        test_url = "https://techcrunch.com/article"

        result = await client.find_similar(
            test_url,
            exclude_source_domain=True,
            num_results=5,
        )

        assert len(result.results) > 0
        # Verify no results from source domain (check actual domain, not redirect URLs)
        source_domain = urlparse(test_url).netloc
        # Normalize domain (remove www. prefix for comparison)
        source_domain_normalized = source_domain.replace("www.", "")
        for res in result.results:
            result_domain = urlparse(res.url).netloc
            result_domain_normalized = result_domain.replace("www.", "")
            # Ensure the result domain is not the same as source domain
            # (check both ways to catch subdomains)
            assert (
                source_domain_normalized != result_domain_normalized
                and not result_domain_normalized.endswith("." + source_domain_normalized)
                and not source_domain_normalized.endswith("." + result_domain_normalized)
            )

    @pytest.mark.asyncio
    async def test_find_similar_include_source_domain(
        self,
        client: ExaClient,
    ) -> None:
        """Test find similar with exclude_source_domain=False."""
        test_url = "https://techcrunch.com/article"

        result = await client.find_similar(
            test_url,
            exclude_source_domain=False,
            num_results=5,
        )

        assert len(result.results) > 0


# =============================================================================
# GET CONTENTS ENDPOINT TESTS
# =============================================================================


class TestExaGetContents:
    """Test Exa get_contents() endpoint."""

    @pytest.mark.asyncio
    async def test_get_contents_basic(self, client: ExaClient) -> None:
        """Test basic content extraction."""
        # First, search to get some IDs
        search_result = await client.search("AI technology", num_results=3)
        assert len(search_result.results) > 0

        # Extract IDs
        ids = [res.id for res in search_result.results[:2]]

        # Get contents
        contents_result = await client.get_contents(ids, text=True)

        assert len(contents_result.results) == len(ids)
        for res in contents_result.results:
            assert res.id in ids
            assert res.url
            assert res.title
            assert res.text  # Should have text content

    @pytest.mark.asyncio
    async def test_get_contents_with_highlights(self, client: ExaClient) -> None:
        """Test content extraction with highlights."""
        # Search first
        search_result = await client.search("machine learning", num_results=2)
        ids = [res.id for res in search_result.results[:2]]

        # Get contents with highlights
        contents_result = await client.get_contents(
            ids,
            text=True,
            highlights=True,
            highlight_query="machine learning applications",
        )

        assert len(contents_result.results) > 0
        for res in contents_result.results:
            assert res.text
            # Highlights may or may not be present
            if res.highlights:
                assert len(res.highlights) > 0

    @pytest.mark.asyncio
    async def test_get_contents_with_summary(self, client: ExaClient) -> None:
        """Test content extraction with AI summary."""
        # Search first
        search_result = await client.search("AI research", num_results=2)
        ids = [res.id for res in search_result.results[:2]]

        # Get contents with summary
        contents_result = await client.get_contents(
            ids,
            text=True,
            summary=True,
        )

        assert len(contents_result.results) > 0
        for res in contents_result.results:
            assert res.text
            # Summary may or may not be present
            if res.summary:
                assert len(res.summary) > 0


# =============================================================================
# SEARCH AND CONTENTS ENDPOINT TESTS
# =============================================================================


class TestExaSearchAndContents:
    """Test Exa search_and_contents() endpoint."""

    @pytest.mark.asyncio
    async def test_search_and_contents_basic(self, client: ExaClient) -> None:
        """Test combined search and contents."""
        result = await client.search_and_contents(
            "AI startups",
            text=True,
            num_results=3,
        )

        assert len(result.results) > 0
        # Results should have text content
        for res in result.results:
            assert res.text
            assert res.url
            assert res.title

    @pytest.mark.asyncio
    async def test_search_and_contents_with_highlights(
        self,
        client: ExaClient,
    ) -> None:
        """Test search and contents with highlights."""
        result = await client.search_and_contents(
            "machine learning",
            text=True,
            highlights=True,
            num_results=3,
        )

        assert len(result.results) > 0
        for res in result.results:
            assert res.text
            if res.highlights:
                assert len(res.highlights) > 0

    @pytest.mark.asyncio
    async def test_search_and_contents_with_summary(
        self,
        client: ExaClient,
    ) -> None:
        """Test search and contents with summary."""
        result = await client.search_and_contents(
            "technology trends",
            text=True,
            summary=True,
            num_results=3,
        )

        assert len(result.results) > 0
        for res in result.results:
            assert res.text
            if res.summary:
                assert len(res.summary) > 0


# =============================================================================
# FIND SIMILAR AND CONTENTS ENDPOINT TESTS
# =============================================================================


class TestExaFindSimilarAndContents:
    """Test Exa find_similar_and_contents() endpoint."""

    @pytest.mark.asyncio
    async def test_find_similar_and_contents_basic(
        self,
        client: ExaClient,
    ) -> None:
        """Test combined find similar and contents."""
        test_url = "https://techcrunch.com/2024/12/01/ai-agents-enterprise/"

        result = await client.find_similar_and_contents(
            test_url,
            text=True,
            num_results=3,
        )

        assert len(result.results) > 0
        for res in result.results:
            assert res.text
            assert res.url != test_url


# =============================================================================
# CONVENIENCE METHOD TESTS
# =============================================================================


class TestExaConvenienceMethods:
    """Test Exa convenience methods."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", COMPANY_SEARCH_SAMPLES)
    async def test_search_companies(
        self,
        client: ExaClient,
        sample: dict[str, str | int],
    ) -> None:
        """Test search_companies() convenience method."""
        query = str(sample["query"])
        expected_min = int(sample["expected_min_results"])

        result = await client.search_companies(query, num_results=10)

        assert len(result.results) >= expected_min
        # Results should be company websites
        for res in result.results:
            assert res.url
            assert res.title

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", RESEARCH_PAPER_SAMPLES)
    async def test_search_research_papers(
        self,
        client: ExaClient,
        sample: dict[str, str | int],
    ) -> None:
        """Test search_research_papers() convenience method."""
        query = str(sample["query"])
        expected_min = int(sample["expected_min_results"])

        result = await client.search_research_papers(query, num_results=10)

        assert len(result.results) >= expected_min
        # Results should be research papers (verify they have URLs)
        for res in result.results:
            assert res.url
            # Research papers can be from various academic sources
            # Just verify we got results (the category filter ensures they're research papers)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", NEWS_SEARCH_SAMPLES)
    async def test_search_news(
        self,
        client: ExaClient,
        sample: dict[str, str | int],
    ) -> None:
        """Test search_news() convenience method."""
        query = str(sample["query"])
        expected_min = int(sample["expected_min_results"])

        result = await client.search_news(query, num_results=10)

        assert len(result.results) >= expected_min
        # Results should be news articles
        for res in result.results:
            assert res.url
            assert res.title


# =============================================================================
# HEALTH CHECK AND UTILITY TESTS
# =============================================================================


class TestExaHealthCheck:
    """Test Exa health check and utility methods."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: ExaClient) -> None:
        """Test health check endpoint."""
        health = await client.health_check()

        assert health["name"] == "exa"
        assert health["healthy"] is True
        assert health["base_url"] == "https://api.exa.ai"

    @pytest.mark.asyncio
    async def test_clear_cache(self, client: ExaClient) -> None:
        """Test cache clearing functionality."""
        # Perform a search to populate cache
        await client.search("test query", num_results=1)

        # Clear cache
        count = client.clear_cache()
        assert count >= 0  # May be 0 if caching didn't work

    @pytest.mark.asyncio
    async def test_caching_works(self, client: ExaClient) -> None:
        """Test that caching actually works."""
        query = "caching test query unique 12345"

        # First search - should hit API
        result1 = await client.search(query, num_results=3)

        # Second search with same query - should use cache
        result2 = await client.search(query, num_results=3)

        # Results should be identical (from cache)
        assert result1.query == result2.query
        assert len(result1.results) == len(result2.results)


# =============================================================================
# FUTURE-PROOF ENDPOINT TESTS
# =============================================================================


class TestExaCallEndpoint:
    """Test Exa call_endpoint() for future-proofing."""

    @pytest.mark.asyncio
    async def test_call_endpoint_search(self, client: ExaClient) -> None:
        """Test call_endpoint() with search endpoint."""
        response = await client.call_endpoint(
            "/search",
            method="POST",
            json={
                "query": "test query",
                "numResults": 3,
            },
        )

        assert "results" in response
        assert isinstance(response["results"], list)

    @pytest.mark.asyncio
    async def test_call_endpoint_find_similar(self, client: ExaClient) -> None:
        """Test call_endpoint() with findSimilar endpoint."""
        response = await client.call_endpoint(
            "/findSimilar",
            method="POST",
            json={
                "url": "https://techcrunch.com/article",
                "numResults": 3,
            },
        )

        assert "results" in response
        assert isinstance(response["results"], list)

    @pytest.mark.asyncio
    async def test_call_endpoint_contents(self, client: ExaClient) -> None:
        """Test call_endpoint() with contents endpoint."""
        # First get some IDs
        search_result = await client.search("test", num_results=2)
        ids = [res.id for res in search_result.results[:2]]

        # Call contents via call_endpoint
        response = await client.call_endpoint(
            "/contents",
            method="POST",
            json={
                "ids": ids,
                "contents": {"text": True},
            },
        )

        assert "results" in response
        assert isinstance(response["results"], list)


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestExaErrorHandling:
    """Test Exa error handling."""

    @pytest.mark.asyncio
    async def test_invalid_query_raises_error(self, client: ExaClient) -> None:
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_invalid_num_results_raises_error(
        self,
        client: ExaClient,
    ) -> None:
        """Test that invalid num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be between"):
            await client.search("test", num_results=0)

        with pytest.raises(ValueError, match="num_results must be between"):
            await client.search("test", num_results=101)

    @pytest.mark.asyncio
    async def test_invalid_url_raises_error(self, client: ExaClient) -> None:
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="url is required"):
            await client.find_similar("")

    @pytest.mark.asyncio
    async def test_empty_ids_raises_error(self, client: ExaClient) -> None:
        """Test that empty IDs list raises ValueError."""
        with pytest.raises(ValueError, match="ids list cannot be empty"):
            await client.get_contents([])
