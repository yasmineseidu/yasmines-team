"""Google Docs API integration package."""

from src.integrations.google_docs.client import (
    GoogleDocsAuthError,
    GoogleDocsClient,
    GoogleDocsError,
    GoogleDocsQuotaError,
    GoogleDocsRateLimitError,
)
from src.integrations.google_docs.models import (
    Document,
    DocumentBody,
    DocumentMetadata,
    InsertTableRequest,
    InsertTextRequest,
    Paragraph,
    ParagraphStyle,
    Permission,
    Table,
    TableCell,
    TextRun,
    TextStyle,
    UpdateTextStyleRequest,
)

__all__ = [
    "GoogleDocsClient",
    "GoogleDocsError",
    "GoogleDocsAuthError",
    "GoogleDocsRateLimitError",
    "GoogleDocsQuotaError",
    "Document",
    "DocumentBody",
    "DocumentMetadata",
    "Paragraph",
    "ParagraphStyle",
    "TextRun",
    "TextStyle",
    "Table",
    "TableCell",
    "Permission",
    "InsertTextRequest",
    "UpdateTextStyleRequest",
    "InsertTableRequest",
]
