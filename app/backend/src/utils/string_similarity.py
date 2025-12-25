"""
String similarity utilities for lead matching and deduplication.

Provides shared similarity functions used by multiple agents including
Duplicate Detection Agent and Cross-Campaign Dedup Agent.
"""

import jellyfish

# Default weights for composite scoring
DEFAULT_FIRST_NAME_WEIGHT: float = 0.3
DEFAULT_LAST_NAME_WEIGHT: float = 0.3
DEFAULT_COMPANY_WEIGHT: float = 0.4
DEFAULT_FUZZY_THRESHOLD: float = 0.85


def jaro_winkler_similarity(s1: str | None, s2: str | None) -> float:
    """
    Calculate Jaro-Winkler similarity between two strings.

    The Jaro-Winkler similarity is a string metric for measuring the edit
    distance between two sequences. It is a variant of the Jaro distance
    metric, which gives more favorable ratings to strings that match from
    the beginning for a set prefix length.

    Args:
        s1: First string (can be None).
        s2: Second string (can be None).

    Returns:
        Similarity score between 0.0 and 1.0, where:
        - 1.0 means identical strings
        - 0.0 means completely different strings

    Examples:
        >>> jaro_winkler_similarity("John", "John")
        1.0
        >>> jaro_winkler_similarity("John", "Jon")
        0.9333...
        >>> jaro_winkler_similarity(None, "John")
        0.0
    """
    if not s1 or not s2:
        return 0.0

    # Normalize strings
    s1_normalized = s1.lower().strip()
    s2_normalized = s2.lower().strip()

    if not s1_normalized or not s2_normalized:
        return 0.0

    return float(jellyfish.jaro_winkler_similarity(s1_normalized, s2_normalized))


def calculate_name_company_score(
    first_name1: str | None,
    last_name1: str | None,
    company1: str | None,
    first_name2: str | None,
    last_name2: str | None,
    company2: str | None,
    first_name_weight: float = DEFAULT_FIRST_NAME_WEIGHT,
    last_name_weight: float = DEFAULT_LAST_NAME_WEIGHT,
    company_weight: float = DEFAULT_COMPANY_WEIGHT,
) -> tuple[float, dict[str, float]]:
    """
    Calculate composite similarity score for name and company fields.

    Uses weighted combination of Jaro-Winkler similarity scores for:
    - First name (default 30% weight)
    - Last name (default 30% weight)
    - Company name (default 40% weight)

    Args:
        first_name1: First person's first name.
        last_name1: First person's last name.
        company1: First person's company name.
        first_name2: Second person's first name.
        last_name2: Second person's last name.
        company2: Second person's company name.
        first_name_weight: Weight for first name similarity (default 0.3).
        last_name_weight: Weight for last name similarity (default 0.3).
        company_weight: Weight for company similarity (default 0.4).

    Returns:
        Tuple of (composite_score, score_breakdown) where:
        - composite_score: Weighted average similarity (0.0 to 1.0)
        - score_breakdown: Dict with individual similarity scores

    Examples:
        >>> score, breakdown = calculate_name_company_score(
        ...     "John", "Smith", "Acme Corp",
        ...     "Jon", "Smith", "Acme Corporation"
        ... )
        >>> score > 0.85
        True
    """
    # Calculate individual similarities
    fn_sim = jaro_winkler_similarity(first_name1, first_name2)
    ln_sim = jaro_winkler_similarity(last_name1, last_name2)
    co_sim = jaro_winkler_similarity(company1, company2)

    # Calculate weighted composite
    composite = (
        (fn_sim * first_name_weight) + (ln_sim * last_name_weight) + (co_sim * company_weight)
    )

    breakdown = {
        "first_name_similarity": fn_sim,
        "last_name_similarity": ln_sim,
        "company_similarity": co_sim,
        "composite_score": composite,
    }

    return composite, breakdown


def is_fuzzy_match(
    first_name1: str | None,
    last_name1: str | None,
    company1: str | None,
    first_name2: str | None,
    last_name2: str | None,
    company2: str | None,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> tuple[bool, float]:
    """
    Check if two people are a fuzzy match based on name and company.

    Convenience function that wraps calculate_name_company_score and
    compares against a threshold.

    Args:
        first_name1: First person's first name.
        last_name1: First person's last name.
        company1: First person's company name.
        first_name2: Second person's first name.
        last_name2: Second person's last name.
        company2: Second person's company name.
        threshold: Minimum composite score for a match (default 0.85).

    Returns:
        Tuple of (is_match, score) where:
        - is_match: True if composite score >= threshold
        - score: The composite similarity score

    Examples:
        >>> is_match, score = is_fuzzy_match(
        ...     "John", "Smith", "Acme",
        ...     "Jon", "Smith", "Acme Corp"
        ... )
        >>> is_match
        True
    """
    score, _ = calculate_name_company_score(
        first_name1,
        last_name1,
        company1,
        first_name2,
        last_name2,
        company2,
    )
    return score >= threshold, score


def normalize_email(email: str | None) -> str | None:
    """
    Normalize email for comparison.

    Converts to lowercase and strips whitespace.

    Args:
        email: Email address to normalize.

    Returns:
        Normalized email or None if input is empty.
    """
    if not email:
        return None
    normalized = email.lower().strip()
    return normalized if normalized else None


def normalize_linkedin_url(url: str | None) -> str | None:
    """
    Normalize LinkedIn URL for comparison.

    Removes protocol, www, trailing slashes, and query parameters.

    Args:
        url: LinkedIn URL to normalize.

    Returns:
        Normalized URL or None if input is empty.

    Examples:
        >>> normalize_linkedin_url("https://www.linkedin.com/in/johnsmith?ref=123")
        'linkedin.com/in/johnsmith'
    """
    if not url:
        return None

    url = url.lower().strip()

    # Remove protocol
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]

    # Remove www
    if url.startswith("www."):
        url = url[4:]

    # Remove query params
    if "?" in url:
        url = url.split("?")[0]

    # Remove trailing slashes
    url = url.rstrip("/")

    return url if url else None
