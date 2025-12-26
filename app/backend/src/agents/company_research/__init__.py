"""
Company Research Agent module.

Phase 4 agent that conducts deep research on target companies using web search,
news, and public data for email personalization.

Exports:
    CompanyResearchAgent: Main agent class
    CompanyResearchInput: Input schema
    CompanyResearchOutput: Output schema
    COMPANY_RESEARCH_TOOLS: List of SDK MCP tools
"""

from src.agents.company_research.agent import CompanyResearchAgent
from src.agents.company_research.schemas import (
    CompanyResearchInput,
    CompanyResearchOutput,
    CompanyToResearch,
    ExtractedFact,
    ResearchResult,
)
from src.agents.company_research.tools import COMPANY_RESEARCH_TOOLS

__all__ = [
    "CompanyResearchAgent",
    "CompanyResearchInput",
    "CompanyResearchOutput",
    "CompanyToResearch",
    "ResearchResult",
    "ExtractedFact",
    "COMPANY_RESEARCH_TOOLS",
]
