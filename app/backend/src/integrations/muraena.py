"""
Muraena API integration client.

Provides B2B lead discovery and email verification capabilities
from Muraena's 720M+ individual database.

API Documentation: https://muraena.readme.io/reference/
Base URL: https://contacts.muraena.ai

Features:
- Lead search with filters
- Contact detail reveal (email, phone)
- Email verification
- Company information lookup

Authentication:
- API key in X-API-Key header

Pricing:
- Business plan required ($149+/month)
- 1 credit per profile with revealed contact details

Example:
    >>> from src.integrations.muraena import MuraenaClient
    >>> client = MuraenaClient(api_key="your-api-key")
    >>> result = await client.find_contact(
    ...     first_name="John",
    ...     last_name="Smith",
    ...     company="Tech Corp"
    ... )
    >>> if result.found:
    ...     print(f"Email: {result.email}")
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class MuraenaError(IntegrationError):
    """Muraena-specific error."""

    pass


@dataclass
class MuraenaContactResult:
    """Result from Muraena contact finding operation."""

    email: str | None
    phone: str | None
    first_name: str | None
    last_name: str | None
    title: str | None
    company: str | None
    linkedin_url: str | None
    is_verified: bool
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if contact was found with email."""
        return self.email is not None

    @property
    def has_phone(self) -> bool:
        """Check if phone number is available."""
        return self.phone is not None


@dataclass
class MuraenaVerificationResult:
    """Result from Muraena email verification operation."""

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
class MuraenaCreditsInfo:
    """Muraena credits information."""

    credits_remaining: int
    plan_name: str | None
    raw_response: dict[str, Any]

    @property
    def has_credits(self) -> bool:
        """Check if account has remaining credits."""
        return self.credits_remaining > 0


class MuraenaClient(BaseIntegrationClient):
    """
    Muraena API client for B2B lead discovery and email verification.

    Muraena is positioned 6th in the waterfall strategy, providing access
    to a large database of 720M+ individuals with verified emails.

    Example:
        >>> async with MuraenaClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.find_contact(
        ...         first_name="John",
        ...         last_name="Smith",
        ...         company="Tech Corp"
        ...     )
        ...     if result.found:
        ...         print(f"Found: {result.email}")
    """

    BASE_URL = "https://contacts.muraena.ai"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Muraena client.

        Args:
            api_key: Muraena API key (requires Business plan)
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="muraena",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Muraena API requests."""
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def find_contact(
        self,
        first_name: str,
        last_name: str,
        company: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
    ) -> MuraenaContactResult:
        """
        Find contact details from name and company/domain.

        Uses 1 credit if contact details are revealed.

        Args:
            first_name: First name of the person
            last_name: Last name of the person
            company: Company name
            domain: Company domain (alternative to company)
            linkedin_url: LinkedIn profile URL

        Returns:
            MuraenaContactResult with contact details

        Raises:
            MuraenaError: If API request fails
            ValueError: If required parameters are missing
        """
        if not first_name or not first_name.strip():
            raise ValueError("first_name is required")
        if not last_name or not last_name.strip():
            raise ValueError("last_name is required")
        if not company and not domain and not linkedin_url:
            raise ValueError("Either company, domain, or linkedin_url is required")

        # Build search filters
        filters: dict[str, Any] = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
        }

        if company:
            filters["company"] = company.strip()
        if domain:
            filters["domain"] = domain.strip().lower()
        if linkedin_url:
            filters["linkedin_url"] = linkedin_url.strip()

        payload = {"filters": filters, "reveal": True}

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/api/client_api/search/",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_contact_result(response)

        except IntegrationError as e:
            raise MuraenaError(
                message=f"Failed to find contact: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_by_linkedin(
        self,
        linkedin_url: str,
    ) -> MuraenaContactResult:
        """
        Find contact details from LinkedIn profile URL.

        Uses 1 credit if contact details are revealed.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            MuraenaContactResult with contact details

        Raises:
            MuraenaError: If API request fails
            ValueError: If LinkedIn URL is invalid
        """
        if not linkedin_url or not linkedin_url.strip():
            raise ValueError("linkedin_url is required")

        url = linkedin_url.strip()
        if "linkedin.com" not in url.lower():
            raise ValueError("Invalid LinkedIn URL")

        # Muraena uses reveal endpoint with linkedin_url as a query param
        params = {"linkedin_url": url}

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/api/client_api/reveal/",
                params=params,
                headers=self._get_headers(),
            )

            return self._parse_contact_result(response)

        except IntegrationError as e:
            raise MuraenaError(
                message=f"Failed to search by LinkedIn: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(self, email: str) -> MuraenaVerificationResult:
        """
        Verify an email address by looking it up in Muraena's database.

        Note: Muraena doesn't have a standalone email verification endpoint.
        This uses the reveal endpoint with email as input to check if the
        email exists in their database. Uses 1 credit if contact is found.

        Args:
            email: Email address to verify

        Returns:
            MuraenaVerificationResult with verification status

        Raises:
            MuraenaError: If API request fails
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        # Use reveal endpoint with email parameter
        params = {"email": email}

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/api/client_api/reveal/",
                params=params,
                headers=self._get_headers(),
            )

            # If we get a successful response with email, it's valid in Muraena's database
            found_email = response.get("email")
            is_verified = response.get("email_verified", False)

            return MuraenaVerificationResult(
                email=email,
                is_valid=found_email is not None,
                is_deliverable=is_verified,
                status="found" if found_email else "not_found",
                raw_response=response,
            )

        except IntegrationError as e:
            # If 404 or similar, email not found but that's not an error
            if e.status_code == 404:
                return MuraenaVerificationResult(
                    email=email,
                    is_valid=False,
                    is_deliverable=False,
                    status="not_found",
                    raw_response=e.response_data or {},
                )
            raise MuraenaError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_credits(self) -> MuraenaCreditsInfo:
        """
        Get remaining credits information.

        Returns:
            MuraenaCreditsInfo with credits remaining

        Raises:
            MuraenaError: If API request fails
        """
        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/user/client_api/balance/",
                headers=self._get_headers(),
            )

            return MuraenaCreditsInfo(
                credits_remaining=response.get("balance", response.get("credits", 0)),
                plan_name=response.get("plan"),
                raw_response=response,
            )

        except IntegrationError as e:
            raise MuraenaError(
                message=f"Failed to get credits: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Muraena API health and connectivity.

        Returns:
            Dictionary with health status

        Raises:
            MuraenaError: If health check fails
        """
        try:
            credits = await self.get_credits()
            return {
                "name": "muraena",
                "healthy": True,
                "credits_remaining": credits.credits_remaining,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "muraena",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_contact_result(self, response: dict[str, Any]) -> MuraenaContactResult:
        """
        Parse API response into MuraenaContactResult.

        Args:
            response: Raw API response

        Returns:
            MuraenaContactResult dataclass
        """
        # Handle results array or single result
        results = response.get("results", [response])
        if not results:
            return MuraenaContactResult(
                email=None,
                phone=None,
                first_name=None,
                last_name=None,
                title=None,
                company=None,
                linkedin_url=None,
                is_verified=False,
                raw_response=response,
            )

        # Take the first/best result
        contact = results[0] if isinstance(results, list) else results

        return MuraenaContactResult(
            email=contact.get("email"),
            phone=contact.get("phone") or contact.get("mobile"),
            first_name=contact.get("first_name"),
            last_name=contact.get("last_name"),
            title=contact.get("title") or contact.get("job_title"),
            company=contact.get("company") or contact.get("company_name"),
            linkedin_url=contact.get("linkedin_url"),
            is_verified=contact.get("email_verified", False),
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Muraena API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            MuraenaError: If request fails
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
            raise MuraenaError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
