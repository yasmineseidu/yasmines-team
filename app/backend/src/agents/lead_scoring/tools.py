"""
Tools for Lead Scoring Agent.

SDK MCP tools for scoring operations following SDK_PATTERNS.md.
"""

import json
import logging
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

# Module-level storage for scoring context
# Tools are self-contained per LEARN-003 - no DI allowed
_scoring_context: dict[str, Any] = {}
_leads_data: list[dict[str, Any]] = []


def set_scoring_context(context: dict[str, Any]) -> None:
    """Set scoring context for tools to use."""
    global _scoring_context
    _scoring_context = context


def set_leads_data(leads: list[dict[str, Any]]) -> None:
    """Set leads data for tools to use."""
    global _leads_data
    _leads_data = leads


@tool(  # type: ignore[misc]
    name="load_scoring_context",
    description="Load scoring context including niche, personas, and industry fit scores",
    input_schema={
        "campaign_id": str,
        "niche_id": str,
    },
)
async def load_scoring_context_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Load scoring context from database.

    In production, this would query the database. For SDK usage,
    the context is pre-loaded by the agent.
    """
    try:
        campaign_id = args.get("campaign_id", "")
        niche_id = args.get("niche_id", "")

        # Context is pre-loaded by agent (per LEARN-003 - no DI in tools)
        context = _scoring_context

        if not context:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": False,
                                "error": "Scoring context not loaded",
                            }
                        ),
                    }
                ],
                "is_error": True,
            }

        logger.info(f"Loaded scoring context for campaign {campaign_id}, niche {niche_id}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "context": {
                                "niche_name": context.get("niche", {}).get("name", ""),
                                "persona_count": len(context.get("personas", [])),
                                "industry_scores_count": len(
                                    context.get("industry_fit_scores", [])
                                ),
                                "target_titles_count": len(
                                    context.get("niche", {}).get("job_titles", [])
                                ),
                            },
                        }
                    ),
                }
            ],
        }
    except Exception as e:
        logger.error(f"load_scoring_context failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    ),
                }
            ],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="score_leads_batch",
    description="Score a batch of leads using the weighted scoring model",
    input_schema={
        "batch_index": int,
        "batch_size": int,
    },
)
async def score_leads_batch_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Score a batch of leads.

    Uses the pre-loaded scoring context and leads data.
    """
    try:
        # Import here to avoid circular imports
        from src.agents.lead_scoring.schemas import (
            LeadScoreRecord,
            ScoringContext,
        )
        from src.agents.lead_scoring.scoring_model import ScoringModel

        batch_index = args.get("batch_index", 0)
        batch_size = args.get("batch_size", 2000)

        # Get leads for this batch
        start = batch_index * batch_size
        end = start + batch_size
        batch_leads = _leads_data[start:end]

        if not batch_leads:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "batch_index": batch_index,
                                "leads_scored": 0,
                                "scores": [],
                            }
                        ),
                    }
                ],
            }

        # Create scoring model
        context = ScoringContext.from_dict(_scoring_context)
        model = ScoringModel(context)

        # Score leads
        lead_records = [LeadScoreRecord.from_dict(lead) for lead in batch_leads]
        scores = model.score_leads_batch(lead_records)

        # Convert to output format
        score_results = [score.to_dict() for score in scores]

        # Calculate batch stats
        total_score = sum(s["score"] for s in score_results)
        avg_score = total_score / len(score_results) if score_results else 0

        tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for s in score_results:
            tier = s.get("tier", "D")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        logger.info(f"Scored batch {batch_index}: {len(score_results)} leads, avg={avg_score:.1f}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "batch_index": batch_index,
                            "leads_scored": len(score_results),
                            "avg_score": round(avg_score, 2),
                            "tier_counts": tier_counts,
                            "scores": score_results,
                        }
                    ),
                }
            ],
        }
    except Exception as e:
        logger.error(f"score_leads_batch failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    ),
                }
            ],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="aggregate_scoring_results",
    description="Aggregate scoring results and calculate final statistics",
    input_schema={
        "batch_results": list,
    },
)
async def aggregate_scoring_results_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate results from all scoring batches.
    """
    try:
        batch_results = args.get("batch_results", [])

        total_scored = 0
        total_score_sum = 0
        tier_a = 0
        tier_b = 0
        tier_c = 0
        tier_d = 0
        all_scores: list[dict[str, Any]] = []

        for batch in batch_results:
            if isinstance(batch, dict):
                total_scored += batch.get("leads_scored", 0)
                scores = batch.get("scores", [])

                for score in scores:
                    total_score_sum += score.get("score", 0)
                    tier = score.get("tier", "D")
                    if tier == "A":
                        tier_a += 1
                    elif tier == "B":
                        tier_b += 1
                    elif tier == "C":
                        tier_c += 1
                    else:
                        tier_d += 1

                all_scores.extend(scores)

        avg_score = total_score_sum / total_scored if total_scored > 0 else 0

        # Calculate score distribution
        distribution = {}
        for i in range(0, 101, 10):
            bucket = f"{i}-{i + 9}"
            distribution[bucket] = len([s for s in all_scores if i <= s.get("score", 0) < i + 10])

        result = {
            "success": True,
            "total_scored": total_scored,
            "avg_score": round(avg_score, 2),
            "tier_a_count": tier_a,
            "tier_b_count": tier_b,
            "tier_c_count": tier_c,
            "tier_d_count": tier_d,
            "score_distribution": distribution,
            "all_scores": all_scores,
        }

        logger.info(
            f"Aggregated results: {total_scored} leads, avg={avg_score:.1f}, "
            f"A={tier_a}, B={tier_b}, C={tier_c}, D={tier_d}"
        )

        return {
            "content": [{"type": "text", "text": json.dumps(result)}],
        }
    except Exception as e:
        logger.error(f"aggregate_scoring_results failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    ),
                }
            ],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="get_scoring_summary",
    description="Generate a human-readable scoring summary report",
    input_schema={
        "total_scored": int,
        "avg_score": float,
        "tier_a_count": int,
        "tier_b_count": int,
        "tier_c_count": int,
        "tier_d_count": int,
    },
)
async def get_scoring_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Generate scoring summary report."""
    try:
        total = args.get("total_scored", 0)
        avg = args.get("avg_score", 0)
        tier_a = args.get("tier_a_count", 0)
        tier_b = args.get("tier_b_count", 0)
        tier_c = args.get("tier_c_count", 0)
        tier_d = args.get("tier_d_count", 0)

        tier_ab_pct = ((tier_a + tier_b) / total * 100) if total > 0 else 0

        summary = f"""
## Lead Scoring Summary

### Overview
- **Total Leads Scored:** {total:,}
- **Average Score:** {avg:.1f}/100
- **Tier A+B Rate:** {tier_ab_pct:.1f}%

### Tier Distribution
| Tier | Count | Percentage | Description |
|------|-------|------------|-------------|
| A (80+) | {tier_a:,} | {tier_a / total * 100 if total else 0:.1f}% | High priority |
| B (60-79) | {tier_b:,} | {tier_b / total * 100 if total else 0:.1f}% | Good leads |
| C (40-59) | {tier_c:,} | {tier_c / total * 100 if total else 0:.1f}% | Moderate |
| D (<40) | {tier_d:,} | {tier_d / total * 100 if total else 0:.1f}% | Low priority |

### Quality Assessment
- **High Quality (A+B):** {tier_a + tier_b:,} leads
- **Standard Quality (C):** {tier_c:,} leads
- **Low Quality (D):** {tier_d:,} leads
"""

        return {
            "content": [{"type": "text", "text": summary.strip()}],
        }
    except Exception as e:
        logger.error(f"get_scoring_summary failed: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    ),
                }
            ],
            "is_error": True,
        }
