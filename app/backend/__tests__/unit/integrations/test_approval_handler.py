"""
Unit tests for ApprovalBotHandler.

Tests all handler methods with mocked dependencies.
No real API calls are made.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.approval_handler import ApprovalBotHandler
from src.integrations.telegram import (
    Chat,
    Message,
    TelegramClient,
    TelegramError,
    TelegramRateLimitError,
    Update,
)
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.services.approval_service import ApprovalService

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_telegram() -> MagicMock:
    """Create mocked TelegramClient."""
    client = MagicMock(spec=TelegramClient)
    client.send_message = AsyncMock(return_value=Message(message_id=42, date=0, raw={}))
    client.edit_message_text = AsyncMock(return_value=Message(message_id=42, date=0, raw={}))
    client.answer_callback_query = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_approval_service() -> MagicMock:
    """Create mocked ApprovalService."""
    service = MagicMock(spec=ApprovalService)
    service.edit_form_base_url = "https://test.example.com/approvals"
    return service


@pytest.fixture
def handler(
    mock_telegram: MagicMock,
    mock_approval_service: MagicMock,
) -> ApprovalBotHandler:
    """Create ApprovalBotHandler with mocked dependencies."""
    return ApprovalBotHandler(
        telegram_client=mock_telegram,
        approval_service=mock_approval_service,
    )


@pytest.fixture
def mock_request() -> ApprovalRequest:
    """Create a mock ApprovalRequest."""
    return ApprovalRequest(
        id="test-request-id",
        title="Test Approval",
        content="Test content",
        requester_id=123,
        approver_id=456,
        telegram_chat_id=789012345,
        telegram_message_id=42,
        status=ApprovalStatus.PENDING,
    )


@pytest.fixture
def callback_query_approve(mock_request: ApprovalRequest) -> dict[str, Any]:
    """Create approve callback query."""
    return {
        "id": "callback_123",
        "from": {"id": 456, "username": "approver"},
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original message",
        },
        "data": f"approve_{mock_request.id}",
    }


@pytest.fixture
def callback_query_disapprove(mock_request: ApprovalRequest) -> dict[str, Any]:
    """Create disapprove callback query."""
    return {
        "id": "callback_456",
        "from": {"id": 456, "username": "approver"},
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original message",
        },
        "data": f"disapprove_{mock_request.id}",
    }


@pytest.fixture
def callback_query_edit(mock_request: ApprovalRequest) -> dict[str, Any]:
    """Create edit callback query."""
    return {
        "id": "callback_789",
        "from": {"id": 456, "username": "approver"},
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original message",
        },
        "data": f"edit_{mock_request.id}",
    }


# =============================================================================
# TEST: process_update
# =============================================================================


class TestProcessUpdate:
    """Tests for process_update method."""

    @pytest.mark.asyncio
    async def test_routes_callback_query(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """process_update should route callback_query to handle_callback_query."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)
        mock_approval_service.format_status_message = MagicMock(return_value="Status")

        update = Update(
            update_id=1,
            callback_query=callback_query_approve,
            raw={},
        )

        result = await handler.process_update(update)

        assert result is True
        mock_approval_service.get_approval_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_message(
        self,
        handler: ApprovalBotHandler,
    ) -> None:
        """process_update should route message to handle_message."""
        update = Update(
            update_id=1,
            message=Message(
                message_id=99,
                date=1703030400,
                text="Test message",
                chat=Chat(id=789012345, type="private"),
                raw={
                    "chat": {"id": 789012345, "type": "private"},
                    "from": {"id": 456, "username": "testuser"},
                },
            ),
            raw={},
        )

        result = await handler.process_update(update)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_update(
        self,
        handler: ApprovalBotHandler,
    ) -> None:
        """process_update should return False for empty update."""
        update = Update(update_id=1, raw={})

        result = await handler.process_update(update)

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_approval_service: MagicMock,
    ) -> None:
        """process_update should handle rate limit errors gracefully."""
        mock_approval_service.get_approval_request = AsyncMock(
            side_effect=TelegramRateLimitError("Rate limit", retry_after=30)
        )

        update = Update(
            update_id=1,
            callback_query=callback_query_approve,
            raw={},
        )

        result = await handler.process_update(update)

        assert result is False


# =============================================================================
# TEST: handle_callback_query
# =============================================================================


class TestHandleCallbackQuery:
    """Tests for handle_callback_query method."""

    @pytest.mark.asyncio
    async def test_parses_valid_callback_data(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_callback_query should parse valid callback data."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)
        mock_approval_service.format_status_message = MagicMock(return_value="Status")

        await handler.handle_callback_query(callback_query_approve)

        mock_approval_service.get_approval_request.assert_called_with(mock_request.id)

    @pytest.mark.asyncio
    async def test_handles_invalid_callback_data(
        self,
        handler: ApprovalBotHandler,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_callback_query should handle invalid callback data format."""
        invalid_query: dict[str, Any] = {
            "id": "callback_123",
            "from": {"id": 456},
            "message": {"message_id": 42, "chat": {"id": 789}},
            "data": "invalid_format_no_underscore",
        }

        await handler.handle_callback_query(invalid_query)

        # Should answer with error
        mock_telegram.answer_callback_query.assert_called_once()
        call_kwargs = mock_telegram.answer_callback_query.call_args.kwargs
        assert call_kwargs["show_alert"] is True


# =============================================================================
# TEST: handle_approve
# =============================================================================


class TestHandleApprove:
    """Tests for handle_approve method."""

    @pytest.mark.asyncio
    async def test_updates_status_to_approved(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """handle_approve should update status to approved."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)
        mock_approval_service.format_status_message = MagicMock(return_value="Approved")

        await handler.handle_approve(callback_query_approve, mock_request.id)

        mock_approval_service.update_approval_status.assert_called_once()
        call_kwargs = mock_approval_service.update_approval_status.call_args.kwargs
        assert call_kwargs["status"] == ApprovalStatus.APPROVED
        assert call_kwargs["actor_id"] == 456

    @pytest.mark.asyncio
    async def test_edits_message(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_approve should edit the message."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)
        mock_approval_service.format_status_message = MagicMock(return_value="Approved")

        await handler.handle_approve(callback_query_approve, mock_request.id)

        mock_telegram.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_answers_callback_query(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_approve should answer the callback query."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)
        mock_approval_service.format_status_message = MagicMock(return_value="Approved")

        await handler.handle_approve(callback_query_approve, mock_request.id)

        mock_telegram.answer_callback_query.assert_called()
        # Should have "success" in the message
        call_kwargs = mock_telegram.answer_callback_query.call_args.kwargs
        assert "success" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_rejects_unauthorized_approver(
        self,
        handler: ApprovalBotHandler,
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_approve should reject unauthorized approver."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)

        # Different user ID than approver
        unauthorized_query: dict[str, Any] = {
            "id": "callback_123",
            "from": {"id": 999, "username": "unauthorized"},
            "message": {"message_id": 42, "chat": {"id": 789}},
            "data": f"approve_{mock_request.id}",
        }

        await handler.handle_approve(unauthorized_query, mock_request.id)

        mock_telegram.answer_callback_query.assert_called()
        call_kwargs = mock_telegram.answer_callback_query.call_args.kwargs
        assert "not authorized" in call_kwargs["text"].lower()
        assert call_kwargs["show_alert"] is True

    @pytest.mark.asyncio
    async def test_rejects_already_processed(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_approve should reject already processed request."""
        mock_request.status = ApprovalStatus.APPROVED
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)

        await handler.handle_approve(callback_query_approve, mock_request.id)

        mock_telegram.answer_callback_query.assert_called()
        call_kwargs = mock_telegram.answer_callback_query.call_args.kwargs
        assert "already been" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_handles_not_found(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_approve should handle request not found."""
        mock_approval_service.get_approval_request = AsyncMock(side_effect=ValueError("Not found"))

        await handler.handle_approve(callback_query_approve, "nonexistent")

        mock_telegram.answer_callback_query.assert_called()
        call_kwargs = mock_telegram.answer_callback_query.call_args.kwargs
        assert "not found" in call_kwargs["text"].lower()


# =============================================================================
# TEST: handle_disapprove
# =============================================================================


class TestHandleDisapprove:
    """Tests for handle_disapprove method."""

    @pytest.mark.asyncio
    async def test_asks_for_reason(
        self,
        handler: ApprovalBotHandler,
        callback_query_disapprove: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_disapprove should ask for reason."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)

        await handler.handle_disapprove(callback_query_disapprove, mock_request.id)

        mock_telegram.send_message.assert_called_once()
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert "reason" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_stores_pending_reason_request(
        self,
        handler: ApprovalBotHandler,
        callback_query_disapprove: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """handle_disapprove should store pending reason request."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)

        await handler.handle_disapprove(callback_query_disapprove, mock_request.id)

        # Check pending_reasons dict
        key = (789012345, 456)  # chat_id, user_id
        assert key in handler.pending_reasons
        assert handler.pending_reasons[key] == mock_request.id


# =============================================================================
# TEST: handle_edit
# =============================================================================


class TestHandleEdit:
    """Tests for handle_edit method."""

    @pytest.mark.asyncio
    async def test_generates_edit_token(
        self,
        handler: ApprovalBotHandler,
        callback_query_edit: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """handle_edit should generate edit token."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.generate_edit_token = AsyncMock(return_value="test-token")
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)

        await handler.handle_edit(callback_query_edit, mock_request.id)

        mock_approval_service.generate_edit_token.assert_called_once_with(mock_request.id)

    @pytest.mark.asyncio
    async def test_updates_status_to_editing(
        self,
        handler: ApprovalBotHandler,
        callback_query_edit: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """handle_edit should update status to editing."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.generate_edit_token = AsyncMock(return_value="test-token")
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)

        await handler.handle_edit(callback_query_edit, mock_request.id)

        mock_approval_service.update_approval_status.assert_called_once()
        call_kwargs = mock_approval_service.update_approval_status.call_args.kwargs
        assert call_kwargs["status"] == ApprovalStatus.EDITING

    @pytest.mark.asyncio
    async def test_sends_edit_form_link(
        self,
        handler: ApprovalBotHandler,
        callback_query_edit: dict[str, Any],
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_edit should send edit form link."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.generate_edit_token = AsyncMock(return_value="test-token")
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)

        await handler.handle_edit(callback_query_edit, mock_request.id)

        mock_telegram.send_message.assert_called_once()
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert "Edit" in call_kwargs["text"]


# =============================================================================
# TEST: handle_message
# =============================================================================


class TestHandleMessage:
    """Tests for handle_message method."""

    @pytest.mark.asyncio
    async def test_completes_disapproval_with_reason(
        self,
        handler: ApprovalBotHandler,
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """handle_message should complete disapproval flow with reason."""
        # Setup pending reason
        handler.pending_reasons[(789012345, 456)] = mock_request.id

        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)

        message = MagicMock()
        message.chat = MagicMock()
        message.chat.id = 789012345
        message.from_user = MagicMock()
        message.from_user.id = 456
        message.from_user.username = "testuser"
        message.text = "Budget is too high"
        message.message_id = 99

        await handler.handle_message(message)

        mock_approval_service.update_approval_status.assert_called_once()
        call_kwargs = mock_approval_service.update_approval_status.call_args.kwargs
        assert call_kwargs["comment"] == "Budget is too high"
        assert call_kwargs["status"] == ApprovalStatus.DISAPPROVED

    @pytest.mark.asyncio
    async def test_handles_skip_reason(
        self,
        handler: ApprovalBotHandler,
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
    ) -> None:
        """handle_message should handle 'skip' as no reason."""
        handler.pending_reasons[(789012345, 456)] = mock_request.id

        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)
        mock_approval_service.update_approval_status = AsyncMock(return_value=True)

        message = MagicMock()
        message.chat = MagicMock()
        message.chat.id = 789012345
        message.from_user = MagicMock()
        message.from_user.id = 456
        message.from_user.username = "testuser"
        message.text = "skip"
        message.message_id = 99

        await handler.handle_message(message)

        call_kwargs = mock_approval_service.update_approval_status.call_args.kwargs
        assert call_kwargs["comment"] is None


# =============================================================================
# TEST: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_approval_service: MagicMock,
    ) -> None:
        """Handler should handle rate limit errors gracefully."""
        mock_approval_service.get_approval_request = AsyncMock(
            side_effect=TelegramRateLimitError("Rate limited", retry_after=30)
        )

        update = Update(
            update_id=1,
            callback_query=callback_query_approve,
            raw={},
        )

        # Should not raise, just return False
        result = await handler.process_update(update)
        assert result is False

    @pytest.mark.asyncio
    async def test_telegram_error_handling(
        self,
        handler: ApprovalBotHandler,
        callback_query_approve: dict[str, Any],
        mock_approval_service: MagicMock,
    ) -> None:
        """Handler should handle Telegram errors gracefully."""
        mock_approval_service.get_approval_request = AsyncMock(
            side_effect=TelegramError("API Error")
        )

        update = Update(
            update_id=1,
            callback_query=callback_query_approve,
            raw={},
        )

        result = await handler.process_update(update)
        assert result is False

    @pytest.mark.asyncio
    async def test_permission_denied_logging(
        self,
        handler: ApprovalBotHandler,
        mock_request: ApprovalRequest,
        mock_approval_service: MagicMock,
        mock_telegram: MagicMock,
    ) -> None:
        """Handler should log permission denied events."""
        mock_approval_service.get_approval_request = AsyncMock(return_value=mock_request)

        unauthorized_query: dict[str, Any] = {
            "id": "callback_123",
            "from": {"id": 999, "username": "hacker"},
            "message": {"message_id": 42, "chat": {"id": 789}},
            "data": f"approve_{mock_request.id}",
        }

        with patch("src.integrations.approval_handler.logger") as mock_logger:
            await handler.handle_approve(unauthorized_query, mock_request.id)
            mock_logger.warning.assert_called()
