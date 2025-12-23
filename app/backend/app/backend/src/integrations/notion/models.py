"""Data models for Notion API integration."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Notion user model."""

    id: str
    object: str
    type: str | None = None
    name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(extra="allow")


class Database(BaseModel):
    """Notion database model."""

    id: str
    object: str
    created_time: datetime
    last_edited_time: datetime
    created_by: dict[str, Any] | None = None
    last_edited_by: dict[str, Any] | None = None
    title: list[dict[str, Any]] = Field(default_factory=list)
    description: list[dict[str, Any]] = Field(default_factory=list)
    is_inline: bool = False
    properties: dict[str, Any] = Field(default_factory=dict)
    parent: dict[str, Any] | None = None
    url: str | None = None
    public_url: str | None = None
    icon: dict[str, Any] | None = None
    cover: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

    @property
    def title_text(self) -> str:
        """Extract plain text from title blocks.

        Returns:
            Title as string, or empty string if no title.
        """
        if not self.title:
            return ""
        text_parts = []
        for block in self.title:
            if "text" in block and isinstance(block["text"], dict) and "content" in block["text"]:
                text_parts.append(block["text"]["content"])
        return "".join(text_parts)


class Page(BaseModel):
    """Notion page model."""

    id: str
    object: str
    created_time: datetime
    last_edited_time: datetime
    created_by: dict[str, Any] | None = None
    last_edited_by: dict[str, Any] | None = None
    archived: bool = False
    parent: dict[str, Any] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    url: str | None = None
    public_url: str | None = None
    icon: dict[str, Any] | None = None
    cover: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class Block(BaseModel):
    """Notion block model."""

    id: str
    object: str
    created_time: datetime
    last_edited_time: datetime
    created_by: dict[str, Any] | None = None
    last_edited_by: dict[str, Any] | None = None
    parent: dict[str, Any] | None = None
    type: str
    archived: bool = False
    has_children: bool = False

    # Block-specific content varies by type
    paragraph: dict[str, Any] | None = None
    heading_1: dict[str, Any] | None = None
    heading_2: dict[str, Any] | None = None
    heading_3: dict[str, Any] | None = None
    bulleted_list_item: dict[str, Any] | None = None
    numbered_list_item: dict[str, Any] | None = None
    to_do: dict[str, Any] | None = None
    toggle: dict[str, Any] | None = None
    template: dict[str, Any] | None = None
    synced_block: dict[str, Any] | None = None
    child_page: dict[str, Any] | None = None
    child_database: dict[str, Any] | None = None
    image: dict[str, Any] | None = None
    video: dict[str, Any] | None = None
    file: dict[str, Any] | None = None
    pdf: dict[str, Any] | None = None
    bookmark: dict[str, Any] | None = None
    code: dict[str, Any] | None = None
    callout: dict[str, Any] | None = None
    quote: dict[str, Any] | None = None
    table: dict[str, Any] | None = None
    table_row: dict[str, Any] | None = None
    divider: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class QueryResult(BaseModel):
    """Result from querying a Notion database."""

    object: str
    results: list[Page] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False

    model_config = ConfigDict(extra="allow")


class SearchResult(BaseModel):
    """Result from searching Notion."""

    object: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False

    model_config = ConfigDict(extra="allow")
