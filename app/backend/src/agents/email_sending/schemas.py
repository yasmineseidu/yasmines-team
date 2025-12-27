"""
Schemas for Email Sending Agent.

Defines result dataclasses and type definitions for email sending operations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BatchResult:
    """Result of a single batch upload operation."""

    batch_number: int
    leads_uploaded: int
    leads_failed: int
    lead_ids: list[str] = field(default_factory=list)
    instantly_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def success_rate(self) -> float:
        """Calculate batch success rate as percentage."""
        total = self.leads_uploaded + self.leads_failed
        if total == 0:
            return 0.0
        return (self.leads_uploaded / total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_number": self.batch_number,
            "leads_uploaded": self.leads_uploaded,
            "leads_failed": self.leads_failed,
            "lead_ids": self.lead_ids,
            "success_rate": self.success_rate,
            "error": self.error,
        }


@dataclass
class SendingProgress:
    """Progress tracking for email sending operation."""

    total_leads: int = 0
    leads_uploaded: int = 0
    batches_completed: int = 0
    batches_failed: int = 0
    tier_a_uploaded: int = 0
    tier_b_uploaded: int = 0
    tier_c_uploaded: int = 0
    leads_skipped: int = 0
    cost_incurred: float = 0.0
    is_resuming: bool = False
    last_checkpoint_batch: int = 0

    @property
    def upload_rate(self) -> float:
        """Calculate overall upload rate as percentage."""
        if self.total_leads == 0:
            return 0.0
        return (self.leads_uploaded / self.total_leads) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_leads": self.total_leads,
            "leads_uploaded": self.leads_uploaded,
            "batches_completed": self.batches_completed,
            "batches_failed": self.batches_failed,
            "tier_a_uploaded": self.tier_a_uploaded,
            "tier_b_uploaded": self.tier_b_uploaded,
            "tier_c_uploaded": self.tier_c_uploaded,
            "leads_skipped": self.leads_skipped,
            "upload_rate": self.upload_rate,
            "cost_incurred": self.cost_incurred,
            "is_resuming": self.is_resuming,
            "last_checkpoint_batch": self.last_checkpoint_batch,
        }


@dataclass
class EmailSendingResult:
    """Result of email sending operation."""

    success: bool
    campaign_id: str
    instantly_campaign_id: str | None = None
    total_uploaded: int = 0
    total_leads: int = 0
    tier_a_uploaded: int = 0
    tier_b_uploaded: int = 0
    tier_c_uploaded: int = 0
    batches_completed: int = 0
    batches_failed: int = 0
    leads_skipped: int = 0
    sending_started: bool = False
    campaign_status: str = "unknown"
    upload_rate: float = 0.0
    cost_incurred: float = 0.0
    verification_passed: bool = False
    instantly_lead_count: int = 0
    discrepancy: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "instantly_campaign_id": self.instantly_campaign_id,
            "total_uploaded": self.total_uploaded,
            "total_leads": self.total_leads,
            "tier_a_uploaded": self.tier_a_uploaded,
            "tier_b_uploaded": self.tier_b_uploaded,
            "tier_c_uploaded": self.tier_c_uploaded,
            "batches_completed": self.batches_completed,
            "batches_failed": self.batches_failed,
            "leads_skipped": self.leads_skipped,
            "sending_started": self.sending_started,
            "campaign_status": self.campaign_status,
            "upload_rate": self.upload_rate,
            "cost_incurred": self.cost_incurred,
            "verification_passed": self.verification_passed,
            "instantly_lead_count": self.instantly_lead_count,
            "discrepancy": self.discrepancy,
            "error": self.error,
        }

    def get_handoff_data(self) -> dict[str, Any]:
        """Get data for handoff to Reply Monitoring Agent (5.3)."""
        return {
            "campaign_id": self.campaign_id,
            "instantly_campaign_id": self.instantly_campaign_id,
            "total_uploaded": self.total_uploaded,
            "tier_breakdown": {
                "tier_a_uploaded": self.tier_a_uploaded,
                "tier_b_uploaded": self.tier_b_uploaded,
                "tier_c_uploaded": self.tier_c_uploaded,
            },
        }
