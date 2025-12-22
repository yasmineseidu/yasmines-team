"""Unit tests for Telegram Bot API integration client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.base import IntegrationError
from src.integrations.telegram import (
    Chat,
    ChatType,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageEntityType,
    ParseMode,
    TelegramClient,
    TelegramError,
    TelegramRateLimitError,
    User,
)


class TestTelegramClientInitialization:
    """Tests for TelegramClient initialization."""

    def test_initialization_with_valid_token(self) -> None:
        """Client should initialize with valid bot token."""
        client = TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        assert client.bot_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert client.name == "telegram"
        assert client.base_url == "https://api.telegram.org"

    def test_initialization_with_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", timeout=60.0)
        assert client.timeout == 60.0

    def test_initialization_raises_on_invalid_token_format(self) -> None:
        """Client should raise ValueError for invalid token format."""
        with pytest.raises(ValueError, match="Invalid bot token format"):
            TelegramClient(bot_token="invalid-token-without-colon")

    def test_initialization_raises_on_empty_token(self) -> None:
        """Client should raise ValueError for empty token."""
        with pytest.raises(ValueError, match="Invalid bot token format"):
            TelegramClient(bot_token="")


class TestTelegramClientGetHeaders:
    """Tests for HTTP headers generation."""

    def test_headers_do_not_include_authorization(self) -> None:
        """Telegram headers should NOT include Authorization."""
        client = TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        headers = client._get_headers()

        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestTelegramClientSendMessage:
    """Tests for send_message method."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_send_message_basic(self, client: TelegramClient) -> None:
        """Should send basic text message."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "message_id": 42,
                "date": 1234567890,
                "text": "Hello",
            }

            result = await client.send_message(chat_id=123456, text="Hello")

            assert result.message_id == 42
            assert result.date == 1234567890
            assert result.text == "Hello"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_parse_mode(self, client: TelegramClient) -> None:
        """Should send message with parse mode."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": 42, "date": 1234567890}

            await client.send_message(
                chat_id=123456, text="**Bold**", parse_mode=ParseMode.MARKDOWN
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_send_message_with_keyboard(self, client: TelegramClient) -> None:
        """Should send message with inline keyboard."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Click", callback_data="action_1"),
                ]
            ]
        )

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": 42, "date": 1234567890}

            await client.send_message(chat_id=123456, text="Hello", reply_markup=keyboard)

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert "reply_markup" in payload
            assert "inline_keyboard" in payload["reply_markup"]

    @pytest.mark.asyncio
    async def test_send_message_to_group(self, client: TelegramClient) -> None:
        """Should send message to group chat."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": 42, "date": 1234567890}

            result = await client.send_message(chat_id=-123456, text="Group message")

            assert result.message_id == 42
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["chat_id"] == -123456


class TestTelegramClientSendPhoto:
    """Tests for send_photo method."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_send_photo_with_file_id(self, client: TelegramClient) -> None:
        """Should send photo using file_id."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": 42, "date": 1234567890}

            result = await client.send_photo(chat_id=123456, photo="AgACAgIAAxkBAAI...")

            assert result.message_id == 42
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["photo"] == "AgACAgIAAxkBAAI..."

    @pytest.mark.asyncio
    async def test_send_photo_with_caption(self, client: TelegramClient) -> None:
        """Should send photo with caption."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": 42, "date": 1234567890}

            await client.send_photo(
                chat_id=123456,
                photo="AgACAgIAAxkBAAI...",
                caption="Beautiful photo",
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload.get("caption") == "Beautiful photo"


class TestTelegramClientGetUpdates:
    """Tests for get_updates method (polling)."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_get_updates_basic(self, client: TelegramClient) -> None:
        """Should retrieve updates via polling."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = [
                {
                    "update_id": 123,
                    "message": {
                        "message_id": 1,
                        "date": 1234567890,
                        "text": "Hello bot",
                    },
                }
            ]

            updates = await client.get_updates()

            assert len(updates) == 1
            assert updates[0].update_id == 123
            assert updates[0].message is not None
            assert updates[0].message.text == "Hello bot"

    @pytest.mark.asyncio
    async def test_get_updates_with_offset(self, client: TelegramClient) -> None:
        """Should retrieve updates with offset."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = []

            await client.get_updates(offset=100)

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["offset"] == 100

    @pytest.mark.asyncio
    async def test_get_updates_with_callback_query(self, client: TelegramClient) -> None:
        """Should retrieve updates with callback queries."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = [
                {
                    "update_id": 456,
                    "callback_query": {
                        "id": "callback_123",
                        "from": {"id": 111, "is_bot": False, "first_name": "User"},
                        "data": "action_1",
                    },
                }
            ]

            updates = await client.get_updates()

            assert len(updates) == 1
            assert updates[0].callback_query is not None
            assert updates[0].callback_query["data"] == "action_1"


class TestTelegramClientWebhook:
    """Tests for webhook methods."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_set_webhook(self, client: TelegramClient) -> None:
        """Should set webhook URL."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            result = await client.set_webhook(url="https://example.com/telegram")

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["url"] == "https://example.com/telegram"

    @pytest.mark.asyncio
    async def test_set_webhook_with_secret_token(self, client: TelegramClient) -> None:
        """Should set webhook with secret token."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            await client.set_webhook(  # pragma: allowlist secret
                url="https://example.com/telegram",
                secret_token="secret123",  # pragma: allowlist secret
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload.get("secret_token") == "secret123"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client: TelegramClient) -> None:
        """Should delete webhook."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            result = await client.delete_webhook()

            assert result is True
            mock_post.assert_called_once_with("/deleteWebhook", json={})

    @pytest.mark.asyncio
    async def test_get_webhook_info(self, client: TelegramClient) -> None:
        """Should get webhook information."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "url": "https://example.com/telegram",
                "has_custom_certificate": False,
                "pending_update_count": 0,
            }

            result = await client.get_webhook_info()

            assert result["url"] == "https://example.com/telegram"


class TestTelegramClientCallbackQuery:
    """Tests for callback query handling."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_answer_callback_query_notification(self, client: TelegramClient) -> None:
        """Should answer callback query with notification."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            result = await client.answer_callback_query(
                callback_query_id="callback_123", text="Thanks for clicking!"
            )

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["text"] == "Thanks for clicking!"

    @pytest.mark.asyncio
    async def test_answer_callback_query_alert(self, client: TelegramClient) -> None:
        """Should answer callback query with alert."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            await client.answer_callback_query(
                callback_query_id="callback_123",
                text="Error occurred",
                show_alert=True,
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["show_alert"] is True


class TestTelegramClientGroupManagement:
    """Tests for group management methods."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_ban_chat_member(self, client: TelegramClient) -> None:
        """Should ban user from chat."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            result = await client.ban_chat_member(chat_id=-123456, user_id=789)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["chat_id"] == -123456
            assert payload["user_id"] == 789

    @pytest.mark.asyncio
    async def test_unban_chat_member(self, client: TelegramClient) -> None:
        """Should unban user from chat."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            result = await client.unban_chat_member(chat_id=-123456, user_id=789)

            assert result is True

    @pytest.mark.asyncio
    async def test_get_chat_member(self, client: TelegramClient) -> None:
        """Should get chat member information."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "status": "member",
                "user": {"id": 789, "is_bot": False, "first_name": "User"},
            }

            result = await client.get_chat_member(chat_id=-123456, user_id=789)

            assert result["status"] == "member"
            assert result["user"]["id"] == 789


class TestTelegramClientBotCommands:
    """Tests for bot command management."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_set_my_commands(self, client: TelegramClient) -> None:
        """Should set bot commands."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = True

            commands = [
                {"command": "start", "description": "Start the bot"},
                {"command": "help", "description": "Get help"},
            ]
            result = await client.set_my_commands(commands=commands)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert len(payload["commands"]) == 2


class TestTelegramClientFileOperations:
    """Tests for file operations."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_get_file(self, client: TelegramClient) -> None:
        """Should get file information."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "file_id": "AgACAgIAAxkBAAI...",
                "file_unique_id": "AQADf7...",
                "file_size": 1234,
                "file_path": "photos/file_123.jpg",
            }

            result = await client.get_file("AgACAgIAAxkBAAI...")

            assert result["file_path"] == "photos/file_123.jpg"

    @pytest.mark.asyncio
    async def test_get_file_url(self, client: TelegramClient) -> None:
        """Should generate file download URL."""
        with patch.object(client, "get_file", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"file_path": "photos/file_123.jpg"}

            url = await client.get_file_url("AgACAgIAAxkBAAI...")

            assert (
                url
                == "https://api.telegram.org/file/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/photos/file_123.jpg"
            )


class TestTelegramClientBotInfo:
    """Tests for getting bot information."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_get_me(self, client: TelegramClient) -> None:
        """Should get bot information."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": 123456789,
                "is_bot": True,
                "first_name": "TestBot",
                "username": "test_bot",
                "can_join_groups": True,
                "can_read_all_group_messages": False,
                "supports_inline_queries": False,
            }

            bot = await client.get_me()

            assert bot.id == 123456789
            assert bot.is_bot is True
            assert bot.first_name == "TestBot"
            assert bot.username == "test_bot"


class TestTelegramClientHealthCheck:
    """Tests for health check."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: TelegramClient) -> None:
        """Should return healthy status."""
        with patch.object(client, "get_me", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = User(
                id=123456789,
                is_bot=True,
                first_name="TestBot",
                username="test_bot",
            )

            result = await client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "telegram"
            assert result["bot_id"] == 123456789

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: TelegramClient) -> None:
        """Should return unhealthy status on error."""
        with patch.object(client, "get_me", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.health_check()

            assert result["healthy"] is False
            assert "failed" in result["message"].lower()


class TestTelegramClientWebhookVerification:
    """Tests for webhook token verification."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(  # pragma: allowlist secret
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"  # pragma: allowlist secret
        )

    def test_verify_webhook_token_valid(self, client: TelegramClient) -> None:
        """Should verify valid webhook token."""
        secret = "my-secret-token-123"  # pragma: allowlist secret
        result = client.verify_webhook_token(secret, secret)
        assert result is True

    def test_verify_webhook_token_invalid(self, client: TelegramClient) -> None:
        """Should reject invalid webhook token."""
        result = client.verify_webhook_token("my-secret-token-123", "different-token")
        assert result is False


class TestTelegramClientDataClasses:
    """Tests for data classes and enums."""

    def test_user_dataclass(self) -> None:
        """Should create User object."""
        user = User(id=123, is_bot=True, first_name="Bot")
        assert user.id == 123
        assert user.is_bot is True
        assert user.first_name == "Bot"

    def test_chat_dataclass(self) -> None:
        """Should create Chat object."""
        chat = Chat(id=-123, type="group", title="Test Group")
        assert chat.id == -123
        assert chat.type == "group"
        assert chat.title == "Test Group"

    def test_message_dataclass(self) -> None:
        """Should create Message object."""
        message = Message(message_id=1, date=1234567890, text="Hello")
        assert message.message_id == 1
        assert message.text == "Hello"

    def test_parse_mode_enum(self) -> None:
        """Should have ParseMode enums."""
        assert ParseMode.MARKDOWN.value == "Markdown"
        assert ParseMode.MARKDOWN_V2.value == "MarkdownV2"
        assert ParseMode.HTML.value == "HTML"

    def test_chat_type_enum(self) -> None:
        """Should have ChatType enums."""
        assert ChatType.PRIVATE.value == "private"
        assert ChatType.GROUP.value == "group"
        assert ChatType.SUPERGROUP.value == "supergroup"
        assert ChatType.CHANNEL.value == "channel"

    def test_message_entity_type_enum(self) -> None:
        """Should have MessageEntityType enums."""
        assert MessageEntityType.BOLD.value == "bold"
        assert MessageEntityType.ITALIC.value == "italic"
        assert MessageEntityType.BOT_COMMAND.value == "bot_command"


class TestInlineKeyboardMarkup:
    """Tests for inline keyboard markup."""

    def test_inline_keyboard_to_dict(self) -> None:
        """Should convert keyboard to dict format."""
        button1 = InlineKeyboardButton(text="Button 1", callback_data="action_1")
        button2 = InlineKeyboardButton(text="Button 2", url="https://example.com")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button1, button2]])
        result = keyboard.to_dict()

        assert "inline_keyboard" in result
        assert len(result["inline_keyboard"]) == 1
        assert len(result["inline_keyboard"][0]) == 2
        assert result["inline_keyboard"][0][0]["text"] == "Button 1"
        assert result["inline_keyboard"][0][0]["callback_data"] == "action_1"
        assert result["inline_keyboard"][0][1]["url"] == "https://example.com"

    def test_inline_keyboard_multiple_rows(self) -> None:
        """Should handle multiple keyboard rows."""
        row1 = [InlineKeyboardButton(text="A", callback_data="a")]
        row2 = [InlineKeyboardButton(text="B", callback_data="b")]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[row1, row2])
        result = keyboard.to_dict()

        assert len(result["inline_keyboard"]) == 2
        assert result["inline_keyboard"][0][0]["text"] == "A"
        assert result["inline_keyboard"][1][0]["text"] == "B"


class TestTelegramClientErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> TelegramClient:
        """Create test client."""
        return TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @pytest.mark.asyncio
    async def test_handle_telegram_error(self, client: TelegramClient) -> None:
        """Should raise TelegramError on API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Bad request",
        }

        with pytest.raises(TelegramError):
            await client._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, client: TelegramClient) -> None:
        """Should raise TelegramRateLimitError on 429 response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 429,
            "description": "Too many requests",
        }

        with pytest.raises(TelegramRateLimitError) as exc_info:
            await client._handle_response(mock_response)

        assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_handle_authentication_error(self, client: TelegramClient) -> None:
        """Should raise IntegrationError on 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized",  # pragma: allowlist secret
        }

        with pytest.raises(IntegrationError):
            await client._handle_response(mock_response)
