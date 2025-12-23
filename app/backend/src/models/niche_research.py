"""
Data models for Niche Research Agent.

Defines the data structures for niche research results including
subreddit analysis, pain points, and scoring metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NicheSubreddit:
    """A subreddit relevant to a niche."""

    name: str
    title: str
    description: str
    subscriber_count: int
    active_users: int
    engagement_score: float
    relevance_score: float
    url: str
    created_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NichePainPoint:
    """A pain point extracted from niche discussions."""

    description: str
    severity: str  # "low", "medium", "high"
    frequency: int  # How often mentioned
    source_posts: list[str] = field(default_factory=list)
    source_subreddits: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NicheOpportunity:
    """An identified business opportunity in the niche."""

    description: str
    pain_point: str  # Linked pain point
    target_audience: str
    potential_reach: int  # Estimated audience size
    confidence_score: float
    supporting_evidence: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NicheResearchResult:
    """Complete niche research results."""

    niche: str
    subreddits: list[NicheSubreddit] = field(default_factory=list)
    pain_points: list[NichePainPoint] = field(default_factory=list)
    opportunities: list[NicheOpportunity] = field(default_factory=list)
    total_subscribers: int = 0
    total_active_users: int = 0
    research_metadata: dict[str, Any] = field(default_factory=dict)
    raw_responses: dict[str, Any] = field(default_factory=dict)


@dataclass
class NicheAnalysisConfig:
    """Configuration for niche research analysis."""

    search_query: str
    max_subreddits: int = 10
    posts_per_subreddit: int = 25
    min_subscribers: int = 1000
    include_nsfw: bool = False
    engagement_weight: float = 0.5
    relevance_weight: float = 0.5
    raw: dict[str, Any] = field(default_factory=dict)
