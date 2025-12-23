"""Google Contacts API exceptions.

Defines custom exceptions for the Google Contacts (People API) integration
with proper error hierarchy and context information.
"""


class GoogleContactsError(Exception):
    """Base exception for Google Contacts API errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class GoogleContactsConfigError(GoogleContactsError):
    """Raised when client configuration is invalid."""

    pass


class GoogleContactsAuthError(GoogleContactsError):
    """Raised when authentication fails."""

    pass


class GoogleContactsAPIError(GoogleContactsError):
    """Raised when API request fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GoogleContactsNotFoundError(GoogleContactsAPIError):
    """Raised when resource is not found (404)."""

    pass


class GoogleContactsValidationError(GoogleContactsError):
    """Raised when input validation fails."""

    pass


class GoogleContactsRateLimitError(GoogleContactsAPIError):
    """Raised when rate limit is exceeded (429)."""

    pass


class GoogleContactsQuotaExceeded(GoogleContactsAPIError):
    """Raised when quota is exceeded (403)."""

    pass


class GoogleContactsPermissionError(GoogleContactsAPIError):
    """Raised when permission is denied (403)."""

    pass
