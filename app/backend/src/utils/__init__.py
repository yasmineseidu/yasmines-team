"""
Utility modules for the backend application.
"""

from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter
from src.utils.search_waterfall import SearchResult, SearchTier, SearchWaterfall, WaterfallResult
from src.utils.string_similarity import (
    calculate_name_company_score,
    is_fuzzy_match,
    jaro_winkler_similarity,
    normalize_email,
    normalize_linkedin_url,
)

__all__ = [
    # Rate limiting
    "TokenBucketRateLimiter",
    "CircuitBreaker",
    # Search waterfall
    "SearchWaterfall",
    "SearchTier",
    "SearchResult",
    "WaterfallResult",
    # String similarity
    "jaro_winkler_similarity",
    "calculate_name_company_score",
    "is_fuzzy_match",
    "normalize_email",
    "normalize_linkedin_url",
]
