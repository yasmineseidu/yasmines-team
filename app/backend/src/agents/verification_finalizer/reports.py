"""
Quality report generation for Verification Finalizer Agent.

Generates comprehensive verification and enrichment quality reports
with metrics, tier breakdowns, and cost summaries.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TierBreakdown:
    """Breakdown of leads by tier with verification metrics."""

    tier: str
    total: int = 0
    verified: int = 0
    enriched: int = 0
    ready: int = 0
    avg_score: float = 0.0
    avg_enrichment_cost: float = 0.0

    @property
    def verification_rate(self) -> float:
        """Calculate verification rate for this tier."""
        if self.total == 0:
            return 0.0
        return round(self.verified / self.total * 100, 2)

    @property
    def enrichment_rate(self) -> float:
        """Calculate enrichment rate for this tier."""
        if self.verified == 0:
            return 0.0
        return round(self.enriched / self.verified * 100, 2)

    @property
    def readiness_rate(self) -> float:
        """Calculate readiness rate for this tier."""
        if self.enriched == 0:
            return 0.0
        return round(self.ready / self.enriched * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier": self.tier,
            "total": self.total,
            "verified": self.verified,
            "enriched": self.enriched,
            "ready": self.ready,
            "avg_score": self.avg_score,
            "avg_enrichment_cost": self.avg_enrichment_cost,
            "verification_rate": self.verification_rate,
            "enrichment_rate": self.enrichment_rate,
            "readiness_rate": self.readiness_rate,
        }


@dataclass
class VerificationSummary:
    """Summary of email verification results."""

    emails_found: int = 0
    emails_verified: int = 0
    emails_valid: int = 0
    emails_invalid: int = 0
    emails_risky: int = 0
    emails_catchall: int = 0

    @property
    def verification_rate(self) -> float:
        """Calculate overall email verification rate."""
        if self.emails_found == 0:
            return 0.0
        return round(self.emails_verified / self.emails_found * 100, 2)

    @property
    def validity_rate(self) -> float:
        """Calculate email validity rate."""
        if self.emails_verified == 0:
            return 0.0
        return round(self.emails_valid / self.emails_verified * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "emails_found": self.emails_found,
            "emails_verified": self.emails_verified,
            "emails_valid": self.emails_valid,
            "emails_invalid": self.emails_invalid,
            "emails_risky": self.emails_risky,
            "emails_catchall": self.emails_catchall,
            "verification_rate": self.verification_rate,
            "validity_rate": self.validity_rate,
        }


@dataclass
class CostSummary:
    """Summary of Phase 3 costs."""

    scraping_cost: float = 0.0
    enrichment_cost: float = 0.0
    verification_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Calculate total Phase 3 cost."""
        return round(self.scraping_cost + self.enrichment_cost + self.verification_cost, 2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scraping_cost": self.scraping_cost,
            "enrichment_cost": self.enrichment_cost,
            "verification_cost": self.verification_cost,
            "total_cost": self.total_cost,
        }


@dataclass
class QualityReport:
    """Comprehensive quality report for Phase 3 completion."""

    campaign_id: str
    campaign_name: str
    niche_name: str
    verification_summary: VerificationSummary = field(default_factory=VerificationSummary)
    tier_breakdowns: dict[str, TierBreakdown] = field(default_factory=dict)
    cost_summary: CostSummary = field(default_factory=CostSummary)
    total_leads: int = 0
    total_ready: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def email_verification_rate(self) -> float:
        """Overall email verification rate."""
        return self.verification_summary.verification_rate

    @property
    def enrichment_completion_rate(self) -> float:
        """Calculate enrichment completion rate across all tiers."""
        total_enriched = sum(t.enriched for t in self.tier_breakdowns.values())
        total_verified = sum(t.verified for t in self.tier_breakdowns.values())
        if total_verified == 0:
            return 0.0
        return round(total_enriched / total_verified * 100, 2)

    @property
    def data_quality_score(self) -> float:
        """Calculate overall data quality score (0-1 scale)."""
        if self.total_leads == 0:
            return 0.0

        # Weighted calculation:
        # - 40% email validity rate
        # - 30% enrichment rate
        # - 30% readiness rate
        validity = self.verification_summary.validity_rate / 100
        enrichment = self.enrichment_completion_rate / 100
        readiness = self.total_ready / self.total_leads if self.total_leads > 0 else 0

        score = (0.4 * validity) + (0.3 * enrichment) + (0.3 * readiness)
        return round(score, 2)

    @property
    def cost_per_ready_lead(self) -> float:
        """Calculate cost per ready lead."""
        if self.total_ready == 0:
            return 0.0
        return round(self.cost_summary.total_cost / self.total_ready, 4)

    def add_tier_breakdown(self, tier: TierBreakdown) -> None:
        """Add a tier breakdown to the report."""
        self.tier_breakdowns[tier.tier] = tier
        logger.debug(f"Added tier breakdown for tier {tier.tier}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "niche_name": self.niche_name,
            "total_leads": self.total_leads,
            "total_ready": self.total_ready,
            "verification_summary": self.verification_summary.to_dict(),
            "tier_breakdowns": {
                tier: breakdown.to_dict() for tier, breakdown in self.tier_breakdowns.items()
            },
            "cost_summary": self.cost_summary.to_dict(),
            "quality_scores": {
                "email_verification_rate": self.email_verification_rate,
                "enrichment_completion_rate": self.enrichment_completion_rate,
                "data_quality_score": self.data_quality_score,
            },
            "cost_per_ready_lead": self.cost_per_ready_lead,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_summary_text(self) -> str:
        """Generate human-readable summary text."""
        lines = [
            f"Phase 3 Verification Report - {self.campaign_name}",
            f"Niche: {self.niche_name}",
            "",
            "Email Verification:",
            f"  - Emails Found: {self.verification_summary.emails_found:,}",
            f"  - Emails Verified: {self.verification_summary.emails_verified:,}",
            f"  - Valid Emails: {self.verification_summary.emails_valid:,}",
            f"  - Verification Rate: {self.verification_summary.verification_rate}%",
            "",
            "Quality by Tier:",
        ]

        for tier_name in ["A", "B", "C"]:
            tier = self.tier_breakdowns.get(tier_name)
            if tier:
                lines.append(f"  Tier {tier_name}:")
                lines.append(f"    - Total: {tier.total:,}")
                lines.append(f"    - Ready: {tier.ready:,}")
                lines.append(f"    - Avg Score: {tier.avg_score:.1f}")

        lines.extend(
            [
                "",
                "Summary:",
                f"  - Total Leads Ready: {self.total_ready:,}",
                f"  - Data Quality Score: {self.data_quality_score:.0%}",
                f"  - Total Cost: ${self.cost_summary.total_cost:,.2f}",
                f"  - Cost per Ready Lead: ${self.cost_per_ready_lead:.4f}",
            ]
        )

        return "\n".join(lines)


class QualityReportGenerator:
    """Generator for quality reports from database data."""

    def __init__(
        self,
        campaign_data: dict[str, Any],
        niche_data: dict[str, Any],
        email_stats: list[dict[str, Any]],
        tier_stats: list[dict[str, Any]],
    ) -> None:
        """
        Initialize report generator.

        Args:
            campaign_data: Campaign data from database
            niche_data: Niche data from database
            email_stats: Email verification statistics by status
            tier_stats: Lead statistics by tier
        """
        self.campaign_data = campaign_data
        self.niche_data = niche_data
        self.email_stats = email_stats
        self.tier_stats = tier_stats

    def generate(self) -> QualityReport:
        """Generate comprehensive quality report."""
        report = QualityReport(
            campaign_id=str(self.campaign_data.get("id", "")),
            campaign_name=self.campaign_data.get("name", "Unknown Campaign"),
            niche_name=self.niche_data.get("name", "Unknown Niche"),
        )

        # Build verification summary
        report.verification_summary = self._build_verification_summary()

        # Build tier breakdowns
        for tier_data in self.tier_stats:
            tier_breakdown = self._build_tier_breakdown(tier_data)
            report.add_tier_breakdown(tier_breakdown)

        # Build cost summary
        report.cost_summary = self._build_cost_summary()

        # Calculate totals
        report.total_leads = sum(t.total for t in report.tier_breakdowns.values())
        report.total_ready = sum(t.ready for t in report.tier_breakdowns.values())

        logger.info(
            f"Generated quality report for campaign {report.campaign_id}: "
            f"{report.total_ready:,} leads ready, "
            f"quality score {report.data_quality_score:.0%}"
        )

        return report

    def _build_verification_summary(self) -> VerificationSummary:
        """Build verification summary from email stats."""
        summary = VerificationSummary()

        for stat in self.email_stats:
            status = stat.get("email_status", "unknown")
            count = stat.get("count", 0)

            summary.emails_found += count

            if status == "valid":
                summary.emails_valid += count
                summary.emails_verified += count
            elif status == "invalid":
                summary.emails_invalid += count
                summary.emails_verified += count
            elif status == "risky":
                summary.emails_risky += count
                summary.emails_verified += count
            elif status == "catchall":
                summary.emails_catchall += count
                summary.emails_verified += count

        return summary

    def _build_tier_breakdown(self, tier_data: dict[str, Any]) -> TierBreakdown:
        """Build tier breakdown from tier statistics."""
        return TierBreakdown(
            tier=tier_data.get("lead_tier", ""),
            total=tier_data.get("total", 0),
            verified=tier_data.get("valid_email", 0),
            enriched=tier_data.get("has_description", 0),
            ready=tier_data.get("valid_email", 0),  # Ready = has valid email
            avg_score=tier_data.get("avg_score", 0.0) or 0.0,
            avg_enrichment_cost=tier_data.get("avg_enrichment_cost", 0.0) or 0.0,
        )

    def _build_cost_summary(self) -> CostSummary:
        """Build cost summary from campaign data."""
        return CostSummary(
            scraping_cost=float(self.campaign_data.get("scraping_cost", 0) or 0),
            enrichment_cost=float(self.campaign_data.get("enrichment_cost", 0) or 0),
            verification_cost=0.0,  # TODO: Calculate from verification logs
        )
