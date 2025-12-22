"""Pytest fixtures for Google Drive integration tests."""

import json
from unittest.mock import AsyncMock

import pytest

from src.integrations.google_drive.client import GoogleDriveClient

# Sample credentials for testing
SAMPLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key123",
    "access_token": "test_token_123",
}

# Sample file metadata responses
SAMPLE_FILE_METADATA = {
    "id": "file123",
    "name": "Test Document",
    "mimeType": "application/vnd.google-apps.document",
    "size": "1024",
    "createdTime": "2025-01-01T00:00:00.000Z",
    "modifiedTime": "2025-01-02T00:00:00.000Z",
    "webViewLink": "https://docs.google.com/document/d/file123/edit",
    "owners": [{"displayName": "Test User", "emailAddress": "test@example.com"}],
    "parents": ["folder123"],
    "shared": True,
    "trashed": False,
}

SAMPLE_FILE_LIST_RESPONSE = {
    "files": [
        {
            "id": "file1",
            "name": "Document 1",
            "mimeType": "application/vnd.google-apps.document",
            "size": "1024",
            "createdTime": "2025-01-01T00:00:00.000Z",
            "modifiedTime": "2025-01-02T00:00:00.000Z",
            "webViewLink": "https://docs.google.com/document/d/file1/edit",
        },
        {
            "id": "file2",
            "name": "Spreadsheet 1",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "size": "2048",
            "createdTime": "2025-01-03T00:00:00.000Z",
            "modifiedTime": "2025-01-04T00:00:00.000Z",
            "webViewLink": "https://docs.google.com/spreadsheets/d/file2/edit",
        },
    ],
    "nextPageToken": None,
}

SAMPLE_CREATED_FILE = {
    "id": "new_file_123",
    "name": "New Document",
    "mimeType": "application/vnd.google-apps.document",
    "webViewLink": "https://docs.google.com/document/d/new_file_123/edit",
}

SAMPLE_PERMISSION = {
    "id": "permission123",
    "type": "user",
    "role": "reader",
    "emailAddress": "user@example.com",
}

SAMPLE_DOCUMENT_CONTENT = """
# Test Document

This is a test document with some content.

## Section 1
Content of section 1.

## Section 2
Content of section 2.
"""


@pytest.fixture
def credentials():
    """Fixture providing sample Google Drive credentials."""
    return SAMPLE_CREDENTIALS.copy()


@pytest.fixture
def credentials_json_str():
    """Fixture providing credentials as JSON string."""
    return json.dumps(SAMPLE_CREDENTIALS)


@pytest.fixture
async def google_drive_client(credentials):
    """Fixture providing configured GoogleDriveClient instance."""
    client = GoogleDriveClient(
        credentials_json=credentials,
        timeout=10.0,
        max_retries=2,
    )
    client.access_token = "test_token_123"
    yield client
    await client.close()


@pytest.fixture
def mock_httpx_client():
    """Fixture providing mocked httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.request = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.patch = AsyncMock()
    mock_client.delete = AsyncMock()
    return mock_client


@pytest.fixture
def file_metadata():
    """Fixture providing sample file metadata."""
    return SAMPLE_FILE_METADATA.copy()


@pytest.fixture
def file_list_response():
    """Fixture providing sample file list response."""
    return SAMPLE_FILE_LIST_RESPONSE.copy()


@pytest.fixture
def created_file():
    """Fixture providing sample created file response."""
    return SAMPLE_CREATED_FILE.copy()


@pytest.fixture
def permission():
    """Fixture providing sample permission object."""
    return SAMPLE_PERMISSION.copy()


@pytest.fixture
def document_content():
    """Fixture providing sample document content."""
    return SAMPLE_DOCUMENT_CONTENT
