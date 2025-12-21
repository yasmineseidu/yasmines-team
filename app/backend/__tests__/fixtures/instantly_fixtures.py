"""
Fixtures and sample data for Instantly.ai API live testing.

This module provides:
- Sample data for all endpoint testing
- Expected response schemas for validation
- Helper functions for test data generation
"""

import uuid
from datetime import datetime
from typing import Any


def generate_unique_campaign_name() -> str:
    """Generate unique campaign name for testing."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"Test_Campaign_{timestamp}_{unique_id}"


def generate_test_email() -> str:
    """Generate unique test email address."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test_{unique_id}@example-test-domain.com"


# Sample campaign schedule configuration
# NOTE: Instantly API V2 uses numeric day indices:
# 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
SAMPLE_CAMPAIGN_SCHEDULE: dict[str, Any] = {
    "schedules": [
        {
            "name": "Test Schedule",
            "timing": {
                "from": "09:00",
                "to": "17:00",
            },
            "days": {
                "1": True,  # Monday
                "2": True,  # Tuesday
                "3": True,  # Wednesday
                "4": True,  # Thursday
                "5": True,  # Friday
            },
            "timezone": "America/Chicago",
        }
    ]
}

# Sample campaign data for creation
SAMPLE_CAMPAIGN_DATA: dict[str, Any] = {
    "name": "Test Campaign - Live API Test",
    "campaign_schedule": SAMPLE_CAMPAIGN_SCHEDULE,
}

# Sample lead data for single lead creation
SAMPLE_LEAD_DATA: dict[str, Any] = {
    "email": "john.doe@test-company.com",
    "first_name": "John",
    "last_name": "Doe",
    "company_name": "Test Company Inc",
    "website": "https://test-company.com",
    "phone": "+1-555-123-4567",
    "custom_variables": {
        "industry": "Technology",
        "company_size": "50-200",
        "lead_source": "live_api_test",
    },
}

# Sample bulk leads data (10 leads for testing)
SAMPLE_BULK_LEADS: list[dict[str, Any]] = [
    {
        "email": f"lead{i}@test-company-{i}.com",
        "first_name": f"Lead{i}",
        "last_name": f"Test{i}",
        "company_name": f"Test Company {i}",
        "custom_variables": {"batch": "live_api_test", "index": i},
    }
    for i in range(1, 11)
]

# Interest status values for testing
INTEREST_STATUS_VALUES: list[str] = [
    "interested",
    "not_interested",
    "meeting_booked",
    "meeting_completed",
    "closed",
    "out_of_office",
    "wrong_person",
]

# Expected response fields for validation
CAMPAIGN_RESPONSE_FIELDS: set[str] = {
    "id",
    "name",
    "status",
}

LEAD_RESPONSE_FIELDS: set[str] = {
    "id",
    "email",
}

ANALYTICS_RESPONSE_FIELDS: set[str] = {
    "total_leads",
    "contacted",
    "emails_sent",
    "emails_opened",
    "emails_clicked",
    "emails_replied",
    "emails_bounced",
}

# Campaign status codes
CAMPAIGN_STATUS_CODES: dict[str, int] = {
    "DRAFT": 0,
    "ACTIVE": 1,
    "PAUSED": 2,
    "COMPLETED": 3,
    "RUNNING_SUBSEQUENCES": 4,
    "ACCOUNT_SUSPENDED": -99,
    "ACCOUNTS_UNHEALTHY": -1,
    "BOUNCE_PROTECT": -2,
}


def create_campaign_payload(name: str | None = None) -> dict[str, Any]:
    """Create campaign payload with optional custom name."""
    payload = SAMPLE_CAMPAIGN_DATA.copy()
    if name:
        payload["name"] = name
    else:
        payload["name"] = generate_unique_campaign_name()
    return payload


def create_lead_payload(
    email: str | None = None,
    campaign_id: str | None = None,
    list_id: str | None = None,
) -> dict[str, Any]:
    """Create lead payload with optional overrides."""
    payload = SAMPLE_LEAD_DATA.copy()
    if email:
        payload["email"] = email
    else:
        payload["email"] = generate_test_email()
    if campaign_id:
        payload["campaign_id"] = campaign_id
    if list_id:
        payload["list_id"] = list_id
    return payload


def create_bulk_leads_payload(count: int = 5) -> list[dict[str, Any]]:
    """Create bulk leads payload with unique emails."""
    return [
        {
            "email": generate_test_email(),
            "first_name": f"BulkLead{i}",
            "last_name": f"Test{i}",
            "company_name": f"Bulk Test Company {i}",
            "custom_variables": {"batch": "live_api_test", "index": i},
        }
        for i in range(1, count + 1)
    ]
