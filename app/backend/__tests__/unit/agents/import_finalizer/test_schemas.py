"""Unit tests for Import Finalizer schemas."""

import pytest

from src.agents.import_finalizer.schemas import (
    CampaignData,
    DeduplicationSummary,
    ImportFinalizerResult,
    ImportSummary,
    LeadRow,
    NicheData,
    ScoringSummary,
    ScrapingSummary,
    SheetExportResult,
    TierBreakdown,
    ValidationSummary,
)


class TestScrapingSummary:
    """Tests for ScrapingSummary."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        summary = ScrapingSummary(
            target_leads=50000,
            total_scraped=45000,
            scraping_cost=450.00,
            cost_per_lead=0.01,
        )
        result = summary.to_dict()

        assert result["target_leads"] == 50000
        assert result["total_scraped"] == 45000
        assert result["scraping_cost"] == 450.00
        assert result["cost_per_lead"] == 0.01

    def test_rounds_values(self) -> None:
        """Test that values are properly rounded."""
        summary = ScrapingSummary(
            target_leads=100,
            total_scraped=90,
            scraping_cost=123.456789,
            cost_per_lead=0.123456789,
        )
        result = summary.to_dict()

        assert result["scraping_cost"] == 123.46
        assert result["cost_per_lead"] == 0.1235


class TestValidationSummary:
    """Tests for ValidationSummary."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        summary = ValidationSummary(
            total_valid=40000,
            total_invalid=5000,
            validity_rate=0.888888,
        )
        result = summary.to_dict()

        assert result["total_valid"] == 40000
        assert result["total_invalid"] == 5000
        assert result["validity_rate"] == 0.8889


class TestDeduplicationSummary:
    """Tests for DeduplicationSummary."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        summary = DeduplicationSummary(
            within_campaign_dupes=500,
            cross_campaign_dupes=200,
            available_after_dedup=39300,
        )
        result = summary.to_dict()

        assert result["within_campaign_dupes"] == 500
        assert result["cross_campaign_dupes"] == 200
        assert result["available_after_dedup"] == 39300


class TestTierBreakdown:
    """Tests for TierBreakdown."""

    def test_total_property(self) -> None:
        """Test total leads calculation."""
        tier = TierBreakdown(
            tier_a=5000,
            tier_b=15000,
            tier_c=10000,
            tier_d=1000,
        )

        assert tier.total == 31000

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        tier = TierBreakdown(tier_a=100, tier_b=200, tier_c=150, tier_d=50)
        result = tier.to_dict()

        assert result["tier_a"] == 100
        assert result["tier_b"] == 200
        assert result["tier_c"] == 150
        assert result["tier_d"] == 50
        assert result["total"] == 500


class TestScoringSummary:
    """Tests for ScoringSummary."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        tier = TierBreakdown(tier_a=500, tier_b=1500, tier_c=1000)
        summary = ScoringSummary(
            total_scored=3000,
            avg_score=68.5,
            tier_breakdown=tier,
        )
        result = summary.to_dict()

        assert result["total_scored"] == 3000
        assert result["avg_score"] == 68.5
        assert result["tier_breakdown"]["tier_a"] == 500


class TestImportSummary:
    """Tests for ImportSummary."""

    @pytest.fixture
    def sample_summary(self) -> ImportSummary:
        """Create a sample import summary."""
        return ImportSummary(
            campaign_id="test-campaign-id",
            campaign_name="Test Campaign",
            niche_name="SaaS Founders",
            scraping=ScrapingSummary(
                target_leads=50000,
                total_scraped=45000,
                scraping_cost=450.00,
                cost_per_lead=0.01,
            ),
            validation=ValidationSummary(
                total_valid=40000,
                total_invalid=5000,
                validity_rate=0.8889,
            ),
            deduplication=DeduplicationSummary(
                within_campaign_dupes=500,
                cross_campaign_dupes=200,
                available_after_dedup=39300,
            ),
            scoring=ScoringSummary(
                total_scored=39300,
                avg_score=72.5,
                tier_breakdown=TierBreakdown(
                    tier_a=5000,
                    tier_b=15000,
                    tier_c=19300,
                ),
            ),
        )

    def test_total_available_property(self, sample_summary: ImportSummary) -> None:
        """Test that total_available matches deduplication available."""
        assert sample_summary.total_available == 39300

    def test_to_dict(self, sample_summary: ImportSummary) -> None:
        """Test conversion to dictionary."""
        result = sample_summary.to_dict()

        assert result["campaign_id"] == "test-campaign-id"
        assert result["campaign_name"] == "Test Campaign"
        assert result["niche_name"] == "SaaS Founders"
        assert result["total_available"] == 39300
        assert "scraping" in result
        assert "validation" in result
        assert "deduplication" in result
        assert "scoring" in result


class TestLeadRow:
    """Tests for LeadRow."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "title": "CEO",
            "company_name": "Acme Inc",
            "company_domain": "acme.com",
            "company_size": "50-200",
            "location": "San Francisco, CA",
            "lead_score": 85,
            "lead_tier": "A",
        }
        lead = LeadRow.from_dict(data)

        assert lead.first_name == "John"
        assert lead.last_name == "Doe"
        assert lead.email == "john@example.com"
        assert lead.lead_score == 85
        assert lead.lead_tier == "A"

    def test_from_dict_with_job_title_alias(self) -> None:
        """Test that job_title is mapped to title."""
        data = {
            "first_name": "Jane",
            "job_title": "CTO",  # Uses job_title instead of title
        }
        lead = LeadRow.from_dict(data)

        assert lead.title == "CTO"

    def test_to_row_basic(self) -> None:
        """Test basic row conversion."""
        lead = LeadRow(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            title="CEO",
            company_name="Acme",
            company_domain="acme.com",
            company_size="50-200",
            location="SF",
            lead_score=85,
            lead_tier="A",
        )
        row = lead.to_row(include_size_location=False)

        assert row == ["John", "Doe", "john@example.com", "CEO", "Acme", "acme.com", 85, "A"]

    def test_to_row_full(self) -> None:
        """Test full row with size and location."""
        lead = LeadRow(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            title="CEO",
            company_name="Acme",
            company_domain="acme.com",
            company_size="50-200",
            location="SF",
            lead_score=85,
            lead_tier="A",
        )
        row = lead.to_row(include_size_location=True)

        assert row == [
            "John",
            "Doe",
            "john@example.com",
            "CEO",
            "Acme",
            "acme.com",
            "50-200",
            "SF",
            85,
            "A",
        ]

    def test_to_row_handles_none(self) -> None:
        """Test that None values are converted to empty strings."""
        lead = LeadRow(
            first_name=None,
            last_name=None,
            email=None,
            title=None,
            company_name=None,
            company_domain=None,
            company_size=None,
            location=None,
            lead_score=None,
            lead_tier=None,
        )
        row = lead.to_row(include_size_location=False)

        assert row == ["", "", "", "", "", "", 0, ""]


class TestSheetExportResult:
    """Tests for SheetExportResult."""

    def test_success_result(self) -> None:
        """Test successful export result."""
        result = SheetExportResult(
            success=True,
            spreadsheet_id="abc123",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/abc123",
            sheet_names=["Summary", "Tier A", "Tier B"],
            total_rows_written=1500,
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["spreadsheet_id"] == "abc123"
        assert "Summary" in data["sheet_names"]

    def test_failed_result(self) -> None:
        """Test failed export result."""
        result = SheetExportResult(
            success=False,
            error_message="Authentication failed",
        )
        data = result.to_dict()

        assert data["success"] is False
        assert data["error_message"] == "Authentication failed"


class TestCampaignData:
    """Tests for CampaignData."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "id": "campaign-123",
            "name": "Q4 Outreach",
            "niche_id": "niche-456",
            "status": "import_complete",
            "target_leads": 50000,
            "total_leads_scraped": 45000,
            "scraping_cost": 450.0,
            "total_leads_valid": 40000,
            "total_leads_invalid": 5000,
            "total_duplicates_found": 500,
            "total_cross_duplicates": 200,
            "total_leads_available": 39300,
            "leads_scored": 39300,
            "avg_lead_score": 72.5,
            "leads_tier_a": 5000,
            "leads_tier_b": 15000,
            "leads_tier_c": 19300,
        }
        campaign = CampaignData.from_dict(data)

        assert campaign.id == "campaign-123"
        assert campaign.name == "Q4 Outreach"
        assert campaign.total_leads_scraped == 45000
        assert campaign.leads_tier_a == 5000

    def test_from_dict_handles_none(self) -> None:
        """Test that None values are handled gracefully."""
        data = {"id": "test", "name": "Test"}
        campaign = CampaignData.from_dict(data)

        assert campaign.total_leads_scraped == 0
        assert campaign.scraping_cost == 0.0
        assert campaign.leads_tier_a == 0


class TestNicheData:
    """Tests for NicheData."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "id": "niche-123",
            "name": "SaaS Founders",
            "industry": ["Technology", "Software"],
            "job_titles": ["CEO", "Founder", "CTO"],
        }
        niche = NicheData.from_dict(data)

        assert niche.id == "niche-123"
        assert niche.name == "SaaS Founders"
        assert "Technology" in niche.industry
        assert "CEO" in niche.job_titles

    def test_from_dict_handles_none(self) -> None:
        """Test that None values are handled gracefully."""
        data = {"id": "test", "name": "Test"}
        niche = NicheData.from_dict(data)

        assert niche.industry == []
        assert niche.job_titles == []


class TestImportFinalizerResult:
    """Tests for ImportFinalizerResult."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = ImportFinalizerResult()

        assert result.success is True
        assert result.status == "completed"
        assert result.errors == []
        assert result.warnings == []

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = ImportFinalizerResult(
            success=True,
            status="completed",
            sheet_url="https://example.com/sheet",
            sheet_id="abc123",
            notification_sent=True,
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["sheet_url"] == "https://example.com/sheet"
        assert data["notification_sent"] is True
