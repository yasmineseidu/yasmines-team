"""Pydantic models for LinkedIn API responses."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class ConnectionDegree(str, Enum):
    """LinkedIn connection degree."""

    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"
    OUT_OF_NETWORK = "OUT_OF_NETWORK"


class PostVisibility(str, Enum):
    """LinkedIn post visibility setting."""

    PUBLIC = "PUBLIC"
    CONNECTIONS = "CONNECTIONS"
    LOGGED_IN = "LOGGED_IN"


class MessageDeliveryStatus(str, Enum):
    """LinkedIn message delivery status."""

    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


# ============================================================================
# Profile Models
# ============================================================================


class LinkedInLocale(BaseModel):
    """Locale information for LinkedIn profile fields."""

    country: str
    language: str

    class Config:
        populate_by_name = True


class LinkedInProfilePicture(BaseModel):
    """Profile picture information."""

    display_image: str | None = Field(default=None, alias="displayImage")
    display_image_url: str | None = Field(default=None, alias="displayImage~")

    class Config:
        populate_by_name = True


class LinkedInProfile(BaseModel):
    """LinkedIn user profile data."""

    id: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: str | None = None
    headline: str | None = None
    vanity_name: str | None = Field(default=None, alias="vanityName")
    industry: str | None = None
    location: str | None = None
    profile_picture: LinkedInProfilePicture | None = Field(default=None, alias="profilePicture")
    public_profile_url: str | None = Field(default=None, alias="publicProfileUrl")
    connection_count: int | None = Field(default=None, alias="numConnections")
    summary: str | None = None

    class Config:
        populate_by_name = True


class LinkedInConnection(BaseModel):
    """LinkedIn connection (network member)."""

    id: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    headline: str | None = None
    profile_picture_url: str | None = Field(default=None, alias="profilePictureUrl")
    connection_degree: ConnectionDegree | None = Field(default=None, alias="connectionDegree")
    connected_at: datetime | None = Field(default=None, alias="connectedAt")

    class Config:
        populate_by_name = True


# ============================================================================
# Post/Content Models
# ============================================================================


class LinkedInMedia(BaseModel):
    """Media attached to a LinkedIn post."""

    id: str | None = None
    media_type: str = Field(alias="mediaType")  # IMAGE, VIDEO, ARTICLE, DOCUMENT
    url: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = Field(default=None, alias="thumbnailUrl")

    class Config:
        populate_by_name = True


class LinkedInAuthor(BaseModel):
    """Author information for posts/comments."""

    id: str
    name: str | None = None
    vanity_name: str | None = Field(default=None, alias="vanityName")

    class Config:
        populate_by_name = True


class LinkedInPostStats(BaseModel):
    """Engagement statistics for a LinkedIn post."""

    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int | None = None
    impressions: int | None = None

    class Config:
        populate_by_name = True


class LinkedInPost(BaseModel):
    """LinkedIn post/article data."""

    id: str
    author: LinkedInAuthor | None = None
    text: str | None = None
    visibility: PostVisibility = PostVisibility.PUBLIC
    media: list[LinkedInMedia] | None = None
    stats: LinkedInPostStats | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    modified_at: datetime | None = Field(default=None, alias="modifiedAt")
    permalink: str | None = None
    is_reshare: bool = Field(default=False, alias="isReshare")
    original_post_id: str | None = Field(default=None, alias="originalPostId")

    class Config:
        populate_by_name = True


class LinkedInComment(BaseModel):
    """Comment on a LinkedIn post."""

    id: str
    post_id: str = Field(alias="postId")
    author: LinkedInAuthor | None = None
    text: str
    created_at: datetime | None = Field(default=None, alias="createdAt")
    likes: int = 0
    parent_comment_id: str | None = Field(default=None, alias="parentCommentId")

    class Config:
        populate_by_name = True


# ============================================================================
# Messaging Models
# ============================================================================


class LinkedInMessageParticipant(BaseModel):
    """Participant in a LinkedIn conversation."""

    id: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    profile_picture_url: str | None = Field(default=None, alias="profilePictureUrl")

    class Config:
        populate_by_name = True


class LinkedInMessage(BaseModel):
    """LinkedIn direct message."""

    id: str
    conversation_id: str = Field(alias="conversationId")
    sender: LinkedInMessageParticipant | None = None
    recipients: list[LinkedInMessageParticipant] | None = None
    subject: str | None = None
    body: str
    created_at: datetime | None = Field(default=None, alias="createdAt")
    delivery_status: MessageDeliveryStatus = MessageDeliveryStatus.SENT
    attachments: list[LinkedInMedia] | None = None

    class Config:
        populate_by_name = True


class LinkedInConversation(BaseModel):
    """LinkedIn messaging conversation/thread."""

    id: str
    participants: list[LinkedInMessageParticipant] | None = None
    last_message: LinkedInMessage | None = Field(default=None, alias="lastMessage")
    last_activity_at: datetime | None = Field(default=None, alias="lastActivityAt")
    unread_count: int = Field(default=0, alias="unreadCount")

    class Config:
        populate_by_name = True


# ============================================================================
# Search Models
# ============================================================================


class LinkedInSearchResult(BaseModel):
    """Search result from LinkedIn people search."""

    profile: LinkedInProfile | None = None
    connection_degree: ConnectionDegree | None = Field(default=None, alias="connectionDegree")
    shared_connections_count: int | None = Field(default=None, alias="sharedConnectionsCount")

    class Config:
        populate_by_name = True


class LinkedInSearchResponse(BaseModel):
    """Paginated search response."""

    results: list[LinkedInSearchResult] = []
    total_count: int = Field(default=0, alias="totalCount")
    page_size: int = Field(default=10, alias="pageSize")
    start: int = 0
    has_more: bool = Field(default=False, alias="hasMore")

    class Config:
        populate_by_name = True


# ============================================================================
# API Response Wrappers
# ============================================================================


class LinkedInPaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    elements: list[dict[str, Any]] = []
    paging: dict[str, Any] | None = None
    total: int | None = None

    class Config:
        populate_by_name = True
