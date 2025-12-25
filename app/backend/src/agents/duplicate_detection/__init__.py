"""
Duplicate Detection Agent - Phase 2, Agent 2.3.

Identifies and merges duplicate leads within a campaign using exact matching
(LinkedIn URL, email) and fuzzy matching (name + company with Jaro-Winkler).

This agent is pure (no side effects). The orchestrator handles all database
persistence per LEARN-007.
"""

from src.agents.duplicate_detection.agent import (
    DuplicateDetectionAgent,
    DuplicateDetectionAgentError,
    DuplicateDetectionResult,
    detect_duplicates,
)
from src.agents.duplicate_detection.matching import (
    DuplicateGroup,
    MatchResult,
    calculate_composite_score,
    find_email_duplicates,
    find_fuzzy_duplicates,
    find_linkedin_duplicates,
    jaro_winkler_similarity,
)
from src.agents.duplicate_detection.merge import (
    MergeResult,
    merge_duplicate_group,
    select_primary_record,
)
from src.agents.duplicate_detection.schemas import (
    DedupInput,
    DedupOutput,
    LeadRecord,
)

__all__ = [
    # Agent
    "DuplicateDetectionAgent",
    "DuplicateDetectionAgentError",
    "DuplicateDetectionResult",
    "detect_duplicates",
    # Matching
    "DuplicateGroup",
    "MatchResult",
    "calculate_composite_score",
    "find_email_duplicates",
    "find_fuzzy_duplicates",
    "find_linkedin_duplicates",
    "jaro_winkler_similarity",
    # Merge
    "MergeResult",
    "merge_duplicate_group",
    "select_primary_record",
    # Schemas
    "DedupInput",
    "DedupOutput",
    "LeadRecord",
]
