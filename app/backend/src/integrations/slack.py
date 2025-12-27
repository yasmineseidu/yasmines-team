"""
Slack integration client stub.

Provides basic Slack messaging functionality for notifications.
This is a minimal implementation to support Campaign Setup notifications.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SlackError(Exception):
    """Exception raised for Slack API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SlackClient:
    """Async client for Slack API.

    Provides basic messaging functionality for campaign notifications.

    Example:
        >>> client = SlackClient(token=os.environ["SLACK_BOT_TOKEN"])
        >>> result = await client.send_message("#campaigns", "Hello!")
        >>> await client.close()
    """

    def __init__(self, token: str, timeout: float = 30.0) -> None:
        """Initialize Slack client.

        Args:
            token: Slack Bot Token.
            timeout: Request timeout in seconds.
        """
        self.token = token
        self._http_client = httpx.AsyncClient(
            base_url="https://slack.com/api",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
        logger.info("Initialized SlackClient")

    async def send_message(
        self,
        channel: str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message to a Slack channel.

        Args:
            channel: Channel name or ID (e.g., "#campaigns" or "C1234567890").  # pragma: allowlist secret
            text: Message text (supports Slack markdown).
            **kwargs: Additional message parameters.

        Returns:
            Slack API response with message timestamp.

        Raises:
            SlackError: If API request fails.
        """
        payload = {
            "channel": channel,
            "text": text,
            **kwargs,
        }

        try:
            response = await self._http_client.post(
                "/chat.postMessage",
                json=payload,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            if not data.get("ok"):
                error = data.get("error", "Unknown error")
                logger.error(f"Slack API error: {error}")
                raise SlackError(error)

            logger.info(f"Sent message to {channel}, ts={data.get('ts')}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Slack HTTP error: {e.response.status_code}")
            raise SlackError(str(e), status_code=e.response.status_code) from e
        except httpx.TimeoutException as e:
            logger.error(f"Slack request timeout: {e}")
            raise SlackError("Request timeout") from e
        except Exception as e:
            logger.error(f"Unexpected Slack error: {e}")
            raise SlackError(str(e)) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
        logger.debug("Closed SlackClient")
