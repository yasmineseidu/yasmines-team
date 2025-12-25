"""Unit tests for Import Finalizer Agent."""

import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.import_finalizer.agent import (
    ImportFinalizerAgent,
    finalize_import,
)
from src.agents.import_finalizer.schemas import (
    ImportFinalizerResult,
    SheetExportResult,
)


@pytest.fixture
def sample_campaign_data() -> dict[str, Any]:
    """Sample campaign data from database."""
    return {
        "id": "campaign-123",
        "name": "Q4 SaaS Outreach",
        "niche_id": "niche-456",
        "status": "scored",
        "target_leads": 50000,
        "total_leads_scraped": 45000,
        "scraping_cost": 450.00,
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


@pytest.fixture
def sample_niche_data() -> dict[str, Any]:
    """Sample niche data from database."""
    return {
        "id": "niche-456",
        "name": "SaaS Founders",
        "industry": ["Technology", "Software"],
        "job_titles": ["CEO", "Founder", "CTO"],
    }


@pytest.fixture
def sample_leads() -> list[dict[str, Any]]:
    """Sample lead data."""
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


class TestImportFinalizerAgentInitialization:
    """Tests for agent initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        agent = ImportFinalizerAgent()

        assert agent.name == "import_finalizer"
        assert agent.model == "claude-sonnet-4-20250514"

    def test_custom_model(self) -> None:
        """Test initialization with custom model."""
        agent = ImportFinalizerAgent(model="claude-opus-4-20250514")

        assert agent.model == "claude-opus-4-20250514"

    def test_has_system_prompt(self) -> None:
        """Test that system prompt is defined."""
        agent = ImportFinalizerAgent()

        assert "import finalization specialist" in agent.system_prompt.lower()
        assert "compile_summary" in agent.system_prompt
        assert "export_to_sheets" in agent.system_prompt


class TestImportFinalizerAgentDirectMode:
    """Tests for direct mode execution."""

    @pytest.fixture
    def agent(self) -> ImportFinalizerAgent:
        """Create an agent instance."""
        return ImportFinalizerAgent()

    @pytest.mark.asyncio
    async def test_run_direct_success(
        self,
        agent: ImportFinalizerAgent,
        sample_campaign_data: dict[str, Any],
        sample_niche_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test successful direct mode execution."""
        # Mock the sheets exporter
        mock_result = SheetExportResult(
            success=True,
            spreadsheet_id="sheet-123",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
            sheet_names=["Summary", "Tier A Leads", "Tier B Leads", "All Leads"],
            total_rows_written=100,
        )

        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(return_value=mock_result)
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            result = await agent.run(
                campaign_id="campaign-123",
                campaign_data=sample_campaign_data,
                niche_data=sample_niche_data,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
                use_claude=False,
            )

        assert result.success is True
        assert result.status == "completed"
        assert result.sheet_url == "https://docs.google.com/spreadsheets/d/sheet-123"
        assert result.sheet_id == "sheet-123"
        assert result.summary is not None
        assert result.summary.campaign_id == "campaign-123"
        assert result.execution_time_ms >= 0  # Can be 0 with fast mocks

    @pytest.mark.asyncio
    async def test_run_direct_with_csv_fallback(
        self,
        agent: ImportFinalizerAgent,
        sample_campaign_data: dict[str, Any],
        sample_niche_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test CSV fallback when Google Sheets fails."""
        # Mock failed Sheets export
        mock_sheets_result = SheetExportResult(
            success=False,
            error_message="Authentication failed",
        )

        # Mock successful CSV export
        expected_csv_path = os.path.join(tempfile.gettempdir(), "exports", "campaign-123_leads.csv")
        mock_csv_result = SheetExportResult(
            success=True,
            spreadsheet_url=expected_csv_path,
            total_rows_written=3,
        )

        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(return_value=mock_sheets_result)
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            with patch("src.agents.import_finalizer.agent.export_leads_to_csv") as mock_csv:
                mock_csv.return_value = mock_csv_result

                result = await agent.run(
                    campaign_id="campaign-123",
                    campaign_data=sample_campaign_data,
                    niche_data=sample_niche_data,
                    tier_a_leads=[sample_leads[0]],
                    tier_b_leads=[sample_leads[1]],
                    all_leads=sample_leads,
                    use_claude=False,
                )

        assert result.success is True
        assert result.status == "completed"
        assert result.sheet_url == expected_csv_path
        assert len(result.warnings) > 0
        assert "Google Sheets failed" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_run_direct_handles_exception(
        self,
        agent: ImportFinalizerAgent,
        sample_campaign_data: dict[str, Any],
        sample_niche_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test exception handling in direct mode."""
        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            result = await agent.run(
                campaign_id="campaign-123",
                campaign_data=sample_campaign_data,
                niche_data=sample_niche_data,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
                use_claude=False,
            )

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "Unexpected error" in result.errors[0]["message"]

    @pytest.mark.asyncio
    async def test_run_direct_without_niche(
        self,
        agent: ImportFinalizerAgent,
        sample_campaign_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test execution without niche data."""
        mock_result = SheetExportResult(
            success=True,
            spreadsheet_id="sheet-123",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
        )

        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(return_value=mock_result)
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            result = await agent.run(
                campaign_id="campaign-123",
                campaign_data=sample_campaign_data,
                niche_data=None,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
                use_claude=False,
            )

        assert result.success is True
        assert result.summary is not None
        assert result.summary.niche_name == "Unknown"


class TestFinalizeImportConvenience:
    """Tests for the finalize_import convenience function."""

    @pytest.mark.asyncio
    async def test_finalize_import_creates_agent(
        self,
        sample_campaign_data: dict[str, Any],
        sample_niche_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test that finalize_import creates and runs agent."""
        mock_result = SheetExportResult(
            success=True,
            spreadsheet_id="sheet-123",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
        )

        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(return_value=mock_result)
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            result = await finalize_import(
                campaign_id="campaign-123",
                campaign_data=sample_campaign_data,
                niche_data=sample_niche_data,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
            )

        assert result.success is True
        assert isinstance(result, ImportFinalizerResult)


class TestImportFinalizerResultToDict:
    """Tests for result serialization."""

    @pytest.mark.asyncio
    async def test_result_to_dict(
        self,
        sample_campaign_data: dict[str, Any],
        sample_niche_data: dict[str, Any],
        sample_leads: list[dict[str, Any]],
    ) -> None:
        """Test that result can be serialized to dict."""
        mock_result = SheetExportResult(
            success=True,
            spreadsheet_id="sheet-123",
            spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-123",
        )

        with patch("src.agents.import_finalizer.agent.SheetsExporter") as MockExporter:
            mock_exporter = AsyncMock()
            mock_exporter.export_leads = AsyncMock(return_value=mock_result)
            mock_exporter.close = AsyncMock()
            MockExporter.return_value = mock_exporter

            agent = ImportFinalizerAgent()
            result = await agent.run(
                campaign_id="campaign-123",
                campaign_data=sample_campaign_data,
                niche_data=sample_niche_data,
                tier_a_leads=[sample_leads[0]],
                tier_b_leads=[sample_leads[1]],
                all_leads=sample_leads,
                use_claude=False,
            )

        data = result.to_dict()

        assert "success" in data
        assert "status" in data
        assert "summary" in data
        assert "sheet_url" in data
        assert "execution_time_ms" in data
        assert data["success"] is True
