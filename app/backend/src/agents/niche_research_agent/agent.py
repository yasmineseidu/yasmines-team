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
from claude_agent_sdk import create_sdk_mcp_server, tool
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.brave import BraveClient
from src.integrations.reddit import (
    RedditClient,
    RedditPost,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
)
from src.integrations.tavily import TavilyClient
from src.models.niche_research import (
    NicheOpportunity,
    NichePainPoint,
    NicheResearchResult,
    NicheSubreddit,
)

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
# Token Bucket Rate Limiter
# ============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API calls.

    Allows bursts up to capacity, then refills at refill_rate per second.
    """

    def __init__(self, capacity: int, refill_rate: float, service_name: str) -> None:
        """
        Initialize rate limiter.

        Args:
            capacity: Maximum tokens (burst capacity)
            refill_rate: Tokens to add per second
            service_name: Service name for logging
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.service_name = service_name
        self.tokens = float(capacity)
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate,
            )
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Wait for tokens to be available
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            logger.debug(
                f"[{self.service_name}] Rate limit reached. "
                f"Waiting {wait_time:.2f}s for token refill"
            )

            await asyncio.sleep(wait_time)

            # Refill and acquire
            self.tokens = self.capacity
            self.tokens -= tokens


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
    },
)
async def search_reddit_tool(args: dict[str, Any], reddit_client: RedditClient) -> dict[str, Any]:
    """
    SDK MCP tool for searching Reddit.

    Args:
        args: Tool arguments with query, max_subreddits, etc.
        reddit_client: Authenticated Reddit client

    Returns:
        Tool result with subreddits and posts
    """
    try:
        query = args["query"]
        max_subreddits = args.get("max_subreddits", 10)
        posts_per_subreddit = args.get("posts_per_subreddit", 25)
        min_subscribers = args.get("min_subscribers", 1000)
        include_nsfw = args.get("include_nsfw", False)

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

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            httpx.TimeoutException | httpx.NetworkError | ServiceUnavailableError
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

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            httpx.TimeoutException | httpx.NetworkError | ServiceUnavailableError
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

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            httpx.TimeoutException | httpx.NetworkError | ServiceUnavailableError
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

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1.0, max=60.0),
        retry=retry_if_exception_type(
            httpx.TimeoutException | httpx.NetworkError | ServiceUnavailableError
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
    ) -> None:
        """
        Initialize the Niche Research Agent.

        Args:
            reddit_client_id: Reddit app client ID (from environment if not provided)
            reddit_client_secret: Reddit app client secret (from environment if not provided)
            brave_api_key: Brave Search API key (from environment if not provided)
            tavily_api_key: Tavily Search API key (from environment if not provided)
        """
        # Get API keys from environment if not provided
        self.reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY", "")
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")

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
            subreddit: RedditSubreddit object

        Returns:
            Engagement score (0.0 to 10.0)
        """
        # Active user ratio (higher is better)
        if subreddit.subscribers > 0:
            active_ratio = subreddit.active_users / subreddit.subscribers
        else:
            active_ratio = 0.0

        # Normalize active ratio (typically 0.01 to 0.10)
        active_score = min(active_ratio * 20, 5.0)

        # Subscriber score (logarithmic, max 5.0)
        if subreddit.subscribers > 0:
            sub_score = min(math.log10(subreddit.subscribers) / 2, 5.0)
        else:
            sub_score = 0.0

        return active_score + sub_score

    def _calculate_relevance_score(
        self,
        subreddit: RedditSubreddit,
        keywords: list[str],
    ) -> float:
        """
        Calculate relevance score based on keyword matching.

        Args:
            subreddit: RedditSubreddit object
            keywords: List of trend keywords

        Returns:
            Relevance score (0.0 to 10.0)
        """
        description_lower = subreddit.title.lower() + " " + subreddit.public_description.lower()

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

        try:
            # Phase 1: Parallel web research
            research_data = await self._parallel_web_research(
                query,
                reddit_client,
                brave_client,
                tavily_client,
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
        max_subreddits: int,
        posts_per_subreddit: int,
        min_subscribers: int,
        include_nsfw: bool,
    ) -> dict[str, Any]:
        """
        Phase 1.1: Parallel web research using multiple sources.

        Searches Reddit, Brave, and Tavily in parallel for maximum speed.

        Args:
            query: Niche search query
            reddit_client: Resilient Reddit client
            brave_client: Resilient Brave client
            tavily_client: Resilient Tavily client
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

        # Create tasks for parallel execution
        tasks = []

        # Reddit search task
        if reddit_client:
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

        # Brave web search task
        if brave_client:
            tasks.append(self._search_web_parallel(brave_client, query))

        # Tavily research task
        if tavily_client:
            tasks.append(self._search_tavily_parallel(tavily_client, query))

        # Execute all tasks in parallel
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    logger.warning(f"Research task {i} failed: {result}")
                    results["errors"].append(str(result))
                elif isinstance(result, dict):
                    # Merge results
                    results.update(result)

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

    async def _aggregate_findings(
        self,
        research_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Phase 1.2: Aggregate findings from all research sources.

        Combines data from Reddit, web search, and Tavily into unified results.

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
            "trend_keywords": [],
        }

        # Extract trend keywords from web results
        keywords: Counter[str] = Counter()
        for result in aggregated["web_results"][:20]:
            # Simple keyword extraction from titles
            words = result.title.lower().split()
            for word in words:
                if len(word) > 4:  # Only meaningful words
                    keywords[word] += 1

        aggregated["trend_keywords"] = [kw for kw, _ in keywords.most_common(20)]

        logger.info(f"Aggregated {len(aggregated['subreddits'])} subreddits")
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

            niche_sub = NicheSubreddit(
                name=subreddit.name,
                title=subreddit.title,
                description=subreddit.public_description,
                subscriber_count=subreddit.subscribers,
                active_users=subreddit.active_users,
                engagement_score=engagement_score,
                relevance_score=relevance_score,
                url=subreddit.url,
                created_at=datetime.fromtimestamp(subreddit.created_utc),
                raw=subreddit.raw if hasattr(subreddit, "raw") else {},
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
            title_lower = post.title.lower()

            # Check for pain indicators
            for indicator in pain_indicators:
                if indicator in title_lower:
                    # Extract the pain context (simple approach)
                    pain_context = self._extract_pain_context(post.title, indicator)
                    if pain_context:
                        pain_counter[pain_context] += 1
                        if pain_context not in source_posts:
                            source_posts[pain_context] = []
                        source_posts[pain_context].append(post.permalink)

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
