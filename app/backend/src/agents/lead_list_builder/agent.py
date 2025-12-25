"""
Lead List Builder Agent - Phase 2, Agent 2.1.

Uses Claude Agent SDK with Apify actors to scrape leads using a
cost-effective waterfall pattern:

1. Leads Finder Primary ($1.5/1k leads with emails) - IoSHqwTR9YGhzccez
2. Leads Scraper PPE (fallback) - T1XDXWc1L92AfIJtd
3. Leads Scraper Multi (last resort) - VYRyEF4ygTTkaIghe

This agent receives persona and niche data from Phase 1 and builds
targeted lead lists based on job titles, industries, and company sizes.

Phase 2 Pipeline Position:
Input: Niche + Persona data from Phase 1 → Output: Raw leads for validation

Per LEARN-007: This agent is pure (no side effects). The orchestrator
handles all database persistence.

Database Interactions:
=====================

1. INPUT: Via function parameters (no direct DB reads)
   - Source Agent: Niche Research Agent (Phase 1.1), Persona Research Agent (Phase 1.2)
   - Required Fields: job_titles, industries, company_sizes, locations, seniority_levels
   - Data Format: Lists of strings for each criteria
   - Handoff Method: Direct function call from Phase 1 Orchestrator

2. OUTPUT: LeadListBuilderResult (returned to orchestrator)
   - Target Agent(s): Data Validation Agent (Phase 2.2)
   - Written Fields: leads[], total_scraped, primary_actor_leads, fallback_actor_leads,
                     total_cost_usd, apify_runs[], errors[], warnings[]
   - Data Format: LeadListBuilderResult dataclass with leads as list[dict]
   - Handoff Method: Return value to orchestrator (orchestrator persists to `leads` table)

3. HANDOFF COORDINATION:
   - Upstream Dependencies: [niche_research_agent, persona_research_agent]
   - Downstream Consumers: [data_validation_agent, duplicate_detection_agent]
   - Failure Handling: Returns LeadListBuilderResult with success=False, errors populated
   - Partial Success: status="partial" when <50% of target leads scraped
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from src.integrations.apify import (
    ApifyError,
    ApifyLeadScraperClient,
    ApifyRateLimitError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class LeadListBuilderAgentError(Exception):
    """Exception raised for Lead List Builder agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InsufficientLeadsError(LeadListBuilderAgentError):
    """Raised when not enough leads could be scraped."""

    def __init__(
        self,
        target: int,
        scraped: int,
        source: str,
    ) -> None:
        message = f"Only scraped {scraped}/{target} leads from {source}"
        super().__init__(message, {"target": target, "scraped": scraped, "source": source})


class AllSourcesFailedError(LeadListBuilderAgentError):
    """Raised when all lead sources fail."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("All lead sources failed", {"errors": errors})


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class LeadListBuilderResult:
    """Result of Lead List Builder agent execution."""

    # Status
    success: bool = True
    status: str = "completed"  # completed, partial, failed

    # Leads
    leads: list[dict[str, Any]] = field(default_factory=list)
    total_scraped: int = 0
    target_leads: int = 0

    # Source breakdown (tracked by Apify actor)
    primary_actor_leads: int = 0  # From Leads Finder Primary
    fallback_actor_leads: int = 0  # From PPE or Multi scrapers

    # Cost tracking
    total_cost_usd: float = 0.0
    apify_runs: list[dict[str, Any]] = field(default_factory=list)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors (if any)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "status": self.status,
            "total_scraped": self.total_scraped,
            "target_leads": self.target_leads,
            "primary_actor_leads": self.primary_actor_leads,
            "fallback_actor_leads": self.fallback_actor_leads,
            "total_cost_usd": self.total_cost_usd,
            "execution_time_ms": self.execution_time_ms,
            "apify_runs": self.apify_runs,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# SDK MCP Tools
# =============================================================================


@tool(  # type: ignore[misc]
    name="scrape_leads",
    description=(
        "Scrape B2B leads using Apify's cost-effective waterfall pattern. "
        "Tries actors in order: Leads Finder Primary ($1.5/1k), PPE (fallback), "
        "Multi (last resort). Returns lead data including name, email, title, company."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "job_titles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Target job titles (e.g., VP, Director, CTO)",
            },
            "seniority_levels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Seniority levels (e.g., VP, Director, CXO)",
            },
            "industries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Target industries (e.g., Technology, Software)",
            },
            "company_sizes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Company size ranges (e.g., 51-200, 201-500)",
            },
            "locations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Geographic locations (e.g., San Francisco, New York)",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional search keywords",
            },
            "max_leads": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
                "description": "Maximum number of leads to scrape",
            },
            "apify_token": {
                "type": "string",
                "description": "Apify API token for authentication",
            },
        },
        "required": ["apify_token"],
    },
)
async def scrape_leads_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for scraping leads via Apify waterfall pattern.

    This tool creates its own Apify client using provided credentials,
    following the SDK pattern where tools are self-contained (LEARN-003).

    Uses waterfall pattern:
    1. Leads Finder Primary (IoSHqwTR9YGhzccez) - $1.5/1k leads
    2. Leads Scraper PPE (T1XDXWc1L92AfIJtd) - fallback
    3. Leads Scraper Multi (VYRyEF4ygTTkaIghe) - last resort

    Args:
        args: Tool arguments with search criteria and credentials.

    Returns:
        Tool result with leads data.
    """
    job_titles = args.get("job_titles", [])
    seniority_levels = args.get("seniority_levels", [])
    industries = args.get("industries", [])
    company_sizes = args.get("company_sizes", [])
    locations = args.get("locations", [])
    keywords = args.get("keywords", [])
    max_leads = args.get("max_leads", 1000)
    apify_token = args.get("apify_token", os.getenv("APIFY_API_TOKEN", ""))

    if not apify_token:
        return {
            "content": [{"type": "text", "text": "Apify API token not provided"}],
            "is_error": True,
        }

    # Require at least some search criteria
    if not any([job_titles, industries, keywords]):
        return {
            "content": [
                {
                    "type": "text",
                    "text": "At least one of job_titles, industries, or keywords is required",
                }
            ],
            "is_error": True,
        }

    try:
        client = ApifyLeadScraperClient(api_token=apify_token)

        async with client:
            result = await client.scrape_leads(
                job_titles=job_titles if job_titles else None,
                seniority_levels=seniority_levels if seniority_levels else None,
                industries=industries if industries else None,
                company_sizes=company_sizes if company_sizes else None,
                locations=locations if locations else None,
                keywords=keywords if keywords else None,
                max_leads=max_leads,
            )

        leads_data = [lead.to_dict() for lead in result.leads]

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Scraped {len(leads_data)} leads via Apify waterfall",
                }
            ],
            "data": {
                "leads": leads_data,
                "actor_id": result.actor_id,
                "run_id": result.run_id,
                "cost_usd": result.cost_usd,
                "duration_secs": result.duration_secs,
            },
        }

    except ApifyRateLimitError as e:
        logger.warning(f"Lead scraping rate limited: {e}")
        return {
            "content": [{"type": "text", "text": f"Rate limit exceeded: {e}"}],
            "is_error": True,
        }
    except ApifyError as e:
        logger.error(f"Lead scraping failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Apify error: {e}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Unexpected error scraping leads: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Lead List Builder Agent
# =============================================================================


class LeadListBuilderAgent:
    """
    Lead List Builder Agent - Phase 2, Agent 2.1.

    Uses Claude Agent SDK to orchestrate lead scraping from multiple sources.
    The agent analyzes persona criteria and decides the best scraping strategy.

    This agent is pure (no side effects). It returns leads data that the
    orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use.
        max_tokens: Maximum tokens for Claude responses.
        apify_token: Apify API token for lead scraping.
        linkedin_session_cookie: LinkedIn session cookie for Sales Navigator.
    """

    def __init__(
        self,
        apify_token: str | None = None,
        linkedin_session_cookie: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
    ) -> None:
        """
        Initialize Lead List Builder Agent.

        Args:
            apify_token: Apify API token. Defaults to APIFY_API_TOKEN env var.
            linkedin_session_cookie: LinkedIn li_at cookie for Sales Navigator.
            model: Claude model to use.
            max_tokens: Maximum tokens for responses.
        """
        self.name = "lead_list_builder"
        self.model = model
        self.max_tokens = max_tokens
        self.apify_token = apify_token or os.getenv("APIFY_API_TOKEN", "")
        self.linkedin_session_cookie = linkedin_session_cookie or os.getenv(
            "LINKEDIN_SESSION_COOKIE", ""
        )

        # Validate required credentials
        if not self.apify_token:
            logger.warning(
                f"[{self.name}] APIFY_API_TOKEN not set. Lead scraping will fail without it."
            )

        logger.info(f"[{self.name}] Agent initialized (model={model})")

    @property
    def system_prompt(self) -> str:
        """System prompt for the Claude agent."""
        return """You are a Lead List Builder agent specializing in B2B lead acquisition.

Your job is to scrape leads using Apify's cost-effective waterfall pattern.

AVAILABLE TOOLS:
1. scrape_leads - Scrape B2B leads via Apify waterfall pattern
   - Tries actors in order: Leads Finder Primary ($1.5/1k), PPE (fallback), Multi (last resort)
   - Provide search criteria: job_titles, seniority_levels, industries, company_sizes, locations, keywords

STRATEGY:
1. Analyze the persona criteria (job titles, industries, company sizes, etc.)
2. Call scrape_leads with the appropriate criteria
3. The tool automatically tries cheaper actors first, falling back to more expensive ones
4. Return all scraped leads

RULES:
- Provide as many search criteria as available for better targeting
- Target the number of leads specified (default 1000)
- Include as much data as possible (name, email, title, company, etc.)
- Report any errors or partial results
- The waterfall pattern ensures cost efficiency automatically

OUTPUT:
Return a summary of scraped leads including count, actor used, and cost."""

    async def run(
        self,
        niche_id: str,
        campaign_id: str,
        target_leads: int = 1000,
        job_titles: list[str] | None = None,
        seniority_levels: list[str] | None = None,
        industries: list[str] | None = None,
        company_sizes: list[str] | None = None,
        locations: list[str] | None = None,
        linkedin_search_url: str | None = None,
    ) -> LeadListBuilderResult:
        """
        Execute lead list building for a campaign.

        This method uses Claude Agent SDK to orchestrate lead scraping.
        The agent decides the best strategy based on the criteria provided.

        Args:
            niche_id: Niche UUID for context.
            campaign_id: Campaign UUID for tracking.
            target_leads: Number of leads to scrape.
            job_titles: Target job titles from persona.
            seniority_levels: Target seniority levels.
            industries: Target industries from niche.
            company_sizes: Target company sizes.
            locations: Target locations/regions.
            linkedin_search_url: Pre-built LinkedIn search URL (optional).

        Returns:
            LeadListBuilderResult with scraped leads and metadata.
        """
        import time

        start_time = time.time()
        result = LeadListBuilderResult(
            target_leads=target_leads,
            started_at=datetime.now(),
        )

        logger.info(
            f"[{self.name}] Starting lead list build for campaign {campaign_id} "
            f"(target={target_leads})"
        )

        try:
            # Build the task prompt
            task_prompt = self._build_task_prompt(
                niche_id=niche_id,
                campaign_id=campaign_id,
                target_leads=target_leads,
                job_titles=job_titles,
                seniority_levels=seniority_levels,
                industries=industries,
                company_sizes=company_sizes,
                locations=locations,
                linkedin_search_url=linkedin_search_url,
            )

            # Create SDK MCP server with our tools
            mcp_server = create_sdk_mcp_server(
                name="lead_tools",
                version="1.0.0",
                tools=[scrape_leads_tool],
            )

            # Clear conflicting env var (LEARN-001)
            os.environ.pop("ANTHROPIC_API_KEY", None)

            # Configure Claude Agent SDK options per SDK_PATTERNS.md
            # - mcp_servers: dict with server name as key
            # - allowed_tools: explicit list of tool names (mcp__servername__toolname)
            # - permission_mode: 'acceptEdits' for automated workflows
            # - system_prompt: goes in options, not query()
            options = ClaudeAgentOptions(
                model=self.model,
                system_prompt=self.system_prompt,
                mcp_servers={"lead_tools": mcp_server},
                allowed_tools=["mcp__lead_tools__scrape_leads"],
                permission_mode="acceptEdits",
                setting_sources=["project"],
            )

            # Process response and extract leads
            all_leads: list[dict[str, Any]] = []
            primary_count = 0
            fallback_count = 0
            total_cost = 0.0

            # Primary actor ID for comparison
            primary_actor = "IoSHqwTR9YGhzccez"

            # Use async iterator pattern per SDK_PATTERNS.md
            # query() returns an async iterator, not an awaitable response object
            async for message in query(prompt=task_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        # Use proper type checking per SDK_PATTERNS.md
                        if isinstance(block, ToolUseBlock):
                            logger.debug(f"[{self.name}] Tool call: {block.name}")
                        elif isinstance(block, ToolResultBlock):
                            # Check for errors first
                            if block.is_error:
                                logger.warning(f"[{self.name}] Tool error: {block.content}")
                                continue

                            # Parse tool result content
                            # ToolResultBlock.content can be str or list[dict]
                            tool_data = self._parse_tool_result(block.content)
                            if tool_data and "data" in tool_data:
                                data = tool_data["data"]
                                leads = data.get("leads", [])
                                all_leads.extend(leads)

                                cost = data.get("cost_usd", 0.0)
                                total_cost += cost

                                run_id = data.get("run_id")
                                actor_id = data.get("actor_id", "")
                                if run_id:
                                    result.apify_runs.append(
                                        {
                                            "run_id": run_id,
                                            "actor_id": actor_id,
                                            "cost_usd": cost,
                                            "leads_count": len(leads),
                                        }
                                    )

                                # Track by actor (primary vs fallback)
                                if actor_id == primary_actor:
                                    primary_count += len(leads)
                                else:
                                    fallback_count += len(leads)
                        elif isinstance(block, TextBlock):
                            logger.debug(f"[{self.name}] Response: {block.text[:100]}...")

                elif isinstance(message, ResultMessage):
                    logger.info(
                        f"[{self.name}] Session completed: "
                        f"session_id={message.session_id}, "
                        f"cost=${message.total_cost_usd or 0:.4f}"
                    )

            # If we didn't get leads from tool results, try direct scraping
            if not all_leads:
                logger.info(f"[{self.name}] No leads from Claude, trying direct scrape")
                direct_result = await self._direct_scrape(
                    target_leads=target_leads,
                    job_titles=job_titles or [],
                    seniority_levels=seniority_levels or [],
                    industries=industries or [],
                    company_sizes=company_sizes or [],
                    locations=locations or [],
                )
                all_leads = direct_result["leads"]
                primary_count = direct_result["primary_count"]
                fallback_count = direct_result["fallback_count"]
                total_cost = direct_result["total_cost"]
                result.apify_runs = direct_result.get("runs", [])
                result.errors = direct_result.get("errors", [])

            # Populate result
            result.leads = all_leads
            result.total_scraped = len(all_leads)
            result.primary_actor_leads = primary_count
            result.fallback_actor_leads = fallback_count
            result.total_cost_usd = total_cost
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            # Determine status
            if result.total_scraped == 0:
                result.success = False
                result.status = "failed"
                result.errors.append(
                    {
                        "type": "no_leads",
                        "message": "No leads could be scraped from any source",
                    }
                )
            elif result.total_scraped < target_leads * 0.5:
                result.status = "partial"
                result.warnings.append(f"Only scraped {result.total_scraped}/{target_leads} leads")
            else:
                result.status = "completed"

            logger.info(
                f"[{self.name}] Lead list build completed: "
                f"{result.total_scraped} leads "
                f"(primary={primary_count}, fallback={fallback_count}, "
                f"cost=${total_cost:.2f}, time={result.execution_time_ms}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Lead list build failed: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append(
                {
                    "type": type(e).__name__,
                    "message": str(e),
                }
            )
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def _direct_scrape(
        self,
        target_leads: int,
        job_titles: list[str],
        seniority_levels: list[str],
        industries: list[str],
        company_sizes: list[str],
        locations: list[str],
    ) -> dict[str, Any]:
        """
        Direct lead scraping without Claude orchestration.

        Fallback method when Claude agent doesn't return leads.
        Uses the Apify waterfall pattern to scrape leads cost-effectively.
        """
        all_leads: list[dict[str, Any]] = []
        primary_count = 0
        fallback_count = 0
        total_cost = 0.0
        runs: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        # Primary actor ID for tracking
        primary_actor = "IoSHqwTR9YGhzccez"

        if self.apify_token:
            try:
                client = ApifyLeadScraperClient(api_token=self.apify_token)
                async with client:
                    # Use the waterfall pattern
                    result = await client.scrape_leads(
                        job_titles=job_titles if job_titles else None,
                        seniority_levels=seniority_levels if seniority_levels else None,
                        industries=industries if industries else None,
                        company_sizes=company_sizes if company_sizes else None,
                        locations=locations if locations else None,
                        max_leads=target_leads,
                    )

                    scraped_leads = [lead.to_dict() for lead in result.leads]
                    all_leads.extend(scraped_leads)
                    total_cost += result.cost_usd

                    # Track which actor was used
                    if result.actor_id == primary_actor:
                        primary_count = len(scraped_leads)
                    else:
                        fallback_count = len(scraped_leads)

                    runs.append(
                        {
                            "run_id": result.run_id,
                            "actor_id": result.actor_id,
                            "cost_usd": result.cost_usd,
                            "leads_count": len(scraped_leads),
                        }
                    )

            except ApifyError as e:
                logger.error(f"[{self.name}] Lead scraping failed: {e}")
                errors.append(
                    {
                        "source": "apify_waterfall",
                        "error": str(e),
                    }
                )
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error during scraping: {e}")
                errors.append(
                    {
                        "source": "apify_waterfall",
                        "error": str(e),
                    }
                )

        return {
            "leads": all_leads,
            "primary_count": primary_count,
            "fallback_count": fallback_count,
            "total_cost": total_cost,
            "runs": runs,
            "errors": errors,
        }

    def _build_task_prompt(
        self,
        niche_id: str,
        campaign_id: str,
        target_leads: int,
        job_titles: list[str] | None,
        seniority_levels: list[str] | None,
        industries: list[str] | None,
        company_sizes: list[str] | None,
        locations: list[str] | None,
        linkedin_search_url: str | None = None,  # Kept for backwards compatibility
    ) -> str:
        """Build the task prompt for Claude."""
        prompt_parts = [
            f"Build a lead list for campaign {campaign_id}.",
            f"Target: {target_leads} leads.",
            "",
            "PERSONA CRITERIA:",
        ]

        if job_titles:
            prompt_parts.append(f"- Job Titles: {', '.join(job_titles)}")
        if seniority_levels:
            prompt_parts.append(f"- Seniority: {', '.join(seniority_levels)}")
        if industries:
            prompt_parts.append(f"- Industries: {', '.join(industries)}")
        if company_sizes:
            prompt_parts.append(f"- Company Sizes: {', '.join(company_sizes)}")
        if locations:
            prompt_parts.append(f"- Locations: {', '.join(locations)}")

        prompt_parts.append("")

        prompt_parts.extend(
            [
                "INSTRUCTIONS:",
                "1. Use the scrape_leads tool with the persona criteria above",
                "2. The tool uses waterfall pattern (cheapest actor first)",
                f"3. Target at least {target_leads} total leads",
                "",
                f"Use apify_token: {(self.apify_token or '')[:10]}... (truncated for security)",
            ]
        )

        return "\n".join(prompt_parts)

    def _parse_tool_result(
        self,
        content: str | list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        """
        Parse tool result content into structured data.

        ToolResultBlock.content can be:
        - str: JSON string or plain text
        - list[dict]: List of content blocks
        - None: No content

        Args:
            content: The tool result content.

        Returns:
            Parsed dictionary with 'data' key if available, None otherwise.
        """
        import json

        if content is None:
            return None

        # If it's a string, try to parse as JSON
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
                return {"content": [{"type": "text", "text": content}]}
            except json.JSONDecodeError:
                # Not JSON, return as text
                return {"content": [{"type": "text", "text": content}]}

        # If it's a list, look for data in text blocks
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    # Check if this block has our data structure
                    if "data" in block:
                        return block
                    # Check for text content that might be JSON
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        try:
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            continue

        return None


# =============================================================================
# Convenience Functions
# =============================================================================


async def build_lead_list(
    campaign_id: str,
    niche_id: str,
    target_leads: int = 1000,
    **persona_criteria: Any,
) -> LeadListBuilderResult:
    """
    Convenience function to build a lead list.

    Args:
        campaign_id: Campaign UUID.
        niche_id: Niche UUID.
        target_leads: Number of leads to scrape.
        **persona_criteria: Persona criteria (job_titles, industries, etc.)

    Returns:
        LeadListBuilderResult with scraped leads.
    """
    agent = LeadListBuilderAgent()
    return await agent.run(
        campaign_id=campaign_id,
        niche_id=niche_id,
        target_leads=target_leads,
        **persona_criteria,
    )
