"""
Anymailfinder API integration client.

Provides email finding and verification capabilities with high accuracy,
especially for C-level executives and corporate professionals.

API Documentation: https://anymailfinder.com/email-finder-api/docs
API Version: v5.1
Base URL: https://api.anymailfinder.com/v5.1

Features:
- Find person's email by name and domain
- Find decision maker's email
- Find all emails at a company
- Email verification
- Bulk email search

Pricing:
- 1 credit per successful email find (valid status)
- 0.2 credits per email verification
- Free: risky, not_found, and blacklisted results
- Free: duplicate searches within 30 days

Example:
    >>> from src.integrations.anymailfinder import AnymailfinderClient
    >>> client = AnymailfinderClient(api_key="your-api-key")
    >>> result = await client.find_person_email(
    ...     first_name="John",
    ...     last_name="Doe",
    ...     domain="microsoft.com"
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


class EmailStatus(str, Enum):
    """Email status returned by Anymailfinder API."""

    VALID = "valid"
    RISKY = "risky"
    NOT_FOUND = "not_found"
    BLACKLISTED = "blacklisted"
    INVALID = "invalid"  # For verification endpoint


@dataclass
class EmailResult:
    """Result from email finding operation."""

    email: str | None
    email_status: EmailStatus
    valid_email: str | None
    raw_response: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if email is valid and deliverable."""
        return self.email_status == EmailStatus.VALID

    @property
    def is_usable(self) -> bool:
        """Check if email is potentially usable (valid or risky)."""
        return self.email_status in (EmailStatus.VALID, EmailStatus.RISKY)


@dataclass
class VerificationResult:
    """Result from email verification operation."""

    email: str
    email_status: EmailStatus
    raw_response: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if email is valid and deliverable."""
        return self.email_status == EmailStatus.VALID

    @property
    def is_deliverable(self) -> bool:
        """Check if email is likely deliverable (valid or risky)."""
        return self.email_status in (EmailStatus.VALID, EmailStatus.RISKY)


@dataclass
class AccountInfo:
    """Account information from Anymailfinder."""

    email: str
    credits_remaining: int
    raw_response: dict[str, Any]


class AnymailfinderError(IntegrationError):
    """Exception raised for Anymailfinder API errors."""

    pass


class AnymailfinderClient(BaseIntegrationClient):
    """
    Async client for Anymailfinder Email Finder API.

    Provides high-accuracy email finding with SMTP verification,
    especially effective for C-level executives. First in the
    lead enrichment waterfall strategy due to highest accuracy.

    Attributes:
        API_VERSION: Current API version (v5.1).
        BASE_URL: Base URL for API requests.

    Note:
        - No rate limits - system auto-scales
        - Recommended timeout: 180 seconds (real-time SMTP verification)
        - Success-based pricing: only pay for valid emails
    """

    API_VERSION = "v5.1"
    BASE_URL = "https://api.anymailfinder.com/v5.1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 180.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Anymailfinder client.

        Args:
            api_key: Anymailfinder API key.
            timeout: Request timeout in seconds (default 180s for SMTP verification).
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="anymailfinder",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client (API {self.API_VERSION})")

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for Anymailfinder API requests.

        Returns:
            Dictionary of HTTP headers with API key authorization.
        """
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def find_person_email(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        domain: str | None = None,
        company_name: str | None = None,
        webhook_url: str | None = None,
    ) -> EmailResult:
        """
        Find a person's email by name and company.

        At least one of (first_name, last_name) or full_name must be provided.
        At least one of domain or company_name must be provided.
        Domain is preferred for more reliable results.

        Args:
            first_name: Person's first name.
            last_name: Person's last name.
            full_name: Full name (alternative to first+last).
            domain: Company domain (e.g., "microsoft.com").
            company_name: Company name (domain preferred if available).
            webhook_url: Optional URL to receive results via POST.

        Returns:
            EmailResult with found email and status.

        Raises:
            AnymailfinderError: If required parameters are missing or API fails.
            ValueError: If invalid parameter combination provided.
        """
        # Validate parameters
        if not full_name and not (first_name and last_name):
            raise ValueError("Either full_name or both first_name and last_name must be provided")
        if not domain and not company_name:
            raise ValueError("Either domain or company_name must be provided")

        payload: dict[str, Any] = {}

        if full_name:
            payload["full_name"] = full_name
        else:
            if first_name:
                payload["first_name"] = first_name
            if last_name:
                payload["last_name"] = last_name

        if domain:
            payload["domain"] = domain
        elif company_name:
            payload["company_name"] = company_name

        headers: dict[str, str] = {}
        if webhook_url:
            headers["x-webhook-url"] = webhook_url

        try:
            response = await self.post(
                "/find-email/person",
                json=payload,
                headers=headers if headers else None,
            )

            email_status = EmailStatus(response.get("email_status", "not_found"))

            return EmailResult(
                email=response.get("email"),
                email_status=email_status,
                valid_email=response.get("valid_email"),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] find_person_email failed: {e}",
                extra={
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain,
                },
            )
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_decision_maker_email(
        self,
        domain: str,
        job_title: str | None = None,
        department: str | None = None,
        seniority: str | None = None,
        webhook_url: str | None = None,
    ) -> EmailResult:
        """
        Find a decision maker's email at a company.

        Args:
            domain: Company domain (e.g., "microsoft.com").
            job_title: Target job title (e.g., "CEO", "CTO").
            department: Target department (e.g., "Engineering", "Sales").
            seniority: Target seniority level (e.g., "C-Level", "VP").
            webhook_url: Optional URL to receive results via POST.

        Returns:
            EmailResult with found email and status.

        Raises:
            AnymailfinderError: If API request fails.
        """
        payload: dict[str, Any] = {"domain": domain}

        if job_title:
            payload["job_title"] = job_title
        if department:
            payload["department"] = department
        if seniority:
            payload["seniority"] = seniority

        headers: dict[str, str] = {}
        if webhook_url:
            headers["x-webhook-url"] = webhook_url

        try:
            response = await self.post(
                "/find-email/decision-maker",
                json=payload,
                headers=headers if headers else None,
            )

            email_status = EmailStatus(response.get("email_status", "not_found"))

            return EmailResult(
                email=response.get("email"),
                email_status=email_status,
                valid_email=response.get("valid_email"),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] find_decision_maker_email failed: {e}",
                extra={"domain": domain, "job_title": job_title},
            )
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def find_company_emails(
        self,
        domain: str,
        limit: int | None = None,
        webhook_url: str | None = None,
    ) -> list[EmailResult]:
        """
        Find all emails at a company domain.

        Args:
            domain: Company domain (e.g., "microsoft.com").
            limit: Maximum number of emails to return.
            webhook_url: Optional URL to receive results via POST.

        Returns:
            List of EmailResult objects for all found emails.

        Raises:
            AnymailfinderError: If API request fails.
        """
        payload: dict[str, Any] = {"domain": domain}

        if limit:
            payload["limit"] = limit

        headers: dict[str, str] = {}
        if webhook_url:
            headers["x-webhook-url"] = webhook_url

        try:
            response = await self.post(
                "/find-email/company",
                json=payload,
                headers=headers if headers else None,
            )

            emails = response.get("emails", [])
            results: list[EmailResult] = []

            for email_data in emails:
                email_status = EmailStatus(email_data.get("email_status", "not_found"))
                results.append(
                    EmailResult(
                        email=email_data.get("email"),
                        email_status=email_status,
                        valid_email=email_data.get("valid_email"),
                        raw_response=email_data,
                    )
                )

            return results

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] find_company_emails failed: {e}",
                extra={"domain": domain},
            )
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(
        self,
        email: str,
        webhook_url: str | None = None,
    ) -> VerificationResult:
        """
        Verify if an email address is valid and deliverable.

        Performs advanced checks beyond standard SMTP validation,
        including detection of catch-all domains and temporary responses.

        Args:
            email: Email address to verify.
            webhook_url: Optional URL to receive results via POST.

        Returns:
            VerificationResult with verification status.

        Raises:
            AnymailfinderError: If API request fails.

        Note:
            Cost: 0.2 credits per verification.
            Repeated verifications within 30 days are free.
        """
        payload = {"email": email}

        headers: dict[str, str] = {}
        if webhook_url:
            headers["x-webhook-url"] = webhook_url

        try:
            response = await self.post(
                "/verify-email",
                json=payload,
                headers=headers if headers else None,
            )

            email_status = EmailStatus(response.get("email_status", "invalid"))

            return VerificationResult(
                email=email,
                email_status=email_status,
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] verify_email failed: {e}",
                extra={"email": email},
            )
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_account_info(self) -> AccountInfo:
        """
        Get account details including remaining credits.

        Returns:
            AccountInfo with email and credits remaining.

        Raises:
            AnymailfinderError: If API request fails.
        """
        try:
            response = await self.get("/account")

            return AccountInfo(
                email=response.get("email", ""),
                credits_remaining=response.get("credits_remaining", 0),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_account_info failed: {e}")
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Anymailfinder API connectivity and account status.

        Returns:
            Health check status with credits remaining.
        """
        try:
            account = await self.get_account_info()
            return {
                "name": self.name,
                "healthy": True,
                "credits_remaining": account.credits_remaining,
                "api_version": self.API_VERSION,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
                "healthy": False,
                "error": str(e),
                "api_version": self.API_VERSION,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling new endpoints that may be released
        in the future without requiring code changes.

        Args:
            endpoint: Endpoint path (e.g., "/v5.1/new-endpoint").
            method: HTTP method (default: "GET").
            **kwargs: Request parameters (json, params, etc.).

        Returns:
            API response as dictionary.

        Raises:
            AnymailfinderError: If API request fails.

        Example:
            >>> result = await client.call_endpoint(
            ...     "/new-feature",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
        """
        try:
            return await self._request_with_retry(method, endpoint, **kwargs)
        except IntegrationError as e:
            raise AnymailfinderError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
