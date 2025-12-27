"""
SDK MCP tools for Campaign Setup Agent (Phase 5.1).

Tools for validating prerequisites, creating Instantly campaigns,
configuring email sequences, schedules, and warmup settings.
"""

import json
import logging
import os
from typing import Any
from uuid import UUID

from claude_agent_sdk import tool

from src.agents.campaign_setup.schemas import (
    PrerequisiteCheckResult,
    SendingSchedule,
    WarmupConfigResult,
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
    name="validate_campaign_prerequisites",
    description="Validate that a campaign is ready for Instantly setup (approved, has leads, has accounts)",
    input_schema={
        "campaign_id": str,
    },
)
async def validate_campaign_prerequisites(args: dict[str, Any]) -> dict[str, Any]:
    """
    Validate that a campaign meets all prerequisites for Instantly setup.

    Checks:
    - Campaign exists and is approved for sending
    - Campaign has leads with verified emails
    - Workspace has active sending accounts

    Args:
        args: Dictionary with campaign_id.

    Returns:
        Tool response with PrerequisiteCheckResult JSON or error.
    """
    from sqlalchemy import func, select

    from src.database.models import CampaignModel as Campaign
    from src.database.models import LeadModel as Lead
    from src.integrations.instantly import AccountStatus, InstantlyClient, InstantlyError

    campaign_id = args.get("campaign_id")
    if not campaign_id:
        return _create_content("Error: campaign_id is required", is_error=True)

    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError:
        return _create_content(f"Invalid campaign_id format: {campaign_id}", is_error=True)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        async with get_session() as session:
            # 1. Check campaign exists and status
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_uuid)
            )
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                return _create_content(
                    json.dumps(
                        PrerequisiteCheckResult(
                            valid=False,
                            campaign_id=campaign_id,
                            errors=["Campaign not found"],
                        ).to_dict()
                    ),
                    is_error=False,
                )

            campaign_status = getattr(campaign, "sending_status", None) or getattr(
                campaign, "status", "unknown"
            )

            # Check if campaign is approved for sending
            approved_statuses = ["ready", "approved", "personalization_complete"]
            if campaign_status not in approved_statuses:
                errors.append(
                    f"Campaign status '{campaign_status}' is not approved for sending. "
                    f"Expected one of: {approved_statuses}"
                )

            # 2. Count leads with verified emails
            lead_count_result = await session.execute(
                select(func.count(Lead.id)).where(
                    Lead.campaign_id == campaign_uuid,
                    Lead.email.isnot(None),
                    Lead.email != "",
                )
            )
            leads_with_emails = lead_count_result.scalar() or 0

            total_lead_result = await session.execute(
                select(func.count(Lead.id)).where(Lead.campaign_id == campaign_uuid)
            )
            total_leads = total_lead_result.scalar() or 0

            if leads_with_emails == 0:
                errors.append("No leads with verified emails found for this campaign")
            elif leads_with_emails < 10:
                warnings.append(
                    f"Only {leads_with_emails} leads with emails (minimum recommended: 10)"
                )

            # 3. Check for active sending accounts via Instantly API
            available_accounts = 0
            instantly_api_key = os.getenv("INSTANTLY_API_KEY")

            if not instantly_api_key:
                errors.append("INSTANTLY_API_KEY not configured")
            else:
                try:
                    client = InstantlyClient(api_key=instantly_api_key)
                    accounts = await client.list_accounts(
                        status=AccountStatus.ACTIVE,
                        limit=100,
                    )
                    available_accounts = len(accounts)
                    await client.close()

                    if available_accounts == 0:
                        errors.append("No active sending accounts found in Instantly")
                    elif available_accounts < 3:
                        warnings.append(
                            f"Only {available_accounts} active accounts (recommended: 3+)"
                        )

                except InstantlyError as e:
                    errors.append(f"Failed to check Instantly accounts: {e}")

            # Build result
            result = PrerequisiteCheckResult(
                valid=len(errors) == 0,
                campaign_id=campaign_id,
                campaign_name=str(campaign.name) if campaign.name else None,
                campaign_status=campaign_status,
                total_leads=total_leads,
                leads_with_emails=leads_with_emails,
                available_accounts=available_accounts,
                errors=errors,
                warnings=warnings,
            )

            logger.info(
                f"Prerequisite check for campaign {campaign_id}: "
                f"valid={result.valid}, leads={leads_with_emails}, accounts={available_accounts}"
            )

            return _create_content(json.dumps(result.to_dict()), is_error=False)

    except Exception as e:
        logger.error(f"Error validating prerequisites: {e}")
        return _create_content(f"Error validating prerequisites: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="create_instantly_campaign",
    description="Create a campaign in Instantly.ai with email sequence and schedule",
    input_schema={
        "campaign_id": str,
        "campaign_name": str,
        "sequence_steps_json": str,
        "schedule_json": str,
        "sending_account_emails": str,
        "daily_limit": int,
        "email_gap_minutes": int,
    },
)
async def create_instantly_campaign(args: dict[str, Any]) -> dict[str, Any]:
    """
    Create a campaign in Instantly.ai with full configuration.

    Creates the campaign with:
    - Multi-step email sequence
    - Sending schedule (days, times, timezone)
    - Assigned sending accounts
    - Daily limit and email gap settings

    Args:
        args: Dictionary with campaign configuration.

    Returns:
        Tool response with created campaign details or error.
    """
    from src.integrations.instantly import InstantlyClient, InstantlyError

    campaign_id = args.get("campaign_id", "")
    campaign_name = args.get("campaign_name", "")
    sequence_steps_json = args.get("sequence_steps_json", "[]")
    schedule_json = args.get("schedule_json", "{}")
    sending_account_emails = args.get("sending_account_emails", "")
    daily_limit = args.get("daily_limit", 50)
    email_gap_minutes = args.get("email_gap_minutes", 5)

    if not campaign_name:
        return _create_content("Error: campaign_name is required", is_error=True)

    # Parse sequence steps
    try:
        sequence_steps_data = json.loads(sequence_steps_json)
    except json.JSONDecodeError as e:
        return _create_content(f"Invalid sequence_steps_json: {e}", is_error=True)

    # Parse schedule
    try:
        schedule_data = json.loads(schedule_json)
    except json.JSONDecodeError as e:
        return _create_content(f"Invalid schedule_json: {e}", is_error=True)

    # Parse account emails
    account_emails = [e.strip() for e in sending_account_emails.split(",") if e.strip()]

    instantly_api_key = os.getenv("INSTANTLY_API_KEY")
    if not instantly_api_key:
        return _create_content("Error: INSTANTLY_API_KEY not configured", is_error=True)

    try:
        client = InstantlyClient(api_key=instantly_api_key)

        # Build sequence in Instantly format
        # Sequences are arrays where only the first element is used
        instantly_steps = []
        for step in sequence_steps_data:
            instantly_step = {
                "type": step.get("type", "email"),
                "delay": step.get("delay_days", 0),
                "variants": step.get(
                    "variants", [{"subject": step.get("subject", ""), "body": step.get("body", "")}]
                ),
            }
            instantly_steps.append(instantly_step)

        sequences = [{"steps": instantly_steps}] if instantly_steps else []

        # Build schedule
        schedule = SendingSchedule(
            name=schedule_data.get("name", "Business Hours"),
            start_time=schedule_data.get("start_time", "09:00"),
            end_time=schedule_data.get("end_time", "17:00"),
            timezone=schedule_data.get("timezone", "America/New_York"),
            monday=schedule_data.get("monday", True),
            tuesday=schedule_data.get("tuesday", True),
            wednesday=schedule_data.get("wednesday", True),
            thursday=schedule_data.get("thursday", True),
            friday=schedule_data.get("friday", True),
            saturday=schedule_data.get("saturday", False),
            sunday=schedule_data.get("sunday", False),
        )

        campaign_schedule = {
            "schedules": [schedule.to_instantly_format()],
        }

        # Create campaign in Instantly
        campaign = await client.create_campaign(
            name=campaign_name,
            campaign_schedule=campaign_schedule,
            sequences=sequences,
            email_list=account_emails,
            daily_limit=daily_limit,
            email_gap=email_gap_minutes,
            stop_on_reply=True,
            link_tracking=True,
            open_tracking=True,
        )

        await client.close()

        result = {
            "success": True,
            "internal_campaign_id": campaign_id,
            "instantly_campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "status": campaign.status.name,
            "sequence_steps": len(instantly_steps),
            "sending_accounts": len(account_emails),
            "daily_limit": daily_limit,
        }

        logger.info(
            f"Created Instantly campaign: {campaign.id} for internal campaign {campaign_id}"
        )
        return _create_content(json.dumps(result), is_error=False)

    except InstantlyError as e:
        logger.error(f"Instantly API error creating campaign: {e}")
        return _create_content(
            json.dumps({"success": False, "error": str(e)}),
            is_error=False,  # Return error in result, not as tool error
        )
    except Exception as e:
        logger.error(f"Error creating Instantly campaign: {e}")
        return _create_content(f"Error creating campaign: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="configure_warmup",
    description="Enable warmup for sending accounts to improve deliverability",
    input_schema={
        "account_emails": str,
    },
)
async def configure_warmup(args: dict[str, Any]) -> dict[str, Any]:
    """
    Enable warmup for specified sending accounts.

    Warmup gradually increases sending volume to improve
    deliverability and reputation with email providers.

    Args:
        args: Dictionary with comma-separated account emails.

    Returns:
        Tool response with warmup configuration result or error.
    """
    from src.integrations.instantly import InstantlyClient, InstantlyError

    account_emails_str = args.get("account_emails", "")
    if not account_emails_str:
        return _create_content("Error: account_emails is required", is_error=True)

    account_emails = [e.strip() for e in account_emails_str.split(",") if e.strip()]

    if not account_emails:
        return _create_content("Error: No valid account emails provided", is_error=True)

    instantly_api_key = os.getenv("INSTANTLY_API_KEY")
    if not instantly_api_key:
        return _create_content("Error: INSTANTLY_API_KEY not configured", is_error=True)

    try:
        client = InstantlyClient(api_key=instantly_api_key)

        job = await client.enable_warmup_for_accounts(emails=account_emails)

        await client.close()

        result = WarmupConfigResult(
            success=True,
            accounts_configured=len(account_emails),
            job_id=job.job_id,
        )

        logger.info(f"Enabled warmup for {len(account_emails)} accounts, job_id: {job.job_id}")

        return _create_content(json.dumps(result.to_dict()), is_error=False)

    except InstantlyError as e:
        logger.error(f"Instantly API error enabling warmup: {e}")
        return _create_content(
            json.dumps(WarmupConfigResult(success=False, error=str(e)).to_dict()),
            is_error=False,
        )
    except Exception as e:
        logger.error(f"Error configuring warmup: {e}")
        return _create_content(f"Error configuring warmup: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="add_leads_to_campaign",
    description="Add leads from the database to an Instantly campaign",
    input_schema={
        "internal_campaign_id": str,
        "instantly_campaign_id": str,
        "batch_size": int,
    },
)
async def add_leads_to_campaign(args: dict[str, Any]) -> dict[str, Any]:
    """
    Add leads from the database to an Instantly campaign.

    Fetches leads with verified emails and adds them in batches
    to the Instantly campaign with their personalization data.

    Args:
        args: Dictionary with campaign IDs and batch size.

    Returns:
        Tool response with leads added count or error.
    """
    from sqlalchemy import select

    from src.database.models import LeadModel as Lead
    from src.integrations.instantly import InstantlyClient, InstantlyError

    internal_campaign_id = args.get("internal_campaign_id", "")
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    batch_size = args.get("batch_size", 1000)

    if not internal_campaign_id or not instantly_campaign_id:
        return _create_content(
            "Error: internal_campaign_id and instantly_campaign_id are required",
            is_error=True,
        )

    try:
        campaign_uuid = UUID(internal_campaign_id)
    except ValueError:
        return _create_content(
            f"Invalid internal_campaign_id format: {internal_campaign_id}",
            is_error=True,
        )

    instantly_api_key = os.getenv("INSTANTLY_API_KEY")
    if not instantly_api_key:
        return _create_content("Error: INSTANTLY_API_KEY not configured", is_error=True)

    total_added = 0
    total_failed = 0

    try:
        async with get_session() as session:
            # Fetch leads with verified emails
            leads_result = await session.execute(
                select(Lead)
                .where(Lead.campaign_id == campaign_uuid)
                .where(Lead.email.isnot(None))
                .where(Lead.email != "")
            )
            leads = leads_result.scalars().all()

            if not leads:
                return _create_content(
                    json.dumps(
                        {
                            "success": True,
                            "leads_added": 0,
                            "leads_failed": 0,
                            "message": "No leads with emails found",
                        }
                    ),
                    is_error=False,
                )

            client = InstantlyClient(api_key=instantly_api_key)

            # Process in batches
            for i in range(0, len(leads), batch_size):
                batch = leads[i : i + batch_size]

                instantly_leads = []
                for lead in batch:
                    lead_data: dict[str, Any] = {
                        "email": lead.email,
                    }
                    if lead.first_name:
                        lead_data["first_name"] = lead.first_name
                    if lead.last_name:
                        lead_data["last_name"] = lead.last_name
                    if lead.company_name:
                        lead_data["company_name"] = lead.company_name
                    if lead.company_domain:
                        lead_data["website"] = lead.company_domain

                    # Add custom variables for personalization
                    custom_vars: dict[str, Any] = {}
                    if lead.title:
                        custom_vars["title"] = lead.title
                    if lead.linkedin_url:
                        custom_vars["linkedin_url"] = lead.linkedin_url
                    if lead.lead_tier:
                        custom_vars["lead_tier"] = lead.lead_tier

                    if custom_vars:
                        lead_data["custom_variables"] = custom_vars

                    instantly_leads.append(lead_data)

                # Bulk add leads to Instantly
                result = await client.bulk_add_leads(
                    leads=instantly_leads,
                    campaign_id=instantly_campaign_id,
                )

                total_added += result.created_count + result.updated_count
                total_failed += result.failed_count

            await client.close()

            response = {
                "success": True,
                "leads_added": total_added,
                "leads_failed": total_failed,
                "total_leads": len(leads),
            }

            logger.info(f"Added {total_added} leads to Instantly campaign {instantly_campaign_id}")

            return _create_content(json.dumps(response), is_error=False)

    except InstantlyError as e:
        logger.error(f"Instantly API error adding leads: {e}")
        return _create_content(
            json.dumps(
                {
                    "success": False,
                    "leads_added": total_added,
                    "leads_failed": total_failed,
                    "error": str(e),
                }
            ),
            is_error=False,
        )
    except Exception as e:
        logger.error(f"Error adding leads to campaign: {e}")
        return _create_content(f"Error adding leads: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="update_campaign_setup_complete",
    description="Update the internal campaign record with Instantly campaign details",
    input_schema={
        "campaign_id": str,
        "instantly_campaign_id": str,
        "leads_added": int,
        "sending_accounts": int,
        "warmup_enabled": bool,
    },
)
async def update_campaign_setup_complete(args: dict[str, Any]) -> dict[str, Any]:
    """
    Update the internal campaign record after Instantly setup.

    Stores the Instantly campaign ID and setup metadata
    in the internal campaign record for tracking.

    Args:
        args: Dictionary with campaign details to update.

    Returns:
        Tool response with update result or error.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select, update

    from src.database.models import CampaignModel as Campaign

    campaign_id = args.get("campaign_id")
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    leads_added = args.get("leads_added", 0)
    sending_accounts = args.get("sending_accounts", 0)
    warmup_enabled = args.get("warmup_enabled", False)

    if not campaign_id:
        return _create_content("Error: campaign_id is required", is_error=True)

    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError:
        return _create_content(f"Invalid campaign_id format: {campaign_id}", is_error=True)

    try:
        async with get_session() as session:
            # Build update values
            update_values: dict[str, Any] = {
                "instantly_campaign_id": instantly_campaign_id,
                "sending_status": "campaign_created",
                "updated_at": datetime.now(UTC),
            }

            # Store setup details in import_summary (as extension)
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_uuid)
            )
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                return _create_content(f"Campaign not found: {campaign_id}", is_error=True)

            # SQLAlchemy Column type doesn't match runtime dict type
            import_summary: dict[str, Any] = dict(campaign.import_summary or {})
            import_summary["phase5_setup"] = {
                "instantly_campaign_id": instantly_campaign_id,
                "leads_added": leads_added,
                "sending_accounts": sending_accounts,
                "warmup_enabled": warmup_enabled,
                "setup_completed_at": datetime.now(UTC).isoformat(),
            }
            update_values["import_summary"] = import_summary

            stmt = update(Campaign).where(Campaign.id == campaign_uuid).values(**update_values)
            await session.execute(stmt)
            await session.commit()

            logger.info(f"Updated campaign {campaign_id} with Instantly setup details")

            return _create_content(
                json.dumps(
                    {
                        "success": True,
                        "campaign_id": campaign_id,
                        "instantly_campaign_id": instantly_campaign_id,
                        "status": "campaign_created",
                    }
                ),
                is_error=False,
            )

    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        return _create_content(f"Error updating campaign: {e}", is_error=True)


@tool(  # type: ignore[misc]
    name="send_setup_notification",
    description="Send Slack notification about campaign setup completion",
    input_schema={
        "campaign_name": str,
        "instantly_campaign_id": str,
        "leads_added": int,
        "sending_accounts": int,
        "daily_limit": int,
    },
)
async def send_setup_notification(args: dict[str, Any]) -> dict[str, Any]:
    """
    Send Slack notification about campaign setup completion.

    Notifies the team that a campaign has been set up in Instantly
    and is ready for activation.

    Args:
        args: Dictionary with campaign details for notification.

    Returns:
        Tool response with notification result or error.
    """
    from src.integrations.slack import SlackClient, SlackError

    campaign_name = args.get("campaign_name", "")
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    leads_added = args.get("leads_added", 0)
    sending_accounts = args.get("sending_accounts", 0)
    daily_limit = args.get("daily_limit", 0)

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        logger.warning("SLACK_BOT_TOKEN not set, skipping notification")
        return _create_content(
            json.dumps({"sent": False, "reason": "SLACK_BOT_TOKEN not configured"}),
            is_error=False,
        )

    slack_channel = os.getenv("SLACK_NOTIFICATION_CHANNEL", "#campaigns")

    # Build notification message
    message = f"""🚀 *Campaign Setup Complete*

*Campaign:* {campaign_name}
*Instantly ID:* `{instantly_campaign_id}`

📊 *Details:*
• Leads Added: {leads_added:,}
• Sending Accounts: {sending_accounts}
• Daily Limit: {daily_limit} emails/day

⏳ *Next Step:* Campaign is ready to activate in Instantly.

Review and activate when ready to start sending."""

    try:
        client = SlackClient(token=slack_token)
        result = await client.send_message(
            channel=slack_channel,
            text=message,
        )
        await client.close()

        logger.info(f"Sent setup notification to {slack_channel}")
        return _create_content(
            json.dumps(
                {
                    "sent": True,
                    "channel": slack_channel,
                    "timestamp": result.get("ts"),
                }
            ),
            is_error=False,
        )

    except SlackError as e:
        logger.error(f"Slack notification error: {e}")
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


def create_campaign_setup_tools_server(
    name: str = "campaign_setup",
    version: str = "1.0.0",
) -> Any:
    """
    Create an SDK MCP server with all Campaign Setup tools.

    This factory function bundles all tools required by the Campaign
    Setup Agent into a single MCP server that can be passed to the SDK.

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
            validate_campaign_prerequisites,
            create_instantly_campaign,
            configure_warmup,
            add_leads_to_campaign,
            update_campaign_setup_complete,
            send_setup_notification,
        ],
    )
