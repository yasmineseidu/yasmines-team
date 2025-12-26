"""
Schemas for Email Generation Agent.

Defines data classes for email generation, quality scoring, and agent results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EmailFramework(str, Enum):
    """Email frameworks for cold outreach."""

    PAS = "pas"  # Pain-Agitate-Solution
    BAB = "bab"  # Before-After-Bridge
    AIDA = "aida"  # Attention-Interest-Desire-Action
    QUESTION = "question"  # Question-Based


class LeadTier(str, Enum):
    """Lead tier classification."""

    A = "A"  # Highest priority
    B = "B"  # Medium priority
    C = "C"  # Lower priority


class PersonalizationLevel(str, Enum):
    """Level of personalization for emails."""

    HYPER_PERSONALIZED = "hyper_personalized"
    PERSONALIZED = "personalized"
    SEMI_PERSONALIZED = "semi_personalized"


@dataclass
class QualityScore:
    """Quality score breakdown for an email."""

    personalization: float = 0.0  # 0-10 scale, 30% weight
    clarity: float = 0.0  # 0-10 scale, 25% weight
    length: float = 0.0  # 0-10 scale, 15% weight
    cta_quality: float = 0.0  # 0-10 scale, 15% weight
    tone: float = 0.0  # 0-10 scale, 15% weight

    @property
    def total_score(self) -> float:
        """Calculate weighted total score (0-100)."""
        return (
            self.personalization * 0.30
            + self.clarity * 0.25
            + self.length * 0.15
            + self.cta_quality * 0.15
            + self.tone * 0.15
        ) * 10

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "personalization": self.personalization,
            "clarity": self.clarity,
            "length": self.length,
            "cta_quality": self.cta_quality,
            "tone": self.tone,
            "total_score": self.total_score,
        }


@dataclass
class GeneratedEmail:
    """A generated email with metadata."""

    lead_id: str
    campaign_id: str
    subject_line: str
    opening_line: str
    body: str
    cta: str
    full_email: str
    framework: EmailFramework
    personalization_level: PersonalizationLevel
    quality_score: float = 0.0
    score_breakdown: QualityScore = field(default_factory=QualityScore)
    company_research_id: str | None = None
    lead_research_id: str | None = None
    generation_prompt: str = ""
    regeneration_attempt: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "lead_id": self.lead_id,
            "campaign_id": self.campaign_id,
            "subject_line": self.subject_line,
            "opening_line": self.opening_line,
            "body": self.body,
            "cta": self.cta,
            "full_email": self.full_email,
            "framework_used": self.framework.value,
            "personalization_level": self.personalization_level.value,
            "quality_score": int(self.quality_score),
            "score_breakdown": self.score_breakdown.to_dict(),
            "company_research_id": self.company_research_id,
            "lead_research_id": self.lead_research_id,
            "generation_prompt": self.generation_prompt,
        }


@dataclass
class LeadContext:
    """Context for a lead for email generation."""

    lead_id: str
    first_name: str
    last_name: str
    title: str
    company_name: str
    company_domain: str | None
    lead_tier: LeadTier
    lead_score: int
    # Research data
    lead_research: dict[str, Any] | None = None
    company_research: dict[str, Any] | None = None
    # References
    company_research_id: str | None = None
    lead_research_id: str | None = None


@dataclass
class PersonaContext:
    """Persona context for messaging."""

    name: str
    challenges: list[str]
    goals: list[str]
    motivations: list[str]
    objections: list[str]
    messaging_tone: str | None
    value_propositions: list[str]


@dataclass
class NicheContext:
    """Niche context for messaging."""

    name: str
    industry: list[str]
    pain_points: list[str]
    value_propositions: list[str]
    messaging_tone: str | None = None


@dataclass
class TierConfig:
    """Configuration for a lead tier."""

    tier: LeadTier
    frameworks: list[EmailFramework]
    personalization_level: PersonalizationLevel
    max_words: int
    quality_threshold: int  # Minimum score before regeneration
    max_regeneration_attempts: int

    @classmethod
    def tier_a(cls) -> "TierConfig":
        """Configuration for Tier A leads."""
        return cls(
            tier=LeadTier.A,
            frameworks=[EmailFramework.PAS, EmailFramework.BAB],
            personalization_level=PersonalizationLevel.HYPER_PERSONALIZED,
            max_words=150,
            quality_threshold=70,
            max_regeneration_attempts=3,
        )

    @classmethod
    def tier_b(cls) -> "TierConfig":
        """Configuration for Tier B leads."""
        return cls(
            tier=LeadTier.B,
            frameworks=[EmailFramework.BAB, EmailFramework.AIDA],
            personalization_level=PersonalizationLevel.PERSONALIZED,
            max_words=120,
            quality_threshold=60,
            max_regeneration_attempts=2,
        )

    @classmethod
    def tier_c(cls) -> "TierConfig":
        """Configuration for Tier C leads."""
        return cls(
            tier=LeadTier.C,
            frameworks=[EmailFramework.AIDA, EmailFramework.QUESTION],
            personalization_level=PersonalizationLevel.SEMI_PERSONALIZED,
            max_words=100,
            quality_threshold=50,
            max_regeneration_attempts=1,
        )


@dataclass
class EmailGenerationResult:
    """Result from email generation agent execution."""

    success: bool
    campaign_id: str
    total_generated: int = 0
    tier_a_generated: int = 0
    tier_b_generated: int = 0
    tier_c_generated: int = 0
    avg_quality_score: float = 0.0
    quality_distribution: dict[str, int] = field(default_factory=dict)
    framework_usage: dict[str, int] = field(default_factory=dict)
    regeneration_stats: dict[str, int] = field(default_factory=dict)
    lines_saved_to_library: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "total_generated": self.total_generated,
            "tier_breakdown": {
                "tier_a": self.tier_a_generated,
                "tier_b": self.tier_b_generated,
                "tier_c": self.tier_c_generated,
            },
            "avg_quality_score": self.avg_quality_score,
            "quality_distribution": self.quality_distribution,
            "framework_usage": self.framework_usage,
            "regeneration_stats": self.regeneration_stats,
            "lines_saved_to_library": self.lines_saved_to_library,
            "error": self.error,
        }
