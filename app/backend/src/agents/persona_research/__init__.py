"""
Persona Research Agent - Phase 1, Agent 1.2.

Deep-dives into target personas using Reddit mining, LinkedIn research,
and industry content analysis. Extracts exact quotes, pain points,
language patterns, and messaging angles for cold email personalization.

Depends On: Niche Research Agent (1.1)
Hands Off To: Research Export Agent (1.3)
"""

from src.agents.persona_research.agent import PersonaResearchAgent
from src.agents.persona_research.schemas import (
    IndustryFitScore,
    LanguagePattern,
    MessagingAngle,
    Objection,
    PainPointQuote,
    Persona,
    PersonaResearchConfig,
    PersonaResearchData,
    PersonaResearchResult,
)

__all__ = [
    # Agent
    "PersonaResearchAgent",
    # Models
    "Persona",
    "PainPointQuote",
    "LanguagePattern",
    "Objection",
    "MessagingAngle",
    "IndustryFitScore",
    "PersonaResearchData",
    "PersonaResearchResult",
    "PersonaResearchConfig",
]
