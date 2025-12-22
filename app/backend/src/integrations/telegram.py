"""
Telegram Bot API integration client.

Provides bot interactions through Telegram's Bot API.
Supports sending messages, handling updates via webhook/polling,
managing groups, and interactive features.

API Documentation: https://core.telegram.org/bots/api
Base URL: https://api.telegram.org/bot

Rate Limits:
- 30 requests per second (global limit)
- 20 text messages per minute per chat
- 5 media messages per minute per chat
- Layer 167+ (Feb 2025): retry_after is per-chat, not per-token

Authentication:
- Bot tokens embedded in URL path: /bot<token>/METHOD
- Webhook requires X-Telegram-Bot-Api-Secret-Token header
- NOT bearer token authentication

Example:
    >>> from src.integrations.telegram import TelegramClient
    >>> client = TelegramClient(bot_token="123456:ABC-DEF...")
    >>> message = await client.send_message(
    ...     chat_id=987654321,
    ...     text="Hello from Telegram bot!"
    ... )
    >>> webhook_info = await client.set_webhook(  # pragma: allowlist secret
    ...     url="https://example.com/telegram/webhook",
    ...     secret_token="your-secret-token"  # pragma: allowlist secret
    ... )
"""

import hmac
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class TelegramError(IntegrationError):
    """Telegram-specific API error."""

    pass


class TelegramRateLimitError(RateLimitError):
    """Telegram rate limit error with retry_after handling."""

    pass


class ChatType(str, Enum):
    """Telegram chat types."""

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class ParseMode(str, Enum):
    """Telegram message parse modes."""

    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"


class MessageEntityType(str, Enum):
    """Telegram message entity types."""

    MENTION = "mention"
    HASHTAG = "hashtag"
    CASHTAG = "cashtag"
    BOT_COMMAND = "bot_command"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    SPOILER = "spoiler"
    CODE = "code"
    PRE = "pre"
    TEXT_LINK = "text_link"
    TEXT_MENTION = "text_mention"


@dataclass
class User:
    """Telegram User object."""

    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool = False
    added_to_attachment_menu: bool = False
    can_join_groups: bool = True
    can_read_all_group_messages: bool = False
    supports_inline_queries: bool = False
    can_connect_to_business: bool = False
    has_main_web_app: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chat:
    """Telegram Chat object."""

    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    description: str | None = None
    photo_id: str | None = None
    permissions: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Telegram Message object."""

    message_id: int
    date: int
    chat: Chat | None = None
    from_user: User | None = None
    text: str | None = None
    caption: str | None = None
    entities: list[dict[str, Any]] = field(default_factory=list)
    document_file_id: str | None = None
    photo_file_ids: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Update:
    """Telegram Update object."""

    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
    channel_post: Message | None = None
    edited_channel_post: Message | None = None
    callback_query: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class InlineKeyboardButton:
    """Inline keyboard button."""

    text: str
    url: str | None = None
    callback_data: str | None = None
    web_app: dict[str, str] | None = None
    switch_inline_query: str | None = None
    switch_inline_query_current_chat: str | None = None
    pay: bool = False


@dataclass
class InlineKeyboardMarkup:
    """Inline keyboard markup."""

    inline_keyboard: list[list[InlineKeyboardButton]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to Telegram API format."""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": button.text,
                        **{
                            k: v
                            for k, v in {
                                "url": button.url,
                                "callback_data": button.callback_data,
                                "web_app": button.web_app,
                                "switch_inline_query": button.switch_inline_query,
                                "switch_inline_query_current_chat": (
                                    button.switch_inline_query_current_chat
                                ),
                                "pay": button.pay if button.pay else None,
                            }.items()
                            if v is not None
                        },
                    }
                    for button in row
                ]
                for row in self.inline_keyboard
            ]
        }


class TelegramClient(BaseIntegrationClient):
    """
    Telegram Bot API client for sending messages and handling updates.

    Supports:
    - Message sending (text, media, interactive)
    - Webhook configuration and updates
    - Long polling for updates
    - Group management
    - File operations
    - Callback query handling

    Rate limiting is handled per-chat (layer 167+).
    """

    def __init__(self, bot_token: str, timeout: float = 30.0) -> None:
        """
        Initialize Telegram Bot client.

        Args:
            bot_token: Bot token from @BotFather (format: 123456:ABC-DEF...)
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If bot_token is invalid format.
        """
        if not bot_token or ":" not in bot_token:
            raise ValueError("Invalid bot token format. Expected: 'bot_id:token_string'")

        self.bot_token = bot_token
        super().__init__(
            name="telegram",
            base_url="https://api.telegram.org",
            api_key=bot_token,
            timeout=timeout,
        )
        logger.info("Initialized Telegram Bot client")

    def _get_headers(self) -> dict[str, str]:
        """
        Override to use Telegram's bot token in URL, not Authorization header.

        Returns:
            HTTP headers without Authorization.
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Override to inject bot token into URL path.

        Args:
            method: HTTP method.
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed API response.

        Raises:
            TelegramError: On API error.
            TelegramRateLimitError: On rate limit (429) with retry_after.
        """
        # Inject bot token into URL path
        endpoint = f"/bot{self.bot_token}{endpoint}"
        return await super()._request_with_retry(method, endpoint, **kwargs)

    async def _handle_response(
        self,
        response: Any,
    ) -> dict[str, Any]:
        """
        Override to handle Telegram-specific response format.

        Telegram wraps all responses in {"ok": bool, "result": ...}.

        Args:
            response: HTTP response object.

        Returns:
            Parsed response data (the 'result' field).

        Raises:
            TelegramError: On API error.
            TelegramRateLimitError: On rate limit with retry_after.
        """
        try:
            data = response.json()
        except Exception:
            data = {"ok": False, "error_code": 500, "description": response.text}

        # Handle rate limit with per-chat retry_after
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise TelegramRateLimitError(
                message="[telegram] Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                status_code=429,
                response_data=data,
            )

        # Check Telegram's "ok" field
        if not data.get("ok", False):
            error_code = data.get("error_code", 400)
            description = data.get("description", "Unknown Telegram error")

            if error_code == 401:
                raise IntegrationError(
                    message=f"[telegram] Authentication failed: {description}",
                    status_code=401,
                    response_data=data,
                )

            raise TelegramError(
                message=f"[telegram] API error: {description}",
                status_code=error_code,
                response_data=data,
            )

        result: dict[str, Any] = data.get("result", {})
        return result

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: ParseMode | str | None = None,
        entities: list[dict[str, Any]] | None = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        protect_content: bool = False,
        reply_to_message_id: int | None = None,
        allow_sending_without_reply: bool = True,
        reply_markup: InlineKeyboardMarkup | dict[str, Any] | None = None,
        message_thread_id: int | None = None,
    ) -> Message:
        """
        Send text message to user or chat.

        Args:
            chat_id: Unique identifier for target chat or user ID.
            text: Text of the message (1-4096 characters).
            parse_mode: Mode for parsing entities ("Markdown", "MarkdownV2", "HTML").
            entities: A list of special entities that appear in message text.
            disable_web_page_preview: Disables link previews.
            disable_notification: Sends message silently.
            protect_content: Protects content from forwarding/saving.
            reply_to_message_id: If reply, ID of original message.
            allow_sending_without_reply: Pass True if reply_to_message_id
                points to deleted message.
            reply_markup: Additional interface options (InlineKeyboardMarkup, etc).
            message_thread_id: Unique identifier of message thread (topic) if in forum.

        Returns:
            Message object.

        Raises:
            TelegramError: On API error.
            TelegramRateLimitError: On rate limit.
        """
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if entities:
            payload["entities"] = entities

        if disable_web_page_preview:
            payload["disable_web_page_preview"] = disable_web_page_preview

        if disable_notification:
            payload["disable_notification"] = disable_notification

        if protect_content:
            payload["protect_content"] = protect_content

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        if not allow_sending_without_reply:
            payload["allow_sending_without_reply"] = allow_sending_without_reply

        if reply_markup:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                payload["reply_markup"] = reply_markup.to_dict()
            else:
                payload["reply_markup"] = reply_markup

        if message_thread_id:
            payload["message_thread_id"] = message_thread_id

        result = await self.post("/sendMessage", json=payload)

        # Parse message response
        return Message(
            message_id=result.get("message_id", 0),
            date=result.get("date", 0),
            text=result.get("text"),
            raw=result,
        )

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str | bytes,
        caption: str | None = None,
        parse_mode: ParseMode | str | None = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        reply_markup: InlineKeyboardMarkup | dict[str, Any] | None = None,
    ) -> Message:
        """
        Send photo to user or chat.

        Args:
            chat_id: Unique identifier for target chat.
            photo: Photo file (file_id, URL, or bytes).
            caption: Photo caption (0-1024 characters).
            parse_mode: Mode for parsing caption entities.
            disable_notification: Sends photo silently.
            reply_to_message_id: If reply, ID of original message.
            reply_markup: Additional interface options.

        Returns:
            Message object.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {
            "chat_id": chat_id,
        }

        if caption:
            payload["caption"] = caption

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if disable_notification:
            payload["disable_notification"] = disable_notification

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        if reply_markup:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                payload["reply_markup"] = reply_markup.to_dict()
            else:
                payload["reply_markup"] = reply_markup

        # Handle photo file
        if isinstance(photo, bytes):
            # File upload
            files = {"photo": ("photo.jpg", photo, "image/jpeg")}
            response = await self.client.post(
                f"{self.base_url}/bot{self.bot_token}/sendPhoto",
                data=payload,
                files=files,
            )
            result = await self._handle_response(response)
        else:
            # File ID or URL
            payload["photo"] = photo
            result = await self.post("/sendPhoto", json=payload)

        return Message(
            message_id=result.get("message_id", 0),
            date=result.get("date", 0),
            caption=result.get("caption"),
            raw=result,
        )

    async def send_document(
        self,
        chat_id: int | str,
        document: str | bytes,
        caption: str | None = None,
        parse_mode: ParseMode | str | None = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        reply_markup: InlineKeyboardMarkup | dict[str, Any] | None = None,
    ) -> Message:
        """
        Send document to user or chat.

        Args:
            chat_id: Unique identifier for target chat.
            document: Document file (file_id, URL, or bytes).
            caption: Document caption (0-1024 characters).
            parse_mode: Mode for parsing caption entities.
            disable_notification: Sends document silently.
            reply_to_message_id: If reply, ID of original message.
            reply_markup: Additional interface options.

        Returns:
            Message object.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {
            "chat_id": chat_id,
        }

        if caption:
            payload["caption"] = caption

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if disable_notification:
            payload["disable_notification"] = disable_notification

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        if reply_markup:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                payload["reply_markup"] = reply_markup.to_dict()
            else:
                payload["reply_markup"] = reply_markup

        if isinstance(document, bytes):
            files = {"document": ("file.pdf", document, "application/pdf")}
            response = await self.client.post(
                f"{self.base_url}/bot{self.bot_token}/sendDocument",
                data=payload,
                files=files,
            )
            result = await self._handle_response(response)
        else:
            payload["document"] = document
            result = await self.post("/sendDocument", json=payload)

        return Message(
            message_id=result.get("message_id", 0),
            date=result.get("date", 0),
            caption=result.get("caption"),
            raw=result,
        )

    async def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 0,
        allowed_updates: list[str] | None = None,
    ) -> list[Update]:
        """
        Get incoming updates using long polling.

        Args:
            offset: Identifier of the first update to be returned.
            limit: Limits updates in response (1-100, default 100).
            timeout: Timeout in seconds for polling (0-50, default 0).
            allowed_updates: List of update types to request (message, callback_query, etc).

        Returns:
            List of Update objects.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"limit": limit, "timeout": timeout}

        if offset is not None:
            payload["offset"] = offset

        if allowed_updates:
            payload["allowed_updates"] = allowed_updates

        raw_results: Any = await self.post("/getUpdates", json=payload)

        updates: list[Update] = []
        if not isinstance(raw_results, list):
            return updates

        for update_data in raw_results:
            update = Update(
                update_id=update_data.get("update_id", 0),
                raw=update_data,
            )
            if "message" in update_data:
                msg = update_data["message"]
                update.message = Message(
                    message_id=msg.get("message_id", 0),
                    date=msg.get("date", 0),
                    text=msg.get("text"),
                    raw=msg,
                )
            if "callback_query" in update_data:
                update.callback_query = update_data["callback_query"]

            updates.append(update)

        return updates

    async def set_webhook(
        self,
        url: str,
        certificate: bytes | None = None,
        ip_address: str | None = None,
        max_connections: int = 40,
        allowed_updates: list[str] | None = None,
        drop_pending_updates: bool = False,
        secret_token: str | None = None,
    ) -> bool:
        """
        Set webhook URL for receiving updates.

        Args:
            url: HTTPS URL to send updates to.
            certificate: Upload PEM certificate for custom verification.
            ip_address: Static IP address of webhook.
            max_connections: Maximum concurrent webhook connections (1-100).
            allowed_updates: List of update types (message, callback_query, etc).
            drop_pending_updates: Drop all pending updates.
            secret_token: Secret token for webhook header validation.

        Returns:
            True if webhook set successfully.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"url": url}

        if ip_address:
            payload["ip_address"] = ip_address

        if max_connections:
            payload["max_connections"] = max_connections

        if allowed_updates:
            payload["allowed_updates"] = allowed_updates

        if drop_pending_updates:
            payload["drop_pending_updates"] = drop_pending_updates

        if secret_token:
            payload["secret_token"] = secret_token

        if certificate:
            files = {"certificate": ("cert.pem", certificate)}
            response = await self.client.post(
                f"{self.base_url}/bot{self.bot_token}/setWebhook",
                data=payload,
                files=files,
            )
            result = await self._handle_response(response)
        else:
            result = await self.post("/setWebhook", json=payload)

        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def get_webhook_info(self) -> dict[str, Any]:
        """
        Get current webhook information.

        Returns:
            Webhook information dict.

        Raises:
            TelegramError: On API error.
        """
        return await self.get("/getWebhookInfo")

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """
        Remove webhook integration.

        Args:
            drop_pending_updates: Drop all pending updates.

        Returns:
            True if webhook deleted successfully.

        Raises:
            TelegramError: On API error.
        """
        payload = {}
        if drop_pending_updates:
            payload["drop_pending_updates"] = drop_pending_updates

        result = await self.post("/deleteWebhook", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
        url: str | None = None,
        cache_time: int = 0,
    ) -> bool:
        """
        Respond to callback query from inline button.

        Args:
            callback_query_id: Unique identifier of callback query.
            text: Notification text (0-200 characters).
            show_alert: Show as alert instead of notification.
            url: URL to open.
            cache_time: Max cache time in seconds (0-86400).

        Returns:
            True if successful.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}

        if text:
            payload["text"] = text

        if show_alert:
            payload["show_alert"] = show_alert

        if url:
            payload["url"] = url

        if cache_time:
            payload["cache_time"] = cache_time

        result = await self.post("/answerCallbackQuery", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def edit_message_text(
        self,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        text: str | None = None,
        parse_mode: ParseMode | str | None = None,
        reply_markup: InlineKeyboardMarkup | dict[str, Any] | None = None,
    ) -> Message | bool:
        """
        Edit text of message.

        Args:
            chat_id: Required if inline_message_id not provided.
            message_id: Required if inline_message_id not provided.
            inline_message_id: Required if chat_id/message_id not provided.
            text: New message text (1-4096 characters).
            parse_mode: Mode for parsing entities.
            reply_markup: New inline keyboard markup.

        Returns:
            Edited Message or True if inline message.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {}

        if chat_id is not None and message_id is not None:
            payload["chat_id"] = chat_id
            payload["message_id"] = message_id
        elif inline_message_id:
            payload["inline_message_id"] = inline_message_id
        else:
            raise ValueError("Either (chat_id + message_id) or inline_message_id required")

        if text:
            payload["text"] = text

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if reply_markup:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                payload["reply_markup"] = reply_markup.to_dict()
            else:
                payload["reply_markup"] = reply_markup

        result = await self.post("/editMessageText", json=payload)

        if inline_message_id:
            return True

        return Message(
            message_id=result.get("message_id", 0),
            date=result.get("date", 0),
            text=result.get("text"),
            raw=result,
        )

    async def delete_message(
        self,
        chat_id: int | str,
        message_id: int,
    ) -> bool:
        """
        Delete message.

        Args:
            chat_id: Unique identifier for target chat.
            message_id: Identifier of message to delete.

        Returns:
            True if successful.

        Raises:
            TelegramError: On API error.
        """
        payload = {"chat_id": chat_id, "message_id": message_id}
        result = await self.post("/deleteMessage", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def get_me(self) -> User:
        """
        Get information about the bot.

        Returns:
            User object representing the bot.

        Raises:
            TelegramError: On API error.
        """
        result = await self.get("/getMe")

        return User(
            id=result.get("id", 0),
            is_bot=result.get("is_bot", True),
            first_name=result.get("first_name", ""),
            last_name=result.get("last_name"),
            username=result.get("username"),
            raw=result,
        )

    async def set_my_commands(
        self,
        commands: list[dict[str, str]],
        scope: dict[str, Any] | None = None,
        language_code: str | None = None,
    ) -> bool:
        """
        Set list of bot commands.

        Args:
            commands: List of BotCommand objects (command + description).
            scope: Scope of commands (default: SCOPE_DEFAULT).
            language_code: Language code for commands.

        Returns:
            True if successful.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"commands": commands}

        if scope:
            payload["scope"] = scope

        if language_code:
            payload["language_code"] = language_code

        result = await self.post("/setMyCommands", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """
        Get basic info about a file.

        Args:
            file_id: File identifier.

        Returns:
            File information dict with file_path.

        Raises:
            TelegramError: On API error.
        """
        payload = {"file_id": file_id}
        return await self.post("/getFile", json=payload)

    async def get_file_url(self, file_id: str) -> str:
        """
        Get download URL for a file.

        Args:
            file_id: File identifier.

        Returns:
            Full download URL.

        Raises:
            TelegramError: On API error.
        """
        file_info = await self.get_file(file_id)
        file_path = file_info.get("file_path", "")
        return f"{self.base_url}/file/bot{self.bot_token}/{file_path}"

    async def ban_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        until_date: int | None = None,
        revoke_messages: bool = False,
    ) -> bool:
        """
        Ban user from chat.

        Args:
            chat_id: Unique identifier for target chat.
            user_id: Unique identifier of user to ban.
            until_date: Date when user will be unbanned (Unix time).
            revoke_messages: Delete all messages from user.

        Returns:
            True if successful.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"chat_id": chat_id, "user_id": user_id}

        if until_date:
            payload["until_date"] = until_date

        if revoke_messages:
            payload["revoke_messages"] = revoke_messages

        result = await self.post("/banChatMember", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def unban_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        only_if_banned: bool = False,
    ) -> bool:
        """
        Unban user from chat.

        Args:
            chat_id: Unique identifier for target chat.
            user_id: Unique identifier of user to unban.
            only_if_banned: Only unban if user was banned.

        Returns:
            True if successful.

        Raises:
            TelegramError: On API error.
        """
        payload: dict[str, Any] = {"chat_id": chat_id, "user_id": user_id}

        if only_if_banned:
            payload["only_if_banned"] = only_if_banned

        result = await self.post("/unbanChatMember", json=payload)
        return bool(result.get("ok", False) if isinstance(result, dict) else result)

    async def get_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Get information about a chat member.

        Args:
            chat_id: Unique identifier for target chat.
            user_id: Unique identifier of user.

        Returns:
            ChatMember object.

        Raises:
            TelegramError: On API error.
        """
        payload = {"chat_id": chat_id, "user_id": user_id}
        return await self.post("/getChatMember", json=payload)

    async def health_check(self) -> dict[str, Any]:
        """
        Check Telegram bot health/connectivity.

        Returns:
            Health status dict with bot info.
        """
        try:
            bot_info = await self.get_me()
            return {
                "name": "telegram",
                "healthy": True,
                "message": f"Telegram bot @{bot_info.username} is online",
                "bot_id": bot_info.id,
                "bot_name": bot_info.first_name,
            }
        except Exception as e:
            logger.error(f"[telegram] Health check failed: {e}")
            return {
                "name": "telegram",
                "healthy": False,
                "message": f"Health check failed: {e}",
            }

    def verify_webhook_token(
        self,
        secret_token: str,
        x_token_header: str,
    ) -> bool:
        """
        Verify webhook request authenticity using secret token.

        Args:
            secret_token: Secret token set in set_webhook().
            x_token_header: X-Telegram-Bot-Api-Secret-Token header value.

        Returns:
            True if token matches, False otherwise.
        """
        return hmac.compare_digest(secret_token, x_token_header)

    async def call_api(
        self,
        method_name: str,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Call any Telegram Bot API method directly.

        This method is future-proof - it allows calling any existing or future
        Telegram Bot API endpoint without needing to add new methods to the client.

        Args:
            method_name: The Telegram Bot API method name (e.g., "getMe", "sendMessage").
            params: Optional parameters for the API call.
            files: Optional files to upload (for media methods).

        Returns:
            The API response data (the 'result' field from Telegram's response).

        Raises:
            TelegramError: On API error.
            TelegramRateLimitError: On rate limit.

        Example:
            # Call any current or future endpoint
            result = await client.call_api("getMe")
            result = await client.call_api("sendMessage", {"chat_id": 123, "text": "Hi"})

            # Future endpoint example (hypothetical)
            result = await client.call_api("createForumTopic", {"chat_id": 123, "name": "Topic"})
        """
        endpoint = f"/{method_name}"
        request_params: dict[str, Any] = {}

        if params:
            request_params["json"] = params

        if files:
            # For file uploads, use multipart form
            request_params["files"] = files
            if params:
                request_params["data"] = params
                del request_params["json"]

        return await self._request_with_retry("POST", endpoint, **request_params)

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await super().close()
        logger.debug("[telegram] Client closed")
