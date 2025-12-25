"""
Schemas for Import Finalizer Agent (Phase 2, Agent 2.6).

Defines input/output types for summary building, sheets export, and result handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# =============================================================================
# Summary Sections
# =============================================================================


@dataclass
class ScrapingSummary:
    """Summary of lead scraping results."""

    target_leads: int
    total_scraped: int
    scraping_cost: float
    cost_per_lead: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_leads": self.target_leads,
            "total_scraped": self.total_scraped,
            "scraping_cost": round(self.scraping_cost, 2),
            "cost_per_lead": round(self.cost_per_lead, 4),
        }


@dataclass
class ValidationSummary:
    """Summary of data validation results."""

    total_valid: int
    total_invalid: int
    validity_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_valid": self.total_valid,
            "total_invalid": self.total_invalid,
            "validity_rate": round(self.validity_rate, 4),
        }


@dataclass
class DeduplicationSummary:
    """Summary of deduplication results."""

    within_campaign_dupes: int
    cross_campaign_dupes: int
    available_after_dedup: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "within_campaign_dupes": self.within_campaign_dupes,
            "cross_campaign_dupes": self.cross_campaign_dupes,
            "available_after_dedup": self.available_after_dedup,
        }


@dataclass
class TierBreakdown:
    """Breakdown of leads by tier."""

    tier_a: int
    tier_b: int
    tier_c: int
    tier_d: int = 0

    @property
    def total(self) -> int:
        """Total leads across all tiers."""
        return self.tier_a + self.tier_b + self.tier_c + self.tier_d

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier_a": self.tier_a,
            "tier_b": self.tier_b,
            "tier_c": self.tier_c,
            "tier_d": self.tier_d,
            "total": self.total,
        }


@dataclass
class ScoringSummary:
    """Summary of lead scoring results."""

    total_scored: int
    avg_score: float
    tier_breakdown: TierBreakdown

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_scored": self.total_scored,
            "avg_score": round(self.avg_score, 2),
            "tier_breakdown": self.tier_breakdown.to_dict(),
        }


# =============================================================================
# Full Summary
# =============================================================================


@dataclass
class ImportSummary:
    """Complete import summary combining all sections."""

    campaign_id: str
    campaign_name: str
    niche_name: str
    scraping: ScrapingSummary
    validation: ValidationSummary
    deduplication: DeduplicationSummary
    scoring: ScoringSummary
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def total_available(self) -> int:
        """Total leads available for campaign."""
        return self.deduplication.available_after_dedup

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "niche_name": self.niche_name,
            "scraping": self.scraping.to_dict(),
            "validation": self.validation.to_dict(),
            "deduplication": self.deduplication.to_dict(),
            "scoring": self.scoring.to_dict(),
            "total_available": self.total_available,
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# Sheets Export Types
# =============================================================================


@dataclass
class LeadRow:
    """Lead data for spreadsheet row."""

    first_name: str | None
    last_name: str | None
    email: str | None
    title: str | None
    company_name: str | None
    company_domain: str | None
    company_size: str | None
    location: str | None
    lead_score: int | None
    lead_tier: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRow":
        """Create from dictionary."""
        return cls(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            title=data.get("title") or data.get("job_title"),
            company_name=data.get("company_name"),
            company_domain=data.get("company_domain"),
            company_size=data.get("company_size"),
            location=data.get("location"),
            lead_score=data.get("lead_score"),
            lead_tier=data.get("lead_tier"),
        )

    def to_row(self, include_size_location: bool = False) -> list[Any]:
        """Convert to spreadsheet row."""
        base: list[Any] = [
            self.first_name or "",
            self.last_name or "",
            self.email or "",
            self.title or "",
            self.company_name or "",
            self.company_domain or "",
        ]
        if include_size_location:
            base.extend([self.company_size or "", self.location or ""])
        base.extend([self.lead_score or 0, self.lead_tier or ""])
        return base


@dataclass
class SheetExportResult:
    """Result of Google Sheets export."""

    success: bool
    spreadsheet_id: str | None = None
    spreadsheet_url: str | None = None
    sheet_names: list[str] = field(default_factory=list)
    total_rows_written: int = 0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "spreadsheet_id": self.spreadsheet_id,
            "spreadsheet_url": self.spreadsheet_url,
            "sheet_names": self.sheet_names,
            "total_rows_written": self.total_rows_written,
            "error_message": self.error_message,
        }


# =============================================================================
# Agent Result
# =============================================================================


@dataclass
class ImportFinalizerResult:
    """Result of Import Finalizer Agent execution."""

    # Status
    success: bool = True
    status: str = "completed"  # completed, partial, failed

    # Output
    summary: ImportSummary | None = None
    sheet_result: SheetExportResult | None = None
    notification_sent: bool = False

    # URLs
    sheet_url: str | None = None
    sheet_id: str | None = None

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "status": self.status,
            "summary": self.summary.to_dict() if self.summary else None,
            "sheet_result": self.sheet_result.to_dict() if self.sheet_result else None,
            "notification_sent": self.notification_sent,
            "sheet_url": self.sheet_url,
            "sheet_id": self.sheet_id,
            "execution_time_ms": self.execution_time_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Campaign Data Types (for database reads)
# =============================================================================


@dataclass
class CampaignData:
    """Campaign data from database."""

    id: str
    name: str
    niche_id: str | None
    status: str
    target_leads: int
    total_leads_scraped: int
    scraping_cost: float
    total_leads_valid: int
    total_leads_invalid: int
    total_duplicates_found: int
    total_cross_duplicates: int
    total_leads_available: int
    leads_scored: int
    avg_lead_score: float
    leads_tier_a: int
    leads_tier_b: int
    leads_tier_c: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CampaignData":
        """Create from dictionary (database row)."""
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            niche_id=str(data.get("niche_id")) if data.get("niche_id") else None,
            status=data.get("status", ""),
            target_leads=data.get("target_leads", 0) or 0,
            total_leads_scraped=data.get("total_leads_scraped", 0) or 0,
            scraping_cost=float(data.get("scraping_cost", 0) or 0),
            total_leads_valid=data.get("total_leads_valid", 0) or 0,
            total_leads_invalid=data.get("total_leads_invalid", 0) or 0,
            total_duplicates_found=data.get("total_duplicates_found", 0) or 0,
            total_cross_duplicates=data.get("total_cross_duplicates", 0) or 0,
            total_leads_available=data.get("total_leads_available", 0) or 0,
            leads_scored=data.get("leads_scored", 0) or 0,
            avg_lead_score=float(data.get("avg_lead_score", 0) or 0),
            leads_tier_a=data.get("leads_tier_a", 0) or 0,
            leads_tier_b=data.get("leads_tier_b", 0) or 0,
            leads_tier_c=data.get("leads_tier_c", 0) or 0,
        )


@dataclass
class NicheData:
    """Niche data from database."""

    id: str
    name: str
    industry: list[str]
    job_titles: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NicheData":
        """Create from dictionary (database row)."""
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            industry=data.get("industry", []) or [],
            job_titles=data.get("job_titles", []) or [],
        )
