"""
Test fixtures for Persona Research Agent.

Provides mock data, sample responses, and test utilities
for unit and integration testing.
"""

import uuid
from typing import Any

import pytest

from src.agents.persona_research.schemas import (
    IndustryFitScore,
    LanguagePattern,
    MessagingAngle,
    Objection,
    PainPointQuote,
    Persona,
    PersonaResearchConfig,
    PersonaResearchData,
    PersonaResearchResult,
    SeniorityLevel,
    ToneType,
)

# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_niche_id() -> str:
    """Sample niche UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_persona_id() -> str:
    """Sample persona UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_job_titles() -> list[str]:
    """Sample job titles for testing."""
    return ["VP of Sales", "Sales Director", "Head of Sales"]


@pytest.fixture
def sample_industry() -> str:
    """Sample industry for testing."""
    return "SaaS"


@pytest.fixture
def sample_pain_points_hint() -> list[str]:
    """Sample pain point hints from niche research."""
    return [
        "CRM adoption is low",
        "Sales reps spend too much time on admin",
        "Pipeline visibility is poor",
    ]


@pytest.fixture
def sample_config(
    sample_niche_id: str, sample_pain_points_hint: list[str]
) -> PersonaResearchConfig:
    """Sample PersonaResearchConfig."""
    return PersonaResearchConfig(
        niche_id=sample_niche_id,
        pain_points_hint=sample_pain_points_hint,
        max_personas=2,
        reddit_enabled=True,
        linkedin_enabled=True,
        industry_content_enabled=True,
    )


@pytest.fixture
def sample_niche_data(sample_niche_id: str) -> dict[str, Any]:
    """Sample niche data from database."""
    return {
        "id": sample_niche_id,
        "name": "SaaS Sales Leaders",
        "slug": "saas-sales-leaders",
        "industry": "SaaS",
        "job_titles": ["VP of Sales", "Sales Director", "Head of Sales"],
        "company_size": "50-500",
        "location": "US",
        "pain_points": ["CRM adoption", "Pipeline visibility", "Rep productivity"],
        "value_propositions": ["Automated data entry", "Real-time insights"],
    }


# ============================================================================
# Pain Point Fixtures
# ============================================================================


@pytest.fixture
def sample_pain_point_quote() -> PainPointQuote:
    """Sample pain point quote."""
    return PainPointQuote(
        pain="CRM adoption is a nightmare",
        intensity=8,
        quote="I've spent 6 months trying to get my team to actually use our CRM consistently. It's like pulling teeth.",
        source="https://reddit.com/r/sales/comments/abc123",
        source_type="reddit",
        frequency="common",
        engagement_score=156,
        raw={
            "post_id": "abc123",
            "subreddit": "sales",
            "num_comments": 45,
        },
    )


@pytest.fixture
def sample_pain_points() -> list[PainPointQuote]:
    """Multiple sample pain points."""
    return [
        PainPointQuote(
            pain="CRM adoption is a nightmare",
            intensity=8,
            quote="I've spent 6 months trying to get my team to actually use our CRM.",
            source="https://reddit.com/r/sales/comments/abc123",
            source_type="reddit",
            frequency="common",
            engagement_score=156,
        ),
        PainPointQuote(
            pain="Pipeline visibility is terrible",
            intensity=7,
            quote="My pipeline data is always 2 weeks behind reality.",
            source="https://reddit.com/r/sales/comments/def456",
            source_type="reddit",
            frequency="common",
            engagement_score=89,
        ),
        PainPointQuote(
            pain="Sales reps hate data entry",
            intensity=9,
            quote="My reps spend 30% of their time updating spreadsheets instead of selling.",
            source="https://reddit.com/r/SaaS/comments/ghi789",
            source_type="reddit",
            frequency="very_common",
            engagement_score=234,
        ),
    ]


# ============================================================================
# Language Pattern Fixtures
# ============================================================================


@pytest.fixture
def sample_language_pattern() -> LanguagePattern:
    """Sample language pattern."""
    return LanguagePattern(
        phrase="drives me crazy",
        context="When describing CRM frustrations",
        category="emotional",
        source="reddit",
        frequency=5,
    )


@pytest.fixture
def sample_language_patterns() -> list[LanguagePattern]:
    """Multiple sample language patterns."""
    return [
        LanguagePattern(
            phrase="drives me crazy",
            context="CRM frustrations",
            category="emotional",
            source="reddit",
            frequency=5,
        ),
        LanguagePattern(
            phrase="waste of time",
            context="Admin work complaints",
            category="pain",
            source="reddit",
            frequency=8,
        ),
        LanguagePattern(
            phrase="pipeline visibility",
            context="Sales forecasting discussions",
            category="jargon",
            source="linkedin",
            frequency=3,
        ),
    ]


# ============================================================================
# Objection Fixtures
# ============================================================================


@pytest.fixture
def sample_objection() -> Objection:
    """Sample objection."""
    return Objection(
        objection="We don't have budget for this right now",
        real_meaning="I'm not convinced of the ROI",
        counter_approach="Show specific cost savings and time-to-value",
        frequency="very_common",
    )


@pytest.fixture
def sample_objections() -> list[Objection]:
    """Multiple sample objections."""
    return [
        Objection(
            objection="We don't have budget for this right now",
            real_meaning="I'm not convinced of the ROI",
            counter_approach="Show specific cost savings",
            frequency="very_common",
        ),
        Objection(
            objection="We're already using a CRM",
            real_meaning="I don't want to go through another migration",
            counter_approach="Emphasize seamless integration",
            frequency="common",
        ),
        Objection(
            objection="Send me some information",
            real_meaning="I want to end this conversation",
            counter_approach="Ask a qualifying question instead",
            frequency="common",
        ),
    ]


# ============================================================================
# Messaging Angle Fixtures
# ============================================================================


@pytest.fixture
def sample_messaging_angle() -> MessagingAngle:
    """Sample messaging angle."""
    return MessagingAngle(
        angle="Pain-focused",
        hook="Stop losing deals to bad CRM data",
        supporting_pain="Pipeline visibility is terrible",
        confidence_score=0.85,
    )


# ============================================================================
# Persona Fixtures
# ============================================================================


@pytest.fixture
def sample_persona(
    sample_persona_id: str,
    sample_niche_id: str,
    sample_pain_points: list[PainPointQuote],
    sample_language_patterns: list[LanguagePattern],
    sample_objections: list[Objection],
    sample_messaging_angle: MessagingAngle,
) -> Persona:
    """Complete sample persona."""
    return Persona(
        id=sample_persona_id,
        niche_id=sample_niche_id,
        name="The Scaling VP",
        job_titles=["VP of Sales", "Sales Director", "Head of Sales"],
        seniority_level=SeniorityLevel.VP,
        department="Sales",
        pain_points=sample_pain_points,
        goals=[
            "Hit revenue targets consistently",
            "Scale sales team efficiently",
            "Improve pipeline predictability",
            "Reduce rep ramp time",
            "Maintain team morale during growth",
        ],
        objections=sample_objections,
        language_patterns=sample_language_patterns,
        trigger_events=[
            "New job or promotion",
            "Funding round announcement",
            "Hiring spike",
            "Quarter end approaching",
            "Competitor pressure",
        ],
        messaging_angles={
            "primary": sample_messaging_angle,
            "secondary": MessagingAngle(
                angle="Goal-focused",
                hook="Hit your number with better data",
                supporting_pain="Pipeline visibility is terrible",
                confidence_score=0.7,
            ),
        },
        angles_to_avoid=[
            "Generic productivity claims",
            "Price-focused messaging",
            "Technical jargon overload",
        ],
        confidence_score=0.8,
    )


# ============================================================================
# Industry Fit Score Fixtures
# ============================================================================


@pytest.fixture
def sample_industry_fit_score() -> IndustryFitScore:
    """Sample industry fit score."""
    return IndustryFitScore(
        industry="SaaS",
        score=82,
        reasoning="Strong pain point alignment with 3 high-intensity matches.",
        pain_point_alignment=[
            "CRM adoption is a nightmare",
            "Pipeline visibility is terrible",
            "Sales reps hate data entry",
        ],
    )


# ============================================================================
# Research Data Fixtures
# ============================================================================


@pytest.fixture
def sample_research_data(sample_persona_id: str) -> PersonaResearchData:
    """Sample research data for audit trail."""
    return PersonaResearchData(
        persona_id=sample_persona_id,
        source="reddit",
        url="https://reddit.com/r/sales/comments/abc123",
        content_type="post",
        content="I've spent 6 months trying to get my team to use our CRM...",
        insights=["CRM adoption is challenging", "Takes ~6 months to see results"],
        language_samples=["pulling teeth", "drives me crazy"],
        quotes=["I've spent 6 months trying to get my team to actually use our CRM"],
        engagement_metrics={"score": 156, "num_comments": 45},
    )


# ============================================================================
# Result Fixtures
# ============================================================================


@pytest.fixture
def sample_research_result(
    sample_niche_id: str,
    sample_persona: Persona,
    sample_industry_fit_score: IndustryFitScore,
    sample_research_data: PersonaResearchData,
) -> PersonaResearchResult:
    """Complete sample research result."""
    return PersonaResearchResult(
        personas=[sample_persona],
        persona_ids=[sample_persona.id],
        consolidated_pain_points=[
            "CRM adoption is a nightmare",
            "Pipeline visibility is terrible",
            "Sales reps hate data entry",
        ],
        value_propositions=[
            "Solve CRM adoption with automated data entry",
            "Get real-time pipeline visibility",
            "Free up rep time for selling",
        ],
        recommended_tone=ToneType.PROFESSIONAL,
        industry_scores=[sample_industry_fit_score],
        research_data=[sample_research_data],
        sources_used=[
            {
                "tool": "reddit_miner",
                "queries_count": 3,
                "results_count": 75,
                "urls": ["https://reddit.com/r/sales", "https://reddit.com/r/SaaS"],
            },
            {
                "tool": "web_search_linkedin",
                "queries_count": 3,
                "results_count": 15,
                "urls": [],
            },
        ],
        niche_id=sample_niche_id,
        total_quotes_collected=12,
        total_language_patterns=25,
        reddit_sources_count=75,
        execution_time_ms=45000,
    )


# ============================================================================
# Mock Reddit Response Fixtures
# ============================================================================


@pytest.fixture
def mock_reddit_post_data() -> dict[str, Any]:
    """Mock Reddit post data."""
    return {
        "id": "abc123",
        "subreddit": "sales",
        "title": "CRM adoption is killing me",
        "selftext": "I've spent 6 months trying to get my team to actually use our CRM consistently. It's like pulling teeth. Every Monday I have to remind them to update their opportunities.",
        "author": "frustrated_vp",
        "score": 156,
        "upvote_ratio": 0.92,
        "num_comments": 45,
        "created_utc": 1703001600.0,
        "url": "https://reddit.com/r/sales/comments/abc123",
        "permalink": "/r/sales/comments/abc123",
        "is_self": True,
        "is_video": False,
        "over_18": False,
        "spoiler": False,
        "stickied": False,
        "locked": False,
    }


@pytest.fixture
def mock_reddit_comment_data() -> dict[str, Any]:
    """Mock Reddit comment data."""
    return {
        "id": "comment123",
        "post_id": "abc123",
        "subreddit": "sales",
        "body": "Same here. My team's CRM data is always 2 weeks behind. It drives me crazy when I'm trying to forecast.",
        "author": "another_vp",
        "score": 89,
        "created_utc": 1703005200.0,
        "permalink": "/r/sales/comments/abc123/comment/comment123",
        "is_submitter": False,
        "stickied": False,
    }


@pytest.fixture
def mock_reddit_mining_result() -> dict[str, Any]:
    """Mock Reddit mining result."""
    return {
        "pain_points": [
            {
                "pain": "CRM adoption is a nightmare",
                "intensity": 8,
                "quote": "I've spent 6 months trying to get my team to actually use our CRM.",
                "source": "https://reddit.com/r/sales/comments/abc123",
                "source_type": "reddit",
                "frequency": "common",
                "engagement_score": 156,
            },
            {
                "pain": "Pipeline visibility is terrible",
                "intensity": 7,
                "quote": "My pipeline data is always 2 weeks behind reality.",
                "source": "https://reddit.com/r/sales/comments/def456",
                "source_type": "reddit",
                "frequency": "common",
                "engagement_score": 89,
            },
        ],
        "language_patterns": [
            {"phrase": "drives me crazy", "category": "emotional", "frequency": 5},
            {"phrase": "waste of time", "category": "pain", "frequency": 8},
        ],
        "quotes": [
            {
                "quote": "I've spent 6 months trying to get my team to actually use our CRM.",
                "source": "https://reddit.com/r/sales/comments/abc123",
                "intensity": 8,
                "engagement": 156,
            }
        ],
        "emotional_indicators": ["frustrated", "nightmare", "drives me crazy"],
        "posts_analyzed": 75,
        "comments_analyzed": 250,
        "subreddit_relevance": {"sales": 8.5, "SaaS": 7.2, "Entrepreneur": 5.1},
    }


# ============================================================================
# Mock Web Search Response Fixtures
# ============================================================================


@pytest.fixture
def mock_linkedin_search_result() -> dict[str, Any]:
    """Mock LinkedIn web search result."""
    return {
        "query": "site:linkedin.com VP of Sales SaaS challenges",
        "content": "Found LinkedIn profiles and posts from VP of Sales discussing challenges...",
    }


@pytest.fixture
def mock_industry_search_result() -> dict[str, Any]:
    """Mock industry content search result."""
    return {
        "query": "state of SaaS sales report 2025",
        "content": "According to the 2025 State of Sales report, 68% of sales leaders cite CRM adoption as their top challenge...",
    }
