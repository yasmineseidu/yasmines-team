"""
Sample test data for live integration testing.

This module contains real-world test data for validating integration clients
against live APIs. All data points are carefully selected to:
1. Minimize credit usage (use well-known, easily findable contacts)
2. Provide predictable results for validation
3. Cover edge cases and error scenarios

Usage:
    from __tests__.fixtures.live_test_data import SAMPLE_CONTACTS, SAMPLE_DOMAINS
"""

from dataclasses import dataclass


@dataclass
class SampleContact:
    """Sample contact for email finding tests."""

    first_name: str
    last_name: str
    domain: str
    company: str
    linkedin_url: str | None = None
    expected_email_pattern: str | None = None  # Regex pattern if known
    notes: str = ""


@dataclass
class SampleDomain:
    """Sample domain for domain-based tests."""

    domain: str
    company_name: str
    expected_mx: bool = True
    notes: str = ""


@dataclass
class SampleEmail:
    """Sample email for verification tests."""

    email: str
    expected_valid: bool
    expected_deliverable: bool | None = None
    category: str = "normal"  # normal, disposable, catch_all, invalid
    notes: str = ""


# =============================================================================
# SAMPLE CONTACTS - Well-known executives for email finding
# =============================================================================
SAMPLE_CONTACTS = [
    SampleContact(
        first_name="Sundar",
        last_name="Pichai",
        domain="google.com",
        company="Google",
        linkedin_url="https://www.linkedin.com/in/sundarpichai",
        notes="CEO of Google - well indexed",
    ),
    SampleContact(
        first_name="Satya",
        last_name="Nadella",
        domain="microsoft.com",
        company="Microsoft",
        linkedin_url="https://www.linkedin.com/in/satyanadella",
        notes="CEO of Microsoft - well indexed",
    ),
    SampleContact(
        first_name="Tim",
        last_name="Cook",
        domain="apple.com",
        company="Apple",
        linkedin_url="https://www.linkedin.com/in/tim-cook-1b548810/",
        notes="CEO of Apple - well indexed",
    ),
    SampleContact(
        first_name="Mark",
        last_name="Zuckerberg",
        domain="meta.com",
        company="Meta",
        notes="CEO of Meta - may be hard to find",
    ),
    SampleContact(
        first_name="Elon",
        last_name="Musk",
        domain="tesla.com",
        company="Tesla",
        notes="CEO of Tesla - challenging due to privacy",
    ),
]

# Smaller test contact for quick validation
QUICK_TEST_CONTACT = SampleContact(
    first_name="John",
    last_name="Smith",
    domain="example.com",
    company="Example Corp",
    notes="Generic test - will likely not find",
)


# =============================================================================
# SAMPLE DOMAINS - For domain-based lookups
# =============================================================================
SAMPLE_DOMAINS = [
    SampleDomain(
        domain="google.com",
        company_name="Google",
        expected_mx=True,
        notes="Large tech company with proper MX",
    ),
    SampleDomain(
        domain="microsoft.com",
        company_name="Microsoft",
        expected_mx=True,
        notes="Large tech company with proper MX",
    ),
    SampleDomain(
        domain="stripe.com",
        company_name="Stripe",
        expected_mx=True,
        notes="Tech startup with proper email setup",
    ),
    SampleDomain(
        domain="invalid-domain-that-does-not-exist-12345.com",
        company_name="Invalid",
        expected_mx=False,
        notes="Non-existent domain for error testing",
    ),
]


# =============================================================================
# SAMPLE EMAILS - For verification testing
# =============================================================================
SAMPLE_EMAILS = [
    # Valid emails (known to exist)
    SampleEmail(
        email="test@gmail.com",
        expected_valid=True,
        expected_deliverable=False,  # Likely catch-all or reserved
        category="normal",
        notes="Standard Gmail test address",
    ),
    SampleEmail(
        email="info@google.com",
        expected_valid=True,
        expected_deliverable=True,
        category="normal",
        notes="Public Google contact email",
    ),
    SampleEmail(
        email="support@stripe.com",
        expected_valid=True,
        expected_deliverable=True,
        category="normal",
        notes="Known Stripe support email",
    ),
    # Invalid emails (syntax or domain issues)
    SampleEmail(
        email="invalid@nonexistent-domain-xyz123.com",
        expected_valid=False,
        expected_deliverable=False,
        category="invalid",
        notes="Domain does not exist",
    ),
    SampleEmail(
        email="definitely.fake.email.12345@gmail.com",
        expected_valid=True,  # Valid format
        expected_deliverable=False,  # But doesn't exist
        category="invalid",
        notes="Valid format but non-existent mailbox",
    ),
    # Disposable emails
    SampleEmail(
        email="test@mailinator.com",
        expected_valid=True,
        expected_deliverable=True,
        category="disposable",
        notes="Known disposable email provider",
    ),
    SampleEmail(
        email="test@tempmail.com",
        expected_valid=True,
        expected_deliverable=True,
        category="disposable",
        notes="Known temp mail provider",
    ),
]

# Quick test email for validation
QUICK_TEST_EMAIL = SampleEmail(
    email="info@google.com",
    expected_valid=True,
    expected_deliverable=True,
    notes="Reliable Google email for quick tests",
)


# =============================================================================
# SAMPLE LINKEDIN URLS
# =============================================================================
SAMPLE_LINKEDIN_URLS = [
    "https://www.linkedin.com/in/sundarpichai",
    "https://www.linkedin.com/in/satyanadella",
    "https://www.linkedin.com/in/jeffweiner08",
    "https://linkedin.com/in/raborman",
]


# =============================================================================
# SAMPLE COMPANIES - For company lookup tests
# =============================================================================
SAMPLE_COMPANIES = [
    {
        "name": "Google",
        "domain": "google.com",
        "industry": "Technology",
        "size": "100000+",
    },
    {
        "name": "Stripe",
        "domain": "stripe.com",
        "industry": "Financial Technology",
        "size": "5000-10000",
    },
    {
        "name": "OpenAI",
        "domain": "openai.com",
        "industry": "Artificial Intelligence",
        "size": "1000-5000",
    },
]


# =============================================================================
# TEST CAMPAIGN DATA - For Instantly tests
# =============================================================================
SAMPLE_CAMPAIGN_DATA = {
    "name": "Test Campaign - Integration Test",
    "subject": "Quick Question",
    "body": "Hi {{firstName}}, this is a test email.",
}

SAMPLE_LEAD_DATA = {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "company_name": "Test Company",
}
