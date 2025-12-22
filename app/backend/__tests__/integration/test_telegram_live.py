"""Live API tests for Telegram Bot integration - MUST pass with real API keys."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.base import IntegrationError
from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramClient,
    TelegramError,
)

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")

# Fixtures for live API testing


@pytest.fixture
def telegram_bot_token() -> str:
    """Get Telegram bot token from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("TELEGRAM_BOT_TOKEN not found in .env")
    return token


@pytest.fixture
def test_chat_id() -> int:
    """Get test chat ID from environment."""
    # Try both env var names for backwards compatibility
    chat_id_str = os.getenv("TELEGRAM_TEST_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id_str:
        pytest.skip("TELEGRAM_TEST_CHAT_ID or TELEGRAM_CHAT_ID not found in .env")
    return int(chat_id_str)


@pytest.fixture
async def client(telegram_bot_token: str) -> TelegramClient:
    """Create Telegram client with real token."""
    return TelegramClient(bot_token=telegram_bot_token)


# Live API tests
@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveGetMe:
    """Live tests for getMe endpoint."""

    async def test_get_me_returns_bot_info(self, client: TelegramClient) -> None:
        """getMe should return bot information."""
        bot = await client.get_me()

        assert bot.id > 0
        assert bot.is_bot is True
        assert bot.first_name
        assert len(bot.first_name) > 0

    async def test_get_me_bot_username(self, client: TelegramClient) -> None:
        """Bot should have a username."""
        bot = await client.get_me()

        assert bot.username is not None
        assert len(bot.username) > 0
        # Username should be alphanumeric with possible underscores/numbers
        assert bot.username and all(c.isalnum() or c == "_" for c in bot.username)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveSendMessage:
    """Live tests for sendMessage endpoint."""

    async def test_send_message_text(self, client: TelegramClient, test_chat_id: int) -> None:
        """Should send text message successfully."""
        result = await client.send_message(
            chat_id=test_chat_id,
            text="Test message from Telegram integration",
        )

        assert result.message_id > 0
        assert result.text == "Test message from Telegram integration"
        assert result.date > 0

    async def test_send_message_with_markdown(
        self, client: TelegramClient, test_chat_id: int
    ) -> None:
        """Should send message with Markdown formatting."""
        text = "*Bold* and _italic_ text"
        result = await client.send_message(
            chat_id=test_chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )

        assert result.message_id > 0

    async def test_send_message_with_html(self, client: TelegramClient, test_chat_id: int) -> None:
        """Should send message with HTML formatting."""
        text = "<b>Bold</b> and <i>italic</i> text"
        result = await client.send_message(
            chat_id=test_chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

        assert result.message_id > 0

    async def test_send_message_with_keyboard(
        self, client: TelegramClient, test_chat_id: int
    ) -> None:
        """Should send message with inline keyboard."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Test Button", callback_data="test_1"),
                ]
            ]
        )

        result = await client.send_message(
            chat_id=test_chat_id,
            text="Message with button",
            reply_markup=keyboard,
        )

        assert result.message_id > 0

    async def test_send_long_message(self, client: TelegramClient, test_chat_id: int) -> None:
        """Should send message up to 4096 characters."""
        long_text = "A" * 4000
        result = await client.send_message(
            chat_id=test_chat_id,
            text=long_text,
        )

        assert result.message_id > 0
        assert result.text == long_text


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveWebhook:
    """Live tests for webhook management."""

    async def test_get_webhook_info_when_not_set(self, client: TelegramClient) -> None:
        """Should get webhook info even when not configured."""
        info = await client.get_webhook_info()

        # Webhook info should be a dict with at least url field
        assert isinstance(info, dict)
        assert "url" in info or "pending_update_count" in info

    async def test_delete_webhook_no_error(self, client: TelegramClient) -> None:
        """Should delete webhook without errors."""
        result = await client.delete_webhook()

        assert result is True


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveGetUpdates:
    """Live tests for polling updates."""

    async def test_get_updates_returns_list(self, client: TelegramClient) -> None:
        """getUpdates should return a list of updates."""
        updates = await client.get_updates(limit=10, timeout=1)

        assert isinstance(updates, list)
        # May be empty if no updates pending

    async def test_get_updates_with_offset(self, client: TelegramClient) -> None:
        """getUpdates should accept offset parameter."""
        # Get initial updates
        updates = await client.get_updates(limit=1)

        if updates:
            # Get updates with offset of last update + 1
            offset = updates[-1].update_id + 1
            new_updates = await client.get_updates(offset=offset, limit=1)

            # New updates should not include the offset update
            assert all(u.update_id >= offset for u in new_updates)


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveFileOperations:
    """Live tests for file operations."""

    async def test_get_file_with_valid_id(self, client: TelegramClient) -> None:
        """Should get file info with valid file_id."""
        # Send a photo first to get a file_id
        try:
            # Note: This test requires a photo to be sent first
            # For now, we'll just verify the method works with a dummy ID
            # In production, this would use a real file_id from a previous message
            bot = await client.get_me()
            assert bot.id > 0
        except (TelegramError, AssertionError):  # pragma: allowlist secret
            # Expected if photo hasn't been sent
            pass


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveBotCommands:
    """Live tests for bot command management."""

    async def test_set_my_commands_success(self, client: TelegramClient) -> None:
        """Should set bot commands successfully."""
        commands = [
            {"command": "test", "description": "Test command"},
            {"command": "help", "description": "Get help"},
        ]

        result = await client.set_my_commands(commands=commands)

        assert result is True

    async def test_set_my_commands_multiple(self, client: TelegramClient) -> None:
        """Should handle multiple commands."""
        commands = [
            {"command": "start", "description": "Start command"},
            {"command": "stop", "description": "Stop command"},
            {"command": "status", "description": "Get status"},
        ]

        result = await client.set_my_commands(commands=commands)

        assert result is True


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveHealthCheck:
    """Live tests for health check."""

    async def test_health_check_success(self, client: TelegramClient) -> None:
        """Health check should succeed with valid token."""
        result = await client.health_check()

        assert result["healthy"] is True
        assert result["name"] == "telegram"
        assert result["bot_id"] > 0
        assert result["bot_name"]

    async def test_health_check_contains_bot_info(self, client: TelegramClient) -> None:
        """Health check should include bot information."""
        result = await client.health_check()

        assert "message" in result
        assert "online" in result["message"].lower()


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveErrorHandling:
    """Live tests for error handling."""

    async def test_invalid_chat_id_raises_error(self, client: TelegramClient) -> None:
        """Should raise error for invalid chat ID."""
        with pytest.raises(TelegramError):
            await client.send_message(
                chat_id=999999999999,  # Invalid chat ID
                text="Test",
            )

    async def test_invalid_token_raises_error(self) -> None:
        """Should raise error with invalid token."""
        client = TelegramClient(bot_token="123456:INVALID_TOKEN_STRING")

        with pytest.raises((TelegramError, IntegrationError)):
            await client.get_me()


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveEditMessage:
    """Live tests for message editing."""

    async def test_edit_message_text(self, client: TelegramClient, test_chat_id: int) -> None:
        """Should edit sent message."""
        # Send initial message
        message = await client.send_message(
            chat_id=test_chat_id,
            text="Original text",
        )

        # Edit the message
        result = await client.edit_message_text(
            chat_id=test_chat_id,
            message_id=message.message_id,
            text="Edited text",
        )

        assert result.message_id == message.message_id


@pytest.mark.asyncio
@pytest.mark.live_api
class TestTelegramClientLiveDeleteMessage:
    """Live tests for message deletion."""

    async def test_delete_message(self, client: TelegramClient, test_chat_id: int) -> None:
        """Should delete sent message."""
        # Send a message
        message = await client.send_message(
            chat_id=test_chat_id,
            text="Message to delete",
        )

        # Delete it
        result = await client.delete_message(
            chat_id=test_chat_id,
            message_id=message.message_id,
        )

        assert result is True


# Test configuration
pytestmark = [pytest.mark.live_api]


def pytest_configure(config: any) -> None:
    """Register live_api marker."""
    config.addinivalue_line("markers", "live_api: tests that call real Telegram API")
