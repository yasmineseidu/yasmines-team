"""
Email Generation Agent - Phase 4, Agent 4.3.

Generates personalized cold emails using research data, persona insights,
and proven email frameworks. Creates subject lines, opening lines, body
copy, and CTAs tailored to each recipient.

This agent uses Claude Agent SDK with SDK MCP tools for:
- Loading campaign context (leads, research, personas)
- Generating personalized emails via LLM
- Scoring email quality
- Saving emails to database
- Updating campaign statistics

API Documentation:
- Anthropic: https://docs.anthropic.com/en/api

Database Flow:
- READS: leads, niches, personas, company_research_data, lead_research_data
- READS: personalization_library (proven opening lines)
- WRITES: generated_emails (new AI-generated emails)
- WRITES: leads (generated_email_id, email_generation_status)
- WRITES: campaigns (total_emails_generated, avg_email_quality)
- WRITES: personalization_library (high-quality lines, score >= 80)

Handoff:
- Receives: campaign_id from Lead Research Agent (4.2)
- Triggers: Personalization Finalizer Agent (4.4)
"""

import asyncio
import json
import logging
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

from src.agents.email_generation.schemas import EmailGenerationResult, TierConfig
from src.agents.email_generation.tools import (
    generate_email,
    generate_email_impl,
    load_campaign_context,
    save_generated_email,
    save_to_personalization_library,
    score_email_quality,
    update_campaign_email_stats,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Class
# =============================================================================


@dataclass
class EmailGenerationAgent:
    """
    Agent for generating personalized cold emails.

    This agent:
    1. Loads campaign context (leads, niche, personas)
    2. Generates emails per tier (A, B, C in parallel)
    3. Scores quality and regenerates if below threshold
    4. Saves emails to database
    5. Updates campaign statistics

    Database Interactions:
    - INPUT: leads, niches, personas, research tables
    - OUTPUT: generated_emails, leads (status), campaigns (stats)

    Handoff Coordination:
    - Upstream: Lead Research Agent (4.2) provides campaign_id
    - Downstream: Personalization Finalizer Agent (4.4)
    """

    name: str = "email_generation_agent"
    description: str = "Generates personalized cold emails using AI"

    # Tier configurations
    tier_configs: dict[str, TierConfig] = field(
        default_factory=lambda: {
            "A": TierConfig.tier_a(),
            "B": TierConfig.tier_b(),
            "C": TierConfig.tier_c(),
        }
    )

    # Statistics tracking
    _stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the agent."""
        logger.info(f"Initialized {self.name}")
        self._reset_stats()

    def _reset_stats(self) -> None:
        """Reset statistics for a new run."""
        self._stats = {
            "total_generated": 0,
            "tier_a_generated": 0,
            "tier_b_generated": 0,
            "tier_c_generated": 0,
            "quality_scores": [],
            "regeneration_attempts": 0,
            "regeneration_improved": 0,
            "lines_saved_to_library": 0,
            "framework_usage": {},
        }

    @property
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        return """You are an expert cold email copywriter specializing in B2B outreach.

Your responsibilities:
1. Load campaign context including leads, personas, and research data
2. Generate personalized emails for each lead using appropriate frameworks
3. Score email quality and regenerate if below threshold
4. Save successful emails to the database
5. Update campaign statistics when complete

Email Framework Selection:
- Tier A leads: Use PAS (Pain-Agitate-Solution) or BAB (Before-After-Bridge)
- Tier B leads: Use BAB or AIDA (Attention-Interest-Desire-Action)
- Tier C leads: Use AIDA or Question-Based framework

Quality Requirements:
- Tier A: Quality score >= 70, regenerate up to 3 times
- Tier B: Quality score >= 60, regenerate up to 2 times
- Tier C: Quality score >= 50, accept as-is

Writing Principles:
- Sound human, not like AI
- Be specific, not generic
- Focus on THEIR problems, not your features
- Short sentences, easy to read
- One clear CTA (soft ask)

AVOID:
- "I hope this email finds you well"
- "I'd love to pick your brain"
- Starting with "My name is..."
- Excessive flattery
- Long paragraphs

When processing:
1. First load_campaign_context to get all leads and context
2. For each lead, call generate_email with persona context
3. If quality score below threshold, regenerate (up to max attempts)
4. Save successful emails with save_generated_email
5. Save high-quality opening lines (score >= 80) to library
6. Finally call update_campaign_email_stats

Always complete all leads before finishing."""

    async def generate_emails(
        self,
        campaign_id: str,
    ) -> EmailGenerationResult:
        """
        Generate emails for all leads in a campaign.

        This is the main entry point that orchestrates:
        1. Load campaign context
        2. Process leads by tier
        3. Generate, score, regenerate as needed
        4. Save emails and update stats

        Args:
            campaign_id: The campaign UUID to generate emails for.

        Returns:
            EmailGenerationResult with completion statistics.
        """
        logger.info(f"Starting email generation for campaign: {campaign_id}")
        self._reset_stats()

        # Create SDK MCP server with all tools
        sdk_server = create_sdk_mcp_server(
            name="email_generation",
            version="2.1.0",
            tools=[
                load_campaign_context,
                generate_email,
                score_email_quality,
                save_generated_email,
                save_to_personalization_library,
                update_campaign_email_stats,
            ],
        )

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"eg": sdk_server},
            allowed_tools=[
                "mcp__eg__load_campaign_context",
                "mcp__eg__generate_email",
                "mcp__eg__score_email_quality",
                "mcp__eg__save_generated_email",
                "mcp__eg__save_to_personalization_library",
                "mcp__eg__update_campaign_email_stats",
            ],
            setting_sources=["project"],
            permission_mode="acceptEdits",
        )

        prompt = f"""Generate personalized cold emails for campaign {campaign_id}.

Execute these steps:
1. Load campaign context using load_campaign_context
2. For EACH lead in the context:
   a. Generate email using generate_email with appropriate framework for tier
   b. Check quality score - if below threshold for tier, regenerate
   c. Save the final email using save_generated_email
   d. If quality score >= 80, save opening line to library
3. After processing all leads, call update_campaign_email_stats

Process leads by tier (A, then B, then C).
Report progress as you work."""

        # Execute agent
        result = await self._execute_agent(prompt, options, campaign_id)

        if result.success:
            logger.info(
                f"Email generation complete for {campaign_id}: "
                f"{result.total_generated} emails, "
                f"avg score {result.avg_quality_score:.1f}"
            )
        else:
            logger.error(f"Email generation failed for {campaign_id}: {result.error}")

        return result

    async def _execute_agent(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        campaign_id: str,
    ) -> EmailGenerationResult:
        """Execute the agent and collect results."""
        last_error: str | None = None

        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            text = block.text
                            logger.debug(f"Agent response: {text[:200]}...")

                            # Try to extract statistics from JSON responses
                            if "{" in text:
                                extracted = self._extract_json_data(text)
                                if extracted:
                                    self._update_stats_from_response(extracted)

                elif isinstance(message, ResultMessage) and message.is_error:
                    last_error = message.result or "Unknown error"
                    logger.error(f"Agent error: {last_error}")

            # Calculate final statistics
            avg_quality = (
                sum(self._stats["quality_scores"]) / len(self._stats["quality_scores"])
                if self._stats["quality_scores"]
                else 0.0
            )

            # Build quality distribution
            quality_dist = {
                "excellent_85plus": sum(1 for s in self._stats["quality_scores"] if s >= 85),
                "good_70_84": sum(1 for s in self._stats["quality_scores"] if 70 <= s < 85),
                "acceptable_55_69": sum(1 for s in self._stats["quality_scores"] if 55 <= s < 70),
                "below_55": sum(1 for s in self._stats["quality_scores"] if s < 55),
            }

            return EmailGenerationResult(
                success=self._stats["total_generated"] > 0,
                campaign_id=campaign_id,
                total_generated=self._stats["total_generated"],
                tier_a_generated=self._stats["tier_a_generated"],
                tier_b_generated=self._stats["tier_b_generated"],
                tier_c_generated=self._stats["tier_c_generated"],
                avg_quality_score=avg_quality,
                quality_distribution=quality_dist,
                framework_usage=self._stats["framework_usage"],
                regeneration_stats={
                    "attempted": self._stats["regeneration_attempts"],
                    "improved": self._stats["regeneration_improved"],
                },
                lines_saved_to_library=self._stats["lines_saved_to_library"],
                error=last_error,
            )

        except CLINotFoundError:
            logger.error("Claude Code CLI not found. Ensure claude-agent-sdk is installed.")
            return EmailGenerationResult(
                success=False,
                campaign_id=campaign_id,
                error="Claude Code CLI not installed",
            )
        except ProcessError as e:
            logger.error(f"SDK process failed (exit {e.exit_code}): {e.stderr}")
            return EmailGenerationResult(
                success=False,
                campaign_id=campaign_id,
                error=f"Process error (exit {e.exit_code}): {e.stderr[:200] if e.stderr else 'unknown'}",
            )
        except CLIJSONDecodeError as e:
            logger.error(f"SDK JSON decode error on line: {e.line}")
            return EmailGenerationResult(
                success=False,
                campaign_id=campaign_id,
                error=f"JSON decode error: {e}",
            )
        except ClaudeSDKError as e:
            logger.error(f"Claude SDK error: {e}")
            return EmailGenerationResult(
                success=False,
                campaign_id=campaign_id,
                error=f"SDK error: {e}",
            )
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return EmailGenerationResult(
                success=False,
                campaign_id=campaign_id,
                error=str(e),
            )

    def _update_stats_from_response(self, data: dict[str, Any]) -> None:
        """Update statistics from agent response data."""
        # Track quality score
        if "quality_score" in data:
            score = data["quality_score"]
            if isinstance(score, int | float):
                self._stats["quality_scores"].append(score)

        # Track generated email
        if "email" in data or "email_id" in data:
            self._stats["total_generated"] += 1

        # Track framework usage
        if "framework" in data:
            framework = data["framework"]
            self._stats["framework_usage"][framework] = (
                self._stats["framework_usage"].get(framework, 0) + 1
            )

        # Track tier stats from campaign update
        if "tier_a_generated" in data:
            self._stats["tier_a_generated"] = data["tier_a_generated"]
        if "tier_b_generated" in data:
            self._stats["tier_b_generated"] = data["tier_b_generated"]
        if "tier_c_generated" in data:
            self._stats["tier_c_generated"] = data["tier_c_generated"]

        # Track library saves
        if data.get("saved") is True and "line_id" in data:
            self._stats["lines_saved_to_library"] += 1

    @staticmethod
    def _extract_json_data(text: str) -> dict[str, Any] | None:
        """Extract JSON data from text response."""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                result: dict[str, Any] = json.loads(json_str)
                return result
        except json.JSONDecodeError:
            pass
        return None


# =============================================================================
# Direct Generation (Batch Processing)
# =============================================================================


class DirectEmailGenerator:
    """
    Direct email generator for batch processing without agent orchestration.

    Use this for high-volume email generation where agent overhead is
    unnecessary. Directly calls the LLM and scoring functions.
    """

    def __init__(self) -> None:
        """Initialize the direct generator."""
        self.name = "direct_email_generator"
        logger.info(f"Initialized {self.name}")

    async def generate_batch(
        self,
        leads: list[dict[str, Any]],
        persona_context: dict[str, Any],
        niche_context: dict[str, Any],
        campaign_id: str,
        concurrency: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Generate emails for a batch of leads concurrently.

        Args:
            leads: List of lead dictionaries.
            persona_context: Persona messaging context.
            niche_context: Niche pain points and value props.
            campaign_id: Campaign UUID.
            concurrency: Max concurrent generations.

        Returns:
            List of generated email results.
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def generate_one(lead: dict[str, Any]) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    # Call generate_email tool with args dict (SDK pattern)
                    args = {
                        "lead_id": lead.get("id", ""),
                        "campaign_id": campaign_id,
                        "first_name": lead.get("first_name", ""),
                        "last_name": lead.get("last_name", ""),
                        "title": lead.get("title", ""),
                        "company_name": lead.get("company_name", ""),
                        "lead_tier": lead.get("lead_tier", "C"),
                        "persona_challenges": ",".join(persona_context.get("challenges", [])),
                        "persona_goals": ",".join(persona_context.get("goals", [])),
                        "messaging_tone": persona_context.get("messaging_tone", "professional"),
                        "lead_research_json": json.dumps(lead.get("lead_research"))
                        if lead.get("lead_research")
                        else None,
                        "company_research_json": json.dumps(lead.get("company_research"))
                        if lead.get("company_research")
                        else None,
                        "company_research_id": lead.get("company_research_id"),
                        "lead_research_id": lead.get("lead_research_id"),
                    }
                    result = await generate_email_impl(args)

                    if not result.get("is_error"):
                        # Parse response
                        content = result.get("content", [{}])[0]
                        text = content.get("text", "{}")
                        parsed: dict[str, Any] = json.loads(text)
                        return parsed
                    return None

                except Exception as e:
                    logger.warning(f"Failed to generate email for lead {lead.get('id')}: {e}")
                    return None

        # Generate concurrently
        tasks = [generate_one(lead) for lead in leads]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, dict):
                results.append(result)

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

    if len(sys.argv) < 2:
        print("Usage: python -m src.agents.email_generation.agent <campaign_id>")
        sys.exit(1)

    campaign_id = sys.argv[1]

    agent = EmailGenerationAgent()
    result = await agent.generate_emails(campaign_id)

    print("\n" + "=" * 60)
    print("Email Generation Result")
    print("=" * 60)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
