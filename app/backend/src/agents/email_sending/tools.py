"""
Tools for Email Sending Agent.

SDK MCP tools for uploading leads to Instantly.ai campaigns,
managing batches, and tracking upload progress.

All tools follow Claude Agent SDK patterns:
- @tool decorator with JSON Schema validation
- Return format: {"content": [...], "is_error": bool}
- Clients created inside tools (no dependency injection - LEARN-003)
"""

import asyncio
import json
import logging
import os
import random
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from claude_agent_sdk import tool

from src.integrations.instantly import InstantlyClient, InstantlyError
from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# =============================================================================
# Module-Level Singletons (LEARN-030)
# =============================================================================

# Rate limiter: 60 requests/minute for Instantly API (per YAML spec)
_instantly_rate_limiter = TokenBucketRateLimiter(
    rate_limit=60,
    rate_window=60,
    service_name="instantly_api",
)

# Circuit breaker: 5 failures, 300s recovery (per YAML spec)
_instantly_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=300.0,
    service_name="instantly_api",
)

# Cost tracking per campaign
_cost_tracker: dict[str, float] = {}


# =============================================================================
# Helper Functions
# =============================================================================


def _get_instantly_client() -> InstantlyClient:
    """Get Instantly client with API key from environment."""
    api_key = os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        raise ValueError("INSTANTLY_API_KEY environment variable not set")
    return InstantlyClient(api_key=api_key)


def _format_lead_for_instantly(
    lead: dict[str, Any],
    email_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Format lead data for Instantly API upload.

    Maps internal fields to Instantly custom variables format.

    Args:
        lead: Lead data from database.
        email_data: Generated email data.

    Returns:
        Dictionary formatted for Instantly leads/add endpoint.
    """
    return {
        "email": lead.get("email", ""),
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "company_name": lead.get("company_name", ""),
        "custom_variables": {
            "subject": email_data.get("subject_line", ""),
            "body": email_data.get("full_email", ""),
            "first_name": lead.get("first_name", ""),
            "company": lead.get("company_name", ""),
        },
    }


async def _retry_with_exponential_backoff(
    func: Any,
    max_attempts: int = 5,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
) -> Any:
    """
    Retry an async function with exponential backoff and jitter.

    Args:
        func: Async function to retry.
        max_attempts: Maximum retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.

    Returns:
        Result from successful function call.

    Raises:
        Last exception if all retries fail.
    """
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except (ConnectionError, TimeoutError, InstantlyError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                # Exponential backoff with jitter
                delay = min(base_delay * (2**attempt), max_delay)
                jitter = delay * random.uniform(0.1, 0.3)
                actual_delay = delay + jitter
                logger.warning(f"Retry {attempt + 1}/{max_attempts} after {actual_delay:.1f}s: {e}")
                await asyncio.sleep(actual_delay)
            else:
                logger.error(f"All {max_attempts} attempts failed: {e}")

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result or exception")


# =============================================================================
# SDK MCP Tools
# =============================================================================


@tool(  # type: ignore[misc]
    name="check_resume_state",
    description="Check if resuming from a previous run by querying upload progress",
    input_schema={
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Campaign UUID to check resume state for",
            },
        },
        "required": ["campaign_id"],
    },
)
async def check_resume_state(args: dict[str, Any]) -> dict[str, Any]:
    """Check if resuming from previous run."""
    return await check_resume_state_impl(args)


async def check_resume_state_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for check_resume_state."""
    campaign_id = args.get("campaign_id", "")

    try:
        # Import here to avoid circular dependency
        from src.database.connection import get_session

        async with get_session() as session:
            # Query sending_logs for upload progress
            from sqlalchemy import text

            result = await session.execute(
                text("""
                    SELECT
                        COUNT(*) as batches_completed,
                        COALESCE(SUM(leads_uploaded), 0) as leads_uploaded,
                        COALESCE(MAX(batch_number), 0) as last_batch
                    FROM sending_logs
                    WHERE campaign_id = :campaign_id
                      AND status = 'uploaded'
                """),
                {"campaign_id": campaign_id},
            )
            row = result.fetchone()

            if row and row.batches_completed > 0:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "is_resuming": True,
                                    "start_from_batch": row.last_batch + 1,
                                    "previously_uploaded": row.leads_uploaded,
                                    "batches_completed": row.batches_completed,
                                    "message": f"Resuming from batch {row.last_batch + 1}, "
                                    f"{row.leads_uploaded} leads already uploaded",
                                }
                            ),
                        }
                    ],
                    "is_error": False,
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "is_resuming": False,
                                "start_from_batch": 1,
                                "previously_uploaded": 0,
                                "batches_completed": 0,
                                "message": "Starting fresh upload",
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

    except Exception as e:
        logger.error(f"Failed to check resume state: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="load_leads",
    description="Load leads prioritized by tier (A > B > C) for sending",
    input_schema={
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Campaign UUID to load leads for",
            },
            "batch_size": {
                "type": "integer",
                "description": "Number of leads per batch (default: 100)",
                "default": 100,
            },
            "max_leads": {
                "type": "integer",
                "description": "Maximum leads to load (default: 10000)",
                "default": 10000,
            },
            "exclude_uploaded": {
                "type": "boolean",
                "description": "Exclude already uploaded leads (default: true)",
                "default": True,
            },
        },
        "required": ["campaign_id"],
    },
)
async def load_leads(args: dict[str, Any]) -> dict[str, Any]:
    """Load leads for sending."""
    return await load_leads_impl(args)


async def load_leads_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for load_leads."""
    campaign_id = args.get("campaign_id", "")
    batch_size = args.get("batch_size", 100)
    max_leads = args.get("max_leads", 10000)
    exclude_uploaded = args.get("exclude_uploaded", True)

    try:
        from src.database.connection import get_session

        async with get_session() as session:
            from sqlalchemy import text

            # Build query with filters
            exclude_clause = ""
            if exclude_uploaded:
                exclude_clause = "AND (sending_status IS NULL OR sending_status = 'pending')"

            # exclude_clause is hardcoded string, not user input - safe
            query = f"""
                SELECT
                    l.id, l.email, l.first_name, l.last_name,
                    l.company_name, l.lead_tier, l.generated_email_id, l.lead_score,
                    ge.subject_line, ge.full_email, ge.quality_score
                FROM leads l
                LEFT JOIN generated_emails ge ON l.generated_email_id = ge.id
                WHERE l.campaign_id = :campaign_id
                  AND l.email_status = 'valid'
                  AND l.email_generation_status = 'generated'
                  {exclude_clause}
                ORDER BY l.lead_score DESC, l.lead_tier ASC
                LIMIT :max_leads
            """  # nosec B608 - exclude_clause is hardcoded, not user input
            result = await session.execute(
                text(query),
                {"campaign_id": campaign_id, "max_leads": max_leads},
            )
            rows = result.fetchall()

            # Group by tier
            leads_by_tier: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
            for row in rows:
                lead_data = {
                    "id": str(row.id),
                    "email": row.email,
                    "first_name": row.first_name,
                    "last_name": row.last_name,
                    "company_name": row.company_name,
                    "lead_tier": row.lead_tier or "C",
                    "generated_email_id": str(row.generated_email_id)
                    if row.generated_email_id
                    else None,
                    "lead_score": row.lead_score,
                    "email_data": {
                        "subject_line": row.subject_line,
                        "full_email": row.full_email,
                        "quality_score": row.quality_score,
                    },
                }
                tier = lead_data["lead_tier"].upper()
                if tier in leads_by_tier:
                    leads_by_tier[tier].append(lead_data)
                else:
                    leads_by_tier["C"].append(lead_data)

            # Create batches in tier priority order
            all_leads = leads_by_tier["A"] + leads_by_tier["B"] + leads_by_tier["C"]
            batches = [all_leads[i : i + batch_size] for i in range(0, len(all_leads), batch_size)]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "total_leads": len(all_leads),
                                "by_tier": {
                                    "tier_a": len(leads_by_tier["A"]),
                                    "tier_b": len(leads_by_tier["B"]),
                                    "tier_c": len(leads_by_tier["C"]),
                                },
                                "batch_count": len(batches),
                                "batch_size": batch_size,
                                "batches": batches,
                            }
                        ),
                    }
                ],
                "is_error": False,
            }

    except Exception as e:
        logger.error(f"Failed to load leads: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="upload_to_instantly",
    description="Upload a batch of leads to Instantly campaign with retry logic",
    input_schema={
        "type": "object",
        "properties": {
            "instantly_campaign_id": {
                "type": "string",
                "description": "Instantly campaign UUID",
            },
            "campaign_id": {
                "type": "string",
                "description": "Internal campaign UUID for logging",
            },
            "batch_number": {
                "type": "integer",
                "description": "Batch number for tracking",
            },
            "leads": {
                "type": "array",
                "description": "Array of lead objects with email, name, and email_data",
                "items": {"type": "object"},
            },
        },
        "required": ["instantly_campaign_id", "campaign_id", "batch_number", "leads"],
    },
)
async def upload_to_instantly(args: dict[str, Any]) -> dict[str, Any]:
    """Upload batch to Instantly."""
    return await upload_to_instantly_impl(args)


async def upload_to_instantly_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for upload_to_instantly."""
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    campaign_id = args.get("campaign_id", "")
    batch_number = args.get("batch_number", 0)
    leads = args.get("leads", [])

    if not leads:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"error": "No leads provided", "batch_number": batch_number}
                    ),
                }
            ],
            "is_error": True,
        }

    # Check circuit breaker
    if not _instantly_circuit_breaker.can_proceed():
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "error": "Circuit breaker open - Instantly API unavailable",
                            "batch_number": batch_number,
                            "retry_after_seconds": _instantly_circuit_breaker.recovery_timeout,
                        }
                    ),
                }
            ],
            "is_error": True,
        }

    try:
        # Rate limiting
        await _instantly_rate_limiter.acquire()

        # Format leads for Instantly
        formatted_leads = []
        for lead in leads:
            email_data = lead.get("email_data", {})
            formatted_leads.append(_format_lead_for_instantly(lead, email_data))

        # Get client and upload
        client = _get_instantly_client()

        async def do_upload() -> dict[str, Any]:
            result = await client.bulk_add_leads(
                leads=formatted_leads,
                campaign_id=instantly_campaign_id,
            )
            return {
                "created_count": result.created_count,
                "updated_count": result.updated_count,
                "failed_count": result.failed_count,
                "created_leads": result.created_leads,
                "failed_leads": result.failed_leads,
            }

        result = await _retry_with_exponential_backoff(do_upload)

        # Record success
        _instantly_circuit_breaker.record_success()

        # Track cost (per YAML: $0.001 per lead)
        leads_uploaded = result["created_count"] + result["updated_count"]
        cost = leads_uploaded * 0.001
        _cost_tracker[campaign_id] = _cost_tracker.get(campaign_id, 0.0) + cost

        # Log batch to database
        await _log_batch_to_database(
            campaign_id=campaign_id,
            instantly_campaign_id=instantly_campaign_id,
            batch_number=batch_number,
            leads_uploaded=leads_uploaded,
            lead_ids=[lead.get("id") for lead in leads],
            instantly_response=result,
        )

        # Update leads sending status
        lead_ids = [lead.get("id") for lead in leads if lead.get("id")]
        await _update_leads_status(lead_ids, "queued")

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "batch_number": batch_number,
                            "leads_uploaded": leads_uploaded,
                            "leads_failed": result["failed_count"],
                            "created_count": result["created_count"],
                            "updated_count": result["updated_count"],
                            "cost_incurred": cost,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except InstantlyError as e:
        _instantly_circuit_breaker.record_failure()
        logger.error(f"Instantly API error on batch {batch_number}: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "error": str(e),
                            "batch_number": batch_number,
                            "leads_failed": len(leads),
                        }
                    ),
                }
            ],
            "is_error": True,
        }
    except Exception as e:
        _instantly_circuit_breaker.record_failure()
        logger.error(f"Failed to upload batch {batch_number}: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


async def _log_batch_to_database(
    campaign_id: str,
    instantly_campaign_id: str,
    batch_number: int,
    leads_uploaded: int,
    lead_ids: list[str | None],
    instantly_response: dict[str, Any],
) -> None:
    """Log batch upload to sending_logs table."""
    try:
        from src.database.connection import get_session

        async with get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text("""
                    INSERT INTO sending_logs (
                        id, campaign_id, instantly_campaign_id, batch_number,
                        leads_uploaded, lead_ids, status, instantly_response,
                        created_at, completed_at
                    ) VALUES (
                        :id, :campaign_id, :instantly_campaign_id, :batch_number,
                        :leads_uploaded, :lead_ids, 'uploaded', :instantly_response,
                        :created_at, :completed_at
                    )
                """),
                {
                    "id": str(uuid4()),
                    "campaign_id": campaign_id,
                    "instantly_campaign_id": instantly_campaign_id,
                    "batch_number": batch_number,
                    "leads_uploaded": leads_uploaded,
                    "lead_ids": [lid for lid in lead_ids if lid],
                    "instantly_response": json.dumps(instantly_response),
                    "created_at": datetime.now(UTC),
                    "completed_at": datetime.now(UTC),
                },
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to log batch to database: {e}")


async def _update_leads_status(lead_ids: list[str], status: str) -> None:
    """Update leads sending status in database."""
    if not lead_ids:
        return

    try:
        from src.database.connection import get_session

        async with get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text("""
                    UPDATE leads
                    SET sending_status = :status,
                        queued_at = :queued_at,
                        updated_at = :updated_at
                    WHERE id = ANY(:lead_ids)
                """),
                {
                    "status": status,
                    "queued_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "lead_ids": lead_ids,
                },
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to update leads status: {e}")


@tool(  # type: ignore[misc]
    name="verify_upload",
    description="Verify upload success by comparing lead counts with 5% tolerance",
    input_schema={
        "type": "object",
        "properties": {
            "instantly_campaign_id": {
                "type": "string",
                "description": "Instantly campaign UUID",
            },
            "expected_count": {
                "type": "integer",
                "description": "Expected number of leads uploaded",
            },
            "tolerance_percent": {
                "type": "number",
                "description": "Tolerance percentage (default: 5)",
                "default": 5,
            },
        },
        "required": ["instantly_campaign_id", "expected_count"],
    },
)
async def verify_upload(args: dict[str, Any]) -> dict[str, Any]:
    """Verify upload success."""
    return await verify_upload_impl(args)


async def verify_upload_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for verify_upload."""
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    expected_count = args.get("expected_count", 0)
    tolerance_percent = args.get("tolerance_percent", 5)

    try:
        client = _get_instantly_client()

        # Get campaign analytics for lead count
        analytics = await client.get_campaign_analytics(instantly_campaign_id)

        # Handle single campaign analytics return
        actual_count = analytics.total_leads if hasattr(analytics, "total_leads") else 0

        # Calculate discrepancy
        discrepancy = abs(actual_count - expected_count)
        tolerance = expected_count * (tolerance_percent / 100)
        verification_passed = discrepancy <= tolerance

        # Get campaign status
        campaign = await client.get_campaign(instantly_campaign_id)
        campaign_status = campaign.status.name if campaign else "unknown"

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "verification_passed": verification_passed,
                            "instantly_lead_count": actual_count,
                            "expected_count": expected_count,
                            "discrepancy": discrepancy,
                            "tolerance": tolerance,
                            "campaign_status": campaign_status,
                            "message": "Verification passed"
                            if verification_passed
                            else f"Lead count discrepancy: {discrepancy} (tolerance: {tolerance})",
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except InstantlyError as e:
        logger.error(f"Instantly API error during verification: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Failed to verify upload: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="start_sending",
    description="Start or resume campaign sending in Instantly",
    input_schema={
        "type": "object",
        "properties": {
            "instantly_campaign_id": {
                "type": "string",
                "description": "Instantly campaign UUID to activate",
            },
            "campaign_id": {
                "type": "string",
                "description": "Internal campaign UUID for status update",
            },
        },
        "required": ["instantly_campaign_id", "campaign_id"],
    },
)
async def start_sending(args: dict[str, Any]) -> dict[str, Any]:
    """Start campaign sending."""
    return await start_sending_impl(args)


async def start_sending_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for start_sending."""
    instantly_campaign_id = args.get("instantly_campaign_id", "")
    campaign_id = args.get("campaign_id", "")

    try:
        client = _get_instantly_client()

        # Activate campaign
        campaign = await client.activate_campaign(instantly_campaign_id)

        # Update internal campaign status
        await _update_campaign_status(
            campaign_id=campaign_id,
            instantly_campaign_id=instantly_campaign_id,
            status="sending",
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "sending_started": True,
                            "campaign_status": campaign.status.name,
                            "campaign_id": instantly_campaign_id,
                            "message": "Campaign sending started successfully",
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except InstantlyError as e:
        logger.error(f"Failed to start sending: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }
    except Exception as e:
        logger.error(f"Failed to start sending: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


async def _update_campaign_status(
    campaign_id: str,
    instantly_campaign_id: str,
    status: str,
) -> None:
    """Update campaign sending status in database."""
    try:
        from src.database.connection import get_session

        async with get_session() as session:
            from sqlalchemy import text

            # Update campaigns table
            await session.execute(
                text("""
                    UPDATE campaigns
                    SET sending_status = :status,
                        updated_at = :updated_at
                    WHERE id = :campaign_id
                """),
                {
                    "status": status,
                    "updated_at": datetime.now(UTC),
                    "campaign_id": campaign_id,
                },
            )

            # Update instantly_campaigns table
            await session.execute(
                text("""
                    UPDATE instantly_campaigns
                    SET status = 'active',
                        sending_started_at = :started_at,
                        updated_at = :updated_at
                    WHERE campaign_id = :campaign_id
                """),
                {
                    "started_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "campaign_id": campaign_id,
                },
            )

            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to update campaign status: {e}")


@tool(  # type: ignore[misc]
    name="update_sending_stats",
    description="Update campaign sending statistics after upload completion",
    input_schema={
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Internal campaign UUID",
            },
            "total_uploaded": {
                "type": "integer",
                "description": "Total leads uploaded",
            },
            "tier_a_uploaded": {
                "type": "integer",
                "description": "Tier A leads uploaded",
            },
            "tier_b_uploaded": {
                "type": "integer",
                "description": "Tier B leads uploaded",
            },
            "tier_c_uploaded": {
                "type": "integer",
                "description": "Tier C leads uploaded",
            },
            "cost_incurred": {
                "type": "number",
                "description": "Total cost incurred",
            },
        },
        "required": ["campaign_id", "total_uploaded"],
    },
)
async def update_sending_stats(args: dict[str, Any]) -> dict[str, Any]:
    """Update sending statistics."""
    return await update_sending_stats_impl(args)


async def update_sending_stats_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation for update_sending_stats."""
    campaign_id = args.get("campaign_id", "")
    total_uploaded = args.get("total_uploaded", 0)
    tier_a_uploaded = args.get("tier_a_uploaded", 0)
    tier_b_uploaded = args.get("tier_b_uploaded", 0)
    tier_c_uploaded = args.get("tier_c_uploaded", 0)
    cost_incurred = args.get("cost_incurred", 0.0)

    try:
        from src.database.connection import get_session

        async with get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text("""
                    UPDATE campaigns
                    SET leads_queued = :total_uploaded,
                        updated_at = :updated_at
                    WHERE id = :campaign_id
                """),
                {
                    "total_uploaded": total_uploaded,
                    "updated_at": datetime.now(UTC),
                    "campaign_id": campaign_id,
                },
            )

            # Update instantly_campaigns with leads_uploaded
            await session.execute(
                text("""
                    UPDATE instantly_campaigns
                    SET leads_uploaded = :total_uploaded,
                        updated_at = :updated_at
                    WHERE campaign_id = :campaign_id
                """),
                {
                    "total_uploaded": total_uploaded,
                    "updated_at": datetime.now(UTC),
                    "campaign_id": campaign_id,
                },
            )

            await session.commit()

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "campaign_id": campaign_id,
                            "total_uploaded": total_uploaded,
                            "tier_a_uploaded": tier_a_uploaded,
                            "tier_b_uploaded": tier_b_uploaded,
                            "tier_c_uploaded": tier_c_uploaded,
                            "cost_incurred": cost_incurred,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

    except Exception as e:
        logger.error(f"Failed to update sending stats: {e}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "is_error": True,
        }


def get_campaign_cost(campaign_id: str) -> float:
    """Get tracked cost for a campaign."""
    return _cost_tracker.get(campaign_id, 0.0)


def reset_cost_tracker(campaign_id: str | None = None) -> None:
    """Reset cost tracker for a campaign or all campaigns."""
    if campaign_id:
        _cost_tracker.pop(campaign_id, None)
    else:
        _cost_tracker.clear()
