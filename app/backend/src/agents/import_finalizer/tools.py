"""
Claude Agent SDK tools for Import Finalizer Agent.

Implements MCP tools following SDK patterns from SDK_PATTERNS.md.
Tools are pure functions decorated with @tool from claude_agent_sdk.

LEARN-003: Create clients inside @tool, no dependency injection.
"""

import json
import logging
import os
import tempfile
from typing import Any

from claude_agent_sdk import tool

from src.agents.import_finalizer.schemas import (
    CampaignData,
    NicheData,
)
from src.agents.import_finalizer.sheets_exporter import (
    SheetsExporter,
    export_leads_to_csv,
)
from src.agents.import_finalizer.summary_builder import (
    build_full_summary,
    format_summary_for_display,
)

logger = logging.getLogger(__name__)


# Module-level storage for data passed from agent
# Tools are self-contained per LEARN-003 - no DI allowed
_campaign_data: dict[str, Any] = {}
_niche_data: dict[str, Any] | None = None
_tier_a_leads: list[dict[str, Any]] = []
_tier_b_leads: list[dict[str, Any]] = []
_all_leads: list[dict[str, Any]] = []


def set_campaign_data(data: dict[str, Any]) -> None:
    """Set campaign data for tools to use."""
    global _campaign_data
    _campaign_data = data


def set_niche_data(data: dict[str, Any] | None) -> None:
    """Set niche data for tools to use."""
    global _niche_data
    _niche_data = data


def set_leads_data(
    tier_a: list[dict[str, Any]],
    tier_b: list[dict[str, Any]],
    all_leads: list[dict[str, Any]],
) -> None:
    """Set leads data for tools to use."""
    global _tier_a_leads, _tier_b_leads, _all_leads
    _tier_a_leads = tier_a
    _tier_b_leads = tier_b
    _all_leads = all_leads


# =============================================================================
# Tool: compile_summary
# =============================================================================


@tool(  # type: ignore[misc]
    name="compile_summary",
    description="Compile comprehensive import summary from campaign data",
    input_schema={
        "use_stored_data": bool,
    },
)
async def compile_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Compile comprehensive import summary from campaign data.

    This tool gathers all statistics from the lead import process
    and generates a structured summary report.

    Args:
        args: Tool arguments (use_stored_data: bool).

    Returns:
        Tool result with summary data.
        Format: {"content": [...], "is_error": bool}
    """
    try:
        campaign = CampaignData.from_dict(_campaign_data)
        niche = NicheData.from_dict(_niche_data) if _niche_data else None

        summary = build_full_summary(campaign, niche)

        # Format for display
        display_text = format_summary_for_display(summary)

        logger.info(
            f"[compile_summary] Generated summary for campaign {campaign.id}: "
            f"{summary.total_available} leads available"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "success",
                            "summary": summary.to_dict(),
                            "display": display_text,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except Exception as e:
        logger.error(f"[compile_summary] Failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "error",
                            "error": str(e),
                        }
                    ),
                }
            ],
            "is_error": True,
        }


# =============================================================================
# Tool: export_to_sheets
# =============================================================================


@tool(  # type: ignore[misc]
    name="export_to_sheets",
    description="Export leads to Google Sheets for review (falls back to CSV)",
    input_schema={
        "fallback_to_csv": bool,
    },
)
async def export_to_sheets_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Export leads to Google Sheets for review.

    Creates a spreadsheet with summary, Tier A, Tier B, and All Leads sheets.
    Uses domain-wide delegation per LEARN-006.

    Falls back to CSV export if Google Sheets fails.

    Args:
        args: Tool arguments (fallback_to_csv: bool).

    Returns:
        Tool result with spreadsheet URL.
        Format: {"content": [...], "is_error": bool}
    """
    try:
        fallback_to_csv = args.get("fallback_to_csv", True)

        # Get data from module storage
        campaign = CampaignData.from_dict(_campaign_data)
        niche = NicheData.from_dict(_niche_data) if _niche_data else None
        campaign_name = campaign.name
        niche_name = niche.name if niche else "Unknown"

        # Build summary from campaign data
        summary = build_full_summary(campaign, niche)

        # Try Google Sheets export
        exporter = SheetsExporter()
        try:
            result = await exporter.export_leads(
                campaign_name=campaign_name,
                niche_name=niche_name,
                summary=summary,
                tier_a_leads=_tier_a_leads,
                tier_b_leads=_tier_b_leads,
                all_leads=_all_leads,
            )
        finally:
            await exporter.close()

        if result.success:
            logger.info(f"[export_to_sheets] Exported to Google Sheets: {result.spreadsheet_url}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "status": "success",
                                "export_type": "google_sheets",
                                "spreadsheet_id": result.spreadsheet_id,
                                "spreadsheet_url": result.spreadsheet_url,
                                "sheet_names": result.sheet_names,
                                "total_rows": result.total_rows_written,
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

        # Fallback to CSV
        if fallback_to_csv:
            logger.warning(
                f"[export_to_sheets] Google Sheets failed, falling back to CSV: "
                f"{result.error_message}"
            )

            campaign_id = campaign.id
            csv_path = os.path.join(tempfile.gettempdir(), "exports", f"{campaign_id}_leads.csv")
            csv_result = export_leads_to_csv(csv_path, summary, _all_leads)

            if csv_result.success:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "status": "success",
                                    "export_type": "csv",
                                    "file_path": csv_path,
                                    "total_rows": csv_result.total_rows_written,
                                    "sheets_error": result.error_message,
                                }
                            ),
                        }
                    ],
                    "is_error": False,
                }

        # Both failed
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "error",
                            "error": result.error_message,
                        }
                    ),
                }
            ],
            "is_error": True,
        }

    except Exception as e:
        logger.error(f"[export_to_sheets] Failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "error",
                            "error": str(e),
                        }
                    ),
                }
            ],
            "is_error": True,
        }


# =============================================================================
# Tool: get_lead_stats
# =============================================================================


@tool(  # type: ignore[misc]
    name="get_lead_stats",
    description="Calculate statistics for the stored leads",
    input_schema={
        "tier_filter": str,
    },
)
async def get_lead_stats_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate statistics for a list of leads.

    Args:
        args: Tool arguments (tier_filter: "all", "tier_a", or "tier_b").

    Returns:
        Tool result with lead statistics.
    """
    try:
        tier_filter = args.get("tier_filter", "all")

        # Select leads based on filter
        if tier_filter == "tier_a":
            leads = _tier_a_leads
        elif tier_filter == "tier_b":
            leads = _tier_b_leads
        else:
            leads = _all_leads

        total = len(leads)

        if total == 0:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "status": "success",
                                "total": 0,
                                "with_email": 0,
                                "with_phone": 0,
                                "tier_breakdown": {},
                                "avg_score": 0.0,
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

        # Count leads with email/phone
        with_email = sum(1 for lead_item in leads if lead_item.get("email"))
        with_phone = sum(1 for lead_item in leads if lead_item.get("phone"))

        # Tier breakdown
        tier_counts: dict[str, int] = {}
        total_score = 0
        scored_count = 0

        for lead in leads:
            tier = lead.get("lead_tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

            score = lead.get("lead_score")
            if score is not None:
                total_score += score
                scored_count += 1

        avg_score = total_score / scored_count if scored_count > 0 else 0.0

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "success",
                            "total": total,
                            "with_email": with_email,
                            "with_phone": with_phone,
                            "email_rate": with_email / total if total > 0 else 0,
                            "tier_breakdown": tier_counts,
                            "avg_score": round(avg_score, 2),
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except Exception as e:
        logger.error(f"[get_lead_stats] Failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "error",
                            "error": str(e),
                        }
                    ),
                }
            ],
            "is_error": True,
        }


# =============================================================================
# Tool: format_notification
# =============================================================================


@tool(  # type: ignore[misc]
    name="format_notification",
    description="Format a notification message for Slack or other channels",
    input_schema={
        "sheet_url": str,
    },
)
async def format_notification_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Format a notification message for Slack or other channels.

    Args:
        args: Tool arguments (sheet_url: optional URL to spreadsheet).

    Returns:
        Tool result with formatted notification.
    """
    try:
        sheet_url = args.get("sheet_url")

        # Get data from module storage
        campaign = CampaignData.from_dict(_campaign_data)
        niche = NicheData.from_dict(_niche_data) if _niche_data else None

        campaign_name = campaign.name
        niche_name = niche.name if niche else "Unknown"
        total_available = campaign.total_leads_available
        tier_a = campaign.leads_tier_a
        tier_b = campaign.leads_tier_b
        avg_score = campaign.avg_lead_score

        # Build Slack blocks
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Lead List Ready!",
                    "emoji": True,
                },
            },
        ]

        if sheet_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*<{sheet_url}|Click here to view your leads>*",
                    },
                }
            )

        blocks.append({"type": "divider"})

        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Campaign:*\n{campaign_name}"},
                    {"type": "mrkdwn", "text": f"*Niche:*\n{niche_name}"},
                    {"type": "mrkdwn", "text": f"*Total Leads:*\n{total_available:,}"},
                    {"type": "mrkdwn", "text": f"*Tier A:*\n{tier_a:,}"},
                    {"type": "mrkdwn", "text": f"*Tier B:*\n{tier_b:,}"},
                    {"type": "mrkdwn", "text": f"*Avg Score:*\n{avg_score:.1f}"},
                ],
            }
        )

        blocks.append({"type": "divider"})

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Phase 2 complete. Proceeding to Phase 3 (Email Verification).",
                    }
                ],
            }
        )

        # Plain text version
        plain_text = (
            f"Lead List Ready for {campaign_name}\n\n"
            f"Niche: {niche_name}\n"
            f"Total Leads: {total_available:,}\n"
            f"Tier A: {tier_a:,}\n"
            f"Tier B: {tier_b:,}\n"
            f"Avg Score: {avg_score:.1f}\n"
        )

        if sheet_url:
            plain_text += f"\nView leads: {sheet_url}"

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "success",
                            "slack_blocks": blocks,
                            "plain_text": plain_text,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except Exception as e:
        logger.error(f"[format_notification] Failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "error",
                            "error": str(e),
                        }
                    ),
                }
            ],
            "is_error": True,
        }
