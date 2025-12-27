"""
Schemas for Campaign Setup Agent (Phase 5.1).

Data structures for campaign configuration, email sequences,
sending schedules, and result reporting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EmailSequenceStep:
    """
    A single step in an email sequence.

    Each step represents one email in a multi-touch sequence
    with delay configuration and A/B variant support.
    """

    step_number: int
    subject: str
    body: str
    delay_days: int = 0
    step_type: str = "email"
    variants: list[dict[str, str]] = field(default_factory=list)

    def to_instantly_format(self) -> dict[str, Any]:
        """Convert to Instantly API sequence step format."""
        step: dict[str, Any] = {
            "type": self.step_type,
            "delay": self.delay_days,
            "variants": [{"subject": self.subject, "body": self.body}],
        }
        if self.variants:
            step["variants"].extend(self.variants)
        return step


@dataclass
class SendingSchedule:
    """
    Sending schedule configuration for a campaign.

    Defines when emails can be sent (days, times, timezone).
    """

    name: str = "Business Hours"
    start_time: str = "09:00"
    end_time: str = "17:00"
    timezone: str = "America/New_York"
    monday: bool = True
    tuesday: bool = True
    wednesday: bool = True
    thursday: bool = True
    friday: bool = True
    saturday: bool = False
    sunday: bool = False

    def to_instantly_format(self) -> dict[str, Any]:
        """Convert to Instantly API schedule format."""
        return {
            "name": self.name,
            "timing": {
                "from": self.start_time,
                "to": self.end_time,
            },
            "days": {
                "0": self.monday,
                "1": self.tuesday,
                "2": self.wednesday,
                "3": self.thursday,
                "4": self.friday,
                "5": self.saturday,
                "6": self.sunday,
            },
            "timezone": self.timezone,
        }


@dataclass
class CampaignSetupResult:
    """
    Result of campaign setup operation.

    Contains the campaign details, setup status, and any errors.
    """

    success: bool
    campaign_id: str
    instantly_campaign_id: str | None = None
    campaign_name: str | None = None
    leads_added: int = 0
    sending_accounts: int = 0
    warmup_enabled: bool = False
    warmup_job_id: str | None = None
    sequence_steps: int = 0
    daily_limit: int = 0
    error: str | None = None
    created_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "instantly_campaign_id": self.instantly_campaign_id,
            "campaign_name": self.campaign_name,
            "leads_added": self.leads_added,
            "sending_accounts": self.sending_accounts,
            "warmup_enabled": self.warmup_enabled,
            "warmup_job_id": self.warmup_job_id,
            "sequence_steps": self.sequence_steps,
            "daily_limit": self.daily_limit,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class PrerequisiteCheckResult:
    """Result of campaign prerequisite validation."""

    valid: bool
    campaign_id: str
    campaign_name: str | None = None
    campaign_status: str | None = None
    total_leads: int = 0
    leads_with_emails: int = 0
    available_accounts: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "valid": self.valid,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "campaign_status": self.campaign_status,
            "total_leads": self.total_leads,
            "leads_with_emails": self.leads_with_emails,
            "available_accounts": self.available_accounts,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class WarmupConfigResult:
    """Result of warmup configuration operation."""

    success: bool
    accounts_configured: int = 0
    job_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "accounts_configured": self.accounts_configured,
            "job_id": self.job_id,
            "error": self.error,
        }
