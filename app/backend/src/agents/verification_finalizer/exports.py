"""
Google Sheets export functionality for Verification Finalizer Agent.

Exports verified leads to Google Sheets for human review with summary,
tier breakdowns, and all lead data.
"""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from src.agents.verification_finalizer.reports import QualityReport
from src.integrations.google_sheets import (
    GoogleSheetsAPIError,
    GoogleSheetsClient,
    ValueInputOption,
)

logger = logging.getLogger(__name__)


class SheetsExportError(Exception):
    """Exception raised when export to Google Sheets fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class VerifiedLeadsExporter:
    """Exports verified leads to Google Sheets for review."""

    # Column headers for lead export
    LEAD_COLUMNS = [
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

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        delegated_user: str | None = None,
    ) -> None:
        """
        Initialize the exporter.

        Args:
            credentials_json: Google service account credentials.
            delegated_user: Email of user to impersonate (domain-wide delegation).
        """
        self.credentials_json = credentials_json or self._load_credentials_from_env()
        self.delegated_user = delegated_user or os.getenv("GOOGLE_DELEGATED_USER")
        self._client: GoogleSheetsClient | None = None

    @staticmethod
    def _load_credentials_from_env() -> dict[str, Any]:
        """Load Google credentials from environment variable."""
        creds_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not creds_str:
            raise SheetsExportError(
                "GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set",
                {"hint": "Set GOOGLE_SERVICE_ACCOUNT_JSON with service account credentials"},
            )
        try:
            result: dict[str, Any] = json.loads(creds_str)
            return result
        except json.JSONDecodeError as e:
            raise SheetsExportError(f"Invalid JSON in credentials: {e}") from e

    async def _get_client(self) -> GoogleSheetsClient:
        """Get authenticated Google Sheets client."""
        if self._client is None:
            self._client = GoogleSheetsClient(
                credentials_json=self.credentials_json,
                delegated_user=self.delegated_user,
            )
            await self._client.authenticate()
        return self._client

    async def close(self) -> None:
        """Close the Google Sheets client."""
        if self._client:
            await self._client.close()
            self._client = None

    async def export_verified_leads(
        self,
        report: QualityReport,
        tier_a_leads: list[dict[str, Any]],
        tier_b_leads: list[dict[str, Any]],
        all_ready_leads: list[dict[str, Any]],
    ) -> dict[str, str]:
        """
        Export verified leads to a new Google Spreadsheet.

        Creates a spreadsheet with:
        - Summary sheet with quality report
        - Tier A leads sheet
        - Tier B leads sheet
        - All Ready Leads sheet

        Args:
            report: Quality report for the campaign.
            tier_a_leads: List of Tier A lead dictionaries.
            tier_b_leads: List of Tier B lead dictionaries.
            all_ready_leads: List of all ready lead dictionaries.

        Returns:
            Dictionary with spreadsheet_id and spreadsheet_url.
        """
        client = await self._get_client()
        current_date = datetime.now(UTC).strftime("%Y-%m-%d")
        title = f"{report.niche_name} - Verified Leads - {current_date}"

        try:
            # Create spreadsheet with all sheets
            spreadsheet = await client.create_spreadsheet(
                title=title,
                sheets=["Summary", "Tier A Leads", "Tier B Leads", "All Ready Leads"],
            )

            spreadsheet_id = spreadsheet.spreadsheet_id
            if not spreadsheet_id:
                raise SheetsExportError("Failed to get spreadsheet ID after creation")

            logger.info(f"Created spreadsheet: {spreadsheet_id}")

            # Populate sheets
            await self._populate_summary_sheet(client, spreadsheet_id, report)
            await self._populate_leads_sheet(client, spreadsheet_id, "Tier A Leads", tier_a_leads)
            await self._populate_leads_sheet(client, spreadsheet_id, "Tier B Leads", tier_b_leads)
            await self._populate_leads_sheet(
                client, spreadsheet_id, "All Ready Leads", all_ready_leads
            )

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            logger.info(
                f"Exported {len(all_ready_leads):,} leads to Google Sheets: {spreadsheet_url}"
            )

            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
            }

        except GoogleSheetsAPIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise SheetsExportError(
                f"Failed to export to Google Sheets: {e}",
                {"api_error": str(e)},
            ) from e

    async def _populate_summary_sheet(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        report: QualityReport,
    ) -> None:
        """Populate the Summary sheet with quality report data."""
        summary_data: list[list[Any]] = [
            ["Phase 3 Verification Summary"],
            [""],
            ["Campaign", report.campaign_name],
            ["Niche", report.niche_name],
            ["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M UTC")],
            [""],
            ["Email Verification"],
            ["Emails Found", report.verification_summary.emails_found],
            ["Emails Verified", report.verification_summary.emails_verified],
            ["Valid Emails", report.verification_summary.emails_valid],
            ["Invalid Emails", report.verification_summary.emails_invalid],
            ["Verification Rate", f"{report.verification_summary.verification_rate}%"],
            [""],
            ["Lead Quality by Tier"],
        ]

        # Add tier breakdowns
        for tier_name in ["A", "B", "C"]:
            tier = report.tier_breakdowns.get(tier_name)
            if tier:
                summary_data.extend(
                    [
                        [f"Tier {tier_name}"],
                        ["  Total", tier.total],
                        ["  Verified", tier.verified],
                        ["  Ready", tier.ready],
                        ["  Avg Score", tier.avg_score],
                    ]
                )

        summary_data.extend(
            [
                [""],
                ["Summary"],
                ["Total Leads Ready", report.total_ready],
                ["Data Quality Score", f"{report.data_quality_score:.0%}"],
                [""],
                ["Cost Summary"],
                ["Scraping Cost", f"${report.cost_summary.scraping_cost:,.2f}"],
                ["Enrichment Cost", f"${report.cost_summary.enrichment_cost:,.2f}"],
                ["Total Cost", f"${report.cost_summary.total_cost:,.2f}"],
                ["Cost per Ready Lead", f"${report.cost_per_ready_lead:.4f}"],
            ]
        )

        await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_="Summary!A1",
            values=summary_data,
            value_input_option=ValueInputOption.USER_ENTERED,
        )

    async def _populate_leads_sheet(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
        leads: list[dict[str, Any]],
    ) -> None:
        """Populate a leads sheet with lead data."""
        if not leads:
            # Just add headers if no leads
            await client.update_values(
                spreadsheet_id=spreadsheet_id,
                range_=f"'{sheet_name}'!A1",
                values=[self.LEAD_COLUMNS],
                value_input_option=ValueInputOption.USER_ENTERED,
            )
            return

        # Build data rows
        rows: list[list[Any]] = [list(self.LEAD_COLUMNS)]
        for lead in leads:
            row = [
                lead.get("first_name", ""),
                lead.get("last_name", ""),
                lead.get("email", ""),
                lead.get("title", "") or lead.get("job_title", ""),
                lead.get("company_name", ""),
                lead.get("company_domain", ""),
                lead.get("lead_score", 0),
                lead.get("lead_tier", ""),
                lead.get("email_status", ""),
                self._truncate_text(lead.get("company_description", ""), 500),
            ]
            rows.append(row)

        await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_=f"'{sheet_name}'!A1",
            values=rows,
            value_input_option=ValueInputOption.USER_ENTERED,
        )

        logger.debug(f"Populated {len(leads)} leads in sheet '{sheet_name}'")

    @staticmethod
    def _truncate_text(text: str | None, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
