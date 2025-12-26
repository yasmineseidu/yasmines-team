"""
Report dataclasses for Personalization Finalizer Agent.

Defines data structures for personalization summary reports,
tier breakdowns, quality metrics, and framework usage statistics.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TierPersonalizationBreakdown:
    """Personalization breakdown for a single lead tier."""

    tier: str
    total_leads: int = 0
    emails_generated: int = 0
    avg_quality_score: float = 0.0
    min_quality_score: int = 0
    max_quality_score: int = 0
    quality_passed: int = 0  # Above threshold
    quality_failed: int = 0  # Below threshold
    regeneration_count: int = 0

    @property
    def generation_rate(self) -> float:
        """Calculate the percentage of leads with generated emails."""
        if self.total_leads == 0:
            return 0.0
        return round((self.emails_generated / self.total_leads) * 100, 1)

    @property
    def pass_rate(self) -> float:
        """Calculate quality pass rate."""
        if self.emails_generated == 0:
            return 0.0
        return round((self.quality_passed / self.emails_generated) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier": self.tier,
            "total_leads": self.total_leads,
            "emails_generated": self.emails_generated,
            "avg_quality_score": round(self.avg_quality_score, 1),
            "min_quality_score": self.min_quality_score,
            "max_quality_score": self.max_quality_score,
            "quality_passed": self.quality_passed,
            "quality_failed": self.quality_failed,
            "regeneration_count": self.regeneration_count,
            "generation_rate": self.generation_rate,
            "pass_rate": self.pass_rate,
        }


@dataclass
class FrameworkUsage:
    """Usage statistics for email frameworks."""

    framework: str
    count: int = 0
    avg_quality_score: float = 0.0
    total_quality_score: float = 0.0

    @property
    def percentage(self) -> float:
        """Percentage of total emails using this framework."""
        # Set by parent report
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "count": self.count,
            "avg_quality_score": round(self.avg_quality_score, 1),
        }


@dataclass
class PersonalizationLevelStats:
    """Statistics by personalization level."""

    level: str
    count: int = 0
    avg_quality_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "count": self.count,
            "avg_quality_score": round(self.avg_quality_score, 1),
        }


@dataclass
class QualityDistribution:
    """Distribution of quality scores by range."""

    excellent: int = 0  # 80-100
    good: int = 0  # 60-79
    acceptable: int = 0  # 40-59
    needs_improvement: int = 0  # 0-39

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "excellent_80_100": self.excellent,
            "good_60_79": self.good,
            "acceptable_40_59": self.acceptable,
            "needs_improvement_0_39": self.needs_improvement,
        }


@dataclass
class PersonalizationReport:
    """Comprehensive personalization report for Phase 4 completion."""

    campaign_id: str
    campaign_name: str
    niche_name: str
    total_leads: int = 0
    total_emails_generated: int = 0
    avg_quality_score: float = 0.0
    min_quality_score: int = 0
    max_quality_score: int = 0

    # Tier breakdowns
    tier_breakdowns: dict[str, TierPersonalizationBreakdown] = field(default_factory=dict)

    # Framework usage
    framework_usage: dict[str, FrameworkUsage] = field(default_factory=dict)

    # Personalization level stats
    personalization_levels: dict[str, PersonalizationLevelStats] = field(default_factory=dict)

    # Quality distribution
    quality_distribution: QualityDistribution = field(default_factory=QualityDistribution)

    # Regeneration stats
    total_regenerations: int = 0

    # Timestamps
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def generation_rate(self) -> float:
        """Overall email generation rate."""
        if self.total_leads == 0:
            return 0.0
        return round((self.total_emails_generated / self.total_leads) * 100, 1)

    @property
    def data_quality_score(self) -> float:
        """Data quality metric (0-1 scale)."""
        if self.total_emails_generated == 0:
            return 0.0
        # Based on average quality score (normalized to 0-1)
        return min(1.0, self.avg_quality_score / 100)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "niche_name": self.niche_name,
            "total_leads": self.total_leads,
            "total_emails_generated": self.total_emails_generated,
            "generation_rate": self.generation_rate,
            "avg_quality_score": round(self.avg_quality_score, 1),
            "min_quality_score": self.min_quality_score,
            "max_quality_score": self.max_quality_score,
            "tier_breakdowns": {
                tier: breakdown.to_dict() for tier, breakdown in self.tier_breakdowns.items()
            },
            "framework_usage": {fw: usage.to_dict() for fw, usage in self.framework_usage.items()},
            "personalization_levels": {
                level: stats.to_dict() for level, stats in self.personalization_levels.items()
            },
            "quality_distribution": self.quality_distribution.to_dict(),
            "total_regenerations": self.total_regenerations,
            "data_quality_score": round(self.data_quality_score, 2),
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class PersonalizationFinalizerResult:
    """Result from Personalization Finalizer Agent execution."""

    success: bool
    campaign_id: str
    report: PersonalizationReport | None = None
    sheets_url: str | None = None
    sheets_id: str | None = None
    notification_sent: bool = False
    notification_message_id: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "report": self.report.to_dict() if self.report else None,
            "sheets_url": self.sheets_url,
            "sheets_id": self.sheets_id,
            "notification_sent": self.notification_sent,
            "notification_message_id": self.notification_message_id,
            "error": self.error,
        }
