"""
Lead Scoring Agent - Phase 2, Agent 2.5.

Scores leads based on fit with target personas, industry alignment,
company size match, seniority level, and data completeness.
"""

from src.agents.lead_scoring.agent import (
    LeadScoringAgent,
    LeadScoringAgentError,
    LeadScoringResult,
    score_leads,
)
from src.agents.lead_scoring.job_title_matcher import (
    JobTitleMatcher,
    extract_seniority_level,
)
from src.agents.lead_scoring.schemas import (
    LeadScoreRecord,
    ScoringContext,
    ScoringInput,
)
from src.agents.lead_scoring.scoring_model import (
    TIER_THRESHOLDS,
    ScoringModel,
    determine_tier,
)

__all__ = [
    # Agent
    "LeadScoringAgent",
    "LeadScoringAgentError",
    "LeadScoringResult",
    "score_leads",
    # Matcher
    "JobTitleMatcher",
    "extract_seniority_level",
    # Schemas
    "LeadScoreRecord",
    "ScoringContext",
    "ScoringInput",
    # Scoring
    "ScoringModel",
    "TIER_THRESHOLDS",
    "determine_tier",
]
