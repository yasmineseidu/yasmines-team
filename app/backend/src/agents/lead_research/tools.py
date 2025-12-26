"""SDK MCP Tools for Lead Research Agent.

Provides Claude Agent SDK @tool decorated functions for:
- search_linkedin_posts: Search for lead's LinkedIn posts
- search_linkedin_profile: Search for lead's LinkedIn profile
- search_articles_authored: Search for articles written by lead
- search_podcast_appearances: Search for podcast appearances (Tier A only)

Per LEARN-003: Tools must be self-contained - no dependency injection.
Per LEARN-005: WebSearch ignores site: operators - use natural language.
"""

import logging
import os
import time
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


# =============================================================================
# Search Tools
# =============================================================================


@tool(
    name="search_linkedin_posts",
    description=(
        "Search for a person's recent LinkedIn posts using natural language. "
        "Returns post content, dates, and topics. "
        "Note: Uses natural language queries, not site: operators."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "title": str,
        "company_name": str,
        "max_results": int,
    },
)
async def search_linkedin_posts_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for searching LinkedIn posts.

    Uses Tavily/Serper for web search with natural language queries.
    Per LEARN-005: WebSearch ignores site: operators.

    Args:
        args: Tool arguments with name, title, company, max_results.

    Returns:
        Tool result with LinkedIn posts found.
    """
    start_time = time.time()

    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    title = args.get("title", "")
    _company_name = args.get("company_name", "")  # Reserved for future use
    max_results = args.get("max_results", 5)
    _ = _company_name  # Silence unused variable warning

    if not first_name or not last_name:
        return {
            "content": [{"type": "text", "text": "first_name and last_name are required"}],
            "is_error": True,
        }

    try:
        # Import inside function per LEARN-003
        from src.integrations.tavily import TavilyClient, TavilyError

        # Natural language query (no site: operators per LEARN-005)
        query = f"{first_name} {last_name} linkedin posts recent"
        if title:
            query += f" {title}"

        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "TAVILY_API_KEY not configured"}],
                "is_error": True,
            }

        async with TavilyClient(api_key=api_key) as client:
            result = await client.search(  # type: ignore[attr-defined]
                query=query,
                max_results=max_results,
                include_raw_content=True,
            )

        # Parse results for LinkedIn posts
        posts = []
        for item in result.results:
            # Check if it's likely a LinkedIn post
            if "linkedin" in item.url.lower():
                posts.append(
                    {
                        "content": item.content[:500] if item.content else "",
                        "url": item.url,
                        "title": item.title,
                        "score": item.score,
                    }
                )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(posts)} LinkedIn posts for {first_name} {last_name}",
                }
            ],
            "data": {
                "posts": posts,
                "query": query,
                "total_results": len(result.results),
                "linkedin_results": len(posts),
                "processing_time_ms": processing_time_ms,
                "cost": 0.001,  # Tavily cost per call
            },
        }

    except TavilyError as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search failed: {e.message}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"LinkedIn posts search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search error: {e}"}],
            "is_error": True,
        }


@tool(
    name="search_linkedin_profile",
    description=(
        "Search for a person's LinkedIn profile to extract headline and about section. "
        "Returns profile headline, summary, and experience info."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "title": str,
        "company_name": str,
    },
)
async def search_linkedin_profile_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for searching LinkedIn profile.

    Args:
        args: Tool arguments with name, title, company.

    Returns:
        Tool result with profile information.
    """
    start_time = time.time()

    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    title = args.get("title", "")
    company_name = args.get("company_name", "")

    if not first_name or not last_name:
        return {
            "content": [{"type": "text", "text": "first_name and last_name are required"}],
            "is_error": True,
        }

    try:
        # Import inside function per LEARN-003
        from src.integrations.serper import SerperClient, SerperError

        # Natural language query
        query = f"{first_name} {last_name} linkedin profile"
        if title:
            query += f" {title}"
        if company_name:
            query += f" {company_name}"

        api_key = os.getenv("SERPER_API_KEY", "")
        if not api_key:
            # Fallback to Tavily
            return await _search_profile_with_tavily(
                first_name, last_name, title, company_name, start_time
            )

        async with SerperClient(api_key=api_key) as client:
            result = await client.search(  # type: ignore[attr-defined]
                query=query, num_results=5
            )

        # Find LinkedIn profile result
        profile_data = {
            "headline": None,
            "about": None,
            "experience": None,
            "url": None,
        }

        for item in result.organic_results:
            if "linkedin.com/in/" in item.link.lower():
                profile_data["url"] = item.link
                profile_data["headline"] = item.title
                profile_data["about"] = item.snippet
                break

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Found LinkedIn profile for {first_name} {last_name}"
                        if profile_data["url"]
                        else f"No LinkedIn profile found for {first_name} {last_name}"
                    ),
                }
            ],
            "data": {
                "profile": profile_data,
                "query": query,
                "processing_time_ms": processing_time_ms,
                "cost": 0.001,
            },
        }

    except SerperError as e:
        logger.error(f"Serper search failed: {e}")
        # Fallback to Tavily
        return await _search_profile_with_tavily(
            first_name, last_name, title, company_name, start_time
        )
    except Exception as e:
        logger.error(f"LinkedIn profile search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search error: {e}"}],
            "is_error": True,
        }


async def _search_profile_with_tavily(
    first_name: str,
    last_name: str,
    title: str,
    company_name: str,
    start_time: float,
) -> dict[str, Any]:
    """Fallback to Tavily for profile search."""
    try:
        from src.integrations.tavily import TavilyClient

        query = f"{first_name} {last_name} linkedin profile"
        if title:
            query += f" {title}"

        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "No search API configured"}],
                "is_error": True,
            }

        async with TavilyClient(api_key=api_key) as client:
            result = await client.search(  # type: ignore[attr-defined]
                query=query, max_results=5
            )

        profile_data = {
            "headline": None,
            "about": None,
            "url": None,
        }

        for item in result.results:
            if "linkedin.com/in/" in item.url.lower():
                profile_data["url"] = item.url
                profile_data["headline"] = item.title
                profile_data["about"] = item.content
                break

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Found LinkedIn profile (via Tavily) for {first_name} {last_name}"
                        if profile_data["url"]
                        else f"No LinkedIn profile found for {first_name} {last_name}"
                    ),
                }
            ],
            "data": {
                "profile": profile_data,
                "query": query,
                "processing_time_ms": processing_time_ms,
                "cost": 0.001,
            },
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Tavily fallback failed: {e}"}],
            "is_error": True,
        }


@tool(
    name="search_articles_authored",
    description=(
        "Search for articles written or authored by a person. "
        "Returns article titles, publications, and key points."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "title": str,
        "max_results": int,
    },
)
async def search_articles_authored_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for searching articles authored by lead.

    Args:
        args: Tool arguments with name, title, max_results.

    Returns:
        Tool result with articles found.
    """
    start_time = time.time()

    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    _title = args.get("title", "")  # Reserved for future use
    max_results = args.get("max_results", 3)
    del _title  # Silence unused variable warning

    if not first_name or not last_name:
        return {
            "content": [{"type": "text", "text": "first_name and last_name are required"}],
            "is_error": True,
        }

    try:
        from src.integrations.tavily import TavilyClient, TavilyError

        # Quote name for exact match
        query = f'"{first_name} {last_name}" article author'

        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "TAVILY_API_KEY not configured"}],
                "is_error": True,
            }

        async with TavilyClient(api_key=api_key) as client:
            result = await client.search(  # type: ignore[attr-defined]
                query=query,
                max_results=max_results,
                include_raw_content=True,
            )

        articles = []
        for item in result.results:
            # Filter out LinkedIn results (we have a separate tool for that)
            if "linkedin" not in item.url.lower():
                articles.append(
                    {
                        "title": item.title,
                        "url": item.url,
                        "content": item.content[:300] if item.content else "",
                        "publication": _extract_publication(item.url),
                        "score": item.score,
                    }
                )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(articles)} articles by {first_name} {last_name}",
                }
            ],
            "data": {
                "articles": articles,
                "query": query,
                "processing_time_ms": processing_time_ms,
                "cost": 0.001,
            },
        }

    except TavilyError as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search failed: {e.message}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Article search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search error: {e}"}],
            "is_error": True,
        }


def _extract_publication(url: str) -> str | None:
    """Extract publication name from URL."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove TLD for common patterns
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[0].replace("-", " ").title()
        return domain
    except Exception:
        return None


@tool(
    name="search_podcast_appearances",
    description=(
        "Search for podcast appearances and interviews of a person. "
        "Tier A leads only. Returns podcast names, episode titles, and dates."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "title": str,
        "max_results": int,
    },
)
async def search_podcast_appearances_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for searching podcast appearances (Tier A only).

    Args:
        args: Tool arguments with name, title, max_results.

    Returns:
        Tool result with podcast appearances found.
    """
    start_time = time.time()

    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    _title = args.get("title", "")  # Reserved for future use
    max_results = args.get("max_results", 3)
    del _title  # Silence unused variable warning

    if not first_name or not last_name:
        return {
            "content": [{"type": "text", "text": "first_name and last_name are required"}],
            "is_error": True,
        }

    try:
        from src.integrations.tavily import TavilyClient, TavilyError

        # Search for podcast appearances
        query = f'"{first_name} {last_name}" podcast interview guest'

        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "TAVILY_API_KEY not configured"}],
                "is_error": True,
            }

        async with TavilyClient(api_key=api_key) as client:
            result = await client.search(  # type: ignore[attr-defined]
                query=query,
                max_results=max_results,
                include_raw_content=True,
            )

        podcasts = []
        podcast_keywords = ["podcast", "episode", "interview", "guest", "show"]

        for item in result.results:
            # Check if it's likely a podcast result
            is_podcast = any(kw in item.title.lower() for kw in podcast_keywords) or any(
                kw in item.url.lower() for kw in podcast_keywords
            )

            if is_podcast:
                podcasts.append(
                    {
                        "title": item.title,
                        "url": item.url,
                        "content": item.content[:300] if item.content else "",
                        "podcast_name": _extract_publication(item.url),
                        "score": item.score,
                    }
                )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Found {len(podcasts)} podcast appearances for {first_name} {last_name}"
                    ),
                }
            ],
            "data": {
                "podcasts": podcasts,
                "query": query,
                "processing_time_ms": processing_time_ms,
                "cost": 0.001,
            },
        }

    except TavilyError as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search failed: {e.message}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Podcast search failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Search error: {e}"}],
            "is_error": True,
        }


@tool(
    name="analyze_headline",
    description=(
        "Analyze a lead's headline and title for personalization hooks. "
        "Basic research for Tier C leads."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "title": str,
        "headline": str,
        "company_name": str,
    },
)
async def analyze_headline_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for analyzing headline (basic research for Tier C).

    This tool doesn't make API calls - it analyzes the existing headline
    to generate personalization hooks.

    Args:
        args: Tool arguments with name, title, headline, company.

    Returns:
        Tool result with headline analysis.
    """
    start_time = time.time()

    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    title = args.get("title", "")
    headline = args.get("headline", "")
    company_name = args.get("company_name", "")

    # Extract keywords and potential hooks from headline
    keywords = []
    hooks = []

    text_to_analyze = f"{title} {headline}".lower()

    # Common role-based hooks
    role_hooks = {
        "ceo": "leading your company",
        "founder": "building your company",
        "cto": "leading technology",
        "vp": "driving growth",
        "director": "leading your team",
        "head of": "heading up",
        "manager": "managing",
    }

    for role, hook in role_hooks.items():
        if role in text_to_analyze:
            hooks.append(f"{hook} at {company_name}" if company_name else hook)
            keywords.append(role)

    # Extract other keywords
    tech_keywords = [
        "ai",
        "machine learning",
        "data",
        "cloud",
        "saas",
        "marketing",
        "sales",
        "growth",
        "product",
        "engineering",
    ]
    for kw in tech_keywords:
        if kw in text_to_analyze:
            keywords.append(kw)

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Analyzed headline for {first_name} {last_name}: found {len(keywords)} keywords",
            }
        ],
        "data": {
            "keywords": keywords,
            "hooks": hooks,
            "title": title,
            "headline": headline,
            "processing_time_ms": processing_time_ms,
            "cost": 0.0,  # No API cost
        },
    }


# =============================================================================
# Tool List for Agent Registration
# =============================================================================

# Export list of tools for easy registration with SDK MCP server
LEAD_RESEARCH_TOOLS = [
    search_linkedin_posts_tool,
    search_linkedin_profile_tool,
    search_articles_authored_tool,
    search_podcast_appearances_tool,
    analyze_headline_tool,
]
