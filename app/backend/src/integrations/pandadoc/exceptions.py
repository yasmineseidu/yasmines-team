"""Custom exceptions for PandaDoc API client."""

from typing import Any


class PandaDocError(Exception):
    """Base exception for PandaDoc errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize PandaDocError.

        Args:
            message: Error message.
            status_code: HTTP status code (if applicable).
            response_data: Response data from API (if applicable).
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


class PandaDocConfigError(PandaDocError):
    """Raised when PandaDoc client configuration is invalid."""

    pass


class PandaDocAuthError(PandaDocError):
    """Raised when authentication fails (401, 403)."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        """Initialize PandaDocAuthError.

        Args:
            message: Error message.
            **kwargs: Additional arguments for parent class.
        """
        kwargs.setdefault("status_code", 401)
        super().__init__(message, **kwargs)


class PandaDocAPIError(PandaDocError):
    """Raised when API request fails."""

    pass


class PandaDocNotFoundError(PandaDocError):
    """Raised when requested resource is not found (404)."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        """Initialize PandaDocNotFoundError.

        Args:
            message: Error message.
            **kwargs: Additional arguments for parent class.
        """
        kwargs.setdefault("status_code", 404)
        super().__init__(message, **kwargs)


class PandaDocRateLimitError(PandaDocError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize PandaDocRateLimitError.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying (from Retry-After header).
            **kwargs: Additional arguments for parent class.
        """
        kwargs.setdefault("status_code", 429)
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
