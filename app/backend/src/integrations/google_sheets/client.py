"""Google Sheets API client with domain-wide delegation support.

Provides comprehensive access to Google Sheets API v4:
- Spreadsheets: Create, get, update spreadsheet metadata
- Sheets: Add, delete, rename, duplicate sheets within a spreadsheet
- Values: Read, write, append, clear cell data using A1 notation
- Batch operations: Efficient bulk read/write operations

Follows the domain-wide delegation pattern documented in SELF-HEALING.md.
"""

import asyncio
import json
import logging
from typing import Any

import httpx

from src.integrations.google_sheets.exceptions import (
    GoogleSheetsAPIError,
    GoogleSheetsAuthError,
    GoogleSheetsConfigError,
    GoogleSheetsNotFoundError,
    GoogleSheetsPermissionError,
    GoogleSheetsQuotaExceeded,
    GoogleSheetsRateLimitError,
    GoogleSheetsValidationError,
)
from src.integrations.google_sheets.models import (
    AppendValuesResponse,
    BatchClearValuesResponse,
    BatchGetValuesResponse,
    BatchUpdateSpreadsheetResponse,
    BatchUpdateValuesResponse,
    ClearValuesResponse,
    InsertDataOption,
    SheetProperties,
    Spreadsheet,
    UpdateValuesResponse,
    ValueInputOption,
    ValueRange,
    ValueRenderOption,
)

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Google Sheets API client with domain-wide delegation support.

    This client supports three authentication methods:
    1. Service account credentials (credentials_json/credentials_str)
    2. Pre-obtained access token (access_token)
    3. Domain-wide delegation (credentials + delegated_user)

    When using domain-wide delegation, only the single broad scope is requested
    to avoid the "unauthorized_client" error that occurs when requesting
    multiple scopes when only some are authorized in the Admin Console.

    Example usage:
        # With domain-wide delegation (access user's spreadsheets)
        client = GoogleSheetsClient(
            credentials_json=service_account_creds,
            delegated_user="user@example.com"
        )
        await client.authenticate()
        spreadsheet = await client.create_spreadsheet("My Spreadsheet")

        # Read values
        values = await client.get_values(spreadsheet.spreadsheet_id, "Sheet1!A1:D10")

        # Write values
        await client.update_values(
            spreadsheet.spreadsheet_id,
            "Sheet1!A1",
            [["Name", "Age"], ["Alice", 30], ["Bob", 25]]
        )
    """

    BASE_URL = "https://sheets.googleapis.com"

    # Scopes for Google Sheets API
    # For domain-wide delegation, use the broader scope
    DELEGATION_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

    # Default scopes when not using delegation
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        access_token: str | None = None,
        delegated_user: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Google Sheets client.

        Args:
            credentials_json: Service account credentials as a dictionary.
            credentials_str: Service account credentials as a JSON string.
            access_token: Pre-obtained OAuth2 access token.
            delegated_user: Email of user to impersonate via domain-wide delegation.
                           When set, uses single scope to avoid authorization errors.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.credentials_json = credentials_json
        self.credentials_str = credentials_str
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

        # Parse credentials string if provided
        if credentials_str and not credentials_json:
            try:
                self.credentials_json = json.loads(credentials_str)
            except json.JSONDecodeError as e:
                raise GoogleSheetsConfigError(f"Invalid credentials JSON: {e}") from e

        # Validate we have some form of credentials
        if not any([self.credentials_json, self.access_token]):
            raise GoogleSheetsConfigError(
                "Must provide either credentials_json, credentials_str, or access_token"
            )

    async def __aenter__(self) -> "GoogleSheetsClient":
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def authenticate(self) -> None:
        """Authenticate and initialize the HTTP client."""
        if not self.access_token and self.credentials_json:
            await self._authenticate_service_account()

        if not self.access_token:
            raise GoogleSheetsAuthError("No valid access token available")

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        logger.info("Google Sheets client authenticated successfully")

    async def _authenticate_service_account(self) -> None:
        """Authenticate using service account credentials.

        IMPORTANT: When using domain-wide delegation (delegated_user is set),
        we request only the single broad scope that's authorized in the
        Google Workspace Admin Console. Requesting multiple scopes when only
        some are authorized causes authentication to fail entirely.
        """
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        # KEY PATTERN: Use single scope for domain-wide delegation
        # See ~/.claude/context/SELF-HEALING.md for details
        if self.delegated_user:
            scopes = [self.DELEGATION_SCOPE]
            logger.info(
                f"Using domain-wide delegation for: {self.delegated_user} "
                f"with scope: {self.DELEGATION_SCOPE}"
            )
        else:
            scopes = self.DEFAULT_SCOPES

        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scopes,
            )

            # Apply delegation if specified
            if self.delegated_user:
                credentials = credentials.with_subject(self.delegated_user)

            request = Request()
            credentials.refresh(request)
            self.access_token = credentials.token

        except Exception as e:
            error_msg = str(e)
            if "unauthorized_client" in error_msg.lower():
                raise GoogleSheetsAuthError(
                    f"Domain-wide delegation failed. Ensure the scope "
                    f"'{self.DELEGATION_SCOPE}' is authorized in the Google "
                    f"Workspace Admin Console for this service account. "
                    f"Original error: {error_msg}"
                ) from e
            raise GoogleSheetsAuthError(f"Service account authentication failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Google Sheets API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Response data as dictionary.

        Raises:
            GoogleSheetsAPIError: On API errors.
            GoogleSheetsNotFoundError: When resource is not found.
            GoogleSheetsRateLimitError: When rate limited.
        """
        if not self._client:
            raise GoogleSheetsAuthError("Client not authenticated. Call authenticate() first.")

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json_data,
                )

                if response.status_code == 204:
                    return {}

                # Handle error responses
                if response.status_code >= 400:
                    await self._handle_error_response(response)

                return response.json() if response.text else {}

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GoogleSheetsAPIError(
                    f"Request failed after {self.max_retries} retries: {e}"
                ) from e

        raise GoogleSheetsAPIError(f"Request failed: {last_error}") from last_error

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text

        if response.status_code == 401:
            raise GoogleSheetsAuthError(error_message)
        elif response.status_code == 403:
            if "quota" in error_message.lower():
                raise GoogleSheetsQuotaExceeded(error_message)
            raise GoogleSheetsPermissionError(error_message)
        elif response.status_code == 404:
            raise GoogleSheetsNotFoundError(error_message)
        elif response.status_code == 400:
            raise GoogleSheetsValidationError(error_message)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise GoogleSheetsRateLimitError(
                error_message,
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise GoogleSheetsAPIError(error_message, status_code=response.status_code)

    # =========================================================================
    # SPREADSHEET OPERATIONS
    # =========================================================================

    async def create_spreadsheet(
        self,
        title: str,
        sheets: list[str] | None = None,
        locale: str | None = None,
        time_zone: str | None = None,
    ) -> Spreadsheet:
        """Create a new spreadsheet.

        Args:
            title: Title of the spreadsheet.
            sheets: Optional list of sheet names to create.
            locale: Locale of the spreadsheet (e.g., "en_US").
            time_zone: Time zone (e.g., "America/New_York").

        Returns:
            The created Spreadsheet.
        """
        body: dict[str, Any] = {
            "properties": {"title": title},
        }

        if locale:
            body["properties"]["locale"] = locale
        if time_zone:
            body["properties"]["timeZone"] = time_zone

        if sheets:
            body["sheets"] = [{"properties": {"title": sheet_name}} for sheet_name in sheets]

        data = await self._request("POST", "/v4/spreadsheets", json_data=body)
        return Spreadsheet.model_validate(data)

    async def get_spreadsheet(
        self,
        spreadsheet_id: str,
        include_grid_data: bool = False,
        ranges: list[str] | None = None,
    ) -> Spreadsheet:
        """Get a spreadsheet by ID.

        Args:
            spreadsheet_id: The spreadsheet ID.
            include_grid_data: Whether to include grid data (cell values).
            ranges: Specific ranges to include (A1 notation).

        Returns:
            The Spreadsheet with metadata and optionally data.
        """
        params: dict[str, Any] = {
            "includeGridData": str(include_grid_data).lower(),
        }
        if ranges:
            params["ranges"] = ranges

        data = await self._request("GET", f"/v4/spreadsheets/{spreadsheet_id}", params=params)
        return Spreadsheet.model_validate(data)

    async def batch_update_spreadsheet(
        self,
        spreadsheet_id: str,
        requests: list[dict[str, Any]],
        include_spreadsheet_in_response: bool = False,
    ) -> BatchUpdateSpreadsheetResponse:
        """Execute batch updates on a spreadsheet.

        This is the primary method for structural changes like:
        - Adding/deleting sheets
        - Updating sheet properties
        - Merging cells
        - Formatting

        Args:
            spreadsheet_id: The spreadsheet ID.
            requests: List of request objects (see Sheets API docs).
            include_spreadsheet_in_response: Include updated spreadsheet in response.

        Returns:
            BatchUpdateSpreadsheetResponse with results.
        """
        body = {
            "requests": requests,
            "includeSpreadsheetInResponse": include_spreadsheet_in_response,
        }

        data = await self._request(
            "POST", f"/v4/spreadsheets/{spreadsheet_id}:batchUpdate", json_data=body
        )
        return BatchUpdateSpreadsheetResponse.model_validate(data)

    # =========================================================================
    # SHEET OPERATIONS
    # =========================================================================

    async def add_sheet(
        self,
        spreadsheet_id: str,
        title: str,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> SheetProperties:
        """Add a new sheet to a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            title: Title of the new sheet.
            row_count: Number of rows (default: 1000).
            column_count: Number of columns (default: 26).

        Returns:
            Properties of the created sheet.
        """
        properties: dict[str, Any] = {"title": title}

        if row_count or column_count:
            properties["gridProperties"] = {}
            if row_count:
                properties["gridProperties"]["rowCount"] = row_count
            if column_count:
                properties["gridProperties"]["columnCount"] = column_count

        response = await self.batch_update_spreadsheet(
            spreadsheet_id,
            requests=[{"addSheet": {"properties": properties}}],
            include_spreadsheet_in_response=False,
        )

        # Extract the new sheet properties from the reply
        if response.replies and len(response.replies) > 0:
            add_sheet_reply = response.replies[0].get("addSheet", {})
            return SheetProperties.model_validate(add_sheet_reply.get("properties", {}))

        return SheetProperties(title=title)

    async def delete_sheet(self, spreadsheet_id: str, sheet_id: int) -> None:
        """Delete a sheet from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The numeric ID of the sheet to delete.
        """
        await self.batch_update_spreadsheet(
            spreadsheet_id,
            requests=[{"deleteSheet": {"sheetId": sheet_id}}],
        )

    async def rename_sheet(self, spreadsheet_id: str, sheet_id: int, new_title: str) -> None:
        """Rename a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The numeric ID of the sheet.
            new_title: New title for the sheet.
        """
        await self.batch_update_spreadsheet(
            spreadsheet_id,
            requests=[
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "title": new_title},
                        "fields": "title",
                    }
                }
            ],
        )

    async def duplicate_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        new_sheet_name: str | None = None,
        insert_index: int | None = None,
    ) -> SheetProperties:
        """Duplicate a sheet within the same spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The numeric ID of the sheet to duplicate.
            new_sheet_name: Name for the new sheet.
            insert_index: Position to insert the new sheet.

        Returns:
            Properties of the duplicated sheet.
        """
        request: dict[str, Any] = {
            "duplicateSheet": {
                "sourceSheetId": sheet_id,
            }
        }

        if new_sheet_name:
            request["duplicateSheet"]["newSheetName"] = new_sheet_name
        if insert_index is not None:
            request["duplicateSheet"]["insertSheetIndex"] = insert_index

        response = await self.batch_update_spreadsheet(
            spreadsheet_id,
            requests=[request],
            include_spreadsheet_in_response=False,
        )

        if response.replies and len(response.replies) > 0:
            dup_reply = response.replies[0].get("duplicateSheet", {})
            return SheetProperties.model_validate(dup_reply.get("properties", {}))

        return SheetProperties()

    async def copy_sheet_to_spreadsheet(
        self,
        source_spreadsheet_id: str,
        sheet_id: int,
        destination_spreadsheet_id: str,
    ) -> SheetProperties:
        """Copy a sheet to another spreadsheet.

        Args:
            source_spreadsheet_id: Source spreadsheet ID.
            sheet_id: Sheet ID to copy.
            destination_spreadsheet_id: Destination spreadsheet ID.

        Returns:
            Properties of the copied sheet.
        """
        data = await self._request(
            "POST",
            f"/v4/spreadsheets/{source_spreadsheet_id}/sheets/{sheet_id}:copyTo",
            json_data={"destinationSpreadsheetId": destination_spreadsheet_id},
        )
        return SheetProperties.model_validate(data)

    # =========================================================================
    # VALUE OPERATIONS (Read/Write cells)
    # =========================================================================

    async def get_values(
        self,
        spreadsheet_id: str,
        range_: str,
        value_render_option: ValueRenderOption = ValueRenderOption.FORMATTED_VALUE,
        major_dimension: str = "ROWS",
    ) -> ValueRange:
        """Get values from a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            range_: A1 notation range (e.g., "Sheet1!A1:D10").
            value_render_option: How values should be rendered.
            major_dimension: "ROWS" or "COLUMNS".

        Returns:
            ValueRange with the cell values.
        """
        params = {
            "valueRenderOption": value_render_option.value,
            "majorDimension": major_dimension,
        }

        data = await self._request(
            "GET",
            f"/v4/spreadsheets/{spreadsheet_id}/values/{range_}",
            params=params,
        )
        return ValueRange.model_validate(data)

    async def update_values(
        self,
        spreadsheet_id: str,
        range_: str,
        values: list[list[Any]],
        value_input_option: ValueInputOption = ValueInputOption.USER_ENTERED,
        include_values_in_response: bool = False,
    ) -> UpdateValuesResponse:
        """Update values in a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            range_: A1 notation range (e.g., "Sheet1!A1").
            values: 2D array of values to write.
            value_input_option: How input should be interpreted.
            include_values_in_response: Include updated values in response.

        Returns:
            UpdateValuesResponse with update details.
        """
        params = {
            "valueInputOption": value_input_option.value,
            "includeValuesInResponse": str(include_values_in_response).lower(),
        }

        body = {"values": values}

        data = await self._request(
            "PUT",
            f"/v4/spreadsheets/{spreadsheet_id}/values/{range_}",
            params=params,
            json_data=body,
        )
        return UpdateValuesResponse.model_validate(data)

    async def append_values(
        self,
        spreadsheet_id: str,
        range_: str,
        values: list[list[Any]],
        value_input_option: ValueInputOption = ValueInputOption.USER_ENTERED,
        insert_data_option: InsertDataOption = InsertDataOption.INSERT_ROWS,
        include_values_in_response: bool = False,
    ) -> AppendValuesResponse:
        """Append values after the last row of a table.

        Args:
            spreadsheet_id: The spreadsheet ID.
            range_: A1 notation range defining the table.
            values: 2D array of values to append.
            value_input_option: How input should be interpreted.
            insert_data_option: How to insert data.
            include_values_in_response: Include appended values in response.

        Returns:
            AppendValuesResponse with append details.
        """
        params = {
            "valueInputOption": value_input_option.value,
            "insertDataOption": insert_data_option.value,
            "includeValuesInResponse": str(include_values_in_response).lower(),
        }

        body = {"values": values}

        data = await self._request(
            "POST",
            f"/v4/spreadsheets/{spreadsheet_id}/values/{range_}:append",
            params=params,
            json_data=body,
        )
        return AppendValuesResponse.model_validate(data)

    async def clear_values(
        self,
        spreadsheet_id: str,
        range_: str,
    ) -> ClearValuesResponse:
        """Clear values from a range (keeps formatting).

        Args:
            spreadsheet_id: The spreadsheet ID.
            range_: A1 notation range to clear.

        Returns:
            ClearValuesResponse with cleared range info.
        """
        data = await self._request(
            "POST",
            f"/v4/spreadsheets/{spreadsheet_id}/values/{range_}:clear",
        )
        return ClearValuesResponse.model_validate(data)

    # =========================================================================
    # BATCH VALUE OPERATIONS
    # =========================================================================

    async def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
        value_render_option: ValueRenderOption = ValueRenderOption.FORMATTED_VALUE,
        major_dimension: str = "ROWS",
    ) -> BatchGetValuesResponse:
        """Get values from multiple ranges in one request.

        Args:
            spreadsheet_id: The spreadsheet ID.
            ranges: List of A1 notation ranges.
            value_render_option: How values should be rendered.
            major_dimension: "ROWS" or "COLUMNS".

        Returns:
            BatchGetValuesResponse with all ranges.
        """
        params = {
            "ranges": ranges,
            "valueRenderOption": value_render_option.value,
            "majorDimension": major_dimension,
        }

        data = await self._request(
            "GET",
            f"/v4/spreadsheets/{spreadsheet_id}/values:batchGet",
            params=params,
        )
        return BatchGetValuesResponse.model_validate(data)

    async def batch_update_values(
        self,
        spreadsheet_id: str,
        data_updates: list[dict[str, Any]],
        value_input_option: ValueInputOption = ValueInputOption.USER_ENTERED,
        include_values_in_response: bool = False,
    ) -> BatchUpdateValuesResponse:
        """Update values in multiple ranges in one request.

        Args:
            spreadsheet_id: The spreadsheet ID.
            data_updates: List of {"range": "A1:B2", "values": [[...]]} dicts.
            value_input_option: How input should be interpreted.
            include_values_in_response: Include updated values in response.

        Returns:
            BatchUpdateValuesResponse with update details.
        """
        body = {
            "valueInputOption": value_input_option.value,
            "data": data_updates,
            "includeValuesInResponse": include_values_in_response,
        }

        data = await self._request(
            "POST",
            f"/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate",
            json_data=body,
        )
        return BatchUpdateValuesResponse.model_validate(data)

    async def batch_clear_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
    ) -> BatchClearValuesResponse:
        """Clear values from multiple ranges in one request.

        Args:
            spreadsheet_id: The spreadsheet ID.
            ranges: List of A1 notation ranges to clear.

        Returns:
            BatchClearValuesResponse with cleared ranges.
        """
        body = {"ranges": ranges}

        data = await self._request(
            "POST",
            f"/v4/spreadsheets/{spreadsheet_id}/values:batchClear",
            json_data=body,
        )
        return BatchClearValuesResponse.model_validate(data)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> int | None:
        """Get a sheet's numeric ID by its name.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the sheet.

        Returns:
            Sheet ID if found, None otherwise.
        """
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)

        if spreadsheet.sheets:
            for sheet in spreadsheet.sheets:
                if sheet.properties and sheet.properties.title == sheet_name:
                    return sheet.properties.sheet_id

        return None

    async def get_all_sheet_names(self, spreadsheet_id: str) -> list[str]:
        """Get all sheet names in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.

        Returns:
            List of sheet names.
        """
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        names: list[str] = []

        if spreadsheet.sheets:
            for sheet in spreadsheet.sheets:
                if sheet.properties and sheet.properties.title:
                    names.append(sheet.properties.title)

        return names

    async def generic_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a generic API request for future-proofing.

        Allows calling any Google Sheets API endpoint, even ones not yet
        wrapped by this client.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path (e.g., "/v4/spreadsheets").
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Raw response data.
        """
        return await self._request(method, endpoint, params, json_data)
