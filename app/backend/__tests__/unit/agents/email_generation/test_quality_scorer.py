"""Unit tests for email quality scorer."""

import pytest

from src.agents.email_generation.quality_scorer import (
    EmailQualityScorer,
    get_quality_scorer,
)
from src.agents.email_generation.schemas import (
    EmailFramework,
    GeneratedEmail,
    LeadContext,
    LeadTier,
    PersonalizationLevel,
    QualityScore,
)


@pytest.fixture
def scorer() -> EmailQualityScorer:
    """Create a quality scorer instance."""
    return EmailQualityScorer()


@pytest.fixture
def sample_lead_context() -> LeadContext:
    """Create sample lead context."""
    return LeadContext(
        lead_id="lead-123",
        first_name="John",
        last_name="Doe",
        title="VP of Marketing",
        company_name="Acme Corp",
        company_domain="acme.com",
        lead_tier=LeadTier.A,
        lead_score=85,
        lead_research={"headline": "Building the future of marketing"},
        company_research={"personalization_angle": "Recently expanded to Europe"},
    )


def create_email(
    subject: str = "Quick question",
    opening: str = "Hi John",
    body: str = "I noticed your company Acme Corp is expanding.",
    cta: str = "Would you be open to a quick chat?",
    full_email: str = "",
) -> GeneratedEmail:
    """Helper to create test emails."""
    if not full_email:
        full_email = f"{opening}\n\n{body}\n\n{cta}"
    return GeneratedEmail(
        lead_id="lead-123",
        campaign_id="campaign-456",
        subject_line=subject,
        opening_line=opening,
        body=body,
        cta=cta,
        full_email=full_email,
        framework=EmailFramework.PAS,
        personalization_level=PersonalizationLevel.PERSONALIZED,
    )


class TestEmailQualityScorerInitialization:
    """Tests for scorer initialization."""

    def test_scorer_initializes(self, scorer: EmailQualityScorer) -> None:
        """Test scorer initializes with patterns."""
        assert len(scorer.avoid_patterns) > 0
        assert len(scorer.flattery_patterns) > 0
        assert len(scorer.soft_cta_patterns) > 0


class TestPersonalizationScoring:
    """Tests for personalization scoring."""

    def test_high_personalization_with_research(
        self,
        scorer: EmailQualityScorer,
        sample_lead_context: LeadContext,
    ) -> None:
        """Test high score when using research data."""
        email = create_email(
            opening="Building the future of marketing - I saw your recent work on this",
            body="At Acme Corp, you're doing great work as VP of Marketing.",
        )
        score = scorer._score_personalization(email, sample_lead_context)
        assert score >= 8.0

    def test_medium_personalization_company_mention(
        self,
        scorer: EmailQualityScorer,
        sample_lead_context: LeadContext,
    ) -> None:
        """Test medium score for company mention."""
        email = create_email(
            opening="Hi John",
            body="I noticed Acme Corp is growing. As someone in marketing, you might find this interesting.",
        )
        score = scorer._score_personalization(email, sample_lead_context)
        assert 5.0 <= score <= 9.0

    def test_low_personalization_generic(
        self,
        scorer: EmailQualityScorer,
        sample_lead_context: LeadContext,
    ) -> None:
        """Test low score for generic email."""
        email = create_email(
            opening="Hello",
            body="I wanted to reach out about our services that help companies grow.",
        )
        score = scorer._score_personalization(email, sample_lead_context)
        assert score <= 5.0


class TestClarityScoring:
    """Tests for clarity scoring."""

    def test_high_clarity_short_sentences(self, scorer: EmailQualityScorer) -> None:
        """Test high score for short, clear sentences."""
        email = create_email(
            body="Short sentences are clear. They're easy to read. People understand them quickly."
        )
        score = scorer._score_clarity(email)
        assert score >= 7.0

    def test_low_clarity_long_sentences(self, scorer: EmailQualityScorer) -> None:
        """Test lower score for long, complex sentences."""
        email = create_email(
            body="This is an extremely long and convoluted sentence that goes on and on, "
            "touching on multiple topics while failing to get to the point in a clear "
            "and concise manner, which makes it very difficult for the reader to understand "
            "what is actually being communicated here."
        )
        score = scorer._score_clarity(email)
        assert score <= 6.0

    def test_low_clarity_with_jargon(self, scorer: EmailQualityScorer) -> None:
        """Test lower score when using jargon."""
        email = create_email(
            body="Let's leverage synergy to move the needle. We should deep dive into this paradigm."
        )
        score = scorer._score_clarity(email)
        assert score <= 5.0


class TestLengthScoring:
    """Tests for length scoring."""

    def test_optimal_length_50_100_words(self, scorer: EmailQualityScorer) -> None:
        """Test perfect score for 50-100 word body."""
        # Create body with exactly 75 words
        words = ["word"] * 75
        email = create_email(body=" ".join(words))
        score = scorer._score_length(email)
        assert score == 10.0

    def test_acceptable_length_100_150_words(self, scorer: EmailQualityScorer) -> None:
        """Test good score for 100-150 word body."""
        words = ["word"] * 120
        email = create_email(body=" ".join(words))
        score = scorer._score_length(email)
        assert score == 7.0

    def test_too_short_under_50_words(self, scorer: EmailQualityScorer) -> None:
        """Test lower score for very short body."""
        email = create_email(body="Short email body here.")
        score = scorer._score_length(email)
        assert score == 4.0

    def test_too_long_over_150_words(self, scorer: EmailQualityScorer) -> None:
        """Test low score for long body."""
        words = ["word"] * 200
        email = create_email(body=" ".join(words))
        score = scorer._score_length(email)
        assert score == 3.0


class TestCTAScoring:
    """Tests for CTA scoring."""

    def test_soft_cta_high_score(self, scorer: EmailQualityScorer) -> None:
        """Test high score for soft CTA."""
        email = create_email(cta="Would you be open to a quick chat?")
        score = scorer._score_cta(email)
        assert score >= 7.0

    def test_question_cta_good_score(self, scorer: EmailQualityScorer) -> None:
        """Test good score for question-based CTA."""
        email = create_email(cta="Is this something you're exploring?")
        score = scorer._score_cta(email)
        assert score >= 7.0

    def test_pushy_cta_low_score(self, scorer: EmailQualityScorer) -> None:
        """Test low score for pushy CTA."""
        email = create_email(cta="Book a call now! Limited time offer!")
        score = scorer._score_cta(email)
        assert score <= 5.0


class TestToneScoring:
    """Tests for tone scoring."""

    def test_conversational_tone_high_score(self, scorer: EmailQualityScorer) -> None:
        """Test high score for conversational tone."""
        email = create_email(
            full_email="I was curious about your approach to marketing. "
            "It seems like you're doing interesting work. "
            "Wondering if you'd be open to connecting?"
        )
        score = scorer._score_tone(email)
        assert score >= 7.0

    def test_corporate_tone_low_score(self, scorer: EmailQualityScorer) -> None:
        """Test lower score for corporate/avoided patterns."""
        email = create_email(
            full_email="I hope this email finds you well. "
            "I'd love to pick your brain about your marketing strategy."
        )
        score = scorer._score_tone(email)
        assert score <= 6.0

    def test_too_casual_low_score(self, scorer: EmailQualityScorer) -> None:
        """Test low score for overly casual tone."""
        email = create_email(
            full_email="Hey! Yo, what's up? Gonna send you some info, "
            "wanna check it out? It's super cool!"
        )
        score = scorer._score_tone(email)
        assert score <= 5.0


class TestFullEmailScoring:
    """Tests for complete email scoring."""

    def test_score_email_returns_quality_score(
        self,
        scorer: EmailQualityScorer,
        sample_lead_context: LeadContext,
    ) -> None:
        """Test that scoring returns QualityScore object."""
        email = create_email()
        score = scorer.score_email(email, sample_lead_context)
        assert isinstance(score, QualityScore)
        assert 0 <= score.total_score <= 100

    def test_excellent_email_high_score(
        self,
        scorer: EmailQualityScorer,
        sample_lead_context: LeadContext,
    ) -> None:
        """Test excellent email gets high score."""
        # Create well-crafted email with 75 words
        body_words = ["Great"] * 70  # Will be ~70 words
        email = create_email(
            subject="About your work on marketing at Acme Corp",
            opening="Building the future of marketing - I noticed your recent focus on this",
            body=f"At Acme Corp, as VP of Marketing, you're likely facing challenges with lead generation. {' '.join(body_words[:50])}",
            cta="Would you be open to a quick chat?",
        )
        score = scorer.score_email(email, sample_lead_context)
        # Should score reasonably well
        assert score.total_score >= 50.0


class TestRegenerationDecision:
    """Tests for regeneration decision logic."""

    def test_should_regenerate_below_threshold(self, scorer: EmailQualityScorer) -> None:
        """Test regeneration is recommended below threshold."""
        score = QualityScore(
            personalization=5.0,
            clarity=5.0,
            length=5.0,
            cta_quality=5.0,
            tone=5.0,
        )
        # Score is 50, threshold is 70
        assert scorer.should_regenerate(score, threshold=70)

    def test_should_not_regenerate_above_threshold(self, scorer: EmailQualityScorer) -> None:
        """Test no regeneration when above threshold."""
        score = QualityScore(
            personalization=8.0,
            clarity=8.0,
            length=8.0,
            cta_quality=8.0,
            tone=8.0,
        )
        # Score is 80, threshold is 70
        assert not scorer.should_regenerate(score, threshold=70)


class TestImprovementSuggestions:
    """Tests for improvement suggestions."""

    def test_suggestions_for_low_personalization(self, scorer: EmailQualityScorer) -> None:
        """Test suggestions include personalization advice."""
        score = QualityScore(
            personalization=2.0,
            clarity=8.0,
            length=8.0,
            cta_quality=8.0,
            tone=8.0,
        )
        suggestions = scorer.get_improvement_suggestions(score)
        assert len(suggestions) > 0
        assert any("personalization" in s.lower() for s in suggestions)

    def test_suggestions_for_low_clarity(self, scorer: EmailQualityScorer) -> None:
        """Test suggestions include clarity advice."""
        score = QualityScore(
            personalization=8.0,
            clarity=2.0,
            length=8.0,
            cta_quality=8.0,
            tone=8.0,
        )
        suggestions = scorer.get_improvement_suggestions(score)
        assert any("clarity" in s.lower() or "simplify" in s.lower() for s in suggestions)

    def test_no_suggestions_for_good_score(self, scorer: EmailQualityScorer) -> None:
        """Test no suggestions for good scores."""
        score = QualityScore(
            personalization=8.0,
            clarity=8.0,
            length=8.0,
            cta_quality=8.0,
            tone=8.0,
        )
        suggestions = scorer.get_improvement_suggestions(score)
        assert len(suggestions) == 0


class TestScorerSingleton:
    """Tests for scorer singleton."""

    def test_get_quality_scorer_returns_instance(self) -> None:
        """Test singleton returns instance."""
        scorer = get_quality_scorer()
        assert isinstance(scorer, EmailQualityScorer)

    def test_get_quality_scorer_returns_same_instance(self) -> None:
        """Test singleton returns same instance."""
        scorer1 = get_quality_scorer()
        scorer2 = get_quality_scorer()
        assert scorer1 is scorer2
