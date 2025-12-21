"""
VoilaNorbert API integration client.

Provides email finding and verification capabilities, best for common names
and general business contacts.

API Documentation: https://api.voilanorbert.com/2018-01-08/
Base URL: https://api.voilanorbert.com/2018-01-08

Features:
- Find email from name and domain/company
- Domain-wide email search
- Bulk email search operations
- Email verification/validation
- Email enrichment

Authentication:
- HTTP Basic Auth with API key as password
- Username can be any string (ignored)

Rate Limits:
- Default: 120 requests/minute
- Search /name: 300 requests/minute, 100,000/day
- Search /domain: 60 requests/minute, 50,000/day
- Bulk operations: 5 requests/minute, 1,000/day

Example:
    >>> from src.integrations.voilanorbert import VoilaNorbertClient
    >>> client = VoilaNorbertClient(api_key="your-api-key")
    >>> result = await client.find_email(
    ...     full_name="John Smith",
    ...     domain="company.com"
    ... )
    >>> if result.found:
    ...     print(f"Email: {result.email}")
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    PaymentRequiredError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class VoilaNorbertEmailStatus(str, Enum):
    """Email status returned by VoilaNorbert API."""

    SEARCHING = "searching"
    FOUND = "found"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"


class VoilaNorbertError(IntegrationError):
    """VoilaNorbert-specific error."""

    pass


@dataclass
class VoilaNorbertEmailResult:
    """Result from VoilaNorbert email finding operation."""

    email: str | None
    status: VoilaNorbertEmailStatus
    score: int  # Confidence score: 100 (verified), 80 (guessed), 5 (low confidence)
    first_name: str | None
    last_name: str | None
    company: str | None
    raw_response: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if email was found."""
        return self.email is not None and self.status == VoilaNorbertEmailStatus.FOUND

    @property
    def is_high_confidence(self) -> bool:
        """Check if result has high confidence (verified)."""
        return self.score >= 80

    @property
    def is_verified(self) -> bool:
        """Check if email is verified (score 100)."""
        return self.score == 100


@dataclass
class VoilaNorbertVerificationResult:
    """Result from VoilaNorbert email verification operation."""

    email: str
    is_valid: bool
    is_deliverable: bool
    is_catch_all: bool
    status: str
    raw_response: dict[str, Any]

    @property
    def is_safe_to_send(self) -> bool:
        """Check if email is safe to send to."""
        return self.is_valid and self.is_deliverable and not self.is_catch_all


@dataclass
class VoilaNorbertAccountInfo:
    """VoilaNorbert account information."""

    email: str
    credits_remaining: int
    plan_name: str | None
    raw_response: dict[str, Any]

    @property
    def has_credits(self) -> bool:
        """Check if account has remaining credits."""
        return self.credits_remaining > 0


class VoilaNorbertClient(BaseIntegrationClient):
    """
    VoilaNorbert API client for email finding and verification.

    VoilaNorbert is positioned 4th in the waterfall strategy, best for
    common names and general business contacts.

    Example:
        >>> async with VoilaNorbertClient(api_key="key") as client:  # pragma: allowlist secret
        ...     result = await client.find_email(
        ...         full_name="John Smith",
        ...         domain="company.com"
        ...     )
        ...     if result.found:
        ...         print(f"Found: {result.email} (score: {result.score})")
    """

    BASE_URL = "https://api.voilanorbert.com/2018-01-08"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize VoilaNorbert client.

        Args:
            api_key: VoilaNorbert API key
            timeout: Request timeout in seconds (default 60s)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="voilanorbert",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for VoilaNorbert API requests."""
        # VoilaNorbert uses HTTP Basic Auth, not Bearer token
        # The API key is passed as the password, username can be any string
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

    def _get_auth(self) -> httpx.BasicAuth:
        """Get HTTP Basic Auth for VoilaNorbert API."""
        return httpx.BasicAuth(username="api", password=self.api_key)

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Override to use HTTP Basic Auth instead of Bearer token.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            Parsed JSON response data

        Raises:
            VoilaNorbertError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # Add Basic Auth
        kwargs["auth"] = self._get_auth()

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )
                return await self._handle_voilanorbert_response(response)

            except Exception as error:
                last_error = error
                is_retryable = self._is_retryable_error(error)

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[{self.name}] Request failed: {error}",
                        extra={
                            "integration": self.name,
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                import asyncio

                delay = self.retry_base_delay * (2**attempt)
                jitter = delay * (0.1 + 0.4 * (attempt / self.max_retries))
                delay += jitter

                logger.warning(
                    f"[{self.name}] Request failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {error}",
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise VoilaNorbertError(f"[{self.name}] Request failed after {self.max_retries} retries")

    async def _handle_voilanorbert_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle VoilaNorbert API response.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response data

        Raises:
            AuthenticationError: For 401 responses
            PaymentRequiredError: For 402 responses
            RateLimitError: For 429 responses
            VoilaNorbertError: For other error responses
        """
        data: dict[str, Any]
        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text}

        if response.status_code == 401:
            raise AuthenticationError(
                message=f"[{self.name}] Authentication failed - check your API key",
                response_data=data,
            )

        if response.status_code == 402:
            raise PaymentRequiredError(
                message=f"[{self.name}] Insufficient credits",
                response_data=data,
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            remaining = response.headers.get("X-RateLimit-Remaining", "0")
            raise RateLimitError(
                message=f"[{self.name}] Rate limit exceeded (remaining: {remaining})",
                status_code=429,
                retry_after=int(retry_after) if retry_after else None,
                response_data=data,
            )

        if response.status_code == 400:
            error_msg = data.get("error", "Bad request")
            raise VoilaNorbertError(
                message=f"[{self.name}] Bad request: {error_msg}",
                status_code=400,
                response_data=data,
            )

        if response.status_code >= 400:
            error_message = data.get("error", data.get("message", "Unknown error"))
            raise VoilaNorbertError(
                message=f"[{self.name}] API error: {error_message}",
                status_code=response.status_code,
                response_data=data,
            )

        return data

    async def find_email(
        self,
        full_name: str,
        domain: str | None = None,
        company: str | None = None,
        webhook: str | None = None,
    ) -> VoilaNorbertEmailResult:
        """
        Find email from full name and domain/company.

        Uses 1 credit if a successful email is found.

        Args:
            full_name: Full name of the person (e.g., "John Smith")
            domain: Company domain (e.g., "company.com")
            company: Company name (alternative to domain)
            webhook: Optional webhook URL for async notifications

        Returns:
            VoilaNorbertEmailResult with email and confidence score

        Raises:
            VoilaNorbertError: If API request fails
            ValueError: If neither domain nor company provided
        """
        if not full_name or not full_name.strip():
            raise ValueError("full_name is required")
        if not domain and not company:
            raise ValueError("Either domain or company is required")

        data: dict[str, str] = {"name": full_name.strip()}

        if domain:
            data["domain"] = domain.strip().lower()
        if company:
            data["company"] = company.strip()
        if webhook:
            data["webhook"] = webhook

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/name",
                data=data,
            )
            return self._parse_email_result(response)
        except IntegrationError as e:
            if isinstance(e, AuthenticationError | PaymentRequiredError | RateLimitError):
                raise
            raise VoilaNorbertError(
                message=f"Failed to find email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def search_domain(
        self,
        domain: str,
        page: int = 1,
    ) -> list[VoilaNorbertEmailResult]:
        """
        Search for all emails associated with a domain.

        Uses credits for each email found.

        Args:
            domain: Company domain to search
            page: Page number for pagination (default 1)

        Returns:
            List of VoilaNorbertEmailResult objects

        Raises:
            VoilaNorbertError: If API request fails
            ValueError: If domain is not provided
        """
        if not domain or not domain.strip():
            raise ValueError("domain is required")

        data = {
            "domain": domain.strip().lower(),
            "page": str(page),
        }

        try:
            response = await self._request_with_retry(
                method="POST",
                endpoint="/search/domain",
                data=data,
            )

            contacts = response.get("contacts", [])
            results = []
            for contact in contacts:
                result = self._parse_email_result(contact)
                results.append(result)

            return results
        except IntegrationError as e:
            if isinstance(e, AuthenticationError | PaymentRequiredError | RateLimitError):
                raise
            raise VoilaNorbertError(
                message=f"Failed to search domain: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def verify_email(
        self,
        email: str,
    ) -> VoilaNorbertVerificationResult:
        """
        Verify an email address for deliverability.

        Args:
            email: Email address to verify

        Returns:
            VoilaNorbertVerificationResult with verification status

        Raises:
            VoilaNorbertError: If API request fails
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        # VoilaNorbert uses bulk verification endpoint
        # For single email, we upload and immediately check
        data = {"emails": email}

        try:
            # Start verification
            upload_response = await self._request_with_retry(
                method="POST",
                endpoint="/verifier/upload",
                data=data,
            )

            token = upload_response.get("token")
            if not token:
                raise VoilaNorbertError(
                    message="No verification token received",
                    response_data=upload_response,
                )

            # Check verification status - in practice this would poll
            # For single email, result is usually immediate
            status_response = await self._request_with_retry(
                method="GET",
                endpoint=f"/verifier/{token}",
            )

            return self._parse_verification_result(email, status_response)

        except IntegrationError as e:
            if isinstance(e, AuthenticationError | PaymentRequiredError | RateLimitError):
                raise
            raise VoilaNorbertError(
                message=f"Failed to verify email: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_account_info(self) -> VoilaNorbertAccountInfo:
        """
        Get account information including remaining credits.

        Returns:
            VoilaNorbertAccountInfo with account details

        Raises:
            VoilaNorbertError: If API request fails
        """
        try:
            response = await self._request_with_retry(
                method="GET",
                endpoint="/account/",
            )

            return VoilaNorbertAccountInfo(
                email=response.get("email", ""),
                credits_remaining=response.get("credits", 0),
                plan_name=response.get("plan", {}).get("name"),
                raw_response=response,
            )
        except IntegrationError as e:
            if isinstance(e, AuthenticationError | PaymentRequiredError | RateLimitError):
                raise
            raise VoilaNorbertError(
                message=f"Failed to get account info: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check VoilaNorbert API health and connectivity.

        Returns:
            Dictionary with health status and account info

        Raises:
            VoilaNorbertError: If health check fails
        """
        try:
            account = await self.get_account_info()
            return {
                "name": "voilanorbert",
                "healthy": True,
                "credits_remaining": account.credits_remaining,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            return {
                "name": "voilanorbert",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    def _parse_email_result(self, response: dict[str, Any]) -> VoilaNorbertEmailResult:
        """
        Parse API response into VoilaNorbertEmailResult.

        Args:
            response: Raw API response

        Returns:
            VoilaNorbertEmailResult dataclass
        """
        email_data = response.get("email", {})

        # Handle both nested and flat response formats
        if isinstance(email_data, dict):
            email = email_data.get("email")
            score = email_data.get("score", 0)
        else:
            email = response.get("email")
            score = response.get("score", 0)

        # Determine status based on response
        if response.get("searching", False):
            status = VoilaNorbertEmailStatus.SEARCHING
        elif email:
            status = VoilaNorbertEmailStatus.FOUND
        else:
            status = VoilaNorbertEmailStatus.NOT_FOUND

        return VoilaNorbertEmailResult(
            email=email,
            status=status,
            score=score if isinstance(score, int) else 0,
            first_name=response.get("first_name"),
            last_name=response.get("last_name"),
            company=response.get("company"),
            raw_response=response,
        )

    def _parse_verification_result(
        self, email: str, response: dict[str, Any]
    ) -> VoilaNorbertVerificationResult:
        """
        Parse verification API response.

        Args:
            email: Original email that was verified
            response: Raw API response

        Returns:
            VoilaNorbertVerificationResult dataclass
        """
        result = response.get("result", {})

        return VoilaNorbertVerificationResult(
            email=email,
            is_valid=result.get("valid", False),
            is_deliverable=result.get("deliverable", False),
            is_catch_all=result.get("catch_all", False),
            status=result.get("status", "unknown"),
            raw_response=response,
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any VoilaNorbert API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/search/name")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            VoilaNorbertError: If request fails
        """
        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            if isinstance(e, AuthenticationError | PaymentRequiredError | RateLimitError):
                raise
            raise VoilaNorbertError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e
