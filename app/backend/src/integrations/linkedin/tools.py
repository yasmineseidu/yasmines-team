"""
LinkedIn tools for agent integration.

Provides MCP tools for agents to interact with LinkedIn API
for social selling, B2B outreach, and engagement tracking.
"""

import logging
from typing import Any

from src.integrations.linkedin.client import LinkedInClient
from src.integrations.linkedin.models import PostVisibility

logger = logging.getLogger(__name__)


# ============================================================================
# Profile Tools
# ============================================================================


async def get_my_profile_tool() -> dict[str, Any]:
    """
    Get the authenticated user's LinkedIn profile.

    Returns:
        Profile data including id, name, headline, and email.

    Raises:
        LinkedInError: If operation fails.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        profile = await client.get_my_profile()
        return profile.model_dump()
    finally:
        await client.close()


async def get_profile_tool(profile_id: str) -> dict[str, Any]:
    """
    Get a LinkedIn profile by ID.

    Args:
        profile_id: LinkedIn profile ID or URN.

    Returns:
        Profile data for the specified user.

    Raises:
        LinkedInNotFoundError: If profile not found.
        LinkedInForbiddenError: If profile not accessible.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        profile = await client.get_profile(profile_id)
        return profile.model_dump()
    finally:
        await client.close()


# ============================================================================
# Post Tools
# ============================================================================


async def create_post_tool(
    text: str,
    visibility: str = "PUBLIC",
) -> dict[str, Any]:
    """
    Create a new LinkedIn post.

    Args:
        text: Post content (max 3000 characters).
        visibility: Post visibility - PUBLIC, CONNECTIONS, or LOGGED_IN.

    Returns:
        Created post data including ID and permalink.

    Raises:
        LinkedInValidationError: If content validation fails.
        LinkedInError: If post creation fails.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        vis = PostVisibility(visibility.upper())
        post = await client.create_post(text=text, visibility=vis)
        return post.model_dump()
    finally:
        await client.close()


async def get_post_tool(post_id: str) -> dict[str, Any]:
    """
    Get a specific LinkedIn post.

    Args:
        post_id: LinkedIn post ID or URN.

    Returns:
        Post data including content and engagement stats.

    Raises:
        LinkedInNotFoundError: If post not found.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        post = await client.get_post(post_id)
        return post.model_dump()
    finally:
        await client.close()


async def delete_post_tool(post_id: str) -> dict[str, Any]:
    """
    Delete a LinkedIn post.

    Args:
        post_id: LinkedIn post ID or URN.

    Returns:
        Success status.

    Raises:
        LinkedInNotFoundError: If post not found.
        LinkedInForbiddenError: If not authorized to delete.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        await client.delete_post(post_id)
        return {"success": True, "message": f"Post {post_id} deleted"}
    finally:
        await client.close()


async def like_post_tool(post_id: str) -> dict[str, Any]:
    """
    Like a LinkedIn post.

    Args:
        post_id: LinkedIn post ID or URN.

    Returns:
        Success status.

    Raises:
        LinkedInError: If like operation fails.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        await client.like_post(post_id)
        return {"success": True, "message": f"Liked post {post_id}"}
    finally:
        await client.close()


async def comment_on_post_tool(post_id: str, text: str) -> dict[str, Any]:
    """
    Comment on a LinkedIn post.

    Args:
        post_id: LinkedIn post ID or URN.
        text: Comment text (max 1250 characters).

    Returns:
        Created comment data.

    Raises:
        LinkedInValidationError: If text too long.
        LinkedInError: If comment fails.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        comment = await client.comment_on_post(post_id, text)
        return comment.model_dump()
    finally:
        await client.close()


async def get_post_stats_tool(post_id: str) -> dict[str, Any]:
    """
    Get engagement statistics for a LinkedIn post.

    Args:
        post_id: LinkedIn post ID or URN.

    Returns:
        Engagement stats including likes, comments, and shares.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        return await client.get_post_stats(post_id)
    finally:
        await client.close()


# ============================================================================
# Connection Tools
# ============================================================================


async def get_connections_tool(
    start: int = 0,
    count: int = 50,
) -> dict[str, Any]:
    """
    Get user's LinkedIn connections.

    Args:
        start: Starting index for pagination.
        count: Number of connections to return (max 50).

    Returns:
        List of connections with profile data.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        connections = await client.get_connections(start=start, count=count)
        return {
            "connections": [c.model_dump() for c in connections],
            "count": len(connections),
            "start": start,
        }
    finally:
        await client.close()


async def send_connection_request_tool(
    profile_id: str,
    message: str | None = None,
) -> dict[str, Any]:
    """
    Send a connection request to a LinkedIn member.

    Args:
        profile_id: Target profile ID or URN.
        message: Optional personalized message (max 300 chars).

    Returns:
        Success status.

    Raises:
        LinkedInValidationError: If message too long.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        await client.send_connection_request(profile_id, message)
        return {"success": True, "message": f"Connection request sent to {profile_id}"}
    finally:
        await client.close()


# ============================================================================
# Messaging Tools
# ============================================================================


async def send_message_tool(
    recipient_id: str,
    body: str,
    subject: str | None = None,
) -> dict[str, Any]:
    """
    Send a direct message to a LinkedIn member.

    Args:
        recipient_id: Recipient's profile ID or URN.
        body: Message body text.
        subject: Optional message subject.

    Returns:
        Sent message data.

    Raises:
        LinkedInForbiddenError: If messaging not permitted.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        message = await client.send_message(recipient_id, body, subject)
        return message.model_dump()
    finally:
        await client.close()


async def get_conversations_tool(
    start: int = 0,
    count: int = 20,
) -> dict[str, Any]:
    """
    Get user's message conversations.

    Args:
        start: Starting index for pagination.
        count: Number of conversations to return.

    Returns:
        List of conversations with metadata.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        conversations = await client.get_conversations(start=start, count=count)
        return {
            "conversations": [c.model_dump() for c in conversations],
            "count": len(conversations),
            "start": start,
        }
    finally:
        await client.close()


async def get_conversation_messages_tool(
    conversation_id: str,
    start: int = 0,
    count: int = 20,
) -> dict[str, Any]:
    """
    Get messages in a conversation.

    Args:
        conversation_id: Conversation ID.
        start: Starting index for pagination.
        count: Number of messages to return.

    Returns:
        List of messages in the conversation.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        messages = await client.get_conversation_messages(conversation_id, start=start, count=count)
        return {
            "messages": [m.model_dump() for m in messages],
            "count": len(messages),
            "conversation_id": conversation_id,
        }
    finally:
        await client.close()


# ============================================================================
# Search Tools
# ============================================================================


async def search_people_tool(
    keywords: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    title: str | None = None,
    start: int = 0,
    count: int = 10,
) -> dict[str, Any]:
    """
    Search for LinkedIn profiles.

    Args:
        keywords: General search keywords.
        first_name: Filter by first name.
        last_name: Filter by last name.
        company: Filter by current company.
        title: Filter by job title.
        start: Starting index for pagination.
        count: Number of results to return.

    Returns:
        Search results with matching profiles.
    """
    client = LinkedInClient()
    await client.authenticate()

    try:
        results = await client.search_people(
            keywords=keywords,
            first_name=first_name,
            last_name=last_name,
            company=company,
            title=title,
            start=start,
            count=count,
        )
        return results.model_dump()
    finally:
        await client.close()


# ============================================================================
# MCP Tool Definitions
# ============================================================================

LINKEDIN_TOOLS = {
    # Profile operations
    "linkedin_get_my_profile": {
        "name": "linkedin_get_my_profile",
        "description": "Get the authenticated user's LinkedIn profile including name, headline, and email",
        "function": get_my_profile_tool,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "linkedin_get_profile": {
        "name": "linkedin_get_profile",
        "description": "Get a LinkedIn profile by ID (first-degree connections only)",
        "function": get_profile_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "LinkedIn profile ID or URN",
                },
            },
            "required": ["profile_id"],
        },
    },
    # Post operations
    "linkedin_create_post": {
        "name": "linkedin_create_post",
        "description": "Create a new LinkedIn post with optional visibility control",
        "function": create_post_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Post content (max 3000 characters)",
                },
                "visibility": {
                    "type": "string",
                    "description": "Post visibility: PUBLIC, CONNECTIONS, or LOGGED_IN",
                    "default": "PUBLIC",
                },
            },
            "required": ["text"],
        },
    },
    "linkedin_get_post": {
        "name": "linkedin_get_post",
        "description": "Get a specific LinkedIn post by ID",
        "function": get_post_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "LinkedIn post ID or URN",
                },
            },
            "required": ["post_id"],
        },
    },
    "linkedin_delete_post": {
        "name": "linkedin_delete_post",
        "description": "Delete a LinkedIn post (must be owner)",
        "function": delete_post_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "LinkedIn post ID or URN",
                },
            },
            "required": ["post_id"],
        },
    },
    "linkedin_like_post": {
        "name": "linkedin_like_post",
        "description": "Like a LinkedIn post",
        "function": like_post_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "LinkedIn post ID or URN",
                },
            },
            "required": ["post_id"],
        },
    },
    "linkedin_comment_on_post": {
        "name": "linkedin_comment_on_post",
        "description": "Comment on a LinkedIn post",
        "function": comment_on_post_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "LinkedIn post ID or URN",
                },
                "text": {
                    "type": "string",
                    "description": "Comment text (max 1250 characters)",
                },
            },
            "required": ["post_id", "text"],
        },
    },
    "linkedin_get_post_stats": {
        "name": "linkedin_get_post_stats",
        "description": "Get engagement statistics for a LinkedIn post (likes, comments, shares)",
        "function": get_post_stats_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "LinkedIn post ID or URN",
                },
            },
            "required": ["post_id"],
        },
    },
    # Connection operations
    "linkedin_get_connections": {
        "name": "linkedin_get_connections",
        "description": "Get user's LinkedIn connections with pagination",
        "function": get_connections_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "integer",
                    "description": "Starting index for pagination",
                    "default": 0,
                },
                "count": {
                    "type": "integer",
                    "description": "Number of connections to return (max 50)",
                    "default": 50,
                },
            },
            "required": [],
        },
    },
    "linkedin_send_connection_request": {
        "name": "linkedin_send_connection_request",
        "description": "Send a connection request to a LinkedIn member with optional personalized message",
        "function": send_connection_request_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Target profile ID or URN",
                },
                "message": {
                    "type": "string",
                    "description": "Optional personalized message (max 300 chars)",
                },
            },
            "required": ["profile_id"],
        },
    },
    # Messaging operations
    "linkedin_send_message": {
        "name": "linkedin_send_message",
        "description": "Send a direct message to a LinkedIn member (first-degree connections only)",
        "function": send_message_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "recipient_id": {
                    "type": "string",
                    "description": "Recipient's profile ID or URN",
                },
                "body": {
                    "type": "string",
                    "description": "Message body text",
                },
                "subject": {
                    "type": "string",
                    "description": "Optional message subject",
                },
            },
            "required": ["recipient_id", "body"],
        },
    },
    "linkedin_get_conversations": {
        "name": "linkedin_get_conversations",
        "description": "Get user's message conversations",
        "function": get_conversations_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "integer",
                    "description": "Starting index for pagination",
                    "default": 0,
                },
                "count": {
                    "type": "integer",
                    "description": "Number of conversations to return",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
    "linkedin_get_conversation_messages": {
        "name": "linkedin_get_conversation_messages",
        "description": "Get messages in a LinkedIn conversation",
        "function": get_conversation_messages_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "Conversation ID",
                },
                "start": {
                    "type": "integer",
                    "description": "Starting index for pagination",
                    "default": 0,
                },
                "count": {
                    "type": "integer",
                    "description": "Number of messages to return",
                    "default": 20,
                },
            },
            "required": ["conversation_id"],
        },
    },
    # Search operations
    "linkedin_search_people": {
        "name": "linkedin_search_people",
        "description": "Search for LinkedIn profiles by keywords, name, company, or title",
        "function": search_people_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "General search keywords",
                },
                "first_name": {
                    "type": "string",
                    "description": "Filter by first name",
                },
                "last_name": {
                    "type": "string",
                    "description": "Filter by last name",
                },
                "company": {
                    "type": "string",
                    "description": "Filter by current company",
                },
                "title": {
                    "type": "string",
                    "description": "Filter by job title",
                },
                "start": {
                    "type": "integer",
                    "description": "Starting index for pagination",
                    "default": 0,
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
}
