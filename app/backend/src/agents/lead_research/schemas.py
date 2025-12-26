"""Pydantic schemas for Lead Research Agent.

Defines input/output schemas, tier configurations, and data models
for lead research operations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Enums
# =============================================================================


class LeadTier(str, Enum):
    """Lead tier classification."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ResearchDepth(str, Enum):
    """Research depth levels."""

    DEEP = "deep"
    STANDARD = "standard"
    BASIC = "basic"


class FactCategory(str, Enum):
    """Fact categorization for personalization angles."""

    LINKEDIN_POST = "linkedin_post"
    ARTICLE = "article"
    PODCAST = "podcast"
    TALK = "talk"
    CAREER_MOVE = "career_move"
    ACHIEVEMENT = "achievement"


# =============================================================================
# Tier Configuration
# =============================================================================


class TierConfig(BaseModel):
    """Configuration for a lead tier's research depth."""

    model_config = ConfigDict(frozen=True)

    depth: ResearchDepth
    queries: int
    max_cost: Decimal
    include: list[str]


# Tier configurations as defined in YAML spec
TIER_CONFIGS: dict[LeadTier, TierConfig] = {
    LeadTier.A: TierConfig(
        depth=ResearchDepth.DEEP,
        queries=5,
        max_cost=Decimal("0.15"),
        include=["linkedin_posts", "articles", "podcasts", "talks"],
    ),
    LeadTier.B: TierConfig(
        depth=ResearchDepth.STANDARD,
        queries=3,
        max_cost=Decimal("0.05"),
        include=["linkedin_posts", "articles"],
    ),
    LeadTier.C: TierConfig(
        depth=ResearchDepth.BASIC,
        queries=1,
        max_cost=Decimal("0.01"),
        include=["headline_analysis"],
    ),
    LeadTier.D: TierConfig(
        depth=ResearchDepth.BASIC,
        queries=1,
        max_cost=Decimal("0.01"),
        include=["headline_analysis"],
    ),
}


# Cost controls
COST_CONTROLS = {
    "max_per_campaign": Decimal("150.00"),
    "max_per_lead_tier_a": Decimal("0.15"),
    "max_per_lead_tier_b": Decimal("0.05"),
    "max_per_lead_tier_c": Decimal("0.01"),
    "alert_at_percent": 80,
}


# API costs per call (in USD)
# These values should be updated if API pricing changes
API_COSTS = {
    "tavily_search": Decimal("0.001"),  # Tavily search API cost per call
    "serper_search": Decimal("0.001"),  # Serper search API cost per call
    "perplexity_search": Decimal("0.005"),  # Perplexity API cost per call
    "headline_analysis": Decimal("0.0"),  # No API cost for local analysis
}


# =============================================================================
# Input Schemas
# =============================================================================


class LeadResearchInput(BaseModel):
    """Input for lead research agent."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    max_leads: int | None = Field(default=None, description="Max leads to process")
    resume_from_checkpoint: bool = Field(default=True, description="Resume from last checkpoint")


class LeadData(BaseModel):
    """Lead data for research."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None  # DB uses 'title', not 'job_title'
    headline: str | None = None
    linkedin_url: str | None = None
    company_name: str | None = None
    lead_score: int | None = None
    lead_tier: LeadTier | None = None
    company_research_id: UUID | None = None

    @property
    def full_name(self) -> str:
        """Get full name from first and last name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

    def get_tier_config(self) -> TierConfig:
        """Get configuration for this lead's tier."""
        tier = self.lead_tier or LeadTier.C
        return TIER_CONFIGS.get(tier, TIER_CONFIGS[LeadTier.C])


# =============================================================================
# Fact Schemas
# =============================================================================


class ExtractedFact(BaseModel):
    """A fact extracted from research."""

    model_config = ConfigDict(from_attributes=True)

    text: str = Field(description="The fact text")
    source_type: FactCategory = Field(description="Category of the fact")
    source_url: str | None = Field(default=None, description="URL where fact was found")
    fact_date: date | None = Field(default=None, description="Date of the fact")
    recency_days: int | None = Field(default=None, description="Days since fact occurred")
    context: str | None = Field(default=None, description="Additional context")

    # Scores (0.0 to 1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    specificity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    business_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    emotional_hook_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_score: float = Field(default=0.0, ge=0.0, le=1.0)


class RankedAngle(BaseModel):
    """A ranked personalization angle."""

    model_config = ConfigDict(from_attributes=True)

    lead_id: UUID
    fact_id: UUID | None = None
    rank_position: int
    angle_type: FactCategory | str
    angle_text: str = Field(description="Opening line template")

    # Scores
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    specificity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    business_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    emotional_hook_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_score: float = Field(default=0.0, ge=0.0, le=1.0)

    is_fallback: bool = Field(default=False, description="Whether this is a fallback angle")


# =============================================================================
# Research Result Schemas
# =============================================================================


class LinkedInPost(BaseModel):
    """A LinkedIn post found during research."""

    model_config = ConfigDict(from_attributes=True)

    content: str
    post_date: date | None = None
    topics: list[str] = Field(default_factory=list)
    engagement: int | None = None
    url: str | None = None


class ResearchResult(BaseModel):
    """Research result for a single lead."""

    model_config = ConfigDict(from_attributes=True)

    lead_id: UUID
    research_depth: ResearchDepth
    profile_headline: str | None = None
    recent_activity: str | None = None
    key_interests: list[str] = Field(default_factory=list)
    linkedin_posts: list[LinkedInPost] = Field(default_factory=list)
    articles: list[dict[str, Any]] = Field(default_factory=list)
    podcasts: list[dict[str, Any]] = Field(default_factory=list)
    primary_hook: str | None = None
    summary: str | None = None
    primary_source_url: str | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    research_cost: Decimal = Field(default=Decimal("0.0"))
    queries_used: int = Field(default=0)
    facts: list[ExtractedFact] = Field(default_factory=list)
    angles: list[RankedAngle] = Field(default_factory=list)


# =============================================================================
# Output Schemas
# =============================================================================


class LeadResearchOutput(BaseModel):
    """Output from lead research agent."""

    model_config = ConfigDict(from_attributes=True)

    total_researched: int
    tier_breakdown: dict[str, int] = Field(default_factory=dict)
    facts_extracted: int
    avg_hooks_per_lead: float
    opening_lines_generated: int
    research_cost: Decimal
    cost_by_tier: dict[str, Decimal] = Field(default_factory=dict)
    fallback_to_company_research: int
    processing_time_ms: int | None = None


class CampaignResearchSummary(BaseModel):
    """Summary of research for a campaign."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    total_leads: int
    leads_researched: int
    leads_skipped: int
    total_facts: int
    total_angles: int
    total_cost: Decimal
    avg_quality_score: float
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "in_progress"
