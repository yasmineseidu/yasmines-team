"""Unit tests for email generation schemas."""

import pytest

from src.agents.email_generation.schemas import (
    EmailFramework,
    EmailGenerationResult,
    GeneratedEmail,
    LeadContext,
    LeadTier,
    NicheContext,
    PersonaContext,
    PersonalizationLevel,
    QualityScore,
    TierConfig,
)


class TestEmailFramework:
    """Tests for EmailFramework enum."""

    def test_framework_values(self) -> None:
        """Test all framework values are defined."""
        assert EmailFramework.PAS.value == "pas"
        assert EmailFramework.BAB.value == "bab"
        assert EmailFramework.AIDA.value == "aida"
        assert EmailFramework.QUESTION.value == "question"

    def test_framework_from_string(self) -> None:
        """Test creating framework from string."""
        assert EmailFramework("pas") == EmailFramework.PAS
        assert EmailFramework("bab") == EmailFramework.BAB


class TestLeadTier:
    """Tests for LeadTier enum."""

    def test_tier_values(self) -> None:
        """Test all tier values are defined."""
        assert LeadTier.A.value == "A"
        assert LeadTier.B.value == "B"
        assert LeadTier.C.value == "C"


class TestPersonalizationLevel:
    """Tests for PersonalizationLevel enum."""

    def test_level_values(self) -> None:
        """Test all personalization levels."""
        assert PersonalizationLevel.HYPER_PERSONALIZED.value == "hyper_personalized"
        assert PersonalizationLevel.PERSONALIZED.value == "personalized"
        assert PersonalizationLevel.SEMI_PERSONALIZED.value == "semi_personalized"


class TestQualityScore:
    """Tests for QualityScore dataclass."""

    def test_default_values(self) -> None:
        """Test default score values are zero."""
        score = QualityScore()
        assert score.personalization == 0.0
        assert score.clarity == 0.0
        assert score.length == 0.0
        assert score.cta_quality == 0.0
        assert score.tone == 0.0

    def test_total_score_calculation(self) -> None:
        """Test weighted total score calculation."""
        score = QualityScore(
            personalization=10.0,  # 30% weight
            clarity=10.0,  # 25% weight
            length=10.0,  # 15% weight
            cta_quality=10.0,  # 15% weight
            tone=10.0,  # 15% weight
        )
        # All 10s should give 100
        assert score.total_score == 100.0

    def test_total_score_partial(self) -> None:
        """Test partial score calculation."""
        score = QualityScore(
            personalization=5.0,  # 5 * 0.30 * 10 = 15
            clarity=5.0,  # 5 * 0.25 * 10 = 12.5
            length=5.0,  # 5 * 0.15 * 10 = 7.5
            cta_quality=5.0,  # 5 * 0.15 * 10 = 7.5
            tone=5.0,  # 5 * 0.15 * 10 = 7.5
        )
        assert score.total_score == 50.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        score = QualityScore(
            personalization=8.0,
            clarity=7.0,
            length=6.0,
            cta_quality=9.0,
            tone=8.0,
        )
        result = score.to_dict()
        assert result["personalization"] == 8.0
        assert result["clarity"] == 7.0
        assert result["length"] == 6.0
        assert result["cta_quality"] == 9.0
        assert result["tone"] == 8.0
        assert "total_score" in result


class TestGeneratedEmail:
    """Tests for GeneratedEmail dataclass."""

    @pytest.fixture
    def sample_email(self) -> GeneratedEmail:
        """Create a sample generated email."""
        return GeneratedEmail(
            lead_id="lead-123",
            campaign_id="campaign-456",
            subject_line="Quick question about marketing",
            opening_line="Noticed your recent post about AI in marketing",
            body="I wanted to reach out because...",
            cta="Would you be open to a quick chat?",
            full_email="Noticed your recent post... Would you be open to a quick chat?",
            framework=EmailFramework.PAS,
            personalization_level=PersonalizationLevel.PERSONALIZED,
            quality_score=75.0,
        )

    def test_email_creation(self, sample_email: GeneratedEmail) -> None:
        """Test email is created with correct values."""
        assert sample_email.lead_id == "lead-123"
        assert sample_email.campaign_id == "campaign-456"
        assert sample_email.framework == EmailFramework.PAS

    def test_to_dict(self, sample_email: GeneratedEmail) -> None:
        """Test conversion to dictionary."""
        result = sample_email.to_dict()
        assert result["lead_id"] == "lead-123"
        assert result["campaign_id"] == "campaign-456"
        assert result["framework_used"] == "pas"
        assert result["personalization_level"] == "personalized"
        assert result["quality_score"] == 75


class TestLeadContext:
    """Tests for LeadContext dataclass."""

    def test_lead_context_creation(self) -> None:
        """Test creating lead context."""
        ctx = LeadContext(
            lead_id="lead-123",
            first_name="John",
            last_name="Doe",
            title="VP of Marketing",
            company_name="Acme Corp",
            company_domain="acme.com",
            lead_tier=LeadTier.A,
            lead_score=85,
        )
        assert ctx.first_name == "John"
        assert ctx.lead_tier == LeadTier.A
        assert ctx.lead_research is None  # Optional field

    def test_lead_context_with_research(self) -> None:
        """Test lead context with research data."""
        ctx = LeadContext(
            lead_id="lead-123",
            first_name="Jane",
            last_name="Smith",
            title="CEO",
            company_name="Tech Inc",
            company_domain="tech.com",
            lead_tier=LeadTier.B,
            lead_score=70,
            lead_research={"headline": "Building the future"},
            company_research={"summary": "Tech company"},
        )
        assert ctx.lead_research is not None
        assert ctx.company_research is not None


class TestPersonaContext:
    """Tests for PersonaContext dataclass."""

    def test_persona_context_creation(self) -> None:
        """Test creating persona context."""
        ctx = PersonaContext(
            name="Marketing Director",
            challenges=["lead generation", "attribution"],
            goals=["increase pipeline", "prove ROI"],
            motivations=["career growth", "team success"],
            objections=["budget constraints", "time"],
            messaging_tone="professional",
            value_propositions=["increase efficiency", "reduce costs"],
        )
        assert ctx.name == "Marketing Director"
        assert len(ctx.challenges) == 2
        assert ctx.messaging_tone == "professional"


class TestNicheContext:
    """Tests for NicheContext dataclass."""

    def test_niche_context_creation(self) -> None:
        """Test creating niche context."""
        ctx = NicheContext(
            name="B2B SaaS",
            industry=["Technology", "Software"],
            pain_points=["long sales cycles", "churn"],
            value_propositions=["faster deals", "better retention"],
        )
        assert ctx.name == "B2B SaaS"
        assert len(ctx.industry) == 2


class TestTierConfig:
    """Tests for TierConfig dataclass."""

    def test_tier_a_config(self) -> None:
        """Test Tier A configuration."""
        config = TierConfig.tier_a()
        assert config.tier == LeadTier.A
        assert EmailFramework.PAS in config.frameworks
        assert EmailFramework.BAB in config.frameworks
        assert config.personalization_level == PersonalizationLevel.HYPER_PERSONALIZED
        assert config.max_words == 150
        assert config.quality_threshold == 70
        assert config.max_regeneration_attempts == 3

    def test_tier_b_config(self) -> None:
        """Test Tier B configuration."""
        config = TierConfig.tier_b()
        assert config.tier == LeadTier.B
        assert config.quality_threshold == 60
        assert config.max_regeneration_attempts == 2

    def test_tier_c_config(self) -> None:
        """Test Tier C configuration."""
        config = TierConfig.tier_c()
        assert config.tier == LeadTier.C
        assert config.quality_threshold == 50
        assert config.max_regeneration_attempts == 1


class TestEmailGenerationResult:
    """Tests for EmailGenerationResult dataclass."""

    def test_result_creation(self) -> None:
        """Test result creation."""
        result = EmailGenerationResult(
            success=True,
            campaign_id="campaign-123",
            total_generated=100,
            tier_a_generated=20,
            tier_b_generated=30,
            tier_c_generated=50,
            avg_quality_score=72.5,
        )
        assert result.success is True
        assert result.total_generated == 100

    def test_result_to_dict(self) -> None:
        """Test result conversion to dictionary."""
        result = EmailGenerationResult(
            success=True,
            campaign_id="campaign-123",
            total_generated=100,
            tier_a_generated=20,
            tier_b_generated=30,
            tier_c_generated=50,
            avg_quality_score=72.5,
            quality_distribution={"excellent_85plus": 15},
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["total_generated"] == 100
        assert data["tier_breakdown"]["tier_a"] == 20
        assert data["quality_distribution"]["excellent_85plus"] == 15

    def test_result_with_error(self) -> None:
        """Test result with error."""
        result = EmailGenerationResult(
            success=False,
            campaign_id="campaign-123",
            error="API rate limit exceeded",
        )
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.total_generated == 0
