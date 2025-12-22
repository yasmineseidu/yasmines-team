"""
Pydantic models for Google Docs API data structures.

Provides type-safe representations of Google Docs entities:
- Document metadata and content
- Text runs with formatting
- Paragraphs and elements
- Tables and cells
- Shared content
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# BASIC MODELS
# ============================================================================


class TextStyle(BaseModel):
    """Text formatting properties."""

    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strikethrough: bool | None = None
    background_color: dict[str, float] | None = None
    foreground_color: dict[str, float] | None = None
    font_size: dict[str, Any] | None = None
    font_family: str | None = None


class TextRun(BaseModel):
    """A run of text with consistent formatting."""

    content: str
    text_style: TextStyle | None = Field(None, alias="textStyle")


class ParagraphStyle(BaseModel):
    """Paragraph formatting properties."""

    alignment: str | None = None
    line_spacing: float | None = Field(None, alias="lineSpacing")
    indent_first_line: float | None = Field(None, alias="indentFirstLine")
    indent_start: float | None = Field(None, alias="indentStart")
    indent_end: float | None = Field(None, alias="indentEnd")
    spacing_before: float | None = Field(None, alias="spacingBefore")
    spacing_after: float | None = Field(None, alias="spacingAfter")


class Paragraph(BaseModel):
    """A paragraph element containing text runs."""

    elements: list[dict[str, Any]] = []
    paragraph_style: ParagraphStyle | None = Field(None, alias="paragraphStyle")


class TableCell(BaseModel):
    """A cell in a table."""

    content: str
    row_index: int = Field(..., alias="rowIndex")
    column_index: int = Field(..., alias="columnIndex")


class Table(BaseModel):
    """A table in a document."""

    rows: int
    columns: int
    cells: list[TableCell] = []


# ============================================================================
# DOCUMENT MODELS
# ============================================================================


class DocumentMetadata(BaseModel):
    """Document metadata."""

    document_id: str = Field(..., alias="documentId")
    title: str
    mime_type: str = Field(default="application/vnd.google-apps.document")
    created_time: str | None = Field(None, alias="createdTime")
    modified_time: str | None = Field(None, alias="modifiedTime")
    size_bytes: int | None = Field(None, alias="size")
    parents: list[str] = []


class DocumentBody(BaseModel):
    """Document body containing content."""

    content: list[dict[str, Any]] = []


class Document(BaseModel):
    """Complete Google Doc representation."""

    document_id: str = Field(..., alias="documentId")
    title: str
    body: DocumentBody | None = None
    document_style: dict[str, Any] | None = Field(None, alias="documentStyle")
    suggestedDocumentStyle: dict[str, Any] | None = None
    named_ranges: dict[str, Any] | None = Field(None, alias="namedRanges")
    revision_id: str | None = Field(None, alias="revisionId")


# ============================================================================
# PERMISSION MODELS
# ============================================================================


class Permission(BaseModel):
    """Document sharing permission."""

    kind: str = "drive#permission"
    id: str
    type: str  # "user", "group", "domain", "anyone"
    email_address: str | None = Field(None, alias="emailAddress")
    domain: str | None = None
    role: str  # "owner", "organizer", "fileOrganizer", "writer", "reader"
    display_name: str | None = Field(None, alias="displayName")


# ============================================================================
# BATCH REQUEST MODELS
# ============================================================================


@dataclass
class InsertTextRequest:
    """Request to insert text into document."""

    text: str
    index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "insertText": {
                "text": self.text,
                "location": {"index": self.index},
            }
        }


@dataclass
class UpdateTextStyleRequest:
    """Request to update text formatting."""

    start_index: int
    end_index: int
    text_style: dict[str, Any]
    fields: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "updateTextStyle": {
                "range": {
                    "startIndex": self.start_index,
                    "endIndex": self.end_index,
                },
                "textStyle": self.text_style,
                "fields": self.fields,
            }
        }


@dataclass
class InsertTableRequest:
    """Request to insert table into document."""

    rows: int
    columns: int
    index: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "insertTable": {
                "rows": self.rows,
                "columns": self.columns,
                "location": {"index": self.index},
            }
        }


# ============================================================================
# OPERATION RESPONSE MODELS
# ============================================================================


class BatchUpdateResponse(BaseModel):
    """Response from batch update operation."""

    document_id: str = Field(..., alias="documentId")
    replies: list[dict[str, Any]] = []
    write_control: dict[str, Any] | None = Field(None, alias="writeControl")


class CreateDocumentResponse(BaseModel):
    """Response from document creation."""

    document_id: str = Field(..., alias="id")
    title: str = Field(..., alias="name")
    mime_type: str = Field(..., alias="mimeType")
    parents: list[str] | None = None
