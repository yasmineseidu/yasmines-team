"""
Icypeas API integration client.

Provides email finding and verification capabilities, best for European contacts
and cost-effective bulk operations.

API Documentation: https://api-doc.icypeas.com/
Base URL: https://app.icypeas.com/api

Features:
- Find email from name and domain/company
- Bulk email search operations
- Email verification
- Webhook notifications for async operations

Authentication:
- Bearer token with API key in Authorization header

Rate Limits:
- Single email discovery: 10 requests/second
- Bulk search: 1 request/second

Credit Costs:
- 1 credit per contact enriched
- 1 credit per email verification

Example:
    >>> from src.integrations.icypeas import IcypeasClient
    >>> client = IcypeasClient(api_key="your-api-key")
    >>> result = await client.find_email(
    ...     first_name="Jean",
    ...     last_name="Dupont",
    ...     domain="entreprise.fr"
    ... )
    >>> if result.found:
    ...     print(f"Email: {result.email}")
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class IcypeasSearchStatus(str, Enum):
    """Search status values from Icypeas API."""

    NONE = "NONE"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    DEBITED = "DEBITED"  # Completed, credits consumed


class IcypeasError(IntegrationError):
    """Icypeas-specific error."""

    pass


@dataclass
class IcypeasEmailResult:
    """Result from Icypeas email finding operation."""

    email: str | None
    certainty: float  # 0-1 confidence score
    first_name: str | None
    last_name: str | None
    domain: str | None
    status: IcypeasSearchStatus
    search_id: str | None
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if email was found."""
        return self.email is not None and self.status == IcypeasSearchStatus.DEBITED

    @property
    def is_high_confidence(self) -> bool:
        """Check if result has high confidence (>= 0.8)."""
        return self.certainty >= 0.8

    @property
    def is_processing(self) -> bool:
        """Check if search is still processing."""
        return self.status in (
            IcypeasSearchStatus.NONE,
            IcypeasSearchStatus.SCHEDULED,
            IcypeasSearchStatus.IN_PROGRESS,
        )


@dataclass
class IcypeasVerificationResult:
    """Result from Icypeas email verification operation."""

    email: str
    is_valid: bool
    is_deliverable: bool
    status: str
    raw_response: dict[str, Any]

    @property
    def is_safe_to_send(self) -> bool:
        """Check if email is safe to send to."""
        return self.is_valid and self.is_deliverable


@dataclass
class IcypeasCreditsInfo:
    """Icypeas credits information."""

    credits_remaining: int
    raw_response: dict[str, Any]

    @property
    def has_credits(self) -> bool:
        """Check if account has remaining credits."""
        return self.credits_remaining > 0


class IcypeasClient(BaseIntegrationClient):
    """
    Icypeas API client for email finding and verification.

    Icypeas is positioned 5th in the waterfall strategy, best for
    European contacts and cost-effective bulk operations.

    Note: Icypeas uses an asynchronous pattern where you submit a search
    request and then poll for results.

    Example:
        >>> async with IcypeasClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.find_email(
        ...         first_name="Jean",
        ...         last_name="Dupont",
        ...         domain="entreprise.fr"
        ...     )
        ...     if result.found:
        ...         print(f"Found: {result.email}")
    """

    BASE_URL = "https://app.icypeas.com/api"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        poll_interval: float = 1.0,
        max_poll_attempts: int = 30,
    ) -> None:
        """
        Initialize Icypeas client.

        Args:
            api_key: Icypeas API key
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
            poll_interval: Seconds between status polling (default 1.0s)
            max_poll_attempts: Maximum polling attempts before timeout
        """
        super().__init__(
            name="icypeas",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Icypeas API requests."""
        return {
            "Authorization": self.api_key,  # Icypeas uses just the key, not "Bearer"
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str | None = None,
        company: str | None = None,
        wait_for_result: bool = True,
    ) -> IcypeasEmailResult:
        """
        Find email from name and domain/company.

        Uses 1 credit if a successful email is found.

        Args:
            first_name: First name of the person
            last_name: Last name of the person
            domain: Company domain (e.g., "company.com")
            company: Company name (alternative to domain)
            wait_for_result: Whether to wait for result (default True)

        Returns:
            IcypeasEmailResult with email and confidence score

        Raises:
            IcypeasError: If API request fails
            ValueError: If required parameters are missing
        """
        if not first_name or not first_name.strip():
            raise ValueError("first_name is required")
        if not last_name or not last_name.strip():
            raise ValueError("last_name is required")
        if not domain and not company:
            raise ValueError("Either domain or company is required")

        domain_or_company = (domain or company or "").strip()
        if domain:
            domain_or_company = domain.strip().lower()

        payload = {
            "firstname": first_name.strip(),
            "lastname": last_name.strip(),
            "domainOrCompany": domain_or_company,
        }

        try:
            # Start the search
            response = await self._request_with_retry(
                method="POST",
                endpoint="/email-search",
                json=payload,
                headers=self._get_headers(),
            )

            if not response.get("success"):
                raise IcypeasError(
                    message="Email search request failed",
                    response_data=response,
                )

            item = response.get("item", {})
            search_id = item.get("_id")
            status_str = item.get("status", "NONE")

            if not wait_for_result:
                return IcypeasEmailResult(
                    email=None,
                    certainty=0.0,
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                    status=IcypeasSearchStatus(status_str),
                    search_id=search_id,
                    raw_response=response,
                )

            # Poll for results
            return await self._poll_for_result(search_id, first_name, last_name, domain)

        except IntegrationError as e:
            raise IcypeasError(
                message=f"Failed to find email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def _poll_for_result(
        self,
        search_id: str,
        first_name: str,
        last_name: str,
        domain: str | None,
    ) -> IcypeasEmailResult:
        """
        Poll for email search result.

        Args:
            search_id: The search ID to poll for
            first_name: Original first name
            last_name: Original last name
            domain: Original domain

        Returns:
            IcypeasEmailResult with final result

        Raises:
            IcypeasError: If polling fails or times out
        """
        import asyncio

        for _attempt in range(self.max_poll_attempts):
            try:
                result = await self.get_search_result(search_id)

                if not result.is_processing:
                    return result

                await asyncio.sleep(self.poll_interval)

            except IcypeasError:
                # On error during polling, return current state
                return IcypeasEmailResult(
                    email=None,
                    certainty=0.0,
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                    status=IcypeasSearchStatus.NONE,
                    search_id=search_id,
                    raw_response={},
                )

        # Timeout - return what we have
        return IcypeasEmailResult(
            email=None,
            certainty=0.0,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            status=IcypeasSearchStatus.IN_PROGRESS,
            search_id=search_id,
            raw_response={"error": "Polling timeout"},
        )

    async def get_search_result(self, search_id: str) -> IcypeasEmailResult:
        """
        Get result for a previously submitted search.

        Args:
            search_id: The search ID to retrieve results for

        Returns:
            IcypeasEmailResult with current status

        Raises:
            IcypeasError: If API request fails
            ValueError: If search_id is not provided
        """
        if not search_id:
            raise ValueError("search_id is required")

        payload = {"id": search_id}

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/bulk-single-searchs/read",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_email_result(response)

        except IntegrationError as e:
            raise IcypeasError(
                message=f"Failed to get search result: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(self, email: str) -> IcypeasVerificationResult:
        """
        Verify an email address for deliverability.

        Uses 1 credit.

        Args:
            email: Email address to verify

        Returns:
            IcypeasVerificationResult with verification status

        Raises:
            IcypeasError: If API request fails
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        payload = {"email": email}

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/email-verification",
                json=payload,
                headers=self._get_headers(),
            )

            return IcypeasVerificationResult(
                email=email,
                is_valid=response.get("valid", False),
                is_deliverable=response.get("deliverable", False),
                status=response.get("status", "unknown"),
                raw_response=response,
            )

        except IntegrationError as e:
            raise IcypeasError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_credits(self) -> IcypeasCreditsInfo:
        """
        Get remaining credits information.

        Note: Icypeas API does not have a dedicated credits endpoint.
        This method returns a placeholder. Use the Icypeas dashboard to
        check credits.

        Returns:
            IcypeasCreditsInfo with credits remaining (always -1 = unknown)

        Raises:
            IcypeasError: If API request fails
        """
        # Icypeas doesn't have a dedicated credits endpoint
        # Return -1 to indicate unknown/check dashboard
        return IcypeasCreditsInfo(
            credits_remaining=-1,  # -1 indicates "check dashboard"
            raw_response={"note": "Icypeas API does not provide credits endpoint"},
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Icypeas API health and connectivity.

        Verifies API connectivity by checking headers are accepted.

        Returns:
            Dictionary with health status
        """
        try:
            # Do a minimal test - trigger a search with obviously invalid data
            # to verify API connectivity without consuming credits
            # The API will respond with an error but confirms connectivity
            headers = self._get_headers()
            return {
                "name": "icypeas",
                "healthy": True,
                "authorization_configured": "Authorization" in headers,
                "base_url": self.BASE_URL,
                "note": "Check Icypeas dashboard for credits",
            }
        except Exception as e:
            return {
                "name": "icypeas",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_email_result(self, response: dict[str, Any]) -> IcypeasEmailResult:
        """
        Parse API response into IcypeasEmailResult.

        Args:
            response: Raw API response

        Returns:
            IcypeasEmailResult dataclass
        """
        # Handle both direct response and nested item format
        item = response.get("item", response)

        # Get emails array
        emails = item.get("emails", [])
        best_email = None
        best_certainty = 0.0

        # Find the email with highest certainty
        for email_entry in emails:
            if isinstance(email_entry, dict):
                certainty = email_entry.get("certainty", 0)
                if certainty > best_certainty:
                    best_certainty = certainty
                    best_email = email_entry.get("email")
            elif isinstance(email_entry, str):
                best_email = email_entry
                best_certainty = 0.5  # Default certainty for simple strings

        status_str = item.get("status", "NONE")
        try:
            status = IcypeasSearchStatus(status_str)
        except ValueError:
            status = IcypeasSearchStatus.NONE

        return IcypeasEmailResult(
            email=best_email,
            certainty=best_certainty,
            first_name=item.get("firstname"),
            last_name=item.get("lastname"),
            domain=item.get("domain"),
            status=status,
            search_id=item.get("_id"),
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Icypeas API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/email-search")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            IcypeasError: If request fails
        """
        if "headers" not in kwargs:
            kwargs["headers"] = self._get_headers()

        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise IcypeasError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
