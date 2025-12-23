"""Pydantic models for Google Sheets API responses.

Based on Google Sheets API v4:
- Spreadsheets: The main document containing sheets
- Sheets: Individual tabs within a spreadsheet
- Values: Cell data accessed via A1 notation
- Formatting: Cell formatting and conditional formatting
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValueInputOption(str, Enum):
    """How input data should be interpreted."""

    INPUT_VALUE_OPTION_UNSPECIFIED = "INPUT_VALUE_OPTION_UNSPECIFIED"
    RAW = "RAW"  # Values are stored as-is
    USER_ENTERED = "USER_ENTERED"  # Values parsed as if user typed them


class ValueRenderOption(str, Enum):
    """How values should be rendered in the output."""

    FORMATTED_VALUE = "FORMATTED_VALUE"  # Display value (formatted)
    UNFORMATTED_VALUE = "UNFORMATTED_VALUE"  # Raw value without formatting
    FORMULA = "FORMULA"  # Formula if cell contains one


class InsertDataOption(str, Enum):
    """How to insert data when appending."""

    OVERWRITE = "OVERWRITE"  # Overwrite existing data
    INSERT_ROWS = "INSERT_ROWS"  # Insert new rows for new data


class Dimension(str, Enum):
    """Dimension of a range."""

    DIMENSION_UNSPECIFIED = "DIMENSION_UNSPECIFIED"
    ROWS = "ROWS"
    COLUMNS = "COLUMNS"


class SheetType(str, Enum):
    """Type of sheet."""

    SHEET_TYPE_UNSPECIFIED = "SHEET_TYPE_UNSPECIFIED"
    GRID = "GRID"  # Regular grid sheet
    OBJECT = "OBJECT"  # Sheet with embedded object (chart)
    DATA_SOURCE = "DATA_SOURCE"  # Connected data source


# Grid Properties


class GridProperties(BaseModel):
    """Properties of a grid (sheet dimensions)."""

    model_config = ConfigDict(populate_by_name=True)

    row_count: int | None = Field(default=None, alias="rowCount")
    column_count: int | None = Field(default=None, alias="columnCount")
    frozen_row_count: int | None = Field(default=None, alias="frozenRowCount")
    frozen_column_count: int | None = Field(default=None, alias="frozenColumnCount")
    hide_gridlines: bool | None = Field(default=None, alias="hideGridlines")
    row_group_control_after: bool | None = Field(default=None, alias="rowGroupControlAfter")
    column_group_control_after: bool | None = Field(default=None, alias="columnGroupControlAfter")


# Color Models


class Color(BaseModel):
    """RGBA color representation."""

    model_config = ConfigDict(populate_by_name=True)

    red: float | None = None
    green: float | None = None
    blue: float | None = None
    alpha: float | None = None


class ColorStyle(BaseModel):
    """Color style (either RGB or theme color)."""

    model_config = ConfigDict(populate_by_name=True)

    rgb_color: Color | None = Field(default=None, alias="rgbColor")
    theme_color: str | None = Field(default=None, alias="themeColor")


# Sheet Properties


class SheetProperties(BaseModel):
    """Properties of a single sheet."""

    model_config = ConfigDict(populate_by_name=True)

    sheet_id: int | None = Field(default=None, alias="sheetId")
    title: str | None = None
    index: int | None = None
    sheet_type: SheetType | None = Field(default=None, alias="sheetType")
    grid_properties: GridProperties | None = Field(default=None, alias="gridProperties")
    hidden: bool | None = None
    tab_color: Color | None = Field(default=None, alias="tabColor")
    tab_color_style: ColorStyle | None = Field(default=None, alias="tabColorStyle")
    right_to_left: bool | None = Field(default=None, alias="rightToLeft")


class Sheet(BaseModel):
    """A single sheet within a spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    properties: SheetProperties | None = None
    data: list[Any] | None = None  # Grid data (if requested)
    merges: list[Any] | None = None  # Merged cell ranges
    conditional_formats: list[Any] | None = Field(default=None, alias="conditionalFormats")
    filter_views: list[Any] | None = Field(default=None, alias="filterViews")
    protected_ranges: list[Any] | None = Field(default=None, alias="protectedRanges")
    basic_filter: Any | None = Field(default=None, alias="basicFilter")
    charts: list[Any] | None = None
    banded_ranges: list[Any] | None = Field(default=None, alias="bandedRanges")
    developer_metadata: list[Any] | None = Field(default=None, alias="developerMetadata")
    row_data: list[Any] | None = Field(default=None, alias="rowData")
    column_groups: list[Any] | None = Field(default=None, alias="columnGroups")
    row_groups: list[Any] | None = Field(default=None, alias="rowGroups")
    slicers: list[Any] | None = None


# Spreadsheet Properties


class SpreadsheetProperties(BaseModel):
    """Properties of a spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    locale: str | None = None
    auto_recalc: str | None = Field(default=None, alias="autoRecalc")
    time_zone: str | None = Field(default=None, alias="timeZone")
    default_format: Any | None = Field(default=None, alias="defaultFormat")
    iterative_calculation_settings: Any | None = Field(
        default=None, alias="iterativeCalculationSettings"
    )
    spreadsheet_theme: Any | None = Field(default=None, alias="spreadsheetTheme")


class Spreadsheet(BaseModel):
    """A Google Sheets spreadsheet.

    Contains metadata and all sheets within the spreadsheet.
    """

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    properties: SpreadsheetProperties | None = None
    sheets: list[Sheet] | None = None
    named_ranges: list[Any] | None = Field(default=None, alias="namedRanges")
    spreadsheet_url: str | None = Field(default=None, alias="spreadsheetUrl")
    developer_metadata: list[Any] | None = Field(default=None, alias="developerMetadata")
    data_sources: list[Any] | None = Field(default=None, alias="dataSources")
    data_source_schedules: list[Any] | None = Field(default=None, alias="dataSourceSchedules")


# Value Range Models


class ValueRange(BaseModel):
    """A range of values in a spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    range: str | None = None  # A1 notation (e.g., "Sheet1!A1:B2")
    major_dimension: Dimension | None = Field(default=None, alias="majorDimension")
    values: list[list[Any]] | None = None  # 2D array of cell values


class UpdateValuesResponse(BaseModel):
    """Response from updating values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    updated_range: str | None = Field(default=None, alias="updatedRange")
    updated_rows: int | None = Field(default=None, alias="updatedRows")
    updated_columns: int | None = Field(default=None, alias="updatedColumns")
    updated_cells: int | None = Field(default=None, alias="updatedCells")
    updated_data: ValueRange | None = Field(default=None, alias="updatedData")


class AppendValuesResponse(BaseModel):
    """Response from appending values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    table_range: str | None = Field(default=None, alias="tableRange")
    updates: UpdateValuesResponse | None = None


class ClearValuesResponse(BaseModel):
    """Response from clearing values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    cleared_range: str | None = Field(default=None, alias="clearedRange")


class BatchGetValuesResponse(BaseModel):
    """Response from batch getting values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    value_ranges: list[ValueRange] | None = Field(default=None, alias="valueRanges")


class BatchUpdateValuesResponse(BaseModel):
    """Response from batch updating values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    total_updated_rows: int | None = Field(default=None, alias="totalUpdatedRows")
    total_updated_columns: int | None = Field(default=None, alias="totalUpdatedColumns")
    total_updated_cells: int | None = Field(default=None, alias="totalUpdatedCells")
    total_updated_sheets: int | None = Field(default=None, alias="totalUpdatedSheets")
    responses: list[UpdateValuesResponse] | None = None


class BatchClearValuesResponse(BaseModel):
    """Response from batch clearing values."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    cleared_ranges: list[str] | None = Field(default=None, alias="clearedRanges")


# Batch Update (Spreadsheet operations) Models


class BatchUpdateSpreadsheetResponse(BaseModel):
    """Response from batch updating a spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str | None = Field(default=None, alias="spreadsheetId")
    replies: list[Any] | None = None  # Responses to each request
    updated_spreadsheet: Spreadsheet | None = Field(default=None, alias="updatedSpreadsheet")


# Request Models for Creating/Updating


class SpreadsheetCreate(BaseModel):
    """Model for creating a new spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    title: str
    sheets: list[SheetProperties] | None = None
    locale: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")


class AddSheetRequest(BaseModel):
    """Request to add a new sheet."""

    model_config = ConfigDict(populate_by_name=True)

    properties: SheetProperties


class DeleteSheetRequest(BaseModel):
    """Request to delete a sheet."""

    model_config = ConfigDict(populate_by_name=True)

    sheet_id: int = Field(alias="sheetId")


class UpdateSheetPropertiesRequest(BaseModel):
    """Request to update sheet properties."""

    model_config = ConfigDict(populate_by_name=True)

    properties: SheetProperties
    fields: str  # Field mask for which properties to update


class DuplicateSheetRequest(BaseModel):
    """Request to duplicate a sheet."""

    model_config = ConfigDict(populate_by_name=True)

    source_sheet_id: int = Field(alias="sourceSheetId")
    insert_sheet_index: int | None = Field(default=None, alias="insertSheetIndex")
    new_sheet_id: int | None = Field(default=None, alias="newSheetId")
    new_sheet_name: str | None = Field(default=None, alias="newSheetName")


class GridRange(BaseModel):
    """A range on a grid (sheet)."""

    model_config = ConfigDict(populate_by_name=True)

    sheet_id: int | None = Field(default=None, alias="sheetId")
    start_row_index: int | None = Field(default=None, alias="startRowIndex")
    end_row_index: int | None = Field(default=None, alias="endRowIndex")
    start_column_index: int | None = Field(default=None, alias="startColumnIndex")
    end_column_index: int | None = Field(default=None, alias="endColumnIndex")


class CopySheetToAnotherSpreadsheetRequest(BaseModel):
    """Request to copy a sheet to another spreadsheet."""

    model_config = ConfigDict(populate_by_name=True)

    destination_spreadsheet_id: str = Field(alias="destinationSpreadsheetId")


class SheetCopyResponse(BaseModel):
    """Response from copying a sheet."""

    model_config = ConfigDict(populate_by_name=True)

    sheet_id: int | None = Field(default=None, alias="sheetId")
    title: str | None = None
    index: int | None = None
    sheet_type: SheetType | None = Field(default=None, alias="sheetType")
    grid_properties: GridProperties | None = Field(default=None, alias="gridProperties")
