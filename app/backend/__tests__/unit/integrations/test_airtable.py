"""Unit tests for Airtable integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.airtable_fixtures import (
    SAMPLE_BATCH_CREATE_RESPONSE,
    SAMPLE_BATCH_DELETE_RESPONSE,
    SAMPLE_BATCH_RECORDS,
    SAMPLE_BATCH_UPDATE_RESPONSE,
    SAMPLE_DELETE_RESPONSE,
    SAMPLE_ERROR_RESPONSE,
    SAMPLE_LEAD_FIELDS,
    SAMPLE_LIST_RECORDS_RESPONSE,
    SAMPLE_LIST_RECORDS_WITH_OFFSET_RESPONSE,
    SAMPLE_LIST_TABLES_RESPONSE,
    SAMPLE_RECORD_RESPONSE,
    SAMPLE_UPDATE_RECORDS,
    SAMPLE_UPSERT_RESPONSE,
    TEST_API_KEY,
    TEST_BASE_ID,
    TEST_RECORD_ID,
    TEST_TABLE_NAME,
)
from src.integrations.airtable import (
    AirtableClient,
    AirtableError,
    AirtableNotFoundError,
    AirtableRecord,
    AirtableTable,
    AirtableValidationError,
    BatchResult,
    CellFormat,
    ListRecordsResult,
    SortConfig,
    SortDirection,
    UpsertResult,
)
from src.integrations.base import RateLimitError


class TestAirtableClientInitialization:
    """Tests for AirtableClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have 'airtable' as name."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.name == "airtable"

    def test_has_correct_base_url(self) -> None:
        """Client should use correct Airtable API base URL."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.base_url == "https://api.airtable.com/v0"

    def test_has_correct_api_version(self) -> None:
        """Client should use API version v0."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.API_VERSION == "v0"

    def test_stores_base_id(self) -> None:
        """Client should store the base ID."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.base_id == TEST_BASE_ID

    def test_has_correct_max_batch_size(self) -> None:
        """Client should have max batch size of 10."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.MAX_BATCH_SIZE == 10

    def test_has_correct_max_page_size(self) -> None:
        """Client should have max page size of 100."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.MAX_PAGE_SIZE == 100

    def test_default_timeout(self) -> None:
        """Client should have default timeout of 30 seconds."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID, timeout=60.0)
        assert client.timeout == 60.0

    def test_default_max_retries(self) -> None:
        """Client should have default max retries of 3."""
        client = AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)
        assert client.max_retries == 3


class TestAirtableClientCreateRecord:
    """Tests for AirtableClient.create_record()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_create_record_success(self, client: AirtableClient) -> None:
        """create_record() should return created record on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            record = await client.create_record(
                table=TEST_TABLE_NAME,
                fields=SAMPLE_LEAD_FIELDS,
            )

            assert isinstance(record, AirtableRecord)
            assert record.id == "recABC123"
            assert record.fields["Name"] == "John Doe"
            assert record.fields["Email"] == "john@example.com"

            mock.assert_called_once()
            call_args = mock.call_args
            assert call_args[0][0] == "POST"
            assert TEST_TABLE_NAME in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_record_with_typecast(self, client: AirtableClient) -> None:
        """create_record() should pass typecast parameter."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            await client.create_record(
                table=TEST_TABLE_NAME,
                fields=SAMPLE_LEAD_FIELDS,
                typecast=True,
            )

            call_args = mock.call_args
            assert call_args[1]["json"]["typecast"] is True

    @pytest.mark.asyncio
    async def test_create_record_validation_error(self, client: AirtableClient) -> None:
        """create_record() should raise AirtableValidationError on 422."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.side_effect = AirtableError(
                message="Validation error",
                status_code=422,
                response_data=SAMPLE_ERROR_RESPONSE,
            )

            with pytest.raises(AirtableValidationError):
                await client.create_record(
                    table=TEST_TABLE_NAME,
                    fields={"Email": "invalid"},
                )


class TestAirtableClientGetRecord:
    """Tests for AirtableClient.get_record()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_get_record_success(self, client: AirtableClient) -> None:
        """get_record() should return record on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            record = await client.get_record(
                table=TEST_TABLE_NAME,
                record_id=TEST_RECORD_ID,
            )

            assert isinstance(record, AirtableRecord)
            assert record.id == TEST_RECORD_ID
            assert record.fields["Name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_get_record_not_found(self, client: AirtableClient) -> None:
        """get_record() should raise AirtableNotFoundError on 404."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.side_effect = AirtableError(
                message="Not found",
                status_code=404,
                response_data=SAMPLE_ERROR_RESPONSE,
            )

            with pytest.raises(AirtableNotFoundError):
                await client.get_record(
                    table=TEST_TABLE_NAME,
                    record_id="recNONEXISTENT",
                )

    @pytest.mark.asyncio
    async def test_get_record_with_cell_format(self, client: AirtableClient) -> None:
        """get_record() should pass cellFormat parameter."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            await client.get_record(
                table=TEST_TABLE_NAME,
                record_id=TEST_RECORD_ID,
                cell_format=CellFormat.STRING,
            )

            call_args = mock.call_args
            assert call_args[1]["params"]["cellFormat"] == "string"


class TestAirtableClientUpdateRecord:
    """Tests for AirtableClient.update_record()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_update_record_success(self, client: AirtableClient) -> None:
        """update_record() should return updated record on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            record = await client.update_record(
                table=TEST_TABLE_NAME,
                record_id=TEST_RECORD_ID,
                fields={"Status": "contacted"},
            )

            assert isinstance(record, AirtableRecord)
            mock.assert_called_once()
            call_args = mock.call_args
            assert call_args[0][0] == "PATCH"  # Default is PATCH

    @pytest.mark.asyncio
    async def test_update_record_destructive(self, client: AirtableClient) -> None:
        """update_record() should use PUT when destructive=True."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_RECORD_RESPONSE

            await client.update_record(
                table=TEST_TABLE_NAME,
                record_id=TEST_RECORD_ID,
                fields={"Status": "contacted"},
                destructive=True,
            )

            call_args = mock.call_args
            assert call_args[0][0] == "PUT"

    @pytest.mark.asyncio
    async def test_update_record_not_found(self, client: AirtableClient) -> None:
        """update_record() should raise AirtableNotFoundError on 404."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.side_effect = AirtableError(
                message="Not found",
                status_code=404,
                response_data=SAMPLE_ERROR_RESPONSE,
            )

            with pytest.raises(AirtableNotFoundError):
                await client.update_record(
                    table=TEST_TABLE_NAME,
                    record_id="recNONEXISTENT",
                    fields={"Status": "contacted"},
                )


class TestAirtableClientDeleteRecord:
    """Tests for AirtableClient.delete_record()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_delete_record_success(self, client: AirtableClient) -> None:
        """delete_record() should return True on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_DELETE_RESPONSE

            result = await client.delete_record(
                table=TEST_TABLE_NAME,
                record_id=TEST_RECORD_ID,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_record_not_found(self, client: AirtableClient) -> None:
        """delete_record() should raise AirtableNotFoundError on 404."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.side_effect = AirtableError(
                message="Not found",
                status_code=404,
                response_data=SAMPLE_ERROR_RESPONSE,
            )

            with pytest.raises(AirtableNotFoundError):
                await client.delete_record(
                    table=TEST_TABLE_NAME,
                    record_id="recNONEXISTENT",
                )


class TestAirtableClientListRecords:
    """Tests for AirtableClient.list_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_list_records_success(self, client: AirtableClient) -> None:
        """list_records() should return ListRecordsResult on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            result = await client.list_records(table=TEST_TABLE_NAME)

            assert isinstance(result, ListRecordsResult)
            assert len(result.records) == 2
            assert result.records[0].id == "recABC123"
            assert result.records[1].id == "recDEF456"
            assert result.offset is None
            assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_records_with_pagination(self, client: AirtableClient) -> None:
        """list_records() should return offset when more records exist."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_WITH_OFFSET_RESPONSE

            result = await client.list_records(table=TEST_TABLE_NAME)

            assert result.offset == "itrXXXXXXXXXXXXXX"
            assert result.has_more is True

    @pytest.mark.asyncio
    async def test_list_records_with_filter(self, client: AirtableClient) -> None:
        """list_records() should pass filterByFormula parameter."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            await client.list_records(
                table=TEST_TABLE_NAME,
                filter_by_formula="{Status} = 'active'",
            )

            call_args = mock.call_args
            assert call_args[1]["params"]["filterByFormula"] == "{Status} = 'active'"

    @pytest.mark.asyncio
    async def test_list_records_with_sort(self, client: AirtableClient) -> None:
        """list_records() should pass sort parameters."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            await client.list_records(
                table=TEST_TABLE_NAME,
                sort=[SortConfig(field="Name", direction=SortDirection.DESC)],
            )

            call_args = mock.call_args
            assert call_args[1]["params"]["sort[0][field]"] == "Name"
            assert call_args[1]["params"]["sort[0][direction]"] == "desc"

    @pytest.mark.asyncio
    async def test_list_records_with_view(self, client: AirtableClient) -> None:
        """list_records() should pass view parameter."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            await client.list_records(
                table=TEST_TABLE_NAME,
                view="Active Leads",
            )

            call_args = mock.call_args
            assert call_args[1]["params"]["view"] == "Active Leads"

    @pytest.mark.asyncio
    async def test_list_records_with_fields(self, client: AirtableClient) -> None:
        """list_records() should pass fields parameter."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            await client.list_records(
                table=TEST_TABLE_NAME,
                fields=["Name", "Email"],
            )

            call_args = mock.call_args
            assert call_args[1]["params"]["fields[]"] == ["Name", "Email"]


class TestAirtableClientListAllRecords:
    """Tests for AirtableClient.list_all_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_list_all_records_single_page(self, client: AirtableClient) -> None:
        """list_all_records() should return all records when no pagination."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_RECORDS_RESPONSE

            records = await client.list_all_records(table=TEST_TABLE_NAME)

            assert len(records) == 2
            assert all(isinstance(r, AirtableRecord) for r in records)

    @pytest.mark.asyncio
    async def test_list_all_records_multiple_pages(self, client: AirtableClient) -> None:
        """list_all_records() should handle pagination automatically."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            # First call returns offset, second call returns no offset
            mock.side_effect = [
                SAMPLE_LIST_RECORDS_WITH_OFFSET_RESPONSE,
                SAMPLE_LIST_RECORDS_RESPONSE,
            ]

            records = await client.list_all_records(table=TEST_TABLE_NAME)

            assert len(records) == 3  # 1 from first page + 2 from second
            assert mock.call_count == 2

    @pytest.mark.asyncio
    async def test_list_all_records_with_max_records(self, client: AirtableClient) -> None:
        """list_all_records() should pass max_records to API."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            # API returns single record when maxRecords=1
            mock.return_value = {
                "records": [SAMPLE_RECORD_RESPONSE],
            }

            records = await client.list_all_records(
                table=TEST_TABLE_NAME,
                max_records=1,
            )

            assert len(records) == 1
            # Verify max_records was passed to API
            call_args = mock.call_args
            assert call_args[1]["params"]["maxRecords"] == 1


class TestAirtableClientBatchCreateRecords:
    """Tests for AirtableClient.batch_create_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_batch_create_records_success(self, client: AirtableClient) -> None:
        """batch_create_records() should return BatchResult on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_BATCH_CREATE_RESPONSE

            result = await client.batch_create_records(
                table=TEST_TABLE_NAME,
                records=SAMPLE_BATCH_RECORDS,
            )

            assert isinstance(result, BatchResult)
            assert result.created_count == 2
            assert len(result.records) == 2

    @pytest.mark.asyncio
    async def test_batch_create_records_exceeds_limit(self, client: AirtableClient) -> None:
        """batch_create_records() should raise ValueError if > 10 records."""
        records = [{"Name": f"Lead {i}"} for i in range(11)]

        with pytest.raises(ValueError, match="Maximum 10 records"):
            await client.batch_create_records(
                table=TEST_TABLE_NAME,
                records=records,
            )


class TestAirtableClientBatchUpdateRecords:
    """Tests for AirtableClient.batch_update_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_batch_update_records_success(self, client: AirtableClient) -> None:
        """batch_update_records() should return BatchResult on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_BATCH_UPDATE_RESPONSE

            result = await client.batch_update_records(
                table=TEST_TABLE_NAME,
                records=SAMPLE_UPDATE_RECORDS,
            )

            assert isinstance(result, BatchResult)
            assert result.updated_count == 1

    @pytest.mark.asyncio
    async def test_batch_update_records_exceeds_limit(self, client: AirtableClient) -> None:
        """batch_update_records() should raise ValueError if > 10 records."""
        records = [{"id": f"rec{i}", "fields": {"Status": "new"}} for i in range(11)]

        with pytest.raises(ValueError, match="Maximum 10 records"):
            await client.batch_update_records(
                table=TEST_TABLE_NAME,
                records=records,
            )


class TestAirtableClientBatchDeleteRecords:
    """Tests for AirtableClient.batch_delete_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_batch_delete_records_success(self, client: AirtableClient) -> None:
        """batch_delete_records() should return list of deleted IDs."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_BATCH_DELETE_RESPONSE

            deleted = await client.batch_delete_records(
                table=TEST_TABLE_NAME,
                record_ids=["recABC123", "recDEF456"],
            )

            assert len(deleted) == 2
            assert "recABC123" in deleted
            assert "recDEF456" in deleted

    @pytest.mark.asyncio
    async def test_batch_delete_records_exceeds_limit(self, client: AirtableClient) -> None:
        """batch_delete_records() should raise ValueError if > 10 records."""
        record_ids = [f"rec{i}" for i in range(11)]

        with pytest.raises(ValueError, match="Maximum 10 records"):
            await client.batch_delete_records(
                table=TEST_TABLE_NAME,
                record_ids=record_ids,
            )


class TestAirtableClientUpsertRecords:
    """Tests for AirtableClient.upsert_records()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_upsert_records_success(self, client: AirtableClient) -> None:
        """upsert_records() should return UpsertResult on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_UPSERT_RESPONSE

            result = await client.upsert_records(
                table=TEST_TABLE_NAME,
                records=SAMPLE_BATCH_RECORDS,
                fields_to_merge_on=["Email"],
            )

            assert isinstance(result, UpsertResult)
            assert result.created_count == 1
            assert result.updated_count == 1
            assert len(result.records) == 2

    @pytest.mark.asyncio
    async def test_upsert_records_payload_format(self, client: AirtableClient) -> None:
        """upsert_records() should send correct payload format."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_UPSERT_RESPONSE

            await client.upsert_records(
                table=TEST_TABLE_NAME,
                records=[{"Email": "test@example.com"}],
                fields_to_merge_on=["Email"],
            )

            call_args = mock.call_args
            payload = call_args[1]["json"]
            assert "performUpsert" in payload
            assert payload["performUpsert"]["fieldsToMergeOn"] == ["Email"]


class TestAirtableClientBulkOperations:
    """Tests for bulk operations with automatic batching."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_bulk_create_records_batching(self, client: AirtableClient) -> None:
        """bulk_create_records() should batch records automatically."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_BATCH_CREATE_RESPONSE

            # Create 15 records (should be 2 batches: 10 + 5)
            records = [{"Name": f"Lead {i}"} for i in range(15)]

            result = await client.bulk_create_records(
                table=TEST_TABLE_NAME,
                records=records,
            )

            assert mock.call_count == 2  # 2 batches
            assert len(result) == 4  # 2 records returned per batch

    @pytest.mark.asyncio
    async def test_bulk_delete_records_batching(self, client: AirtableClient) -> None:
        """bulk_delete_records() should batch deletions automatically."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_BATCH_DELETE_RESPONSE

            # Delete 15 records (should be 2 batches: 10 + 5)
            record_ids = [f"rec{i}" for i in range(15)]

            await client.bulk_delete_records(
                table=TEST_TABLE_NAME,
                record_ids=record_ids,
            )

            assert mock.call_count == 2  # 2 batches


class TestAirtableClientQueryHelpers:
    """Tests for query helper methods."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_find_record_by_field_found(self, client: AirtableClient) -> None:
        """find_record_by_field() should return record when found."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "records": [SAMPLE_RECORD_RESPONSE],
            }

            record = await client.find_record_by_field(
                table=TEST_TABLE_NAME,
                field="Email",
                value="john@example.com",
            )

            assert record is not None
            assert record.fields["Email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_find_record_by_field_not_found(self, client: AirtableClient) -> None:
        """find_record_by_field() should return None when not found."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = {"records": []}

            record = await client.find_record_by_field(
                table=TEST_TABLE_NAME,
                field="Email",
                value="nonexistent@example.com",
            )

            assert record is None

    @pytest.mark.asyncio
    async def test_find_record_by_field_escapes_quotes(self, client: AirtableClient) -> None:
        """find_record_by_field() should escape single quotes in value."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = {"records": []}

            await client.find_record_by_field(
                table=TEST_TABLE_NAME,
                field="Name",
                value="O'Brien",
            )

            call_args = mock.call_args
            formula = call_args[1]["params"]["filterByFormula"]
            assert "O\\'Brien" in formula


class TestAirtableClientListTables:
    """Tests for AirtableClient.list_tables()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_list_tables_success(self, client: AirtableClient) -> None:
        """list_tables() should return list of AirtableTable objects."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_TABLES_RESPONSE

            tables = await client.list_tables()

            assert len(tables) == 2
            assert all(isinstance(t, AirtableTable) for t in tables)
            assert tables[0].name == "Leads"
            assert tables[1].name == "Contacts"

    @pytest.mark.asyncio
    async def test_get_table_found(self, client: AirtableClient) -> None:
        """get_table() should return table when found."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_TABLES_RESPONSE

            table = await client.get_table("tblXXXXXXXXXXXXXX")

            assert table is not None
            assert table.name == "Leads"

    @pytest.mark.asyncio
    async def test_get_table_not_found(self, client: AirtableClient) -> None:
        """get_table() should return None when not found."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_TABLES_RESPONSE

            table = await client.get_table("tblNONEXISTENT")

            assert table is None


class TestAirtableClientHealthCheck:
    """Tests for AirtableClient.health_check()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client: AirtableClient) -> None:
        """health_check() should return healthy status on success."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_LIST_TABLES_RESPONSE

            result = await client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "airtable"
            assert result["base_id"] == TEST_BASE_ID
            assert result["tables_count"] == 2

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client: AirtableClient) -> None:
        """health_check() should return unhealthy status on error."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.side_effect = AirtableError("Connection failed")

            result = await client.health_check()

            assert result["healthy"] is False
            assert "error" in result


class TestAirtableClientRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_rate_limit_error_retries(self, client: AirtableClient) -> None:
        """Client should retry after rate limit error."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            # First call raises rate limit, second succeeds
            mock.side_effect = [
                RateLimitError("Rate limit exceeded", retry_after=30),
                SAMPLE_RECORD_RESPONSE,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                record = await client.get_record(
                    table=TEST_TABLE_NAME,
                    record_id=TEST_RECORD_ID,
                )

            assert record.id == TEST_RECORD_ID
            assert mock.call_count == 2


class TestAirtableClientCallEndpoint:
    """Tests for AirtableClient.call_endpoint()."""

    @pytest.fixture
    def client(self) -> AirtableClient:
        """Create client instance for tests."""
        return AirtableClient(api_key=TEST_API_KEY, base_id=TEST_BASE_ID)

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: AirtableClient) -> None:
        """call_endpoint() should make request to arbitrary endpoint."""
        with patch.object(client, "_request_with_rate_limit", new_callable=AsyncMock) as mock:
            mock.return_value = {"data": "response"}

            result = await client.call_endpoint(
                endpoint="/meta/bases/appXXX/tables",
                method="GET",
            )

            assert result == {"data": "response"}
            mock.assert_called_once_with(
                "GET",
                "/meta/bases/appXXX/tables",
            )


class TestAirtableRecordDataclass:
    """Tests for AirtableRecord dataclass."""

    def test_get_field_existing(self) -> None:
        """get_field() should return field value."""
        record = AirtableRecord(
            id="rec123",
            fields={"Name": "John", "Email": "john@example.com"},
        )
        assert record.get_field("Name") == "John"

    def test_get_field_missing_with_default(self) -> None:
        """get_field() should return default for missing field."""
        record = AirtableRecord(
            id="rec123",
            fields={"Name": "John"},
        )
        assert record.get_field("Missing", default="N/A") == "N/A"

    def test_dict_like_access(self) -> None:
        """Record should support dict-like field access."""
        record = AirtableRecord(
            id="rec123",
            fields={"Name": "John"},
        )
        assert record["Name"] == "John"

    def test_contains_check(self) -> None:
        """Record should support 'in' operator for fields."""
        record = AirtableRecord(
            id="rec123",
            fields={"Name": "John"},
        )
        assert "Name" in record
        assert "Missing" not in record


class TestSortConfig:
    """Tests for SortConfig dataclass."""

    def test_to_dict_ascending(self) -> None:
        """to_dict() should return correct format for ascending sort."""
        config = SortConfig(field="Name", direction=SortDirection.ASC)
        assert config.to_dict() == {"field": "Name", "direction": "asc"}

    def test_to_dict_descending(self) -> None:
        """to_dict() should return correct format for descending sort."""
        config = SortConfig(field="Created", direction=SortDirection.DESC)
        assert config.to_dict() == {"field": "Created", "direction": "desc"}

    def test_default_direction(self) -> None:
        """Default direction should be ascending."""
        config = SortConfig(field="Name")
        assert config.direction == SortDirection.ASC
