"""
Job Title Matcher for Lead Scoring Agent.

Provides fuzzy matching with synonyms and seniority extraction.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Final

# =============================================================================
# Constants
# =============================================================================

# Seniority levels with numeric ranking (higher = more senior)
SENIORITY_LEVELS: Final[dict[str, int]] = {
    "c_suite": 6,
    "c-suite": 6,
    "c_level": 6,
    "c-level": 6,
    "chief": 6,
    "ceo": 6,
    "cfo": 6,
    "cmo": 6,
    "cto": 6,
    "coo": 6,
    "cio": 6,
    "cro": 6,
    "vp": 5,
    "vice_president": 5,
    "vice-president": 5,
    "evp": 5,
    "svp": 5,
    "director": 4,
    "head": 4,
    "senior_manager": 3,
    "senior manager": 3,
    "manager": 2,
    "senior": 1,
    "lead": 1,
    "specialist": 0,
    "coordinator": 0,
    "analyst": 0,
    "associate": 0,
    "ic": 0,
}

# Patterns to extract seniority from job titles
SENIORITY_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"\b(chief|ceo|cfo|cmo|cto|coo|cio|cro)\b", "c_suite"),
    (r"\b(c-level|c-suite|c level|c suite)\b", "c_suite"),
    (r"\b(evp|svp)\b", "vp"),
    (r"\b(vp|vice\s*president)\b", "vp"),
    (r"\b(director|head\s+of)\b", "director"),
    (r"\b(senior\s+manager)\b", "senior_manager"),
    (r"\b(manager)\b", "manager"),
    (r"\b(senior|lead)\b", "senior"),
    (r"\b(specialist|coordinator|analyst|associate)\b", "ic"),
]

# Job title synonyms for better matching
TITLE_SYNONYMS: Final[dict[str, list[str]]] = {
    # Marketing titles
    "VP Marketing": [
        "Vice President Marketing",
        "VP of Marketing",
        "Marketing VP",
        "Vice President of Marketing",
    ],
    "Marketing Director": [
        "Director of Marketing",
        "Director, Marketing",
        "Marketing Dir",
        "Head of Marketing",
    ],
    "Head of Marketing": ["Marketing Lead", "Marketing Head", "Chief Marketing Officer"],
    "CMO": ["Chief Marketing Officer", "Head of Marketing"],
    # Sales titles
    "VP Sales": [
        "Vice President Sales",
        "VP of Sales",
        "Sales VP",
        "Vice President of Sales",
    ],
    "Sales Director": [
        "Director of Sales",
        "Director, Sales",
        "Head of Sales",
        "Sales Dir",
    ],
    "Head of Sales": ["Sales Lead", "Sales Head", "Chief Revenue Officer"],
    "CRO": ["Chief Revenue Officer", "Head of Revenue"],
    # Operations titles
    "VP Operations": [
        "Vice President Operations",
        "VP of Operations",
        "Operations VP",
    ],
    "Operations Director": [
        "Director of Operations",
        "Director, Operations",
        "Head of Operations",
    ],
    "COO": ["Chief Operating Officer", "Head of Operations"],
    # Technology titles
    "VP Engineering": [
        "Vice President Engineering",
        "VP of Engineering",
        "Engineering VP",
    ],
    "Engineering Director": [
        "Director of Engineering",
        "Director, Engineering",
        "Head of Engineering",
    ],
    "CTO": ["Chief Technology Officer", "Head of Technology", "VP Technology"],
    # HR titles
    "VP HR": ["Vice President HR", "VP of HR", "HR VP", "VP Human Resources"],
    "HR Director": [
        "Director of HR",
        "Director, HR",
        "Head of HR",
        "Director Human Resources",
    ],
    "CHRO": ["Chief Human Resources Officer", "Head of HR"],
    # Finance titles
    "VP Finance": ["Vice President Finance", "VP of Finance", "Finance VP"],
    "Finance Director": [
        "Director of Finance",
        "Director, Finance",
        "Head of Finance",
    ],
    "CFO": ["Chief Financial Officer", "Head of Finance"],
    # Product titles
    "VP Product": ["Vice President Product", "VP of Product", "Product VP"],
    "Product Director": [
        "Director of Product",
        "Director, Product",
        "Head of Product",
    ],
    "CPO": ["Chief Product Officer", "Head of Product"],
    # Growth titles
    "VP Growth": ["Vice President Growth", "VP of Growth", "Growth VP"],
    "Growth Director": [
        "Director of Growth",
        "Director, Growth",
        "Head of Growth",
    ],
    "CGO": ["Chief Growth Officer", "Head of Growth"],
}


# =============================================================================
# Matcher Classes
# =============================================================================


@dataclass
class MatchResult:
    """Result of a job title match."""

    matched: bool = False
    score: float = 0.0
    matched_title: str | None = None
    matched_persona: str | None = None
    seniority_level: str | None = None


def normalize_title(title: str) -> str:
    """Normalize job title for comparison."""
    if not title:
        return ""

    # Convert to lowercase
    normalized = title.lower()

    # Remove common noise
    noise_patterns = [
        r"\s*-\s*",  # Dashes
        r"\s*,\s*",  # Commas
        r"\s+",  # Multiple spaces
        r"[^\w\s]",  # Special characters
    ]

    for pattern in noise_patterns:
        normalized = re.sub(pattern, " ", normalized)

    return normalized.strip()


def calculate_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two job titles using SequenceMatcher.

    Args:
        title1: First job title
        title2: Second job title

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not title1 or not title2:
        return 0.0

    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    if norm1 == norm2:
        return 1.0

    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_seniority_level(title: str) -> str:
    """
    Extract seniority level from job title.

    Args:
        title: Job title to analyze

    Returns:
        Seniority level string (c_suite, vp, director, etc.)
    """
    if not title:
        return "ic"

    title_lower = title.lower()

    # Check patterns in order of seniority (highest first)
    for pattern, level in SENIORITY_PATTERNS:
        if re.search(pattern, title_lower, re.IGNORECASE):
            return level

    return "ic"  # Default to individual contributor


def get_seniority_rank(level: str) -> int:
    """Get numeric rank for seniority level."""
    return SENIORITY_LEVELS.get(level.lower(), 0)


def expand_with_synonyms(title: str) -> list[str]:
    """Expand title with synonyms."""
    result = [title]

    title_lower = title.lower()
    for canonical, synonyms in TITLE_SYNONYMS.items():
        if title_lower == canonical.lower():
            result.extend(synonyms)
        elif title_lower in [s.lower() for s in synonyms]:
            result.append(canonical)
            result.extend(s for s in synonyms if s.lower() != title_lower)

    return list(set(result))


class JobTitleMatcher:
    """
    Job title matcher with fuzzy matching and synonym support.

    Uses SequenceMatcher for fuzzy matching and a synonym dictionary
    for common variations.
    """

    def __init__(
        self,
        threshold: float = 0.80,
        synonyms: dict[str, list[str]] | None = None,
    ) -> None:
        """
        Initialize matcher.

        Args:
            threshold: Minimum similarity score for a match (0.0-1.0)
            synonyms: Custom synonym dictionary
        """
        self.threshold = threshold
        self.synonyms = synonyms or TITLE_SYNONYMS

    def match(
        self,
        lead_title: str,
        target_titles: list[str],
        personas: list[dict[str, Any]] | None = None,
    ) -> MatchResult:
        """
        Match lead title against target titles.

        Args:
            lead_title: Lead's job title
            target_titles: List of target job titles to match against
            personas: Optional list of persona dictionaries

        Returns:
            MatchResult with match details
        """
        if not lead_title:
            return MatchResult()

        best_score = 0.0
        best_title: str | None = None
        best_persona: str | None = None

        # Expand lead title with synonyms
        lead_variants = expand_with_synonyms(lead_title)

        # Match against target titles
        for target in target_titles:
            target_variants = expand_with_synonyms(target)

            for lead_var in lead_variants:
                for target_var in target_variants:
                    score = calculate_similarity(lead_var, target_var)
                    if score > best_score:
                        best_score = score
                        best_title = target

        # Also check against persona job titles
        # Use >= to prefer persona matches when scores are tied
        if personas:
            for persona in personas:
                persona_titles = persona.get("job_titles", [])
                persona_name = persona.get("name", "Unknown")

                for target in persona_titles:
                    target_variants = expand_with_synonyms(target)

                    for lead_var in lead_variants:
                        for target_var in target_variants:
                            score = calculate_similarity(lead_var, target_var)
                            if score >= best_score:
                                best_score = score
                                best_title = target
                                best_persona = persona_name

        matched = best_score >= self.threshold
        seniority = extract_seniority_level(lead_title)

        return MatchResult(
            matched=matched,
            score=best_score,
            matched_title=best_title if matched else None,
            matched_persona=best_persona if matched else None,
            seniority_level=seniority,
        )

    def match_seniority(
        self,
        lead_seniority: str | None,
        target_seniorities: list[str],
    ) -> tuple[int, str | None]:
        """
        Match seniority level against targets.

        Args:
            lead_seniority: Lead's seniority level
            target_seniorities: Target seniority levels

        Returns:
            Tuple of (score, matched_level)
        """
        if not lead_seniority:
            return 5, None  # Partial points for unknown

        lead_rank = get_seniority_rank(lead_seniority)

        best_diff = float("inf")
        best_target: str | None = None

        for target in target_seniorities:
            target_rank = get_seniority_rank(target)
            diff = abs(lead_rank - target_rank)

            if diff < best_diff:
                best_diff = diff
                best_target = target

        # Calculate score based on difference
        # 0=exact(20), 1=one-off(15), 2=two-off(10), else=far(5)
        score_by_diff = {0: 20, 1: 15, 2: 10}
        score = score_by_diff.get(int(best_diff), 5)
        return score, best_target
