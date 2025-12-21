"""
Fixtures and sample data for Reoon Email Verifier API testing.

This module provides:
- Sample data for all endpoint testing
- Expected response schemas for validation
- Helper functions for test data generation
"""

import uuid
from typing import Any


def generate_test_email() -> str:
    """Generate unique test email address."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test_{unique_id}@example-test-domain.com"


def generate_bulk_emails(count: int = 15) -> list[str]:
    """Generate a list of unique test email addresses."""
    return [generate_test_email() for _ in range(count)]


# Sample verification response for Quick mode
SAMPLE_QUICK_VERIFICATION_RESPONSE: dict[str, Any] = {
    "email": "test@example.com",
    "status": "valid",
    "overall_score": 75,
    "is_safe_to_send": True,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": False,
    "can_connect_smtp": False,  # Not checked in quick mode
    "has_inbox_full": False,
    "is_catch_all": False,
    "is_deliverable": True,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mx1.example.com", "mx2.example.com"],
    "verification_mode": "quick",
    "username": "test",
    "domain": "example.com",
}

# Sample verification response for Power mode
SAMPLE_POWER_VERIFICATION_RESPONSE: dict[str, Any] = {
    "email": "real.person@company.com",
    "status": "safe",
    "overall_score": 95,
    "is_safe_to_send": True,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": False,
    "can_connect_smtp": True,
    "has_inbox_full": False,
    "is_catch_all": False,
    "is_deliverable": True,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mail.company.com"],
    "verification_mode": "power",
    "username": "real.person",
    "domain": "company.com",
}

# Sample invalid email response
SAMPLE_INVALID_EMAIL_RESPONSE: dict[str, Any] = {
    "email": "invalid@nonexistent-domain-xyz.com",
    "status": "invalid",
    "overall_score": 0,
    "is_safe_to_send": False,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": False,
    "can_connect_smtp": False,
    "has_inbox_full": False,
    "is_catch_all": False,
    "is_deliverable": False,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": False,
    "mx_records": [],
    "verification_mode": "power",
    "username": "invalid",
    "domain": "nonexistent-domain-xyz.com",
}

# Sample disposable email response
SAMPLE_DISPOSABLE_EMAIL_RESPONSE: dict[str, Any] = {
    "email": "temp@mailinator.com",
    "status": "disposable",
    "overall_score": 10,
    "is_safe_to_send": False,
    "is_valid_syntax": True,
    "is_disposable": True,
    "is_role_account": False,
    "can_connect_smtp": True,
    "has_inbox_full": False,
    "is_catch_all": True,
    "is_deliverable": True,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mx.mailinator.com"],
    "verification_mode": "power",
    "username": "temp",
    "domain": "mailinator.com",
}

# Sample catch-all response
SAMPLE_CATCH_ALL_RESPONSE: dict[str, Any] = {
    "email": "any@catch-all-domain.com",
    "status": "catch_all",
    "overall_score": 60,
    "is_safe_to_send": False,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": False,
    "can_connect_smtp": True,
    "has_inbox_full": False,
    "is_catch_all": True,
    "is_deliverable": True,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mail.catch-all-domain.com"],
    "verification_mode": "power",
    "username": "any",
    "domain": "catch-all-domain.com",
}

# Sample role account response
SAMPLE_ROLE_ACCOUNT_RESPONSE: dict[str, Any] = {
    "email": "support@company.com",
    "status": "role_account",
    "overall_score": 50,
    "is_safe_to_send": False,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": True,
    "can_connect_smtp": True,
    "has_inbox_full": False,
    "is_catch_all": False,
    "is_deliverable": True,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mail.company.com"],
    "verification_mode": "power",
    "username": "support",
    "domain": "company.com",
}

# Sample inbox full response
SAMPLE_INBOX_FULL_RESPONSE: dict[str, Any] = {
    "email": "full@company.com",
    "status": "inbox_full",
    "overall_score": 30,
    "is_safe_to_send": False,
    "is_valid_syntax": True,
    "is_disposable": False,
    "is_role_account": False,
    "can_connect_smtp": True,
    "has_inbox_full": True,
    "is_catch_all": False,
    "is_deliverable": False,
    "is_disabled": False,
    "is_spamtrap": False,
    "is_free_email": False,
    "mx_accepts_mail": True,
    "mx_records": ["mail.company.com"],
    "verification_mode": "power",
    "username": "full",
    "domain": "company.com",
}

# Sample account balance response
SAMPLE_ACCOUNT_BALANCE_RESPONSE: dict[str, Any] = {
    "api_status": "active",
    "remaining_daily_credits": 500,
    "remaining_instant_credits": 1000,
    "status": "success",
}

# Sample bulk task creation response
SAMPLE_BULK_TASK_CREATED_RESPONSE: dict[str, Any] = {
    "status": "success",
    "task_id": "task-123-abc-456",
    "count_submitted": 100,
    "count_duplicates_removed": 5,
    "count_rejected_emails": 2,
    "count_processing": 93,
}

# Sample bulk task status - running
SAMPLE_BULK_TASK_RUNNING_RESPONSE: dict[str, Any] = {
    "task_id": "task-123-abc-456",
    "name": "Test Bulk Verification",
    "status": "running",
    "count_total": 93,
    "count_checked": 45,
    "progress_percentage": 48.4,
    "results": {},
}

# Sample bulk task status - completed
SAMPLE_BULK_TASK_COMPLETED_RESPONSE: dict[str, Any] = {
    "task_id": "task-123-abc-456",
    "name": "Test Bulk Verification",
    "status": "completed",
    "count_total": 93,
    "count_checked": 93,
    "progress_percentage": 100.0,
    "results": {
        "test1@example.com": {
            "status": "safe",
            "overall_score": 95,
            "is_safe_to_send": True,
        },
        "test2@example.com": {
            "status": "invalid",
            "overall_score": 0,
            "is_safe_to_send": False,
        },
    },
}

# Expected response fields for validation
VERIFICATION_RESPONSE_FIELDS: set[str] = {
    "email",
    "status",
    "overall_score",
    "is_safe_to_send",
    "is_valid_syntax",
    "is_disposable",
    "is_role_account",
    "mx_accepts_mail",
}

ACCOUNT_BALANCE_FIELDS: set[str] = {
    "api_status",
    "remaining_daily_credits",
    "remaining_instant_credits",
}

BULK_TASK_CREATED_FIELDS: set[str] = {
    "status",
    "task_id",
    "count_submitted",
    "count_processing",
}

BULK_TASK_STATUS_FIELDS: set[str] = {
    "task_id",
    "status",
    "count_total",
    "count_checked",
    "progress_percentage",
}

# Verification status values
VERIFICATION_STATUS_VALUES: list[str] = [
    "safe",
    "valid",
    "invalid",
    "disabled",
    "disposable",
    "inbox_full",
    "catch_all",
    "role_account",
    "spamtrap",
    "unknown",
]

# Bulk task status values
BULK_TASK_STATUS_VALUES: list[str] = [
    "waiting",
    "running",
    "completed",
    "file_not_found",
    "file_loading_error",
]


def create_verification_response(
    email: str,
    status: str = "safe",
    overall_score: int = 95,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a verification response with optional overrides."""
    username, domain = email.split("@") if "@" in email else ("", "")
    response = {
        "email": email,
        "status": status,
        "overall_score": overall_score,
        "is_safe_to_send": status == "safe",
        "is_valid_syntax": True,
        "is_disposable": status == "disposable",
        "is_role_account": status == "role_account",
        "can_connect_smtp": True,
        "has_inbox_full": status == "inbox_full",
        "is_catch_all": status == "catch_all",
        "is_deliverable": status not in ["invalid", "disabled", "inbox_full"],
        "is_disabled": status == "disabled",
        "is_spamtrap": status == "spamtrap",
        "is_free_email": False,
        "mx_accepts_mail": True,
        "mx_records": [f"mx.{domain}"] if domain else [],
        "verification_mode": "power",
        "username": username,
        "domain": domain,
    }
    response.update(overrides)
    return response


def create_bulk_task_status_response(
    task_id: str,
    status: str = "completed",
    count_total: int = 100,
    count_checked: int | None = None,
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a bulk task status response with optional overrides."""
    if count_checked is None:
        count_checked = count_total if status == "completed" else count_total // 2
    progress = (count_checked / count_total * 100) if count_total > 0 else 0.0

    return {
        "task_id": task_id,
        "name": "Test Verification Task",
        "status": status,
        "count_total": count_total,
        "count_checked": count_checked,
        "progress_percentage": progress,
        "results": results or {},
    }
