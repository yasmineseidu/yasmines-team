"""
Brave Search API integration client.

Provides privacy-focused web search with independent results, news search,
image search, video search, and suggest/autocomplete capabilities.

API Documentation: https://brave.com/search/api/
Base URL: https://api.search.brave.com/res/v1

Features:
- Web search with privacy focus (no personal data collection)
- News search with publication metadata
- Image search with thumbnails
- Video search with metadata
- Suggest/autocomplete
- Result filtering by date (freshness)
- Safe search filtering
- Country and language localization
- Source diversity (independent from Google)

Pricing:
- FREE: Up to 2,000 queries/month
- Basic ($5/month): 20,000 queries/month
- Starter ($20/month): 100,000 queries/month
- Pro ($50/month): 500,000 queries/month

Rate Limits:
- Free tier: 1 request/second, 15,000 requests/month
- Paid tiers: Higher limits based on plan

Example:
    >>> from src.integrations.brave import BraveClient
    >>> client = BraveClient(api_key="your-api-key")
    >>> result = await client.search("AI companies hiring 2025")
    >>> for item in result.results[:5]:
    ...     print(f"{item.title}: {item.url}")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class BraveSafesearch(str, Enum):
    """Safe search filtering options."""

    OFF = "off"
    MODERATE = "moderate"  # Note: Not supported for Images API
    STRICT = "strict"


class BraveImageSafesearch(str, Enum):
    """Safe search filtering options for Images API (only off/strict supported)."""

    OFF = "off"
    STRICT = "strict"


class BraveFreshness(str, Enum):
    """Result freshness filters."""

    DAY = "pd"  # Past day
    WEEK = "pw"  # Past week
    MONTH = "pm"  # Past month
    YEAR = "py"  # Past year


class BraveSearchType(str, Enum):
    """Types of searches supported by Brave API."""

    WEB = "web"
    NEWS = "news"
    IMAGES = "images"
    VIDEOS = "videos"
    SUGGEST = "suggest"


class BraveError(IntegrationError):
    """Brave Search API-specific error."""

    pass


@dataclass
class BraveWebResult:
    """Single web search result from Brave."""

    title: str
    url: str
    description: str
    age: str | None = None  # How old the result is (e.g., "2 hours ago")
    page_age: str | None = None  # When the page was last updated
    family_friendly: bool = True
    extra_snippets: list[str] = field(default_factory=list)
    deep_results: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveNewsResult:
    """Single news result from Brave."""

    title: str
    url: str
    description: str
    source: str
    age: str | None = None
    page_age: str | None = None
    thumbnail_url: str | None = None
    meta_url: dict[str, str] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveImageResult:
    """Single image result from Brave."""

    title: str
    url: str
    thumbnail_url: str
    source: str
    page_url: str
    width: int | None = None
    height: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveVideoResult:
    """Single video result from Brave."""

    title: str
    url: str
    description: str | None
    thumbnail_url: str | None
    age: str | None = None
    duration: str | None = None
    creator: str | None = None
    publisher: str | None = None
    views: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveInfobox:
    """Infobox (knowledge panel) from Brave search."""

    title: str
    description: str | None
    type: str | None
    url: str | None = None
    thumbnail_url: str | None = None
    long_desc: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveFaq:
    """FAQ result from Brave search."""

    question: str
    answer: str
    url: str | None = None
    title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveSearchResponse:
    """Complete search response from Brave."""

    query: str
    search_type: BraveSearchType
    results: list[BraveWebResult] = field(default_factory=list)
    news_results: list[BraveNewsResult] = field(default_factory=list)
    image_results: list[BraveImageResult] = field(default_factory=list)
    video_results: list[BraveVideoResult] = field(default_factory=list)
    infobox: BraveInfobox | None = None
    faqs: list[BraveFaq] = field(default_factory=list)
    query_info: dict[str, Any] = field(default_factory=dict)
    response_time: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class BraveSuggestResponse:
    """Suggest/autocomplete response from Brave."""

    query: str
    suggestions: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


class BraveClient(BaseIntegrationClient):
    """
    Brave Search API client for privacy-focused web search.

    Provides independent search results without personal data collection,
    making it ideal for unbiased research and compliance-sensitive applications.

    Example:
        >>> async with BraveClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.search("startup funding news")
        ...     for r in result.results[:5]:
        ...         print(f"{r.title}: {r.url}")
        ...     for news in result.news_results[:3]:
        ...         print(f"News: {news.title} - {news.source}")
    """

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        enable_caching: bool = True,
        cache_ttl: int = 86400,  # 24 hours default
    ) -> None:
        """
        Initialize Brave Search client.

        Args:
            api_key: Brave Search API subscription token
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
            enable_caching: Enable result caching to reduce API calls (default True)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
        """
        super().__init__(
            name="brave",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[BraveSearchResponse | BraveSuggestResponse, datetime]] = {}

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for Brave API requests.

        Note: Brave uses X-Subscription-Token header for authentication.
        """
        return {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

    def _get_cache_key(self, search_type: str, **params: Any) -> str:
        """
        Generate cache key from search parameters.

        Args:
            search_type: Type of search (web, news, images, etc.)
            **params: Search parameters

        Returns:
            Cache key string
        """
        sorted_params = sorted(params.items())
        return f"{search_type}:{sorted_params}"

    def _get_cached_result(
        self, cache_key: str
    ) -> BraveSearchResponse | BraveSuggestResponse | None:
        """
        Retrieve cached result if valid.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached result if found and not expired, None otherwise
        """
        if not self.enable_caching or cache_key not in self._cache:
            return None

        cached_result, cached_time = self._cache[cache_key]
        age = datetime.now() - cached_time

        if age.total_seconds() < self.cache_ttl:
            logger.debug(f"[{self.name}] Cache hit for key (age: {age.total_seconds():.0f}s)")
            return cached_result

        # Expired - remove from cache
        del self._cache[cache_key]
        logger.debug(f"[{self.name}] Cache expired")
        return None

    def _cache_result(
        self, cache_key: str, result: BraveSearchResponse | BraveSuggestResponse
    ) -> None:
        """
        Cache search result.

        Args:
            cache_key: Cache key
            result: Search result to cache
        """
        if self.enable_caching:
            self._cache[cache_key] = (result, datetime.now())
            logger.debug(f"[{self.name}] Cached result")

    async def search(
        self,
        query: str,
        *,
        count: int = 10,
        offset: int = 0,
        country: str = "us",
        language: str = "en",
        safesearch: BraveSafesearch | str = BraveSafesearch.MODERATE,
        freshness: BraveFreshness | str | None = None,
        text_decorations: bool = True,
        spellcheck: bool = True,
        result_filter: str | None = None,
        extra_snippets: bool = False,
    ) -> BraveSearchResponse:
        """
        Perform a web search using Brave Search API.

        Args:
            query: Search query string
            count: Number of results to return (max 20, default 10)
            offset: Pagination offset (default 0)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safesearch: Safe search filter level (off, moderate, strict)
            freshness: Time filter (pd=day, pw=week, pm=month, py=year)
            text_decorations: Include highlighting markers in results
            spellcheck: Enable spellcheck suggestions
            result_filter: Comma-separated result types to include
            extra_snippets: Include additional text snippets

        Returns:
            BraveSearchResponse with web results, infobox, FAQs

        Raises:
            BraveError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if count < 1 or count > 20:
            raise ValueError("count must be between 1 and 20")

        if offset < 0 or offset > 9:
            raise ValueError("offset must be between 0 and 9")

        # Build query parameters
        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "offset": offset,
            "country": country.lower(),
            "search_lang": language.lower(),
            "safesearch": safesearch.value
            if isinstance(safesearch, BraveSafesearch)
            else safesearch,
            "text_decorations": str(text_decorations).lower(),
            "spellcheck": str(spellcheck).lower(),
        }

        if freshness:
            params["freshness"] = (
                freshness.value if isinstance(freshness, BraveFreshness) else freshness
            )

        if result_filter:
            params["result_filter"] = result_filter

        if extra_snippets:
            params["extra_snippets"] = "true"

        # Check cache
        cache_key = self._get_cache_key("web", **params)
        cached = self._get_cached_result(cache_key)
        if cached and isinstance(cached, BraveSearchResponse):
            return cached

        # Make API request
        try:
            response = await self.get("/web/search", params=params)
            result = self._parse_web_response(query, response)

            # Cache result
            self._cache_result(cache_key, result)

            return result

        except IntegrationError as e:
            raise BraveError(
                message=f"Web search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_news(
        self,
        query: str,
        *,
        count: int = 10,
        offset: int = 0,
        country: str = "us",
        language: str = "en",
        safesearch: BraveSafesearch | str = BraveSafesearch.MODERATE,
        freshness: BraveFreshness | str | None = None,
        spellcheck: bool = True,
    ) -> BraveSearchResponse:
        """
        Perform a news search using Brave Search API.

        Args:
            query: Search query string
            count: Number of results to return (max 20, default 10)
            offset: Pagination offset (default 0)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safesearch: Safe search filter level (off, moderate, strict)
            freshness: Time filter (pd=day, pw=week, pm=month, py=year)
            spellcheck: Enable spellcheck suggestions

        Returns:
            BraveSearchResponse with news_results populated

        Raises:
            BraveError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if count < 1 or count > 20:
            raise ValueError("count must be between 1 and 20")

        # Build query parameters
        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "offset": offset,
            "country": country.lower(),
            "search_lang": language.lower(),
            "safesearch": safesearch.value
            if isinstance(safesearch, BraveSafesearch)
            else safesearch,
            "spellcheck": str(spellcheck).lower(),
        }

        if freshness:
            params["freshness"] = (
                freshness.value if isinstance(freshness, BraveFreshness) else freshness
            )

        # Check cache
        cache_key = self._get_cache_key("news", **params)
        cached = self._get_cached_result(cache_key)
        if cached and isinstance(cached, BraveSearchResponse):
            return cached

        try:
            response = await self.get("/news/search", params=params)
            result = self._parse_news_response(query, response)

            self._cache_result(cache_key, result)
            return result

        except IntegrationError as e:
            raise BraveError(
                message=f"News search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_images(
        self,
        query: str,
        *,
        count: int = 10,
        country: str = "us",
        language: str = "en",
        safesearch: BraveImageSafesearch | str = BraveImageSafesearch.STRICT,
        spellcheck: bool = True,
    ) -> BraveSearchResponse:
        """
        Perform an image search using Brave Search API.

        Note: Images API only supports 'off' or 'strict' safesearch values.

        Args:
            query: Search query string
            count: Number of results to return (max 150, default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safesearch: Safe search filter level (off or strict only)
            spellcheck: Enable spellcheck suggestions

        Returns:
            BraveSearchResponse with image_results populated

        Raises:
            BraveError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if count < 1 or count > 150:
            raise ValueError("count must be between 1 and 150")

        # Images API only supports 'off' or 'strict' safesearch
        safesearch_value = (
            safesearch.value if isinstance(safesearch, BraveImageSafesearch) else safesearch
        )
        # Handle BraveSafesearch.MODERATE being passed - default to strict
        if safesearch_value == "moderate":
            safesearch_value = "strict"

        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "country": country.lower(),
            "search_lang": language.lower(),
            "safesearch": safesearch_value,
            "spellcheck": str(spellcheck).lower(),
        }

        # Check cache
        cache_key = self._get_cache_key("images", **params)
        cached = self._get_cached_result(cache_key)
        if cached and isinstance(cached, BraveSearchResponse):
            return cached

        try:
            response = await self.get("/images/search", params=params)
            result = self._parse_images_response(query, response)

            self._cache_result(cache_key, result)
            return result

        except IntegrationError as e:
            raise BraveError(
                message=f"Image search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_videos(
        self,
        query: str,
        *,
        count: int = 10,
        offset: int = 0,
        country: str = "us",
        language: str = "en",
        safesearch: BraveSafesearch | str = BraveSafesearch.MODERATE,
        freshness: BraveFreshness | str | None = None,
        spellcheck: bool = True,
    ) -> BraveSearchResponse:
        """
        Perform a video search using Brave Search API.

        Args:
            query: Search query string
            count: Number of results to return (max 50, default 10)
            offset: Pagination offset (default 0)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safesearch: Safe search filter level (off, moderate, strict)
            freshness: Time filter (pd=day, pw=week, pm=month, py=year)
            spellcheck: Enable spellcheck suggestions

        Returns:
            BraveSearchResponse with video_results populated

        Raises:
            BraveError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if count < 1 or count > 50:
            raise ValueError("count must be between 1 and 50")

        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "offset": offset,
            "country": country.lower(),
            "search_lang": language.lower(),
            "safesearch": safesearch.value
            if isinstance(safesearch, BraveSafesearch)
            else safesearch,
            "spellcheck": str(spellcheck).lower(),
        }

        if freshness:
            params["freshness"] = (
                freshness.value if isinstance(freshness, BraveFreshness) else freshness
            )

        # Check cache
        cache_key = self._get_cache_key("videos", **params)
        cached = self._get_cached_result(cache_key)
        if cached and isinstance(cached, BraveSearchResponse):
            return cached

        try:
            response = await self.get("/videos/search", params=params)
            result = self._parse_videos_response(query, response)

            self._cache_result(cache_key, result)
            return result

        except IntegrationError as e:
            raise BraveError(
                message=f"Video search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def suggest(
        self,
        query: str,
        *,
        count: int = 5,
        country: str = "us",
        language: str = "en",
        rich: bool = False,
    ) -> BraveSuggestResponse:
        """
        Get search suggestions/autocomplete for a query.

        Args:
            query: Partial query string for suggestions
            count: Number of suggestions to return (default 5)
            country: Country code for localized suggestions (default "us")
            language: Language code for suggestions (default "en")
            rich: Include rich suggestions with extra metadata

        Returns:
            BraveSuggestResponse with list of suggestions

        Raises:
            BraveError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "country": country.lower(),
            "lang": language.lower(),
        }

        if rich:
            params["rich"] = "true"

        # Check cache
        cache_key = self._get_cache_key("suggest", **params)
        cached = self._get_cached_result(cache_key)
        if cached and isinstance(cached, BraveSuggestResponse):
            return cached

        try:
            response = await self.get("/suggest/search", params=params)
            result = self._parse_suggest_response(query, response)

            self._cache_result(cache_key, result)
            return result

        except IntegrationError as e:
            raise BraveError(
                message=f"Suggest failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Brave Search API health and connectivity.

        Performs a minimal search to verify API connectivity.

        Returns:
            Dictionary with health status
        """
        try:
            await self.search("test", count=1)
            return {
                "name": "brave",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "brave",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Brave API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/web/search")
            method: HTTP method (default GET)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            BraveError: If request fails
        """
        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise BraveError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_web_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> BraveSearchResponse:
        """
        Parse web search API response.

        Args:
            query: Original search query
            response: Raw API response

        Returns:
            BraveSearchResponse with parsed data
        """
        result = BraveSearchResponse(
            query=query,
            search_type=BraveSearchType.WEB,
            query_info=response.get("query", {}),
            raw_response=response,
        )

        # Parse web results
        web_data = response.get("web", {})
        for item in web_data.get("results", []):
            result.results.append(
                BraveWebResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    age=item.get("age"),
                    page_age=item.get("page_age"),
                    family_friendly=item.get("family_friendly", True),
                    extra_snippets=item.get("extra_snippets", []),
                    deep_results=item.get("deep_results", []),
                    raw=item,
                )
            )

        # Parse infobox if present
        infoboxes = response.get("infobox", {})
        if infoboxes and "results" in infoboxes and infoboxes["results"]:
            ib = infoboxes["results"][0]
            result.infobox = BraveInfobox(
                title=ib.get("title", ""),
                description=ib.get("description"),
                type=ib.get("type"),
                url=ib.get("url"),
                thumbnail_url=ib.get("thumbnail", {}).get("src"),
                long_desc=ib.get("long_desc"),
                attributes={
                    attr.get("label", ""): attr.get("value", "")
                    for attr in ib.get("attributes", [])
                    if isinstance(attr, dict) and "label" in attr
                },
                raw=ib,
            )

        # Parse FAQs if present
        faq_data = response.get("faq", {})
        for item in faq_data.get("results", []):
            result.faqs.append(
                BraveFaq(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    url=item.get("url"),
                    title=item.get("title"),
                    raw=item,
                )
            )

        # Also parse any news mixed into web results
        news_data = response.get("news", {})
        for item in news_data.get("results", []):
            result.news_results.append(
                BraveNewsResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    source=item.get("meta_url", {}).get("hostname", ""),
                    age=item.get("age"),
                    page_age=item.get("page_age"),
                    thumbnail_url=item.get("thumbnail", {}).get("src"),
                    meta_url=item.get("meta_url"),
                    raw=item,
                )
            )

        # Parse videos mixed into web results
        videos_data = response.get("videos", {})
        for item in videos_data.get("results", []):
            result.video_results.append(
                BraveVideoResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description"),
                    thumbnail_url=item.get("thumbnail", {}).get("src"),
                    age=item.get("age"),
                    duration=item.get("video", {}).get("duration"),
                    creator=item.get("video", {}).get("creator"),
                    publisher=item.get("video", {}).get("publisher"),
                    views=item.get("video", {}).get("views"),
                    raw=item,
                )
            )

        return result

    def _parse_news_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> BraveSearchResponse:
        """
        Parse news search API response.

        Args:
            query: Original search query
            response: Raw API response

        Returns:
            BraveSearchResponse with news_results populated
        """
        result = BraveSearchResponse(
            query=query,
            search_type=BraveSearchType.NEWS,
            query_info=response.get("query", {}),
            raw_response=response,
        )

        # Parse news results
        news_data = response.get("results", [])
        for item in news_data:
            result.news_results.append(
                BraveNewsResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    source=item.get("meta_url", {}).get("hostname", ""),
                    age=item.get("age"),
                    page_age=item.get("page_age"),
                    thumbnail_url=item.get("thumbnail", {}).get("src"),
                    meta_url=item.get("meta_url"),
                    raw=item,
                )
            )

        return result

    def _parse_images_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> BraveSearchResponse:
        """
        Parse images search API response.

        Args:
            query: Original search query
            response: Raw API response

        Returns:
            BraveSearchResponse with image_results populated
        """
        result = BraveSearchResponse(
            query=query,
            search_type=BraveSearchType.IMAGES,
            query_info=response.get("query", {}),
            raw_response=response,
        )

        # Parse image results
        images_data = response.get("results", [])
        for item in images_data:
            properties = item.get("properties", {})
            result.image_results.append(
                BraveImageResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    thumbnail_url=item.get("thumbnail", {}).get("src", ""),
                    source=item.get("source", ""),
                    page_url=item.get("page_url", properties.get("url", "")),
                    width=properties.get("width"),
                    height=properties.get("height"),
                    raw=item,
                )
            )

        return result

    def _parse_videos_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> BraveSearchResponse:
        """
        Parse videos search API response.

        Args:
            query: Original search query
            response: Raw API response

        Returns:
            BraveSearchResponse with video_results populated
        """
        result = BraveSearchResponse(
            query=query,
            search_type=BraveSearchType.VIDEOS,
            query_info=response.get("query", {}),
            raw_response=response,
        )

        # Parse video results
        videos_data = response.get("results", [])
        for item in videos_data:
            video_info = item.get("video", {})
            result.video_results.append(
                BraveVideoResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description"),
                    thumbnail_url=item.get("thumbnail", {}).get("src"),
                    age=item.get("age"),
                    duration=video_info.get("duration"),
                    creator=video_info.get("creator"),
                    publisher=video_info.get("publisher"),
                    views=video_info.get("views"),
                    raw=item,
                )
            )

        return result

    def _parse_suggest_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> BraveSuggestResponse:
        """
        Parse suggest API response.

        Args:
            query: Original query
            response: Raw API response (dict format expected)

        Returns:
            BraveSuggestResponse with suggestions
        """
        suggestions: list[str] = []

        # Parse suggestions from dict response format
        # Brave API returns suggestions in a "results" key
        raw_results = response.get("results", [])
        if isinstance(raw_results, list):
            suggestions = [str(s) for s in raw_results if s]

        return BraveSuggestResponse(
            query=query,
            suggestions=suggestions,
            raw_response=response,
        )

    def clear_cache(self) -> int:
        """
        Clear the result cache.

        Returns:
            Number of cache entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[{self.name}] Cleared {count} cache entries")
        return count

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cache cleanup."""
        self.clear_cache()
        await super().__aexit__(exc_type, exc_val, exc_tb)
