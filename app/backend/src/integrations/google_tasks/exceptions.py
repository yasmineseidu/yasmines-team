"""Custom exceptions for Google Tasks API integration."""


class GoogleTasksError(Exception):
    """Base exception for Google Tasks API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class GoogleTasksConfigError(GoogleTasksError):
    """Raised when configuration is invalid or missing."""

    pass


class GoogleTasksAuthError(GoogleTasksError):
    """Raised when authentication fails."""

    pass


class GoogleTasksAPIError(GoogleTasksError):
    """Raised when Google Tasks API returns an error."""

    pass


class GoogleTasksNotFoundError(GoogleTasksError):
    """Raised when requested task or task list is not found."""

    def __init__(self, message: str = "Task or task list not found", **kwargs: int | None) -> None:
        super().__init__(message, **kwargs)


class GoogleTasksValidationError(GoogleTasksError):
    """Raised when task data validation fails."""

    pass


class GoogleTasksRateLimitError(GoogleTasksError):
    """Raised when API rate limit is exceeded."""

    pass


class GoogleTasksQuotaExceeded(GoogleTasksError):
    """Raised when daily quota is exceeded."""

    pass
