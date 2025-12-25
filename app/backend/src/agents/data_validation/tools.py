"""
SDK MCP Tools for Data Validation Agent.

Provides Claude Agent SDK @tool decorated functions for:
- validate_lead_batch: Validate a batch of leads
- aggregate_validation: Aggregate validation results

Per LEARN-003: Tools must be self-contained - no dependency injection.
All dependencies (validators, normalizers) are imported inside functions.
"""

import json
import logging
import time
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Tool
# =============================================================================


@tool(
    name="validate_lead_batch",
    description=(
        "Validate and normalize a batch of leads. "
        "Checks required fields (linkedin_url, first_name, last_name, company_name, job_title), "
        "validates formats (email, LinkedIn URL), normalizes data (title case names, "
        "expand job title abbreviations), and flags leads missing email for enrichment. "
        "Returns validation results with normalized data for each lead."
    ),
    input_schema={
        "leads": list,  # List of lead dictionaries
        "batch_number": int,  # Batch number for tracking
    },
)
async def validate_lead_batch_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for validating a batch of leads.

    This tool is self-contained per LEARN-003. It imports validators and
    normalizers inside the function to avoid dependency injection issues.

    Args:
        args: Tool arguments with leads list and batch_number.

    Returns:
        Tool result with validation results.
    """
    start_time = time.time()

    leads = args.get("leads", [])
    batch_number = args.get("batch_number", 1)

    if not leads:
        return {
            "content": [{"type": "text", "text": "No leads to validate"}],
            "is_error": True,
        }

    try:
        # Import inside function per LEARN-003
        from src.agents.data_validation.normalizers import normalize_lead
        from src.agents.data_validation.validators import validate_lead

        results: list[dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0
        error_counts: dict[str, int] = {}

        for lead in leads:
            lead_id = str(lead.get("id", "unknown"))

            # Normalize first
            normalized = normalize_lead(lead)

            # Then validate
            validation = validate_lead(normalized)

            # Track errors
            for error in validation.get("errors", []):
                # Extract error type from message
                error_type = _extract_error_type(error)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

            if validation["is_valid"]:
                valid_count += 1
            else:
                invalid_count += 1

            # Check if needs email enrichment
            needs_enrichment = normalized.get("needs_email_enrichment", False) or not lead.get(
                "email"
            )

            results.append(
                {
                    "lead_id": lead_id,
                    "is_valid": validation["is_valid"],
                    "status": validation["status"],
                    "new_status": validation["new_status"],
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                    "normalized_data": validation["normalized"],
                    "needs_email_enrichment": needs_enrichment,
                }
            )

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Batch {batch_number}: Validated {len(leads)} leads "
            f"(valid={valid_count}, invalid={invalid_count}, time={processing_time_ms}ms)"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Validated batch {batch_number}: "
                        f"{valid_count} valid, {invalid_count} invalid"
                    ),
                }
            ],
            "data": {
                "batch_number": batch_number,
                "batch_size": len(leads),
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "results": results,
                "error_counts": error_counts,
                "processing_time_ms": processing_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"Error validating batch {batch_number}: {e}")
        return {
            "content": [{"type": "text", "text": f"Validation error: {e}"}],
            "is_error": True,
        }


def _extract_error_type(error_message: str) -> str:
    """
    Extract error type from error message.

    Args:
        error_message: Full error message.

    Returns:
        Error type key.
    """
    error_map = {
        "linkedin_url": "missing_linkedin",
        "first_name": "missing_first_name",
        "last_name": "missing_last_name",
        "company_name": "missing_company",
        "job_title": "missing_job_title",
        "email format": "invalid_email",
        "invalid characters": "invalid_characters",
    }

    for key, error_type in error_map.items():
        if key in error_message.lower():
            return error_type

    return "other"


# =============================================================================
# Aggregation Tool
# =============================================================================


@tool(
    name="aggregate_validation_results",
    description=(
        "Aggregate validation results from all batches. "
        "Computes total counts, validation rate, and error breakdown. "
        "Returns summary statistics for the campaign."
    ),
    input_schema={
        "batch_results": list,  # List of batch result dictionaries
        "campaign_id": str,  # Campaign UUID
    },
)
async def aggregate_validation_results_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for aggregating validation results.

    Args:
        args: Tool arguments with batch_results list.

    Returns:
        Tool result with aggregated statistics.
    """
    batch_results = args.get("batch_results", [])
    campaign_id = args.get("campaign_id", "")

    if not batch_results:
        return {
            "content": [{"type": "text", "text": "No batch results to aggregate"}],
            "is_error": True,
        }

    try:
        total_processed = 0
        total_valid = 0
        total_invalid = 0
        total_needs_enrichment = 0
        error_breakdown: dict[str, int] = {}
        total_time_ms = 0

        for batch in batch_results:
            batch_size = batch.get("batch_size", 0)
            valid_count = batch.get("valid_count", 0)
            invalid_count = batch.get("invalid_count", 0)

            total_processed += batch_size
            total_valid += valid_count
            total_invalid += invalid_count
            total_time_ms += batch.get("processing_time_ms", 0)

            # Aggregate error counts
            for error_type, count in batch.get("error_counts", {}).items():
                error_breakdown[error_type] = error_breakdown.get(error_type, 0) + count

            # Count needs enrichment
            for result in batch.get("results", []):
                if result.get("needs_email_enrichment"):
                    total_needs_enrichment += 1

        # Calculate validation rate
        validation_rate = total_valid / total_processed if total_processed > 0 else 0.0

        summary = {
            "campaign_id": campaign_id,
            "total_processed": total_processed,
            "total_valid": total_valid,
            "total_invalid": total_invalid,
            "validation_rate": round(validation_rate, 4),
            "needs_enrichment": total_needs_enrichment,
            "error_breakdown": error_breakdown,
            "total_batches": len(batch_results),
            "total_processing_time_ms": total_time_ms,
        }

        logger.info(
            f"Aggregated validation for campaign {campaign_id}: "
            f"{total_valid}/{total_processed} valid ({validation_rate:.1%})"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Validation complete: {total_valid}/{total_processed} valid "
                        f"({validation_rate:.1%}), {total_needs_enrichment} need email enrichment"
                    ),
                }
            ],
            "data": summary,
        }

    except Exception as e:
        logger.error(f"Error aggregating results: {e}")
        return {
            "content": [{"type": "text", "text": f"Aggregation error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Single Lead Validation Tool (for debugging/testing)
# =============================================================================


@tool(
    name="validate_single_lead",
    description=(
        "Validate and normalize a single lead. "
        "Useful for debugging or testing validation rules. "
        "Returns detailed validation result with normalized data."
    ),
    input_schema={
        "lead": dict,  # Lead dictionary
    },
)
async def validate_single_lead_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for validating a single lead.

    Args:
        args: Tool arguments with lead dictionary.

    Returns:
        Tool result with validation result.
    """
    lead = args.get("lead", {})

    if not lead:
        return {
            "content": [{"type": "text", "text": "No lead provided"}],
            "is_error": True,
        }

    try:
        # Import inside function per LEARN-003
        from src.agents.data_validation.normalizers import normalize_lead
        from src.agents.data_validation.validators import validate_lead

        # Normalize
        normalized = normalize_lead(lead)

        # Validate
        validation = validate_lead(normalized)

        # Check if needs enrichment
        needs_enrichment = not lead.get("email")

        result = {
            "lead_id": str(lead.get("id", "test")),
            "is_valid": validation["is_valid"],
            "status": validation["status"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "normalized_data": validation["normalized"],
            "needs_email_enrichment": needs_enrichment,
        }

        status_text = "VALID" if validation["is_valid"] else "INVALID"
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Lead validation: {status_text}\n"
                        f"Errors: {json.dumps(validation['errors'])}\n"
                        f"Warnings: {json.dumps(validation['warnings'])}"
                    ),
                }
            ],
            "data": result,
        }

    except Exception as e:
        logger.error(f"Error validating lead: {e}")
        return {
            "content": [{"type": "text", "text": f"Validation error: {e}"}],
            "is_error": True,
        }


# =============================================================================
# Tool List for Agent Registration
# =============================================================================

# Export list of tools for easy registration with SDK MCP server
DATA_VALIDATION_TOOLS = [
    validate_lead_batch_tool,
    aggregate_validation_results_tool,
    validate_single_lead_tool,
]
