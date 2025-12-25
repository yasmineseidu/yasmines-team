"""
Import Finalizer Agent - Phase 2, Agent 2.6.

Finalizes the lead import process by generating comprehensive summary reports,
exporting lead lists to Google Sheets for review, and optionally triggering
human approval gates.

This agent is pure (no side effects). The orchestrator handles all database
persistence per LEARN-007.

Database Interactions:

1. INPUT TABLE: campaigns
   - Source Agent: Lead Scoring Agent (2.5)
   - Required Fields: id, name, niche_id, status, target_leads, total_leads_scraped,
                      scraping_cost, total_leads_valid, total_leads_invalid,
                      total_duplicates_found, total_cross_duplicates, total_leads_available,
                      leads_scored, avg_lead_score, leads_tier_a, leads_tier_b, leads_tier_c
   - Data Format: dict[str, Any]
   - Handoff Method: Orchestrator passes campaign dict directly to run()

2. INPUT TABLE: niches
   - Required Fields: id, name, industry, job_titles
   - Data Format: dict[str, Any]
   - Handoff Method: Orchestrator passes niche dict

3. INPUT TABLE: leads
   - Required Fields: id, first_name, last_name, email, title, company_name,
                      company_domain, company_size, location, lead_score, lead_tier, status
   - Data Format: list[dict[str, Any]]
   - Handoff Method: Orchestrator passes leads list, filtered by status

4. OUTPUT: ImportFinalizerResult (returned to orchestrator)
   - Target: Database updates to campaigns table
   - Written Fields: lead_list_url, import_summary, status, import_completed_at
   - Data Format: ImportFinalizerResult dataclass
   - Handoff Method: Orchestrator receives result and handles DB persistence

5. HANDOFF COORDINATION:
   - Upstream Dependencies: Lead Scoring Agent (2.5) must complete first
   - Downstream Consumers: Phase 3 (Email Verification)
   - Failure Handling: Returns result with success=False, errors populated
"""

import logging
import os
import tempfile
import time
from datetime import datetime
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query
from claude_agent_sdk.types import AssistantMessage

from src.agents.import_finalizer.schemas import (
    CampaignData,
    ImportFinalizerResult,
    NicheData,
)
from src.agents.import_finalizer.sheets_exporter import SheetsExporter, export_leads_to_csv
from src.agents.import_finalizer.summary_builder import (
    build_full_summary,
)
from src.agents.import_finalizer.tools import (
    compile_summary_tool,
    export_to_sheets_tool,
    format_notification_tool,
    get_lead_stats_tool,
    set_campaign_data,
    set_leads_data,
    set_niche_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class ImportFinalizerAgentError(Exception):
    """Exception raised for Import Finalizer agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ExportFailedError(ImportFinalizerAgentError):
    """Raised when export to Google Sheets and CSV fallback both fail."""

    pass


# =============================================================================
# Import Finalizer Agent
# =============================================================================


class ImportFinalizerAgent:
    """
    Import Finalizer Agent - Phase 2, Agent 2.6.

    Uses Claude Agent SDK to orchestrate import finalization:
    - Compile comprehensive summary statistics
    - Export leads to Google Sheets (with CSV fallback)
    - Format notifications for stakeholders

    This agent is pure (no side effects). It returns results that the
    orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """
        Initialize Import Finalizer Agent.

        Args:
            model: Claude model to use.
        """
        self.name = "import_finalizer"
        self.model = model

        logger.info(f"[{self.name}] Agent initialized (model={model})")

    @property
    def system_prompt(self) -> str:
        """System prompt for the Claude agent."""
        return """You are an import finalization specialist preparing lead lists for review.

AVAILABLE TOOLS:
1. compile_summary - Compile comprehensive import statistics
2. export_to_sheets - Export leads to Google Sheets (falls back to CSV)
3. get_lead_stats - Calculate statistics for a list of leads
4. format_notification - Format a notification message

RESPONSIBILITIES:
1. Compile comprehensive import statistics from campaign data
2. Export leads to Google Sheets for human review
3. Generate clear summary for stakeholders
4. Prepare notification messages

EXPORT STRUCTURE:
The Google Sheets export should include:
- Summary sheet: Campaign stats, tier distribution
- Tier A Leads: High-priority leads (score 80+)
- Tier B Leads: Good leads (score 60-79)
- All Leads: All available leads by score

PROCESS:
1. Use compile_summary to generate import statistics
2. Use export_to_sheets to create the spreadsheet
3. Use format_notification to prepare the notification
4. Return the results for orchestrator

QUALITY GOALS:
- Complete and accurate summary
- Well-formatted spreadsheet
- Clear tier breakdown
- Actionable notification"""

    async def run(
        self,
        campaign_id: str,
        campaign_data: dict[str, Any],
        niche_data: dict[str, Any] | None,
        tier_a_leads: list[dict[str, Any]],
        tier_b_leads: list[dict[str, Any]],
        all_leads: list[dict[str, Any]],
        use_claude: bool = False,
    ) -> ImportFinalizerResult:
        """
        Execute import finalization for a campaign.

        This method can run in two modes:
        1. Direct mode (default): Uses Python functions directly
        2. Claude mode: Uses Claude Agent SDK for orchestration

        Args:
            campaign_id: Campaign UUID.
            campaign_data: Campaign data dictionary from database.
            niche_data: Optional niche data dictionary.
            tier_a_leads: List of Tier A lead dictionaries.
            tier_b_leads: List of Tier B lead dictionaries.
            all_leads: List of all lead dictionaries.
            use_claude: If True, use Claude for orchestration.

        Returns:
            ImportFinalizerResult with export results.
        """
        start_time = time.time()
        result = ImportFinalizerResult(
            started_at=datetime.now(),
        )

        logger.info(
            f"[{self.name}] Starting import finalization for campaign {campaign_id} "
            f"({len(all_leads)} leads, {len(tier_a_leads)} Tier A, {len(tier_b_leads)} Tier B)"
        )

        try:
            if use_claude:
                return await self._run_with_claude(
                    campaign_id,
                    campaign_data,
                    niche_data,
                    tier_a_leads,
                    tier_b_leads,
                    all_leads,
                    start_time,
                )
            else:
                return await self._run_direct(
                    campaign_id,
                    campaign_data,
                    niche_data,
                    tier_a_leads,
                    tier_b_leads,
                    all_leads,
                    start_time,
                )

        except Exception as e:
            logger.error(f"[{self.name}] Import finalization failed: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append({"type": type(e).__name__, "message": str(e)})
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def _run_direct(
        self,
        campaign_id: str,
        campaign_data: dict[str, Any],
        niche_data: dict[str, Any] | None,
        tier_a_leads: list[dict[str, Any]],
        tier_b_leads: list[dict[str, Any]],
        all_leads: list[dict[str, Any]],
        start_time: float,
    ) -> ImportFinalizerResult:
        """
        Run import finalization directly with Python functions.

        This is the recommended mode for production - faster and more reliable.
        """
        result = ImportFinalizerResult(
            started_at=datetime.now(),
        )

        # Step 1: Build summary
        campaign = CampaignData.from_dict(campaign_data)
        niche = NicheData.from_dict(niche_data) if niche_data else None

        summary = build_full_summary(campaign, niche)
        result.summary = summary

        logger.info(f"[{self.name}] Summary compiled: {summary.total_available} leads available")

        # Step 2: Export to Google Sheets
        exporter = SheetsExporter()
        try:
            sheet_result = await exporter.export_leads(
                campaign_name=campaign.name,
                niche_name=niche.name if niche else "Unknown",
                summary=summary,
                tier_a_leads=tier_a_leads,
                tier_b_leads=tier_b_leads,
                all_leads=all_leads,
            )
        finally:
            await exporter.close()

        result.sheet_result = sheet_result

        if sheet_result.success:
            result.sheet_url = sheet_result.spreadsheet_url
            result.sheet_id = sheet_result.spreadsheet_id
            logger.info(f"[{self.name}] Exported to Google Sheets: {result.sheet_url}")
        else:
            # Fallback to CSV
            logger.warning(f"[{self.name}] Google Sheets export failed, trying CSV fallback")

            csv_path = os.path.join(tempfile.gettempdir(), "exports", f"{campaign_id}_leads.csv")
            csv_result = export_leads_to_csv(csv_path, summary, all_leads)

            if csv_result.success:
                result.sheet_result = csv_result
                result.sheet_url = csv_path
                result.warnings.append(
                    f"Google Sheets failed: {sheet_result.error_message}. "
                    f"Exported to CSV: {csv_path}"
                )
                logger.info(f"[{self.name}] Exported to CSV: {csv_path}")
            else:
                result.errors.append(
                    {
                        "type": "ExportFailed",
                        "message": f"Both Google Sheets and CSV export failed: {sheet_result.error_message}",
                    }
                )

        # Step 3: Finalize result
        result.success = result.sheet_url is not None
        result.status = "completed" if result.success else "failed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Import finalization {'completed' if result.success else 'failed'}: "
            f"sheet_url={result.sheet_url}, time={result.execution_time_ms}ms"
        )

        return result

    async def _run_with_claude(
        self,
        campaign_id: str,
        campaign_data: dict[str, Any],
        niche_data: dict[str, Any] | None,
        tier_a_leads: list[dict[str, Any]],
        tier_b_leads: list[dict[str, Any]],
        all_leads: list[dict[str, Any]],
        start_time: float,
    ) -> ImportFinalizerResult:
        """
        Run import finalization with Claude Agent SDK orchestration.

        Uses Claude to analyze and coordinate the finalization process.
        """
        result = ImportFinalizerResult(
            started_at=datetime.now(),
        )

        # Set data for tools (module-level storage per LEARN-003)
        set_campaign_data(campaign_data)
        set_niche_data(niche_data)
        set_leads_data(tier_a_leads, tier_b_leads, all_leads)

        # Build task prompt
        task_prompt = self._build_task_prompt(
            campaign_id,
            campaign_data,
            len(tier_a_leads),
            len(tier_b_leads),
            len(all_leads),
        )

        # Create SDK MCP server with tools
        mcp_server = create_sdk_mcp_server(
            name="import_finalizer_tools",
            tools=[
                compile_summary_tool,
                export_to_sheets_tool,
                get_lead_stats_tool,
                format_notification_tool,
            ],
        )

        # Clear conflicting env var (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Query Claude with tools
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.system_prompt,
            mcp_servers={"import_finalizer_tools": mcp_server},
        )

        # Process messages from query iterator
        async for message in query(prompt=task_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "tool_result"):
                        tool_data = getattr(block, "tool_result", {})
                        if isinstance(tool_data, dict) and "data" in tool_data:
                            data = tool_data["data"]

                            # Check for summary
                            if "summary" in data:
                                result.summary = data.get("summary")

                            # Check for sheet URL
                            if "spreadsheet_url" in data:
                                result.sheet_url = data.get("spreadsheet_url")
                                result.sheet_id = data.get("spreadsheet_id")

        # Finalize result
        result.success = result.sheet_url is not None
        result.status = "completed" if result.success else "failed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Claude-orchestrated finalization completed: "
            f"sheet_url={result.sheet_url}"
        )

        return result

    def _build_task_prompt(
        self,
        campaign_id: str,
        campaign_data: dict[str, Any],
        tier_a_count: int,
        tier_b_count: int,
        total_count: int,
    ) -> str:
        """Build the task prompt for Claude."""
        campaign_name = campaign_data.get("name", "Unknown")
        return f"""Finalize lead import for campaign: {campaign_name} ({campaign_id})

LEAD COUNTS:
- Tier A: {tier_a_count}
- Tier B: {tier_b_count}
- Total: {total_count}

INSTRUCTIONS:
1. Use compile_summary to generate import statistics from the campaign data
2. Use export_to_sheets to create a Google Sheets spreadsheet with all leads
3. Use format_notification to prepare a notification message

The campaign data is provided. Generate a comprehensive summary and export
the leads for human review.

GOALS:
- Complete import summary with all statistics
- Google Sheets export with Summary, Tier A, Tier B, and All Leads sheets
- Clear notification message for stakeholders

Report the final results including the spreadsheet URL."""


# =============================================================================
# Convenience Functions
# =============================================================================


async def finalize_import(
    campaign_id: str,
    campaign_data: dict[str, Any],
    niche_data: dict[str, Any] | None,
    tier_a_leads: list[dict[str, Any]],
    tier_b_leads: list[dict[str, Any]],
    all_leads: list[dict[str, Any]],
    use_claude: bool = False,
) -> ImportFinalizerResult:
    """
    Convenience function to finalize lead import.

    Args:
        campaign_id: Campaign UUID.
        campaign_data: Campaign data from database.
        niche_data: Optional niche data.
        tier_a_leads: Tier A leads.
        tier_b_leads: Tier B leads.
        all_leads: All leads.
        use_claude: Use Claude for orchestration.

    Returns:
        ImportFinalizerResult with export results.
    """
    agent = ImportFinalizerAgent()
    return await agent.run(
        campaign_id=campaign_id,
        campaign_data=campaign_data,
        niche_data=niche_data,
        tier_a_leads=tier_a_leads,
        tier_b_leads=tier_b_leads,
        all_leads=all_leads,
        use_claude=use_claude,
    )
