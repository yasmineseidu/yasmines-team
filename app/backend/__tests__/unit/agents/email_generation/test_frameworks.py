"""Unit tests for email frameworks."""

import pytest

from src.agents.email_generation.frameworks import (
    AIDA_TEMPLATE,
    AVOID_PATTERNS,
    BAB_TEMPLATE,
    EXCESSIVE_FLATTERY_PATTERNS,
    FRAMEWORK_TEMPLATES,
    PAS_TEMPLATE,
    QUESTION_TEMPLATE,
    SOFT_CTAS,
    build_generation_prompt,
    get_framework_template,
    select_framework_for_tier,
)
from src.agents.email_generation.schemas import EmailFramework


class TestFrameworkTemplates:
    """Tests for framework templates."""

    def test_pas_template_exists(self) -> None:
        """Test PAS template is defined."""
        assert PAS_TEMPLATE.name == "Pain-Agitate-Solution"
        assert PAS_TEMPLATE.framework == EmailFramework.PAS
        assert len(PAS_TEMPLATE.structure) == 5
        assert "personalization_hook" in PAS_TEMPLATE.structure

    def test_bab_template_exists(self) -> None:
        """Test BAB template is defined."""
        assert BAB_TEMPLATE.name == "Before-After-Bridge"
        assert BAB_TEMPLATE.framework == EmailFramework.BAB
        assert "before" in BAB_TEMPLATE.structure
        assert "after" in BAB_TEMPLATE.structure
        assert "bridge" in BAB_TEMPLATE.structure

    def test_aida_template_exists(self) -> None:
        """Test AIDA template is defined."""
        assert AIDA_TEMPLATE.name == "Attention-Interest-Desire-Action"
        assert AIDA_TEMPLATE.framework == EmailFramework.AIDA
        assert "attention" in AIDA_TEMPLATE.structure
        assert "interest" in AIDA_TEMPLATE.structure

    def test_question_template_exists(self) -> None:
        """Test Question template is defined."""
        assert QUESTION_TEMPLATE.name == "Question-Based"
        assert QUESTION_TEMPLATE.framework == EmailFramework.QUESTION
        assert "personalized_question" in QUESTION_TEMPLATE.structure

    def test_all_frameworks_in_lookup(self) -> None:
        """Test all frameworks are in lookup dictionary."""
        assert EmailFramework.PAS in FRAMEWORK_TEMPLATES
        assert EmailFramework.BAB in FRAMEWORK_TEMPLATES
        assert EmailFramework.AIDA in FRAMEWORK_TEMPLATES
        assert EmailFramework.QUESTION in FRAMEWORK_TEMPLATES


class TestGetFrameworkTemplate:
    """Tests for get_framework_template function."""

    def test_get_pas_template(self) -> None:
        """Test getting PAS template."""
        template = get_framework_template(EmailFramework.PAS)
        assert template == PAS_TEMPLATE

    def test_get_bab_template(self) -> None:
        """Test getting BAB template."""
        template = get_framework_template(EmailFramework.BAB)
        assert template == BAB_TEMPLATE

    def test_get_aida_template(self) -> None:
        """Test getting AIDA template."""
        template = get_framework_template(EmailFramework.AIDA)
        assert template == AIDA_TEMPLATE

    def test_get_question_template(self) -> None:
        """Test getting Question template."""
        template = get_framework_template(EmailFramework.QUESTION)
        assert template == QUESTION_TEMPLATE


class TestSelectFrameworkForTier:
    """Tests for select_framework_for_tier function."""

    def test_tier_a_gets_pas_or_bab(self) -> None:
        """Test Tier A gets PAS or BAB."""
        framework_0 = select_framework_for_tier("A", 0)
        framework_1 = select_framework_for_tier("A", 1)
        assert framework_0 == EmailFramework.PAS
        assert framework_1 == EmailFramework.BAB

    def test_tier_b_gets_bab_or_aida(self) -> None:
        """Test Tier B gets BAB or AIDA."""
        framework_0 = select_framework_for_tier("B", 0)
        framework_1 = select_framework_for_tier("B", 1)
        assert framework_0 == EmailFramework.BAB
        assert framework_1 == EmailFramework.AIDA

    def test_tier_c_gets_aida_or_question(self) -> None:
        """Test Tier C gets AIDA or Question."""
        framework_0 = select_framework_for_tier("C", 0)
        framework_1 = select_framework_for_tier("C", 1)
        assert framework_0 == EmailFramework.AIDA
        assert framework_1 == EmailFramework.QUESTION

    def test_unknown_tier_defaults_to_c(self) -> None:
        """Test unknown tier defaults to C patterns."""
        framework = select_framework_for_tier("Z", 0)
        assert framework == EmailFramework.AIDA


class TestAvoidPatterns:
    """Tests for avoid patterns."""

    def test_avoid_patterns_populated(self) -> None:
        """Test avoid patterns list is populated."""
        assert len(AVOID_PATTERNS) > 0

    def test_common_bad_patterns_included(self) -> None:
        """Test common bad patterns are included."""
        assert any("hope this email finds you" in p.lower() for p in AVOID_PATTERNS)
        assert any("pick your brain" in p.lower() for p in AVOID_PATTERNS)

    def test_flattery_patterns_populated(self) -> None:
        """Test flattery patterns list is populated."""
        assert len(EXCESSIVE_FLATTERY_PATTERNS) > 0


class TestSoftCTAs:
    """Tests for soft CTA examples."""

    def test_soft_ctas_populated(self) -> None:
        """Test soft CTAs list is populated."""
        assert len(SOFT_CTAS) > 0

    def test_soft_ctas_are_questions(self) -> None:
        """Test soft CTAs end with question marks."""
        for cta in SOFT_CTAS:
            assert cta.endswith("?"), f"CTA should be a question: {cta}"


class TestBuildGenerationPrompt:
    """Tests for build_generation_prompt function."""

    @pytest.fixture
    def lead_context(self) -> dict:
        """Create sample lead context."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "title": "VP of Marketing",
            "company_name": "Acme Corp",
            "lead_tier": "A",
        }

    @pytest.fixture
    def persona_context(self) -> dict:
        """Create sample persona context."""
        return {
            "challenges": ["lead generation", "attribution"],
            "goals": ["increase pipeline", "prove ROI"],
            "messaging_tone": "professional",
        }

    @pytest.fixture
    def niche_context(self) -> dict:
        """Create sample niche context."""
        return {
            "pain_points": ["long sales cycles"],
            "value_propositions": ["faster deals"],
        }

    def test_prompt_contains_lead_info(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes lead information."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "John" in prompt
        assert "Doe" in prompt
        assert "VP of Marketing" in prompt
        assert "Acme Corp" in prompt

    def test_prompt_contains_persona_info(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes persona information."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "lead generation" in prompt or "Pain Points" in prompt
        assert "increase pipeline" in prompt or "Goals" in prompt

    def test_prompt_contains_framework_info(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes framework information."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "Pain-Agitate-Solution" in prompt

    def test_prompt_contains_output_format(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes output format."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "subject_line" in prompt
        assert "opening_line" in prompt
        assert "body" in prompt
        assert "cta" in prompt
        assert "JSON" in prompt

    def test_prompt_includes_research_when_provided(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes research data when provided."""
        lead_research = {"headline": "Building the future", "key_interests": ["AI", "growth"]}
        company_research = {
            "summary": "Tech company",
            "personalization_angle": "Expanding globally",
        }

        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
            lead_research=lead_research,
            company_research=company_research,
        )
        assert "Building the future" in prompt
        assert "Expanding globally" in prompt

    def test_prompt_includes_proven_lines(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes proven lines when provided."""
        proven_lines = ["Great opening line 1", "Great opening line 2"]

        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
            proven_lines=proven_lines,
        )
        assert "Great opening line 1" in prompt

    def test_prompt_respects_max_words(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes max words constraint."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
            max_words=100,
        )
        assert "100 words" in prompt

    def test_prompt_includes_avoid_patterns(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test prompt includes patterns to avoid."""
        prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "AVOID" in prompt
        # Should include at least one avoid pattern
        assert any(p in prompt for p in AVOID_PATTERNS[:3])

    def test_different_frameworks_produce_different_prompts(
        self,
        lead_context: dict,
        persona_context: dict,
        niche_context: dict,
    ) -> None:
        """Test different frameworks produce different prompts."""
        pas_prompt = build_generation_prompt(
            framework=EmailFramework.PAS,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        bab_prompt = build_generation_prompt(
            framework=EmailFramework.BAB,
            lead_context=lead_context,
            persona_context=persona_context,
            niche_context=niche_context,
        )
        assert "Pain-Agitate-Solution" in pas_prompt
        assert "Before-After-Bridge" in bab_prompt
        assert "Pain-Agitate-Solution" not in bab_prompt
