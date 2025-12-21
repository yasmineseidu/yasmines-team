"""
Test fixtures for Findymail integration tests.

Provides mock responses and test data for unit testing
the FindymailClient without making real API calls.
"""

from typing import Any


def create_email_found_response(
    email: str = "jane.smith@techstartup.com",
    status: str = "verified",
    first_name: str = "Jane",
    last_name: str = "Smith",
    domain: str = "techstartup.com",
) -> dict[str, Any]:
    """Create mock response for successful email find."""
    return {
        "email": email,
        "status": status,
        "first_name": first_name,
        "last_name": last_name,
        "domain": domain,
    }


def create_email_not_found_response() -> dict[str, Any]:
    """Create mock response for email not found."""
    return {
        "email": None,
        "status": "not_found",
    }


def create_catch_all_response(
    email: str = "contact@catchall.com",
) -> dict[str, Any]:
    """Create mock response for catch-all domain."""
    return {
        "email": email,
        "status": "catch_all",
    }


def create_verification_success_response(
    email: str = "test@example.com",
    status: str = "verified",
    deliverable: bool = True,
    catch_all: bool = False,
) -> dict[str, Any]:
    """Create mock response for email verification."""
    return {
        "email": email,
        "status": status,
        "deliverable": deliverable,
        "catch_all": catch_all,
    }


def create_verification_invalid_response(
    email: str = "invalid@nonexistent.com",
) -> dict[str, Any]:
    """Create mock response for invalid email verification."""
    return {
        "email": email,
        "status": "invalid",
        "deliverable": False,
        "catch_all": False,
    }


def create_phone_found_response(
    phone: str = "+1-555-123-4567",
) -> dict[str, Any]:
    """Create mock response for phone found."""
    return {
        "phone": phone,
    }


def create_phone_not_found_response() -> dict[str, Any]:
    """Create mock response for phone not found."""
    return {
        "phone": None,
    }


def create_error_response(
    error: str = "Invalid request",
    code: str = "BAD_REQUEST",
) -> dict[str, Any]:
    """Create mock error response."""
    return {
        "error": error,
        "code": code,
    }


# Sample test data
SAMPLE_LINKEDIN_URLS = [
    "https://linkedin.com/in/satyanadella",
    "https://www.linkedin.com/in/jeffweiner08",
    "https://linkedin.com/in/raborchestrato",
]

SAMPLE_TECH_COMPANIES = [
    {"name": "Jane Smith", "domain": "stripe.com"},
    {"name": "John Doe", "domain": "airbnb.com"},
    {"name": "Sarah Connor", "domain": "figma.com"},
]

SAMPLE_EMAILS_TO_VERIFY = [
    "ceo@stripe.com",
    "founder@techstartup.io",
    "sales@enterprise.com",
]
