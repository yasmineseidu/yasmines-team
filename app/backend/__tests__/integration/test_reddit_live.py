"""
Live API tests for Reddit integration.

These tests use REAL API credentials from .env and make actual API calls.
All tests MUST pass 100% before proceeding to review.

To run:
    uv run pytest __tests__/integration/test_reddit_live.py -v -m live_api

Environment variables required:
    - REDDIT_CLIENT_ID
    - REDDIT_CLIENT_SECRET
    - REDDIT_USER_AGENT (optional, has default)
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.reddit import (
    RedditClient,
    RedditComment,
    RedditError,
    RedditPost,
    RedditSearchResult,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
    RedditUser,
    SubredditAnalysis,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


@pytest.fixture
def reddit_credentials() -> dict[str, str]:
    """Get Reddit API credentials from .env."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "smarter-team-test/1.0")

    if not client_id or client_id == "...":
        pytest.skip("REDDIT_CLIENT_ID not configured in .env")
    if not client_secret or client_secret == "...":
        pytest.skip("REDDIT_CLIENT_SECRET not configured in .env")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
    }


@pytest.fixture
async def client(reddit_credentials: dict[str, str]) -> RedditClient:
    """Create authenticated Reddit client."""
    return RedditClient(**reddit_credentials)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveAuthentication:
    """Live tests for Reddit OAuth authentication."""

    async def test_oauth_token_acquisition(self, reddit_credentials: dict[str, str]) -> None:
        """Should successfully acquire OAuth access token."""
        client = RedditClient(**reddit_credentials)

        # Token should start as None
        assert client._access_token is None

        # Force token acquisition
        token = await client._ensure_access_token()

        # Token should be set
        assert token is not None
        assert len(token) > 0
        assert client._token_expires_at > 0

        await client.close()

    async def test_health_check(self, reddit_credentials: dict[str, str]) -> None:
        """Should return healthy status with valid credentials."""
        async with RedditClient(**reddit_credentials) as client:
            result = await client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "reddit"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveSubreddits:
    """Live tests for subreddit endpoints."""

    async def test_get_subreddit_python(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch r/Python subreddit info."""
        async with RedditClient(**reddit_credentials) as client:
            subreddit = await client.get_subreddit("python")

            assert isinstance(subreddit, RedditSubreddit)
            assert subreddit.display_name.lower() == "python"
            assert subreddit.subscribers > 0
            assert subreddit.subreddit_type in ("public", "restricted")

    async def test_get_subreddit_entrepreneur(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch r/Entrepreneur subreddit info."""
        async with RedditClient(**reddit_credentials) as client:
            subreddit = await client.get_subreddit("Entrepreneur")

            assert isinstance(subreddit, RedditSubreddit)
            assert subreddit.display_name.lower() == "entrepreneur"
            assert subreddit.subscribers > 100000  # Popular subreddit

    async def test_search_subreddits(self, reddit_credentials: dict[str, str]) -> None:
        """Should find subreddits matching query."""
        async with RedditClient(**reddit_credentials) as client:
            results = await client.search_subreddits("programming", limit=5)

            assert len(results) > 0
            assert len(results) <= 5
            assert all(isinstance(r, RedditSubreddit) for r in results)

    async def test_get_subreddit_rules(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch subreddit rules."""
        async with RedditClient(**reddit_credentials) as client:
            rules = await client.get_subreddit_rules("python")

            assert isinstance(rules, list)
            # Most subreddits have at least one rule


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLivePosts:
    """Live tests for post endpoints."""

    async def test_get_hot_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch hot posts from subreddit."""
        async with RedditClient(**reddit_credentials) as client:
            posts = await client.get_subreddit_posts(
                "python",
                sort=RedditSortType.HOT,
                limit=10,
            )

            assert len(posts) > 0
            assert len(posts) <= 10
            assert all(isinstance(p, RedditPost) for p in posts)
            assert all(p.subreddit.lower() == "python" for p in posts)

    async def test_get_new_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch new posts from subreddit."""
        async with RedditClient(**reddit_credentials) as client:
            posts = await client.get_subreddit_posts(
                "AskReddit",
                sort=RedditSortType.NEW,
                limit=5,
            )

            assert len(posts) > 0
            assert all(isinstance(p, RedditPost) for p in posts)

    async def test_get_top_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch top posts with time filter."""
        async with RedditClient(**reddit_credentials) as client:
            posts = await client.get_subreddit_posts(
                "technology",
                sort=RedditSortType.TOP,
                time_filter=RedditTimeFilter.WEEK,
                limit=10,
            )

            assert len(posts) > 0
            # Top posts should have high scores
            assert any(p.score > 100 for p in posts)

    async def test_search_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should search for posts across Reddit."""
        async with RedditClient(**reddit_credentials) as client:
            result = await client.search_posts(
                "machine learning",
                sort="relevance",
                limit=10,
            )

            assert isinstance(result, RedditSearchResult)
            assert len(result.posts) > 0
            assert all(isinstance(p, RedditPost) for p in result.posts)

    async def test_search_posts_in_subreddit(self, reddit_credentials: dict[str, str]) -> None:
        """Should search for posts within a subreddit."""
        async with RedditClient(**reddit_credentials) as client:
            result = await client.search_posts(
                "async",
                subreddit="python",
                limit=5,
            )

            assert isinstance(result, RedditSearchResult)
            # All posts should be from r/python
            for post in result.posts:
                assert post.subreddit.lower() == "python"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveComments:
    """Live tests for comment endpoints."""

    async def test_get_post_comments(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch comments for a post."""
        async with RedditClient(**reddit_credentials) as client:
            # First get a hot post from a popular subreddit
            posts = await client.get_subreddit_posts(
                "AskReddit",
                sort=RedditSortType.HOT,
                limit=1,
            )

            if not posts:
                pytest.skip("No posts found")

            post = posts[0]
            comments = await client.get_post_comments(
                post.id,
                subreddit="AskReddit",
                limit=20,
            )

            assert isinstance(comments, list)
            if post.num_comments > 0:
                assert len(comments) > 0
                assert all(isinstance(c, RedditComment) for c in comments)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveUsers:
    """Live tests for user endpoints."""

    async def test_get_user(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch user profile."""
        async with RedditClient(**reddit_credentials) as client:
            # Use a well-known Reddit account
            user = await client.get_user("spez")  # Reddit CEO

            assert isinstance(user, RedditUser)
            assert user.name.lower() == "spez"
            assert user.total_karma > 0

    async def test_get_user_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should fetch user's submitted posts."""
        async with RedditClient(**reddit_credentials) as client:
            posts = await client.get_user_posts("spez", limit=5)

            assert isinstance(posts, list)
            # spez has posts
            if posts:
                assert all(isinstance(p, RedditPost) for p in posts)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveAnalysis:
    """Live tests for analysis methods."""

    async def test_analyze_subreddit(self, reddit_credentials: dict[str, str]) -> None:
        """Should analyze subreddit for pain points and topics."""
        async with RedditClient(**reddit_credentials) as client:
            analysis = await client.analyze_subreddit(
                "Entrepreneur",
                post_limit=20,
                time_filter=RedditTimeFilter.WEEK,
            )

            assert isinstance(analysis, SubredditAnalysis)
            assert analysis.subreddit.display_name.lower() == "entrepreneur"
            assert len(analysis.top_posts) <= 20
            assert "avg_post_score" in analysis.engagement_metrics
            assert "subscribers" in analysis.engagement_metrics
            assert len(analysis.common_topics) > 0


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveCallEndpoint:
    """Live tests for generic endpoint calling."""

    async def test_call_endpoint_subreddit_about(self, reddit_credentials: dict[str, str]) -> None:
        """Should call arbitrary endpoint and return raw response."""
        async with RedditClient(**reddit_credentials) as client:
            result = await client.call_endpoint("/r/python/about")

            assert isinstance(result, dict)
            assert "data" in result or "kind" in result


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveEdgeCases:
    """Live tests for edge cases and error handling."""

    async def test_nonexistent_subreddit(self, reddit_credentials: dict[str, str]) -> None:
        """Should handle nonexistent subreddit gracefully."""
        async with RedditClient(**reddit_credentials) as client:
            # This might raise or return empty - depends on Reddit API
            try:
                result = await client.get_subreddit(
                    "this_subreddit_definitely_does_not_exist_12345xyz"
                )
                # If no error, result might have default values
                assert result is not None
            except RedditError:
                # Expected for nonexistent subreddits
                pass

    async def test_empty_subreddit_posts(self, reddit_credentials: dict[str, str]) -> None:
        """Should handle subreddit with no/few posts."""
        async with RedditClient(**reddit_credentials) as client:
            # Use a very niche subreddit
            posts = await client.get_subreddit_posts(
                "test",  # r/test is a testing subreddit
                limit=5,
            )

            assert isinstance(posts, list)
            # May or may not have posts


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRedditClientLiveRateLimiting:
    """Live tests for rate limit handling."""

    async def test_multiple_requests_no_rate_limit(
        self, reddit_credentials: dict[str, str]
    ) -> None:
        """Should handle multiple requests without hitting rate limit."""
        async with RedditClient(**reddit_credentials) as client:
            # Make several requests in sequence
            subreddits = ["python", "programming", "technology", "datascience"]

            for subreddit in subreddits:
                result = await client.get_subreddit(subreddit)
                assert result.display_name.lower() == subreddit.lower()

            # All requests should complete without rate limit errors
