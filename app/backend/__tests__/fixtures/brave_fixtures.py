"""
Test fixtures for Brave Search API integration.

Provides mock responses, test data, and helper fixtures for testing
the BraveClient and related functionality.
"""

from typing import Any


def create_web_search_response(
    query: str = "test query",
    num_results: int = 3,
    include_infobox: bool = False,
    include_faq: bool = False,
    include_news: bool = False,
    include_videos: bool = False,
) -> dict[str, Any]:
    """
    Create a mock web search response.

    Args:
        query: Search query for the response
        num_results: Number of web results to include
        include_infobox: Include infobox in response
        include_faq: Include FAQ results
        include_news: Include news results
        include_videos: Include video results

    Returns:
        Mock web search API response
    """
    response: dict[str, Any] = {
        "query": {
            "original": query,
            "show_strict_warning": False,
            "is_navigational": False,
            "local_decision": "drop",
            "spellcheck_off": True,
            "country": "us",
            "language": "en",
        },
        "web": {
            "type": "search",
            "results": [
                {
                    "title": f"Result {i + 1} for {query}",
                    "url": f"https://example{i + 1}.com/page",
                    "description": f"This is the description for result {i + 1}.",
                    "age": f"{i + 1} days ago",
                    "page_age": "2025-01-01T00:00:00Z",
                    "family_friendly": True,
                    "extra_snippets": [f"Extra snippet {i + 1}"],
                    "deep_results": [],
                }
                for i in range(num_results)
            ],
            "family_friendly": True,
        },
    }

    if include_infobox:
        response["infobox"] = {
            "type": "infobox",
            "results": [
                {
                    "title": f"Infobox for {query}",
                    "description": "This is an infobox description.",
                    "type": "entity",
                    "url": "https://example.com/infobox",
                    "thumbnail": {"src": "https://example.com/thumb.jpg"},
                    "long_desc": "This is a longer description.",
                    "attributes": [
                        {"label": "Founded", "value": "2020"},
                        {"label": "Location", "value": "San Francisco"},
                    ],
                }
            ],
        }

    if include_faq:
        response["faq"] = {
            "type": "faq",
            "results": [
                {
                    "question": f"What is {query}?",
                    "answer": f"This is the answer about {query}.",
                    "url": "https://example.com/faq",
                    "title": "FAQ Page",
                }
            ],
        }

    if include_news:
        response["news"] = {
            "type": "news",
            "results": [
                {
                    "title": f"News about {query}",
                    "url": "https://news.example.com/article",
                    "description": "Latest news description.",
                    "age": "2 hours ago",
                    "page_age": "2025-01-15T12:00:00Z",
                    "meta_url": {"hostname": "news.example.com"},
                    "thumbnail": {"src": "https://news.example.com/thumb.jpg"},
                }
            ],
        }

    if include_videos:
        response["videos"] = {
            "type": "videos",
            "results": [
                {
                    "title": f"Video about {query}",
                    "url": "https://youtube.com/watch?v=12345",
                    "description": "Video description.",
                    "age": "1 week ago",
                    "thumbnail": {"src": "https://youtube.com/thumb.jpg"},
                    "video": {
                        "duration": "10:30",
                        "creator": "Creator Name",
                        "publisher": "YouTube",
                        "views": "1M views",
                    },
                }
            ],
        }

    return response


def create_news_search_response(
    query: str = "test news",
    num_results: int = 3,
) -> dict[str, Any]:
    """
    Create a mock news search response.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        Mock news search API response
    """
    return {
        "query": {
            "original": query,
            "country": "us",
            "language": "en",
        },
        "results": [
            {
                "title": f"News Article {i + 1}: {query}",
                "url": f"https://news{i + 1}.example.com/article",
                "description": f"News description for article {i + 1}.",
                "age": f"{i + 1} hours ago",
                "page_age": "2025-01-15T12:00:00Z",
                "meta_url": {"hostname": f"news{i + 1}.example.com"},
                "thumbnail": {"src": f"https://news{i + 1}.example.com/thumb.jpg"},
            }
            for i in range(num_results)
        ],
    }


def create_images_search_response(
    query: str = "test images",
    num_results: int = 3,
) -> dict[str, Any]:
    """
    Create a mock images search response.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        Mock images search API response
    """
    return {
        "query": {
            "original": query,
            "country": "us",
            "language": "en",
        },
        "results": [
            {
                "title": f"Image {i + 1}: {query}",
                "url": f"https://images.example.com/img{i + 1}.jpg",
                "thumbnail": {"src": f"https://images.example.com/thumb{i + 1}.jpg"},
                "source": f"example{i + 1}.com",
                "page_url": f"https://example{i + 1}.com/page",
                "properties": {
                    "url": f"https://example{i + 1}.com/page",
                    "width": 1920,
                    "height": 1080,
                },
            }
            for i in range(num_results)
        ],
    }


def create_videos_search_response(
    query: str = "test videos",
    num_results: int = 3,
) -> dict[str, Any]:
    """
    Create a mock videos search response.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        Mock videos search API response
    """
    return {
        "query": {
            "original": query,
            "country": "us",
            "language": "en",
        },
        "results": [
            {
                "title": f"Video {i + 1}: {query}",
                "url": f"https://youtube.com/watch?v={i + 1}",
                "description": f"Video description {i + 1}.",
                "age": f"{i + 1} days ago",
                "thumbnail": {"src": f"https://youtube.com/thumb{i + 1}.jpg"},
                "video": {
                    "duration": f"{i + 5}:30",
                    "creator": f"Creator {i + 1}",
                    "publisher": "YouTube",
                    "views": f"{(i + 1) * 100}K views",
                },
            }
            for i in range(num_results)
        ],
    }


def create_suggest_response(
    query: str = "test",
    num_suggestions: int = 5,
) -> dict[str, Any]:
    """
    Create a mock suggest/autocomplete response.

    Args:
        query: Original query
        num_suggestions: Number of suggestions

    Returns:
        Mock suggest API response (dict format)
    """
    return {
        "query": query,
        "results": [f"{query} suggestion {i + 1}" for i in range(num_suggestions)],
    }


def create_error_response(
    error_type: str = "RateLimitReached",
    message: str = "Rate limit exceeded",
    status_code: int = 429,
) -> dict[str, Any]:
    """
    Create a mock error response.

    Args:
        error_type: Type of error
        message: Error message
        status_code: HTTP status code

    Returns:
        Mock error response
    """
    return {
        "type": error_type,
        "message": message,
        "status": status_code,
    }


# Pre-built fixtures for common test scenarios
MOCK_WEB_SEARCH_RESPONSE = create_web_search_response(
    query="AI companies",
    num_results=5,
    include_infobox=True,
    include_faq=True,
)

MOCK_WEB_SEARCH_SIMPLE = create_web_search_response(
    query="simple search",
    num_results=3,
)

MOCK_NEWS_SEARCH_RESPONSE = create_news_search_response(
    query="tech news",
    num_results=5,
)

MOCK_IMAGES_SEARCH_RESPONSE = create_images_search_response(
    query="nature photos",
    num_results=5,
)

MOCK_VIDEOS_SEARCH_RESPONSE = create_videos_search_response(
    query="tutorials",
    num_results=5,
)

MOCK_SUGGEST_RESPONSE = create_suggest_response(
    query="python",
    num_suggestions=5,
)

MOCK_EMPTY_RESPONSE: dict[str, Any] = {
    "query": {"original": "no results query"},
    "web": {"type": "search", "results": []},
}

MOCK_RATE_LIMIT_ERROR = create_error_response(
    error_type="RateLimitReached",
    message="Rate limit exceeded. Please try again later.",
    status_code=429,
)

MOCK_AUTH_ERROR = create_error_response(
    error_type="Unauthorized",
    message="Invalid API key",
    status_code=401,
)
