"""
Test fixtures for Tomba integration tests.

Provides mock responses and test data for unit testing
the TombaClient without making real API calls.
"""

from typing import Any


def create_account_info_response(
    email: str = "user@example.com",
    user_id: int = 12345,
    plan_name: str = "Starter",
    search_available: int = 100,
    search_used: int = 25,
    verifications_available: int = 200,
    verifications_used: int = 50,
) -> dict[str, Any]:
    """Create mock response for /me endpoint."""
    return {
        "data": {
            "user_id": user_id,
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "requests": {
                "search": {
                    "available": search_available,
                    "used": search_used,
                },
                "verifications": {
                    "available": verifications_available,
                    "used": verifications_used,
                },
                "phone": {
                    "available": 10,
                    "used": 0,
                },
            },
            "pricing": {
                "name": plan_name,
            },
        },
    }


def create_domain_search_response(
    domain: str = "stripe.com",
    emails: list[dict[str, Any]] | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    """Create mock response for domain search."""
    if emails is None:
        emails = [
            {
                "email": "john.doe@stripe.com",
                "first_name": "John",
                "last_name": "Doe",
                "full_name": "John Doe",
                "position": "Software Engineer",
                "department": "engineering",
                "type": "personal",
                "seniority": "senior",
                "linkedin": "https://linkedin.com/in/johndoe",
                "twitter": "@johndoe",
                "phone_number": "+1-555-123-4567",
                "sources": [{"uri": "https://example.com", "extracted_on": "2024-01-15"}],
                "verification": {"status": "valid"},
                "score": 95,
            },
            {
                "email": "jane.smith@stripe.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "full_name": "Jane Smith",
                "position": "Product Manager",
                "department": "product",
                "type": "personal",
                "seniority": "executive",
                "linkedin": "https://linkedin.com/in/janesmith",
                "twitter": None,
                "phone_number": None,
                "sources": [],
                "verification": {"status": "valid"},
                "score": 90,
            },
        ]

    return {
        "data": {
            "organization": {
                "organization": "Stripe Inc",
                "country": "United States",
                "state": "California",
                "city": "San Francisco",
                "postal_code": "94103",
                "street_address": "354 Oyster Point Blvd",
                "accept_all": False,
                "website_url": f"https://{domain}",
            },
            "emails": emails,
            "disposable": False,
            "webmail": False,
            "pattern": "{first}.{last}",
        },
        "meta": {
            "total": total if total is not None else len(emails),
            "page": 1,
            "limit": 10,
        },
    }


def create_domain_search_empty_response(domain: str = "nonexistent.com") -> dict[str, Any]:
    """Create mock response for domain with no emails."""
    return {
        "data": {
            "organization": {},
            "emails": [],
            "disposable": False,
            "webmail": False,
            "pattern": None,
        },
        "meta": {
            "total": 0,
            "page": 1,
            "limit": 10,
        },
    }


def create_email_finder_response(
    email: str = "john.doe@stripe.com",
    first_name: str = "John",
    last_name: str = "Doe",
    confidence: int = 95,
) -> dict[str, Any]:
    """Create mock response for email finder."""
    return {
        "data": {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "domain": email.split("@")[1] if "@" in email else None,
            "position": "Software Engineer",
            "department": "engineering",
            "seniority": "senior",
            "linkedin": "https://linkedin.com/in/johndoe",
            "twitter": "@johndoe",
            "phone_number": "+1-555-123-4567",
            "company": "Stripe Inc",
            "type": "personal",
            "score": confidence,
            "sources": [{"uri": "https://example.com", "extracted_on": "2024-01-15"}],
        },
    }


def create_email_finder_not_found_response() -> dict[str, Any]:
    """Create mock response for email not found."""
    return {
        "data": {
            "email": None,
            "first_name": None,
            "last_name": None,
            "full_name": None,
            "domain": None,
            "position": None,
            "department": None,
            "seniority": None,
            "linkedin": None,
            "twitter": None,
            "phone_number": None,
            "company": None,
            "type": None,
            "score": 0,
            "sources": [],
        },
    }


def create_verification_response(
    email: str = "john.doe@stripe.com",
    status: str = "valid",
    accept_all: bool = False,
    disposable: bool = False,
) -> dict[str, Any]:
    """Create mock response for email verification."""
    return {
        "data": {
            "email": {
                "email": email,
            },
            "status": status,
            "result": "deliverable" if status == "valid" else "undeliverable",
            "accept_all": accept_all,
            "disposable": disposable,
            "webmail": False,
            "mx_records": True,
            "smtp_server": True,
            "smtp_check": True,
            "block": False,
            "sources": [{"uri": "https://example.com", "extracted_on": "2024-01-15"}],
        },
    }


def create_verification_invalid_response(
    email: str = "invalid@nonexistent.com",
) -> dict[str, Any]:
    """Create mock response for invalid email verification."""
    return {
        "data": {
            "email": {
                "email": email,
            },
            "status": "invalid",
            "result": "undeliverable",
            "accept_all": False,
            "disposable": False,
            "webmail": False,
            "mx_records": False,
            "smtp_server": False,
            "smtp_check": False,
            "block": False,
            "sources": [],
        },
    }


def create_email_count_response(
    domain: str = "stripe.com",
    total: int = 150,
    personal: int = 120,
    generic: int = 30,
) -> dict[str, Any]:
    """Create mock response for email count."""
    return {
        "data": {
            "total": total,
            "personal_emails": personal,
            "generic_emails": generic,
            "department": {
                "engineering": 50,
                "sales": 30,
                "marketing": 25,
                "support": 20,
                "executive": 10,
                "finance": 8,
                "hr": 7,
            },
            "seniority": {
                "junior": 30,
                "senior": 50,
                "executive": 20,
                "director": 25,
                "vp": 15,
                "c_level": 10,
            },
        },
    }


def create_linkedin_email_response(
    email: str = "john.doe@stripe.com",
    linkedin_url: str = "https://linkedin.com/in/johndoe",
) -> dict[str, Any]:
    """Create mock response for LinkedIn email finder."""
    return {
        "data": {
            "email": email,
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "domain": email.split("@")[1] if "@" in email else None,
            "position": "Software Engineer",
            "department": "engineering",
            "seniority": "senior",
            "linkedin": linkedin_url,
            "twitter": "@johndoe",
            "phone_number": "+1-555-123-4567",
            "company": "Stripe Inc",
            "type": "personal",
            "score": 95,
            "sources": [],
        },
    }


def create_error_response(
    message: str = "Invalid request",
    code: int = 400,
) -> dict[str, Any]:
    """Create mock error response."""
    return {
        "error": message,
        "code": code,
    }


# Sample test data
SAMPLE_DOMAINS = [
    "stripe.com",
    "airbnb.com",
    "figma.com",
    "notion.so",
]

SAMPLE_LINKEDIN_URLS = [
    "https://linkedin.com/in/satyanadella",
    "https://www.linkedin.com/in/jeffweiner08",
    "https://linkedin.com/in/johndoe",
]

SAMPLE_PERSONS = [
    {"first_name": "John", "last_name": "Doe", "domain": "stripe.com"},
    {"first_name": "Jane", "last_name": "Smith", "domain": "airbnb.com"},
    {"first_name": "Bob", "last_name": "Johnson", "domain": "figma.com"},
]

SAMPLE_EMAILS_TO_VERIFY = [
    "john.doe@stripe.com",
    "jane.smith@airbnb.com",
    "contact@figma.com",
]
