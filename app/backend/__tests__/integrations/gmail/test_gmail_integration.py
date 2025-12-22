"""Integration tests for Gmail client.

Tests end-to-end workflows combining multiple operations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.gmail import GmailClient


class TestGmailClientIntegrationMessageWorkflow:
    """Integration tests for message workflows."""

    @pytest.mark.asyncio
    async def test_list_and_read_messages(self):
        """Workflow: List messages then read each one."""
        client = GmailClient(access_token="test-token")

        # Mock list_messages response
        list_response = MagicMock()
        list_response.status_code = 200
        list_response.headers = {}
        list_response.json = MagicMock(
            return_value={
                "messages": [
                    {"id": "msg-1", "threadId": "thread-1"},
                    {"id": "msg-2", "threadId": "thread-2"},
                ]
            }
        )

        # Mock get_message responses
        get_response_1 = MagicMock()
        get_response_1.status_code = 200
        get_response_1.headers = {}
        get_response_1.json = MagicMock(
            return_value={"id": "msg-1", "threadId": "thread-1", "snippet": "Test message 1"}
        )

        get_response_2 = MagicMock()
        get_response_2.status_code = 200
        get_response_2.headers = {}
        get_response_2.json = MagicMock(
            return_value={"id": "msg-2", "threadId": "thread-2", "snippet": "Test message 2"}
        )

        # Set up mock client to return different responses for different calls
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return list_response
            elif call_count == 2:
                return get_response_1
            else:
                return get_response_2

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: List messages
        messages = await client.list_messages()
        assert len(messages["messages"]) == 2

        # Workflow: Read each message
        msg1 = await client.get_message("msg-1")
        assert msg1["id"] == "msg-1"

        msg2 = await client.get_message("msg-2")
        assert msg2["id"] == "msg-2"

    @pytest.mark.asyncio
    async def test_send_and_archive_message(self):
        """Workflow: Send message then archive it."""
        client = GmailClient(access_token="test-token")

        # Mock send response
        send_response = MagicMock()
        send_response.status_code = 200
        send_response.headers = {}
        send_response.json = MagicMock(return_value={"id": "msg-sent-123"})

        # Mock archive response
        archive_response = MagicMock()
        archive_response.status_code = 200
        archive_response.headers = {}
        archive_response.json = MagicMock(return_value={"id": "msg-sent-123", "labelIds": []})

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return send_response if call_count == 1 else archive_response

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: Send message
        sent = await client.send_message(
            to="recipient@example.com", subject="Test", body="Test body"
        )
        assert sent["id"] == "msg-sent-123"

        # Workflow: Archive sent message
        archived = await client.archive_message("msg-sent-123")
        assert archived["id"] == "msg-sent-123"

    @pytest.mark.asyncio
    async def test_message_label_workflow(self):
        """Workflow: Create label and apply to message."""
        client = GmailClient(access_token="test-token")

        # Mock create_label response
        create_label_response = MagicMock()
        create_label_response.status_code = 200
        create_label_response.headers = {}
        create_label_response.json = MagicMock(
            return_value={"id": "Label_new", "name": "Important"}
        )

        # Mock add_label response
        add_label_response = MagicMock()
        add_label_response.status_code = 200
        add_label_response.headers = {}
        add_label_response.json = MagicMock(
            return_value={"id": "msg-123", "labelIds": ["Label_new"]}
        )

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return create_label_response if call_count == 1 else add_label_response

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: Create label
        label = await client.create_label("Important")
        assert label["name"] == "Important"

        # Workflow: Apply label to message
        labeled = await client.add_label("msg-123", "Label_new")
        assert "Label_new" in labeled["labelIds"]


class TestGmailClientIntegrationErrorRecovery:
    """Integration tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Workflow: Handle rate limit error gracefully."""
        from src.integrations.gmail import GmailRateLimitError

        client = GmailClient(access_token="test-token")

        # Mock rate limit response
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "60"}

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=rate_limit_response)
        client._client = mock_client

        # Expect rate limit error to be raised with retry_after
        with pytest.raises(GmailRateLimitError) as exc_info:
            await client.list_messages()

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_quota_exceeded_handling(self):
        """Workflow: Handle quota exceeded error."""
        from src.integrations.gmail import GmailQuotaExceeded

        client = GmailClient(access_token="test-token")

        # Mock quota exceeded response
        quota_response = MagicMock()
        quota_response.status_code = 403
        quota_response.headers = {}
        quota_response.json = MagicMock(
            return_value={"error": {"reason": "quotaExceeded", "message": "Daily quota exceeded"}}
        )

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=quota_response)
        client._client = mock_client

        # Expect quota exceeded error
        with pytest.raises(GmailQuotaExceeded):
            await client.list_messages()

    @pytest.mark.asyncio
    async def test_auth_error_detection(self):
        """Workflow: Detect authentication errors."""
        from src.integrations.gmail import GmailAuthError

        client = GmailClient(access_token="invalid-token")

        # Mock auth error response
        auth_response = MagicMock()
        auth_response.status_code = 401
        auth_response.headers = {}

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=auth_response)
        client._client = mock_client

        # Expect auth error
        with pytest.raises(GmailAuthError):
            await client.list_messages()


class TestGmailClientIntegrationThreadWorkflow:
    """Integration tests for thread operations."""

    @pytest.mark.asyncio
    async def test_thread_conversation_workflow(self):
        """Workflow: Get thread and process all messages."""
        client = GmailClient(access_token="test-token")

        # Mock thread response with multiple messages
        thread_response = MagicMock()
        thread_response.status_code = 200
        thread_response.headers = {}
        thread_response.json = MagicMock(
            return_value={
                "id": "thread-123",
                "messages": [
                    {
                        "id": "msg-1",
                        "threadId": "thread-123",
                        "snippet": "First message",
                    },
                    {
                        "id": "msg-2",
                        "threadId": "thread-123",
                        "snippet": "Reply to first",
                    },
                ],
            }
        )

        # Mock mark as read response
        read_response = MagicMock()
        read_response.status_code = 200
        read_response.headers = {}
        read_response.json = MagicMock(return_value={"id": "thread-123"})

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return thread_response if call_count == 1 else read_response

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: Get thread
        thread = await client.get_thread("thread-123")
        assert len(thread["messages"]) == 2

        # Workflow: Mark thread messages as read
        result = await client.modify_thread("thread-123", add_labels=["UNREAD"])
        assert result["id"] == "thread-123"

    @pytest.mark.asyncio
    async def test_thread_management_workflow(self):
        """Workflow: Archive and delete threads."""
        client = GmailClient(access_token="test-token")

        # Mock responses
        archive_response = MagicMock()
        archive_response.status_code = 200
        archive_response.headers = {}
        archive_response.json = MagicMock(return_value={"id": "thread-123"})

        delete_response = MagicMock()
        delete_response.status_code = 200
        delete_response.headers = {}
        delete_response.json = MagicMock(return_value={})

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return archive_response if call_count == 1 else delete_response

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: Archive thread (move to All Mail)
        archived = await client.modify_thread("thread-123", add_labels=["ARCHIVE"])
        assert archived["id"] == "thread-123"

        # Workflow: Delete thread permanently
        deleted = await client.delete_thread("thread-123")
        assert deleted == {}


class TestGmailClientIntegrationDraftWorkflow:
    """Integration tests for draft operations."""

    @pytest.mark.asyncio
    async def test_draft_creation_and_send_workflow(self):
        """Workflow: Create draft, then send it."""
        client = GmailClient(access_token="test-token")

        # Mock create draft response
        create_response = MagicMock()
        create_response.status_code = 200
        create_response.headers = {}
        create_response.json = MagicMock(return_value={"id": "draft-123"})

        # Mock send draft response
        send_response = MagicMock()
        send_response.status_code = 200
        send_response.headers = {}
        send_response.json = MagicMock(return_value={"id": "msg-sent-456"})

        # Set up mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return create_response if call_count == 1 else send_response

        mock_client.request = AsyncMock(side_effect=mock_request)
        client._client = mock_client

        # Workflow: Create draft
        draft = await client.create_draft(
            to="recipient@example.com", subject="Test", body="Test content"
        )
        assert draft["id"] == "draft-123"

        # Workflow: Send draft
        sent = await client.send_draft("draft-123")
        assert sent["id"] == "msg-sent-456"
