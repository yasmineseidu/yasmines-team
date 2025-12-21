"""
Tomba API integration client.

Provides domain-wide email discovery and verification, excelling at
finding multiple contacts from the same company domain.

API Documentation: https://developer.tomba.io/
Base URL: https://api.tomba.io/v1/

Features:
- Domain search (find all emails from a domain)
- Email finder (find specific person's email)
- Email verification
- LinkedIn email lookup
- Email count per domain
- Technology detection

Pricing:
- Pay-per-lookup (~$0.15-0.25)
- Free plan: 25 searches, 50 verifications/month

Rate Limits:
- 429 HTTP status code when exceeded

Authentication:
- Requires both X-Tomba-Key and X-Tomba-Secret headers

Example:
    >>> from src.integrations.tomba import TombaClient
    >>> client = TombaClient(
    ...     api_key="ta_xxxx",  # pragma: allowlist secret
    ...     api_secret="ts_xxxx"  # pragma: allowlist secret
    ... )
    >>> result = await client.search_domain("techcompany.com")
    >>> for email in result.emails:
    ...     print(email.email)
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


class TombaEmailType(str, Enum):
    """Type of email address returned by Tomba."""

    PERSONAL = "personal"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class TombaVerificationStatus(str, Enum):
    """Email verification status from Tomba."""

    VALID = "valid"
    INVALID = "invalid"
    ACCEPT_ALL = "accept_all"
    WEBMAIL = "webmail"
    DISPOSABLE = "disposable"
    UNKNOWN = "unknown"


class TombaError(IntegrationError):
    """Tomba-specific error."""

    pass


@dataclass
class TombaEmail:
    """Email address found by Tomba domain search."""

    email: str
    first_name: str | None
    last_name: str | None
    full_name: str | None
    position: str | None
    department: str | None
    email_type: TombaEmailType
    seniority: str | None
    linkedin: str | None
    twitter: str | None
    phone_number: str | None
    sources: list[dict[str, Any]]
    verification_status: TombaVerificationStatus | None
    confidence: int | None
    raw_data: dict[str, Any]

    @property
    def is_verified(self) -> bool:
        """Check if email is verified as valid."""
        return self.verification_status == TombaVerificationStatus.VALID

    @property
    def has_social(self) -> bool:
        """Check if contact has social media profiles."""
        return bool(self.linkedin or self.twitter)


@dataclass
class TombaDomainSearchResult:
    """Result from Tomba domain search operation."""

    domain: str
    emails: list[TombaEmail]
    organization: str | None
    country: str | None
    state: str | None
    city: str | None
    postal_code: str | None
    street_address: str | None
    accept_all: bool
    website_url: str | None
    disposable: bool
    webmail: bool
    pattern: str | None
    total_results: int
    page: int
    limit: int
    raw_response: dict[str, Any]

    @property
    def has_more(self) -> bool:
        """Check if there are more results to fetch."""
        return len(self.emails) < self.total_results


@dataclass
class TombaEmailFinderResult:
    """Result from Tomba email finder operation."""

    email: str | None
    first_name: str | None
    last_name: str | None
    full_name: str | None
    domain: str | None
    position: str | None
    department: str | None
    seniority: str | None
    linkedin: str | None
    twitter: str | None
    phone_number: str | None
    company: str | None
    email_type: TombaEmailType
    confidence: int
    sources: list[dict[str, Any]]
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if email was found."""
        return self.email is not None

    @property
    def is_high_confidence(self) -> bool:
        """Check if result has high confidence (>75%)."""
        return self.confidence >= 75


@dataclass
class TombaVerificationResult:
    """Result from Tomba email verification operation."""

    email: str
    status: TombaVerificationStatus
    result: str
    accept_all: bool
    disposable: bool
    webmail: bool
    mx_records: bool
    smtp_server: bool
    smtp_check: bool
    block: bool
    sources: list[dict[str, Any]]
    raw_response: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if email is verified and deliverable."""
        return self.status == TombaVerificationStatus.VALID

    @property
    def is_risky(self) -> bool:
        """Check if email is risky (accept_all, disposable, etc.)."""
        return self.accept_all or self.disposable


@dataclass
class TombaEmailCountResult:
    """Result from Tomba email count operation."""

    domain: str
    total: int
    personal_emails: int
    generic_emails: int
    department: dict[str, int]
    seniority: dict[str, int]
    raw_response: dict[str, Any]

    @property
    def has_emails(self) -> bool:
        """Check if domain has any emails."""
        return self.total > 0


@dataclass
class TombaAccountInfo:
    """Tomba account information from /me endpoint."""

    user_id: int
    email: str
    first_name: str | None
    last_name: str | None
    requests_available: int
    requests_used: int
    verifications_available: int
    verifications_used: int
    phone_credits_available: int
    phone_credits_used: int
    plan_name: str | None
    raw_response: dict[str, Any]

    @property
    def search_remaining(self) -> int:
        """Get remaining search credits."""
        return max(0, self.requests_available - self.requests_used)

    @property
    def verification_remaining(self) -> int:
        """Get remaining verification credits."""
        return max(0, self.verifications_available - self.verifications_used)


class TombaClient(BaseIntegrationClient):
    """
    Tomba API client for domain-wide email discovery and verification.

    Tomba excels at finding multiple emails from the same company domain.
    Third position in the waterfall strategy for comprehensive coverage.

    Note: Tomba requires both an API key (ta_xxxx) and API secret (ts_xxxx)
    for authentication, unlike most APIs that use a single key.

    Example:
        >>> async with TombaClient(
        ...     api_key="ta_xxxx",  # pragma: allowlist secret
        ...     api_secret="ts_xxxx"  # pragma: allowlist secret
        ... ) as client:
        ...     result = await client.search_domain("stripe.com")
        ...     for email in result.emails:
        ...         if email.is_verified:
        ...             print(f"Found: {email.email} ({email.position})")
    """

    BASE_URL = "https://api.tomba.io/v1"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Tomba client.

        Args:
            api_key: Tomba API key (format: ta_xxxx)
            api_secret: Tomba API secret (format: ts_xxxx)
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="tomba",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.api_secret = api_secret

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Tomba API requests with dual-key auth."""
        return {
            "X-Tomba-Key": self.api_key,
            "X-Tomba-Secret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_account_info(self) -> TombaAccountInfo:
        """
        Get account information and usage stats.

        Returns:
            TombaAccountInfo with subscription and usage details

        Raises:
            TombaError: If API request fails
        """
        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/me",
            )
            data = response.get("data", response)
            credits = data.get("requests", {})
            # Tomba uses "domains" for domain search credits, not "search"
            domains = credits.get("domains", {})
            verifications = credits.get("verifications", {})
            phones = credits.get("phones", {})
            return TombaAccountInfo(
                user_id=data.get("user_id", 0),
                email=data.get("email", ""),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                requests_available=domains.get("available", 0),
                requests_used=domains.get("used", 0),
                verifications_available=verifications.get("available", 0),
                verifications_used=verifications.get("used", 0),
                phone_credits_available=phones.get("available", 0),
                phone_credits_used=phones.get("used", 0),
                plan_name=data.get("pricing", {}).get("name"),
                raw_response=response,
            )
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to get account info: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_domain(
        self,
        domain: str,
        page: int = 1,
        limit: int = 10,
        department: str | None = None,
        email_type: TombaEmailType | None = None,
    ) -> TombaDomainSearchResult:
        """
        Search for all emails from a domain.

        Returns all professional email addresses associated with a domain,
        including contact details and social profiles.

        Args:
            domain: Company domain to search (e.g., "stripe.com")
            page: Page number for pagination (default 1)
            limit: Results per page (max 100, default 10)
            department: Filter by department (e.g., "engineering", "sales")
            email_type: Filter by email type (personal or generic)

        Returns:
            TombaDomainSearchResult with list of emails and company info

        Raises:
            TombaError: If API request fails
            ValueError: If domain is empty
        """
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        # Tomba only accepts specific limit values: 10, 20, 50, 100
        valid_limits = [10, 20, 50, 100]
        # Find the closest valid limit that's >= requested (or max)
        effective_limit = next((v for v in valid_limits if v >= limit), 100)

        params: dict[str, Any] = {
            "domain": domain.strip().lower(),
            "page": page,
            "limit": effective_limit,
        }

        if department:
            params["department"] = department.strip().lower()
        if email_type:
            params["type"] = email_type.value

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/domain-search",
                params=params,
            )
            return self._parse_domain_search_result(response, domain)
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to search domain: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_email(
        self,
        domain: str,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
    ) -> TombaEmailFinderResult:
        """
        Find a specific person's email by name and domain.

        Generates or retrieves the most likely email address for a person
        based on their name and company domain.

        Args:
            domain: Company domain (e.g., "stripe.com")
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last name)

        Returns:
            TombaEmailFinderResult with email and confidence score

        Raises:
            TombaError: If API request fails
            ValueError: If required parameters are missing
        """
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        if not full_name and not (first_name and last_name):
            raise ValueError("Either full_name or both first_name and last_name required")

        params: dict[str, Any] = {
            "domain": domain.strip().lower(),
        }

        if full_name:
            # Parse full name into first/last
            parts = full_name.strip().split(maxsplit=1)
            params["first_name"] = parts[0]
            params["last_name"] = parts[1] if len(parts) > 1 else ""
        else:
            params["first_name"] = first_name.strip() if first_name else ""
            params["last_name"] = last_name.strip() if last_name else ""

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/email-finder",
                params=params,
            )
            return self._parse_email_finder_result(response)
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to find email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(
        self,
        email: str,
    ) -> TombaVerificationResult:
        """
        Verify an email address for deliverability.

        Performs SMTP and MX record checks to determine if
        the email address is valid and deliverable.

        Args:
            email: Email address to verify

        Returns:
            TombaVerificationResult with verification status

        Raises:
            TombaError: If API request fails
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        # Basic email validation
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint=f"/email-verifier/{email}",
            )
            return self._parse_verification_result(response, email)
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_email_from_linkedin(
        self,
        linkedin_url: str,
    ) -> TombaEmailFinderResult:
        """
        Find work email from LinkedIn profile URL.

        Extracts email, job title, company information from
        a LinkedIn profile URL.

        Args:
            linkedin_url: LinkedIn profile URL (e.g., "https://linkedin.com/in/username")

        Returns:
            TombaEmailFinderResult with email and profile info

        Raises:
            TombaError: If API request fails
            ValueError: If LinkedIn URL is invalid
        """
        if not linkedin_url or not linkedin_url.strip():
            raise ValueError("linkedin_url is required")

        url = linkedin_url.strip()
        if "linkedin.com" not in url.lower():
            raise ValueError("Invalid LinkedIn URL")

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/linkedin",
                params={"url": url},
            )
            return self._parse_email_finder_result(response)
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to find email from LinkedIn: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_email_count(
        self,
        domain: str,
    ) -> TombaEmailCountResult:
        """
        Get count of emails available for a domain.

        Returns the total number of emails Tomba has for a domain,
        broken down by department and seniority. Useful for estimating
        costs before running a full domain search.

        Args:
            domain: Company domain to check

        Returns:
            TombaEmailCountResult with email counts

        Raises:
            TombaError: If API request fails
            ValueError: If domain is empty
        """
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/email-count",
                params={"domain": domain.strip().lower()},
            )
            data = response.get("data", response)
            return TombaEmailCountResult(
                domain=domain.strip().lower(),
                total=data.get("total", 0),
                personal_emails=data.get("personal_emails", 0),
                generic_emails=data.get("generic_emails", 0),
                department=data.get("department", {}),
                seniority=data.get("seniority", {}),
                raw_response=response,
            )
        except IntegrationError as e:
            raise TombaError(
                message=f"Failed to get email count: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Tomba API health and connectivity.

        Uses the /me endpoint to verify API credentials and connectivity.

        Returns:
            Dictionary with health status and account info

        Raises:
            TombaError: If health check fails
        """
        try:
            account = await self.get_account_info()
            return {
                "name": "tomba",
                "healthy": True,
                "base_url": self.BASE_URL,
                "email": account.email,
                "plan": account.plan_name,
                "search_remaining": account.search_remaining,
                "verification_remaining": account.verification_remaining,
            }
        except Exception as e:
            return {
                "name": "tomba",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Tomba API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/domain-search")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            TombaError: If request fails
        """
        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise TombaError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_email_type(self, type_str: str | None) -> TombaEmailType:
        """Parse email type string to enum."""
        if not type_str:
            return TombaEmailType.UNKNOWN
        try:
            return TombaEmailType(type_str.lower())
        except ValueError:
            return TombaEmailType.UNKNOWN

    def _parse_verification_status(self, status_str: str | None) -> TombaVerificationStatus:
        """Parse verification status string to enum."""
        if not status_str:
            return TombaVerificationStatus.UNKNOWN
        try:
            return TombaVerificationStatus(status_str.lower())
        except ValueError:
            return TombaVerificationStatus.UNKNOWN

    def _parse_email(self, data: dict[str, Any]) -> TombaEmail:
        """Parse email data from API response."""
        verification_str = (
            data.get("verification", {}).get("status")
            if isinstance(data.get("verification"), dict)
            else None
        )
        return TombaEmail(
            email=data.get("email", ""),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            full_name=data.get("full_name"),
            position=data.get("position"),
            department=data.get("department"),
            email_type=self._parse_email_type(data.get("type")),
            seniority=data.get("seniority"),
            linkedin=data.get("linkedin"),
            twitter=data.get("twitter"),
            phone_number=data.get("phone_number"),
            sources=data.get("sources", []),
            verification_status=self._parse_verification_status(verification_str),
            confidence=data.get("score"),
            raw_data=data,
        )

    def _parse_domain_search_result(
        self,
        response: dict[str, Any],
        domain: str,
    ) -> TombaDomainSearchResult:
        """Parse domain search response."""
        data = response.get("data", response)
        org_data = data.get("organization", {})
        emails_data = data.get("emails", [])

        return TombaDomainSearchResult(
            domain=domain,
            emails=[self._parse_email(e) for e in emails_data],
            organization=org_data.get("organization"),
            country=org_data.get("country"),
            state=org_data.get("state"),
            city=org_data.get("city"),
            postal_code=org_data.get("postal_code"),
            street_address=org_data.get("street_address"),
            accept_all=org_data.get("accept_all", False),
            website_url=org_data.get("website_url"),
            disposable=data.get("disposable", False),
            webmail=data.get("webmail", False),
            pattern=data.get("pattern"),
            total_results=response.get("meta", {}).get("total", len(emails_data)),
            page=response.get("meta", {}).get("page", 1),
            limit=response.get("meta", {}).get("limit", 10),
            raw_response=response,
        )

    def _parse_email_finder_result(
        self,
        response: dict[str, Any],
    ) -> TombaEmailFinderResult:
        """Parse email finder response."""
        data = response.get("data", response)
        return TombaEmailFinderResult(
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            full_name=data.get("full_name"),
            domain=data.get("domain"),
            position=data.get("position"),
            department=data.get("department"),
            seniority=data.get("seniority"),
            linkedin=data.get("linkedin"),
            twitter=data.get("twitter"),
            phone_number=data.get("phone_number"),
            company=data.get("company"),
            email_type=self._parse_email_type(data.get("type")),
            confidence=data.get("score", 0),
            sources=data.get("sources", []),
            raw_response=response,
        )

    def _parse_verification_result(
        self,
        response: dict[str, Any],
        email: str,
    ) -> TombaVerificationResult:
        """Parse verification response."""
        data = response.get("data", response)
        return TombaVerificationResult(
            email=email,
            status=self._parse_verification_status(data.get("status")),
            result=data.get("result", ""),
            accept_all=data.get("accept_all", False),
            disposable=data.get("disposable", False),
            webmail=data.get("webmail", False),
            mx_records=data.get("mx_records", False),
            smtp_server=data.get("smtp_server", False),
            smtp_check=data.get("smtp_check", False),
            block=data.get("block", False),
            sources=data.get("sources", []),
            raw_response=response,
        )
