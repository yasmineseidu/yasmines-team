"""Gmail API tools for agent use.

Provides agent-friendly tool wrappers for Gmail operations.
Each tool manages its own client lifecycle.
"""

import logging
from typing import Any

from .client import GmailClient

logger = logging.getLogger(__name__)


# ==================== MESSAGE OPERATIONS ====================


async def list_messages_tool(
    query: str | None = None,
    label_ids: list[str] | None = None,
    page_size: int = 10,
    page_token: str | None = None,
) -> dict[str, Any]:
    """List messages from Gmail inbox with optional filtering.

    Args:
        query: Gmail search query (e.g., "from:user@example.com", "has:attachment").
        label_ids: Filter by specific label IDs.
        page_size: Number of results per page (1-500).
        page_token: Token for pagination to next page.

    Returns:
        Dict containing messages list and next page token.

    Raises:
        GmailError: If API call fails.
    """
    client = GmailClient()

    try:
        result = await client.list_messages(
            query=query,
            label_ids=label_ids,
            page_size=page_size,
            page_token=page_token,
        )
        return result
    finally:
        await client.close()


async def get_message_tool(message_id: str, format_type: str = "full") -> dict[str, Any]:
    """Retrieve full message content and metadata.

    Args:
        message_id: Gmail message ID.
        format_type: Format for content ("minimal", "full", "raw").

    Returns:
        Dict with full message content, headers, and body.

    Raises:
        GmailError: If message not found or API call fails.
    """
    client = GmailClient()

    try:
        result = await client.get_message(message_id, format_type)
        return result
    finally:
        await client.close()


async def send_message_tool(
    to: str,
    subject: str,
    body: str,
    html: bool = False,
    cc: str | None = None,
    bcc: str | None = None,
) -> dict[str, Any]:
    """Send email message.

    Args:
        to: Recipient email address or comma-separated list.
        subject: Email subject line.
        body: Email body text or HTML content.
        html: If True, body is treated as HTML.
        cc: CC recipient(s).
        bcc: BCC recipient(s).

    Returns:
        Dict with sent message ID.

    Raises:
        GmailError: If send fails.
    """
    client = GmailClient()

    try:
        result = await client.send_message(
            to=to, subject=subject, body=body, html=html, cc=cc, bcc=bcc
        )
        logger.info(f"Sent message to {to} with subject: {subject[:50]}")
        return result
    finally:
        await client.close()


async def delete_message_tool(message_id: str) -> dict[str, Any]:
    """Permanently delete message.

    Args:
        message_id: ID of message to delete.

    Returns:
        Empty response dict.

    Raises:
        GmailError: If deletion fails.
    """
    client = GmailClient()

    try:
        result = await client.delete_message(message_id)
        logger.info(f"Deleted message {message_id}")
        return result
    finally:
        await client.close()


async def trash_message_tool(message_id: str) -> dict[str, Any]:
    """Move message to trash folder.

    Args:
        message_id: ID of message to trash.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.trash_message(message_id)
        logger.info(f"Trashed message {message_id}")
        return result
    finally:
        await client.close()


async def untrash_message_tool(message_id: str) -> dict[str, Any]:
    """Restore message from trash.

    Args:
        message_id: ID of message to restore.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.untrash_message(message_id)
        logger.info(f"Restored message {message_id}")
        return result
    finally:
        await client.close()


async def mark_as_read_tool(message_id: str) -> dict[str, Any]:
    """Mark message as read.

    Args:
        message_id: ID of message to mark as read.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.mark_as_read(message_id)
        logger.info(f"Marked message {message_id} as read")
        return result
    finally:
        await client.close()


async def mark_as_unread_tool(message_id: str) -> dict[str, Any]:
    """Mark message as unread.

    Args:
        message_id: ID of message to mark as unread.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.mark_as_unread(message_id)
        logger.info(f"Marked message {message_id} as unread")
        return result
    finally:
        await client.close()


async def star_message_tool(message_id: str) -> dict[str, Any]:
    """Star/flag message for later.

    Args:
        message_id: ID of message to star.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.star_message(message_id)
        logger.info(f"Starred message {message_id}")
        return result
    finally:
        await client.close()


async def unstar_message_tool(message_id: str) -> dict[str, Any]:
    """Remove star from message.

    Args:
        message_id: ID of message to unstar.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.unstar_message(message_id)
        logger.info(f"Unstarred message {message_id}")
        return result
    finally:
        await client.close()


async def archive_message_tool(message_id: str) -> dict[str, Any]:
    """Archive message (remove from inbox).

    Args:
        message_id: ID of message to archive.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.archive_message(message_id)
        logger.info(f"Archived message {message_id}")
        return result
    finally:
        await client.close()


async def unarchive_message_tool(message_id: str) -> dict[str, Any]:
    """Restore archived message to inbox.

    Args:
        message_id: ID of message to restore.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.unarchive_message(message_id)
        logger.info(f"Unarchived message {message_id}")
        return result
    finally:
        await client.close()


# ==================== LABEL OPERATIONS ====================


async def list_labels_tool() -> dict[str, Any]:
    """List all available labels in Gmail account.

    Returns:
        Dict with labels list including system and custom labels.

    Raises:
        GmailError: If API call fails.
    """
    client = GmailClient()

    try:
        result = await client.list_labels()
        return result
    finally:
        await client.close()


async def get_label_tool(label_id: str) -> dict[str, Any]:
    """Get label details including message and thread counts.

    Args:
        label_id: ID of label to retrieve.

    Returns:
        Dict with label information.

    Raises:
        GmailError: If label not found.
    """
    client = GmailClient()

    try:
        result = await client.get_label(label_id)
        return result
    finally:
        await client.close()


async def create_label_tool(
    name: str,
    label_list_visibility: str = "labelShow",
    message_list_visibility: str = "show",
) -> dict[str, Any]:
    """Create new custom label.

    Args:
        name: Name for the new label.
        label_list_visibility: Show/hide in label list ("labelShow", "labelHide").
        message_list_visibility: Show/hide in message list ("show", "hide").

    Returns:
        Dict with new label details.

    Raises:
        GmailError: If creation fails.
    """
    client = GmailClient()

    try:
        result = await client.create_label(name, label_list_visibility, message_list_visibility)
        logger.info(f"Created label: {name}")
        return result
    finally:
        await client.close()


async def delete_label_tool(label_id: str) -> dict[str, Any]:
    """Delete label (cannot delete system labels).

    Args:
        label_id: ID of label to delete.

    Returns:
        Empty response dict.

    Raises:
        GmailError: If deletion fails.
    """
    client = GmailClient()

    try:
        result = await client.delete_label(label_id)
        logger.info(f"Deleted label {label_id}")
        return result
    finally:
        await client.close()


async def add_label_tool(message_id: str, label_id: str) -> dict[str, Any]:
    """Apply label to message.

    Args:
        message_id: ID of message to label.
        label_id: ID of label to apply.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.add_label(message_id, label_id)
        logger.info(f"Added label {label_id} to message {message_id}")
        return result
    finally:
        await client.close()


async def remove_label_tool(message_id: str, label_id: str) -> dict[str, Any]:
    """Remove label from message.

    Args:
        message_id: ID of message.
        label_id: ID of label to remove.

    Returns:
        Updated message dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.remove_label(message_id, label_id)
        logger.info(f"Removed label {label_id} from message {message_id}")
        return result
    finally:
        await client.close()


# ==================== DRAFT OPERATIONS ====================


async def list_drafts_tool(page_size: int = 10, page_token: str | None = None) -> dict[str, Any]:
    """List draft messages.

    Args:
        page_size: Number of drafts per page.
        page_token: Token for pagination.

    Returns:
        Dict with drafts list and next page token.

    Raises:
        GmailError: If API call fails.
    """
    client = GmailClient()

    try:
        result = await client.list_drafts(page_size, page_token)
        return result
    finally:
        await client.close()


async def get_draft_tool(draft_id: str) -> dict[str, Any]:
    """Get draft message details and content.

    Args:
        draft_id: ID of draft to retrieve.

    Returns:
        Dict with draft information and message content.

    Raises:
        GmailError: If draft not found.
    """
    client = GmailClient()

    try:
        result = await client.get_draft(draft_id)
        return result
    finally:
        await client.close()


async def create_draft_tool(to: str, subject: str, body: str, html: bool = False) -> dict[str, Any]:
    """Create draft email (not sent).

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body text or HTML.
        html: If True, body is treated as HTML.

    Returns:
        Dict with new draft ID.

    Raises:
        GmailError: If creation fails.
    """
    client = GmailClient()

    try:
        result = await client.create_draft(to, subject, body, html)
        logger.info(f"Created draft for {to}")
        return result
    finally:
        await client.close()


async def send_draft_tool(draft_id: str) -> dict[str, Any]:
    """Send existing draft message.

    Args:
        draft_id: ID of draft to send.

    Returns:
        Dict with sent message ID.

    Raises:
        GmailError: If send fails.
    """
    client = GmailClient()

    try:
        result = await client.send_draft(draft_id)
        logger.info(f"Sent draft {draft_id}")
        return result
    finally:
        await client.close()


async def delete_draft_tool(draft_id: str) -> dict[str, Any]:
    """Delete draft message.

    Args:
        draft_id: ID of draft to delete.

    Returns:
        Empty response dict.

    Raises:
        GmailError: If deletion fails.
    """
    client = GmailClient()

    try:
        result = await client.delete_draft(draft_id)
        logger.info(f"Deleted draft {draft_id}")
        return result
    finally:
        await client.close()


# ==================== THREAD OPERATIONS ====================


async def list_threads_tool(
    query: str | None = None,
    label_ids: list[str] | None = None,
    page_size: int = 10,
    page_token: str | None = None,
) -> dict[str, Any]:
    """List conversation threads.

    Args:
        query: Gmail search query to filter threads.
        label_ids: Filter by label IDs.
        page_size: Number of threads per page.
        page_token: Token for pagination.

    Returns:
        Dict with threads list and next page token.

    Raises:
        GmailError: If API call fails.
    """
    client = GmailClient()

    try:
        result = await client.list_threads(query, label_ids, page_size, page_token)
        return result
    finally:
        await client.close()


async def get_thread_tool(thread_id: str) -> dict[str, Any]:
    """Get complete thread with all messages in conversation.

    Args:
        thread_id: ID of thread to retrieve.

    Returns:
        Dict with thread and all message content.

    Raises:
        GmailError: If thread not found.
    """
    client = GmailClient()

    try:
        result = await client.get_thread(thread_id)
        return result
    finally:
        await client.close()


async def delete_thread_tool(thread_id: str) -> dict[str, Any]:
    """Permanently delete entire thread.

    Args:
        thread_id: ID of thread to delete.

    Returns:
        Empty response dict.

    Raises:
        GmailError: If deletion fails.
    """
    client = GmailClient()

    try:
        result = await client.delete_thread(thread_id)
        logger.info(f"Deleted thread {thread_id}")
        return result
    finally:
        await client.close()


async def trash_thread_tool(thread_id: str) -> dict[str, Any]:
    """Move entire thread to trash.

    Args:
        thread_id: ID of thread to trash.

    Returns:
        Updated thread dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.trash_thread(thread_id)
        logger.info(f"Trashed thread {thread_id}")
        return result
    finally:
        await client.close()


async def untrash_thread_tool(thread_id: str) -> dict[str, Any]:
    """Restore thread from trash.

    Args:
        thread_id: ID of thread to restore.

    Returns:
        Updated thread dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.untrash_thread(thread_id)
        logger.info(f"Restored thread {thread_id}")
        return result
    finally:
        await client.close()


async def modify_thread_tool(
    thread_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Add or remove labels from entire thread.

    Args:
        thread_id: ID of thread to modify.
        add_labels: List of label IDs to add.
        remove_labels: List of label IDs to remove.

    Returns:
        Updated thread dict.

    Raises:
        GmailError: If operation fails.
    """
    client = GmailClient()

    try:
        result = await client.modify_thread(thread_id, add_labels, remove_labels)
        logger.info(f"Modified thread {thread_id}")
        return result
    finally:
        await client.close()


# ==================== USER OPERATIONS ====================


async def get_user_profile_tool() -> dict[str, Any]:
    """Get authenticated user's Gmail profile information.

    Returns:
        Dict with email address and message/thread counts.

    Raises:
        GmailError: If API call fails.
    """
    client = GmailClient()

    try:
        result = await client.get_user_profile()
        return result
    finally:
        await client.close()


# ==================== ATTACHMENT OPERATIONS ====================


async def get_message_attachments_tool(message_id: str) -> list[dict[str, Any]]:
    """Get list of attachments in message.

    Args:
        message_id: ID of message to check for attachments.

    Returns:
        List of attachment metadata dicts with filename and MIME type.

    Raises:
        GmailError: If message not found.
    """
    client = GmailClient()

    try:
        result = await client.get_message_attachments(message_id)
        return result
    finally:
        await client.close()


async def download_attachment_tool(message_id: str, attachment_id: str) -> dict[str, Any]:
    """Download attachment content.

    Args:
        message_id: ID of message containing attachment.
        attachment_id: ID of attachment to download.

    Returns:
        Dict with attachment data encoded as base64.

    Raises:
        GmailError: If download fails.
    """
    client = GmailClient()

    try:
        data = await client.download_attachment(message_id, attachment_id)
        logger.info(f"Downloaded attachment {attachment_id} from message {message_id}")
        return {"data": data.hex(), "size": len(data)}
    finally:
        await client.close()


async def send_message_with_attachment_tool(
    to: str, subject: str, body: str, attachment_path: str
) -> dict[str, Any]:
    """Send email with file attachment.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body text.
        attachment_path: Full path to file to attach.

    Returns:
        Dict with sent message ID.

    Raises:
        GmailError: If send fails or file not found.
    """
    client = GmailClient()

    try:
        result = await client.send_message_with_attachment(to, subject, body, attachment_path)
        logger.info(f"Sent message to {to} with attachment")
        return result
    finally:
        await client.close()
