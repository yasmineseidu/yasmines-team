"""Unit tests for Reddit API integration client."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.reddit import (
    RedditAuthError,
    RedditClient,
    RedditComment,
    RedditError,
    RedditPost,
    RedditRateLimitError,
    RedditSearchResult,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
    RedditUser,
    SubredditAnalysis,
)


class TestRedditClientInitialization:
    """Tests for RedditClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have name 'reddit'."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert client.name == "reddit"

    def test_has_correct_base_url(self) -> None:
        """Client should use oauth.reddit.com as base URL."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert client.base_url == "https://oauth.reddit.com"

    def test_stores_client_credentials(self) -> None:
        """Client should store client ID and secret."""
        client = RedditClient(
            client_id="my-client-id",  # pragma: allowlist secret
            client_secret="my-client-secret",  # pragma: allowlist secret
        )
        assert client.client_id == "my-client-id"  # pragma: allowlist secret
        assert client.client_secret == "my-client-secret"  # pragma: allowlist secret

    def test_default_user_agent(self) -> None:
        """Client should have default user agent."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert "smarter-team" in client.user_agent

    def test_custom_user_agent(self) -> None:
        """Client should accept custom user agent."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
            user_agent="myapp/2.0",
        )
        assert client.user_agent == "myapp/2.0"

    def test_default_timeout(self) -> None:
        """Client should have 30s default timeout."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
            timeout=60.0,
        )
        assert client.timeout == 60.0

    def test_default_max_retries(self) -> None:
        """Client should have 3 default max retries."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert client.max_retries == 3

    def test_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
            max_retries=5,
        )
        assert client.max_retries == 5

    def test_token_starts_as_none(self) -> None:
        """Client should start without access token."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        assert client._access_token is None
        assert client._token_expires_at == 0


class TestRedditClientHeaders:
    """Tests for RedditClient header generation."""

    def test_get_headers_includes_user_agent(self) -> None:
        """Headers should include User-Agent."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
            user_agent="myapp/1.0",
        )
        headers = client._get_headers()
        assert headers["User-Agent"] == "myapp/1.0"

    def test_get_headers_includes_accept(self) -> None:
        """Headers should include Accept: application/json."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestRedditClientAuthentication:
    """Tests for RedditClient OAuth2 authentication."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        return RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )

    @pytest.fixture
    def mock_token_response(self) -> dict:
        """Sample token response from Reddit."""
        return {
            "access_token": "mock-access-token",  # pragma: allowlist secret
            "token_type": "bearer",
            "expires_in": 3600,
            "scope": "read",
        }

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self, client: RedditClient, mock_token_response: dict
    ) -> None:
        """Should successfully refresh access token."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.content = b"{}"

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.is_closed = False
        client._client = mock_http_client

        await client._refresh_access_token()

        assert client._access_token == "mock-access-token"  # pragma: allowlist secret
        assert client._token_expires_at > time.time()

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, client: RedditClient) -> None:
        """Should raise RedditAuthError on token refresh failure."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.content = b'{"error": "invalid_grant"}'

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.is_closed = False
        client._client = mock_http_client

        with pytest.raises(RedditAuthError):
            await client._refresh_access_token()

    @pytest.mark.asyncio
    async def test_ensure_access_token_refreshes_when_expired(
        self, client: RedditClient, mock_token_response: dict
    ) -> None:
        """Should refresh token when expired."""
        # Set expired token
        client._access_token = "old-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() - 100  # Expired

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.content = b"{}"

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.is_closed = False
        client._client = mock_http_client

        token = await client._ensure_access_token()

        assert token == "mock-access-token"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_ensure_access_token_uses_cached_when_valid(self, client: RedditClient) -> None:
        """Should use cached token when still valid."""
        client._access_token = "cached-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600  # Valid for 1 hour

        token = await client._ensure_access_token()

        assert token == "cached-token"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_auth_headers_includes_bearer_token(self, client: RedditClient) -> None:
        """Auth headers should include Bearer token."""
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600

        headers = await client._get_auth_headers()

        assert headers["Authorization"] == "Bearer test-token"  # pragma: allowlist secret
        assert headers["User-Agent"] == client.user_agent


class TestRedditClientSubredditMethods:
    """Tests for RedditClient subreddit methods."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        # Pre-set valid token to avoid auth calls
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.fixture
    def mock_subreddit_response(self) -> dict:
        """Sample subreddit about response."""
        return {
            "kind": "t5",
            "data": {
                "name": "t5_2qh1i",
                "display_name": "Python",
                "title": "Python - The programming language",
                "description": "News about the Python programming language.",
                "public_description": "News about Python.",
                "subscribers": 1500000,
                "accounts_active": 5000,
                "created_utc": 1219339935.0,
                "over18": False,
                "subreddit_type": "public",
                "url": "/r/Python/",
                "icon_img": "https://example.com/icon.png",
                "banner_img": "https://example.com/banner.png",
            },
        }

    @pytest.mark.asyncio
    async def test_get_subreddit_success(
        self, client: RedditClient, mock_subreddit_response: dict
    ) -> None:
        """Should return parsed subreddit data."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_subreddit_response

            result = await client.get_subreddit("python")

            assert isinstance(result, RedditSubreddit)
            assert result.display_name == "Python"
            assert result.subscribers == 1500000
            mock.assert_called_once_with("/r/python/about")

    @pytest.mark.asyncio
    async def test_get_subreddit_strips_prefix(
        self, client: RedditClient, mock_subreddit_response: dict
    ) -> None:
        """Should strip r/ prefix from subreddit name."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_subreddit_response

            await client.get_subreddit("r/Python")

            mock.assert_called_once_with("/r/python/about")

    @pytest.mark.asyncio
    async def test_get_subreddit_empty_name_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty subreddit name."""
        with pytest.raises(ValueError, match="subreddit name is required"):
            await client.get_subreddit("")

    @pytest.mark.asyncio
    async def test_search_subreddits_success(self, client: RedditClient) -> None:
        """Should return list of matching subreddits."""
        mock_response = {
            "data": {
                "children": [
                    {"data": {"display_name": "Python", "subscribers": 1500000}},
                    {"data": {"display_name": "learnpython", "subscribers": 750000}},
                ]
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response

            results = await client.search_subreddits("python", limit=10)

            assert len(results) == 2
            assert all(isinstance(r, RedditSubreddit) for r in results)
            assert results[0].display_name == "Python"

    @pytest.mark.asyncio
    async def test_search_subreddits_empty_query_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search_subreddits("")


class TestRedditClientPostMethods:
    """Tests for RedditClient post methods."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.fixture
    def mock_posts_response(self) -> dict:
        """Sample posts listing response."""
        return {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "abc123",
                            "subreddit": "Python",
                            "title": "What's new in Python 3.12?",
                            "selftext": "Let's discuss the new features.",
                            "author": "pythonista",
                            "score": 500,
                            "upvote_ratio": 0.95,
                            "num_comments": 150,
                            "created_utc": 1700000000.0,
                            "url": "https://example.com",
                            "permalink": "/r/Python/comments/abc123/",
                            "is_self": True,
                            "is_video": False,
                            "over_18": False,
                            "spoiler": False,
                            "stickied": False,
                            "locked": False,
                        },
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "def456",
                            "subreddit": "Python",
                            "title": "How to use async/await?",
                            "selftext": "",
                            "author": "newbie",
                            "score": 100,
                            "upvote_ratio": 0.88,
                            "num_comments": 42,
                            "created_utc": 1699999000.0,
                            "url": "https://example.com/2",
                            "permalink": "/r/Python/comments/def456/",
                            "is_self": True,
                            "is_video": False,
                            "over_18": False,
                            "spoiler": False,
                            "stickied": False,
                            "locked": False,
                        },
                    },
                ],
                "after": "t3_def456",
                "before": None,
            }
        }

    @pytest.mark.asyncio
    async def test_get_subreddit_posts_success(
        self, client: RedditClient, mock_posts_response: dict
    ) -> None:
        """Should return list of posts."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_posts_response

            posts = await client.get_subreddit_posts("python", limit=25)

            assert len(posts) == 2
            assert all(isinstance(p, RedditPost) for p in posts)
            assert posts[0].id == "abc123"
            assert posts[0].title == "What's new in Python 3.12?"
            assert posts[0].score == 500

    @pytest.mark.asyncio
    async def test_get_subreddit_posts_with_sort(
        self, client: RedditClient, mock_posts_response: dict
    ) -> None:
        """Should use specified sort type."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_posts_response

            await client.get_subreddit_posts(
                "python",
                sort=RedditSortType.TOP,
                time_filter=RedditTimeFilter.WEEK,
            )

            call_args = mock.call_args
            assert "/python/top" in call_args[0][0]
            assert call_args[1]["params"]["t"] == "week"

    @pytest.mark.asyncio
    async def test_get_subreddit_posts_empty_subreddit_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty subreddit."""
        with pytest.raises(ValueError, match="subreddit is required"):
            await client.get_subreddit_posts("")

    @pytest.mark.asyncio
    async def test_search_posts_success(self, client: RedditClient) -> None:
        """Should return search results."""
        mock_response = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "search1",
                            "subreddit": "Python",
                            "title": "Python async tutorial",
                            "selftext": "",
                            "author": "user1",
                            "score": 200,
                            "upvote_ratio": 0.92,
                            "num_comments": 30,
                            "created_utc": 1700000000.0,
                            "url": "https://example.com",
                            "permalink": "/r/Python/comments/search1/",
                            "is_self": True,
                            "is_video": False,
                            "over_18": False,
                            "spoiler": False,
                            "stickied": False,
                            "locked": False,
                        },
                    },
                ],
                "after": "t3_search1",
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response

            result = await client.search_posts("async tutorial", subreddit="python")

            assert isinstance(result, RedditSearchResult)
            assert len(result.posts) == 1
            assert result.posts[0].title == "Python async tutorial"
            assert result.after == "t3_search1"

    @pytest.mark.asyncio
    async def test_search_posts_empty_query_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search_posts("")


class TestRedditClientCommentMethods:
    """Tests for RedditClient comment methods."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.fixture
    def mock_comments_response(self) -> list:
        """Sample comments response (post + comments)."""
        return [
            {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {"id": "abc123", "title": "Test Post"},
                        }
                    ]
                }
            },
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment1",
                                "body": "Great post!",
                                "author": "user1",
                                "score": 50,
                                "created_utc": 1700000000.0,
                                "permalink": "/r/test/comments/abc123/test/comment1/",
                                "is_submitter": False,
                                "stickied": False,
                                "subreddit": "test",
                                "parent_id": "t3_abc123",
                                "replies": {
                                    "data": {
                                        "children": [
                                            {
                                                "kind": "t1",
                                                "data": {
                                                    "id": "reply1",
                                                    "body": "Thanks!",
                                                    "author": "user2",
                                                    "score": 10,
                                                    "created_utc": 1700001000.0,
                                                    "permalink": "/r/test/comments/abc123/test/reply1/",
                                                    "is_submitter": True,
                                                    "stickied": False,
                                                    "subreddit": "test",
                                                    "parent_id": "t1_comment1",
                                                    "replies": "",
                                                },
                                            }
                                        ]
                                    }
                                },
                            },
                        },
                    ]
                }
            },
        ]

    @pytest.mark.asyncio
    async def test_get_post_comments_success(
        self, client: RedditClient, mock_comments_response: list
    ) -> None:
        """Should return flattened list of comments."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_comments_response

            comments = await client.get_post_comments("abc123", subreddit="test")

            assert len(comments) == 2  # Parent + 1 reply
            assert all(isinstance(c, RedditComment) for c in comments)
            assert comments[0].body == "Great post!"
            assert comments[0].depth == 0
            assert comments[1].body == "Thanks!"
            assert comments[1].depth == 1

    @pytest.mark.asyncio
    async def test_get_post_comments_empty_post_id_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty post ID."""
        with pytest.raises(ValueError, match="post_id is required"):
            await client.get_post_comments("")


class TestRedditClientUserMethods:
    """Tests for RedditClient user methods."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.fixture
    def mock_user_response(self) -> dict:
        """Sample user about response."""
        return {
            "data": {
                "id": "user123",
                "name": "pythonista",
                "created_utc": 1500000000.0,
                "link_karma": 10000,
                "comment_karma": 25000,
                "total_karma": 35000,
                "is_gold": True,
                "is_mod": False,
                "has_verified_email": True,
                "icon_img": "https://example.com/avatar.png",
                "subreddit": {"display_name_prefixed": "u/pythonista"},
            }
        }

    @pytest.mark.asyncio
    async def test_get_user_success(self, client: RedditClient, mock_user_response: dict) -> None:
        """Should return parsed user data."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_user_response

            user = await client.get_user("pythonista")

            assert isinstance(user, RedditUser)
            assert user.name == "pythonista"
            assert user.total_karma == 35000
            assert user.is_gold is True

    @pytest.mark.asyncio
    async def test_get_user_strips_prefix(
        self, client: RedditClient, mock_user_response: dict
    ) -> None:
        """Should strip u/ prefix from username."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = mock_user_response

            await client.get_user("u/pythonista")

            mock.assert_called_once_with("/user/pythonista/about")

    @pytest.mark.asyncio
    async def test_get_user_empty_username_raises(self, client: RedditClient) -> None:
        """Should raise ValueError for empty username."""
        with pytest.raises(ValueError, match="username is required"):
            await client.get_user("")


class TestRedditClientAnalysis:
    """Tests for RedditClient analysis methods."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.mark.asyncio
    async def test_analyze_subreddit_success(self, client: RedditClient) -> None:
        """Should return comprehensive subreddit analysis."""
        mock_subreddit = {
            "data": {
                "display_name": "entrepreneur",
                "subscribers": 2000000,
                "accounts_active": 10000,
            }
        }

        mock_posts = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "post1",
                            "subreddit": "entrepreneur",
                            "title": "How do I find my first customer?",
                            "selftext": "",
                            "author": "user1",
                            "score": 500,
                            "upvote_ratio": 0.95,
                            "num_comments": 100,
                            "created_utc": 1700000000.0,
                            "url": "https://example.com",
                            "permalink": "/r/entrepreneur/comments/post1/",
                            "is_self": True,
                            "is_video": False,
                            "over_18": False,
                            "spoiler": False,
                            "stickied": False,
                            "locked": False,
                        },
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "post2",
                            "subreddit": "entrepreneur",
                            "title": "I'm struggling with marketing. Help!",
                            "selftext": "",
                            "author": "user2",
                            "score": 300,
                            "upvote_ratio": 0.90,
                            "num_comments": 50,
                            "created_utc": 1699999000.0,
                            "url": "https://example.com/2",
                            "permalink": "/r/entrepreneur/comments/post2/",
                            "is_self": True,
                            "is_video": False,
                            "over_18": False,
                            "spoiler": False,
                            "stickied": False,
                            "locked": False,
                        },
                    },
                ]
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            # First call: get_subreddit, Second call: get_subreddit_posts
            mock.side_effect = [mock_subreddit, mock_posts]

            analysis = await client.analyze_subreddit("entrepreneur", post_limit=10)

            assert isinstance(analysis, SubredditAnalysis)
            assert analysis.subreddit.display_name == "entrepreneur"
            assert len(analysis.top_posts) == 2
            assert analysis.engagement_metrics["avg_post_score"] == 400.0
            assert len(analysis.pain_points) > 0
            # Both titles contain pain indicators (? or "struggling", "help")
            assert any("struggling" in p.lower() for p in analysis.pain_points)


class TestRedditClientHealthCheck:
    """Tests for RedditClient health check."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        return RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: RedditClient) -> None:
        """Should return healthy status when API is accessible."""
        mock_token_response = {
            "access_token": "test-token",  # pragma: allowlist secret
            "expires_in": 3600,
        }
        mock_subreddit_response = {"data": {"display_name": "python"}}

        # Set up mock HTTP client
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.content = b"{}"

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.is_closed = False
        client._client = mock_http_client

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_subreddit_response

            result = await client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "reddit"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: RedditClient) -> None:
        """Should return unhealthy status when API fails."""
        with patch.object(client, "_ensure_access_token", new_callable=AsyncMock) as mock:
            mock.side_effect = RedditAuthError("Auth failed")

            result = await client.health_check()

            assert result["healthy"] is False
            assert "error" in result


class TestRedditClientCallEndpoint:
    """Tests for RedditClient.call_endpoint method."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: RedditClient) -> None:
        """Should call arbitrary endpoint and return response."""
        mock_response = {"data": {"some_field": "some_value"}}

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response

            result = await client.call_endpoint("/r/python/about")

            assert result == mock_response
            mock.assert_called_once_with("GET", "/r/python/about")

    @pytest.mark.asyncio
    async def test_call_endpoint_with_method(self, client: RedditClient) -> None:
        """Should use specified HTTP method."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            await client.call_endpoint("/api/vote", method="POST", json={"dir": 1})

            mock.assert_called_once_with("POST", "/api/vote", json={"dir": 1})


class TestRedditEnums:
    """Tests for Reddit enums."""

    def test_sort_type_values(self) -> None:
        """Sort type enum should have correct values."""
        assert RedditSortType.HOT.value == "hot"
        assert RedditSortType.NEW.value == "new"
        assert RedditSortType.TOP.value == "top"
        assert RedditSortType.RISING.value == "rising"
        assert RedditSortType.CONTROVERSIAL.value == "controversial"

    def test_time_filter_values(self) -> None:
        """Time filter enum should have correct values."""
        assert RedditTimeFilter.HOUR.value == "hour"
        assert RedditTimeFilter.DAY.value == "day"
        assert RedditTimeFilter.WEEK.value == "week"
        assert RedditTimeFilter.MONTH.value == "month"
        assert RedditTimeFilter.YEAR.value == "year"
        assert RedditTimeFilter.ALL.value == "all"


class TestRedditDataclasses:
    """Tests for Reddit dataclasses."""

    def test_reddit_subreddit_creation(self) -> None:
        """Should create RedditSubreddit with required fields."""
        sub = RedditSubreddit(
            name="t5_test",
            display_name="test",
            title="Test Subreddit",
            description="A test subreddit",
            public_description="Public test",
            subscribers=1000,
            active_users=50,
            created_utc=1700000000.0,
            over18=False,
            subreddit_type="public",
            url="/r/test/",
        )
        assert sub.display_name == "test"
        assert sub.subscribers == 1000

    def test_reddit_post_creation(self) -> None:
        """Should create RedditPost with required fields."""
        post = RedditPost(
            id="abc123",
            subreddit="test",
            title="Test Post",
            selftext="Content",
            author="user",
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            created_utc=1700000000.0,
            url="https://example.com",
            permalink="https://reddit.com/r/test/comments/abc123/",
            is_self=True,
            is_video=False,
            over_18=False,
            spoiler=False,
            stickied=False,
            locked=False,
        )
        assert post.id == "abc123"
        assert post.score == 100

    def test_reddit_comment_creation(self) -> None:
        """Should create RedditComment with required fields."""
        comment = RedditComment(
            id="xyz789",
            post_id="abc123",
            subreddit="test",
            body="Great post!",
            author="commenter",
            score=25,
            created_utc=1700000000.0,
            permalink="https://reddit.com/r/test/comments/abc123/test/xyz789/",
            is_submitter=False,
            stickied=False,
        )
        assert comment.id == "xyz789"
        assert comment.body == "Great post!"

    def test_reddit_user_creation(self) -> None:
        """Should create RedditUser with required fields."""
        user = RedditUser(
            id="user123",
            name="testuser",
            created_utc=1600000000.0,
            link_karma=1000,
            comment_karma=5000,
            total_karma=6000,
            is_gold=False,
            is_mod=True,
            has_verified_email=True,
        )
        assert user.name == "testuser"
        assert user.total_karma == 6000


class TestRedditClientErrorHandling:
    """Tests for RedditClient error handling."""

    @pytest.fixture
    def client(self) -> RedditClient:
        """Create RedditClient instance for testing."""
        client = RedditClient(
            client_id="test-id",  # pragma: allowlist secret
            client_secret="test-secret",  # pragma: allowlist secret
        )
        client._access_token = "test-token"  # pragma: allowlist secret
        client._token_expires_at = time.time() + 3600
        return client

    @pytest.mark.asyncio
    async def test_handle_response_401_raises_auth_error(self, client: RedditClient) -> None:
        """Should raise RedditAuthError for 401 response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "unauthorized"}

        with pytest.raises(RedditAuthError):
            await client._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_403_raises_auth_error(self, client: RedditClient) -> None:
        """Should raise RedditAuthError for 403 response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "forbidden"}

        with pytest.raises(RedditAuthError):
            await client._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_429_raises_rate_limit_error(self, client: RedditClient) -> None:
        """Should raise RedditRateLimitError for 429 response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "rate_limited"}
        mock_response.headers = {"Retry-After": "60"}

        with pytest.raises(RedditRateLimitError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_handle_response_500_raises_error(self, client: RedditClient) -> None:
        """Should raise RedditError for 500 response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "internal_error"}

        with pytest.raises(RedditError):
            await client._handle_response(mock_response)
