"""
Slack integration client.

Provides Slack messaging functionality for notifications with
exponential backoff retry logic and rate limiting support.

API Documentation: https://api.slack.com/methods
Rate Limits: https://api.slack.com/docs/rate-limits
- Tier 1 (chat.postMessage): ~1 request per second per channel

Authentication:
- Bearer token via Bot Token from Slack App

Example:
    >>> from src.integrations.slack import SlackClient
    >>> client = SlackClient(token="xoxb-...")
    >>> result = await client.send_message("#campaigns", "Hello!")
    >>> await client.close()
"""

import logging
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class SlackError(IntegrationError):
    """Exception raised for Slack API errors."""

    pass


class SlackClient(BaseIntegrationClient):
    """
    Async client for Slack API with retry logic.

    Provides messaging functionality for campaign notifications with
    exponential backoff, jitter, and rate limit handling.

    Inherits from BaseIntegrationClient for:
    - Exponential backoff retry (base delay * 2^attempt)
    - Jitter to prevent thundering herd
    - Retry on 5xx, timeouts, and rate limits
    - Connection pooling

    Attributes:
        BASE_URL: Slack API base URL.

    Note:
        - Rate limit: ~1 request per second per channel (Tier 1)
        - Bearer token authentication via Bot Token
    """

    BASE_URL = "https://slack.com/api"

    def __init__(
        self,
        token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Slack client.

        Args:
            token: Slack Bot Token (xoxb-...).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="slack",
            base_url=self.BASE_URL,
            api_key=token,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client")

    async def send_message(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a message to a Slack channel.

        Args:
            channel: Channel name or ID (e.g., "#campaigns" or "C1234567890").  # pragma: allowlist secret
            text: Message text (supports Slack markdown).
            **kwargs: Additional message parameters (blocks, attachments, etc.).

        Returns:
            Slack API response with message timestamp.

        Raises:
            SlackError: If API request fails after retries.
        """
        payload = {
            "channel": channel,
            "text": text,
            **kwargs,
        }

        try:
            response = await self.post("/chat.postMessage", json=payload)

            # Slack API returns ok: false for errors with 200 status
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                logger.error(
                    f"[{self.name}] API error: {error}",
                    extra={"channel": channel, "error": error},
                )
                raise SlackError(
                    message=f"Slack API error: {error}",
                    response_data=response,
                )

            logger.info(
                f"[{self.name}] Sent message to {channel}",
                extra={"channel": channel, "ts": response.get("ts")},
            )
            return response

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] send_message failed: {e}",
                extra={"channel": channel},
            )
            raise SlackError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def send_block_message(
        self,
        channel: str,
        blocks: list[dict[str, Any]],
        text: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a rich Block Kit message to a Slack channel.

        Args:
            channel: Channel name or ID.
            blocks: Block Kit blocks defining the message structure.
            text: Fallback text for notifications (recommended).
            **kwargs: Additional message parameters.

        Returns:
            Slack API response with message timestamp.

        Raises:
            SlackError: If API request fails.
        """
        return await self.send_message(
            channel=channel,
            text=text or "New message",
            blocks=blocks,
            **kwargs,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Slack API connectivity.

        Returns:
            Health check status with API connectivity info.
        """
        try:
            # Use auth.test which is a simple, rate-limit-friendly endpoint
            response = await self.get("/auth.test")

            if response.get("ok"):
                return {
                    "name": self.name,
                    "healthy": True,
                    "team": response.get("team"),
                    "user": response.get("user"),
                }
            return {
                "name": self.name,
                "healthy": False,
                "error": response.get("error", "Unknown error"),
            }

        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
            }
