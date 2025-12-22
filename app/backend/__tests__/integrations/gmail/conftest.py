"""Fixtures for Gmail integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.gmail import GmailClient


def create_mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a properly configured mock HTTP response.

    Args:
        status_code: HTTP status code for the response.
        json_data: JSON data to return from json() method.

    Returns:
        Configured MagicMock response object.
    """
    if json_data is None:
        json_data = {}

    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.text = str(json_data)
    # json() returns the data when called
    response.json = MagicMock(return_value=json_data)
    return response


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for Gmail client."""
    return AsyncMock()


@pytest.fixture
def gmail_client_with_mock():
    """Gmail client with mocked HTTP client."""
    client = GmailClient(access_token="test-token")
    # Create a properly mocked async client
    mock_client = AsyncMock()
    # CRITICAL: Set is_closed=False so the client property doesn't create a real httpx client
    mock_client.is_closed = False
    # Create a default mock response that tests can override
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    # Make json() return an empty dict by default
    mock_response.json = MagicMock(return_value={})
    mock_client.request = AsyncMock(return_value=mock_response)
    client._client = mock_client
    return client


@pytest.fixture
def sample_message():
    """Sample Gmail message response."""
    return {
        "id": "msg-123",
        "threadId": "thread-456",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Test message content preview",
        "internalDate": "1640000000000",
        "sizeEstimate": 1024,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Subject"},
            ],
            "body": {"size": 100, "data": "VGVzdCBib2R5IGNvbnRlbnQ="},
        },
    }


@pytest.fixture
def sample_label():
    """Sample Gmail label response."""
    return {
        "id": "Label_1",
        "name": "TestLabel",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "messagesTotal": 10,
        "threadsTotal": 5,
    }


@pytest.fixture
def sample_draft():
    """Sample Gmail draft response."""
    return {
        "id": "draft-789",
        "message": {
            "id": "msg-draft-123",
            "threadId": "thread-draft-456",
            "labelIds": ["DRAFT"],
            "snippet": "Draft message content",
        },
    }


@pytest.fixture
def sample_thread():
    """Sample Gmail thread response."""
    return {
        "id": "thread-xyz",
        "historyId": "1234567890",
        "messages": [
            {
                "id": "msg-1",
                "threadId": "thread-xyz",
                "labelIds": ["INBOX"],
                "snippet": "First message in thread",
            },
            {
                "id": "msg-2",
                "threadId": "thread-xyz",
                "labelIds": ["INBOX"],
                "snippet": "Reply message",
            },
        ],
        "snippet": "Conversation thread preview",
    }


@pytest.fixture
def sample_profile():
    """Sample Gmail user profile response."""
    return {
        "emailAddress": "user@example.com",
        "messagesTotal": 5432,
        "threadsTotal": 2100,
        "historyId": "1234567890",
    }


@pytest.fixture
def sample_list_messages_response(sample_message):
    """Sample list messages response."""
    return {
        "messages": [sample_message],
        "nextPageToken": "token-next-page",
        "resultSizeEstimate": 1,
    }


@pytest.fixture
def sample_list_labels_response(sample_label):
    """Sample list labels response."""
    return {
        "labels": [
            sample_label,
            {
                "id": "INBOX",
                "name": "INBOX",
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "messagesTotal": 100,
                "threadsTotal": 50,
            },
        ]
    }
