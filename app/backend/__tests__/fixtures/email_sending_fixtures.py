"""
Test fixtures for Email Sending Agent.

Provides sample data for testing lead upload, batch processing,
and Instantly API interactions.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def create_sample_lead(
    lead_id: str | None = None,
    tier: str = "A",
    with_email_data: bool = True,
) -> dict[str, Any]:
    """Create a sample lead for testing."""
    lead_id = lead_id or str(uuid4())
    return {
        "id": lead_id,
        "email": f"test_{lead_id[:8]}@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Acme Corp",
        "lead_tier": tier,
        "generated_email_id": str(uuid4()) if with_email_data else None,
        "lead_score": {"A": 95, "B": 75, "C": 50}.get(tier, 50),
        "email_data": {
            "subject_line": f"Quick question about {tier} tier leads",
            "full_email": f"Hi John,\n\nI noticed Acme Corp is expanding. "
            f"Would love to discuss how we can help with {tier} priorities.\n\nBest,\nSender",
            "quality_score": {"A": 85, "B": 70, "C": 55}.get(tier, 55),
        }
        if with_email_data
        else None,
    }


def create_sample_batch(
    batch_size: int = 10,
    tier: str = "A",
) -> list[dict[str, Any]]:
    """Create a batch of sample leads."""
    return [create_sample_lead(tier=tier) for _ in range(batch_size)]


def create_sample_campaign(campaign_id: str | None = None) -> dict[str, Any]:
    """Create a sample campaign for testing."""
    return {
        "id": campaign_id or str(uuid4()),
        "name": "Q1 2025 Outreach",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }


def create_instantly_bulk_add_response(
    created_count: int = 10,
    updated_count: int = 0,
    failed_count: int = 0,
) -> dict[str, Any]:
    """Create a sample Instantly bulk add API response."""
    return {
        "status": "success",
        "created_count": created_count,
        "updated_count": updated_count,
        "failed_count": failed_count,
        "created_leads": [str(uuid4()) for _ in range(created_count)],
        "failed_leads": [],
        "in_blocklist": 0,
        "invalid_email_count": 0,
        "remaining_in_plan": 10000 - created_count,
    }


def create_instantly_campaign_response(
    campaign_id: str | None = None,
    status: int = 1,  # ACTIVE
    total_leads: int = 100,
) -> dict[str, Any]:
    """Create a sample Instantly campaign API response."""
    return {
        "id": campaign_id or str(uuid4()),
        "name": "Test Campaign",
        "status": status,
        "workspace_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "total_leads": total_leads,
    }


def create_instantly_analytics_response(
    campaign_id: str | None = None,
    total_leads: int = 100,
    emails_sent: int = 50,
) -> dict[str, Any]:
    """Create a sample Instantly analytics API response."""
    return {
        "campaign_id": campaign_id or str(uuid4()),
        "total_leads": total_leads,
        "contacted": emails_sent,
        "emails_sent": emails_sent,
        "emails_opened": int(emails_sent * 0.25),
        "emails_clicked": int(emails_sent * 0.05),
        "emails_replied": int(emails_sent * 0.02),
        "emails_bounced": int(emails_sent * 0.01),
        "unsubscribed": 0,
    }


def create_resume_state(
    batches_completed: int = 5,
    leads_uploaded: int = 500,
    last_batch: int = 5,
) -> dict[str, Any]:
    """Create a sample resume state."""
    return {
        "is_resuming": True,
        "start_from_batch": last_batch + 1,
        "previously_uploaded": leads_uploaded,
        "batches_completed": batches_completed,
        "message": f"Resuming from batch {last_batch + 1}, "
        f"{leads_uploaded} leads already uploaded",
    }


def create_sending_result(
    success: bool = True,
    total_uploaded: int = 100,
    total_leads: int = 100,
    tier_a: int = 30,
    tier_b: int = 40,
    tier_c: int = 30,
    batches_completed: int = 1,
    batches_failed: int = 0,
    sending_started: bool = True,
) -> dict[str, Any]:
    """Create a sample sending result."""
    return {
        "success": success,
        "campaign_id": str(uuid4()),
        "instantly_campaign_id": str(uuid4()),
        "total_uploaded": total_uploaded,
        "total_leads": total_leads,
        "tier_a_uploaded": tier_a,
        "tier_b_uploaded": tier_b,
        "tier_c_uploaded": tier_c,
        "batches_completed": batches_completed,
        "batches_failed": batches_failed,
        "leads_skipped": 0,
        "sending_started": sending_started,
        "campaign_status": "active",
        "upload_rate": (total_uploaded / total_leads * 100) if total_leads > 0 else 0,
        "cost_incurred": total_uploaded * 0.001,
        "verification_passed": True,
        "error": None,
    }


# Database row fixtures
def create_db_lead_row(
    lead_id: str | None = None,
    campaign_id: str | None = None,
    tier: str = "A",
) -> dict[str, Any]:
    """Create a sample database lead row."""
    return {
        "id": lead_id or str(uuid4()),
        "campaign_id": campaign_id or str(uuid4()),
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Acme Corp",
        "lead_tier": tier,
        "email_status": "valid",
        "email_generation_status": "generated",
        "sending_status": None,
        "generated_email_id": str(uuid4()),
        "lead_score": 85,
    }


def create_db_sending_log_row(
    campaign_id: str | None = None,
    batch_number: int = 1,
    leads_uploaded: int = 100,
) -> dict[str, Any]:
    """Create a sample database sending log row."""
    return {
        "id": str(uuid4()),
        "campaign_id": campaign_id or str(uuid4()),
        "instantly_campaign_id": str(uuid4()),
        "batch_number": batch_number,
        "leads_uploaded": leads_uploaded,
        "lead_ids": [str(uuid4()) for _ in range(leads_uploaded)],
        "status": "uploaded",
        "instantly_response": {},
        "created_at": datetime.now(UTC),
        "completed_at": datetime.now(UTC),
    }
