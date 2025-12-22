"""Pydantic models for Gmail API responses.

Handles camelCase to snake_case conversion for Gmail API responses.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GmailAttachment(BaseModel):
    """Email attachment metadata and content."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str | None = None
    mime_type: str = Field(alias="mimeType")
    size: int | None = None
    data: str | None = None  # Base64-encoded content
    attachment_id: str | None = Field(default=None, alias="attachmentId")


class GmailMessagePart(BaseModel):
    """Part of a Gmail message (multipart structure)."""

    model_config = ConfigDict(populate_by_name=True)

    mime_type: str = Field(alias="mimeType")
    headers: list[dict[str, Any]] | None = None
    body: dict[str, Any] | None = None
    parts: list["GmailMessagePart"] | None = None
    filename: str | None = None
    partition_id: str | None = Field(default=None, alias="partId")


GmailMessagePart.model_rebuild()


class GmailMessage(BaseModel):
    """Gmail message metadata and content."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    thread_id: str = Field(alias="threadId")
    label_ids: list[str] = Field(default_factory=list, alias="labelIds")
    snippet: str = ""
    payload: GmailMessagePart | None = None
    internal_date: int | None = Field(default=None, alias="internalDate")
    size_estimate: int | None = Field(default=None, alias="sizeEstimate")
    history_id: str | None = Field(default=None, alias="historyId")


class GmailLabel(BaseModel):
    """Gmail label for organizing messages."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    label_list_visibility: str = Field(alias="labelListVisibility")
    message_list_visibility: str = Field(alias="messageListVisibility")
    message_count: int | None = Field(default=None, alias="messagesTotal")
    thread_count: int | None = Field(default=None, alias="threadsTotal")


class GmailDraft(BaseModel):
    """Gmail draft message."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    message: GmailMessage = Field(alias="message")


class GmailThread(BaseModel):
    """Gmail conversation thread with all messages."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    history_id: str | None = Field(default=None, alias="historyId")
    messages: list[GmailMessage] = Field(default_factory=list)
    snippet: str = ""


class GmailProfile(BaseModel):
    """Authenticated user's Gmail profile information."""

    model_config = ConfigDict(populate_by_name=True)

    email_address: str = Field(alias="emailAddress")
    messages_total: int = Field(alias="messagesTotal")
    threads_total: int = Field(alias="threadsTotal")
    history_id: str | None = Field(default=None, alias="historyId")
