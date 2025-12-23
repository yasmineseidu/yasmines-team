"""Google Contacts API client (People API v1) integration.

Provides async access to Google Contacts REST API including:
- OAuth2 service account authentication with domain-wide delegation
- Contact CRUD operations (create, read, update, delete)
- Contact listing and searching
- Contact group management
- Comprehensive error handling and retry logic with exponential backoff

Rate Limits:
- Per user quotas
- 429 = Rate limited (retry with backoff)
- 403 = Quota exceeded or permission denied

Example:
    >>> from src.integrations.google_contacts.client import GoogleContactsClient
    >>> client = GoogleContactsClient(credentials_json={...})
    >>> await client.authenticate()
    >>> contact = await client.create_contact(given_name="John", family_name="Doe")
    >>> contacts = await client.list_contacts()
"""

import asyncio
import json
import logging
import os
import random
from typing import Any, cast

import httpx

from src.integrations.google_contacts.exceptions import (
    GoogleContactsAPIError,
    GoogleContactsAuthError,
    GoogleContactsConfigError,
    GoogleContactsNotFoundError,
    GoogleContactsPermissionError,
    GoogleContactsQuotaExceeded,
    GoogleContactsRateLimitError,
    GoogleContactsValidationError,
)
from src.integrations.google_contacts.models import (
    Contact,
    ContactGroup,
    ContactGroupsListResponse,
    ContactsListResponse,
)

logger = logging.getLogger(__name__)


class GoogleContactsClient:
    """Async client for Google Contacts API (People API v1).

    Supports contact CRUD operations, listing, searching, and group management
    with comprehensive error handling and exponential backoff retry logic.

    Attributes:
        credentials_json: OAuth2 service account credentials
        access_token: Current OAuth2 access token
        scopes: OAuth2 scopes for Contacts access
        delegated_user: Email address for domain-wide delegation
    """

    # Google People API endpoints
    PEOPLE_API_BASE = "https://people.googleapis.com/v1"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # OAuth2 scopes
    # For domain-wide delegation, use single broad scope
    DELEGATION_SCOPE = "https://www.googleapis.com/auth/contacts"

    # Default scopes when not using delegation
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/contacts",
        "https://www.googleapis.com/auth/contacts.readonly",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        credentials_path: str | None = None,
        access_token: str | None = None,
        delegated_user: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize Google Contacts client.

        Args:
            credentials_json: OAuth2 service account credentials as dict
            credentials_str: OAuth2 service account credentials as JSON string
            credentials_path: Path to service account credentials JSON file
            access_token: Pre-obtained OAuth2 access token (optional)
            delegated_user: Email of user to impersonate (domain-wide delegation)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)

        Raises:
            GoogleContactsConfigError: If credentials are invalid or missing
        """
        # Load credentials from various sources
        if credentials_str and not credentials_json:
            try:
                credentials_json = json.loads(credentials_str)
            except json.JSONDecodeError as e:
                raise GoogleContactsConfigError(f"Invalid JSON in credentials string: {e}") from e

        if credentials_path and not credentials_json:
            credentials_json = self._load_credentials_from_path(credentials_path)

        if not credentials_json and not access_token:
            # Try to load from environment variable
            env_path = os.getenv("GOOGLE_CONTACTS_CREDENTIALS_JSON")
            if env_path:
                credentials_json = self._load_credentials_from_path(env_path)
            else:
                raise GoogleContactsConfigError(
                    "Credentials required. Provide credentials_json, credentials_str, "
                    "credentials_path, or set GOOGLE_CONTACTS_CREDENTIALS_JSON "
                    "environment variable."
                )

        self.name = "google_contacts"
        self.base_url = self.PEOPLE_API_BASE
        self.credentials_json = credentials_json or {}
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

        # Set scopes based on delegation
        if delegated_user:
            self.scopes = [self.DELEGATION_SCOPE]
        else:
            self.scopes = self.DEFAULT_SCOPES

        # Validate credentials structure if provided
        if self.credentials_json:
            self._validate_credentials(self.credentials_json)

        logger.info("Initialized Google Contacts client")

    def _load_credentials_from_path(self, path: str) -> dict[str, Any]:
        """Load credentials from a file path.

        Args:
            path: Path to credentials JSON file

        Returns:
            Parsed credentials dictionary

        Raises:
            GoogleContactsConfigError: If file cannot be read or parsed
        """
        try:
            with open(path, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise GoogleContactsConfigError(f"Failed to load credentials from {path}: {e}") from e

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Validate credentials structure.

        Args:
            credentials: Credentials dictionary

        Raises:
            GoogleContactsConfigError: If credentials are invalid
        """
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        missing = [f for f in required_fields if f not in credentials]
        if missing:
            raise GoogleContactsConfigError(
                f"Invalid credentials structure. Missing fields: {', '.join(missing)}"
            )

    async def authenticate(self) -> None:
        """Authenticate with Google API and obtain access token.

        Raises:
            GoogleContactsAuthError: If authentication fails
        """
        if self.access_token:
            logger.info("Using provided access token")
            return

        if not self.credentials_json:
            raise GoogleContactsAuthError("No credentials available for authentication")

        try:
            cred_type = self.credentials_json.get("type")

            if cred_type == "service_account":
                await self._authenticate_service_account()
            elif "access_token" in self.credentials_json:
                self.access_token = self.credentials_json["access_token"]
            else:
                raise GoogleContactsAuthError(
                    f"Unsupported credential type: {cred_type}. "
                    "Expected 'service_account' or credentials with access_token."
                )

            logger.info("Successfully authenticated with Google Contacts API")

        except GoogleContactsAuthError:
            raise
        except Exception as e:
            raise GoogleContactsAuthError(f"Authentication failed: {e}") from e

    async def _authenticate_service_account(self) -> None:
        """Authenticate using service account credentials.

        Implements JWT bearer token flow for service account authentication.
        Supports domain-wide delegation when delegated_user is specified.

        Raises:
            GoogleContactsAuthError: If JWT generation or token exchange fails
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            # Use single scope for domain-wide delegation or full scopes
            scopes = [self.DELEGATION_SCOPE] if self.delegated_user else self.DEFAULT_SCOPES

            # Create credentials from service account JSON
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scopes,
            )

            # Apply domain-wide delegation if delegated_user is specified
            if self.delegated_user:
                credentials = credentials.with_subject(self.delegated_user)
                logger.info(f"Using domain-wide delegation for: {self.delegated_user}")

            # Refresh to get access token
            request = Request()
            credentials.refresh(request)
            self.access_token = credentials.token

            logger.info("Service account authenticated successfully")

        except ImportError as e:
            raise GoogleContactsAuthError(
                "google-auth library required for service account authentication. "
                "Install with: pip install google-auth"
            ) from e
        except Exception as e:
            raise GoogleContactsAuthError(f"Service account auth failed: {e}") from e

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request to the People API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            API response as dictionary

        Raises:
            GoogleContactsAPIError: If request fails
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method, url=url, headers=headers, **kwargs
                )

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Rate limited. Retrying in {delay:.2f}s (attempt {attempt + 1}/"
                            f"{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise GoogleContactsRateLimitError("Rate limit exceeded", status_code=429)

                # Handle quota exceeded
                if response.status_code == 403:
                    error_data = response.json()
                    if "quotaExceeded" in str(error_data):
                        raise GoogleContactsQuotaExceeded("Quota exceeded", status_code=403)
                    raise GoogleContactsPermissionError(
                        error_data.get("error", {}).get("message", "Permission denied"),
                        status_code=403,
                    )

                # Handle not found
                if response.status_code == 404:
                    raise GoogleContactsNotFoundError("Resource not found", status_code=404)

                # Handle other errors
                if response.status_code >= 400:
                    raise GoogleContactsAPIError(
                        f"API request failed: {response.status_code}",
                        status_code=response.status_code,
                    )

                if response.text:
                    return cast(dict[str, Any], response.json())
                return {}

            except (httpx.RequestError, TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Request failed: {e}. Retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise GoogleContactsAPIError(f"Request failed after retries: {e}") from e

        # This line is unreachable in normal execution but required for MyPy type checking
        raise GoogleContactsAPIError("Request failed after all retries")

    async def list_contacts(
        self,
        person_fields: list[str] | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> ContactsListResponse:
        """List contacts for the authenticated user.

        Args:
            person_fields: Fields to include in response
            page_size: Number of results per page (max 1000)
            page_token: Token for pagination
            sync_token: Token for incremental sync

        Returns:
            ContactsListResponse with list of contacts

        Raises:
            GoogleContactsAPIError: If request fails
        """
        if not person_fields:
            person_fields = ["names", "emailAddresses", "phoneNumbers"]

        params = {
            "resourceName": "people/me",
            "personFields": ",".join(person_fields),
            "pageSize": page_size,
        }
        if page_token:
            params["pageToken"] = page_token
        if sync_token:
            params["syncToken"] = sync_token

        response = await self._make_request("GET", "/people/me/connections", params=params)
        return ContactsListResponse(**response)

    async def get_contact(
        self,
        resource_name: str,
        person_fields: list[str] | None = None,
    ) -> Contact:
        """Get a specific contact by resource name.

        Args:
            resource_name: Contact resource name (e.g., "people/c1234567890")
            person_fields: Fields to include in response

        Returns:
            Contact object

        Raises:
            GoogleContactsNotFoundError: If contact not found
            GoogleContactsAPIError: If request fails
        """
        if not person_fields:
            person_fields = [
                "names",
                "emailAddresses",
                "phoneNumbers",
                "addresses",
                "organizations",
            ]

        params = {"personFields": ",".join(person_fields)}

        response = await self._make_request("GET", f"/{resource_name}", params=params)
        return Contact(**response)

    async def create_contact(
        self,
        given_name: str | None = None,
        family_name: str | None = None,
        email_address: str | None = None,
        phone_number: str | None = None,
        organization: str | None = None,
        job_title: str | None = None,
    ) -> Contact:
        """Create a new contact.

        Args:
            given_name: Contact's first name
            family_name: Contact's last name
            email_address: Email address
            phone_number: Phone number
            organization: Organization name
            job_title: Job title

        Returns:
            Created Contact object

        Raises:
            GoogleContactsValidationError: If input is invalid
            GoogleContactsAPIError: If request fails
        """
        if not given_name and not family_name and not email_address:
            raise GoogleContactsValidationError(
                "At least one of given_name, family_name, or email_address is required"
            )

        # Build contact data
        contact_data: dict[str, Any] = {}

        if given_name or family_name:
            contact_data["names"] = [
                {
                    "givenName": given_name,
                    "familyName": family_name,
                }
            ]

        if email_address:
            contact_data["emailAddresses"] = [{"value": email_address, "type": "work"}]

        if phone_number:
            contact_data["phoneNumbers"] = [{"value": phone_number, "type": "mobile"}]

        if organization or job_title:
            org_data: dict[str, Any] = {}
            if organization:
                org_data["name"] = organization
            if job_title:
                org_data["title"] = job_title
            contact_data["organizations"] = [org_data]

        response = await self._make_request("POST", "/people:createContact", json=contact_data)
        return Contact(**response)

    async def update_contact(
        self,
        resource_name: str,
        etag: str | None = None,
        given_name: str | None = None,
        family_name: str | None = None,
        email_address: str | None = None,
        phone_number: str | None = None,
        organization: str | None = None,
        job_title: str | None = None,
    ) -> Contact:
        """Update an existing contact.

        Args:
            resource_name: Contact resource name
            etag: Contact's etag for conflict detection
            given_name: Contact's first name
            family_name: Contact's last name
            email_address: Email address
            phone_number: Phone number
            organization: Organization name
            job_title: Job title

        Returns:
            Updated Contact object

        Raises:
            GoogleContactsNotFoundError: If contact not found
            GoogleContactsAPIError: If request fails
        """
        # Get current contact to get etag and structure
        current = await self.get_contact(resource_name)
        if not etag and current.etag:
            etag = current.etag

        # Build update data
        contact_data: dict[str, Any] = {"etag": etag}

        if given_name or family_name:
            current_name = current.names[0] if current.names else None
            contact_data["names"] = [
                {
                    "givenName": given_name or (current_name.given_name if current_name else None),
                    "familyName": family_name
                    or (current_name.family_name if current_name else None),
                }
            ]

        if email_address:
            contact_data["emailAddresses"] = [{"value": email_address, "type": "work"}]

        if phone_number:
            contact_data["phoneNumbers"] = [{"value": phone_number, "type": "mobile"}]

        if organization or job_title:
            org_data: dict[str, Any] = {}
            if organization:
                org_data["name"] = organization
            if job_title:
                org_data["title"] = job_title
            contact_data["organizations"] = [org_data]

        update_mask = ",".join(contact_data.keys())
        params = {"updatePersonFields": update_mask}

        response = await self._make_request(
            "PATCH", f"/{resource_name}:updateContact", json=contact_data, params=params
        )
        return Contact(**response)

    async def delete_contact(self, resource_name: str) -> None:
        """Delete a contact.

        Args:
            resource_name: Contact resource name

        Raises:
            GoogleContactsNotFoundError: If contact not found
            GoogleContactsAPIError: If request fails
        """
        await self._make_request("DELETE", f"/{resource_name}")
        logger.info(f"Deleted contact: {resource_name}")

    async def create_contact_group(self, name: str) -> ContactGroup:
        """Create a contact group.

        Args:
            name: Group name

        Returns:
            Created ContactGroup object

        Raises:
            GoogleContactsValidationError: If input is invalid
            GoogleContactsAPIError: If request fails
        """
        if not name:
            raise GoogleContactsValidationError("Group name is required")

        data = {"contactGroup": {"name": name}}
        response = await self._make_request("POST", "/contactGroups", json=data)
        return ContactGroup(**response.get("contactGroup", {}))

    async def list_contact_groups(self, page_size: int = 100) -> ContactGroupsListResponse:
        """List contact groups.

        Args:
            page_size: Number of results per page

        Returns:
            ContactGroupsListResponse with list of groups

        Raises:
            GoogleContactsAPIError: If request fails
        """
        params = {"pageSize": page_size}
        response = await self._make_request("GET", "/contactGroups", params=params)
        return ContactGroupsListResponse(**response)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GoogleContactsClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
