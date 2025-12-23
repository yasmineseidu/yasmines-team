"""
Niche Research Agent Package.

Agent for discovering and analyzing market niches using Reddit,
web search, and AI-powered analysis.
"""

from src.agents.niche_research_agent.agent import (
    NicheResearchAgent,
    NicheResearchAgentError,
)

__all__ = ["NicheResearchAgent", "NicheResearchAgentError"]
