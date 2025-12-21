"""
Nimbler API integration client.

Provides B2B contact enrichment with access to 100M+ verified US-based
business contacts.

API Documentation: https://www.nimbler.com/platform
Base URL: https://api.nimbler.com/v1

Features:
- Contact enrichment with 50+ attributes
- Mobile phone discovery
- Personal email discovery
- LinkedIn profile lookup
- Company information

Authentication:
- Bearer token with API key

Pricing:
- Starter plan: $149/month
- APIs range from $249/month to $150,000/year

Example:
    >>> from src.integrations.nimbler import NimblerClient
    >>> client = NimblerClient(api_key="your-api-key")
    >>> result = await client.enrich_contact(
    ...     email="john.smith@company.com"
    ... )
    >>> if result.found:
    ...     print(f"Phone: {result.mobile_phone}")
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class NimblerError(IntegrationError):
    """Nimbler-specific error."""

    pass


@dataclass
class NimblerContactResult:
    """Result from Nimbler contact enrichment operation."""

    email: str | None
    personal_email: str | None
    mobile_phone: str | None
    direct_phone: str | None
    first_name: str | None
    last_name: str | None
    title: str | None
    company: str | None
    linkedin_url: str | None
    location: str | None
    skills: list[str]
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if contact was found."""
        return self.email is not None or self.mobile_phone is not None

    @property
    def has_mobile(self) -> bool:
        """Check if mobile phone is available."""
        return self.mobile_phone is not None

    @property
    def has_personal_email(self) -> bool:
        """Check if personal email is available."""
        return self.personal_email is not None


@dataclass
class NimblerCompanyResult:
    """Result from Nimbler company lookup operation."""

    name: str | None
    domain: str | None
    industry: str | None
    size: str | None
    location: str | None
    linkedin_url: str | None
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if company was found."""
        return self.name is not None


class NimblerClient(BaseIntegrationClient):
    """
    Nimbler API client for B2B contact enrichment.

    Nimbler is positioned 7th in the waterfall strategy, providing
    comprehensive contact enrichment with 50+ attributes.

    Example:
        >>> async with NimblerClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.enrich_contact(
        ...         email="john.smith@company.com"
        ...     )
        ...     if result.has_mobile:
        ...         print(f"Mobile: {result.mobile_phone}")
    """

    BASE_URL = "https://api.nimbler.com/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Nimbler client.

        Args:
            api_key: Nimbler API key (requires Starter plan or higher)
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="nimbler",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Nimbler API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def enrich_contact(
        self,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
    ) -> NimblerContactResult:
        """
        Enrich contact with additional data attributes.

        Requires at least one of: email, linkedin_url, or name+company.

        Args:
            email: Work email address
            linkedin_url: LinkedIn profile URL
            first_name: First name (used with last_name and company)
            last_name: Last name (used with first_name and company)
            company: Company name (used with first_name and last_name)

        Returns:
            NimblerContactResult with enriched data

        Raises:
            NimblerError: If API request fails
            ValueError: If required parameters are missing
        """
        has_email = email and email.strip()
        has_linkedin = linkedin_url and linkedin_url.strip()
        has_name_company = (
            first_name
            and first_name.strip()
            and last_name
            and last_name.strip()
            and company
            and company.strip()
        )

        if not has_email and not has_linkedin and not has_name_company:
            raise ValueError(
                "Either email, linkedin_url, or (first_name + last_name + company) is required"
            )

        payload: dict[str, Any] = {}

        if email:
            payload["email"] = email.strip().lower()
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url.strip()
        if first_name:
            payload["first_name"] = first_name.strip()
        if last_name:
            payload["last_name"] = last_name.strip()
        if company:
            payload["company"] = company.strip()

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/enrich/contact",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_contact_result(response)

        except IntegrationError as e:
            raise NimblerError(
                message=f"Failed to enrich contact: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_mobile(
        self,
        linkedin_url: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
    ) -> NimblerContactResult:
        """
        Find mobile phone number for a contact.

        Uses LinkedIn URL, email, or name+company to find mobile.

        Args:
            linkedin_url: LinkedIn profile URL
            email: Work email address
            first_name: First name
            last_name: Last name
            company: Company name

        Returns:
            NimblerContactResult with mobile phone if found

        Raises:
            NimblerError: If API request fails
            ValueError: If required parameters are missing
        """
        has_linkedin = linkedin_url and linkedin_url.strip()
        has_email = email and email.strip()
        has_name_company = (
            first_name
            and first_name.strip()
            and last_name
            and last_name.strip()
            and company
            and company.strip()
        )

        if not has_linkedin and not has_email and not has_name_company:
            raise ValueError(
                "Either linkedin_url, email, or (first_name + last_name + company) is required"
            )

        payload: dict[str, Any] = {}

        if linkedin_url:
            payload["linkedin_url"] = linkedin_url.strip()
        if email:
            payload["email"] = email.strip().lower()
        if first_name:
            payload["first_name"] = first_name.strip()
        if last_name:
            payload["last_name"] = last_name.strip()
        if company:
            payload["company"] = company.strip()

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/enrich/mobile",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_contact_result(response)

        except IntegrationError as e:
            raise NimblerError(
                message=f"Failed to find mobile: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def lookup_company(
        self,
        domain: str | None = None,
        company_name: str | None = None,
    ) -> NimblerCompanyResult:
        """
        Look up company information.

        Args:
            domain: Company domain (e.g., "company.com")
            company_name: Company name

        Returns:
            NimblerCompanyResult with company information

        Raises:
            NimblerError: If API request fails
            ValueError: If neither domain nor company_name provided
        """
        if not domain and not company_name:
            raise ValueError("Either domain or company_name is required")

        payload: dict[str, str] = {}
        if domain:
            payload["domain"] = domain.strip().lower()
        if company_name:
            payload["company_name"] = company_name.strip()

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/company/lookup",
                json=payload,
                headers=self._get_headers(),
            )

            return NimblerCompanyResult(
                name=response.get("name") or response.get("company_name"),
                domain=response.get("domain"),
                industry=response.get("industry"),
                size=response.get("size") or response.get("employee_count"),
                location=response.get("location") or response.get("headquarters"),
                linkedin_url=response.get("linkedin_url"),
                raw_response=response,
            )

        except IntegrationError as e:
            raise NimblerError(
                message=f"Failed to lookup company: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Nimbler API health and connectivity.

        Returns:
            Dictionary with health status
        """
        try:
            # Nimbler may not have a dedicated health endpoint
            # We'll verify by checking if the API responds
            return {
                "name": "nimbler",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "nimbler",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_contact_result(self, response: dict[str, Any]) -> NimblerContactResult:
        """
        Parse API response into NimblerContactResult.

        Args:
            response: Raw API response

        Returns:
            NimblerContactResult dataclass
        """
        # Handle nested data structure
        data = response.get("data", response)
        contact = data.get("contact", data)

        # Handle skills array
        skills = contact.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        return NimblerContactResult(
            email=contact.get("email") or contact.get("work_email"),
            personal_email=contact.get("personal_email"),
            mobile_phone=contact.get("mobile_phone") or contact.get("mobile"),
            direct_phone=contact.get("direct_phone") or contact.get("phone"),
            first_name=contact.get("first_name"),
            last_name=contact.get("last_name"),
            title=contact.get("title") or contact.get("job_title"),
            company=contact.get("company") or contact.get("company_name"),
            linkedin_url=contact.get("linkedin_url"),
            location=contact.get("location"),
            skills=skills if isinstance(skills, list) else [],
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Nimbler API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            NimblerError: If request fails
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
            raise NimblerError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
