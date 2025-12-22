"""Gmail API integration module.

Provides complete Gmail API client, models, exceptions, and tools
for email operations, label management, and attachment handling.

Example:
    >>> from src.integrations.gmail import GmailClient, send_message_tool
    >>> client = GmailClient(access_token="ya29...")
    >>> await client.send_message(to="user@example.com", subject="Hello", body="Test")
    >>> result = await send_message_tool(to="user@example.com", subject="Hello", body="Test")
"""

from .client import GmailClient
from .exceptions import (
    GmailAuthError,
    GmailError,
    GmailNotFoundError,
    GmailQuotaExceeded,
    GmailRateLimitError,
)
from .models import (
    GmailAttachment,
    GmailDraft,
    GmailLabel,
    GmailMessage,
    GmailMessagePart,
    GmailProfile,
    GmailThread,
)
from .tools import (
    add_label_tool,
    archive_message_tool,
    create_draft_tool,
    create_label_tool,
    delete_draft_tool,
    delete_label_tool,
    delete_message_tool,
    delete_thread_tool,
    download_attachment_tool,
    get_draft_tool,
    get_label_tool,
    get_message_attachments_tool,
    get_message_tool,
    get_thread_tool,
    get_user_profile_tool,
    list_drafts_tool,
    list_labels_tool,
    list_messages_tool,
    list_threads_tool,
    mark_as_read_tool,
    mark_as_unread_tool,
    modify_thread_tool,
    remove_label_tool,
    send_draft_tool,
    send_message_tool,
    send_message_with_attachment_tool,
    star_message_tool,
    trash_message_tool,
    trash_thread_tool,
    unarchive_message_tool,
    unstar_message_tool,
    untrash_message_tool,
    untrash_thread_tool,
)

__all__ = [
    # Client
    "GmailClient",
    # Models
    "GmailMessage",
    "GmailLabel",
    "GmailDraft",
    "GmailThread",
    "GmailProfile",
    "GmailAttachment",
    "GmailMessagePart",
    # Exceptions
    "GmailError",
    "GmailAuthError",
    "GmailRateLimitError",
    "GmailQuotaExceeded",
    "GmailNotFoundError",
    # Tools
    "list_messages_tool",
    "get_message_tool",
    "send_message_tool",
    "delete_message_tool",
    "trash_message_tool",
    "untrash_message_tool",
    "mark_as_read_tool",
    "mark_as_unread_tool",
    "star_message_tool",
    "unstar_message_tool",
    "archive_message_tool",
    "unarchive_message_tool",
    "list_labels_tool",
    "get_label_tool",
    "create_label_tool",
    "delete_label_tool",
    "add_label_tool",
    "remove_label_tool",
    "list_drafts_tool",
    "get_draft_tool",
    "create_draft_tool",
    "send_draft_tool",
    "delete_draft_tool",
    "list_threads_tool",
    "get_thread_tool",
    "delete_thread_tool",
    "trash_thread_tool",
    "untrash_thread_tool",
    "modify_thread_tool",
    "get_user_profile_tool",
    "get_message_attachments_tool",
    "download_attachment_tool",
    "send_message_with_attachment_tool",
]
