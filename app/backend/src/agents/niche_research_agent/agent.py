"""
Niche Research Agent - Phase 1, Agent 1.1.

Uses Claude Agent SDK with Reddit API, web search (Brave/Tavily), and
multi-strategy parallel research for niche discovery and pain point extraction.

Phase 1 Research Steps:
1. Parallel Web Research: Reddit search, web search, trend analysis
2. Data Aggregation: Combine findings from all sources
3. Subreddit Scoring: Score by relevance and engagement
4. Pain Point Extraction: Extract common pain points
5. Opportunity Identification: Identify business opportunities

This agent uses Claude Agent SDK with SDK MCP tools for in-process execution.
"""

import asyncio
import logging
import math
import os
from collections import Counter
from datetime import datetime
from typing import Any

import httpx
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from claude_agent_sdk.types import AssistantMessage, TextBlock
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.brave import BraveClient
from src.integrations.exa import ExaClient
from src.integrations.google_docs.client import GoogleDocsClient
from src.integrations.google_drive.client import GoogleDriveClient
from src.integrations.reddit import (
    RedditClient,
    RedditPost,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
)
from src.integrations.serper import SerperClient
from src.integrations.tavily import TavilyClient
from src.models.niche_research import (
    NicheOpportunity,
    NichePainPoint,
    NicheResearchResult,
    NicheSubreddit,
)
from src.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class NicheResearchAgentError(Exception):
    """Exception raised for niche research agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RateLimitExceededError(NicheResearchAgentError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, service: str, retry_after: int | None = None) -> None:
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after}s"
        super().__init__(message, {"service": service, "retry_after": retry_after})


class AuthenticationFailedError(NicheResearchAgentError):
    """Raised when API authentication fails."""

    def __init__(self, service: str) -> None:
        super().__init__(f"Authentication failed for {service}", {"service": service})


class ServiceUnavailableError(NicheResearchAgentError):
    """Raised when API service is unavailable (5xx errors)."""

    def __init__(self, service: str, status_code: int) -> None:
        super().__init__(
            f"Service unavailable for {service} (status {status_code})",
            {"service": service, "status_code": status_code},
        )


# ============================================================================
# SDK MCP Tools
# ============================================================================


@tool(  # type: ignore[misc]
    name="search_reddit",
    description="Search Reddit for relevant subreddits and posts based on a query",
    input_schema={
        "query": str,
        "max_subreddits": int,
        "posts_per_subreddit": int,
        "min_subscribers": int,
        "include_nsfw": bool,
        "client_id": str,
        "client_secret": str,
    },
)
async def search_reddit_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for searching Reddit.

    This tool creates its own Reddit client using provided credentials,
    following the SDK pattern where tools are self-contained.

    Args:
        args: Tool arguments with query, max_subreddits, credentials, etc.

    Returns:
        Tool result with subreddits and posts
    """
    try:
        query = args["query"]
        max_subreddits = args.get("max_subreddits", 10)
        posts_per_subreddit = args.get("posts_per_subreddit", 25)
        min_subscribers = args.get("min_subscribers", 1000)
        include_nsfw = args.get("include_nsfw", False)
        client_id = args.get("client_id", os.getenv("REDDIT_CLIENT_ID", ""))
        client_secret = args.get("client_secret", os.getenv("REDDIT_CLIENT_SECRET", ""))

        if not client_id or not client_secret:
            return {
                "content": [{"type": "text", "text": "Reddit credentials not provided"}],
                "is_error": True,
            }

        # Create Reddit client for this tool call
        reddit_client = RedditClient(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="smarter-team-niche-research/1.0",
        )

        async with reddit_client:
            # Search for subreddits
            subreddits_list = await reddit_client.search_subreddits(
                query=query,
                limit=max_subreddits,
                include_over18=include_nsfw,
            )

            # Filter by subscriber count
            subreddits: list[RedditSubreddit] = []
            seen: set[str] = set()

            for subreddit in subreddits_list:
                if subreddit.subscribers >= min_subscribers and subreddit.name not in seen:
                    seen.add(subreddit.name)
                    subreddits.append(subreddit)

                    if len(subreddits) >= max_subreddits:
                        break

            # Get top posts from each subreddit
            all_posts: list[RedditPost] = []
            for subreddit in subreddits[:5]:  # Limit to top 5
                posts = await reddit_client.get_subreddit_posts(
                    subreddit.name,
                    sort=RedditSortType.HOT,
                    time_filter=RedditTimeFilter.MONTH,
                    limit=posts_per_subreddit,
                )
                all_posts.extend(posts)

        # Format results
        subreddit_data = [
            {
                "name": sub.name,
                "title": sub.title,
                "description": sub.public_description,
                "subscribers": sub.subscribers,
                "active_users": sub.active_users,
                "url": sub.url,
            }
            for sub in subreddits
        ]

        posts_data = [
            {
                "id": post.id,
                "subreddit": post.subreddit,
                "title": post.title,
                "score": post.score,
                "num_comments": post.num_comments,
                "url": post.url,
            }
            for post in all_posts
        ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(subreddits)} subreddits and {len(all_posts)} posts",
                }
            ],
            "data": {
                "subreddits": subreddit_data,
                "posts": posts_data,
            },
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitExceededError(
                "Reddit",
                retry_after=int(e.response.headers.get("Retry-After", 60)),
            ) from e
        if e.response.status_code == 401:
            raise AuthenticationFailedError("Reddit") from e
        if 500 <= e.response.status_code < 600:
            raise ServiceUnavailableError("Reddit", e.response.status_code) from e
        raise NicheResearchAgentError(f"Reddit API error: {e}") from e

    except httpx.TimeoutException as e:
        raise NicheResearchAgentError("Reddit request timed out") from e

    except httpx.NetworkError as e:
        raise NicheResearchAgentError(f"Reddit network error: {e}") from e

    except Exception as e:
        logger.error(f"Reddit search failed: {e}")
        raise


@tool(  # type: ignore[misc]
    name="extract_pain_points",
    description="Extract pain points from Reddit post titles using pain indicators",
    input_schema={
        "posts": list,  # List of post dicts with 'title' field
        "top_n": int,  # Number of top pain points to return
    },
)
async def extract_pain_points_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for extracting pain points from posts.

    Args:
        args: Tool arguments with posts list and top_n

    Returns:
        Tool result with extracted pain points
    """
    posts = args.get("posts", [])
    top_n = args.get("top_n", 10)

    pain_indicators = [
        "problem",
        "issue",
        "struggle",
        "difficult",
        "hard",
        "challenge",
        "frustrated",
        "annoying",
        "help",
        "how to",
        "need",
        "want",
        "looking for",
        "any advice",
        "solutions",
        "fix",
        "workaround",
    ]

    pain_counter: Counter[str] = Counter()
    source_posts: dict[str, list[str]] = {}

    for post in posts:
        title = post.get("title", "")
        title_lower = title.lower()

        for indicator in pain_indicators:
            if indicator in title_lower:
                pain_context = title.strip()
                if pain_context:
                    pain_counter[pain_context] += 1
                    if pain_context not in source_posts:
                        source_posts[pain_context] = []
                    source_posts[pain_context].append(post.get("url", ""))

    # Create pain point objects
    pain_points = []
    for pain, freq in pain_counter.most_common(top_n):
        severity = "high" if freq >= 5 else "medium" if freq >= 3 else "low"

        pain_points.append(
            {
                "description": pain,
                "severity": severity,
                "frequency": freq,
                "source_posts": source_posts.get(pain, [])[:3],
            }
        )

    return {
        "content": [
            {
                "type": "text",
                "text": f"Extracted {len(pain_points)} pain points",
            }
        ],
        "data": {"pain_points": pain_points},
    }


@tool(  # type: ignore[misc]
    name="identify_opportunities",
    description="Identify business opportunities from pain points and subreddits",
    input_schema={
        "pain_points": list,  # List of pain point dicts
        "subreddits": list,  # List of subreddit dicts
        "top_n": int,  # Number of opportunities to return
    },
)
async def identify_opportunities_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for identifying business opportunities.

    Args:
        args: Tool arguments with pain_points, subreddits, and top_n

    Returns:
        Tool result with identified opportunities
    """
    pain_points = args.get("pain_points", [])
    subreddits = args.get("subreddits", [])
    top_n = args.get("top_n", 5)

    opportunities = []

    # Total potential reach
    total_reach = sum(sub.get("subscribers", 0) for sub in subreddits)

    for pain_point in pain_points[:top_n]:
        description = pain_point.get("description", "")
        frequency = pain_point.get("frequency", 1)
        severity = pain_point.get("severity", "medium")

        # Generate opportunity description
        opp_description = f"Solve {description.lower()}"

        # Estimate potential reach
        potential_reach = min(total_reach, frequency * 1000)

        # Confidence based on pain point severity and frequency
        severity_scores = {"high": 0.9, "medium": 0.6, "low": 0.3}
        confidence = severity_scores.get(severity, 0.5) * min(frequency / 10, 1.0)

        # Target audience
        target_audience = ", ".join(sub.get("name", "") for sub in subreddits[:3])

        opportunities.append(
            {
                "description": opp_description,
                "pain_point": description,
                "target_audience": target_audience,
                "potential_reach": potential_reach,
                "confidence_score": confidence,
                "supporting_evidence": pain_point.get("source_posts", [])[:2],
            }
        )

    return {
        "content": [
            {
                "type": "text",
                "text": f"Identified {len(opportunities)} opportunities",
            }
        ],
        "data": {"opportunities": opportunities},
    }


# ============================================================================
# Resilient Integration Clients with Retry and Rate Limiting
# ============================================================================


class ResilientRedditClient:
    """
    Reddit client with retry logic and rate limiting.

    Ultra-resilient integration with:
    - Tenacity retry with exponential backoff and jitter
    - Token bucket rate limiting (60 requests/minute)
    - Specific error handling for 4xx/5xx/timeout/connection errors
    """

    # Reddit API limit: 60 requests/minute
    RATE_LIMIT = 60
    RATE_WINDOW = 60.0  # seconds

    def __init__(self, client_id: str, client_secret: str, user_agent: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=self.RATE_LIMIT,
            refill_rate=self.RATE_LIMIT / self.RATE_WINDOW,
            service_name="Reddit",
        )
        self._client: RedditClient | None = None

    async def _get_client(self) -> RedditClient:
        """Get or create Reddit client."""
        if self._client is None:
            self._client = RedditClient(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search_subreddits(
        self,
        query: str,
        limit: int = 10,
        include_over18: bool = False,
    ) -> list[RedditSubreddit]:
        """Search subreddits with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search_subreddits(
                    query=query,
                    limit=limit,
                    include_over18=include_over18,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                raise RateLimitExceededError("Reddit", retry_after) from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Reddit") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Reddit", e.response.status_code) from e
            raise NicheResearchAgentError(f"Reddit API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Reddit request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Reddit network error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_subreddit_posts(
        self,
        subreddit: str,
        sort: RedditSortType = RedditSortType.HOT,
        time_filter: RedditTimeFilter = RedditTimeFilter.MONTH,
        limit: int = 25,
    ) -> list[RedditPost]:
        """Get subreddit posts with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.get_subreddit_posts(
                    subreddit=subreddit,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                raise RateLimitExceededError("Reddit", retry_after) from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Reddit") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Reddit", e.response.status_code) from e
            raise NicheResearchAgentError(f"Reddit API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Reddit request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Reddit network error: {e}") from e


class ResilientBraveClient:
    """
    Brave client with retry logic and rate limiting.

    Ultra-resilient integration with:
    - Tenacity retry with exponential backoff and jitter
    - Token bucket rate limiting (100 requests/minute)
    - Specific error handling for 4xx/5xx/timeout/connection errors
    """

    # Brave API limit: 100 requests/minute (free tier)
    RATE_LIMIT = 100
    RATE_WINDOW = 60.0  # seconds

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=self.RATE_LIMIT,
            refill_rate=self.RATE_LIMIT / self.RATE_WINDOW,
            service_name="Brave",
        )
        self._client: BraveClient | None = None

    async def _get_client(self) -> BraveClient:
        """Get or create Brave client."""
        if self._client is None:
            self._client = BraveClient(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: str | None = None,
    ) -> Any:
        """Search with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search(
                    query=query,
                    count=count,
                    freshness=freshness,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Brave") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Brave") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Brave", e.response.status_code) from e
            raise NicheResearchAgentError(f"Brave API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Brave request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Brave network error: {e}") from e


class ResilientTavilyClient:
    """
    Tavily client with retry logic and rate limiting.

    Ultra-resilient integration with:
    - Tenacity retry with exponential backoff and jitter
    - Token bucket rate limiting (60 requests/minute)
    - Specific error handling for 4xx/5xx/timeout/connection errors
    """

    # Tavily API limit: 60 requests/minute (free tier)
    RATE_LIMIT = 60
    RATE_WINDOW = 60.0  # seconds

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=self.RATE_LIMIT,
            refill_rate=self.RATE_LIMIT / self.RATE_WINDOW,
            service_name="Tavily",
        )
        self._client: TavilyClient | None = None

    async def _get_client(self) -> TavilyClient:
        """Get or create Tavily client."""
        if self._client is None:
            self._client = TavilyClient(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def research(
        self,
        query: str,
        max_iterations: int = 3,
    ) -> Any:
        """Research with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.research(
                    query=query,
                    max_iterations=max_iterations,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Tavily") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Tavily") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Tavily", e.response.status_code) from e
            raise NicheResearchAgentError(f"Tavily API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Tavily request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Tavily network error: {e}") from e


class ResilientExaClient:
    """
    Exa client with retry logic and rate limiting.

    Ultra-resilient integration with:
    - Tenacity retry with exponential backoff and jitter
    - Token bucket rate limiting (10 requests/second)
    - Specific error handling for 4xx/5xx/timeout/connection errors

    Free tier: 1,000 searches/month (use wisely!)
    """

    # Exa API limit: 10 requests/second
    RATE_LIMIT = 10
    RATE_WINDOW = 1.0  # seconds

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=self.RATE_LIMIT,
            refill_rate=self.RATE_LIMIT / self.RATE_WINDOW,
            service_name="Exa",
        )
        self._client: ExaClient | None = None

    async def _get_client(self) -> ExaClient:
        """Get or create Exa client."""
        if self._client is None:
            self._client = ExaClient(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        num_results: int = 10,
        use_autoprompt: bool = True,
    ) -> Any:
        """Semantic search with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search(
                    query=query,
                    num_results=num_results,
                    use_autoprompt=use_autoprompt,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Exa") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Exa") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Exa", e.response.status_code) from e
            raise NicheResearchAgentError(f"Exa API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Exa request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Exa network error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search_companies(
        self,
        query: str,
        num_results: int = 10,
    ) -> Any:
        """Search for companies with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search_companies(
                    query=query,
                    num_results=num_results,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Exa") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Exa") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Exa", e.response.status_code) from e
            raise NicheResearchAgentError(f"Exa API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Exa request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Exa network error: {e}") from e


class ResilientSerperClient:
    """
    Serper client with retry logic and rate limiting.

    Ultra-resilient integration with:
    - Tenacity retry with exponential backoff and jitter
    - Token bucket rate limiting (50 requests/second)
    - Specific error handling for 4xx/5xx/timeout/connection errors

    Free tier: 2,500 queries included!
    """

    # Serper API limit: 50 QPS (Starter tier)
    RATE_LIMIT = 50
    RATE_WINDOW = 1.0  # seconds

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=self.RATE_LIMIT,
            refill_rate=self.RATE_LIMIT / self.RATE_WINDOW,
            service_name="Serper",
        )
        self._client: SerperClient | None = None

    async def _get_client(self) -> SerperClient:
        """Get or create Serper client."""
        if self._client is None:
            self._client = SerperClient(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        num: int = 10,
    ) -> Any:
        """Google search with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search(
                    query=query,
                    num=num,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Serper") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Serper") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Serper", e.response.status_code) from e
            raise NicheResearchAgentError(f"Serper API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Serper request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Serper network error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search_news(
        self,
        query: str,
        num: int = 10,
    ) -> Any:
        """News search with retry and rate limiting."""
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                return await client.search_news(
                    query=query,
                    num=num,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError("Serper") from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Serper") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError("Serper", e.response.status_code) from e
            raise NicheResearchAgentError(f"Serper API error: {e}") from e

        except httpx.TimeoutException as e:
            raise NicheResearchAgentError("Serper request timed out") from e

        except httpx.NetworkError as e:
            raise NicheResearchAgentError(f"Serper network error: {e}") from e


# ============================================================================
# Niche Research Agent using Claude Agent SDK
# ============================================================================


class NicheResearchAgent:
    """
    Agent for discovering and analyzing market niches using Claude Agent SDK.

    Uses Reddit API for community discovery, web search for market validation,
    and AI analysis for pain point extraction and opportunity identification.

    Example:
        >>> agent = NicheResearchAgent()
        >>> result = await agent.research_niche("AI tools for solopreneurs")
        >>> print(f"Found {len(result.subreddits)} relevant subreddits")
        >>> print(f"Identified {len(result.pain_points)} pain points")
    """

    def __init__(
        self,
        reddit_client_id: str | None = None,
        reddit_client_secret: str | None = None,
        brave_api_key: str | None = None,
        tavily_api_key: str | None = None,
        exa_api_key: str | None = None,
        serper_api_key: str | None = None,
    ) -> None:
        """
        Initialize the Niche Research Agent.

        Args:
            reddit_client_id: Reddit app client ID (from environment if not provided)
            reddit_client_secret: Reddit app client secret (from environment if not provided)
            brave_api_key: Brave Search API key (from environment if not provided)
            tavily_api_key: Tavily Search API key (from environment if not provided)
            exa_api_key: EXA AI Search API key (from environment if not provided)
            serper_api_key: Serper Google Search API key (from environment if not provided)
        """
        # Get API keys from environment if not provided
        self.reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY", "")
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY", "")
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY", "")

        self.name = "niche_research_agent"
        logger.info(f"Initialized {self.name}")

    def _calculate_engagement_score(self, subreddit: RedditSubreddit) -> float:
        """
        Calculate engagement score for a subreddit.

        Score based on:
        - Active user ratio (active_users / subscribers)
        - Subscriber count (logarithmic scale)
        - Base score of 1.0

        Args:
            subreddit: RedditSubreddit or NicheSubreddit object

        Returns:
            Engagement score (0.0 to 10.0)
        """
        # Handle both RedditSubreddit (subscribers) and NicheSubreddit (subscriber_count)
        subscribers = (
            getattr(subreddit, "subscribers", None)
            or getattr(subreddit, "subscriber_count", 0)
            or 0
        )
        active_users = getattr(subreddit, "active_users", 0) or 0

        # Active user ratio (higher is better)
        active_ratio = active_users / subscribers if subscribers > 0 else 0.0

        # Normalize active ratio (typically 0.01 to 0.10)
        active_score = min(active_ratio * 20, 5.0)

        # Subscriber score (logarithmic, max 5.0)
        sub_score = min(math.log10(subscribers) / 2, 5.0) if subscribers > 0 else 0.0

        return active_score + sub_score

    def _calculate_relevance_score(
        self,
        subreddit: RedditSubreddit | NicheSubreddit,
        keywords: list[str],
    ) -> float:
        """
        Calculate relevance score based on keyword matching.

        Args:
            subreddit: RedditSubreddit or NicheSubreddit object
            keywords: List of trend keywords

        Returns:
            Relevance score (0.0 to 10.0)
        """
        # Handle both RedditSubreddit (public_description) and NicheSubreddit (description)
        title = getattr(subreddit, "title", "") or ""
        description = (
            getattr(subreddit, "public_description", None)
            or getattr(subreddit, "description", "")
            or ""
        )
        description_lower = title.lower() + " " + description.lower()

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in description_lower)

        # Normalize score (max 10.0 for 10+ matches)
        return min(matches, 10.0)

    async def research_niche(
        self,
        query: str,
        *,
        max_subreddits: int = 10,
        posts_per_subreddit: int = 25,
        min_subscribers: int = 1000,
        include_nsfw: bool = False,
        engagement_weight: float = 0.5,
        relevance_weight: float = 0.5,
    ) -> NicheResearchResult:
        """
        Perform complete niche research analysis.

        This is the main entry point for niche research. It orchestrates
        all phases of the research pipeline:
        1. Parallel web research
        2. Data aggregation
        3. Subreddit scoring
        4. Pain point extraction
        5. Opportunity identification

        Args:
            query: Niche search query (e.g., "AI tools for solopreneurs")
            max_subreddits: Maximum number of subreddits to analyze
            posts_per_subreddit: Number of posts to analyze per subreddit
            min_subscribers: Minimum subscriber count for subreddits
            include_nsfw: Whether to include NSFW subreddits
            engagement_weight: Weight for engagement score (0.0 to 1.0)
            relevance_weight: Weight for relevance score (0.0 to 1.0)

        Returns:
            NicheResearchResult with complete analysis

        Raises:
            NicheResearchAgentError: If research fails
        """
        if not query or not query.strip():
            raise NicheResearchAgentError("Query is required and cannot be empty")

        logger.info(f"Starting niche research for: {query}")

        # Create resilient clients
        reddit_client: ResilientRedditClient | None = None
        brave_client: ResilientBraveClient | None = None
        tavily_client: ResilientTavilyClient | None = None
        exa_client: ResilientExaClient | None = None
        serper_client: ResilientSerperClient | None = None

        if self.reddit_client_id and self.reddit_client_secret:
            reddit_client = ResilientRedditClient(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent="smarter-team-niche-research/1.0",
            )

        if self.brave_api_key:
            brave_client = ResilientBraveClient(api_key=self.brave_api_key)

        if self.tavily_api_key:
            tavily_client = ResilientTavilyClient(api_key=self.tavily_api_key)

        if self.exa_api_key:
            exa_client = ResilientExaClient(api_key=self.exa_api_key)

        if self.serper_api_key:
            serper_client = ResilientSerperClient(api_key=self.serper_api_key)

        try:
            # Phase 1: Parallel web research
            research_data = await self._parallel_web_research(
                query,
                reddit_client,
                brave_client,
                tavily_client,
                exa_client,
                serper_client,
                max_subreddits,
                posts_per_subreddit,
                min_subscribers,
                include_nsfw,
            )

            # Phase 2: Aggregate findings
            aggregated_data = await self._aggregate_findings(research_data)

            # Phase 3: Score subreddits
            scored_subreddits = await self._score_subreddits(
                aggregated_data,
                engagement_weight,
                relevance_weight,
            )

            # Phase 4: Extract pain points
            pain_points = await self._extract_pain_points(
                aggregated_data,
                scored_subreddits,
            )

            # Phase 5: Identify opportunities
            opportunities = await self._identify_opportunities(
                pain_points,
                scored_subreddits,
            )

            # Calculate totals
            total_subscribers = sum(s.subscriber_count for s in scored_subreddits)
            total_active_users = sum(s.active_users for s in scored_subreddits)

            # Build result
            result = NicheResearchResult(
                niche=query,
                subreddits=scored_subreddits,
                pain_points=pain_points,
                opportunities=opportunities,
                total_subscribers=total_subscribers,
                total_active_users=total_active_users,
                research_metadata={
                    "max_subreddits": max_subreddits,
                    "posts_analyzed": len(aggregated_data.get("posts", [])),
                    "web_results": len(aggregated_data.get("web_results", [])),
                    "research_timestamp": datetime.now().isoformat(),
                },
                raw_responses={
                    "research_data": research_data,
                    "aggregated_data": aggregated_data,
                },
            )

            logger.info(
                f"Niche research complete: {len(result.subreddits)} subreddits, "
                f"{len(result.pain_points)} pain points, {len(result.opportunities)} opportunities"
            )

            return result

        except NicheResearchAgentError:
            raise
        except Exception as e:
            logger.error(f"Niche research failed: {e}")
            raise NicheResearchAgentError(f"Research failed: {e}") from e

    async def _parallel_web_research(
        self,
        query: str,
        reddit_client: ResilientRedditClient | None,
        brave_client: ResilientBraveClient | None,
        tavily_client: ResilientTavilyClient | None,
        exa_client: ResilientExaClient | None,
        serper_client: ResilientSerperClient | None,
        max_subreddits: int,
        posts_per_subreddit: int,
        min_subscribers: int,
        include_nsfw: bool,
    ) -> dict[str, Any]:
        """
        Phase 1.1: Parallel web research using multiple sources.

        Searches ALL available sources in parallel for maximum coverage:
        - Claude SDK WebSearch (always, free)
        - Reddit API (if credentials)
        - EXA semantic search (1K/mo free)
        - Serper Google search (2.5K free)
        - Brave search (if key available)
        - Tavily deep research (if key available)

        Args:
            query: Niche search query
            reddit_client: Resilient Reddit client
            brave_client: Resilient Brave client
            tavily_client: Resilient Tavily client
            exa_client: Resilient Exa client (semantic search)
            serper_client: Resilient Serper client (Google search)
            max_subreddits: Maximum subreddits to find
            posts_per_subreddit: Posts per subreddit
            min_subscribers: Minimum subscriber count
            include_nsfw: Include NSFW subreddits

        Returns:
            Dictionary with research findings from all sources
        """
        logger.info(f"Starting parallel web research for query: {query}")

        results: dict[str, Any] = {
            "subreddits": [],
            "posts": [],
            "web_results": [],
            "research_results": [],
            "errors": [],
        }

        # Create tasks for parallel execution - ALL SOURCES RUN IN PARALLEL
        tasks = []

        # 1. ALWAYS use Claude SDK WebSearch (built-in, no API key needed)
        # This is PRIMARY and always runs for comprehensive research
        logger.info("Adding Claude SDK WebSearch for comprehensive Reddit + web research")
        tasks.append(
            self._deep_research_via_claude_sdk(
                query,
                max_subreddits,
            )
        )

        # 2. Reddit API (if credentials available) - ADDITIONAL source
        if reddit_client:
            logger.info("Adding Reddit API for direct subreddit/post data")
            tasks.append(
                self._search_reddit_parallel(
                    reddit_client,
                    query,
                    max_subreddits,
                    posts_per_subreddit,
                    min_subscribers,
                    include_nsfw,
                )
            )

        # 3. EXA semantic search (1,000 free/month) - CHEAP SOURCE
        if exa_client:
            logger.info("Adding EXA for semantic/neural search (1K free/mo)")
            tasks.append(self._search_exa_parallel(exa_client, query))

        # 4. Serper Google search (2,500 free queries) - CHEAP SOURCE
        if serper_client:
            logger.info("Adding Serper for Google search (2.5K free)")
            tasks.append(self._search_serper_parallel(serper_client, query))

        # 5. Brave web search (market research + Reddit via web)
        if brave_client:
            logger.info("Adding Brave Search for market validation + Reddit web search")
            tasks.append(self._search_web_parallel(brave_client, query))
            tasks.append(self._search_reddit_via_web(brave_client, query, max_subreddits))

        # 6. Tavily deep research
        if tavily_client:
            logger.info("Adding Tavily for deep market research")
            tasks.append(self._search_tavily_parallel(tavily_client, query))

        # Execute all tasks in parallel
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    logger.warning(f"Research task {i} failed: {result}")
                    results["errors"].append(str(result))
                elif isinstance(result, dict):
                    # MERGE results (don't overwrite, extend lists)
                    for key, value in result.items():
                        if (
                            key in results
                            and isinstance(results[key], list)
                            and isinstance(value, list)
                        ):
                            # Extend lists (subreddits, posts, web_results, etc.)
                            results[key].extend(value)
                        elif key not in results or not results[key]:
                            results[key] = value

            # Deduplicate subreddits by name
            seen_subs: set[str] = set()
            unique_subs: list[Any] = []
            for sub in results.get("subreddits", []):
                name = getattr(sub, "name", "") if hasattr(sub, "name") else sub.get("name", "")
                if name and name not in seen_subs:
                    seen_subs.add(name)
                    unique_subs.append(sub)
            results["subreddits"] = unique_subs

            logger.info(
                f"Merged research: {len(results['subreddits'])} unique subreddits, "
                f"{len(results.get('posts', []))} posts, "
                f"{len(results.get('web_results', []))} web results"
            )

        logger.info(f"Parallel research complete. Found {len(results['subreddits'])} subreddits")
        return results

    async def _search_reddit_parallel(
        self,
        reddit_client: ResilientRedditClient,
        query: str,
        max_subreddits: int,
        posts_per_subreddit: int,
        min_subscribers: int,
        include_nsfw: bool,
    ) -> dict[str, Any]:
        """Search Reddit for relevant subreddits and posts."""
        logger.info("Searching Reddit for relevant subreddits")
        results: dict[str, Any] = {"subreddits": [], "posts": [], "errors": []}

        try:
            # Search for subreddits
            subreddits_list = await reddit_client.search_subreddits(
                query=query,
                limit=max_subreddits,
                include_over18=include_nsfw,
            )

            # Filter by subscriber count
            seen: set[str] = set()
            for subreddit in subreddits_list:
                if subreddit.subscribers >= min_subscribers and subreddit.name not in seen:
                    seen.add(subreddit.name)
                    results["subreddits"].append(subreddit)

                    if len(results["subreddits"]) >= max_subreddits:
                        break

            # Get top posts from each subreddit
            for subreddit in results["subreddits"][:5]:  # Limit to top 5
                try:
                    posts = await reddit_client.get_subreddit_posts(
                        subreddit.name,
                        sort=RedditSortType.HOT,
                        time_filter=RedditTimeFilter.MONTH,
                        limit=posts_per_subreddit,
                    )
                    results["posts"].extend(posts)
                except NicheResearchAgentError as e:
                    logger.warning(f"Failed to get posts from r/{subreddit.name}: {e}")

        except NicheResearchAgentError as e:
            logger.error(f"Reddit search failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _deep_research_via_claude_sdk(
        self,
        search_query: str,
        max_subreddits: int = 10,
    ) -> dict[str, Any]:
        """
        Comprehensive deep research using Claude SDK's WebSearch and WebFetch.

        This is the PRIMARY research method that always runs.
        Performs multi-phase research:
        1. Reddit community discovery
        2. Pain point and problem discovery
        3. Market trends and opportunities
        4. Deep content fetching for insights

        Args:
            search_query: Search query for research
            max_subreddits: Maximum subreddits to find

        Returns:
            Comprehensive research findings from all searches
        """
        logger.info(f"Starting deep research via Claude SDK for: {search_query}")
        results: dict[str, Any] = {
            "subreddits": [],
            "posts": [],
            "web_results": [],
            "pain_points_raw": [],
            "market_insights": [],
            "errors": [],
        }

        try:
            # Configure Claude SDK with WebSearch AND WebFetch
            # Using acceptEdits for safer automated workflows (per SDK_PATTERNS.md)
            # bypassPermissions requires security hooks which aren't needed for built-in tools
            options = ClaudeAgentOptions(
                allowed_tools=["WebSearch", "WebFetch"],
                permission_mode="acceptEdits",
                max_turns=15,  # More turns for comprehensive research
                setting_sources=["project"],  # Load CLAUDE.md settings
            )

            # PHASE 1: Reddit Community Discovery
            phase1_prompt = f"""You are a market research expert. Research "{search_query}" thoroughly.

PHASE 1: Find Reddit Communities

Use WebSearch to find Reddit communities discussing "{search_query}". Search for:
1. "Reddit {search_query} community subreddit"
2. "Reddit {search_query} discussion forum"
3. "best subreddits for {search_query}"
4. "Reddit where to discuss {search_query}"

For each subreddit found, extract:
- Subreddit name (e.g., "entrepreneur", "startups")
- What the community discusses
- Estimated size/activity level if mentioned

Return as JSON:
{{
    "subreddits": [
        {{"name": "subreddit_name", "description": "what they discuss", "activity": "high/medium/low"}}
    ]
}}"""

            phase1_response = await self._run_claude_sdk_query(phase1_prompt, options)
            phase1_data = self._parse_json_response(phase1_response)

            for sub_data in phase1_data.get("subreddits", [])[:max_subreddits]:
                name = sub_data.get("name", "").lower().strip().replace("r/", "")
                if name and len(name) > 1:
                    activity = sub_data.get("activity", "medium")
                    engagement = 8.0 if activity == "high" else 5.0 if activity == "medium" else 3.0
                    niche_sub = NicheSubreddit(
                        name=name,
                        title=f"r/{name}",
                        description=sub_data.get("description", "")[:500],
                        subscriber_count=0,
                        active_users=0,
                        engagement_score=engagement,
                        relevance_score=7.0,
                        url=f"https://reddit.com/r/{name}",
                        created_at=datetime.now(),
                        raw={"source": "claude_sdk_phase1"},
                    )
                    results["subreddits"].append(niche_sub)

            logger.info(f"Phase 1 found {len(results['subreddits'])} subreddits")

            # PHASE 2: Pain Points and Problems Discovery
            phase2_prompt = f"""You are a market research expert analyzing pain points for "{search_query}".

PHASE 2: Find Pain Points and Problems

Use WebSearch to find problems and frustrations people have with "{search_query}". Search for:
1. "Reddit {search_query} problems frustrated"
2. "{search_query} challenges issues help"
3. "struggling with {search_query} advice"
4. "{search_query} not working alternatives"
5. "hate {search_query} issues"

Look for:
- Specific complaints and frustrations
- Common questions people ask
- Things people wish were different
- Repeated problems across multiple posts

Return as JSON:
{{
    "pain_points": [
        {{"problem": "specific problem description", "severity": "high/medium/low", "frequency": "common/occasional/rare", "source": "where you found it"}}
    ],
    "common_questions": [
        "Question people frequently ask"
    ]
}}"""

            phase2_response = await self._run_claude_sdk_query(phase2_prompt, options)
            phase2_data = self._parse_json_response(phase2_response)

            for pp in phase2_data.get("pain_points", []):
                results["pain_points_raw"].append(pp)
                # Also add as a post for pain point extraction
                results["posts"].append(
                    {
                        "title": pp.get("problem", ""),
                        "subreddit": "research",
                        "url": pp.get("source", ""),
                        "source": "claude_sdk_phase2",
                        "severity": pp.get("severity", "medium"),
                    }
                )

            for q in phase2_data.get("common_questions", []):
                results["posts"].append(
                    {
                        "title": q,
                        "subreddit": "research",
                        "url": "",
                        "source": "claude_sdk_phase2_question",
                    }
                )

            logger.info(f"Phase 2 found {len(results['pain_points_raw'])} pain points")

            # PHASE 3: Market Trends and Opportunities
            phase3_prompt = f"""You are a market research expert analyzing opportunities for "{search_query}".

PHASE 3: Market Trends and Opportunities

Use WebSearch to find market trends and business opportunities for "{search_query}". Search for:
1. "{search_query} market size growth 2024"
2. "{search_query} trends opportunities"
3. "{search_query} startup ideas business"
4. "best tools for {search_query}"
5. "{search_query} industry analysis"

Look for:
- Market size and growth trends
- Emerging opportunities
- Gaps in current solutions
- What successful products/services exist
- Underserved segments

Return as JSON:
{{
    "market_insights": [
        {{"insight": "specific market insight", "opportunity": "potential business opportunity", "evidence": "where you found this"}}
    ],
    "existing_solutions": [
        {{"name": "product/service name", "what_it_does": "brief description", "gap": "what it doesn't do well"}}
    ],
    "trends": [
        "Emerging trend in this space"
    ]
}}"""

            phase3_response = await self._run_claude_sdk_query(phase3_prompt, options)
            phase3_data = self._parse_json_response(phase3_response)

            for insight in phase3_data.get("market_insights", []):
                results["market_insights"].append(insight)
                results["web_results"].append(
                    {
                        "title": insight.get("insight", ""),
                        "description": insight.get("opportunity", ""),
                        "url": insight.get("evidence", ""),
                        "source": "claude_sdk_phase3",
                    }
                )

            for solution in phase3_data.get("existing_solutions", []):
                results["web_results"].append(
                    {
                        "title": solution.get("name", ""),
                        "description": f"{solution.get('what_it_does', '')} - Gap: {solution.get('gap', '')}",
                        "source": "claude_sdk_phase3_solution",
                    }
                )

            for trend in phase3_data.get("trends", []):
                results["web_results"].append(
                    {
                        "title": trend,
                        "description": "Market trend",
                        "source": "claude_sdk_phase3_trend",
                    }
                )

            logger.info(f"Phase 3 found {len(results['market_insights'])} market insights")

            # PHASE 4: Deep Dive on Top Findings (using WebFetch)
            if results["subreddits"]:
                top_subreddits = [s.name for s in results["subreddits"][:3]]
                phase4_prompt = f"""You are a market research expert doing deep research on "{search_query}".

PHASE 4: Deep Dive Research

The top Reddit communities for this niche are: {', '.join(top_subreddits)}

Use WebFetch to get more details from relevant pages. Try to fetch:
1. One of the subreddit pages if accessible
2. A relevant article or blog post about "{search_query}"

Then use WebSearch for:
1. "Reddit r/{top_subreddits[0] if top_subreddits else search_query} top posts"
2. "{search_query} expert advice tips"

Analyze what you find and return:
{{
    "deep_insights": [
        {{"finding": "specific finding", "implication": "what this means for business", "confidence": "high/medium/low"}}
    ],
    "additional_communities": [
        {{"name": "community_name", "platform": "reddit/forum/other", "relevance": "why it's relevant"}}
    ],
    "key_influencers": [
        "Name or username of key voice in this space"
    ]
}}"""

                phase4_response = await self._run_claude_sdk_query(phase4_prompt, options)
                phase4_data = self._parse_json_response(phase4_response)

                for insight in phase4_data.get("deep_insights", []):
                    results["market_insights"].append(
                        {
                            "insight": insight.get("finding", ""),
                            "opportunity": insight.get("implication", ""),
                            "confidence": insight.get("confidence", "medium"),
                        }
                    )

                for community in phase4_data.get("additional_communities", []):
                    if community.get("platform") == "reddit":
                        name = community.get("name", "").lower().strip().replace("r/", "")
                        if name and not any(s.name == name for s in results["subreddits"]):
                            niche_sub = NicheSubreddit(
                                name=name,
                                title=f"r/{name}",
                                description=community.get("relevance", "")[:500],
                                subscriber_count=0,
                                active_users=0,
                                engagement_score=5.0,
                                relevance_score=6.0,
                                url=f"https://reddit.com/r/{name}",
                                created_at=datetime.now(),
                                raw={"source": "claude_sdk_phase4"},
                            )
                            results["subreddits"].append(niche_sub)

                logger.info(
                    f"Phase 4 added {len(phase4_data.get('deep_insights', []))} deep insights"
                )

            logger.info(
                f"Claude SDK deep research complete: "
                f"{len(results['subreddits'])} subreddits, "
                f"{len(results['posts'])} posts, "
                f"{len(results['pain_points_raw'])} pain points, "
                f"{len(results['market_insights'])} insights"
            )

        except Exception as e:
            logger.error(f"Claude SDK deep research failed: {e}")
            import traceback

            logger.debug(f"Claude SDK traceback: {traceback.format_exc()}")
            results["errors"].append(str(e))

        return results

    async def _run_claude_sdk_query(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
    ) -> str:
        """Run a Claude SDK query and return the response text."""
        response_text = ""
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
        except Exception as e:
            logger.warning(f"Claude SDK query failed: {e}")
        return response_text

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON from Claude SDK response."""
        import json
        import re

        if not response_text:
            return {}

        # Find JSON in response
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
        return {}

    async def _search_reddit_via_claude_sdk(
        self,
        search_query: str,
        max_subreddits: int = 10,
    ) -> dict[str, Any]:
        """Legacy method - redirects to deep research."""
        return await self._deep_research_via_claude_sdk(search_query, max_subreddits)

    async def _search_reddit_via_web(
        self,
        brave_client: ResilientBraveClient,
        query: str,
        max_subreddits: int = 10,
    ) -> dict[str, Any]:
        """
        Search Reddit via web search when Reddit API credentials are not available.

        Uses Brave to search site:reddit.com for subreddits and posts.
        This is a fallback method that provides similar functionality to the Reddit API.

        Args:
            brave_client: Resilient Brave client for web search
            query: Search query
            max_subreddits: Maximum subreddits to find

        Returns:
            Dictionary with subreddits and posts extracted from web results
        """
        logger.info(f"Searching Reddit via web search for: {query}")
        results: dict[str, Any] = {"subreddits": [], "posts": [], "errors": []}

        try:
            # Search for subreddits
            subreddit_queries = [
                f"site:reddit.com/r/ {query}",
                f"site:reddit.com {query} subreddit community",
            ]

            seen_subreddits: set[str] = set()
            seen_posts: set[str] = set()

            for search_query in subreddit_queries:
                try:
                    response = await brave_client.search(
                        query=search_query,
                        count=20,
                        freshness="month",
                    )

                    for result in response.results:
                        url = getattr(result, "url", "") or ""
                        title = getattr(result, "title", "") or ""
                        description = getattr(result, "description", "") or ""

                        # Extract subreddit from URL
                        if "/r/" in url:
                            parts = url.split("/r/")
                            if len(parts) > 1:
                                subreddit_part = parts[1].split("/")[0]
                                subreddit_name = subreddit_part.lower()

                                if subreddit_name and subreddit_name not in seen_subreddits:
                                    seen_subreddits.add(subreddit_name)

                                    # Create a NicheSubreddit from web data
                                    from datetime import datetime

                                    niche_sub = NicheSubreddit(
                                        name=subreddit_name,
                                        title=f"r/{subreddit_name}",
                                        description=description[:500] if description else "",
                                        subscriber_count=0,  # Unknown from web search
                                        active_users=0,
                                        engagement_score=5.0,  # Default score
                                        relevance_score=7.0,  # Higher since it matched query
                                        url=f"https://reddit.com/r/{subreddit_name}",
                                        created_at=datetime.now(),
                                        raw={"source": "web_search", "original_url": url},
                                    )
                                    results["subreddits"].append(niche_sub)

                                # Check if this is a post (has /comments/)
                                if "/comments/" in url and url not in seen_posts:
                                    seen_posts.add(url)
                                    # Create a mock post for pain point extraction
                                    results["posts"].append(
                                        {
                                            "title": title,
                                            "url": url,
                                            "subreddit": subreddit_name,
                                            "source": "web_search",
                                        }
                                    )

                except NicheResearchAgentError as e:
                    logger.warning(f"Web search for Reddit failed: {e}")
                    continue

            # Search for pain points/problems on Reddit
            pain_queries = [
                f"site:reddit.com {query} problem issue help",
                f"site:reddit.com {query} struggling frustrated",
                f"site:reddit.com {query} how to advice",
            ]

            for search_query in pain_queries:
                try:
                    response = await brave_client.search(
                        query=search_query,
                        count=15,
                        freshness="month",
                    )

                    for result in response.results:
                        url = getattr(result, "url", "") or ""
                        title = getattr(result, "title", "") or ""

                        if "/r/" in url and "/comments/" in url and url not in seen_posts:
                            seen_posts.add(url)
                            # Extract subreddit name
                            parts = url.split("/r/")
                            subreddit_name = parts[1].split("/")[0] if len(parts) > 1 else "unknown"

                            results["posts"].append(
                                {
                                    "title": title,
                                    "url": url,
                                    "subreddit": subreddit_name,
                                    "source": "web_search",
                                }
                            )

                except NicheResearchAgentError as e:
                    logger.warning(f"Pain point search failed: {e}")
                    continue

            logger.info(
                f"Web-based Reddit search complete: "
                f"{len(results['subreddits'])} subreddits, {len(results['posts'])} posts"
            )

        except Exception as e:
            logger.error(f"Reddit web search failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _search_web_parallel(
        self,
        brave_client: ResilientBraveClient,
        query: str,
    ) -> dict[str, Any]:
        """Search the web using Brave for market validation."""
        logger.info("Searching web with Brave for market validation")
        results: dict[str, Any] = {"web_results": []}

        try:
            # Search for niche validation
            search_queries = [
                f"{query} market size",
                f"{query} business opportunities",
                f"{query} problems challenges",
                f"{query} community forum",
            ]

            for search_query in search_queries:
                try:
                    response = await brave_client.search(
                        query=search_query,
                        count=10,
                        freshness="month",
                    )
                    results["web_results"].extend(response.results)
                except NicheResearchAgentError as e:
                    logger.warning(f"Brave search failed for '{search_query}': {e}")
                    continue

        except NicheResearchAgentError as e:
            logger.error(f"Web search failed: {e}")
            results["errors"] = [str(e)]

        return results

    async def _search_tavily_parallel(
        self,
        tavily_client: ResilientTavilyClient,
        query: str,
    ) -> dict[str, Any]:
        """Search using Tavily for deep research."""
        logger.info("Searching with Tavily for deep research")
        results: dict[str, Any] = {"research_results": []}

        try:
            # Perform deep research
            response = await tavily_client.research(
                query=f"{query} niche market business opportunities",
                max_iterations=3,
            )
            results["research_results"] = response.results

        except NicheResearchAgentError as e:
            logger.error(f"Tavily research failed: {e}")
            results["errors"] = [str(e)]

        return results

    async def _search_exa_parallel(
        self,
        exa_client: ResilientExaClient,
        query: str,
    ) -> dict[str, Any]:
        """
        Search using EXA for semantic/neural search.

        EXA understands meaning, not just keywords - great for finding
        companies, trends, and content by concept.

        Free tier: 1,000 searches/month
        """
        logger.info("Searching with EXA for semantic/neural search")
        results: dict[str, Any] = {
            "web_results": [],
            "market_insights": [],
            "errors": [],
        }

        try:
            # Semantic search for market insights
            search_queries = [
                f"{query} market opportunities",
                f"{query} business problems challenges",
                f"{query} Reddit community discussion",
            ]

            for search_query in search_queries:
                try:
                    response = await exa_client.search(
                        query=search_query,
                        num_results=10,
                        use_autoprompt=True,
                    )

                    for item in response.results:
                        results["web_results"].append(
                            {
                                "title": item.title,
                                "url": item.url,
                                "description": item.summary or "",
                                "score": item.score,
                                "source": "exa_semantic",
                            }
                        )

                        # Check if it's a Reddit URL (subreddit discovery)
                        if "reddit.com/r/" in item.url:
                            parts = item.url.split("/r/")
                            if len(parts) > 1:
                                subreddit_name = parts[1].split("/")[0].lower()
                                results["market_insights"].append(
                                    {
                                        "insight": f"Reddit community r/{subreddit_name} discusses {query}",
                                        "opportunity": item.title,
                                        "evidence": item.url,
                                        "source": "exa_semantic",
                                    }
                                )

                except NicheResearchAgentError as e:
                    logger.warning(f"EXA search failed for '{search_query}': {e}")
                    continue

            logger.info(
                f"EXA search complete: {len(results['web_results'])} results, "
                f"{len(results['market_insights'])} insights"
            )

        except Exception as e:
            logger.error(f"EXA search failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _search_serper_parallel(
        self,
        serper_client: ResilientSerperClient,
        query: str,
    ) -> dict[str, Any]:
        """
        Search using Serper for Google Search results.

        Returns organic results, knowledge graphs, "People Also Ask",
        and related searches - great for market validation.

        Free tier: 2,500 queries included!
        """
        logger.info("Searching with Serper for Google Search results")
        results: dict[str, Any] = {
            "web_results": [],
            "market_insights": [],
            "posts": [],  # Pain points from "People Also Ask"
            "errors": [],
        }

        try:
            # Multiple search queries for comprehensive coverage
            search_queries = [
                f"{query} market size trends",
                f"site:reddit.com {query}",
                f"{query} problems challenges issues",
            ]

            for search_query in search_queries:
                try:
                    response = await serper_client.search(
                        query=search_query,
                        num=15,
                    )

                    # Organic results
                    for item in response.organic:
                        results["web_results"].append(
                            {
                                "title": item.title,
                                "url": item.link,
                                "description": item.snippet,
                                "source": "serper_google",
                            }
                        )

                        # Check for Reddit posts (not just subreddit links)
                        if "reddit.com/r/" in item.link and "/comments/" in item.link:
                            # It's a post - useful for pain point extraction
                            parts = item.link.split("/r/")
                            subreddit = parts[1].split("/")[0] if len(parts) > 1 else "unknown"
                            results["posts"].append(
                                {
                                    "title": item.title,
                                    "url": item.link,
                                    "subreddit": subreddit,
                                    "source": "serper_google",
                                }
                            )

                    # Knowledge Graph (if available)
                    if response.knowledge_graph:
                        kg = response.knowledge_graph
                        results["market_insights"].append(
                            {
                                "insight": kg.title or "",
                                "opportunity": kg.description or "",
                                "evidence": kg.website or "",
                                "source": "serper_knowledge_graph",
                            }
                        )

                    # People Also Ask (great for pain point discovery!)
                    for paa in response.people_also_ask:
                        results["posts"].append(
                            {
                                "title": paa.question,
                                "url": paa.link or "",
                                "subreddit": "serper_paa",
                                "source": "serper_people_also_ask",
                            }
                        )
                        results["market_insights"].append(
                            {
                                "insight": paa.question,
                                "opportunity": paa.snippet or "",
                                "evidence": paa.link or "",
                                "source": "serper_people_also_ask",
                            }
                        )

                    # Related searches (trend discovery)
                    for rs in response.related_searches:
                        results["market_insights"].append(
                            {
                                "insight": f"Related search: {rs.query}",
                                "opportunity": f"People also search for: {rs.query}",
                                "evidence": "",
                                "source": "serper_related",
                            }
                        )

                except NicheResearchAgentError as e:
                    logger.warning(f"Serper search failed for '{search_query}': {e}")
                    continue

            logger.info(
                f"Serper search complete: {len(results['web_results'])} results, "
                f"{len(results['posts'])} posts, {len(results['market_insights'])} insights"
            )

        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _aggregate_findings(
        self,
        research_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Phase 1.2: Aggregate findings from all research sources.

        Combines data from Reddit, web search, Tavily, and Claude SDK into unified results.

        Args:
            research_data: Raw research data from all sources

        Returns:
            Dictionary with aggregated findings
        """
        logger.info("Aggregating findings from all sources")

        aggregated = {
            "subreddits": research_data.get("subreddits", []),
            "posts": research_data.get("posts", []),
            "web_results": research_data.get("web_results", []),
            "research_results": research_data.get("research_results", []),
            "pain_points_raw": research_data.get("pain_points_raw", []),
            "market_insights": research_data.get("market_insights", []),
            "trend_keywords": [],
        }

        # Extract trend keywords from web results
        keywords: Counter[str] = Counter()

        # From web results
        for result in aggregated["web_results"][:20]:
            title = (
                result.get("title", "")
                if isinstance(result, dict)
                else getattr(result, "title", "")
            )
            if title:
                words = title.lower().split()
                for word in words:
                    if len(word) > 4:
                        keywords[word] += 1

        # From market insights
        for insight in aggregated["market_insights"][:10]:
            if isinstance(insight, dict):
                text = insight.get("insight", "") + " " + insight.get("opportunity", "")
                words = text.lower().split()
                for word in words:
                    if len(word) > 4:
                        keywords[word] += 1

        # From pain points
        for pp in aggregated["pain_points_raw"][:10]:
            if isinstance(pp, dict):
                problem = pp.get("problem", "")
                words = problem.lower().split()
                for word in words:
                    if len(word) > 4:
                        keywords[word] += 1

        aggregated["trend_keywords"] = [kw for kw, _ in keywords.most_common(30)]

        logger.info(
            f"Aggregated: {len(aggregated['subreddits'])} subreddits, "
            f"{len(aggregated['posts'])} posts, "
            f"{len(aggregated['web_results'])} web results, "
            f"{len(aggregated['market_insights'])} market insights, "
            f"{len(aggregated['pain_points_raw'])} raw pain points"
        )
        return aggregated

    async def _score_subreddits(
        self,
        aggregated_data: dict[str, Any],
        engagement_weight: float,
        relevance_weight: float,
    ) -> list[NicheSubreddit]:
        """
        Phase 1.3: Score subreddits by relevance and engagement.

        Args:
            aggregated_data: Aggregated research findings
            engagement_weight: Weight for engagement score
            relevance_weight: Weight for relevance score

        Returns:
            List of scored niche subreddits
        """
        logger.info("Scoring subreddits by relevance and engagement")

        scored_subreddits: list[NicheSubreddit] = []

        for subreddit in aggregated_data.get("subreddits", []):
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(subreddit)

            # Calculate relevance score based on keyword matching
            relevance_score = self._calculate_relevance_score(
                subreddit,
                aggregated_data.get("trend_keywords", []),
            )

            # Handle both RedditSubreddit and NicheSubreddit input types
            # If it's already a NicheSubreddit, just update scores
            if isinstance(subreddit, NicheSubreddit):
                subreddit.engagement_score = engagement_score
                subreddit.relevance_score = relevance_score
                niche_sub = subreddit
            else:
                # It's a RedditSubreddit - convert to NicheSubreddit
                niche_sub = NicheSubreddit(
                    name=subreddit.name,
                    title=subreddit.title,
                    description=getattr(subreddit, "public_description", "")
                    or getattr(subreddit, "description", "")
                    or "",
                    subscriber_count=getattr(subreddit, "subscribers", 0)
                    or getattr(subreddit, "subscriber_count", 0)
                    or 0,
                    active_users=getattr(subreddit, "active_users", 0) or 0,
                    engagement_score=engagement_score,
                    relevance_score=relevance_score,
                    url=getattr(subreddit, "url", ""),
                    created_at=datetime.fromtimestamp(getattr(subreddit, "created_utc", 0))
                    if getattr(subreddit, "created_utc", 0)
                    else datetime.now(),
                    raw=getattr(subreddit, "raw", {}),
                )

            scored_subreddits.append(niche_sub)

        # Sort by combined score (descending)
        scored_subreddits.sort(
            key=lambda s: s.engagement_score * engagement_weight
            + s.relevance_score * relevance_weight,
            reverse=True,
        )

        logger.info(f"Scored {len(scored_subreddits)} subreddits")
        return scored_subreddits

    async def _extract_pain_points(
        self,
        aggregated_data: dict[str, Any],
        scored_subreddits: list[NicheSubreddit],
    ) -> list[NichePainPoint]:
        """
        Phase 1.4: Extract pain points from discussions.

        Analyzes post titles and content to identify common pain points.

        Args:
            aggregated_data: Aggregated research findings
            scored_subreddits: List of scored subreddits

        Returns:
            List of identified pain points
        """
        logger.info("Extracting pain points from discussions")

        pain_points: list[NichePainPoint] = []

        # Analyze post titles for pain point indicators
        pain_indicators = [
            "problem",
            "issue",
            "struggle",
            "difficult",
            "hard",
            "challenge",
            "frustrated",
            "annoying",
            "help",
            "how to",
            "need",
            "want",
            "looking for",
            "any advice",
            "solutions",
            "fix",
            "workaround",
        ]

        posts = aggregated_data.get("posts", [])

        # Count pain point mentions
        pain_counter: Counter[str] = Counter()
        source_posts: dict[str, list[str]] = {}

        for post in posts:
            # Handle both dict (from web search) and object (from Reddit API) formats
            if isinstance(post, dict):
                title = post.get("title", "")
                permalink = post.get("url", "") or post.get("permalink", "")
            else:
                title = getattr(post, "title", "")
                permalink = getattr(post, "permalink", "") or getattr(post, "url", "")

            title_lower = title.lower()

            # Check for pain indicators
            for indicator in pain_indicators:
                if indicator in title_lower:
                    # Extract the pain context (simple approach)
                    pain_context = self._extract_pain_context(title, indicator)
                    if pain_context:
                        pain_counter[pain_context] += 1
                        if pain_context not in source_posts:
                            source_posts[pain_context] = []
                        source_posts[pain_context].append(permalink)

        # Create pain point objects
        for pain, freq in pain_counter.most_common(10):
            severity = "high" if freq >= 5 else "medium" if freq >= 3 else "low"

            pain_point = NichePainPoint(
                description=pain,
                severity=severity,
                frequency=freq,
                source_posts=source_posts.get(pain, [])[:3],  # Top 3 sources
                source_subreddits=[s.name for s in scored_subreddits[:3]],
            )
            pain_points.append(pain_point)

        logger.info(f"Extracted {len(pain_points)} pain points")
        return pain_points

    def _extract_pain_context(self, title: str, indicator: str) -> str | None:
        """
        Extract pain context from post title.

        Args:
            title: Post title
            indicator: Pain indicator word found in title

        Returns:
            Pain context description or None
        """
        # Simple extraction: return the title with the indicator highlighted
        if indicator in title.lower():
            # Return a cleaned version of the title
            return title.strip()

        return None

    async def _identify_opportunities(
        self,
        pain_points: list[NichePainPoint],
        scored_subreddits: list[NicheSubreddit],
    ) -> list[NicheOpportunity]:
        """
        Phase 1.5: Identify business opportunities from pain points.

        For each pain point, identifies potential solutions/business opportunities.

        Args:
            pain_points: List of identified pain points
            scored_subreddits: List of scored subreddits

        Returns:
            List of identified opportunities
        """
        logger.info("Identifying business opportunities")

        opportunities: list[NicheOpportunity] = []

        # Total potential reach across all subreddits
        total_reach = sum(s.subscriber_count for s in scored_subreddits)

        for pain_point in pain_points[:5]:  # Top 5 pain points
            # Generate opportunity description
            opp_description = f"Solve {pain_point.description.lower()}"

            # Estimate potential reach
            potential_reach = min(total_reach, pain_point.frequency * 1000)

            # Confidence based on pain point severity and frequency
            severity_scores = {"high": 0.9, "medium": 0.6, "low": 0.3}
            confidence = severity_scores.get(pain_point.severity, 0.5) * min(
                pain_point.frequency / 10, 1.0
            )

            opportunity = NicheOpportunity(
                description=opp_description,
                pain_point=pain_point.description,
                target_audience=", ".join(s.name for s in scored_subreddits[:3]),
                potential_reach=potential_reach,
                confidence_score=confidence,
                supporting_evidence=pain_point.source_posts[:2],
            )
            opportunities.append(opportunity)

        logger.info(f"Identified {len(opportunities)} opportunities")
        return opportunities

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health of the niche research agent.

        Verifies connectivity to all required services.

        Returns:
            Dictionary with health status for each service
        """
        services: dict[str, dict[str, Any]] = {}
        healthy = True

        # Check Reddit
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                reddit_client = ResilientRedditClient(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent="smarter-team-niche-research/1.0",
                )
                # Simple test search
                await reddit_client.search_subreddits("test", limit=1)
                services["reddit"] = {"healthy": True}
            except Exception as e:
                services["reddit"] = {"healthy": False, "error": str(e)}
                healthy = False
        else:
            services["reddit"] = {"healthy": False, "error": "No credentials"}
            healthy = False

        # Check Brave
        if self.brave_api_key:
            try:
                brave_client = ResilientBraveClient(api_key=self.brave_api_key)
                await brave_client.search("test", count=1)
                services["brave"] = {"healthy": True}
            except Exception as e:
                services["brave"] = {"healthy": False, "error": str(e)}
        else:
            services["brave"] = {"healthy": False, "error": "No API key"}

        # Check Tavily
        if self.tavily_api_key:
            try:
                tavily_client = ResilientTavilyClient(api_key=self.tavily_api_key)
                await tavily_client.research("test", max_iterations=1)
                services["tavily"] = {"healthy": True}
            except Exception as e:
                services["tavily"] = {"healthy": False, "error": str(e)}
        else:
            services["tavily"] = {"healthy": False, "error": "No API key"}

        return {
            "agent": self.name,
            "services": services,
            "healthy": healthy,
        }

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return """You are a Niche Research Agent specializing in market discovery and analysis.

Your capabilities include:
- Discovering relevant communities (subreddits) for any niche
- Analyzing engagement and relevance metrics
- Extracting common pain points from community discussions
- Identifying business opportunities based on pain points

You use Reddit, web search, and AI analysis to provide comprehensive insights."""

    # ========================================================================
    # Google Drive/Docs Export Methods
    # ========================================================================

    async def export_to_google_drive(
        self,
        result: NicheResearchResult,
        parent_folder_id: str,
        credentials_path: str | None = None,
        delegated_user: str | None = None,
    ) -> dict[str, Any]:
        """
        Export research results to Google Drive as formatted Google Docs.

        Creates a folder with the niche name and date, containing:
        1. Niche Overview - Summary, scores, subreddits
        2. Pain Points Analysis - All discovered pain points
        3. Market Insights - Opportunities and trends
        4. Raw Data - JSON export of all data

        Args:
            result: NicheResearchResult from research_niche()
            parent_folder_id: Google Drive folder ID to create research folder in
            credentials_path: Path to Google service account JSON (optional)
            delegated_user: Email to impersonate for domain-wide delegation

        Returns:
            Dictionary with folder_url and document URLs

        Example:
            >>> result = await agent.research_niche("AI tools for solopreneurs")
            >>> export = await agent.export_to_google_drive(
            ...     result=result,
            ...     parent_folder_id="1abc123...",
            ...     delegated_user="yasmine@smarterflo.com"
            ... )
            >>> print(export["folder_url"])
        """
        import json

        logger.info(f"Exporting research to Google Drive: {result.niche}")

        # Load credentials
        credentials_json = None
        if credentials_path:
            with open(credentials_path) as f:
                credentials_json = json.load(f)
        else:
            # Try environment variable
            creds_env = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
            if creds_env:
                if creds_env.startswith("{"):
                    credentials_json = json.loads(creds_env)
                elif os.path.exists(creds_env):
                    with open(creds_env) as f:
                        credentials_json = json.load(f)

        if not credentials_json:
            raise NicheResearchAgentError(
                "Google credentials required. Set GOOGLE_DRIVE_CREDENTIALS_JSON or pass credentials_path"
            )

        # Initialize clients
        drive_client = GoogleDriveClient(
            credentials_json=credentials_json,
            delegated_user=delegated_user or os.getenv("GOOGLE_DELEGATED_USER"),
        )
        docs_client = GoogleDocsClient(
            credentials_json=credentials_json,
            delegated_user=delegated_user or os.getenv("GOOGLE_DELEGATED_USER"),
        )

        try:
            # Authenticate
            await drive_client.authenticate()
            await docs_client.authenticate()

            # Create folder for this research
            folder_name = f"{result.niche} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            folder = await drive_client.create_document(
                title=folder_name,
                mime_type="application/vnd.google-apps.folder",
                parent_folder_id=parent_folder_id,
            )
            folder_id = folder.get("id")
            logger.info(f"Created folder: {folder_name} ({folder_id})")

            documents: list[dict[str, Any]] = []

            # 1. Create Niche Overview Document
            overview_content = self._generate_overview_content(result)
            overview_doc = await docs_client.create_document(
                title=f"1. Niche Overview - {result.niche}",
                parent_folder_id=folder_id,
            )
            await docs_client.insert_text(overview_doc["documentId"], overview_content)
            documents.append(
                {
                    "name": "Niche Overview",
                    "type": "overview",
                    "doc_id": overview_doc["documentId"],
                    "url": f"https://docs.google.com/document/d/{overview_doc['documentId']}/edit",
                }
            )
            logger.info("Created Niche Overview doc")

            # 2. Create Pain Points Document
            pain_points_content = self._generate_pain_points_content(result)
            pain_doc = await docs_client.create_document(
                title=f"2. Pain Points Analysis - {result.niche}",
                parent_folder_id=folder_id,
            )
            await docs_client.insert_text(pain_doc["documentId"], pain_points_content)
            documents.append(
                {
                    "name": "Pain Points Analysis",
                    "type": "pain_points",
                    "doc_id": pain_doc["documentId"],
                    "url": f"https://docs.google.com/document/d/{pain_doc['documentId']}/edit",
                }
            )
            logger.info("Created Pain Points doc")

            # 3. Create Market Insights Document
            insights_content = self._generate_insights_content(result)
            insights_doc = await docs_client.create_document(
                title=f"3. Market Insights - {result.niche}",
                parent_folder_id=folder_id,
            )
            await docs_client.insert_text(insights_doc["documentId"], insights_content)
            documents.append(
                {
                    "name": "Market Insights",
                    "type": "insights",
                    "doc_id": insights_doc["documentId"],
                    "url": f"https://docs.google.com/document/d/{insights_doc['documentId']}/edit",
                }
            )
            logger.info("Created Market Insights doc")

            # 4. Create Raw Data JSON
            raw_data = {
                "niche": result.niche,
                "total_subscribers": result.total_subscribers,
                "total_active_users": result.total_active_users,
                "subreddits": [
                    {
                        "name": s.name,
                        "title": s.title,
                        "description": s.description,
                        "subscriber_count": s.subscriber_count,
                        "engagement_score": s.engagement_score,
                        "relevance_score": s.relevance_score,
                    }
                    for s in result.subreddits
                ],
                "pain_points": [
                    {
                        "description": p.description,
                        "severity": p.severity,
                        "frequency": p.frequency,
                        "source_subreddits": p.source_subreddits,
                    }
                    for p in result.pain_points
                ],
                "opportunities": [
                    {
                        "description": o.description,
                        "target_audience": o.target_audience,
                        "potential_reach": o.potential_reach,
                        "confidence_score": o.confidence_score,
                    }
                    for o in result.opportunities
                ],
            }
            raw_doc = await docs_client.create_document(
                title=f"4. Raw Data - {result.niche}",
                parent_folder_id=folder_id,
            )
            await docs_client.insert_text(
                raw_doc["documentId"],
                json.dumps(raw_data, indent=2, default=str),
            )
            documents.append(
                {
                    "name": "Raw Data",
                    "type": "raw_data",
                    "doc_id": raw_doc["documentId"],
                    "url": f"https://docs.google.com/document/d/{raw_doc['documentId']}/edit",
                }
            )
            logger.info("Created Raw Data doc")

            # Make folder shareable
            await drive_client.share_file(
                file_id=folder_id,
                share_type="anyone",
                role="reader",
            )

            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

            logger.info(f"Export complete: {folder_url}")

            return {
                "folder_id": folder_id,
                "folder_url": folder_url,
                "folder_name": folder_name,
                "documents": documents,
                "niche": result.niche,
                "exported_at": datetime.now().isoformat(),
            }

        finally:
            await drive_client.close()
            await docs_client.close()

    def _generate_overview_content(self, result: NicheResearchResult) -> str:
        """Generate formatted content for Niche Overview document."""
        lines = [
            f"NICHE OVERVIEW: {result.niche.upper()}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "=" * 60,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Total Market Reach: {result.total_subscribers:,} subscribers",
            f"Active Users: {result.total_active_users:,}",
            f"Communities Found: {len(result.subreddits)}",
            f"Pain Points Identified: {len(result.pain_points)}",
            f"Business Opportunities: {len(result.opportunities)}",
            "",
            "=" * 60,
            "",
            "RELEVANT COMMUNITIES",
            "-" * 40,
        ]

        for i, sub in enumerate(result.subreddits[:15], 1):
            lines.extend(
                [
                    f"{i}. r/{sub.name}",
                    f"   Subscribers: {sub.subscriber_count:,}",
                    f"   Engagement Score: {sub.engagement_score:.1f}/10",
                    f"   Relevance Score: {sub.relevance_score:.1f}/10",
                    f"   Description: {sub.description[:200]}..."
                    if len(sub.description) > 200
                    else f"   Description: {sub.description}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _generate_pain_points_content(self, result: NicheResearchResult) -> str:
        """Generate formatted content for Pain Points document."""
        lines = [
            f"PAIN POINTS ANALYSIS: {result.niche.upper()}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "=" * 60,
            "",
            f"Total Pain Points Discovered: {len(result.pain_points)}",
            "",
        ]

        # Group by severity
        high = [p for p in result.pain_points if p.severity == "high"]
        medium = [p for p in result.pain_points if p.severity == "medium"]
        low = [p for p in result.pain_points if p.severity == "low"]

        if high:
            lines.extend(
                [
                    "HIGH SEVERITY PAIN POINTS",
                    "-" * 40,
                ]
            )
            for i, pp in enumerate(high, 1):
                lines.extend(
                    [
                        f"{i}. {pp.description}",
                        f"   Frequency: {pp.frequency} mentions",
                        f"   Sources: {', '.join(pp.source_subreddits[:5])}",
                        "",
                    ]
                )

        if medium:
            lines.extend(
                [
                    "",
                    "MEDIUM SEVERITY PAIN POINTS",
                    "-" * 40,
                ]
            )
            for i, pp in enumerate(medium, 1):
                lines.extend(
                    [
                        f"{i}. {pp.description}",
                        f"   Frequency: {pp.frequency} mentions",
                        f"   Sources: {', '.join(pp.source_subreddits[:5])}",
                        "",
                    ]
                )

        if low:
            lines.extend(
                [
                    "",
                    "LOW SEVERITY PAIN POINTS",
                    "-" * 40,
                ]
            )
            for i, pp in enumerate(low, 1):
                lines.extend(
                    [
                        f"{i}. {pp.description}",
                        f"   Frequency: {pp.frequency} mentions",
                        f"   Sources: {', '.join(pp.source_subreddits[:5])}",
                        "",
                    ]
                )

        return "\n".join(lines)

    def _generate_insights_content(self, result: NicheResearchResult) -> str:
        """Generate formatted content for Market Insights document."""
        lines = [
            f"MARKET INSIGHTS: {result.niche.upper()}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "=" * 60,
            "",
            "BUSINESS OPPORTUNITIES",
            "-" * 40,
        ]

        for i, opp in enumerate(result.opportunities, 1):
            confidence_pct = int(opp.confidence_score * 100)
            lines.extend(
                [
                    f"{i}. {opp.description}",
                    f"   Target Audience: {opp.target_audience}",
                    f"   Potential Reach: {opp.potential_reach:,} users",
                    f"   Confidence: {confidence_pct}%",
                    "",
                ]
            )

        # Add market insights from metadata if available
        if hasattr(result, "research_metadata") and result.research_metadata:
            metadata = result.research_metadata
            if "market_insights" in metadata:
                lines.extend(
                    [
                        "",
                        "=" * 60,
                        "",
                        "ADDITIONAL MARKET INSIGHTS",
                        "-" * 40,
                    ]
                )
                for insight in metadata.get("market_insights", [])[:10]:
                    if isinstance(insight, dict):
                        lines.append(f"• {insight.get('insight', insight.get('title', ''))}")
                        if insight.get("opportunity"):
                            lines.append(f"  → {insight['opportunity']}")
                        lines.append("")

        lines.extend(
            [
                "",
                "=" * 60,
                "",
                "RECOMMENDED NEXT STEPS",
                "-" * 40,
                "1. Validate top pain points with direct outreach",
                "2. Research existing solutions and their gaps",
                "3. Identify key influencers in these communities",
                "4. Develop messaging angles based on pain points",
                "5. Create lead lists from identified communities",
            ]
        )

        return "\n".join(lines)


# ============================================================================
# SDK MCP Server Factory
# ============================================================================


def create_niche_research_mcp_server() -> Any:
    """
    Create SDK MCP server for niche research tools.

    Returns:
        SDK MCP server instance
    """
    return create_sdk_mcp_server(
        name="niche_research",
        version="1.0.0",
        tools=[
            search_reddit_tool,
            extract_pain_points_tool,
            identify_opportunities_tool,
        ],
    )
