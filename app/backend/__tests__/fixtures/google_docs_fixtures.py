"""Test fixtures for Google Docs integration.

Provides sample data, expected response schemas, and fixture utilities
for comprehensive integration testing of the Google Docs API client.
"""

from typing import Any

# ============================================================================
# SAMPLE INPUT DATA
# ============================================================================

SAMPLE_DATA = {
    # Document creation
    "doc_title": "Integration Test Document",
    "doc_title_special": "Test Document with Special Chars: @#$%",
    "parent_folder_id": "1234567890abcdefg",

    # Text operations
    "text_to_insert": "Hello, World!",
    "long_text": "This is a longer text that will be inserted into the document for testing purposes.",
    "text_with_unicode": "Unicode test: café, 日本語, emoji 🚀",

    # Formatting
    "format_start_index": 1,
    "format_end_index": 5,
    "font_size": 12,

    # Table operations
    "table_rows": 3,
    "table_columns": 2,

    # Sharing
    "share_email": "test@example.com",
    "share_role": "reader",
    "share_email_writer": "writer@example.com",
    "share_role_writer": "writer",

    # Colors (RGB format 0.0-1.0)
    "text_color_red": {"red": 1.0, "green": 0.0, "blue": 0.0},
    "text_color_blue": {"red": 0.0, "green": 0.0, "blue": 1.0},
    "text_color_black": {"red": 0.0, "green": 0.0, "blue": 0.0},
}

# ============================================================================
# RESPONSE SCHEMAS (for validation)
# ============================================================================

RESPONSE_SCHEMAS = {
    "document_metadata": {
        "documentId": str,
        "title": str,
        "mimeType": str,
    },
    "document_full": {
        "documentId": str,
        "title": str,
        "body": dict,
        "documentStyle": dict,
        "revisionId": str,
        "suggestionsViewMode": str,
    },
    "batch_update_response": {
        "documentId": str,
        "replies": list,
    },
    "permission": {
        "kind": str,
        "id": str,
        "type": str,
        "emailAddress": str,
        "role": str,
    },
    "permission_list": {
        "kind": str,
        "permissions": list,
    },
}

# ============================================================================
# SAMPLE RESPONSES (from live API)
# ============================================================================

SAMPLE_RESPONSES = {
    "create_document": {
        "documentId": "1test-document-id-12345",
        "title": "Integration Test Document",
        "mimeType": "application/vnd.google-apps.document",
    },
    "get_document": {
        "documentId": "1test-document-id-12345",
        "title": "Integration Test Document",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "Hello, World!",
                                    "textStyle": {},
                                }
                            }
                        ],
                        "paragraphStyle": {},
                    }
                }
            ]
        },
        "documentStyle": {
            "defaultHeaderId": "",
            "defaultFooterId": "",
            "evenPageHeaderId": "",
            "evenPageFooterId": "",
        },
        "revisionId": "test-revision-id",
        "suggestionsViewMode": "SUGGESTIONS_INLINE",
    },
    "batch_update_response": {
        "documentId": "1test-document-id-12345",
        "replies": [
            {
                "insertText": {},
            }
        ],
    },
    "format_text_response": {
        "documentId": "1test-document-id-12345",
        "replies": [
            {
                "updateTextStyle": {},
            }
        ],
    },
    "create_table_response": {
        "documentId": "1test-document-id-12345",
        "replies": [
            {
                "insertTable": {
                    "objectId": "test-table-id",
                }
            }
        ],
    },
    "share_document": {
        "kind": "drive#permission",
        "id": "test-permission-id",
        "type": "user",
        "emailAddress": "test@example.com",
        "role": "reader",
    },
    "get_permissions": {
        "kind": "drive#permissionList",
        "permissions": [
            {
                "kind": "drive#permission",
                "id": "test-permission-id-1",
                "type": "user",
                "emailAddress": "test@example.com",
                "role": "reader",
            },
            {
                "kind": "drive#permission",
                "id": "test-permission-id-2",
                "type": "user",
                "emailAddress": "owner@example.com",
                "role": "owner",
            },
        ],
    },
}

# ============================================================================
# DOCUMENT IDS FOR TESTING
# ============================================================================

DOCUMENT_IDS = {
    "valid": "1test-document-id-12345",
    "invalid": "invalid-id",
    "empty": "",
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def create_mock_credentials(access_token: str = "test-access-token") -> dict[str, Any]:
    """Create mock Google Docs credentials for testing.

    Args:
        access_token: OAuth2 access token

    Returns:
        Dictionary with credential format
    """
    return {
        "type": "service_account",
        "project_id": "smarter-team",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
        "client_email": "smarterteam@smarter-team.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "access_token": access_token,
    }


def validate_response_schema(
    response: dict[str, Any],
    schema: dict[str, type],
) -> bool:
    """Validate response against schema.

    Args:
        response: Response dictionary
        schema: Schema with field names and types

    Returns:
        True if response matches schema

    Raises:
        AssertionError: If schema doesn't match
    """
    for field, expected_type in schema.items():
        assert field in response, f"Missing field: {field}"
        assert isinstance(
            response[field], expected_type
        ), f"Field {field}: expected {expected_type}, got {type(response[field])}"
    return True


# ============================================================================
# ERROR SCENARIOS
# ============================================================================

ERROR_SCENARIOS = {
    "missing_access_token": {
        "error": "Not authenticated. Call authenticate() first.",
        "type": "GoogleDocsAuthError",
    },
    "invalid_document_id": {
        "error": "Document not found",
        "type": "GoogleDocsError",
        "status_code": 404,
    },
    "rate_limited": {
        "error": "Rate limit exceeded",
        "type": "GoogleDocsRateLimitError",
        "status_code": 429,
    },
    "auth_failed": {
        "error": "Authentication failed",
        "type": "GoogleDocsAuthError",
        "status_code": 401,
    },
    "invalid_input": {
        "error": "Invalid parameter",
        "type": "ValueError",
    },
    "missing_required_param": {
        "error": "Missing required parameter",
        "type": "TypeError",
    },
}
