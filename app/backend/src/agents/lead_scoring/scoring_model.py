"""
Scoring Model for Lead Scoring Agent.

Implements weighted scoring with 6 components.
"""

from typing import Any, Final

from src.agents.lead_scoring.job_title_matcher import (
    JobTitleMatcher,
    extract_seniority_level,
    get_seniority_rank,
)
from src.agents.lead_scoring.schemas import (
    LeadScore,
    LeadScoreRecord,
    ScoreBreakdown,
    ScoringContext,
)

# =============================================================================
# Constants
# =============================================================================

# Score component weights (must sum to 1.0)
SCORE_WEIGHTS: Final[dict[str, float]] = {
    "job_title_match": 0.30,  # 30 points max
    "seniority_match": 0.20,  # 20 points max
    "company_size_match": 0.15,  # 15 points max
    "industry_fit": 0.20,  # 20 points max
    "location_match": 0.10,  # 10 points max
    "data_completeness": 0.05,  # 5 points max
}

# Maximum points per component
MAX_POINTS: Final[dict[str, int]] = {
    "job_title_match": 30,
    "seniority_match": 20,
    "company_size_match": 15,
    "industry_fit": 20,
    "location_match": 10,
    "data_completeness": 5,
}

# Tier thresholds
TIER_THRESHOLDS: Final[dict[str, int]] = {
    "A": 80,  # 80+ = High-priority leads
    "B": 60,  # 60-79 = Good leads
    "C": 40,  # 40-59 = Moderate leads
    "D": 0,  # <40 = Low-priority leads
}

# Company size mappings for comparison
COMPANY_SIZE_ORDER: Final[list[str]] = [
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1001-5000",
    "5001-10000",
    "10001+",
]

# Alternative company size labels
COMPANY_SIZE_ALIASES: Final[dict[str, str]] = {
    "self-employed": "1-10",
    "1-10 employees": "1-10",
    "11-50 employees": "11-50",
    "51-200 employees": "51-200",
    "201-500 employees": "201-500",
    "501-1000 employees": "501-1000",
    "1001-5000 employees": "1001-5000",
    "5001-10000 employees": "5001-10000",
    "10001+ employees": "10001+",
    "small": "1-10",
    "medium": "51-200",
    "large": "1001-5000",
    "enterprise": "5001-10000",
}

# Important data fields for completeness
COMPLETENESS_FIELDS: Final[list[str]] = [
    "email",
    "phone",
    "company_domain",
    "linkedin_url",
]


# =============================================================================
# Helper Functions
# =============================================================================


def determine_tier(score: int) -> str:
    """
    Determine tier based on score.

    Args:
        score: Total score (0-100)

    Returns:
        Tier letter (A, B, C, or D)
    """
    if score >= TIER_THRESHOLDS["A"]:
        return "A"
    elif score >= TIER_THRESHOLDS["B"]:
        return "B"
    elif score >= TIER_THRESHOLDS["C"]:
        return "C"
    else:
        return "D"


def normalize_company_size(size: str | None) -> str | None:
    """Normalize company size to standard format."""
    if not size:
        return None

    size_lower = size.lower().strip()

    # Check aliases
    if size_lower in COMPANY_SIZE_ALIASES:
        return COMPANY_SIZE_ALIASES[size_lower]

    # Check if already in standard format
    for std_size in COMPANY_SIZE_ORDER:
        if std_size.lower() in size_lower or size_lower in std_size.lower():
            return std_size

    return size


def get_company_size_index(size: str | None) -> int:
    """Get index of company size in order."""
    if not size:
        return -1

    normalized = normalize_company_size(size)
    if normalized in COMPANY_SIZE_ORDER:
        return COMPANY_SIZE_ORDER.index(normalized)

    return -1


# =============================================================================
# Scoring Model
# =============================================================================


class ScoringModel:
    """
    Lead scoring model with weighted components.

    Calculates scores based on:
    - Job title match (30%)
    - Seniority match (20%)
    - Company size match (15%)
    - Industry fit (20%)
    - Location match (10%)
    - Data completeness (5%)
    """

    def __init__(
        self,
        context: ScoringContext,
        job_title_threshold: float = 0.80,
    ) -> None:
        """
        Initialize scoring model.

        Args:
            context: Scoring context with niche, personas, industry scores
            job_title_threshold: Threshold for job title fuzzy matching
        """
        self.context = context
        self.job_title_matcher = JobTitleMatcher(threshold=job_title_threshold)

        # Pre-compute target values for efficiency
        self._target_titles = context.get_all_target_job_titles()
        self._target_seniorities = context.get_all_target_seniorities()
        self._target_sizes = context.get_all_target_company_sizes()
        self._target_countries = context.target_countries

    def score_lead(self, lead: LeadScoreRecord) -> LeadScore:
        """
        Score a single lead.

        Args:
            lead: Lead record to score

        Returns:
            LeadScore with total score, tier, and breakdown
        """
        breakdown = ScoreBreakdown()

        # 1. Job Title Match (30 points max)
        breakdown.job_title_match = self._calculate_job_title_score(lead)

        # 2. Seniority Match (20 points max)
        breakdown.seniority_match = self._calculate_seniority_score(lead)

        # 3. Company Size Match (15 points max)
        breakdown.company_size_match = self._calculate_company_size_score(lead)

        # 4. Industry Fit (20 points max)
        breakdown.industry_fit = self._calculate_industry_score(lead)

        # 5. Location Match (10 points max)
        breakdown.location_match = self._calculate_location_score(lead)

        # 6. Data Completeness (5 points max)
        breakdown.data_completeness = self._calculate_completeness_score(lead)

        # Calculate total and tier
        total_score = breakdown.total_score
        tier = determine_tier(total_score)

        # Extract persona tags
        persona_tags = self._extract_persona_tags(lead, breakdown)

        return LeadScore(
            lead_id=lead.id,
            total_score=total_score,
            tier=tier,
            breakdown=breakdown,
            persona_tags=persona_tags,
        )

    def _calculate_job_title_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate job title match score."""
        max_score = MAX_POINTS["job_title_match"]

        if not lead.title:
            return {
                "score": 0,
                "max": max_score,
                "matched_title": None,
                "similarity": 0.0,
                "reason": "No job title provided",
            }

        # Match against target titles and personas
        personas_dicts = [
            {
                "name": p.name,
                "job_titles": p.job_titles,
            }
            for p in self.context.personas
        ]

        match_result = self.job_title_matcher.match(
            lead.title,
            self._target_titles,
            personas_dicts,
        )

        if match_result.matched:
            # Scale similarity to max points
            score = int(match_result.score * max_score)
        elif match_result.score >= 0.5:
            # Partial match
            score = int(match_result.score * max_score * 0.66)
        elif match_result.seniority_level in ["c_suite", "vp", "director"]:
            # Seniority-only match bonus
            score = 10
        else:
            score = 0

        return {
            "score": min(score, max_score),
            "max": max_score,
            "matched_title": match_result.matched_title,
            "matched_persona": match_result.matched_persona,
            "similarity": round(match_result.score, 2),
        }

    def _calculate_seniority_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate seniority match score."""
        max_score = MAX_POINTS["seniority_match"]

        # Extract seniority from title if not provided
        lead_seniority = lead.seniority
        if not lead_seniority and lead.title:
            lead_seniority = extract_seniority_level(lead.title)

        if not lead_seniority:
            return {
                "score": 5,  # Partial points for unknown
                "max": max_score,
                "detected": None,
                "target": self._target_seniorities,
                "reason": "Could not determine seniority",
            }

        # If no target seniorities defined, use default
        target_seniorities = self._target_seniorities or ["director", "vp", "c_suite"]

        score, matched = self.job_title_matcher.match_seniority(
            lead_seniority,
            target_seniorities,
        )

        return {
            "score": min(score, max_score),
            "max": max_score,
            "detected": lead_seniority,
            "target": matched,
            "rank": get_seniority_rank(lead_seniority),
        }

    def _calculate_company_size_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate company size match score."""
        max_score = MAX_POINTS["company_size_match"]

        if not lead.company_size:
            return {
                "score": 5,  # Partial points for unknown
                "max": max_score,
                "detected": None,
                "target": self._target_sizes,
                "reason": "Company size not provided",
            }

        lead_size = normalize_company_size(lead.company_size)
        lead_index = get_company_size_index(lead_size)

        if lead_index < 0:
            return {
                "score": 5,
                "max": max_score,
                "detected": lead.company_size,
                "target": self._target_sizes,
                "reason": "Unknown company size format",
            }

        # Check against target sizes
        best_diff = float("inf")
        best_target: str | None = None

        for target_size in self._target_sizes:
            target_normalized = normalize_company_size(target_size)
            target_index = get_company_size_index(target_normalized)

            if target_index >= 0:
                diff = abs(lead_index - target_index)
                if diff < best_diff:
                    best_diff = diff
                    best_target = target_size

        # Calculate score based on difference
        if best_diff == 0:
            score = max_score  # Exact match
        elif best_diff == 1:
            score = 10  # Adjacent size
        elif best_diff == 2:
            score = 7
        else:
            score = 5  # Far off

        return {
            "score": min(score, max_score),
            "max": max_score,
            "detected": lead_size,
            "target": best_target or self._target_sizes,
        }

    def _calculate_industry_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate industry fit score."""
        max_score = MAX_POINTS["industry_fit"]

        if not lead.company_industry:
            return {
                "score": 10,  # Default for missing industry
                "max": max_score,
                "industry": None,
                "fit_score": 50,
                "reason": "Industry not provided",
            }

        # Get fit score from context
        fit_score = self.context.get_industry_fit_score(lead.company_industry)

        # Normalize to max points (fit_score is 0-100)
        score = int((fit_score / 100) * max_score)

        return {
            "score": min(score, max_score),
            "max": max_score,
            "industry": lead.company_industry,
            "fit_score": fit_score,
        }

    def _calculate_location_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate location match score."""
        max_score = MAX_POINTS["location_match"]

        # Use country if available, otherwise parse location
        country = lead.country
        if not country and lead.location:
            # Try to extract country from location
            location_lower = lead.location.lower()
            if "united states" in location_lower or ", us" in location_lower:
                country = "United States"
            elif "canada" in location_lower or ", ca" in location_lower:
                country = "Canada"
            elif "uk" in location_lower or "united kingdom" in location_lower:
                country = "United Kingdom"

        if not country:
            return {
                "score": 3,  # Partial for unknown
                "max": max_score,
                "country": None,
                "reason": "Location not determined",
            }

        # Check if country matches target
        country_lower = country.lower()
        for target in self._target_countries:
            if target.lower() == country_lower:
                return {
                    "score": max_score,
                    "max": max_score,
                    "country": country,
                    "matched": True,
                }

        # Check common aliases
        us_aliases = ["united states", "us", "usa", "u.s.", "america"]
        if country_lower in us_aliases and any(
            t.lower() in us_aliases for t in self._target_countries
        ):
            return {
                "score": max_score,
                "max": max_score,
                "country": country,
                "matched": True,
            }

        # Non-target country gets partial points
        return {
            "score": 3,
            "max": max_score,
            "country": country,
            "matched": False,
            "target": self._target_countries,
        }

    def _calculate_completeness_score(self, lead: LeadScoreRecord) -> dict[str, Any]:
        """Calculate data completeness score."""
        max_score = MAX_POINTS["data_completeness"]
        points_per_field = max_score / len(COMPLETENESS_FIELDS)

        present_fields = []
        for field_name in COMPLETENESS_FIELDS:
            value = getattr(lead, field_name, None)
            if value:
                present_fields.append(field_name)

        score = int(len(present_fields) * points_per_field)

        return {
            "score": min(score, max_score),
            "max": max_score,
            "fields_present": present_fields,
            "fields_missing": [f for f in COMPLETENESS_FIELDS if f not in present_fields],
        }

    def _extract_persona_tags(
        self,
        lead: LeadScoreRecord,
        breakdown: ScoreBreakdown,
    ) -> list[str]:
        """Extract persona tags from scoring results."""
        tags: set[str] = set()

        # Add matched persona
        matched_persona = breakdown.job_title_match.get("matched_persona")
        if matched_persona:
            tags.add(matched_persona)

        # Add tier tag
        tier = determine_tier(breakdown.total_score)
        tags.add(f"tier_{tier.lower()}")

        # Add seniority tag
        seniority = breakdown.seniority_match.get("detected")
        if seniority:
            tags.add(f"seniority_{seniority}")

        # Add high-value tags for A-tier
        if breakdown.total_score >= 80:
            tags.add("high_priority")

        return list(tags)

    def score_leads_batch(
        self,
        leads: list[LeadScoreRecord],
    ) -> list[LeadScore]:
        """
        Score a batch of leads.

        Args:
            leads: List of lead records

        Returns:
            List of LeadScore results
        """
        return [self.score_lead(lead) for lead in leads]
