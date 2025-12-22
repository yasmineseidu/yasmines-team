"""
Live integration tests for Brave Search API.

These tests make real API calls to verify functionality against the live Brave API.
Run with: uv run pytest __tests__/integration/test_brave_live.py -v

Requirements:
    - Valid BRAVE_API_KEY in environment or .env file
    - Internet connectivity
    - API credits available

Note: These tests consume API credits. Use sparingly.
"""

import os
from pathlib import Path

import pytest

from src.integrations.brave import (
    BraveClient,
    BraveError,
    BraveFaq,
    BraveFreshness,
    BraveImageResult,
    BraveImageSafesearch,
    BraveInfobox,
    BraveNewsResult,
    BraveSafesearch,
    BraveSearchResponse,
    BraveSearchType,
    BraveSuggestResponse,
    BraveVideoResult,
    BraveWebResult,
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
                        if key and value:
                            os.environ.setdefault(key, value)
            break


# Load .env file
load_env_file()


def get_api_key() -> str | None:
    """Get Brave API key from environment."""
    return os.environ.get("BRAVE_API_KEY")


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not get_api_key(),
    reason="BRAVE_API_KEY not found in environment",
)


# =============================================================================
# SAMPLE TEST DATA
# =============================================================================

# Web search test queries
WEB_SEARCH_SAMPLES = [
    {"query": "artificial intelligence startups 2025", "description": "Tech industry search"},
    {"query": "best CRM software for small business", "description": "B2B software search"},
    {"query": "Python async programming best practices", "description": "Technical search"},
    {
        "query": "climate change solutions renewable energy",
        "description": "General knowledge search",
    },
    {"query": "New York restaurants", "description": "Local search"},
]

# News search test queries
NEWS_SEARCH_SAMPLES = [
    {"query": "AI technology news", "description": "Tech news"},
    {"query": "startup funding announcements", "description": "Business news"},
    {"query": "climate change policy", "description": "Environmental news"},
]

# Image search test queries
IMAGE_SEARCH_SAMPLES = [
    {"query": "golden gate bridge", "description": "Landmark image"},
    {"query": "abstract art patterns", "description": "Art image"},
    {"query": "electric vehicles", "description": "Product image"},
]

# Video search test queries
VIDEO_SEARCH_SAMPLES = [
    {"query": "Python tutorial for beginners", "description": "Educational video"},
    {"query": "cooking pasta recipes", "description": "How-to video"},
    {"query": "TED talks innovation", "description": "Presentation video"},
]

# Suggest/autocomplete test queries
SUGGEST_SAMPLES = [
    {"query": "how to", "description": "Common starter"},
    {"query": "best way to", "description": "Advice starter"},
    {"query": "python", "description": "Tech term"},
]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def client() -> BraveClient:
    """Create a BraveClient with real API key."""
    api_key = get_api_key()
    if not api_key:
        pytest.skip("BRAVE_API_KEY not found")
    return BraveClient(
        api_key=api_key,  # pragma: allowlist secret
        enable_caching=False,  # Don't cache during live tests
    )


@pytest.fixture
async def async_client() -> BraveClient:
    """Create an async context managed BraveClient."""
    api_key = get_api_key()
    if not api_key:
        pytest.skip("BRAVE_API_KEY not found")
    client = BraveClient(
        api_key=api_key,  # pragma: allowlist secret
        enable_caching=False,
    )
    yield client
    await client.close()


# =============================================================================
# WEB SEARCH TESTS
# =============================================================================


class TestWebSearchLive:
    """Live tests for web search endpoint."""

    @pytest.mark.asyncio
    async def test_basic_web_search(self, client: BraveClient) -> None:
        """Basic web search should return valid results."""
        result = await client.search("Python programming language")

        assert isinstance(result, BraveSearchResponse)
        assert result.query == "Python programming language"
        assert result.search_type == BraveSearchType.WEB
        assert len(result.results) > 0
        assert all(isinstance(r, BraveWebResult) for r in result.results)

    @pytest.mark.asyncio
    async def test_web_search_with_count(self, client: BraveClient) -> None:
        """Web search with count parameter should limit results."""
        result = await client.search("machine learning", count=5)

        assert isinstance(result, BraveSearchResponse)
        assert len(result.results) <= 5
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_web_search_with_safesearch(self, client: BraveClient) -> None:
        """Web search with safesearch should work correctly."""
        result = await client.search(
            "technology news",
            safesearch=BraveSafesearch.STRICT,
        )

        assert isinstance(result, BraveSearchResponse)
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_web_search_with_freshness(self, client: BraveClient) -> None:
        """Web search with freshness filter should return recent results."""
        result = await client.search(
            "latest tech news today",
            freshness=BraveFreshness.WEEK,
        )

        assert isinstance(result, BraveSearchResponse)
        # Freshness filter applied - results should be recent

    @pytest.mark.asyncio
    async def test_web_search_result_structure(self, client: BraveClient) -> None:
        """Web search results should have valid structure."""
        result = await client.search("OpenAI GPT")

        assert len(result.results) > 0
        first_result = result.results[0]

        # Verify required fields
        assert first_result.title
        assert first_result.url
        assert first_result.url.startswith("http")
        assert first_result.description

    @pytest.mark.asyncio
    async def test_web_search_infobox(self, client: BraveClient) -> None:
        """Web search for entities should include infobox when available."""
        result = await client.search("Apple Inc company")

        assert isinstance(result, BraveSearchResponse)
        # Infobox may or may not be present depending on query
        if result.infobox:
            assert isinstance(result.infobox, BraveInfobox)
            assert result.infobox.title

    @pytest.mark.asyncio
    async def test_web_search_faqs(self, client: BraveClient) -> None:
        """Web search should include FAQs when available."""
        result = await client.search("how to learn programming")

        assert isinstance(result, BraveSearchResponse)
        # FAQs may or may not be present depending on query
        if result.faqs:
            assert all(isinstance(f, BraveFaq) for f in result.faqs)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", WEB_SEARCH_SAMPLES, ids=lambda s: s["description"])
    async def test_web_search_samples(self, client: BraveClient, sample: dict) -> None:
        """Test web search with various sample queries."""
        result = await client.search(sample["query"], count=5)

        assert isinstance(result, BraveSearchResponse)
        assert len(result.results) > 0, f"No results for: {sample['query']}"

    @pytest.mark.asyncio
    async def test_web_search_localization(self, client: BraveClient) -> None:
        """Web search with country/language settings should work."""
        result = await client.search(
            "weather",
            country="us",
            language="en",
            count=5,
        )

        assert isinstance(result, BraveSearchResponse)
        assert len(result.results) > 0


# =============================================================================
# NEWS SEARCH TESTS
# =============================================================================


class TestNewsSearchLive:
    """Live tests for news search endpoint."""

    @pytest.mark.asyncio
    async def test_basic_news_search(self, client: BraveClient) -> None:
        """Basic news search should return valid results."""
        result = await client.search_news("technology news")

        assert isinstance(result, BraveSearchResponse)
        assert result.search_type == BraveSearchType.NEWS
        assert len(result.news_results) > 0
        assert all(isinstance(r, BraveNewsResult) for r in result.news_results)

    @pytest.mark.asyncio
    async def test_news_search_result_structure(self, client: BraveClient) -> None:
        """News search results should have valid structure."""
        result = await client.search_news("AI companies", count=5)

        assert len(result.news_results) > 0
        first_result = result.news_results[0]

        # Verify required fields
        assert first_result.title
        assert first_result.url
        assert first_result.url.startswith("http")

    @pytest.mark.asyncio
    async def test_news_search_with_freshness(self, client: BraveClient) -> None:
        """News search with freshness filter should return recent news."""
        result = await client.search_news(
            "breaking news",
            freshness=BraveFreshness.DAY,
        )

        assert isinstance(result, BraveSearchResponse)
        # Should return news from past day

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", NEWS_SEARCH_SAMPLES, ids=lambda s: s["description"])
    async def test_news_search_samples(self, client: BraveClient, sample: dict) -> None:
        """Test news search with various sample queries."""
        result = await client.search_news(sample["query"], count=5)

        assert isinstance(result, BraveSearchResponse)
        assert len(result.news_results) > 0, f"No news for: {sample['query']}"


# =============================================================================
# IMAGE SEARCH TESTS
# =============================================================================


class TestImageSearchLive:
    """Live tests for image search endpoint."""

    @pytest.mark.asyncio
    async def test_basic_image_search(self, client: BraveClient) -> None:
        """Basic image search should return valid results."""
        result = await client.search_images("sunset beach")

        assert isinstance(result, BraveSearchResponse)
        assert result.search_type == BraveSearchType.IMAGES
        assert len(result.image_results) > 0
        assert all(isinstance(r, BraveImageResult) for r in result.image_results)

    @pytest.mark.asyncio
    async def test_image_search_result_structure(self, client: BraveClient) -> None:
        """Image search results should have valid structure."""
        result = await client.search_images("mountains landscape", count=10)

        assert len(result.image_results) > 0
        first_result = result.image_results[0]

        # Verify required fields
        assert first_result.title
        assert first_result.url
        assert first_result.thumbnail_url

    @pytest.mark.asyncio
    async def test_image_search_with_safesearch(self, client: BraveClient) -> None:
        """Image search with safesearch should filter content."""
        result = await client.search_images(
            "nature photography",
            safesearch=BraveImageSafesearch.STRICT,
        )

        assert isinstance(result, BraveSearchResponse)
        assert len(result.image_results) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", IMAGE_SEARCH_SAMPLES, ids=lambda s: s["description"])
    async def test_image_search_samples(self, client: BraveClient, sample: dict) -> None:
        """Test image search with various sample queries."""
        result = await client.search_images(sample["query"], count=5)

        assert isinstance(result, BraveSearchResponse)
        assert len(result.image_results) > 0, f"No images for: {sample['query']}"


# =============================================================================
# VIDEO SEARCH TESTS
# =============================================================================


class TestVideoSearchLive:
    """Live tests for video search endpoint."""

    @pytest.mark.asyncio
    async def test_basic_video_search(self, client: BraveClient) -> None:
        """Basic video search should return valid results."""
        result = await client.search_videos("Python tutorial")

        assert isinstance(result, BraveSearchResponse)
        assert result.search_type == BraveSearchType.VIDEOS
        assert len(result.video_results) > 0
        assert all(isinstance(r, BraveVideoResult) for r in result.video_results)

    @pytest.mark.asyncio
    async def test_video_search_result_structure(self, client: BraveClient) -> None:
        """Video search results should have valid structure."""
        result = await client.search_videos("cooking recipes", count=5)

        assert len(result.video_results) > 0
        first_result = result.video_results[0]

        # Verify required fields
        assert first_result.title
        assert first_result.url

    @pytest.mark.asyncio
    async def test_video_search_with_freshness(self, client: BraveClient) -> None:
        """Video search with freshness filter should work."""
        result = await client.search_videos(
            "tech review",
            freshness=BraveFreshness.MONTH,
        )

        assert isinstance(result, BraveSearchResponse)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", VIDEO_SEARCH_SAMPLES, ids=lambda s: s["description"])
    async def test_video_search_samples(self, client: BraveClient, sample: dict) -> None:
        """Test video search with various sample queries."""
        result = await client.search_videos(sample["query"], count=5)

        assert isinstance(result, BraveSearchResponse)
        assert len(result.video_results) > 0, f"No videos for: {sample['query']}"


# =============================================================================
# SUGGEST/AUTOCOMPLETE TESTS
# Note: Suggest endpoint requires a paid plan. Tests skip if not available.
# =============================================================================


async def check_suggest_available(client: BraveClient) -> bool:
    """Check if suggest endpoint is available in the current plan."""
    try:
        await client.suggest("test", count=1)
        return True
    except BraveError as e:
        if "OPTION_NOT_IN_PLAN" in str(e):
            return False
        raise


class TestSuggestLive:
    """Live tests for suggest/autocomplete endpoint."""

    @pytest.mark.asyncio
    async def test_basic_suggest(self, client: BraveClient) -> None:
        """Basic suggest should return suggestions (if available in plan)."""
        try:
            result = await client.suggest("how to learn")

            assert isinstance(result, BraveSuggestResponse)
            assert result.query == "how to learn"
        except BraveError as e:
            if "OPTION_NOT_IN_PLAN" in str(e):
                pytest.skip("Suggest endpoint not available in current API plan")
            raise

    @pytest.mark.asyncio
    async def test_suggest_with_count(self, client: BraveClient) -> None:
        """Suggest with count should limit suggestions (if available in plan)."""
        try:
            result = await client.suggest("python", count=3)

            assert isinstance(result, BraveSuggestResponse)
        except BraveError as e:
            if "OPTION_NOT_IN_PLAN" in str(e):
                pytest.skip("Suggest endpoint not available in current API plan")
            raise

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", SUGGEST_SAMPLES, ids=lambda s: s["description"])
    async def test_suggest_samples(self, client: BraveClient, sample: dict) -> None:
        """Test suggest with various sample queries (if available in plan)."""
        try:
            result = await client.suggest(sample["query"])

            assert isinstance(result, BraveSuggestResponse)
        except BraveError as e:
            if "OPTION_NOT_IN_PLAN" in str(e):
                pytest.skip("Suggest endpoint not available in current API plan")
            raise


# =============================================================================
# FUTURE-PROOF ENDPOINT TESTS
# =============================================================================


class TestCallEndpointLive:
    """Live tests for the future-proof call_endpoint() method."""

    @pytest.mark.asyncio
    async def test_call_endpoint_web_search(self, client: BraveClient) -> None:
        """call_endpoint() should work for web search endpoint."""
        result = await client.call_endpoint(
            "/web/search",
            method="GET",
            params={"q": "test query", "count": 3},
        )

        assert isinstance(result, dict)
        assert "web" in result or "results" in result

    @pytest.mark.asyncio
    async def test_call_endpoint_news_search(self, client: BraveClient) -> None:
        """call_endpoint() should work for news search endpoint."""
        result = await client.call_endpoint(
            "/news/search",
            method="GET",
            params={"q": "technology", "count": 3},
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_call_endpoint_images_search(self, client: BraveClient) -> None:
        """call_endpoint() should work for images search endpoint."""
        result = await client.call_endpoint(
            "/images/search",
            method="GET",
            params={"q": "nature", "count": 3},
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_call_endpoint_videos_search(self, client: BraveClient) -> None:
        """call_endpoint() should work for videos search endpoint."""
        result = await client.call_endpoint(
            "/videos/search",
            method="GET",
            params={"q": "tutorial", "count": 3},
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_call_endpoint_custom_params(self, client: BraveClient) -> None:
        """call_endpoint() should accept custom parameters."""
        result = await client.call_endpoint(
            "/web/search",
            method="GET",
            params={
                "q": "AI",
                "count": 5,
                "country": "us",
                "search_lang": "en",
                "safesearch": "moderate",
            },
        )

        assert isinstance(result, dict)


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthCheckLive:
    """Live tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_passes(self, client: BraveClient) -> None:
        """Health check should pass with valid API key."""
        result = await client.health_check()

        assert result["name"] == "brave"
        assert result["healthy"] is True
        assert result["base_url"] == "https://api.search.brave.com/res/v1"


# =============================================================================
# CONTEXT MANAGER TESTS
# =============================================================================


class TestContextManagerLive:
    """Live tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_search(self) -> None:
        """Context manager should work correctly for searches."""
        api_key = get_api_key()
        if not api_key:
            pytest.skip("BRAVE_API_KEY not found")

        async with BraveClient(
            api_key=api_key, enable_caching=False
        ) as client:  # pragma: allowlist secret
            result = await client.search("test query", count=1)
            assert isinstance(result, BraveSearchResponse)


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandlingLive:
    """Live tests for error handling."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_error(self) -> None:
        """Invalid API key should raise appropriate error."""
        client = BraveClient(
            api_key="invalid-api-key",  # pragma: allowlist secret
            enable_caching=False,
        )

        with pytest.raises(BraveError):
            await client.search("test")

        await client.close()


# =============================================================================
# COMPREHENSIVE ENDPOINT VERIFICATION
# =============================================================================


class TestAllEndpointsPass:
    """Comprehensive test to verify all endpoints pass 100%."""

    @pytest.mark.asyncio
    async def test_all_endpoints_sequential(self, client: BraveClient) -> None:
        """Run all endpoints sequentially to verify 100% pass rate."""
        results = {}
        skipped = []

        # 1. Web Search
        web_result = await client.search("Python programming", count=3)
        results["web_search"] = len(web_result.results) > 0
        assert results["web_search"], "Web search failed to return results"

        # 2. News Search
        news_result = await client.search_news("technology", count=3)
        results["news_search"] = len(news_result.news_results) > 0
        assert results["news_search"], "News search failed to return results"

        # 3. Image Search (uses strict safesearch by default now)
        image_result = await client.search_images("mountains", count=3)
        results["image_search"] = len(image_result.image_results) > 0
        assert results["image_search"], "Image search failed to return results"

        # 4. Video Search
        video_result = await client.search_videos("tutorial", count=3)
        results["video_search"] = len(video_result.video_results) > 0
        assert results["video_search"], "Video search failed to return results"

        # 5. Suggest (may not be available in all plans)
        try:
            suggest_result = await client.suggest("how to")
            results["suggest"] = isinstance(suggest_result, BraveSuggestResponse)
        except BraveError as e:
            if "OPTION_NOT_IN_PLAN" in str(e):
                skipped.append("suggest (not in plan)")
            else:
                raise

        # 6. Health Check
        health_result = await client.health_check()
        results["health_check"] = health_result["healthy"]
        assert results["health_check"], "Health check failed"

        # 7. call_endpoint (future-proof)
        raw_result = await client.call_endpoint(
            "/web/search",
            method="GET",
            params={"q": "test", "count": 1},
        )
        results["call_endpoint"] = isinstance(raw_result, dict)
        assert results["call_endpoint"], "call_endpoint failed"

        # Summary
        print("\n" + "=" * 60)
        print("BRAVE SEARCH API - ALL ENDPOINTS TEST RESULTS")
        print("=" * 60)
        for endpoint, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {endpoint}: {status}")
        if skipped:
            print("\nSkipped (plan limitation):")
            for item in skipped:
                print(f"  ⏭️  {item}")
        print("=" * 60)

        all_passed = all(results.values())
        assert all_passed, f"Some endpoints failed: {results}"
        print(f"\n🎉 ALL {len(results)} TESTED ENDPOINTS PASSED 100%!")
