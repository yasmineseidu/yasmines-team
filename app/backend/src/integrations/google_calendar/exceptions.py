"""Custom exceptions for Google Calendar API integration."""

from typing import Any

from src.integrations.base import IntegrationError


class GoogleCalendarError(IntegrationError):
    """Base exception for Google Calendar API errors."""

    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Raised when Google Calendar authentication fails."""

    def __init__(
        self,
        message: str = "Google Calendar authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class GoogleCalendarAPIError(GoogleCalendarError):
    """Raised when Google Calendar API call fails."""

    def __init__(
        self,
        message: str = "Google Calendar API error",
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)


class GoogleCalendarConfigError(GoogleCalendarError):
    """Raised when Google Calendar configuration/credentials are invalid."""

    def __init__(
        self,
        message: str = "Google Calendar configuration error",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class GoogleCalendarNotFoundError(GoogleCalendarError):
    """Raised when a calendar or event is not found."""

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


class GoogleCalendarValidationError(GoogleCalendarError):
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


class GoogleCalendarRateLimitError(GoogleCalendarError):
    """Raised when Google Calendar API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Calendar API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class GoogleCalendarQuotaExceeded(GoogleCalendarError):
    """Raised when quota exceeded or project limits reached."""

    def __init__(
        self,
        message: str = "Google Calendar quota exceeded",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)
