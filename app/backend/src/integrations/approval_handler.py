"""
Telegram approval bot handler.

Handles callback queries and messages for the approval workflow.
Routes button clicks to appropriate handlers and manages the
interactive approval flow.

Example:
    >>> from src.integrations.approval_handler import ApprovalBotHandler
    >>> from src.services.approval_service import ApprovalService
    >>> handler = ApprovalBotHandler(
    ...     telegram_client=telegram,
    ...     approval_service=approval_service,
    ... )
    >>> await handler.process_update(update)
"""

import logging
from typing import Any

from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramClient,
    TelegramError,
    TelegramRateLimitError,
    Update,
)
from src.models.approval import ApprovalStatus
from src.services.approval_service import ApprovalService

logger = logging.getLogger(__name__)


class ApprovalBotHandler:
    """
    Handler for approval-related Telegram updates.

    Routes callback queries from inline buttons to appropriate
    handlers (approve, disapprove, edit) and manages the approval
    workflow state.

    Attributes:
        telegram_client: TelegramClient for API calls.
        approval_service: ApprovalService for business logic.
        pending_reasons: Dict tracking users waiting to provide disapproval reasons.
    """

    def __init__(
        self,
        telegram_client: TelegramClient,
        approval_service: ApprovalService,
    ) -> None:
        """
        Initialize the approval bot handler.

        Args:
            telegram_client: Configured TelegramClient instance.
            approval_service: Configured ApprovalService instance.
        """
        self.telegram_client = telegram_client
        self.approval_service = approval_service
        # Track users waiting to provide disapproval reasons
        # Key: (chat_id, user_id), Value: request_id
        self.pending_reasons: dict[tuple[int, int], str] = {}
        logger.info("Initialized ApprovalBotHandler")

    async def process_update(self, update: Update) -> bool:
        """
        Process a Telegram update.

        Routes to appropriate handler based on update type.

        Args:
            update: Telegram Update object.

        Returns:
            True if update was processed, False if skipped.
        """
        logger.debug(f"Processing update {update.update_id}")

        try:
            # Handle callback queries (button clicks)
            if update.callback_query:
                await self.handle_callback_query(update.callback_query)
                return True

            # Handle messages (e.g., disapproval reasons)
            if update.message:
                await self.handle_message(update.message)
                return True

            return False

        except TelegramRateLimitError as e:
            logger.warning(f"Rate limit hit: {e}. Retry after {e.retry_after}s")
            return False

        except TelegramError as e:
            logger.error(f"Telegram error processing update: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error processing update: {e}", exc_info=True)
            return False

    async def handle_callback_query(self, callback_query: dict[str, Any]) -> None:
        """
        Handle a callback query from an inline button.

        Parses the callback_data and routes to appropriate handler.

        Args:
            callback_query: Callback query data from Telegram.
        """
        callback_data = callback_query.get("data", "")
        callback_id = callback_query.get("id", "")

        logger.info(f"Handling callback query: {callback_data}")

        # Parse callback data
        parts = callback_data.split("_", 1)
        if len(parts) != 2:
            await self._answer_callback(callback_id, "Invalid action", show_alert=True)
            logger.warning(f"Invalid callback data format: {callback_data}")
            return

        action, request_id = parts

        # Route to appropriate handler
        if action == "approve":
            await self.handle_approve(callback_query, request_id)
        elif action == "disapprove":
            await self.handle_disapprove(callback_query, request_id)
        elif action == "edit":
            await self.handle_edit(callback_query, request_id)
        else:
            await self._answer_callback(callback_id, f"Unknown action: {action}", show_alert=True)
            logger.warning(f"Unknown callback action: {action}")

    async def handle_approve(self, callback_query: dict[str, Any], request_id: str) -> None:
        """
        Handle approval of a request.

        Updates status to approved, edits the message to show status,
        answers the callback, and notifies the requester.

        Args:
            callback_query: Callback query data from Telegram.
            request_id: ID of the approval request.
        """
        callback_id = callback_query.get("id", "")
        user = callback_query.get("from", {})
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        user_id = user.get("id", 0)
        username = user.get("username")

        logger.info(f"Processing approval for request {request_id} by user {user_id}")

        # Get the request
        try:
            request = await self.approval_service.get_approval_request(request_id)
        except ValueError:
            await self._answer_callback(callback_id, "Request not found", show_alert=True)
            logger.warning(f"Approval request {request_id} not found")
            return

        # Verify approver
        if request.approver_id != user_id:
            await self._answer_callback(
                callback_id,
                "You are not authorized to approve this request",
                show_alert=True,
            )
            logger.warning(f"User {user_id} not authorized to approve request {request_id}")
            return

        # Check if already processed
        if not request.is_pending():
            await self._answer_callback(
                callback_id,
                f"This request has already been {request.status.value}",
                show_alert=True,
            )
            return

        # Update status
        success = await self.approval_service.update_approval_status(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            actor_id=user_id,
            actor_username=username,
            telegram_callback_query_id=callback_id,
        )

        if not success:
            await self._answer_callback(callback_id, "Failed to update status", show_alert=True)
            return

        # Edit the message to show approval status
        status_message = self.approval_service.format_status_message(
            status=ApprovalStatus.APPROVED,
            actor_username=username,
        )

        original_text = message.get("text", "")
        updated_text = f"{original_text}\n\n{'=' * 30}\n\n{status_message}"

        try:
            await self.telegram_client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_text,
                parse_mode=ParseMode.HTML,
                # Remove buttons after action
                reply_markup=self._build_completed_keyboard(request_id, ApprovalStatus.APPROVED),
            )
        except TelegramError as e:
            logger.error(f"Failed to edit message: {e}")

        # Answer callback
        await self._answer_callback(callback_id, "Approval recorded successfully")

        # Notify requester (if we have their chat_id)
        # In a real implementation, you'd look up the requester's chat_id
        logger.info(f"Request {request_id} approved by {username or user_id}")

    async def handle_disapprove(self, callback_query: dict[str, Any], request_id: str) -> None:
        """
        Handle disapproval of a request.

        Prompts for a reason, then updates status and notifies requester.

        Args:
            callback_query: Callback query data from Telegram.
            request_id: ID of the approval request.
        """
        callback_id = callback_query.get("id", "")
        user = callback_query.get("from", {})
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        user_id = user.get("id", 0)

        logger.info(f"Processing disapproval for request {request_id} by user {user_id}")

        # Get the request
        try:
            request = await self.approval_service.get_approval_request(request_id)
        except ValueError:
            await self._answer_callback(callback_id, "Request not found", show_alert=True)
            return

        # Verify approver
        if request.approver_id != user_id:
            await self._answer_callback(
                callback_id,
                "You are not authorized to disapprove this request",
                show_alert=True,
            )
            return

        # Check if already processed
        if not request.is_pending():
            await self._answer_callback(
                callback_id,
                f"This request has already been {request.status.value}",
                show_alert=True,
            )
            return

        # Store pending reason request
        self.pending_reasons[(chat_id, user_id)] = request_id

        # Ask for reason
        await self.telegram_client.send_message(
            chat_id=chat_id,
            text=(
                "Please provide a reason for disapproval:\n\n"
                "<i>Reply to this message with your reason, "
                "or send 'skip' to disapprove without a reason.</i>"
            ),
            parse_mode=ParseMode.HTML,
            reply_to_message_id=message_id,
        )

        await self._answer_callback(callback_id, "Please provide a reason for disapproval")

    async def _complete_disapproval(
        self,
        request_id: str,
        chat_id: int,
        user_id: int,
        username: str | None,
        reason: str | None,
        original_message_id: int | None = None,
    ) -> None:
        """
        Complete the disapproval flow after receiving reason.

        Args:
            request_id: ID of the approval request.
            chat_id: Chat ID where the approval message is.
            user_id: ID of the disapproving user.
            username: Username of the disapproving user.
            reason: Reason for disapproval (or None).
            original_message_id: ID of the original approval message.
        """
        # Update status
        success = await self.approval_service.update_approval_status(
            request_id=request_id,
            status=ApprovalStatus.DISAPPROVED,
            actor_id=user_id,
            actor_username=username,
            comment=reason,
        )

        if not success:
            await self.telegram_client.send_message(
                chat_id=chat_id,
                text="Failed to update status. Please try again.",
            )
            return

        # Get request for original message
        try:
            request = await self.approval_service.get_approval_request(request_id)
        except ValueError:
            return

        # Edit original message if we have the message_id
        if request.telegram_message_id:
            status_message = self.approval_service.format_status_message(
                status=ApprovalStatus.DISAPPROVED,
                actor_username=username,
                comment=reason,
            )

            try:
                # Get original message text (we don't have it stored, so create summary)
                updated_text = (
                    f"<b>APPROVAL REQUEST</b>\n"
                    f"{'=' * 30}\n\n"
                    f"<b>Title:</b> {request.title}\n\n"
                    f"<b>Details:</b>\n{request.content[:500]}...\n\n"
                    f"{'=' * 30}\n\n"
                    f"{status_message}"
                )

                await self.telegram_client.edit_message_text(
                    chat_id=chat_id,
                    message_id=request.telegram_message_id,
                    text=updated_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=self._build_completed_keyboard(
                        request_id, ApprovalStatus.DISAPPROVED
                    ),
                )
            except TelegramError as e:
                logger.error(f"Failed to edit original message: {e}")

        # Confirm to user
        await self.telegram_client.send_message(
            chat_id=chat_id,
            text="Request has been disapproved.",
        )

        logger.info(f"Request {request_id} disapproved by {username or user_id}")

    async def handle_edit(self, callback_query: dict[str, Any], request_id: str) -> None:
        """
        Handle edit request for an approval.

        Generates edit token and sends edit form link.

        Args:
            callback_query: Callback query data from Telegram.
            request_id: ID of the approval request.
        """
        callback_id = callback_query.get("id", "")
        user = callback_query.get("from", {})
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        user_id = user.get("id", 0)
        username = user.get("username")

        logger.info(f"Processing edit request for {request_id} by user {user_id}")

        # Get the request
        try:
            request = await self.approval_service.get_approval_request(request_id)
        except ValueError:
            await self._answer_callback(callback_id, "Request not found", show_alert=True)
            return

        # Verify approver
        if request.approver_id != user_id:
            await self._answer_callback(
                callback_id,
                "You are not authorized to edit this request",
                show_alert=True,
            )
            return

        # Check if actionable
        if not request.is_actionable():
            await self._answer_callback(
                callback_id,
                f"This request has already been {request.status.value}",
                show_alert=True,
            )
            return

        # Generate edit token
        try:
            token = await self.approval_service.generate_edit_token(request_id)
        except ValueError as e:
            await self._answer_callback(callback_id, str(e), show_alert=True)
            return

        # Update status to editing
        await self.approval_service.update_approval_status(
            request_id=request_id,
            status=ApprovalStatus.EDITING,
            actor_id=user_id,
            actor_username=username,
            telegram_callback_query_id=callback_id,
        )

        # Build edit URL
        edit_url = f"{self.approval_service.edit_form_base_url}/{request_id}/edit?token={token}"

        # Send edit form link
        edit_message = (
            "<b>Edit Mode</b>\n\n"
            "Click the button below to edit this approval request.\n"
            "The link will expire in 24 hours."
        )

        edit_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open Edit Form",
                        url=edit_url,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cancel Edit",
                        callback_data=f"cancel_edit_{request_id}",
                    )
                ],
            ]
        )

        await self.telegram_client.send_message(
            chat_id=chat_id,
            text=edit_message,
            parse_mode=ParseMode.HTML,
            reply_markup=edit_keyboard,
            reply_to_message_id=message_id,
        )

        await self._answer_callback(callback_id, "Edit form link generated")

        logger.info(f"Edit token generated for request {request_id}")

    async def handle_message(self, message: Any) -> None:
        """
        Handle a regular message (non-callback).

        Used for receiving disapproval reasons.

        Args:
            message: Message object from Telegram.
        """
        chat_id_raw = (
            message.chat.id if hasattr(message, "chat") else message.get("chat", {}).get("id")
        )
        chat_id: int = int(chat_id_raw) if chat_id_raw else 0
        from_user = message.from_user if hasattr(message, "from_user") else message.get("from", {})
        user_id_raw = (
            from_user.get("id") if isinstance(from_user, dict) else getattr(from_user, "id", 0)
        )
        user_id: int = int(user_id_raw) if user_id_raw else 0
        username = (
            from_user.get("username")
            if isinstance(from_user, dict)
            else getattr(from_user, "username", None)
        )
        text = message.text if hasattr(message, "text") else message.get("text", "")

        # Check if we're waiting for a disapproval reason
        key = (chat_id, user_id)
        if key in self.pending_reasons:
            request_id = self.pending_reasons.pop(key)

            reason: str | None = text.strip() if text and text.strip().lower() != "skip" else None

            # Get original message ID from request
            try:
                request = await self.approval_service.get_approval_request(request_id)
                original_message_id = request.telegram_message_id
            except ValueError:
                original_message_id = None

            await self._complete_disapproval(
                request_id=request_id,
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                reason=reason,
                original_message_id=original_message_id,
            )

    async def _answer_callback(
        self,
        callback_id: str,
        text: str,
        show_alert: bool = False,
    ) -> None:
        """
        Answer a callback query.

        Args:
            callback_id: Callback query ID.
            text: Response text.
            show_alert: Whether to show as alert popup.
        """
        try:
            await self.telegram_client.answer_callback_query(
                callback_query_id=callback_id,
                text=text,
                show_alert=show_alert,
            )
        except TelegramError as e:
            logger.error(f"Failed to answer callback query: {e}")

    def _build_completed_keyboard(
        self,
        request_id: str,
        status: ApprovalStatus,
    ) -> InlineKeyboardMarkup:
        """
        Build keyboard for completed (approved/disapproved) requests.

        Shows status indicator and view details button only.

        Args:
            request_id: ID of the approval request.
            status: Final status of the request.

        Returns:
            InlineKeyboardMarkup with status indicator.
        """
        if status == ApprovalStatus.APPROVED:
            status_text = "Approved"
        elif status == ApprovalStatus.DISAPPROVED:
            status_text = "Disapproved"
        else:
            status_text = status.value.title()

        view_url = f"{self.approval_service.edit_form_base_url}/{request_id}/view"

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"Status: {status_text}",
                        callback_data=f"status_{request_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="View Details",
                        url=view_url,
                    )
                ],
            ]
        )
