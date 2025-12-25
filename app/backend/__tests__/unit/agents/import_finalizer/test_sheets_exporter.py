"""Unit tests for Import Finalizer sheets exporter."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.import_finalizer.schemas import (
    DeduplicationSummary,
    ImportSummary,
    ScoringSummary,
    ScrapingSummary,
    TierBreakdown,
    ValidationSummary,
)
from src.agents.import_finalizer.sheets_exporter import (
    SheetsExporter,
    export_leads_to_csv,
)


@pytest.fixture
def sample_summary() -> ImportSummary:
    """Create a sample import summary."""
    return ImportSummary(
        campaign_id="campaign-123",
        campaign_name="Q4 SaaS Outreach",
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


@pytest.fixture
def sample_leads() -> list[dict[str, Any]]:
    """Create sample lead data."""
    return [
        {
            "id": "lead-1",
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
        },
        {
            "id": "lead-2",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "title": "CTO",
            "company_name": "Tech Corp",
            "company_domain": "techcorp.com",
            "company_size": "200-500",
            "location": "New York, NY",
            "lead_score": 75,
            "lead_tier": "B",
        },
    ]


class TestSheetsExporterInitialization:
    """Tests for SheetsExporter initialization."""

    def test_initialization_without_credentials(self) -> None:
        """Test initialization logs warning without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            exporter = SheetsExporter()

            assert exporter.delegated_user is None
            assert exporter._credentials_json is None

    def test_initialization_with_delegated_user_env(self) -> None:
        """Test that delegated user is loaded from environment."""
        with patch.dict(
            "os.environ",
            {"GOOGLE_DELEGATED_USER": "user@example.com"},
        ):
            exporter = SheetsExporter()

            assert exporter.delegated_user == "user@example.com"

    def test_initialization_with_credentials_json(self) -> None:
        """Test initialization with credentials JSON."""
        creds = {"client_email": "test@project.iam.gserviceaccount.com"}
        exporter = SheetsExporter(credentials_json=creds)

        assert exporter._credentials_json == creds

    def test_initialization_with_credentials_path(self) -> None:
        """Test initialization with credentials path."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            import json

            json.dump({"client_email": "test@example.com"}, f)
            f.flush()

            exporter = SheetsExporter(credentials_path=f.name)

            assert exporter._credentials_json is not None
            assert exporter._credentials_json["client_email"] == "test@example.com"


class TestSheetsExporterHeaders:
    """Tests for column headers."""

    def test_basic_headers(self) -> None:
        """Test basic lead headers."""
        expected = [
            "First Name",
            "Last Name",
            "Email",
            "Job Title",
            "Company",
            "Domain",
            "Score",
            "Tier",
        ]
        assert expected == SheetsExporter.LEAD_HEADERS_BASIC

    def test_full_headers(self) -> None:
        """Test full lead headers with size and location."""
        expected = [
            "First Name",
            "Last Name",
            "Email",
            "Job Title",
            "Company",
            "Domain",
            "Company Size",
            "Location",
            "Score",
            "Tier",
        ]
        assert expected == SheetsExporter.LEAD_HEADERS_FULL


class TestSheetsExporterExport:
    """Tests for export_leads method."""

    @pytest.mark.asyncio
    async def test_export_success(
        self,
        sample_summary: ImportSummary,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test successful export to Google Sheets."""
        # Mock the GoogleSheetsClient
        with patch("src.agents.import_finalizer.sheets_exporter.GoogleSheetsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.close = AsyncMock()
            mock_client.create_spreadsheet = AsyncMock(
                return_value=MagicMock(
                    spreadsheet_id="sheet-123",
                    spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
                )
            )
            mock_client.update_values = AsyncMock()
            MockClient.return_value = mock_client

            exporter = SheetsExporter(
                credentials_json={"client_email": "test@example.com"},
                delegated_user="user@example.com",
            )

            result = await exporter.export_leads(
                campaign_name="Test Campaign",
                niche_name="Test Niche",
                summary=sample_summary,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
            )

            await exporter.close()

        assert result.success is True
        assert result.spreadsheet_id == "sheet-123"
        assert result.spreadsheet_url == "https://docs.google.com/spreadsheets/d/sheet-123"
        assert "Summary" in result.sheet_names
        assert result.total_rows_written > 0

    @pytest.mark.asyncio
    async def test_export_auth_failure(
        self,
        sample_summary: ImportSummary,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test handling of authentication failure."""
        from src.integrations.google_sheets import GoogleSheetsAuthError

        with patch("src.agents.import_finalizer.sheets_exporter.GoogleSheetsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock(side_effect=GoogleSheetsAuthError("Auth failed"))
            MockClient.return_value = mock_client

            exporter = SheetsExporter(
                credentials_json={"client_email": "test@example.com"},
            )

            result = await exporter.export_leads(
                campaign_name="Test Campaign",
                niche_name="Test Niche",
                summary=sample_summary,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
            )

            await exporter.close()

        assert result.success is False
        assert "Authentication failed" in result.error_message

    @pytest.mark.asyncio
    async def test_export_api_failure(
        self,
        sample_summary: ImportSummary,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test handling of API failure."""
        from src.integrations.google_sheets import GoogleSheetsAPIError

        with patch("src.agents.import_finalizer.sheets_exporter.GoogleSheetsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.close = AsyncMock()
            mock_client.create_spreadsheet = AsyncMock(
                side_effect=GoogleSheetsAPIError("API error")
            )
            MockClient.return_value = mock_client

            exporter = SheetsExporter(
                credentials_json={"client_email": "test@example.com"},
            )

            result = await exporter.export_leads(
                campaign_name="Test Campaign",
                niche_name="Test Niche",
                summary=sample_summary,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
            )

            await exporter.close()

        assert result.success is False
        assert "API error" in result.error_message


class TestExportLeadsToCsv:
    """Tests for CSV export fallback."""

    def test_csv_export_success(
        self,
        sample_summary: ImportSummary,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test successful CSV export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = f"{tmpdir}/leads.csv"

            result = export_leads_to_csv(csv_path, sample_summary, sample_leads)

            assert result.success is True
            assert result.total_rows_written == 3  # header + 2 leads
            assert Path(csv_path).exists()

            # Check content
            content = Path(csv_path).read_text()
            assert "First Name" in content
            assert "John" in content
            assert "jane@example.com" in content

    def test_csv_export_creates_directory(
        self,
        sample_summary: ImportSummary,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test that CSV export creates parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = f"{tmpdir}/nested/dir/leads.csv"

            result = export_leads_to_csv(csv_path, sample_summary, sample_leads)

            assert result.success is True
            assert Path(csv_path).exists()

    def test_csv_export_empty_leads(
        self,
        sample_summary: ImportSummary,
    ) -> None:
        """Test CSV export with empty leads list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = f"{tmpdir}/leads.csv"

            result = export_leads_to_csv(csv_path, sample_summary, [])

            assert result.success is True
            assert result.total_rows_written == 1  # Just header

    def test_csv_export_handles_none_values(
        self,
        sample_summary: ImportSummary,
    ) -> None:
        """Test that None values are handled in CSV."""
        leads = [
            {
                "first_name": None,
                "last_name": "Doe",
                "email": None,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = f"{tmpdir}/leads.csv"

            result = export_leads_to_csv(csv_path, sample_summary, leads)

            assert result.success is True

            content = Path(csv_path).read_text()
            assert "Doe" in content
