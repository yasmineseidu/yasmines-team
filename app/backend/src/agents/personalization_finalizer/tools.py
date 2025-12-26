"""
SDK MCP tools for Personalization Finalizer Agent.

Tools for compiling personalization stats, generating reports,
exporting to Google Sheets, and sending approval notifications.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from claude_agent_sdk import tool

from src.agents.personalization_finalizer.reports import (
    FrameworkUsage,
    PersonalizationLevelStats,
    PersonalizationReport,
    QualityDistribution,
    TierPersonalizationBreakdown,
)
from src.database.connection import get_session

logger = logging.getLogger(__name__)


def _create_content(text: str, is_error: bool = False) -> dict[str, Any]:
    """Create a properly formatted tool response.

    Args:
        text: The response text.
        is_error: Whether this is an error response.

    Returns:
        Properly formatted tool response dictionary.
    """
    return {
        "content": [{"type": "text", "text": text}],
        "is_error": is_error,
    }


@tool(  # type: ignore[misc]
    name="get_personalization_stats",
    description="Get personalization statistics for a campaign from generated emails",
    input_schema={
        "campaign_id": str,
    },
)
async def get_personalization_stats(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get personalization statistics for a campaign.

    Queries the generated_emails table to compile comprehensive stats
    including quality scores, framework usage, and tier breakdowns.

    Args:
        args: Dictionary with campaign_id.

    Returns:
        Tool response with personalization statistics or error.
    """
    from sqlalchemy import select

    from src.database.models import CampaignModel as Campaign
    from src.database.models import GeneratedEmailModel as GeneratedEmail
    from src.database.models import LeadModel as Lead

    campaign_id = args.get("campaign_id")
    if not campaign_id:
        return _create_content("Error: campaign_id is required", is_error=True)

    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError:
        return _create_content(f"Invalid campaign_id format: {campaign_id}", is_error=True)

    try:
        async with get_session() as session:
            # Get campaign info
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_uuid)
            )
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                return _create_content(f"Campaign not found: {campaign_id}", is_error=True)

            # Get all generated emails for this campaign
            emails_result = await session.execute(
                select(GeneratedEmail, Lead)
                .join(Lead, GeneratedEmail.lead_id == Lead.id)
                .where(GeneratedEmail.campaign_id == campaign_uuid)
            )
            email_lead_pairs = emails_result.all()

            if not email_lead_pairs:
                return _create_content(
                    json.dumps(
                        {
                            "campaign_id": campaign_id,
                            "campaign_name": campaign.name,
                            "total_emails": 0,
                            "message": "No generated emails found for this campaign",
                        }
                    ),
                    is_error=False,
                )

            # Compile statistics
            total_quality = 0.0
            quality_scores: list[int] = []
            tier_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "count": 0,
                    "quality_total": 0.0,
                    "quality_scores": [],
                    "regenerations": 0,
                }
            )
            framework_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "quality_total": 0.0}
            )
            level_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "quality_total": 0.0}
            )
            quality_dist = {"excellent": 0, "good": 0, "acceptable": 0, "needs_improvement": 0}

            for email, lead in email_lead_pairs:
                score = email.quality_score or 0
                quality_scores.append(score)
                total_quality += score

                # Tier breakdown
                tier = lead.lead_tier or "C"
                tier_stats[tier]["count"] += 1
                tier_stats[tier]["quality_total"] += score
                tier_stats[tier]["quality_scores"].append(score)

                # Framework usage
                framework = email.framework_used or "unknown"
                framework_stats[framework]["count"] += 1
                framework_stats[framework]["quality_total"] += score

                # Personalization level
                level = email.personalization_level or "unknown"
                level_stats[level]["count"] += 1
                level_stats[level]["quality_total"] += score

                # Quality distribution
                if score >= 80:
                    quality_dist["excellent"] += 1
                elif score >= 60:
                    quality_dist["good"] += 1
                elif score >= 40:
                    quality_dist["acceptable"] += 1
                else:
                    quality_dist["needs_improvement"] += 1

            total_emails = len(email_lead_pairs)
            avg_quality = total_quality / total_emails if total_emails > 0 else 0.0

            # Build response
            stats = {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "niche_name": campaign.niche_name or "Unknown Niche",
                "total_emails_generated": total_emails,
                "avg_quality_score": round(avg_quality, 1),
                "min_quality_score": min(quality_scores) if quality_scores else 0,
                "max_quality_score": max(quality_scores) if quality_scores else 0,
                "tier_breakdown": {
                    tier: {
                        "count": data["count"],
                        "avg_quality": round(data["quality_total"] / data["count"], 1)
                        if data["count"] > 0
                        else 0,
                        "min_quality": min(data["quality_scores"]) if data["quality_scores"] else 0,
                        "max_quality": max(data["quality_scores"]) if data["quality_scores"] else 0,
                    }
                    for tier, data in tier_stats.items()
                },
                "framework_usage": {
                    fw: {
                        "count": data["count"],
                        "avg_quality": round(data["quality_total"] / data["count"], 1)
                        if data["count"] > 0
                        else 0,
                    }
                    for fw, data in framework_stats.items()
                },
                "personalization_levels": {
                    level: {
                        "count": data["count"],
                        "avg_quality": round(data["quality_total"] / data["count"], 1)
                        if data["count"] > 0
                        else 0,
                    }
                    for level, data in level_stats.items()
                },
                "quality_distribution": quality_dist,
            }

            logger.info(
                f"Compiled personalization stats for campaign {campaign_id}: {total_emails} emails"
            )
            return _create_content(json.dumps(stats), is_error=False)

    except Exception as e:
        logger.error(f"Error getting personalization stats: {e}")
        return _create_content(f"Error getting personalization stats: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="generate_personalization_report",
    description="Generate a comprehensive personalization report from campaign stats",
    input_schema={
        "campaign_id": str,
        "campaign_name": str,
        "niche_name": str,
        "stats_json": str,
    },
)
async def generate_personalization_report(args: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a comprehensive personalization report from stats.

    Takes the stats from get_personalization_stats and creates a
    structured PersonalizationReport object.

    Args:
        args: Dictionary with campaign_id, campaign_name, niche_name, stats_json.

    Returns:
        Tool response with report JSON or error.
    """
    campaign_id = args.get("campaign_id", "")
    campaign_name = args.get("campaign_name", "")
    niche_name = args.get("niche_name", "")
    stats_json = args.get("stats_json", "{}")

    try:
        stats = json.loads(stats_json)
    except json.JSONDecodeError as e:
        return _create_content(f"Invalid stats JSON: {e}", is_error=True)

    try:
        # Build tier breakdowns
        tier_breakdowns: dict[str, TierPersonalizationBreakdown] = {}
        tier_data = stats.get("tier_breakdown", {})
        for tier_name, tier_stats_data in tier_data.items():
            tier_breakdowns[tier_name] = TierPersonalizationBreakdown(
                tier=tier_name,
                total_leads=tier_stats_data.get("count", 0),
                emails_generated=tier_stats_data.get("count", 0),
                avg_quality_score=tier_stats_data.get("avg_quality", 0.0),
                min_quality_score=tier_stats_data.get("min_quality", 0),
                max_quality_score=tier_stats_data.get("max_quality", 0),
                quality_passed=0,  # Would need threshold to calculate
                quality_failed=0,
                regeneration_count=0,
            )

        # Build framework usage
        framework_usage: dict[str, FrameworkUsage] = {}
        fw_data = stats.get("framework_usage", {})
        for fw_name, fw_stats_data in fw_data.items():
            framework_usage[fw_name] = FrameworkUsage(
                framework=fw_name,
                count=fw_stats_data.get("count", 0),
                avg_quality_score=fw_stats_data.get("avg_quality", 0.0),
            )

        # Build personalization levels
        personalization_levels: dict[str, PersonalizationLevelStats] = {}
        level_data = stats.get("personalization_levels", {})
        for level_name, level_stats_data in level_data.items():
            personalization_levels[level_name] = PersonalizationLevelStats(
                level=level_name,
                count=level_stats_data.get("count", 0),
                avg_quality_score=level_stats_data.get("avg_quality", 0.0),
            )

        # Build quality distribution
        q_dist = stats.get("quality_distribution", {})
        quality_distribution = QualityDistribution(
            excellent=q_dist.get("excellent", 0),
            good=q_dist.get("good", 0),
            acceptable=q_dist.get("acceptable", 0),
            needs_improvement=q_dist.get("needs_improvement", 0),
        )

        # Create report
        report = PersonalizationReport(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            niche_name=niche_name,
            total_leads=stats.get("total_emails_generated", 0),
            total_emails_generated=stats.get("total_emails_generated", 0),
            avg_quality_score=stats.get("avg_quality_score", 0.0),
            min_quality_score=stats.get("min_quality_score", 0),
            max_quality_score=stats.get("max_quality_score", 0),
            tier_breakdowns=tier_breakdowns,
            framework_usage=framework_usage,
            personalization_levels=personalization_levels,
            quality_distribution=quality_distribution,
            total_regenerations=0,
            generated_at=datetime.now(UTC),
        )

        logger.info(f"Generated personalization report for campaign {campaign_id}")
        return _create_content(json.dumps(report.to_dict()), is_error=False)

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return _create_content(f"Error generating report: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="get_email_samples",
    description="Get email samples for each tier for Google Sheets export",
    input_schema={
        "campaign_id": str,
        "samples_per_tier": int,
    },
)
async def get_email_samples(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get email samples for each tier for Google Sheets export.

    Args:
        args: Dictionary with campaign_id and samples_per_tier.

    Returns:
        Tool response with email samples JSON or error.
    """
    from sqlalchemy import select

    from src.database.models import GeneratedEmailModel as GeneratedEmail
    from src.database.models import LeadModel as Lead

    campaign_id = args.get("campaign_id")
    samples_per_tier = args.get("samples_per_tier", 5)

    if not campaign_id:
        return _create_content("Error: campaign_id is required", is_error=True)

    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError:
        return _create_content(f"Invalid campaign_id format: {campaign_id}", is_error=True)

    try:
        async with get_session() as session:
            samples: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}

            for tier in ["A", "B", "C"]:
                # Get top samples by quality score for each tier
                query = (
                    select(GeneratedEmail, Lead)
                    .join(Lead, GeneratedEmail.lead_id == Lead.id)
                    .where(GeneratedEmail.campaign_id == campaign_uuid)
                    .where(Lead.lead_tier == tier)
                    .order_by(GeneratedEmail.quality_score.desc())
                    .limit(samples_per_tier)
                )
                result = await session.execute(query)
                email_lead_pairs = result.all()

                for email, lead in email_lead_pairs:
                    samples[tier].append(
                        {
                            "lead_id": str(lead.id),
                            "first_name": lead.first_name,
                            "last_name": lead.last_name,
                            "company_name": lead.company_name,
                            "title": lead.title,
                            "lead_tier": tier,
                            "subject_line": email.subject_line,
                            "opening_line": email.opening_line,
                            "body": email.body,
                            "cta": email.cta,
                            "full_email": email.full_email,
                            "framework_used": email.framework_used,
                            "personalization_level": email.personalization_level,
                            "quality_score": email.quality_score,
                        }
                    )

            total_samples = sum(len(s) for s in samples.values())
            logger.info(f"Retrieved {total_samples} email samples for campaign {campaign_id}")

            return _create_content(json.dumps(samples), is_error=False)

    except Exception as e:
        logger.error(f"Error getting email samples: {e}")
        return _create_content(f"Error getting email samples: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="export_emails_to_sheets",
    description="Export email samples to Google Sheets for human review",
    input_schema={
        "report_json": str,
        "samples_json": str,
    },
)
async def export_emails_to_sheets(args: dict[str, Any]) -> dict[str, Any]:
    """
    Export email samples to Google Sheets.

    Creates a new spreadsheet with summary and tier-specific sheets.

    Args:
        args: Dictionary with report_json and samples_json.

    Returns:
        Tool response with spreadsheet URL or error.
    """
    from src.agents.personalization_finalizer.exports import (
        EmailSamplesExporter,
        SheetsExportError,
    )

    report_json = args.get("report_json", "{}")
    samples_json = args.get("samples_json", "{}")

    try:
        report_data = json.loads(report_json)
        samples_data = json.loads(samples_json)
    except json.JSONDecodeError as e:
        return _create_content(f"Invalid JSON input: {e}", is_error=True)

    # Reconstruct report object (simplified)
    report = PersonalizationReport(
        campaign_id=report_data.get("campaign_id", ""),
        campaign_name=report_data.get("campaign_name", ""),
        niche_name=report_data.get("niche_name", ""),
        total_leads=report_data.get("total_leads", 0),
        total_emails_generated=report_data.get("total_emails_generated", 0),
        avg_quality_score=report_data.get("avg_quality_score", 0.0),
        min_quality_score=report_data.get("min_quality_score", 0),
        max_quality_score=report_data.get("max_quality_score", 0),
    )

    # Extract samples by tier
    tier_a_samples = samples_data.get("A", [])
    tier_b_samples = samples_data.get("B", [])
    tier_c_samples = samples_data.get("C", [])

    exporter = EmailSamplesExporter()

    try:
        result = await exporter.export_email_samples(
            report=report,
            tier_a_samples=tier_a_samples,
            tier_b_samples=tier_b_samples,
            tier_c_samples=tier_c_samples,
        )

        logger.info(f"Exported emails to Google Sheets: {result['spreadsheet_url']}")
        return _create_content(json.dumps(result), is_error=False)

    except SheetsExportError as e:
        logger.error(f"Sheets export error: {e}")
        return _create_content(f"Google Sheets export failed: {e.message}", is_error=True)
    except Exception as e:
        logger.error(f"Unexpected export error: {e}")
        return _create_content(f"Export failed: {e}", is_error=True)
    finally:
        await exporter.close()


@tool(  # type: ignore[misc]
    name="send_phase4_approval_notification",
    description="Send Phase 4 completion notification via Telegram for human approval",
    input_schema={
        "campaign_name": str,
        "niche_name": str,
        "total_emails": int,
        "avg_quality": float,
        "sheets_url": str,
        "chat_id": str,
    },
)
async def send_phase4_approval_notification(args: dict[str, Any]) -> dict[str, Any]:
    """
    Send Phase 4 completion notification via Telegram.

    Notifies the team that personalization is complete and emails
    are ready for review before Phase 5 (Campaign Execution).

    Args:
        args: Dictionary with campaign_name, niche_name, total_emails, avg_quality, sheets_url, chat_id.

    Returns:
        Tool response with notification result or error.
    """
    from src.integrations.telegram import TelegramClient, TelegramError

    campaign_name = args.get("campaign_name", "")
    niche_name = args.get("niche_name", "")
    total_emails = args.get("total_emails", 0)
    avg_quality = args.get("avg_quality", 0.0)
    sheets_url = args.get("sheets_url", "")
    chat_id = args.get("chat_id")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        # Notification is optional - return success even without token
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping notification")
        return _create_content(
            json.dumps({"sent": False, "reason": "TELEGRAM_BOT_TOKEN not configured"}),
            is_error=False,
        )

    notification_chat_id = chat_id or os.getenv("TELEGRAM_NOTIFICATION_CHAT_ID")
    if not notification_chat_id:
        logger.warning("No chat_id provided and TELEGRAM_NOTIFICATION_CHAT_ID not set")
        return _create_content(
            json.dumps({"sent": False, "reason": "No chat_id configured"}),
            is_error=False,
        )

    # Build notification message
    quality_emoji = "🟢" if avg_quality >= 70 else "🟡" if avg_quality >= 50 else "🔴"
    message = f"""🎯 *Phase 4 Complete: Personalization Ready for Review*

📋 *Campaign:* {campaign_name}
🏢 *Niche:* {niche_name}

📊 *Results:*
• Emails Generated: {total_emails:,}
• Avg Quality Score: {avg_quality:.1f} {quality_emoji}

📄 *Email Samples:*
[View in Google Sheets]({sheets_url})

⏳ *Next Step:* Human review required before Phase 5 (Campaign Execution)

Please review the email samples and approve to proceed with sending."""

    client = TelegramClient(bot_token=bot_token)

    try:
        result = await client.send_message(
            chat_id=notification_chat_id,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        logger.info(f"Sent Phase 4 approval notification to chat {notification_chat_id}")
        return _create_content(
            json.dumps(
                {
                    "sent": True,
                    "message_id": result.message_id,
                    "chat_id": notification_chat_id,
                }
            ),
            is_error=False,
        )

    except TelegramError as e:
        logger.error(f"Telegram notification error: {e}")
        return _create_content(
            json.dumps({"sent": False, "error": str(e)}),
            is_error=False,  # Notification failure is not critical
        )
    except Exception as e:
        logger.error(f"Unexpected notification error: {e}")
        return _create_content(
            json.dumps({"sent": False, "error": str(e)}),
            is_error=False,
        )
    finally:
        await client.close()


@tool(  # type: ignore[misc]
    name="update_campaign_personalization_complete",
    description="Update campaign status to personalization_complete with summary data",
    input_schema={
        "campaign_id": str,
        "total_emails": int,
        "avg_quality": float,
        "sheets_url": str,
        "summary_json": str,
    },
)
async def update_campaign_personalization_complete(args: dict[str, Any]) -> dict[str, Any]:
    """
    Update campaign status to personalization_complete.

    Updates the campaign record with personalization results and
    marks it ready for Phase 5 human approval.

    Args:
        args: Dictionary with campaign_id, total_emails, avg_quality, sheets_url, summary_json.

    Returns:
        Tool response with update result or error.
    """
    from sqlalchemy import update

    from src.database.models import CampaignModel as Campaign

    campaign_id = args.get("campaign_id")
    total_emails = args.get("total_emails", 0)
    avg_quality = args.get("avg_quality", 0.0)
    sheets_url = args.get("sheets_url", "")
    summary_json = args.get("summary_json", "{}")

    if not campaign_id:
        return _create_content("Error: campaign_id is required", is_error=True)

    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError:
        return _create_content(f"Invalid campaign_id format: {campaign_id}", is_error=True)

    try:
        summary = json.loads(summary_json)
    except json.JSONDecodeError:
        summary = {}

    try:
        async with get_session() as session:
            stmt = (
                update(Campaign)
                .where(Campaign.id == campaign_uuid)
                .values(
                    total_emails_generated=total_emails,
                    avg_email_quality=avg_quality,
                    email_samples_url=sheets_url,
                    personalization_summary=summary,
                    personalization_completed_at=datetime.now(UTC),
                    sending_status="ready",  # Ready for Phase 5 approval
                    updated_at=datetime.now(UTC),
                )
            )
            await session.execute(stmt)
            await session.commit()

            logger.info(f"Updated campaign {campaign_id} to personalization_complete")
            return _create_content(
                json.dumps(
                    {
                        "success": True,
                        "campaign_id": campaign_id,
                        "status": "personalization_complete",
                        "sending_status": "ready",
                    }
                ),
                is_error=False,
            )

    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        return _create_content(f"Error updating campaign: {e}", is_error=True)


def create_personalization_finalizer_tools_server(
    name: str = "personalization_finalizer",
    version: str = "1.0.0",
) -> Any:
    """
    Create an SDK MCP server with all Personalization Finalizer tools.

    This factory function bundles all tools required by the Personalization
    Finalizer Agent into a single MCP server that can be passed to the SDK.

    Args:
        name: Name for the MCP server.
        version: Version string for the MCP server.

    Returns:
        Configured SDK MCP server with all tools registered.
    """
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server(
        name=name,
        version=version,
        tools=[
            get_personalization_stats,
            generate_personalization_report,
            get_email_samples,
            export_emails_to_sheets,
            send_phase4_approval_notification,
            update_campaign_personalization_complete,
        ],
    )
