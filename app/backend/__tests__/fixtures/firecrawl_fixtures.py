"""
Test fixtures for Firecrawl API integration.

Provides mock responses, test data, and helper fixtures for testing
the FirecrawlClient and related functionality.
"""

from typing import Any


def create_scrape_response(
    url: str = "https://example.com",
    include_metadata: bool = True,
    include_links: bool = True,
    include_images: bool = True,
) -> dict[str, Any]:
    """
    Create a mock scrape response.

    Args:
        url: URL that was scraped
        include_metadata: Include metadata in response
        include_links: Include links in response
        include_images: Include images in response

    Returns:
        Mock scrape API response
    """
    response: dict[str, Any] = {
        "data": {
            "url": url,
            "content": "This is the main content of the page. It contains important information about the topic.",
            "markdown": "# Example Page\n\nThis is the main content of the page.",
            "html": "<html><head><title>Example Page</title></head><body><h1>Example Page</h1><p>This is the main content.</p></body></html>",
            "statusCode": 200,
        }
    }

    if include_metadata:
        response["data"]["metadata"] = {
            "title": "Example Page",
            "description": "This is an example page for testing",
            "author": "Test Author",
            "keywords": ["test", "example", "sample"],
            "ogTitle": "Example Page",
            "ogDescription": "This is an example page for testing",
            "ogImage": "https://example.com/image.jpg",
        }
        response["data"]["title"] = "Example Page"
        response["data"]["description"] = "This is an example page for testing"
        response["data"]["author"] = "Test Author"

    if include_links:
        response["data"]["links"] = [
            "https://example.com/about",
            "https://example.com/contact",
            "https://example.com/blog",
        ]

    if include_images:
        response["data"]["images"] = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.png",
        ]

    return response


def create_crawl_job_response(
    job_id: str = "job-123",
    status: str = "active",
    urls_crawled: int = 0,
    urls_found: int = 5,
    include_data: bool = False,
) -> dict[str, Any]:
    """
    Create a mock crawl job response.

    Args:
        job_id: Crawl job ID
        status: Job status (active, completed, failed, etc.)
        urls_crawled: Number of URLs crawled
        urls_found: Number of URLs found
        include_data: Include scraped page data

    Returns:
        Mock crawl job API response
    """
    response: dict[str, Any] = {
        "job": {
            "id": job_id,
            "status": status,
            "urlsCrawled": urls_crawled,
            "urlsFound": urls_found,
        }
    }

    if include_data:
        response["job"]["data"] = [
            {
                "url": "https://example.com/page1",
                "content": "Content from page 1",
                "statusCode": 200,
            },
            {
                "url": "https://example.com/page2",
                "content": "Content from page 2",
                "statusCode": 200,
            },
        ]

    return response


def create_search_response(
    query: str = "test query",
    num_results: int = 3,
) -> dict[str, Any]:
    """
    Create a mock search response.

    Args:
        query: Search query
        num_results: Number of results to include

    Returns:
        Mock search API response
    """
    return {
        "data": [
            {
                "url": f"https://example.com/result{i + 1}",
                "content": f"Content for result {i + 1} matching query: {query}",
                "title": f"Result {i + 1}",
                "statusCode": 200,
            }
            for i in range(num_results)
        ]
    }


# Sample test URLs for live testing
SAMPLE_URLS = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://httpbin.org/json",
    "https://www.wikipedia.org",
    "https://github.com",
]

# Sample crawl URLs
SAMPLE_CRAWL_URLS = [
    "https://example.com",
    "https://httpbin.org",
]

# Sample search queries
SAMPLE_SEARCH_QUERIES = [
    "Python web scraping",
    "API documentation",
    "test page",
]

