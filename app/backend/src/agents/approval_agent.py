"""
Approval workflow orchestrator agent.

Coordinates the complete approval workflow including sending requests,
handling callbacks, and managing the approval lifecycle.

This agent can be used with the Claude Agent SDK for AI-assisted
approval workflows.

Example:
    >>> from src.agents.approval_agent import ApprovalAgent
    >>> agent = ApprovalAgent()
    >>> await agent.initialize()
    >>> request_id = await agent.send_approval(
    ...     title="Q4 Budget",
    ...     content="Marketing budget request",
    ...     requester_id=123,
    ...     approver_id=456,
    ...     chat_id=789,
    ... )
"""

import asyncio
import contextlib
import logging
import os
from typing import Any

from src.integrations.approval_handler import ApprovalBotHandler
from src.integrations.telegram import TelegramClient, TelegramError, Update
from src.services.approval_service import ApprovalService

logger = logging.getLogger(__name__)


class ApprovalAgent:
    """
    Agent that orchestrates the approval workflow.

    Manages the lifecycle of approval requests through Telegram,
    including sending, receiving callbacks, and status updates.

    Attributes:
        name: Agent identifier.
        description: Agent description.
        telegram_client: TelegramClient instance.
        approval_service: ApprovalService instance.
        approval_handler: ApprovalBotHandler instance.
        polling_active: Whether polling is currently active.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        edit_form_base_url: str | None = None,
    ) -> None:
        """
        Initialize the approval agent.

        Args:
            bot_token: Telegram bot token. Uses TELEGRAM_BOT_TOKEN env var if not provided.
            edit_form_base_url: Base URL for edit forms.
        """
        self.name = "approval_agent"
        self.description = "Manages approval workflows through Telegram"

        self._bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._edit_form_base_url: str = (
            edit_form_base_url
            or os.getenv(
                "APPROVAL_EDIT_FORM_URL",
                "https://app.example.com/approvals",
            )
            or "https://app.example.com/approvals"
        )

        self.telegram_client: TelegramClient | None = None
        self.approval_service: ApprovalService | None = None
        self.approval_handler: ApprovalBotHandler | None = None

        self.polling_active = False
        self._polling_task: asyncio.Task[None] | None = None
        self._last_update_id = 0

        logger.info(f"Created {self.name}")

    async def initialize(self) -> None:
        """
        Initialize the agent's dependencies.

        Creates TelegramClient, ApprovalService, and ApprovalBotHandler.

        Raises:
            ValueError: If bot token is not configured.
        """
        if not self._bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not configured. "
                "Set environment variable or pass bot_token to constructor."
            )

        self.telegram_client = TelegramClient(bot_token=self._bot_token)

        self.approval_service = ApprovalService(
            telegram_client=self.telegram_client,
            edit_form_base_url=self._edit_form_base_url,
        )

        self.approval_handler = ApprovalBotHandler(
            telegram_client=self.telegram_client,
            approval_service=self.approval_service,
        )

        # Verify connection
        try:
            bot_info = await self.telegram_client.get_me()
            logger.info(f"Approval agent connected as @{bot_info.username}")
        except TelegramError as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            raise

    async def send_approval(
        self,
        title: str,
        content: str,
        requester_id: int,
        approver_id: int,
        chat_id: int,
        content_type: str = "custom",
        data: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a new approval request.

        Args:
            title: Request title.
            content: Request content/description.
            requester_id: User ID of requester.
            approver_id: User ID of approver.
            chat_id: Telegram chat ID to send to.
            content_type: Type of content (budget, document, content, custom).
            data: Additional data for the request.

        Returns:
            Request ID (UUID string).

        Raises:
            RuntimeError: If agent not initialized.
            ValueError: If request data is invalid.
            TelegramError: If message sending fails.
        """
        if not self.approval_service:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return await self.approval_service.send_approval_request(
            request_data={
                "title": title,
                "content": content,
                "requester_id": requester_id,
                "approver_id": approver_id,
                "telegram_chat_id": chat_id,
                "content_type": content_type,
                "data": data or {},
            }
        )

    async def send_budget_approval(
        self,
        title: str,
        amount: float,
        department: str,
        description: str,
        requester_id: int,
        approver_id: int,
        chat_id: int,
    ) -> str:
        """
        Send a budget approval request.

        Convenience method for budget-type approvals.

        Args:
            title: Budget request title.
            amount: Budget amount.
            department: Department requesting budget.
            description: Budget description.
            requester_id: User ID of requester.
            approver_id: User ID of approver.
            chat_id: Telegram chat ID to send to.

        Returns:
            Request ID (UUID string).
        """
        return await self.send_approval(
            title=title,
            content=description,
            requester_id=requester_id,
            approver_id=approver_id,
            chat_id=chat_id,
            content_type="budget",
            data={"amount": amount, "department": department},
        )

    async def send_document_approval(
        self,
        title: str,
        description: str,
        file_url: str,
        document_type: str,
        requester_id: int,
        approver_id: int,
        chat_id: int,
    ) -> str:
        """
        Send a document approval request.

        Convenience method for document-type approvals.

        Args:
            title: Document title.
            description: Document description.
            file_url: URL to the document.
            document_type: Type of document (contract, proposal, etc.).
            requester_id: User ID of requester.
            approver_id: User ID of approver.
            chat_id: Telegram chat ID to send to.

        Returns:
            Request ID (UUID string).
        """
        return await self.send_approval(
            title=title,
            content=description,
            requester_id=requester_id,
            approver_id=approver_id,
            chat_id=chat_id,
            content_type="document",
            data={"file_url": file_url, "document_type": document_type},
        )

    async def send_content_approval(
        self,
        title: str,
        content_text: str,
        tags: list[str],
        requester_id: int,
        approver_id: int,
        chat_id: int,
    ) -> str:
        """
        Send a content approval request.

        Convenience method for content-type approvals (blog posts, etc.).

        Args:
            title: Content title.
            content_text: The content to approve.
            tags: Content tags.
            requester_id: User ID of requester.
            approver_id: User ID of approver.
            chat_id: Telegram chat ID to send to.

        Returns:
            Request ID (UUID string).
        """
        return await self.send_approval(
            title=title,
            content=content_text,
            requester_id=requester_id,
            approver_id=approver_id,
            chat_id=chat_id,
            content_type="content",
            data={"tags": tags},
        )

    async def get_request(self, request_id: str) -> dict[str, Any]:
        """
        Get approval request by ID.

        Args:
            request_id: UUID of the request.

        Returns:
            Request data dictionary.

        Raises:
            RuntimeError: If agent not initialized.
            ValueError: If request not found.
        """
        if not self.approval_service:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        request = await self.approval_service.get_approval_request(request_id)
        return request.to_dict()

    async def list_pending(self, approver_id: int) -> list[dict[str, Any]]:
        """
        List pending approval requests for an approver.

        Args:
            approver_id: User ID of the approver.

        Returns:
            List of pending request dictionaries.

        Raises:
            RuntimeError: If agent not initialized.
        """
        if not self.approval_service:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        requests = await self.approval_service.list_pending_approvals(approver_id)
        return [r.to_dict() for r in requests]

    async def process_update(self, update: Update) -> bool:
        """
        Process a Telegram update.

        Delegates to the approval handler.

        Args:
            update: Telegram Update object.

        Returns:
            True if update was processed.

        Raises:
            RuntimeError: If agent not initialized.
        """
        if not self.approval_handler:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return await self.approval_handler.process_update(update)

    async def start_polling(
        self,
        timeout: int = 30,
        allowed_updates: list[str] | None = None,
    ) -> None:
        """
        Start polling for updates.

        Runs in background, processing updates as they arrive.

        Args:
            timeout: Long polling timeout in seconds.
            allowed_updates: List of update types to receive.

        Raises:
            RuntimeError: If agent not initialized.
        """
        if not self.telegram_client or not self.approval_handler:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        if self.polling_active:
            logger.warning("Polling already active")
            return

        self.polling_active = True
        allowed = allowed_updates or ["message", "callback_query"]

        logger.info("Starting approval agent polling...")

        self._polling_task = asyncio.create_task(
            self._polling_loop(timeout=timeout, allowed_updates=allowed)
        )

    async def _polling_loop(
        self,
        timeout: int,
        allowed_updates: list[str],
    ) -> None:
        """
        Internal polling loop.

        Args:
            timeout: Polling timeout.
            allowed_updates: Update types to receive.
        """
        backoff = 1.0
        max_backoff = 30.0

        while self.polling_active:
            try:
                if not self.telegram_client:
                    break

                updates = await self.telegram_client.get_updates(
                    offset=self._last_update_id + 1 if self._last_update_id else None,
                    timeout=timeout,
                    allowed_updates=allowed_updates,
                )

                for update in updates:
                    self._last_update_id = max(self._last_update_id, update.update_id)
                    await self.process_update(update)

                # Reset backoff on success
                backoff = 1.0

            except TelegramError as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break

            except Exception as e:
                logger.error(f"Unexpected polling error: {e}", exc_info=True)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop_polling(self) -> None:
        """Stop polling for updates."""
        self.polling_active = False

        if self._polling_task:
            self._polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._polling_task
            self._polling_task = None

        logger.info("Approval agent polling stopped")

    async def health_check(self) -> dict[str, Any]:
        """
        Check agent health.

        Returns:
            Health status dictionary.
        """
        status: dict[str, Any] = {
            "name": self.name,
            "healthy": False,
            "message": "Not initialized",
        }

        if self.telegram_client:
            try:
                telegram_health = await self.telegram_client.health_check()
                status["healthy"] = telegram_health.get("healthy", False)
                status["message"] = telegram_health.get("message", "Unknown")
                status["polling_active"] = self.polling_active
            except Exception as e:
                status["message"] = str(e)

        return status

    async def close(self) -> None:
        """Close the agent and release resources."""
        await self.stop_polling()

        if self.approval_service:
            await self.approval_service.close()

        self.telegram_client = None
        self.approval_service = None
        self.approval_handler = None

        logger.info(f"{self.name} closed")

    async def __aenter__(self) -> "ApprovalAgent":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
