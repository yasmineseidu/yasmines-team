"""Unit tests for Scoring Model."""

import pytest

from src.agents.lead_scoring.schemas import (
    IndustryFitScore,
    LeadScoreRecord,
    NicheContext,
    PersonaContext,
    ScoreBreakdown,
    ScoringContext,
)
from src.agents.lead_scoring.scoring_model import (
    ScoringModel,
    determine_tier,
    get_company_size_index,
    normalize_company_size,
)


class TestDetermineTier:
    """Tests for determine_tier function."""

    def test_tier_a(self) -> None:
        assert determine_tier(100) == "A"
        assert determine_tier(80) == "A"

    def test_tier_b(self) -> None:
        assert determine_tier(79) == "B"
        assert determine_tier(60) == "B"

    def test_tier_c(self) -> None:
        assert determine_tier(59) == "C"
        assert determine_tier(40) == "C"

    def test_tier_d(self) -> None:
        assert determine_tier(39) == "D"
        assert determine_tier(0) == "D"


class TestNormalizeCompanySize:
    """Tests for normalize_company_size function."""

    def test_standard_formats(self) -> None:
        assert normalize_company_size("201-500") == "201-500"
        assert normalize_company_size("1-10") == "1-10"

    def test_with_employees_suffix(self) -> None:
        assert normalize_company_size("201-500 employees") == "201-500"

    def test_aliases(self) -> None:
        assert normalize_company_size("small") == "1-10"
        assert normalize_company_size("medium") == "51-200"
        assert normalize_company_size("large") == "1001-5000"
        assert normalize_company_size("enterprise") == "5001-10000"

    def test_none(self) -> None:
        assert normalize_company_size(None) is None

    def test_case_insensitive(self) -> None:
        assert normalize_company_size("SMALL") == "1-10"


class TestGetCompanySizeIndex:
    """Tests for get_company_size_index function."""

    def test_known_sizes(self) -> None:
        assert get_company_size_index("1-10") == 0
        assert get_company_size_index("201-500") == 3
        assert get_company_size_index("10001+") == 7

    def test_unknown_size(self) -> None:
        assert get_company_size_index(None) == -1
        assert get_company_size_index("unknown") == -1


class TestScoringContext:
    """Tests for ScoringContext class."""

    @pytest.fixture
    def context(self) -> ScoringContext:
        return ScoringContext(
            niche=NicheContext(
                id="niche-1",
                name="SaaS Marketing",
                industries=["SaaS", "Software"],
                company_sizes=["201-500", "501-1000"],
                job_titles=["VP Marketing", "CMO"],
            ),
            personas=[
                PersonaContext(
                    id="persona-1",
                    name="Marketing Leader",
                    job_titles=["VP Marketing", "Marketing Director"],
                    seniority_levels=["vp", "director"],
                    company_sizes=["201-500", "501-1000"],
                ),
                PersonaContext(
                    id="persona-2",
                    name="Growth Leader",
                    job_titles=["Head of Growth", "VP Growth"],
                    seniority_levels=["director", "vp"],
                    company_sizes=["51-200", "201-500"],
                ),
            ],
            industry_fit_scores=[
                IndustryFitScore(industry="SaaS", fit_score=95),
                IndustryFitScore(industry="Software", fit_score=85),
                IndustryFitScore(industry="Consulting", fit_score=60),
            ],
        )

    def test_get_all_target_job_titles(self, context: ScoringContext) -> None:
        titles = context.get_all_target_job_titles()
        assert "VP Marketing" in titles
        assert "Marketing Director" in titles
        assert "Head of Growth" in titles

    def test_get_all_target_seniorities(self, context: ScoringContext) -> None:
        seniorities = context.get_all_target_seniorities()
        assert "vp" in seniorities
        assert "director" in seniorities

    def test_get_all_target_company_sizes(self, context: ScoringContext) -> None:
        sizes = context.get_all_target_company_sizes()
        assert "201-500" in sizes
        assert "501-1000" in sizes

    def test_get_industry_fit_score_exact(self, context: ScoringContext) -> None:
        assert context.get_industry_fit_score("SaaS") == 95

    def test_get_industry_fit_score_case_insensitive(self, context: ScoringContext) -> None:
        assert context.get_industry_fit_score("saas") == 95

    def test_get_industry_fit_score_partial(self, context: ScoringContext) -> None:
        # Partial match
        score = context.get_industry_fit_score("SaaS Solutions")
        assert score in [50, 95]  # May match SaaS or default

    def test_get_industry_fit_score_unknown(self, context: ScoringContext) -> None:
        assert context.get_industry_fit_score("Healthcare") == 50  # Default

    def test_get_industry_fit_score_missing(self, context: ScoringContext) -> None:
        assert context.get_industry_fit_score("") == 50


class TestScoringModel:
    """Tests for ScoringModel class."""

    @pytest.fixture
    def context(self) -> ScoringContext:
        return ScoringContext(
            niche=NicheContext(
                id="niche-1",
                name="SaaS Marketing",
                industries=["SaaS", "Software"],
                company_sizes=["201-500", "501-1000"],
                job_titles=["VP Marketing", "CMO"],
            ),
            personas=[
                PersonaContext(
                    id="persona-1",
                    name="Marketing Leader",
                    job_titles=["VP Marketing", "Marketing Director"],
                    seniority_levels=["vp", "director"],
                    company_sizes=["201-500", "501-1000"],
                ),
            ],
            industry_fit_scores=[
                IndustryFitScore(industry="SaaS", fit_score=95),
                IndustryFitScore(industry="Consulting", fit_score=60),
            ],
            target_countries=["United States"],
        )

    @pytest.fixture
    def model(self, context: ScoringContext) -> ScoringModel:
        return ScoringModel(context)

    @pytest.fixture
    def high_quality_lead(self) -> LeadScoreRecord:
        return LeadScoreRecord(
            id="lead-1",
            title="VP Marketing",
            seniority="vp",
            company_name="Acme Corp",
            company_size="201-500",
            company_industry="SaaS",
            country="United States",
            email="vp@acme.com",
            phone="555-1234",
            company_domain="acme.com",
            linkedin_url="https://linkedin.com/in/vp",
        )

    @pytest.fixture
    def medium_quality_lead(self) -> LeadScoreRecord:
        return LeadScoreRecord(
            id="lead-2",
            title="Marketing Manager",
            seniority="manager",
            company_name="Small Co",
            company_size="11-50",
            company_industry="Consulting",
            country="Canada",
            email="manager@small.com",
        )

    @pytest.fixture
    def low_quality_lead(self) -> LeadScoreRecord:
        return LeadScoreRecord(
            id="lead-3",
            title="Software Engineer",
            company_name="Tech Corp",
            company_industry="Unknown",
        )

    def test_score_high_quality_lead(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)

        assert result.lead_id == "lead-1"
        assert result.tier == "A"
        assert result.total_score >= 80
        assert "Marketing Leader" in result.persona_tags or "tier_a" in result.persona_tags

    def test_score_medium_quality_lead(
        self, model: ScoringModel, medium_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(medium_quality_lead)

        assert result.lead_id == "lead-2"
        assert result.tier in ["B", "C"]
        assert 40 <= result.total_score < 80

    def test_score_low_quality_lead(
        self, model: ScoringModel, low_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(low_quality_lead)

        assert result.lead_id == "lead-3"
        assert result.tier in ["C", "D"]
        assert result.total_score < 60

    def test_score_breakdown_components(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        breakdown = result.breakdown

        # Check all components are present
        assert "score" in breakdown.job_title_match
        assert "score" in breakdown.seniority_match
        assert "score" in breakdown.company_size_match
        assert "score" in breakdown.industry_fit
        assert "score" in breakdown.location_match
        assert "score" in breakdown.data_completeness

        # Check max scores
        assert breakdown.job_title_match["max"] == 30
        assert breakdown.seniority_match["max"] == 20
        assert breakdown.company_size_match["max"] == 15
        assert breakdown.industry_fit["max"] == 20
        assert breakdown.location_match["max"] == 10
        assert breakdown.data_completeness["max"] == 5

    def test_job_title_score_exact_match(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        assert result.breakdown.job_title_match["score"] == 30  # Exact match

    def test_job_title_score_no_title(self, model: ScoringModel) -> None:
        lead = LeadScoreRecord(id="lead-x", title=None)
        result = model.score_lead(lead)
        assert result.breakdown.job_title_match["score"] == 0

    def test_seniority_score_exact_match(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        assert result.breakdown.seniority_match["score"] >= 15  # Exact or close match

    def test_company_size_score_exact_match(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        assert result.breakdown.company_size_match["score"] == 15  # Exact match

    def test_industry_score_high_fit(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        # SaaS industry has 95% fit score -> ~19 points
        assert result.breakdown.industry_fit["score"] >= 18

    def test_location_score_target_country(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        assert result.breakdown.location_match["score"] == 10  # US is target

    def test_location_score_non_target_country(
        self, model: ScoringModel, medium_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(medium_quality_lead)
        assert result.breakdown.location_match["score"] == 3  # Canada is not target

    def test_completeness_score_all_fields(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)
        assert result.breakdown.data_completeness["score"] == 5  # All 4 fields

    def test_completeness_score_partial_fields(
        self, model: ScoringModel, medium_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(medium_quality_lead)
        # Only email present
        assert result.breakdown.data_completeness["score"] in [1, 2]

    def test_score_leads_batch(self, model: ScoringModel) -> None:
        leads = [
            LeadScoreRecord(id="1", title="VP Marketing", company_industry="SaaS"),
            LeadScoreRecord(id="2", title="Marketing Director", company_industry="Software"),
            LeadScoreRecord(id="3", title="Software Engineer", company_industry="Unknown"),
        ]

        results = model.score_leads_batch(leads)

        assert len(results) == 3
        assert all(r.lead_id in ["1", "2", "3"] for r in results)
        assert all(r.tier in ["A", "B", "C", "D"] for r in results)

    def test_persona_tags_included(
        self, model: ScoringModel, high_quality_lead: LeadScoreRecord
    ) -> None:
        result = model.score_lead(high_quality_lead)

        # Should have tier tag
        assert any("tier_" in tag for tag in result.persona_tags)

        # Should have seniority tag
        assert any("seniority_" in tag for tag in result.persona_tags)


class TestScoreBreakdown:
    """Tests for ScoreBreakdown class."""

    def test_total_score_calculation(self) -> None:
        breakdown = ScoreBreakdown(
            job_title_match={"score": 25, "max": 30},
            seniority_match={"score": 15, "max": 20},
            company_size_match={"score": 10, "max": 15},
            industry_fit={"score": 18, "max": 20},
            location_match={"score": 10, "max": 10},
            data_completeness={"score": 5, "max": 5},
        )

        assert breakdown.total_score == 83

    def test_to_dict(self) -> None:
        breakdown = ScoreBreakdown(
            job_title_match={"score": 25},
            seniority_match={"score": 15},
            company_size_match={"score": 10},
            industry_fit={"score": 18},
            location_match={"score": 10},
            data_completeness={"score": 5},
        )

        result = breakdown.to_dict()

        assert "job_title_match" in result
        assert "seniority_match" in result
        assert "company_size_match" in result
        assert "industry_fit" in result
        assert "location_match" in result
        assert "data_completeness" in result
