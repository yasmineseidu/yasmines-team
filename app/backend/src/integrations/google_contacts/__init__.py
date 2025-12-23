"""Google Contacts API integration (People API v1).

Provides async client for managing contacts through Google Contacts API
with domain-wide delegation support and comprehensive error handling.
"""

from src.integrations.google_contacts.client import GoogleContactsClient
from src.integrations.google_contacts.exceptions import (
    GoogleContactsAPIError,
    GoogleContactsAuthError,
    GoogleContactsConfigError,
    GoogleContactsError,
    GoogleContactsNotFoundError,
    GoogleContactsPermissionError,
    GoogleContactsQuotaExceeded,
    GoogleContactsRateLimitError,
    GoogleContactsValidationError,
)
from src.integrations.google_contacts.models import (
    Contact,
    ContactCreateRequest,
    ContactGroup,
    ContactGroupsListResponse,
    ContactsListResponse,
    ContactUpdateRequest,
    EmailAddress,
    Name,
    Organization,
    PhoneNumber,
    PostalAddress,
)

__all__ = [
    "GoogleContactsClient",
    "GoogleContactsError",
    "GoogleContactsAPIError",
    "GoogleContactsAuthError",
    "GoogleContactsConfigError",
    "GoogleContactsNotFoundError",
    "GoogleContactsPermissionError",
    "GoogleContactsQuotaExceeded",
    "GoogleContactsRateLimitError",
    "GoogleContactsValidationError",
    "Contact",
    "ContactGroup",
    "ContactCreateRequest",
    "ContactUpdateRequest",
    "ContactsListResponse",
    "ContactGroupsListResponse",
    "Name",
    "EmailAddress",
    "PhoneNumber",
    "PostalAddress",
    "Organization",
]
