"""Sample data fixtures for Tavily API testing."""

from typing import Any

# Sample data for /search endpoint
SEARCH_SAMPLE_DATA = {
    "basic_search": {
        "query": "best CRM software 2024",
        "max_results": 3,
        "search_depth": "basic",
    },
    "advanced_search": {
        "query": "AI trends 2025 machine learning",
        "search_depth": "advanced",
        "max_results": 5,
        "include_answer": "advanced",
        "include_raw_content": "markdown",
        "include_images": True,
    },
    "news_search": {
        "query": "latest technology news",
        "topic": "news",
        "time_range": "week",
        "max_results": 3,
    },
    "finance_search": {
        "query": "stock market trends",
        "topic": "finance",
        "max_results": 3,
    },
    "domain_filtered_search": {
        "query": "Python documentation",
        "include_domains": ["python.org", "docs.python.org"],
        "max_results": 3,
    },
}

# Sample data for /extract endpoint
EXTRACT_SAMPLE_DATA = {
    "basic_extract": {
        "urls": [
            "https://docs.python.org/3/",
        ],
    },
    "extract_with_raw_content": {
        "urls": [
            "https://www.python.org/about/",
        ],
        "include_raw_content": True,
    },
}

# Sample data for /crawl endpoint
CRAWL_SAMPLE_DATA = {
    "basic_crawl": {
        "url": "https://docs.python.org",
        "max_depth": 1,
        "limit": 5,
    },
    "crawl_with_instructions": {
        "url": "https://docs.tavily.com",
        "instructions": "Find all documentation pages",
        "max_depth": 2,
        "limit": 10,
        "extract_depth": "basic",
        "format": "markdown",
    },
    "crawl_with_filters": {
        "url": "https://docs.python.org",
        "max_depth": 1,
        "limit": 5,
        "select_paths": ["/3/"],
        "exclude_paths": ["/2/"],
        "allow_external": False,
    },
}

# Sample data for /map endpoint
MAP_SAMPLE_DATA = {
    "basic_map": {
        "url": "https://docs.python.org",
        "max_depth": 1,
        "limit": 10,
    },
    "map_with_instructions": {
        "url": "https://docs.tavily.com",
        "instructions": "Map all documentation sections",
        "max_depth": 2,
        "limit": 20,
    },
    "map_with_filters": {
        "url": "https://docs.python.org",
        "max_depth": 1,
        "limit": 10,
        "exclude_paths": ["/2/"],
        "allow_external": False,
    },
}

# Sample data for /research endpoint (async research task)
RESEARCH_SAMPLE_DATA = {
    "mini_research": {
        "input": "What are the benefits of TypeScript over JavaScript?",
        "model": "mini",
        "citation_format": "numbered",
    },
    "pro_research": {
        "input": "Compare top 3 CRM platforms for small business",
        "model": "pro",
        "citation_format": "apa",
    },
    "auto_research": {
        "input": "Explain quantum computing for beginners",
        "model": "auto",
        "citation_format": "numbered",
    },
}

# Expected response schemas for validation
EXPECTED_SCHEMAS = {
    "search_response": {
        "required_fields": ["query", "results", "response_time"],
        "result_fields": ["title", "url", "content", "score"],
    },
    "extract_response": {
        "required_fields": ["results"],
    },
    "crawl_response": {
        "required_fields": ["base_url", "results", "response_time"],
        "result_fields": ["url"],
    },
    "map_response": {
        "required_fields": ["base_url", "results", "response_time"],
    },
    "usage_response": {
        "required_fields": ["credits_used"],
    },
    "research_task": {
        "required_fields": ["request_id", "status", "input", "model", "created_at"],
    },
}


def get_sample_data(endpoint: str, scenario: str = "basic") -> dict[str, Any]:
    """
    Get sample data for a specific endpoint and scenario.

    Args:
        endpoint: API endpoint (search, extract, crawl, map, research)
        scenario: Specific scenario (basic, advanced, etc.)

    Returns:
        Dictionary with sample request parameters

    Raises:
        ValueError: If endpoint or scenario not found
    """
    endpoint_data = {
        "search": SEARCH_SAMPLE_DATA,
        "extract": EXTRACT_SAMPLE_DATA,
        "crawl": CRAWL_SAMPLE_DATA,
        "map": MAP_SAMPLE_DATA,
        "research": RESEARCH_SAMPLE_DATA,
    }

    if endpoint not in endpoint_data:
        raise ValueError(f"Unknown endpoint: {endpoint}")

    data = endpoint_data[endpoint]

    # Try specific scenario first, fallback to first available
    if scenario in data:
        return data[scenario]
    elif f"{scenario}_{endpoint}" in data:
        return data[f"{scenario}_{endpoint}"]
    else:
        # Return first available scenario
        return list(data.values())[0]


def get_expected_schema(response_type: str) -> dict[str, Any]:
    """
    Get expected response schema for validation.

    Args:
        response_type: Type of response (search_response, crawl_response, etc.)

    Returns:
        Dictionary with expected schema

    Raises:
        ValueError: If response_type not found
    """
    if response_type not in EXPECTED_SCHEMAS:
        raise ValueError(f"Unknown response type: {response_type}")

    return EXPECTED_SCHEMAS[response_type]
