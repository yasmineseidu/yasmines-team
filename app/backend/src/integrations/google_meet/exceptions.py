"""Custom exceptions for Google Meet API integration."""

from typing import Any

from src.integrations.base import IntegrationError


class GoogleMeetError(IntegrationError):
    """Base exception for Google Meet API errors."""

    pass


class GoogleMeetAuthError(GoogleMeetError):
    """Raised when Google Meet authentication fails."""

    def __init__(
        self,
        message: str = "Google Meet authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class GoogleMeetAPIError(GoogleMeetError):
    """Raised when Google Meet API call fails."""

    def __init__(
        self,
        message: str = "Google Meet API error",
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)


class GoogleMeetConfigError(GoogleMeetError):
    """Raised when Google Meet configuration/credentials are invalid."""

    def __init__(
        self,
        message: str = "Google Meet configuration error",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class GoogleMeetNotFoundError(GoogleMeetError):
    """Raised when a space or conference record is not found."""

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


class GoogleMeetValidationError(GoogleMeetError):
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


class GoogleMeetRateLimitError(GoogleMeetError):
    """Raised when Google Meet API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Meet API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class GoogleMeetQuotaExceeded(GoogleMeetError):
    """Raised when quota exceeded or project limits reached."""

    def __init__(
        self,
        message: str = "Google Meet quota exceeded",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)


class GoogleMeetPermissionError(GoogleMeetError):
    """Raised when user doesn't have permission to access a resource."""

    def __init__(
        self,
        message: str = "Permission denied",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)
