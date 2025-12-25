"""
SDK MCP Tools for Duplicate Detection Agent.

Implements @tool decorated functions for duplicate detection operations.
Tools are self-contained per LEARN-003.
"""

import logging
from typing import Any

from claude_agent_sdk import tool

from src.agents.duplicate_detection.matching import (
    calculate_composite_score,
    find_email_duplicates,
    find_fuzzy_duplicates,
    find_linkedin_duplicates,
    jaro_winkler_similarity,
    merge_duplicate_groups,
)
from src.agents.duplicate_detection.merge import (
    merge_duplicate_group,
    prepare_database_updates,
)
from src.agents.duplicate_detection.schemas import LeadRecord

logger = logging.getLogger(__name__)


@tool(  # type: ignore[misc]
    name="analyze_leads_for_duplicates",
    description=(
        "Analyze a batch of leads to detect duplicates using exact matching "
        "(LinkedIn URL, email) and fuzzy matching (name + company). "
        "Returns duplicate groups with confidence scores."
    ),
    input_schema={
        "leads": list,
        "fuzzy_threshold": float,
    },
)
async def analyze_leads_for_duplicates_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for analyzing leads and detecting duplicates.

    This tool runs all three matching algorithms and returns detected groups.

    Args:
        args: Tool arguments with leads data and optional threshold.

    Returns:
        Tool result with duplicate groups.
    """
    leads_data = args.get("leads", [])
    fuzzy_threshold = args.get("fuzzy_threshold", 0.85)

    if not leads_data:
        return {
            "content": [{"type": "text", "text": "No leads provided for analysis"}],
            "is_error": True,
        }

    try:
        # Convert to LeadRecord objects
        leads = [LeadRecord.from_dict(lead) for lead in leads_data]
        logger.info(f"Analyzing {len(leads)} leads for duplicates")

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
            threshold=fuzzy_threshold,
        )

        # Merge overlapping groups
        all_groups = merge_duplicate_groups(linkedin_groups, email_groups, fuzzy_groups)

        # Count duplicates
        exact_count = sum(len(g.lead_ids) - 1 for g in linkedin_groups + email_groups)
        fuzzy_count = sum(len(g.lead_ids) - 1 for g in fuzzy_groups)
        total_duplicates = sum(len(g.lead_ids) - 1 for g in all_groups)
        unique_count = len(leads) - total_duplicates

        # Convert groups to serializable format
        groups_data = [
            {
                "lead_ids": g.lead_ids,
                "match_type": g.match_type,
                "confidence": g.confidence,
                "match_details": g.match_details,
            }
            for g in all_groups
        ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Analyzed {len(leads)} leads. "
                        f"Found {len(all_groups)} duplicate groups "
                        f"({exact_count} exact, {fuzzy_count} fuzzy). "
                        f"{unique_count} unique leads remain."
                    ),
                }
            ],
            "data": {
                "total_checked": len(leads),
                "exact_duplicates": exact_count,
                "fuzzy_duplicates": fuzzy_count,
                "total_duplicates": total_duplicates,
                "unique_leads": unique_count,
                "duplicate_groups": groups_data,
                "duplicate_rate": total_duplicates / len(leads) if leads else 0,
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing leads for duplicates: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="merge_duplicate_groups",
    description=(
        "Merge groups of duplicate leads. Selects primary record (most complete) "
        "and prepares merge operations. Returns updates needed for database."
    ),
    input_schema={
        "leads": list,
        "duplicate_groups": list,
    },
)
async def merge_duplicate_groups_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for merging duplicate lead groups.

    Args:
        args: Tool arguments with leads and duplicate groups.

    Returns:
        Tool result with merge operations.
    """
    leads_data = args.get("leads", [])
    groups_data = args.get("duplicate_groups", [])

    if not leads_data or not groups_data:
        return {
            "content": [{"type": "text", "text": "No leads or groups provided"}],
            "is_error": True,
        }

    try:
        # Convert to LeadRecord objects and create lookup
        leads_by_id: dict[str, LeadRecord] = {}
        for lead_data in leads_data:
            lead = LeadRecord.from_dict(lead_data)
            leads_by_id[lead.id] = lead

        # Process each group
        merge_results = []
        for group in groups_data:
            lead_ids = group.get("lead_ids", [])
            if len(lead_ids) < 2:
                continue

            result = merge_duplicate_group(leads_by_id, lead_ids)
            if result.duplicate_ids:
                merge_results.append(result)

        # Prepare database updates
        primary_updates, duplicate_updates = prepare_database_updates(merge_results)

        total_merged = sum(len(r.duplicate_ids) for r in merge_results)

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Processed {len(groups_data)} groups. "
                        f"Merged {total_merged} duplicates into "
                        f"{len(merge_results)} primary records."
                    ),
                }
            ],
            "data": {
                "groups_processed": len(groups_data),
                "merges_performed": len(merge_results),
                "total_merged": total_merged,
                "primary_updates": primary_updates,
                "duplicate_updates": duplicate_updates,
                "merge_results": [
                    {
                        "primary_id": r.primary_id,
                        "duplicate_ids": r.duplicate_ids,
                        "merged_fields": r.merged_fields,
                        "details": r.merge_details,
                    }
                    for r in merge_results
                ],
            },
        }

    except Exception as e:
        logger.error(f"Error merging duplicate groups: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="calculate_similarity",
    description=(
        "Calculate Jaro-Winkler similarity between two leads. "
        "Returns composite score and breakdown by field."
    ),
    input_schema={
        "lead1": dict,
        "lead2": dict,
    },
)
async def calculate_similarity_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for calculating similarity between two leads.

    Useful for testing and debugging matching logic.

    Args:
        args: Tool arguments with two lead dictionaries.

    Returns:
        Tool result with similarity scores.
    """
    lead1_data = args.get("lead1", {})
    lead2_data = args.get("lead2", {})

    if not lead1_data or not lead2_data:
        return {
            "content": [{"type": "text", "text": "Two leads required"}],
            "is_error": True,
        }

    try:
        lead1 = LeadRecord.from_dict(lead1_data)
        lead2 = LeadRecord.from_dict(lead2_data)

        composite, breakdown = calculate_composite_score(lead1, lead2)

        # Also calculate individual field similarities
        name_sim = jaro_winkler_similarity(
            f"{lead1.first_name} {lead1.last_name}",
            f"{lead2.first_name} {lead2.last_name}",
        )

        is_match = composite >= 0.85

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Similarity: {composite:.2%} "
                        f"({'MATCH' if is_match else 'NO MATCH'}). "
                        f"First name: {breakdown['first_name_similarity']:.2%}, "
                        f"Last name: {breakdown['last_name_similarity']:.2%}, "
                        f"Company: {breakdown['company_similarity']:.2%}"
                    ),
                }
            ],
            "data": {
                "composite_score": composite,
                "is_match": is_match,
                "breakdown": breakdown,
                "full_name_similarity": name_sim,
            },
        }

    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


@tool(  # type: ignore[misc]
    name="get_dedup_summary",
    description=(
        "Generate a summary report of deduplication results. "
        "Includes counts, rates, and detailed breakdown."
    ),
    input_schema={
        "total_checked": int,
        "exact_duplicates": int,
        "fuzzy_duplicates": int,
        "total_merged": int,
        "unique_leads": int,
    },
)
async def get_dedup_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for generating deduplication summary.

    Args:
        args: Tool arguments with dedup counts.

    Returns:
        Tool result with formatted summary.
    """
    total_checked = args.get("total_checked", 0)
    exact_duplicates = args.get("exact_duplicates", 0)
    fuzzy_duplicates = args.get("fuzzy_duplicates", 0)
    total_merged = args.get("total_merged", 0)
    unique_leads = args.get("unique_leads", 0)

    total_duplicates = exact_duplicates + fuzzy_duplicates
    duplicate_rate = total_duplicates / total_checked if total_checked else 0

    # Generate quality assessment
    if duplicate_rate < 0.05:
        quality = "excellent"
        assessment = "Very low duplicate rate - data quality is high"
    elif duplicate_rate < 0.15:
        quality = "good"
        assessment = "Acceptable duplicate rate within normal range"
    elif duplicate_rate < 0.30:
        quality = "fair"
        assessment = "High duplicate rate - consider reviewing data sources"
    else:
        quality = "poor"
        assessment = "Very high duplicate rate - data quality concerns"

    summary = (
        f"Deduplication Summary:\n"
        f"- Total leads checked: {total_checked:,}\n"
        f"- Exact duplicates: {exact_duplicates:,} (LinkedIn/email matches)\n"
        f"- Fuzzy duplicates: {fuzzy_duplicates:,} (name+company matches)\n"
        f"- Total merged: {total_merged:,}\n"
        f"- Unique leads: {unique_leads:,}\n"
        f"- Duplicate rate: {duplicate_rate:.1%}\n"
        f"- Quality: {quality.upper()}\n"
        f"- Assessment: {assessment}"
    )

    return {
        "content": [{"type": "text", "text": summary}],
        "data": {
            "total_checked": total_checked,
            "exact_duplicates": exact_duplicates,
            "fuzzy_duplicates": fuzzy_duplicates,
            "total_merged": total_merged,
            "unique_leads": unique_leads,
            "duplicate_rate": duplicate_rate,
            "quality": quality,
            "assessment": assessment,
        },
    }
