"""Unit tests for Google Sheets client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from __tests__.fixtures.google_sheets_fixtures import (
    BATCH_UPDATE_DATA,
    ERROR_RESPONSES,
    MOCK_SERVICE_ACCOUNT_CREDENTIALS,
    SAMPLE_RESPONSES,
    TEST_VALUES,
)
from src.integrations.google_sheets.client import GoogleSheetsClient
from src.integrations.google_sheets.exceptions import (
    GoogleSheetsAuthError,
    GoogleSheetsConfigError,
    GoogleSheetsNotFoundError,
    GoogleSheetsPermissionError,
    GoogleSheetsQuotaExceeded,
    GoogleSheetsRateLimitError,
    GoogleSheetsValidationError,
)
from src.integrations.google_sheets.models import (
    Spreadsheet,
    ValueInputOption,
    ValueRange,
    ValueRenderOption,
)


class TestGoogleSheetsClientInitialization:
    """Tests for GoogleSheetsClient initialization."""

    def test_init_with_credentials_json(self) -> None:
        """Should initialize with credentials_json parameter."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS
        assert client.access_token is None
        assert client.delegated_user is None

    def test_init_with_credentials_str(self) -> None:
        """Should initialize with credentials_str parameter."""
        creds_str = json.dumps(MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client = GoogleSheetsClient(credentials_str=creds_str)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS

    def test_init_with_access_token(self) -> None:
        """Should initialize with pre-obtained access token."""
        client = GoogleSheetsClient(access_token="test-token-123")
        assert client.access_token == "test-token-123"
        assert client.credentials_json is None

    def test_init_with_delegated_user(self) -> None:
        """Should initialize with delegated_user for domain-wide delegation."""
        client = GoogleSheetsClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            delegated_user="user@example.com",
        )
        assert client.delegated_user == "user@example.com"

    def test_init_with_invalid_json_str_raises(self) -> None:
        """Should raise error for invalid JSON string."""
        with pytest.raises(GoogleSheetsConfigError) as exc_info:
            GoogleSheetsClient(credentials_str="not valid json")
        assert "Invalid credentials JSON" in str(exc_info.value)

    def test_init_without_credentials_raises(self) -> None:
        """Should raise error when no credentials provided."""
        with pytest.raises(GoogleSheetsConfigError) as exc_info:
            GoogleSheetsClient()
        assert "Must provide either" in str(exc_info.value)

    def test_init_sets_default_timeout(self) -> None:
        """Should set default timeout of 30 seconds."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.timeout == 30.0

    def test_init_sets_default_max_retries(self) -> None:
        """Should set default max_retries of 3."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.max_retries == 3


class TestGoogleSheetsClientAuthentication:
    """Tests for authentication methods."""

    @pytest.fixture
    def client(self) -> GoogleSheetsClient:
        """Create client instance for tests."""
        return GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

    @pytest.mark.asyncio
    async def test_authenticate_service_account_success(self, client: GoogleSheetsClient) -> None:
        """Should authenticate successfully with service account."""
        mock_credentials = MagicMock()
        mock_credentials.token = "test-access-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        assert client.access_token == "test-access-token"
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_delegation_uses_single_scope(self) -> None:
        """Should use single scope when delegated_user is set."""
        client = GoogleSheetsClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            delegated_user="user@example.com",
        )

        mock_credentials = MagicMock()
        mock_credentials.token = "delegated-token"
        mock_credentials.with_subject = MagicMock(return_value=mock_credentials)

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

            # Verify single scope was used
            call_args = mock_creds.call_args
            scopes = call_args.kwargs.get("scopes", call_args[1].get("scopes"))
            assert len(scopes) == 1
            assert scopes[0] == client.DELEGATION_SCOPE

            # Verify delegation was applied
            mock_credentials.with_subject.assert_called_once_with("user@example.com")

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Should work as async context manager."""
        mock_credentials = MagicMock()
        mock_credentials.token = "context-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials

            with patch("google.auth.transport.requests.Request"):
                async with GoogleSheetsClient(
                    credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS
                ) as client:
                    assert client.access_token == "context-token"
                    assert client._client is not None


class TestGoogleSheetsClientSpreadsheetOperations:
    """Tests for spreadsheet operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_create_spreadsheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should create a new spreadsheet."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        spreadsheet = await authenticated_client.create_spreadsheet("Test Spreadsheet")

        assert isinstance(spreadsheet, Spreadsheet)
        assert spreadsheet.spreadsheet_id is not None
        assert spreadsheet.properties.title == "Test Spreadsheet"

    @pytest.mark.asyncio
    async def test_create_spreadsheet_with_sheets(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should create spreadsheet with custom sheets."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.create_spreadsheet("Test", sheets=["Sheet1", "Data", "Summary"])

        call_args = authenticated_client._client.request.call_args
        body = call_args.kwargs["json"]
        assert "sheets" in body
        assert len(body["sheets"]) == 3

    @pytest.mark.asyncio
    async def test_get_spreadsheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should get spreadsheet by ID."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        spreadsheet = await authenticated_client.get_spreadsheet("spreadsheet-id")

        assert isinstance(spreadsheet, Spreadsheet)
        assert len(spreadsheet.sheets) == 2

    @pytest.mark.asyncio
    async def test_get_spreadsheet_with_grid_data(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should request grid data when specified."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.get_spreadsheet("spreadsheet-id", include_grid_data=True)

        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["params"]["includeGridData"] == "true"


class TestGoogleSheetsClientSheetOperations:
    """Tests for sheet operations within spreadsheets."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_add_sheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should add a new sheet."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["add_sheet_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        sheet = await authenticated_client.add_sheet("spreadsheet-id", "New Sheet")

        assert sheet.title == "Added Sheet"
        assert sheet.sheet_id == 999

    @pytest.mark.asyncio
    async def test_delete_sheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should delete a sheet."""
        mock_response = httpx.Response(200, json={"spreadsheetId": "id", "replies": [{}]})
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.delete_sheet("spreadsheet-id", 123)

        call_args = authenticated_client._client.request.call_args
        body = call_args.kwargs["json"]
        assert body["requests"][0]["deleteSheet"]["sheetId"] == 123

    @pytest.mark.asyncio
    async def test_rename_sheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should rename a sheet."""
        mock_response = httpx.Response(200, json={"spreadsheetId": "id", "replies": [{}]})
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.rename_sheet("spreadsheet-id", 123, "New Name")

        call_args = authenticated_client._client.request.call_args
        body = call_args.kwargs["json"]
        update_req = body["requests"][0]["updateSheetProperties"]
        assert update_req["properties"]["title"] == "New Name"
        assert update_req["fields"] == "title"

    @pytest.mark.asyncio
    async def test_duplicate_sheet(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should duplicate a sheet."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["duplicate_sheet_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        sheet = await authenticated_client.duplicate_sheet(
            "spreadsheet-id", 0, new_sheet_name="Sheet1 Copy"
        )

        assert sheet.title == "Sheet1 Copy"

    @pytest.mark.asyncio
    async def test_copy_sheet_to_spreadsheet(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should copy sheet to another spreadsheet."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["copy_sheet_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        sheet = await authenticated_client.copy_sheet_to_spreadsheet("source-id", 0, "dest-id")

        assert sheet.title == "Copied Sheet"


class TestGoogleSheetsClientValueOperations:
    """Tests for value (cell data) operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_get_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should get values from a range."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["value_range"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.get_values("spreadsheet-id", "Sheet1!A1:D5")

        assert isinstance(result, ValueRange)
        assert result.range == "Sheet1!A1:D5"
        assert len(result.values) == 5
        assert result.values[0] == ["Name", "Age", "City", "Country"]

    @pytest.mark.asyncio
    async def test_get_values_with_render_option(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should pass value render option."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["value_range"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.get_values(
            "spreadsheet-id",
            "Sheet1!A1:D5",
            value_render_option=ValueRenderOption.FORMULA,
        )

        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["params"]["valueRenderOption"] == "FORMULA"

    @pytest.mark.asyncio
    async def test_update_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should update values in a range."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["update_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.update_values(
            "spreadsheet-id", "Sheet1!A1", TEST_VALUES["simple"]
        )

        assert result.updated_cells == 20
        assert result.updated_rows == 5

    @pytest.mark.asyncio
    async def test_update_values_with_input_option(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should pass value input option."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["update_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        await authenticated_client.update_values(
            "spreadsheet-id",
            "Sheet1!A1",
            TEST_VALUES["simple"],
            value_input_option=ValueInputOption.RAW,
        )

        call_args = authenticated_client._client.request.call_args
        assert call_args.kwargs["params"]["valueInputOption"] == "RAW"

    @pytest.mark.asyncio
    async def test_append_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should append values to a range."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["append_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.append_values(
            "spreadsheet-id", "Sheet1!A:D", [["New", "Row", "Data", "Here"]]
        )

        assert result.updates.updated_rows == 1

    @pytest.mark.asyncio
    async def test_clear_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should clear values from a range."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["clear_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.clear_values("spreadsheet-id", "Sheet1!A1:D5")

        assert result.cleared_range == "Sheet1!A1:D5"


class TestGoogleSheetsClientBatchOperations:
    """Tests for batch operations."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_batch_get_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should get values from multiple ranges."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["batch_get_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.batch_get_values(
            "spreadsheet-id", ["Sheet1!A1:B2", "Sheet1!C1:D2"]
        )

        assert len(result.value_ranges) == 2

    @pytest.mark.asyncio
    async def test_batch_update_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should update values in multiple ranges."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["batch_update_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.batch_update_values("spreadsheet-id", BATCH_UPDATE_DATA)

        assert result.total_updated_cells == 8
        assert len(result.responses) == 2

    @pytest.mark.asyncio
    async def test_batch_clear_values(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should clear values from multiple ranges."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["batch_clear_values_response"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.batch_clear_values(
            "spreadsheet-id", ["Sheet1!A1:B2", "Sheet1!C1:D2"]
        )

        assert len(result.cleared_ranges) == 2


class TestGoogleSheetsClientUtilityMethods:
    """Tests for utility methods."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_get_sheet_id_by_name(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should find sheet ID by name."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        sheet_id = await authenticated_client.get_sheet_id_by_name("spreadsheet-id", "Data")

        assert sheet_id == 123456

    @pytest.mark.asyncio
    async def test_get_sheet_id_by_name_not_found(
        self, authenticated_client: GoogleSheetsClient
    ) -> None:
        """Should return None for non-existent sheet."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        sheet_id = await authenticated_client.get_sheet_id_by_name("spreadsheet-id", "NonExistent")

        assert sheet_id is None

    @pytest.mark.asyncio
    async def test_get_all_sheet_names(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should return all sheet names."""
        mock_response = httpx.Response(200, json=SAMPLE_RESPONSES["spreadsheet"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        names = await authenticated_client.get_all_sheet_names("spreadsheet-id")

        assert names == ["Sheet1", "Data"]

    @pytest.mark.asyncio
    async def test_generic_request(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should make generic API request."""
        mock_response = httpx.Response(200, json={"custom": "response"})
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        result = await authenticated_client.generic_request(
            "GET", "/v4/spreadsheets/id", params={"key": "value"}
        )

        assert result == {"custom": "response"}


class TestGoogleSheetsClientErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    async def authenticated_client(self) -> GoogleSheetsClient:
        """Create authenticated client for tests."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        mock_credentials = MagicMock()
        mock_credentials.token = "test-token"

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as mock_creds:
            mock_creds.return_value = mock_credentials
            with patch("google.auth.transport.requests.Request"):
                await client.authenticate()

        return client

    @pytest.mark.asyncio
    async def test_not_found_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise NotFoundError for 404."""
        mock_response = httpx.Response(404, json=ERROR_RESPONSES["not_found"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsNotFoundError):
            await authenticated_client.get_spreadsheet("nonexistent")

    @pytest.mark.asyncio
    async def test_permission_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise PermissionError for 403."""
        mock_response = httpx.Response(403, json=ERROR_RESPONSES["permission_denied"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsPermissionError):
            await authenticated_client.get_spreadsheet("id")

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise QuotaExceeded for quota errors."""
        mock_response = httpx.Response(403, json=ERROR_RESPONSES["quota_exceeded"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsQuotaExceeded):
            await authenticated_client.get_spreadsheet("id")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise RateLimitError for 429."""
        mock_response = httpx.Response(
            429, json=ERROR_RESPONSES["rate_limited"], headers={"Retry-After": "60"}
        )
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsRateLimitError) as exc_info:
            await authenticated_client.create_spreadsheet("Test")
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_validation_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise ValidationError for 400."""
        mock_response = httpx.Response(400, json=ERROR_RESPONSES["invalid_argument"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsValidationError):
            await authenticated_client.get_values("id", "InvalidRange!")

    @pytest.mark.asyncio
    async def test_auth_error(self, authenticated_client: GoogleSheetsClient) -> None:
        """Should raise AuthError for 401."""
        mock_response = httpx.Response(401, json=ERROR_RESPONSES["unauthorized"])
        authenticated_client._client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleSheetsAuthError):
            await authenticated_client.get_spreadsheet("id")

    @pytest.mark.asyncio
    async def test_request_without_auth_raises(self) -> None:
        """Should raise error when making request without authentication."""
        client = GoogleSheetsClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        with pytest.raises(GoogleSheetsAuthError) as exc_info:
            await client.get_spreadsheet("id")
        assert "not authenticated" in str(exc_info.value).lower()


class TestGoogleSheetsModels:
    """Tests for Pydantic models."""

    def test_spreadsheet_model_parsing(self) -> None:
        """Should parse spreadsheet response correctly."""
        spreadsheet = Spreadsheet.model_validate(SAMPLE_RESPONSES["spreadsheet"])

        assert spreadsheet.spreadsheet_id is not None
        assert spreadsheet.properties.title == "Test Spreadsheet"
        assert len(spreadsheet.sheets) == 2

    def test_value_range_model_parsing(self) -> None:
        """Should parse value range correctly."""
        value_range = ValueRange.model_validate(SAMPLE_RESPONSES["value_range"])

        assert value_range.range == "Sheet1!A1:D5"
        assert len(value_range.values) == 5

    def test_empty_value_range(self) -> None:
        """Should handle empty value range."""
        value_range = ValueRange.model_validate(SAMPLE_RESPONSES["value_range_empty"])

        assert value_range.range == "Sheet1!A1:D5"
        assert value_range.values is None
