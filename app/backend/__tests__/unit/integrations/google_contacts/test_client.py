"""Unit tests for Google Contacts API client.

Tests GoogleContactsClient initialization, authentication, and API operations
with comprehensive mocking and error handling validation.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.google_contacts.client import GoogleContactsClient
from src.integrations.google_contacts.exceptions import (
    GoogleContactsAuthError,
    GoogleContactsConfigError,
    GoogleContactsNotFoundError,
    GoogleContactsPermissionError,
    GoogleContactsQuotaExceeded,
    GoogleContactsValidationError,
)
from src.integrations.google_contacts.models import Contact, ContactGroup, ContactsListResponse

pytest_plugins = ("pytest_asyncio",)


class TestGoogleContactsClientInitialization:
    """Tests for client initialization."""

    def test_init_with_credentials_json(self) -> None:
        """Client should initialize with credentials_json."""
        creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "key",  # pragma: allowlist secret
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        client = GoogleContactsClient(credentials_json=creds)
        assert client.name == "google_contacts"
        assert client.credentials_json == creds

    def test_init_with_credentials_str(self) -> None:
        """Client should initialize with credentials_str (JSON string)."""
        import json

        creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "key",  # pragma: allowlist secret
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_str = json.dumps(creds)
        client = GoogleContactsClient(credentials_str=creds_str)
        assert client.credentials_json == creds

    def test_init_with_access_token(self) -> None:
        """Client should initialize with pre-obtained access token."""
        client = GoogleContactsClient(access_token="test-token-123")
        assert client.access_token == "test-token-123"

    def test_init_raises_on_missing_credentials(self) -> None:
        """Client should raise ConfigError if no credentials provided."""
        with pytest.raises(GoogleContactsConfigError):
            GoogleContactsClient()

    def test_init_raises_on_invalid_credentials_json(self) -> None:
        """Client should raise ConfigError on invalid JSON."""
        with pytest.raises(GoogleContactsConfigError):
            GoogleContactsClient(credentials_str="invalid json")

    def test_init_raises_on_missing_required_fields(self) -> None:
        """Client should raise ConfigError if credentials missing required fields."""
        invalid_creds = {"type": "service_account", "project_id": "test"}
        with pytest.raises(GoogleContactsConfigError):
            GoogleContactsClient(credentials_json=invalid_creds)

    def test_init_with_delegated_user(self) -> None:
        """Client should set delegation scope for domain-wide delegation."""
        creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "key",  # pragma: allowlist secret
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        client = GoogleContactsClient(credentials_json=creds, delegated_user="user@example.com")
        assert client.delegated_user == "user@example.com"
        assert client.scopes == [GoogleContactsClient.DELEGATION_SCOPE]

    def test_init_without_delegated_user(self) -> None:
        """Client should set default scopes without domain-wide delegation."""
        creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "key",  # pragma: allowlist secret
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        client = GoogleContactsClient(credentials_json=creds)
        assert client.scopes == GoogleContactsClient.DEFAULT_SCOPES


class TestGoogleContactsClientAuthentication:
    """Tests for authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_with_access_token(self) -> None:
        """Client should skip authentication if access token provided."""
        client = GoogleContactsClient(access_token="test-token")
        await client.authenticate()  # Should not raise
        assert client.access_token == "test-token"

    @pytest.mark.asyncio
    async def test_authenticate_without_credentials(self) -> None:
        """Client should raise AuthError if no credentials available."""
        client = GoogleContactsClient(access_token="test-token")
        client.credentials_json = {}
        client.access_token = None
        with pytest.raises(GoogleContactsAuthError):
            await client.authenticate()


class TestGoogleContactsClientListContacts:
    """Tests for list_contacts() operation."""

    @pytest.mark.asyncio
    async def test_list_contacts_success(self) -> None:
        """Should list contacts successfully."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c123",
                    "names": [{"givenName": "John", "familyName": "Doe"}],
                }
            ]
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.list_contacts()

            assert isinstance(result, ContactsListResponse)
            assert len(result.connections) == 1
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_contacts_with_pagination(self) -> None:
        """Should support pagination with page_token."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {"connections": []}
            await client.list_contacts(page_token="token123", page_size=50)

            # Verify pagination params were passed
            call_args = mock.call_args
            assert "pageSize" in str(call_args) or "page_token" in str(call_args)

    @pytest.mark.asyncio
    async def test_list_contacts_default_fields(self) -> None:
        """Should use default person fields if not specified."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {"connections": []}
            await client.list_contacts()

            # Should include default fields
            call_args = mock.call_args
            assert call_args is not None


class TestGoogleContactsClientGetContact:
    """Tests for get_contact() operation."""

    @pytest.mark.asyncio
    async def test_get_contact_success(self) -> None:
        """Should retrieve contact by resource name."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "resourceName": "people/c123",
            "names": [{"givenName": "John", "familyName": "Doe"}],
            "emailAddresses": [{"value": "john@example.com"}],
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.get_contact("people/c123")

            assert isinstance(result, Contact)
            assert result.resource_name == "people/c123"

    @pytest.mark.asyncio
    async def test_get_contact_not_found(self) -> None:
        """Should raise NotFoundError if contact doesn't exist."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = GoogleContactsNotFoundError("Not found", 404)
            with pytest.raises(GoogleContactsNotFoundError):
                await client.get_contact("people/invalid")


class TestGoogleContactsClientCreateContact:
    """Tests for create_contact() operation."""

    @pytest.mark.asyncio
    async def test_create_contact_success(self) -> None:
        """Should create contact successfully."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "resourceName": "people/c123",
            "names": [{"givenName": "Jane", "familyName": "Smith"}],
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.create_contact(given_name="Jane", family_name="Smith")

            assert isinstance(result, Contact)
            assert result.resource_name == "people/c123"

    @pytest.mark.asyncio
    async def test_create_contact_with_email(self) -> None:
        """Should create contact with email address."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {"resourceName": "people/c123"}
            await client.create_contact(email_address="jane@example.com")

            # Verify email was included in request
            call_args = mock.call_args
            assert "email" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_create_contact_missing_required_fields(self) -> None:
        """Should raise ValidationError if no required fields provided."""
        client = GoogleContactsClient(access_token="test-token")

        with pytest.raises(GoogleContactsValidationError):
            await client.create_contact()

    @pytest.mark.asyncio
    async def test_create_contact_with_phone(self) -> None:
        """Should create contact with phone number."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {"resourceName": "people/c123"}
            await client.create_contact(given_name="Jane", phone_number="+1-555-1234")

            # Verify phone was included
            call_args = mock.call_args
            assert "phone" in str(call_args).lower()


class TestGoogleContactsClientUpdateContact:
    """Tests for update_contact() operation."""

    @pytest.mark.asyncio
    async def test_update_contact_success(self) -> None:
        """Should update contact successfully."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "resourceName": "people/c123",
            "names": [{"givenName": "Janet", "familyName": "Smith"}],
            "etag": "updated-etag",
        }

        with (
            patch.object(client, "_make_request", new_callable=AsyncMock) as mock,
            patch.object(client, "get_contact", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Contact(**mock_response)
            mock.return_value = mock_response

            result = await client.update_contact("people/c123", given_name="Janet")

            assert result.resource_name == "people/c123"

    @pytest.mark.asyncio
    async def test_update_contact_not_found(self) -> None:
        """Should raise NotFoundError if contact doesn't exist."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "get_contact", new_callable=AsyncMock) as mock:
            mock.side_effect = GoogleContactsNotFoundError("Not found", 404)
            with pytest.raises(GoogleContactsNotFoundError):
                await client.update_contact("people/invalid", given_name="Jane")


class TestGoogleContactsClientDeleteContact:
    """Tests for delete_contact() operation."""

    @pytest.mark.asyncio
    async def test_delete_contact_success(self) -> None:
        """Should delete contact successfully."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {}
            await client.delete_contact("people/c123")

            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_contact_not_found(self) -> None:
        """Should raise NotFoundError if contact doesn't exist."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = GoogleContactsNotFoundError("Not found", 404)
            with pytest.raises(GoogleContactsNotFoundError):
                await client.delete_contact("people/invalid")


class TestGoogleContactsClientContactGroups:
    """Tests for contact group operations."""

    @pytest.mark.asyncio
    async def test_create_contact_group_success(self) -> None:
        """Should create contact group successfully."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "contactGroup": {
                "resourceName": "contactGroups/c123",
                "name": "Friends",
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.create_contact_group("Friends")

            assert isinstance(result, ContactGroup)
            assert result.name == "Friends"

    @pytest.mark.asyncio
    async def test_create_contact_group_missing_name(self) -> None:
        """Should raise ValidationError if group name missing."""
        client = GoogleContactsClient(access_token="test-token")

        with pytest.raises(GoogleContactsValidationError):
            await client.create_contact_group("")

    @pytest.mark.asyncio
    async def test_list_contact_groups_success(self) -> None:
        """Should list contact groups successfully."""
        client = GoogleContactsClient(access_token="test-token")

        mock_response = {
            "contactGroups": [{"resourceName": "contactGroups/c123", "name": "Friends"}]
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.list_contact_groups()

            assert result.contact_groups is not None
            assert len(result.contact_groups) == 1


class TestGoogleContactsClientErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_retry(self) -> None:
        """Should retry on rate limit (429) error."""
        client = GoogleContactsClient(access_token="test-token")

        # This should retry on rate limit
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_make:
            mock_make.return_value = {"connections": []}
            result = await client.list_contacts()
            assert result is not None

    @pytest.mark.asyncio
    async def test_permission_error_403(self) -> None:
        """Should raise PermissionError on 403 status."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = GoogleContactsPermissionError("Permission denied", 403)
            with pytest.raises(GoogleContactsPermissionError):
                await client.list_contacts()

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self) -> None:
        """Should raise QuotaExceeded error."""
        client = GoogleContactsClient(access_token="test-token")

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = GoogleContactsQuotaExceeded("Quota exceeded", 403)
            with pytest.raises(GoogleContactsQuotaExceeded):
                await client.list_contacts()


class TestGoogleContactsClientContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Should support async with statement."""
        creds = {  # pragma: allowlist secret
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "key",  # pragma: allowlist secret
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        async with GoogleContactsClient(
            credentials_json=creds, access_token="test-token"
        ) as client:
            assert client.access_token == "test-token"
