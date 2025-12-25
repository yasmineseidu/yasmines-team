"""
Data Validation Agent - Phase 2, Agent 2.2.

Uses Claude Agent SDK to validate and normalize scraped lead data.
Checks required fields, normalizes names and job titles, validates
URLs and emails, and prepares data for deduplication.

Phase 2 Pipeline Position:
Input: Raw leads from Lead List Builder Agent (2.1)
Output: Validated leads for Duplicate Detection Agent (2.3)

Per LEARN-007: This agent is pure (no side effects). The orchestrator
handles all database persistence.

Database Interactions:
1. INPUT TABLE: leads
   - Source Agent: Lead List Builder (2.1)
   - Required Fields: id, linkedin_url, first_name, last_name, company_name, title
   - Data Format: LeadModel with status='new'
   - Handoff Method: database table (filtered by campaign_id and status='new')

2. OUTPUT TABLE: leads (via orchestrator)
   - Target Agent(s): Duplicate Detection (2.3)
   - Written Fields: validation_status, validation_errors, status, normalized fields
   - Data Format: LeadValidationResult per lead
   - Handoff Method: orchestrator persists results

3. HANDOFF COORDINATION:
   - Upstream Dependencies: Lead List Builder (2.1) must complete
   - Downstream Consumers: Duplicate Detection (2.3)
   - Failure Handling: Returns partial results, orchestrator handles retry
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server
from claude_agent_sdk.types import AssistantMessage, TextBlock

from src.agents.data_validation.normalizers import normalize_lead
from src.agents.data_validation.schemas import (
    BatchValidationResult,
    DataValidationResult,
    LeadValidationResult,
    ValidationHandoff,
)
from src.agents.data_validation.tools import DATA_VALIDATION_TOOLS
from src.agents.data_validation.validators import validate_lead

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class DataValidationAgentError(Exception):
    """Exception raised for data validation agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationBatchError(DataValidationAgentError):
    """Raised when a batch validation fails."""

    def __init__(self, batch_number: int, error: str) -> None:
        super().__init__(
            f"Batch {batch_number} validation failed: {error}",
            {"batch_number": batch_number},
        )


# =============================================================================
# Data Validation Agent
# =============================================================================


class DataValidationAgent:
    """
    Data Validation Agent - Phase 2, Agent 2.2.

    Uses Claude Agent SDK to orchestrate lead validation. The agent can
    optionally use Claude to make decisions about validation, but primarily
    uses the direct validation path for efficiency with large datasets.

    This agent is pure (no side effects). It returns validation results
    that the orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use (for AI-assisted validation).
        batch_size: Number of leads per batch.
        max_parallel_batches: Maximum concurrent batches.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        batch_size: int = 1000,
        max_parallel_batches: int = 10,
        use_claude: bool = False,
    ) -> None:
        """
        Initialize Data Validation Agent.

        Args:
            model: Claude model to use for AI-assisted validation.
            batch_size: Number of leads per validation batch.
            max_parallel_batches: Maximum concurrent batch processing.
            use_claude: Whether to use Claude for orchestration (default: False for efficiency).
        """
        self.name = "data_validation"
        self.model = model
        self.batch_size = batch_size
        self.max_parallel_batches = max_parallel_batches
        self.use_claude = use_claude

        logger.info(
            f"[{self.name}] Agent initialized "
            f"(model={model}, batch_size={batch_size}, parallel={max_parallel_batches})"
        )

    @property
    def system_prompt(self) -> str:
        """System prompt for Claude-assisted validation."""
        return """You are a data quality specialist validating and normalizing lead data.

Your job is to ensure lead data is clean, complete, and ready for outreach.

CRITICAL FIELDS (must be present and valid):
- linkedin_url: Valid LinkedIn profile URL
- first_name: Person's first name (1-100 chars)
- last_name: Person's last name (1-100 chars)
- company_name: Company name (1-200 chars)
- job_title: Job title (1-200 chars)

OPTIONAL FIELDS (validate if present):
- email: Valid email format (if present)
- company_size: Must be valid range (1-10, 11-50, etc.)
- location, city, state, country

NORMALIZATION RULES:
- Title case names (John Smith, not JOHN SMITH)
- Expand abbreviations (VP -> Vice President)
- Remove legal suffixes (Inc., LLC, Ltd.)
- Derive full_name from first_name + last_name

EMAIL HANDLING:
- Email is optional for validation
- Flag leads missing email for Phase 3 enrichment
- Validate format if email is present

Use the validate_lead_batch tool to process leads and aggregate_validation_results to compile results."""

    async def run(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
    ) -> DataValidationResult:
        """
        Execute lead validation for a campaign.

        This is the main entry point for the agent. It processes leads in
        batches, either using Claude orchestration or direct validation.

        Args:
            campaign_id: Campaign UUID.
            leads: List of lead dictionaries to validate.

        Returns:
            DataValidationResult with validation statistics and individual results.
        """
        start_time = time.time()
        result = DataValidationResult(
            campaign_id=campaign_id,
            started_at=datetime.now(),
        )

        if not leads:
            logger.warning(f"[{self.name}] No leads to validate for campaign {campaign_id}")
            result.status = "completed"
            result.completed_at = datetime.now()
            return result

        logger.info(
            f"[{self.name}] Starting validation for campaign {campaign_id} "
            f"({len(leads)} leads, batch_size={self.batch_size})"
        )

        try:
            if self.use_claude:
                # Use Claude Agent SDK for orchestration
                result = await self._run_with_claude(campaign_id, leads, result)
            else:
                # Direct validation for efficiency (recommended for large datasets)
                result = await self._run_direct(campaign_id, leads, result)

            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[{self.name}] Validation complete for campaign {campaign_id}: "
                f"{result.total_valid}/{result.total_processed} valid "
                f"({result.validation_rate:.1%}), time={result.execution_time_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Validation failed for campaign {campaign_id}: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append({"type": type(e).__name__, "message": str(e)})
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def _run_direct(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
        result: DataValidationResult,
    ) -> DataValidationResult:
        """
        Run validation directly without Claude orchestration.

        This is the efficient path for processing large lead volumes.
        Uses parallel batch processing with asyncio.

        Args:
            campaign_id: Campaign UUID.
            leads: List of leads to validate.
            result: Result object to populate.

        Returns:
            Updated DataValidationResult.
        """
        # Split leads into batches
        batches = [leads[i : i + self.batch_size] for i in range(0, len(leads), self.batch_size)]
        result.total_batches = len(batches)

        logger.info(
            f"[{self.name}] Processing {len(leads)} leads in {len(batches)} batches "
            f"(max {self.max_parallel_batches} parallel)"
        )

        # Process batches in parallel with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_parallel_batches)
        tasks = [
            self._validate_batch_async(batch, i + 1, semaphore) for i, batch in enumerate(batches)
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        error_breakdown: dict[str, int] = {}
        needs_enrichment = 0

        for batch_result in batch_results:
            if isinstance(batch_result, BaseException):
                result.errors.append({"type": "batch_error", "message": str(batch_result)})
                continue

            # Type narrowing: batch_result is now BatchValidationResult
            batch: BatchValidationResult = batch_result
            result.batch_results.append(batch)
            result.total_processed += batch.batch_size
            result.total_valid += batch.valid_count
            result.total_invalid += batch.invalid_count

            # Count leads needing enrichment
            for lead_result in batch.results:
                if lead_result.needs_email_enrichment:
                    needs_enrichment += 1

                # Aggregate errors
                for error in lead_result.errors:
                    error_type = self._categorize_error(error)
                    error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1

        result.needs_enrichment = needs_enrichment
        result.error_breakdown = error_breakdown
        result.validation_rate = (
            result.total_valid / result.total_processed if result.total_processed > 0 else 0.0
        )
        result.status = "completed"

        return result

    async def _validate_batch_async(
        self,
        batch: list[dict[str, Any]],
        batch_number: int,
        semaphore: asyncio.Semaphore,
    ) -> BatchValidationResult:
        """
        Validate a single batch of leads asynchronously.

        Args:
            batch: List of leads in this batch.
            batch_number: Batch number for tracking.
            semaphore: Semaphore for concurrency control.

        Returns:
            BatchValidationResult with validation results.
        """
        async with semaphore:
            return await asyncio.to_thread(self._validate_batch_sync, batch, batch_number)

    def _validate_batch_sync(
        self,
        batch: list[dict[str, Any]],
        batch_number: int,
    ) -> BatchValidationResult:
        """
        Validate a batch of leads synchronously.

        This is called from a thread pool to avoid blocking the event loop.

        Args:
            batch: List of leads in this batch.
            batch_number: Batch number for tracking.

        Returns:
            BatchValidationResult with validation results.
        """
        start_time = time.time()

        result = BatchValidationResult(
            batch_number=batch_number,
            batch_size=len(batch),
        )

        for lead in batch:
            lead_id = str(lead.get("id", "unknown"))

            # Normalize
            normalized = normalize_lead(lead)

            # Validate
            validation = validate_lead(normalized)

            # Check if needs enrichment
            needs_enrichment = not lead.get("email")

            lead_result = LeadValidationResult(
                lead_id=lead_id,
                is_valid=validation["is_valid"],
                status=validation["status"],
                errors=validation["errors"],
                warnings=validation["warnings"],
                normalized_data=validation["normalized"],
                needs_email_enrichment=needs_enrichment,
            )

            result.results.append(lead_result)

            if validation["is_valid"]:
                result.valid_count += 1
            else:
                result.invalid_count += 1

        result.processing_time_ms = int((time.time() - start_time) * 1000)

        logger.debug(
            f"[{self.name}] Batch {batch_number}: "
            f"{result.valid_count} valid, {result.invalid_count} invalid, "
            f"{result.processing_time_ms}ms"
        )

        return result

    async def _run_with_claude(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
        result: DataValidationResult,
    ) -> DataValidationResult:
        """
        Run validation with Claude Agent SDK orchestration.

        This path uses Claude to orchestrate validation, which is useful
        for complex validation scenarios or when AI decision-making is needed.

        Args:
            campaign_id: Campaign UUID.
            leads: List of leads to validate.
            result: Result object to populate.

        Returns:
            Updated DataValidationResult.
        """
        # Split into batches for tool calls
        batches = [leads[i : i + self.batch_size] for i in range(0, len(leads), self.batch_size)]
        result.total_batches = len(batches)

        # Build task prompt
        task_prompt = self._build_task_prompt(campaign_id, len(leads), len(batches))

        # Create SDK MCP server with validation tools
        mcp_server = create_sdk_mcp_server(
            name="data_validation_tools",
            tools=DATA_VALIDATION_TOOLS,
        )

        # Clear conflicting env var (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Query Claude using ClaudeSDKClient
        options = ClaudeAgentOptions(
            model=self.model,
            mcp_servers={"validation": mcp_server},  # dict, not list
            system_prompt=self.system_prompt,
            permission_mode="bypassPermissions",  # Automated agent, no user prompts
            allowed_tools=[
                "mcp__validation__validate_lead_batch",
                "mcp__validation__aggregate_validation_results",
                "mcp__validation__validate_single_lead",
            ],
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query(task_prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logger.debug(f"[{self.name}] Claude: {block.text[:200]}")

                        # Extract tool results
                        if hasattr(block, "tool_result"):
                            tool_data = getattr(block, "tool_result", {})
                            if isinstance(tool_data, dict) and "data" in tool_data:
                                self._process_tool_result(tool_data["data"], result)

        # If Claude didn't process all leads, fall back to direct
        if result.total_processed < len(leads):
            logger.info(
                f"[{self.name}] Claude processed {result.total_processed}/{len(leads)}, "
                f"falling back to direct validation for remaining"
            )
            remaining_leads = leads[result.total_processed :]
            direct_result = await self._run_direct(
                campaign_id, remaining_leads, DataValidationResult(campaign_id=campaign_id)
            )

            # Merge results
            result.total_processed += direct_result.total_processed
            result.total_valid += direct_result.total_valid
            result.total_invalid += direct_result.total_invalid
            result.batch_results.extend(direct_result.batch_results)

        # Calculate final stats
        result.validation_rate = (
            result.total_valid / result.total_processed if result.total_processed > 0 else 0.0
        )
        result.status = "completed"

        return result

    def _process_tool_result(
        self,
        data: dict[str, Any],
        result: DataValidationResult,
    ) -> None:
        """
        Process tool result from Claude and update result.

        Args:
            data: Tool result data.
            result: Result object to update.
        """
        # Check for batch validation result
        if "batch_number" in data and "results" in data:
            batch_result = BatchValidationResult(
                batch_number=data["batch_number"],
                batch_size=data.get("batch_size", 0),
                valid_count=data.get("valid_count", 0),
                invalid_count=data.get("invalid_count", 0),
                processing_time_ms=data.get("processing_time_ms", 0),
            )

            for r in data.get("results", []):
                lead_result = LeadValidationResult(
                    lead_id=r.get("lead_id", ""),
                    is_valid=r.get("is_valid", False),
                    status=r.get("status", "invalid"),
                    errors=r.get("errors", []),
                    warnings=r.get("warnings", []),
                    normalized_data=r.get("normalized_data", {}),
                    needs_email_enrichment=r.get("needs_email_enrichment", False),
                )
                batch_result.results.append(lead_result)

            result.batch_results.append(batch_result)
            result.total_processed += batch_result.batch_size
            result.total_valid += batch_result.valid_count
            result.total_invalid += batch_result.invalid_count

        # Check for aggregated result
        elif "total_processed" in data:
            result.error_breakdown = data.get("error_breakdown", {})
            result.needs_enrichment = data.get("needs_enrichment", 0)

    def _build_task_prompt(
        self,
        campaign_id: str,
        total_leads: int,
        total_batches: int,
    ) -> str:
        """Build task prompt for Claude."""
        return f"""Validate leads for campaign {campaign_id}.

LEAD COUNT: {total_leads} leads in {total_batches} batches

TASK:
1. Use validate_lead_batch to process each batch of leads
2. Track validation results (valid, invalid, needs enrichment)
3. Use aggregate_validation_results to compile final statistics

Process all leads and report validation results."""

    def _categorize_error(self, error: str) -> str:
        """Categorize an error message."""
        error_lower = error.lower()

        if "linkedin" in error_lower:
            return "missing_linkedin"
        if "first_name" in error_lower:
            return "missing_first_name"
        if "last_name" in error_lower:
            return "missing_last_name"
        if "company" in error_lower:
            return "missing_company"
        if "job_title" in error_lower or "title" in error_lower:
            return "missing_job_title"
        if "email" in error_lower:
            return "invalid_email"

        return "other"

    def get_handoff(self, result: DataValidationResult) -> ValidationHandoff:
        """
        Create handoff data for Duplicate Detection Agent (2.3).

        Args:
            result: Validation result.

        Returns:
            ValidationHandoff with data for next agent.
        """
        return ValidationHandoff(
            campaign_id=result.campaign_id,
            total_valid_leads=result.total_valid,
            validation_rate=result.validation_rate,
            needs_enrichment_count=result.needs_enrichment,
        )


# =============================================================================
# Convenience Functions
# =============================================================================


async def validate_leads(
    campaign_id: str,
    leads: list[dict[str, Any]],
    batch_size: int = 1000,
    use_claude: bool = False,
) -> DataValidationResult:
    """
    Convenience function to validate leads.

    Args:
        campaign_id: Campaign UUID.
        leads: List of lead dictionaries.
        batch_size: Leads per batch.
        use_claude: Whether to use Claude orchestration.

    Returns:
        DataValidationResult with validation results.
    """
    agent = DataValidationAgent(batch_size=batch_size, use_claude=use_claude)
    return await agent.run(campaign_id, leads)
