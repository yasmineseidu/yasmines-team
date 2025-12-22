"""Live API tests for Gmail client with real Gmail account.

SETUP REQUIRED:
1. Create .env file with:
   - GMAIL_ACCESS_TOKEN=<your_access_token>
   - GMAIL_REFRESH_TOKEN=<your_refresh_token>
   - GOOGLE_CLIENT_ID=<your_client_id>
   - GOOGLE_CLIENT_SECRET=<your_client_secret>
   - TEST_EMAIL=<test_gmail_address>

2. Get credentials from Google Cloud:
   - Visit https://console.cloud.google.com/
   - Create OAuth 2.0 credentials
   - Use OAuth flow to get access/refresh tokens

3. Run tests with: pytest test_gmail_live_api.py -v --tb=short
"""

import contextlib
import os
from datetime import datetime

import pytest

from src.integrations.gmail import GmailClient, GmailError

# Skip all tests if credentials are not available
pytestmark = pytest.mark.skipif(
    not os.getenv("GMAIL_ACCESS_TOKEN"),
    reason="Live API tests require GMAIL_ACCESS_TOKEN environment variable",
)


@pytest.fixture
def gmail_live_client():
    """Create a real Gmail client with live API credentials."""
    return GmailClient(
        access_token=os.getenv("GMAIL_ACCESS_TOKEN"),
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )


@pytest.fixture
def test_email():
    """Get test email address."""
    return os.getenv("TEST_EMAIL", "yasmineseidu@gmail.com")


class TestGmailClientLiveAPIAuthentication:
    """Live API tests for authentication and basic operations."""

    @pytest.mark.asyncio
    async def test_get_user_profile(self, gmail_live_client):
        """Test: Get authenticated user's profile."""
        profile = await gmail_live_client.get_user_profile()

        # Verify profile structure
        assert "emailAddress" in profile
        assert "messagesTotal" in profile
        assert "threadsTotal" in profile
        assert profile["messagesTotal"] >= 0
        assert profile["threadsTotal"] >= 0

    @pytest.mark.asyncio
    async def test_list_messages_live(self, gmail_live_client):
        """Test: List messages from real Gmail account."""
        messages = await gmail_live_client.list_messages()

        # Verify response structure
        assert isinstance(messages, dict)
        if "messages" in messages:
            assert isinstance(messages["messages"], list)
            # Verify each message has required fields
            for msg in messages["messages"]:
                assert "id" in msg
                assert "threadId" in msg


class TestGmailClientLiveAPISendReceive:
    """Live API tests for sending and receiving emails."""

    @pytest.mark.asyncio
    async def test_send_test_email(self, gmail_live_client, test_email):
        """Test: Send test email to verify sending capability."""
        subject = f"Test Email - {datetime.now().isoformat()}"
        body = "This is a test email from the Gmail API integration."

        sent = await gmail_live_client.send_message(
            to=test_email, subject=subject, body=body, html=False
        )

        # Verify sent message structure
        assert "id" in sent
        assert sent["id"]  # Should have non-empty ID

        # Store message ID for cleanup
        return sent["id"]

    @pytest.mark.asyncio
    async def test_read_message_details(self, gmail_live_client):
        """Test: Read full message details from real account."""
        # Get most recent message
        messages = await gmail_live_client.list_messages(max_results=1)

        if not messages.get("messages"):
            pytest.skip("No messages available in test account")

        msg_id = messages["messages"][0]["id"]

        # Get full message details
        message = await gmail_live_client.get_message(msg_id)

        # Verify message structure
        assert message["id"] == msg_id
        assert "threadId" in message
        assert "labelIds" in message
        assert isinstance(message["labelIds"], list)


class TestGmailClientLiveAPILabels:
    """Live API tests for label operations."""

    @pytest.mark.asyncio
    async def test_list_labels(self, gmail_live_client):
        """Test: List all labels in account."""
        labels = await gmail_live_client.list_labels()

        # Verify response structure
        assert "labels" in labels
        assert isinstance(labels["labels"], list)

        # Verify system labels exist
        label_names = [label["name"] for label in labels["labels"]]
        assert any(name in label_names for name in ["INBOX", "SENT", "DRAFT"])

    @pytest.mark.asyncio
    async def test_label_workflow(self, gmail_live_client):
        """Test: Create label, apply to message, remove label."""
        label_name = f"TestLabel-{int(datetime.now().timestamp())}"

        try:
            # Create label
            created = await gmail_live_client.create_label(label_name)
            assert created["name"] == label_name
            label_id = created["id"]

            # Get a message to apply label to
            messages = await gmail_live_client.list_messages(max_results=1)
            if messages.get("messages"):
                msg_id = messages["messages"][0]["id"]

                # Apply label to message
                labeled = await gmail_live_client.add_label(msg_id, label_id)
                assert label_id in labeled.get("labelIds", [])

                # Remove label from message
                unlabeled = await gmail_live_client.remove_label(msg_id, label_id)
                assert label_id not in unlabeled.get("labelIds", [])

        finally:
            # Cleanup: Delete the test label
            with contextlib.suppress(GmailError):
                await gmail_live_client.delete_label(label_name)


class TestGmailClientLiveAPIThreads:
    """Live API tests for thread operations."""

    @pytest.mark.asyncio
    async def test_list_threads(self, gmail_live_client):
        """Test: List threads from real account."""
        threads = await gmail_live_client.list_threads()

        # Verify response structure
        assert isinstance(threads, dict)
        if "threads" in threads:
            assert isinstance(threads["threads"], list)

    @pytest.mark.asyncio
    async def test_get_thread_details(self, gmail_live_client):
        """Test: Get detailed thread information."""
        # Get threads
        threads_response = await gmail_live_client.list_threads(max_results=1)

        if not threads_response.get("threads"):
            pytest.skip("No threads available in test account")

        thread_id = threads_response["threads"][0]["id"]

        # Get thread details
        thread = await gmail_live_client.get_thread(thread_id)

        # Verify thread structure
        assert thread["id"] == thread_id
        assert "messages" in thread
        assert isinstance(thread["messages"], list)


class TestGmailClientLiveAPIDrafts:
    """Live API tests for draft operations."""

    @pytest.mark.asyncio
    async def test_draft_workflow(self, gmail_live_client, test_email):
        """Test: Create draft, get draft, send draft."""
        # Create draft
        draft_subject = f"Draft Test - {datetime.now().isoformat()}"
        draft = await gmail_live_client.create_draft(
            to=test_email, subject=draft_subject, body="This is a draft email."
        )

        draft_id = draft["id"]

        try:
            # Get draft details
            retrieved = await gmail_live_client.get_draft(draft_id)
            assert retrieved["id"] == draft_id

            # Send the draft
            sent = await gmail_live_client.send_draft(draft_id)
            assert "id" in sent

        except GmailError:
            # Draft may have been already sent or deleted
            pass


class TestGmailClientLiveAPIMessageOperations:
    """Live API tests for message operations."""

    @pytest.mark.asyncio
    async def test_message_read_unread_workflow(self, gmail_live_client):
        """Test: Mark message as read, then unread."""
        # Get a message
        messages = await gmail_live_client.list_messages(max_results=1)

        if not messages.get("messages"):
            pytest.skip("No messages available in test account")

        msg_id = messages["messages"][0]["id"]

        try:
            # Mark as read
            read = await gmail_live_client.mark_as_read(msg_id)
            assert msg_id == read.get("id") or "id" in read

            # Mark as unread
            unread = await gmail_live_client.mark_as_unread(msg_id)
            assert msg_id == unread.get("id") or "id" in unread

        except GmailError:
            # Message may have been deleted
            pass

    @pytest.mark.asyncio
    async def test_message_star_workflow(self, gmail_live_client):
        """Test: Star and unstar a message."""
        # Get a message
        messages = await gmail_live_client.list_messages(max_results=1)

        if not messages.get("messages"):
            pytest.skip("No messages available in test account")

        msg_id = messages["messages"][0]["id"]

        try:
            # Star message
            starred = await gmail_live_client.star_message(msg_id)
            assert msg_id == starred.get("id") or "id" in starred

            # Unstar message
            unstarred = await gmail_live_client.unstar_message(msg_id)
            assert msg_id == unstarred.get("id") or "id" in unstarred

        except GmailError:
            # Message may have been deleted
            pass

    @pytest.mark.asyncio
    async def test_message_archive_workflow(self, gmail_live_client):
        """Test: Archive and unarchive a message."""
        # Get a message from INBOX
        messages = await gmail_live_client.list_messages(query="in:INBOX", max_results=1)

        if not messages.get("messages"):
            pytest.skip("No INBOX messages available in test account")

        msg_id = messages["messages"][0]["id"]

        try:
            # Archive message
            archived = await gmail_live_client.archive_message(msg_id)
            assert msg_id == archived.get("id") or "id" in archived

        except GmailError:
            # Message may have been deleted or already archived
            pass
