"""Unit tests for Gmail client.

Tests client initialization, authentication, and API methods.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.gmail import (
    GmailAuthError,
    GmailClient,
    GmailError,
    GmailQuotaExceeded,
    GmailRateLimitError,
)


class TestGmailClientInitialization:
    """Tests for GmailClient initialization."""

    def test_init_with_access_token(self):
        """Client initializes with access token."""
        client = GmailClient(access_token="test-token")
        assert client.access_token == "test-token"
        assert client.name == "gmail"
        assert client.user_id == "me"

    def test_init_missing_access_token_raises_error(self):
        """Client raises error without access token."""
        with pytest.raises(GmailError) as exc_info:
            GmailClient()
        assert "No access_token provided" in str(exc_info.value)

    def test_init_with_all_oauth_params(self):
        """Client initializes with all OAuth parameters."""
        client = GmailClient(
            access_token="access-123",  # pragma: allowlist secret
            refresh_token="refresh-456",  # pragma: allowlist secret
            client_id="client-789",  # pragma: allowlist secret
            client_secret="secret-000",  # pragma: allowlist secret
        )
        assert client.access_token == "access-123"
        assert client.refresh_token == "refresh-456"  # pragma: allowlist secret
        assert client.client_id == "client-789"  # pragma: allowlist secret
        assert client.client_secret == "secret-000"  # pragma: allowlist secret

    def test_init_with_credentials_json_dict(self):
        """Client parses credentials from dict."""
        creds = {
            "access_token": "token-from-dict",
            "refresh_token": "refresh-from-dict",
        }
        client = GmailClient(credentials_json=creds)
        assert client.access_token == "token-from-dict"
        assert client.refresh_token == "refresh-from-dict"

    def test_init_with_credentials_json_string(self):
        """Client parses credentials from JSON string."""
        import json

        creds = {"access_token": "token-from-json"}
        creds_json = json.dumps(creds)
        client = GmailClient(credentials_json=creds_json)
        assert client.access_token == "token-from-json"

    def test_init_with_invalid_json_raises_error(self):
        """Client raises error with invalid JSON credentials."""
        with pytest.raises(GmailError) as exc_info:
            GmailClient(credentials_json="{invalid json")
        assert "Invalid credentials JSON" in str(exc_info.value)


class TestGmailClientHeaders:
    """Tests for header generation."""

    def test_get_headers_includes_bearer_token(self):
        """Headers include Bearer authorization."""
        client = GmailClient(access_token="test-token")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestGmailClientMessageOperations:
    """Tests for message operations."""

    @pytest.mark.asyncio
    async def test_list_messages_success(self, gmail_client_with_mock):
        """list_messages returns messages list."""
        expected_response = {
            "messages": [{"id": "msg-1", "threadId": "thread-1"}],
            "resultSizeEstimate": 1,
        }
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: expected_response)
        )

        result = await gmail_client_with_mock.list_messages(query="from:test@example.com")
        assert "messages" in result
        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_list_messages_with_pagination(self, gmail_client_with_mock):
        """list_messages supports pagination."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"messages": [], "nextPageToken": "token-next"},
            )
        )

        result = await gmail_client_with_mock.list_messages(
            page_size=50, page_token="token-current"
        )
        assert "nextPageToken" in result

    @pytest.mark.asyncio
    async def test_get_message_success(self, gmail_client_with_mock, sample_message):
        """get_message returns full message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: sample_message)
        )

        result = await gmail_client_with_mock.get_message("msg-123")
        assert result["id"] == "msg-123"
        assert result["threadId"] == "thread-456"

    @pytest.mark.asyncio
    async def test_send_message_success(self, gmail_client_with_mock):
        """send_message sends email successfully."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "msg-sent-123", "threadId": "thread-1"}
            )
        )

        result = await gmail_client_with_mock.send_message(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body",
            html=False,
        )
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_with_multiple_recipients(self, gmail_client_with_mock):
        """send_message handles multiple recipients."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-sent"})
        )

        result = await gmail_client_with_mock.send_message(
            to=["user1@example.com", "user2@example.com"],
            subject="Test",
            body="Test",
        )
        assert "id" in result

    @pytest.mark.asyncio
    async def test_delete_message_success(self, gmail_client_with_mock):
        """delete_message permanently deletes message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {})
        )

        result = await gmail_client_with_mock.delete_message("msg-123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, gmail_client_with_mock):
        """mark_as_read marks message as read."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "msg-123", "labelIds": ["INBOX"]}
            )
        )

        result = await gmail_client_with_mock.mark_as_read("msg-123")
        assert "id" in result

    @pytest.mark.asyncio
    async def test_star_message_success(self, gmail_client_with_mock):
        """star_message stars message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"id": "msg-123", "labelIds": ["STARRED"]},
            )
        )

        result = await gmail_client_with_mock.star_message("msg-123")
        assert "id" in result

    @pytest.mark.asyncio
    async def test_archive_message_success(self, gmail_client_with_mock):
        """archive_message archives message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-123"})
        )

        result = await gmail_client_with_mock.archive_message("msg-123")
        assert "id" in result


class TestGmailClientLabelOperations:
    """Tests for label operations."""

    @pytest.mark.asyncio
    async def test_list_labels_success(self, gmail_client_with_mock, sample_list_labels_response):
        """list_labels returns labels list."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: sample_list_labels_response)
        )

        result = await gmail_client_with_mock.list_labels()
        assert "labels" in result
        assert len(result["labels"]) > 0

    @pytest.mark.asyncio
    async def test_create_label_success(self, gmail_client_with_mock):
        """create_label creates new label."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {
                    "id": "Label_new",
                    "name": "TestLabel",
                },
            )
        )

        result = await gmail_client_with_mock.create_label("TestLabel")
        assert result["name"] == "TestLabel"

    @pytest.mark.asyncio
    async def test_delete_label_success(self, gmail_client_with_mock):
        """delete_label deletes label."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {})
        )

        result = await gmail_client_with_mock.delete_label("Label_1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_add_label_to_message(self, gmail_client_with_mock):
        """add_label applies label to message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "msg-123", "labelIds": ["Label_1"]}
            )
        )

        result = await gmail_client_with_mock.add_label("msg-123", "Label_1")
        assert "labelIds" in result


class TestGmailClientDraftOperations:
    """Tests for draft operations."""

    @pytest.mark.asyncio
    async def test_list_drafts_success(self, gmail_client_with_mock):
        """list_drafts returns drafts list."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"drafts": [{"id": "draft-1"}]},
            )
        )

        result = await gmail_client_with_mock.list_drafts()
        assert "drafts" in result

    @pytest.mark.asyncio
    async def test_create_draft_success(self, gmail_client_with_mock):
        """create_draft creates new draft."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "draft-123"})
        )

        result = await gmail_client_with_mock.create_draft(
            to="user@example.com", subject="Test", body="Test content"
        )
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_draft_success(self, gmail_client_with_mock):
        """send_draft sends existing draft."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-sent"})
        )

        result = await gmail_client_with_mock.send_draft("draft-123")
        assert "id" in result


class TestGmailClientThreadOperations:
    """Tests for thread operations."""

    @pytest.mark.asyncio
    async def test_list_threads_success(self, gmail_client_with_mock):
        """list_threads returns threads list."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"threads": [{"id": "thread-1"}]})
        )

        result = await gmail_client_with_mock.list_threads()
        assert "threads" in result

    @pytest.mark.asyncio
    async def test_get_thread_success(self, gmail_client_with_mock, sample_thread):
        """get_thread returns thread with all messages."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: sample_thread)
        )

        result = await gmail_client_with_mock.get_thread("thread-xyz")
        assert result["id"] == "thread-xyz"
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_delete_thread_success(self, gmail_client_with_mock):
        """delete_thread deletes thread."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {})
        )

        result = await gmail_client_with_mock.delete_thread("thread-123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_modify_thread_add_labels(self, gmail_client_with_mock):
        """modify_thread adds labels to thread."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "thread-1", "labelIds": ["Label_1"]}
            )
        )

        result = await gmail_client_with_mock.modify_thread("thread-1", add_labels=["Label_1"])
        assert "labelIds" in result


class TestGmailClientUserOperations:
    """Tests for user operations."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, gmail_client_with_mock, sample_profile):
        """get_user_profile returns user profile."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: sample_profile)
        )

        result = await gmail_client_with_mock.get_user_profile()
        assert result["emailAddress"] == "user@example.com"
        assert "messagesTotal" in result


class TestGmailClientErrorHandling:
    """Tests for error handling and responses."""

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, gmail_client_with_mock):
        """401 response raises GmailAuthError."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=401, text="Unauthorized")
        )

        with pytest.raises(GmailAuthError):
            await gmail_client_with_mock.list_messages()

    @pytest.mark.asyncio
    async def test_403_quota_raises_quota_error(self, gmail_client_with_mock):
        """403 response raises GmailQuotaExceeded."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=403,
                json=lambda: {
                    "error": {
                        "reason": "quotaExceeded",
                        "message": "Quota exceeded",
                    }
                },
            )
        )

        with pytest.raises(GmailQuotaExceeded):
            await gmail_client_with_mock.list_messages()

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, gmail_client_with_mock):
        """429 response raises GmailRateLimitError."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=429,
                headers={"Retry-After": "60"},
                text="Rate limit exceeded",
            )
        )

        with pytest.raises(GmailRateLimitError) as exc_info:
            await gmail_client_with_mock.list_messages()
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_500_raises_gmail_error(self, gmail_client_with_mock):
        """500 response raises GmailError."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=500, json=lambda: {"error": {"message": "Server error"}}
            )
        )

        with pytest.raises(GmailError):
            await gmail_client_with_mock.list_messages()


class TestGmailClientRetryLogic:
    """Tests for retry logic and resilience."""

    def test_rate_limit_error_is_retryable(self, gmail_client_with_mock):
        """Rate limit errors are retryable."""
        rate_limit_error = GmailRateLimitError("Rate limited")
        assert gmail_client_with_mock._is_retryable_error(rate_limit_error) is True

    def test_auth_error_triggers_refresh(self, gmail_client_with_mock):
        """Auth errors are detected and logged."""
        gmail_client_with_mock.refresh_token = "refresh-token"  # pragma: allowlist secret
        gmail_client_with_mock.client_id = "client-id"  # pragma: allowlist secret
        gmail_client_with_mock.client_secret = "client-secret"  # pragma: allowlist secret

        auth_error = GmailAuthError("Unauthorized")
        result = gmail_client_with_mock._is_retryable_error(auth_error)
        # Auth errors should not automatically retry at this level
        assert result is False

    def test_non_retryable_error(self, gmail_client_with_mock):
        """Non-retryable errors are not retried."""
        value_error = ValueError("Invalid value")
        result = gmail_client_with_mock._is_retryable_error(value_error)
        assert result is False


class TestGmailClientMessageSending:
    """Tests for advanced message sending capabilities."""

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, gmail_client_with_mock, tmp_path):
        """send_message_with_attachment sends email with attachment."""
        # Create a temporary file for testing
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test attachment content")

        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-with-attachment"})
        )

        result = await gmail_client_with_mock.send_message_with_attachment(
            to="user@example.com",
            subject="Test Email",
            body="Email with attachment",
            attachment_path=str(test_file),
        )
        assert result["id"] == "msg-with-attachment"

    @pytest.mark.asyncio
    async def test_send_html_message(self, gmail_client_with_mock):
        """send_message handles HTML content."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-html"})
        )

        result = await gmail_client_with_mock.send_message(
            to="user@example.com", subject="HTML Email", body="<h1>Hello</h1>", html=True
        )
        assert result["id"] == "msg-html"


class TestGmailClientThreadOperationsAdv:
    """Advanced tests for thread operations."""

    @pytest.mark.asyncio
    async def test_trash_thread(self, gmail_client_with_mock):
        """trash_thread moves thread to trash."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "thread-123"})
        )

        result = await gmail_client_with_mock.trash_thread("thread-123")
        assert result["id"] == "thread-123"

    @pytest.mark.asyncio
    async def test_untrash_thread(self, gmail_client_with_mock):
        """untrash_thread restores thread from trash."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "thread-123"})
        )

        result = await gmail_client_with_mock.untrash_thread("thread-123")
        assert result["id"] == "thread-123"


class TestGmailClientMessageAdv:
    """Advanced tests for message operations."""

    @pytest.mark.asyncio
    async def test_trash_message(self, gmail_client_with_mock):
        """trash_message moves message to trash."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-123"})
        )

        result = await gmail_client_with_mock.trash_message("msg-123")
        assert result["id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_untrash_message(self, gmail_client_with_mock):
        """untrash_message restores message from trash."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-123"})
        )

        result = await gmail_client_with_mock.untrash_message("msg-123")
        assert result["id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_mark_as_unread(self, gmail_client_with_mock):
        """mark_as_unread marks message as unread."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "msg-123", "labelIds": ["UNREAD"]}
            )
        )

        result = await gmail_client_with_mock.mark_as_unread("msg-123")
        assert "id" in result

    @pytest.mark.asyncio
    async def test_unstar_message(self, gmail_client_with_mock):
        """unstar_message removes star from message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-123"})
        )

        result = await gmail_client_with_mock.unstar_message("msg-123")
        assert result["id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_get_message_attachments(self, gmail_client_with_mock):
        """get_message_attachments retrieves attachments."""
        # Mock the get_message response which has attachment parts
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {
                    "id": "msg-123",
                    "payload": {
                        "parts": [
                            {"filename": "test.txt", "mimeType": "text/plain"},
                            {"filename": "image.jpg", "mimeType": "image/jpeg"},
                        ]
                    },
                },
            )
        )

        result = await gmail_client_with_mock.get_message_attachments("msg-123")
        # Result is a list of attachment dicts
        assert isinstance(result, list)
        assert len(result) == 2


class TestGmailClientLabelAdv:
    """Advanced tests for label operations."""

    @pytest.mark.asyncio
    async def test_get_label(self, gmail_client_with_mock):
        """get_label retrieves specific label."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"id": "Label_1", "name": "MyLabel"}
            )
        )

        result = await gmail_client_with_mock.get_label("Label_1")
        assert result["name"] == "MyLabel"

    @pytest.mark.asyncio
    async def test_remove_label(self, gmail_client_with_mock):
        """remove_label removes label from message."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "msg-123"})
        )

        result = await gmail_client_with_mock.remove_label("msg-123", "Label_1")
        assert result["id"] == "msg-123"


class TestGmailClientDraftAdv:
    """Advanced tests for draft operations."""

    @pytest.mark.asyncio
    async def test_get_draft(self, gmail_client_with_mock):
        """get_draft retrieves draft details."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"id": "draft-123", "message": {}})
        )

        result = await gmail_client_with_mock.get_draft("draft-123")
        assert result["id"] == "draft-123"

    @pytest.mark.asyncio
    async def test_delete_draft(self, gmail_client_with_mock):
        """delete_draft deletes draft permanently."""
        gmail_client_with_mock._client.request = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {})
        )

        result = await gmail_client_with_mock.delete_draft("draft-123")
        assert result == {}
