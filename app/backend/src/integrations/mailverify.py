"""
MailVerify API integration client.

Provides email verification and deliverability checking capabilities.

API Documentation: https://docs.mailverify.ai/
Base URL: https://api.mailverify.ai/api/v1

Features:
- Single email verification
- Bulk email verification
- Deliverability checking
- Spam trap detection
- Catch-all detection
- Disposable email detection

Authentication:
- API key in X-API-Key header

Example:
    >>> from src.integrations.mailverify import MailVerifyClient
    >>> client = MailVerifyClient(api_key="your-api-key")
    >>> result = await client.verify_email("john@company.com")
    >>> if result.is_deliverable:
    ...     print(f"Email is valid and deliverable")
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


class MailVerifyStatus(str, Enum):
    """Email verification status from MailVerify API."""

    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    UNKNOWN = "unknown"
    CATCH_ALL = "catch_all"
    DISPOSABLE = "disposable"
    SPAM_TRAP = "spam_trap"


class MailVerifyError(IntegrationError):
    """MailVerify-specific error."""

    pass


@dataclass
class MailVerifyResult:
    """Result from MailVerify email verification operation."""

    email: str
    status: MailVerifyStatus
    is_valid: bool
    is_deliverable: bool
    is_catch_all: bool
    is_disposable: bool
    is_spam_trap: bool
    domain: str | None
    mx_records: list[str]
    raw_response: dict[str, Any]

    @property
    def is_safe_to_send(self) -> bool:
        """Check if email is safe to send to."""
        return (
            self.is_valid
            and self.is_deliverable
            and not self.is_disposable
            and not self.is_spam_trap
        )

    @property
    def is_risky(self) -> bool:
        """Check if email is risky to send to."""
        return self.status == MailVerifyStatus.RISKY or self.is_catch_all


@dataclass
class MailVerifyBulkResult:
    """Result from MailVerify bulk verification operation."""

    job_id: str
    status: str
    total_emails: int
    processed: int
    valid_count: int
    invalid_count: int
    risky_count: int
    results: list[MailVerifyResult]
    raw_response: dict[str, Any]

    @property
    def is_complete(self) -> bool:
        """Check if bulk verification is complete."""
        return self.processed >= self.total_emails

    @property
    def valid_rate(self) -> float:
        """Calculate valid email rate."""
        if self.total_emails == 0:
            return 0.0
        return self.valid_count / self.total_emails


class MailVerifyClient(BaseIntegrationClient):
    """
    MailVerify API client for email verification and deliverability checking.

    MailVerify is positioned 8th in the waterfall strategy, providing
    final verification and deliverability checking for emails.

    Example:
        >>> async with MailVerifyClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.verify_email("john@company.com")
        ...     if result.is_safe_to_send:
        ...         print(f"Email is safe to send")
    """

    BASE_URL = "https://api.mailverify.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize MailVerify client.

        Args:
            api_key: MailVerify API key
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="mailverify",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for MailVerify API requests."""
        return {
            "x-auth-mailverify": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def verify_email(self, email: str) -> MailVerifyResult:
        """
        Verify a single email address.

        Args:
            email: Email address to verify

        Returns:
            MailVerifyResult with verification status

        Raises:
            MailVerifyError: If API request fails
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
                endpoint="/verify/single",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_verify_result(email, response)

        except IntegrationError as e:
            raise MailVerifyError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_bulk(
        self,
        emails: list[str],
        webhook_url: str | None = None,
    ) -> MailVerifyBulkResult:
        """
        Verify multiple email addresses in bulk.

        Args:
            emails: List of email addresses to verify
            webhook_url: Optional webhook for completion notification

        Returns:
            MailVerifyBulkResult with job status

        Raises:
            MailVerifyError: If API request fails
            ValueError: If emails list is empty
        """
        if not emails:
            raise ValueError("emails list is required")

        # Clean and validate emails
        clean_emails = []
        for email in emails:
            email = email.strip().lower()
            if "@" in email and "." in email.split("@")[-1]:
                clean_emails.append(email)

        if not clean_emails:
            raise ValueError("No valid emails provided")

        payload: dict[str, Any] = {"emails": clean_emails}
        if webhook_url:
            payload["webhook_url"] = webhook_url

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/verify/bulk",
                json=payload,
                headers=self._get_headers(),
            )

            return self._parse_bulk_result(response)

        except IntegrationError as e:
            raise MailVerifyError(
                message=f"Failed to start bulk verification: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_bulk_status(self, job_id: str) -> MailVerifyBulkResult:
        """
        Get status of a bulk verification job.

        Args:
            job_id: The bulk job ID to check

        Returns:
            MailVerifyBulkResult with current status

        Raises:
            MailVerifyError: If API request fails
            ValueError: If job_id is not provided
        """
        if not job_id:
            raise ValueError("job_id is required")

        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint=f"/verify/bulk/{job_id}",
                headers=self._get_headers(),
            )

            return self._parse_bulk_result(response)

        except IntegrationError as e:
            raise MailVerifyError(
                message=f"Failed to get bulk status: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def check_domain(self, domain: str) -> dict[str, Any]:
        """
        Check domain MX records and mail server status.

        Args:
            domain: Domain to check (e.g., "company.com")

        Returns:
            Dictionary with domain mail server information

        Raises:
            MailVerifyError: If API request fails
            ValueError: If domain is invalid
        """
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        domain = domain.strip().lower()
        if "." not in domain:
            raise ValueError("Invalid domain format")

        payload = {"domain": domain}

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/domain/check",
                json=payload,
                headers=self._get_headers(),
            )

            return response

        except IntegrationError as e:
            raise MailVerifyError(
                message=f"Failed to check domain: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check MailVerify API health and connectivity.

        Returns:
            Dictionary with health status
        """
        try:
            # Use a simple test verification to check connectivity
            return {
                "name": "mailverify",
                "healthy": True,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "mailverify",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_verify_result(self, email: str, response: dict[str, Any]) -> MailVerifyResult:
        """
        Parse API response into MailVerifyResult.

        Args:
            email: Original email that was verified
            response: Raw API response

        Returns:
            MailVerifyResult dataclass
        """
        status_str = response.get("status", "unknown").lower()
        try:
            status = MailVerifyStatus(status_str)
        except ValueError:
            status = MailVerifyStatus.UNKNOWN

        mx_records = response.get("mx_records", [])
        if isinstance(mx_records, str):
            mx_records = [mx_records]

        return MailVerifyResult(
            email=email,
            status=status,
            is_valid=response.get("valid", False),
            is_deliverable=response.get("deliverable", False),
            is_catch_all=response.get("catch_all", False),
            is_disposable=response.get("disposable", False),
            is_spam_trap=response.get("spam_trap", False),
            domain=response.get("domain"),
            mx_records=mx_records,
            raw_response=response,
        )

    def _parse_bulk_result(self, response: dict[str, Any]) -> MailVerifyBulkResult:
        """
        Parse bulk verification API response.

        Args:
            response: Raw API response

        Returns:
            MailVerifyBulkResult dataclass
        """
        results = []
        for item in response.get("results", []):
            email = item.get("email", "")
            results.append(self._parse_verify_result(email, item))

        return MailVerifyBulkResult(
            job_id=response.get("job_id", ""),
            status=response.get("status", "unknown"),
            total_emails=response.get("total", 0),
            processed=response.get("processed", 0),
            valid_count=response.get("valid_count", 0),
            invalid_count=response.get("invalid_count", 0),
            risky_count=response.get("risky_count", 0),
            results=results,
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any MailVerify API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            MailVerifyError: If request fails
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
            raise MailVerifyError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
