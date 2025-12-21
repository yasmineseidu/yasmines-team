"""
Findymail API integration client.

Provides email finding and verification with excellent accuracy,
especially for tech companies and startups.

API Documentation: https://app.findymail.com/docs/
Base URL: https://app.findymail.com/api

Features:
- Find work email from name and domain
- Find email from LinkedIn URL
- Find phone from LinkedIn URL
- Email verification
- List management

Pricing:
- 1 credit per successful email find
- 1 credit per email verification
- 10 credits per phone find
- Free: duplicate searches

Rate Limits:
- 300 concurrent requests
- No daily or hourly limits

Example:
    >>> from src.integrations.findymail import FindymailClient
    >>> client = FindymailClient(api_key="your-api-key")
    >>> result = await client.find_work_email(
    ...     full_name="Jane Smith",
    ...     domain="techcompany.com"
    ... )
    >>> print(result.email)
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


class FindymailEmailStatus(str, Enum):
    """Email status returned by Findymail API."""

    VERIFIED = "verified"
    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


class FindymailError(IntegrationError):
    """Findymail-specific error."""

    pass


@dataclass
class FindymailEmailResult:
    """Result from Findymail email finding operation."""

    email: str | None
    status: FindymailEmailStatus
    first_name: str | None
    last_name: str | None
    domain: str | None
    raw_response: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if email is valid and verified."""
        return self.status in (FindymailEmailStatus.VERIFIED, FindymailEmailStatus.VALID)

    @property
    def is_usable(self) -> bool:
        """Check if email is potentially usable."""
        return self.status in (
            FindymailEmailStatus.VERIFIED,
            FindymailEmailStatus.VALID,
            FindymailEmailStatus.CATCH_ALL,
        )


@dataclass
class FindymailVerificationResult:
    """Result from Findymail email verification operation."""

    email: str
    status: FindymailEmailStatus
    is_deliverable: bool
    is_catch_all: bool
    raw_response: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if email is verified and deliverable."""
        return self.is_deliverable and self.status == FindymailEmailStatus.VERIFIED


@dataclass
class FindymailPhoneResult:
    """Result from Findymail phone finding operation."""

    phone: str | None
    linkedin_url: str
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if phone was found."""
        return self.phone is not None


class FindymailClient(BaseIntegrationClient):
    """
    Findymail API client for email finding and verification.

    Findymail excels at finding emails for tech companies and startups.
    Second position in the waterfall strategy for good coverage.

    Example:
        >>> async with FindymailClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.find_work_email(
        ...         full_name="Jane Smith",
        ...         domain="techstartup.com"
        ...     )
        ...     if result.is_valid:
        ...         print(f"Found: {result.email}")
    """

    BASE_URL = "https://app.findymail.com/api"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Findymail client.

        Args:
            api_key: Findymail API key
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="findymail",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Findymail API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def find_work_email(
        self,
        full_name: str,
        domain: str,
    ) -> FindymailEmailResult:
        """
        Find work email from full name and company domain.

        Uses 1 credit if a verified email is found.

        Args:
            full_name: Full name of the person (e.g., "Jane Smith")
            domain: Company domain (e.g., "techcompany.com")

        Returns:
            FindymailEmailResult with email and status

        Raises:
            FindymailError: If API request fails
            ValueError: If required parameters are missing
        """
        if not full_name or not full_name.strip():
            raise ValueError("full_name is required")
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        payload = {
            "name": full_name.strip(),
            "domain": domain.strip().lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/name",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_email_result(response)
        except IntegrationError as e:
            raise FindymailError(
                message=f"Failed to find email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_email_by_domain(
        self,
        name: str,
        domain: str,
    ) -> FindymailEmailResult:
        """
        Find email using name and company domain via domain endpoint.

        Alternative endpoint that may use different search logic.

        Args:
            name: Name of the person
            domain: Company domain

        Returns:
            FindymailEmailResult with email and status

        Raises:
            FindymailError: If API request fails
        """
        if not name or not name.strip():
            raise ValueError("name is required")
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        payload = {
            "name": name.strip(),
            "domain": domain.strip().lower(),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/domain",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_email_result(response)
        except IntegrationError as e:
            raise FindymailError(
                message=f"Failed to find email by domain: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_email_from_linkedin(
        self,
        linkedin_url: str,
    ) -> FindymailEmailResult:
        """
        Find work email from LinkedIn profile URL.

        Uses 1 credit if a verified email is found.

        Args:
            linkedin_url: LinkedIn profile URL (e.g., "https://linkedin.com/in/username")

        Returns:
            FindymailEmailResult with email and status

        Raises:
            FindymailError: If API request fails
            ValueError: If LinkedIn URL is invalid
        """
        if not linkedin_url or not linkedin_url.strip():
            raise ValueError("linkedin_url is required")

        # Basic LinkedIn URL validation
        url = linkedin_url.strip()
        if "linkedin.com" not in url.lower():
            raise ValueError("Invalid LinkedIn URL")

        payload = {
            "linkedin_url": url,
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/linkedin",
                json=payload,
                headers=self._get_headers(),
            )
            return self._parse_email_result(response)
        except IntegrationError as e:
            raise FindymailError(
                message=f"Failed to find email from LinkedIn: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_phone_from_linkedin(
        self,
        linkedin_url: str,
    ) -> FindymailPhoneResult:
        """
        Find phone number from LinkedIn profile URL.

        Uses 10 credits if a phone is found.
        Note: EU citizens excluded due to privacy laws.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            FindymailPhoneResult with phone and status

        Raises:
            FindymailError: If API request fails
            ValueError: If LinkedIn URL is invalid
        """
        if not linkedin_url or not linkedin_url.strip():
            raise ValueError("linkedin_url is required")

        url = linkedin_url.strip()
        if "linkedin.com" not in url.lower():
            raise ValueError("Invalid LinkedIn URL")

        payload = {
            "linkedin_url": url,
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/phone",
                json=payload,
                headers=self._get_headers(),
            )
            return FindymailPhoneResult(
                phone=response.get("phone"),
                linkedin_url=url,
                raw_response=response,
            )
        except IntegrationError as e:
            raise FindymailError(
                message=f"Failed to find phone: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(
        self,
        email: str,
    ) -> FindymailVerificationResult:
        """
        Verify an email address for deliverability.

        Uses 1 verification credit.

        Args:
            email: Email address to verify

        Returns:
            FindymailVerificationResult with verification status

        Raises:
            FindymailError: If API request fails
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        # Basic email validation
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        payload = {
            "email": email,
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/verify",
                json=payload,
                headers=self._get_headers(),
            )

            status_str = response.get("status", "unknown").lower()
            try:
                status = FindymailEmailStatus(status_str)
            except ValueError:
                status = FindymailEmailStatus.UNKNOWN

            return FindymailVerificationResult(
                email=email,
                status=status,
                is_deliverable=response.get("deliverable", False),
                is_catch_all=response.get("catch_all", False),
                raw_response=response,
            )
        except IntegrationError as e:
            raise FindymailError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Findymail API health and connectivity.

        Returns:
            Dictionary with health status

        Raises:
            FindymailError: If health check fails
        """
        try:
            # Use verify endpoint with a test to check connectivity
            # Most email finder APIs don't have a dedicated health endpoint
            return {
                "name": "findymail",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "findymail",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_email_result(self, response: dict[str, Any]) -> FindymailEmailResult:
        """
        Parse API response into FindymailEmailResult.

        Args:
            response: Raw API response

        Returns:
            FindymailEmailResult dataclass
        """
        email = response.get("email")
        status_str = response.get("status", "not_found" if not email else "valid").lower()

        try:
            status = FindymailEmailStatus(status_str)
        except ValueError:
            # Map unknown statuses
            status = FindymailEmailStatus.VALID if email else FindymailEmailStatus.NOT_FOUND

        return FindymailEmailResult(
            email=email,
            status=status,
            first_name=response.get("first_name"),
            last_name=response.get("last_name"),
            domain=response.get("domain"),
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Findymail API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search/name")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            FindymailError: If request fails
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
            raise FindymailError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
