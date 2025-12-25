"""
Schemas for Lead Scoring Agent.

Defines dataclasses for input/output validation and data transfer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LeadScoreRecord:
    """
    Lead record for scoring.

    Contains fields needed for scoring calculation.
    """

    id: str
    title: str | None = None  # Job title (DB uses 'title')
    seniority: str | None = None
    company_name: str | None = None
    company_size: str | None = None
    company_industry: str | None = None
    company_domain: str | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadScoreRecord":
        """Create LeadScoreRecord from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            title=data.get("title") or data.get("job_title"),
            seniority=data.get("seniority") or data.get("seniority_level"),
            company_name=data.get("company_name"),
            company_size=data.get("company_size"),
            company_industry=data.get("company_industry") or data.get("industry"),
            company_domain=data.get("company_domain"),
            location=data.get("location"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
            email=data.get("email"),
            phone=data.get("phone"),
            linkedin_url=data.get("linkedin_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "seniority": self.seniority,
            "company_name": self.company_name,
            "company_size": self.company_size,
            "company_industry": self.company_industry,
            "company_domain": self.company_domain,
            "location": self.location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "email": self.email,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
        }


@dataclass
class PersonaContext:
    """Persona data for scoring context."""

    id: str
    name: str
    job_titles: list[str] = field(default_factory=list)
    seniority_levels: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    company_sizes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonaContext":
        """Create PersonaContext from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            job_titles=data.get("job_titles") or [],
            seniority_levels=data.get("seniority_levels") or [],
            departments=data.get("departments") or [],
            industries=data.get("industries") or [],
            company_sizes=data.get("company_sizes") or data.get("company_size") or [],
        )


@dataclass
class NicheContext:
    """Niche data for scoring context."""

    id: str
    name: str
    industries: list[str] = field(default_factory=list)
    company_sizes: list[str] = field(default_factory=list)
    job_titles: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NicheContext":
        """Create NicheContext from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            industries=data.get("industry") or data.get("industries") or [],
            company_sizes=data.get("company_size") or data.get("company_sizes") or [],
            job_titles=data.get("job_titles") or [],
        )


@dataclass
class IndustryFitScore:
    """Industry fit score from niche research."""

    industry: str
    fit_score: int  # 0-100

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndustryFitScore":
        """Create IndustryFitScore from dictionary."""
        return cls(
            industry=data.get("industry", ""),
            fit_score=int(data.get("fit_score", 0)),
        )


@dataclass
class ScoringContext:
    """
    Complete scoring context loaded from database.

    Contains niche, personas, and industry fit scores.
    """

    niche: NicheContext
    personas: list[PersonaContext] = field(default_factory=list)
    industry_fit_scores: list[IndustryFitScore] = field(default_factory=list)
    target_countries: list[str] = field(default_factory=lambda: ["United States", "US"])

    def get_all_target_job_titles(self) -> list[str]:
        """Get all target job titles from personas and niche."""
        titles: set[str] = set()
        for persona in self.personas:
            titles.update(persona.job_titles)
        titles.update(self.niche.job_titles)
        return list(titles)

    def get_all_target_seniorities(self) -> list[str]:
        """Get all target seniority levels from personas."""
        seniorities: set[str] = set()
        for persona in self.personas:
            seniorities.update(persona.seniority_levels)
        return list(seniorities)

    def get_all_target_company_sizes(self) -> list[str]:
        """Get all target company sizes from personas and niche."""
        sizes: set[str] = set()
        for persona in self.personas:
            sizes.update(persona.company_sizes)
        sizes.update(self.niche.company_sizes)
        return list(sizes)

    def get_industry_fit_score(self, industry: str) -> int:
        """Get industry fit score or default."""
        if not industry:
            return 50  # Default for missing industry

        industry_lower = industry.lower()
        for fit in self.industry_fit_scores:
            if fit.industry.lower() == industry_lower:
                return fit.fit_score

        # Check partial match
        for fit in self.industry_fit_scores:
            if fit.industry.lower() in industry_lower or industry_lower in fit.industry.lower():
                return fit.fit_score

        return 50  # Default for unknown industry

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScoringContext":
        """Create ScoringContext from dictionary."""
        niche_data = data.get("niche", {})
        personas_data = data.get("personas", [])
        industry_scores_data = data.get("industry_fit_scores", [])

        return cls(
            niche=NicheContext.from_dict(niche_data),
            personas=[PersonaContext.from_dict(p) for p in personas_data],
            industry_fit_scores=[IndustryFitScore.from_dict(s) for s in industry_scores_data],
            target_countries=data.get("target_countries", ["United States", "US"]),
        )


@dataclass
class ScoringInput:
    """Input for lead scoring agent."""

    campaign_id: str
    available_leads: int
    leads: list[LeadScoreRecord] = field(default_factory=list)
    scoring_context: ScoringContext | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScoringInput":
        """Create ScoringInput from dictionary."""
        leads_data = data.get("leads", [])
        context_data = data.get("scoring_context")

        return cls(
            campaign_id=str(data.get("campaign_id", "")),
            available_leads=int(data.get("available_leads", len(leads_data))),
            leads=[LeadScoreRecord.from_dict(lead) for lead in leads_data],
            scoring_context=ScoringContext.from_dict(context_data) if context_data else None,
        )


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown for a lead."""

    job_title_match: dict[str, Any] = field(default_factory=dict)
    seniority_match: dict[str, Any] = field(default_factory=dict)
    company_size_match: dict[str, Any] = field(default_factory=dict)
    industry_fit: dict[str, Any] = field(default_factory=dict)
    location_match: dict[str, Any] = field(default_factory=dict)
    data_completeness: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_title_match": self.job_title_match,
            "seniority_match": self.seniority_match,
            "company_size_match": self.company_size_match,
            "industry_fit": self.industry_fit,
            "location_match": self.location_match,
            "data_completeness": self.data_completeness,
        }

    @property
    def total_score(self) -> int:
        """Calculate total score from components."""
        return int(
            self.job_title_match.get("score", 0)
            + self.seniority_match.get("score", 0)
            + self.company_size_match.get("score", 0)
            + self.industry_fit.get("score", 0)
            + self.location_match.get("score", 0)
            + self.data_completeness.get("score", 0)
        )


@dataclass
class LeadScore:
    """Scored lead result."""

    lead_id: str
    total_score: int
    tier: str
    breakdown: ScoreBreakdown
    persona_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "lead_id": self.lead_id,
            "score": self.total_score,
            "tier": self.tier,
            "breakdown": self.breakdown.to_dict(),
            "persona_tags": self.persona_tags,
        }


@dataclass
class ScoringOutput:
    """Output from lead scoring agent."""

    # Counts
    total_scored: int = 0
    avg_score: float = 0.0
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_c_count: int = 0
    tier_d_count: int = 0

    # Score distribution
    score_distribution: dict[str, int] = field(default_factory=dict)

    # Individual scores for database updates
    lead_scores: list[LeadScore] = field(default_factory=list)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_scored": self.total_scored,
            "avg_score": round(self.avg_score, 2),
            "tier_a_count": self.tier_a_count,
            "tier_b_count": self.tier_b_count,
            "tier_c_count": self.tier_c_count,
            "tier_d_count": self.tier_d_count,
            "score_distribution": self.score_distribution,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
        }
