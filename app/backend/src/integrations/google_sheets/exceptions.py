"""Custom exceptions for Google Sheets API integration."""

from typing import Any

from src.integrations.base import IntegrationError


class GoogleSheetsError(IntegrationError):
    """Base exception for Google Sheets API errors."""

    pass


class GoogleSheetsAuthError(GoogleSheetsError):
    """Raised when Google Sheets authentication fails."""

    def __init__(
        self,
        message: str = "Google Sheets authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class GoogleSheetsAPIError(GoogleSheetsError):
    """Raised when Google Sheets API call fails."""

    def __init__(
        self,
        message: str = "Google Sheets API error",
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)


class GoogleSheetsConfigError(GoogleSheetsError):
    """Raised when Google Sheets configuration/credentials are invalid."""

    def __init__(
        self,
        message: str = "Google Sheets configuration error",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class GoogleSheetsNotFoundError(GoogleSheetsError):
    """Raised when a spreadsheet or sheet is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str = "resource",
        resource_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        if resource_id:
            message = f"{resource_type.capitalize()} not found: {resource_id}"
        super().__init__(message, status_code=404, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class GoogleSheetsValidationError(GoogleSheetsError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        if field:
            message = f"Validation error for field '{field}': {message}"
        super().__init__(message, status_code=400, **kwargs)
        self.field = field


class GoogleSheetsRateLimitError(GoogleSheetsError):
    """Raised when Google Sheets API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Sheets API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class GoogleSheetsQuotaExceeded(GoogleSheetsError):
    """Raised when quota exceeded or project limits reached."""

    def __init__(
        self,
        message: str = "Google Sheets quota exceeded",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)


class GoogleSheetsPermissionError(GoogleSheetsError):
    """Raised when user doesn't have permission to access a resource."""

    def __init__(
        self,
        message: str = "Permission denied",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)
