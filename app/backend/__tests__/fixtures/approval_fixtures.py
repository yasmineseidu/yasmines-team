"""
Test fixtures for approval workflow tests.

Provides mock data, sample requests, and fixture factories
for testing the approval system.
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.telegram import (
    Message,
    TelegramClient,
    Update,
    User,
)
from src.models.approval import (
    ApprovalContentType,
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from src.services.approval_service import ApprovalService, InMemoryDatabase

# =============================================================================
# SAMPLE DATA
# =============================================================================

BUDGET_SAMPLE = {
    "id": "budget_test_123",
    "title": "Q4 Marketing Budget",
    "content": "Budget allocation for Q4 marketing campaigns including digital ads and events.",
    "content_type": "budget",
    "requester_id": 123,
    "approver_id": 456,
    "telegram_chat_id": 789012345,
    "data": {
        "amount": 50000,
        "department": "Marketing",
        "fiscal_year": "2025",
    },
}

DOCUMENT_SAMPLE = {
    "id": "doc_test_456",
    "title": "Partnership Agreement Review",
    "content": "Review and approval needed for partnership agreement with Company X.",
    "content_type": "document",
    "requester_id": 234,
    "approver_id": 567,
    "telegram_chat_id": 890123456,
    "data": {
        "file_url": "https://example.com/docs/partnership_agreement.pdf",
        "document_type": "Contract",
    },
}

CONTENT_SAMPLE = {
    "id": "post_test_789",
    "title": "Blog Post: How to Scale Your Business",
    "content": """# How to Scale Your Business

Scaling a business requires careful planning and execution.
Here are the key steps to consider...

1. Build a solid foundation
2. Automate processes
3. Hire the right team
4. Focus on customer retention""",
    "content_type": "content",
    "requester_id": 345,
    "approver_id": 678,
    "telegram_chat_id": 901234567,
    "data": {
        "tags": ["business", "scaling", "growth"],
        "category": "Business Strategy",
    },
}

CUSTOM_SAMPLE = {
    "id": "custom_test_101",
    "title": "Custom Approval Request",
    "content": "This is a custom approval request for testing purposes.",
    "content_type": "custom",
    "requester_id": 456,
    "approver_id": 789,
    "telegram_chat_id": 123456789,
    "data": {
        "custom_field": "custom_value",
    },
}


# =============================================================================
# TELEGRAM MOCK RESPONSES
# =============================================================================

MOCK_BOT_INFO = {
    "id": 123456789,
    "is_bot": True,
    "first_name": "TestBot",
    "username": "test_approval_bot",
    "can_join_groups": True,
    "can_read_all_group_messages": False,
    "supports_inline_queries": False,
}

MOCK_SENT_MESSAGE = {
    "message_id": 42,
    "date": 1703030400,
    "chat": {
        "id": 789012345,
        "type": "private",
    },
    "text": "Test message",
}

MOCK_CALLBACK_QUERY = {
    "id": "callback_query_123",
    "from": {
        "id": 456,
        "is_bot": False,
        "first_name": "Test",
        "username": "testuser",
    },
    "message": {
        "message_id": 42,
        "date": 1703030400,
        "chat": {"id": 789012345, "type": "private"},
        "text": "Original approval message",
    },
    "chat_instance": "123456789",
    "data": "approve_test-request-id",
}


# =============================================================================
# PYTEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_telegram_client() -> MagicMock:
    """Create a mocked TelegramClient."""
    client = MagicMock(spec=TelegramClient)

    # Mock async methods
    client.send_message = AsyncMock(
        return_value=Message(
            message_id=42,
            date=1703030400,
            text="Test message",
            raw=MOCK_SENT_MESSAGE,
        )
    )
    client.edit_message_text = AsyncMock(
        return_value=Message(
            message_id=42,
            date=1703030400,
            text="Updated message",
            raw=MOCK_SENT_MESSAGE,
        )
    )
    client.answer_callback_query = AsyncMock(return_value=True)
    client.delete_message = AsyncMock(return_value=True)
    client.get_me = AsyncMock(
        return_value=User(
            id=123456789,
            is_bot=True,
            first_name="TestBot",
            username="test_approval_bot",
            raw=MOCK_BOT_INFO,
        )
    )
    client.get_updates = AsyncMock(return_value=[])
    client.set_webhook = AsyncMock(return_value=True)
    client.delete_webhook = AsyncMock(return_value=True)
    client.get_webhook_info = AsyncMock(return_value={"url": ""})
    client.health_check = AsyncMock(
        return_value={
            "name": "telegram",
            "healthy": True,
            "message": "Telegram bot @test_approval_bot is online",
        }
    )
    client.close = AsyncMock()

    # Non-async methods
    client.verify_webhook_token = MagicMock(return_value=True)

    return client


@pytest.fixture
def in_memory_db() -> InMemoryDatabase:
    """Create an in-memory database for testing."""
    return InMemoryDatabase()


@pytest.fixture
def approval_service(
    mock_telegram_client: MagicMock, in_memory_db: InMemoryDatabase
) -> ApprovalService:
    """Create an ApprovalService with mocked dependencies."""
    return ApprovalService(
        telegram_client=mock_telegram_client,
        db=in_memory_db,
        edit_form_base_url="https://test.example.com/approvals",
        edit_token_expiry_hours=24,
    )


@pytest.fixture
def budget_request_data() -> dict[str, Any]:
    """Get sample budget approval request data."""
    return BUDGET_SAMPLE.copy()


@pytest.fixture
def document_request_data() -> dict[str, Any]:
    """Get sample document approval request data."""
    return DOCUMENT_SAMPLE.copy()


@pytest.fixture
def content_request_data() -> dict[str, Any]:
    """Get sample content approval request data."""
    return CONTENT_SAMPLE.copy()


@pytest.fixture
def custom_request_data() -> dict[str, Any]:
    """Get sample custom approval request data."""
    return CUSTOM_SAMPLE.copy()


@pytest.fixture
def approval_request() -> ApprovalRequest:
    """Create a sample ApprovalRequest object."""
    return ApprovalRequest(
        id=str(uuid.uuid4()),
        title="Test Approval",
        content="Test content for approval",
        content_type=ApprovalContentType.CUSTOM,
        status=ApprovalStatus.PENDING,
        requester_id=123,
        approver_id=456,
        telegram_chat_id=789012345,
        telegram_message_id=42,
        data={"test": True},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def approval_request_create() -> ApprovalRequestCreate:
    """Create a sample ApprovalRequestCreate object."""
    return ApprovalRequestCreate(
        title="Test Approval",
        content="Test content for approval",
        content_type=ApprovalContentType.CUSTOM,
        requester_id=123,
        approver_id=456,
        telegram_chat_id=789012345,
        data={"test": True},
    )


@pytest.fixture
def mock_callback_query_approve() -> dict[str, Any]:
    """Create a mock callback query for approval."""
    return {
        "id": "callback_approve_123",
        "from": {
            "id": 456,  # Matches approver_id
            "is_bot": False,
            "first_name": "Approver",
            "username": "approver_user",
        },
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original approval message",
        },
        "chat_instance": "123456789",
        "data": "approve_REQUEST_ID_PLACEHOLDER",
    }


@pytest.fixture
def mock_callback_query_disapprove() -> dict[str, Any]:
    """Create a mock callback query for disapproval."""
    return {
        "id": "callback_disapprove_456",
        "from": {
            "id": 456,
            "is_bot": False,
            "first_name": "Approver",
            "username": "approver_user",
        },
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original approval message",
        },
        "chat_instance": "123456789",
        "data": "disapprove_REQUEST_ID_PLACEHOLDER",
    }


@pytest.fixture
def mock_callback_query_edit() -> dict[str, Any]:
    """Create a mock callback query for edit."""
    return {
        "id": "callback_edit_789",
        "from": {
            "id": 456,
            "is_bot": False,
            "first_name": "Approver",
            "username": "approver_user",
        },
        "message": {
            "message_id": 42,
            "date": 1703030400,
            "chat": {"id": 789012345, "type": "private"},
            "text": "Original approval message",
        },
        "chat_instance": "123456789",
        "data": "edit_REQUEST_ID_PLACEHOLDER",
    }


@pytest.fixture
def mock_update_with_message() -> Update:
    """Create a mock Update with a message."""
    return Update(
        update_id=12345,
        message=Message(
            message_id=99,
            date=1703030400,
            text="Test reason for disapproval",
            raw={
                "message_id": 99,
                "date": 1703030400,
                "text": "Test reason for disapproval",
                "chat": {"id": 789012345, "type": "private"},
                "from": {"id": 456, "username": "testuser"},
            },
        ),
        raw={},
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_approval_request(
    request_id: str | None = None,
    title: str = "Test Approval",
    content: str = "Test content",
    content_type: ApprovalContentType = ApprovalContentType.CUSTOM,
    status: ApprovalStatus = ApprovalStatus.PENDING,
    requester_id: int = 123,
    approver_id: int = 456,
    telegram_chat_id: int = 789012345,
    telegram_message_id: int | None = 42,
    data: dict[str, Any] | None = None,
) -> ApprovalRequest:
    """Helper to create ApprovalRequest with custom values."""
    return ApprovalRequest(
        id=request_id or str(uuid.uuid4()),
        title=title,
        content=content,
        content_type=content_type,
        status=status,
        requester_id=requester_id,
        approver_id=approver_id,
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
        data=data or {},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def create_callback_query(
    action: str,
    request_id: str,
    user_id: int = 456,
    username: str = "testuser",
    chat_id: int = 789012345,
    message_id: int = 42,
) -> dict[str, Any]:
    """Helper to create callback query dict."""
    return {
        "id": f"callback_{action}_{request_id[:8]}",
        "from": {
            "id": user_id,
            "is_bot": False,
            "first_name": "Test",
            "username": username,
        },
        "message": {
            "message_id": message_id,
            "date": int(datetime.now(UTC).timestamp()),
            "chat": {"id": chat_id, "type": "private"},
            "text": "Original message",
        },
        "chat_instance": "123456789",
        "data": f"{action}_{request_id}",
    }
