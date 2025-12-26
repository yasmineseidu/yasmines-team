"""
Personalization Finalizer Agent (Phase 4.4).

Compiles personalization statistics, exports email samples to Google Sheets
for human review, and sends approval notifications before Phase 5.

This is the final agent in Phase 4 (Research & Personalization).
It creates a human gate before proceeding to Phase 5 (Campaign Execution).
"""

import json
import logging
import os
import re
from dataclasses import dataclass

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

from src.agents.personalization_finalizer.reports import (
    PersonalizationFinalizerResult,
)
from src.agents.personalization_finalizer.tools import (
    export_emails_to_sheets,
    generate_personalization_report,
    get_email_samples,
    get_personalization_stats,
    send_phase4_approval_notification,
    update_campaign_personalization_complete,
)

logger = logging.getLogger(__name__)


@dataclass
class PersonalizationFinalizerConfig:
    """Configuration for Personalization Finalizer Agent."""

    samples_per_tier: int = 5
    send_notification: bool = True
    notification_chat_id: str | None = None


class PersonalizationFinalizerAgent:
    """
    Agent 4.4: Personalization Finalizer.

    Compiles personalization statistics from generated emails,
    exports email samples to Google Sheets for human review,
    and sends approval notifications via Telegram.

    Database Interactions:
    - Input: generated_emails table (from Agent 4.3 Email Generation)
    - Output: campaigns table (email_samples_url, personalization_summary)
    - Status: Updates campaign to personalization_complete

    Handoff: Triggers human gate for Phase 5 (Campaign Execution) approval.
    """

    SYSTEM_PROMPT = """You are a Personalization Finalizer agent responsible for Phase 4 completion.

Your task is to:
1. Compile personalization statistics for a campaign's generated emails
2. Generate a comprehensive personalization report
3. Export email samples to Google Sheets for human review
4. Send a notification about completion (if enabled)
5. Update the campaign status to personalization_complete

You have access to tools for querying email data, generating reports,
exporting to Google Sheets, sending Telegram notifications, and updating campaigns.

IMPORTANT: Execute tools in the correct order:
1. First, get personalization stats
2. Then, generate the report from those stats
3. Get email samples for each tier
4. Export samples to Google Sheets
5. Optionally send notification
6. Finally, update campaign status

Always provide the final result as JSON with these fields:
- success: boolean
- campaign_id: string
- sheets_url: string (if exported)
- total_emails: number
- avg_quality: number
- notification_sent: boolean
- error: string (if any error occurred)
"""

    def __init__(
        self,
        config: PersonalizationFinalizerConfig | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """
        Initialize Personalization Finalizer Agent.

        Args:
            config: Agent configuration.
            model: Claude model to use.
        """
        self.config = config or PersonalizationFinalizerConfig()
        self.model = model

        # Remove ANTHROPIC_API_KEY conflict (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        logger.info("Initialized PersonalizationFinalizerAgent")

    async def finalize_personalization(
        self,
        campaign_id: str,
    ) -> PersonalizationFinalizerResult:
        """
        Execute personalization finalization for a campaign.

        Args:
            campaign_id: UUID of the campaign to finalize.

        Returns:
            PersonalizationFinalizerResult with success status and details.
        """
        logger.info(f"Starting personalization finalization for campaign {campaign_id}")

        # Create SDK MCP server with all tools
        sdk_server = create_sdk_mcp_server(
            name="personalization_finalizer",
            version="1.0.0",
            tools=[
                get_personalization_stats,
                generate_personalization_report,
                get_email_samples,
                export_emails_to_sheets,
                send_phase4_approval_notification,
                update_campaign_personalization_complete,
            ],
        )

        # Build user message
        notification_line = ""
        if self.config.notification_chat_id:
            notification_line = f"- Notification chat ID: {self.config.notification_chat_id}"

        user_message = f"""Finalize personalization for campaign: {campaign_id}

Configuration:
- Samples per tier: {self.config.samples_per_tier}
- Send notification: {self.config.send_notification}
{notification_line}

Execute the following steps:
1. Get personalization stats for campaign {campaign_id}
2. Generate personalization report from the stats
3. Get email samples ({self.config.samples_per_tier} per tier)
4. Export email samples to Google Sheets
5. {"Send approval notification via Telegram" if self.config.send_notification else "Skip notification (disabled)"}
6. Update campaign status to personalization_complete

Return the final result as JSON."""

        # Configure agent options
        options = ClaudeAgentOptions(
            system_prompt=self.SYSTEM_PROMPT,
            mcp_servers={"pf": sdk_server},
            allowed_tools=[
                "mcp__pf__get_personalization_stats",
                "mcp__pf__generate_personalization_report",
                "mcp__pf__get_email_samples",
                "mcp__pf__export_emails_to_sheets",
                "mcp__pf__send_phase4_approval_notification",
                "mcp__pf__update_campaign_personalization_complete",
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
            logger.info(f"Personalization finalization complete: {result.success}")
            return result

        except CLINotFoundError:
            logger.error("Claude Code CLI not found - ensure claude-agent-sdk is installed")
            return PersonalizationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                error="Claude Code CLI not installed. Run: pip install claude-agent-sdk",
            )

        except ProcessError as e:
            logger.error(f"SDK process failed (exit {e.exit_code}): {e.stderr}")
            return PersonalizationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK process error (exit {e.exit_code}): {e.stderr}",
            )

        except CLIJSONDecodeError as e:
            logger.error(f"SDK JSON decode error on line: {e.line}")
            return PersonalizationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK JSON decode error: {e.original_error}",
            )

        except ClaudeSDKError as e:
            logger.error(f"Claude SDK error: {e}")
            return PersonalizationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK error: {e}",
            )

        except Exception as e:
            logger.error(f"Unexpected agent execution error: {e}")
            return PersonalizationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                error=str(e),
            )

    def _parse_agent_response(
        self,
        campaign_id: str,
        text_content: str,
    ) -> PersonalizationFinalizerResult:
        """
        Parse the agent's response text to extract the result.

        Args:
            campaign_id: The campaign ID.
            text_content: Collected text from agent response.

        Returns:
            PersonalizationFinalizerResult parsed from response.
        """
        # Try to find JSON in the response
        try:
            # Look for JSON object in text
            json_match = re.search(r"\{[^{}]*\}", text_content, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())

                return PersonalizationFinalizerResult(
                    success=result_data.get("success", False),
                    campaign_id=campaign_id,
                    sheets_url=result_data.get("sheets_url"),
                    sheets_id=result_data.get("sheets_id"),
                    notification_sent=result_data.get("notification_sent", False),
                    notification_message_id=result_data.get("notification_message_id"),
                    error=result_data.get("error"),
                )
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Could not parse JSON from response: {e}")

        # If we couldn't parse, check for success indicators
        success_indicators = [
            "personalization_complete",
            "successfully",
            "exported to google sheets",
            "update successful",
        ]
        is_success = any(indicator in text_content.lower() for indicator in success_indicators)

        return PersonalizationFinalizerResult(
            success=is_success,
            campaign_id=campaign_id,
            error=None if is_success else "Could not parse agent response",
        )


async def run_personalization_finalizer(
    campaign_id: str,
    config: PersonalizationFinalizerConfig | None = None,
) -> PersonalizationFinalizerResult:
    """
    Convenience function to run personalization finalization.

    Args:
        campaign_id: UUID of the campaign to finalize.
        config: Optional configuration.

    Returns:
        PersonalizationFinalizerResult with success status and details.
    """
    agent = PersonalizationFinalizerAgent(config=config)
    return await agent.finalize_personalization(campaign_id)
