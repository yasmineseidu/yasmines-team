"""
SerpApi (serpapi.com) integration client.

Provides Google Search results via SerpApi service with support for
organic results, paid ads, related searches, knowledge graph, and more.

API Documentation: https://serpapi.com/search-api
Base URL: https://serpapi.com

Features:
- Google Search with organic results, featured snippets, knowledge graph
- Google Ads (paid results) retrieval
- Related searches and People Also Ask
- Image, News, Shopping, Video search types
- Location and language customization
- Pagination support for deep result retrieval
- Multiple search engines (Google, Bing, Yahoo, DuckDuckGo)

Pricing:
- Free: 100 searches/month
- $50/month: 5,000 searches
- $130/month: 15,000 searches
- $250/month: 30,000 searches

Rate Limits:
- Depends on plan tier
- Recommended: 1-2 requests per second

Example:
    >>> from src.integrations.serp_api import SerpApiClient
    >>> client = SerpApiClient(api_key="your-api-key")
    >>> result = await client.search("best CRM software 2024")
    >>> for item in result.organic_results:
    ...     print(f"{item.position}. {item.title}: {item.link}")
    >>> if result.answer_box:
    ...     print(f"Answer: {result.answer_box.snippet}")
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


class SerpApiEngine(str, Enum):
    """Search engines supported by SerpApi."""

    GOOGLE = "google"
    BING = "bing"
    YAHOO = "yahoo"
    DUCKDUCKGO = "duckduckgo"
    BAIDU = "baidu"
    YANDEX = "yandex"


class SerpApiSearchType(str, Enum):
    """Types of Google searches supported."""

    SEARCH = "search"
    IMAGES = "isch"
    NEWS = "nws"
    SHOPPING = "shop"
    VIDEOS = "vid"
    MAPS = "maps"
    JOBS = "jobs"
    SCHOLAR = "scholar"
    PATENTS = "patents"


class SerpApiTimeFilter(str, Enum):
    """Time filters for search results."""

    PAST_HOUR = "qdr:h"
    PAST_DAY = "qdr:d"
    PAST_WEEK = "qdr:w"
    PAST_MONTH = "qdr:m"
    PAST_YEAR = "qdr:y"


class SerpApiError(IntegrationError):
    """SerpApi-specific error."""

    pass


@dataclass
class SerpApiOrganicResult:
    """Single organic search result from SerpApi."""

    position: int
    title: str
    link: str
    snippet: str
    displayed_link: str | None = None
    favicon: str | None = None
    date: str | None = None
    cached_page_link: str | None = None
    related_pages_link: str | None = None
    sitelinks: list[dict[str, str]] = field(default_factory=list)
    rich_snippet: dict[str, Any] | None = None
    source: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiAdResult:
    """Paid advertisement result from SerpApi."""

    position: int
    title: str
    link: str
    tracking_link: str | None = None
    displayed_link: str | None = None
    description: str | None = None
    sitelinks: list[dict[str, str]] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiKnowledgeGraph:
    """Knowledge graph data from Google search."""

    title: str | None
    type: str | None
    description: str | None
    entity_type: str | None
    kgmid: str | None
    source: dict[str, str] | None
    image: str | None
    website: str | None
    attributes: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiAnswerBox:
    """Answer box / featured snippet from Google search."""

    type: str | None
    title: str | None
    snippet: str | None
    link: str | None
    displayed_link: str | None
    highlighted_words: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    table: list[list[str]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiPeopleAlsoAsk:
    """People Also Ask question from Google search."""

    question: str
    snippet: str | None
    title: str | None
    link: str | None
    displayed_link: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiRelatedSearch:
    """Related search suggestion from Google."""

    query: str
    link: str | None = None


@dataclass
class SerpApiImageResult:
    """Image search result from SerpApi."""

    position: int
    title: str
    thumbnail: str
    original: str
    source: str | None = None
    link: str | None = None
    is_product: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiNewsResult:
    """News search result from SerpApi."""

    position: int
    title: str
    link: str
    source: str
    date: str | None = None
    snippet: str | None = None
    thumbnail: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiShoppingResult:
    """Shopping search result from SerpApi."""

    position: int
    title: str
    link: str
    price: str | None = None
    extracted_price: float | None = None
    source: str | None = None
    rating: float | None = None
    reviews: int | None = None
    thumbnail: str | None = None
    delivery: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiLocalResult:
    """Local/Maps search result from SerpApi."""

    position: int
    title: str
    place_id: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    rating: float | None = None
    reviews: int | None = None
    type: str | None = None
    hours: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    thumbnail: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiSearchMetadata:
    """Search metadata from SerpApi response."""

    id: str | None = None
    status: str | None = None
    created_at: str | None = None
    processed_at: str | None = None
    total_time_taken: float | None = None
    google_url: str | None = None
    raw_html_file: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiSearchInfo:
    """Search information from SerpApi response."""

    query_displayed: str | None = None
    total_results: int | None = None
    time_taken_displayed: float | None = None
    organic_results_state: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiSearchResponse:
    """Complete search response from SerpApi."""

    query: str
    search_engine: SerpApiEngine
    search_type: SerpApiSearchType | None = None

    # Metadata
    search_metadata: SerpApiSearchMetadata | None = None
    search_info: SerpApiSearchInfo | None = None

    # Core results
    organic_results: list[SerpApiOrganicResult] = field(default_factory=list)
    ads_results: list[SerpApiAdResult] = field(default_factory=list)

    # Rich results
    knowledge_graph: SerpApiKnowledgeGraph | None = None
    answer_box: SerpApiAnswerBox | None = None
    people_also_ask: list[SerpApiPeopleAlsoAsk] = field(default_factory=list)
    related_searches: list[SerpApiRelatedSearch] = field(default_factory=list)

    # Specialized results
    images: list[SerpApiImageResult] = field(default_factory=list)
    news: list[SerpApiNewsResult] = field(default_factory=list)
    shopping: list[SerpApiShoppingResult] = field(default_factory=list)
    local_results: list[SerpApiLocalResult] = field(default_factory=list)

    # Pagination
    serpapi_pagination: dict[str, Any] = field(default_factory=dict)

    # Raw response
    raw_response: dict[str, Any] = field(default_factory=dict)


class SerpApiClient(BaseIntegrationClient):
    """
    SerpApi client for Google and other search engine results.

    Provides comprehensive access to search engine results pages (SERPs)
    including organic results, ads, featured snippets, knowledge graphs,
    and specialized search types (images, news, shopping, etc.).

    Example:
        >>> async with SerpApiClient(api_key="key") as client:  # pragma: allowlist secret
        ...     # Web search
        ...     result = await client.search("AI startups 2024")
        ...     for r in result.organic_results[:5]:
        ...         print(f"{r.position}. {r.title}")
        ...
        ...     # Image search
        ...     images = await client.search_images("robot AI")
        ...     for img in images.images[:3]:
        ...         print(f"{img.title}: {img.original}")
        ...
        ...     # Get ads/paid results
        ...     ads_result = await client.search("CRM software")
        ...     for ad in ads_result.ads_results:
        ...         print(f"Ad: {ad.title}")
    """

    BASE_URL = "https://serpapi.com"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        default_engine: SerpApiEngine = SerpApiEngine.GOOGLE,
    ) -> None:
        """
        Initialize SerpApi client.

        Args:
            api_key: SerpApi API key from serpapi.com dashboard
            timeout: Request timeout in seconds (default 60s - searches can be slow)
            max_retries: Maximum retry attempts for transient failures
            default_engine: Default search engine to use (default: Google)
        """
        super().__init__(
            name="serpapi",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.default_engine = default_engine

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for SerpApi requests.

        Note: SerpApi uses query parameter authentication, not headers.
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_params(
        self,
        query: str,
        engine: SerpApiEngine | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Build query parameters for SerpApi request.

        Args:
            query: Search query string
            engine: Search engine to use
            **kwargs: Additional parameters

        Returns:
            Dictionary of query parameters
        """
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "engine": (engine or self.default_engine).value,
            "q": query.strip(),
            "output": "json",
        }

        # Add optional parameters
        for key, value in kwargs.items():
            if value is not None:
                # Convert enum values
                if isinstance(value, Enum):
                    params[key] = value.value
                else:
                    params[key] = value

        return params

    async def search(
        self,
        query: str,
        *,
        engine: SerpApiEngine | None = None,
        num: int = 10,
        start: int = 0,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
        time_filter: SerpApiTimeFilter | str | None = None,
        safe: bool = True,
        no_cache: bool = False,
    ) -> SerpApiSearchResponse:
        """
        Perform a web search using SerpApi.

        Args:
            query: Search query string
            engine: Search engine to use (default: Google)
            num: Number of results per page (1-100, default 10)
            start: Result offset for pagination (default 0)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            location: Specific location for local results (e.g., "Austin, Texas")
            time_filter: Time filter for results (hour, day, week, month, year)
            safe: Enable safe search filtering (default True)
            no_cache: Force fresh results, bypass cache (default False)

        Returns:
            SerpApiSearchResponse with organic results, ads, knowledge graph, etc.

        Raises:
            SerpApiError: If API request fails
            ValueError: If required parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        if not 1 <= num <= 100:
            raise ValueError("num must be between 1 and 100")

        if start < 0:
            raise ValueError("start must be >= 0")

        params = self._build_params(
            query=query,
            engine=engine,
            num=num,
            start=start,
            gl=country.lower(),
            hl=language.lower(),
        )

        if location:
            params["location"] = location

        if time_filter:
            if isinstance(time_filter, SerpApiTimeFilter):
                params["tbs"] = time_filter.value
            else:
                params["tbs"] = time_filter

        if not safe:
            params["safe"] = "off"

        if no_cache:
            params["no_cache"] = "true"

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=engine or self.default_engine,
                search_type=SerpApiSearchType.SEARCH,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Web search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_images(
        self,
        query: str,
        *,
        engine: SerpApiEngine | None = None,
        num: int = 100,
        country: str = "us",
        language: str = "en",
        safe: bool = True,
        image_size: str | None = None,
        image_type: str | None = None,
        image_color: str | None = None,
    ) -> SerpApiSearchResponse:
        """
        Perform an image search using SerpApi.

        Args:
            query: Search query string
            engine: Search engine to use (default: Google)
            num: Number of images to return (default 100)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            safe: Enable safe search filtering (default True)
            image_size: Filter by size (large, medium, icon, etc.)
            image_type: Filter by type (photo, clipart, lineart, animated)
            image_color: Filter by color (color, gray, trans, etc.)

        Returns:
            SerpApiSearchResponse with images list populated

        Raises:
            SerpApiError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        params = self._build_params(
            query=query,
            engine=engine,
            tbm="isch",  # Image search type
            ijn=0,  # Page number (0-indexed)
            gl=country.lower(),
            hl=language.lower(),
        )

        if not safe:
            params["safe"] = "off"

        if image_size:
            params["imgsz"] = image_size

        if image_type:
            params["imgtype"] = image_type

        if image_color:
            params["imgc"] = image_color

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=engine or self.default_engine,
                search_type=SerpApiSearchType.IMAGES,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Image search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_news(
        self,
        query: str,
        *,
        engine: SerpApiEngine | None = None,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        time_filter: SerpApiTimeFilter | str | None = None,
    ) -> SerpApiSearchResponse:
        """
        Perform a news search using SerpApi.

        Args:
            query: Search query string
            engine: Search engine to use (default: Google)
            num: Number of results to return (default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            time_filter: Time filter for results (hour, day, week, month, year)

        Returns:
            SerpApiSearchResponse with news list populated

        Raises:
            SerpApiError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        params = self._build_params(
            query=query,
            engine=engine,
            tbm="nws",  # News search type
            num=num,
            gl=country.lower(),
            hl=language.lower(),
        )

        if time_filter:
            if isinstance(time_filter, SerpApiTimeFilter):
                params["tbs"] = time_filter.value
            else:
                params["tbs"] = time_filter

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=engine or self.default_engine,
                search_type=SerpApiSearchType.NEWS,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"News search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_shopping(
        self,
        query: str,
        *,
        engine: SerpApiEngine | None = None,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> SerpApiSearchResponse:
        """
        Perform a shopping search using SerpApi.

        Args:
            query: Search query string
            engine: Search engine to use (default: Google)
            num: Number of results to return (default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            min_price: Minimum price filter (in cents for USD)
            max_price: Maximum price filter (in cents for USD)

        Returns:
            SerpApiSearchResponse with shopping list populated

        Raises:
            SerpApiError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        params = self._build_params(
            query=query,
            engine=engine,
            tbm="shop",  # Shopping search type
            num=num,
            gl=country.lower(),
            hl=language.lower(),
        )

        # Build price filter
        price_parts = []
        if min_price is not None:
            price_parts.append(f"price:1,ppr_min:{min_price}")
        if max_price is not None:
            price_parts.append(f"ppr_max:{max_price}")

        if price_parts:
            params["tbs"] = ",".join(price_parts)

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=engine or self.default_engine,
                search_type=SerpApiSearchType.SHOPPING,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Shopping search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_videos(
        self,
        query: str,
        *,
        engine: SerpApiEngine | None = None,
        num: int = 10,
        country: str = "us",
        language: str = "en",
        time_filter: SerpApiTimeFilter | str | None = None,
    ) -> SerpApiSearchResponse:
        """
        Perform a video search using SerpApi.

        Args:
            query: Search query string
            engine: Search engine to use (default: Google)
            num: Number of results to return (default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")
            time_filter: Time filter for results (hour, day, week, month, year)

        Returns:
            SerpApiSearchResponse with video results in organic_results

        Raises:
            SerpApiError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        params = self._build_params(
            query=query,
            engine=engine,
            tbm="vid",  # Video search type
            num=num,
            gl=country.lower(),
            hl=language.lower(),
        )

        if time_filter:
            if isinstance(time_filter, SerpApiTimeFilter):
                params["tbs"] = time_filter.value
            else:
                params["tbs"] = time_filter

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=engine or self.default_engine,
                search_type=SerpApiSearchType.VIDEOS,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Video search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_local(
        self,
        query: str,
        *,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        num: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> SerpApiSearchResponse:
        """
        Perform a local/maps search using SerpApi.

        Args:
            query: Search query string (e.g., "coffee shops")
            location: Location string (e.g., "Austin, Texas")
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            num: Number of results to return (default 10)
            country: Country code for localized results (default "us")
            language: Language code for results (default "en")

        Returns:
            SerpApiSearchResponse with local_results populated

        Raises:
            SerpApiError: If API request fails
        """
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")

        # Use Google Local engine for local search
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "engine": "google_local",
            "q": query.strip(),
            "output": "json",
            "gl": country.lower(),
            "hl": language.lower(),
        }

        if location:
            params["location"] = location

        if latitude is not None and longitude is not None:
            params["ll"] = f"@{latitude},{longitude},14z"

        try:
            response = await self.get("/search", params=params)
            return self._parse_search_response(
                query=query,
                engine=SerpApiEngine.GOOGLE,
                search_type=SerpApiSearchType.MAPS,
                response=response,
            )
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Local search failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_organic_results(
        self,
        query: str,
        *,
        num: int = 10,
        start: int = 0,
        country: str = "us",
        language: str = "en",
    ) -> list[SerpApiOrganicResult]:
        """
        Convenience method to get only organic search results.

        Args:
            query: Search query string
            num: Number of results (1-100, default 10)
            start: Result offset for pagination (default 0)
            country: Country code (default "us")
            language: Language code (default "en")

        Returns:
            List of organic search results only

        Raises:
            SerpApiError: If API request fails
        """
        result = await self.search(
            query=query,
            num=num,
            start=start,
            country=country,
            language=language,
        )
        return result.organic_results

    async def get_paid_results(
        self,
        query: str,
        *,
        num: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> list[SerpApiAdResult]:
        """
        Convenience method to get only paid/ad search results.

        Args:
            query: Search query string
            num: Number of results (1-100, default 10)
            country: Country code (default "us")
            language: Language code (default "en")

        Returns:
            List of ad/paid search results only

        Raises:
            SerpApiError: If API request fails
        """
        result = await self.search(
            query=query,
            num=num,
            country=country,
            language=language,
        )
        return result.ads_results

    async def get_related_searches(
        self,
        query: str,
        *,
        country: str = "us",
        language: str = "en",
    ) -> list[SerpApiRelatedSearch]:
        """
        Convenience method to get related searches.

        Args:
            query: Search query string
            country: Country code (default "us")
            language: Language code (default "en")

        Returns:
            List of related search suggestions

        Raises:
            SerpApiError: If API request fails
        """
        result = await self.search(
            query=query,
            num=10,
            country=country,
            language=language,
        )
        return result.related_searches

    async def paginate_results(
        self,
        query: str,
        *,
        pages: int = 3,
        results_per_page: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> SerpApiSearchResponse:
        """
        Fetch multiple pages of search results.

        Args:
            query: Search query string
            pages: Number of pages to fetch (default 3)
            results_per_page: Results per page (default 10)
            country: Country code (default "us")
            language: Language code (default "en")

        Returns:
            SerpApiSearchResponse with aggregated organic results from all pages

        Raises:
            SerpApiError: If any API request fails
            ValueError: If pages < 1
        """
        if pages < 1:
            raise ValueError("pages must be >= 1")

        all_organic: list[SerpApiOrganicResult] = []
        aggregated_response: SerpApiSearchResponse | None = None

        for page in range(pages):
            start = page * results_per_page

            try:
                result = await self.search(
                    query=query,
                    num=results_per_page,
                    start=start,
                    country=country,
                    language=language,
                )

                # Use first page response as base
                if aggregated_response is None:
                    aggregated_response = result
                else:
                    # Append organic results from subsequent pages
                    all_organic.extend(result.organic_results)

                # Stop if we got fewer results than requested (no more pages)
                if len(result.organic_results) < results_per_page:
                    break

            except SerpApiError:
                # Stop pagination on error but return what we have
                logger.warning(f"[{self.name}] Pagination stopped at page {page + 1} due to error")
                break

        if aggregated_response:
            # Combine all organic results
            aggregated_response.organic_results.extend(all_organic)

            # Update position numbers
            for i, organic_result in enumerate(aggregated_response.organic_results):
                organic_result.position = i + 1

            return aggregated_response

        # Should not reach here, but handle edge case
        raise SerpApiError(message="No results returned from pagination")

    async def health_check(self) -> dict[str, Any]:
        """
        Check SerpApi connectivity and API key validity.

        Performs a minimal search to verify API connectivity.

        Returns:
            Dictionary with health status

        Raises:
            SerpApiError: If health check fails
        """
        try:
            # Perform minimal search to check connectivity
            await self.search("test", num=1)
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

    async def get_account_info(self) -> dict[str, Any]:
        """
        Get account information and remaining API credits.

        Returns:
            Dictionary with account information

        Raises:
            SerpApiError: If request fails
        """
        try:
            params = {"api_key": self.api_key}
            return await self.get("/account", params=params)
        except IntegrationError as e:
            raise SerpApiError(
                message=f"Failed to get account info: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any SerpApi endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search")
            method: HTTP method (default GET)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            SerpApiError: If request fails
        """
        try:
            if method.upper() == "GET":
                return await self.get(endpoint, **kwargs)
            else:
                return await self.post(endpoint, **kwargs)
        except IntegrationError as e:
            raise SerpApiError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_search_response(
        self,
        query: str,
        engine: SerpApiEngine,
        search_type: SerpApiSearchType | None,
        response: dict[str, Any],
    ) -> SerpApiSearchResponse:
        """
        Parse API response into SerpApiSearchResponse.

        Args:
            query: Original search query
            engine: Search engine used
            search_type: Type of search performed
            response: Raw API response

        Returns:
            SerpApiSearchResponse dataclass with all parsed data
        """
        result = SerpApiSearchResponse(
            query=query,
            search_engine=engine,
            search_type=search_type,
            raw_response=response,
        )

        # Parse search metadata
        meta = response.get("search_metadata", {})
        if meta:
            result.search_metadata = SerpApiSearchMetadata(
                id=meta.get("id"),
                status=meta.get("status"),
                created_at=meta.get("created_at"),
                processed_at=meta.get("processed_at"),
                total_time_taken=meta.get("total_time_taken"),
                google_url=meta.get("google_url"),
                raw_html_file=meta.get("raw_html_file"),
                raw=meta,
            )

        # Parse search info
        info = response.get("search_information", {})
        if info:
            result.search_info = SerpApiSearchInfo(
                query_displayed=info.get("query_displayed"),
                total_results=info.get("total_results"),
                time_taken_displayed=info.get("time_taken_displayed"),
                organic_results_state=info.get("organic_results_state"),
                raw=info,
            )

        # Parse organic results
        for item in response.get("organic_results", []):
            result.organic_results.append(
                SerpApiOrganicResult(
                    position=item.get("position", len(result.organic_results) + 1),
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    displayed_link=item.get("displayed_link"),
                    favicon=item.get("favicon"),
                    date=item.get("date"),
                    cached_page_link=item.get("cached_page_link"),
                    related_pages_link=item.get("related_pages_link"),
                    sitelinks=item.get("sitelinks", {}).get("inline", [])
                    or item.get("sitelinks", {}).get("expanded", []),
                    rich_snippet=item.get("rich_snippet"),
                    source=item.get("source"),
                    raw=item,
                )
            )

        # Parse ads (top and bottom)
        for ads_key in ["ads", "top_ads", "bottom_ads"]:
            for ad in response.get(ads_key, []):
                result.ads_results.append(
                    SerpApiAdResult(
                        position=ad.get("position", len(result.ads_results) + 1),
                        title=ad.get("title", ""),
                        link=ad.get("link", ""),
                        tracking_link=ad.get("tracking_link"),
                        displayed_link=ad.get("displayed_link"),
                        description=ad.get("description"),
                        sitelinks=ad.get("sitelinks", []),
                        extensions=ad.get("extensions", []),
                        raw=ad,
                    )
                )

        # Parse knowledge graph
        kg = response.get("knowledge_graph")
        if kg:
            result.knowledge_graph = SerpApiKnowledgeGraph(
                title=kg.get("title"),
                type=kg.get("type"),
                description=kg.get("description"),
                entity_type=kg.get("entity_type"),
                kgmid=kg.get("kgmid"),
                source=kg.get("source"),
                image=kg.get("header_images", [{}])[0].get("image")
                if kg.get("header_images")
                else kg.get("image"),
                website=kg.get("website"),
                attributes=kg.get("attributes", {}),
                raw=kg,
            )

        # Parse answer box
        ab = response.get("answer_box")
        if ab:
            result.answer_box = SerpApiAnswerBox(
                type=ab.get("type"),
                title=ab.get("title"),
                snippet=ab.get("snippet") or ab.get("answer"),
                link=ab.get("link"),
                displayed_link=ab.get("displayed_link"),
                highlighted_words=ab.get("highlighted_words", []),
                list_items=ab.get("list", []),
                table=ab.get("table", []),
                raw=ab,
            )

        # Parse people also ask
        for paa in response.get("related_questions", []):
            result.people_also_ask.append(
                SerpApiPeopleAlsoAsk(
                    question=paa.get("question", ""),
                    snippet=paa.get("snippet"),
                    title=paa.get("title"),
                    link=paa.get("link"),
                    displayed_link=paa.get("displayed_link"),
                    raw=paa,
                )
            )

        # Parse related searches
        for rs in response.get("related_searches", []):
            result.related_searches.append(
                SerpApiRelatedSearch(
                    query=rs.get("query", ""),
                    link=rs.get("link"),
                )
            )

        # Parse images
        for img in response.get("images_results", []) or response.get("images", []):
            result.images.append(
                SerpApiImageResult(
                    position=img.get("position", len(result.images) + 1),
                    title=img.get("title", ""),
                    thumbnail=img.get("thumbnail", ""),
                    original=img.get("original", ""),
                    source=img.get("source"),
                    link=img.get("link"),
                    is_product=img.get("is_product", False),
                    raw=img,
                )
            )

        # Parse news
        for news in response.get("news_results", []) or response.get("top_stories", []):
            result.news.append(
                SerpApiNewsResult(
                    position=news.get("position", len(result.news) + 1),
                    title=news.get("title", ""),
                    link=news.get("link", ""),
                    source=news.get("source", ""),
                    date=news.get("date"),
                    snippet=news.get("snippet"),
                    thumbnail=news.get("thumbnail"),
                    raw=news,
                )
            )

        # Parse shopping
        for shop in response.get("shopping_results", []) or response.get("inline_shopping", []):
            result.shopping.append(
                SerpApiShoppingResult(
                    position=shop.get("position", len(result.shopping) + 1),
                    title=shop.get("title", ""),
                    link=shop.get("link", ""),
                    price=shop.get("price"),
                    extracted_price=shop.get("extracted_price"),
                    source=shop.get("source"),
                    rating=shop.get("rating"),
                    reviews=shop.get("reviews"),
                    thumbnail=shop.get("thumbnail"),
                    delivery=shop.get("delivery"),
                    raw=shop,
                )
            )

        # Parse local results
        for local in response.get("local_results", []) or response.get("places_results", []):
            result.local_results.append(
                SerpApiLocalResult(
                    position=local.get("position", len(result.local_results) + 1),
                    title=local.get("title", ""),
                    place_id=local.get("place_id"),
                    address=local.get("address"),
                    phone=local.get("phone"),
                    website=local.get("website"),
                    rating=local.get("rating"),
                    reviews=local.get("reviews"),
                    type=local.get("type"),
                    hours=local.get("hours"),
                    latitude=local.get("gps_coordinates", {}).get("latitude"),
                    longitude=local.get("gps_coordinates", {}).get("longitude"),
                    thumbnail=local.get("thumbnail"),
                    raw=local,
                )
            )

        # Parse pagination info
        result.serpapi_pagination = response.get("serpapi_pagination", {})

        return result
