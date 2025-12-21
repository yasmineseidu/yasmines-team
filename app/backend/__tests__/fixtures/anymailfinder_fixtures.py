"""
Test fixtures for Anymailfinder integration tests.

Provides mock data and response fixtures for testing the AnymailfinderClient
without making actual API calls.
"""

from typing import Any

# Sample API responses
VALID_EMAIL_RESPONSE: dict[str, Any] = {
    "email": "john.doe@microsoft.com",
    "email_status": "valid",
    "valid_email": "john.doe@microsoft.com",
}

RISKY_EMAIL_RESPONSE: dict[str, Any] = {
    "email": "john.doe@example.com",
    "email_status": "risky",
    "valid_email": None,
}

NOT_FOUND_RESPONSE: dict[str, Any] = {
    "email": None,
    "email_status": "not_found",
    "valid_email": None,
}

BLACKLISTED_RESPONSE: dict[str, Any] = {
    "email": "spam@badcompany.com",
    "email_status": "blacklisted",
    "valid_email": None,
}

# Email verification responses
VERIFICATION_VALID_RESPONSE: dict[str, Any] = {
    "email_status": "valid",
    "input": {"email": "test@example.com"},
}

VERIFICATION_INVALID_RESPONSE: dict[str, Any] = {
    "email_status": "invalid",
    "input": {"email": "invalid@nonexistent.com"},
}

VERIFICATION_RISKY_RESPONSE: dict[str, Any] = {
    "email_status": "risky",
    "input": {"email": "catchall@company.com"},
}

# Company emails response
COMPANY_EMAILS_RESPONSE: dict[str, Any] = {
    "domain": "microsoft.com",
    "emails": [
        {
            "email": "john.doe@microsoft.com",
            "email_status": "valid",
            "valid_email": "john.doe@microsoft.com",
        },
        {
            "email": "jane.smith@microsoft.com",
            "email_status": "valid",
            "valid_email": "jane.smith@microsoft.com",
        },
        {
            "email": "unknown@microsoft.com",
            "email_status": "risky",
            "valid_email": None,
        },
    ],
}

# Decision maker response
DECISION_MAKER_RESPONSE: dict[str, Any] = {
    "email": "ceo@startup.com",
    "email_status": "valid",
    "valid_email": "ceo@startup.com",
    "name": "John Smith",
    "title": "CEO",
}

# Account info response
ACCOUNT_INFO_RESPONSE: dict[str, Any] = {
    "email": "user@company.com",
    "credits_remaining": 1000,
    "plan": "pro",
}

ACCOUNT_LOW_CREDITS_RESPONSE: dict[str, Any] = {
    "email": "user@company.com",
    "credits_remaining": 5,
    "plan": "starter",
}

# Error responses
UNAUTHORIZED_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key",
    "message": "The provided API key is invalid or expired",
}

PAYMENT_REQUIRED_RESPONSE: dict[str, Any] = {
    "error": "Insufficient credits",
    "message": "Your account has insufficient credits. Please top up to continue.",
}

BAD_REQUEST_RESPONSE: dict[str, Any] = {
    "error": "Bad request",
    "message": "Missing required parameter: domain",
}

# Test data for requests
SAMPLE_PERSON_SEARCH = {
    "first_name": "John",
    "last_name": "Doe",
    "domain": "microsoft.com",
}

SAMPLE_FULL_NAME_SEARCH = {
    "full_name": "John Doe",
    "domain": "microsoft.com",
}

SAMPLE_COMPANY_NAME_SEARCH = {
    "first_name": "Jane",
    "last_name": "Smith",
    "company_name": "Microsoft Corporation",
}

SAMPLE_DECISION_MAKER_SEARCH = {
    "domain": "startup.com",
    "job_title": "CEO",
    "seniority": "C-Level",
}

SAMPLE_EMAILS_TO_VERIFY = [
    "valid@example.com",
    "invalid@nonexistent.com",
    "catchall@company.com",
]
