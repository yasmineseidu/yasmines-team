"""
Serper API integration client.

Provides Google Search API capabilities for web, image, news, places,
maps, videos, shopping, scholar, and patents search.

API Documentation: https://serper.dev/
Base URL: https://google.serper.dev

Features:
- Web search with organic results, knowledge graph, answer box
- Image search with thumbnails and source URLs
- News search with publication metadata
- Places/local search with business info
- Maps search with location data
- Video search with YouTube integration
- Shopping search with prices and retailers
- Scholar search for academic papers
- Patents search for intellectual property
- Autocomplete suggestions

Pricing:
- Free: 2,500 queries included
- $0.30 - $1.00 per 1,000 queries depending on tier
- Credits valid for 6 months

Rate Limits:
- Starter: 50 QPS
- Standard: 100 QPS
- Scale: 200 QPS
- Ultimate: 300 QPS

Example:
    >>> from src.integrations.serper import SerperClient
    >>> client = SerperClient(api_key="your-api-key")
    >>> result = await client.search("best CRM software 2024")
    >>> for item in result.organic:
    ...     print(f"{item.title}: {item.link}")
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class SerperSearchType(str, Enum):
    """Types of searches supported by Serper API."""

    SEARCH = "search"
    IMAGES = "images"
    NEWS = "news"
    PLACES = "places"
    MAPS = "maps"
    VIDEOS = "videos"
    SHOPPING = "shopping"
    SCHOLAR = "scholar"
    PATENTS = "patents"
    AUTOCOMPLETE = "autocomplete"


class SerperError(IntegrationError):
    """Serper-specific error."""

    pass


@dataclass
class SerperOrganicResult:
    """Single organic search result from Serper."""

    position: int
    title: str
    link: str
    snippet: str
    displayed_link: str | None = None
    date: str | None = None
    sitelinks: list[dict[str, str]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperKnowledgeGraph:
    """Knowledge graph data from Google search."""

    title: str | None
    type: str | None
    description: str | None
    website: str | None
    image_url: str | None
    attributes: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperAnswerBox:
    """Answer box / featured snippet from Google search."""

    snippet: str | None
    title: str | None
    link: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperPeopleAlsoAsk:
    """People Also Ask question from Google search."""

    question: str
    snippet: str | None
    title: str | None
    link: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperRelatedSearch:
    """Related search suggestion from Google."""

    query: str


@dataclass
class SerperImageResult:
    """Image search result from Serper."""

    position: int
    title: str
    image_url: str
    source: str
    link: str
    thumbnail_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperNewsResult:
    """News search result from Serper."""

    position: int
    title: str
    link: str
    snippet: str
    source: str
    date: str | None = None
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperPlaceResult:
    """Places/local search result from Serper."""

    position: int
    title: str
    address: str | None
    rating: float | None
    reviews_count: int | None
    phone: str | None
    website: str | None
    category: str | None
    latitude: float | None = None
    longitude: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperVideoResult:
    """Video search result from Serper."""

    position: int
    title: str
    link: str
    snippet: str | None
    duration: str | None
    channel: str | None
    date: str | None
    thumbnail_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperShoppingResult:
    """Shopping search result from Serper."""

    position: int
    title: str
    link: str
    price: str | None
    source: str | None
    rating: float | None
    reviews_count: int | None
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperScholarResult:
    """Scholar/academic search result from Serper."""

    position: int
    title: str
    link: str
    snippet: str
    publication_info: str | None
    cited_by_count: int | None
    cited_by_link: str | None
    related_articles_link: str | None
    pdf_link: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperSearchResult:
    """Complete search result from Serper web search."""

    query: str
    search_type: SerperSearchType
    organic: list[SerperOrganicResult] = field(default_factory=list)
    knowledge_graph: SerperKnowledgeGraph | None = None
    answer_box: SerperAnswerBox | None = None
    people_also_ask: list[SerperPeopleAlsoAsk] = field(default_factory=list)
    related_searches: list[SerperRelatedSearch] = field(default_factory=list)
    images: list[SerperImageResult] = field(default_factory=list)
    news: list[SerperNewsResult] = field(default_factory=list)
    places: list[SerperPlaceResult] = field(default_factory=list)
    videos: list[SerperVideoResult] = field(default_factory=list)
    shopping: list[SerperShoppingResult] = field(default_factory=list)
    scholar: list[SerperScholarResult] = field(default_factory=list)
    credits_used: int = 1
    search_parameters: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerperAutocompleteResult:
    """Autocomplete suggestions from Serper."""

    query: str
    suggestions: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


class SerperClient(BaseIntegrationClient):
    """
    Serper API client for Google Search data.

    Provides access to Google Search, Images, News, Places, Maps,
    Videos, Shopping, Scholar, Patents, and Autocomplete APIs.

    Example:
        >>> async with SerperClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.search("AI startups 2024")
        ...     for r in result.organic[:5]:
        ...         print(f"{r.position}. {r.title}")
        ...     if result.knowledge_graph:
        ...         print(f"KG: {result.knowledge_graph.title}")
    """

    BASE_URL = "https://google.serper.dev"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Serper client.

        Args:
            api_key: Serper API key from serper.dev dashboard
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="serper",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Serper API requests.

        Note: Serper uses X-API-KEY header instead of Bearer token.
        """
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def search(
        self,
        query: str,
        *,
        num: int = 10,
        page: int = 1,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
        time_period: str | None = None,
        safe_search: bool = True,
    ) -> SerperSearchResult:
        """
        Perform a web search using Google Search API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            page: Page number for pagination (default 1)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            location: Specific location for local results
            time_period: Time filter (qdr:h, qdr:d, qdr:w, qdr:m, qdr:y)
            safe_search: Enable safe search filtering (default True)

        Returns:
            SerperSearchResult with organic results, knowledge graph, etc.

        Raises:
            SerperError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required")
        if not 1 <= num <= 100:
            raise ValueError("num must be between 1 and 100")
        if page < 1:
            raise ValueError("page must be >= 1")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if page > 1:
            payload["page"] = page

        if location:
            payload["location"] = location

        if time_period:
            payload["tbs"] = time_period

        if not safe_search:
            payload["safe"] = "off"

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.SEARCH, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Web search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_images(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        safe_search: bool = True,
    ) -> SerperSearchResult:
        """
        Perform an image search using Google Images API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safe_search: Enable safe search filtering (default True)

        Returns:
            SerperSearchResult with images list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if not safe_search:
            payload["safe"] = "off"

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/images",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.IMAGES, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Image search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_news(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        time_period: str | None = None,
    ) -> SerperSearchResult:
        """
        Perform a news search using Google News API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            time_period: Time filter (qdr:h, qdr:d, qdr:w, qdr:m, qdr:y)

        Returns:
            SerperSearchResult with news list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if time_period:
            payload["tbs"] = time_period

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/news",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.NEWS, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"News search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_places(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
    ) -> SerperSearchResult:
        """
        Perform a places/local search using Google Places API.

        Args:
            query: Search query string (e.g., "coffee shops near me")
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            location: Specific location for local results

        Returns:
            SerperSearchResult with places list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if location:
            payload["location"] = location

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/places",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.PLACES, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Places search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_maps(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
    ) -> SerperSearchResult:
        """
        Perform a maps search using Google Maps API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            location: Specific location for local results

        Returns:
            SerperSearchResult with places list populated (maps returns places)

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if location:
            payload["location"] = location

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/maps",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.MAPS, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Maps search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_videos(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> SerperSearchResult:
        """
        Perform a video search using Google Videos API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")

        Returns:
            SerperSearchResult with videos list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/videos",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.VIDEOS, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Video search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_shopping(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> SerperSearchResult:
        """
        Perform a shopping search using Google Shopping API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")

        Returns:
            SerperSearchResult with shopping list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
            "hl": language.lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/shopping",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.SHOPPING, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Shopping search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_scholar(
        self,
        query: str,
        *,
        num: int = 10,
        year_low: int | None = None,
        year_high: int | None = None,
    ) -> SerperSearchResult:
        """
        Perform a scholar/academic search using Google Scholar API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            year_low: Minimum publication year filter
            year_high: Maximum publication year filter

        Returns:
            SerperSearchResult with scholar list populated

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
        }

        if year_low:
            payload["as_ylo"] = year_low
        if year_high:
            payload["as_yhi"] = year_high

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/scholar",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.SCHOLAR, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Scholar search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_patents(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
    ) -> SerperSearchResult:
        """
        Perform a patents search using Google Patents API.

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: Country code for patent jurisdiction (default "us")

        Returns:
            SerperSearchResult with organic list populated (patents as organic)

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "num": num,
            "gl": country.lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/patents",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_search_result(query, SerperSearchType.PATENTS, response)
        except IntegrationError as e:
            raise SerperError(
                message=f"Patents search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def autocomplete(
        self,
        query: str,
        *,
        country: str = "us",
        language: str = "en",
    ) -> SerperAutocompleteResult:
        """
        Get autocomplete suggestions for a search query.

        Args:
            query: Partial search query string
            country: Country code for localized suggestions (default "us")
            language: Language code for suggestions (default "en")

        Returns:
            SerperAutocompleteResult with list of suggestions

        Raises:
            SerperError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        payload: dict[str, Any] = {
            "q": query.strip(),
            "gl": country.lower(),
            "hl": language.lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/autocomplete",
                json=payload,
                headers=self._get_headers(),
            )

            suggestions: list[str] = []
            if "suggestions" in response:
                suggestions = [
                    s.get("value", s) if isinstance(s, dict) else s for s in response["suggestions"]
                ]

            return SerperAutocompleteResult(
                query=query,
                suggestions=suggestions,
                raw_response=response,
            )
        except IntegrationError as e:
            raise SerperError(
                message=f"Autocomplete failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Serper API health and connectivity.

        Performs a minimal search to verify API connectivity.

        Returns:
            Dictionary with health status

        Raises:
            SerperError: If health check fails
        """
        try:
            # Perform minimal search to check connectivity
            await self.search("test", num=1)
            return {
                "name": "serper",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "serper",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "POST",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Serper API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search")
            method: HTTP method (default POST)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            SerperError: If request fails
        """
        if "headers" not in kwargs:
            kwargs["headers"] = self._get_headers()

        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise SerperError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_search_result(
        self,
        query: str,
        search_type: SerperSearchType,
        response: dict[str, Any],
    ) -> SerperSearchResult:
        """
        Parse API response into SerperSearchResult.

        Args:
            query: Original search query
            search_type: Type of search performed
            response: Raw API response

        Returns:
            SerperSearchResult dataclass with all parsed data
        """
        result = SerperSearchResult(
            query=query,
            search_type=search_type,
            search_parameters=response.get("searchParameters", {}),
            raw_response=response,
        )

        # Parse organic results
        for item in response.get("organic", []):
            result.organic.append(
                SerperOrganicResult(
                    position=item.get("position", len(result.organic) + 1),
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    displayed_link=item.get("displayedLink"),
                    date=item.get("date"),
                    sitelinks=item.get("sitelinks", []),
                    raw=item,
                )
            )

        # Parse knowledge graph
        kg = response.get("knowledgeGraph")
        if kg:
            result.knowledge_graph = SerperKnowledgeGraph(
                title=kg.get("title"),
                type=kg.get("type"),
                description=kg.get("description"),
                website=kg.get("website"),
                image_url=kg.get("imageUrl"),
                attributes=kg.get("attributes", {}),
                raw=kg,
            )

        # Parse answer box
        ab = response.get("answerBox")
        if ab:
            result.answer_box = SerperAnswerBox(
                snippet=ab.get("snippet") or ab.get("answer"),
                title=ab.get("title"),
                link=ab.get("link"),
                raw=ab,
            )

        # Parse people also ask
        for paa in response.get("peopleAlsoAsk", []):
            result.people_also_ask.append(
                SerperPeopleAlsoAsk(
                    question=paa.get("question", ""),
                    snippet=paa.get("snippet"),
                    title=paa.get("title"),
                    link=paa.get("link"),
                    raw=paa,
                )
            )

        # Parse related searches
        for rs in response.get("relatedSearches", []):
            query_text = rs.get("query", "") if isinstance(rs, dict) else str(rs)
            result.related_searches.append(SerperRelatedSearch(query=query_text))

        # Parse images
        for img in response.get("images", []):
            result.images.append(
                SerperImageResult(
                    position=img.get("position", len(result.images) + 1),
                    title=img.get("title", ""),
                    image_url=img.get("imageUrl", ""),
                    source=img.get("source", ""),
                    link=img.get("link", ""),
                    thumbnail_url=img.get("thumbnailUrl"),
                    raw=img,
                )
            )

        # Parse news
        for news in response.get("news", []):
            result.news.append(
                SerperNewsResult(
                    position=news.get("position", len(result.news) + 1),
                    title=news.get("title", ""),
                    link=news.get("link", ""),
                    snippet=news.get("snippet", ""),
                    source=news.get("source", ""),
                    date=news.get("date"),
                    image_url=news.get("imageUrl"),
                    raw=news,
                )
            )

        # Parse places (from places or maps search)
        for place in response.get("places", []):
            result.places.append(
                SerperPlaceResult(
                    position=place.get("position", len(result.places) + 1),
                    title=place.get("title", ""),
                    address=place.get("address"),
                    rating=place.get("rating"),
                    reviews_count=place.get("reviewsCount") or place.get("reviews"),
                    phone=place.get("phone") or place.get("phoneNumber"),
                    website=place.get("website"),
                    category=place.get("category") or place.get("type"),
                    latitude=place.get("latitude") or place.get("lat"),
                    longitude=place.get("longitude") or place.get("lng"),
                    raw=place,
                )
            )

        # Parse videos
        for video in response.get("videos", []):
            result.videos.append(
                SerperVideoResult(
                    position=video.get("position", len(result.videos) + 1),
                    title=video.get("title", ""),
                    link=video.get("link", ""),
                    snippet=video.get("snippet"),
                    duration=video.get("duration"),
                    channel=video.get("channel"),
                    date=video.get("date"),
                    thumbnail_url=video.get("thumbnailUrl") or video.get("thumbnail"),
                    raw=video,
                )
            )

        # Parse shopping
        for shop in response.get("shopping", []):
            result.shopping.append(
                SerperShoppingResult(
                    position=shop.get("position", len(result.shopping) + 1),
                    title=shop.get("title", ""),
                    link=shop.get("link", ""),
                    price=shop.get("price"),
                    source=shop.get("source"),
                    rating=shop.get("rating"),
                    reviews_count=shop.get("reviewsCount") or shop.get("reviews"),
                    image_url=shop.get("imageUrl") or shop.get("thumbnail"),
                    raw=shop,
                )
            )

        # Parse scholar/academic results
        for scholar in (
            response.get("organic", []) if search_type == SerperSearchType.SCHOLAR else []
        ):
            result.scholar.append(
                SerperScholarResult(
                    position=scholar.get("position", len(result.scholar) + 1),
                    title=scholar.get("title", ""),
                    link=scholar.get("link", ""),
                    snippet=scholar.get("snippet", ""),
                    publication_info=scholar.get("publicationInfo") or scholar.get("publication"),
                    cited_by_count=scholar.get("citedByCount") or scholar.get("citedBy"),
                    cited_by_link=scholar.get("citedByLink"),
                    related_articles_link=scholar.get("relatedArticlesLink"),
                    pdf_link=scholar.get("pdfLink"),
                    raw=scholar,
                )
            )

        return result
