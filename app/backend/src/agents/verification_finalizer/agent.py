"""
Verification Finalizer Agent - Phase 3, Agent 3.3.

Finalizes the verification and enrichment phase, generates quality reports,
exports enriched lead data for review, and triggers human approval gate
before proceeding to personalization.

This agent uses Claude Agent SDK with SDK MCP tools for:
- Compiling verification statistics from database
- Generating quality reports
- Exporting leads to Google Sheets
- Sending Telegram notifications for approval

API Documentation:
- Google Sheets: https://developers.google.com/sheets/api/reference/rest
- Telegram: https://core.telegram.org/bots/api

Database Flow:
- READS: leads (email_status, lead_tier, lead_score, enrichment data)
- READS: campaigns, niches (campaign and niche metadata)
- WRITES: campaigns (verification_summary, verified_lead_list_url, status)
- WRITES: campaign_audit_log (verification completion event)

Handoff:
- Receives: campaign_id, emails_valid from Email Verification Agent (3.1)
- Triggers: Human Gate for Phase 4 approval (Telegram notification)
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

from src.agents.verification_finalizer.tools import (
    export_leads_to_sheets,
    generate_quality_report,
    get_campaign_verification_stats,
    send_approval_notification,
    update_campaign_verification_complete,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class VerificationFinalizerResult:
    """Result from verification finalizer execution."""

    success: bool
    campaign_id: str
    total_ready: int
    tier_a_ready: int
    tier_b_ready: int
    tier_c_ready: int
    sheets_url: str | None
    notification_sent: bool
    quality_score: float
    total_cost: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "total_ready": self.total_ready,
            "tier_a_ready": self.tier_a_ready,
            "tier_b_ready": self.tier_b_ready,
            "tier_c_ready": self.tier_c_ready,
            "sheets_url": self.sheets_url,
            "notification_sent": self.notification_sent,
            "quality_score": self.quality_score,
            "total_cost": self.total_cost,
            "error": self.error,
        }


# ============================================================================
# Verification Finalizer Agent
# ============================================================================


class VerificationFinalizerAgent:
    """
    Agent for finalizing Phase 3 verification and triggering approval gate.

    This agent:
    1. Compiles verification statistics from the database
    2. Generates a quality report
    3. Exports verified leads to Google Sheets
    4. Sends Telegram notification for human approval
    5. Updates campaign status to verification_complete

    Database Interactions:
    - INPUT: leads table (campaign_id, email_status, lead_tier, lead_score)
    - INPUT: campaigns, niches tables (campaign and niche metadata)
    - OUTPUT: campaigns table (verification_summary, verified_lead_list_url, status)
    - OUTPUT: campaign_audit_log table (verification completion event)

    Handoff Coordination:
    - Upstream: Email Verification Agent (3.1) provides campaign_id, emails_valid
    - Downstream: Human Gate → Phase 4 Personalization
    """

    def __init__(self) -> None:
        """Initialize the verification finalizer agent."""
        self.name = "verification_finalizer_agent"
        self.description = "Finalizes verification phase, exports leads, triggers approval gate"
        logger.info(f"Initialized {self.name}")

    @property
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        return """You are a verification quality specialist preparing leads for personalization.

Your responsibilities:
1. Compile verification and enrichment statistics
2. Generate quality assessment reports
3. Export verified leads to Google Sheets for human review
4. Send approval notifications via Telegram
5. Update campaign status when complete

Quality Checks:
- Only leads with valid email addresses are considered "ready"
- Tier A and B leads are prioritized for personalization
- Data quality score must be reasonable before proceeding

Export Requirements:
- Create clear summary with key metrics
- Organize leads by tier in separate sheets
- Include all enrichment data for review

When processing a campaign:
1. First call get_campaign_verification_stats to get all statistics
2. Then call generate_quality_report to create the report
3. Call export_leads_to_sheets to create the Google Sheets export
4. Call send_approval_notification to notify stakeholders
5. Finally call update_campaign_verification_complete to update status

Always complete all steps in order. Report any errors clearly."""

    async def finalize_verification(
        self,
        campaign_id: str,
        emails_valid: int | None = None,
    ) -> VerificationFinalizerResult:
        """
        Finalize verification for a campaign.

        This is the main entry point that orchestrates all steps:
        1. Get verification statistics
        2. Generate quality report
        3. Export to Google Sheets
        4. Send notification
        5. Update campaign status

        Args:
            campaign_id: The campaign UUID to finalize.
            emails_valid: Optional count of valid emails (from upstream agent).

        Returns:
            VerificationFinalizerResult with completion status.
        """
        logger.info(f"Starting verification finalization for campaign: {campaign_id}")

        # Create SDK MCP server with all tools
        sdk_server = create_sdk_mcp_server(
            name="verification_finalizer",
            version="2.0.0",
            tools=[
                get_campaign_verification_stats,
                generate_quality_report,
                export_leads_to_sheets,
                send_approval_notification,
                update_campaign_verification_complete,
            ],
        )

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"vf": sdk_server},
            allowed_tools=[
                "mcp__vf__get_campaign_verification_stats",
                "mcp__vf__generate_quality_report",
                "mcp__vf__export_leads_to_sheets",
                "mcp__vf__send_approval_notification",
                "mcp__vf__update_campaign_verification_complete",
            ],
            setting_sources=["project"],
            permission_mode="acceptEdits",
        )

        prompt = f"""Finalize verification for campaign {campaign_id}.

Execute these steps in order:
1. Get verification statistics using get_campaign_verification_stats
2. Generate quality report using generate_quality_report
3. Export leads to Google Sheets using export_leads_to_sheets
4. Send approval notification using send_approval_notification
5. Update campaign status using update_campaign_verification_complete

Report results for each step."""

        # Execute agent
        result = await self._execute_agent(prompt, options, campaign_id)

        if result.success:
            logger.info(
                f"Verification finalization complete for {campaign_id}: "
                f"{result.total_ready:,} leads ready, "
                f"quality score {result.quality_score:.0%}"
            )
        else:
            logger.error(f"Verification finalization failed for {campaign_id}: {result.error}")

        return result

    async def _execute_agent(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        campaign_id: str,
    ) -> VerificationFinalizerResult:
        """Execute the agent and collect results."""
        sheets_url: str | None = None
        notification_sent = False
        total_ready = 0
        tier_a_ready = 0
        tier_b_ready = 0
        tier_c_ready = 0
        quality_score = 0.0
        total_cost = 0.0
        last_error: str | None = None

        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Parse results from agent responses
                            text = block.text
                            logger.debug(f"Agent response: {text[:200]}...")

                            # Try to extract data from JSON responses
                            if "{" in text:
                                extracted = self._extract_json_data(text)
                                if extracted:
                                    sheets_url = extracted.get("spreadsheet_url") or sheets_url
                                    notification_sent = (
                                        extracted.get("sent", False) or notification_sent
                                    )

                                    # Extract report data
                                    if "total_ready" in extracted:
                                        total_ready = extracted.get("total_ready", 0)
                                    if "tier_a_ready" in extracted:
                                        tier_a_ready = extracted.get("tier_a_ready", 0)
                                    if "tier_b_ready" in extracted:
                                        tier_b_ready = extracted.get("tier_b_ready", 0)
                                    if "tier_c_ready" in extracted:
                                        tier_c_ready = extracted.get("tier_c_ready", 0)
                                    if "quality_scores" in extracted:
                                        scores = extracted.get("quality_scores", {})
                                        quality_score = scores.get("data_quality_score", 0)
                                    if "cost_summary" in extracted:
                                        costs = extracted.get("cost_summary", {})
                                        total_cost = costs.get("total_cost", 0)

                                    # Extract from tier breakdowns
                                    tier_breakdowns = extracted.get("tier_breakdowns", {})
                                    if tier_breakdowns:
                                        tier_a = tier_breakdowns.get("A", {})
                                        tier_b = tier_breakdowns.get("B", {})
                                        tier_c = tier_breakdowns.get("C", {})
                                        tier_a_ready = tier_a.get("ready", tier_a_ready)
                                        tier_b_ready = tier_b.get("ready", tier_b_ready)
                                        tier_c_ready = tier_c.get("ready", tier_c_ready)
                                        total_ready = tier_a_ready + tier_b_ready + tier_c_ready

                elif isinstance(message, ResultMessage) and message.is_error:
                    last_error = message.result or "Unknown error"
                    logger.error(f"Agent error: {last_error}")

            return VerificationFinalizerResult(
                success=sheets_url is not None,
                campaign_id=campaign_id,
                total_ready=total_ready,
                tier_a_ready=tier_a_ready,
                tier_b_ready=tier_b_ready,
                tier_c_ready=tier_c_ready,
                sheets_url=sheets_url,
                notification_sent=notification_sent,
                quality_score=quality_score,
                total_cost=total_cost,
                error=last_error,
            )

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return VerificationFinalizerResult(
                success=False,
                campaign_id=campaign_id,
                total_ready=0,
                tier_a_ready=0,
                tier_b_ready=0,
                tier_c_ready=0,
                sheets_url=None,
                notification_sent=False,
                quality_score=0.0,
                total_cost=0.0,
                error=str(e),
            )

    @staticmethod
    def _extract_json_data(text: str) -> dict[str, Any] | None:
        """Extract JSON data from text response."""
        try:
            # Find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                result: dict[str, Any] = json.loads(json_str)
                return result
        except json.JSONDecodeError:
            pass
        return None


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> None:
    """Main entry point for testing the agent."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m src.agents.verification_finalizer.agent <campaign_id>")
        sys.exit(1)

    campaign_id = sys.argv[1]

    agent = VerificationFinalizerAgent()
    result = await agent.finalize_verification(campaign_id)

    print("\n" + "=" * 60)
    print("Verification Finalization Result")
    print("=" * 60)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
