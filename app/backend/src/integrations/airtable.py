"""
Airtable API integration client.

Provides database management capabilities for storing leads, contacts,
campaigns, and structured data. Central hub for the Smarter Team system.

API Documentation: https://airtable.com/developers/web/api/introduction
API Version: v0
Base URL: https://api.airtable.com/v0

Features:
- Record CRUD operations (create, read, update, delete)
- Batch operations (up to 10 records per request)
- Filtering with formulas
- Sorting and pagination
- Field management
- Upsert support (find or create/update)
- Attachment handling
- View-based queries

Rate Limits:
- 5 requests per second per base
- 429 response requires 30 second wait
- Pagination: max 100 records per page

Authentication:
- Bearer token via Personal Access Token or OAuth
- API key from Airtable account settings

Example:
    >>> from src.integrations.airtable import AirtableClient
    >>> client = AirtableClient(
    ...     api_key="your-api-key",  # pragma: allowlist secret
    ...     base_id="appXXXXXXXXXXXXXX"
    ... )
    >>> record = await client.create_record(
    ...     table="Leads",
    ...     fields={"Name": "John Doe", "Email": "john@example.com"}
    ... )
    >>> print(record.id)
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# Rate limiting: 5 requests per second per base
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_PERIOD = 1.0  # seconds
RATE_LIMIT_WAIT = 30  # seconds to wait on 429


class SortDirection(str, Enum):
    """Sort direction for record queries."""

    ASC = "asc"
    DESC = "desc"


class CellFormat(str, Enum):
    """Cell value format options."""

    JSON = "json"
    STRING = "string"


@dataclass
class AirtableRecord:
    """Record entity from Airtable API."""

    id: str
    fields: dict[str, Any]
    created_time: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    def get_field(self, name: str, default: Any = None) -> Any:
        """Get a field value by name with optional default."""
        return self.fields.get(name, default)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to fields."""
        return self.fields[key]

    def __contains__(self, key: str) -> bool:
        """Check if field exists."""
        return key in self.fields


@dataclass
class AirtableTable:
    """Table metadata from Airtable API."""

    id: str
    name: str
    primary_field_id: str | None = None
    description: str | None = None
    fields: list[dict[str, Any]] = field(default_factory=list)
    views: list[dict[str, Any]] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class ListRecordsResult:
    """Result from list records operation with pagination support."""

    records: list[AirtableRecord]
    offset: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def has_more(self) -> bool:
        """Check if there are more records to fetch."""
        return self.offset is not None


@dataclass
class BatchResult:
    """Result from batch create/update operations."""

    records: list[AirtableRecord]
    created_count: int = 0
    updated_count: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpsertResult:
    """Result from upsert operation."""

    records: list[AirtableRecord]
    created_records: list[AirtableRecord] = field(default_factory=list)
    updated_records: list[AirtableRecord] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def created_count(self) -> int:
        """Number of records created."""
        return len(self.created_records)

    @property
    def updated_count(self) -> int:
        """Number of records updated."""
        return len(self.updated_records)

    @property
    def created_record_ids(self) -> list[str]:
        """IDs of created records."""
        return [r.id for r in self.created_records]

    @property
    def updated_record_ids(self) -> list[str]:
        """IDs of updated records."""
        return [r.id for r in self.updated_records]


@dataclass
class SortConfig:
    """Sort configuration for queries."""

    field: str
    direction: SortDirection = SortDirection.ASC

    def to_dict(self) -> dict[str, str]:
        """Convert to API format."""
        return {"field": self.field, "direction": self.direction.value}


class AirtableError(IntegrationError):
    """Exception raised for Airtable API errors."""

    pass


class AirtableValidationError(AirtableError):
    """Exception raised for Airtable validation errors."""

    pass


class AirtableNotFoundError(AirtableError):
    """Exception raised when a record or table is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=404, **kwargs)


class AirtableClient(BaseIntegrationClient):
    """
    Async client for Airtable API v0.

    Provides comprehensive database management including record CRUD,
    batch operations, filtering, sorting, and pagination.

    Attributes:
        API_VERSION: Current API version (v0).
        BASE_URL: Base URL for API requests.
        MAX_BATCH_SIZE: Maximum records per batch operation (10).
        MAX_PAGE_SIZE: Maximum records per page (100).

    Note:
        - Rate limit: 5 requests per second per base
        - Bearer token authentication
        - Batch operations support up to 10 records
    """

    API_VERSION = "v0"
    BASE_URL = "https://api.airtable.com/v0"
    MAX_BATCH_SIZE = 10
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        api_key: str,
        base_id: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Airtable client.

        Args:
            api_key: Airtable API key (Personal Access Token).
            base_id: Airtable base ID (starts with 'app').
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="airtable",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            # Longer delay for rate limit handling
            retry_base_delay=2.0,
        )
        self.base_id = base_id
        self._last_request_time: float = 0.0
        self._request_count: int = 0
        logger.info(f"Initialized {self.name} client (API {self.API_VERSION}, base={base_id})")

    async def _rate_limit(self) -> None:
        """
        Enforce rate limiting (5 requests per second per base).

        This implements a simple token bucket algorithm to stay within limits.
        """
        current_time = asyncio.get_running_loop().time()
        elapsed = current_time - self._last_request_time

        if elapsed >= RATE_LIMIT_PERIOD:
            # Reset counter if a full period has passed
            self._request_count = 0
            self._last_request_time = current_time
        elif self._request_count >= RATE_LIMIT_REQUESTS:
            # Wait for the remainder of the period
            wait_time = RATE_LIMIT_PERIOD - elapsed
            logger.debug(f"[{self.name}] Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self._request_count = 0
            self._last_request_time = asyncio.get_running_loop().time()

        self._request_count += 1

    async def _request_with_rate_limit(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make request with rate limiting applied.

        Args:
            method: HTTP method.
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.

        Raises:
            AirtableError: If request fails.
        """
        await self._rate_limit()

        try:
            return await self._request_with_retry(method, endpoint, **kwargs)
        except RateLimitError:
            # Airtable 429 requires 30 second wait
            logger.warning(f"[{self.name}] Rate limit hit, waiting {RATE_LIMIT_WAIT}s")
            await asyncio.sleep(RATE_LIMIT_WAIT)
            # Retry once after waiting
            return await self._request_with_retry(method, endpoint, **kwargs)
        except IntegrationError as e:
            raise AirtableError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _build_table_url(self, table: str) -> str:
        """Build URL for table operations."""
        return f"/{self.base_id}/{table}"

    # -------------------------------------------------------------------------
    # Record Operations
    # -------------------------------------------------------------------------

    async def create_record(
        self,
        table: str,
        fields: dict[str, Any],
        typecast: bool = False,
    ) -> AirtableRecord:
        """
        Create a single record in a table.

        Args:
            table: Table name or ID.
            fields: Field values for the record.
            typecast: Auto-convert field types (e.g., string to number).

        Returns:
            Created AirtableRecord.

        Raises:
            AirtableError: If creation fails.
            AirtableValidationError: If field validation fails.

        Example:
            >>> record = await client.create_record(
            ...     table="Leads",
            ...     fields={"Name": "John Doe", "Email": "john@example.com"}
            ... )
        """
        payload: dict[str, Any] = {"fields": fields}
        if typecast:
            payload["typecast"] = True

        try:
            response = await self._request_with_rate_limit(
                "POST",
                self._build_table_url(table),
                json=payload,
            )
            return self._parse_record(response)

        except AirtableError as e:
            if e.status_code == 422:
                raise AirtableValidationError(
                    message=f"Validation error: {e.message}",
                    status_code=422,
                    response_data=e.response_data,
                ) from e
            logger.error(
                f"[{self.name}] create_record failed: {e}",
                extra={"table": table},
            )
            raise

    async def get_record(
        self,
        table: str,
        record_id: str,
        cell_format: CellFormat | None = None,
        return_fields_by_field_id: bool = False,
    ) -> AirtableRecord:
        """
        Get a single record by ID.

        Args:
            table: Table name or ID.
            record_id: Record ID (starts with 'rec').
            cell_format: Output format for cell values.
            return_fields_by_field_id: Key fields by ID instead of name.

        Returns:
            AirtableRecord with full details.

        Raises:
            AirtableNotFoundError: If record not found.
            AirtableError: If request fails.
        """
        params: dict[str, Any] = {}
        if cell_format:
            params["cellFormat"] = cell_format.value
        if return_fields_by_field_id:
            params["returnFieldsByFieldId"] = "true"

        try:
            response = await self._request_with_rate_limit(
                "GET",
                f"{self._build_table_url(table)}/{record_id}",
                params=params if params else None,
            )
            return self._parse_record(response)

        except AirtableError as e:
            if e.status_code == 404:
                raise AirtableNotFoundError(
                    message=f"Record not found: {record_id}",
                    response_data=e.response_data,
                ) from e
            logger.error(
                f"[{self.name}] get_record failed: {e}",
                extra={"table": table, "record_id": record_id},
            )
            raise

    async def update_record(
        self,
        table: str,
        record_id: str,
        fields: dict[str, Any],
        typecast: bool = False,
        destructive: bool = False,
    ) -> AirtableRecord:
        """
        Update a record (PATCH for partial, PUT for full replacement).

        Args:
            table: Table name or ID.
            record_id: Record ID to update.
            fields: Field values to update.
            typecast: Auto-convert field types.
            destructive: If True, use PUT (clears unspecified fields).

        Returns:
            Updated AirtableRecord.

        Raises:
            AirtableNotFoundError: If record not found.
            AirtableError: If update fails.
        """
        payload: dict[str, Any] = {"fields": fields}
        if typecast:
            payload["typecast"] = True

        method = "PUT" if destructive else "PATCH"

        try:
            response = await self._request_with_rate_limit(
                method,
                f"{self._build_table_url(table)}/{record_id}",
                json=payload,
            )
            return self._parse_record(response)

        except AirtableError as e:
            if e.status_code == 404:
                raise AirtableNotFoundError(
                    message=f"Record not found: {record_id}",
                    response_data=e.response_data,
                ) from e
            logger.error(
                f"[{self.name}] update_record failed: {e}",
                extra={"table": table, "record_id": record_id},
            )
            raise

    async def delete_record(
        self,
        table: str,
        record_id: str,
    ) -> bool:
        """
        Delete a single record.

        Args:
            table: Table name or ID.
            record_id: Record ID to delete.

        Returns:
            True if deletion was successful.

        Raises:
            AirtableNotFoundError: If record not found.
            AirtableError: If deletion fails.
        """
        try:
            response = await self._request_with_rate_limit(
                "DELETE",
                f"{self._build_table_url(table)}/{record_id}",
            )
            deleted: bool = bool(response.get("deleted", False))
            if deleted:
                logger.info(f"[{self.name}] Deleted record {record_id}")
            return deleted

        except AirtableError as e:
            if e.status_code == 404:
                raise AirtableNotFoundError(
                    message=f"Record not found: {record_id}",
                    response_data=e.response_data,
                ) from e
            logger.error(
                f"[{self.name}] delete_record failed: {e}",
                extra={"table": table, "record_id": record_id},
            )
            raise

    async def list_records(
        self,
        table: str,
        view: str | None = None,
        fields: list[str] | None = None,
        filter_by_formula: str | None = None,
        sort: list[SortConfig] | None = None,
        max_records: int | None = None,
        page_size: int | None = None,
        offset: str | None = None,
        cell_format: CellFormat | None = None,
        return_fields_by_field_id: bool = False,
    ) -> ListRecordsResult:
        """
        List records with filtering, sorting, and pagination.

        Args:
            table: Table name or ID.
            view: View name or ID to filter by.
            fields: Subset of field names to return.
            filter_by_formula: Airtable formula for filtering.
            sort: List of sort configurations.
            max_records: Maximum total records to return.
            page_size: Records per page (max 100).
            offset: Pagination token from previous response.
            cell_format: Output format for cell values.
            return_fields_by_field_id: Key fields by ID instead of name.

        Returns:
            ListRecordsResult with records and pagination offset.

        Raises:
            AirtableError: If listing fails.

        Example:
            >>> result = await client.list_records(
            ...     table="Leads",
            ...     filter_by_formula="{Status} = 'active'",
            ...     sort=[SortConfig(field="Created", direction=SortDirection.DESC)],
            ...     page_size=50
            ... )
            >>> for record in result.records:
            ...     print(record.fields["Name"])
        """
        params: dict[str, Any] = {}

        if view:
            params["view"] = view
        if fields:
            params["fields[]"] = fields
        if filter_by_formula:
            params["filterByFormula"] = filter_by_formula
        if sort:
            for i, s in enumerate(sort):
                params[f"sort[{i}][field]"] = s.field
                params[f"sort[{i}][direction]"] = s.direction.value
        if max_records:
            params["maxRecords"] = max_records
        if page_size:
            params["pageSize"] = min(page_size, self.MAX_PAGE_SIZE)
        if offset:
            params["offset"] = offset
        if cell_format:
            params["cellFormat"] = cell_format.value
        if return_fields_by_field_id:
            params["returnFieldsByFieldId"] = "true"

        try:
            response = await self._request_with_rate_limit(
                "GET",
                self._build_table_url(table),
                params=params if params else None,
            )

            records_data = response.get("records", [])
            records = [self._parse_record(r) for r in records_data]

            return ListRecordsResult(
                records=records,
                offset=response.get("offset"),
                raw_response=response,
            )

        except AirtableError:
            logger.error(
                f"[{self.name}] list_records failed",
                extra={"table": table},
            )
            raise

    async def list_all_records(
        self,
        table: str,
        view: str | None = None,
        fields: list[str] | None = None,
        filter_by_formula: str | None = None,
        sort: list[SortConfig] | None = None,
        max_records: int | None = None,
    ) -> list[AirtableRecord]:
        """
        List all records with automatic pagination.

        Convenience method that handles pagination automatically.

        Args:
            table: Table name or ID.
            view: View name or ID to filter by.
            fields: Subset of field names to return.
            filter_by_formula: Airtable formula for filtering.
            sort: List of sort configurations.
            max_records: Maximum total records to return.

        Returns:
            List of all matching AirtableRecords.

        Raises:
            AirtableError: If listing fails.
        """
        all_records: list[AirtableRecord] = []
        offset: str | None = None

        while True:
            result = await self.list_records(
                table=table,
                view=view,
                fields=fields,
                filter_by_formula=filter_by_formula,
                sort=sort,
                max_records=max_records,
                page_size=self.MAX_PAGE_SIZE,
                offset=offset,
            )

            all_records.extend(result.records)
            offset = result.offset

            # Check if we've reached the limit or no more pages
            if not offset:
                break
            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break

        return all_records

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    async def batch_create_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        typecast: bool = False,
    ) -> BatchResult:
        """
        Create multiple records in a single request (max 10).

        Args:
            table: Table name or ID.
            records: List of field dictionaries (max 10).
            typecast: Auto-convert field types.

        Returns:
            BatchResult with created records.

        Raises:
            ValueError: If more than 10 records provided.
            AirtableError: If creation fails.

        Example:
            >>> result = await client.batch_create_records(
            ...     table="Leads",
            ...     records=[
            ...         {"Name": "John", "Email": "john@example.com"},
            ...         {"Name": "Jane", "Email": "jane@example.com"},
            ...     ]
            ... )
        """
        if len(records) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} records per batch operation")

        payload: dict[str, Any] = {
            "records": [{"fields": r} for r in records],
        }
        if typecast:
            payload["typecast"] = True

        try:
            response = await self._request_with_rate_limit(
                "POST",
                self._build_table_url(table),
                json=payload,
            )

            created_records = [self._parse_record(r) for r in response.get("records", [])]

            return BatchResult(
                records=created_records,
                created_count=len(created_records),
                raw_response=response,
            )

        except AirtableError:
            logger.error(
                f"[{self.name}] batch_create_records failed",
                extra={"table": table, "count": len(records)},
            )
            raise

    async def batch_update_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        typecast: bool = False,
        destructive: bool = False,
    ) -> BatchResult:
        """
        Update multiple records in a single request (max 10).

        Args:
            table: Table name or ID.
            records: List of dicts with 'id' and 'fields' keys.
            typecast: Auto-convert field types.
            destructive: If True, use PUT (clears unspecified fields).

        Returns:
            BatchResult with updated records.

        Raises:
            ValueError: If more than 10 records provided.
            AirtableError: If update fails.

        Example:
            >>> result = await client.batch_update_records(
            ...     table="Leads",
            ...     records=[
            ...         {"id": "recXXX", "fields": {"Status": "contacted"}},
            ...         {"id": "recYYY", "fields": {"Status": "qualified"}},
            ...     ]
            ... )
        """
        if len(records) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} records per batch operation")

        payload: dict[str, Any] = {"records": records}
        if typecast:
            payload["typecast"] = True

        method = "PUT" if destructive else "PATCH"

        try:
            response = await self._request_with_rate_limit(
                method,
                self._build_table_url(table),
                json=payload,
            )

            updated_records = [self._parse_record(r) for r in response.get("records", [])]

            return BatchResult(
                records=updated_records,
                updated_count=len(updated_records),
                raw_response=response,
            )

        except AirtableError:
            logger.error(
                f"[{self.name}] batch_update_records failed",
                extra={"table": table, "count": len(records)},
            )
            raise

    async def batch_delete_records(
        self,
        table: str,
        record_ids: list[str],
    ) -> list[str]:
        """
        Delete multiple records in a single request (max 10).

        Args:
            table: Table name or ID.
            record_ids: List of record IDs to delete.

        Returns:
            List of deleted record IDs.

        Raises:
            ValueError: If more than 10 records provided.
            AirtableError: If deletion fails.
        """
        if len(record_ids) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} records per batch operation")

        # Airtable expects records as repeated query params
        params = {"records[]": record_ids}

        try:
            response = await self._request_with_rate_limit(
                "DELETE",
                self._build_table_url(table),
                params=params,
            )

            deleted_ids = [r.get("id") for r in response.get("records", []) if r.get("deleted")]
            logger.info(f"[{self.name}] Batch deleted {len(deleted_ids)} records")
            return deleted_ids

        except AirtableError:
            logger.error(
                f"[{self.name}] batch_delete_records failed",
                extra={"table": table, "count": len(record_ids)},
            )
            raise

    async def upsert_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        fields_to_merge_on: list[str],
        typecast: bool = False,
    ) -> UpsertResult:
        """
        Upsert (find and update, or create) records.

        Uses performUpsert to find existing records by specified fields
        and update them, or create new records if not found.

        Args:
            table: Table name or ID.
            records: List of field dictionaries (max 10).
            fields_to_merge_on: Fields to match for finding existing records.
            typecast: Auto-convert field types.

        Returns:
            UpsertResult with created and updated records.

        Raises:
            ValueError: If more than 10 records provided.
            AirtableError: If upsert fails.

        Example:
            >>> result = await client.upsert_records(
            ...     table="Contacts",
            ...     records=[
            ...         {"Email": "john@example.com", "Name": "John Doe"},
            ...     ],
            ...     fields_to_merge_on=["Email"]
            ... )
            >>> print(f"Created: {result.created_count}, Updated: {result.updated_count}")
        """
        if len(records) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} records per batch operation")

        payload: dict[str, Any] = {
            "records": [{"fields": r} for r in records],
            "performUpsert": {
                "fieldsToMergeOn": fields_to_merge_on,
            },
        }
        if typecast:
            payload["typecast"] = True

        try:
            response = await self._request_with_rate_limit(
                "PATCH",
                self._build_table_url(table),
                json=payload,
            )

            all_records = [self._parse_record(r) for r in response.get("records", [])]

            # Parse created vs updated records
            created_ids = set(response.get("createdRecords", []))
            updated_ids = set(response.get("updatedRecords", []))

            created_records = [r for r in all_records if r.id in created_ids]
            updated_records = [r for r in all_records if r.id in updated_ids]

            return UpsertResult(
                records=all_records,
                created_records=created_records,
                updated_records=updated_records,
                raw_response=response,
            )

        except AirtableError:
            logger.error(
                f"[{self.name}] upsert_records failed",
                extra={"table": table, "count": len(records)},
            )
            raise

    # -------------------------------------------------------------------------
    # Bulk Operations (handles batching automatically)
    # -------------------------------------------------------------------------

    async def bulk_create_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        typecast: bool = False,
    ) -> list[AirtableRecord]:
        """
        Create many records with automatic batching.

        Handles batching automatically for large record sets.

        Args:
            table: Table name or ID.
            records: List of field dictionaries (any size).
            typecast: Auto-convert field types.

        Returns:
            List of all created AirtableRecords.

        Raises:
            AirtableError: If creation fails.
        """
        all_created: list[AirtableRecord] = []

        # Process in batches of MAX_BATCH_SIZE
        for i in range(0, len(records), self.MAX_BATCH_SIZE):
            batch = records[i : i + self.MAX_BATCH_SIZE]
            result = await self.batch_create_records(
                table=table,
                records=batch,
                typecast=typecast,
            )
            all_created.extend(result.records)

        logger.info(f"[{self.name}] Bulk created {len(all_created)} records in {table}")
        return all_created

    async def bulk_update_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        typecast: bool = False,
        destructive: bool = False,
    ) -> list[AirtableRecord]:
        """
        Update many records with automatic batching.

        Handles batching automatically for large record sets.

        Args:
            table: Table name or ID.
            records: List of dicts with 'id' and 'fields' keys.
            typecast: Auto-convert field types.
            destructive: If True, use PUT (clears unspecified fields).

        Returns:
            List of all updated AirtableRecords.

        Raises:
            AirtableError: If update fails.
        """
        all_updated: list[AirtableRecord] = []

        # Process in batches of MAX_BATCH_SIZE
        for i in range(0, len(records), self.MAX_BATCH_SIZE):
            batch = records[i : i + self.MAX_BATCH_SIZE]
            result = await self.batch_update_records(
                table=table,
                records=batch,
                typecast=typecast,
                destructive=destructive,
            )
            all_updated.extend(result.records)

        logger.info(f"[{self.name}] Bulk updated {len(all_updated)} records in {table}")
        return all_updated

    async def bulk_delete_records(
        self,
        table: str,
        record_ids: list[str],
    ) -> list[str]:
        """
        Delete many records with automatic batching.

        Handles batching automatically for large record sets.

        Args:
            table: Table name or ID.
            record_ids: List of record IDs to delete.

        Returns:
            List of all deleted record IDs.

        Raises:
            AirtableError: If deletion fails.
        """
        all_deleted: list[str] = []

        # Process in batches of MAX_BATCH_SIZE
        for i in range(0, len(record_ids), self.MAX_BATCH_SIZE):
            batch = record_ids[i : i + self.MAX_BATCH_SIZE]
            deleted = await self.batch_delete_records(
                table=table,
                record_ids=batch,
            )
            all_deleted.extend(deleted)

        logger.info(f"[{self.name}] Bulk deleted {len(all_deleted)} records from {table}")
        return all_deleted

    async def bulk_upsert_records(
        self,
        table: str,
        records: list[dict[str, Any]],
        fields_to_merge_on: list[str],
        typecast: bool = False,
    ) -> UpsertResult:
        """
        Upsert many records with automatic batching.

        Handles batching automatically for large record sets.

        Args:
            table: Table name or ID.
            records: List of field dictionaries (any size).
            fields_to_merge_on: Fields to match for finding existing records.
            typecast: Auto-convert field types.

        Returns:
            Combined UpsertResult with all created and updated records.

        Raises:
            AirtableError: If upsert fails.
        """
        all_records: list[AirtableRecord] = []
        all_created: list[AirtableRecord] = []
        all_updated: list[AirtableRecord] = []

        # Process in batches of MAX_BATCH_SIZE
        for i in range(0, len(records), self.MAX_BATCH_SIZE):
            batch = records[i : i + self.MAX_BATCH_SIZE]
            result = await self.upsert_records(
                table=table,
                records=batch,
                fields_to_merge_on=fields_to_merge_on,
                typecast=typecast,
            )
            all_records.extend(result.records)
            all_created.extend(result.created_records)
            all_updated.extend(result.updated_records)

        logger.info(
            f"[{self.name}] Bulk upserted {len(all_records)} records "
            f"(created: {len(all_created)}, updated: {len(all_updated)})"
        )

        return UpsertResult(
            records=all_records,
            created_records=all_created,
            updated_records=all_updated,
        )

    # -------------------------------------------------------------------------
    # Query Helpers
    # -------------------------------------------------------------------------

    async def find_record_by_field(
        self,
        table: str,
        field: str,
        value: Any,
    ) -> AirtableRecord | None:
        """
        Find a single record by field value.

        Args:
            table: Table name or ID.
            field: Field name to search.
            value: Value to match.

        Returns:
            AirtableRecord if found, None otherwise.

        Example:
            >>> lead = await client.find_record_by_field(
            ...     table="Leads",
            ...     field="Email",
            ...     value="john@example.com"
            ... )
        """
        # Escape single quotes in value
        escaped_value = str(value).replace("'", "\\'")
        formula = f"{{{field}}} = '{escaped_value}'"

        result = await self.list_records(
            table=table,
            filter_by_formula=formula,
            page_size=1,
        )

        return result.records[0] if result.records else None

    async def find_records_by_field(
        self,
        table: str,
        field: str,
        value: Any,
    ) -> list[AirtableRecord]:
        """
        Find all records matching a field value.

        Args:
            table: Table name or ID.
            field: Field name to search.
            value: Value to match.

        Returns:
            List of matching AirtableRecords.
        """
        # Escape single quotes in value
        escaped_value = str(value).replace("'", "\\'")
        formula = f"{{{field}}} = '{escaped_value}'"

        return await self.list_all_records(
            table=table,
            filter_by_formula=formula,
        )

    # -------------------------------------------------------------------------
    # Table Metadata (Meta API)
    # -------------------------------------------------------------------------

    async def list_tables(self) -> list[AirtableTable]:
        """
        List all tables in the base.

        Uses the Meta API to retrieve table metadata.

        Returns:
            List of AirtableTable objects.

        Raises:
            AirtableError: If listing fails.
        """
        try:
            # Meta API endpoint
            response = await self._request_with_rate_limit(
                "GET",
                f"/meta/bases/{self.base_id}/tables",
            )

            tables_data = response.get("tables", [])
            return [self._parse_table(t) for t in tables_data]

        except AirtableError:
            logger.error(f"[{self.name}] list_tables failed")
            raise

    async def get_table(self, table_id: str) -> AirtableTable | None:
        """
        Get table metadata by ID.

        Args:
            table_id: Table ID (starts with 'tbl').

        Returns:
            AirtableTable if found, None otherwise.
        """
        tables = await self.list_tables()
        for table in tables:
            if table.id == table_id:
                return table
        return None

    # -------------------------------------------------------------------------
    # Health Check & Utility
    # -------------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """
        Check Airtable API connectivity.

        Returns:
            Health check status with base accessibility.
        """
        try:
            # Try to list tables to verify connectivity
            tables = await self.list_tables()
            return {
                "name": self.name,
                "healthy": True,
                "api_version": self.API_VERSION,
                "base_id": self.base_id,
                "tables_count": len(tables),
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
                "api_version": self.API_VERSION,
                "base_id": self.base_id,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling new endpoints that may be released
        in the future without requiring code changes.

        Args:
            endpoint: Endpoint path (e.g., "/meta/bases/{base_id}/tables").
            method: HTTP method (default: "GET").
            **kwargs: Request parameters (json, params, etc.).

        Returns:
            API response as dictionary.

        Raises:
            AirtableError: If API request fails.

        Example:
            >>> result = await client.call_endpoint(
            ...     "/meta/bases/appXXX/tables",
            ...     method="GET"
            ... )
        """
        try:
            return await self._request_with_rate_limit(method, endpoint, **kwargs)
        except IntegrationError as e:
            raise AirtableError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _parse_record(self, data: dict[str, Any]) -> AirtableRecord:
        """Parse raw API response into AirtableRecord dataclass."""
        created_time = None
        if data.get("createdTime"):
            with contextlib.suppress(ValueError, AttributeError):
                created_time = datetime.fromisoformat(data["createdTime"].replace("Z", "+00:00"))

        return AirtableRecord(
            id=data.get("id", ""),
            fields=data.get("fields", {}),
            created_time=created_time,
            raw_response=data,
        )

    def _parse_table(self, data: dict[str, Any]) -> AirtableTable:
        """Parse raw API response into AirtableTable dataclass."""
        return AirtableTable(
            id=data.get("id", ""),
            name=data.get("name", ""),
            primary_field_id=data.get("primaryFieldId"),
            description=data.get("description"),
            fields=data.get("fields", []),
            views=data.get("views", []),
            raw_response=data,
        )
