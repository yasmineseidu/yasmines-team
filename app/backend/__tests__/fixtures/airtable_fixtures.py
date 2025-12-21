"""Test fixtures for Airtable integration tests."""

from typing import Any

# Sample API responses for mocking

SAMPLE_RECORD_RESPONSE: dict[str, Any] = {
    "id": "recABC123",
    "createdTime": "2025-01-15T10:30:00.000Z",
    "fields": {
        "Name": "John Doe",
        "Email": "john@example.com",
        "Company": "Acme Corp",
        "Status": "active",
        "Score": 85,
    },
}

SAMPLE_RECORD_RESPONSE_2: dict[str, Any] = {
    "id": "recDEF456",
    "createdTime": "2025-01-15T11:00:00.000Z",
    "fields": {
        "Name": "Jane Smith",
        "Email": "jane@example.com",
        "Company": "Tech Inc",
        "Status": "contacted",
        "Score": 92,
    },
}

SAMPLE_LIST_RECORDS_RESPONSE: dict[str, Any] = {
    "records": [
        SAMPLE_RECORD_RESPONSE,
        SAMPLE_RECORD_RESPONSE_2,
    ],
}

SAMPLE_LIST_RECORDS_WITH_OFFSET_RESPONSE: dict[str, Any] = {
    "records": [
        SAMPLE_RECORD_RESPONSE,
    ],
    "offset": "itrXXXXXXXXXXXXXX",
}

SAMPLE_BATCH_CREATE_RESPONSE: dict[str, Any] = {
    "records": [
        SAMPLE_RECORD_RESPONSE,
        SAMPLE_RECORD_RESPONSE_2,
    ],
}

SAMPLE_BATCH_UPDATE_RESPONSE: dict[str, Any] = {
    "records": [
        {
            "id": "recABC123",
            "createdTime": "2025-01-15T10:30:00.000Z",
            "fields": {
                "Name": "John Doe",
                "Email": "john@example.com",
                "Status": "qualified",
            },
        },
    ],
}

SAMPLE_DELETE_RESPONSE: dict[str, Any] = {
    "id": "recABC123",
    "deleted": True,
}

SAMPLE_BATCH_DELETE_RESPONSE: dict[str, Any] = {
    "records": [
        {"id": "recABC123", "deleted": True},
        {"id": "recDEF456", "deleted": True},
    ],
}

SAMPLE_UPSERT_RESPONSE: dict[str, Any] = {
    "records": [
        SAMPLE_RECORD_RESPONSE,
        SAMPLE_RECORD_RESPONSE_2,
    ],
    "createdRecords": ["recDEF456"],
    "updatedRecords": ["recABC123"],
}

SAMPLE_TABLE_RESPONSE: dict[str, Any] = {
    "id": "tblXXXXXXXXXXXXXX",
    "name": "Leads",
    "primaryFieldId": "fldXXXXXXXXXXXXXX",
    "description": "Lead tracking table",
    "fields": [
        {"id": "fld001", "name": "Name", "type": "singleLineText"},
        {"id": "fld002", "name": "Email", "type": "email"},
        {"id": "fld003", "name": "Status", "type": "singleSelect"},
    ],
    "views": [
        {"id": "viw001", "name": "Grid view", "type": "grid"},
        {"id": "viw002", "name": "Active Leads", "type": "grid"},
    ],
}

SAMPLE_LIST_TABLES_RESPONSE: dict[str, Any] = {
    "tables": [
        SAMPLE_TABLE_RESPONSE,
        {
            "id": "tblYYYYYYYYYYYYYY",
            "name": "Contacts",
            "primaryFieldId": "fldYYYYYYYYYYYYYY",
            "description": "Contact information",
            "fields": [
                {"id": "fld004", "name": "First Name", "type": "singleLineText"},
                {"id": "fld005", "name": "Last Name", "type": "singleLineText"},
                {"id": "fld006", "name": "Email", "type": "email"},
            ],
            "views": [
                {"id": "viw003", "name": "Grid view", "type": "grid"},
            ],
        },
    ],
}

SAMPLE_ERROR_RESPONSE: dict[str, Any] = {
    "error": {
        "type": "INVALID_REQUEST_UNKNOWN",
        "message": "Could not find record recNONEXISTENT",
    },
}

SAMPLE_VALIDATION_ERROR_RESPONSE: dict[str, Any] = {
    "error": {
        "type": "INVALID_VALUE_FOR_COLUMN",
        "message": "Field 'Email' is not a valid email address",
    },
}

SAMPLE_RATE_LIMIT_ERROR_RESPONSE: dict[str, Any] = {
    "error": {
        "type": "RATE_LIMIT_REACHED",
        "message": "You have exceeded the rate limit. Try again in 30 seconds.",
    },
}

# Sample input data for tests

SAMPLE_LEAD_FIELDS: dict[str, Any] = {
    "Name": "John Doe",
    "Email": "john@example.com",
    "Company": "Acme Corp",
    "Status": "new",
    "Score": 75,
}

SAMPLE_CONTACT_FIELDS: dict[str, Any] = {
    "First Name": "Jane",
    "Last Name": "Smith",
    "Email": "jane@example.com",
    "Title": "CEO",
    "LinkedIn URL": "https://linkedin.com/in/janesmith",
}

SAMPLE_CAMPAIGN_FIELDS: dict[str, Any] = {
    "Name": "Q1 Outreach",
    "Type": "Email",
    "Status": "Planning",
    "Start Date": "2025-02-01",
    "Leads Target": 500,
}

SAMPLE_BATCH_RECORDS: list[dict[str, Any]] = [
    {"Name": "Lead 1", "Email": "lead1@example.com"},
    {"Name": "Lead 2", "Email": "lead2@example.com"},
    {"Name": "Lead 3", "Email": "lead3@example.com"},
]

SAMPLE_UPDATE_RECORDS: list[dict[str, Any]] = [
    {"id": "recABC123", "fields": {"Status": "contacted"}},
    {"id": "recDEF456", "fields": {"Status": "qualified"}},
]

# Test configuration

TEST_API_KEY = "pat_test_api_key_123"  # pragma: allowlist secret
TEST_BASE_ID = "appTEST123456789"
TEST_TABLE_NAME = "Leads"
TEST_RECORD_ID = "recABC123"
