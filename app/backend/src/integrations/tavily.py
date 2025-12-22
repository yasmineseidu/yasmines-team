"""
Tavily API integration client.

Provides AI-powered search and research capabilities with context extraction,
competitive analysis, and market research features.

API Documentation: https://docs.tavily.com/documentation/api-reference/endpoint/search
Base URL: https://api.tavily.com

Features:
- Web search optimized for LLMs with relevance scoring
- Context extraction from search results
- Source reliability scoring
- Multi-domain search with include/exclude filters
- Time-range filtering (day, week, month, year)
- Topic-specific search (general, news, finance)
- Raw content extraction (markdown, text)
- Image search integration
- Research report generation
- Competitive analysis

Pricing:
- Free (Researcher): 1,000 API credits/month, 100 RPM
- Project ($30/month): 4,000 API credits/month, 1,000 RPM
- Credits: basic search (1 credit), advanced search (2 credits)
- Credits reset monthly on 1st day

Rate Limits:
- Development: 100 requests/minute
- Production: 1,000 requests/minute
- Crawl endpoint: Separate rate limit applies

Example:
    >>> from src.integrations.tavily import TavilyClient
    >>> client = TavilyClient(api_key="tvly-your-api-key")  # pragma: allowlist secret
    >>> result = await client.search("AI SaaS market trends 2025")
    >>> for item in result.results[:3]:
    ...     print(f"{item.title}: {item.score:.2f}")
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


class TavilyTopic(str, Enum):
    """Topic types for Tavily search."""

    GENERAL = "general"
    NEWS = "news"
    FINANCE = "finance"


class TavilySearchDepth(str, Enum):
    """Search depth options (affects credit cost)."""

    BASIC = "basic"  # 1 credit
    ADVANCED = "advanced"  # 2 credits


class TavilyTimeRange(str, Enum):
    """Time range filters for search results."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    # Abbreviated forms
    D = "d"
    W = "w"
    M = "m"
    Y = "y"


class TavilyError(IntegrationError):
    """Tavily-specific error."""

    pass


@dataclass
class TavilySearchResult:
    """Single search result from Tavily."""

    title: str
    url: str
    content: str
    score: float  # Relevance score 0-1
    favicon: str | None = None
    published_date: str | None = None
    raw_content: str | None = None  # Full content if requested
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TavilyImage:
    """Image result from Tavily search."""

    url: str
    description: str | None = None


@dataclass
class TavilyAnswer:
    """AI-generated answer from Tavily."""

    text: str
    answer_type: str  # "basic" or "advanced"


@dataclass
class TavilySearchResponse:
    """Complete search response from Tavily."""

    query: str
    results: list[TavilySearchResult] = field(default_factory=list)
    answer: TavilyAnswer | None = None
    images: list[TavilyImage] = field(default_factory=list)
    response_time: float = 0.0
    credits_used: int = 1
    request_id: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class TavilyClient(BaseIntegrationClient):
    """
    Tavily API client for AI-powered search and research.

    Provides optimized search for LLMs with built-in relevance scoring,
    context extraction, and source reliability analysis.

    Example:
        >>> async with TavilyClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.search("best CRM 2024", max_results=5)
        ...     for r in result.results:
        ...         print(f"{r.title} (score: {r.score:.2f})")
        ...     if result.answer:
        ...         print(f"Answer: {result.answer.text}")
    """

    BASE_URL = "https://api.tavily.com"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        enable_caching: bool = True,
        cache_ttl: int = 86400,  # 24 hours
    ) -> None:
        """
        Initialize Tavily client.

        Args:
            api_key: Tavily API key from tavily.com dashboard (starts with "tvly-")
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
            enable_caching: Enable result caching to save credits (default True)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
        """
        super().__init__(
            name="tavily",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[TavilySearchResponse, datetime]] = {}

    def _get_cache_key(self, **params: Any) -> str:
        """
        Generate cache key from search parameters.

        Args:
            **params: Search parameters

        Returns:
            Cache key string
        """
        # Sort params for consistent keys
        sorted_params = sorted(params.items())
        return str(sorted_params)

    def _get_cached_result(self, cache_key: str) -> TavilySearchResponse | None:
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
            logger.debug(
                f"[{self.name}] Cache hit for {cache_key} (age: {age.total_seconds():.0f}s)"
            )
            return cached_result

        # Expired - remove from cache
        del self._cache[cache_key]
        logger.debug(f"[{self.name}] Cache expired for {cache_key}")
        return None

    def _cache_result(self, cache_key: str, result: TavilySearchResponse) -> None:
        """
        Cache search result.

        Args:
            cache_key: Cache key
            result: Search result to cache
        """
        if self.enable_caching:
            self._cache[cache_key] = (result, datetime.now())
            logger.debug(f"[{self.name}] Cached result for {cache_key}")

    async def search(
        self,
        query: str,
        *,
        topic: TavilyTopic | str = TavilyTopic.GENERAL,
        search_depth: TavilySearchDepth | str = TavilySearchDepth.BASIC,
        max_results: int = 5,
        time_range: TavilyTimeRange | str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_answer: bool | str = False,
        include_raw_content: bool | str = False,
        include_images: bool = False,
        include_favicon: bool = True,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        country: str | None = None,
    ) -> TavilySearchResponse:
        """
        Perform AI-powered web search.

        Args:
            query: Search query string
            topic: Search topic (general, news, finance)
            search_depth: basic (1 credit) or advanced (2 credits)
            max_results: Number of results to return (0-20, default 5)
            time_range: Time filter (day/d, week/w, month/m, year/y)
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            include_answer: Include AI answer (bool, "basic", or "advanced")
            include_raw_content: Include full content (bool, "markdown", or "text")
            include_images: Include related images
            include_favicon: Include favicon URLs (default True)
            include_domains: List of domains to include (max 300)
            exclude_domains: List of domains to exclude (max 150)
            country: Country code for localized results (e.g., "us")

        Returns:
            TavilySearchResponse with ranked results and optional answer

        Raises:
            TavilyError: If API request fails
            ValueError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if not 0 <= max_results <= 20:
            raise ValueError("max_results must be between 0 and 20")

        if include_domains and len(include_domains) > 300:
            raise ValueError("include_domains maximum is 300 domains")

        if exclude_domains and len(exclude_domains) > 150:
            raise ValueError("exclude_domains maximum is 150 domains")

        # Build request payload
        payload: dict[str, Any] = {
            "query": query.strip(),
            "topic": topic.value if isinstance(topic, TavilyTopic) else topic,
            "search_depth": (
                search_depth.value if isinstance(search_depth, TavilySearchDepth) else search_depth
            ),
            "max_results": max_results,
            "include_favicon": include_favicon,
        }

        # Add optional parameters
        if time_range:
            payload["time_range"] = (
                time_range.value if isinstance(time_range, TavilyTimeRange) else time_range
            )

        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date

        if include_answer:
            payload["include_answer"] = include_answer

        if include_raw_content:
            payload["include_raw_content"] = include_raw_content

        if include_images:
            payload["include_images"] = True

        if include_domains:
            payload["include_domains"] = include_domains

        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        if country:
            payload["country"] = country.lower()

        # Check cache
        cache_key = self._get_cache_key(**payload)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        # Make API request
        try:
            response = await self.post("/search", json=payload)
            result = self._parse_search_response(query, response)

            # Cache result
            self._cache_result(cache_key, result)

            return result

        except IntegrationError as e:
            raise TavilyError(
                message=f"Search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def extract(
        self,
        urls: list[str],
        *,
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        """
        Extract content from specific URLs.

        Args:
            urls: List of URLs to extract content from (max 20)
            include_raw_content: Include full raw content

        Returns:
            Dictionary with extracted content per URL

        Raises:
            TavilyError: If API request fails
            ValueError: If parameters are invalid
        """
        if not urls:
            raise ValueError("urls list cannot be empty")

        if len(urls) > 20:
            raise ValueError("Maximum 20 URLs per request")

        payload: dict[str, Any] = {
            "urls": urls,
        }

        if include_raw_content:
            payload["include_raw_content"] = True

        try:
            response = await self.post("/extract", json=payload)
            return response

        except IntegrationError as e:
            raise TavilyError(
                message=f"Content extraction failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def research(
        self,
        query: str,
        *,
        max_iterations: int = 5,
        include_images: bool = False,
    ) -> TavilySearchResponse:
        """
        Perform deep research on a topic with multiple iterations.

        Uses advanced search depth for comprehensive research.

        Args:
            query: Research topic or question
            max_iterations: Maximum research iterations (default 5)
            include_images: Include related images

        Returns:
            TavilySearchResponse with comprehensive research results

        Raises:
            TavilyError: If research fails
        """
        if not 1 <= max_iterations <= 10:
            raise ValueError("max_iterations must be between 1 and 10")

        # Use advanced search depth for research
        return await self.search(
            query=query,
            search_depth=TavilySearchDepth.ADVANCED,
            max_results=10,
            include_answer="advanced",
            include_raw_content="markdown",
            include_images=include_images,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Tavily API health and connectivity.

        Performs a minimal search to verify API connectivity.

        Returns:
            Dictionary with health status

        Raises:
            TavilyError: If health check fails
        """
        try:
            # Perform minimal basic search to check connectivity
            await self.search("test", max_results=1, search_depth=TavilySearchDepth.BASIC)
            return {
                "name": "tavily",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "tavily",
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
        Call any Tavily API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search", "/extract")
            method: HTTP method (default POST)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            TavilyError: If request fails
        """
        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise TavilyError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_search_response(
        self,
        query: str,
        response: dict[str, Any],
    ) -> TavilySearchResponse:
        """
        Parse API response into TavilySearchResponse.

        Args:
            query: Original search query
            response: Raw API response

        Returns:
            TavilySearchResponse dataclass with all parsed data
        """
        result = TavilySearchResponse(
            query=query,
            response_time=response.get("response_time", 0.0),
            request_id=response.get("request_id"),
            raw_response=response,
        )

        # Determine credits used based on usage data or search depth
        usage = response.get("usage", {})
        if "credits_used" in usage:
            result.credits_used = usage["credits_used"]
        else:
            # Fallback: calculate based on search depth
            search_params = response.get("search_parameters", {})
            search_depth = search_params.get("search_depth", "basic")
            result.credits_used = 2 if search_depth == "advanced" else 1

        # Parse search results
        for item in response.get("results", []):
            result.results.append(
                TavilySearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    favicon=item.get("favicon"),
                    published_date=item.get("published_date"),
                    raw_content=item.get("raw_content"),
                    raw=item,
                )
            )

        # Parse answer if present
        if "answer" in response:
            answer_data = response["answer"]
            if isinstance(answer_data, str):
                result.answer = TavilyAnswer(text=answer_data, answer_type="basic")
            elif isinstance(answer_data, dict):
                result.answer = TavilyAnswer(
                    text=answer_data.get("text", ""),
                    answer_type=answer_data.get("type", "basic"),
                )

        # Parse images if present
        for img in response.get("images", []):
            if isinstance(img, str):
                result.images.append(TavilyImage(url=img))
            elif isinstance(img, dict):
                result.images.append(
                    TavilyImage(
                        url=img.get("url", ""),
                        description=img.get("description"),
                    )
                )

        return result

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
