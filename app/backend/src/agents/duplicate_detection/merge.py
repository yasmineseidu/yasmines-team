"""
Merge strategies for duplicate leads.

Implements strategies for selecting primary records and merging
fields from duplicate leads.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.agents.duplicate_detection.schemas import LeadRecord

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of merging duplicate leads."""

    primary_id: str
    duplicate_ids: list[str]
    merged_fields: dict[str, Any]
    merge_details: dict[str, Any] = field(default_factory=dict)


def select_primary_record(leads: list[LeadRecord]) -> LeadRecord:
    """
    Select the primary record from a group of duplicates.

    Priority:
    1. Has email address
    2. More fields populated
    3. Created first (oldest)

    Args:
        leads: List of duplicate leads.

    Returns:
        The selected primary lead.
    """
    if len(leads) == 1:
        return leads[0]

    def score_lead(lead: LeadRecord) -> tuple[int, int, float]:
        """
        Score a lead for primary selection.

        Returns tuple for sorting (higher is better):
        - has_email: 1 if has email, 0 otherwise
        - field_count: number of populated fields
        - created_order: negative timestamp (oldest first)
        """
        has_email = 1 if lead.email else 0
        field_count = lead.count_populated_fields()

        # For created_at, we want oldest first, so we use a timestamp
        # If no created_at, use 0 (which will be considered oldest)
        if lead.created_at:
            # Convert to timestamp, negate so older = higher score
            try:
                ts = lead.created_at.timestamp()
            except Exception:
                ts = 0
        else:
            ts = 0

        return (has_email, field_count, -ts)

    # Sort by score, highest first
    sorted_leads = sorted(leads, key=score_lead, reverse=True)
    primary = sorted_leads[0]

    logger.debug(
        f"Selected primary {primary.id} from {len(leads)} duplicates "
        f"(email={bool(primary.email)}, fields={primary.count_populated_fields()})"
    )

    return primary


def _first_non_null(*values: Any) -> Any:
    """Return the first non-null value."""
    for v in values:
        if v is not None and v != "":
            return v
    return None


def _longest_value(*values: str | None) -> str | None:
    """Return the longest non-null string."""
    valid_values = [v for v in values if v]
    if not valid_values:
        return None
    return max(valid_values, key=len)


def _most_specific_location(*locations: str | None) -> str | None:
    """
    Return the most specific location string.

    More specific = longer and contains more parts (city, state, country).
    """
    valid_locations = [loc for loc in locations if loc]
    if not valid_locations:
        return None

    def score_location(loc: str) -> tuple[int, int]:
        """Score location by parts and length."""
        parts = len([p for p in loc.split(",") if p.strip()])
        return (parts, len(loc))

    return max(valid_locations, key=score_location)


def merge_fields(
    primary: LeadRecord,
    duplicates: list[LeadRecord],
) -> dict[str, Any]:
    """
    Merge fields from duplicates into the primary record.

    Strategies:
    - email, phone: first non-null wins
    - title: longest value
    - location: most specific

    Args:
        primary: Primary lead record.
        duplicates: List of duplicate leads.

    Returns:
        Dictionary of merged field values.
    """
    all_leads = [primary] + duplicates

    merged: dict[str, Any] = {}

    # Email - first non-null
    emails = [lead.email for lead in all_leads]
    merged_email = _first_non_null(*emails)
    if merged_email and merged_email != primary.email:
        merged["email"] = merged_email

    # Phone - first non-null
    phones = [lead.phone for lead in all_leads]
    merged_phone = _first_non_null(*phones)
    if merged_phone and merged_phone != primary.phone:
        merged["phone"] = merged_phone

    # Title - longest value
    titles = [lead.title for lead in all_leads]
    merged_title = _longest_value(*titles)
    if merged_title and merged_title != primary.title:
        merged["title"] = merged_title

    # Company name - longest value
    company_names = [lead.company_name for lead in all_leads]
    merged_company = _longest_value(*company_names)
    if merged_company and merged_company != primary.company_name:
        merged["company_name"] = merged_company

    # Company domain - first non-null
    domains = [lead.company_domain for lead in all_leads]
    merged_domain = _first_non_null(*domains)
    if merged_domain and merged_domain != primary.company_domain:
        merged["company_domain"] = merged_domain

    # Location - most specific
    locations = [lead.location for lead in all_leads]
    merged_location = _most_specific_location(*locations)
    if merged_location and merged_location != primary.location:
        merged["location"] = merged_location

    # LinkedIn URL - first non-null
    linkedin_urls = [lead.linkedin_url for lead in all_leads]
    merged_linkedin = _first_non_null(*linkedin_urls)
    if merged_linkedin and merged_linkedin != primary.linkedin_url:
        merged["linkedin_url"] = merged_linkedin

    return merged


def merge_duplicate_group(
    leads_by_id: dict[str, LeadRecord],
    duplicate_ids: list[str],
) -> MergeResult:
    """
    Merge a group of duplicate leads.

    Args:
        leads_by_id: Dictionary mapping lead ID to LeadRecord.
        duplicate_ids: List of duplicate lead IDs.

    Returns:
        MergeResult with primary, duplicates, and merged fields.
    """
    # Get leads
    leads = [leads_by_id[lid] for lid in duplicate_ids if lid in leads_by_id]

    if len(leads) < 2:
        # Not enough leads to merge
        return MergeResult(
            primary_id=leads[0].id if leads else "",
            duplicate_ids=[],
            merged_fields={},
            merge_details={"skipped": "not_enough_leads"},
        )

    # Select primary
    primary = select_primary_record(leads)
    duplicates = [lead for lead in leads if lead.id != primary.id]
    duplicate_id_list = [lead.id for lead in duplicates]

    # Merge fields
    merged_fields = merge_fields(primary, duplicates)

    result = MergeResult(
        primary_id=primary.id,
        duplicate_ids=duplicate_id_list,
        merged_fields=merged_fields,
        merge_details={
            "primary_email": primary.email,
            "primary_field_count": primary.count_populated_fields(),
            "duplicates_merged": len(duplicate_id_list),
            "fields_updated": list(merged_fields.keys()),
        },
    )

    logger.info(
        f"Merged {len(duplicate_id_list)} duplicates into {primary.id}, "
        f"updated fields: {list(merged_fields.keys())}"
    )

    return result


def prepare_database_updates(
    merge_results: list[MergeResult],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Prepare database update operations from merge results.

    Returns:
        Tuple of (primary_updates, duplicate_updates) for database operations.
    """
    primary_updates: list[dict[str, Any]] = []
    duplicate_updates: list[dict[str, Any]] = []

    for result in merge_results:
        if not result.duplicate_ids:
            continue

        # Update for primary record
        primary_update: dict[str, Any] = {
            "id": result.primary_id,
            "merged_from": result.duplicate_ids,
        }
        # Add merged field values
        primary_update.update(result.merged_fields)
        primary_updates.append(primary_update)

        # Updates for duplicate records
        for dup_id in result.duplicate_ids:
            duplicate_updates.append(
                {
                    "id": dup_id,
                    "status": "duplicate",
                    "duplicate_of": result.primary_id,
                }
            )

    return primary_updates, duplicate_updates
