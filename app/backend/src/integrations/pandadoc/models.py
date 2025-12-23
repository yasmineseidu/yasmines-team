"""Data models for PandaDoc API.

Defines Pydantic models for documents, templates, recipients, signatures,
and API responses aligned with PandaDoc REST API schema.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Template(BaseModel):
    """PandaDoc template model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    date_created: datetime | None = Field(default=None, alias="date_created")
    date_modified: datetime | None = Field(default=None, alias="date_modified")
    version: str | None = None


class TemplatesListResponse(BaseModel):
    """Response from list templates API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    results: list[Template]


class Recipient(BaseModel):
    """Document recipient model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    email: str
    name: str | None = None
    role: str | None = None  # e.g., "signer", "approver"
    signing_order: int | None = Field(default=None, alias="signing_order")
    message: str | None = None
    redirect_uri: str | None = Field(default=None, alias="redirect_uri")
    decline_redirect_uri: str | None = Field(default=None, alias="decline_redirect_uri")
    completed_redirect_uri: str | None = Field(default=None, alias="completed_redirect_uri")


class Signature(BaseModel):
    """Document signature model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    email: str
    name: str | None = None
    status: str  # "pending", "completed", "declined", "expired"
    signed_at: datetime | None = Field(default=None, alias="signed_at")
    declined_at: datetime | None = Field(default=None, alias="declined_at")
    decline_reason: str | None = Field(default=None, alias="decline_reason")
    ip_address: str | None = Field(default=None, alias="ip_address")


class Document(BaseModel):
    """PandaDoc document model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    status: str  # e.g., "document.draft", "document.sent", "document.completed"
    date_created: datetime | None = Field(default=None, alias="date_created")
    date_modified: datetime | None = Field(default=None, alias="date_modified")
    date_completed: datetime | None = Field(default=None, alias="date_completed")
    expiration_date: datetime | None = Field(default=None, alias="expiration_date")
    version: str | None = None


class DocumentsListResponse(BaseModel):
    """Response from list documents API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    results: list[Document]


class WebhookEvent(BaseModel):
    """PandaDoc webhook event model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    event: str  # e.g., "document.sent", "document.signed", "document.completed"
    data: dict[str, Any]
    timestamp: datetime | None = None
