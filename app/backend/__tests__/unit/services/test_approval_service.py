"""
Unit tests for ApprovalService.

Tests all ApprovalService methods with mocked dependencies.
No real API calls are made.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.telegram import (
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    TelegramError,
)
from src.models.approval import (
    ApprovalContentType,
    ApprovalRequest,
    ApprovalStatus,
)
from src.services.approval_service import ApprovalService, InMemoryDatabase

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_telegram() -> MagicMock:
    """Create mocked TelegramClient."""
    client = MagicMock()
    client.send_message = AsyncMock(
        return_value=Message(
            message_id=42,
            date=1703030400,
            text="Test",
            raw={},
        )
    )
    client.edit_message_text = AsyncMock(return_value=Message(message_id=42, date=0, raw={}))
    client.answer_callback_query = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def service(mock_telegram: MagicMock) -> ApprovalService:
    """Create ApprovalService with mocked Telegram client."""
    return ApprovalService(
        telegram_client=mock_telegram,
        db=InMemoryDatabase(),
        edit_form_base_url="https://test.example.com/approvals",
    )


# =============================================================================
# TEST: send_approval_request
# =============================================================================


class TestSendApprovalRequest:
    """Tests for send_approval_request method."""

    @pytest.mark.asyncio
    async def test_creates_database_record(self, service: ApprovalService) -> None:
        """send_approval_request should create a database record."""
        request_data = {
            "title": "Test Budget",
            "content": "Budget request",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
            "content_type": "budget",
            "data": {"amount": 5000},
        }

        request_id = await service.send_approval_request(request_data)

        # Verify record created
        assert request_id is not None
        assert isinstance(service.db, InMemoryDatabase)
        assert request_id in service.db.requests

    @pytest.mark.asyncio
    async def test_calls_telegram_api(
        self, service: ApprovalService, mock_telegram: MagicMock
    ) -> None:
        """send_approval_request should call Telegram send_message."""
        request_data = {
            "title": "Test",
            "content": "Content",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
        }

        await service.send_approval_request(request_data)

        mock_telegram.send_message.assert_called_once()
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 789
        assert call_kwargs["parse_mode"] == ParseMode.HTML
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_returns_request_id(self, service: ApprovalService) -> None:
        """send_approval_request should return the request ID."""
        request_data = {
            "title": "Test",
            "content": "Content",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
        }

        request_id = await service.send_approval_request(request_data)

        assert request_id is not None
        assert len(request_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_stores_message_id(
        self, service: ApprovalService, mock_telegram: MagicMock
    ) -> None:
        """send_approval_request should store the Telegram message ID."""
        mock_telegram.send_message.return_value = Message(message_id=99, date=0, raw={})

        request_data = {
            "title": "Test",
            "content": "Content",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
        }

        request_id = await service.send_approval_request(request_data)

        assert isinstance(service.db, InMemoryDatabase)
        stored = service.db.requests[request_id]
        assert stored["telegram_message_id"] == 99

    @pytest.mark.asyncio
    async def test_raises_on_invalid_data(self, service: ApprovalService) -> None:
        """send_approval_request should raise ValueError on invalid data."""
        invalid_data: dict[str, Any] = {
            "title": "",  # Empty title
            "content": "Content",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
        }

        with pytest.raises(ValueError, match="Invalid request data"):
            await service.send_approval_request(invalid_data)

    @pytest.mark.asyncio
    async def test_raises_on_telegram_error(
        self, service: ApprovalService, mock_telegram: MagicMock
    ) -> None:
        """send_approval_request should raise TelegramError on API failure."""
        mock_telegram.send_message.side_effect = TelegramError("API Error")

        request_data = {
            "title": "Test",
            "content": "Content",
            "requester_id": 123,
            "approver_id": 456,
            "telegram_chat_id": 789,
        }

        with pytest.raises(TelegramError):
            await service.send_approval_request(request_data)


# =============================================================================
# TEST: format_approval_message
# =============================================================================


class TestFormatApprovalMessage:
    """Tests for format_approval_message method."""

    def test_budget_content_formatting(self, service: ApprovalService) -> None:
        """format_approval_message should format budget content correctly."""
        result = service.format_approval_message(
            title="Q4 Budget",
            content="Marketing budget",
            content_type=ApprovalContentType.BUDGET,
            data={"amount": 50000, "department": "Marketing"},
        )

        assert "APPROVAL REQUEST" in result
        assert "Q4 Budget" in result
        assert "Budget Approval" in result
        assert "Marketing" in result
        assert "$50,000.00" in result

    def test_document_content_formatting(self, service: ApprovalService) -> None:
        """format_approval_message should format document content correctly."""
        result = service.format_approval_message(
            title="Contract Review",
            content="Partnership agreement",
            content_type=ApprovalContentType.DOCUMENT,
            data={
                "file_url": "https://example.com/doc.pdf",
                "document_type": "Contract",
            },
        )

        assert "APPROVAL REQUEST" in result
        assert "Contract Review" in result
        assert "Contract Review" in result
        assert "https://example.com/doc.pdf" in result

    def test_content_type_formatting(self, service: ApprovalService) -> None:
        """format_approval_message should format content type correctly."""
        result = service.format_approval_message(
            title="Blog Post",
            content="Article content here",
            content_type=ApprovalContentType.CONTENT,
            data={"tags": ["tech", "ai"]},
        )

        assert "CONTENT APPROVAL REQUEST" in result
        assert "Blog Post" in result
        assert "tech, ai" in result

    def test_custom_content_formatting(self, service: ApprovalService) -> None:
        """format_approval_message should format custom content correctly."""
        result = service.format_approval_message(
            title="Custom Request",
            content="Custom content here",
            content_type=ApprovalContentType.CUSTOM,
        )

        assert "APPROVAL REQUEST" in result
        assert "Custom Request" in result
        assert "Custom content here" in result

    def test_includes_timestamp(self, service: ApprovalService) -> None:
        """format_approval_message should include timestamp."""
        result = service.format_approval_message(
            title="Test",
            content="Content",
        )

        assert "Requested at:" in result
        assert "UTC" in result


# =============================================================================
# TEST: build_approval_buttons
# =============================================================================


class TestBuildApprovalButtons:
    """Tests for build_approval_buttons method."""

    def test_returns_inline_keyboard(self, service: ApprovalService) -> None:
        """build_approval_buttons should return InlineKeyboardMarkup."""
        result = service.build_approval_buttons("test-id")

        assert isinstance(result, InlineKeyboardMarkup)

    def test_has_approve_button(self, service: ApprovalService) -> None:
        """build_approval_buttons should include approve button."""
        result = service.build_approval_buttons("test-id")

        buttons_flat = [btn for row in result.inline_keyboard for btn in row]
        approve_btn = next((b for b in buttons_flat if "Approve" in b.text), None)

        assert approve_btn is not None
        assert approve_btn.callback_data == "approve_test-id"

    def test_has_disapprove_button(self, service: ApprovalService) -> None:
        """build_approval_buttons should include disapprove button."""
        result = service.build_approval_buttons("test-id")

        buttons_flat = [btn for row in result.inline_keyboard for btn in row]
        disapprove_btn = next((b for b in buttons_flat if "Disapprove" in b.text), None)

        assert disapprove_btn is not None
        assert disapprove_btn.callback_data == "disapprove_test-id"

    def test_has_edit_button_by_default(self, service: ApprovalService) -> None:
        """build_approval_buttons should include edit button by default."""
        result = service.build_approval_buttons("test-id")

        buttons_flat = [btn for row in result.inline_keyboard for btn in row]
        edit_btn = next((b for b in buttons_flat if "Edit" in b.text), None)

        assert edit_btn is not None
        assert edit_btn.callback_data == "edit_test-id"

    def test_can_exclude_edit_button(self, service: ApprovalService) -> None:
        """build_approval_buttons should allow excluding edit button."""
        result = service.build_approval_buttons("test-id", include_edit=False)

        buttons_flat = [btn for row in result.inline_keyboard for btn in row]
        edit_btn = next((b for b in buttons_flat if "Edit" in b.text), None)

        assert edit_btn is None

    def test_has_view_details_url_button(self, service: ApprovalService) -> None:
        """build_approval_buttons should include view details URL button."""
        result = service.build_approval_buttons("test-id")

        buttons_flat = [btn for row in result.inline_keyboard for btn in row]
        view_btn = next((b for b in buttons_flat if "View Details" in b.text), None)

        assert view_btn is not None
        assert view_btn.url is not None
        assert "test-id" in view_btn.url


# =============================================================================
# TEST: update_approval_status
# =============================================================================


class TestUpdateApprovalStatus:
    """Tests for update_approval_status method."""

    @pytest.mark.asyncio
    async def test_updates_database(self, service: ApprovalService) -> None:
        """update_approval_status should update the database record."""
        # Create a request first
        request_id = await service.send_approval_request(
            {
                "title": "Test",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        success = await service.update_approval_status(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            actor_id=456,
            actor_username="testuser",
        )

        assert success is True
        assert isinstance(service.db, InMemoryDatabase)
        assert service.db.requests[request_id]["status"] == "approved"

    @pytest.mark.asyncio
    async def test_creates_history_entry(self, service: ApprovalService) -> None:
        """update_approval_status should create a history entry."""
        request_id = await service.send_approval_request(
            {
                "title": "Test",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        await service.update_approval_status(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            actor_id=456,
            actor_username="testuser",
        )

        assert isinstance(service.db, InMemoryDatabase)
        assert len(service.db.history) == 1

        history = list(service.db.history.values())[0]
        assert history["request_id"] == request_id
        assert history["action"] == "approve"
        assert history["actor_id"] == 456

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent(self, service: ApprovalService) -> None:
        """update_approval_status should return False for nonexistent request."""
        success = await service.update_approval_status(
            request_id="nonexistent-id",
            status=ApprovalStatus.APPROVED,
            actor_id=456,
        )

        assert success is False


# =============================================================================
# TEST: get_approval_request
# =============================================================================


class TestGetApprovalRequest:
    """Tests for get_approval_request method."""

    @pytest.mark.asyncio
    async def test_returns_correct_request(self, service: ApprovalService) -> None:
        """get_approval_request should return the correct request."""
        request_id = await service.send_approval_request(
            {
                "title": "Test Title",
                "content": "Test Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        result = await service.get_approval_request(request_id)

        assert isinstance(result, ApprovalRequest)
        assert result.id == request_id
        assert result.title == "Test Title"

    @pytest.mark.asyncio
    async def test_raises_on_not_found(self, service: ApprovalService) -> None:
        """get_approval_request should raise ValueError if not found."""
        with pytest.raises(ValueError, match="not found"):
            await service.get_approval_request("nonexistent-id")


# =============================================================================
# TEST: list_pending_approvals
# =============================================================================


class TestListPendingApprovals:
    """Tests for list_pending_approvals method."""

    @pytest.mark.asyncio
    async def test_filters_by_approver(self, service: ApprovalService) -> None:
        """list_pending_approvals should filter by approver_id."""
        # Create requests for different approvers
        await service.send_approval_request(
            {
                "title": "For Approver 456",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )
        await service.send_approval_request(
            {
                "title": "For Approver 999",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 999,
                "telegram_chat_id": 789,
            }
        )

        results = await service.list_pending_approvals(456)

        assert len(results) == 1
        assert results[0].approver_id == 456

    @pytest.mark.asyncio
    async def test_orders_by_created_at_desc(self, service: ApprovalService) -> None:
        """list_pending_approvals should order by created_at descending."""
        await service.send_approval_request(
            {
                "title": "First",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )
        await service.send_approval_request(
            {
                "title": "Second",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        results = await service.list_pending_approvals(456)

        assert len(results) == 2
        # Second should come first (most recent)
        assert results[0].title == "Second"


# =============================================================================
# TEST: generate_edit_token
# =============================================================================


class TestGenerateEditToken:
    """Tests for generate_edit_token method."""

    @pytest.mark.asyncio
    async def test_generates_token(self, service: ApprovalService) -> None:
        """generate_edit_token should generate a secure token."""
        request_id = await service.send_approval_request(
            {
                "title": "Test",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        token = await service.generate_edit_token(request_id)

        assert token is not None
        assert len(token) > 20  # Token should be reasonably long

    @pytest.mark.asyncio
    async def test_stores_token_in_request(self, service: ApprovalService) -> None:
        """generate_edit_token should store the token in the request."""
        request_id = await service.send_approval_request(
            {
                "title": "Test",
                "content": "Content",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789,
            }
        )

        token = await service.generate_edit_token(request_id)

        assert isinstance(service.db, InMemoryDatabase)
        stored = service.db.requests[request_id]
        assert stored["edit_token"] == token
        assert stored["edit_token_expires_at"] is not None


# =============================================================================
# TEST: format_status_message
# =============================================================================


class TestFormatStatusMessage:
    """Tests for format_status_message method."""

    def test_approved_message(self, service: ApprovalService) -> None:
        """format_status_message should format approved status."""
        result = service.format_status_message(
            status=ApprovalStatus.APPROVED,
            actor_username="approver",
        )

        assert "APPROVED" in result
        assert "@approver" in result
        assert "Approved at:" in result

    def test_disapproved_message_with_comment(self, service: ApprovalService) -> None:
        """format_status_message should include comment for disapproved."""
        result = service.format_status_message(
            status=ApprovalStatus.DISAPPROVED,
            actor_username="approver",
            comment="Budget too high",
        )

        assert "DISAPPROVED" in result
        assert "@approver" in result
        assert "Budget too high" in result

    def test_editing_message(self, service: ApprovalService) -> None:
        """format_status_message should format editing status."""
        result = service.format_status_message(
            status=ApprovalStatus.EDITING,
            actor_username="editor",
        )

        assert "EDITING" in result
        assert "Waiting for edits" in result
