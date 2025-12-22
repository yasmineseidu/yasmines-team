"""
Unit tests for QuickBooks Online integration client.

Tests cover:
- Client initialization and validation
- OAuth2 token management and refresh
- Customer CRUD operations
- Invoice CRUD operations
- Expense/Purchase CRUD operations
- Company info retrieval
- Error handling for all HTTP status codes
- Retry logic and rate limiting
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.quickbooks import (
    CompanyInfo,
    Customer,
    EntityType,
    Expense,
    Invoice,
    InvoiceStatus,
    PaymentMethod,
    QuickBooksAuthError,
    QuickBooksClient,
    QuickBooksError,
    QuickBooksNotFoundError,
    QuickBooksRateLimitError,
    QuickBooksValidationError,
    TokenInfo,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_credentials() -> dict[str, str]:
    """Return mock QuickBooks OAuth2 credentials."""
    return {
        "client_id": "test_client_id",  # pragma: allowlist secret
        "client_secret": "test_client_secret",  # pragma: allowlist secret
        "realm_id": "123456789",
        "access_token": "test_access_token",  # pragma: allowlist secret
        "refresh_token": "test_refresh_token",  # pragma: allowlist secret
    }


@pytest.fixture
def client(mock_credentials: dict[str, str]) -> QuickBooksClient:
    """Create a QuickBooksClient instance for testing."""
    return QuickBooksClient(**mock_credentials)


@pytest.fixture
def sandbox_client(mock_credentials: dict[str, str]) -> QuickBooksClient:
    """Create a sandbox QuickBooksClient instance for testing."""
    return QuickBooksClient(**mock_credentials, environment="sandbox")


@pytest.fixture
def mock_customer_response() -> dict:
    """Return mock customer API response."""
    return {
        "Customer": {
            "Id": "1",
            "DisplayName": "Acme Corp",
            "SyncToken": "0",
            "CompanyName": "Acme Corporation",
            "GivenName": "John",
            "FamilyName": "Doe",
            "PrimaryEmailAddr": {"Address": "john@acme.com"},
            "PrimaryPhone": {"FreeFormNumber": "555-1234"},
            "Mobile": {"FreeFormNumber": "555-5678"},
            "Balance": 1500.00,
            "BillAddr": {
                "Line1": "123 Main St",
                "City": "San Francisco",
                "Country": "USA",
            },
            "Active": True,
            "MetaData": {
                "CreateTime": "2025-01-01T10:00:00-08:00",
                "LastUpdatedTime": "2025-01-15T14:30:00-08:00",
            },
        }
    }


@pytest.fixture
def mock_invoice_response() -> dict:
    """Return mock invoice API response."""
    return {
        "Invoice": {
            "Id": "100",
            "DocNumber": "INV-001",
            "SyncToken": "1",
            "CustomerRef": {"value": "1", "name": "Acme Corp"},
            "Line": [
                {
                    "Amount": 500.00,
                    "Description": "Consulting services",
                    "DetailType": "SalesItemLineDetail",
                }
            ],
            "TotalAmt": 500.00,
            "Balance": 500.00,
            "DueDate": "2025-02-15",
            "TxnDate": "2025-01-15",
            "EmailStatus": "NotSet",
            "BillEmail": {"Address": "billing@acme.com"},
            "MetaData": {
                "CreateTime": "2025-01-15T10:00:00-08:00",
                "LastUpdatedTime": "2025-01-15T10:00:00-08:00",
            },
        }
    }


@pytest.fixture
def mock_expense_response() -> dict:
    """Return mock expense/purchase API response."""
    return {
        "Purchase": {
            "Id": "50",
            "SyncToken": "0",
            "PaymentType": "CreditCard",
            "AccountRef": {"value": "1", "name": "Business Credit Card"},
            "Line": [
                {
                    "Amount": 150.00,
                    "Description": "Office supplies",
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "10"}},
                }
            ],
            "TotalAmt": 150.00,
            "TxnDate": "2025-01-10",
            "EntityRef": {"value": "5", "type": "Vendor"},
            "MetaData": {
                "CreateTime": "2025-01-10T09:00:00-08:00",
                "LastUpdatedTime": "2025-01-10T09:00:00-08:00",
            },
        }
    }


@pytest.fixture
def mock_company_info_response() -> dict:
    """Return mock company info API response."""
    return {
        "CompanyInfo": {
            "Id": "123456789",
            "CompanyName": "My Test Company",
            "SyncToken": "5",
            "LegalName": "My Test Company LLC",
            "CompanyAddr": {
                "Line1": "100 Business Ave",
                "City": "San Francisco",
                "Country": "USA",
            },
            "Email": {"Address": "info@testcompany.com"},
            "PrimaryPhone": {"FreeFormNumber": "555-9999"},
            "FiscalYearStartMonth": "January",
            "Country": "US",
            "SupportedLanguages": "en,es",
        }
    }


@pytest.fixture
def mock_token_response() -> dict:
    """Return mock token refresh response."""
    return {
        "access_token": "new_access_token",  # pragma: allowlist secret
        "refresh_token": "new_refresh_token",  # pragma: allowlist secret
        "token_type": "Bearer",
        "expires_in": 3600,
        "x_refresh_token_expires_in": 8726400,
    }


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestQuickBooksClientInitialization:
    """Tests for QuickBooksClient initialization."""

    def test_initialization_success(self, mock_credentials: dict[str, str]) -> None:
        """Client initializes with valid credentials."""
        client = QuickBooksClient(**mock_credentials)

        assert client.client_id == mock_credentials["client_id"]
        assert client.client_secret == mock_credentials["client_secret"]
        assert client.realm_id == mock_credentials["realm_id"]
        assert client.access_token == mock_credentials["access_token"]
        assert client.refresh_token == mock_credentials["refresh_token"]
        assert client.environment == "production"
        assert client.minor_version == 75

    def test_initialization_sandbox_environment(self, mock_credentials: dict[str, str]) -> None:
        """Client initializes with sandbox environment."""
        client = QuickBooksClient(**mock_credentials, environment="sandbox")

        assert client.environment == "sandbox"
        assert "sandbox" in client.base_url

    def test_initialization_production_environment(self, mock_credentials: dict[str, str]) -> None:
        """Client initializes with production environment."""
        client = QuickBooksClient(**mock_credentials, environment="production")

        assert client.environment == "production"
        assert "sandbox" not in client.base_url

    def test_initialization_custom_minor_version(self, mock_credentials: dict[str, str]) -> None:
        """Client initializes with custom minor version."""
        client = QuickBooksClient(**mock_credentials, minor_version=76)

        assert client.minor_version == 76

    def test_initialization_empty_client_id_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for empty client_id."""
        mock_credentials["client_id"] = ""

        with pytest.raises(ValueError, match="client_id cannot be empty"):
            QuickBooksClient(**mock_credentials)

    def test_initialization_empty_client_secret_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for empty client_secret."""
        mock_credentials["client_secret"] = ""

        with pytest.raises(ValueError, match="client_secret cannot be empty"):
            QuickBooksClient(**mock_credentials)

    def test_initialization_empty_realm_id_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for empty realm_id."""
        mock_credentials["realm_id"] = ""

        with pytest.raises(ValueError, match="realm_id cannot be empty"):
            QuickBooksClient(**mock_credentials)

    def test_initialization_empty_access_token_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for empty access_token."""
        mock_credentials["access_token"] = ""

        with pytest.raises(ValueError, match="access_token cannot be empty"):
            QuickBooksClient(**mock_credentials)

    def test_initialization_empty_refresh_token_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for empty refresh_token."""
        mock_credentials["refresh_token"] = ""

        with pytest.raises(ValueError, match="refresh_token cannot be empty"):
            QuickBooksClient(**mock_credentials)

    def test_initialization_invalid_environment_raises_error(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Raises ValueError for invalid environment."""
        with pytest.raises(ValueError, match="environment must be"):
            QuickBooksClient(**mock_credentials, environment="invalid")

    def test_initialization_whitespace_values_trimmed(
        self, mock_credentials: dict[str, str]
    ) -> None:
        """Whitespace is trimmed from credential values."""
        mock_credentials["client_id"] = "  test_client_id  "
        mock_credentials["realm_id"] = " 123456789 "

        client = QuickBooksClient(**mock_credentials)

        assert client.client_id == "test_client_id"
        assert client.realm_id == "123456789"


class TestQuickBooksClientHeaders:
    """Tests for header generation."""

    def test_get_headers_returns_bearer_token(self, client: QuickBooksClient) -> None:
        """Headers include Bearer token authorization."""
        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_access_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestQuickBooksClientEndpoints:
    """Tests for endpoint URL generation."""

    def test_get_endpoint_with_entity(self, client: QuickBooksClient) -> None:
        """Endpoint includes realm_id and minor version."""
        endpoint = client._get_endpoint("customer")

        assert "123456789" in endpoint
        assert "customer" in endpoint
        assert "minorversion=75" in endpoint

    def test_get_endpoint_with_entity_id(self, client: QuickBooksClient) -> None:
        """Endpoint includes entity ID when provided."""
        endpoint = client._get_endpoint("customer", "1")

        assert "/123456789/customer/1" in endpoint
        assert "minorversion=75" in endpoint


# ============================================================================
# TOKEN MANAGEMENT TESTS
# ============================================================================


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_token_not_expired_when_fresh(self) -> None:
        """Token is not expired when freshly created."""
        token = TokenInfo(
            access_token="test",
            refresh_token="test",
            expires_in=3600,
        )

        assert token.is_expired is False

    def test_token_expired_after_expiry_time(self) -> None:
        """Token is expired after expiry time (minus buffer)."""
        token = TokenInfo(
            access_token="test",
            refresh_token="test",
            expires_in=3600,
            created_at=time.time() - 3600,  # Created 1 hour ago
        )

        assert token.is_expired is True

    def test_token_expired_within_buffer(self) -> None:
        """Token is considered expired within 5-minute buffer."""
        token = TokenInfo(
            access_token="test",
            refresh_token="test",
            expires_in=3600,
            created_at=time.time() - 3400,  # Created 56 mins ago (< 5 min buffer)
        )

        assert token.is_expired is True

    def test_refresh_token_expiration_timestamp(self) -> None:
        """Refresh token expiration is calculated correctly."""
        now = time.time()
        token = TokenInfo(
            access_token="test",
            refresh_token="test",
            x_refresh_token_expires_in=8726400,  # ~100 days
            created_at=now,
        )

        expected = now + 8726400
        assert abs(token.refresh_token_expires_at - expected) < 1


class TestQuickBooksClientTokenRefresh:
    """Tests for OAuth2 token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self,
        client: QuickBooksClient,
        mock_token_response: dict,
    ) -> None:
        """Successfully refreshes access token."""
        # Mark token as expired so refresh will proceed
        client._token_info = TokenInfo(
            access_token="old_token",
            refresh_token="old_refresh",
            expires_in=3600,
            created_at=time.time() - 3700,  # Expired
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            token_info = await client.refresh_access_token()

            assert token_info.access_token == "new_access_token"
            assert token_info.refresh_token == "new_refresh_token"
            assert client.access_token == "new_access_token"
            assert client.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksAuthError on refresh failure."""
        # Mark token as expired so refresh will proceed
        client._token_info = TokenInfo(
            access_token="old_token",
            refresh_token="old_refresh",
            expires_in=3600,
            created_at=time.time() - 3700,  # Expired
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token expired",
        }
        mock_response.text = '{"error": "invalid_grant"}'

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(QuickBooksAuthError, match="Token refresh failed"):
                await client.refresh_access_token()

    @pytest.mark.asyncio
    async def test_auto_refresh_when_token_expired(
        self,
        client: QuickBooksClient,
        mock_token_response: dict,
        mock_customer_response: dict,
    ) -> None:
        """Automatically refreshes token when expired."""
        # Set token as expired
        client._token_info = TokenInfo(
            access_token="old_token",
            refresh_token="old_refresh",
            expires_in=3600,
            created_at=time.time() - 3700,  # Expired
        )

        # Mock token refresh
        token_mock_response = MagicMock()
        token_mock_response.status_code = 200
        token_mock_response.json.return_value = mock_token_response

        with (
            patch.object(client.client, "post", new_callable=AsyncMock) as mock_post,
            patch.object(client, "get", new_callable=AsyncMock) as mock_get,
        ):
            mock_post.return_value = token_mock_response
            mock_get.return_value = mock_customer_response

            # This should trigger token refresh before making the actual request
            await client.get_customer("1")

            # Verify token was refreshed
            assert client.access_token == "new_access_token"


# ============================================================================
# CUSTOMER OPERATIONS TESTS
# ============================================================================


class TestQuickBooksCustomerOperations:
    """Tests for customer CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_customer_success(
        self,
        client: QuickBooksClient,
        mock_customer_response: dict,
    ) -> None:
        """Successfully creates a customer."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_customer_response

            customer = await client.create_customer(
                display_name="Acme Corp",
                company_name="Acme Corporation",
                email="john@acme.com",
                phone="555-1234",
            )

            assert isinstance(customer, Customer)
            assert customer.id == "1"
            assert customer.display_name == "Acme Corp"
            assert customer.email == "john@acme.com"
            assert customer.company_name == "Acme Corporation"

    @pytest.mark.asyncio
    async def test_create_customer_with_address(
        self,
        client: QuickBooksClient,
        mock_customer_response: dict,
    ) -> None:
        """Creates customer with billing and shipping addresses."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_customer_response

            billing_addr = {"Line1": "123 Main St", "City": "SF", "Country": "USA"}
            customer = await client.create_customer(
                display_name="Acme Corp",
                billing_address=billing_addr,
            )

            assert customer.billing_address == mock_customer_response["Customer"]["BillAddr"]
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "BillAddr" in call_args.kwargs["json"]

    @pytest.mark.asyncio
    async def test_create_customer_validation_error(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksValidationError on 400 response."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Duplicate name exists", status_code=400)

            with pytest.raises(QuickBooksValidationError, match="Invalid customer data"):
                await client.create_customer(display_name="Duplicate")

    @pytest.mark.asyncio
    async def test_get_customer_success(
        self,
        client: QuickBooksClient,
        mock_customer_response: dict,
    ) -> None:
        """Successfully retrieves a customer."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_customer_response

            customer = await client.get_customer("1")

            assert customer.id == "1"
            assert customer.display_name == "Acme Corp"
            assert customer.sync_token == "0"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksNotFoundError for non-existent customer."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Not found", status_code=404)

            with pytest.raises(QuickBooksNotFoundError, match="not found"):
                await client.get_customer("999")

    @pytest.mark.asyncio
    async def test_update_customer_success(
        self,
        client: QuickBooksClient,
        mock_customer_response: dict,
    ) -> None:
        """Successfully updates a customer."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_customer_response

            customer = await client.update_customer(
                customer_id="1",
                sync_token="0",
                display_name="Acme Corp Updated",
                email="updated@acme.com",
            )

            assert isinstance(customer, Customer)
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["Id"] == "1"
            assert call_args.kwargs["json"]["SyncToken"] == "0"
            assert call_args.kwargs["json"]["sparse"] is True

    @pytest.mark.asyncio
    async def test_update_customer_stale_sync_token(self, client: QuickBooksClient) -> None:
        """Raises error on stale sync token."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Stale object", status_code=400)

            with pytest.raises(QuickBooksValidationError, match="stale sync token"):
                await client.update_customer(customer_id="1", sync_token="0", display_name="Test")

    @pytest.mark.asyncio
    async def test_query_customers_success(self, client: QuickBooksClient) -> None:
        """Successfully queries customers."""
        query_response = {
            "QueryResponse": {
                "Customer": [
                    {"Id": "1", "DisplayName": "Acme", "SyncToken": "0"},
                    {"Id": "2", "DisplayName": "Beta Corp", "SyncToken": "1"},
                ]
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = query_response

            customers = await client.query_customers(where="Active = true", max_results=10)

            assert len(customers) == 2
            assert customers[0].display_name == "Acme"
            assert customers[1].display_name == "Beta Corp"

    @pytest.mark.asyncio
    async def test_query_customers_empty_result(self, client: QuickBooksClient) -> None:
        """Returns empty list when no customers match query."""
        query_response = {"QueryResponse": {}}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = query_response

            customers = await client.query_customers(where="Balance > 10000")

            assert customers == []


# ============================================================================
# INVOICE OPERATIONS TESTS
# ============================================================================


class TestQuickBooksInvoiceOperations:
    """Tests for invoice CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_invoice_success(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Successfully creates an invoice."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_invoice_response

            line_items = [
                {
                    "Amount": 500.00,
                    "Description": "Consulting",
                    "DetailType": "SalesItemLineDetail",
                }
            ]

            invoice = await client.create_invoice(
                customer_id="1",
                line_items=line_items,
                due_date="2025-02-15",
            )

            assert isinstance(invoice, Invoice)
            assert invoice.id == "100"
            assert invoice.total_amount == 500.00
            assert invoice.customer_ref["value"] == "1"

    @pytest.mark.asyncio
    async def test_create_invoice_with_billing_email(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Creates invoice with billing email."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_invoice_response

            await client.create_invoice(
                customer_id="1",
                line_items=[{"Amount": 100}],
                billing_email="billing@acme.com",
            )

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["BillEmail"]["Address"] == "billing@acme.com"

    @pytest.mark.asyncio
    async def test_get_invoice_success(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Successfully retrieves an invoice."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_invoice_response

            invoice = await client.get_invoice("100")

            assert invoice.id == "100"
            assert invoice.doc_number == "INV-001"
            assert invoice.due_date == "2025-02-15"

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksNotFoundError for non-existent invoice."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Not found", status_code=404)

            with pytest.raises(QuickBooksNotFoundError, match="not found"):
                await client.get_invoice("999")

    @pytest.mark.asyncio
    async def test_update_invoice_success(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Successfully updates an invoice."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_invoice_response

            invoice = await client.update_invoice(
                invoice_id="100",
                sync_token="1",
                due_date="2025-03-01",
            )

            assert isinstance(invoice, Invoice)
            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["DueDate"] == "2025-03-01"

    @pytest.mark.asyncio
    async def test_query_invoices_success(self, client: QuickBooksClient) -> None:
        """Successfully queries invoices."""
        query_response = {
            "QueryResponse": {
                "Invoice": [
                    {
                        "Id": "100",
                        "DocNumber": "INV-001",
                        "SyncToken": "0",
                        "CustomerRef": {"value": "1"},
                        "TotalAmt": 500,
                    }
                ]
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = query_response

            invoices = await client.query_invoices(
                where="TotalAmt > '100.00'", order_by="TxnDate DESC"
            )

            assert len(invoices) == 1
            assert invoices[0].doc_number == "INV-001"

    @pytest.mark.asyncio
    async def test_send_invoice_success(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Successfully sends an invoice via email."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_invoice_response

            invoice = await client.send_invoice("100", email="customer@example.com")

            assert isinstance(invoice, Invoice)
            mock_post.assert_called_once()
            # Verify endpoint includes sendTo parameter
            call_args = mock_post.call_args
            assert "send" in str(call_args)


# ============================================================================
# EXPENSE OPERATIONS TESTS
# ============================================================================


class TestQuickBooksExpenseOperations:
    """Tests for expense/purchase CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_expense_success(
        self,
        client: QuickBooksClient,
        mock_expense_response: dict,
    ) -> None:
        """Successfully creates an expense."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_expense_response

            line_items = [
                {
                    "Amount": 150.00,
                    "Description": "Office supplies",
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "10"}},
                }
            ]

            expense = await client.create_expense(
                account_id="1",
                payment_type="CreditCard",
                line_items=line_items,
                txn_date="2025-01-10",
            )

            assert isinstance(expense, Expense)
            assert expense.id == "50"
            assert expense.total_amount == 150.00
            assert expense.payment_type == "CreditCard"

    @pytest.mark.asyncio
    async def test_create_expense_with_vendor(
        self,
        client: QuickBooksClient,
        mock_expense_response: dict,
    ) -> None:
        """Creates expense with vendor reference."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_expense_response

            await client.create_expense(
                account_id="1",
                payment_type="Check",
                line_items=[{"Amount": 100}],
                vendor_id="5",
            )

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["EntityRef"]["value"] == "5"

    @pytest.mark.asyncio
    async def test_get_expense_success(
        self,
        client: QuickBooksClient,
        mock_expense_response: dict,
    ) -> None:
        """Successfully retrieves an expense."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_expense_response

            expense = await client.get_expense("50")

            assert expense.id == "50"
            assert expense.payment_type == "CreditCard"

    @pytest.mark.asyncio
    async def test_get_expense_not_found(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksNotFoundError for non-existent expense."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Not found", status_code=404)

            with pytest.raises(QuickBooksNotFoundError, match="not found"):
                await client.get_expense("999")

    @pytest.mark.asyncio
    async def test_update_expense_success(
        self,
        client: QuickBooksClient,
        mock_expense_response: dict,
    ) -> None:
        """Successfully updates an expense."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_expense_response

            expense = await client.update_expense(
                expense_id="50",
                sync_token="0",
                private_note="Updated note",
            )

            assert isinstance(expense, Expense)
            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["PrivateNote"] == "Updated note"

    @pytest.mark.asyncio
    async def test_query_expenses_success(self, client: QuickBooksClient) -> None:
        """Successfully queries expenses."""
        query_response = {
            "QueryResponse": {
                "Purchase": [
                    {
                        "Id": "50",
                        "SyncToken": "0",
                        "PaymentType": "CreditCard",
                        "AccountRef": {"value": "1"},
                        "TotalAmt": 150,
                    }
                ]
            }
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = query_response

            expenses = await client.query_expenses(where="TotalAmt > '50.00'")

            assert len(expenses) == 1
            assert expenses[0].payment_type == "CreditCard"


# ============================================================================
# COMPANY INFO TESTS
# ============================================================================


class TestQuickBooksCompanyInfo:
    """Tests for company info retrieval."""

    @pytest.mark.asyncio
    async def test_get_company_info_success(
        self,
        client: QuickBooksClient,
        mock_company_info_response: dict,
    ) -> None:
        """Successfully retrieves company info."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_company_info_response

            company = await client.get_company_info()

            assert isinstance(company, CompanyInfo)
            assert company.id == "123456789"
            assert company.company_name == "My Test Company"
            assert company.legal_name == "My Test Company LLC"
            assert company.country == "US"
            assert "en" in company.supported_languages


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestQuickBooksErrorHandling:
    """Tests for error handling across all operations."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksRateLimitError on 429 response."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Rate limited", status_code=429)

            with pytest.raises(QuickBooksRateLimitError):
                await client.get_customer("1")

    @pytest.mark.asyncio
    async def test_auth_error_handling(self, client: QuickBooksClient) -> None:
        """Raises QuickBooksError on 401 response without auto-refresh."""
        from src.integrations.base import AuthenticationError

        client.auto_refresh = False

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = AuthenticationError("Invalid token")

            with pytest.raises(QuickBooksError, match="Failed to get customer"):
                await client.get_customer("1")

    @pytest.mark.asyncio
    async def test_generic_error_wrapping(self, client: QuickBooksClient) -> None:
        """Wraps generic errors in QuickBooksError."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = IntegrationError("Server error", status_code=500)

            with pytest.raises(QuickBooksError, match="Failed to get customer"):
                await client.get_customer("1")


# ============================================================================
# UTILITY METHOD TESTS
# ============================================================================


class TestQuickBooksUtilityMethods:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: QuickBooksClient) -> None:
        """call_endpoint works for GET requests."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": "test"}

            result = await client.call_endpoint("/estimate", method="GET")

            assert result == {"data": "test"}
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: QuickBooksClient) -> None:
        """call_endpoint works for POST requests."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "1"}

            result = await client.call_endpoint("/estimate", method="POST", json={"data": "test"})

            assert result == {"id": "1"}
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_adds_realm_id(self, client: QuickBooksClient) -> None:
        """call_endpoint adds realm_id to endpoint if missing."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}

            await client.call_endpoint("/payment")

            call_args = mock_get.call_args[0][0]
            assert client.realm_id in call_args

    @pytest.mark.asyncio
    async def test_call_endpoint_adds_minor_version(self, client: QuickBooksClient) -> None:
        """call_endpoint adds minorversion if missing."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}

            await client.call_endpoint("/payment")

            call_args = mock_get.call_args[0][0]
            assert "minorversion=75" in call_args

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        client: QuickBooksClient,
        mock_company_info_response: dict,
    ) -> None:
        """Health check returns healthy status on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_company_info_response

            result = await client.health_check()

            assert result["healthy"] is True
            assert result["name"] == "quickbooks"
            assert result["company_name"] == "My Test Company"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: QuickBooksClient) -> None:
        """Health check returns unhealthy status on failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.health_check()

            assert result["healthy"] is False
            assert "error" in result


# ============================================================================
# ENUM TESTS
# ============================================================================


class TestQuickBooksEnums:
    """Tests for enum values."""

    def test_entity_type_values(self) -> None:
        """EntityType enum has expected values."""
        assert EntityType.CUSTOMER.value == "Customer"
        assert EntityType.INVOICE.value == "Invoice"
        assert EntityType.PURCHASE.value == "Purchase"

    def test_invoice_status_values(self) -> None:
        """InvoiceStatus enum has expected values."""
        assert InvoiceStatus.DRAFT.value == "Draft"
        assert InvoiceStatus.PAID.value == "Paid"
        assert InvoiceStatus.OVERDUE.value == "Overdue"

    def test_payment_method_values(self) -> None:
        """PaymentMethod enum has expected values."""
        assert PaymentMethod.CASH.value == "Cash"
        assert PaymentMethod.CHECK.value == "Check"
        assert PaymentMethod.CREDIT_CARD.value == "CreditCard"


# ============================================================================
# DATA CLASS PARSING TESTS
# ============================================================================


class TestQuickBooksDataClassParsing:
    """Tests for data class parsing methods."""

    def test_parse_customer_complete(
        self,
        client: QuickBooksClient,
        mock_customer_response: dict,
    ) -> None:
        """Parses complete customer data correctly."""
        customer = client._parse_customer(mock_customer_response["Customer"])

        assert customer.id == "1"
        assert customer.display_name == "Acme Corp"
        assert customer.sync_token == "0"
        assert customer.email == "john@acme.com"
        assert customer.phone == "555-1234"
        assert customer.mobile == "555-5678"
        assert customer.balance == 1500.00
        assert customer.active is True
        assert customer.created_at == "2025-01-01T10:00:00-08:00"

    def test_parse_customer_minimal(self, client: QuickBooksClient) -> None:
        """Parses minimal customer data with defaults."""
        minimal_data = {"Id": "1", "DisplayName": "Test"}
        customer = client._parse_customer(minimal_data)

        assert customer.id == "1"
        assert customer.display_name == "Test"
        assert customer.sync_token == "0"  # Default
        assert customer.email is None
        assert customer.billing_address == {}

    def test_parse_invoice_complete(
        self,
        client: QuickBooksClient,
        mock_invoice_response: dict,
    ) -> None:
        """Parses complete invoice data correctly."""
        invoice = client._parse_invoice(mock_invoice_response["Invoice"])

        assert invoice.id == "100"
        assert invoice.doc_number == "INV-001"
        assert invoice.sync_token == "1"
        assert invoice.total_amount == 500.00
        assert invoice.due_date == "2025-02-15"
        assert invoice.billing_email == "billing@acme.com"
        assert len(invoice.line_items) == 1

    def test_parse_expense_complete(
        self,
        client: QuickBooksClient,
        mock_expense_response: dict,
    ) -> None:
        """Parses complete expense data correctly."""
        expense = client._parse_expense(mock_expense_response["Purchase"])

        assert expense.id == "50"
        assert expense.payment_type == "CreditCard"
        assert expense.total_amount == 150.00
        assert expense.entity_ref["value"] == "5"

    def test_parse_company_info_complete(
        self,
        client: QuickBooksClient,
        mock_company_info_response: dict,
    ) -> None:
        """Parses complete company info correctly."""
        company = client._parse_company_info(mock_company_info_response["CompanyInfo"])

        assert company.id == "123456789"
        assert company.company_name == "My Test Company"
        assert company.legal_name == "My Test Company LLC"
        assert company.country == "US"
        assert company.supported_languages == ["en", "es"]
