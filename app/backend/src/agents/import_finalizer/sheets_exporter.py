"""
Google Sheets exporter for Import Finalizer Agent.

Exports lead lists to Google Sheets for human review.
Reuses the existing GoogleSheetsClient with domain-wide delegation (LEARN-006).
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.import_finalizer.schemas import (
    ImportSummary,
    LeadRow,
    SheetExportResult,
)
from src.integrations.google_sheets import (
    GoogleSheetsAPIError,
    GoogleSheetsAuthError,
    GoogleSheetsClient,
)

logger = logging.getLogger(__name__)


class SheetsExporter:
    """
    Export leads to Google Sheets for review.

    Uses the existing GoogleSheetsClient with domain-wide delegation
    as documented in LEARN-006.

    Attributes:
        client: GoogleSheetsClient instance.
        delegated_user: Email of user to impersonate.
    """

    # Column headers for lead sheets
    LEAD_HEADERS_BASIC = [
        "First Name",
        "Last Name",
        "Email",
        "Job Title",
        "Company",
        "Domain",
        "Score",
        "Tier",
    ]

    LEAD_HEADERS_FULL = [
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

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_path: str | None = None,
        delegated_user: str | None = None,
    ) -> None:
        """
        Initialize the sheets exporter.

        Uses LEARN-006 pattern: domain-wide delegation for Google API quota.

        Args:
            credentials_json: Service account credentials dict.
            credentials_path: Path to service account JSON file.
            delegated_user: Email to impersonate (from GOOGLE_DELEGATED_USER).
        """
        # Load credentials from file if not provided
        if not credentials_json and credentials_path:
            with open(credentials_path) as f:
                credentials_json = json.load(f)

        # Load from environment if not provided
        if not credentials_json:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and Path(creds_path).exists():
                with open(creds_path) as f:
                    credentials_json = json.load(f)

        # Get delegated user from environment if not provided (LEARN-006)
        self.delegated_user = delegated_user or os.getenv("GOOGLE_DELEGATED_USER")

        if not self.delegated_user:
            logger.warning(
                "GOOGLE_DELEGATED_USER not set - domain-wide delegation will not work. "
                "See LEARN-006 in SELF-HEALING.md"
            )

        self._credentials_json = credentials_json
        self._client: GoogleSheetsClient | None = None

    async def _get_client(self) -> GoogleSheetsClient:
        """
        Get or create authenticated GoogleSheetsClient.

        Uses domain-wide delegation as per LEARN-006.
        """
        if self._client is None:
            self._client = GoogleSheetsClient(
                credentials_json=self._credentials_json,
                delegated_user=self.delegated_user,
            )
            await self._client.authenticate()
        return self._client

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def export_leads(
        self,
        campaign_name: str,
        niche_name: str,
        summary: ImportSummary,
        tier_a_leads: list[dict[str, Any]],
        tier_b_leads: list[dict[str, Any]],
        all_leads: list[dict[str, Any]],
    ) -> SheetExportResult:
        """
        Export leads to a new Google Spreadsheet.

        Creates a spreadsheet with:
        - Summary sheet with campaign statistics
        - Tier A leads sheet
        - Tier B leads sheet
        - All leads sheet

        Args:
            campaign_name: Name of the campaign.
            niche_name: Name of the target niche.
            summary: ImportSummary with statistics.
            tier_a_leads: List of Tier A lead dictionaries.
            tier_b_leads: List of Tier B lead dictionaries.
            all_leads: List of all lead dictionaries.

        Returns:
            SheetExportResult with spreadsheet URL and status.
        """
        try:
            client = await self._get_client()
        except (GoogleSheetsAuthError, GoogleSheetsAPIError) as e:
            logger.error(f"Failed to authenticate Google Sheets: {e}")
            return SheetExportResult(
                success=False,
                error_message=f"Authentication failed: {e}",
            )

        # Create spreadsheet
        date_str = datetime.now().strftime("%Y-%m-%d")
        spreadsheet_title = f"{niche_name} - Lead List - {date_str}"

        try:
            # Create the spreadsheet with summary sheet
            spreadsheet = await client.create_spreadsheet(
                title=spreadsheet_title,
                sheets=["Summary", "Tier A Leads", "Tier B Leads", "All Leads"],
            )

            spreadsheet_id = spreadsheet.spreadsheet_id
            if not spreadsheet_id:
                raise GoogleSheetsAPIError("Spreadsheet created but no ID returned")

            logger.info(f"Created spreadsheet: {spreadsheet_id}")

            # Write summary sheet
            await self._write_summary_sheet(client, spreadsheet_id, summary)

            # Write tier A leads
            tier_a_rows = await self._write_leads_sheet(
                client,
                spreadsheet_id,
                "Tier A Leads",
                tier_a_leads,
            )

            # Write tier B leads
            tier_b_rows = await self._write_leads_sheet(
                client,
                spreadsheet_id,
                "Tier B Leads",
                tier_b_leads,
            )

            # Write all leads
            all_rows = await self._write_leads_sheet(
                client,
                spreadsheet_id,
                "All Leads",
                all_leads,
                include_size_location=True,
            )

            total_rows = tier_a_rows + tier_b_rows + all_rows
            spreadsheet_url = spreadsheet.spreadsheet_url or (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            )

            logger.info(f"Exported {total_rows} total rows to {spreadsheet_url}")

            return SheetExportResult(
                success=True,
                spreadsheet_id=spreadsheet_id,
                spreadsheet_url=spreadsheet_url,
                sheet_names=["Summary", "Tier A Leads", "Tier B Leads", "All Leads"],
                total_rows_written=total_rows,
            )

        except GoogleSheetsAPIError as e:
            logger.error(f"Google Sheets API error: {e}")
            return SheetExportResult(
                success=False,
                error_message=f"API error: {e}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during export: {e}")
            return SheetExportResult(
                success=False,
                error_message=f"Export failed: {e}",
            )

    async def _write_summary_sheet(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        summary: ImportSummary,
    ) -> None:
        """Write the summary sheet with campaign statistics."""
        values: list[list[Any]] = [
            ["Campaign Summary"],
            [],
            ["Campaign", summary.campaign_name],
            ["Niche", summary.niche_name],
            ["Generated", summary.generated_at.strftime("%Y-%m-%d %H:%M")],
            [],
            ["Lead Scraping"],
            ["Target Leads", summary.scraping.target_leads],
            ["Total Scraped", summary.scraping.total_scraped],
            ["Scraping Cost", f"${summary.scraping.scraping_cost:.2f}"],
            ["Cost per Lead", f"${summary.scraping.cost_per_lead:.4f}"],
            [],
            ["Data Validation"],
            ["Valid Leads", summary.validation.total_valid],
            ["Invalid Leads", summary.validation.total_invalid],
            ["Validity Rate", f"{summary.validation.validity_rate:.1%}"],
            [],
            ["Deduplication"],
            ["Within-Campaign Duplicates", summary.deduplication.within_campaign_dupes],
            ["Cross-Campaign Duplicates", summary.deduplication.cross_campaign_dupes],
            ["Available After Dedup", summary.deduplication.available_after_dedup],
            [],
            ["Lead Scoring"],
            ["Total Scored", summary.scoring.total_scored],
            ["Average Score", f"{summary.scoring.avg_score:.1f}"],
            [],
            ["Tier Distribution"],
            ["Tier A (80+)", summary.scoring.tier_breakdown.tier_a],
            ["Tier B (60-79)", summary.scoring.tier_breakdown.tier_b],
            ["Tier C (40-59)", summary.scoring.tier_breakdown.tier_c],
            [],
            ["TOTAL AVAILABLE", summary.total_available],
        ]

        await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_="Summary!A1",
            values=values,
        )

    async def _write_leads_sheet(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
        leads: list[dict[str, Any]],
        include_size_location: bool = False,
    ) -> int:
        """
        Write leads to a sheet.

        Args:
            client: GoogleSheetsClient instance.
            spreadsheet_id: Spreadsheet ID.
            sheet_name: Name of the sheet.
            leads: List of lead dictionaries.
            include_size_location: Include company size and location columns.

        Returns:
            Number of rows written (including header).
        """
        if not leads:
            # Write just headers for empty sheets
            headers = self.LEAD_HEADERS_FULL if include_size_location else self.LEAD_HEADERS_BASIC
            await client.update_values(
                spreadsheet_id=spreadsheet_id,
                range_=f"'{sheet_name}'!A1",
                values=[headers],
            )
            return 1

        # Convert leads to rows
        headers = self.LEAD_HEADERS_FULL if include_size_location else self.LEAD_HEADERS_BASIC
        rows = [headers]

        for lead_data in leads:
            lead = LeadRow.from_dict(lead_data)
            rows.append(lead.to_row(include_size_location=include_size_location))

        # Write in batches if needed (Sheets API has limits)
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            start_row = i + 1  # 1-indexed
            await client.update_values(
                spreadsheet_id=spreadsheet_id,
                range_=f"'{sheet_name}'!A{start_row}",
                values=batch,
            )

        return len(rows)


# =============================================================================
# CSV Fallback
# =============================================================================


def export_leads_to_csv(
    output_path: str,
    summary: ImportSummary,
    leads: list[dict[str, Any]],
) -> SheetExportResult:
    """
    Export leads to CSV file as fallback when Google Sheets fails.

    Args:
        output_path: Path to output CSV file.
        summary: ImportSummary for header info.
        leads: List of lead dictionaries.

    Returns:
        SheetExportResult with file path.
    """
    try:
        # Ensure directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write headers
            headers = [
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
            writer.writerow(headers)

            # Write leads
            for lead_data in leads:
                lead = LeadRow.from_dict(lead_data)
                writer.writerow(lead.to_row(include_size_location=True))

        logger.info(f"Exported {len(leads)} leads to CSV: {output_path}")

        return SheetExportResult(
            success=True,
            spreadsheet_url=f"file://{output_path}",
            total_rows_written=len(leads) + 1,  # +1 for header
        )

    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        return SheetExportResult(
            success=False,
            error_message=f"CSV export failed: {e}",
        )
