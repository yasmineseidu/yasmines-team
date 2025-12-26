"""Unit tests for Verification Finalizer reports module."""

import pytest

from src.agents.verification_finalizer.reports import (
    CostSummary,
    QualityReport,
    QualityReportGenerator,
    TierBreakdown,
    VerificationSummary,
)


class TestTierBreakdown:
    """Tests for TierBreakdown dataclass."""

    def test_tier_breakdown_default_values(self) -> None:
        """TierBreakdown should have correct default values."""
        tier = TierBreakdown(tier="A")
        assert tier.tier == "A"
        assert tier.total == 0
        assert tier.verified == 0
        assert tier.enriched == 0
        assert tier.ready == 0
        assert tier.avg_score == 0.0
        assert tier.avg_enrichment_cost == 0.0

    def test_tier_breakdown_with_values(self) -> None:
        """TierBreakdown should store provided values."""
        tier = TierBreakdown(
            tier="A",
            total=1000,
            verified=900,
            enriched=850,
            ready=800,
            avg_score=85.5,
            avg_enrichment_cost=0.05,
        )
        assert tier.total == 1000
        assert tier.verified == 900
        assert tier.enriched == 850
        assert tier.ready == 800
        assert tier.avg_score == 85.5
        assert tier.avg_enrichment_cost == 0.05

    def test_verification_rate_calculation(self) -> None:
        """verification_rate should calculate correctly."""
        tier = TierBreakdown(tier="A", total=1000, verified=900)
        assert tier.verification_rate == 90.0

    def test_verification_rate_zero_total(self) -> None:
        """verification_rate should return 0 when total is 0."""
        tier = TierBreakdown(tier="A", total=0, verified=0)
        assert tier.verification_rate == 0.0

    def test_enrichment_rate_calculation(self) -> None:
        """enrichment_rate should calculate correctly."""
        tier = TierBreakdown(tier="A", verified=900, enriched=810)
        assert tier.enrichment_rate == 90.0

    def test_enrichment_rate_zero_verified(self) -> None:
        """enrichment_rate should return 0 when verified is 0."""
        tier = TierBreakdown(tier="A", verified=0, enriched=0)
        assert tier.enrichment_rate == 0.0

    def test_readiness_rate_calculation(self) -> None:
        """readiness_rate should calculate correctly."""
        tier = TierBreakdown(tier="A", enriched=100, ready=95)
        assert tier.readiness_rate == 95.0

    def test_readiness_rate_zero_enriched(self) -> None:
        """readiness_rate should return 0 when enriched is 0."""
        tier = TierBreakdown(tier="A", enriched=0, ready=0)
        assert tier.readiness_rate == 0.0

    def test_to_dict(self) -> None:
        """to_dict should return correct dictionary."""
        tier = TierBreakdown(
            tier="A",
            total=1000,
            verified=900,
            enriched=850,
            ready=800,
        )
        result = tier.to_dict()
        assert result["tier"] == "A"
        assert result["total"] == 1000
        assert result["verified"] == 900
        assert result["enriched"] == 850
        assert result["ready"] == 800
        assert "verification_rate" in result
        assert "enrichment_rate" in result
        assert "readiness_rate" in result


class TestVerificationSummary:
    """Tests for VerificationSummary dataclass."""

    def test_verification_summary_default_values(self) -> None:
        """VerificationSummary should have correct default values."""
        summary = VerificationSummary()
        assert summary.emails_found == 0
        assert summary.emails_verified == 0
        assert summary.emails_valid == 0
        assert summary.emails_invalid == 0
        assert summary.emails_risky == 0
        assert summary.emails_catchall == 0

    def test_verification_rate_calculation(self) -> None:
        """verification_rate should calculate correctly."""
        summary = VerificationSummary(emails_found=1000, emails_verified=920)
        assert summary.verification_rate == 92.0

    def test_verification_rate_zero_found(self) -> None:
        """verification_rate should return 0 when emails_found is 0."""
        summary = VerificationSummary(emails_found=0)
        assert summary.verification_rate == 0.0

    def test_validity_rate_calculation(self) -> None:
        """validity_rate should calculate correctly."""
        summary = VerificationSummary(emails_verified=1000, emails_valid=850)
        assert summary.validity_rate == 85.0

    def test_validity_rate_zero_verified(self) -> None:
        """validity_rate should return 0 when emails_verified is 0."""
        summary = VerificationSummary(emails_verified=0)
        assert summary.validity_rate == 0.0

    def test_to_dict(self) -> None:
        """to_dict should return correct dictionary."""
        summary = VerificationSummary(
            emails_found=1000,
            emails_verified=920,
            emails_valid=850,
            emails_invalid=50,
            emails_risky=10,
            emails_catchall=10,
        )
        result = summary.to_dict()
        assert result["emails_found"] == 1000
        assert result["emails_verified"] == 920
        assert result["emails_valid"] == 850
        assert "verification_rate" in result
        assert "validity_rate" in result


class TestCostSummary:
    """Tests for CostSummary dataclass."""

    def test_cost_summary_default_values(self) -> None:
        """CostSummary should have correct default values."""
        cost = CostSummary()
        assert cost.scraping_cost == 0.0
        assert cost.enrichment_cost == 0.0
        assert cost.verification_cost == 0.0

    def test_total_cost_calculation(self) -> None:
        """total_cost should sum all costs."""
        cost = CostSummary(
            scraping_cost=100.0,
            enrichment_cost=250.0,
            verification_cost=50.0,
        )
        assert cost.total_cost == 400.0

    def test_to_dict(self) -> None:
        """to_dict should return correct dictionary."""
        cost = CostSummary(scraping_cost=100.0, enrichment_cost=250.0)
        result = cost.to_dict()
        assert result["scraping_cost"] == 100.0
        assert result["enrichment_cost"] == 250.0
        assert "total_cost" in result


class TestQualityReport:
    """Tests for QualityReport dataclass."""

    @pytest.fixture
    def sample_report(self) -> QualityReport:
        """Create a sample report for testing."""
        report = QualityReport(
            campaign_id="test-campaign-123",
            campaign_name="Test Campaign",
            niche_name="SaaS Founders",
            total_leads=3000,
            total_ready=2500,
        )
        report.verification_summary = VerificationSummary(
            emails_found=3000,
            emails_verified=2800,
            emails_valid=2500,
            emails_invalid=200,
            emails_risky=50,
            emails_catchall=50,
        )
        report.tier_breakdowns["A"] = TierBreakdown(
            tier="A",
            total=1000,
            verified=950,
            enriched=900,
            ready=850,
            avg_score=90.0,
        )
        report.tier_breakdowns["B"] = TierBreakdown(
            tier="B",
            total=1500,
            verified=1400,
            enriched=1300,
            ready=1200,
            avg_score=75.0,
        )
        report.tier_breakdowns["C"] = TierBreakdown(
            tier="C",
            total=500,
            verified=450,
            enriched=400,
            ready=450,
            avg_score=55.0,
        )
        report.cost_summary = CostSummary(
            scraping_cost=150.0,
            enrichment_cost=500.0,
            verification_cost=100.0,
        )
        return report

    def test_quality_report_initialization(self, sample_report: QualityReport) -> None:
        """QualityReport should initialize correctly."""
        assert sample_report.campaign_id == "test-campaign-123"
        assert sample_report.campaign_name == "Test Campaign"
        assert sample_report.niche_name == "SaaS Founders"

    def test_email_verification_rate(self, sample_report: QualityReport) -> None:
        """email_verification_rate should return verification summary rate."""
        # 2800/3000 = 93.33%
        assert sample_report.email_verification_rate == 93.33

    def test_enrichment_completion_rate(self, sample_report: QualityReport) -> None:
        """enrichment_completion_rate should calculate across all tiers."""
        # Total enriched: 900 + 1300 + 400 = 2600
        # Total verified: 950 + 1400 + 450 = 2800
        # Rate: 2600/2800 = 92.86%
        assert sample_report.enrichment_completion_rate == 92.86

    def test_data_quality_score(self, sample_report: QualityReport) -> None:
        """data_quality_score should calculate weighted score."""
        # This is a weighted calculation, just check it's reasonable
        assert 0 <= sample_report.data_quality_score <= 1

    def test_data_quality_score_zero_leads(self) -> None:
        """data_quality_score should return 0 when total_leads is 0."""
        report = QualityReport(
            campaign_id="test",
            campaign_name="Test",
            niche_name="Test",
            total_leads=0,
        )
        assert report.data_quality_score == 0.0

    def test_cost_per_ready_lead(self, sample_report: QualityReport) -> None:
        """cost_per_ready_lead should calculate correctly."""
        # Total cost: 150 + 500 + 100 = 750
        # Ready leads: 2500
        # Cost per lead: 750/2500 = 0.30
        assert sample_report.cost_per_ready_lead == 0.30

    def test_cost_per_ready_lead_zero_ready(self) -> None:
        """cost_per_ready_lead should return 0 when total_ready is 0."""
        report = QualityReport(
            campaign_id="test",
            campaign_name="Test",
            niche_name="Test",
            total_ready=0,
        )
        assert report.cost_per_ready_lead == 0.0

    def test_add_tier_breakdown(self) -> None:
        """add_tier_breakdown should add tier to breakdowns dict."""
        report = QualityReport(
            campaign_id="test",
            campaign_name="Test",
            niche_name="Test",
        )
        tier = TierBreakdown(tier="A", total=100)
        report.add_tier_breakdown(tier)
        assert "A" in report.tier_breakdowns
        assert report.tier_breakdowns["A"].total == 100

    def test_to_dict(self, sample_report: QualityReport) -> None:
        """to_dict should return complete dictionary."""
        result = sample_report.to_dict()
        assert result["campaign_id"] == "test-campaign-123"
        assert result["campaign_name"] == "Test Campaign"
        assert result["niche_name"] == "SaaS Founders"
        assert "verification_summary" in result
        assert "tier_breakdowns" in result
        assert "cost_summary" in result
        assert "quality_scores" in result
        assert "cost_per_ready_lead" in result
        assert "generated_at" in result

    def test_to_summary_text(self, sample_report: QualityReport) -> None:
        """to_summary_text should generate readable text."""
        text = sample_report.to_summary_text()
        assert "Test Campaign" in text
        assert "SaaS Founders" in text
        assert "Email Verification:" in text
        assert "Quality by Tier:" in text
        assert "Tier A:" in text
        assert "Summary:" in text


class TestQualityReportGenerator:
    """Tests for QualityReportGenerator."""

    @pytest.fixture
    def sample_data(self) -> dict[str, list[dict]]:
        """Create sample data for generator."""
        return {
            "campaign_data": {
                "id": "test-123",
                "name": "Test Campaign",
                "scraping_cost": 100.0,
                "enrichment_cost": 250.0,
            },
            "niche_data": {
                "name": "SaaS Founders",
            },
            "email_stats": [
                {"email_status": "valid", "count": 850, "avg_score": 80.0},
                {"email_status": "invalid", "count": 100, "avg_score": 50.0},
                {"email_status": "risky", "count": 30, "avg_score": 60.0},
                {"email_status": "catchall", "count": 20, "avg_score": 65.0},
            ],
            "tier_stats": [
                {
                    "lead_tier": "A",
                    "total": 300,
                    "valid_email": 280,
                    "has_description": 270,
                    "avg_score": 90.0,
                    "avg_enrichment_cost": 0.05,
                },
                {
                    "lead_tier": "B",
                    "total": 500,
                    "valid_email": 450,
                    "has_description": 420,
                    "avg_score": 75.0,
                    "avg_enrichment_cost": 0.04,
                },
                {
                    "lead_tier": "C",
                    "total": 200,
                    "valid_email": 120,
                    "has_description": 100,
                    "avg_score": 55.0,
                    "avg_enrichment_cost": 0.03,
                },
            ],
        }

    def test_generator_creates_report(self, sample_data: dict[str, list[dict]]) -> None:
        """Generator should create a QualityReport."""
        generator = QualityReportGenerator(
            campaign_data=sample_data["campaign_data"],
            niche_data=sample_data["niche_data"],
            email_stats=sample_data["email_stats"],
            tier_stats=sample_data["tier_stats"],
        )
        report = generator.generate()

        assert isinstance(report, QualityReport)
        assert report.campaign_id == "test-123"
        assert report.campaign_name == "Test Campaign"
        assert report.niche_name == "SaaS Founders"

    def test_generator_builds_verification_summary(
        self, sample_data: dict[str, list[dict]]
    ) -> None:
        """Generator should build verification summary from email stats."""
        generator = QualityReportGenerator(
            campaign_data=sample_data["campaign_data"],
            niche_data=sample_data["niche_data"],
            email_stats=sample_data["email_stats"],
            tier_stats=sample_data["tier_stats"],
        )
        report = generator.generate()

        # 850 + 100 + 30 + 20 = 1000 found
        assert report.verification_summary.emails_found == 1000
        assert report.verification_summary.emails_valid == 850
        assert report.verification_summary.emails_invalid == 100
        assert report.verification_summary.emails_risky == 30
        assert report.verification_summary.emails_catchall == 20

    def test_generator_builds_tier_breakdowns(self, sample_data: dict[str, list[dict]]) -> None:
        """Generator should build tier breakdowns from tier stats."""
        generator = QualityReportGenerator(
            campaign_data=sample_data["campaign_data"],
            niche_data=sample_data["niche_data"],
            email_stats=sample_data["email_stats"],
            tier_stats=sample_data["tier_stats"],
        )
        report = generator.generate()

        assert "A" in report.tier_breakdowns
        assert "B" in report.tier_breakdowns
        assert "C" in report.tier_breakdowns

        tier_a = report.tier_breakdowns["A"]
        assert tier_a.total == 300
        assert tier_a.verified == 280
        assert tier_a.enriched == 270

    def test_generator_builds_cost_summary(self, sample_data: dict[str, list[dict]]) -> None:
        """Generator should build cost summary from campaign data."""
        generator = QualityReportGenerator(
            campaign_data=sample_data["campaign_data"],
            niche_data=sample_data["niche_data"],
            email_stats=sample_data["email_stats"],
            tier_stats=sample_data["tier_stats"],
        )
        report = generator.generate()

        assert report.cost_summary.scraping_cost == 100.0
        assert report.cost_summary.enrichment_cost == 250.0

    def test_generator_calculates_totals(self, sample_data: dict[str, list[dict]]) -> None:
        """Generator should calculate total leads and ready counts."""
        generator = QualityReportGenerator(
            campaign_data=sample_data["campaign_data"],
            niche_data=sample_data["niche_data"],
            email_stats=sample_data["email_stats"],
            tier_stats=sample_data["tier_stats"],
        )
        report = generator.generate()

        # Total leads: 300 + 500 + 200 = 1000
        assert report.total_leads == 1000
        # Total ready: 280 + 450 + 120 = 850 (valid_email counts)
        assert report.total_ready == 850
