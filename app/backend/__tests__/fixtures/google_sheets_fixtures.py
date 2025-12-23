"""Fixtures for Google Sheets API integration tests."""

# Mock service account credentials for testing (NOT REAL - for unit tests only)
MOCK_SERVICE_ACCOUNT_CREDENTIALS = {  # pragma: allowlist secret
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "key-123",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA2mKq...\n-----END RSA PRIVATE KEY-----\n",  # pragma: allowlist secret
    "client_email": "test@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project-123.iam.gserviceaccount.com",
}

# Sample API responses (mock data for testing)
SAMPLE_RESPONSES = {
    "spreadsheet": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",  # pragma: allowlist secret
        "properties": {
            "title": "Test Spreadsheet",
            "locale": "en_US",
            "timeZone": "America/New_York",
        },
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
        "sheets": [
            {
                "properties": {
                    "sheetId": 0,
                    "title": "Sheet1",
                    "index": 0,
                    "sheetType": "GRID",
                    "gridProperties": {
                        "rowCount": 1000,
                        "columnCount": 26,
                    },
                }
            },
            {
                "properties": {
                    "sheetId": 123456,
                    "title": "Data",
                    "index": 1,
                    "sheetType": "GRID",
                    "gridProperties": {
                        "rowCount": 500,
                        "columnCount": 10,
                    },
                }
            },
        ],
    },
    "spreadsheet_minimal": {
        "spreadsheetId": "abc123",
        "properties": {
            "title": "Minimal Spreadsheet",
        },
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/abc123/edit",
        "sheets": [
            {
                "properties": {
                    "sheetId": 0,
                    "title": "Sheet1",
                    "index": 0,
                }
            }
        ],
    },
    "value_range": {
        "range": "Sheet1!A1:D5",
        "majorDimension": "ROWS",
        "values": [
            ["Name", "Age", "City", "Country"],
            ["Alice", "30", "New York", "USA"],
            ["Bob", "25", "London", "UK"],
            ["Charlie", "35", "Paris", "France"],
            ["Diana", "28", "Tokyo", "Japan"],
        ],
    },
    "value_range_empty": {
        "range": "Sheet1!A1:D5",
        "majorDimension": "ROWS",
    },
    "update_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "updatedRange": "Sheet1!A1:D5",
        "updatedRows": 5,
        "updatedColumns": 4,
        "updatedCells": 20,
    },
    "append_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "tableRange": "Sheet1!A1:D5",
        "updates": {
            "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "updatedRange": "Sheet1!A6:D6",
            "updatedRows": 1,
            "updatedColumns": 4,
            "updatedCells": 4,
        },
    },
    "clear_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "clearedRange": "Sheet1!A1:D5",
    },
    "batch_get_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "valueRanges": [
            {
                "range": "Sheet1!A1:B2",
                "majorDimension": "ROWS",
                "values": [["A1", "B1"], ["A2", "B2"]],
            },
            {
                "range": "Sheet1!C1:D2",
                "majorDimension": "ROWS",
                "values": [["C1", "D1"], ["C2", "D2"]],
            },
        ],
    },
    "batch_update_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "totalUpdatedRows": 4,
        "totalUpdatedColumns": 4,
        "totalUpdatedCells": 8,
        "totalUpdatedSheets": 1,
        "responses": [
            {
                "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "updatedRange": "Sheet1!A1:B2",
                "updatedRows": 2,
                "updatedColumns": 2,
                "updatedCells": 4,
            },
            {
                "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "updatedRange": "Sheet1!C1:D2",
                "updatedRows": 2,
                "updatedColumns": 2,
                "updatedCells": 4,
            },
        ],
    },
    "batch_clear_values_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "clearedRanges": ["Sheet1!A1:B2", "Sheet1!C1:D2"],
    },
    "batch_update_spreadsheet_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "replies": [
            {
                "addSheet": {
                    "properties": {
                        "sheetId": 789,
                        "title": "New Sheet",
                        "index": 2,
                        "sheetType": "GRID",
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 26,
                        },
                    }
                }
            }
        ],
    },
    "add_sheet_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "replies": [
            {
                "addSheet": {
                    "properties": {
                        "sheetId": 999,
                        "title": "Added Sheet",
                        "index": 1,
                        "sheetType": "GRID",
                    }
                }
            }
        ],
    },
    "duplicate_sheet_response": {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "replies": [
            {
                "duplicateSheet": {
                    "properties": {
                        "sheetId": 888,
                        "title": "Sheet1 Copy",
                        "index": 1,
                        "sheetType": "GRID",
                    }
                }
            }
        ],
    },
    "copy_sheet_response": {
        "sheetId": 777,
        "title": "Copied Sheet",
        "index": 0,
        "sheetType": "GRID",
        "gridProperties": {
            "rowCount": 1000,
            "columnCount": 26,
        },
    },
}

# Error responses
ERROR_RESPONSES = {
    "not_found": {
        "error": {
            "code": 404,
            "message": "Requested entity was not found.",
            "status": "NOT_FOUND",
        }
    },
    "permission_denied": {
        "error": {
            "code": 403,
            "message": "The caller does not have permission",
            "status": "PERMISSION_DENIED",
        }
    },
    "quota_exceeded": {
        "error": {
            "code": 403,
            "message": "Quota exceeded for quota metric 'Read requests'",
            "status": "RESOURCE_EXHAUSTED",
        }
    },
    "rate_limited": {
        "error": {
            "code": 429,
            "message": "Rate Limit Exceeded",
            "status": "RESOURCE_EXHAUSTED",
        }
    },
    "unauthorized": {
        "error": {
            "code": 401,
            "message": "Request had invalid authentication credentials",
            "status": "UNAUTHENTICATED",
        }
    },
    "invalid_argument": {
        "error": {
            "code": 400,
            "message": "Unable to parse range: InvalidRange!",
            "status": "INVALID_ARGUMENT",
        }
    },
}

# Test data for creating/updating values
TEST_VALUES = {
    "simple": [["A", "B", "C"], [1, 2, 3], [4, 5, 6]],
    "headers": [
        ["ID", "Name", "Email", "Created"],
        [1, "Alice", "alice@example.com", "2024-01-01"],
        [2, "Bob", "bob@example.com", "2024-01-02"],
    ],
    "mixed_types": [
        ["String", "Number", "Boolean", "Formula"],
        ["Hello", 42, True, "=A1+B1"],
        ["World", 3.14, False, "=SUM(A1:B1)"],
    ],
    "single_cell": [["Single Value"]],
    "empty": [],
}

# Batch update data
BATCH_UPDATE_DATA = [
    {"range": "Sheet1!A1:B2", "values": [["A1", "B1"], ["A2", "B2"]]},
    {"range": "Sheet1!C1:D2", "values": [["C1", "D1"], ["C2", "D2"]]},
]
