"""
Duplicate Detection Agent - Phase 2, Agent 2.3.

Identifies and handles duplicate leads within the current campaign using
exact matching (LinkedIn URL, email) and fuzzy matching (name + company).
Merges duplicate records, preserving the most complete data.

This agent is pure (no side effects). The orchestrator handles all database
persistence per LEARN-007.

Database Interactions:

1. INPUT: leads (from orchestrator)
   - Source Agent: Lead List Builder Agent (2.2)
   - Required Fields: id, linkedin_url, email, first_name, last_name, company_name
   - Data Format: list[dict[str, Any]] with lead records
   - Handoff Method: Orchestrator passes leads list directly to run()

2. OUTPUT: DuplicateDetectionResult (returned to orchestrator)
   - Target Agent: Cross-Campaign Dedup Agent (2.4)
   - Written Fields: primary_updates, duplicate_updates, merge_results
   - Data Format: DuplicateDetectionResult dataclass with DB update operations
   - Handoff Method: Orchestrator receives result and handles DB persistence

3. HANDOFF COORDINATION:
   - Upstream Dependencies: Lead List Builder Agent (2.2) must complete first
   - Downstream Consumers: Cross-Campaign Dedup Agent (2.4)
   - Failure Handling: Returns DuplicateDetectionResult with success=False, errors populated
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query
from claude_agent_sdk.types import AssistantMessage

from src.agents.duplicate_detection.matching import (
    find_email_duplicates,
    find_fuzzy_duplicates,
    find_linkedin_duplicates,
    merge_duplicate_groups,
)
from src.agents.duplicate_detection.merge import (
    merge_duplicate_group,
    prepare_database_updates,
)
from src.agents.duplicate_detection.schemas import LeadRecord
from src.agents.duplicate_detection.tools import (
    analyze_leads_for_duplicates_tool,
    calculate_similarity_tool,
    get_dedup_summary_tool,
    merge_duplicate_groups_tool,
)

# Model constants
DEFAULT_MODEL: Final[str] = "claude-sonnet-4-20250514"
OPUS_MODEL: Final[str] = "claude-opus-4-20250514"
HAIKU_MODEL: Final[str] = "claude-haiku-3-20250310"

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class DuplicateDetectionAgentError(Exception):
    """Exception raised for Duplicate Detection agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InsufficientLeadsError(DuplicateDetectionAgentError):
    """Raised when not enough leads remain after deduplication."""

    def __init__(self, unique_leads: int, required: int) -> None:
        message = f"Only {unique_leads} unique leads remain (required: {required})"
        super().__init__(message, {"unique_leads": unique_leads, "required": required})


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class DuplicateDetectionResult:
    """Result of Duplicate Detection agent execution."""

    # Status
    success: bool = True
    status: str = "completed"  # completed, partial, failed

    # Counts
    total_checked: int = 0
    exact_duplicates: int = 0
    fuzzy_duplicates: int = 0
    total_merged: int = 0
    unique_leads: int = 0
    duplicate_rate: float = 0.0

    # Detailed results
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    merge_results: list[dict[str, Any]] = field(default_factory=list)

    # Database updates (for orchestrator)
    primary_updates: list[dict[str, Any]] = field(default_factory=list)
    duplicate_updates: list[dict[str, Any]] = field(default_factory=list)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "status": self.status,
            "total_checked": self.total_checked,
            "exact_duplicates": self.exact_duplicates,
            "fuzzy_duplicates": self.fuzzy_duplicates,
            "total_merged": self.total_merged,
            "unique_leads": self.unique_leads,
            "duplicate_rate": self.duplicate_rate,
            "duplicate_groups": self.duplicate_groups,
            "merge_results": self.merge_results,
            "primary_updates": self.primary_updates,
            "duplicate_updates": self.duplicate_updates,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Duplicate Detection Agent
# =============================================================================


class DuplicateDetectionAgent:
    """
    Duplicate Detection Agent - Phase 2, Agent 2.3.

    Uses Claude Agent SDK to orchestrate duplicate detection and merging.
    The agent identifies duplicates using exact matching (LinkedIn, email)
    and fuzzy matching (Jaro-Winkler on name + company).

    This agent is pure (no side effects). It returns detection and merge
    results that the orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use.
        fuzzy_threshold: Minimum score for fuzzy matching.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        fuzzy_threshold: float = 0.85,
    ) -> None:
        """
        Initialize Duplicate Detection Agent.

        Args:
            model: Claude model to use.
            fuzzy_threshold: Minimum composite score for fuzzy matches.
        """
        self.name = "duplicate_detection"
        self.model = model
        self.fuzzy_threshold = fuzzy_threshold

        logger.info(
            f"[{self.name}] Agent initialized (model={model}, fuzzy_threshold={fuzzy_threshold})"
        )

    @property
    def system_prompt(self) -> str:
        """System prompt for the Claude agent."""
        return """You are a data deduplication specialist identifying duplicate leads.

AVAILABLE TOOLS:
1. analyze_leads_for_duplicates - Find duplicates using exact and fuzzy matching
2. merge_duplicate_groups - Merge duplicate groups, selecting primary records
3. calculate_similarity - Calculate similarity between two specific leads
4. get_dedup_summary - Generate a summary report

DETECTION STRATEGY:
1. Exact matching (100% confidence):
   - Same LinkedIn URL
   - Same email address (case-insensitive)

2. Fuzzy matching (85%+ confidence):
   - Jaro-Winkler similarity on first name (30% weight)
   - Jaro-Winkler similarity on last name (30% weight)
   - Jaro-Winkler similarity on company name (40% weight)
   - Composite score must be >= 0.85

MERGE STRATEGY:
- Select record with most complete data as primary
- Prefer records with email addresses
- Prefer older records (created first)
- Merge fields: first non-null wins for email/phone, longest for title
- Mark duplicates with status='duplicate' and duplicate_of=primary_id
- Store merged_from IDs in primary record

QUALITY GOALS:
- Catch all true duplicates
- Minimize false positives (don't merge different people)
- Preserve data integrity
- Target duplicate rate < 15%

PROCESS:
1. Analyze all leads for duplicates
2. Merge duplicate groups
3. Generate summary report
4. Return results for database updates"""

    async def run(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
        use_claude: bool = False,
    ) -> DuplicateDetectionResult:
        """
        Execute duplicate detection for a campaign.

        This method can run in two modes:
        1. Direct mode (default): Uses Python algorithms directly
        2. Claude mode: Uses Claude Agent SDK for orchestration

        Args:
            campaign_id: Campaign UUID.
            leads: List of lead dictionaries.
            use_claude: If True, use Claude for orchestration.

        Returns:
            DuplicateDetectionResult with detection and merge results.
        """
        start_time = time.time()
        result = DuplicateDetectionResult(
            started_at=datetime.now(),
            total_checked=len(leads),
        )

        logger.info(
            f"[{self.name}] Starting duplicate detection for campaign {campaign_id} "
            f"({len(leads)} leads)"
        )

        if not leads:
            result.success = True
            result.status = "completed"
            result.unique_leads = 0
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[{self.name}] No leads to process")
            return result

        try:
            if use_claude:
                return await self._run_with_claude(campaign_id, leads, start_time)
            else:
                return await self._run_direct(campaign_id, leads, start_time)

        except Exception as e:
            logger.error(f"[{self.name}] Duplicate detection failed: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append({"type": type(e).__name__, "message": str(e)})
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def _run_direct(
        self,
        campaign_id: str,
        leads_data: list[dict[str, Any]],
        start_time: float,
    ) -> DuplicateDetectionResult:
        """
        Run duplicate detection directly with Python algorithms.

        This is the recommended mode for production - faster and more reliable.
        """
        result = DuplicateDetectionResult(
            started_at=datetime.now(),
            total_checked=len(leads_data),
        )

        # Convert to LeadRecord objects
        leads = [LeadRecord.from_dict(lead) for lead in leads_data]
        leads_by_id = {lead.id: lead for lead in leads}

        # Find exact duplicates
        linkedin_groups = find_linkedin_duplicates(leads)
        email_groups = find_email_duplicates(leads)

        # Get IDs already matched for fuzzy exclusion
        already_matched: set[str] = set()
        for group in linkedin_groups:
            already_matched.update(group.lead_ids)
        for group in email_groups:
            already_matched.update(group.lead_ids)

        # Find fuzzy duplicates
        fuzzy_groups = find_fuzzy_duplicates(
            leads,
            already_matched_ids=already_matched,
            threshold=self.fuzzy_threshold,
        )

        # Merge overlapping groups
        all_groups = merge_duplicate_groups(linkedin_groups, email_groups, fuzzy_groups)

        # Calculate counts
        exact_count = sum(len(g.lead_ids) - 1 for g in linkedin_groups + email_groups)
        fuzzy_count = sum(len(g.lead_ids) - 1 for g in fuzzy_groups)

        # Process merges
        merge_results = []
        for group in all_groups:
            if len(group.lead_ids) >= 2:
                merge_result = merge_duplicate_group(leads_by_id, group.lead_ids)
                if merge_result.duplicate_ids:
                    merge_results.append(merge_result)

        # Prepare database updates
        primary_updates, duplicate_updates = prepare_database_updates(merge_results)

        # Calculate final counts
        total_merged = sum(len(m.duplicate_ids) for m in merge_results)
        unique_leads = len(leads) - total_merged
        duplicate_rate = total_merged / len(leads) if leads else 0

        # Build result
        result.exact_duplicates = exact_count
        result.fuzzy_duplicates = fuzzy_count
        result.total_merged = total_merged
        result.unique_leads = unique_leads
        result.duplicate_rate = duplicate_rate
        result.duplicate_groups = [
            {
                "lead_ids": g.lead_ids,
                "match_type": g.match_type,
                "confidence": g.confidence,
            }
            for g in all_groups
        ]
        result.merge_results = [
            {
                "primary_id": m.primary_id,
                "duplicate_ids": m.duplicate_ids,
                "merged_fields": m.merged_fields,
            }
            for m in merge_results
        ]
        result.primary_updates = primary_updates
        result.duplicate_updates = duplicate_updates
        result.success = True
        result.status = "completed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Duplicate detection completed: "
            f"{total_merged} duplicates merged, "
            f"{unique_leads} unique leads, "
            f"rate={duplicate_rate:.1%}, "
            f"time={result.execution_time_ms}ms"
        )

        return result

    async def _run_with_claude(
        self,
        campaign_id: str,
        leads_data: list[dict[str, Any]],
        start_time: float,
    ) -> DuplicateDetectionResult:
        """
        Run duplicate detection with Claude Agent SDK orchestration.

        Uses Claude to analyze leads and coordinate the deduplication process.
        """
        result = DuplicateDetectionResult(
            started_at=datetime.now(),
            total_checked=len(leads_data),
        )

        # Build task prompt
        task_prompt = self._build_task_prompt(campaign_id, len(leads_data))

        # Create SDK MCP server with tools
        mcp_server = create_sdk_mcp_server(
            name="duplicate_detection_tools",
            tools=[
                analyze_leads_for_duplicates_tool,
                merge_duplicate_groups_tool,
                calculate_similarity_tool,
                get_dedup_summary_tool,
            ],
        )

        # Clear conflicting env var (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Tool names for allowed_tools (mcp__{server}__{tool} pattern per SDK_PATTERNS.md)
        tool_names = [
            "mcp__duplicate_detection_tools__analyze_leads_for_duplicates",
            "mcp__duplicate_detection_tools__merge_duplicate_groups",
            "mcp__duplicate_detection_tools__calculate_similarity",
            "mcp__duplicate_detection_tools__get_dedup_summary",
        ]

        # Query Claude with tools
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.system_prompt,
            setting_sources=["project"],  # Required for CLAUDE.md (CRITICAL-002)
            mcp_servers={"duplicate_detection_tools": mcp_server},
            allowed_tools=tool_names,  # Required for Claude to use tools (CRITICAL-001)
        )

        # Process messages from query iterator
        async for message in query(prompt=task_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "tool_result"):
                        tool_data = getattr(block, "tool_result", {})
                        if isinstance(tool_data, dict) and "data" in tool_data:
                            data = tool_data["data"]

                            # Check for analysis results
                            if "total_checked" in data:
                                result.total_checked = data.get(
                                    "total_checked", result.total_checked
                                )
                                result.exact_duplicates = data.get("exact_duplicates", 0)
                                result.fuzzy_duplicates = data.get("fuzzy_duplicates", 0)
                                result.unique_leads = data.get("unique_leads", 0)
                                result.duplicate_rate = data.get("duplicate_rate", 0)
                                result.duplicate_groups = data.get("duplicate_groups", [])

                            # Check for merge results
                            if "primary_updates" in data:
                                result.primary_updates = data.get("primary_updates", [])
                                result.duplicate_updates = data.get("duplicate_updates", [])
                                result.total_merged = data.get("total_merged", 0)
                                result.merge_results = data.get("merge_results", [])

        # Finalize result
        result.success = True
        result.status = "completed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Claude-orchestrated dedup completed: "
            f"{result.total_merged} duplicates merged, "
            f"{result.unique_leads} unique leads"
        )

        return result

    def _build_task_prompt(self, campaign_id: str, lead_count: int) -> str:
        """Build the task prompt for Claude."""
        return f"""Deduplicate leads for campaign {campaign_id}.

LEADS TO PROCESS: {lead_count}

INSTRUCTIONS:
1. Use analyze_leads_for_duplicates to find all duplicates
2. Use merge_duplicate_groups to merge duplicate groups
3. Use get_dedup_summary to generate final report

GOALS:
- Identify all exact duplicates (LinkedIn URL, email)
- Find fuzzy duplicates (similar name + company, threshold {self.fuzzy_threshold})
- Merge duplicate groups, selecting most complete record as primary
- Return database update operations for orchestrator

Report the final counts and any issues encountered."""


# =============================================================================
# Convenience Functions
# =============================================================================


async def detect_duplicates(
    campaign_id: str,
    leads: list[dict[str, Any]],
    fuzzy_threshold: float = 0.85,
    use_claude: bool = False,
) -> DuplicateDetectionResult:
    """
    Convenience function to detect and merge duplicates.

    Args:
        campaign_id: Campaign UUID.
        leads: List of lead dictionaries.
        fuzzy_threshold: Minimum score for fuzzy matching.
        use_claude: If True, use Claude for orchestration.

    Returns:
        DuplicateDetectionResult with detection and merge results.
    """
    agent = DuplicateDetectionAgent(fuzzy_threshold=fuzzy_threshold)
    return await agent.run(
        campaign_id=campaign_id,
        leads=leads,
        use_claude=use_claude,
    )
