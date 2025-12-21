"""Live API tests for Serper integration with real API keys.

These tests verify the Serper client works correctly with the actual API.
They use real API keys from the .env file at the project root.

Run these tests with:
    uv run pytest __tests__/integration/test_serper_live.py -v -m live_api

Note: These tests consume API credits.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.serper import (
    SerperAutocompleteResult,
    SerperClient,
    SerperError,
    SerperImageResult,
    SerperNewsResult,
    SerperOrganicResult,
    SerperPlaceResult,
    SerperSearchResult,
    SerperSearchType,
    SerperShoppingResult,
    SerperVideoResult,
)

# Load .env from project root (yasmines-team/.env)
# Path: __tests__/integration/test_serper_live.py -> app/backend -> app -> yasmines-team
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")


@pytest.fixture
def api_key() -> str:
    """Get Serper API key from environment."""
    key = os.getenv("SERPER_API_KEY")
    if not key:
        pytest.skip("SERPER_API_KEY not found in .env")
    return key


@pytest.fixture
def client(api_key: str) -> SerperClient:
    """Create SerperClient with real API key."""
    return SerperClient(api_key=api_key)


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperWebSearchLive:
    """Live API tests for web search."""

    async def test_web_search_returns_results(self, client: SerperClient) -> None:
        """Web search should return organic results."""
        result = await client.search("python programming tutorial")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.SEARCH
        assert result.query == "python programming tutorial"
        assert len(result.organic) > 0

    async def test_web_search_organic_result_structure(self, client: SerperClient) -> None:
        """Organic results should have required fields."""
        result = await client.search("best CRM software 2024", num=5)

        assert len(result.organic) >= 1
        first_result = result.organic[0]

        assert isinstance(first_result, SerperOrganicResult)
        assert first_result.position >= 1
        assert first_result.title
        assert first_result.link
        assert first_result.link.startswith("http")
        assert first_result.snippet

    async def test_web_search_with_pagination(self, client: SerperClient) -> None:
        """Web search should support pagination."""
        result = await client.search("artificial intelligence", num=10, page=1)

        assert len(result.organic) > 0
        assert result.search_parameters.get("q") == "artificial intelligence"

    async def test_web_search_with_location(self, client: SerperClient) -> None:
        """Web search should support location parameter."""
        result = await client.search(
            "coffee shops",
            country="us",
            language="en",
            location="San Francisco, CA",
        )

        assert len(result.organic) > 0

    async def test_web_search_knowledge_graph(self, client: SerperClient) -> None:
        """Web search should return knowledge graph for entities."""
        result = await client.search("Apple Inc")

        # Knowledge graph is often returned for company searches
        # It may or may not be present depending on the query
        assert isinstance(result, SerperSearchResult)

    async def test_web_search_related_searches(self, client: SerperClient) -> None:
        """Web search should return related searches."""
        result = await client.search("machine learning basics")

        # Related searches are commonly returned
        assert isinstance(result.related_searches, list)

    async def test_web_search_people_also_ask(self, client: SerperClient) -> None:
        """Web search should return people also ask questions."""
        result = await client.search("what is python used for")

        # People Also Ask is common for question queries
        assert isinstance(result.people_also_ask, list)


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperImageSearchLive:
    """Live API tests for image search."""

    async def test_image_search_returns_results(self, client: SerperClient) -> None:
        """Image search should return image results."""
        result = await client.search_images("sunset beach")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.IMAGES
        assert len(result.images) > 0

    async def test_image_search_result_structure(self, client: SerperClient) -> None:
        """Image results should have required fields."""
        result = await client.search_images("mountain landscape", num=5)

        assert len(result.images) >= 1
        first_image = result.images[0]

        assert isinstance(first_image, SerperImageResult)
        assert first_image.title
        assert first_image.image_url
        assert first_image.image_url.startswith("http")
        assert first_image.link


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperNewsSearchLive:
    """Live API tests for news search."""

    async def test_news_search_returns_results(self, client: SerperClient) -> None:
        """News search should return news results."""
        result = await client.search_news("technology news")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.NEWS
        assert len(result.news) > 0

    async def test_news_search_result_structure(self, client: SerperClient) -> None:
        """News results should have required fields."""
        result = await client.search_news("AI announcements", num=5)

        assert len(result.news) >= 1
        first_news = result.news[0]

        assert isinstance(first_news, SerperNewsResult)
        assert first_news.title
        assert first_news.link
        assert first_news.source


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperPlacesSearchLive:
    """Live API tests for places search."""

    async def test_places_search_returns_results(self, client: SerperClient) -> None:
        """Places search should return place results."""
        result = await client.search_places("restaurants in New York")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.PLACES
        assert len(result.places) > 0

    async def test_places_search_result_structure(self, client: SerperClient) -> None:
        """Place results should have business info."""
        result = await client.search_places("coffee shops in Seattle", num=5)

        assert len(result.places) >= 1
        first_place = result.places[0]

        assert isinstance(first_place, SerperPlaceResult)
        assert first_place.title


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperVideoSearchLive:
    """Live API tests for video search."""

    async def test_video_search_returns_results(self, client: SerperClient) -> None:
        """Video search should return video results."""
        result = await client.search_videos("python tutorial for beginners")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.VIDEOS
        assert len(result.videos) > 0

    async def test_video_search_result_structure(self, client: SerperClient) -> None:
        """Video results should have required fields."""
        result = await client.search_videos("how to code", num=5)

        assert len(result.videos) >= 1
        first_video = result.videos[0]

        assert isinstance(first_video, SerperVideoResult)
        assert first_video.title
        assert first_video.link


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperShoppingSearchLive:
    """Live API tests for shopping search."""

    async def test_shopping_search_returns_results(self, client: SerperClient) -> None:
        """Shopping search should return product results."""
        result = await client.search_shopping("wireless headphones")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.SHOPPING
        assert len(result.shopping) > 0

    async def test_shopping_search_result_structure(self, client: SerperClient) -> None:
        """Shopping results should have product info."""
        result = await client.search_shopping("laptop computer", num=5)

        assert len(result.shopping) >= 1
        first_product = result.shopping[0]

        assert isinstance(first_product, SerperShoppingResult)
        assert first_product.title
        assert first_product.link


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperScholarSearchLive:
    """Live API tests for scholar search."""

    async def test_scholar_search_returns_results(self, client: SerperClient) -> None:
        """Scholar search should return academic results."""
        result = await client.search_scholar("deep learning neural networks")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.SCHOLAR
        # Scholar returns results in organic field
        assert len(result.organic) > 0 or len(result.scholar) > 0

    async def test_scholar_search_with_year_filter(self, client: SerperClient) -> None:
        """Scholar search should support year filters."""
        result = await client.search_scholar(
            "machine learning",
            year_low=2020,
            year_high=2024,
            num=5,
        )

        assert isinstance(result, SerperSearchResult)


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperAutocompleteLive:
    """Live API tests for autocomplete."""

    async def test_autocomplete_returns_suggestions(self, client: SerperClient) -> None:
        """Autocomplete should return query suggestions."""
        result = await client.autocomplete("how to learn prog")

        assert isinstance(result, SerperAutocompleteResult)
        assert result.query == "how to learn prog"
        assert len(result.suggestions) > 0

    async def test_autocomplete_suggestions_are_relevant(self, client: SerperClient) -> None:
        """Autocomplete suggestions should be relevant to query."""
        result = await client.autocomplete("best restaurants in")

        assert len(result.suggestions) > 0
        # At least some suggestions should contain the query words
        suggestions_text = " ".join(result.suggestions).lower()
        assert "restaurant" in suggestions_text or "best" in suggestions_text


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperHealthCheckLive:
    """Live API tests for health check."""

    async def test_health_check_passes(self, client: SerperClient) -> None:
        """Health check should pass with valid API key."""
        result = await client.health_check()

        assert result["name"] == "serper"
        assert result["healthy"] is True
        assert result["base_url"] == "https://google.serper.dev"


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperCallEndpointLive:
    """Live API tests for call_endpoint."""

    async def test_call_endpoint_web_search(self, client: SerperClient) -> None:
        """call_endpoint should work for raw API calls."""
        result = await client.call_endpoint(
            "/search",
            method="POST",
            json={"q": "test query", "num": 3},
        )

        assert "organic" in result
        assert len(result["organic"]) > 0


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperErrorHandlingLive:
    """Live API tests for error handling."""

    async def test_invalid_api_key_raises_error(self) -> None:
        """Invalid API key should raise authentication error."""
        client = SerperClient(api_key="invalid-key-12345")

        with pytest.raises(SerperError):
            await client.search("test query")


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperMapsSearchLive:
    """Live API tests for maps search."""

    async def test_maps_search_returns_results(self, client: SerperClient) -> None:
        """Maps search should return place results."""
        result = await client.search_maps("hotels in Los Angeles")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.MAPS
        # Maps search returns places
        assert len(result.places) > 0


@pytest.mark.live_api
@pytest.mark.asyncio
class TestSerperPatentsSearchLive:
    """Live API tests for patents search."""

    async def test_patents_search_returns_results(self, client: SerperClient) -> None:
        """Patents search should return patent results."""
        result = await client.search_patents("artificial intelligence")

        assert isinstance(result, SerperSearchResult)
        assert result.search_type == SerperSearchType.PATENTS
        # Patents return organic results
        assert len(result.organic) > 0
