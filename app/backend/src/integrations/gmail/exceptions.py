"""Gmail API custom exceptions.

Extends base integration exceptions with Gmail-specific error types.
"""

from src.integrations.base import IntegrationError


class GmailError(IntegrationError):
    """Base exception for Gmail API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize GmailError.

        Args:
            message: Error message describing what went wrong.
            status_code: Optional HTTP status code from Gmail API.
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GmailAuthError(GmailError):
    """Authentication/authorization error (401).

    Raised when credentials are invalid, expired, or insufficient permissions.
    """

    def __init__(self, message: str) -> None:
        """Initialize GmailAuthError.

        Args:
            message: Error description.
        """
        super().__init__(message, status_code=401)


class GmailRateLimitError(GmailError):
    """Rate limit exceeded error (429).

    Raised when Gmail API rate limits are exceeded. Includes optional
    Retry-After header value for intelligent backoff.
    """

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Initialize GmailRateLimitError.

        Args:
            message: Error description.
            retry_after: Seconds to wait before retrying (from Retry-After header).
        """
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class GmailQuotaExceeded(GmailError):
    """Daily/usage quota exceeded error (403).

    Raised when user has exceeded daily limits or project quotas.
    """

    def __init__(self, message: str) -> None:
        """Initialize GmailQuotaExceeded.

        Args:
            message: Error description including quota details.
        """
        super().__init__(message, status_code=403)


class GmailNotFoundError(GmailError):
    """Resource not found error (404).

    Raised when message, draft, label, or thread ID doesn't exist.
    """

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize GmailNotFoundError.

        Args:
            resource_type: Type of resource (message, draft, label, thread).
            resource_id: ID of the resource that wasn't found.
        """
        message = f"{resource_type} '{resource_id}' not found"
        super().__init__(message, status_code=404)
