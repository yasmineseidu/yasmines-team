"""
Campaign Setup Agent (Phase 5.1).

Creates campaigns in Instantly.ai with email sequences, configures
sending schedules, and sets up warmup settings for optimal deliverability.

This is the first agent in Phase 5 (Campaign Execution).
It prepares the campaign infrastructure before email sending begins.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
    TextBlock,
    create_sdk_mcp_server,
    query,
)

from src.agents.campaign_setup.schemas import (
    CampaignSetupResult,
    EmailSequenceStep,
    SendingSchedule,
)
from src.agents.campaign_setup.tools import (
    add_leads_to_campaign,
    configure_warmup,
    create_instantly_campaign,
    send_setup_notification,
    update_campaign_setup_complete,
    validate_campaign_prerequisites,
)

logger = logging.getLogger(__name__)


@dataclass
class CampaignSetupConfig:
    """Configuration for Campaign Setup Agent."""

    # Default 4-step email sequence from YAML spec
    default_sequence: list[EmailSequenceStep] = field(
        default_factory=lambda: [
            EmailSequenceStep(
                step_number=1,
                subject="Quick question about {{companyName}}",
                body="Hi {{firstName}},\n\n{{opening_line}}\n\n{{body}}\n\n{{cta}}\n\nBest,\n{{senderName}}",
                delay_days=0,
            ),
            EmailSequenceStep(
                step_number=2,
                subject="Re: Quick question about {{companyName}}",
                body="Hi {{firstName}},\n\nJust following up on my previous email. {{follow_up_line}}\n\nBest,\n{{senderName}}",
                delay_days=3,
            ),
            EmailSequenceStep(
                step_number=3,
                subject="Re: Quick question about {{companyName}}",
                body="Hi {{firstName}},\n\n{{value_reminder}}\n\nWould love to connect if you have 15 minutes this week.\n\nBest,\n{{senderName}}",
                delay_days=4,
            ),
            EmailSequenceStep(
                step_number=4,
                subject="Should I close your file?",
                body="Hi {{firstName}},\n\nI haven't heard back, so I wanted to check if you're still interested.\n\nIf not, no worries - I'll close your file. If timing is just off, let me know when would be better.\n\nBest,\n{{senderName}}",
                delay_days=7,
            ),
        ]
    )

    # Default sending schedule (Mon-Fri, 9am-5pm EST)
    default_schedule: SendingSchedule = field(
        default_factory=lambda: SendingSchedule(
            name="Business Hours",
            start_time="09:00",
            end_time="17:00",
            timezone="America/New_York",
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            saturday=False,
            sunday=False,
        )
    )

    # Sending configuration
    daily_limit: int = 50
    email_gap_minutes: int = 5
    enable_warmup: bool = True
    send_notification: bool = True

    # Lead batch size for Instantly upload
    lead_batch_size: int = 1000


class CampaignSetupAgent:
    """
    Agent 5.1: Campaign Setup.

    Creates campaigns in Instantly.ai with email sequences,
    configures sending schedules, and enables warmup for accounts.

    Database Interactions:
    - Input: campaigns table (personalization_complete status)
    - Input: leads table (with verified emails)
    - Output: campaigns table (instantly_campaign_id, setup details)
    - Status: Updates campaign to campaign_created

    Handoff: Prepares campaign for Email Sending Agent (5.2).
    """

    SYSTEM_PROMPT = """You are a Campaign Setup agent responsible for Phase 5.1.

Your task is to:
1. Validate that the campaign is approved and has leads with verified emails
2. Check that sending accounts are available in Instantly
3. Create a campaign in Instantly.ai with the email sequence
4. Configure the sending schedule (weekdays, business hours)
5. Enable warmup for sending accounts (if configured)
6. Add leads from the database to the Instantly campaign
7. Update the internal campaign record with Instantly details
8. Send a notification about setup completion (if enabled)

You have access to tools for validation, Instantly campaign creation,
warmup configuration, lead upload, database updates, and notifications.

IMPORTANT: Execute tools in the correct order:
1. First, validate prerequisites
2. If valid, create the Instantly campaign
3. Configure warmup if enabled
4. Add leads to the campaign
5. Update internal campaign record
6. Send notification if enabled

Always provide the final result as JSON with these fields:
- success: boolean
- campaign_id: string (internal)
- instantly_campaign_id: string
- leads_added: number
- sending_accounts: number
- warmup_enabled: boolean
- error: string (if any error occurred)

STOP if prerequisites fail - do not proceed with campaign creation."""

    def __init__(
        self,
        config: CampaignSetupConfig | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """
        Initialize Campaign Setup Agent.

        Args:
            config: Agent configuration.
            model: Claude model to use.
        """
        self.config = config or CampaignSetupConfig()
        self.model = model

        # Remove ANTHROPIC_API_KEY conflict (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        logger.info("Initialized CampaignSetupAgent")

    async def setup_campaign(
        self,
        campaign_id: str,
        sequence: list[EmailSequenceStep] | None = None,
        schedule: SendingSchedule | None = None,
    ) -> CampaignSetupResult:
        """
        Execute campaign setup in Instantly.ai.

        Args:
            campaign_id: UUID of the campaign to set up.
            sequence: Custom email sequence (uses default if None).
            schedule: Custom sending schedule (uses default if None).

        Returns:
            CampaignSetupResult with success status and details.
        """
        logger.info(f"Starting campaign setup for campaign {campaign_id}")

        # Use provided sequence/schedule or defaults
        email_sequence = sequence or self.config.default_sequence
        sending_schedule = schedule or self.config.default_schedule

        # Convert sequence to JSON for tool
        sequence_json = json.dumps(
            [
                {
                    "step_number": step.step_number,
                    "subject": step.subject,
                    "body": step.body,
                    "delay_days": step.delay_days,
                    "type": step.step_type,
                    "variants": step.variants,
                }
                for step in email_sequence
            ]
        )

        # Convert schedule to JSON for tool
        schedule_json = json.dumps(
            {
                "name": sending_schedule.name,
                "start_time": sending_schedule.start_time,
                "end_time": sending_schedule.end_time,
                "timezone": sending_schedule.timezone,
                "monday": sending_schedule.monday,
                "tuesday": sending_schedule.tuesday,
                "wednesday": sending_schedule.wednesday,
                "thursday": sending_schedule.thursday,
                "friday": sending_schedule.friday,
                "saturday": sending_schedule.saturday,
                "sunday": sending_schedule.sunday,
            }
        )

        # Create SDK MCP server with all tools
        sdk_server = create_sdk_mcp_server(
            name="campaign_setup",
            version="1.0.0",
            tools=[
                validate_campaign_prerequisites,
                create_instantly_campaign,
                configure_warmup,
                add_leads_to_campaign,
                update_campaign_setup_complete,
                send_setup_notification,
            ],
        )

        # Build user message
        user_message = f"""Set up campaign in Instantly.ai for campaign: {campaign_id}

Configuration:
- Daily limit: {self.config.daily_limit} emails/day
- Email gap: {self.config.email_gap_minutes} minutes
- Enable warmup: {self.config.enable_warmup}
- Send notification: {self.config.send_notification}
- Lead batch size: {self.config.lead_batch_size}

Email sequence (JSON):
{sequence_json}

Sending schedule (JSON):
{schedule_json}

Execute the following steps:
1. Validate prerequisites for campaign {campaign_id}
2. If valid, create campaign in Instantly with the sequence and schedule
3. {"Enable warmup for the sending accounts" if self.config.enable_warmup else "Skip warmup (disabled)"}
4. Add leads from database to the Instantly campaign (batch size: {self.config.lead_batch_size})
5. Update internal campaign record with Instantly details
6. {"Send Slack notification about setup completion" if self.config.send_notification else "Skip notification (disabled)"}

If prerequisites fail, STOP immediately and return the validation errors.

Return the final result as JSON."""

        # Configure agent options
        options = ClaudeAgentOptions(
            system_prompt=self.SYSTEM_PROMPT,
            mcp_servers={"cs": sdk_server},
            allowed_tools=[
                "mcp__cs__validate_campaign_prerequisites",
                "mcp__cs__create_instantly_campaign",
                "mcp__cs__configure_warmup",
                "mcp__cs__add_leads_to_campaign",
                "mcp__cs__update_campaign_setup_complete",
                "mcp__cs__send_setup_notification",
            ],
            setting_sources=["project"],  # Load CLAUDE.md settings
            permission_mode="acceptEdits",  # Automated agent workflow
        )

        try:
            # Execute query using async iterator pattern
            text_content = ""
            async for message in query(prompt=user_message, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            text_content += block.text

            # Parse result from collected response
            result = self._parse_agent_response(campaign_id, text_content)
            logger.info(f"Campaign setup complete: {result.success}")
            return result

        except CLINotFoundError:
            logger.error("Claude Code CLI not found - ensure claude-agent-sdk is installed")
            return CampaignSetupResult(
                success=False,
                campaign_id=campaign_id,
                error="Claude Code CLI not installed. Run: pip install claude-agent-sdk",
            )

        except ProcessError as e:
            logger.error(f"SDK process failed (exit {e.exit_code}): {e.stderr}")
            return CampaignSetupResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK process error (exit {e.exit_code}): {e.stderr}",
            )

        except CLIJSONDecodeError as e:
            logger.error(f"SDK JSON decode error on line: {e.line}")
            return CampaignSetupResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK JSON decode error: {e.original_error}",
            )

        except ClaudeSDKError as e:
            logger.error(f"Claude SDK error: {e}")
            return CampaignSetupResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK error: {e}",
            )

        except Exception as e:
            logger.error(f"Unexpected agent execution error: {e}")
            return CampaignSetupResult(
                success=False,
                campaign_id=campaign_id,
                error=str(e),
            )

    def _parse_agent_response(
        self,
        campaign_id: str,
        text_content: str,
    ) -> CampaignSetupResult:
        """
        Parse the agent's response text to extract the result.

        Args:
            campaign_id: The campaign ID.
            text_content: Collected text from agent response.

        Returns:
            CampaignSetupResult parsed from response.
        """
        # Try to find JSON in the response
        try:
            # Look for JSON object in text
            json_match = re.search(r"\{[^{}]*\}", text_content, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())

                return CampaignSetupResult(
                    success=result_data.get("success", False),
                    campaign_id=campaign_id,
                    instantly_campaign_id=result_data.get("instantly_campaign_id"),
                    campaign_name=result_data.get("campaign_name"),
                    leads_added=result_data.get("leads_added", 0),
                    sending_accounts=result_data.get("sending_accounts", 0),
                    warmup_enabled=result_data.get("warmup_enabled", False),
                    warmup_job_id=result_data.get("warmup_job_id"),
                    sequence_steps=result_data.get("sequence_steps", 0),
                    daily_limit=result_data.get("daily_limit", 0),
                    error=result_data.get("error"),
                    created_at=datetime.now(UTC),
                )
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Could not parse JSON from response: {e}")

        # If we couldn't parse, check for success indicators
        success_indicators = [
            "campaign_created",
            "setup complete",
            "successfully",
            "leads added",
        ]
        is_success = any(indicator in text_content.lower() for indicator in success_indicators)

        # Check for failure indicators
        failure_indicators = [
            "prerequisites fail",
            "error:",
            "failed",
            "not approved",
            "no leads",
            "no accounts",
        ]
        has_failure = any(indicator in text_content.lower() for indicator in failure_indicators)

        return CampaignSetupResult(
            success=is_success and not has_failure,
            campaign_id=campaign_id,
            error=None if is_success and not has_failure else "Could not parse agent response",
            created_at=datetime.now(UTC),
        )


async def run_campaign_setup(
    campaign_id: str,
    config: CampaignSetupConfig | None = None,
    sequence: list[EmailSequenceStep] | None = None,
    schedule: SendingSchedule | None = None,
) -> CampaignSetupResult:
    """
    Convenience function to run campaign setup.

    Args:
        campaign_id: UUID of the campaign to set up.
        config: Optional agent configuration.
        sequence: Optional custom email sequence.
        schedule: Optional custom sending schedule.

    Returns:
        CampaignSetupResult with success status and details.
    """
    agent = CampaignSetupAgent(config=config)
    return await agent.setup_campaign(
        campaign_id=campaign_id,
        sequence=sequence,
        schedule=schedule,
    )
