"""Unit tests for Import Finalizer summary builder."""

import pytest

from src.agents.import_finalizer.schemas import CampaignData, NicheData
from src.agents.import_finalizer.summary_builder import (
    build_dedup_summary,
    build_full_summary,
    build_scoring_summary,
    build_scraping_summary,
    build_summary_from_dict,
    build_validation_summary,
    format_summary_for_display,
)


@pytest.fixture
def sample_campaign() -> CampaignData:
    """Create a sample campaign data object."""
    return CampaignData(
        id="campaign-123",
        name="Q4 SaaS Outreach",
        niche_id="niche-456",
        status="scored",
        target_leads=50000,
        total_leads_scraped=45000,
        scraping_cost=450.00,
        total_leads_valid=40000,
        total_leads_invalid=5000,
        total_duplicates_found=500,
        total_cross_duplicates=200,
        total_leads_available=39300,
        leads_scored=39300,
        avg_lead_score=72.5,
        leads_tier_a=5000,
        leads_tier_b=15000,
        leads_tier_c=19300,
    )


@pytest.fixture
def sample_niche() -> NicheData:
    """Create a sample niche data object."""
    return NicheData(
        id="niche-456",
        name="SaaS Founders",
        industry=["Technology", "Software"],
        job_titles=["CEO", "Founder", "CTO"],
    )


class TestBuildScrapingSummary:
    """Tests for build_scraping_summary."""

    def test_calculates_cost_per_lead(self, sample_campaign: CampaignData) -> None:
        """Test that cost per lead is calculated correctly."""
        summary = build_scraping_summary(sample_campaign)

        assert summary.target_leads == 50000
        assert summary.total_scraped == 45000
        assert summary.scraping_cost == 450.00
        assert summary.cost_per_lead == 0.01  # 450 / 45000

    def test_handles_zero_scraped(self) -> None:
        """Test handling of zero scraped leads."""
        campaign = CampaignData(
            id="test",
            name="Test",
            niche_id=None,
            status="draft",
            target_leads=50000,
            total_leads_scraped=0,
            scraping_cost=0.0,
            total_leads_valid=0,
            total_leads_invalid=0,
            total_duplicates_found=0,
            total_cross_duplicates=0,
            total_leads_available=0,
            leads_scored=0,
            avg_lead_score=0.0,
            leads_tier_a=0,
            leads_tier_b=0,
            leads_tier_c=0,
        )
        summary = build_scraping_summary(campaign)

        assert summary.cost_per_lead == 0.0


class TestBuildValidationSummary:
    """Tests for build_validation_summary."""

    def test_calculates_validity_rate(self, sample_campaign: CampaignData) -> None:
        """Test that validity rate is calculated correctly."""
        summary = build_validation_summary(sample_campaign)

        assert summary.total_valid == 40000
        assert summary.total_invalid == 5000
        # 40000 / 45000 = 0.8889
        assert abs(summary.validity_rate - 0.8889) < 0.001

    def test_handles_zero_checked(self) -> None:
        """Test handling of zero checked leads."""
        campaign = CampaignData(
            id="test",
            name="Test",
            niche_id=None,
            status="draft",
            target_leads=50000,
            total_leads_scraped=0,
            scraping_cost=0.0,
            total_leads_valid=0,
            total_leads_invalid=0,
            total_duplicates_found=0,
            total_cross_duplicates=0,
            total_leads_available=0,
            leads_scored=0,
            avg_lead_score=0.0,
            leads_tier_a=0,
            leads_tier_b=0,
            leads_tier_c=0,
        )
        summary = build_validation_summary(campaign)

        assert summary.validity_rate == 0.0


class TestBuildDedupSummary:
    """Tests for build_dedup_summary."""

    def test_includes_all_counts(self, sample_campaign: CampaignData) -> None:
        """Test that all dedup counts are included."""
        summary = build_dedup_summary(sample_campaign)

        assert summary.within_campaign_dupes == 500
        assert summary.cross_campaign_dupes == 200
        assert summary.available_after_dedup == 39300


class TestBuildScoringSummary:
    """Tests for build_scoring_summary."""

    def test_includes_tier_breakdown(self, sample_campaign: CampaignData) -> None:
        """Test that tier breakdown is included."""
        summary = build_scoring_summary(sample_campaign)

        assert summary.total_scored == 39300
        assert summary.avg_score == 72.5
        assert summary.tier_breakdown.tier_a == 5000
        assert summary.tier_breakdown.tier_b == 15000
        assert summary.tier_breakdown.tier_c == 19300


class TestBuildFullSummary:
    """Tests for build_full_summary."""

    def test_combines_all_sections(
        self,
        sample_campaign: CampaignData,
        sample_niche: NicheData,
    ) -> None:
        """Test that all sections are combined."""
        summary = build_full_summary(sample_campaign, sample_niche)

        assert summary.campaign_id == "campaign-123"
        assert summary.campaign_name == "Q4 SaaS Outreach"
        assert summary.niche_name == "SaaS Founders"
        assert summary.scraping.target_leads == 50000
        assert summary.validation.total_valid == 40000
        assert summary.deduplication.available_after_dedup == 39300
        assert summary.scoring.total_scored == 39300

    def test_handles_no_niche(self, sample_campaign: CampaignData) -> None:
        """Test handling when niche is not provided."""
        summary = build_full_summary(sample_campaign, None)

        assert summary.niche_name == "Unknown"

    def test_total_available_property(
        self,
        sample_campaign: CampaignData,
        sample_niche: NicheData,
    ) -> None:
        """Test that total_available is correct."""
        summary = build_full_summary(sample_campaign, sample_niche)

        assert summary.total_available == 39300


class TestBuildSummaryFromDict:
    """Tests for build_summary_from_dict."""

    def test_creates_summary_from_dicts(self) -> None:
        """Test creation from raw dictionaries."""
        campaign_dict = {
            "id": "campaign-123",
            "name": "Test Campaign",
            "niche_id": "niche-456",
            "status": "scored",
            "target_leads": 10000,
            "total_leads_scraped": 9000,
            "scraping_cost": 90.0,
            "total_leads_valid": 8000,
            "total_leads_invalid": 1000,
            "total_duplicates_found": 100,
            "total_cross_duplicates": 50,
            "total_leads_available": 7850,
            "leads_scored": 7850,
            "avg_lead_score": 65.0,
            "leads_tier_a": 1000,
            "leads_tier_b": 3000,
            "leads_tier_c": 3850,
        }
        niche_dict = {
            "id": "niche-456",
            "name": "Test Niche",
            "industry": ["Tech"],
            "job_titles": ["CTO"],
        }

        summary = build_summary_from_dict(campaign_dict, niche_dict)

        assert summary.campaign_name == "Test Campaign"
        assert summary.niche_name == "Test Niche"
        assert summary.total_available == 7850


class TestFormatSummaryForDisplay:
    """Tests for format_summary_for_display."""

    def test_includes_all_sections(
        self,
        sample_campaign: CampaignData,
        sample_niche: NicheData,
    ) -> None:
        """Test that all sections are included in display."""
        summary = build_full_summary(sample_campaign, sample_niche)
        display = format_summary_for_display(summary)

        assert "Q4 SaaS Outreach" in display
        assert "SaaS Founders" in display
        assert "SCRAPING:" in display
        assert "VALIDATION:" in display
        assert "DEDUPLICATION:" in display
        assert "SCORING:" in display
        assert "TOTAL AVAILABLE:" in display

    def test_formats_numbers(
        self,
        sample_campaign: CampaignData,
        sample_niche: NicheData,
    ) -> None:
        """Test that numbers are formatted with commas."""
        summary = build_full_summary(sample_campaign, sample_niche)
        display = format_summary_for_display(summary)

        # Should have formatted numbers
        assert "50,000" in display  # target_leads
        assert "45,000" in display  # total_scraped
