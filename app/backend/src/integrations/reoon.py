"""
Reoon Email Verifier API integration client.

Provides email verification and deliverability monitoring with two modes:
Quick (fast syntax/disposable checks) and Power (deep inbox verification).

API Documentation: https://www.reoon.com/articles/api-documentation-of-reoon-email-verifier/
Base URL: https://emailverifier.reoon.com/api/v1

Features:
- Single email verification (Quick and Power modes)
- Bulk email verification with async task processing
- Account balance checking
- Comprehensive verification statuses

Verification Modes:
- Quick: ~0.5 seconds, syntax/disposable/MX validation
- Power: Seconds to minutes, includes inbox existence checks

Rate Limits:
- Single endpoint: Max 5 concurrent threads
- Bulk: Up to 50,000 emails per task

Authentication:
- API key via query parameter (?key=YOUR_API_KEY)

Example:
    >>> from src.integrations.reoon import ReoonClient
    >>> client = ReoonClient(api_key="your-api-key")
    >>> result = await client.verify_email_quick("test@example.com")
    >>> print(result.status, result.overall_score)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class ReoonVerificationStatus(str, Enum):
    """Email verification status codes from Reoon API."""

    SAFE = "safe"
    VALID = "valid"
    INVALID = "invalid"
    DISABLED = "disabled"
    DISPOSABLE = "disposable"
    INBOX_FULL = "inbox_full"
    CATCH_ALL = "catch_all"
    ROLE_ACCOUNT = "role_account"
    SPAMTRAP = "spamtrap"
    UNKNOWN = "unknown"


class ReoonVerificationMode(str, Enum):
    """Verification mode for Reoon API."""

    QUICK = "quick"
    POWER = "power"


class ReoonBulkTaskStatus(str, Enum):
    """Bulk verification task status."""

    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FILE_NOT_FOUND = "file_not_found"
    FILE_LOADING_ERROR = "file_loading_error"
    ERROR = "error"


class ReoonError(IntegrationError):
    """Exception raised for Reoon API errors."""

    pass


@dataclass
class ReoonVerificationResult:
    """Result from single email verification."""

    email: str
    status: ReoonVerificationStatus
    overall_score: int
    is_safe_to_send: bool
    is_valid_syntax: bool
    is_disposable: bool
    is_role_account: bool
    can_connect_smtp: bool
    has_inbox_full: bool
    is_catch_all: bool
    is_deliverable: bool
    is_disabled: bool
    is_spamtrap: bool
    is_free_email: bool
    mx_accepts_mail: bool
    mx_records: list[str]
    verification_mode: ReoonVerificationMode
    username: str | None = None
    domain: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_safe(self) -> bool:
        """Check if email is safe to send."""
        return self.is_safe_to_send and self.status == ReoonVerificationStatus.SAFE

    @property
    def is_risky(self) -> bool:
        """Check if email is risky (catch-all, unknown, inbox full)."""
        return self.status in (
            ReoonVerificationStatus.CATCH_ALL,
            ReoonVerificationStatus.UNKNOWN,
            ReoonVerificationStatus.INBOX_FULL,
        )

    @property
    def should_not_send(self) -> bool:
        """Check if email should not be sent to."""
        return self.status in (
            ReoonVerificationStatus.INVALID,
            ReoonVerificationStatus.DISABLED,
            ReoonVerificationStatus.DISPOSABLE,
            ReoonVerificationStatus.SPAMTRAP,
        )


@dataclass
class ReoonAccountBalance:
    """Account balance information from Reoon API."""

    remaining_daily_credits: int
    remaining_instant_credits: int
    api_status: str
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def total_remaining_credits(self) -> int:
        """Get total remaining credits."""
        return self.remaining_daily_credits + self.remaining_instant_credits

    @property
    def has_credits(self) -> bool:
        """Check if account has remaining credits."""
        return self.total_remaining_credits > 0


@dataclass
class ReoonBulkTaskResult:
    """Result from creating a bulk verification task."""

    task_id: str
    status: str
    count_submitted: int
    count_duplicates_removed: int
    count_rejected_emails: int
    count_processing: int
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_created(self) -> bool:
        """Check if task was created successfully."""
        return self.status.lower() == "success" and bool(self.task_id)


@dataclass
class ReoonBulkVerificationStatus:
    """Status of a bulk verification task."""

    task_id: str
    name: str
    status: ReoonBulkTaskStatus
    count_total: int
    count_checked: int
    progress_percentage: float
    results: dict[str, dict[str, Any]]
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == ReoonBulkTaskStatus.COMPLETED

    @property
    def is_running(self) -> bool:
        """Check if task is still running."""
        return self.status in (ReoonBulkTaskStatus.WAITING, ReoonBulkTaskStatus.RUNNING)

    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.status in (
            ReoonBulkTaskStatus.FILE_NOT_FOUND,
            ReoonBulkTaskStatus.FILE_LOADING_ERROR,
            ReoonBulkTaskStatus.ERROR,
        )


class ReoonClient(BaseIntegrationClient):
    """
    Async client for Reoon Email Verifier API.

    Provides email verification with two modes:
    - Quick: Fast syntax and disposable checks (~0.5s)
    - Power: Deep verification including inbox checks (seconds to minutes)

    Attributes:
        BASE_URL: Base URL for Reoon API.

    Note:
        - Single endpoint: Max 5 concurrent threads
        - Bulk: Up to 50,000 emails per task
        - API key authentication via query parameter
    """

    BASE_URL = "https://emailverifier.reoon.com/api/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Reoon client.

        Args:
            api_key: Reoon API key from dashboard.
            timeout: Request timeout in seconds (default 120s for power mode).
            max_retries: Maximum retry attempts for transient errors.
        """
        super().__init__(
            name="reoon",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {self.name} client")

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for Reoon API requests.

        Note: Reoon uses query parameter authentication, not Bearer token.
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _add_api_key_to_params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        """
        Add API key to request parameters.

        Args:
            params: Existing query parameters.

        Returns:
            Parameters with API key added.
        """
        if params is None:
            params = {}
        params["key"] = self.api_key
        return params

    # -------------------------------------------------------------------------
    # Single Email Verification
    # -------------------------------------------------------------------------

    async def verify_email_quick(
        self,
        email: str,
    ) -> ReoonVerificationResult:
        """
        Verify an email address using Quick mode.

        Quick mode is extremely fast (~0.5s) but doesn't check inbox existence.
        Suitable for real-time validation at data entry points.

        Args:
            email: Email address to verify.

        Returns:
            ReoonVerificationResult with verification details.

        Raises:
            ReoonError: If verification fails.
            ValueError: If email is invalid.
        """
        return await self._verify_email(email, ReoonVerificationMode.QUICK)

    async def verify_email_power(
        self,
        email: str,
    ) -> ReoonVerificationResult:
        """
        Verify an email address using Power mode.

        Power mode performs deep verification including inbox existence checks.
        Takes longer (seconds to minutes) but provides more accurate results.

        Args:
            email: Email address to verify.

        Returns:
            ReoonVerificationResult with comprehensive verification details.

        Raises:
            ReoonError: If verification fails.
            ValueError: If email is invalid.
        """
        return await self._verify_email(email, ReoonVerificationMode.POWER)

    async def _verify_email(
        self,
        email: str,
        mode: ReoonVerificationMode,
    ) -> ReoonVerificationResult:
        """
        Internal method to verify an email address.

        Args:
            email: Email address to verify.
            mode: Verification mode (quick or power).

        Returns:
            ReoonVerificationResult with verification details.

        Raises:
            ReoonError: If verification fails.
            ValueError: If email is invalid.
        """
        if not email or not email.strip():
            raise ValueError("email is required")

        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

        params = self._add_api_key_to_params(
            {
                "email": email,
                "mode": mode.value,
            }
        )

        try:
            response = await self.get("/verify", params=params)
            return self._parse_verification_result(response, mode)

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] verify_email failed: {e}",
                extra={"email": email, "mode": mode.value},
            )
            raise ReoonError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Bulk Email Verification
    # -------------------------------------------------------------------------

    async def create_bulk_verification_task(
        self,
        emails: list[str],
        name: str | None = None,
    ) -> ReoonBulkTaskResult:
        """
        Create a bulk email verification task.

        Emails will be deduplicated and processed asynchronously.
        Use get_bulk_verification_status() to check progress and results.

        Args:
            emails: List of email addresses to verify (10-50,000).
            name: Optional task name (max 25 characters).

        Returns:
            ReoonBulkTaskResult with task ID and initial status.

        Raises:
            ReoonError: If task creation fails.
            ValueError: If email list is invalid.
        """
        if not emails:
            raise ValueError("emails list is required")
        if len(emails) < 10:
            raise ValueError("Bulk verification requires at least 10 emails")
        if len(emails) > 50000:
            raise ValueError("Maximum 50,000 emails per bulk verification task")

        # Clean and validate emails
        cleaned_emails = [e.strip().lower() for e in emails if e and e.strip()]
        if len(cleaned_emails) < 10:
            raise ValueError("At least 10 valid emails required after cleaning")

        payload: dict[str, Any] = {
            "emails": cleaned_emails,
            "key": self.api_key,
        }

        if name:
            payload["name"] = name[:25]  # Max 25 characters

        try:
            response = await self.post("/create-bulk-verification-task/", json=payload)

            return ReoonBulkTaskResult(
                task_id=response.get("task_id", ""),
                status=response.get("status", ""),
                count_submitted=response.get("count_submitted", 0),
                count_duplicates_removed=response.get("count_duplicates_removed", 0),
                count_rejected_emails=response.get("count_rejected_emails", 0),
                count_processing=response.get("count_processing", 0),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] create_bulk_verification_task failed: {e}",
                extra={"email_count": len(emails)},
            )
            raise ReoonError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def get_bulk_verification_status(
        self,
        task_id: str | int,
    ) -> ReoonBulkVerificationStatus:
        """
        Get the status and results of a bulk verification task.

        Poll this endpoint to check progress and retrieve results
        when the task is completed.

        Args:
            task_id: Task ID from create_bulk_verification_task().

        Returns:
            ReoonBulkVerificationStatus with progress and results.

        Raises:
            ReoonError: If status retrieval fails.
            ValueError: If task_id is invalid.
        """
        # Handle both int and string task_ids from API
        task_id_str = str(task_id).strip() if task_id is not None else ""
        if not task_id_str:
            raise ValueError("task_id is required")

        params = self._add_api_key_to_params(
            {
                "task_id": task_id_str,
            }
        )

        try:
            response = await self.get("/get-result-bulk-verification-task/", params=params)

            status_str = response.get("status", "unknown").lower()
            try:
                status = ReoonBulkTaskStatus(status_str)
            except ValueError:
                status = ReoonBulkTaskStatus.ERROR

            return ReoonBulkVerificationStatus(
                task_id=response.get("task_id", task_id),
                name=response.get("name", ""),
                status=status,
                count_total=response.get("count_total", 0),
                count_checked=response.get("count_checked", 0),
                progress_percentage=response.get("progress_percentage", 0.0),
                results=response.get("results", {}),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(
                f"[{self.name}] get_bulk_verification_status failed: {e}",
                extra={"task_id": task_id},
            )
            raise ReoonError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Account Management
    # -------------------------------------------------------------------------

    async def get_account_balance(self) -> ReoonAccountBalance:
        """
        Check account balance and remaining credits.

        Returns:
            ReoonAccountBalance with credit information.

        Raises:
            ReoonError: If balance retrieval fails.
        """
        params = self._add_api_key_to_params({})

        try:
            response = await self.get("/check-account-balance/", params=params)

            return ReoonAccountBalance(
                remaining_daily_credits=response.get("remaining_daily_credits", 0),
                remaining_instant_credits=response.get("remaining_instant_credits", 0),
                api_status=response.get("api_status", ""),
                raw_response=response,
            )

        except IntegrationError as e:
            logger.error(f"[{self.name}] get_account_balance failed: {e}")
            raise ReoonError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Health Check & Utility
    # -------------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """
        Check Reoon API health and connectivity.

        Returns:
            Health check status with account balance info.
        """
        try:
            balance = await self.get_account_balance()
            return {
                "name": self.name,
                "healthy": True,
                "has_credits": balance.has_credits,
                "remaining_credits": balance.total_remaining_credits,
                "base_url": self.BASE_URL,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "name": self.name,
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
        Call any Reoon API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/verify").
            method: HTTP method (GET, POST, etc.).
            **kwargs: Additional arguments passed to the request.

        Returns:
            Raw API response as dictionary.

        Raises:
            ReoonError: If request fails.

        Example:
            >>> result = await client.call_endpoint(
            ...     "/new-endpoint",
            ...     method="GET",
            ...     params={"email": "test@example.com"}
            ... )
        """
        # Add API key to params for GET requests
        if method.upper() == "GET":
            kwargs["params"] = self._add_api_key_to_params(kwargs.get("params"))
        # For POST requests, add to JSON body
        elif method.upper() == "POST" and "json" in kwargs:
            kwargs["json"]["key"] = self.api_key

        try:
            return await self._request_with_retry(method, endpoint, **kwargs)
        except IntegrationError as e:
            raise ReoonError(
                message=str(e),
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _parse_verification_result(
        self,
        data: dict[str, Any],
        mode: ReoonVerificationMode,
    ) -> ReoonVerificationResult:
        """Parse raw API response into ReoonVerificationResult."""
        status_str = data.get("status", "unknown").lower()
        try:
            status = ReoonVerificationStatus(status_str)
        except ValueError:
            status = ReoonVerificationStatus.UNKNOWN

        # Extract MX records (may be string or list)
        mx_records_raw = data.get("mx_records", [])
        if isinstance(mx_records_raw, str):
            mx_records = [mx_records_raw] if mx_records_raw else []
        elif isinstance(mx_records_raw, list):
            mx_records = mx_records_raw
        else:
            mx_records = []

        return ReoonVerificationResult(
            email=data.get("email", ""),
            status=status,
            overall_score=data.get("overall_score", 0),
            is_safe_to_send=data.get("is_safe_to_send", False),
            is_valid_syntax=data.get("is_valid_syntax", False),
            is_disposable=data.get("is_disposable", False),
            is_role_account=data.get("is_role_account", False),
            can_connect_smtp=data.get("can_connect_smtp", False),
            has_inbox_full=data.get("has_inbox_full", False),
            is_catch_all=data.get("is_catch_all", False),
            is_deliverable=data.get("is_deliverable", False),
            is_disabled=data.get("is_disabled", False),
            is_spamtrap=data.get("is_spamtrap", False),
            is_free_email=data.get("is_free_email", False),
            mx_accepts_mail=data.get("mx_accepts_mail", False),
            mx_records=mx_records,
            verification_mode=mode,
            username=data.get("username"),
            domain=data.get("domain"),
            raw_response=data,
        )
