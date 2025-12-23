"""Live integration tests for Google Sheets API.

These tests run against the real Google Sheets API using domain-wide delegation.
They create, read, update, and delete real spreadsheets.

Prerequisites:
- GOOGLE_SERVICE_ACCOUNT_FILE environment variable set
- GOOGLE_DELEGATED_USER environment variable set
- Service account has domain-wide delegation with spreadsheets scope
- Google Sheets API enabled in Cloud Console

Run with: uv run pytest __tests__/integration/google_sheets/ -v
"""

import pytest

from src.integrations.google_sheets import (
    GoogleSheetsClient,
    GoogleSheetsNotFoundError,
    InsertDataOption,
    ValueInputOption,
    ValueRenderOption,
)


class TestGoogleSheetsLiveAPI:
    """Live API tests for Google Sheets integration."""

    @pytest.fixture(autouse=True)
    def setup(self, google_service_account_json: dict, google_delegated_user: str):
        """Set up client for each test."""
        self.credentials = google_service_account_json
        self.delegated_user = google_delegated_user
        self.created_spreadsheet_ids: list[str] = []

    @pytest.fixture
    def sheets_client(self) -> GoogleSheetsClient:
        """Create authenticated client."""
        return GoogleSheetsClient(
            credentials_json=self.credentials,
            delegated_user=self.delegated_user,
        )

    async def cleanup_spreadsheets(self, client: GoogleSheetsClient):
        """Clean up created spreadsheets after tests."""
        # Note: Sheets API doesn't have delete - use Drive API for that
        # For now, we'll just track what was created
        for spreadsheet_id in self.created_spreadsheet_ids:
            print(f"  Created spreadsheet (not deleted): {spreadsheet_id}")

    # ========== Health Check ==========

    @pytest.mark.asyncio
    async def test_health_check(self, sheets_client: GoogleSheetsClient):
        """Test that we can authenticate and make a basic API call."""
        async with sheets_client:
            # Try to get a non-existent spreadsheet - should get 404, not auth error
            with pytest.raises(GoogleSheetsNotFoundError):
                await sheets_client.get_spreadsheet("nonexistent-id-12345")
            print("✅ Health check passed - authentication working")

    # ========== Spreadsheet Operations ==========

    @pytest.mark.asyncio
    async def test_create_spreadsheet(
        self, sheets_client: GoogleSheetsClient, test_spreadsheet_data: dict
    ):
        """Test creating a new spreadsheet."""
        async with sheets_client:
            result = await sheets_client.create_spreadsheet(
                title=test_spreadsheet_data["title"],
            )

            assert result.spreadsheet_id is not None
            assert result.properties.title == test_spreadsheet_data["title"]
            assert result.spreadsheet_url is not None
            assert len(result.sheets) >= 1  # At least default sheet

            self.created_spreadsheet_ids.append(result.spreadsheet_id)
            print(f"✅ Created spreadsheet: {result.spreadsheet_id}")
            print(f"   URL: {result.spreadsheet_url}")

    @pytest.mark.asyncio
    async def test_create_spreadsheet_with_sheets(self, sheets_client: GoogleSheetsClient):
        """Test creating a spreadsheet with predefined sheets."""
        async with sheets_client:
            result = await sheets_client.create_spreadsheet(
                title="Multi-Sheet Test",
                sheets=["Data", "Summary", "Charts"],
            )

            assert result.spreadsheet_id is not None
            sheet_names = [s.properties.title for s in result.sheets]
            assert "Data" in sheet_names
            assert "Summary" in sheet_names
            assert "Charts" in sheet_names

            self.created_spreadsheet_ids.append(result.spreadsheet_id)
            print(f"✅ Created spreadsheet with {len(result.sheets)} sheets")

    @pytest.mark.asyncio
    async def test_get_spreadsheet(self, sheets_client: GoogleSheetsClient):
        """Test getting spreadsheet metadata."""
        async with sheets_client:
            # First create a spreadsheet
            created = await sheets_client.create_spreadsheet(title="Get Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Then get it
            result = await sheets_client.get_spreadsheet(created.spreadsheet_id)

            assert result.spreadsheet_id == created.spreadsheet_id
            assert result.properties.title == "Get Test"
            print(f"✅ Retrieved spreadsheet: {result.properties.title}")

    # ========== Sheet Operations ==========

    @pytest.mark.asyncio
    async def test_add_sheet(self, sheets_client: GoogleSheetsClient):
        """Test adding a new sheet to a spreadsheet."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Add Sheet Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Add a sheet
            result = await sheets_client.add_sheet(
                spreadsheet_id=created.spreadsheet_id,
                title="New Sheet",
                row_count=500,
                column_count=20,
            )

            # add_sheet returns SheetProperties directly
            assert result.title == "New Sheet"
            assert result.sheet_id is not None
            print(f"✅ Added sheet: {result.title} (ID: {result.sheet_id})")

    @pytest.mark.asyncio
    async def test_rename_sheet(self, sheets_client: GoogleSheetsClient):
        """Test renaming a sheet."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Rename Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Get the default sheet ID
            sheet_id = created.sheets[0].properties.sheet_id

            # Rename the sheet
            await sheets_client.rename_sheet(
                spreadsheet_id=created.spreadsheet_id,
                sheet_id=sheet_id,
                new_title="Renamed Sheet",
            )

            # Verify by getting spreadsheet again
            updated = await sheets_client.get_spreadsheet(created.spreadsheet_id)
            sheet_names = [s.properties.title for s in updated.sheets]
            assert "Renamed Sheet" in sheet_names
            print("✅ Renamed sheet to: Renamed Sheet")

    @pytest.mark.asyncio
    async def test_duplicate_sheet(self, sheets_client: GoogleSheetsClient):
        """Test duplicating a sheet within a spreadsheet."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Duplicate Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Get the default sheet ID
            sheet_id = created.sheets[0].properties.sheet_id

            # Duplicate the sheet
            await sheets_client.duplicate_sheet(
                spreadsheet_id=created.spreadsheet_id,
                sheet_id=sheet_id,
                new_sheet_name="Sheet1 Copy",
            )

            # Verify
            updated = await sheets_client.get_spreadsheet(created.spreadsheet_id)
            assert len(updated.sheets) == 2
            sheet_names = [s.properties.title for s in updated.sheets]
            assert "Sheet1 Copy" in sheet_names
            print(f"✅ Duplicated sheet: {sheet_names}")

    @pytest.mark.asyncio
    async def test_delete_sheet(self, sheets_client: GoogleSheetsClient):
        """Test deleting a sheet from a spreadsheet."""
        async with sheets_client:
            # Create spreadsheet with 2 sheets
            created = await sheets_client.create_spreadsheet(
                title="Delete Sheet Test",
                sheets=["Keep", "Delete"],
            )
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Find the sheet to delete
            sheet_to_delete = next(s for s in created.sheets if s.properties.title == "Delete")

            # Delete the sheet
            await sheets_client.delete_sheet(
                spreadsheet_id=created.spreadsheet_id,
                sheet_id=sheet_to_delete.properties.sheet_id,
            )

            # Verify
            updated = await sheets_client.get_spreadsheet(created.spreadsheet_id)
            sheet_names = [s.properties.title for s in updated.sheets]
            assert "Keep" in sheet_names
            assert "Delete" not in sheet_names
            print(f"✅ Deleted sheet, remaining: {sheet_names}")

    # ========== Value Operations ==========

    @pytest.mark.asyncio
    async def test_update_and_get_values(
        self, sheets_client: GoogleSheetsClient, sample_values: list[list]
    ):
        """Test writing and reading values."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Values Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write values
            update_result = await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D5",
                values=sample_values,
                value_input_option=ValueInputOption.USER_ENTERED,
            )

            assert update_result.updated_rows == 5
            assert update_result.updated_columns == 4
            assert update_result.updated_cells == 20
            print(f"✅ Updated {update_result.updated_cells} cells")

            # Read values back
            get_result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D5",
            )

            assert len(get_result.values) == 5
            assert get_result.values[0] == ["Name", "Age", "City", "Country"]
            # Note: Numbers come back as strings when read from API
            assert get_result.values[1][0] == "Alice"
            print(f"✅ Read back {len(get_result.values)} rows")

    @pytest.mark.asyncio
    async def test_append_values(
        self, sheets_client: GoogleSheetsClient, sample_values: list[list]
    ):
        """Test appending values to a sheet."""
        async with sheets_client:
            # Create spreadsheet with initial data
            created = await sheets_client.create_spreadsheet(title="Append Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write initial data
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D5",
                values=sample_values,
            )

            # Append new row
            new_row = [["Eve", 32, "Berlin", "Germany"]]
            append_result = await sheets_client.append_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D1",  # Append after table
                values=new_row,
                insert_data_option=InsertDataOption.INSERT_ROWS,
            )

            assert append_result.updates.updated_rows == 1
            print(f"✅ Appended row at: {append_result.updates.updated_range}")

            # Verify by reading all data
            get_result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D10",
            )
            assert len(get_result.values) == 6
            assert get_result.values[5][0] == "Eve"
            print(f"✅ Verified append - now {len(get_result.values)} rows")

    @pytest.mark.asyncio
    async def test_clear_values(self, sheets_client: GoogleSheetsClient):
        """Test clearing values from a range."""
        async with sheets_client:
            # Create and populate spreadsheet
            created = await sheets_client.create_spreadsheet(title="Clear Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:B2",
                values=[["A", "B"], ["C", "D"]],
            )

            # Clear the range
            clear_result = await sheets_client.clear_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:B2",
            )

            assert clear_result.cleared_range == "Sheet1!A1:B2"
            print(f"✅ Cleared range: {clear_result.cleared_range}")

            # Verify cleared
            get_result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:B2",
            )
            # Empty range returns no values
            assert get_result.values is None or len(get_result.values) == 0
            print("✅ Verified range is empty")

    @pytest.mark.asyncio
    async def test_formulas(self, sheets_client: GoogleSheetsClient, sample_formulas: list[list]):
        """Test writing and reading formulas."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Formula Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write data with formulas
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D4",
                values=sample_formulas,
                value_input_option=ValueInputOption.USER_ENTERED,
            )

            # Read as formatted values (computed)
            formatted = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!C2:D4",
                value_render_option=ValueRenderOption.FORMATTED_VALUE,
            )
            print(f"✅ Formatted values: {formatted.values}")

            # Read as formulas
            formulas = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!C2:D4",
                value_render_option=ValueRenderOption.FORMULA,
            )
            # Should contain =A2+B2 etc.
            assert formulas.values[0][0].startswith("=")
            print(f"✅ Formula values: {formulas.values}")

    # ========== Batch Operations ==========

    @pytest.mark.asyncio
    async def test_batch_get_values(self, sheets_client: GoogleSheetsClient):
        """Test reading multiple ranges in one call."""
        async with sheets_client:
            # Create and populate spreadsheet
            created = await sheets_client.create_spreadsheet(title="Batch Get Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D4",
                values=[
                    ["A1", "B1", "C1", "D1"],
                    ["A2", "B2", "C2", "D2"],
                    ["A3", "B3", "C3", "D3"],
                    ["A4", "B4", "C4", "D4"],
                ],
            )

            # Batch get multiple ranges
            result = await sheets_client.batch_get_values(
                spreadsheet_id=created.spreadsheet_id,
                ranges=["Sheet1!A1:B2", "Sheet1!C3:D4"],
            )

            assert len(result.value_ranges) == 2
            assert result.value_ranges[0].values[0][0] == "A1"
            assert result.value_ranges[1].values[0][0] == "C3"
            print(f"✅ Batch get returned {len(result.value_ranges)} ranges")

    @pytest.mark.asyncio
    async def test_batch_update_values(self, sheets_client: GoogleSheetsClient):
        """Test updating multiple ranges in one call."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Batch Update Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Batch update multiple ranges
            data = [
                {"range": "Sheet1!A1:B2", "values": [["A1", "B1"], ["A2", "B2"]]},
                {"range": "Sheet1!D1:E2", "values": [["D1", "E1"], ["D2", "E2"]]},
            ]

            result = await sheets_client.batch_update_values(
                spreadsheet_id=created.spreadsheet_id,
                data_updates=data,
            )

            assert result.total_updated_cells == 8
            print(f"✅ Batch updated {result.total_updated_cells} cells")

            # Verify
            get_result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:E2",
            )
            assert get_result.values[0][0] == "A1"
            assert get_result.values[0][3] == "D1"
            print("✅ Verified batch update")

    @pytest.mark.asyncio
    async def test_batch_clear_values(self, sheets_client: GoogleSheetsClient):
        """Test clearing multiple ranges in one call."""
        async with sheets_client:
            # Create and populate spreadsheet
            created = await sheets_client.create_spreadsheet(title="Batch Clear Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            await sheets_client.batch_update_values(
                spreadsheet_id=created.spreadsheet_id,
                data_updates=[
                    {"range": "Sheet1!A1:B2", "values": [["1", "2"], ["3", "4"]]},
                    {"range": "Sheet1!D1:E2", "values": [["5", "6"], ["7", "8"]]},
                ],
            )

            # Batch clear
            result = await sheets_client.batch_clear_values(
                spreadsheet_id=created.spreadsheet_id,
                ranges=["Sheet1!A1:B2", "Sheet1!D1:E2"],
            )

            assert len(result.cleared_ranges) == 2
            print(f"✅ Batch cleared {len(result.cleared_ranges)} ranges")

    # ========== Utility Methods ==========

    @pytest.mark.asyncio
    async def test_get_sheet_id_by_name(self, sheets_client: GoogleSheetsClient):
        """Test getting sheet ID by name."""
        async with sheets_client:
            # Create spreadsheet with named sheets
            created = await sheets_client.create_spreadsheet(
                title="Sheet ID Test",
                sheets=["Data", "Config"],
            )
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Get sheet ID by name
            data_id = await sheets_client.get_sheet_id_by_name(
                spreadsheet_id=created.spreadsheet_id,
                sheet_name="Data",
            )
            config_id = await sheets_client.get_sheet_id_by_name(
                spreadsheet_id=created.spreadsheet_id,
                sheet_name="Config",
            )

            assert data_id is not None
            assert config_id is not None
            assert data_id != config_id
            print(f"✅ Sheet IDs - Data: {data_id}, Config: {config_id}")

    @pytest.mark.asyncio
    async def test_get_all_sheet_names(self, sheets_client: GoogleSheetsClient):
        """Test getting all sheet names."""
        async with sheets_client:
            # Create spreadsheet with multiple sheets
            created = await sheets_client.create_spreadsheet(
                title="All Names Test",
                sheets=["Alpha", "Beta", "Gamma"],
            )
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Get all sheet names
            names = await sheets_client.get_all_sheet_names(created.spreadsheet_id)

            assert "Alpha" in names
            assert "Beta" in names
            assert "Gamma" in names
            print(f"✅ Sheet names: {names}")

    # ========== Future-Proofing Tests ==========

    @pytest.mark.asyncio
    async def test_generic_request_get(self, sheets_client: GoogleSheetsClient):
        """Test generic_request method for arbitrary GET endpoints."""
        async with sheets_client:
            # Create a spreadsheet first
            created = await sheets_client.create_spreadsheet(title="Generic Request Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Use generic_request to get spreadsheet (same as get_spreadsheet)
            result = await sheets_client.generic_request(
                method="GET",
                endpoint=f"/v4/spreadsheets/{created.spreadsheet_id}",
            )

            assert result["spreadsheetId"] == created.spreadsheet_id
            assert result["properties"]["title"] == "Generic Request Test"
            print("✅ generic_request GET works for arbitrary endpoints")

    @pytest.mark.asyncio
    async def test_generic_request_post(self, sheets_client: GoogleSheetsClient):
        """Test generic_request method for arbitrary POST endpoints."""
        async with sheets_client:
            # Create spreadsheet using generic_request
            result = await sheets_client.generic_request(
                method="POST",
                endpoint="/v4/spreadsheets",
                json_data={
                    "properties": {"title": "Created via generic_request"},
                },
            )

            assert result["spreadsheetId"] is not None
            self.created_spreadsheet_ids.append(result["spreadsheetId"])
            print(f"✅ generic_request POST works - created: {result['spreadsheetId']}")

    @pytest.mark.asyncio
    async def test_batch_update_spreadsheet_formatting(self, sheets_client: GoogleSheetsClient):
        """Test batch_update_spreadsheet for formatting (future-proof pattern)."""
        async with sheets_client:
            # Create spreadsheet
            created = await sheets_client.create_spreadsheet(title="Formatting Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)
            sheet_id = created.sheets[0].properties.sheet_id

            # Use batch_update_spreadsheet for formatting (mergeCells, formatting, etc.)
            # This demonstrates how to call any structural update
            result = await sheets_client.batch_update_spreadsheet(
                spreadsheet_id=created.spreadsheet_id,
                requests=[
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": sheet_id,
                                "title": "Formatted Sheet",
                            },
                            "fields": "title",
                        }
                    }
                ],
            )

            assert result.spreadsheet_id == created.spreadsheet_id
            print("✅ batch_update_spreadsheet works for any structural change")

    # ========== Comprehensive Sample Data Tests ==========

    @pytest.mark.asyncio
    async def test_employee_data(
        self, sheets_client: GoogleSheetsClient, sample_employee_data: list[list]
    ):
        """Test with comprehensive employee database data."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Employee Database Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write employee data
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:F9",
                values=sample_employee_data,
                value_input_option=ValueInputOption.USER_ENTERED,
            )

            # Read back and verify
            result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:F9",
            )

            assert len(result.values) == 9  # Header + 8 employees
            assert result.values[0] == [
                "ID",
                "Name",
                "Department",
                "Salary",
                "Start Date",
                "Active",
            ]
            print(f"✅ Employee data: {len(result.values)} rows written and verified")

    @pytest.mark.asyncio
    async def test_sales_data_with_formulas(
        self, sheets_client: GoogleSheetsClient, sample_sales_data: list[list]
    ):
        """Test sales data with complex formulas."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Sales Report Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write sales data with formulas
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:F7",
                values=sample_sales_data,
                value_input_option=ValueInputOption.USER_ENTERED,
            )

            # Read formulas
            formulas = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!E2:E7",
                value_render_option=ValueRenderOption.FORMULA,
            )
            assert formulas.values[0][0] == "=SUM(B2:D2)"

            # Read computed values
            computed = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!E2:E7",
                value_render_option=ValueRenderOption.FORMATTED_VALUE,
            )
            # Verify formulas computed correctly (15000 + 22000 + 8500 = 45500)
            assert int(computed.values[0][0]) == 45500
            print(f"✅ Sales data formulas computed correctly: {computed.values}")

    @pytest.mark.asyncio
    async def test_unicode_data(
        self, sheets_client: GoogleSheetsClient, sample_unicode_data: list[list]
    ):
        """Test with unicode characters (international text, emojis)."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Unicode Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write unicode data
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D7",
                values=sample_unicode_data,
                value_input_option=ValueInputOption.RAW,
            )

            # Read back and verify unicode preservation
            result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D7",
            )

            # Row indices: 0=header, 1=English, 2=Spanish, 3=Japanese, 4=Arabic, 5=Chinese, 6=Russian
            assert result.values[4][1] == "مرحبا"  # Arabic
            assert result.values[5][1] == "你好"  # Chinese
            assert result.values[1][3] == "👋"  # Emoji
            print("✅ Unicode data preserved correctly")

    @pytest.mark.asyncio
    async def test_large_dataset(
        self, sheets_client: GoogleSheetsClient, sample_large_dataset: list[list]
    ):
        """Test with larger dataset (100+ rows)."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Large Dataset Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write large dataset
            update_result = await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:E101",
                values=sample_large_dataset,
                value_input_option=ValueInputOption.USER_ENTERED,
            )

            assert update_result.updated_rows == 101  # Header + 100 data rows
            assert update_result.updated_cells == 505  # 101 rows * 5 columns

            # Verify formulas computed
            result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!E2:E101",
                value_render_option=ValueRenderOption.FORMATTED_VALUE,
            )
            assert len(result.values) == 100
            # First row: 10 + 20 + 30 = 60
            assert int(result.values[0][0]) == 60
            print(
                f"✅ Large dataset: {update_result.updated_rows} rows, {update_result.updated_cells} cells"
            )

    # ========== Edge Cases ==========

    @pytest.mark.asyncio
    async def test_empty_spreadsheet(self, sheets_client: GoogleSheetsClient):
        """Test handling of empty spreadsheet/ranges."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Empty Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Read empty range
            result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1:D10",
            )
            assert result.values is None or len(result.values) == 0
            print("✅ Empty range handled correctly")

    @pytest.mark.asyncio
    async def test_single_cell_operations(self, sheets_client: GoogleSheetsClient):
        """Test single cell read/write operations."""
        async with sheets_client:
            created = await sheets_client.create_spreadsheet(title="Single Cell Test")
            self.created_spreadsheet_ids.append(created.spreadsheet_id)

            # Write single cell
            await sheets_client.update_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1",
                values=[["Single Value"]],
            )

            # Read single cell
            result = await sheets_client.get_values(
                spreadsheet_id=created.spreadsheet_id,
                range_="Sheet1!A1",
            )
            assert result.values[0][0] == "Single Value"
            print("✅ Single cell operations work")

    @pytest.mark.asyncio
    async def test_copy_sheet_to_another_spreadsheet(self, sheets_client: GoogleSheetsClient):
        """Test copying a sheet to another spreadsheet."""
        async with sheets_client:
            # Create source spreadsheet with data
            source = await sheets_client.create_spreadsheet(title="Copy Source")
            self.created_spreadsheet_ids.append(source.spreadsheet_id)

            await sheets_client.update_values(
                spreadsheet_id=source.spreadsheet_id,
                range_="Sheet1!A1:B2",
                values=[["Source", "Data"], [1, 2]],
            )

            # Create destination spreadsheet
            dest = await sheets_client.create_spreadsheet(title="Copy Destination")
            self.created_spreadsheet_ids.append(dest.spreadsheet_id)

            # Copy sheet to destination
            sheet_id = source.sheets[0].properties.sheet_id
            result = await sheets_client.copy_sheet_to_spreadsheet(
                source_spreadsheet_id=source.spreadsheet_id,
                sheet_id=sheet_id,
                destination_spreadsheet_id=dest.spreadsheet_id,
            )

            assert result.sheet_id is not None
            print(f"✅ Copied sheet to another spreadsheet: {result.title}")


# Run summary if executed directly
if __name__ == "__main__":
    print("Run with: uv run pytest __tests__/integration/google_sheets/ -v")
