"""Test fixtures for Google Drive integration.

Provides sample data, credentials, and expected response schemas for comprehensive testing.
"""

import json
from typing import Any

# Sample test data
SAMPLE_DATA = {
    # File listing
    "page_size": 10,
    "query": "name contains 'test'",
    "order_by": "modifiedTime desc",

    # File operations
    "file_id": "test-file-123",
    "file_name": "test-document.txt",
    "file_content": "This is test content for Google Drive",
    "file_content_bytes": b"This is test content as bytes",

    # Document operations
    "doc_title": "Test Document",
    "sheet_title": "Test Spreadsheet",
    "folder_title": "Test Folder",

    # Folder operations
    "parent_folder_id": "parent-folder-123",
    "folder_id": "folder-456",

    # Sharing
    "share_email": "test-user@example.com",
    "share_role": "editor",
    "share_type": "user",

    # Export formats
    "export_formats": ["pdf", "docx", "xlsx", "csv", "json", "txt"],
}

# Expected response schemas (field structure and types)
RESPONSE_SCHEMAS = {
    "file": {
        "id": str,
        "name": str,
        "mimeType": str,
        "createdTime": str,
        "modifiedTime": str,
        "webViewLink": str,
    },
    "file_with_size": {
        "id": str,
        "name": str,
        "mimeType": str,
        "size": int,
        "createdTime": str,
        "modifiedTime": str,
        "webViewLink": str,
    },
    "file_list": {
        "files": list,
        "nextPageToken": str,  # Optional but should be checked
    },
    "metadata": {
        "id": str,
        "name": str,
        "mimeType": str,
        "size": int,
        "createdTime": str,
        "modifiedTime": str,
        "webViewLink": str,
        "shared": bool,
        "trashed": bool,
    },
    "permission": {
        "id": str,
        "type": str,
        "role": str,
    },
    "health_check": {
        "name": str,
        "healthy": bool,
        "message": str,
    },
}

# Sample responses from live API (cached examples for reference)
SAMPLE_RESPONSES = {
    "file": {
        "id": "1abc-def-2gh-3ij",
        "name": "Test Document",
        "mimeType": "application/vnd.google-apps.document",
        "size": 1024,
        "createdTime": "2025-12-22T10:00:00Z",
        "modifiedTime": "2025-12-22T11:00:00Z",
        "webViewLink": "https://docs.google.com/document/d/1abc-def-2gh-3ij/edit",
    },
    "file_list": {
        "files": [
            {
                "id": "1abc-def-2gh-3ij",
                "name": "Test Document",
                "mimeType": "application/vnd.google-apps.document",
                "createdTime": "2025-12-22T10:00:00Z",
                "modifiedTime": "2025-12-22T11:00:00Z",
                "webViewLink": "https://docs.google.com/document/d/1abc-def-2gh-3ij/edit",
            }
        ],
        "nextPageToken": "token-for-next-page",
    },
    "metadata": {
        "id": "1abc-def-2gh-3ij",
        "name": "Test Document",
        "mimeType": "application/vnd.google-apps.document",
        "size": 1024,
        "createdTime": "2025-12-22T10:00:00Z",
        "modifiedTime": "2025-12-22T11:00:00Z",
        "webViewLink": "https://docs.google.com/document/d/1abc-def-2gh-3ij/edit",
        "shared": True,
        "trashed": False,
    },
    "permission": {
        "id": "perm-123",
        "type": "user",
        "role": "reader",
        "emailAddress": "test-user@example.com",
    },
    "health_check": {
        "name": "google_drive",
        "healthy": True,
        "message": "Google Drive API is accessible",
    },
}

# MIME types for testing document operations
MIME_TYPES = {
    "google_doc": "application/vnd.google-apps.document",
    "google_sheet": "application/vnd.google-apps.spreadsheet",
    "google_slide": "application/vnd.google-apps.presentation",
    "google_form": "application/vnd.google-apps.form",
    "pdf": "application/pdf",
    "text": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
}

# Test credentials (will be loaded from .env)
def get_test_credentials() -> dict[str, Any]:
    """Load test credentials from environment.

    Returns:
        Dictionary with credentials_json or credentials_str

    Raises:
        ValueError: If credentials not found in environment
    """
    import os

    creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
    if creds_json:
        # Check if it's a file path or JSON string
        if creds_json.startswith("{"):
            # It's JSON
            try:
                return json.loads(creds_json)
            except json.JSONDecodeError:
                raise ValueError("GOOGLE_DRIVE_CREDENTIALS_JSON is not valid JSON")
        else:
            # It's a file path - try multiple locations
            cred_paths = [
                creds_json,  # As-is from env
                os.path.join(os.getcwd(), creds_json),  # Relative to cwd
                os.path.join(os.path.dirname(__file__), "..", "..", creds_json.replace("app/backend/", "")),  # Without duplicate prefix
            ]
            for path in cred_paths:
                if os.path.exists(path):
                    with open(path) as f:
                        return json.load(f)
            raise ValueError(f"Credentials file not found at: {cred_paths}")

    creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")
    if creds_path and os.path.exists(creds_path):
        with open(creds_path) as f:
            return json.load(f)

    raise ValueError(
        "No Google Drive credentials found. Set GOOGLE_DRIVE_CREDENTIALS_JSON "
        "or GOOGLE_DRIVE_CREDENTIALS_PATH in .env"
    )


def get_test_access_token() -> str | None:
    """Get pre-generated access token from environment.

    Returns:
        Access token if available, None otherwise
    """
    import os
    return os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN")


# List of all endpoints to test (auto-discovery)
ENDPOINTS_TO_TEST = [
    {
        "name": "list_files",
        "method": "GET",
        "description": "List files from Google Drive with filtering and pagination",
        "required_auth": True,
    },
    {
        "name": "get_file_metadata",
        "method": "GET",
        "description": "Get file metadata including size, dates, owners, permissions",
        "required_auth": True,
    },
    {
        "name": "read_document_content",
        "method": "GET",
        "description": "Read document content (Docs, Sheets, PDF)",
        "required_auth": True,
    },
    {
        "name": "create_document",
        "method": "POST",
        "description": "Create new document (Docs, Sheets, Slides, Forms)",
        "required_auth": True,
    },
    {
        "name": "upload_file",
        "method": "POST",
        "description": "Upload file to Google Drive",
        "required_auth": True,
    },
    {
        "name": "delete_file",
        "method": "DELETE",
        "description": "Delete file (trash or permanently)",
        "required_auth": True,
    },
    {
        "name": "share_file",
        "method": "POST",
        "description": "Share file with user or change permissions",
        "required_auth": True,
    },
    {
        "name": "export_document",
        "method": "GET",
        "description": "Export document in specified format (PDF, DOCX, CSV, etc)",
        "required_auth": True,
    },
    {
        "name": "health_check",
        "method": "GET",
        "description": "Check API connectivity and authentication",
        "required_auth": False,
    },
    {
        "name": "authenticate",
        "method": "POST",
        "description": "Authenticate with Google using service account or user credentials",
        "required_auth": False,
    },
]


# Expected error scenarios
ERROR_SCENARIOS = {
    "invalid_file_id": {
        "file_id": "invalid-file-id-that-does-not-exist",
        "expected_error": "File not found",
        "status_code": 404,
    },
    "invalid_credentials": {
        "credentials": {"type": "invalid"},
        "expected_error": "Invalid credentials",
        "status_code": 401,
    },
    "quota_exceeded": {
        "expected_error": "Quota exceeded",
        "status_code": 403,
    },
    "rate_limited": {
        "expected_error": "Rate limited",
        "status_code": 429,
    },
    "permission_denied": {
        "expected_error": "Permission denied",
        "status_code": 403,
    },
}
