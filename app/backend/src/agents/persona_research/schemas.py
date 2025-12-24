"""
Data models for Persona Research Agent.

Defines comprehensive data structures for buyer personas including
pain points with exact quotes, language patterns, objections,
messaging angles, and industry fit scores.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SeniorityLevel(str, Enum):
    """Seniority levels for personas."""

    C_SUITE = "c_suite"
    VP = "vp"
    DIRECTOR = "director"
    MANAGER = "manager"
    SENIOR_IC = "senior_ic"
    IC = "ic"


class ToneType(str, Enum):
    """Recommended messaging tone types."""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    DIRECT = "direct"
    CONSULTATIVE = "consultative"


class PainSeverity(str, Enum):
    """Pain point severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PainPointQuote:
    """
    A pain point with exact quote from real research.

    The quote is critical - it must be the exact words used,
    not paraphrased, for effective cold email personalization.
    """

    pain: str  # Description of the pain point
    intensity: int  # 1-10 scale
    quote: str  # EXACT quote from research (not paraphrased)
    source: str  # URL or source reference
    source_type: str = "reddit"  # reddit, linkedin, industry_report
    frequency: str = "occasional"  # rare, occasional, common, very_common
    engagement_score: int = 0  # Upvotes/likes from source
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LanguagePattern:
    """
    Language pattern extracted from persona research.

    These are exact phrases the target persona uses when
    discussing problems, goals, or their work.
    """

    phrase: str  # The exact phrase they use
    context: str  # When/how they use it
    category: str = "general"  # pain, goal, jargon, emotional
    source: str = ""  # Where it was found
    frequency: int = 1  # How many times observed
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Objection:
    """
    Common objection and how to counter it.

    Objections are what prospects say to dismiss cold emails.
    Understanding the real meaning helps craft better responses.
    """

    objection: str  # What they say
    real_meaning: str  # What they actually mean
    counter_approach: str  # How to address it
    frequency: str = "common"  # rare, occasional, common, very_common
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessagingAngle:
    """
    A messaging approach for cold email outreach.

    Primary angles are the best approach, secondary for non-responders.
    """

    angle: str  # The messaging approach
    hook: str  # Opening hook/line
    supporting_pain: str  # Pain point this addresses
    confidence_score: float = 0.7  # How confident we are this will work
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Persona:
    """
    Complete buyer persona with all research data.

    A persona represents a distinct type of buyer within the niche,
    with their specific pain points, language, and messaging needs.
    """

    # Identity
    name: str  # Memorable name like "The Scaling VP"
    job_titles: list[str]  # Actual titles they use
    seniority_level: SeniorityLevel
    department: str

    # Pain points with quotes (CRITICAL)
    pain_points: list[PainPointQuote]

    # Goals and aspirations
    goals: list[str]

    # Objections and counters
    objections: list[Objection]

    # Language patterns
    language_patterns: list[LanguagePattern]

    # Trigger events that create buying urgency
    trigger_events: list[str]

    # Messaging recommendations
    messaging_angles: dict[str, MessagingAngle]  # primary, secondary
    angles_to_avoid: list[str]

    # Metadata
    id: str = ""
    niche_id: str = ""
    confidence_score: float = 0.7
    created_at: datetime = field(default_factory=datetime.now)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndustryFitScore:
    """
    Industry fit score for lead scoring.

    Scores how well the niche/persona fits a specific industry,
    used to prioritize leads during list building.
    """

    industry: str
    score: int  # 0-100
    reasoning: str
    pain_point_alignment: list[str]  # Which pain points align
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaResearchData:
    """
    Raw research data collected during persona research.

    Stored for audit trail and future reference.
    """

    persona_id: str
    source: str  # reddit, linkedin, web
    url: str
    content_type: str  # post, comment, article, profile
    content: str  # Raw content
    insights: list[str]  # Extracted insights
    language_samples: list[str]  # Language patterns found
    quotes: list[str]  # Exact quotes extracted
    engagement_metrics: dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaResearchResult:
    """
    Complete results from persona research.

    This is the final output of the Persona Research Agent,
    containing all personas, consolidated pain points, and scores.
    """

    # Core outputs
    personas: list[Persona]
    persona_ids: list[str]
    consolidated_pain_points: list[str]
    value_propositions: list[str]
    recommended_tone: ToneType
    industry_scores: list[IndustryFitScore]

    # Research data for audit trail
    research_data: list[PersonaResearchData]

    # Sources used for transparency
    sources_used: list[dict[str, Any]]

    # Metadata
    niche_id: str = ""
    total_quotes_collected: int = 0
    total_language_patterns: int = 0
    reddit_sources_count: int = 0
    research_timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaResearchConfig:
    """
    Configuration for persona research execution.

    Controls research depth, timeouts, and source priorities.
    """

    niche_id: str

    # Optional hints from niche research
    pain_points_hint: list[str] = field(default_factory=list)
    competitors_hint: list[dict[str, Any]] = field(default_factory=list)

    # Research parameters
    max_personas: int = 3
    max_quotes_per_persona: int = 10
    max_language_patterns: int = 20

    # Source configuration
    reddit_enabled: bool = True
    linkedin_enabled: bool = True
    industry_content_enabled: bool = True

    # Parallel execution
    max_parallel_searches: int = 15
    max_parallel_fetch: int = 10

    # Timeouts
    timeout_seconds: int = 900  # 15 minutes

    raw: dict[str, Any] = field(default_factory=dict)
