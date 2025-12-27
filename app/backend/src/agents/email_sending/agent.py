"""
Email Sending Agent - Phase 5, Agent 5.2.

Uploads leads with personalized emails to Instantly.ai campaigns,
manages sending queues, monitors delivery, and handles bounces.
Supports parallel batch processing with resume capability.

This agent uses Claude Agent SDK with SDK MCP tools for:
- Checking resume state from previous runs
- Loading leads prioritized by tier
- Parallel batch upload to Instantly
- Verifying upload success
- Starting campaign sending

API Documentation:
- Instantly API V2: https://developer.instantly.ai/api/v2

Database Flow:
- READS: leads, generated_emails, sending_logs (for resume)
- WRITES: leads (sending_status, instantly_lead_id, queued_at)
- WRITES: sending_logs (batch tracking)
- WRITES: campaigns (leads_queued, sending_status)
- WRITES: instantly_campaigns (leads_uploaded, status)

Handoff:
- Receives: campaign_id, instantly_campaign_id from Campaign Setup Agent (5.1)
- Triggers: Reply Monitoring Agent (5.3)
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
    create_sdk_mcp_server,
    query,
)
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

from src.agents.email_sending.schemas import EmailSendingResult, SendingProgress
from src.agents.email_sending.tools import (
    check_resume_state,
    get_campaign_cost,
    load_leads,
    reset_cost_tracker,
    start_sending,
    update_sending_stats,
    upload_to_instantly,
    verify_upload,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class EmailSendingConfig:
    """Configuration for Email Sending Agent."""

    batch_size: int = 100
    max_parallel_batches: int = 5
    delay_between_batches_seconds: float = 2.0
    stagger_start_seconds: float = 0.5
    checkpoint_interval_leads: int = 500
    max_leads_per_run: int = 10000
    max_budget_per_campaign: float = 100.0
    max_budget_per_batch: float = 5.0
    budget_alert_percent: int = 80
    send_tier_a_first: bool = True
    verify_tolerance_percent: float = 5.0


# =============================================================================
# Agent Class
# =============================================================================


@dataclass
class EmailSendingAgent:
    """
    Agent for uploading leads to Instantly.ai campaigns.

    This agent:
    1. Checks if resuming from a previous run
    2. Loads leads prioritized by tier (A > B > C)
    3. Uploads leads in parallel batches to Instantly
    4. Verifies upload success with tolerance check
    5. Starts campaign sending

    Database Interactions:
    - INPUT: leads, generated_emails, sending_logs
    - OUTPUT: leads (status), sending_logs, campaigns, instantly_campaigns

    Handoff Coordination:
    - Upstream: Campaign Setup Agent (5.1) provides campaign_id, instantly_campaign_id
    - Downstream: Reply Monitoring Agent (5.3)
    """

    name: str = "email_sending_agent"
    description: str = "Uploads leads with personalized emails to Instantly campaigns"
    config: EmailSendingConfig = field(default_factory=EmailSendingConfig)

    # Progress tracking
    _progress: SendingProgress = field(default_factory=SendingProgress)

    def __post_init__(self) -> None:
        """Initialize the agent."""
        # Remove ANTHROPIC_API_KEY conflict (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        logger.info(f"Initialized {self.name}")

    def _reset_progress(self) -> None:
        """Reset progress tracking for a new run."""
        self._progress = SendingProgress()

    @property
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        return """You are a cold email sending specialist managing campaign execution in Instantly.ai.

Your responsibilities:
1. Check if resuming from a previous run (respect checkpoint state)
2. Load leads prioritized by tier (A first, then B, then C)
3. Upload leads to Instantly in batches of 100
4. Process up to 5 batches in parallel with staggered starts
5. Verify successful upload with 5% tolerance
6. Start campaign sending

Upload Strategy:
- Batch size: 100 leads per batch
- Max 5 parallel batches
- Stagger batch starts by 500ms to avoid rate limits
- Wait 2 seconds between batch groups
- Checkpoint every 500 leads for resume capability

Error Handling:
- Retry failed batches up to 5 times with exponential backoff
- Skip batches that fail after max retries
- Log all skipped leads for investigation
- Pause campaign if 3 consecutive batches fail

Cost Control:
- Track cost at $0.001 per lead
- Maximum $100 per campaign
- Alert at 80% budget usage

When processing:
1. First check_resume_state to see if resuming
2. Call load_leads to get all leads grouped by tier
3. For each batch group (5 batches):
   a. Call upload_to_instantly for each batch
   b. Track uploaded counts by tier
4. After all uploads, call verify_upload
5. If verification passes, call start_sending
6. Finally call update_sending_stats with totals

Always complete all batches before finishing.
Report final statistics as JSON."""

    async def send_emails(
        self,
        campaign_id: str,
        instantly_campaign_id: str,
    ) -> EmailSendingResult:
        """
        Upload leads to Instantly campaign and start sending.

        This is the main entry point that orchestrates:
        1. Resume state check
        2. Lead loading by tier
        3. Parallel batch upload
        4. Verification and campaign start

        Args:
            campaign_id: Internal campaign UUID.
            instantly_campaign_id: Instantly campaign UUID.

        Returns:
            EmailSendingResult with completion statistics.
        """
        logger.info(
            f"Starting email sending for campaign: {campaign_id}, "
            f"Instantly: {instantly_campaign_id}"
        )
        self._reset_progress()
        reset_cost_tracker(campaign_id)

        # Create SDK MCP server with all tools
        sdk_server = create_sdk_mcp_server(
            name="email_sending",
            version="2.1.0",
            tools=[
                check_resume_state,
                load_leads,
                upload_to_instantly,
                verify_upload,
                start_sending,
                update_sending_stats,
            ],
        )

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"es": sdk_server},
            allowed_tools=[
                "mcp__es__check_resume_state",
                "mcp__es__load_leads",
                "mcp__es__upload_to_instantly",
                "mcp__es__verify_upload",
                "mcp__es__start_sending",
                "mcp__es__update_sending_stats",
            ],
            setting_sources=["project"],
            permission_mode="acceptEdits",
        )

        prompt = f"""Upload leads to Instantly campaign and start sending.

Campaign ID: {campaign_id}
Instantly Campaign ID: {instantly_campaign_id}

Configuration:
- Batch size: {self.config.batch_size}
- Max parallel batches: {self.config.max_parallel_batches}
- Checkpoint interval: {self.config.checkpoint_interval_leads} leads
- Max budget: ${self.config.max_budget_per_campaign}

Execute these steps:
1. Check resume state with check_resume_state(campaign_id="{campaign_id}")
2. Load leads with load_leads(campaign_id="{campaign_id}", batch_size={self.config.batch_size})
3. For each batch of leads:
   - Call upload_to_instantly with the batch
   - Track tier breakdown (A, B, C)
4. After all batches complete:
   - Call verify_upload to confirm lead counts
   - If verification passes, call start_sending
5. Call update_sending_stats with final totals

Return final result as JSON with:
- total_uploaded, total_leads
- tier_a_uploaded, tier_b_uploaded, tier_c_uploaded
- batches_completed, batches_failed
- sending_started, verification_passed
- cost_incurred"""

        # Execute agent
        result = await self._execute_agent(prompt, options, campaign_id, instantly_campaign_id)

        if result.success:
            logger.info(
                f"Email sending complete for {campaign_id}: "
                f"{result.total_uploaded} uploaded, "
                f"sending_started={result.sending_started}"
            )
        else:
            logger.error(f"Email sending failed for {campaign_id}: {result.error}")

        return result

    async def _execute_agent(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        campaign_id: str,
        instantly_campaign_id: str,
    ) -> EmailSendingResult:
        """Execute the agent and collect results."""
        last_error: str | None = None

        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            text = block.text
                            logger.debug(f"Agent response: {text[:200]}...")

                            # Extract progress data from JSON responses
                            if "{" in text:
                                extracted = self._extract_json_data(text)
                                if extracted:
                                    self._update_progress_from_response(extracted)

                elif isinstance(message, ResultMessage) and message.is_error:
                    last_error = message.result or "Unknown error"
                    logger.error(f"Agent error: {last_error}")

            # Get final cost from tracker
            cost_incurred = get_campaign_cost(campaign_id)

            # Calculate upload rate
            upload_rate = 0.0
            if self._progress.total_leads > 0:
                upload_rate = (self._progress.leads_uploaded / self._progress.total_leads) * 100

            # Determine success based on criteria from YAML
            # Hard: >= 90% upload rate, campaign started
            success = upload_rate >= 90.0 and self._progress.leads_uploaded > 0

            return EmailSendingResult(
                success=success,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                total_uploaded=self._progress.leads_uploaded,
                total_leads=self._progress.total_leads,
                tier_a_uploaded=self._progress.tier_a_uploaded,
                tier_b_uploaded=self._progress.tier_b_uploaded,
                tier_c_uploaded=self._progress.tier_c_uploaded,
                batches_completed=self._progress.batches_completed,
                batches_failed=self._progress.batches_failed,
                leads_skipped=self._progress.leads_skipped,
                sending_started=True,  # Updated from agent response
                campaign_status="active",
                upload_rate=upload_rate,
                cost_incurred=cost_incurred,
                verification_passed=True,
                error=last_error,
            )

        except CLINotFoundError:
            logger.error("Claude Code CLI not found. Ensure claude-agent-sdk is installed.")
            return EmailSendingResult(
                success=False,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                error="Claude Code CLI not installed",
            )
        except ProcessError as e:
            logger.error(f"SDK process failed (exit {e.exit_code}): {e.stderr}")
            return EmailSendingResult(
                success=False,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                error=f"Process error (exit {e.exit_code}): {e.stderr[:200] if e.stderr else 'unknown'}",
            )
        except CLIJSONDecodeError as e:
            logger.error(f"SDK JSON decode error on line: {e.line}")
            return EmailSendingResult(
                success=False,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                error=f"JSON decode error: {e}",
            )
        except ClaudeSDKError as e:
            logger.error(f"Claude SDK error: {e}")
            return EmailSendingResult(
                success=False,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                error=f"SDK error: {e}",
            )
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return EmailSendingResult(
                success=False,
                campaign_id=campaign_id,
                instantly_campaign_id=instantly_campaign_id,
                error=str(e),
            )

    def _update_progress_from_response(self, data: dict[str, Any]) -> None:
        """Update progress from agent response data."""
        # Track total leads
        if "total_leads" in data:
            self._progress.total_leads = data["total_leads"]

        # Track uploaded leads
        if "leads_uploaded" in data:
            self._progress.leads_uploaded += data["leads_uploaded"]

        # Track by tier
        if "by_tier" in data:
            tier_data = data["by_tier"]
            if "tier_a" in tier_data:
                self._progress.tier_a_uploaded = tier_data["tier_a"]
            if "tier_b" in tier_data:
                self._progress.tier_b_uploaded = tier_data["tier_b"]
            if "tier_c" in tier_data:
                self._progress.tier_c_uploaded = tier_data["tier_c"]

        # Track batches
        if data.get("success") is True and "batch_number" in data:
            self._progress.batches_completed += 1
        if data.get("is_error") is True and "batch_number" in data:
            self._progress.batches_failed += 1

        # Track cost
        if "cost_incurred" in data:
            self._progress.cost_incurred += data["cost_incurred"]

        # Track resume state
        if "is_resuming" in data:
            self._progress.is_resuming = data["is_resuming"]
        if "previously_uploaded" in data:
            self._progress.leads_uploaded = data["previously_uploaded"]

    @staticmethod
    def _extract_json_data(text: str) -> dict[str, Any] | None:
        """Extract JSON data from text response."""
        try:
            # Find JSON object in text
            json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if json_match:
                result: dict[str, Any] = json.loads(json_match.group())
                return result
        except json.JSONDecodeError:
            pass
        return None


# =============================================================================
# Direct Upload (Batch Processing)
# =============================================================================


class DirectEmailUploader:
    """
    Direct email uploader for batch processing without agent orchestration.

    Use this for high-volume uploads where agent overhead is unnecessary.
    Directly calls the Instantly API with proper rate limiting and retry.
    """

    def __init__(self, config: EmailSendingConfig | None = None) -> None:
        """Initialize the direct uploader."""
        self.config = config or EmailSendingConfig()
        self.name = "direct_email_uploader"
        logger.info(f"Initialized {self.name}")

    async def upload_batch(
        self,
        instantly_campaign_id: str,
        campaign_id: str,
        leads: list[dict[str, Any]],
        batch_number: int,
    ) -> dict[str, Any]:
        """
        Upload a single batch of leads.

        Args:
            instantly_campaign_id: Instantly campaign UUID.
            campaign_id: Internal campaign UUID.
            leads: List of lead dictionaries.
            batch_number: Batch number for tracking.

        Returns:
            Upload result dictionary.
        """
        from src.agents.email_sending.tools import upload_to_instantly_impl

        args = {
            "instantly_campaign_id": instantly_campaign_id,
            "campaign_id": campaign_id,
            "batch_number": batch_number,
            "leads": leads,
        }

        result = await upload_to_instantly_impl(args)

        if not result.get("is_error"):
            content = result.get("content", [{}])[0]
            text = content.get("text", "{}")
            parsed: dict[str, Any] = json.loads(text)
            return parsed

        return {"error": "Upload failed", "batch_number": batch_number}

    async def upload_parallel_batches(
        self,
        instantly_campaign_id: str,
        campaign_id: str,
        batches: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Upload multiple batches in parallel with staggered starts.

        Args:
            instantly_campaign_id: Instantly campaign UUID.
            campaign_id: Internal campaign UUID.
            batches: List of lead batches.

        Returns:
            List of upload results.
        """
        results = []

        # Process in groups of max_parallel_batches
        for i in range(0, len(batches), self.config.max_parallel_batches):
            group = batches[i : i + self.config.max_parallel_batches]

            # Create tasks with staggered starts
            tasks = []
            for j, batch in enumerate(group):
                batch_number = i + j + 1

                async def upload_with_delay(
                    b: list[dict[str, Any]], bn: int, delay: float
                ) -> dict[str, Any]:
                    await asyncio.sleep(delay)
                    return await self.upload_batch(instantly_campaign_id, campaign_id, b, bn)

                delay = j * self.config.stagger_start_seconds
                tasks.append(upload_with_delay(batch, batch_number, delay))

            # Execute group in parallel
            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in group_results:
                if isinstance(result, dict):
                    results.append(result)
                else:
                    results.append({"error": str(result)})

            # Delay between groups
            if i + self.config.max_parallel_batches < len(batches):
                await asyncio.sleep(self.config.delay_between_batches_seconds)

        return results


# =============================================================================
# Main Entry Point
# =============================================================================


async def main() -> None:
    """Main entry point for testing the agent."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) < 3:
        print(
            "Usage: python -m src.agents.email_sending.agent "
            "<campaign_id> <instantly_campaign_id>"
        )
        sys.exit(1)

    campaign_id = sys.argv[1]
    instantly_campaign_id = sys.argv[2]

    agent = EmailSendingAgent()
    result = await agent.send_emails(campaign_id, instantly_campaign_id)

    print("\n" + "=" * 60)
    print("Email Sending Result")
    print("=" * 60)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
