"""
SDK MCP Tools for Company Research Agent.

Provides Claude Agent SDK @tool decorated functions for:
- search_company_news: Search for recent company news
- search_company_funding: Search for funding/investment info
- search_company_hiring: Search for hiring signals
- search_company_tech: Search for product/tech initiatives
- extract_and_score_facts: Extract and score facts from research
- aggregate_research_results: Aggregate results across companies

Per LEARN-003: Tools must be self-contained - no dependency injection.
However, rate limiters and circuit breakers are module-level singletons
to maintain state across calls (otherwise they're useless).

Note on return format: Tools return {"content": [...], "data": {...}}.
The "data" key is an internal extension for direct-call mode, containing
structured data for the agent. When used via Claude SDK MCP, only "content"
is processed by Claude.
"""

import logging
import os
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import tool

if TYPE_CHECKING:
    from src.integrations.serper import SerperClient
    from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# =============================================================================
# Module-Level Singletons for Resilience Patterns
# =============================================================================
# These MUST be module-level to maintain state across tool calls.
# Creating new instances per call defeats their purpose entirely.

_serper_rate_limiter: "TokenBucketRateLimiter | None" = None
_serper_circuit_breaker: "CircuitBreaker | None" = None
_serper_client: "SerperClient | None" = None


def _get_serper_rate_limiter() -> "TokenBucketRateLimiter":
    """Get or create the shared Serper rate limiter."""
    global _serper_rate_limiter
    if _serper_rate_limiter is None:
        from src.utils.rate_limiter import TokenBucketRateLimiter

        _serper_rate_limiter = TokenBucketRateLimiter(
            rate_limit=100,  # Serper standard tier: 100 QPS
            rate_window=60,
            service_name="serper",
        )
    return _serper_rate_limiter


def _get_serper_circuit_breaker() -> "CircuitBreaker":
    """Get or create the shared Serper circuit breaker."""
    global _serper_circuit_breaker
    if _serper_circuit_breaker is None:
        from src.utils.rate_limiter import CircuitBreaker

        _serper_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60.0,
            service_name="serper",
        )
    return _serper_circuit_breaker


def _get_serper_client() -> "SerperClient | None":
    """Get or create the shared Serper client (if API key available)."""
    global _serper_client
    serper_api_key = os.environ.get("SERPER_API_KEY", "")
    if not serper_api_key:
        return None
    if _serper_client is None:
        from src.integrations.serper import SerperClient

        _serper_client = SerperClient(api_key=serper_api_key)
    return _serper_client


def reset_resilience_state() -> None:
    """Reset all module-level singletons. Useful for testing."""
    global _serper_rate_limiter, _serper_circuit_breaker, _serper_client
    _serper_rate_limiter = None
    _serper_circuit_breaker = None
    _serper_client = None


# =============================================================================
# Tool Cost Configuration (from YAML)
# =============================================================================

TOOL_COSTS = {
    "serper_search": 0.001,
    "tavily_search": 0.001,
    "perplexity_search": 0.005,
    "web_search": 0.0,  # Built-in Claude web search is free
}

# Scoring weights (from YAML)
SCORING_WEIGHTS = {
    "recency": 0.30,
    "specificity": 0.25,
    "business_relevance": 0.25,
    "emotional_hook": 0.20,
}


# =============================================================================
# Helper Functions
# =============================================================================


def _calculate_recency_score(recency_days: int | None, decay_days: int = 90) -> float:
    """Calculate recency score with exponential decay."""
    if recency_days is None:
        return 0.5  # Unknown recency gets middle score
    if recency_days <= 0:
        return 1.0
    if recency_days >= decay_days:
        return 0.0
    return 1.0 - (recency_days / decay_days)


def _calculate_total_score(
    recency_score: float,
    specificity_score: float,
    business_relevance_score: float,
    emotional_hook_score: float,
) -> float:
    """Calculate weighted total score."""
    return (
        recency_score * SCORING_WEIGHTS["recency"]
        + specificity_score * SCORING_WEIGHTS["specificity"]
        + business_relevance_score * SCORING_WEIGHTS["business_relevance"]
        + emotional_hook_score * SCORING_WEIGHTS["emotional_hook"]
    )


def _get_current_year() -> int:
    """Get current year for search queries."""
    return datetime.now(UTC).year


# =============================================================================
# Search Tools
# =============================================================================


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="search_company_news",
    description=(
        "Search for recent news about a company. "
        "Finds press releases, media coverage, and announcements from the last 6 months. "
        "Uses Serper API for Google News search with circuit breaker protection. "
        "Returns structured search results with headlines, dates, and URLs."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "max_results": int,
    },
)
async def search_company_news_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search for recent company news using Serper API.

    Uses shared rate limiter and circuit breaker for resilience.

    Args:
        args: Tool arguments with company_name, company_domain, max_results.

    Returns:
        Tool result with news search results.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    max_results = args.get("max_results", 5)

    if not company_name:
        return {
            "content": [{"type": "text", "text": "company_name is required"}],
            "is_error": True,
        }

    try:
        # Build search query
        year = _get_current_year()
        query = f"{company_name} news {year}"

        results: list[dict[str, Any]] = []
        tool_used = "serper_search"
        cost = 0.0

        # Use shared client and resilience patterns
        client = _get_serper_client()
        if client is not None:
            circuit_breaker = _get_serper_circuit_breaker()
            rate_limiter = _get_serper_rate_limiter()

            if circuit_breaker.can_proceed():
                try:
                    await rate_limiter.acquire()
                    search_result = await client.search_news(
                        query=query,
                        num=max_results,
                    )
                    circuit_breaker.record_success()

                    # Extract results
                    for item in search_result.news[:max_results]:
                        results.append(
                            {
                                "title": item.title,
                                "snippet": item.snippet,
                                "url": item.link,
                                "date": item.date,
                                "source": item.source,
                            }
                        )

                    cost = TOOL_COSTS["serper_search"]

                except Exception as e:
                    logger.warning(f"Serper news search failed: {e}")
                    circuit_breaker.record_failure()
            else:
                logger.warning("Serper circuit breaker is open, skipping search")
        else:
            logger.debug("SERPER_API_KEY not set, returning empty results")

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"News search for {company_name}: found {len(results)} results "
            f"(tool={tool_used}, cost=${cost:.4f}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(results)} news articles for {company_name}",
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "query": query,
                "results": results,
                "result_count": len(results),
                "tool_used": tool_used,
                "cost": cost,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error searching news for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"News search error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="search_company_funding",
    description=(
        "Search for company funding and investment information. "
        "Finds funding rounds, investments, and financial milestones. "
        "Returns funding amounts, investors, and dates when available."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "max_results": int,
    },
)
async def search_company_funding_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search for company funding/investment information using Serper API.

    Uses shared rate limiter and circuit breaker for resilience.

    Args:
        args: Tool arguments with company_name, company_domain, max_results.

    Returns:
        Tool result with funding search results.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    max_results = args.get("max_results", 5)

    if not company_name:
        return {
            "content": [{"type": "text", "text": "company_name is required"}],
            "is_error": True,
        }

    try:
        # Build search query
        query = f"{company_name} funding investment growth"

        results: list[dict[str, Any]] = []
        tool_used = "serper_search"
        cost = 0.0

        # Use shared client and resilience patterns
        client = _get_serper_client()
        if client is not None:
            circuit_breaker = _get_serper_circuit_breaker()
            rate_limiter = _get_serper_rate_limiter()

            if circuit_breaker.can_proceed():
                try:
                    await rate_limiter.acquire()
                    search_result = await client.search(
                        query=query,
                        num=max_results,
                    )
                    circuit_breaker.record_success()

                    # Extract results
                    for item in search_result.organic[:max_results]:
                        results.append(
                            {
                                "title": item.title,
                                "snippet": item.snippet,
                                "url": item.link,
                                "position": item.position,
                            }
                        )

                    cost = TOOL_COSTS["serper_search"]

                except Exception as e:
                    logger.warning(f"Serper funding search failed: {e}")
                    circuit_breaker.record_failure()
            else:
                logger.warning("Serper circuit breaker is open, skipping search")
        else:
            logger.debug("SERPER_API_KEY not set, returning empty results")

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Funding search for {company_name}: found {len(results)} results "
            f"(tool={tool_used}, cost=${cost:.4f}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(results)} funding-related results for {company_name}",
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "query": query,
                "results": results,
                "result_count": len(results),
                "tool_used": tool_used,
                "cost": cost,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error searching funding for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"Funding search error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="search_company_hiring",
    description=(
        "Search for company hiring signals and job postings. "
        "Finds open positions, team growth indicators, and new hires. "
        "Hiring activity indicates company growth and potential needs."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "max_results": int,
    },
)
async def search_company_hiring_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search for company hiring/jobs information using Serper API.

    Uses shared rate limiter and circuit breaker for resilience.

    Args:
        args: Tool arguments with company_name, company_domain, max_results.

    Returns:
        Tool result with hiring search results.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    max_results = args.get("max_results", 5)

    if not company_name:
        return {
            "content": [{"type": "text", "text": "company_name is required"}],
            "is_error": True,
        }

    try:
        # Build search query
        query = f"{company_name} hiring careers jobs"

        results: list[dict[str, Any]] = []
        tool_used = "serper_search"
        cost = 0.0

        # Use shared client and resilience patterns
        client = _get_serper_client()
        if client is not None:
            circuit_breaker = _get_serper_circuit_breaker()
            rate_limiter = _get_serper_rate_limiter()

            if circuit_breaker.can_proceed():
                try:
                    await rate_limiter.acquire()
                    search_result = await client.search(
                        query=query,
                        num=max_results,
                    )
                    circuit_breaker.record_success()

                    # Extract results
                    for item in search_result.organic[:max_results]:
                        results.append(
                            {
                                "title": item.title,
                                "snippet": item.snippet,
                                "url": item.link,
                                "position": item.position,
                            }
                        )

                    cost = TOOL_COSTS["serper_search"]

                except Exception as e:
                    logger.warning(f"Serper hiring search failed: {e}")
                    circuit_breaker.record_failure()
            else:
                logger.warning("Serper circuit breaker is open, skipping search")
        else:
            logger.debug("SERPER_API_KEY not set, returning empty results")

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Hiring search for {company_name}: found {len(results)} results "
            f"(tool={tool_used}, cost=${cost:.4f}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(results)} hiring-related results for {company_name}",
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "query": query,
                "results": results,
                "result_count": len(results),
                "tool_used": tool_used,
                "cost": cost,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error searching hiring for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"Hiring search error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="search_company_tech",
    description=(
        "Search for company product launches and technology initiatives. "
        "Finds new products, features, services, and tech investments. "
        "Product launches indicate innovation and potential needs."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "max_results": int,
    },
)
async def search_company_tech_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search for company product/tech information using Serper API.

    Uses shared rate limiter and circuit breaker for resilience.

    Args:
        args: Tool arguments with company_name, company_domain, max_results.

    Returns:
        Tool result with tech search results.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    max_results = args.get("max_results", 5)

    if not company_name:
        return {
            "content": [{"type": "text", "text": "company_name is required"}],
            "is_error": True,
        }

    try:
        # Build search query
        query = f"{company_name} product launch technology"

        results: list[dict[str, Any]] = []
        tool_used = "serper_search"
        cost = 0.0

        # Use shared client and resilience patterns
        client = _get_serper_client()
        if client is not None:
            circuit_breaker = _get_serper_circuit_breaker()
            rate_limiter = _get_serper_rate_limiter()

            if circuit_breaker.can_proceed():
                try:
                    await rate_limiter.acquire()
                    search_result = await client.search(
                        query=query,
                        num=max_results,
                    )
                    circuit_breaker.record_success()

                    # Extract results
                    for item in search_result.organic[:max_results]:
                        results.append(
                            {
                                "title": item.title,
                                "snippet": item.snippet,
                                "url": item.link,
                                "position": item.position,
                            }
                        )

                    cost = TOOL_COSTS["serper_search"]

                except Exception as e:
                    logger.warning(f"Serper tech search failed: {e}")
                    circuit_breaker.record_failure()
            else:
                logger.warning("Serper circuit breaker is open, skipping search")
        else:
            logger.debug("SERPER_API_KEY not set, returning empty results")

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Tech search for {company_name}: found {len(results)} results "
            f"(tool={tool_used}, cost=${cost:.4f}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(results)} tech-related results for {company_name}",
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "query": query,
                "results": results,
                "result_count": len(results),
                "tool_used": tool_used,
                "cost": cost,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error searching tech for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"Tech search error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Fact Extraction and Scoring Tool
# =============================================================================


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="extract_and_score_facts",
    description=(
        "Extract and score facts from research results. "
        "Identifies specific facts from search results and scores them by: "
        "recency (30%), specificity (25%), business relevance (25%), emotional hook (20%). "
        "Returns scored facts sorted by total score."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "search_results": list,  # List of search result dicts
    },
)
async def extract_and_score_facts_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and score facts from search results.

    Args:
        args: Tool arguments with company_name, company_domain, search_results.

    Returns:
        Tool result with extracted and scored facts.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    search_results = args.get("search_results", [])

    if not company_name or not search_results:
        return {
            "content": [{"type": "text", "text": "company_name and search_results are required"}],
            "is_error": True,
        }

    try:
        facts: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        for result in search_results:
            # Extract fact from search result
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            date_str = result.get("date", "")
            source = result.get("source", "")
            category = result.get("category", "news")

            if not title and not snippet:
                continue

            fact_text = f"{title}. {snippet}" if snippet else title

            # Calculate recency
            recency_days = None
            fact_date = None
            if date_str:
                try:
                    # Parse various date formats
                    for fmt in ["%Y-%m-%d", "%B %d, %Y", "%d %B %Y", "%Y"]:
                        try:
                            fact_date = datetime.strptime(date_str, fmt).replace(tzinfo=UTC)
                            recency_days = (now - fact_date).days
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # Calculate scores
            recency_score = _calculate_recency_score(recency_days)

            # Heuristic scoring based on content
            specificity_score = 0.5
            if any(char.isdigit() for char in fact_text):
                specificity_score += 0.2
            if "$" in fact_text or "%" in fact_text:
                specificity_score += 0.2
            if len(fact_text) > 100:
                specificity_score += 0.1
            specificity_score = min(1.0, specificity_score)

            # Business relevance based on keywords
            business_keywords = [
                "funding",
                "investment",
                "growth",
                "revenue",
                "customers",
                "launch",
                "partnership",
                "acquisition",
                "hire",
                "expand",
            ]
            business_relevance_score = 0.3
            for keyword in business_keywords:
                if keyword.lower() in fact_text.lower():
                    business_relevance_score += 0.1
            business_relevance_score = min(1.0, business_relevance_score)

            # Emotional hook based on sentiment keywords
            emotional_keywords = [
                "excited",
                "thrilled",
                "milestone",
                "breakthrough",
                "record",
                "first",
                "new",
                "innovative",
                "leading",
                "best",
            ]
            emotional_hook_score = 0.3
            for keyword in emotional_keywords:
                if keyword.lower() in fact_text.lower():
                    emotional_hook_score += 0.1
            emotional_hook_score = min(1.0, emotional_hook_score)

            # Calculate total score
            total_score = _calculate_total_score(
                recency_score,
                specificity_score,
                business_relevance_score,
                emotional_hook_score,
            )

            facts.append(
                {
                    "fact_text": fact_text[:500],  # Limit length
                    "category": category,
                    "source_type": source or "web_search",
                    "source_url": url,
                    "fact_date": fact_date.isoformat() if fact_date else None,
                    "recency_days": recency_days,
                    "recency_score": round(recency_score, 4),
                    "specificity_score": round(specificity_score, 4),
                    "business_relevance_score": round(business_relevance_score, 4),
                    "emotional_hook_score": round(emotional_hook_score, 4),
                    "total_score": round(total_score, 4),
                }
            )

        # Sort by total score descending
        facts.sort(key=lambda x: x["total_score"], reverse=True)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Calculate averages
        avg_score = sum(f["total_score"] for f in facts) / len(facts) if facts else 0

        logger.info(
            f"Extracted {len(facts)} facts for {company_name} "
            f"(avg_score={avg_score:.2f}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Extracted {len(facts)} facts for {company_name}, avg score {avg_score:.2f}",
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "facts": facts,
                "fact_count": len(facts),
                "avg_score": round(avg_score, 4),
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error extracting facts for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"Fact extraction error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Aggregation Tool
# =============================================================================


@tool(  # type: ignore[misc]  # SDK @tool decorator lacks type stubs (LEARN-017)
    name="aggregate_company_research",
    description=(
        "Aggregate research results from all search types for a company. "
        "Combines news, funding, hiring, and tech search results. "
        "Generates primary personalization hook from best facts. "
        "Returns comprehensive research summary for the company."
    ),
    input_schema={
        "company_name": str,
        "company_domain": str,
        "news_results": dict,
        "funding_results": dict,
        "hiring_results": dict,
        "tech_results": dict,
        "extracted_facts": list,
    },
)
async def aggregate_company_research_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate all research results for a company.

    Args:
        args: Tool arguments with all search results and extracted facts.

    Returns:
        Tool result with aggregated research summary.
    """
    start_time = time.time()

    company_name = args.get("company_name", "")
    company_domain = args.get("company_domain", "")
    news_results = args.get("news_results", {})
    funding_results = args.get("funding_results", {})
    hiring_results = args.get("hiring_results", {})
    tech_results = args.get("tech_results", {})
    extracted_facts = args.get("extracted_facts", [])

    if not company_name:
        return {
            "content": [{"type": "text", "text": "company_name is required"}],
            "is_error": True,
        }

    try:
        # Aggregate costs
        total_cost = 0.0
        tools_used = []
        cost_by_tool: dict[str, float] = {}

        for results, _name in [
            (news_results, "news"),
            (funding_results, "funding"),
            (hiring_results, "hiring"),
            (tech_results, "tech"),
        ]:
            if results and results.get("data"):
                data = results["data"]
                cost = data.get("cost", 0)
                tool = data.get("tool_used", "unknown")
                total_cost += cost
                if tool not in tools_used:
                    tools_used.append(tool)
                cost_by_tool[tool] = cost_by_tool.get(tool, 0) + cost

        # Determine what categories were found
        has_recent_news = bool(news_results.get("data", {}).get("result_count", 0))
        has_funding = bool(funding_results.get("data", {}).get("result_count", 0))
        has_hiring = bool(hiring_results.get("data", {}).get("result_count", 0))
        has_product_launch = bool(tech_results.get("data", {}).get("result_count", 0))

        # Generate primary hook from best fact
        primary_hook = None
        headline = None
        summary = None
        relevance_score = 0.0

        if extracted_facts:
            # Get best fact
            best_fact = extracted_facts[0]
            primary_hook = best_fact.get("fact_text", "")
            headline = primary_hook[:200] if primary_hook else None
            relevance_score = best_fact.get("total_score", 0)

            # Generate summary from top 3 facts
            top_facts = extracted_facts[:3]
            summary_parts = [f.get("fact_text", "")[:100] for f in top_facts]
            summary = " | ".join(summary_parts) if summary_parts else None

        # Collect all source URLs
        source_urls = []
        for results in [news_results, funding_results, hiring_results, tech_results]:
            if results and results.get("data", {}).get("results"):
                for r in results["data"]["results"]:
                    if r.get("url"):
                        source_urls.append(r["url"])

        # Generate personalization hooks by category
        personalization_hooks: dict[str, list[str]] = {
            "news": [],
            "funding": [],
            "hiring": [],
            "product": [],
        }
        for fact in extracted_facts:
            category = fact.get("category", "news")
            hook = fact.get("fact_text", "")
            if category in personalization_hooks and hook:
                personalization_hooks[category].append(hook[:200])

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Aggregated research for {company_name}: "
            f"facts={len(extracted_facts)}, cost=${total_cost:.4f}"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Research complete for {company_name}: "
                        f"{len(extracted_facts)} facts, ${total_cost:.4f} cost"
                    ),
                }
            ],
            "data": {
                "company_name": company_name,
                "company_domain": company_domain,
                "headline": headline,
                "summary": summary,
                "primary_hook": primary_hook,
                "relevance_score": round(relevance_score, 4),
                "has_recent_news": has_recent_news,
                "has_funding": has_funding,
                "has_hiring": has_hiring,
                "has_product_launch": has_product_launch,
                "facts": extracted_facts,
                "fact_count": len(extracted_facts),
                "personalization_hooks": personalization_hooks,
                "source_urls": source_urls[:10],  # Limit to 10
                "total_cost": round(total_cost, 4),
                "cost_by_tool": cost_by_tool,
                "tools_used": tools_used,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error aggregating research for {company_name}: {e}")
        return {
            "content": [{"type": "text", "text": f"Aggregation error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool List for Agent Registration
# =============================================================================

# Export list of tools for easy registration with SDK MCP server
COMPANY_RESEARCH_TOOLS = [
    search_company_news_tool,
    search_company_funding_tool,
    search_company_hiring_tool,
    search_company_tech_tool,
    extract_and_score_facts_tool,
    aggregate_company_research_tool,
]
