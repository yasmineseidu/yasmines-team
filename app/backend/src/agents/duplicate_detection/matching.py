"""
Matching algorithms for duplicate detection.

Implements exact matching (LinkedIn URL, email) and fuzzy matching
(Jaro-Winkler similarity on name + company).
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import jellyfish

from src.agents.duplicate_detection.schemas import LeadRecord
from src.utils.string_similarity import (
    DEFAULT_COMPANY_WEIGHT,
    DEFAULT_FIRST_NAME_WEIGHT,
    DEFAULT_FUZZY_THRESHOLD,
    DEFAULT_LAST_NAME_WEIGHT,
)
from src.utils.string_similarity import (
    jaro_winkler_similarity as _jaro_winkler_similarity,
)
from src.utils.string_similarity import (
    normalize_email as _normalize_email,
)
from src.utils.string_similarity import (
    normalize_linkedin_url as _normalize_linkedin_url,
)

logger = logging.getLogger(__name__)

# Re-export thresholds from shared utils for backward compatibility
FUZZY_THRESHOLD = DEFAULT_FUZZY_THRESHOLD
NAME_THRESHOLD = 0.9  # Threshold for name matching (agent-specific)
COMPANY_THRESHOLD = 0.85  # Threshold for company matching (agent-specific)

# Re-export weights from shared utils for backward compatibility
FIRST_NAME_WEIGHT = DEFAULT_FIRST_NAME_WEIGHT
LAST_NAME_WEIGHT = DEFAULT_LAST_NAME_WEIGHT
COMPANY_WEIGHT = DEFAULT_COMPANY_WEIGHT


@dataclass
class MatchResult:
    """Result of a duplicate match."""

    lead1_id: str
    lead2_id: str
    match_type: str  # 'linkedin', 'email', 'fuzzy'
    confidence: float
    match_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicateGroup:
    """Group of duplicate leads."""

    lead_ids: list[str]
    match_type: str
    confidence: float
    match_details: dict[str, Any] = field(default_factory=dict)


def jaro_winkler_similarity(s1: str | None, s2: str | None) -> float:
    """
    Calculate Jaro-Winkler similarity between two strings.

    Delegates to shared utility in src.utils.string_similarity.

    Args:
        s1: First string (can be None).
        s2: Second string (can be None).

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    return _jaro_winkler_similarity(s1, s2)


def calculate_composite_score(
    lead1: LeadRecord,
    lead2: LeadRecord,
) -> tuple[float, dict[str, float]]:
    """
    Calculate composite similarity score for two leads.

    Uses weighted combination of first name, last name, and company name.

    Args:
        lead1: First lead record.
        lead2: Second lead record.

    Returns:
        Tuple of (composite_score, score_breakdown).
    """
    # Calculate individual similarities
    fn_sim = jaro_winkler_similarity(lead1.first_name, lead2.first_name)
    ln_sim = jaro_winkler_similarity(lead1.last_name, lead2.last_name)
    co_sim = jaro_winkler_similarity(lead1.company_name, lead2.company_name)

    # Calculate weighted composite
    composite = (
        (fn_sim * FIRST_NAME_WEIGHT) + (ln_sim * LAST_NAME_WEIGHT) + (co_sim * COMPANY_WEIGHT)
    )

    breakdown = {
        "first_name_similarity": fn_sim,
        "last_name_similarity": ln_sim,
        "company_similarity": co_sim,
        "composite_score": composite,
    }

    return composite, breakdown


def find_linkedin_duplicates(leads: list[LeadRecord]) -> list[DuplicateGroup]:
    """
    Find duplicates by exact LinkedIn URL match.

    Args:
        leads: List of lead records.

    Returns:
        List of duplicate groups.
    """
    # Group by normalized LinkedIn URL
    url_to_leads: dict[str, list[str]] = defaultdict(list)

    for lead in leads:
        normalized = _normalize_linkedin_url(lead.linkedin_url)
        if normalized:
            url_to_leads[normalized].append(lead.id)

    # Find groups with more than one lead
    groups: list[DuplicateGroup] = []
    for url, lead_ids in url_to_leads.items():
        if len(lead_ids) > 1:
            groups.append(
                DuplicateGroup(
                    lead_ids=lead_ids,
                    match_type="linkedin",
                    confidence=1.0,
                    match_details={"linkedin_url": url},
                )
            )

    logger.info(f"Found {len(groups)} LinkedIn URL duplicate groups")
    return groups


def find_email_duplicates(leads: list[LeadRecord]) -> list[DuplicateGroup]:
    """
    Find duplicates by exact email match.

    Args:
        leads: List of lead records.

    Returns:
        List of duplicate groups.
    """
    # Group by normalized email
    email_to_leads: dict[str, list[str]] = defaultdict(list)

    for lead in leads:
        normalized = _normalize_email(lead.email)
        if normalized:
            email_to_leads[normalized].append(lead.id)

    # Find groups with more than one lead
    groups: list[DuplicateGroup] = []
    for email, lead_ids in email_to_leads.items():
        if len(lead_ids) > 1:
            groups.append(
                DuplicateGroup(
                    lead_ids=lead_ids,
                    match_type="email",
                    confidence=1.0,
                    match_details={"email": email},
                )
            )

    logger.info(f"Found {len(groups)} email duplicate groups")
    return groups


def _create_blocking_key(lead: LeadRecord) -> str | None:
    """
    Create blocking key for fuzzy matching.

    Uses first_name soundex + first 3 chars of company name.
    This reduces comparison space for fuzzy matching.
    """
    if not lead.first_name:
        return None

    # Get soundex of first name
    try:
        fn_soundex = jellyfish.soundex(lead.first_name)
    except Exception:
        fn_soundex = lead.first_name[:4].upper() if lead.first_name else ""

    # Get first 3 chars of company name
    co_prefix = (lead.company_name or "")[:3].lower()

    if not fn_soundex or not co_prefix:
        return None

    return f"{fn_soundex}:{co_prefix}"


def find_fuzzy_duplicates(
    leads: list[LeadRecord],
    already_matched_ids: set[str] | None = None,
    threshold: float = FUZZY_THRESHOLD,
) -> list[DuplicateGroup]:
    """
    Find duplicates by fuzzy matching on name + company.

    Uses blocking keys to reduce comparison space, then applies
    Jaro-Winkler similarity with composite scoring.

    Args:
        leads: List of lead records.
        already_matched_ids: Set of lead IDs already matched (from exact matching).
        threshold: Minimum composite score for match.

    Returns:
        List of duplicate groups.
    """
    if already_matched_ids is None:
        already_matched_ids = set()

    # Filter out already matched leads
    eligible_leads = [lead for lead in leads if lead.id not in already_matched_ids]

    # Create blocking key index
    blocking_index: dict[str, list[LeadRecord]] = defaultdict(list)
    for lead in eligible_leads:
        key = _create_blocking_key(lead)
        if key:
            blocking_index[key].append(lead)

    # Find matches within each blocking group
    matched_pairs: list[MatchResult] = []
    processed: set[tuple[str, str]] = set()

    for _key, block_leads in blocking_index.items():
        if len(block_leads) < 2:
            continue

        # Compare all pairs within the block
        for i, lead1 in enumerate(block_leads):
            for lead2 in block_leads[i + 1 :]:
                # Create ordered pair key for deduplication
                if lead1.id < lead2.id:
                    pair_key: tuple[str, str] = (lead1.id, lead2.id)
                else:
                    pair_key = (lead2.id, lead1.id)
                if pair_key in processed:
                    continue
                processed.add(pair_key)

                score, breakdown = calculate_composite_score(lead1, lead2)

                if score >= threshold:
                    matched_pairs.append(
                        MatchResult(
                            lead1_id=lead1.id,
                            lead2_id=lead2.id,
                            match_type="fuzzy",
                            confidence=score,
                            match_details=breakdown,
                        )
                    )

    # Convert pairs to groups using union-find
    groups = _pairs_to_groups(matched_pairs)

    logger.info(f"Found {len(groups)} fuzzy duplicate groups")
    return groups


def _pairs_to_groups(pairs: list[MatchResult]) -> list[DuplicateGroup]:
    """
    Convert matched pairs to groups using union-find algorithm.

    Args:
        pairs: List of match results.

    Returns:
        List of duplicate groups.
    """
    if not pairs:
        return []

    # Union-find parent mapping
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Union all matched pairs
    for pair in pairs:
        union(pair.lead1_id, pair.lead2_id)

    # Group by root
    groups_dict: dict[str, list[str]] = defaultdict(list)
    all_ids = {p.lead1_id for p in pairs} | {p.lead2_id for p in pairs}
    for lead_id in all_ids:
        root = find(lead_id)
        groups_dict[root].append(lead_id)

    # Build group objects with confidence scores
    groups: list[DuplicateGroup] = []
    for lead_ids in groups_dict.values():
        if len(lead_ids) > 1:
            # Calculate average confidence for the group
            relevant_pairs = [p for p in pairs if p.lead1_id in lead_ids or p.lead2_id in lead_ids]
            avg_confidence = (
                sum(p.confidence for p in relevant_pairs) / len(relevant_pairs)
                if relevant_pairs
                else FUZZY_THRESHOLD
            )

            groups.append(
                DuplicateGroup(
                    lead_ids=lead_ids,
                    match_type="fuzzy",
                    confidence=avg_confidence,
                    match_details={
                        "pair_count": len(relevant_pairs),
                        "avg_score": avg_confidence,
                    },
                )
            )

    return groups


def merge_duplicate_groups(
    linkedin_groups: list[DuplicateGroup],
    email_groups: list[DuplicateGroup],
    fuzzy_groups: list[DuplicateGroup],
) -> list[DuplicateGroup]:
    """
    Merge overlapping duplicate groups from different detection methods.

    Args:
        linkedin_groups: Groups from LinkedIn URL matching.
        email_groups: Groups from email matching.
        fuzzy_groups: Groups from fuzzy matching.

    Returns:
        Combined list of non-overlapping duplicate groups.
    """
    # Combine all groups
    all_groups = linkedin_groups + email_groups + fuzzy_groups

    if not all_groups:
        return []

    # Use union-find to merge overlapping groups
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Track best match type and confidence for each lead
    lead_info: dict[str, tuple[str, float]] = {}

    for group in all_groups:
        # Union all leads in this group
        first_id = group.lead_ids[0]
        for lead_id in group.lead_ids[1:]:
            union(first_id, lead_id)

        # Track best match info
        for lead_id in group.lead_ids:
            current = lead_info.get(lead_id, ("", 0.0))
            if group.confidence > current[1]:
                lead_info[lead_id] = (group.match_type, group.confidence)

    # Build merged groups
    groups_dict: dict[str, list[str]] = defaultdict(list)
    for lead_id in parent:
        root = find(lead_id)
        groups_dict[root].append(lead_id)

    merged_groups: list[DuplicateGroup] = []
    for lead_ids in groups_dict.values():
        if len(lead_ids) > 1:
            # Determine best match type for the group
            match_types = [lead_info.get(lid, ("", 0.0))[0] for lid in lead_ids]
            confidences = [lead_info.get(lid, ("", 0.0))[1] for lid in lead_ids]

            # Prefer exact matches over fuzzy
            if "linkedin" in match_types:
                match_type = "linkedin"
            elif "email" in match_types:
                match_type = "email"
            else:
                match_type = "fuzzy"

            merged_groups.append(
                DuplicateGroup(
                    lead_ids=lead_ids,
                    match_type=match_type,
                    confidence=max(confidences) if confidences else 1.0,
                    match_details={"merged_from": list(set(match_types))},
                )
            )

    return merged_groups
