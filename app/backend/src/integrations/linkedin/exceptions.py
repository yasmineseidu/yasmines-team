"""Custom exceptions for LinkedIn API integration."""

from typing import Any

from src.integrations.base import IntegrationError


class LinkedInError(IntegrationError):
    """Base exception for LinkedIn API errors."""

    pass


class LinkedInAuthError(LinkedInError):
    """Raised when LinkedIn OAuth2 authentication fails."""

    def __init__(
        self,
        message: str = "LinkedIn authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class LinkedInRateLimitError(LinkedInError):
    """Raised when LinkedIn API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "LinkedIn API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class LinkedInForbiddenError(LinkedInError):
    """Raised when access to LinkedIn resource is forbidden."""

    def __init__(
        self,
        message: str = "LinkedIn access forbidden - insufficient permissions",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)


class LinkedInNotFoundError(LinkedInError):
    """Raised when LinkedIn resource is not found."""

    def __init__(
        self,
        message: str = "LinkedIn resource not found",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=404, **kwargs)


class LinkedInValidationError(LinkedInError):
    """Raised when LinkedIn request validation fails."""

    def __init__(
        self,
        message: str = "LinkedIn request validation failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=400, **kwargs)
