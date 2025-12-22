"""
Reddit API integration client for niche research and pain point extraction.

Provides async access to Reddit's OAuth2 API for:
- Subreddit discovery and analysis
- Post retrieval (hot, new, top, rising)
- Comment extraction and thread analysis
- User behavior tracking
- Engagement metrics (upvotes, comments, awards)
- Pain point and sentiment extraction

API Documentation:
- OAuth2: https://github.com/reddit-archive/reddit/wiki/OAuth2
- API: https://www.reddit.com/dev/api/

Authentication:
- Uses OAuth2 "script" app flow (client credentials)
- Tokens expire after 1 hour (auto-refresh implemented)
- Rate limit: 100 requests/minute per OAuth client ID

Example:
    >>> from src.integrations.reddit import RedditClient
    >>> client = RedditClient(
    ...     client_id="your_client_id",
    ...     client_secret="your_client_secret",  # pragma: allowlist secret
    ...     user_agent="smarter-team/1.0"
    ... )
    >>> async with client:
    ...     posts = await client.get_subreddit_posts("entrepreneur", sort="hot", limit=25)
    ...     for post in posts:
    ...         print(f"{post.title} - {post.score} upvotes")
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class RedditSortType(str, Enum):
    """Sort types for Reddit listings."""

    HOT = "hot"
    NEW = "new"
    TOP = "top"
    RISING = "rising"
    CONTROVERSIAL = "controversial"


class RedditTimeFilter(str, Enum):
    """Time filters for Reddit top/controversial listings."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"


class RedditError(IntegrationError):
    """Reddit-specific error."""

    pass


class RedditAuthError(AuthenticationError):
    """Reddit authentication error."""

    pass


class RedditRateLimitError(RateLimitError):
    """Reddit rate limit error."""

    pass


@dataclass
class RedditSubreddit:
    """Subreddit information."""

    name: str
    display_name: str
    title: str
    description: str
    public_description: str
    subscribers: int
    active_users: int
    created_utc: float
    over18: bool
    subreddit_type: str
    url: str
    icon_url: str | None = None
    banner_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RedditPost:
    """Reddit post/submission."""

    id: str
    subreddit: str
    title: str
    selftext: str
    author: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    url: str
    permalink: str
    is_self: bool
    is_video: bool
    over_18: bool
    spoiler: bool
    stickied: bool
    locked: bool
    distinguished: str | None = None
    link_flair_text: str | None = None
    author_flair_text: str | None = None
    thumbnail: str | None = None
    preview_url: str | None = None
    awards_count: int = 0
    total_awards_received: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RedditComment:
    """Reddit comment."""

    id: str
    post_id: str
    subreddit: str
    body: str
    author: str
    score: int
    created_utc: float
    permalink: str
    is_submitter: bool
    stickied: bool
    distinguished: str | None = None
    parent_id: str | None = None
    depth: int = 0
    awards_count: int = 0
    replies_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RedditUser:
    """Reddit user profile."""

    id: str
    name: str
    created_utc: float
    link_karma: int
    comment_karma: int
    total_karma: int
    is_gold: bool
    is_mod: bool
    has_verified_email: bool
    icon_url: str | None = None
    subreddit_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RedditSearchResult:
    """Search results from Reddit."""

    posts: list[RedditPost] = field(default_factory=list)
    after: str | None = None
    before: str | None = None
    count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubredditAnalysis:
    """Analysis results for a subreddit."""

    subreddit: RedditSubreddit
    top_posts: list[RedditPost]
    common_topics: list[str]
    engagement_metrics: dict[str, float]
    pain_points: list[str]
    raw: dict[str, Any] = field(default_factory=dict)


class RedditClient(BaseIntegrationClient):
    """
    Async Reddit API client for niche research and pain point extraction.

    Uses OAuth2 "script" app flow with automatic token refresh.
    Rate limited to 100 requests/minute per OAuth client ID.

    Example:
        >>> async with RedditClient(
        ...     client_id="id",
        ...     client_secret="secret",  # pragma: allowlist secret
        ...     user_agent="myapp/1.0"
        ... ) as client:
        ...     subreddit = await client.get_subreddit("entrepreneur")
        ...     print(f"{subreddit.display_name}: {subreddit.subscribers} subscribers")
    """

    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    API_BASE_URL = "https://oauth.reddit.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "smarter-team/1.0 (by /u/smarter-team-bot)",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Reddit client.

        Args:
            client_id: Reddit app client ID (from reddit.com/prefs/apps)
            client_secret: Reddit app client secret
            user_agent: User-Agent string (required by Reddit API)
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
        """
        # Initialize with placeholder API key - we use OAuth tokens
        super().__init__(
            name="reddit",
            base_url=self.API_BASE_URL,
            api_key="",  # Not used - we use OAuth
            timeout=timeout,
            max_retries=max_retries,
        )

        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._token_lock = asyncio.Lock()

    async def _ensure_access_token(self) -> str:
        """
        Ensure we have a valid access token, refreshing if needed.

        Uses lazy refresh - token is refreshed when expired or about to expire.
        Token is considered expired 60 seconds before actual expiry to avoid
        race conditions.

        Returns:
            Valid access token.

        Raises:
            RedditAuthError: If token acquisition fails.
        """
        async with self._token_lock:
            # Refresh if token is missing or expires in less than 60 seconds
            if self._access_token is None or time.time() >= self._token_expires_at - 60:
                await self._refresh_access_token()

            if self._access_token is None:
                raise RedditAuthError("Failed to acquire access token")

            return self._access_token

    async def _refresh_access_token(self) -> None:
        """
        Refresh the OAuth2 access token using client credentials.

        Reddit requires HTTP Basic Auth with client_id:client_secret
        for the token endpoint.

        Raises:
            RedditAuthError: If token refresh fails.
        """
        # Create Basic Auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "User-Agent": self.user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "client_credentials",
        }

        try:
            response = await self.client.post(
                self.AUTH_URL,
                headers=headers,
                data=data,
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise RedditAuthError(
                    message=f"Token refresh failed: {error_data.get('error', 'Unknown error')}",
                    response_data=error_data,
                )

            token_data = response.json()
            self._access_token = token_data["access_token"]
            # Token expires in 3600 seconds (1 hour)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in

            logger.info(f"[{self.name}] Access token refreshed, expires in {expires_in}s")

        except httpx.HTTPError as e:
            raise RedditAuthError(
                message=f"Token refresh failed: {e}",
            ) from e

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for Reddit API requests.

        Note: This returns headers without the Bearer token.
        Use _get_auth_headers() for authenticated requests.
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    async def _get_auth_headers(self) -> dict[str, str]:
        """
        Get authenticated headers for Reddit API requests.

        Returns:
            Headers dict with Bearer token.
        """
        token = await self._ensure_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry and auth handling.

        Overrides base class to handle Reddit-specific auth and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            Parsed JSON response data.

        Raises:
            RedditError: After all retries exhausted.
        """
        url = f"{self.base_url}{endpoint}"

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                # Get fresh auth headers for each attempt
                headers = await self._get_auth_headers()

                # Merge custom headers if provided
                if "headers" in kwargs:
                    headers.update(kwargs.pop("headers"))

                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )

                return await self._handle_response(response)

            except AuthenticationError:
                # Token might be expired - force refresh and retry once
                if attempt == 0:
                    logger.warning(f"[{self.name}] Auth failed, forcing token refresh")
                    self._access_token = None
                    continue
                raise

            except Exception as error:
                last_error = error
                is_retryable = self._is_retryable_error(error)

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[{self.name}] Request failed: {error}",
                        extra={
                            "integration": self.name,
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = self.retry_base_delay * (2**attempt)
                jitter = delay * (0.1 + 0.4 * (attempt / self.max_retries))
                delay += jitter

                logger.warning(
                    f"[{self.name}] Request failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {error}",
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise RedditError(f"[{self.name}] Request failed after {self.max_retries} retries")

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON response data.

        Raises:
            RedditAuthError: For 401/403 responses.
            RedditRateLimitError: For 429 responses.
            RedditError: For other error responses.
        """
        data: dict[str, Any]
        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text}

        if response.status_code == 401:
            raise RedditAuthError(
                message=f"[{self.name}] Authentication failed",
                response_data=data,
            )

        if response.status_code == 403:
            raise RedditAuthError(
                message=f"[{self.name}] Access forbidden - check app permissions",
                response_data=data,
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RedditRateLimitError(
                message=f"[{self.name}] Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else 60,
                status_code=429,
                response_data=data,
            )

        if response.status_code >= 400:
            error_message = data.get("error", data.get("message", "Unknown error"))
            raise RedditError(
                message=f"[{self.name}] API error: {error_message}",
                status_code=response.status_code,
                response_data=data,
            )

        return data

    # =========================================================================
    # Subreddit Methods
    # =========================================================================

    async def get_subreddit(self, name: str) -> RedditSubreddit:
        """
        Get information about a subreddit.

        Args:
            name: Subreddit name (without r/ prefix)

        Returns:
            RedditSubreddit with subreddit details.

        Raises:
            RedditError: If request fails.
            ValueError: If subreddit name is empty.
        """
        if not name or not name.strip():
            raise ValueError("subreddit name is required")

        name = name.strip().lower().lstrip("r/")

        response = await self.get(f"/r/{name}/about")
        data = response.get("data", {})

        return self._parse_subreddit(data)

    async def search_subreddits(
        self,
        query: str,
        *,
        limit: int = 25,
        include_over18: bool = False,
    ) -> list[RedditSubreddit]:
        """
        Search for subreddits by name or description.

        Args:
            query: Search query
            limit: Maximum results to return (1-100, default 25)
            include_over18: Include NSFW subreddits (default False)

        Returns:
            List of matching subreddits.

        Raises:
            RedditError: If request fails.
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        params: dict[str, Any] = {
            "q": query.strip(),
            "limit": min(max(1, limit), 100),
            "include_over_18": "true" if include_over18 else "false",
        }

        response = await self.get("/subreddits/search", params=params)
        children = response.get("data", {}).get("children", [])

        return [self._parse_subreddit(child.get("data", {})) for child in children]

    async def get_subreddit_rules(self, name: str) -> list[dict[str, Any]]:
        """
        Get rules for a subreddit.

        Args:
            name: Subreddit name (without r/ prefix)

        Returns:
            List of subreddit rules.

        Raises:
            RedditError: If request fails.
        """
        if not name or not name.strip():
            raise ValueError("subreddit name is required")

        name = name.strip().lower().lstrip("r/")

        response = await self.get(f"/r/{name}/about/rules")
        rules: list[dict[str, Any]] = response.get("rules", [])
        return rules

    # =========================================================================
    # Post Methods
    # =========================================================================

    async def get_subreddit_posts(
        self,
        subreddit: str,
        *,
        sort: RedditSortType | str = RedditSortType.HOT,
        time_filter: RedditTimeFilter | str = RedditTimeFilter.DAY,
        limit: int = 25,
        after: str | None = None,
        before: str | None = None,
    ) -> list[RedditPost]:
        """
        Get posts from a subreddit.

        Args:
            subreddit: Subreddit name (without r/ prefix)
            sort: Sort type (hot, new, top, rising, controversial)
            time_filter: Time filter for top/controversial (hour, day, week, month, year, all)
            limit: Maximum results to return (1-100, default 25)
            after: Fullname of item to fetch after (pagination)
            before: Fullname of item to fetch before (pagination)

        Returns:
            List of posts.

        Raises:
            RedditError: If request fails.
        """
        if not subreddit or not subreddit.strip():
            raise ValueError("subreddit is required")

        subreddit = subreddit.strip().lower().lstrip("r/")
        sort_value = sort.value if isinstance(sort, RedditSortType) else sort
        time_value = time_filter.value if isinstance(time_filter, RedditTimeFilter) else time_filter

        params: dict[str, Any] = {
            "limit": min(max(1, limit), 100),
        }

        # Time filter only applies to top and controversial
        if sort_value in ("top", "controversial"):
            params["t"] = time_value

        if after:
            params["after"] = after
        if before:
            params["before"] = before

        response = await self.get(f"/r/{subreddit}/{sort_value}", params=params)
        children = response.get("data", {}).get("children", [])

        return [self._parse_post(child.get("data", {})) for child in children]

    async def get_post(self, post_id: str, subreddit: str | None = None) -> RedditPost:
        """
        Get a specific post by ID.

        Args:
            post_id: Post ID (with or without t3_ prefix)
            subreddit: Optional subreddit name (for faster lookup)

        Returns:
            RedditPost with post details.

        Raises:
            RedditError: If request fails.
        """
        if not post_id or not post_id.strip():
            raise ValueError("post_id is required")

        # Remove t3_ prefix if present
        post_id = post_id.strip().lstrip("t3_")

        if subreddit:
            subreddit = subreddit.strip().lower().lstrip("r/")
            endpoint = f"/r/{subreddit}/comments/{post_id}"
        else:
            endpoint = f"/comments/{post_id}"

        response: Any = await self.get(endpoint)

        # Reddit returns an array with [post_listing, comments_listing]
        if isinstance(response, list) and len(response) > 0:
            post_data = response[0].get("data", {}).get("children", [{}])[0].get("data", {})
            return self._parse_post(post_data)

        raise RedditError(
            message=f"[{self.name}] Post not found: {post_id}",
            status_code=404,
        )

    async def search_posts(
        self,
        query: str,
        *,
        subreddit: str | None = None,
        sort: str = "relevance",
        time_filter: RedditTimeFilter | str = RedditTimeFilter.ALL,
        limit: int = 25,
        after: str | None = None,
    ) -> RedditSearchResult:
        """
        Search for posts across Reddit or within a subreddit.

        Args:
            query: Search query
            subreddit: Optional subreddit to search within
            sort: Sort order (relevance, hot, top, new, comments)
            time_filter: Time filter (hour, day, week, month, year, all)
            limit: Maximum results to return (1-100, default 25)
            after: Fullname for pagination

        Returns:
            RedditSearchResult with matching posts.

        Raises:
            RedditError: If request fails.
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        time_value = time_filter.value if isinstance(time_filter, RedditTimeFilter) else time_filter

        params: dict[str, Any] = {
            "q": query.strip(),
            "sort": sort,
            "t": time_value,
            "limit": min(max(1, limit), 100),
            "type": "link",  # Posts only
        }

        if after:
            params["after"] = after

        if subreddit:
            subreddit = subreddit.strip().lower().lstrip("r/")
            endpoint = f"/r/{subreddit}/search"
            params["restrict_sr"] = "true"
        else:
            endpoint = "/search"

        response = await self.get(endpoint, params=params)
        data = response.get("data", {})

        posts = [self._parse_post(child.get("data", {})) for child in data.get("children", [])]

        return RedditSearchResult(
            posts=posts,
            after=data.get("after"),
            before=data.get("before"),
            count=len(posts),
            raw=response,
        )

    # =========================================================================
    # Comment Methods
    # =========================================================================

    async def get_post_comments(
        self,
        post_id: str,
        subreddit: str | None = None,
        *,
        sort: str = "best",
        limit: int = 100,
        depth: int | None = None,
    ) -> list[RedditComment]:
        """
        Get comments for a post.

        Args:
            post_id: Post ID (with or without t3_ prefix)
            subreddit: Optional subreddit name (for faster lookup)
            sort: Comment sort (best, top, new, controversial, old, qa)
            limit: Maximum comments to return (default 100)
            depth: Maximum comment depth to return

        Returns:
            List of comments (flattened tree).

        Raises:
            RedditError: If request fails.
        """
        if not post_id or not post_id.strip():
            raise ValueError("post_id is required")

        post_id = post_id.strip().lstrip("t3_")

        params: dict[str, Any] = {
            "sort": sort,
            "limit": limit,
        }

        if depth is not None:
            params["depth"] = depth

        if subreddit:
            subreddit = subreddit.strip().lower().lstrip("r/")
            endpoint = f"/r/{subreddit}/comments/{post_id}"
        else:
            endpoint = f"/comments/{post_id}"

        response: Any = await self.get(endpoint, params=params)

        # Reddit returns [post_listing, comments_listing]
        if isinstance(response, list) and len(response) > 1:
            comments_data = response[1].get("data", {}).get("children", [])
            return self._flatten_comments(comments_data, post_id)

        return []

    def _flatten_comments(
        self,
        children: list[dict[str, Any]],
        post_id: str,
        depth: int = 0,
    ) -> list[RedditComment]:
        """
        Flatten nested comment tree into a list.

        Args:
            children: List of comment children from API
            post_id: Parent post ID
            depth: Current nesting depth

        Returns:
            Flattened list of comments.
        """
        comments: list[RedditComment] = []

        for child in children:
            if child.get("kind") != "t1":  # t1 = comment
                continue

            data = child.get("data", {})
            comment = self._parse_comment(data, post_id, depth)
            comments.append(comment)

            # Recursively flatten replies
            replies = data.get("replies")
            if isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                comments.extend(self._flatten_comments(reply_children, post_id, depth + 1))

        return comments

    # =========================================================================
    # User Methods
    # =========================================================================

    async def get_user(self, username: str) -> RedditUser:
        """
        Get information about a Reddit user.

        Args:
            username: Reddit username (without u/ prefix)

        Returns:
            RedditUser with user details.

        Raises:
            RedditError: If request fails.
        """
        if not username or not username.strip():
            raise ValueError("username is required")

        # Remove u/ or /u/ prefix
        username = username.strip()
        if username.startswith("/u/"):
            username = username[3:]
        elif username.startswith("u/"):
            username = username[2:]

        response = await self.get(f"/user/{username}/about")
        data = response.get("data", {})

        return self._parse_user(data)

    async def get_user_posts(
        self,
        username: str,
        *,
        sort: str = "new",
        time_filter: RedditTimeFilter | str = RedditTimeFilter.ALL,
        limit: int = 25,
        after: str | None = None,
    ) -> list[RedditPost]:
        """
        Get posts submitted by a user.

        Args:
            username: Reddit username
            sort: Sort order (hot, new, top, controversial)
            time_filter: Time filter for top/controversial
            limit: Maximum results to return (1-100, default 25)
            after: Fullname for pagination

        Returns:
            List of posts by the user.

        Raises:
            RedditError: If request fails.
        """
        if not username or not username.strip():
            raise ValueError("username is required")

        # Remove u/ or /u/ prefix
        username = username.strip()
        if username.startswith("/u/"):
            username = username[3:]
        elif username.startswith("u/"):
            username = username[2:]
        time_value = time_filter.value if isinstance(time_filter, RedditTimeFilter) else time_filter

        params: dict[str, Any] = {
            "sort": sort,
            "t": time_value,
            "limit": min(max(1, limit), 100),
        }

        if after:
            params["after"] = after

        response = await self.get(f"/user/{username}/submitted", params=params)
        children = response.get("data", {}).get("children", [])

        return [
            self._parse_post(child.get("data", {}))
            for child in children
            if child.get("kind") == "t3"  # t3 = post/link
        ]

    async def get_user_comments(
        self,
        username: str,
        *,
        sort: str = "new",
        time_filter: RedditTimeFilter | str = RedditTimeFilter.ALL,
        limit: int = 25,
        after: str | None = None,
    ) -> list[RedditComment]:
        """
        Get comments by a user.

        Args:
            username: Reddit username
            sort: Sort order (hot, new, top, controversial)
            time_filter: Time filter for top/controversial
            limit: Maximum results to return (1-100, default 25)
            after: Fullname for pagination

        Returns:
            List of comments by the user.

        Raises:
            RedditError: If request fails.
        """
        if not username or not username.strip():
            raise ValueError("username is required")

        # Remove u/ or /u/ prefix
        username = username.strip()
        if username.startswith("/u/"):
            username = username[3:]
        elif username.startswith("u/"):
            username = username[2:]
        time_value = time_filter.value if isinstance(time_filter, RedditTimeFilter) else time_filter

        params: dict[str, Any] = {
            "sort": sort,
            "t": time_value,
            "limit": min(max(1, limit), 100),
        }

        if after:
            params["after"] = after

        response = await self.get(f"/user/{username}/comments", params=params)
        children = response.get("data", {}).get("children", [])

        return [
            self._parse_comment(child.get("data", {}), "", 0)
            for child in children
            if child.get("kind") == "t1"  # t1 = comment
        ]

    # =========================================================================
    # Analysis Methods
    # =========================================================================

    async def analyze_subreddit(
        self,
        name: str,
        *,
        post_limit: int = 50,
        time_filter: RedditTimeFilter | str = RedditTimeFilter.WEEK,
    ) -> SubredditAnalysis:
        """
        Analyze a subreddit for niche research and pain points.

        Retrieves subreddit info, top posts, and extracts common topics
        and potential pain points from post titles and content.

        Args:
            name: Subreddit name (without r/ prefix)
            post_limit: Number of posts to analyze (default 50)
            time_filter: Time filter for top posts (default week)

        Returns:
            SubredditAnalysis with research insights.

        Raises:
            RedditError: If request fails.
        """
        # Get subreddit info and top posts in parallel-ish manner
        subreddit = await self.get_subreddit(name)
        posts = await self.get_subreddit_posts(
            name,
            sort=RedditSortType.TOP,
            time_filter=time_filter,
            limit=post_limit,
        )

        # Calculate engagement metrics
        if posts:
            total_score = sum(p.score for p in posts)
            total_comments = sum(p.num_comments for p in posts)
            avg_score = total_score / len(posts)
            avg_comments = total_comments / len(posts)
            avg_upvote_ratio = sum(p.upvote_ratio for p in posts) / len(posts)
        else:
            avg_score = 0.0
            avg_comments = 0.0
            avg_upvote_ratio = 0.0

        engagement_metrics = {
            "avg_post_score": avg_score,
            "avg_comments_per_post": avg_comments,
            "avg_upvote_ratio": avg_upvote_ratio,
            "total_posts_analyzed": len(posts),
            "subscribers": subreddit.subscribers,
            "active_users": subreddit.active_users,
        }

        # Extract common topics from titles (simple word frequency)
        # This is a basic implementation - can be enhanced with NLP
        word_counts: dict[str, int] = {}
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "up",
            "about",
            "into",
            "over",
            "after",
            "beneath",
            "under",
            "above",
            "and",
            "but",
            "or",
            "nor",
            "so",
            "yet",
            "both",
            "either",
            "neither",
            "not",
            "only",
            "own",
            "same",
            "than",
            "too",
            "very",
            "just",
            "i",
            "me",
            "my",
            "myself",
            "we",
            "our",
            "ours",
            "you",
            "your",
            "he",
            "him",
            "his",
            "she",
            "her",
            "it",
            "its",
            "they",
            "them",
            "what",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "am",
            "as",
            "if",
            "how",
            "when",
            "where",
            "why",
            "all",
            "each",
            "any",
            "some",
            "no",
            "there",
            "here",
        }

        for post in posts:
            words = post.title.lower().split()
            for word in words:
                # Clean word of punctuation
                clean_word = "".join(c for c in word if c.isalnum())
                if clean_word and len(clean_word) > 2 and clean_word not in stop_words:
                    word_counts[clean_word] = word_counts.get(clean_word, 0) + 1

        # Get top 20 most common words as topics
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        common_topics = [word for word, _ in sorted_words[:20]]

        # Extract pain points (posts with question marks or negative sentiment indicators)
        pain_indicators = [
            "help",
            "problem",
            "issue",
            "stuck",
            "can't",
            "won't",
            "error",
            "failed",
            "failing",
            "struggling",
            "frustrated",
            "advice",
            "how do",
            "how to",
            "why does",
            "why is",
            "what's wrong",
        ]
        pain_points: list[str] = []

        for post in posts:
            title_lower = post.title.lower()
            if "?" in post.title or any(ind in title_lower for ind in pain_indicators):
                pain_points.append(post.title)

        return SubredditAnalysis(
            subreddit=subreddit,
            top_posts=posts,
            common_topics=common_topics,
            engagement_metrics=engagement_metrics,
            pain_points=pain_points[:20],  # Limit to top 20 pain points
            raw={},
        )

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check Reddit API health and connectivity.

        Attempts to authenticate and fetch basic data.

        Returns:
            Dictionary with health status.
        """
        try:
            # Try to get access token
            await self._ensure_access_token()

            # Try to fetch a popular subreddit
            await self.get_subreddit("python")

            return {
                "name": self.name,
                "healthy": True,
                "auth_url": self.AUTH_URL,
                "api_url": self.API_BASE_URL,
            }
        except Exception as e:
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
                "auth_url": self.AUTH_URL,
                "api_url": self.API_BASE_URL,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Reddit API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/r/python/about")
            method: HTTP method (default GET)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary.

        Raises:
            RedditError: If request fails.
        """
        return await self._request_with_retry(method, endpoint, **kwargs)

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def _parse_subreddit(self, data: dict[str, Any]) -> RedditSubreddit:
        """Parse subreddit data from API response."""
        return RedditSubreddit(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            public_description=data.get("public_description", ""),
            subscribers=data.get("subscribers", 0),
            active_users=data.get("accounts_active", 0) or data.get("active_user_count", 0),
            created_utc=data.get("created_utc", 0),
            over18=data.get("over18", False),
            subreddit_type=data.get("subreddit_type", "public"),
            url=data.get("url", ""),
            icon_url=data.get("icon_img") or data.get("community_icon"),
            banner_url=data.get("banner_img") or data.get("banner_background_image"),
            raw=data,
        )

    def _parse_post(self, data: dict[str, Any]) -> RedditPost:
        """Parse post data from API response."""
        # Extract preview URL if available
        preview_url = None
        preview = data.get("preview", {})
        if preview:
            images = preview.get("images", [])
            if images:
                preview_url = images[0].get("source", {}).get("url")

        return RedditPost(
            id=data.get("id", ""),
            subreddit=data.get("subreddit", ""),
            title=data.get("title", ""),
            selftext=data.get("selftext", ""),
            author=data.get("author", "[deleted]"),
            score=data.get("score", 0),
            upvote_ratio=data.get("upvote_ratio", 0.0),
            num_comments=data.get("num_comments", 0),
            created_utc=data.get("created_utc", 0),
            url=data.get("url", ""),
            permalink=f"https://reddit.com{data.get('permalink', '')}",
            is_self=data.get("is_self", False),
            is_video=data.get("is_video", False),
            over_18=data.get("over_18", False),
            spoiler=data.get("spoiler", False),
            stickied=data.get("stickied", False),
            locked=data.get("locked", False),
            distinguished=data.get("distinguished"),
            link_flair_text=data.get("link_flair_text"),
            author_flair_text=data.get("author_flair_text"),
            thumbnail=data.get("thumbnail"),
            preview_url=preview_url,
            awards_count=len(data.get("all_awardings", [])),
            total_awards_received=data.get("total_awards_received", 0),
            raw=data,
        )

    def _parse_comment(
        self,
        data: dict[str, Any],
        post_id: str,
        depth: int,
    ) -> RedditComment:
        """Parse comment data from API response."""
        # Count replies
        replies_count = 0
        replies = data.get("replies")
        if isinstance(replies, dict):
            replies_count = len(replies.get("data", {}).get("children", []))

        return RedditComment(
            id=data.get("id", ""),
            post_id=post_id or data.get("link_id", "").lstrip("t3_"),
            subreddit=data.get("subreddit", ""),
            body=data.get("body", ""),
            author=data.get("author", "[deleted]"),
            score=data.get("score", 0),
            created_utc=data.get("created_utc", 0),
            permalink=f"https://reddit.com{data.get('permalink', '')}",
            is_submitter=data.get("is_submitter", False),
            stickied=data.get("stickied", False),
            distinguished=data.get("distinguished"),
            parent_id=data.get("parent_id"),
            depth=depth,
            awards_count=len(data.get("all_awardings", [])),
            replies_count=replies_count,
            raw=data,
        )

    def _parse_user(self, data: dict[str, Any]) -> RedditUser:
        """Parse user data from API response."""
        return RedditUser(
            id=data.get("id", ""),
            name=data.get("name", ""),
            created_utc=data.get("created_utc", 0),
            link_karma=data.get("link_karma", 0),
            comment_karma=data.get("comment_karma", 0),
            total_karma=data.get("total_karma", 0),
            is_gold=data.get("is_gold", False),
            is_mod=data.get("is_mod", False),
            has_verified_email=data.get("has_verified_email", False),
            icon_url=data.get("icon_img"),
            subreddit_name=data.get("subreddit", {}).get("display_name_prefixed"),
            raw=data,
        )
