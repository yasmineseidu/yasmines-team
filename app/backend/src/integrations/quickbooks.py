"""
QuickBooks Online API integration client for accounting and financial management.

Provides async access to QuickBooks Online REST API v3 including:
- OAuth2 authentication with automatic token refresh
- Customer management (CRUD operations)
- Invoice management (create, update, send)
- Expense/purchase management
- Company information retrieval
- Query-based filtering with JPQL-style syntax

API Documentation: https://developer.intuit.com/app/developer/qbo/docs/develop
Base URL (Production): https://quickbooks.api.intuit.com/v3
Base URL (Sandbox): https://sandbox-quickbooks.api.intuit.com/v3

Rate Limits:
- 500 requests per minute per realm ID
- Exponential backoff on 429 (Too Many Requests)

Authentication:
- OAuth 2.0 with access tokens (60-minute expiry)
- Refresh tokens (100-day expiry)
- Token refresh endpoint: https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer

Example:
    >>> from src.integrations.quickbooks import QuickBooksClient
    >>> client = QuickBooksClient(
    ...     client_id="your_client_id",
    ...     client_secret="your_client_secret",  # pragma: allowlist secret
    ...     realm_id="123456789",
    ...     access_token="...",
    ...     refresh_token="..."
    ... )
    >>> customer = await client.create_customer(
    ...     display_name="Acme Corp",
    ...     email="contact@acme.com"
    ... )
    >>> print(customer.id)
"""

import asyncio
import base64
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import quote

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class QuickBooksError(IntegrationError):
    """Base exception for QuickBooks API errors."""

    pass


class QuickBooksAuthError(QuickBooksError):
    """Raised when QuickBooks authentication fails or token is invalid."""

    def __init__(
        self,
        message: str = "QuickBooks authentication failed",
        **kwargs: Any,
    ) -> None:
        # Remove status_code from kwargs if present to avoid duplicate
        kwargs.pop("status_code", None)
        super().__init__(message, status_code=401, **kwargs)


class QuickBooksRateLimitError(QuickBooksError):
    """Raised when QuickBooks API rate limit is exceeded (500 req/min per realm)."""

    def __init__(
        self,
        message: str = "QuickBooks API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        # Remove status_code from kwargs if present to avoid duplicate
        kwargs.pop("status_code", None)
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class QuickBooksValidationError(QuickBooksError):
    """Raised when request validation fails (e.g., missing required fields)."""

    def __init__(
        self,
        message: str = "QuickBooks validation error",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=400, **kwargs)


class QuickBooksNotFoundError(QuickBooksError):
    """Raised when requested entity is not found."""

    def __init__(
        self,
        message: str = "QuickBooks entity not found",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=404, **kwargs)


class QuickBooksTokenExpiredError(QuickBooksAuthError):
    """Raised when OAuth2 access token has expired and needs refresh."""

    pass


# ============================================================================
# ENUMS
# ============================================================================


class EntityType(str, Enum):
    """QuickBooks entity types."""

    CUSTOMER = "Customer"
    INVOICE = "Invoice"
    PURCHASE = "Purchase"
    BILL = "Bill"
    VENDOR = "Vendor"
    ITEM = "Item"
    ACCOUNT = "Account"
    PAYMENT = "Payment"
    ESTIMATE = "Estimate"
    CREDIT_MEMO = "CreditMemo"
    SALES_RECEIPT = "SalesReceipt"


class InvoiceStatus(str, Enum):
    """Invoice status values."""

    DRAFT = "Draft"
    PENDING = "Pending"
    SENT = "Sent"
    PAID = "Paid"
    OVERDUE = "Overdue"
    VOIDED = "Voided"


class PaymentMethod(str, Enum):
    """Payment method types."""

    CASH = "Cash"
    CHECK = "Check"
    CREDIT_CARD = "CreditCard"
    BANK_TRANSFER = "BankTransfer"
    OTHER = "Other"


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class Customer:
    """QuickBooks Customer entity."""

    id: str
    display_name: str
    sync_token: str  # Required for updates (optimistic locking)
    company_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    fax: str | None = None
    website: str | None = None
    balance: float | None = None
    billing_address: dict[str, Any] = field(default_factory=dict)
    shipping_address: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    taxable: bool | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """QuickBooks Invoice entity."""

    id: str
    doc_number: str | None  # Invoice number
    sync_token: str  # Required for updates
    customer_ref: dict[str, str]  # {"value": "customer_id", "name": "..."}
    line_items: list[dict[str, Any]] = field(default_factory=list)
    total_amount: float | None = None
    balance: float | None = None
    due_date: str | None = None
    txn_date: str | None = None  # Transaction date
    email_status: str | None = None
    billing_email: str | None = None
    ship_date: str | None = None
    tracking_num: str | None = None
    private_note: str | None = None
    customer_memo: str | None = None
    currency_ref: dict[str, str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Expense:
    """QuickBooks Purchase/Expense entity."""

    id: str
    sync_token: str  # Required for updates
    payment_type: str  # Cash, Check, CreditCard
    account_ref: dict[str, str]  # {"value": "account_id", "name": "..."}
    line_items: list[dict[str, Any]] = field(default_factory=list)
    total_amount: float | None = None
    txn_date: str | None = None
    entity_ref: dict[str, str] | None = None  # Vendor reference
    private_note: str | None = None
    doc_number: str | None = None
    currency_ref: dict[str, str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompanyInfo:
    """QuickBooks Company information."""

    id: str
    company_name: str
    sync_token: str
    legal_name: str | None = None
    company_addr: dict[str, Any] = field(default_factory=dict)
    customer_communication_addr: dict[str, Any] = field(default_factory=dict)
    legal_addr: dict[str, Any] = field(default_factory=dict)
    company_email: str | None = None
    company_phone: str | None = None
    fiscal_year_start_month: str | None = None
    country: str | None = None
    industry_type: str | None = None
    supported_languages: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenInfo:
    """OAuth2 token information."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds
    x_refresh_token_expires_in: int = 8726400  # ~100 days in seconds
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired (with 5-minute buffer)."""
        return time.time() > (self.created_at + self.expires_in - 300)

    @property
    def refresh_token_expires_at(self) -> float:
        """Get refresh token expiration timestamp."""
        return self.created_at + self.x_refresh_token_expires_in


# ============================================================================
# CLIENT
# ============================================================================


class QuickBooksClient(BaseIntegrationClient):
    """
    Async client for QuickBooks Online API v3.

    Supports full accounting operations including customer management,
    invoicing, expenses, and company information with OAuth2 authentication
    and automatic token refresh.

    Attributes:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        realm_id: QuickBooks company ID (realm ID)
        access_token: Current OAuth2 access token
        refresh_token: OAuth2 refresh token for obtaining new access tokens
        environment: "production" or "sandbox"
        minor_version: API minor version (default: 75)
    """

    # API endpoints
    PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
    SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company"
    TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        realm_id: str,
        access_token: str,
        refresh_token: str,
        environment: str = "production",
        minor_version: int = 75,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        auto_refresh: bool = True,
    ) -> None:
        """
        Initialize QuickBooks client.

        Args:
            client_id: OAuth2 client ID from Intuit developer portal
            client_secret: OAuth2 client secret
            realm_id: QuickBooks company ID (realm ID)
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token
            environment: "production" or "sandbox" (default: production)
            minor_version: API minor version (default: 75, minimum supported)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)
            auto_refresh: Automatically refresh expired tokens (default: True)

        Raises:
            ValueError: If required parameters are empty
            QuickBooksAuthError: If credentials are invalid
        """
        # Validate required parameters
        if not client_id or not client_id.strip():
            raise ValueError("client_id cannot be empty")
        if not client_secret or not client_secret.strip():
            raise ValueError("client_secret cannot be empty")
        if not realm_id or not realm_id.strip():
            raise ValueError("realm_id cannot be empty")
        if not access_token or not access_token.strip():
            raise ValueError("access_token cannot be empty")
        if not refresh_token or not refresh_token.strip():
            raise ValueError("refresh_token cannot be empty")

        # Validate environment
        if environment not in ("production", "sandbox"):
            raise ValueError("environment must be 'production' or 'sandbox'")

        # Select base URL based on environment
        base_url = (
            self.PRODUCTION_BASE_URL if environment == "production" else self.SANDBOX_BASE_URL
        )

        super().__init__(
            name="quickbooks",
            base_url=base_url,
            api_key=access_token,  # Used for Authorization header
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )

        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.realm_id = realm_id.strip()
        self.access_token = access_token.strip()
        self.refresh_token = refresh_token.strip()
        self.environment = environment
        self.minor_version = minor_version
        self.auto_refresh = auto_refresh

        # Token information
        self._token_info: TokenInfo | None = TokenInfo(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
        )

        # Async lock to prevent concurrent token refresh
        self._refresh_lock = asyncio.Lock()

        logger.info(
            f"Initialized QuickBooks client for realm {self.realm_id} "
            f"(environment: {self.environment}, version: {self.minor_version})"
        )

    def _get_headers(self) -> dict[str, str]:
        """
        Get request headers with OAuth2 bearer token.

        Returns:
            Dictionary with Authorization and Content-Type headers
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # Pattern to detect potentially dangerous query input
    # Note: Single quotes ARE allowed as QuickBooks uses them for string values
    # e.g., WHERE DisplayName = 'John Smith'
    _UNSAFE_QUERY_PATTERN = re.compile(
        r"(--|/\*|\*/|;\s*$|;\s*\w)"  # SQL comment/termination patterns
        r"|\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE)\b",  # Dangerous keywords
        re.IGNORECASE,
    )

    def _validate_query_clause(self, clause: str, clause_type: str) -> None:
        """
        Validate WHERE/ORDER BY clause for potentially dangerous input.

        QuickBooks uses JPQL-style queries (not SQL), but we still validate
        to prevent potential injection attacks.

        Args:
            clause: The clause to validate
            clause_type: "WHERE" or "ORDER BY" for error messages

        Raises:
            QuickBooksValidationError: If clause contains dangerous characters
        """
        if self._UNSAFE_QUERY_PATTERN.search(clause):
            raise QuickBooksValidationError(
                f"Invalid characters in {clause_type} clause. "
                f"Avoid SQL keywords and special characters like ; -- /* */"
            )

    def _get_endpoint(self, entity: str, entity_id: str | None = None) -> str:
        """
        Build API endpoint with realm ID and minor version.

        Args:
            entity: Entity type (e.g., "customer", "invoice")
            entity_id: Optional entity ID for specific operations

        Returns:
            Full endpoint path
        """
        base = f"/{self.realm_id}/{entity.lower()}"
        if entity_id:
            base = f"{base}/{entity_id}"
        return f"{base}?minorversion={self.minor_version}"

    async def _ensure_token_valid(self) -> None:
        """
        Check if access token is valid and refresh if needed.

        Raises:
            QuickBooksAuthError: If token refresh fails
        """
        if not self.auto_refresh:
            return

        if self._token_info and self._token_info.is_expired:
            logger.info("Access token expired, refreshing...")
            await self.refresh_access_token()

    async def refresh_access_token(self) -> TokenInfo:
        """
        Refresh the OAuth2 access token using the refresh token.

        Uses async locking to prevent concurrent refresh requests from
        multiple requests detecting token expiry at the same time.

        Returns:
            Updated TokenInfo with new access and refresh tokens

        Raises:
            QuickBooksAuthError: If token refresh fails
        """
        async with self._refresh_lock:
            # Check again after acquiring lock - another request may have refreshed
            if self._token_info and not self._token_info.is_expired:
                return self._token_info

            # Build Basic auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            basic_auth = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }

            try:
                response = await self.client.post(
                    self.TOKEN_ENDPOINT,
                    headers=headers,
                    data=data,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise QuickBooksAuthError(
                        message=f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}",
                        response_data=error_data,
                    )

                token_data = response.json()

                # Update tokens
                self.access_token = token_data["access_token"]
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                self.api_key = self.access_token  # Update base class api_key

                # Update token info
                self._token_info = TokenInfo(
                    access_token=self.access_token,
                    refresh_token=self.refresh_token,
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in", 3600),
                    x_refresh_token_expires_in=token_data.get(
                        "x_refresh_token_expires_in", 8726400
                    ),
                )

                logger.info("Successfully refreshed QuickBooks access token")
                return self._token_info

            except QuickBooksAuthError:
                raise
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                raise QuickBooksAuthError(f"Failed to refresh access token: {e}") from e

    async def _request_with_auth(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make authenticated request with automatic token refresh.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments

        Returns:
            API response data

        Raises:
            QuickBooksError: On API errors
        """
        await self._ensure_token_valid()

        try:
            if method.upper() == "GET":
                return await self.get(endpoint, **kwargs)
            elif method.upper() == "POST":
                return await self.post(endpoint, **kwargs)
            elif method.upper() == "DELETE":
                return await self.delete(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except AuthenticationError as e:
            # Try to refresh token once and retry
            if self.auto_refresh and "401" in str(e):
                logger.info("Got 401, attempting token refresh and retry...")
                await self.refresh_access_token()

                if method.upper() == "GET":
                    return await self.get(endpoint, **kwargs)
                elif method.upper() == "POST":
                    return await self.post(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    return await self.delete(endpoint, **kwargs)
            raise

    # ========================================================================
    # CUSTOMER OPERATIONS
    # ========================================================================

    async def create_customer(
        self,
        display_name: str,
        company_name: str | None = None,
        given_name: str | None = None,
        family_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        billing_address: dict[str, Any] | None = None,
        shipping_address: dict[str, Any] | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Customer:
        """
        Create a new customer.

        Args:
            display_name: Display name (required, must be unique)
            company_name: Company name
            given_name: First name
            family_name: Last name
            email: Primary email address
            phone: Primary phone number
            billing_address: Billing address dict with Line1, City, Country, etc.
            shipping_address: Shipping address dict
            notes: Internal notes
            **kwargs: Additional QuickBooks customer fields

        Returns:
            Created Customer object

        Raises:
            QuickBooksError: If customer creation fails
            QuickBooksValidationError: If required fields missing
        """
        data: dict[str, Any] = {
            "DisplayName": display_name,
        }

        if company_name:
            data["CompanyName"] = company_name
        if given_name:
            data["GivenName"] = given_name
        if family_name:
            data["FamilyName"] = family_name
        if email:
            data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if billing_address:
            data["BillAddr"] = billing_address
        if shipping_address:
            data["ShipAddr"] = shipping_address
        if notes:
            data["Notes"] = notes

        # Add any additional fields
        data.update(kwargs)

        try:
            endpoint = self._get_endpoint("customer")
            response = await self._request_with_auth("POST", endpoint, json=data)

            customer_data = response.get("Customer", response)
            customer = self._parse_customer(customer_data)

            logger.info(f"Created customer: {customer.id} - {customer.display_name}")
            return customer

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(f"Invalid customer data: {e}") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to create customer: {e}") from e

    async def get_customer(self, customer_id: str) -> Customer:
        """
        Retrieve a customer by ID.

        Args:
            customer_id: QuickBooks customer ID

        Returns:
            Customer object

        Raises:
            QuickBooksNotFoundError: If customer not found
            QuickBooksError: On other errors
        """
        try:
            endpoint = self._get_endpoint("customer", customer_id)
            response = await self._request_with_auth("GET", endpoint)

            customer_data = response.get("Customer", response)
            return self._parse_customer(customer_data)

        except IntegrationError as e:
            if e.status_code == 404:
                raise QuickBooksNotFoundError(f"Customer {customer_id} not found") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to get customer: {e}") from e

    async def update_customer(
        self,
        customer_id: str,
        sync_token: str,
        **kwargs: Any,
    ) -> Customer:
        """
        Update an existing customer.

        QuickBooks requires the SyncToken for optimistic locking.
        Get the current customer first to obtain the latest SyncToken.

        Args:
            customer_id: QuickBooks customer ID
            sync_token: Current SyncToken (required for concurrency control)
            **kwargs: Fields to update (DisplayName, Email, Phone, etc.)

        Returns:
            Updated Customer object

        Raises:
            QuickBooksError: If update fails
            QuickBooksValidationError: If sync token mismatch
        """
        data: dict[str, Any] = {
            "Id": customer_id,
            "SyncToken": sync_token,
            "sparse": True,  # Sparse update - only update provided fields
        }

        # Map common field names to QuickBooks format
        field_mapping = {
            "display_name": "DisplayName",
            "company_name": "CompanyName",
            "given_name": "GivenName",
            "family_name": "FamilyName",
            "email": "PrimaryEmailAddr",
            "phone": "PrimaryPhone",
            "notes": "Notes",
            "active": "Active",
        }

        for key, value in kwargs.items():
            qb_key = field_mapping.get(key, key)
            if key == "email" and value:
                data[qb_key] = {"Address": value}
            elif key == "phone" and value:
                data[qb_key] = {"FreeFormNumber": value}
            else:
                data[qb_key] = value

        try:
            endpoint = self._get_endpoint("customer")
            response = await self._request_with_auth("POST", endpoint, json=data)

            customer_data = response.get("Customer", response)
            customer = self._parse_customer(customer_data)

            logger.info(f"Updated customer: {customer.id}")
            return customer

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(
                    f"Invalid update data or stale sync token: {e}"
                ) from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to update customer: {e}") from e

    async def query_customers(
        self,
        where: str | None = None,
        order_by: str | None = None,
        start_position: int = 1,
        max_results: int = 100,
    ) -> list[Customer]:
        """
        Query customers using SQL-like syntax.

        Args:
            where: WHERE clause (e.g., "Active = true AND Balance > 0")
            order_by: ORDER BY clause (e.g., "DisplayName ASC")
            start_position: Starting position for pagination (1-based)
            max_results: Maximum results to return (max 1000)

        Returns:
            List of Customer objects matching query

        Raises:
            QuickBooksValidationError: If WHERE/ORDER BY clause contains dangerous input
            QuickBooksError: If query fails
        """
        # Validate input clauses for safety
        if where:
            self._validate_query_clause(where, "WHERE")
        if order_by:
            self._validate_query_clause(order_by, "ORDER BY")

        query = "SELECT * FROM Customer"

        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDERBY {order_by}"

        query += f" STARTPOSITION {start_position} MAXRESULTS {min(max_results, 1000)}"

        try:
            # URL encode the query to handle special characters (spaces, quotes, etc.)
            encoded_query = quote(query, safe="")
            endpoint = (
                f"/{self.realm_id}/query?minorversion={self.minor_version}&query={encoded_query}"
            )
            response = await self._request_with_auth("GET", endpoint)

            query_response = response.get("QueryResponse", {})
            customers_data = query_response.get("Customer", [])

            customers = [self._parse_customer(c) for c in customers_data]
            logger.info(f"Query returned {len(customers)} customers")
            return customers

        except IntegrationError as e:
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to query customers: {e}") from e

    # ========================================================================
    # INVOICE OPERATIONS
    # ========================================================================

    async def create_invoice(
        self,
        customer_id: str,
        line_items: list[dict[str, Any]],
        due_date: str | None = None,
        txn_date: str | None = None,
        doc_number: str | None = None,
        billing_email: str | None = None,
        private_note: str | None = None,
        customer_memo: str | None = None,
        **kwargs: Any,
    ) -> Invoice:
        """
        Create a new invoice.

        Args:
            customer_id: Customer ID (required)
            line_items: List of line item dicts, each containing:
                - Amount: decimal amount
                - Description: item description (optional)
                - DetailType: "SalesItemLineDetail" or "DescriptionOnly"
                - SalesItemLineDetail (optional): {"ItemRef": {"value": "item_id"}, "Qty": 1}
            due_date: Invoice due date (YYYY-MM-DD format)
            txn_date: Transaction date (YYYY-MM-DD format)
            doc_number: Invoice number (auto-generated if not provided)
            billing_email: Email address for invoice delivery
            private_note: Internal note (not visible to customer)
            customer_memo: Customer-facing memo
            **kwargs: Additional QuickBooks invoice fields

        Returns:
            Created Invoice object

        Raises:
            QuickBooksError: If invoice creation fails

        Example:
            >>> line_items = [
            ...     {
            ...         "Amount": 100.00,
            ...         "Description": "Consulting services",
            ...         "DetailType": "SalesItemLineDetail",
            ...         "SalesItemLineDetail": {
            ...             "ItemRef": {"value": "1"},
            ...             "Qty": 2,
            ...             "UnitPrice": 50.00
            ...         }
            ...     }
            ... ]
            >>> invoice = await client.create_invoice(
            ...     customer_id="123",
            ...     line_items=line_items,
            ...     due_date="2025-01-15"
            ... )
        """
        data: dict[str, Any] = {
            "CustomerRef": {"value": customer_id},
            "Line": line_items,
        }

        if due_date:
            data["DueDate"] = due_date
        if txn_date:
            data["TxnDate"] = txn_date
        if doc_number:
            data["DocNumber"] = doc_number
        if billing_email:
            data["BillEmail"] = {"Address": billing_email}
        if private_note:
            data["PrivateNote"] = private_note
        if customer_memo:
            data["CustomerMemo"] = {"value": customer_memo}

        data.update(kwargs)

        try:
            endpoint = self._get_endpoint("invoice")
            response = await self._request_with_auth("POST", endpoint, json=data)

            invoice_data = response.get("Invoice", response)
            invoice = self._parse_invoice(invoice_data)

            logger.info(f"Created invoice: {invoice.id} - ${invoice.total_amount}")
            return invoice

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(f"Invalid invoice data: {e}") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to create invoice: {e}") from e

    async def get_invoice(self, invoice_id: str) -> Invoice:
        """
        Retrieve an invoice by ID.

        Args:
            invoice_id: QuickBooks invoice ID

        Returns:
            Invoice object

        Raises:
            QuickBooksNotFoundError: If invoice not found
            QuickBooksError: On other errors
        """
        try:
            endpoint = self._get_endpoint("invoice", invoice_id)
            response = await self._request_with_auth("GET", endpoint)

            invoice_data = response.get("Invoice", response)
            return self._parse_invoice(invoice_data)

        except IntegrationError as e:
            if e.status_code == 404:
                raise QuickBooksNotFoundError(f"Invoice {invoice_id} not found") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to get invoice: {e}") from e

    async def update_invoice(
        self,
        invoice_id: str,
        sync_token: str,
        **kwargs: Any,
    ) -> Invoice:
        """
        Update an existing invoice.

        Args:
            invoice_id: QuickBooks invoice ID
            sync_token: Current SyncToken (required)
            **kwargs: Fields to update

        Returns:
            Updated Invoice object

        Raises:
            QuickBooksError: If update fails
        """
        data: dict[str, Any] = {
            "Id": invoice_id,
            "SyncToken": sync_token,
            "sparse": True,
        }

        field_mapping = {
            "due_date": "DueDate",
            "txn_date": "TxnDate",
            "doc_number": "DocNumber",
            "private_note": "PrivateNote",
            "customer_memo": "CustomerMemo",
            "line_items": "Line",
        }

        for key, value in kwargs.items():
            qb_key = field_mapping.get(key, key)
            if key == "billing_email" and value:
                data["BillEmail"] = {"Address": value}
            elif key == "customer_memo" and value:
                data["CustomerMemo"] = {"value": value}
            else:
                data[qb_key] = value

        try:
            endpoint = self._get_endpoint("invoice")
            response = await self._request_with_auth("POST", endpoint, json=data)

            invoice_data = response.get("Invoice", response)
            invoice = self._parse_invoice(invoice_data)

            logger.info(f"Updated invoice: {invoice.id}")
            return invoice

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(f"Invalid update data: {e}") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to update invoice: {e}") from e

    async def query_invoices(
        self,
        where: str | None = None,
        order_by: str | None = None,
        start_position: int = 1,
        max_results: int = 100,
    ) -> list[Invoice]:
        """
        Query invoices using SQL-like syntax.

        Args:
            where: WHERE clause (e.g., "TotalAmt > '1000.00'")
            order_by: ORDER BY clause (e.g., "TxnDate DESC")
            start_position: Starting position (1-based)
            max_results: Maximum results (max 1000)

        Returns:
            List of Invoice objects

        Raises:
            QuickBooksValidationError: If WHERE/ORDER BY clause contains dangerous input
            QuickBooksError: If query fails
        """
        # Validate input clauses for safety
        if where:
            self._validate_query_clause(where, "WHERE")
        if order_by:
            self._validate_query_clause(order_by, "ORDER BY")

        query = "SELECT * FROM Invoice"

        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDERBY {order_by}"

        query += f" STARTPOSITION {start_position} MAXRESULTS {min(max_results, 1000)}"

        try:
            # URL encode the query to handle special characters
            encoded_query = quote(query, safe="")
            endpoint = (
                f"/{self.realm_id}/query?minorversion={self.minor_version}&query={encoded_query}"
            )
            response = await self._request_with_auth("GET", endpoint)

            query_response = response.get("QueryResponse", {})
            invoices_data = query_response.get("Invoice", [])

            invoices = [self._parse_invoice(i) for i in invoices_data]
            logger.info(f"Query returned {len(invoices)} invoices")
            return invoices

        except IntegrationError as e:
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to query invoices: {e}") from e

    async def send_invoice(
        self,
        invoice_id: str,
        email: str | None = None,
    ) -> Invoice:
        """
        Send invoice via email.

        Args:
            invoice_id: Invoice ID to send
            email: Override email address (uses customer email if not provided)

        Returns:
            Updated Invoice object

        Raises:
            QuickBooksError: If send fails
        """
        try:
            endpoint = (
                f"/{self.realm_id}/invoice/{invoice_id}/send?minorversion={self.minor_version}"
            )
            if email:
                endpoint += f"&sendTo={email}"

            response = await self._request_with_auth("POST", endpoint)

            invoice_data = response.get("Invoice", response)
            invoice = self._parse_invoice(invoice_data)

            logger.info(f"Sent invoice {invoice_id} to {email or 'customer email'}")
            return invoice

        except IntegrationError as e:
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to send invoice: {e}") from e

    # ========================================================================
    # EXPENSE/PURCHASE OPERATIONS
    # ========================================================================

    async def create_expense(
        self,
        account_id: str,
        payment_type: str,
        line_items: list[dict[str, Any]],
        txn_date: str | None = None,
        vendor_id: str | None = None,
        doc_number: str | None = None,
        private_note: str | None = None,
        **kwargs: Any,
    ) -> Expense:
        """
        Create a new expense/purchase.

        Args:
            account_id: Payment account ID (e.g., bank account)
            payment_type: "Cash", "Check", or "CreditCard"
            line_items: List of expense line items:
                - Amount: decimal amount
                - Description: expense description
                - DetailType: "AccountBasedExpenseLineDetail"
                - AccountBasedExpenseLineDetail: {"AccountRef": {"value": "expense_account_id"}}
            txn_date: Transaction date (YYYY-MM-DD)
            vendor_id: Vendor/supplier ID
            doc_number: Reference number
            private_note: Internal note
            **kwargs: Additional fields

        Returns:
            Created Expense object

        Raises:
            QuickBooksError: If expense creation fails
        """
        data: dict[str, Any] = {
            "AccountRef": {"value": account_id},
            "PaymentType": payment_type,
            "Line": line_items,
        }

        if txn_date:
            data["TxnDate"] = txn_date
        if vendor_id:
            data["EntityRef"] = {"value": vendor_id, "type": "Vendor"}
        if doc_number:
            data["DocNumber"] = doc_number
        if private_note:
            data["PrivateNote"] = private_note

        data.update(kwargs)

        try:
            endpoint = self._get_endpoint("purchase")
            response = await self._request_with_auth("POST", endpoint, json=data)

            expense_data = response.get("Purchase", response)
            expense = self._parse_expense(expense_data)

            logger.info(f"Created expense: {expense.id} - ${expense.total_amount}")
            return expense

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(f"Invalid expense data: {e}") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to create expense: {e}") from e

    async def get_expense(self, expense_id: str) -> Expense:
        """
        Retrieve an expense/purchase by ID.

        Args:
            expense_id: QuickBooks purchase ID

        Returns:
            Expense object

        Raises:
            QuickBooksNotFoundError: If expense not found
            QuickBooksError: On other errors
        """
        try:
            endpoint = self._get_endpoint("purchase", expense_id)
            response = await self._request_with_auth("GET", endpoint)

            expense_data = response.get("Purchase", response)
            return self._parse_expense(expense_data)

        except IntegrationError as e:
            if e.status_code == 404:
                raise QuickBooksNotFoundError(f"Expense {expense_id} not found") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to get expense: {e}") from e

    async def update_expense(
        self,
        expense_id: str,
        sync_token: str,
        **kwargs: Any,
    ) -> Expense:
        """
        Update an existing expense/purchase.

        Args:
            expense_id: QuickBooks purchase ID
            sync_token: Current SyncToken (required)
            **kwargs: Fields to update

        Returns:
            Updated Expense object

        Raises:
            QuickBooksError: If update fails
        """
        data: dict[str, Any] = {
            "Id": expense_id,
            "SyncToken": sync_token,
            "sparse": True,
        }

        field_mapping = {
            "txn_date": "TxnDate",
            "doc_number": "DocNumber",
            "private_note": "PrivateNote",
            "line_items": "Line",
            "payment_type": "PaymentType",
        }

        for key, value in kwargs.items():
            qb_key = field_mapping.get(key, key)
            data[qb_key] = value

        try:
            endpoint = self._get_endpoint("purchase")
            response = await self._request_with_auth("POST", endpoint, json=data)

            expense_data = response.get("Purchase", response)
            expense = self._parse_expense(expense_data)

            logger.info(f"Updated expense: {expense.id}")
            return expense

        except IntegrationError as e:
            if e.status_code == 400:
                raise QuickBooksValidationError(f"Invalid update data: {e}") from e
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to update expense: {e}") from e

    async def query_expenses(
        self,
        where: str | None = None,
        order_by: str | None = None,
        start_position: int = 1,
        max_results: int = 100,
    ) -> list[Expense]:
        """
        Query expenses/purchases using SQL-like syntax.

        Args:
            where: WHERE clause
            order_by: ORDER BY clause
            start_position: Starting position (1-based)
            max_results: Maximum results (max 1000)

        Returns:
            List of Expense objects

        Raises:
            QuickBooksValidationError: If WHERE/ORDER BY clause contains dangerous input
            QuickBooksError: If query fails
        """
        # Validate input clauses for safety
        if where:
            self._validate_query_clause(where, "WHERE")
        if order_by:
            self._validate_query_clause(order_by, "ORDER BY")

        query = "SELECT * FROM Purchase"

        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDERBY {order_by}"

        query += f" STARTPOSITION {start_position} MAXRESULTS {min(max_results, 1000)}"

        try:
            # URL encode the query to handle special characters
            encoded_query = quote(query, safe="")
            endpoint = (
                f"/{self.realm_id}/query?minorversion={self.minor_version}&query={encoded_query}"
            )
            response = await self._request_with_auth("GET", endpoint)

            query_response = response.get("QueryResponse", {})
            expenses_data = query_response.get("Purchase", [])

            expenses = [self._parse_expense(e) for e in expenses_data]
            logger.info(f"Query returned {len(expenses)} expenses")
            return expenses

        except IntegrationError as e:
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to query expenses: {e}") from e

    # ========================================================================
    # COMPANY OPERATIONS
    # ========================================================================

    async def get_company_info(self) -> CompanyInfo:
        """
        Retrieve company information for the connected QuickBooks account.

        Returns:
            CompanyInfo object with company details

        Raises:
            QuickBooksError: If retrieval fails
        """
        try:
            endpoint = self._get_endpoint("companyinfo", self.realm_id)
            response = await self._request_with_auth("GET", endpoint)

            company_data = response.get("CompanyInfo", response)
            return self._parse_company_info(company_data)

        except IntegrationError as e:
            if e.status_code == 429:
                raise QuickBooksRateLimitError(str(e)) from e
            raise QuickBooksError(f"Failed to get company info: {e}") from e

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling endpoints that may be released in the future
        without requiring code changes to the client.

        Args:
            endpoint: Endpoint path (e.g., "/estimate", "/payment/123")
            method: HTTP method (GET, POST, DELETE)
            **kwargs: Request parameters (json, params, etc.)

        Returns:
            API response as dictionary

        Example:
            >>> result = await client.call_endpoint(
            ...     "/estimate",
            ...     method="POST",
            ...     json={"CustomerRef": {"value": "123"}, ...}
            ... )
        """
        # Ensure endpoint has realm ID
        if not endpoint.startswith(f"/{self.realm_id}"):
            endpoint = f"/{self.realm_id}{endpoint}"

        # Add minor version if not present
        if "minorversion" not in endpoint:
            separator = "&" if "?" in endpoint else "?"
            endpoint += f"{separator}minorversion={self.minor_version}"

        try:
            return await self._request_with_auth(method, endpoint, **kwargs)
        except IntegrationError as e:
            logger.error(f"API call to {endpoint} failed: {e}")
            raise QuickBooksError(f"Failed to call endpoint {endpoint}: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check integration health/connectivity.

        Returns:
            Health check response with status

        Raises:
            QuickBooksError: If health check fails
        """
        try:
            company = await self.get_company_info()
            return {
                "name": self.name,
                "healthy": True,
                "message": f"QuickBooks '{company.company_name}' is online",
                "realm_id": self.realm_id,
                "company_name": company.company_name,
                "environment": self.environment,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "message": f"Health check failed: {e}",
                "realm_id": self.realm_id,
                "environment": self.environment,
                "error": str(e),
            }

    # ========================================================================
    # PARSING HELPERS
    # ========================================================================

    def _parse_customer(self, data: dict[str, Any]) -> Customer:
        """Parse API response into Customer object."""
        return Customer(
            id=str(data.get("Id", "")),
            display_name=data.get("DisplayName", ""),
            sync_token=data.get("SyncToken", "0"),
            company_name=data.get("CompanyName"),
            given_name=data.get("GivenName"),
            family_name=data.get("FamilyName"),
            email=data.get("PrimaryEmailAddr", {}).get("Address"),
            phone=data.get("PrimaryPhone", {}).get("FreeFormNumber"),
            mobile=data.get("Mobile", {}).get("FreeFormNumber"),
            fax=data.get("Fax", {}).get("FreeFormNumber"),
            website=data.get("WebAddr", {}).get("URI"),
            balance=data.get("Balance"),
            billing_address=data.get("BillAddr", {}),
            shipping_address=data.get("ShipAddr", {}),
            active=data.get("Active", True),
            taxable=data.get("Taxable"),
            notes=data.get("Notes"),
            created_at=data.get("MetaData", {}).get("CreateTime"),
            updated_at=data.get("MetaData", {}).get("LastUpdatedTime"),
            raw=data,
        )

    def _parse_invoice(self, data: dict[str, Any]) -> Invoice:
        """Parse API response into Invoice object."""
        return Invoice(
            id=str(data.get("Id", "")),
            doc_number=data.get("DocNumber"),
            sync_token=data.get("SyncToken", "0"),
            customer_ref=data.get("CustomerRef", {}),
            line_items=data.get("Line", []),
            total_amount=data.get("TotalAmt"),
            balance=data.get("Balance"),
            due_date=data.get("DueDate"),
            txn_date=data.get("TxnDate"),
            email_status=data.get("EmailStatus"),
            billing_email=data.get("BillEmail", {}).get("Address"),
            ship_date=data.get("ShipDate"),
            tracking_num=data.get("TrackingNum"),
            private_note=data.get("PrivateNote"),
            customer_memo=data.get("CustomerMemo", {}).get("value"),
            currency_ref=data.get("CurrencyRef"),
            created_at=data.get("MetaData", {}).get("CreateTime"),
            updated_at=data.get("MetaData", {}).get("LastUpdatedTime"),
            raw=data,
        )

    def _parse_expense(self, data: dict[str, Any]) -> Expense:
        """Parse API response into Expense object."""
        return Expense(
            id=str(data.get("Id", "")),
            sync_token=data.get("SyncToken", "0"),
            payment_type=data.get("PaymentType", ""),
            account_ref=data.get("AccountRef", {}),
            line_items=data.get("Line", []),
            total_amount=data.get("TotalAmt"),
            txn_date=data.get("TxnDate"),
            entity_ref=data.get("EntityRef"),
            private_note=data.get("PrivateNote"),
            doc_number=data.get("DocNumber"),
            currency_ref=data.get("CurrencyRef"),
            created_at=data.get("MetaData", {}).get("CreateTime"),
            updated_at=data.get("MetaData", {}).get("LastUpdatedTime"),
            raw=data,
        )

    def _parse_company_info(self, data: dict[str, Any]) -> CompanyInfo:
        """Parse API response into CompanyInfo object."""
        return CompanyInfo(
            id=str(data.get("Id", "")),
            company_name=data.get("CompanyName", ""),
            sync_token=data.get("SyncToken", "0"),
            legal_name=data.get("LegalName"),
            company_addr=data.get("CompanyAddr", {}),
            customer_communication_addr=data.get("CustomerCommunicationAddr", {}),
            legal_addr=data.get("LegalAddr", {}),
            company_email=data.get("Email", {}).get("Address"),
            company_phone=data.get("PrimaryPhone", {}).get("FreeFormNumber"),
            fiscal_year_start_month=data.get("FiscalYearStartMonth"),
            country=data.get("Country"),
            industry_type=data.get("IndustryType"),
            supported_languages=data.get("SupportedLanguages", "").split(",")
            if data.get("SupportedLanguages")
            else [],
            raw=data,
        )
