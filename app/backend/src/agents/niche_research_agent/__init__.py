"""
Niche Research Agent Package.

Agent for discovering and analyzing market niches using Reddit,
web search, and AI-powered analysis with Claude Agent SDK.

This agent includes:
- SDK MCP tools for Reddit search, pain point extraction, opportunity identification
- Resilient integration clients with retry logic and rate limiting
- Token bucket rate limiters for API call management
- Ultra-resilient error handling for 4xx/5xx/timeout/connection errors
"""

from src.agents.niche_research_agent.agent import (
    AuthenticationFailedError,
    NicheResearchAgent,
    NicheResearchAgentError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TokenBucketRateLimiter,
    create_niche_research_mcp_server,
)

__all__ = [
    "NicheResearchAgent",
    "NicheResearchAgentError",
    "RateLimitExceededError",
    "AuthenticationFailedError",
    "ServiceUnavailableError",
    "TokenBucketRateLimiter",
    "create_niche_research_mcp_server",
]
