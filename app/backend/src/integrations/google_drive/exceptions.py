"""Custom exceptions for Google Drive API integration."""

from typing import Any

from src.integrations.base import IntegrationError


class GoogleDriveError(IntegrationError):
    """Base exception for Google Drive API errors."""

    pass


class GoogleDriveAuthError(GoogleDriveError):
    """Raised when Google Drive authentication fails."""

    def __init__(
        self,
        message: str = "Google Drive authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class GoogleDriveRateLimitError(GoogleDriveError):
    """Raised when Google Drive API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Drive API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class GoogleDriveQuotaExceeded(GoogleDriveError):
    """Raised when quota exceeded or project limits reached."""

    def __init__(
        self,
        message: str = "Google Drive quota exceeded",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)
