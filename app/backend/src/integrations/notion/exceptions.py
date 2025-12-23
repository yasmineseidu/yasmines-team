"""Custom exceptions for Notion API integration."""

from typing import Any


class NotionError(Exception):
    """Base exception for all Notion integration errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Notion error.

        Args:
            message: Error message.
            status_code: HTTP status code if applicable.
            response_data: API response data if available.
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation."""
        if self.status_code:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class NotionAuthError(NotionError):
    """Raised when Notion API authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs: Any,
    ) -> None:
        """Initialize auth error."""
        super().__init__(message, status_code=401, **kwargs)


class NotionAPIError(NotionError):
    """Raised for general Notion API errors."""

    pass


class NotionRateLimitError(NotionError):
    """Raised when Notion API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
            **kwargs: Additional arguments for parent class.
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class NotionNotFoundError(NotionError):
    """Raised when requested Notion resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        **kwargs: Any,
    ) -> None:
        """Initialize not found error."""
        super().__init__(message, status_code=404, **kwargs)


class NotionValidationError(NotionError):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        **kwargs: Any,
    ) -> None:
        """Initialize validation error."""
        super().__init__(message, status_code=400, **kwargs)
