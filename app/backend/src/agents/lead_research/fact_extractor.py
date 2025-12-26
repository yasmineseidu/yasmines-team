"""Fact extraction and scoring for Lead Research Agent.

Extracts facts from research results and scores them based on:
- Recency (30% weight, 60-day decay)
- Specificity (25%)
- Business relevance (25%)
- Emotional hook (20%)

Facts below 0.5 threshold are filtered out.
"""

import logging
import math
from datetime import date, datetime
from typing import Any

from src.agents.lead_research.schemas import (
    ExtractedFact,
    FactCategory,
    RankedAngle,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Scoring Configuration
# =============================================================================

SCORING_WEIGHTS = {
    "recency": 0.30,
    "specificity": 0.25,
    "business_relevance": 0.25,
    "emotional_hook": 0.20,
}

RECENCY_DECAY_DAYS = 60  # Days after which recency score starts decaying
MIN_SCORE_THRESHOLD = 0.5  # Minimum score to keep a fact


# =============================================================================
# Fact Extraction
# =============================================================================


def extract_facts_from_research(
    research_data: dict[str, Any],
    lead_id: str,
) -> list[ExtractedFact]:
    """
    Extract facts from research results.

    Args:
        research_data: Raw research data from tools.
        lead_id: UUID of the lead.

    Returns:
        List of extracted facts with scores.
    """
    facts: list[ExtractedFact] = []

    # Extract from LinkedIn posts
    posts = research_data.get("linkedin_posts", [])
    for post in posts:
        fact = _extract_fact_from_post(post)
        if fact:
            facts.append(fact)

    # Extract from articles
    articles = research_data.get("articles", [])
    for article in articles:
        fact = _extract_fact_from_article(article)
        if fact:
            facts.append(fact)

    # Extract from podcasts
    podcasts = research_data.get("podcasts", [])
    for podcast in podcasts:
        fact = _extract_fact_from_podcast(podcast)
        if fact:
            facts.append(fact)

    # Extract from profile headline
    profile = research_data.get("profile", {})
    if profile:
        fact = _extract_fact_from_profile(profile)
        if fact:
            facts.append(fact)

    # Score all facts
    scored_facts = [score_fact(fact) for fact in facts]

    # Filter by threshold
    filtered_facts = [f for f in scored_facts if f.total_score >= MIN_SCORE_THRESHOLD]

    logger.info(
        f"Extracted {len(facts)} facts, {len(filtered_facts)} above threshold for lead {lead_id}"
    )

    return filtered_facts


def _extract_fact_from_post(post: dict[str, Any]) -> ExtractedFact | None:
    """Extract a fact from a LinkedIn post."""
    content = post.get("content", "")
    if not content or len(content) < 20:
        return None

    # Try to extract meaningful text
    fact_text = _extract_key_point(content)
    if not fact_text:
        return None

    # Parse date if available
    post_date = _parse_date(post.get("post_date"))
    recency_days = _calculate_recency_days(post_date) if post_date else None

    # Convert topics list to comma-separated string for context
    topics = post.get("topics")
    context = None
    if isinstance(topics, list) and topics:
        context = ", ".join(str(t) for t in topics[:3])
    elif isinstance(topics, str):
        context = topics

    return ExtractedFact(
        text=fact_text,
        source_type=FactCategory.LINKEDIN_POST,
        source_url=post.get("url"),
        fact_date=post_date,
        recency_days=recency_days,
        context=context,
    )


def _extract_fact_from_article(article: dict[str, Any]) -> ExtractedFact | None:
    """Extract a fact from an article."""
    title = article.get("title", "")
    if not title:
        return None

    publication = article.get("publication", "")
    if publication:
        fact_text = f"Published article '{title}' in {publication}"
    else:
        fact_text = f"Published article '{title}'"

    return ExtractedFact(
        text=fact_text,
        source_type=FactCategory.ARTICLE,
        source_url=article.get("url"),
        context=article.get("content", "")[:200] if article.get("content") else None,
    )


def _extract_fact_from_podcast(podcast: dict[str, Any]) -> ExtractedFact | None:
    """Extract a fact from a podcast appearance."""
    title = podcast.get("title", "")
    if not title:
        return None

    podcast_name = podcast.get("podcast_name", "")
    if podcast_name:
        fact_text = f"Guest on '{podcast_name}': {title}"
    else:
        fact_text = f"Podcast appearance: {title}"

    return ExtractedFact(
        text=fact_text,
        source_type=FactCategory.PODCAST,
        source_url=podcast.get("url"),
        context=podcast.get("content", "")[:200] if podcast.get("content") else None,
    )


def _extract_fact_from_profile(profile: dict[str, Any]) -> ExtractedFact | None:
    """Extract a fact from LinkedIn profile."""
    headline = profile.get("headline", "")
    about = profile.get("about", "")

    if not headline and not about:
        return None

    # Use headline if available, otherwise about
    fact_text = headline if headline else about[:200]

    return ExtractedFact(
        text=fact_text,
        source_type=FactCategory.CAREER_MOVE,
        source_url=profile.get("url"),
    )


def _extract_key_point(content: str) -> str | None:
    """Extract the most important point from content."""
    if not content:
        return None

    # Clean and truncate
    cleaned = content.strip()
    if len(cleaned) > 200:
        # Try to find a natural break point
        break_points = [". ", "! ", "? ", "\n"]
        for bp in break_points:
            if bp in cleaned[:200]:
                idx = cleaned[:200].rfind(bp)
                return cleaned[: idx + 1].strip()
        return cleaned[:197] + "..."

    return cleaned


def _parse_date(date_value: Any) -> date | None:
    """Parse a date from various formats."""
    if not date_value:
        return None

    if isinstance(date_value, date):
        return date_value

    if isinstance(date_value, datetime):
        return date_value.date()

    if isinstance(date_value, str):
        # Try common formats
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt).date()
            except ValueError:
                continue

    return None


def _calculate_recency_days(fact_date: date) -> int:
    """Calculate days since the fact occurred."""
    today = date.today()
    delta = today - fact_date
    return delta.days


# =============================================================================
# Fact Scoring
# =============================================================================


def score_fact(fact: ExtractedFact) -> ExtractedFact:
    """
    Score a fact based on scoring criteria.

    Applies:
    - Recency (30% weight, 60-day decay)
    - Specificity (25%)
    - Business relevance (25%)
    - Emotional hook (20%)

    Args:
        fact: The fact to score.

    Returns:
        The fact with scores populated.
    """
    # Calculate recency score
    recency_score = _calculate_recency_score(fact.recency_days)

    # Calculate specificity score
    specificity_score = _calculate_specificity_score(fact.text)

    # Calculate business relevance score
    business_relevance_score = _calculate_business_relevance_score(fact.text, fact.source_type)

    # Calculate emotional hook score
    emotional_hook_score = _calculate_emotional_hook_score(fact.text)

    # Calculate weighted total
    total_score = (
        recency_score * SCORING_WEIGHTS["recency"]
        + specificity_score * SCORING_WEIGHTS["specificity"]
        + business_relevance_score * SCORING_WEIGHTS["business_relevance"]
        + emotional_hook_score * SCORING_WEIGHTS["emotional_hook"]
    )

    # Update fact with scores
    fact.recency_score = round(recency_score, 4)
    fact.specificity_score = round(specificity_score, 4)
    fact.business_relevance_score = round(business_relevance_score, 4)
    fact.emotional_hook_score = round(emotional_hook_score, 4)
    fact.total_score = round(total_score, 4)

    return fact


def _calculate_recency_score(recency_days: int | None) -> float:
    """
    Calculate recency score with exponential decay.

    Score is 1.0 for recent facts and decays exponentially
    after RECENCY_DECAY_DAYS.
    """
    if recency_days is None:
        return 0.5  # Unknown recency gets middle score

    if recency_days <= 0:
        return 1.0

    if recency_days <= RECENCY_DECAY_DAYS:
        return 1.0

    # Exponential decay after decay threshold
    days_over = recency_days - RECENCY_DECAY_DAYS
    # Decay to 0.1 at 365 days
    decay_rate = -math.log(0.1) / (365 - RECENCY_DECAY_DAYS)
    score = math.exp(-decay_rate * days_over)

    return max(0.1, min(1.0, score))


def _calculate_specificity_score(text: str) -> float:
    """
    Calculate specificity score based on content quality.

    Higher scores for:
    - Specific numbers, names, dates
    - Unique details
    - Longer, more detailed content
    """
    if not text:
        return 0.0

    score = 0.5  # Base score

    # Check for specific details
    specificity_indicators = [
        any(char.isdigit() for char in text),  # Contains numbers
        "%" in text,  # Contains percentages
        "$" in text,  # Contains money
        len(text.split()) > 10,  # Longer content
        any(
            word in text.lower()
            for word in ["launched", "achieved", "increased", "reduced", "built"]
        ),
    ]

    for indicator in specificity_indicators:
        if indicator:
            score += 0.1

    return min(1.0, score)


def _calculate_business_relevance_score(text: str, source_type: FactCategory) -> float:
    """
    Calculate business relevance score.

    Higher scores for business-related content and professional sources.
    """
    if not text:
        return 0.0

    score = 0.5  # Base score

    # Source type bonus
    source_bonuses = {
        FactCategory.ARTICLE: 0.2,
        FactCategory.PODCAST: 0.2,
        FactCategory.LINKEDIN_POST: 0.15,
        FactCategory.TALK: 0.25,
        FactCategory.ACHIEVEMENT: 0.2,
        FactCategory.CAREER_MOVE: 0.1,
    }
    score += source_bonuses.get(source_type, 0.0)

    # Business keyword bonus
    business_keywords = [
        "revenue",
        "growth",
        "team",
        "customers",
        "product",
        "strategy",
        "leadership",
        "innovation",
        "technology",
        "market",
        "business",
        "company",
        "startup",
        "enterprise",
    ]

    text_lower = text.lower()
    keyword_count = sum(1 for kw in business_keywords if kw in text_lower)
    score += min(0.2, keyword_count * 0.05)

    return min(1.0, score)


def _calculate_emotional_hook_score(text: str) -> float:
    """
    Calculate emotional hook potential.

    Higher scores for content that creates connection opportunities.
    """
    if not text:
        return 0.0

    score = 0.4  # Base score

    # Personal/emotional indicators
    emotional_keywords = [
        "proud",
        "excited",
        "thrilled",
        "passionate",
        "love",
        "challenge",
        "journey",
        "story",
        "mission",
        "vision",
        "dream",
        "grateful",
    ]

    text_lower = text.lower()
    emotional_count = sum(1 for kw in emotional_keywords if kw in text_lower)
    score += min(0.3, emotional_count * 0.1)

    # Achievement indicators (good hooks)
    achievement_keywords = [
        "won",
        "awarded",
        "recognized",
        "launched",
        "achieved",
        "completed",
        "milestone",
        "success",
    ]

    achievement_count = sum(1 for kw in achievement_keywords if kw in text_lower)
    score += min(0.2, achievement_count * 0.1)

    return min(1.0, score)


# =============================================================================
# Angle Ranking
# =============================================================================


def rank_angles_from_facts(
    facts: list[ExtractedFact],
    lead_id: str,
    max_angles: int = 5,
) -> list[RankedAngle]:
    """
    Create ranked personalization angles from facts.

    Args:
        facts: Scored facts to rank.
        lead_id: UUID of the lead.
        max_angles: Maximum number of angles to return.

    Returns:
        List of ranked angles.
    """
    # Sort facts by total score descending
    sorted_facts = sorted(facts, key=lambda f: f.total_score, reverse=True)

    angles: list[RankedAngle] = []

    for i, fact in enumerate(sorted_facts[:max_angles]):
        # Generate opening line template
        angle_text = _generate_opening_line_template(fact)

        from uuid import UUID, uuid4

        angle = RankedAngle(
            lead_id=UUID(lead_id) if isinstance(lead_id, str) else lead_id,
            fact_id=uuid4(),  # Will be updated when fact is saved
            rank_position=i + 1,
            angle_type=fact.source_type,
            angle_text=angle_text,
            recency_score=fact.recency_score,
            specificity_score=fact.specificity_score,
            business_relevance_score=fact.business_relevance_score,
            emotional_hook_score=fact.emotional_hook_score,
            total_score=fact.total_score,
            is_fallback=False,
        )
        angles.append(angle)

    return angles


def _generate_opening_line_template(fact: ExtractedFact) -> str:
    """Generate an opening line template from a fact."""
    templates = {
        FactCategory.LINKEDIN_POST: [
            "Loved your post about {{ topic }}",
            "Your take on {{ topic }} resonated with me",
            "Really enjoyed your recent thoughts on {{ topic }}",
        ],
        FactCategory.ARTICLE: [
            "Your article on {{ topic }} was insightful",
            "Read your piece in {{ publication }} - compelling perspective",
            "Your writing on {{ topic }} caught my attention",
        ],
        FactCategory.PODCAST: [
            "Heard your interview on {{ podcast }} - great insights",
            "Your podcast appearance discussing {{ topic }} was excellent",
        ],
        FactCategory.TALK: [
            "Your talk on {{ topic }} was inspiring",
            "Caught your presentation about {{ topic }}",
        ],
        FactCategory.CAREER_MOVE: [
            "Congrats on your role as {{ title }}",
            "Noticed you're {{ achievement }} - impressive",
        ],
        FactCategory.ACHIEVEMENT: [
            "Congratulations on {{ achievement }}",
            "Impressive work on {{ achievement }}",
        ],
    }

    category_templates = templates.get(fact.source_type, ["{{ fact }}"])

    # Use first template and fill in with fact text
    template = category_templates[0]

    # Simple substitution (can be enhanced with actual values)
    result = template.replace("{{ topic }}", fact.text[:50] if len(fact.text) > 50 else fact.text)
    result = result.replace("{{ fact }}", fact.text[:50] if len(fact.text) > 50 else fact.text)
    result = result.replace("{{ publication }}", fact.context or "publication")
    result = result.replace("{{ podcast }}", fact.context or "the podcast")
    result = result.replace(
        "{{ achievement }}", fact.text[:50] if len(fact.text) > 50 else fact.text
    )
    result = result.replace("{{ title }}", fact.text[:30] if len(fact.text) > 30 else fact.text)

    return result


def create_fallback_angle(
    lead_id: str,
    company_research: dict[str, Any] | None,
) -> RankedAngle | None:
    """
    Create a fallback angle from company research.

    Used when lead-specific research is sparse.

    Args:
        lead_id: UUID of the lead.
        company_research: Company research data.

    Returns:
        Fallback angle or None.
    """
    if not company_research:
        return None

    personalization_angle = company_research.get("personalization_angle")
    if not personalization_angle:
        # Try to use company headline
        headline = company_research.get("headline", "")
        if headline:
            personalization_angle = f"Regarding {headline}"
        else:
            return None

    from uuid import UUID

    return RankedAngle(
        lead_id=UUID(lead_id) if isinstance(lead_id, str) else lead_id,
        fact_id=None,
        rank_position=99,  # Low priority
        angle_type="company_fallback",
        angle_text=personalization_angle,
        recency_score=0.5,
        specificity_score=0.5,
        business_relevance_score=0.6,
        emotional_hook_score=0.4,
        total_score=0.5,
        is_fallback=True,
    )
