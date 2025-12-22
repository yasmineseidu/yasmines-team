"""
Firecrawl.dev API integration client.

Provides web scraping and content extraction capabilities for competitive
analysis and research. Supports single page scraping, full website crawling,
JavaScript rendering, and structured data extraction.

API Documentation: https://docs.firecrawl.dev
Base URL: https://api.firecrawl.dev/v1

Features:
- Single page scraping with JavaScript rendering
- Full website crawling with URL filtering
- Content extraction (text, images, links, metadata)
- Structured data extraction
- Robots.txt compliance
- Rate limiting and crawl delays
- Caching support

Rate Limits:
- Varies by plan (typically 100-1000 requests/day)
- Respects robots.txt and implements crawl delays

Authentication:
- Bearer token via API key from Firecrawl dashboard

Example:
    >>> from src.integrations.firecrawl import FirecrawlClient
    >>> client = FirecrawlClient(api_key="your-api-key")
    >>> result = await client.scrape_page(
    ...     url="https://example.com",
    ...     include_tags=["h1", "p", "img"]
    ... )
    >>> print(result.content)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class FirecrawlError(IntegrationError):
    """Exception raised for Firecrawl API errors."""

    pass


@dataclass
class ScrapedPage:
    """Scraped page data from Firecrawl API."""

    url: str
    content: str
    markdown: str | None = None
    html: str | None = None
    title: str | None = None
    description: str | None = None
    author: str | None = None
    links: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status_code: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def has_content(self) -> bool:
        """Check if page has extracted content."""
        return bool(self.content or self.markdown or self.html)


@dataclass
class CrawlJob:
    """Crawl job information from Firecrawl API."""

    job_id: str
    status: str
    urls_crawled: int = 0
    urls_found: int = 0
    data: list[ScrapedPage] = field(default_factory=list)
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if crawl job is complete."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def is_running(self) -> bool:
        """Check if crawl job is still running."""
        return self.status in ("active", "queued", "paused")


class FirecrawlClient(BaseIntegrationClient):
    """
    Async client for Firecrawl.dev API.

    Provides web scraping and crawling capabilities with JavaScript rendering,
    content extraction, and structured data extraction.

    Attributes:
        BASE_URL: Base URL for API requests.
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,  # Longer timeout for scraping operations
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key from dashboard.
            timeout: Request timeout in seconds (default 60s for scraping).
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="firecrawl",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client")

    async def scrape_page(
        self,
        url: str,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        wait_for: int | None = None,
        timeout: int | None = None,
        only_main_content: bool = False,
        remove_selectors: list[str] | None = None,
        extract_metadata: bool = True,
        **kwargs: Any,
    ) -> ScrapedPage:
        """
        Scrape a single web page.

        Args:
            url: URL to scrape.
            include_tags: HTML tags to include in extraction.
            exclude_tags: HTML tags to exclude from extraction.
            wait_for: Milliseconds to wait for page load.
            timeout: Request timeout in milliseconds.
            only_main_content: Extract only main content (skip nav, footer, etc.).
            remove_selectors: CSS selectors to remove from page.
            extract_metadata: Extract page metadata (title, description, etc.).
            **kwargs: Additional parameters for API.

        Returns:
            ScrapedPage with extracted content and metadata.

        Raises:
            FirecrawlError: If API request fails.
        """
        payload: dict[str, Any] = {"url": url}

        if include_tags:
            payload["includeTags"] = include_tags
        if exclude_tags:
            payload["excludeTags"] = exclude_tags
        if wait_for is not None:
            payload["waitFor"] = wait_for
        if timeout is not None:
            payload["timeout"] = timeout
        if only_main_content:
            payload["onlyMainContent"] = only_main_content
        if remove_selectors:
            payload["removeSelectors"] = remove_selectors
        if extract_metadata:
            payload["extractMetadata"] = extract_metadata

        payload.update(kwargs)

        try:
            response = await self.post("/scrape", json=payload)
            return self._parse_scraped_page(response)
        except IntegrationError:
            # Let base integration errors propagate (Auth, RateLimit, Payment, etc.)
            raise
        except Exception as e:
            logger.error(f"Failed to scrape page {url}: {e}")
            raise FirecrawlError(f"Failed to scrape page: {e}") from e

    async def crawl_website(
        self,
        url: str,
        max_pages: int = 10,
        limit: int | None = None,
        include_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
        allow_backward_links: bool = False,
        max_depth: int | None = None,
        crawler_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CrawlJob:
        """
        Start a full website crawl job.

        Args:
            url: Starting URL for crawl.
            max_pages: Maximum number of pages to crawl.
            limit: Alternative limit parameter.
            include_paths: URL patterns to include.
            exclude_paths: URL patterns to exclude.
            allow_backward_links: Allow crawling backward links.
            max_depth: Maximum crawl depth.
            crawler_options: Additional crawler configuration.
            **kwargs: Additional parameters for API.

        Returns:
            CrawlJob with job ID and initial status.

        Raises:
            FirecrawlError: If API request fails.
        """
        payload: dict[str, Any] = {"url": url}

        if max_pages is not None:
            payload["maxPages"] = max_pages
        if limit is not None:
            payload["limit"] = limit
        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths
        if allow_backward_links:
            payload["allowBackwardLinks"] = allow_backward_links
        if max_depth is not None:
            payload["maxDepth"] = max_depth
        if crawler_options:
            payload["crawlerOptions"] = crawler_options

        payload.update(kwargs)

        try:
            response = await self.post("/crawl", json=payload)
            return self._parse_crawl_job(response)
        except IntegrationError:
            # Let base integration errors propagate (Auth, RateLimit, Payment, etc.)
            raise
        except Exception as e:
            logger.error(f"Failed to start crawl for {url}: {e}")
            raise FirecrawlError(f"Failed to start crawl: {e}") from e

    async def get_crawl_status(self, job_id: str) -> CrawlJob:
        """
        Get status of a crawl job.

        Args:
            job_id: Crawl job ID.

        Returns:
            CrawlJob with current status and data.

        Raises:
            FirecrawlError: If API request fails.
        """
        try:
            response = await self.get(f"/crawl/status/{job_id}")
            return self._parse_crawl_job(response)
        except IntegrationError:
            # Let base integration errors propagate (Auth, RateLimit, Payment, etc.)
            raise
        except Exception as e:
            logger.error(f"Failed to get crawl status for {job_id}: {e}")
            raise FirecrawlError(f"Failed to get crawl status: {e}") from e

    async def search(
        self,
        query: str,
        page_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[ScrapedPage]:
        """
        Search and scrape pages based on query.

        Args:
            query: Search query.
            page_options: Options for page scraping.
            **kwargs: Additional parameters for API.

        Returns:
            List of ScrapedPage results.

        Raises:
            FirecrawlError: If API request fails.
        """
        payload: dict[str, Any] = {"query": query}

        if page_options:
            payload["pageOptions"] = page_options

        payload.update(kwargs)

        try:
            response = await self.post("/search", json=payload)
            data = response.get("data", [])
            return [self._parse_scraped_page(item) for item in data]
        except IntegrationError:
            # Let base integration errors propagate (Auth, RateLimit, Payment, etc.)
            raise
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            raise FirecrawlError(f"Failed to search: {e}") from e

    def _parse_scraped_page(self, data: dict[str, Any]) -> ScrapedPage:
        """
        Parse raw API response into ScrapedPage dataclass.

        Args:
            data: Raw API response data.

        Returns:
            Parsed ScrapedPage object.
        """
        # Handle nested data structure if present
        page_data = data.get("data", data)

        return ScrapedPage(
            url=page_data.get("url", data.get("url", "")),
            content=page_data.get("content", ""),
            markdown=page_data.get("markdown"),
            html=page_data.get("html"),
            title=page_data.get("metadata", {}).get("title") or page_data.get("title"),
            description=page_data.get("metadata", {}).get("description")
            or page_data.get("description"),
            author=page_data.get("metadata", {}).get("author") or page_data.get("author"),
            links=page_data.get("links", []),
            images=page_data.get("images", []),
            metadata=page_data.get("metadata", {}),
            status_code=page_data.get("statusCode") or data.get("statusCode"),
            raw_response=data,
        )

    def _parse_crawl_job(self, data: dict[str, Any]) -> CrawlJob:
        """
        Parse raw API response into CrawlJob dataclass.

        Args:
            data: Raw API response data.

        Returns:
            Parsed CrawlJob object.
        """
        job_data = data.get("job", data)

        # Parse scraped pages if present
        pages: list[ScrapedPage] = []
        if "data" in job_data:
            for page_data in job_data["data"]:
                pages.append(self._parse_scraped_page(page_data))

        return CrawlJob(
            job_id=job_data.get("id", data.get("jobId", "")),
            status=job_data.get("status", "unknown"),
            urls_crawled=job_data.get("urlsCrawled", 0),
            urls_found=job_data.get("urlsFound", 0),
            data=pages,
            error=job_data.get("error") or data.get("error"),
            raw_response=data,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Firecrawl API health.

        Returns:
            Health check status with name and healthy status.
        """
        try:
            # Try a lightweight endpoint to verify connectivity
            # If no health endpoint exists, try scraping a simple page
            response = await self.get("/health", timeout=10.0)
            return {
                "name": self.name,
                "healthy": True,
                "message": "API is healthy",
                "response": response,
            }
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "message": f"Health check failed: {e}",
            }
