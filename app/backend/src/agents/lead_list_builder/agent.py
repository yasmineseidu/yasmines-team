"""
Lead List Builder Agent - Phase 2, Agent 2.1.

Uses Claude Agent SDK with Apify actors to scrape leads from:
- LinkedIn Sales Navigator (primary source)
- LinkedIn Search (fallback)
- Apollo.io (enrichment/supplementary)

This agent receives persona and niche data from Phase 1 and builds
targeted lead lists based on job titles, industries, and company sizes.

Phase 2 Pipeline Position:
Input: Niche + Persona data from Phase 1 → Output: Raw leads for validation

Per LEARN-007: This agent is pure (no side effects). The orchestrator
handles all database persistence.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from claude_agent_sdk.types import AssistantMessage

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

    # Source breakdown
    linkedin_leads: int = 0
    apollo_leads: int = 0

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
            "linkedin_leads": self.linkedin_leads,
            "apollo_leads": self.apollo_leads,
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
    name="scrape_linkedin_leads",
    description=(
        "Scrape leads from LinkedIn using a search URL. "
        "Supports both regular LinkedIn search and Sales Navigator. "
        "Returns lead data including name, title, company, and LinkedIn URL."
    ),
    input_schema={
        "search_url": str,
        "max_leads": int,
        "use_sales_navigator": bool,
        "session_cookie": str,
        "apify_token": str,
    },
)
async def scrape_linkedin_leads_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for scraping LinkedIn leads via Apify.

    This tool creates its own Apify client using provided credentials,
    following the SDK pattern where tools are self-contained (LEARN-003).

    Args:
        args: Tool arguments with search URL, max leads, and credentials.

    Returns:
        Tool result with leads data.
    """
    search_url = args["search_url"]
    max_leads = args.get("max_leads", 1000)
    use_sales_navigator = args.get("use_sales_navigator", False)
    session_cookie = args.get("session_cookie")
    apify_token = args.get("apify_token", os.getenv("APIFY_API_TOKEN", ""))

    if not apify_token:
        return {
            "content": [{"type": "text", "text": "Apify API token not provided"}],
            "is_error": True,
        }

    if not search_url:
        return {
            "content": [{"type": "text", "text": "LinkedIn search URL is required"}],
            "is_error": True,
        }

    try:
        client = ApifyLeadScraperClient(api_token=apify_token)

        async with client:
            if use_sales_navigator:
                result = await client.scrape_linkedin_sales_navigator(
                    search_url=search_url,
                    max_leads=max_leads,
                    session_cookie=session_cookie,
                )
            else:
                result = await client.scrape_linkedin_leads(
                    search_url=search_url,
                    max_leads=max_leads,
                )

        leads_data = [lead.to_dict() for lead in result.leads]

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Scraped {len(leads_data)} leads from LinkedIn",
                }
            ],
            "data": {
                "leads": leads_data,
                "run_id": result.run_id,
                "cost_usd": result.cost_usd,
                "duration_secs": result.duration_secs,
            },
        }

    except ApifyRateLimitError as e:
        logger.warning(f"LinkedIn scraping rate limited: {e}")
        return {
            "content": [{"type": "text", "text": f"Rate limit exceeded: {e}"}],
            "is_error": True,
        }
    except ApifyError as e:
        logger.error(f"LinkedIn scraping failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Apify error: {e}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Unexpected error scraping LinkedIn: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="scrape_apollo_leads",
    description=(
        "Scrape leads from Apollo.io. "
        "Provide search filters like job titles, industries, and company sizes."
    ),
    input_schema={
        "job_titles": list,
        "industries": list,
        "company_sizes": list,
        "locations": list,
        "max_leads": int,
        "apify_token": str,
    },
)
async def scrape_apollo_leads_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for scraping Apollo.io leads via Apify.

    Args:
        args: Tool arguments with search filters.

    Returns:
        Tool result with leads data.
    """
    job_titles = args.get("job_titles", [])
    industries = args.get("industries", [])
    company_sizes = args.get("company_sizes", [])
    locations = args.get("locations", [])
    max_leads = args.get("max_leads", 1000)
    apify_token = args.get("apify_token", os.getenv("APIFY_API_TOKEN", ""))

    if not apify_token:
        return {
            "content": [{"type": "text", "text": "Apify API token not provided"}],
            "is_error": True,
        }

    try:
        client = ApifyLeadScraperClient(api_token=apify_token)

        search_params: dict[str, Any] = {}
        if job_titles:
            search_params["personTitles"] = job_titles
        if industries:
            search_params["organizationIndustries"] = industries
        if company_sizes:
            search_params["organizationNumEmployeesRanges"] = company_sizes
        if locations:
            search_params["personLocations"] = locations

        async with client:
            result = await client.scrape_apollo_leads(
                search_params=search_params,
                max_leads=max_leads,
            )

        leads_data = [lead.to_dict() for lead in result.leads]

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Scraped {len(leads_data)} leads from Apollo.io",
                }
            ],
            "data": {
                "leads": leads_data,
                "run_id": result.run_id,
                "cost_usd": result.cost_usd,
                "duration_secs": result.duration_secs,
            },
        }

    except ApifyError as e:
        logger.error(f"Apollo scraping failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Apify error: {e}"}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Unexpected error scraping Apollo: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="build_linkedin_search_url",
    description=(
        "Build a LinkedIn Sales Navigator search URL from persona criteria. "
        "Returns a properly formatted search URL."
    ),
    input_schema={
        "job_titles": list,
        "seniority_levels": list,
        "industries": list,
        "company_sizes": list,
        "locations": list,
    },
)
async def build_linkedin_search_url_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for building LinkedIn search URLs.

    Constructs a Sales Navigator search URL from persona criteria.

    Args:
        args: Tool arguments with search criteria.

    Returns:
        Tool result with the constructed search URL.
    """
    job_titles = args.get("job_titles", [])
    seniority_levels = args.get("seniority_levels", [])
    industries = args.get("industries", [])
    company_sizes = args.get("company_sizes", [])
    locations = args.get("locations", [])

    # Base Sales Navigator URL
    base_url = "https://www.linkedin.com/sales/search/people"

    # Build filters
    # Note: This is a simplified URL builder. Real Sales Navigator
    # URLs have complex encoded filter parameters.
    params: list[str] = []

    if job_titles:
        titles_str = ",".join(f'"{t}"' for t in job_titles[:5])
        params.append(f"titleIncluded={titles_str}")

    if seniority_levels:
        # Map to LinkedIn seniority IDs
        seniority_map = {
            "Owner": "1",
            "Partner": "2",
            "CXO": "3",
            "VP": "4",
            "Director": "5",
            "Manager": "6",
            "Senior": "7",
            "Entry": "8",
            "Training": "9",
        }
        seniority_ids = [seniority_map.get(s, s) for s in seniority_levels]
        params.append(f"seniorityIncluded={','.join(seniority_ids)}")

    if industries:
        # Industries need to be mapped to LinkedIn industry IDs
        # For now, use a placeholder approach
        params.append(f"industryIncluded={','.join(industries[:10])}")

    if company_sizes:
        # Map company sizes to LinkedIn size ranges
        size_map = {
            "1-10": "B",
            "11-50": "C",
            "51-200": "D",
            "201-500": "E",
            "501-1000": "F",
            "1001-5000": "G",
            "5001-10000": "H",
            "10001+": "I",
        }
        size_ids = [size_map.get(s, s) for s in company_sizes]
        params.append(f"companySize={','.join(size_ids)}")

    if locations:
        params.append(f"geoIncluded={','.join(locations[:5])}")

    # Construct URL
    search_url = f"{base_url}?{'&'.join(params)}" if params else base_url

    return {
        "content": [
            {
                "type": "text",
                "text": f"Built LinkedIn search URL with {len(params)} filters",
            }
        ],
        "data": {
            "search_url": search_url,
            "filters_applied": len(params),
        },
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

Your job is to scrape leads from LinkedIn and Apollo.io based on persona criteria.

AVAILABLE TOOLS:
1. build_linkedin_search_url - Build a LinkedIn search URL from criteria
2. scrape_linkedin_leads - Scrape leads from LinkedIn via Apify
3. scrape_apollo_leads - Scrape leads from Apollo.io via Apify

STRATEGY:
1. Analyze the persona criteria (job titles, industries, company sizes, etc.)
2. Build an appropriate LinkedIn search URL using the criteria
3. Scrape leads from LinkedIn (primary source)
4. If needed, supplement with Apollo.io leads
5. Return all scraped leads

RULES:
- Always start with LinkedIn as the primary source
- Use Apollo.io to supplement if LinkedIn doesn't return enough leads
- Target the number of leads specified (default 1000)
- Include as much data as possible (name, email, title, company, etc.)
- Report any errors or partial results

OUTPUT:
Return a summary of scraped leads with counts from each source."""

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
                name="lead_list_builder_tools",
                tools=[
                    build_linkedin_search_url_tool,
                    scrape_linkedin_leads_tool,
                    scrape_apollo_leads_tool,
                ],
            )

            # Clear conflicting env var (LEARN-001)
            os.environ.pop("ANTHROPIC_API_KEY", None)

            # Query Claude with tools
            options = ClaudeAgentOptions(
                model=self.model,
                max_tokens=self.max_tokens,
                mcp_servers=[mcp_server],
            )

            response = await query(
                prompt=task_prompt,
                system=self.system_prompt,
                options=options,
            )

            # Process response and extract leads
            all_leads: list[dict[str, Any]] = []
            linkedin_count = 0
            apollo_count = 0
            total_cost = 0.0

            for message in response.messages:
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "tool_result"):
                            tool_data = getattr(block, "tool_result", {})
                            if isinstance(tool_data, dict) and "data" in tool_data:
                                data = tool_data["data"]
                                leads = data.get("leads", [])
                                all_leads.extend(leads)

                                cost = data.get("cost_usd", 0.0)
                                total_cost += cost

                                run_id = data.get("run_id")
                                if run_id:
                                    result.apify_runs.append(
                                        {
                                            "run_id": run_id,
                                            "cost_usd": cost,
                                            "leads_count": len(leads),
                                        }
                                    )

                                # Count by source
                                for lead in leads:
                                    source = lead.get("source", "")
                                    if "linkedin" in source.lower():
                                        linkedin_count += 1
                                    elif "apollo" in source.lower():
                                        apollo_count += 1

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
                    linkedin_search_url=linkedin_search_url,
                )
                all_leads = direct_result["leads"]
                linkedin_count = direct_result["linkedin_count"]
                apollo_count = direct_result["apollo_count"]
                total_cost = direct_result["total_cost"]
                result.apify_runs = direct_result.get("runs", [])
                result.errors = direct_result.get("errors", [])

            # Populate result
            result.leads = all_leads
            result.total_scraped = len(all_leads)
            result.linkedin_leads = linkedin_count
            result.apollo_leads = apollo_count
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
                f"(LinkedIn={linkedin_count}, Apollo={apollo_count}, "
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
        linkedin_search_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Direct lead scraping without Claude orchestration.

        Fallback method when Claude agent doesn't return leads.
        """
        all_leads: list[dict[str, Any]] = []
        linkedin_count = 0
        apollo_count = 0
        total_cost = 0.0
        runs: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        # Try LinkedIn first
        if self.apify_token:
            try:
                client = ApifyLeadScraperClient(api_token=self.apify_token)
                async with client:
                    # Build search URL if not provided
                    if not linkedin_search_url:
                        # Construct a basic search URL
                        linkedin_search_url = "https://www.linkedin.com/sales/search/people"

                    # Try Sales Navigator if we have a session cookie
                    if self.linkedin_session_cookie:
                        result = await client.scrape_linkedin_sales_navigator(
                            search_url=linkedin_search_url,
                            max_leads=target_leads,
                            session_cookie=self.linkedin_session_cookie,
                        )
                    else:
                        result = await client.scrape_linkedin_leads(
                            search_url=linkedin_search_url,
                            max_leads=target_leads,
                        )

                    linkedin_leads = [lead.to_dict() for lead in result.leads]
                    all_leads.extend(linkedin_leads)
                    linkedin_count = len(linkedin_leads)
                    total_cost += result.cost_usd
                    runs.append(
                        {
                            "run_id": result.run_id,
                            "source": "linkedin",
                            "cost_usd": result.cost_usd,
                            "leads_count": len(linkedin_leads),
                        }
                    )

            except Exception as e:
                logger.error(f"[{self.name}] LinkedIn scraping failed: {e}")
                errors.append(
                    {
                        "source": "linkedin",
                        "error": str(e),
                    }
                )

        # Supplement with Apollo if needed
        remaining = target_leads - len(all_leads)
        if remaining > 0 and (job_titles or industries):
            try:
                client = ApifyLeadScraperClient(api_token=self.apify_token)
                async with client:
                    search_params: dict[str, Any] = {}
                    if job_titles:
                        search_params["personTitles"] = job_titles
                    if industries:
                        search_params["organizationIndustries"] = industries
                    if company_sizes:
                        search_params["organizationNumEmployeesRanges"] = company_sizes
                    if locations:
                        search_params["personLocations"] = locations

                    result = await client.scrape_apollo_leads(
                        search_params=search_params,
                        max_leads=remaining,
                    )

                    apollo_leads = [lead.to_dict() for lead in result.leads]
                    all_leads.extend(apollo_leads)
                    apollo_count = len(apollo_leads)
                    total_cost += result.cost_usd
                    runs.append(
                        {
                            "run_id": result.run_id,
                            "source": "apollo",
                            "cost_usd": result.cost_usd,
                            "leads_count": len(apollo_leads),
                        }
                    )

            except Exception as e:
                logger.error(f"[{self.name}] Apollo scraping failed: {e}")
                errors.append(
                    {
                        "source": "apollo",
                        "error": str(e),
                    }
                )

        return {
            "leads": all_leads,
            "linkedin_count": linkedin_count,
            "apollo_count": apollo_count,
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
        linkedin_search_url: str | None,
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

        if linkedin_search_url:
            prompt_parts.append(f"PRE-BUILT SEARCH URL: {linkedin_search_url}")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "INSTRUCTIONS:",
                "1. Build LinkedIn search URL if not provided",
                "2. Scrape leads from LinkedIn (primary source)",
                "3. Supplement with Apollo.io if needed",
                f"4. Target at least {target_leads} total leads",
                "",
                f"Use apify_token: {(self.apify_token or '')[:10]}... (truncated for security)",
            ]
        )

        return "\n".join(prompt_parts)


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
