"""
Telegram webhook API routes.

Handles incoming Telegram webhook updates for the approval workflow.
Verifies webhook authenticity using secret token.

Example:
    >>> # Register routes with FastAPI app
    >>> from src.api.routes.telegram import router
    >>> app.include_router(router, prefix="/api/telegram")
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import BaseModel

from src.integrations.approval_handler import ApprovalBotHandler
from src.integrations.telegram import (
    Message,
    TelegramClient,
    TelegramError,
    Update,
)
from src.services.approval_service import ApprovalService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])

# Global instances (initialized on startup)
_telegram_client: TelegramClient | None = None
_approval_service: ApprovalService | None = None
_approval_handler: ApprovalBotHandler | None = None


class WebhookUpdate(BaseModel):
    """Telegram webhook update model."""

    update_id: int
    message: dict[str, Any] | None = None
    edited_message: dict[str, Any] | None = None
    channel_post: dict[str, Any] | None = None
    edited_channel_post: dict[str, Any] | None = None
    callback_query: dict[str, Any] | None = None

    class Config:
        """Pydantic config."""

        extra = "allow"


def get_telegram_client() -> TelegramClient:
    """
    Get or create TelegramClient instance.

    Returns:
        Configured TelegramClient.

    Raises:
        HTTPException: If bot token not configured.
    """
    global _telegram_client

    if _telegram_client is None:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TELEGRAM_BOT_TOKEN not configured",
            )
        _telegram_client = TelegramClient(bot_token=bot_token)

    return _telegram_client


def get_approval_service() -> ApprovalService:
    """
    Get or create ApprovalService instance.

    Returns:
        Configured ApprovalService.
    """
    global _approval_service

    if _approval_service is None:
        telegram_client = get_telegram_client()
        edit_form_base_url = os.getenv(
            "APPROVAL_EDIT_FORM_URL",
            "https://app.example.com/approvals",
        )
        _approval_service = ApprovalService(
            telegram_client=telegram_client,
            edit_form_base_url=edit_form_base_url,
        )

    return _approval_service


def get_approval_handler() -> ApprovalBotHandler:
    """
    Get or create ApprovalBotHandler instance.

    Returns:
        Configured ApprovalBotHandler.
    """
    global _approval_handler

    if _approval_handler is None:
        telegram_client = get_telegram_client()
        approval_service = get_approval_service()
        _approval_handler = ApprovalBotHandler(
            telegram_client=telegram_client,
            approval_service=approval_service,
        )

    return _approval_handler


async def process_webhook_update(update_data: dict[str, Any]) -> None:
    """
    Process a webhook update in the background.

    Args:
        update_data: Raw update data from Telegram.
    """
    try:
        handler = get_approval_handler()

        # Parse update
        update = Update(
            update_id=update_data.get("update_id", 0),
            callback_query=update_data.get("callback_query"),
            raw=update_data,
        )

        # Parse message if present
        if "message" in update_data:
            msg = update_data["message"]
            update.message = Message(
                message_id=msg.get("message_id", 0),
                date=msg.get("date", 0),
                text=msg.get("text"),
                raw=msg,
            )
            if "chat" in msg:
                update.message.chat = msg["chat"]
            if "from" in msg:
                update.message.from_user = msg["from"]

        # Process update
        await handler.process_update(update)

    except Exception as e:
        logger.error(f"Failed to process webhook update: {e}", exc_info=True)


@router.post("/webhook")  # type: ignore[misc]
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, str]:
    """
    Handle incoming Telegram webhook updates.

    Validates the secret token header and processes the update
    in a background task for fast response.

    Args:
        request: FastAPI request object.
        background_tasks: FastAPI background tasks.
        x_telegram_bot_api_secret_token: Secret token header from Telegram.

    Returns:
        Success acknowledgment.

    Raises:
        HTTPException: If validation fails.
    """
    # Verify webhook secret
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if webhook_secret and x_telegram_bot_api_secret_token:
        telegram_client = get_telegram_client()
        if not telegram_client.verify_webhook_token(
            webhook_secret,
            x_telegram_bot_api_secret_token,
        ):
            logger.warning("Invalid webhook secret token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token",
            )

    # Parse request body
    try:
        update_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook body: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from None

    logger.debug(f"Received webhook update: {update_data.get('update_id')}")

    # Process in background for fast response
    background_tasks.add_task(process_webhook_update, update_data)

    return {"status": "ok"}


@router.get("/webhook/info")  # type: ignore[misc]
async def get_webhook_info() -> dict[str, Any]:
    """
    Get current webhook configuration.

    Returns:
        Webhook information from Telegram.

    Raises:
        HTTPException: If API call fails.
    """
    try:
        telegram_client = get_telegram_client()
        info = await telegram_client.get_webhook_info()
        return {"status": "ok", "webhook_info": info}
    except TelegramError as e:
        logger.error(f"Failed to get webhook info: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telegram API error: {e}",
        ) from None


@router.post("/webhook/set")  # type: ignore[misc]
async def set_webhook(
    url: str,
    secret_token: str | None = None,
    drop_pending: bool = False,
) -> dict[str, Any]:
    """
    Set Telegram webhook URL.

    Args:
        url: HTTPS URL for webhook.
        secret_token: Optional secret token for validation.
        drop_pending: Whether to drop pending updates.

    Returns:
        Success status.

    Raises:
        HTTPException: If API call fails.
    """
    try:
        telegram_client = get_telegram_client()
        success = await telegram_client.set_webhook(
            url=url,
            secret_token=secret_token,
            drop_pending_updates=drop_pending,
            allowed_updates=["message", "callback_query"],
        )
        return {"status": "ok" if success else "failed", "url": url}
    except TelegramError as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telegram API error: {e}",
        ) from None


@router.delete("/webhook")  # type: ignore[misc]
async def delete_webhook(drop_pending: bool = False) -> dict[str, Any]:
    """
    Remove Telegram webhook.

    Args:
        drop_pending: Whether to drop pending updates.

    Returns:
        Success status.

    Raises:
        HTTPException: If API call fails.
    """
    try:
        telegram_client = get_telegram_client()
        success = await telegram_client.delete_webhook(drop_pending_updates=drop_pending)
        return {"status": "ok" if success else "failed"}
    except TelegramError as e:
        logger.error(f"Failed to delete webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telegram API error: {e}",
        ) from None


@router.get("/health")  # type: ignore[misc]
async def telegram_health() -> dict[str, Any]:
    """
    Check Telegram bot health.

    Returns:
        Health status.
    """
    try:
        telegram_client = get_telegram_client()
        health = await telegram_client.health_check()
        return health
    except Exception as e:
        return {
            "name": "telegram",
            "healthy": False,
            "message": str(e),
        }
