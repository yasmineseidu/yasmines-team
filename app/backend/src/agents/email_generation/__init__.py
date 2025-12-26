"""
Email Generation Agent - Phase 4, Agent 4.3.

Generates personalized cold emails using research data, persona insights,
and proven email frameworks with quality scoring and regeneration.
"""

from src.agents.email_generation.agent import EmailGenerationAgent
from src.agents.email_generation.quality_scorer import EmailQualityScorer
from src.agents.email_generation.schemas import (
    EmailFramework,
    EmailGenerationResult,
    GeneratedEmail,
    LeadTier,
    QualityScore,
)

__all__ = [
    "EmailGenerationAgent",
    "EmailQualityScorer",
    "EmailFramework",
    "EmailGenerationResult",
    "GeneratedEmail",
    "LeadTier",
    "QualityScore",
]
