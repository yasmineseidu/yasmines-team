"""
Approval workflow service.

Provides business logic for managing approval requests through Telegram.
Handles creating, updating, and retrieving approval requests with
full audit trail support.

Example:
    >>> from src.services.approval_service import ApprovalService
    >>> from src.integrations.telegram import TelegramClient
    >>> telegram = TelegramClient(bot_token="...")
    >>> service = ApprovalService(telegram_client=telegram)
    >>> request_id = await service.send_approval_request(
    ...     request_data={
    ...         "title": "Q4 Budget",
    ...         "content": "Marketing budget approval",
    ...         "requester_id": 123,
    ...         "approver_id": 456,
    ...         "telegram_chat_id": 789,
    ...         "content_type": "budget",
    ...         "data": {"amount": 50000}
    ...     }
    ... )
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramClient,
    TelegramError,
)
from src.models.approval import (
    ApprovalAction,
    ApprovalContentType,
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
)

logger = logging.getLogger(__name__)


class DatabaseConnection(Protocol):
    """Protocol for database connection interface."""

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute a query."""
        ...

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row."""
        ...

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows."""
        ...


class InMemoryDatabase:
    """
    In-memory database for development and testing.

    Stores approval requests and history in memory.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self.requests: dict[str, dict[str, Any]] = {}
        self.history: dict[str, dict[str, Any]] = {}

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute a query (simulated)."""
        return None

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row (simulated)."""
        return None

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows (simulated)."""
        return []

    async def insert_request(self, data: dict[str, Any]) -> str:
        """Insert approval request."""
        request_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        self.requests[request_id] = {
            **data,
            "id": request_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        return request_id

    async def get_request(self, request_id: str) -> dict[str, Any] | None:
        """Get approval request by ID."""
        return self.requests.get(request_id)

    async def update_request(self, request_id: str, updates: dict[str, Any]) -> bool:
        """Update approval request."""
        if request_id not in self.requests:
            return False
        self.requests[request_id].update(updates)
        self.requests[request_id]["updated_at"] = datetime.now(UTC)
        return True

    async def insert_history(self, data: dict[str, Any]) -> str:
        """Insert history record."""
        history_id = str(uuid.uuid4())
        self.history[history_id] = {
            **data,
            "id": history_id,
            "created_at": datetime.now(UTC),
        }
        return history_id

    async def get_pending_by_approver(self, approver_id: int) -> list[dict[str, Any]]:
        """Get pending requests for approver."""
        return [
            r
            for r in self.requests.values()
            if r.get("approver_id") == approver_id and r.get("status") == "pending"
        ]

    async def get_request_by_edit_token(self, token: str) -> dict[str, Any] | None:
        """Get request by edit token."""
        for r in self.requests.values():
            if r.get("edit_token") == token:
                return r
        return None


class ApprovalService:
    """
    Service for managing approval workflows.

    Coordinates between Telegram messaging and database persistence
    to provide a complete approval workflow system.

    Attributes:
        telegram_client: TelegramClient instance for messaging.
        db: Database connection for persistence.
        edit_form_base_url: Base URL for edit forms.
        edit_token_expiry_hours: Hours until edit token expires.
    """

    def __init__(
        self,
        telegram_client: TelegramClient,
        db: DatabaseConnection | InMemoryDatabase | None = None,
        edit_form_base_url: str = "https://app.example.com/approvals",
        edit_token_expiry_hours: int = 24,
    ) -> None:
        """
        Initialize the approval service.

        Args:
            telegram_client: Configured TelegramClient instance.
            db: Database connection (uses in-memory if not provided).
            edit_form_base_url: Base URL for edit form links.
            edit_token_expiry_hours: Hours until edit tokens expire.
        """
        self.telegram_client = telegram_client
        self.db: DatabaseConnection | InMemoryDatabase = db or InMemoryDatabase()
        self.edit_form_base_url = edit_form_base_url.rstrip("/")
        self.edit_token_expiry_hours = edit_token_expiry_hours
        logger.info("Initialized ApprovalService")

    async def send_approval_request(
        self,
        request_data: dict[str, Any],
    ) -> str:
        """
        Send a new approval request via Telegram.

        Creates a database record, formats the message, builds the
        interactive keyboard, and sends to the approver's chat.

        Args:
            request_data: Dictionary containing:
                - title: Request title (required)
                - content: Request content (required)
                - requester_id: User ID of requester (required)
                - approver_id: User ID of approver (required)
                - telegram_chat_id: Chat ID to send to (required)
                - content_type: Type of content (optional, default: custom)
                - data: Additional data dict (optional)
                - expires_at: Expiration datetime (optional)

        Returns:
            Request ID (UUID string).

        Raises:
            ValueError: If request_data is invalid.
            TelegramError: If message sending fails.
        """
        # Validate input
        create_request = ApprovalRequestCreate(
            title=request_data.get("title", ""),
            content=request_data.get("content", ""),
            requester_id=request_data.get("requester_id", 0),
            approver_id=request_data.get("approver_id", 0),
            telegram_chat_id=request_data.get("telegram_chat_id", 0),
            content_type=ApprovalContentType(request_data.get("content_type", "custom")),
            data=request_data.get("data", {}),
            expires_at=request_data.get("expires_at"),
        )

        errors = create_request.validate()
        if errors:
            raise ValueError(f"Invalid request data: {'; '.join(errors)}")

        # Create database record
        request_id = await self.db.insert_request(create_request.to_dict())

        logger.info(f"Created approval request {request_id}: {create_request.title}")

        # Format message
        message_text = self.format_approval_message(
            title=create_request.title,
            content=create_request.content,
            content_type=create_request.content_type,
            data=create_request.data,
        )

        # Build keyboard
        keyboard = self.build_approval_buttons(request_id)

        # Send Telegram message
        try:
            message = await self.telegram_client.send_message(
                chat_id=create_request.telegram_chat_id,
                text=message_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )

            # Update record with message ID
            await self.db.update_request(
                request_id,
                {"telegram_message_id": message.message_id},
            )

            logger.info(f"Sent approval request {request_id} as message {message.message_id}")

        except TelegramError as e:
            logger.error(f"Failed to send approval request {request_id}: {e}")
            raise

        return request_id

    def format_approval_message(
        self,
        title: str,
        content: str,
        content_type: ApprovalContentType = ApprovalContentType.CUSTOM,
        data: dict[str, Any] | None = None,
    ) -> str:
        """
        Format approval request as HTML message.

        Args:
            title: Request title.
            content: Request content/description.
            content_type: Type of approval content.
            data: Additional data for type-specific formatting.

        Returns:
            Formatted HTML message string.
        """
        data = data or {}
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # Build message based on content type
        if content_type == ApprovalContentType.BUDGET:
            amount = data.get("amount", 0)
            department = data.get("department", "General")
            formatted_amount = f"${amount:,.2f}" if isinstance(amount, int | float) else amount
            return (
                f"<b>APPROVAL REQUEST</b>\n"
                f"{'=' * 30}\n\n"
                f"<b>Title:</b> {title}\n"
                f"<b>Type:</b> Budget Approval\n"
                f"<b>Department:</b> {department}\n"
                f"<b>Amount:</b> {formatted_amount}\n\n"
                f"<b>Details:</b>\n{content}\n\n"
                f"<i>Requested at: {timestamp}</i>"
            )

        elif content_type == ApprovalContentType.DOCUMENT:
            file_url = data.get("file_url", "")
            document_type = data.get("document_type", "Document")
            message = (
                f"<b>APPROVAL REQUEST</b>\n"
                f"{'=' * 30}\n\n"
                f"<b>Title:</b> {title}\n"
                f"<b>Type:</b> {document_type} Review\n\n"
                f"<b>Details:</b>\n{content}\n"
            )
            if file_url:
                message += f'\n<a href="{file_url}">View Document</a>\n'
            message += f"\n<i>Requested at: {timestamp}</i>"
            return message

        elif content_type == ApprovalContentType.CONTENT:
            tags = data.get("tags", [])
            tags_str = ", ".join(tags) if tags else "None"
            return (
                f"<b>CONTENT APPROVAL REQUEST</b>\n"
                f"{'=' * 30}\n\n"
                f"<b>Title:</b> {title}\n"
                f"<b>Tags:</b> {tags_str}\n\n"
                f"<b>Content:</b>\n{content}\n\n"
                f"<i>Requested at: {timestamp}</i>"
            )

        else:  # CUSTOM
            return (
                f"<b>APPROVAL REQUEST</b>\n"
                f"{'=' * 30}\n\n"
                f"<b>Title:</b> {title}\n\n"
                f"<b>Details:</b>\n{content}\n\n"
                f"<i>Requested at: {timestamp}</i>"
            )

    def build_approval_buttons(
        self,
        request_id: str,
        include_edit: bool = True,
        include_view: bool = True,
    ) -> InlineKeyboardMarkup:
        """
        Build inline keyboard for approval actions.

        Args:
            request_id: ID of the approval request.
            include_edit: Whether to include edit button.
            include_view: Whether to include view details button.

        Returns:
            InlineKeyboardMarkup with approve/disapprove/edit buttons.
        """
        buttons: list[list[InlineKeyboardButton]] = []

        # Row 1: Approve and Disapprove
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Approve",
                    callback_data=f"approve_{request_id}",
                ),
                InlineKeyboardButton(
                    text="Disapprove",
                    callback_data=f"disapprove_{request_id}",
                ),
            ]
        )

        # Row 2: Edit
        if include_edit:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="Edit",
                        callback_data=f"edit_{request_id}",
                    ),
                ]
            )

        # Row 3: View Details (URL button)
        if include_view:
            view_url = f"{self.edit_form_base_url}/{request_id}/view"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="View Details",
                        url=view_url,
                    ),
                ]
            )

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def update_approval_status(
        self,
        request_id: str,
        status: ApprovalStatus,
        actor_id: int,
        actor_username: str | None = None,
        comment: str | None = None,
        action_data: dict[str, Any] | None = None,
        telegram_callback_query_id: str | None = None,
    ) -> bool:
        """
        Update the status of an approval request.

        Updates the database record and creates a history entry
        for the audit trail.

        Args:
            request_id: ID of the approval request.
            status: New status to set.
            actor_id: ID of user taking the action.
            actor_username: Username of the actor.
            comment: Optional comment/reason for action.
            action_data: Additional data about the action.
            telegram_callback_query_id: Callback query ID from Telegram.

        Returns:
            True if update succeeded, False otherwise.
        """
        # Get current request
        request_data = await self.db.get_request(request_id)
        if not request_data:
            logger.warning(f"Approval request {request_id} not found")
            return False

        previous_status = ApprovalStatus(request_data.get("status", "pending"))

        # Determine action based on status change
        action = ApprovalAction.APPROVE
        if status == ApprovalStatus.APPROVED:
            action = ApprovalAction.APPROVE
        elif status == ApprovalStatus.DISAPPROVED:
            action = ApprovalAction.DISAPPROVE
        elif status == ApprovalStatus.EDITING:
            action = ApprovalAction.EDIT
        elif status == ApprovalStatus.CANCELLED:
            action = ApprovalAction.CANCEL
        elif status == ApprovalStatus.EXPIRED:
            action = ApprovalAction.EXPIRE

        # Update request
        success = await self.db.update_request(
            request_id,
            {"status": status.value},
        )
        if not success:
            logger.error(f"Failed to update approval request {request_id}")
            return False

        # Create history entry
        history_data = {
            "request_id": request_id,
            "action": action.value,
            "actor_id": actor_id,
            "actor_username": actor_username,
            "comment": comment,
            "edited_data": action_data,
            "previous_status": previous_status.value,
            "new_status": status.value,
            "telegram_callback_query_id": telegram_callback_query_id,
        }

        await self.db.insert_history(history_data)

        logger.info(
            f"Updated approval request {request_id} from {previous_status.value} "
            f"to {status.value} by user {actor_id}"
        )

        return True

    async def get_approval_request(self, request_id: str) -> ApprovalRequest:
        """
        Get an approval request by ID.

        Args:
            request_id: ID of the approval request.

        Returns:
            ApprovalRequest object.

        Raises:
            ValueError: If request not found.
        """
        request_data = await self.db.get_request(request_id)
        if not request_data:
            raise ValueError(f"Approval request {request_id} not found")

        return ApprovalRequest.from_dict(request_data)

    async def list_pending_approvals(self, approver_id: int) -> list[ApprovalRequest]:
        """
        List pending approval requests for an approver.

        Args:
            approver_id: User ID of the approver.

        Returns:
            List of pending ApprovalRequest objects, ordered by created_at DESC.
        """
        rows = await self.db.get_pending_by_approver(approver_id)
        requests = [ApprovalRequest.from_dict(row) for row in rows]

        # Sort by created_at descending (already ordered by DB, but ensure consistency)
        requests.sort(key=lambda r: r.created_at or datetime.min, reverse=True)

        return requests

    async def generate_edit_token(self, request_id: str) -> str:
        """
        Generate a secure edit token for web-based editing.

        Args:
            request_id: ID of the approval request.

        Returns:
            Generated edit token.

        Raises:
            ValueError: If request not found.
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=self.edit_token_expiry_hours)

        # Update request with token
        success = await self.db.update_request(
            request_id,
            {
                "edit_token": token,
                "edit_token_expires_at": expires_at,
            },
        )
        if not success:
            raise ValueError(f"Approval request {request_id} not found")

        logger.info(f"Generated edit token for request {request_id}")

        return token

    async def notify_requester(
        self,
        request_id: str,
        action: ApprovalAction,
        message: str,
        requester_chat_id: int,
    ) -> bool:
        """
        Notify the requester about an action on their request.

        Args:
            request_id: ID of the approval request.
            action: Action that was taken.
            message: Notification message.
            requester_chat_id: Chat ID of the requester.

        Returns:
            True if notification sent successfully.
        """
        # Get request details
        try:
            request = await self.get_approval_request(request_id)
        except ValueError:
            logger.warning(f"Cannot notify: request {request_id} not found")
            return False

        # Format notification
        if action == ApprovalAction.APPROVE:
            icon = ""
            status_text = "APPROVED"
        elif action == ApprovalAction.DISAPPROVE:
            icon = ""
            status_text = "DISAPPROVED"
        elif action == ApprovalAction.EDIT:
            icon = ""
            status_text = "CHANGES REQUESTED"
        else:
            icon = ""
            status_text = action.value.upper()

        notification_text = (
            f"{icon} <b>Your approval request has been {status_text}</b>\n\n"
            f"<b>Title:</b> {request.title}\n\n"
            f"{message}"
        )

        try:
            await self.telegram_client.send_message(
                chat_id=requester_chat_id,
                text=notification_text,
                parse_mode=ParseMode.HTML,
            )
            logger.info(f"Notified requester about {action.value} on request {request_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to notify requester: {e}")
            return False

    def format_status_message(
        self,
        status: ApprovalStatus,
        actor_username: str | None = None,
        comment: str | None = None,
    ) -> str:
        """
        Format a status update message for the approval.

        Args:
            status: New status of the approval.
            actor_username: Username of who took the action.
            comment: Optional comment/reason.

        Returns:
            Formatted HTML message for status update.
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        actor_text = f"@{actor_username}" if actor_username else "Unknown"

        if status == ApprovalStatus.APPROVED:
            message = (
                f"<b>APPROVED</b>\n\n" f"Approved by: {actor_text}\n" f"Approved at: {timestamp}"
            )
        elif status == ApprovalStatus.DISAPPROVED:
            message = f"<b>DISAPPROVED</b>\n\n" f"Disapproved by: {actor_text}\n"
            if comment:
                message += f"Reason: {comment}\n"
            message += f"Processed at: {timestamp}"
        elif status == ApprovalStatus.EDITING:
            message = (
                f"<b>EDITING</b>\n\n"
                f"Edit requested by: {actor_text}\n"
                f"At: {timestamp}\n\n"
                f"Waiting for edits to be submitted."
            )
        elif status == ApprovalStatus.CANCELLED:
            message = f"<b>CANCELLED</b>\n\n" f"Cancelled by: {actor_text}\n" f"At: {timestamp}"
        else:
            message = (
                f"<b>Status: {status.value.upper()}</b>\n\n"
                f"Updated by: {actor_text}\n"
                f"At: {timestamp}"
            )

        return message

    async def get_request_by_edit_token(self, token: str) -> ApprovalRequest | None:
        """
        Get an approval request by its edit token.

        Args:
            token: Edit token to look up.

        Returns:
            ApprovalRequest if found and token is valid, None otherwise.
        """
        request_data = await self.db.get_request_by_edit_token(token)
        if not request_data:
            return None

        request = ApprovalRequest.from_dict(request_data)

        # Check if token is expired
        if request.edit_token_expires_at and request.edit_token_expires_at < datetime.now(UTC):
            logger.warning(f"Edit token expired for request {request.id}")
            return None

        return request

    async def close(self) -> None:
        """Close the service and release resources."""
        await self.telegram_client.close()
        logger.debug("ApprovalService closed")
