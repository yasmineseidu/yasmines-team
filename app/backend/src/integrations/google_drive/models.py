"""Pydantic models for Google Drive API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DrivePermission(BaseModel):
    """Google Drive file permission model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str  # user, group, domain, anyone
    role: str  # owner, organizer, fileOrganizer, writer, commenter, reader
    email_address: str | None = Field(default=None, alias="emailAddress")
    display_name: str | None = Field(default=None, alias="displayName")
    photo_link: str | None = Field(default=None, alias="photoLink")


class DriveMetadata(BaseModel):
    """Google Drive file metadata model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    size: int | None = None
    created_time: datetime | None = Field(default=None, alias="createdTime")
    modified_time: datetime | None = Field(default=None, alias="modifiedTime")
    web_view_link: str | None = Field(default=None, alias="webViewLink")
    owners: list[dict[str, Any]] | None = None
    parents: list[str] | None = None
    shared: bool = False
    trashed: bool = False


class DriveFile(BaseModel):
    """Google Drive file model with content and metadata."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    size: int | None = None
    content: str | bytes | None = None
    metadata: DriveMetadata | None = None
    permissions: list[DrivePermission] | None = None
