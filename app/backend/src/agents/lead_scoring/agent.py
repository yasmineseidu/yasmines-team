"""
Lead Scoring Agent - Phase 2, Agent 2.5.

Scores leads based on fit with target personas, industry alignment,
company size match, seniority level, and data completeness.

This agent is pure (no side effects). The orchestrator handles all database
persistence per LEARN-007.

Database Interactions:

1. INPUT: leads (from orchestrator)
   - Source Agent: Cross-Campaign Dedup Agent (2.4)
   - Required Fields: id, title, seniority, company_name, company_size,
                      company_industry, location, country, email, phone
   - Data Format: list[dict[str, Any]] with lead records
   - Handoff Method: Orchestrator passes leads list directly to run()

2. INPUT: scoring_context (from orchestrator)
   - Source: Database (niches, personas, industry_fit_scores tables)
   - Required Data: niche details, persona job titles/seniorities, industry scores
   - Data Format: ScoringContext dataclass
   - Handoff Method: Orchestrator loads and passes context to run()

3. OUTPUT: LeadScoringResult (returned to orchestrator)
   - Target Agent: Import Finalizer Agent (2.6)
   - Written Fields: lead_scores with score, tier, breakdown, persona_tags
   - Data Format: LeadScoringResult dataclass with DB update operations
   - Handoff Method: Orchestrator receives result and handles DB persistence

4. HANDOFF COORDINATION:
   - Upstream Dependencies: Cross-Campaign Dedup Agent (2.4) must complete first
   - Downstream Consumers: Import Finalizer Agent (2.6)
   - Failure Handling: Returns LeadScoringResult with success=False, errors populated
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query
from claude_agent_sdk.types import AssistantMessage

from src.agents.lead_scoring.schemas import (
    LeadScore,
    LeadScoreRecord,
    ScoringContext,
)
from src.agents.lead_scoring.scoring_model import ScoringModel
from src.agents.lead_scoring.tools import (
    aggregate_scoring_results_tool,
    get_scoring_summary_tool,
    load_scoring_context_tool,
    score_leads_batch_tool,
    set_leads_data,
    set_scoring_context,
)

logger = logging.getLogger(__name__)

# Model constants
DEFAULT_MODEL: Final[str] = "claude-sonnet-4-20250514"
OPUS_MODEL: Final[str] = "claude-opus-4-20250514"
HAIKU_MODEL: Final[str] = "claude-haiku-3-20250310"


# =============================================================================
# Exceptions
# =============================================================================


class LeadScoringAgentError(Exception):
    """Exception raised for Lead Scoring agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InsufficientLeadsError(LeadScoringAgentError):
    """Raised when no leads are available for scoring."""

    def __init__(self, message: str = "No leads available for scoring") -> None:
        super().__init__(message)


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class LeadScoringResult:
    """Result of Lead Scoring agent execution."""

    # Status
    success: bool = True
    status: str = "completed"  # completed, partial, failed

    # Counts
    total_scored: int = 0
    avg_score: float = 0.0
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_c_count: int = 0
    tier_d_count: int = 0

    # Score distribution
    score_distribution: dict[str, int] = field(default_factory=dict)

    # Individual scores for database updates
    lead_scores: list[dict[str, Any]] = field(default_factory=list)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "status": self.status,
            "total_scored": self.total_scored,
            "avg_score": round(self.avg_score, 2),
            "tier_a_count": self.tier_a_count,
            "tier_b_count": self.tier_b_count,
            "tier_c_count": self.tier_c_count,
            "tier_d_count": self.tier_d_count,
            "score_distribution": self.score_distribution,
            "lead_scores": self.lead_scores,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Lead Scoring Agent
# =============================================================================


class LeadScoringAgent:
    """
    Lead Scoring Agent - Phase 2, Agent 2.5.

    Uses Claude Agent SDK to orchestrate lead scoring with weighted components:
    - Job Title Match (30%)
    - Seniority Match (20%)
    - Company Size Match (15%)
    - Industry Fit (20%)
    - Location Match (10%)
    - Data Completeness (5%)

    This agent is pure (no side effects). It returns scoring results that
    the orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use.
        batch_size: Number of leads per batch.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        batch_size: int = 2000,
        job_title_threshold: float = 0.80,
    ) -> None:
        """
        Initialize Lead Scoring Agent.

        Args:
            model: Claude model to use.
            batch_size: Number of leads to process per batch.
            job_title_threshold: Threshold for job title fuzzy matching.
        """
        self.name = "lead_scoring"
        self.model = model
        self.batch_size = batch_size
        self.job_title_threshold = job_title_threshold

        logger.info(
            f"[{self.name}] Agent initialized "
            f"(model={model}, batch_size={batch_size}, "
            f"job_title_threshold={job_title_threshold})"
        )

    @property
    def system_prompt(self) -> str:
        """System prompt for the Claude agent."""
        return """You are a lead scoring specialist evaluating fit with target personas.

AVAILABLE TOOLS:
1. load_scoring_context - Load niche, personas, and industry fit scores
2. score_leads_batch - Score a batch of leads using weighted model
3. aggregate_scoring_results - Compile scoring statistics from batches
4. get_scoring_summary - Generate human-readable summary report

SCORING COMPONENTS (100 points total):
- Job Title Match (30 pts): Exact/similar match to target titles
- Seniority Match (20 pts): Correct decision-making level
- Company Size Match (15 pts): Within target range
- Industry Fit (20 pts): Based on industry scores from research
- Location Match (10 pts): Geographic alignment
- Data Completeness (5 pts): Email, phone, domain available

TIER THRESHOLDS:
- Tier A (80+): High priority - prioritize for personalization
- Tier B (60-79): Good leads - include in campaign
- Tier C (40-59): Moderate - include if capacity allows
- Tier D (<40): Low priority - skip or use generic messaging

PROCESS:
1. Load scoring context
2. Score leads in batches
3. Aggregate results
4. Generate summary report

QUALITY GOALS:
- Score all available leads
- Target 50% Tier A+B
- Average score >= 50"""

    async def run(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
        scoring_context: dict[str, Any] | None = None,
        use_claude: bool = False,
    ) -> LeadScoringResult:
        """
        Execute lead scoring for a campaign.

        This method can run in two modes:
        1. Direct mode (default): Uses Python scoring model directly
        2. Claude mode: Uses Claude Agent SDK for orchestration

        Args:
            campaign_id: Campaign UUID.
            leads: List of lead dictionaries.
            scoring_context: Optional pre-loaded scoring context.
            use_claude: If True, use Claude for orchestration.

        Returns:
            LeadScoringResult with scores and statistics.
        """
        start_time = time.time()
        result = LeadScoringResult(
            started_at=datetime.now(),
        )

        logger.info(
            f"[{self.name}] Starting lead scoring for campaign {campaign_id} ({len(leads)} leads)"
        )

        if not leads:
            result.success = True
            result.status = "completed"
            result.total_scored = 0
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[{self.name}] No leads to score")
            return result

        if not scoring_context:
            result.success = False
            result.status = "failed"
            result.errors.append(
                {
                    "type": "MissingScoringContext",
                    "message": "Scoring context not provided",
                }
            )
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{self.name}] Scoring context not provided")
            return result

        try:
            if use_claude:
                return await self._run_with_claude(campaign_id, leads, scoring_context, start_time)
            else:
                return await self._run_direct(campaign_id, leads, scoring_context, start_time)

        except Exception as e:
            logger.error(f"[{self.name}] Lead scoring failed: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append({"type": type(e).__name__, "message": str(e)})
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    async def _run_direct(
        self,
        campaign_id: str,
        leads_data: list[dict[str, Any]],
        scoring_context_data: dict[str, Any],
        start_time: float,
    ) -> LeadScoringResult:
        """
        Run lead scoring directly with Python scoring model.

        This is the recommended mode for production - faster and more reliable.
        """
        result = LeadScoringResult(
            started_at=datetime.now(),
        )

        # Create scoring model
        context = ScoringContext.from_dict(scoring_context_data)
        model = ScoringModel(context, job_title_threshold=self.job_title_threshold)

        # Convert leads to records
        lead_records = [LeadScoreRecord.from_dict(lead) for lead in leads_data]

        # Score all leads
        all_scores: list[LeadScore] = []
        for i in range(0, len(lead_records), self.batch_size):
            batch = lead_records[i : i + self.batch_size]
            batch_scores = model.score_leads_batch(batch)
            all_scores.extend(batch_scores)

            logger.debug(
                f"[{self.name}] Scored batch {i // self.batch_size + 1}: {len(batch_scores)} leads"
            )

        # Calculate statistics
        total_scored = len(all_scores)
        total_score_sum = sum(s.total_score for s in all_scores)
        avg_score = total_score_sum / total_scored if total_scored > 0 else 0

        tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for score in all_scores:
            tier_counts[score.tier] = tier_counts.get(score.tier, 0) + 1

        # Calculate score distribution
        distribution = {}
        for i in range(0, 101, 10):
            bucket = f"{i}-{i + 9}"
            distribution[bucket] = len([s for s in all_scores if i <= s.total_score < i + 10])

        # Convert scores to output format for database updates
        lead_scores = [
            {
                "lead_id": s.lead_id,
                "score": s.total_score,
                "tier": s.tier,
                "breakdown": s.breakdown.to_dict(),
                "persona_tags": s.persona_tags,
            }
            for s in all_scores
        ]

        # Build result
        result.total_scored = total_scored
        result.avg_score = avg_score
        result.tier_a_count = tier_counts["A"]
        result.tier_b_count = tier_counts["B"]
        result.tier_c_count = tier_counts["C"]
        result.tier_d_count = tier_counts["D"]
        result.score_distribution = distribution
        result.lead_scores = lead_scores
        result.success = True
        result.status = "completed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Scoring completed: "
            f"{total_scored} leads scored, "
            f"avg={avg_score:.1f}, "
            f"A={tier_counts['A']}, B={tier_counts['B']}, "
            f"C={tier_counts['C']}, D={tier_counts['D']}, "
            f"time={result.execution_time_ms}ms"
        )

        return result

    async def _run_with_claude(
        self,
        campaign_id: str,
        leads_data: list[dict[str, Any]],
        scoring_context_data: dict[str, Any],
        start_time: float,
    ) -> LeadScoringResult:
        """
        Run lead scoring with Claude Agent SDK orchestration.

        Uses Claude to coordinate the scoring process.
        """
        result = LeadScoringResult(
            started_at=datetime.now(),
        )

        # Set up tool context (per LEARN-003 - tools must be self-contained)
        set_scoring_context(scoring_context_data)
        set_leads_data(leads_data)

        # Build task prompt
        num_batches = (len(leads_data) + self.batch_size - 1) // self.batch_size
        task_prompt = self._build_task_prompt(campaign_id, len(leads_data), num_batches)

        # Create SDK MCP server with tools
        mcp_server = create_sdk_mcp_server(
            name="lead_scoring_tools",
            tools=[
                load_scoring_context_tool,
                score_leads_batch_tool,
                aggregate_scoring_results_tool,
                get_scoring_summary_tool,
            ],
        )

        # Clear conflicting env var (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Tool names for allowed_tools (mcp__{server}__{tool} pattern per SDK_PATTERNS.md)
        tool_names = [
            "mcp__lead_scoring_tools__load_scoring_context",
            "mcp__lead_scoring_tools__score_leads_batch",
            "mcp__lead_scoring_tools__aggregate_scoring_results",
            "mcp__lead_scoring_tools__get_scoring_summary",
        ]

        # Query Claude with tools
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.system_prompt,
            setting_sources=["project"],  # Required for CLAUDE.md (CRITICAL-002)
            mcp_servers={"lead_scoring_tools": mcp_server},
            allowed_tools=tool_names,  # Required for Claude to use tools (CRITICAL-001)
        )

        # Process messages from query iterator
        all_scores: list[dict[str, Any]] = []

        async for message in query(prompt=task_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "tool_result"):
                        tool_data = getattr(block, "tool_result", {})
                        if isinstance(tool_data, dict) and "data" in tool_data:
                            data = tool_data["data"]

                            # Check for aggregated results
                            if "total_scored" in data and "all_scores" in data:
                                result.total_scored = data.get("total_scored", 0)
                                result.avg_score = data.get("avg_score", 0)
                                result.tier_a_count = data.get("tier_a_count", 0)
                                result.tier_b_count = data.get("tier_b_count", 0)
                                result.tier_c_count = data.get("tier_c_count", 0)
                                result.tier_d_count = data.get("tier_d_count", 0)
                                result.score_distribution = data.get("score_distribution", {})
                                all_scores = data.get("all_scores", [])

        # Set lead scores
        result.lead_scores = all_scores
        result.success = True
        result.status = "completed"
        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{self.name}] Claude-orchestrated scoring completed: "
            f"{result.total_scored} leads scored, avg={result.avg_score:.1f}"
        )

        return result

    def _build_task_prompt(self, campaign_id: str, lead_count: int, num_batches: int) -> str:
        """Build the task prompt for Claude."""
        return f"""Score leads for campaign {campaign_id}.

LEADS TO SCORE: {lead_count}
BATCHES: {num_batches} (batch size: {self.batch_size})

INSTRUCTIONS:
1. Use load_scoring_context to verify context is loaded
2. For each batch (0 to {num_batches - 1}):
   - Use score_leads_batch with batch_index and batch_size={self.batch_size}
3. Use aggregate_scoring_results with all batch results
4. Use get_scoring_summary to generate final report

SCORING COMPONENTS:
- Job Title Match (30%): Fuzzy match with {self.job_title_threshold} threshold
- Seniority Match (20%): Compare against target levels
- Company Size Match (15%): Range comparison
- Industry Fit (20%): Lookup from industry_fit_scores
- Location Match (10%): Country/region match
- Data Completeness (5%): email, phone, domain, linkedin

TIERS: A (80+), B (60-79), C (40-59), D (<40)

Report final counts and any issues encountered."""


# =============================================================================
# Convenience Functions
# =============================================================================


async def score_leads(
    campaign_id: str,
    leads: list[dict[str, Any]],
    scoring_context: dict[str, Any],
    batch_size: int = 2000,
    use_claude: bool = False,
) -> LeadScoringResult:
    """
    Convenience function to score leads.

    Args:
        campaign_id: Campaign UUID.
        leads: List of lead dictionaries.
        scoring_context: Scoring context dictionary.
        batch_size: Number of leads per batch.
        use_claude: If True, use Claude for orchestration.

    Returns:
        LeadScoringResult with scores and statistics.
    """
    agent = LeadScoringAgent(batch_size=batch_size)
    return await agent.run(
        campaign_id=campaign_id,
        leads=leads,
        scoring_context=scoring_context,
        use_claude=use_claude,
    )
