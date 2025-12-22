"""
Unit tests for Firecrawl integration client.

Tests cover:
- Client initialization
- Page scraping (single page)
- Website crawling (full crawl jobs)
- Crawl status retrieval
- Search functionality
- Error handling (401, 402, 429, network errors)
- Health check functionality
- Dataclass properties and computed values

Coverage target: >80%
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.firecrawl import (
    CrawlJob,
    FirecrawlClient,
    FirecrawlError,
    ScrapedPage,
)


class TestFirecrawlClientInitialization:
    """Tests for FirecrawlClient initialization."""

    def test_client_has_correct_name(self) -> None:
        """Client should have 'firecrawl' as name."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "firecrawl"

    def test_client_has_correct_base_url(self) -> None:
        """Client should use correct base URL."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://api.firecrawl.dev/v1"

    def test_client_default_timeout_is_60_seconds(self) -> None:
        """Client should have 60s default timeout for scraping."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_client_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = FirecrawlClient(api_key="test-key", timeout=120.0)
        assert client.timeout == 120.0

    def test_client_default_max_retries(self) -> None:
        """Client should have 3 retries by default."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_client_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = FirecrawlClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5

    def test_client_stores_api_key(self) -> None:
        """Client should store API key."""
        client = FirecrawlClient(api_key="my-secret-key")  # pragma: allowlist secret
        assert client.api_key == "my-secret-key"  # pragma: allowlist secret


class TestFirecrawlClientHeaders:
    """Tests for HTTP headers configuration."""

    def test_headers_include_bearer_token(self) -> None:
        """Headers should include Bearer token in Authorization."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_headers_include_content_type(self) -> None:
        """Headers should include JSON content type."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_accept(self) -> None:
        """Headers should include Accept header."""
        client = FirecrawlClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestScrapePage:
    """Tests for scrape_page method."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_scrape_page_success(self, client: FirecrawlClient) -> None:
        """Should scrape page successfully."""
        mock_response = {
            "data": {
                "url": "https://example.com",
                "content": "Example content",
                "markdown": "# Example",
                "title": "Example Page",
                "description": "Example description",
                "links": ["https://example.com/about"],
                "images": ["https://example.com/image.jpg"],
                "metadata": {"title": "Example Page"},
                "statusCode": 200,
            }
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.scrape_page(url="https://example.com")

            assert isinstance(result, ScrapedPage)
            assert result.url == "https://example.com"
            assert result.content == "Example content"
            assert result.title == "Example Page"
            assert result.status_code == 200

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/scrape"
            assert call_args[1]["json"]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_scrape_page_with_options(self, client: FirecrawlClient) -> None:
        """Should pass scraping options to API."""
        mock_response = {
            "data": {
                "url": "https://example.com",
                "content": "Content",
            }
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.scrape_page(
                url="https://example.com",
                include_tags=["h1", "p"],
                only_main_content=True,
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["includeTags"] == ["h1", "p"]
            assert payload["onlyMainContent"] is True

    @pytest.mark.asyncio
    async def test_scrape_page_raises_on_error(self, client: FirecrawlClient) -> None:
        """Should raise FirecrawlError on API error."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")
            with pytest.raises(FirecrawlError):
                await client.scrape_page(url="https://example.com")


class TestCrawlWebsite:
    """Tests for crawl_website method."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_crawl_website_success(self, client: FirecrawlClient) -> None:
        """Should start crawl job successfully."""
        mock_response = {
            "job": {
                "id": "job-123",
                "status": "active",
                "urlsCrawled": 0,
                "urlsFound": 0,
            }
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.crawl_website(url="https://example.com", max_pages=10)

            assert isinstance(result, CrawlJob)
            assert result.job_id == "job-123"
            assert result.status == "active"
            assert result.is_running is True

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/crawl"
            assert call_args[1]["json"]["url"] == "https://example.com"
            assert call_args[1]["json"]["maxPages"] == 10

    @pytest.mark.asyncio
    async def test_crawl_website_with_options(self, client: FirecrawlClient) -> None:
        """Should pass crawl options to API."""
        mock_response = {
            "job": {
                "id": "job-123",
                "status": "active",
            }
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.crawl_website(
                url="https://example.com",
                max_pages=50,
                include_paths=["/blog", "/docs"],
                exclude_paths=["/admin"],
                max_depth=3,
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["maxPages"] == 50
            assert payload["includePaths"] == ["/blog", "/docs"]
            assert payload["excludePaths"] == ["/admin"]
            assert payload["maxDepth"] == 3

    @pytest.mark.asyncio
    async def test_crawl_website_raises_on_error(self, client: FirecrawlClient) -> None:
        """Should raise FirecrawlError on API error."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")
            with pytest.raises(FirecrawlError):
                await client.crawl_website(url="https://example.com")


class TestGetCrawlStatus:
    """Tests for get_crawl_status method."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_crawl_status_success(self, client: FirecrawlClient) -> None:
        """Should get crawl status successfully."""
        mock_response = {
            "job": {
                "id": "job-123",
                "status": "completed",
                "urlsCrawled": 10,
                "urlsFound": 15,
                "data": [
                    {
                        "url": "https://example.com",
                        "content": "Page 1",
                    }
                ],
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_crawl_status(job_id="job-123")

            assert isinstance(result, CrawlJob)
            assert result.job_id == "job-123"
            assert result.status == "completed"
            assert result.is_complete is True
            assert result.urls_crawled == 10
            assert result.urls_found == 15
            assert len(result.data) == 1

            mock_get.assert_called_once_with("/crawl/status/job-123")

    @pytest.mark.asyncio
    async def test_get_crawl_status_raises_on_error(self, client: FirecrawlClient) -> None:
        """Should raise FirecrawlError on API error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(FirecrawlError):
                await client.get_crawl_status(job_id="job-123")


class TestSearch:
    """Tests for search method."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_search_success(self, client: FirecrawlClient) -> None:
        """Should search and return results successfully."""
        mock_response = {
            "data": [
                {
                    "url": "https://example.com/page1",
                    "content": "Content 1",
                },
                {
                    "url": "https://example.com/page2",
                    "content": "Content 2",
                },
            ]
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await client.search(query="test query")

            assert len(results) == 2
            assert all(isinstance(r, ScrapedPage) for r in results)
            assert results[0].url == "https://example.com/page1"
            assert results[1].url == "https://example.com/page2"

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/search"
            assert call_args[1]["json"]["query"] == "test query"

    @pytest.mark.asyncio
    async def test_search_raises_on_error(self, client: FirecrawlClient) -> None:
        """Should raise FirecrawlError on API error."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")
            with pytest.raises(FirecrawlError):
                await client.search(query="test")


class TestScrapedPage:
    """Tests for ScrapedPage dataclass."""

    def test_has_content_with_content(self) -> None:
        """Should return True when content exists."""
        page = ScrapedPage(
            url="https://example.com",
            content="Some content",
        )
        assert page.has_content is True

    def test_has_content_with_markdown(self) -> None:
        """Should return True when markdown exists."""
        page = ScrapedPage(
            url="https://example.com",
            content="",
            markdown="# Title",
        )
        assert page.has_content is True

    def test_has_content_with_html(self) -> None:
        """Should return True when HTML exists."""
        page = ScrapedPage(
            url="https://example.com",
            content="",
            html="<html>",
        )
        assert page.has_content is True

    def test_has_content_without_content(self) -> None:
        """Should return False when no content exists."""
        page = ScrapedPage(
            url="https://example.com",
            content="",
        )
        assert page.has_content is False


class TestCrawlJob:
    """Tests for CrawlJob dataclass."""

    def test_is_complete_with_completed(self) -> None:
        """Should return True for completed status."""
        job = CrawlJob(job_id="job-123", status="completed")
        assert job.is_complete is True

    def test_is_complete_with_failed(self) -> None:
        """Should return True for failed status."""
        job = CrawlJob(job_id="job-123", status="failed")
        assert job.is_complete is True

    def test_is_complete_with_cancelled(self) -> None:
        """Should return True for cancelled status."""
        job = CrawlJob(job_id="job-123", status="cancelled")
        assert job.is_complete is True

    def test_is_complete_with_active(self) -> None:
        """Should return False for active status."""
        job = CrawlJob(job_id="job-123", status="active")
        assert job.is_complete is False

    def test_is_running_with_active(self) -> None:
        """Should return True for active status."""
        job = CrawlJob(job_id="job-123", status="active")
        assert job.is_running is True

    def test_is_running_with_queued(self) -> None:
        """Should return True for queued status."""
        job = CrawlJob(job_id="job-123", status="queued")
        assert job.is_running is True

    def test_is_running_with_completed(self) -> None:
        """Should return False for completed status."""
        job = CrawlJob(job_id="job-123", status="completed")
        assert job.is_running is False


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: FirecrawlClient) -> None:
        """Should return healthy status when API responds."""
        mock_response = {"status": "ok"}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.health_check()

            assert result["name"] == "firecrawl"
            assert result["healthy"] is True
            assert "API is healthy" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: FirecrawlClient) -> None:
        """Should return unhealthy status when API fails."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.health_check()

            assert result["name"] == "firecrawl"
            assert result["healthy"] is False
            assert "failed" in result["message"].lower()


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> FirecrawlClient:
        """Create client for testing."""
        return FirecrawlClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self, client: FirecrawlClient) -> None:
        """Should handle 401 authentication errors."""
        from src.integrations.base import AuthenticationError

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = AuthenticationError("Invalid API key")

            with pytest.raises(AuthenticationError):
                await client.scrape_page(url="https://example.com")

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, client: FirecrawlClient) -> None:
        """Should handle 429 rate limit errors."""
        from src.integrations.base import RateLimitError

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RateLimitError("Rate limit exceeded")

            with pytest.raises(RateLimitError):
                await client.scrape_page(url="https://example.com")

    @pytest.mark.asyncio
    async def test_handles_payment_required_error(self, client: FirecrawlClient) -> None:
        """Should handle 402 payment required errors."""
        from src.integrations.base import PaymentRequiredError

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = PaymentRequiredError("Insufficient credits")

            with pytest.raises(PaymentRequiredError):
                await client.scrape_page(url="https://example.com")
