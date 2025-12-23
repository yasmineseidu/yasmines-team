"""Cal.com API custom exceptions."""

from typing import Any


class CalComError(Exception):
    """Base exception for all Cal.com errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Cal.com error.

        Args:
            message: Error message describing what went wrong.
            status_code: HTTP status code if applicable.
            response_data: The API response body for debugging.
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.status_code:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class CalComAuthError(CalComError):
    """Raised when authentication to Cal.com fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        """Initialize auth error."""
        super().__init__(message, status_code=401, **kwargs)


class CalComAPIError(CalComError):
    """Raised when Cal.com API request fails."""

    pass


class CalComConfigError(CalComError):
    """Raised when Cal.com client configuration is invalid."""

    def __init__(self, message: str = "Configuration error", **kwargs: Any) -> None:
        """Initialize config error."""
        super().__init__(message, **kwargs)


class CalComNotFoundError(CalComError):
    """Raised when a Cal.com resource is not found."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        """Initialize not found error."""
        super().__init__(message, status_code=404, **kwargs)


class CalComValidationError(CalComError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation error", **kwargs: Any) -> None:
        """Initialize validation error."""
        super().__init__(message, **kwargs)


class CalComRateLimitError(CalComError):
    """Raised when Cal.com API rate limit is exceeded."""

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
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after
