"""
Google Sheets export functionality for Personalization Finalizer Agent.

Exports email samples to Google Sheets for human review with summary,
tier breakdowns, and sample emails from each tier.
"""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from src.agents.personalization_finalizer.reports import PersonalizationReport
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


class EmailSamplesExporter:
    """Exports email samples to Google Sheets for review."""

    # Column headers for email samples export
    EMAIL_COLUMNS = [
        "Lead Name",
        "Company",
        "Title",
        "Lead Tier",
        "Subject Line",
        "Opening Line",
        "Body",
        "CTA",
        "Framework",
        "Personalization Level",
        "Quality Score",
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

    async def export_email_samples(
        self,
        report: PersonalizationReport,
        tier_a_samples: list[dict[str, Any]],
        tier_b_samples: list[dict[str, Any]],
        tier_c_samples: list[dict[str, Any]],
    ) -> dict[str, str]:
        """
        Export email samples to a new Google Spreadsheet.

        Creates a spreadsheet with:
        - Summary sheet with personalization report
        - Tier A email samples sheet
        - Tier B email samples sheet
        - Tier C email samples sheet

        Args:
            report: Personalization report for the campaign.
            tier_a_samples: List of Tier A email sample dictionaries.
            tier_b_samples: List of Tier B email sample dictionaries.
            tier_c_samples: List of Tier C email sample dictionaries.

        Returns:
            Dictionary with spreadsheet_id and spreadsheet_url.
        """
        client = await self._get_client()
        current_date = datetime.now(UTC).strftime("%Y-%m-%d")
        title = f"{report.niche_name} - Email Samples - {current_date}"

        try:
            # Create spreadsheet with all sheets
            spreadsheet = await client.create_spreadsheet(
                title=title,
                sheets=[
                    "Summary",
                    "Tier A Emails",
                    "Tier B Emails",
                    "Tier C Emails",
                ],
            )

            spreadsheet_id = spreadsheet.spreadsheet_id
            if not spreadsheet_id:
                raise SheetsExportError("Failed to get spreadsheet ID after creation")

            logger.info(f"Created spreadsheet: {spreadsheet_id}")

            # Populate sheets
            await self._populate_summary_sheet(client, spreadsheet_id, report)
            await self._populate_emails_sheet(
                client, spreadsheet_id, "Tier A Emails", tier_a_samples
            )
            await self._populate_emails_sheet(
                client, spreadsheet_id, "Tier B Emails", tier_b_samples
            )
            await self._populate_emails_sheet(
                client, spreadsheet_id, "Tier C Emails", tier_c_samples
            )

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            total_samples = len(tier_a_samples) + len(tier_b_samples) + len(tier_c_samples)
            logger.info(
                f"Exported {total_samples} email samples to Google Sheets: {spreadsheet_url}"
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
        report: PersonalizationReport,
    ) -> None:
        """Populate the Summary sheet with personalization report data."""
        summary_data: list[list[Any]] = [
            ["Phase 4 Personalization Summary"],
            [""],
            ["Campaign", report.campaign_name],
            ["Niche", report.niche_name],
            ["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M UTC")],
            [""],
            ["Email Generation Overview"],
            ["Total Leads", report.total_leads],
            ["Emails Generated", report.total_emails_generated],
            ["Generation Rate", f"{report.generation_rate}%"],
            [""],
            ["Quality Metrics"],
            ["Average Quality Score", report.avg_quality_score],
            ["Min Quality Score", report.min_quality_score],
            ["Max Quality Score", report.max_quality_score],
            ["Data Quality Score", f"{report.data_quality_score:.0%}"],
            ["Total Regenerations", report.total_regenerations],
            [""],
            ["Quality Distribution"],
            ["Excellent (80-100)", report.quality_distribution.excellent],
            ["Good (60-79)", report.quality_distribution.good],
            ["Acceptable (40-59)", report.quality_distribution.acceptable],
            ["Needs Improvement (0-39)", report.quality_distribution.needs_improvement],
            [""],
            ["Tier Breakdown"],
        ]

        # Add tier breakdowns
        for tier_name in ["A", "B", "C"]:
            tier = report.tier_breakdowns.get(tier_name)
            if tier:
                summary_data.extend(
                    [
                        [f"Tier {tier_name}"],
                        ["  Total Leads", tier.total_leads],
                        ["  Emails Generated", tier.emails_generated],
                        ["  Avg Quality Score", round(tier.avg_quality_score, 1)],
                        ["  Quality Pass Rate", f"{tier.pass_rate}%"],
                        ["  Regenerations", tier.regeneration_count],
                    ]
                )

        summary_data.extend(
            [
                [""],
                ["Framework Usage"],
            ]
        )

        # Add framework usage
        for framework, usage in report.framework_usage.items():
            summary_data.append(
                [framework.upper(), usage.count, f"Avg: {usage.avg_quality_score:.1f}"]
            )

        summary_data.extend(
            [
                [""],
                ["Personalization Levels"],
            ]
        )

        # Add personalization levels
        for level, stats in report.personalization_levels.items():
            summary_data.append([level, stats.count, f"Avg: {stats.avg_quality_score:.1f}"])

        await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_="Summary!A1",
            values=summary_data,
            value_input_option=ValueInputOption.USER_ENTERED,
        )

    async def _populate_emails_sheet(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
        emails: list[dict[str, Any]],
    ) -> None:
        """Populate an email samples sheet with email data."""
        if not emails:
            # Just add headers if no emails
            await client.update_values(
                spreadsheet_id=spreadsheet_id,
                range_=f"'{sheet_name}'!A1",
                values=[self.EMAIL_COLUMNS],
                value_input_option=ValueInputOption.USER_ENTERED,
            )
            return

        # Build data rows
        rows: list[list[Any]] = [list(self.EMAIL_COLUMNS)]
        for email in emails:
            lead_name = f"{email.get('first_name', '')} {email.get('last_name', '')}".strip()
            row = [
                lead_name or "Unknown",
                email.get("company_name", ""),
                email.get("title", ""),
                email.get("lead_tier", ""),
                email.get("subject_line", ""),
                self._truncate_text(email.get("opening_line", ""), 200),
                self._truncate_text(email.get("body", ""), 1000),
                self._truncate_text(email.get("cta", ""), 200),
                email.get("framework_used", ""),
                email.get("personalization_level", ""),
                email.get("quality_score", 0),
            ]
            rows.append(row)

        await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_=f"'{sheet_name}'!A1",
            values=rows,
            value_input_option=ValueInputOption.USER_ENTERED,
        )

        logger.debug(f"Populated {len(emails)} emails in sheet '{sheet_name}'")

    @staticmethod
    def _truncate_text(text: str | None, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
