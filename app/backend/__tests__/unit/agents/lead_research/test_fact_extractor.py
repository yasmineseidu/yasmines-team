"""Unit tests for Lead Research Agent fact extractor.

Tests fact extraction and scoring:
- extract_facts_from_research
- score_fact
- rank_angles_from_facts
- create_fallback_angle
"""

from datetime import date
from uuid import uuid4

from src.agents.lead_research.fact_extractor import (
    MIN_SCORE_THRESHOLD,
    SCORING_WEIGHTS,
    create_fallback_angle,
    extract_facts_from_research,
    rank_angles_from_facts,
    score_fact,
)
from src.agents.lead_research.schemas import ExtractedFact, FactCategory


class TestExtractFactsFromResearch:
    """Tests for extract_facts_from_research function."""

    def test_extracts_facts_from_linkedin_posts(self) -> None:
        """Test extraction from LinkedIn posts."""
        research_data = {
            "linkedin_posts": [
                {
                    "content": "Excited to announce our new AI product launch!",
                    "url": "https://linkedin.com/posts/123",
                    "post_date": date.today(),
                    "topics": ["AI", "product launch"],
                }
            ],
            "articles": [],
            "podcasts": [],
            "profile": {},
        }

        facts = extract_facts_from_research(research_data, str(uuid4()))

        assert len(facts) >= 1
        linkedin_facts = [f for f in facts if f.source_type == FactCategory.LINKEDIN_POST]
        assert len(linkedin_facts) >= 1

    def test_extracts_facts_from_articles(self) -> None:
        """Test extraction from articles."""
        research_data = {
            "linkedin_posts": [],
            "articles": [
                {
                    "title": "The Future of AI in Enterprise",
                    "url": "https://techcrunch.com/article/123",
                    "content": "In this article, I explore...",
                    "publication": "TechCrunch",
                }
            ],
            "podcasts": [],
            "profile": {},
        }

        facts = extract_facts_from_research(research_data, str(uuid4()))

        article_facts = [f for f in facts if f.source_type == FactCategory.ARTICLE]
        assert len(article_facts) >= 1
        assert "TechCrunch" in article_facts[0].text

    def test_extracts_facts_from_podcasts(self) -> None:
        """Test extraction from podcasts."""
        research_data = {
            "linkedin_posts": [],
            "articles": [],
            "podcasts": [
                {
                    "title": "Tech Leaders Podcast - Episode with John",
                    "url": "https://podcasts.example.com/123",
                    "content": "Discussion about leadership...",
                    "podcast_name": "Tech Leaders Podcast",
                }
            ],
            "profile": {},
        }

        facts = extract_facts_from_research(research_data, str(uuid4()))

        podcast_facts = [f for f in facts if f.source_type == FactCategory.PODCAST]
        assert len(podcast_facts) >= 1

    def test_extracts_facts_from_profile(self) -> None:
        """Test extraction from profile."""
        research_data = {
            "linkedin_posts": [],
            "articles": [],
            "podcasts": [],
            "profile": {
                "headline": "CEO at TechCorp | Building the future of AI",
                "about": "Passionate about technology and innovation...",
                "url": "https://linkedin.com/in/john",
            },
        }

        facts = extract_facts_from_research(research_data, str(uuid4()))

        profile_facts = [f for f in facts if f.source_type == FactCategory.CAREER_MOVE]
        assert len(profile_facts) >= 1

    def test_filters_facts_below_threshold(self) -> None:
        """Test that facts below threshold are filtered."""
        # Create research data that would produce low-scoring facts
        research_data = {
            "linkedin_posts": [
                {
                    "content": "x",  # Very short content
                    "url": "https://linkedin.com/posts/123",
                }
            ],
            "articles": [],
            "podcasts": [],
            "profile": {},
        }

        facts = extract_facts_from_research(research_data, str(uuid4()))

        # All returned facts should be above threshold
        for fact in facts:
            assert fact.total_score >= MIN_SCORE_THRESHOLD


class TestScoreFact:
    """Tests for score_fact function."""

    def test_scores_recent_fact_higher(self) -> None:
        """Test that recent facts score higher on recency."""
        recent_fact = ExtractedFact(
            text="Launched new product feature",
            source_type=FactCategory.LINKEDIN_POST,
            recency_days=7,
        )
        old_fact = ExtractedFact(
            text="Launched new product feature",
            source_type=FactCategory.LINKEDIN_POST,
            recency_days=180,
        )

        scored_recent = score_fact(recent_fact)
        scored_old = score_fact(old_fact)

        assert scored_recent.recency_score > scored_old.recency_score

    def test_scores_specific_fact_higher(self) -> None:
        """Test that specific facts score higher."""
        specific_fact = ExtractedFact(
            text="Increased revenue by 150% in Q4 2024",
            source_type=FactCategory.ARTICLE,
        )
        vague_fact = ExtractedFact(
            text="Did some good work",
            source_type=FactCategory.ARTICLE,
        )

        scored_specific = score_fact(specific_fact)
        scored_vague = score_fact(vague_fact)

        assert scored_specific.specificity_score > scored_vague.specificity_score

    def test_scores_business_content_higher(self) -> None:
        """Test that business-related content scores higher."""
        business_fact = ExtractedFact(
            text="Led team to achieve $10M revenue growth and expanded customer base",
            source_type=FactCategory.ARTICLE,
        )
        personal_fact = ExtractedFact(
            text="Enjoyed a nice vacation with family",
            source_type=FactCategory.LINKEDIN_POST,
        )

        scored_business = score_fact(business_fact)
        scored_personal = score_fact(personal_fact)

        assert scored_business.business_relevance_score > scored_personal.business_relevance_score

    def test_scores_emotional_content_higher(self) -> None:
        """Test that emotional hook content scores higher."""
        emotional_fact = ExtractedFact(
            text="So proud and excited to announce we've won the Innovation Award!",
            source_type=FactCategory.ACHIEVEMENT,
        )
        neutral_fact = ExtractedFact(
            text="Company received award",
            source_type=FactCategory.ACHIEVEMENT,
        )

        scored_emotional = score_fact(emotional_fact)
        scored_neutral = score_fact(neutral_fact)

        assert scored_emotional.emotional_hook_score > scored_neutral.emotional_hook_score

    def test_calculates_total_score_with_weights(self) -> None:
        """Test that total score uses correct weights."""
        fact = ExtractedFact(
            text="Launched innovative product achieving growth",
            source_type=FactCategory.LINKEDIN_POST,
            recency_days=30,
        )

        scored = score_fact(fact)

        # Verify total is weighted sum
        expected_total = (
            scored.recency_score * SCORING_WEIGHTS["recency"]
            + scored.specificity_score * SCORING_WEIGHTS["specificity"]
            + scored.business_relevance_score * SCORING_WEIGHTS["business_relevance"]
            + scored.emotional_hook_score * SCORING_WEIGHTS["emotional_hook"]
        )

        assert abs(scored.total_score - expected_total) < 0.01

    def test_handles_none_recency_days(self) -> None:
        """Test handling of None recency_days."""
        fact = ExtractedFact(
            text="Some content without date",
            source_type=FactCategory.ARTICLE,
            recency_days=None,
        )

        scored = score_fact(fact)

        # Should get middle score for unknown recency
        assert scored.recency_score == 0.5


class TestRankAnglesFromFacts:
    """Tests for rank_angles_from_facts function."""

    def test_ranks_by_total_score_descending(self) -> None:
        """Test that angles are ranked by score descending."""
        lead_id = str(uuid4())

        facts = [
            score_fact(
                ExtractedFact(
                    text="Low score fact",
                    source_type=FactCategory.LINKEDIN_POST,
                    recency_days=365,
                )
            ),
            score_fact(
                ExtractedFact(
                    text="High score fact with specific $1M achievement launched recently",
                    source_type=FactCategory.ACHIEVEMENT,
                    recency_days=7,
                )
            ),
        ]

        angles = rank_angles_from_facts(facts, lead_id)

        assert len(angles) >= 1
        # First angle should have highest score
        if len(angles) > 1:
            assert angles[0].total_score >= angles[1].total_score

    def test_limits_to_max_angles(self) -> None:
        """Test that result is limited to max_angles."""
        lead_id = str(uuid4())

        facts = [
            score_fact(
                ExtractedFact(
                    text=f"Fact number {i} with some content",
                    source_type=FactCategory.LINKEDIN_POST,
                    recency_days=30,
                )
            )
            for i in range(10)
        ]

        angles = rank_angles_from_facts(facts, lead_id, max_angles=3)

        assert len(angles) <= 3

    def test_generates_opening_line_templates(self) -> None:
        """Test that angles have opening line templates."""
        lead_id = str(uuid4())

        facts = [
            score_fact(
                ExtractedFact(
                    text="Excited about our new AI product",
                    source_type=FactCategory.LINKEDIN_POST,
                    recency_days=14,
                )
            )
        ]

        angles = rank_angles_from_facts(facts, lead_id)

        assert len(angles) >= 1
        assert angles[0].angle_text  # Has opening line
        assert len(angles[0].angle_text) > 10

    def test_assigns_rank_positions(self) -> None:
        """Test that rank positions are assigned correctly."""
        lead_id = str(uuid4())

        facts = [
            score_fact(
                ExtractedFact(
                    text=f"Fact {i}",
                    source_type=FactCategory.ARTICLE,
                    recency_days=30,
                )
            )
            for i in range(3)
        ]

        angles = rank_angles_from_facts(facts, lead_id)

        for i, angle in enumerate(angles):
            assert angle.rank_position == i + 1


class TestCreateFallbackAngle:
    """Tests for create_fallback_angle function."""

    def test_creates_fallback_from_company_research(self) -> None:
        """Test creation of fallback angle."""
        lead_id = str(uuid4())
        company_research = {
            "personalization_angle": "Noticed your company's recent growth in AI",
            "headline": "Leading AI Solutions Provider",
        }

        fallback = create_fallback_angle(lead_id, company_research)

        assert fallback is not None
        assert fallback.is_fallback is True
        assert fallback.rank_position == 99
        assert "AI" in fallback.angle_text

    def test_uses_headline_when_no_angle(self) -> None:
        """Test using headline as fallback."""
        lead_id = str(uuid4())
        company_research = {
            "headline": "Innovative Tech Company",
        }

        fallback = create_fallback_angle(lead_id, company_research)

        assert fallback is not None
        assert "Innovative Tech Company" in fallback.angle_text

    def test_returns_none_when_no_data(self) -> None:
        """Test returns None when no usable data."""
        lead_id = str(uuid4())

        fallback = create_fallback_angle(lead_id, None)
        assert fallback is None

        fallback = create_fallback_angle(lead_id, {})
        assert fallback is None
