"""
Exa (formerly Metaphor) API integration client.

Provides semantic/neural search capabilities for content discovery,
competitive analysis, and market research with AI-powered relevance ranking.

API Documentation: https://docs.exa.ai
Base URL: https://api.exa.ai

Features:
- Semantic search using neural embeddings (understands meaning, not just keywords)
- Similarity search (find content similar to a URL)
- Keyword search (traditional search fallback)
- Auto-search (intelligently chooses between neural and keyword)
- Content extraction from search results (full text, highlights, summary)
- Domain/URL filtering (include/exclude specific sites)
- Date filtering (start/end date ranges)
- Category filtering (company, research paper, news, blog, etc.)
- Livecrawl option for real-time content retrieval

Pricing:
- Free: 1,000 searches/month
- Growth: $99/month for 10,000 searches
- Pro: Custom pricing for higher volume

Rate Limits:
- Default: 10 requests/second
- Higher limits available on paid plans

Example:
    >>> from src.integrations.exa import ExaClient
    >>> client = ExaClient(api_key="your-api-key")  # pragma: allowlist secret
    >>> result = await client.search("AI startup funding trends 2024")
    >>> for item in result.results[:5]:
    ...     print(f"{item.title}: {item.url}")
    >>> # Find similar content
    >>> similar = await client.find_similar("https://techcrunch.com/article")
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


class ExaSearchType(str, Enum):
    """Search type options for Exa."""

    NEURAL = "neural"  # Semantic/embedding-based search
    KEYWORD = "keyword"  # Traditional keyword search
    AUTO = "auto"  # Automatically choose best method


class ExaCategory(str, Enum):
    """Content category filters for Exa search."""

    COMPANY = "company"
    RESEARCH_PAPER = "research paper"
    NEWS = "news"
    LINKEDIN_PROFILE = "linkedin profile"
    GITHUB = "github"
    TWEET = "tweet"
    MOVIE = "movie"
    SONG = "song"
    PERSONAL_SITE = "personal site"
    PDF = "pdf"


class ExaContentType(str, Enum):
    """Content retrieval options."""

    TEXT = "text"  # Full text content
    HIGHLIGHTS = "highlights"  # Key excerpts
    SUMMARY = "summary"  # AI-generated summary


class ExaError(IntegrationError):
    """Exa API-specific error."""

    pass


@dataclass
class ExaHighlight:
    """A highlighted excerpt from a search result."""

    text: str
    score: float | None = None


@dataclass
class ExaSearchResult:
    """Single search result from Exa."""

    id: str
    url: str
    title: str
    score: float | None = None
    published_date: str | None = None
    author: str | None = None
    text: str | None = None  # Full text if requested
    highlights: list[str] = field(default_factory=list)  # Key excerpts if requested
    highlight_scores: list[float] = field(default_factory=list)
    summary: str | None = None  # AI summary if requested
    image: str | None = None
    favicon: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExaAutopromptInfo:
    """Information about autoprompt transformation."""

    original_query: str
    transformed_query: str | None = None


@dataclass
class ExaSearchResponse:
    """Complete search response from Exa."""

    query: str
    search_type: ExaSearchType
    results: list[ExaSearchResult] = field(default_factory=list)
    autoprompt: ExaAutopromptInfo | None = None
    cost_credits: float | None = None
    request_id: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExaContentsResult:
    """Content extraction result from Exa."""

    id: str
    url: str
    title: str
    text: str | None = None
    highlights: list[str] = field(default_factory=list)
    highlight_scores: list[float] = field(default_factory=list)
    summary: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExaContentsResponse:
    """Complete contents response from Exa."""

    results: list[ExaContentsResult] = field(default_factory=list)
    cost_credits: float | None = None
    request_id: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class ExaClient(BaseIntegrationClient):
    """
    Exa API client for semantic search and content discovery.

    Provides neural/semantic search that understands meaning and context,
    enabling more relevant results for complex queries compared to
    traditional keyword-based search.

    Example:
        >>> async with ExaClient(api_key="key") as client:  # pragma: allowlist secret
        ...     # Semantic search
        ...     result = await client.search("companies building AI agents")
        ...     for r in result.results[:5]:
        ...         print(f"{r.title}: {r.url}")
        ...
        ...     # Find similar content
        ...     similar = await client.find_similar("https://example.com/article")
        ...
        ...     # Search with content extraction
        ...     result = await client.search_and_contents(
        ...         "latest AI research papers",
        ...         text=True,
        ...         highlights=True,
        ...     )
    """

    BASE_URL = "https://api.exa.ai"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        enable_caching: bool = True,
        cache_ttl: int = 86400,  # 24 hours
    ) -> None:
        """
        Initialize Exa client.

        Args:
            api_key: Exa API key from dashboard.exa.ai
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
            enable_caching: Enable result caching to save credits (default True)
            cache_ttl: Cache time-to-live in seconds (default 24 hours)
        """
        super().__init__(
            name="exa",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[ExaSearchResponse, datetime]] = {}

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Exa API requests."""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_cache_key(self, **params: Any) -> str:
        """Generate cache key from search parameters."""
        sorted_params = sorted(params.items())
        return str(sorted_params)

    def _get_cached_result(self, cache_key: str) -> ExaSearchResponse | None:
        """Retrieve cached result if valid."""
        if not self.enable_caching or cache_key not in self._cache:
            return None

        cached_result, cached_time = self._cache[cache_key]
        age = datetime.now() - cached_time

        if age.total_seconds() < self.cache_ttl:
            logger.debug(
                f"[{self.name}] Cache hit for {cache_key[:50]}... "
                f"(age: {age.total_seconds():.0f}s)"
            )
            return cached_result

        del self._cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: ExaSearchResponse) -> None:
        """Cache search result."""
        if self.enable_caching:
            self._cache[cache_key] = (result, datetime.now())
            logger.debug(f"[{self.name}] Cached result for {cache_key[:50]}...")

    async def search(
        self,
        query: str,
        *,
        search_type: ExaSearchType | str = ExaSearchType.AUTO,
        num_results: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_crawl_date: str | None = None,
        end_crawl_date: str | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        category: ExaCategory | str | None = None,
        use_autoprompt: bool = False,
        livecrawl: str | None = None,
    ) -> ExaSearchResponse:
        """
        Perform semantic search using Exa.

        Args:
            query: Natural language search query
            search_type: "neural" (semantic), "keyword", or "auto" (default)
            num_results: Number of results to return (1-100, default 10)
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains
            start_crawl_date: Filter by crawl date (ISO format: YYYY-MM-DD)
            end_crawl_date: Filter by crawl date (ISO format: YYYY-MM-DD)
            start_published_date: Filter by publish date (ISO format: YYYY-MM-DD)
            end_published_date: Filter by publish date (ISO format: YYYY-MM-DD)
            category: Filter by content category (company, news, research paper, etc.)
            use_autoprompt: Enhance query using AI (improves neural search)
            livecrawl: Enable real-time crawling ("always", "fallback", or None)

        Returns:
            ExaSearchResponse with ranked search results

        Raises:
            ExaError: If API request fails
            ValueError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if not 1 <= num_results <= 100:
            raise ValueError("num_results must be between 1 and 100")

        payload: dict[str, Any] = {
            "query": query.strip(),
            "numResults": num_results,
            "type": (search_type.value if isinstance(search_type, ExaSearchType) else search_type),
        }

        if include_domains:
            payload["includeDomains"] = include_domains

        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        if start_crawl_date:
            payload["startCrawlDate"] = start_crawl_date

        if end_crawl_date:
            payload["endCrawlDate"] = end_crawl_date

        if start_published_date:
            payload["startPublishedDate"] = start_published_date

        if end_published_date:
            payload["endPublishedDate"] = end_published_date

        if category:
            payload["category"] = category.value if isinstance(category, ExaCategory) else category

        if use_autoprompt:
            payload["useAutoprompt"] = True

        if livecrawl:
            payload["livecrawl"] = livecrawl

        # Check cache
        cache_key = self._get_cache_key(**payload)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        try:
            response = await self.post("/search", json=payload)
            search_type_enum = (
                search_type
                if isinstance(search_type, ExaSearchType)
                else ExaSearchType(search_type)
            )
            result = self._parse_search_response(query, search_type_enum, response)
            self._cache_result(cache_key, result)
            return result

        except IntegrationError as e:
            raise ExaError(
                message=f"Search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_crawl_date: str | None = None,
        end_crawl_date: str | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        category: ExaCategory | str | None = None,
        exclude_source_domain: bool = True,
    ) -> ExaSearchResponse:
        """
        Find content similar to a given URL.

        Uses Exa's neural embeddings to find semantically similar content
        based on the content at the provided URL.

        Args:
            url: URL to find similar content for
            num_results: Number of results to return (1-100, default 10)
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains
            start_crawl_date: Filter by crawl date (ISO format)
            end_crawl_date: Filter by crawl date (ISO format)
            start_published_date: Filter by publish date (ISO format)
            end_published_date: Filter by publish date (ISO format)
            category: Filter by content category
            exclude_source_domain: Exclude source URL's domain from results (default True)

        Returns:
            ExaSearchResponse with similar content results

        Raises:
            ExaError: If API request fails
            ValueError: If URL is invalid
        """
        if not url or not url.strip():
            raise ValueError("url is required and cannot be empty")

        if not 1 <= num_results <= 100:
            raise ValueError("num_results must be between 1 and 100")

        payload: dict[str, Any] = {
            "url": url.strip(),
            "numResults": num_results,
            "excludeSourceDomain": exclude_source_domain,
        }

        if include_domains:
            payload["includeDomains"] = include_domains

        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        if start_crawl_date:
            payload["startCrawlDate"] = start_crawl_date

        if end_crawl_date:
            payload["endCrawlDate"] = end_crawl_date

        if start_published_date:
            payload["startPublishedDate"] = start_published_date

        if end_published_date:
            payload["endPublishedDate"] = end_published_date

        if category:
            payload["category"] = category.value if isinstance(category, ExaCategory) else category

        try:
            response = await self.post("/findSimilar", json=payload)
            return self._parse_search_response(f"similar:{url}", ExaSearchType.NEURAL, response)

        except IntegrationError as e:
            raise ExaError(
                message=f"Find similar failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_contents(
        self,
        ids: list[str],
        *,
        text: bool = True,
        highlights: bool = False,
        highlight_query: str | None = None,
        summary: bool = False,
    ) -> ExaContentsResponse:
        """
        Get content from documents by their Exa IDs.

        Retrieves full text, highlights, and/or summaries for documents
        returned from a previous search.

        Args:
            ids: List of Exa document IDs from search results
            text: Include full text content (default True)
            highlights: Include key excerpt highlights (default False)
            highlight_query: Query to use for highlighting (uses search query if not provided)
            summary: Include AI-generated summary (default False)

        Returns:
            ExaContentsResponse with document contents

        Raises:
            ExaError: If API request fails
            ValueError: If no IDs provided
        """
        if not ids:
            raise ValueError("ids list cannot be empty")

        payload: dict[str, Any] = {"ids": ids}

        # Build contents options
        contents: dict[str, Any] = {}
        if text:
            contents["text"] = True
        if highlights:
            highlight_opts: dict[str, Any] = {}
            if highlight_query:
                highlight_opts["query"] = highlight_query
            contents["highlights"] = highlight_opts if highlight_opts else True
        if summary:
            contents["summary"] = True

        if contents:
            payload["contents"] = contents

        try:
            response = await self.post("/contents", json=payload)
            return self._parse_contents_response(response)

        except IntegrationError as e:
            raise ExaError(
                message=f"Get contents failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_and_contents(
        self,
        query: str,
        *,
        search_type: ExaSearchType | str = ExaSearchType.AUTO,
        num_results: int = 10,
        text: bool = True,
        highlights: bool = False,
        summary: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        category: ExaCategory | str | None = None,
        use_autoprompt: bool = False,
    ) -> ExaSearchResponse:
        """
        Search and retrieve contents in a single request.

        Combines search with content extraction for efficiency.
        More cost-effective than separate search + contents calls.

        Args:
            query: Natural language search query
            search_type: "neural", "keyword", or "auto" (default)
            num_results: Number of results (1-100, default 10)
            text: Include full text content (default True)
            highlights: Include key excerpt highlights (default False)
            summary: Include AI-generated summary (default False)
            include_domains: Only include these domains
            exclude_domains: Exclude these domains
            start_published_date: Filter by publish date (ISO format)
            end_published_date: Filter by publish date (ISO format)
            category: Filter by content category
            use_autoprompt: Enhance query with AI

        Returns:
            ExaSearchResponse with results including content

        Raises:
            ExaError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        payload: dict[str, Any] = {
            "query": query.strip(),
            "numResults": num_results,
            "type": (search_type.value if isinstance(search_type, ExaSearchType) else search_type),
        }

        # Build contents options
        contents: dict[str, Any] = {}
        if text:
            contents["text"] = True
        if highlights:
            contents["highlights"] = True
        if summary:
            contents["summary"] = True

        if contents:
            payload["contents"] = contents

        if include_domains:
            payload["includeDomains"] = include_domains

        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        if start_published_date:
            payload["startPublishedDate"] = start_published_date

        if end_published_date:
            payload["endPublishedDate"] = end_published_date

        if category:
            payload["category"] = category.value if isinstance(category, ExaCategory) else category

        if use_autoprompt:
            payload["useAutoprompt"] = True

        try:
            response = await self.post("/search", json=payload)
            search_type_enum = (
                search_type
                if isinstance(search_type, ExaSearchType)
                else ExaSearchType(search_type)
            )
            return self._parse_search_response(query, search_type_enum, response)

        except IntegrationError as e:
            raise ExaError(
                message=f"Search and contents failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_similar_and_contents(
        self,
        url: str,
        *,
        num_results: int = 10,
        text: bool = True,
        highlights: bool = False,
        summary: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        exclude_source_domain: bool = True,
    ) -> ExaSearchResponse:
        """
        Find similar content and retrieve contents in a single request.

        Args:
            url: URL to find similar content for
            num_results: Number of results (1-100, default 10)
            text: Include full text content (default True)
            highlights: Include key excerpts (default False)
            summary: Include AI summary (default False)
            include_domains: Only include these domains
            exclude_domains: Exclude these domains
            exclude_source_domain: Exclude source URL's domain (default True)

        Returns:
            ExaSearchResponse with similar content and extracted text

        Raises:
            ExaError: If API request fails
        """
        if not url or not url.strip():
            raise ValueError("url is required and cannot be empty")

        payload: dict[str, Any] = {
            "url": url.strip(),
            "numResults": num_results,
            "excludeSourceDomain": exclude_source_domain,
        }

        # Build contents options
        contents: dict[str, Any] = {}
        if text:
            contents["text"] = True
        if highlights:
            contents["highlights"] = True
        if summary:
            contents["summary"] = True

        if contents:
            payload["contents"] = contents

        if include_domains:
            payload["includeDomains"] = include_domains

        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        try:
            response = await self.post("/findSimilar", json=payload)
            return self._parse_search_response(f"similar:{url}", ExaSearchType.NEURAL, response)

        except IntegrationError as e:
            raise ExaError(
                message=f"Find similar and contents failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_companies(
        self,
        query: str,
        *,
        num_results: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> ExaSearchResponse:
        """
        Search for company websites matching a description.

        Convenience method that sets category to "company" for finding
        company homepages and about pages.

        Args:
            query: Description of companies to find (e.g., "AI startups in healthcare")
            num_results: Number of results (1-100, default 10)
            include_domains: Only include these domains
            exclude_domains: Exclude these domains

        Returns:
            ExaSearchResponse with company results

        Raises:
            ExaError: If API request fails
        """
        return await self.search(
            query=query,
            num_results=num_results,
            category=ExaCategory.COMPANY,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            use_autoprompt=True,
        )

    async def search_research_papers(
        self,
        query: str,
        *,
        num_results: int = 10,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
    ) -> ExaSearchResponse:
        """
        Search for research papers and academic content.

        Convenience method that sets category to "research paper" for finding
        academic papers, preprints, and scholarly articles.

        Args:
            query: Research topic or question
            num_results: Number of results (1-100, default 10)
            start_published_date: Filter by publish date (ISO format)
            end_published_date: Filter by publish date (ISO format)

        Returns:
            ExaSearchResponse with research paper results

        Raises:
            ExaError: If API request fails
        """
        return await self.search(
            query=query,
            num_results=num_results,
            category=ExaCategory.RESEARCH_PAPER,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
            use_autoprompt=True,
        )

    async def search_news(
        self,
        query: str,
        *,
        num_results: int = 10,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
    ) -> ExaSearchResponse:
        """
        Search for news articles.

        Convenience method that sets category to "news" for finding
        news articles and press coverage.

        Args:
            query: News topic or query
            num_results: Number of results (1-100, default 10)
            start_published_date: Filter by publish date (ISO format)
            end_published_date: Filter by publish date (ISO format)

        Returns:
            ExaSearchResponse with news article results

        Raises:
            ExaError: If API request fails
        """
        return await self.search(
            query=query,
            num_results=num_results,
            category=ExaCategory.NEWS,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Exa API connectivity and key validity.

        Performs a minimal search to verify API connectivity.

        Returns:
            Dictionary with health status

        Raises:
            ExaError: If health check fails
        """
        try:
            await self.search("test", num_results=1)
            return {
                "name": self.name,
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": self.name,
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
        Call any Exa API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search")
            method: HTTP method (default POST)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            ExaError: If request fails
        """
        try:
            if method.upper() == "GET":
                return await self.get(endpoint, **kwargs)
            else:
                return await self.post(endpoint, **kwargs)
        except IntegrationError as e:
            raise ExaError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

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

    def _parse_search_response(
        self,
        query: str,
        search_type: ExaSearchType,
        response: dict[str, Any],
    ) -> ExaSearchResponse:
        """Parse API response into ExaSearchResponse."""
        result = ExaSearchResponse(
            query=query,
            search_type=search_type,
            request_id=response.get("requestId"),
            cost_credits=response.get("costCredits"),
            raw_response=response,
        )

        # Parse autoprompt info if present
        if "autopromptString" in response:
            result.autoprompt = ExaAutopromptInfo(
                original_query=query,
                transformed_query=response.get("autopromptString"),
            )

        # Parse results
        for item in response.get("results", []):
            search_result = ExaSearchResult(
                id=item.get("id", ""),
                url=item.get("url", ""),
                title=item.get("title", ""),
                score=item.get("score"),
                published_date=item.get("publishedDate"),
                author=item.get("author"),
                text=item.get("text"),
                highlights=item.get("highlights", []),
                highlight_scores=item.get("highlightScores", []),
                summary=item.get("summary"),
                image=item.get("image"),
                favicon=item.get("favicon"),
                raw=item,
            )
            result.results.append(search_result)

        return result

    def _parse_contents_response(
        self,
        response: dict[str, Any],
    ) -> ExaContentsResponse:
        """Parse contents API response into ExaContentsResponse."""
        result = ExaContentsResponse(
            request_id=response.get("requestId"),
            cost_credits=response.get("costCredits"),
            raw_response=response,
        )

        for item in response.get("results", []):
            content_result = ExaContentsResult(
                id=item.get("id", ""),
                url=item.get("url", ""),
                title=item.get("title", ""),
                text=item.get("text"),
                highlights=item.get("highlights", []),
                highlight_scores=item.get("highlightScores", []),
                summary=item.get("summary"),
                raw=item,
            )
            result.results.append(content_result)

        return result

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cache cleanup."""
        self.clear_cache()
        await super().__aexit__(exc_type, exc_val, exc_tb)

