"""
Pydantic schemas for Company Research Agent.

Defines input/output types for the agent and its tools, following
SDK patterns for type safety and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class CompanyToResearch:
    """A company to research from the leads table."""

    lead_id: UUID
    company_name: str
    company_domain: str
    company_linkedin_url: str | None = None
    company_industry: str | None = None
    company_size: str | None = None
    lead_count: int = 1
    max_lead_score: int | None = None


@dataclass
class ExtractedFact:
    """An individual fact extracted from research with scoring."""

    fact_text: str
    category: str  # news, funding, hiring, product_launch, partnership, award, leadership
    source_type: str  # web_search, news, linkedin
    source_url: str | None = None
    fact_date: datetime | None = None
    recency_days: int | None = None

    # Scoring components (0.0 to 1.0)
    recency_score: float = 0.0
    specificity_score: float = 0.0
    business_relevance_score: float = 0.0
    emotional_hook_score: float = 0.0
    total_score: float = 0.0

    # Context for email writing
    context_notes: str | None = None
    suggested_angle: str | None = None


@dataclass
class ResearchResult:
    """Research result for a single company."""

    company_domain: str
    company_name: str
    research_id: UUID | None = None

    # Research findings
    headline: str | None = None
    summary: str | None = None
    content: dict[str, Any] = field(default_factory=dict)

    # Source info
    primary_source_url: str | None = None
    source_urls: list[str] = field(default_factory=list)
    latest_news_date: datetime | None = None

    # Analysis
    relevance_score: float = 0.0
    sentiment: str | None = None  # positive, neutral, negative
    key_insights: list[str] = field(default_factory=list)
    personalization_hooks: list[str] = field(default_factory=list)
    primary_hook: str | None = None

    # Categories found
    has_recent_news: bool = False
    has_funding: bool = False
    has_hiring: bool = False
    has_product_launch: bool = False

    # Extracted facts
    facts: list[ExtractedFact] = field(default_factory=list)

    # Cost tracking
    research_cost: float = 0.0
    tools_used: list[str] = field(default_factory=list)

    # Status
    success: bool = True
    error_message: str | None = None


@dataclass
class CompanyResearchInput:
    """Input schema for Company Research Agent."""

    campaign_id: UUID
    research_depth: str = "standard"  # minimal, standard, deep
    max_companies: int = 1000
    max_cost_per_company: float = 0.10
    max_total_cost: float = 100.0


@dataclass
class CompanyResearchOutput:
    """Output schema for Company Research Agent."""

    campaign_id: UUID
    total_companies: int = 0
    companies_researched: int = 0
    companies_failed: int = 0
    facts_extracted: int = 0
    hooks_generated: int = 0

    # Hook breakdown by category
    personalization_hooks: dict[str, int] = field(default_factory=dict)

    # Cost tracking
    research_cost: float = 0.0
    cost_by_tool: dict[str, float] = field(default_factory=dict)

    # Quality metrics
    avg_fact_score: float = 0.0
    avg_relevance_score: float = 0.0

    # Reliability metrics
    circuit_breaker_trips: int = 0

    # Status
    success: bool = True
    error_message: str | None = None

    # Duration
    duration_seconds: float = 0.0


@dataclass
class CostTracker:
    """Tracks research costs across the agent run."""

    max_per_campaign: float = 100.0
    max_per_company: float = 0.10
    alert_at_percent: float = 0.80

    total_cost: float = 0.0
    cost_by_tool: dict[str, float] = field(default_factory=dict)
    companies_researched: int = 0

    def add_cost(self, tool_name: str, cost: float) -> None:
        """Add cost for a tool usage."""
        self.total_cost += cost
        if tool_name not in self.cost_by_tool:
            self.cost_by_tool[tool_name] = 0.0
        self.cost_by_tool[tool_name] += cost

    def can_continue(self, company_cost_estimate: float = 0.0) -> bool:
        """Check if we can continue researching."""
        return self.total_cost + company_cost_estimate < self.max_per_campaign

    def is_at_alert_threshold(self) -> bool:
        """Check if we're at the alert threshold."""
        return self.total_cost >= self.max_per_campaign * self.alert_at_percent

    def get_remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0.0, self.max_per_campaign - self.total_cost)
