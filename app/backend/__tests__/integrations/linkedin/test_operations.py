"""Unit tests for LinkedIn client operations."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.linkedin import (
    LinkedInClient,
    LinkedInError,
    LinkedInValidationError,
    PostVisibility,
)

# ============================================================================
# PROFILE OPERATIONS
# ============================================================================


class TestProfileOperations:
    """Tests for profile-related operations."""

    @pytest.mark.asyncio
    async def test_get_my_profile_success(self, client: LinkedInClient) -> None:
        """Should return authenticated user's profile."""
        from __tests__.integrations.linkedin.conftest import MOCK_PROFILE_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_PROFILE_RESPONSE

            profile = await client.get_my_profile()

            assert profile.id == "user123"
            assert profile.first_name == "Test"
            assert profile.last_name == "User"
            assert profile.email == "test@example.com"
            mock_get.assert_called_once_with("/userinfo")

    @pytest.mark.asyncio
    async def test_get_profile_by_id_success(self, client: LinkedInClient) -> None:
        """Should return profile by ID."""
        mock_response = {
            "id": "profile123",
            "firstName": {"localized": {"en_US": "Jane"}},
            "lastName": {"localized": {"en_US": "Doe"}},
            "headline": {"localized": {"en_US": "Software Engineer"}},
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            profile = await client.get_profile("profile123")

            assert profile.id == "profile123"
            assert profile.first_name == "Jane"
            assert profile.last_name == "Doe"
            assert profile.headline == "Software Engineer"

    @pytest.mark.asyncio
    async def test_get_profile_normalizes_id_to_urn(self, client: LinkedInClient) -> None:
        """Should convert plain ID to URN format."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": "test"}

            await client.get_profile("profile123")

            # Should call with URN format
            mock_get.assert_called_once_with("/people/urn:li:person:profile123")

    @pytest.mark.asyncio
    async def test_get_profile_preserves_existing_urn(self, client: LinkedInClient) -> None:
        """Should preserve existing URN format."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": "test"}

            await client.get_profile("urn:li:person:profile123")

            mock_get.assert_called_once_with("/people/urn:li:person:profile123")


# ============================================================================
# POST OPERATIONS
# ============================================================================


class TestPostOperations:
    """Tests for post-related operations."""

    @pytest.mark.asyncio
    async def test_create_post_success(self, client: LinkedInClient) -> None:
        """Should create a new post."""
        from __tests__.integrations.linkedin.conftest import MOCK_POST_RESPONSE

        client.member_id = "user123"

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_POST_RESPONSE

            post = await client.create_post(text="Hello LinkedIn!")

            assert post.id == "urn:li:ugcPost:123456"
            assert post.text == "Hello LinkedIn!"
            assert post.visibility == PostVisibility.PUBLIC
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_post_requires_authentication(self, client: LinkedInClient) -> None:
        """Should fail if not authenticated."""
        client.member_id = None

        with pytest.raises(LinkedInError, match="Must authenticate before creating"):
            await client.create_post(text="Hello!")

    @pytest.mark.asyncio
    async def test_create_post_validates_text_length(self, client: LinkedInClient) -> None:
        """Should validate text length (max 3000 chars)."""
        client.member_id = "user123"

        long_text = "x" * 3001
        with pytest.raises(LinkedInValidationError, match="3000 character limit"):
            await client.create_post(text=long_text)

    @pytest.mark.asyncio
    async def test_create_post_with_visibility(self, client: LinkedInClient) -> None:
        """Should respect visibility setting."""
        client.member_id = "user123"

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "post123"}

            post = await client.create_post(
                text="Connections only",
                visibility=PostVisibility.CONNECTIONS,
            )

            assert post.visibility == PostVisibility.CONNECTIONS
            # Check the payload included correct visibility
            call_kwargs = mock_post.call_args[1]
            assert (
                call_kwargs["json"]["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"]
                == "CONNECTIONS"
            )

    @pytest.mark.asyncio
    async def test_get_post_success(self, client: LinkedInClient) -> None:
        """Should retrieve a post by ID."""
        mock_response = {
            "id": "urn:li:ugcPost:123456",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": "Test post content"},
                }
            },
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            post = await client.get_post("123456")

            assert post.id == "urn:li:ugcPost:123456"
            assert post.text == "Test post content"

    @pytest.mark.asyncio
    async def test_delete_post_success(self, client: LinkedInClient) -> None:
        """Should delete a post."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {}

            result = await client.delete_post("123456")

            assert result is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_like_post_success(self, client: LinkedInClient) -> None:
        """Should like a post."""
        client.member_id = "user123"

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {}

            result = await client.like_post("123456")

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_like_post_requires_authentication(self, client: LinkedInClient) -> None:
        """Should fail if not authenticated."""
        client.member_id = None

        with pytest.raises(LinkedInError, match="Must authenticate before liking"):
            await client.like_post("123456")

    @pytest.mark.asyncio
    async def test_comment_on_post_success(self, client: LinkedInClient) -> None:
        """Should comment on a post."""
        client.member_id = "user123"

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "comment123"}

            comment = await client.comment_on_post("post123", "Great post!")

            assert comment.id == "comment123"
            assert comment.text == "Great post!"
            assert comment.post_id == "urn:li:ugcPost:post123"

    @pytest.mark.asyncio
    async def test_comment_validates_text_length(self, client: LinkedInClient) -> None:
        """Should validate comment length (max 1250 chars)."""
        client.member_id = "user123"

        long_text = "x" * 1251
        with pytest.raises(LinkedInValidationError, match="1250 character limit"):
            await client.comment_on_post("post123", long_text)


# ============================================================================
# CONNECTION OPERATIONS
# ============================================================================


class TestConnectionOperations:
    """Tests for connection-related operations."""

    @pytest.mark.asyncio
    async def test_get_connections_success(self, client: LinkedInClient) -> None:
        """Should retrieve user's connections."""
        from __tests__.integrations.linkedin.conftest import MOCK_CONNECTIONS_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_CONNECTIONS_RESPONSE

            connections = await client.get_connections()

            assert len(connections) == 2
            assert connections[0].first_name == "Alice"
            assert connections[1].first_name == "Bob"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connections_with_pagination(self, client: LinkedInClient) -> None:
        """Should respect pagination parameters."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"elements": []}

            await client.get_connections(start=10, count=25)

            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"]["start"] == 10
            assert call_kwargs["params"]["count"] == 25

    @pytest.mark.asyncio
    async def test_get_connections_limits_count(self, client: LinkedInClient) -> None:
        """Should limit count to maximum 50."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"elements": []}

            await client.get_connections(count=100)

            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"]["count"] == 50

    @pytest.mark.asyncio
    async def test_send_connection_request_success(self, client: LinkedInClient) -> None:
        """Should send a connection request."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {}

            result = await client.send_connection_request("profile123", message="Let's connect!")

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_connection_request_validates_message_length(
        self, client: LinkedInClient
    ) -> None:
        """Should validate message length (max 300 chars)."""
        long_message = "x" * 301
        with pytest.raises(LinkedInValidationError, match="300 character limit"):
            await client.send_connection_request("profile123", message=long_message)


# ============================================================================
# MESSAGING OPERATIONS
# ============================================================================


class TestMessagingOperations:
    """Tests for messaging-related operations."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, client: LinkedInClient) -> None:
        """Should send a direct message."""
        client.member_id = "user123"

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "msg123", "conversationId": "conv456"}

            message = await client.send_message(
                recipient_id="recipient123",
                body="Hello!",
                subject="Test message",
            )

            assert message.id == "msg123"
            assert message.body == "Hello!"
            assert message.subject == "Test message"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_requires_authentication(self, client: LinkedInClient) -> None:
        """Should fail if not authenticated."""
        client.member_id = None

        with pytest.raises(LinkedInError, match="Must authenticate before sending"):
            await client.send_message("recipient123", "Hello!")

    @pytest.mark.asyncio
    async def test_get_conversations_success(self, client: LinkedInClient) -> None:
        """Should retrieve user's conversations."""
        mock_response = {
            "elements": [
                {"id": "conv1", "unreadCount": 5},
                {"id": "conv2", "unreadCount": 0},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            conversations = await client.get_conversations()

            assert len(conversations) == 2
            assert conversations[0].unread_count == 5

    @pytest.mark.asyncio
    async def test_get_conversation_messages_success(self, client: LinkedInClient) -> None:
        """Should retrieve messages in a conversation."""
        mock_response = {
            "elements": [
                {
                    "id": "event1",
                    "eventContent": {
                        "com.linkedin.voyager.messaging.event.MessageEvent": {"body": "Hello!"}
                    },
                }
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            messages = await client.get_conversation_messages("conv123")

            assert len(messages) == 1
            assert messages[0].body == "Hello!"


# ============================================================================
# SEARCH OPERATIONS
# ============================================================================


class TestSearchOperations:
    """Tests for search-related operations."""

    @pytest.mark.asyncio
    async def test_search_people_success(self, client: LinkedInClient) -> None:
        """Should search for people."""
        from __tests__.integrations.linkedin.conftest import MOCK_SEARCH_RESPONSE

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_SEARCH_RESPONSE

            results = await client.search_people(keywords="software engineer")

            assert results.total_count == 100
            assert len(results.results) == 1

    @pytest.mark.asyncio
    async def test_search_people_with_filters(self, client: LinkedInClient) -> None:
        """Should include search filters in query."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"elements": [], "paging": {}}

            await client.search_people(
                first_name="John",
                last_name="Doe",
                company="Acme Corp",
                title="Engineer",
            )

            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"]["firstName"] == "John"
            assert call_kwargs["params"]["lastName"] == "Doe"
            assert call_kwargs["params"]["company"] == "Acme Corp"
            assert call_kwargs["params"]["title"] == "Engineer"


# ============================================================================
# ENGAGEMENT TRACKING
# ============================================================================


class TestEngagementTracking:
    """Tests for engagement tracking operations."""

    @pytest.mark.asyncio
    async def test_get_post_stats_success(self, client: LinkedInClient) -> None:
        """Should retrieve post engagement statistics."""
        mock_response = {
            "likesSummary": {"totalLikes": 100},
            "commentsSummary": {"totalFirstLevelComments": 25},
            "sharesSummary": {"totalShares": 10},
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            stats = await client.get_post_stats("post123")

            assert stats["likes"] == 100
            assert stats["comments"] == 25
            assert stats["shares"] == 10
