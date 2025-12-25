"""
Cross-Campaign Deduplication Agent - Phase 2, Agent 2.4.

Identifies and excludes leads that exist across campaigns based on:
- Historical matching (LinkedIn URL, email, name+company fuzzy)
- Exclusion rules (recently contacted, bounced, unsubscribed, suppression list)
"""

from src.agents.cross_campaign_dedup.agent import (
    CrossCampaignDedupAgent,
    CrossCampaignDedupError,
    CrossCampaignDedupResult,
    ExclusionResult,
    HistoricalDataLoadError,
    NoLeadsToProcessError,
    cross_campaign_dedup,
    fuzzy_match_score,
    name_company_match,
    normalize_string,
)

__all__ = [
    # Agent
    "CrossCampaignDedupAgent",
    "cross_campaign_dedup",
    # Results
    "CrossCampaignDedupResult",
    "ExclusionResult",
    # Exceptions
    "CrossCampaignDedupError",
    "NoLeadsToProcessError",
    "HistoricalDataLoadError",
    # Utilities
    "normalize_string",
    "fuzzy_match_score",
    "name_company_match",
]
