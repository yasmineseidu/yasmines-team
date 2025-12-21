"""
Live API tests for Airtable integration.

These tests run against the REAL Airtable API using actual API keys.
They verify that all endpoints work correctly with the live service.

Requirements:
- AIRTABLE_API_KEY must be set in .env at project root
- AIRTABLE_BASE_ID must be a valid Airtable base ID (e.g., appXXXXXXXXXXXXXX)
- Tests create/modify/delete real data in the Airtable base
- Run with: pytest __tests__/integration/test_airtable_live.py -v -m live_api

Coverage:
- Record CRUD (create, get, update, delete)
- Batch operations (batch create, batch update, batch delete)
- Bulk operations (bulk create, bulk update, bulk delete)
- Upsert operations
- List and filter records
- Schema introspection (list tables)
- Health check
- Future-proof call_endpoint method
- Error handling

IMPORTANT: All tests MUST pass 100%. No exceptions.
"""

import contextlib
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations import (
    AirtableClient,
    AirtableError,
    AirtableNotFoundError,
    AirtableRecord,
    AirtableTable,
    BatchResult,
    ListRecordsResult,
    SortDirection,
    UpsertResult,
)

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# Test table name - using "Leads Enhanced" table
# Fields: Full Name, First Name, Last Name, Email, Phone
TEST_TABLE_NAME = "Leads Enhanced"


def get_credentials() -> tuple[str, str]:
    """Get API key and base ID from environment."""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key:
        pytest.skip("AIRTABLE_API_KEY not found in .env - skipping live tests")
    if not base_id or base_id == "app...":
        pytest.skip("AIRTABLE_BASE_ID not configured in .env - skipping live tests")

    return api_key, base_id


def generate_unique_name() -> str:
    """Generate a unique name for test records."""
    return f"LiveTest_{uuid.uuid4().hex[:8]}"


def generate_test_email() -> str:
    """Generate a unique test email."""
    return f"test_{uuid.uuid4().hex[:8]}@airtable-live-test.com"


@pytest.fixture
def credentials() -> tuple[str, str]:
    """Fixture to get API key and base ID."""
    return get_credentials()


@pytest.fixture
async def client(credentials: tuple[str, str]) -> AirtableClient:
    """Create AirtableClient for testing."""
    api_key, base_id = credentials
    return AirtableClient(api_key=api_key, base_id=base_id, timeout=60.0, max_retries=3)


@pytest.fixture
async def test_record(client: AirtableClient) -> AirtableRecord:
    """Create a test record and clean up after test."""
    name = generate_unique_name()
    email = generate_test_email()

    record = await client.create_record(
        table=TEST_TABLE_NAME,
        fields={"Full Name": name, "First Name": "Test", "Last Name": "User", "Email": email},
    )
    yield record
    # Cleanup: delete the record after test
    with contextlib.suppress(AirtableError):
        await client.delete_record(TEST_TABLE_NAME, record.id)


# =============================================================================
# RECORD CRUD TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestRecordCRUDLive:
    """Live tests for record CRUD operations - MUST pass 100%."""

    async def test_create_record_success(self, client: AirtableClient) -> None:
        """Test creating a record with real API - MUST PASS."""
        name = generate_unique_name()
        email = generate_test_email()

        record = await client.create_record(
            table=TEST_TABLE_NAME,
            fields={"Full Name": name, "First Name": "Test", "Last Name": "User", "Email": email},
        )

        # Verify response structure
        assert isinstance(record, AirtableRecord)
        assert record.id is not None
        assert record.id.startswith("rec")
        assert record.fields["Full Name"] == name
        assert record.fields["Email"] == email

        # Cleanup
        await client.delete_record(TEST_TABLE_NAME, record.id)
        print(f"  create_record: Created and verified record {record.id}")

    async def test_get_record_success(
        self, client: AirtableClient, test_record: AirtableRecord
    ) -> None:
        """Test getting a single record - MUST PASS."""
        record = await client.get_record(TEST_TABLE_NAME, test_record.id)

        assert isinstance(record, AirtableRecord)
        assert record.id == test_record.id
        assert record.fields["Full Name"] == test_record.fields["Full Name"]

        print(f"  get_record: Retrieved record {record.id}")

    async def test_update_record_success(
        self, client: AirtableClient, test_record: AirtableRecord
    ) -> None:
        """Test updating a record - MUST PASS."""
        new_phone = "+1-555-123-4567"

        updated = await client.update_record(
            table=TEST_TABLE_NAME,
            record_id=test_record.id,
            fields={"Phone": new_phone},
        )

        assert isinstance(updated, AirtableRecord)
        assert updated.id == test_record.id
        assert updated.fields["Phone"] == new_phone

        print(f"  update_record: Updated record {updated.id}")

    async def test_delete_record_success(self, client: AirtableClient) -> None:
        """Test deleting a record - MUST PASS."""
        # Create a record to delete
        record = await client.create_record(
            table=TEST_TABLE_NAME,
            fields={"Full Name": generate_unique_name(), "Email": generate_test_email()},
        )

        result = await client.delete_record(TEST_TABLE_NAME, record.id)

        assert result is True

        # Verify deletion by trying to get it (should fail)
        # Note: Airtable may return 403 or 404 for deleted/invalid records
        with pytest.raises((AirtableNotFoundError, AirtableError)):
            await client.get_record(TEST_TABLE_NAME, record.id)

        print(f"  delete_record: Deleted record {record.id}")


# =============================================================================
# LIST RECORDS TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestListRecordsLive:
    """Live tests for listing records - MUST pass 100%."""

    async def test_list_records_success(self, client: AirtableClient) -> None:
        """Test listing records with real API - MUST PASS."""
        result = await client.list_records(table=TEST_TABLE_NAME, max_records=10)

        assert isinstance(result, ListRecordsResult)
        assert isinstance(result.records, list)
        for record in result.records:
            assert isinstance(record, AirtableRecord)
            assert record.id is not None

        print(f"  list_records: Retrieved {len(result.records)} records")

    async def test_list_records_with_filter(
        self, client: AirtableClient, test_record: AirtableRecord
    ) -> None:
        """Test listing records with filter formula - MUST PASS."""
        filter_formula = f"{{Full Name}} = '{test_record.fields['Full Name']}'"

        result = await client.list_records(
            table=TEST_TABLE_NAME,
            filter_by_formula=filter_formula,
        )

        assert isinstance(result, ListRecordsResult)
        # Should find our test record
        assert any(r.id == test_record.id for r in result.records)

        print(f"  list_records with filter: Found {len(result.records)} matching records")

    async def test_list_records_with_sort(self, client: AirtableClient) -> None:
        """Test listing records with sorting - MUST PASS."""
        from src.integrations import SortConfig

        result = await client.list_records(
            table=TEST_TABLE_NAME,
            max_records=10,
            sort=[SortConfig(field="Full Name", direction=SortDirection.ASC)],
        )

        assert isinstance(result, ListRecordsResult)
        print(f"  list_records with sort: Retrieved {len(result.records)} sorted records")

    async def test_list_records_with_fields(self, client: AirtableClient) -> None:
        """Test listing records with field selection - MUST PASS."""
        result = await client.list_records(
            table=TEST_TABLE_NAME,
            max_records=5,
            fields=["Full Name", "Email"],
        )

        assert isinstance(result, ListRecordsResult)
        print(
            f"  list_records with fields: Retrieved {len(result.records)} records with selected fields"
        )

    async def test_list_all_records_success(self, client: AirtableClient) -> None:
        """Test listing all records with pagination - MUST PASS."""
        records = await client.list_all_records(
            table=TEST_TABLE_NAME,
            max_records=20,
        )

        assert isinstance(records, list)
        for record in records:
            assert isinstance(record, AirtableRecord)

        print(f"  list_all_records: Retrieved {len(records)} total records")


# =============================================================================
# BATCH OPERATIONS TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestBatchOperationsLive:
    """Live tests for batch operations - MUST pass 100%."""

    async def test_batch_create_records_success(self, client: AirtableClient) -> None:
        """Test batch creating records - MUST PASS."""
        records_to_create = [
            {"Full Name": generate_unique_name(), "Email": generate_test_email()} for _ in range(3)
        ]

        result = await client.batch_create_records(
            table=TEST_TABLE_NAME,
            records=records_to_create,
        )

        assert isinstance(result, BatchResult)
        assert result.created_count == 3
        assert len(result.records) == 3

        # Cleanup
        for record in result.records:
            await client.delete_record(TEST_TABLE_NAME, record.id)

        print(f"  batch_create_records: Created {result.created_count} records")

    async def test_batch_update_records_success(self, client: AirtableClient) -> None:
        """Test batch updating records - MUST PASS."""
        # Create records first
        records_to_create = [
            {"Full Name": generate_unique_name(), "Email": generate_test_email()} for _ in range(3)
        ]
        create_result = await client.batch_create_records(
            table=TEST_TABLE_NAME,
            records=records_to_create,
        )

        # Prepare update payload
        updates = [
            {"id": record.id, "fields": {"Phone": "+1-555-000-0000"}}
            for record in create_result.records
        ]

        result = await client.batch_update_records(
            table=TEST_TABLE_NAME,
            records=updates,
        )

        assert isinstance(result, BatchResult)
        assert result.updated_count == 3

        # Cleanup
        for record in create_result.records:
            await client.delete_record(TEST_TABLE_NAME, record.id)

        print(f"  batch_update_records: Updated {result.updated_count} records")

    async def test_batch_delete_records_success(self, client: AirtableClient) -> None:
        """Test batch deleting records - MUST PASS."""
        # Create records first
        records_to_create = [
            {"Full Name": generate_unique_name(), "Email": generate_test_email()} for _ in range(3)
        ]
        create_result = await client.batch_create_records(
            table=TEST_TABLE_NAME,
            records=records_to_create,
        )

        # Delete them
        record_ids = [record.id for record in create_result.records]
        deleted_ids = await client.batch_delete_records(
            table=TEST_TABLE_NAME,
            record_ids=record_ids,
        )

        assert isinstance(deleted_ids, list)
        assert len(deleted_ids) == 3

        print(f"  batch_delete_records: Deleted {len(deleted_ids)} records")


# =============================================================================
# BULK OPERATIONS TESTS (auto-batching)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestBulkOperationsLive:
    """Live tests for bulk operations with auto-batching - MUST pass 100%."""

    async def test_bulk_create_records_success(self, client: AirtableClient) -> None:
        """Test bulk creating records (>10 records) - MUST PASS."""
        # Create 15 records to test auto-batching (max batch size is 10)
        records_to_create = [
            {"Full Name": generate_unique_name(), "Email": generate_test_email()} for _ in range(15)
        ]

        records = await client.bulk_create_records(
            table=TEST_TABLE_NAME,
            records=records_to_create,
        )

        assert isinstance(records, list)
        assert len(records) == 15

        # Cleanup
        record_ids = [record.id for record in records]
        await client.bulk_delete_records(TEST_TABLE_NAME, record_ids)

        print(f"  bulk_create_records: Created {len(records)} records with auto-batching")

    async def test_bulk_delete_records_success(self, client: AirtableClient) -> None:
        """Test bulk deleting records (>10 records) - MUST PASS."""
        # Create 12 records first
        records_to_create = [
            {"Full Name": generate_unique_name(), "Email": generate_test_email()} for _ in range(12)
        ]
        records = await client.bulk_create_records(
            table=TEST_TABLE_NAME,
            records=records_to_create,
        )

        # Delete all at once
        record_ids = [record.id for record in records]
        deleted_ids = await client.bulk_delete_records(
            table=TEST_TABLE_NAME,
            record_ids=record_ids,
        )

        assert isinstance(deleted_ids, list)
        assert len(deleted_ids) == 12

        print(f"  bulk_delete_records: Deleted {len(deleted_ids)} records with auto-batching")


# =============================================================================
# UPSERT OPERATIONS TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestUpsertOperationsLive:
    """Live tests for upsert operations - MUST pass 100%."""

    async def test_upsert_records_create_new(self, client: AirtableClient) -> None:
        """Test upserting new records - MUST PASS."""
        unique_email = generate_test_email()
        records = [{"Full Name": generate_unique_name(), "Email": unique_email}]

        result = await client.upsert_records(
            table=TEST_TABLE_NAME,
            records=records,
            fields_to_merge_on=["Email"],
        )

        assert isinstance(result, UpsertResult)
        assert len(result.records) == 1
        assert len(result.created_record_ids) == 1  # Should be a new record

        # Cleanup
        await client.delete_record(TEST_TABLE_NAME, result.records[0].id)

        print(f"  upsert_records (create): Created {len(result.created_record_ids)} new records")

    async def test_upsert_records_update_existing(
        self, client: AirtableClient, test_record: AirtableRecord
    ) -> None:
        """Test upserting to update existing records - MUST PASS."""
        # Upsert with same email should update existing record
        records = [
            {
                "Full Name": "Updated Name",
                "Email": test_record.fields["Email"],
                "Phone": "+1-999-999-9999",
            }
        ]

        result = await client.upsert_records(
            table=TEST_TABLE_NAME,
            records=records,
            fields_to_merge_on=["Email"],
        )

        assert isinstance(result, UpsertResult)
        assert len(result.records) == 1
        assert len(result.updated_record_ids) == 1  # Should be an update

        print(
            f"  upsert_records (update): Updated {len(result.updated_record_ids)} existing records"
        )


# =============================================================================
# SCHEMA INTROSPECTION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestSchemaIntrospectionLive:
    """Live tests for schema introspection - MUST pass 100%."""

    async def test_list_tables_success(self, client: AirtableClient) -> None:
        """Test listing tables in base - MUST PASS."""
        tables = await client.list_tables()

        assert isinstance(tables, list)
        assert len(tables) > 0
        for table in tables:
            assert isinstance(table, AirtableTable)
            assert table.id is not None
            assert table.name is not None

        print(f"  list_tables: Found {len(tables)} tables")


# =============================================================================
# HEALTH CHECK AND UTILITY TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestHealthAndUtilityLive:
    """Live tests for health check and utility methods - MUST pass 100%."""

    async def test_health_check_success(self, client: AirtableClient) -> None:
        """Test health check with real API - MUST PASS."""
        health = await client.health_check()

        assert isinstance(health, dict)
        assert health["name"] == "airtable"
        assert health["healthy"] is True
        assert health["api_version"] == "v0"

        print("  health_check: API is healthy")

    async def test_call_endpoint_list_records(self, client: AirtableClient) -> None:
        """Test future-proof call_endpoint for listing records - MUST PASS."""
        result = await client.call_endpoint(
            f"/{client.base_id}/{TEST_TABLE_NAME}",
            method="GET",
            params={"maxRecords": 5},
        )

        assert isinstance(result, dict)
        assert "records" in result

        print("  call_endpoint (GET /table): Future-proof method works")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestErrorHandlingLive:
    """Live tests for error handling - MUST pass 100%."""

    async def test_get_nonexistent_record_raises_error(self, client: AirtableClient) -> None:
        """Test getting non-existent record raises error - MUST PASS."""
        fake_id = "recNONEXISTENT123"

        # Note: Airtable returns 403 for invalid record IDs (not 404)
        with pytest.raises((AirtableNotFoundError, AirtableError)):
            await client.get_record(TEST_TABLE_NAME, fake_id)

        print("  error_handling: Non-existent record raises AirtableError")

    async def test_invalid_api_key_raises_error(self) -> None:
        """Test invalid API key raises authentication error - MUST PASS."""
        _, base_id = get_credentials()
        invalid_client = AirtableClient(
            api_key="pat_invalid_key_12345",  # pragma: allowlist secret
            base_id=base_id,
        )

        with pytest.raises(AirtableError):
            await invalid_client.list_records(TEST_TABLE_NAME)

        print("  error_handling: Invalid API key raises AirtableError")


# =============================================================================
# FIND RECORD TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestFindRecordLive:
    """Live tests for finding records - MUST pass 100%."""

    async def test_find_record_by_field_success(
        self, client: AirtableClient, test_record: AirtableRecord
    ) -> None:
        """Test finding a record by field value - MUST PASS."""
        record = await client.find_record_by_field(
            table=TEST_TABLE_NAME,
            field="Email",
            value=test_record.fields["Email"],
        )

        assert record is not None
        assert record.id == test_record.id

        print(f"  find_record_by_field: Found record {record.id}")

    async def test_find_record_by_field_not_found(self, client: AirtableClient) -> None:
        """Test finding a non-existent record returns None - MUST PASS."""
        record = await client.find_record_by_field(
            table=TEST_TABLE_NAME,
            field="Email",
            value="nonexistent@email.com",
        )

        assert record is None

        print("  find_record_by_field: Returns None for non-existent record")


# =============================================================================
# COMPREHENSIVE INTEGRATION TEST
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestComprehensiveIntegration:
    """Full integration test covering complete workflow - MUST pass 100%."""

    async def test_complete_record_lifecycle(self, client: AirtableClient) -> None:
        """Test complete record lifecycle: create, read, update, delete."""
        print("\n Starting complete record lifecycle test...")

        # 1. Create record
        name = generate_unique_name()
        email = generate_test_email()
        record = await client.create_record(
            table=TEST_TABLE_NAME,
            fields={
                "Full Name": name,
                "First Name": "Lifecycle",
                "Last Name": "Test",
                "Email": email,
            },
        )
        assert record.id is not None
        print(f"  1. Created record: {record.id}")

        # 2. Read record
        fetched = await client.get_record(TEST_TABLE_NAME, record.id)
        assert fetched.fields["Full Name"] == name
        print(f"  2. Read record: {fetched.id}")

        # 3. Update record
        updated = await client.update_record(
            table=TEST_TABLE_NAME,
            record_id=record.id,
            fields={"Phone": "+1-555-LIFECYCLE"},
        )
        assert updated.fields["Phone"] == "+1-555-LIFECYCLE"
        print(f"  3. Updated record: {updated.id}")

        # 4. Find record by email
        found = await client.find_record_by_field(
            table=TEST_TABLE_NAME,
            field="Email",
            value=email,
        )
        assert found is not None
        assert found.id == record.id
        print(f"  4. Found record by email: {found.id}")

        # 5. Delete record
        deleted = await client.delete_record(TEST_TABLE_NAME, record.id)
        assert deleted is True
        print(f"  5. Deleted record: {record.id}")

        print(" Complete record lifecycle: ALL STEPS PASSED")


# =============================================================================
# RUN ALL TESTS SUMMARY
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
async def test_all_endpoints_summary() -> None:
    """
    Summary test to verify all endpoint categories work.

    This test provides a final verification that all major
    endpoint categories are functional.
    """
    api_key, base_id = get_credentials()
    client = AirtableClient(api_key=api_key, base_id=base_id, timeout=60.0)

    print("\n" + "=" * 60)
    print("AIRTABLE API LIVE TEST SUMMARY")
    print("=" * 60)

    results: dict[str, bool] = {}

    # Test 1: Health Check
    try:
        health = await client.health_check()
        results["Health Check"] = health["healthy"]
    except Exception as e:
        results["Health Check"] = False
        print(f"  Health Check: {e}")

    # Test 2: List Tables
    try:
        tables = await client.list_tables()
        results["List Tables"] = len(tables) > 0
    except Exception as e:
        results["List Tables"] = False
        print(f"  List Tables: {e}")

    # Test 3: List Records
    try:
        result = await client.list_records(TEST_TABLE_NAME, max_records=1)
        results["List Records"] = isinstance(result, ListRecordsResult)
    except Exception as e:
        results["List Records"] = False
        print(f"  List Records: {e}")

    # Test 4: Future-Proof call_endpoint
    try:
        await client.call_endpoint(
            f"/{base_id}/{TEST_TABLE_NAME}", method="GET", params={"maxRecords": 1}
        )
        results["Future-Proof call_endpoint"] = True
    except Exception as e:
        results["Future-Proof call_endpoint"] = False
        print(f"  Future-Proof call_endpoint: {e}")

    # Print Summary
    print("\nResults:")
    all_passed = True
    for endpoint, passed in results.items():
        status = " PASS" if passed else " FAIL"
        print(f"  {endpoint}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    assert all_passed, "Some endpoints failed - see details above"
    print(" ALL ENDPOINTS PASSED 100%")
