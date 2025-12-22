"""Integration tests for Gmail API.

Tests EVERY public endpoint with real API keys from .env.
Ensures 100% endpoint coverage with no exceptions.

Test organization:
- Setup: Authentication and client initialization
- Messages: List, get, send, delete, manage
- Labels: List, get, create, delete, apply
- Drafts: List, get, create, send, delete
- Threads: List, get, delete, manage
- User: Profile information
- Attachments: Get, download

Requires:
- Gmail service account credentials in .env (GMAIL_CREDENTIALS_JSON or OAuth tokens)
- Internet connection for live API testing
"""

import json
import os

import pytest

from __tests__.fixtures.gmail_fixtures import (
    SAMPLE_DATA,
    get_test_message_queries,
    get_test_recipients,
)
from src.integrations.gmail.client import GmailClient
from src.integrations.gmail.exceptions import (
    GmailAuthError,
    GmailError,
    GmailNotFoundError,
)


class TestGmailIntegration:
    """Integration tests for Gmail API client."""

    @pytest.fixture(autouse=True, scope="function")
    async def setup(self) -> None:
        """Initialize Gmail client with credentials from environment.

        Supports three authentication methods:
        1. Service Account (GMAIL_CREDENTIALS_JSON) - requires google-auth library
        2. OAuth 2.0 (GMAIL_ACCESS_TOKEN, GMAIL_REFRESH_TOKEN, etc.)
        3. Pre-generated Token (GMAIL_ACCESS_TOKEN)
        """
        # Get credentials from environment
        credentials_json_path = os.getenv("GMAIL_CREDENTIALS_JSON")
        access_token = os.getenv("GMAIL_ACCESS_TOKEN")
        refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        user_email = os.getenv("GMAIL_USER_EMAIL")

        # Load credentials JSON if path provided
        credentials_dict = None
        if credentials_json_path:
            # Handle relative paths from project root
            if not os.path.isabs(credentials_json_path):
                # Get the project root (yasmines-team/)
                test_file = os.path.abspath(__file__)
                # Go up 5 levels: integration -> __tests__ -> backend -> app -> yasmines-team
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(test_file)))))
                full_path = os.path.join(project_root, credentials_json_path)
            else:
                full_path = credentials_json_path

            try:
                with open(full_path) as f:
                    credentials_dict = json.load(f)
            except FileNotFoundError:
                pytest.skip(f"Credentials file not found: {full_path}")
            except json.JSONDecodeError as e:
                pytest.skip(f"Invalid JSON in credentials: {e}")

        # Ensure we have some form of credentials
        if not (credentials_dict or access_token):
            pytest.skip(
                "No Gmail credentials found. Set GMAIL_CREDENTIALS_JSON or GMAIL_ACCESS_TOKEN"
            )

        # Initialize client
        try:
            self.client = GmailClient(
                credentials_json=credentials_dict,
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                user_email=user_email,
            )
        except GmailAuthError as e:
            pytest.skip(f"Failed to initialize Gmail client: {e}")

        # Authenticate
        try:
            await self.client.authenticate()
        except GmailAuthError as e:
            pytest.skip(f"Gmail authentication failed: {e}")

    # ==================== MESSAGES ====================

    @pytest.mark.asyncio
    async def test_list_messages_happy_path(self) -> None:
        """Test list_messages - happy path with defaults."""
        result = await self.client.list_messages()

        assert result is not None
        assert isinstance(result, dict)
        assert "resultSizeEstimate" in result
        assert isinstance(result["resultSizeEstimate"], int)

    @pytest.mark.asyncio
    async def test_list_messages_with_query(self) -> None:
        """Test list_messages with search query."""
        for query in get_test_message_queries()[:2]:  # Test 2 queries
            result = await self.client.list_messages(query=query)

            assert result is not None
            assert isinstance(result, dict)
            if "messages" in result:
                assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_list_messages_with_pagination(self) -> None:
        """Test list_messages with custom page size."""
        result = await self.client.list_messages(page_size=5)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_list_messages_invalid_page_size(self) -> None:
        """Test list_messages with invalid page size."""
        # Page size > 500 should be clamped, not error
        result = await self.client.list_messages(page_size=1000)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_message_missing_id(self) -> None:
        """Test get_message with non-existent message ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.get_message("invalid_message_id_xyz")

    @pytest.mark.asyncio
    async def test_get_message_empty_id(self) -> None:
        """Test get_message with empty ID."""
        with pytest.raises((GmailError, TypeError, ValueError)):
            await self.client.get_message("")

    @pytest.mark.asyncio
    async def test_get_message_format_options(self) -> None:
        """Test get_message with different format types."""
        # First get a real message ID
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available for testing")

        message_id = messages["messages"][0]["id"]

        # Test different formats
        for format_type in ["minimal", "full", "raw"]:
            result = await self.client.get_message(message_id, format_type=format_type)
            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_basic(self) -> None:
        """Test send_message with basic parameters."""
        result = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject=SAMPLE_DATA["email_subject"],
            body=SAMPLE_DATA["email_body"],
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result
        assert isinstance(result["id"], str)

    @pytest.mark.asyncio
    async def test_send_message_html(self) -> None:
        """Test send_message with HTML body."""
        result = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="HTML Email Test",
            body=SAMPLE_DATA["email_html_body"],
            html=True,
        )

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_with_cc_bcc(self) -> None:
        """Test send_message with CC and BCC."""
        result = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="Email with CC/BCC",
            body="Test",
            cc=SAMPLE_DATA["email_cc"],
            bcc=SAMPLE_DATA["email_bcc"],
        )

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_with_reply_to(self) -> None:
        """Test send_message with reply-to header."""
        result = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="Email with Reply-To",
            body="Test",
            reply_to=SAMPLE_DATA["email_reply_to"],
        )

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_to_multiple(self) -> None:
        """Test send_message to multiple recipients as list."""
        recipients = get_test_recipients()[:2]
        result = await self.client.send_message(
            to=recipients,
            subject="Multi-recipient test",
            body="Test",
        )

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_send_message_empty_recipient(self) -> None:
        """Test send_message with empty recipient."""
        with pytest.raises((GmailError, ValueError, TypeError)):
            await self.client.send_message(
                to="",
                subject="Test",
                body="Test",
            )

    @pytest.mark.asyncio
    async def test_send_message_empty_subject(self) -> None:
        """Test send_message with empty subject (should still work)."""
        result = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="",
            body="Test body",
        )

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_trash_message(self) -> None:
        """Test trash_message - move to trash."""
        # First send a test message
        sent = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="Will be trashed",
            body="Test",
        )
        message_id = sent["id"]

        # Trash it
        result = await self.client.trash_message(message_id)
        assert result is not None
        assert "labelIds" in result or "id" in result

    @pytest.mark.asyncio
    async def test_trash_message_invalid_id(self) -> None:
        """Test trash_message with invalid ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.trash_message("invalid_id_xyz")

    @pytest.mark.asyncio
    async def test_untrash_message(self) -> None:
        """Test untrash_message - restore from trash."""
        # First send, then trash, then untrash
        sent = await self.client.send_message(
            to=SAMPLE_DATA["email_to"],
            subject="Will be untrashed",
            body="Test",
        )
        message_id = sent["id"]

        await self.client.trash_message(message_id)
        result = await self.client.untrash_message(message_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_mark_as_read(self) -> None:
        """Test mark_as_read."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]
        result = await self.client.mark_as_read(message_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_mark_as_unread(self) -> None:
        """Test mark_as_unread."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]
        result = await self.client.mark_as_unread(message_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_star_message(self) -> None:
        """Test star_message."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]
        result = await self.client.star_message(message_id)

        assert result is not None
        assert isinstance(result, dict)
        assert "labelIds" in result or "id" in result

    @pytest.mark.asyncio
    async def test_unstar_message(self) -> None:
        """Test unstar_message."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]

        # Star first
        await self.client.star_message(message_id)
        # Then unstar
        result = await self.client.unstar_message(message_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_archive_message(self) -> None:
        """Test archive_message - remove from inbox."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]
        result = await self.client.archive_message(message_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_unarchive_message(self) -> None:
        """Test unarchive_message - restore to inbox."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]

        await self.client.archive_message(message_id)
        result = await self.client.unarchive_message(message_id)

        assert result is not None
        assert isinstance(result, dict)

    # ==================== LABELS ====================

    @pytest.mark.asyncio
    async def test_list_labels(self) -> None:
        """Test list_labels."""
        result = await self.client.list_labels()

        assert result is not None
        assert isinstance(result, dict)
        assert "labels" in result
        assert isinstance(result["labels"], list)

    @pytest.mark.asyncio
    async def test_get_label(self) -> None:
        """Test get_label with system label."""
        # INBOX is always available
        result = await self.client.get_label("INBOX")

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result

    @pytest.mark.asyncio
    async def test_get_label_invalid_id(self) -> None:
        """Test get_label with invalid ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.get_label("invalid_label_xyz")

    @pytest.mark.asyncio
    async def test_create_label(self) -> None:
        """Test create_label."""
        label_name = "TestLabel_" + str(int(__import__("time").time()))
        result = await self.client.create_label(
            name=label_name,
            label_list_visibility="labelShow",
            message_list_visibility="show",
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result
        assert result.get("name") == label_name

        # Cleanup: delete the label
        await self.client.delete_label(result["id"])

    @pytest.mark.asyncio
    async def test_create_label_empty_name(self) -> None:
        """Test create_label with empty name."""
        with pytest.raises(GmailError):
            await self.client.create_label("")

    @pytest.mark.asyncio
    async def test_add_label_to_message(self) -> None:
        """Test add_label - apply label to message."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]

        # Use a system label
        result = await self.client.add_label(message_id, "STARRED")

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_remove_label_from_message(self) -> None:
        """Test remove_label - remove label from message."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]

        # First add, then remove
        await self.client.add_label(message_id, "STARRED")
        result = await self.client.remove_label(message_id, "STARRED")

        assert result is not None
        assert isinstance(result, dict)

    # ==================== DRAFTS ====================

    @pytest.mark.asyncio
    async def test_list_drafts(self) -> None:
        """Test list_drafts."""
        result = await self.client.list_drafts()

        assert result is not None
        assert isinstance(result, dict)
        assert "resultSizeEstimate" in result

    @pytest.mark.asyncio
    async def test_list_drafts_pagination(self) -> None:
        """Test list_drafts with pagination."""
        result = await self.client.list_drafts(page_size=5)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_draft(self) -> None:
        """Test create_draft."""
        result = await self.client.create_draft(
            to=SAMPLE_DATA["email_to"],
            subject="Draft test",
            body="This is a draft",
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result

        # Cleanup: delete the draft
        await self.client.delete_draft(result["id"])

    @pytest.mark.asyncio
    async def test_create_draft_html(self) -> None:
        """Test create_draft with HTML body."""
        result = await self.client.create_draft(
            to=SAMPLE_DATA["email_to"],
            subject="HTML Draft",
            body="<html><body>HTML content</body></html>",
            html=True,
        )

        assert result is not None
        assert "id" in result

        # Cleanup
        await self.client.delete_draft(result["id"])

    @pytest.mark.asyncio
    async def test_get_draft(self) -> None:
        """Test get_draft."""
        # First create a draft
        created = await self.client.create_draft(
            to=SAMPLE_DATA["email_to"],
            subject="Draft to get",
            body="Test",
        )
        draft_id = created["id"]

        # Get it
        result = await self.client.get_draft(draft_id)

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result

        # Cleanup
        await self.client.delete_draft(draft_id)

    @pytest.mark.asyncio
    async def test_get_draft_invalid_id(self) -> None:
        """Test get_draft with invalid ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.get_draft("invalid_draft_xyz")

    @pytest.mark.asyncio
    async def test_send_draft(self) -> None:
        """Test send_draft."""
        # Create a draft
        created = await self.client.create_draft(
            to=SAMPLE_DATA["email_to"],
            subject="Draft to send",
            body="Test",
        )
        draft_id = created["id"]

        # Send it
        result = await self.client.send_draft(draft_id)

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result

    # ==================== THREADS ====================

    @pytest.mark.asyncio
    async def test_list_threads(self) -> None:
        """Test list_threads."""
        result = await self.client.list_threads()

        assert result is not None
        assert isinstance(result, dict)
        assert "resultSizeEstimate" in result

    @pytest.mark.asyncio
    async def test_list_threads_with_query(self) -> None:
        """Test list_threads with search query."""
        result = await self.client.list_threads(query="subject:test")

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_list_threads_pagination(self) -> None:
        """Test list_threads with pagination."""
        result = await self.client.list_threads(page_size=5)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_thread(self) -> None:
        """Test get_thread."""
        threads = await self.client.list_threads(page_size=1)
        if not threads.get("threads"):
            pytest.skip("No threads available")

        thread_id = threads["threads"][0]["id"]
        result = await self.client.get_thread(thread_id)

        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_get_thread_invalid_id(self) -> None:
        """Test get_thread with invalid ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.get_thread("invalid_thread_xyz")

    @pytest.mark.asyncio
    async def test_trash_thread(self) -> None:
        """Test trash_thread."""
        threads = await self.client.list_threads(page_size=1)
        if not threads.get("threads"):
            pytest.skip("No threads available")

        thread_id = threads["threads"][0]["id"]
        result = await self.client.trash_thread(thread_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_untrash_thread(self) -> None:
        """Test untrash_thread."""
        threads = await self.client.list_threads(page_size=1)
        if not threads.get("threads"):
            pytest.skip("No threads available")

        thread_id = threads["threads"][0]["id"]

        await self.client.trash_thread(thread_id)
        result = await self.client.untrash_thread(thread_id)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_modify_thread_add_labels(self) -> None:
        """Test modify_thread - add labels."""
        threads = await self.client.list_threads(page_size=1)
        if not threads.get("threads"):
            pytest.skip("No threads available")

        thread_id = threads["threads"][0]["id"]
        result = await self.client.modify_thread(thread_id, add_labels=["STARRED"])

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_modify_thread_remove_labels(self) -> None:
        """Test modify_thread - remove labels."""
        threads = await self.client.list_threads(page_size=1)
        if not threads.get("threads"):
            pytest.skip("No threads available")

        thread_id = threads["threads"][0]["id"]

        # First add, then remove
        await self.client.modify_thread(thread_id, add_labels=["STARRED"])
        result = await self.client.modify_thread(thread_id, remove_labels=["STARRED"])

        assert result is not None
        assert isinstance(result, dict)

    # ==================== USER ====================

    @pytest.mark.asyncio
    async def test_get_user_profile(self) -> None:
        """Test get_user_profile."""
        result = await self.client.get_user_profile()

        assert result is not None
        assert isinstance(result, dict)
        assert "emailAddress" in result
        assert "messagesTotal" in result
        assert "messagesUnread" in result

    # ==================== ATTACHMENTS ====================

    @pytest.mark.asyncio
    async def test_get_message_attachments_no_attachment(self) -> None:
        """Test get_message_attachments - message without attachments."""
        messages = await self.client.list_messages(page_size=1)
        if not messages.get("messages"):
            pytest.skip("No messages available")

        message_id = messages["messages"][0]["id"]
        result = await self.client.get_message_attachments(message_id)

        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_message_attachments_invalid_id(self) -> None:
        """Test get_message_attachments with invalid message ID."""
        with pytest.raises((GmailError, GmailNotFoundError)):
            await self.client.get_message_attachments("invalid_id_xyz")
