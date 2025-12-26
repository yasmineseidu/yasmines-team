"""
Claude Agent SDK MCP tools for Verification Finalizer Agent.

Provides tools for:
- Compiling verification summary statistics
- Generating quality reports
- Exporting leads to Google Sheets
- Sending approval notifications via Telegram
"""

import json
import logging
import os
from typing import Any

from claude_agent_sdk import tool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.verification_finalizer.exports import SheetsExportError, VerifiedLeadsExporter
from src.agents.verification_finalizer.reports import (
    CostSummary,
    QualityReport,
    QualityReportGenerator,
    TierBreakdown,
    VerificationSummary,
)
from src.database.connection import get_session
from src.database.repositories.campaign_repository import CampaignRepository
from src.database.repositories.lead_repository import LeadRepository
from src.integrations.telegram import TelegramClient, TelegramError

logger = logging.getLogger(__name__)


# ============================================================================
# Database Query Tools
# ============================================================================


@tool(  # type: ignore[misc]
    name="get_campaign_verification_stats",
    description="Get verification and enrichment statistics for a campaign",
    input_schema={
        "campaign_id": str,
    },
)
async def get_campaign_verification_stats(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get comprehensive verification statistics for a campaign.

    Queries the database for:
    - Campaign and niche details
    - Email verification status counts
    - Lead tier breakdown with enrichment metrics

    Args:
        args: Dictionary with campaign_id.

    Returns:
        Dictionary with statistics or error.
    """
    campaign_id = args.get("campaign_id")
    if not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: campaign_id is required"}],
            "is_error": True,
        }

    try:
        async with get_session() as session:
            campaign_repo = CampaignRepository(session)

            # Get campaign with niche
            campaign_data = await campaign_repo.get_campaign_with_niche(campaign_id)
            if not campaign_data:
                return {
                    "content": [{"type": "text", "text": f"Campaign {campaign_id} not found"}],
                    "is_error": True,
                }

            # Get email status counts
            email_stats = await _get_email_stats(session, campaign_id)

            # Get tier statistics
            tier_stats = await _get_tier_stats(session, campaign_id)

            result = {
                "campaign": campaign_data["campaign"],
                "niche": campaign_data["niche"],
                "email_stats": email_stats,
                "tier_stats": tier_stats,
            }

            return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except Exception as e:
        logger.error(f"Error getting verification stats: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e!s}"}],
            "is_error": True,
        }


async def _get_email_stats(session: AsyncSession, campaign_id: str) -> list[dict[str, Any]]:
    """Get email verification status counts."""
    query = text(
        """
        SELECT
            email_status,
            COUNT(*) as count,
            AVG(lead_score) as avg_score
        FROM leads
        WHERE campaign_id = :campaign_id
          AND status NOT IN ('duplicate', 'invalid', 'cross_campaign_duplicate')
        GROUP BY email_status
        """
    )
    result = await session.execute(query, {"campaign_id": campaign_id})
    rows = result.fetchall()
    return [
        {
            "email_status": row[0],
            "count": row[1],
            "avg_score": float(row[2]) if row[2] else 0,
        }
        for row in rows
    ]


async def _get_tier_stats(session: AsyncSession, campaign_id: str) -> list[dict[str, Any]]:
    """Get lead statistics by tier."""
    query = text(
        """
        SELECT
            lead_tier,
            COUNT(*) as total,
            COUNT(CASE WHEN email_status = 'valid' THEN 1 END) as valid_email,
            COUNT(CASE WHEN company_description IS NOT NULL THEN 1 END) as has_description,
            COUNT(CASE WHEN status = 'enriched' THEN 1 END) as enriched_count,
            AVG(lead_score) as avg_score
        FROM leads
        WHERE campaign_id = :campaign_id
          AND status NOT IN ('duplicate', 'invalid', 'cross_campaign_duplicate')
        GROUP BY lead_tier
        ORDER BY lead_tier
        """
    )
    result = await session.execute(query, {"campaign_id": campaign_id})
    rows = result.fetchall()
    return [
        {
            "lead_tier": row[0] or "Unknown",
            "total": row[1],
            "valid_email": row[2],
            "has_description": row[3],
            "enriched_count": row[4],
            "avg_score": float(row[5]) if row[5] else 0,
        }
        for row in rows
    ]


# ============================================================================
# Report Generation Tool
# ============================================================================


@tool(  # type: ignore[misc]
    name="generate_quality_report",
    description="Generate a comprehensive quality report for the campaign verification phase",
    input_schema={
        "campaign_id": str,
        "campaign_data": dict,
        "niche_data": dict,
        "email_stats": list,
        "tier_stats": list,
    },
)
async def generate_quality_report(args: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a comprehensive quality report from verification data.

    Args:
        args: Dictionary with campaign data, niche data, email stats, and tier stats.

    Returns:
        Dictionary with quality report or error.
    """
    try:
        campaign_data = args.get("campaign_data", {})
        niche_data = args.get("niche_data", {})
        email_stats = args.get("email_stats", [])
        tier_stats = args.get("tier_stats", [])

        generator = QualityReportGenerator(
            campaign_data=campaign_data,
            niche_data=niche_data,
            email_stats=email_stats,
            tier_stats=tier_stats,
        )

        report = generator.generate()

        return {
            "content": [{"type": "text", "text": json.dumps(report.to_dict())}],
        }

    except Exception as e:
        logger.error(f"Error generating quality report: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e!s}"}],
            "is_error": True,
        }


# ============================================================================
# Google Sheets Export Tool
# ============================================================================


@tool(  # type: ignore[misc]
    name="export_leads_to_sheets",
    description="Export verified leads to Google Sheets for human review",
    input_schema={
        "campaign_id": str,
        "report_json": str,
    },
)
async def export_leads_to_sheets(args: dict[str, Any]) -> dict[str, Any]:
    """
    Export verified leads to Google Sheets.

    Creates a spreadsheet with summary and lead data organized by tier.

    Args:
        args: Dictionary with campaign_id and report_json.

    Returns:
        Dictionary with spreadsheet_id and spreadsheet_url.
    """
    campaign_id = args.get("campaign_id")
    report_json = args.get("report_json")

    if not campaign_id or not report_json:
        return {
            "content": [{"type": "text", "text": "Error: campaign_id and report_json required"}],
            "is_error": True,
        }

    try:
        # Parse report JSON
        report_data = json.loads(report_json)
        report = _reconstruct_report_from_dict(report_data)

        # Get leads from database
        tier_a_leads: list[dict[str, Any]] = []
        tier_b_leads: list[dict[str, Any]] = []
        all_ready_leads: list[dict[str, Any]] = []

        async with get_session() as session:
            lead_repo = LeadRepository(session)

            # Get Tier A leads with valid email
            tier_a_models = await lead_repo.get_campaign_leads(
                campaign_id=campaign_id,
                tier="A",
                has_verified_email=True,
                limit=10000,
            )
            tier_a_leads = [_lead_model_to_dict(lead) for lead in tier_a_models]

            # Get Tier B leads with valid email
            tier_b_models = await lead_repo.get_campaign_leads(
                campaign_id=campaign_id,
                tier="B",
                has_verified_email=True,
                limit=10000,
            )
            tier_b_leads = [_lead_model_to_dict(lead) for lead in tier_b_models]

            # Get all ready leads
            all_ready_models = await lead_repo.get_campaign_leads(
                campaign_id=campaign_id,
                has_verified_email=True,
                limit=50000,
            )
            all_ready_leads = [_lead_model_to_dict(lead) for lead in all_ready_models]

        # Export to Google Sheets
        exporter = VerifiedLeadsExporter()
        try:
            result = await exporter.export_verified_leads(
                report=report,
                tier_a_leads=tier_a_leads,
                tier_b_leads=tier_b_leads,
                all_ready_leads=all_ready_leads,
            )

            return {
                "content": [{"type": "text", "text": json.dumps(result)}],
            }
        finally:
            await exporter.close()

    except SheetsExportError as e:
        logger.error(f"Sheets export error: {e.message}")
        return {
            "content": [{"type": "text", "text": f"Export error: {e.message}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Error exporting to sheets: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e!s}"}],
            "is_error": True,
        }


def _lead_model_to_dict(lead: Any) -> dict[str, Any]:
    """Convert LeadModel to dictionary."""
    return {
        "id": str(lead.id),
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "title": lead.title,
        "company_name": lead.company_name,
        "company_domain": lead.company_domain,
        "company_description": lead.company_description,
        "lead_score": lead.lead_score,
        "lead_tier": lead.lead_tier,
        "email_status": lead.email_status,
    }


def _reconstruct_report_from_dict(data: dict[str, Any]) -> QualityReport:
    """Reconstruct QualityReport from dictionary."""
    report = QualityReport(
        campaign_id=data.get("campaign_id", ""),
        campaign_name=data.get("campaign_name", ""),
        niche_name=data.get("niche_name", ""),
        total_leads=data.get("total_leads", 0),
        total_ready=data.get("total_ready", 0),
    )

    # Reconstruct verification summary
    vs_data = data.get("verification_summary", {})
    report.verification_summary = VerificationSummary(
        emails_found=vs_data.get("emails_found", 0),
        emails_verified=vs_data.get("emails_verified", 0),
        emails_valid=vs_data.get("emails_valid", 0),
        emails_invalid=vs_data.get("emails_invalid", 0),
        emails_risky=vs_data.get("emails_risky", 0),
        emails_catchall=vs_data.get("emails_catchall", 0),
    )

    # Reconstruct tier breakdowns
    for tier, tb_data in data.get("tier_breakdowns", {}).items():
        report.tier_breakdowns[tier] = TierBreakdown(
            tier=tier,
            total=tb_data.get("total", 0),
            verified=tb_data.get("verified", 0),
            enriched=tb_data.get("enriched", 0),
            ready=tb_data.get("ready", 0),
            avg_score=tb_data.get("avg_score", 0.0),
            avg_enrichment_cost=tb_data.get("avg_enrichment_cost", 0.0),
        )

    # Reconstruct cost summary
    cs_data = data.get("cost_summary", {})
    report.cost_summary = CostSummary(
        scraping_cost=cs_data.get("scraping_cost", 0.0),
        enrichment_cost=cs_data.get("enrichment_cost", 0.0),
        verification_cost=cs_data.get("verification_cost", 0.0),
    )

    return report


# ============================================================================
# Notification Tool
# ============================================================================


@tool(  # type: ignore[misc]
    name="send_approval_notification",
    description="Send approval notification via Telegram with campaign summary and approval buttons",
    input_schema={
        "campaign_id": str,
        "campaign_name": str,
        "total_ready": int,
        "tier_a_ready": int,
        "tier_b_ready": int,
        "sheets_url": str,
        "total_cost": float,
    },
)
async def send_approval_notification(args: dict[str, Any]) -> dict[str, Any]:
    """
    Send approval notification via Telegram.

    Sends a message with campaign summary and buttons for approval actions.

    Args:
        args: Dictionary with campaign details and sheets URL.

    Returns:
        Dictionary with notification status.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_APPROVALS_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured, skipping notification")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "sent": False,
                            "reason": "Telegram credentials not configured",
                        }
                    ),
                }
            ],
        }

    try:
        client = TelegramClient(bot_token=bot_token)

        message = _build_notification_message(
            campaign_name=args.get("campaign_name", "Unknown"),
            total_ready=args.get("total_ready", 0),
            tier_a_ready=args.get("tier_a_ready", 0),
            tier_b_ready=args.get("tier_b_ready", 0),
            sheets_url=args.get("sheets_url", ""),
            total_cost=args.get("total_cost", 0.0),
        )

        # Send message with inline keyboard for approval
        keyboard = _build_approval_keyboard(args.get("campaign_id", ""))

        result = await client.send_message(
            chat_id=int(chat_id),
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "sent": True,
                            "message_id": result.message_id,
                            "chat_id": chat_id,
                        }
                    ),
                }
            ],
        }

    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
        return {
            "content": [{"type": "text", "text": f"Telegram error: {e!s}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e!s}"}],
            "is_error": True,
        }


def _build_notification_message(
    campaign_name: str,
    total_ready: int,
    tier_a_ready: int,
    tier_b_ready: int,
    sheets_url: str,
    total_cost: float,
) -> str:
    """Build Telegram notification message."""
    return f"""<b>Verified Leads Ready for Personalization</b>

<b>Campaign:</b> {campaign_name}

<b>Lead Summary:</b>
• Total Ready: {total_ready:,}
• Tier A: {tier_a_ready:,}
• Tier B: {tier_b_ready:,}
• Total Cost: ${total_cost:,.2f}

<a href="{sheets_url}">View Verified Leads in Google Sheets</a>

Please review and approve to proceed with personalization."""


def _build_approval_keyboard(campaign_id: str) -> dict[str, Any]:
    """Build inline keyboard with approval buttons."""
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Start Full Personalization",
                    "callback_data": f"approve_full_{campaign_id}",
                },
            ],
            [
                {
                    "text": "Tier A Only",
                    "callback_data": f"approve_tier_a_{campaign_id}",
                },
            ],
            [
                {
                    "text": "Need More Data",
                    "callback_data": f"more_data_{campaign_id}",
                },
                {
                    "text": "Reject",
                    "callback_data": f"reject_{campaign_id}",
                },
            ],
        ]
    }


# ============================================================================
# Database Update Tool
# ============================================================================


@tool(  # type: ignore[misc]
    name="update_campaign_verification_complete",
    description="Update campaign status to verification_complete with summary data",
    input_schema={
        "campaign_id": str,
        "sheets_url": str,
        "total_ready": int,
        "report_json": str,
    },
)
async def update_campaign_verification_complete(args: dict[str, Any]) -> dict[str, Any]:
    """
    Update campaign to verification_complete status.

    Args:
        args: Dictionary with campaign_id, sheets_url, total_ready, and report_json.

    Returns:
        Dictionary with update status.
    """
    campaign_id = args.get("campaign_id")
    sheets_url = args.get("sheets_url")
    total_ready = args.get("total_ready", 0)
    report_json = args.get("report_json", "{}")

    if not campaign_id:
        return {
            "content": [{"type": "text", "text": "Error: campaign_id is required"}],
            "is_error": True,
        }

    try:
        async with get_session() as session:
            campaign_repo = CampaignRepository(session)

            # Update campaign
            campaign = await campaign_repo.update_campaign(
                campaign_id=campaign_id,
                status="verification_complete",
                verified_lead_list_url=sheets_url,
                total_leads_ready=total_ready,
                verification_summary=json.loads(report_json),
            )

            if not campaign:
                return {
                    "content": [{"type": "text", "text": f"Campaign {campaign_id} not found"}],
                    "is_error": True,
                }

            # Log audit entry
            await _log_verification_complete(session, campaign_id, report_json)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "updated": True,
                                "campaign_id": campaign_id,
                                "status": "verification_complete",
                            }
                        ),
                    }
                ],
            }

    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e!s}"}],
            "is_error": True,
        }


async def _log_verification_complete(
    session: AsyncSession,
    campaign_id: str,
    report_json: str,
) -> None:
    """Log verification completion to audit log."""
    query = text(
        """
        INSERT INTO campaign_audit_log (campaign_id, action, actor, actor_type, details)
        VALUES (:campaign_id, 'verification_completed', 'verification_finalizer_agent', 'agent', :details::jsonb)
        """
    )
    await session.execute(
        query,
        {
            "campaign_id": campaign_id,
            "details": report_json,
        },
    )
