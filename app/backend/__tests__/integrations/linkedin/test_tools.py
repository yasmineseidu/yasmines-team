"""Unit tests for LinkedIn MCP tools."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.linkedin.tools import (
    LINKEDIN_TOOLS,
    comment_on_post_tool,
    create_post_tool,
    delete_post_tool,
    get_connections_tool,
    get_conversation_messages_tool,
    get_conversations_tool,
    get_my_profile_tool,
    get_post_stats_tool,
    get_post_tool,
    get_profile_tool,
    like_post_tool,
    search_people_tool,
    send_connection_request_tool,
    send_message_tool,
)

# ============================================================================
# TOOL REGISTRY TESTS
# ============================================================================


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_tools_registry_has_expected_tools(self) -> None:
        """Registry should contain all expected tools."""
        expected_tools = [
            "linkedin_get_my_profile",
            "linkedin_get_profile",
            "linkedin_create_post",
            "linkedin_get_post",
            "linkedin_delete_post",
            "linkedin_like_post",
            "linkedin_comment_on_post",
            "linkedin_get_post_stats",
            "linkedin_get_connections",
            "linkedin_send_connection_request",
            "linkedin_send_message",
            "linkedin_get_conversations",
            "linkedin_get_conversation_messages",
            "linkedin_search_people",
        ]
        for tool_name in expected_tools:
            assert tool_name in LINKEDIN_TOOLS

    def test_each_tool_has_required_fields(self) -> None:
        """Each tool should have name, description, function, parameters."""
        for tool_name, tool_def in LINKEDIN_TOOLS.items():
            assert "name" in tool_def, f"{tool_name} missing 'name'"
            assert "description" in tool_def, f"{tool_name} missing 'description'"
            assert "function" in tool_def, f"{tool_name} missing 'function'"
            assert "parameters" in tool_def, f"{tool_name} missing 'parameters'"


# ============================================================================
# PROFILE TOOL TESTS
# ============================================================================


class TestProfileTools:
    """Tests for profile-related tools."""

    @pytest.mark.asyncio
    async def test_get_my_profile_tool(self) -> None:
        """Should return authenticated user's profile."""
        from unittest.mock import MagicMock

        mock_profile_data = {
            "id": "user123",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
        }

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_profile = MagicMock()
            mock_profile.model_dump.return_value = mock_profile_data
            mock_instance.get_my_profile = AsyncMock(return_value=mock_profile)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_my_profile_tool()

            assert result == mock_profile_data
            mock_instance.authenticate.assert_called_once()
            mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profile_tool(self) -> None:
        """Should return profile by ID."""
        from unittest.mock import MagicMock

        mock_profile_data = {
            "id": "profile123",
            "first_name": "Jane",
            "last_name": "Doe",
        }

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_profile = MagicMock()
            mock_profile.model_dump.return_value = mock_profile_data
            mock_instance.get_profile = AsyncMock(return_value=mock_profile)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_profile_tool("profile123")

            assert result == mock_profile_data
            mock_instance.get_profile.assert_called_once_with("profile123")


# ============================================================================
# POST TOOL TESTS
# ============================================================================


class TestPostTools:
    """Tests for post-related tools."""

    @pytest.mark.asyncio
    async def test_create_post_tool(self) -> None:
        """Should create a new post."""
        from unittest.mock import MagicMock

        mock_post_data = {"id": "post123", "text": "Hello!"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_post = MagicMock()
            mock_post.model_dump.return_value = mock_post_data
            mock_instance.create_post = AsyncMock(return_value=mock_post)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await create_post_tool(text="Hello!", visibility="PUBLIC")

            assert result == mock_post_data
            mock_instance.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_post_tool(self) -> None:
        """Should retrieve a post."""
        from unittest.mock import MagicMock

        mock_post_data = {"id": "post123", "text": "Test post"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_post = MagicMock()
            mock_post.model_dump.return_value = mock_post_data
            mock_instance.get_post = AsyncMock(return_value=mock_post)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_post_tool("post123")

            assert result == mock_post_data

    @pytest.mark.asyncio
    async def test_delete_post_tool(self) -> None:
        """Should delete a post."""
        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.delete_post = AsyncMock()
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await delete_post_tool("post123")

            assert result["success"] is True
            mock_instance.delete_post.assert_called_once_with("post123")

    @pytest.mark.asyncio
    async def test_like_post_tool(self) -> None:
        """Should like a post."""
        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.like_post = AsyncMock()
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await like_post_tool("post123")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_comment_on_post_tool(self) -> None:
        """Should comment on a post."""
        from unittest.mock import MagicMock

        mock_comment_data = {"id": "comment123", "text": "Great!"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_comment = MagicMock()
            mock_comment.model_dump.return_value = mock_comment_data
            mock_instance.comment_on_post = AsyncMock(return_value=mock_comment)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await comment_on_post_tool("post123", "Great!")

            assert result == mock_comment_data

    @pytest.mark.asyncio
    async def test_get_post_stats_tool(self) -> None:
        """Should get post engagement stats."""
        mock_stats = {"likes": 100, "comments": 25, "shares": 10}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.get_post_stats = AsyncMock(return_value=mock_stats)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_post_stats_tool("post123")

            assert result == mock_stats


# ============================================================================
# CONNECTION TOOL TESTS
# ============================================================================


class TestConnectionTools:
    """Tests for connection-related tools."""

    @pytest.mark.asyncio
    async def test_get_connections_tool(self) -> None:
        """Should get user's connections."""
        mock_conn = AsyncMock()
        mock_conn.model_dump.return_value = {"id": "conn1", "first_name": "Alice"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.get_connections = AsyncMock(return_value=[mock_conn])
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_connections_tool(start=0, count=10)

            assert result["count"] == 1
            assert "connections" in result

    @pytest.mark.asyncio
    async def test_send_connection_request_tool(self) -> None:
        """Should send a connection request."""
        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.send_connection_request = AsyncMock()
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await send_connection_request_tool("profile123", message="Let's connect!")

            assert result["success"] is True


# ============================================================================
# MESSAGING TOOL TESTS
# ============================================================================


class TestMessagingTools:
    """Tests for messaging-related tools."""

    @pytest.mark.asyncio
    async def test_send_message_tool(self) -> None:
        """Should send a direct message."""
        from unittest.mock import MagicMock

        mock_msg_data = {"id": "msg123", "body": "Hello!"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_msg = MagicMock()
            mock_msg.model_dump.return_value = mock_msg_data
            mock_instance.send_message = AsyncMock(return_value=mock_msg)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await send_message_tool("recipient123", "Hello!", "Hi")

            assert result == mock_msg_data

    @pytest.mark.asyncio
    async def test_get_conversations_tool(self) -> None:
        """Should get user's conversations."""
        mock_conv = AsyncMock()
        mock_conv.model_dump.return_value = {"id": "conv1", "unread_count": 5}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.get_conversations = AsyncMock(return_value=[mock_conv])
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_conversations_tool(start=0, count=10)

            assert result["count"] == 1
            assert "conversations" in result

    @pytest.mark.asyncio
    async def test_get_conversation_messages_tool(self) -> None:
        """Should get messages in a conversation."""
        mock_msg = AsyncMock()
        mock_msg.model_dump.return_value = {"id": "msg1", "body": "Hello"}

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_instance.get_conversation_messages = AsyncMock(return_value=[mock_msg])
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await get_conversation_messages_tool("conv123", start=0, count=10)

            assert result["count"] == 1
            assert result["conversation_id"] == "conv123"


# ============================================================================
# SEARCH TOOL TESTS
# ============================================================================


class TestSearchTools:
    """Tests for search-related tools."""

    @pytest.mark.asyncio
    async def test_search_people_tool(self) -> None:
        """Should search for people."""
        from unittest.mock import MagicMock

        mock_results_data = {
            "results": [],
            "total_count": 100,
            "page_size": 10,
            "start": 0,
            "has_more": True,
        }

        with patch("src.integrations.linkedin.tools.LinkedInClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.authenticate = AsyncMock()
            mock_results = MagicMock()
            mock_results.model_dump.return_value = mock_results_data
            mock_instance.search_people = AsyncMock(return_value=mock_results)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await search_people_tool(keywords="engineer", count=10)

            assert result == mock_results_data
