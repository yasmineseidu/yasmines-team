"""Unit tests for Verification Finalizer exports module."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.verification_finalizer.exports import (
    SheetsExportError,
    VerifiedLeadsExporter,
)
from src.agents.verification_finalizer.reports import (
    CostSummary,
    QualityReport,
    TierBreakdown,
    VerificationSummary,
)


class TestSheetsExportError:
    """Tests for SheetsExportError exception."""

    def test_error_with_message(self) -> None:
        """Error should store message."""
        error = SheetsExportError("Test error")
        assert error.message == "Test error"
        assert str(error) == "Test error"

    def test_error_with_details(self) -> None:
        """Error should store details."""
        error = SheetsExportError("Test error", {"key": "value"})
        assert error.details == {"key": "value"}

    def test_error_default_details(self) -> None:
        """Error should have empty details by default."""
        error = SheetsExportError("Test error")
        assert error.details == {}


class TestVerifiedLeadsExporter:
    """Tests for VerifiedLeadsExporter class."""

    @pytest.fixture
    def sample_report(self) -> QualityReport:
        """Create sample quality report."""
        report = QualityReport(
            campaign_id="test-123",
            campaign_name="Test Campaign",
            niche_name="SaaS Founders",
            total_leads=1000,
            total_ready=850,
        )
        report.verification_summary = VerificationSummary(
            emails_found=1000,
            emails_verified=920,
            emails_valid=850,
        )
        report.tier_breakdowns["A"] = TierBreakdown(
            tier="A",
            total=300,
            verified=280,
            enriched=270,
            ready=260,
        )
        report.tier_breakdowns["B"] = TierBreakdown(
            tier="B",
            total=500,
            verified=450,
            enriched=430,
            ready=420,
        )
        report.cost_summary = CostSummary(
            scraping_cost=100.0,
            enrichment_cost=250.0,
        )
        return report

    @pytest.fixture
    def sample_leads(self) -> list[dict[str, Any]]:
        """Create sample leads."""
        return [
            {
                "id": "lead-1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "title": "CEO",
                "company_name": "Example Inc",
                "company_domain": "example.com",
                "lead_score": 90,
                "lead_tier": "A",
                "email_status": "valid",
                "company_description": "A great company",
            },
            {
                "id": "lead-2",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "title": "CTO",
                "company_name": "Tech Corp",
                "company_domain": "tech.com",
                "lead_score": 85,
                "lead_tier": "A",
                "email_status": "valid",
                "company_description": None,
            },
        ]

    def test_exporter_initialization_with_credentials(self) -> None:
        """Exporter should initialize with credentials."""
        creds = {"type": "service_account", "project_id": "test"}
        exporter = VerifiedLeadsExporter(
            credentials_json=creds,
            delegated_user="user@example.com",
        )
        assert exporter.credentials_json == creds
        assert exporter.delegated_user == "user@example.com"

    def test_exporter_initialization_without_credentials_raises(self) -> None:
        """Exporter should raise when no credentials available."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SheetsExportError) as exc_info:
                VerifiedLeadsExporter()
            assert "GOOGLE_SERVICE_ACCOUNT_JSON" in exc_info.value.message

    def test_exporter_initialization_with_env_credentials(self) -> None:
        """Exporter should load credentials from environment."""
        creds_json = '{"type": "service_account", "project_id": "test"}'
        with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": creds_json}):
            exporter = VerifiedLeadsExporter()
            assert exporter.credentials_json["type"] == "service_account"

    def test_exporter_initialization_with_invalid_json(self) -> None:
        """Exporter should raise on invalid JSON credentials."""
        with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": "not-json"}):
            with pytest.raises(SheetsExportError) as exc_info:
                VerifiedLeadsExporter()
            assert "Invalid JSON" in exc_info.value.message

    def test_truncate_text_short(self) -> None:
        """_truncate_text should not truncate short text."""
        result = VerifiedLeadsExporter._truncate_text("Short text", 100)
        assert result == "Short text"

    def test_truncate_text_long(self) -> None:
        """_truncate_text should truncate long text with ellipsis."""
        long_text = "A" * 100
        result = VerifiedLeadsExporter._truncate_text(long_text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncate_text_none(self) -> None:
        """_truncate_text should return empty string for None."""
        result = VerifiedLeadsExporter._truncate_text(None, 100)
        assert result == ""

    def test_truncate_text_empty(self) -> None:
        """_truncate_text should return empty string for empty input."""
        result = VerifiedLeadsExporter._truncate_text("", 100)
        assert result == ""

    @pytest.mark.asyncio
    async def test_export_verified_leads_success(
        self,
        sample_report: QualityReport,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """export_verified_leads should create spreadsheet and return URL."""
        creds = {"type": "service_account", "project_id": "test"}

        mock_client = AsyncMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.spreadsheet_id = "test-spreadsheet-id"
        mock_client.create_spreadsheet.return_value = mock_spreadsheet
        mock_client.update_values.return_value = MagicMock()

        with patch.object(
            VerifiedLeadsExporter,
            "_get_client",
            return_value=mock_client,
        ):
            exporter = VerifiedLeadsExporter(credentials_json=creds)
            result = await exporter.export_verified_leads(
                report=sample_report,
                tier_a_leads=sample_leads,
                tier_b_leads=[],
                all_ready_leads=sample_leads,
            )

            assert result["spreadsheet_id"] == "test-spreadsheet-id"
            assert "spreadsheet_url" in result
            assert "test-spreadsheet-id" in result["spreadsheet_url"]

    @pytest.mark.asyncio
    async def test_export_verified_leads_creates_sheets(
        self,
        sample_report: QualityReport,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """export_verified_leads should create multiple sheets."""
        creds = {"type": "service_account", "project_id": "test"}

        mock_client = AsyncMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.spreadsheet_id = "test-id"
        mock_client.create_spreadsheet.return_value = mock_spreadsheet
        mock_client.update_values.return_value = MagicMock()

        with patch.object(
            VerifiedLeadsExporter,
            "_get_client",
            return_value=mock_client,
        ):
            exporter = VerifiedLeadsExporter(credentials_json=creds)
            await exporter.export_verified_leads(
                report=sample_report,
                tier_a_leads=sample_leads,
                tier_b_leads=[],
                all_ready_leads=sample_leads,
            )

            # Should create spreadsheet with 4 sheets
            mock_client.create_spreadsheet.assert_called_once()
            call_args = mock_client.create_spreadsheet.call_args
            sheets = call_args.kwargs.get("sheets") or call_args[1].get("sheets")
            assert len(sheets) == 4
            assert "Summary" in sheets
            assert "Tier A Leads" in sheets
            assert "Tier B Leads" in sheets
            assert "All Ready Leads" in sheets

    @pytest.mark.asyncio
    async def test_export_verified_leads_populates_data(
        self,
        sample_report: QualityReport,
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """export_verified_leads should populate all sheets with data."""
        creds = {"type": "service_account", "project_id": "test"}

        mock_client = AsyncMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.spreadsheet_id = "test-id"
        mock_client.create_spreadsheet.return_value = mock_spreadsheet
        mock_client.update_values.return_value = MagicMock()

        with patch.object(
            VerifiedLeadsExporter,
            "_get_client",
            return_value=mock_client,
        ):
            exporter = VerifiedLeadsExporter(credentials_json=creds)
            await exporter.export_verified_leads(
                report=sample_report,
                tier_a_leads=sample_leads,
                tier_b_leads=[],
                all_ready_leads=sample_leads,
            )

            # Should update values 4 times (one per sheet)
            assert mock_client.update_values.call_count == 4

    @pytest.mark.asyncio
    async def test_export_verified_leads_handles_api_error(
        self,
        sample_report: QualityReport,
    ) -> None:
        """export_verified_leads should wrap API errors."""
        creds = {"type": "service_account", "project_id": "test"}

        mock_client = AsyncMock()
        from src.integrations.google_sheets import GoogleSheetsAPIError

        mock_client.create_spreadsheet.side_effect = GoogleSheetsAPIError("API error")

        with patch.object(
            VerifiedLeadsExporter,
            "_get_client",
            return_value=mock_client,
        ):
            exporter = VerifiedLeadsExporter(credentials_json=creds)
            with pytest.raises(SheetsExportError) as exc_info:
                await exporter.export_verified_leads(
                    report=sample_report,
                    tier_a_leads=[],
                    tier_b_leads=[],
                    all_ready_leads=[],
                )

            assert "API error" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_exporter_close(self) -> None:
        """close should close the underlying client."""
        creds = {"type": "service_account", "project_id": "test"}
        exporter = VerifiedLeadsExporter(credentials_json=creds)

        mock_client = AsyncMock()
        exporter._client = mock_client

        await exporter.close()

        mock_client.close.assert_called_once()
        assert exporter._client is None

    @pytest.mark.asyncio
    async def test_exporter_close_when_not_connected(self) -> None:
        """close should handle case when not connected."""
        creds = {"type": "service_account", "project_id": "test"}
        exporter = VerifiedLeadsExporter(credentials_json=creds)

        # Should not raise
        await exporter.close()

    def test_lead_columns_constant(self) -> None:
        """LEAD_COLUMNS should contain expected columns."""
        expected = [
            "First Name",
            "Last Name",
            "Email",
            "Job Title",
            "Company Name",
            "Company Domain",
            "Lead Score",
            "Lead Tier",
            "Email Status",
            "Company Description",
        ]
        assert expected == VerifiedLeadsExporter.LEAD_COLUMNS
