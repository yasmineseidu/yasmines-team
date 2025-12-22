"""
Live API integration tests for approval workflow.

These tests require real Telegram API credentials and should be run manually
during development or in a staging environment.

Run with: pytest -m live_api --env=staging

Required environment variables:
- TELEGRAM_BOT_TOKEN: Bot token from @BotFather
- TELEGRAM_TEST_CHAT_ID: Chat ID for test messages
- TELEGRAM_TEST_USER_ID: User ID for approval tests
"""

import asyncio
import contextlib
import os
import uuid

import pytest

from src.agents.approval_agent import ApprovalAgent
from src.integrations.telegram import TelegramClient, TelegramError
from src.models.approval import ApprovalContentType, ApprovalStatus
from src.services.approval_service import ApprovalService

# Skip all tests in this module if not running live API tests
pytestmark = [
    pytest.mark.live_api,
    pytest.mark.asyncio,
]


@pytest.fixture
def bot_token() -> str:
    """Get bot token from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("TELEGRAM_BOT_TOKEN not set")
    return token


@pytest.fixture
def test_chat_id() -> int:
    """Get test chat ID from environment."""
    chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
    if not chat_id:
        pytest.skip("TELEGRAM_TEST_CHAT_ID not set")
    return int(chat_id)


@pytest.fixture
def test_user_id() -> int:
    """Get test user ID from environment."""
    user_id = os.getenv("TELEGRAM_TEST_USER_ID")
    if not user_id:
        pytest.skip("TELEGRAM_TEST_USER_ID not set")
    return int(user_id)


@pytest.fixture
async def telegram_client(bot_token: str) -> TelegramClient:
    """Create a real TelegramClient."""
    client = TelegramClient(bot_token=bot_token)
    yield client
    await client.close()


@pytest.fixture
async def approval_service(telegram_client: TelegramClient) -> ApprovalService:
    """Create ApprovalService with real Telegram client."""
    service = ApprovalService(
        telegram_client=telegram_client,
        edit_form_base_url="https://test.example.com/approvals",
    )
    yield service
    await service.close()


@pytest.fixture
async def approval_agent(bot_token: str) -> ApprovalAgent:
    """Create and initialize ApprovalAgent."""
    agent = ApprovalAgent(
        bot_token=bot_token,
        edit_form_base_url="https://test.example.com/approvals",
    )
    await agent.initialize()
    yield agent
    await agent.close()


class TestTelegramClientConnection:
    """Test Telegram API connectivity."""

    async def test_get_me(self, telegram_client: TelegramClient) -> None:
        """Test bot info retrieval."""
        bot_info = await telegram_client.get_me()

        assert bot_info.is_bot is True
        assert bot_info.username is not None
        print(f"Connected as @{bot_info.username}")

    async def test_health_check(self, telegram_client: TelegramClient) -> None:
        """Test health check endpoint."""
        health = await telegram_client.health_check()

        assert health["healthy"] is True
        assert "message" in health

    async def test_send_simple_message(
        self,
        telegram_client: TelegramClient,
        test_chat_id: int,
    ) -> None:
        """Test sending a simple text message."""
        message = await telegram_client.send_message(
            chat_id=test_chat_id,
            text="🧪 Test message from approval workflow live tests",
        )

        assert message.message_id > 0
        print(f"Sent message ID: {message.message_id}")

        # Clean up - delete the test message
        await telegram_client.delete_message(
            chat_id=test_chat_id,
            message_id=message.message_id,
        )


class TestApprovalWorkflowEndToEnd:
    """End-to-end tests for approval workflow."""

    async def test_send_budget_approval(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test sending a budget approval request."""
        request_id = await approval_agent.send_budget_approval(
            title="🧪 Test Budget Request",
            amount=15000.00,
            department="Engineering",
            description="Test budget approval for live API testing.\n\nThis is a test request.",
            requester_id=test_user_id,
            approver_id=test_user_id,  # Self-approval for testing
            chat_id=test_chat_id,
        )

        assert request_id is not None
        assert len(request_id) == 36  # UUID format

        # Verify request was stored
        request = await approval_agent.get_request(request_id)
        assert request["title"] == "🧪 Test Budget Request"
        assert request["status"] == ApprovalStatus.PENDING.value
        assert request["data"]["amount"] == 15000.00

        print(f"Created budget approval request: {request_id}")

    async def test_send_document_approval(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test sending a document approval request."""
        request_id = await approval_agent.send_document_approval(
            title="🧪 Test Contract Review",
            description="Please review the attached contract for legal compliance.",
            file_url="https://example.com/contracts/test-contract.pdf",
            document_type="Contract",
            requester_id=test_user_id,
            approver_id=test_user_id,
            chat_id=test_chat_id,
        )

        assert request_id is not None

        request = await approval_agent.get_request(request_id)
        assert request["content_type"] == ApprovalContentType.DOCUMENT.value
        assert request["data"]["file_url"] == "https://example.com/contracts/test-contract.pdf"

        print(f"Created document approval request: {request_id}")

    async def test_send_content_approval(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test sending a content approval request."""
        blog_content = """# How to Test Your Code

Testing is essential for maintaining code quality.

## Why Test?

1. Catch bugs early
2. Document behavior
3. Enable refactoring

## Conclusion

Write tests!"""

        request_id = await approval_agent.send_content_approval(
            title="🧪 Test Blog Post",
            content_text=blog_content,
            tags=["testing", "engineering", "best-practices"],
            requester_id=test_user_id,
            approver_id=test_user_id,
            chat_id=test_chat_id,
        )

        assert request_id is not None

        request = await approval_agent.get_request(request_id)
        assert request["content_type"] == ApprovalContentType.CONTENT.value
        assert "testing" in request["data"]["tags"]

        print(f"Created content approval request: {request_id}")

    async def test_send_custom_approval(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test sending a custom approval request."""
        request_id = await approval_agent.send_approval(
            title="🧪 Custom Request",
            content="This is a custom approval request for testing.",
            requester_id=test_user_id,
            approver_id=test_user_id,
            chat_id=test_chat_id,
            content_type="custom",
            data={"custom_field": "custom_value", "priority": "high"},
        )

        assert request_id is not None

        request = await approval_agent.get_request(request_id)
        assert request["content_type"] == ApprovalContentType.CUSTOM.value
        assert request["data"]["custom_field"] == "custom_value"

        print(f"Created custom approval request: {request_id}")

    async def test_list_pending_approvals(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test listing pending approvals for a user."""
        # Create a test request first
        await approval_agent.send_approval(
            title="🧪 Pending Test",
            content="Test request for listing",
            requester_id=test_user_id,
            approver_id=test_user_id,
            chat_id=test_chat_id,
        )

        # List pending
        pending = await approval_agent.list_pending(test_user_id)

        assert isinstance(pending, list)
        assert len(pending) >= 1

        # All should be pending
        for req in pending:
            assert req["status"] == ApprovalStatus.PENDING.value

        print(f"Found {len(pending)} pending approvals")


class TestApprovalServiceDirect:
    """Direct tests of ApprovalService."""

    async def test_format_budget_message(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Test budget message formatting."""
        message = approval_service.format_approval_message(
            title="Budget Request",
            content="Department budget for Q1",
            content_type=ApprovalContentType.BUDGET,
            data={"amount": 25000, "department": "Marketing"},
        )

        assert "Budget Request" in message
        assert "$25,000" in message
        assert "Marketing" in message
        assert "📊" in message  # Budget emoji

    async def test_format_document_message(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Test document message formatting."""
        message = approval_service.format_approval_message(
            title="Contract Review",
            content="Partnership agreement needs review",
            content_type=ApprovalContentType.DOCUMENT,
            data={
                "file_url": "https://example.com/doc.pdf",
                "document_type": "Contract",
            },
        )

        assert "Contract Review" in message
        assert "https://example.com/doc.pdf" in message
        assert "📄" in message  # Document emoji

    async def test_generate_and_verify_edit_token(
        self,
        approval_service: ApprovalService,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test edit token generation and verification."""
        # Create a request
        request_id = await approval_service.send_approval_request(
            request_data={
                "title": "Token Test",
                "content": "Test content",
                "requester_id": test_user_id,
                "approver_id": test_user_id,
                "telegram_chat_id": test_chat_id,
                "content_type": "custom",
                "data": {},
            }
        )

        # Generate edit token
        edit_url = await approval_service.generate_edit_token(request_id)
        assert "token=" in edit_url

        # Extract token from URL
        token = edit_url.split("token=")[1]

        # Verify token
        request = await approval_service.get_request_by_edit_token(token)
        assert request is not None
        assert request.id == request_id


class TestAgentHealthAndLifecycle:
    """Test agent health checks and lifecycle."""

    async def test_agent_health_check(
        self,
        approval_agent: ApprovalAgent,
    ) -> None:
        """Test agent health check."""
        health = await approval_agent.health_check()

        assert health["name"] == "approval_agent"
        assert health["healthy"] is True
        assert "polling_active" in health

    async def test_agent_context_manager(self, bot_token: str) -> None:
        """Test agent as async context manager."""
        async with ApprovalAgent(bot_token=bot_token) as agent:
            health = await agent.health_check()
            assert health["healthy"] is True

        # After exit, should be closed
        assert agent.telegram_client is None

    async def test_polling_start_stop(
        self,
        approval_agent: ApprovalAgent,
    ) -> None:
        """Test starting and stopping polling."""
        # Start polling
        await approval_agent.start_polling(timeout=5)
        assert approval_agent.polling_active is True

        # Wait briefly
        await asyncio.sleep(1)

        # Stop polling
        await approval_agent.stop_polling()
        assert approval_agent.polling_active is False


class TestErrorHandling:
    """Test error handling with real API."""

    async def test_invalid_chat_id(
        self,
        approval_agent: ApprovalAgent,
        test_user_id: int,
    ) -> None:
        """Test sending to invalid chat ID."""
        with pytest.raises(TelegramError):
            await approval_agent.send_approval(
                title="Test",
                content="Test",
                requester_id=test_user_id,
                approver_id=test_user_id,
                chat_id=0,  # Invalid
            )

    async def test_nonexistent_request(
        self,
        approval_agent: ApprovalAgent,
    ) -> None:
        """Test getting nonexistent request."""
        fake_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="not found"):
            await approval_agent.get_request(fake_id)


class TestRateLimiting:
    """Test behavior under rate limiting."""

    async def test_rapid_message_sending(
        self,
        approval_agent: ApprovalAgent,
        test_chat_id: int,
        test_user_id: int,
    ) -> None:
        """Test sending multiple messages rapidly."""
        request_ids = []

        # Send 5 requests rapidly
        for i in range(5):
            request_id = await approval_agent.send_approval(
                title=f"🧪 Rate Test {i + 1}",
                content=f"Testing rate limiting - message {i + 1}",
                requester_id=test_user_id,
                approver_id=test_user_id,
                chat_id=test_chat_id,
            )
            request_ids.append(request_id)

        # All should succeed (Telegram allows 1/sec per chat)
        assert len(request_ids) == 5
        print(f"Successfully sent {len(request_ids)} messages")


# =============================================================================
# CLEANUP UTILITY
# =============================================================================


async def cleanup_test_messages(
    telegram_client: TelegramClient,
    chat_id: int,
    message_ids: list[int],
) -> None:
    """Utility to clean up test messages."""
    for msg_id in message_ids:
        with contextlib.suppress(TelegramError):
            await telegram_client.delete_message(chat_id=chat_id, message_id=msg_id)
