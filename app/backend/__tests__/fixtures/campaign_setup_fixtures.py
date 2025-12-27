"""
Test fixtures for Campaign Setup Agent (Phase 5.1).

Provides mock data for testing campaign setup, Instantly API responses,
and database interactions.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def sample_campaign_id() -> str:
    """Generate a sample campaign UUID."""
    return str(uuid4())


def sample_instantly_campaign_id() -> str:
    """Generate a sample Instantly campaign UUID."""
    return str(uuid4())


def sample_campaign_data(
    campaign_id: str | None = None,
    status: str = "ready",
    name: str = "Test Campaign",
) -> dict[str, Any]:
    """
    Generate sample campaign database record.

    Args:
        campaign_id: Optional campaign UUID (generates one if not provided).
        status: Campaign status.
        name: Campaign name.

    Returns:
        Dictionary with campaign data matching CampaignModel structure.
    """
    return {
        "id": campaign_id or sample_campaign_id(),
        "name": name,
        "status": status,
        "sending_status": status,
        "niche_id": str(uuid4()),
        "target_leads": 1000,
        "total_leads_scraped": 500,
        "total_leads_valid": 450,
        "import_summary": {},
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def sample_lead_data(
    campaign_id: str,
    email: str | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
) -> dict[str, Any]:
    """
    Generate sample lead database record.

    Args:
        campaign_id: Campaign UUID the lead belongs to.
        email: Lead email (generates one if not provided).
        first_name: Lead first name.
        last_name: Lead last name.

    Returns:
        Dictionary with lead data matching LeadModel structure.
    """
    return {
        "id": str(uuid4()),
        "campaign_id": campaign_id,
        "email": email or f"{first_name.lower()}.{last_name.lower()}@example.com",
        "first_name": first_name,
        "last_name": last_name,
        "company_name": "Acme Corp",
        "title": "Director of Engineering",
        "website": "https://acme.example.com",
        "linkedin_url": f"https://linkedin.com/in/{first_name.lower()}{last_name.lower()}",
        "lead_tier": "A",
        "lead_score": 85.0,
        "email_verified": True,
        "created_at": datetime.now(UTC).isoformat(),
    }


def sample_email_account_data(
    email: str = "sender@example.com",
    status: int = 1,
    warmup_status: int = 1,
) -> dict[str, Any]:
    """
    Generate sample Instantly email account response.

    Args:
        email: Account email address.
        status: Account status (1=active, 2=paused, -1=error).
        warmup_status: Warmup status (0=paused, 1=active, -1=banned).

    Returns:
        Dictionary matching Instantly API account response.
    """
    return {
        "email": email,
        "status": status,
        "warmup_status": warmup_status,
        "first_name": "Sender",
        "last_name": "Name",
        "daily_limit": 50,
        "warmup_limit": 10,
        "warmup_score": 85,
        "provider_code": 2,  # Google
        "custom_tag_ids": [],
        "timestamp_created": datetime.now(UTC).isoformat(),
    }


def sample_instantly_campaign_response(
    campaign_id: str | None = None,
    name: str = "Test Campaign",
    status: int = 0,  # Draft
) -> dict[str, Any]:
    """
    Generate sample Instantly campaign creation response.

    Args:
        campaign_id: Campaign UUID (generates one if not provided).
        name: Campaign name.
        status: Campaign status code.

    Returns:
        Dictionary matching Instantly API campaign response.
    """
    return {
        "id": campaign_id or sample_instantly_campaign_id(),
        "name": name,
        "status": status,
        "workspace_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def sample_bulk_add_leads_response(
    created_count: int = 100,
    updated_count: int = 0,
    failed_count: int = 0,
) -> dict[str, Any]:
    """
    Generate sample Instantly bulk add leads response.

    Args:
        created_count: Number of leads created.
        updated_count: Number of leads updated.
        failed_count: Number of leads that failed.

    Returns:
        Dictionary matching Instantly API bulk add response.
    """
    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "failed_count": failed_count,
        "created_leads": [str(uuid4()) for _ in range(created_count)],
        "failed_leads": [],
    }


def sample_background_job_response(
    job_id: str | None = None,
    status: str = "completed",
    progress: int = 100,
) -> dict[str, Any]:
    """
    Generate sample Instantly background job response.

    Args:
        job_id: Job UUID (generates one if not provided).
        status: Job status.
        progress: Job progress percentage.

    Returns:
        Dictionary matching Instantly API background job response.
    """
    return {
        "id": job_id or str(uuid4()),
        "job_id": job_id or str(uuid4()),
        "status": status,
        "progress": progress,
    }


def sample_sequence_steps() -> list[dict[str, Any]]:
    """
    Generate sample email sequence steps.

    Returns:
        List of sequence step dictionaries.
    """
    return [
        {
            "step_number": 1,
            "subject": "Quick question about {{companyName}}",
            "body": "Hi {{firstName}},\n\n{{opening_line}}\n\nBest,\n{{senderName}}",
            "delay_days": 0,
            "type": "email",
            "variants": [],
        },
        {
            "step_number": 2,
            "subject": "Re: Quick question about {{companyName}}",
            "body": "Hi {{firstName}},\n\nJust following up.\n\nBest,\n{{senderName}}",
            "delay_days": 3,
            "type": "email",
            "variants": [],
        },
        {
            "step_number": 3,
            "subject": "Re: Quick question about {{companyName}}",
            "body": "Hi {{firstName}},\n\nWould love to connect.\n\nBest,\n{{senderName}}",
            "delay_days": 4,
            "type": "email",
            "variants": [],
        },
        {
            "step_number": 4,
            "subject": "Should I close your file?",
            "body": "Hi {{firstName}},\n\nLet me know if timing is off.\n\nBest,\n{{senderName}}",
            "delay_days": 7,
            "type": "email",
            "variants": [],
        },
    ]


def sample_sending_schedule() -> dict[str, Any]:
    """
    Generate sample sending schedule configuration.

    Returns:
        Dictionary with schedule configuration.
    """
    return {
        "name": "Business Hours",
        "start_time": "09:00",
        "end_time": "17:00",
        "timezone": "America/New_York",
        "monday": True,
        "tuesday": True,
        "wednesday": True,
        "thursday": True,
        "friday": True,
        "saturday": False,
        "sunday": False,
    }


def sample_prerequisite_check_success(
    campaign_id: str,
    leads_count: int = 100,
    accounts_count: int = 5,
) -> dict[str, Any]:
    """
    Generate sample successful prerequisite check result.

    Args:
        campaign_id: Campaign UUID.
        leads_count: Number of leads with emails.
        accounts_count: Number of active sending accounts.

    Returns:
        Dictionary with prerequisite check result.
    """
    return {
        "valid": True,
        "campaign_id": campaign_id,
        "campaign_name": "Test Campaign",
        "campaign_status": "ready",
        "total_leads": leads_count + 10,
        "leads_with_emails": leads_count,
        "available_accounts": accounts_count,
        "errors": [],
        "warnings": [],
    }


def sample_prerequisite_check_failure(
    campaign_id: str,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generate sample failed prerequisite check result.

    Args:
        campaign_id: Campaign UUID.
        errors: List of error messages.

    Returns:
        Dictionary with failed prerequisite check result.
    """
    return {
        "valid": False,
        "campaign_id": campaign_id,
        "campaign_name": "Test Campaign",
        "campaign_status": "building",
        "total_leads": 50,
        "leads_with_emails": 0,
        "available_accounts": 0,
        "errors": errors or ["Campaign status 'building' is not approved for sending"],
        "warnings": [],
    }


def sample_campaign_setup_result_success(
    campaign_id: str,
    instantly_campaign_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate sample successful campaign setup result.

    Args:
        campaign_id: Internal campaign UUID.
        instantly_campaign_id: Instantly campaign UUID.

    Returns:
        Dictionary with successful setup result.
    """
    return {
        "success": True,
        "campaign_id": campaign_id,
        "instantly_campaign_id": instantly_campaign_id or sample_instantly_campaign_id(),
        "campaign_name": "Test Campaign",
        "leads_added": 100,
        "sending_accounts": 5,
        "warmup_enabled": True,
        "warmup_job_id": str(uuid4()),
        "sequence_steps": 4,
        "daily_limit": 50,
        "error": None,
    }


def sample_campaign_setup_result_failure(
    campaign_id: str,
    error: str = "Prerequisites validation failed",
) -> dict[str, Any]:
    """
    Generate sample failed campaign setup result.

    Args:
        campaign_id: Internal campaign UUID.
        error: Error message.

    Returns:
        Dictionary with failed setup result.
    """
    return {
        "success": False,
        "campaign_id": campaign_id,
        "instantly_campaign_id": None,
        "campaign_name": None,
        "leads_added": 0,
        "sending_accounts": 0,
        "warmup_enabled": False,
        "warmup_job_id": None,
        "sequence_steps": 0,
        "daily_limit": 0,
        "error": error,
    }


# Mock response generators for InstantlyClient methods
class MockInstantlyResponses:
    """Collection of mock Instantly API responses for testing."""

    @staticmethod
    def list_accounts(count: int = 5) -> list[dict[str, Any]]:
        """Generate mock list_accounts response."""
        return [sample_email_account_data(email=f"sender{i}@example.com") for i in range(count)]

    @staticmethod
    def create_campaign(name: str = "Test Campaign") -> dict[str, Any]:
        """Generate mock create_campaign response."""
        return sample_instantly_campaign_response(name=name)

    @staticmethod
    def bulk_add_leads(count: int = 100) -> dict[str, Any]:
        """Generate mock bulk_add_leads response."""
        return sample_bulk_add_leads_response(created_count=count)

    @staticmethod
    def enable_warmup(email_count: int = 5) -> dict[str, Any]:
        """Generate mock enable_warmup response."""
        _ = email_count  # Used for API consistency
        return sample_background_job_response(status="pending")

    @staticmethod
    def get_background_job(completed: bool = True) -> dict[str, Any]:
        """Generate mock get_background_job response."""
        return sample_background_job_response(
            status="completed" if completed else "running",
            progress=100 if completed else 50,
        )
