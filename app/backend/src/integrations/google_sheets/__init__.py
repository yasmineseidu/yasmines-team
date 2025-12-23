"""Google Sheets API integration for spreadsheet management.

This module provides comprehensive access to Google Sheets API v4:
- Create and manage spreadsheets
- Add, delete, rename, duplicate sheets
- Read, write, append, clear cell values
- Batch operations for efficiency

Supports domain-wide delegation for accessing user spreadsheets.
See ~/.claude/context/SELF-HEALING.md for delegation patterns.
"""

from src.integrations.google_sheets.client import GoogleSheetsClient
from src.integrations.google_sheets.exceptions import (
    GoogleSheetsAPIError,
    GoogleSheetsAuthError,
    GoogleSheetsConfigError,
    GoogleSheetsError,
    GoogleSheetsNotFoundError,
    GoogleSheetsPermissionError,
    GoogleSheetsQuotaExceeded,
    GoogleSheetsRateLimitError,
    GoogleSheetsValidationError,
)
from src.integrations.google_sheets.models import (
    AddSheetRequest,
    AppendValuesResponse,
    BatchClearValuesResponse,
    BatchGetValuesResponse,
    BatchUpdateSpreadsheetResponse,
    BatchUpdateValuesResponse,
    ClearValuesResponse,
    Color,
    ColorStyle,
    CopySheetToAnotherSpreadsheetRequest,
    DeleteSheetRequest,
    Dimension,
    DuplicateSheetRequest,
    GridProperties,
    GridRange,
    InsertDataOption,
    Sheet,
    SheetCopyResponse,
    SheetProperties,
    SheetType,
    Spreadsheet,
    SpreadsheetCreate,
    SpreadsheetProperties,
    UpdateSheetPropertiesRequest,
    UpdateValuesResponse,
    ValueInputOption,
    ValueRange,
    ValueRenderOption,
)

__all__ = [
    # Client
    "GoogleSheetsClient",
    # Exceptions
    "GoogleSheetsError",
    "GoogleSheetsAuthError",
    "GoogleSheetsAPIError",
    "GoogleSheetsConfigError",
    "GoogleSheetsNotFoundError",
    "GoogleSheetsValidationError",
    "GoogleSheetsRateLimitError",
    "GoogleSheetsQuotaExceeded",
    "GoogleSheetsPermissionError",
    # Enums
    "ValueInputOption",
    "ValueRenderOption",
    "InsertDataOption",
    "Dimension",
    "SheetType",
    # Models - Spreadsheet
    "Spreadsheet",
    "SpreadsheetProperties",
    "SpreadsheetCreate",
    # Models - Sheet
    "Sheet",
    "SheetProperties",
    "GridProperties",
    "GridRange",
    "Color",
    "ColorStyle",
    # Models - Values
    "ValueRange",
    "UpdateValuesResponse",
    "AppendValuesResponse",
    "ClearValuesResponse",
    "BatchGetValuesResponse",
    "BatchUpdateValuesResponse",
    "BatchClearValuesResponse",
    "BatchUpdateSpreadsheetResponse",
    # Models - Requests
    "AddSheetRequest",
    "DeleteSheetRequest",
    "UpdateSheetPropertiesRequest",
    "DuplicateSheetRequest",
    "CopySheetToAnotherSpreadsheetRequest",
    "SheetCopyResponse",
]
