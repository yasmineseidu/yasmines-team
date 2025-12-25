"""
Cross-Campaign Deduplication Agent - Phase 2, Agent 2.4.

Uses Claude Agent SDK to identify leads that exist across campaigns
and should be excluded based on:
- Historical matching (LinkedIn URL, email, name+company fuzzy)
- Exclusion rules (recently contacted, bounced, unsubscribed, suppression list)

Phase 2 Pipeline Position:
Input: Deduplicated leads from Agent 2.3 -> Output: Cross-deduped leads for scoring

Per LEARN-007: This agent is pure (no side effects). The orchestrator
handles all database persistence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class CrossCampaignDedupError(Exception):
    """Exception raised for Cross-Campaign Dedup agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NoLeadsToProcessError(CrossCampaignDedupError):
    """Raised when no leads are provided for processing."""

    def __init__(self) -> None:
        super().__init__("No leads provided for cross-campaign deduplication")


class HistoricalDataLoadError(CrossCampaignDedupError):
    """Raised when historical data cannot be loaded."""

    def __init__(self, source: str, error: str) -> None:
        super().__init__(
            f"Failed to load historical data from {source}: {error}",
            {"source": source, "error": error},
        )


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class ExclusionResult:
    """Result for a single excluded lead."""

    lead_id: str
    exclusion_reason: str
    excluded_due_to_campaign: str | None = None
    matched_identifier: str | None = None
    match_confidence: float = 1.0


@dataclass
class CrossCampaignDedupResult:
    """Result of Cross-Campaign Dedup agent execution."""

    # Status
    success: bool = True
    status: str = "completed"  # completed, partial, failed

    # Counts
    total_checked: int = 0
    previously_contacted: int = 0
    bounced_excluded: int = 0
    unsubscribed_excluded: int = 0
    suppression_list_excluded: int = 0
    fuzzy_match_excluded: int = 0
    remaining_leads: int = 0

    # Excluded leads with details
    exclusions: list[ExclusionResult] = field(default_factory=list)

    # IDs of leads that passed (not excluded)
    passed_lead_ids: list[str] = field(default_factory=list)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Settings used
    lookback_days: int = 90
    fuzzy_threshold: float = 0.85

    # Errors (if any)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "status": self.status,
            "total_checked": self.total_checked,
            "previously_contacted": self.previously_contacted,
            "bounced_excluded": self.bounced_excluded,
            "unsubscribed_excluded": self.unsubscribed_excluded,
            "suppression_list_excluded": self.suppression_list_excluded,
            "fuzzy_match_excluded": self.fuzzy_match_excluded,
            "remaining_leads": self.remaining_leads,
            "exclusions": [
                {
                    "lead_id": e.lead_id,
                    "exclusion_reason": e.exclusion_reason,
                    "excluded_due_to_campaign": e.excluded_due_to_campaign,
                    "matched_identifier": e.matched_identifier,
                    "match_confidence": e.match_confidence,
                }
                for e in self.exclusions
            ],
            "passed_lead_ids": self.passed_lead_ids,
            "execution_time_ms": self.execution_time_ms,
            "lookback_days": self.lookback_days,
            "fuzzy_threshold": self.fuzzy_threshold,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Fuzzy Matching Utilities
# =============================================================================


def normalize_string(s: str | None) -> str:
    """Normalize string for comparison."""
    if not s:
        return ""
    return " ".join(s.lower().strip().split())


def fuzzy_match_score(s1: str | None, s2: str | None) -> float:
    """Calculate fuzzy match score between two strings."""
    n1 = normalize_string(s1)
    n2 = normalize_string(s2)
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1, n2).ratio()


def name_company_match(
    first_name: str | None,
    last_name: str | None,
    company_name: str | None,
    hist_first_name: str | None,
    hist_last_name: str | None,
    hist_company: str | None,
    threshold: float = 0.85,
) -> tuple[bool, float]:
    """
    Check if name+company fuzzy match exceeds threshold.

    Returns:
        Tuple of (is_match, combined_score)
    """
    # Build full names
    full_name = f"{first_name or ''} {last_name or ''}".strip()
    hist_full_name = f"{hist_first_name or ''} {hist_last_name or ''}".strip()

    # Calculate scores
    name_score = fuzzy_match_score(full_name, hist_full_name)
    company_score = fuzzy_match_score(company_name, hist_company)

    # Combined score: weighted average (name slightly more important)
    combined_score = (name_score * 0.6) + (company_score * 0.4)

    return combined_score >= threshold, combined_score


# =============================================================================
# SDK MCP Tools
# =============================================================================


@tool(
    name="check_linkedin_url_history",
    description=(
        "Check if a LinkedIn URL exists in historical lead data. "
        "Returns matching historical lead info if found."
    ),
    input_schema={
        "linkedin_url": str,
        "historical_data": list,
    },
)
async def check_linkedin_url_history_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for checking LinkedIn URL against historical data.

    Args:
        args: Tool arguments with linkedin_url and historical_data.

    Returns:
        Tool result with match status and details.
    """
    linkedin_url = args.get("linkedin_url", "")
    historical_data = args.get("historical_data", [])

    if not linkedin_url:
        return {
            "content": [{"type": "text", "text": "No LinkedIn URL provided"}],
            "is_error": True,
        }

    # Normalize URL for comparison
    normalized_url = linkedin_url.lower().rstrip("/")

    for hist_lead in historical_data:
        hist_url = (hist_lead.get("linkedin_url") or "").lower().rstrip("/")
        if hist_url and normalized_url == hist_url:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"LinkedIn URL match found in campaign {hist_lead.get('campaign_id')}",
                    }
                ],
                "data": {
                    "matched": True,
                    "match_type": "linkedin_url",
                    "campaign_id": hist_lead.get("campaign_id"),
                    "email_status": hist_lead.get("email_status"),
                    "last_contacted_at": hist_lead.get("last_contacted_at"),
                },
            }

    return {
        "content": [{"type": "text", "text": "No LinkedIn URL match found"}],
        "data": {"matched": False},
    }


@tool(
    name="check_email_history",
    description=(
        "Check if an email exists in historical lead data or suppression list. "
        "Returns matching info if found."
    ),
    input_schema={
        "email": str,
        "historical_data": list,
        "suppression_list": list,
    },
)
async def check_email_history_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for checking email against historical and suppression data.

    Args:
        args: Tool arguments with email, historical_data, and suppression_list.

    Returns:
        Tool result with match status and details.
    """
    email = args.get("email", "")
    historical_data = args.get("historical_data", [])
    suppression_list = args.get("suppression_list", [])

    if not email:
        return {
            "content": [{"type": "text", "text": "No email provided"}],
            "is_error": True,
        }

    normalized_email = email.lower().strip()

    # Check suppression list first (highest priority)
    suppression_set = {e.lower().strip() for e in suppression_list if e}
    if normalized_email in suppression_set:
        return {
            "content": [{"type": "text", "text": f"Email {email} is on suppression list"}],
            "data": {
                "matched": True,
                "match_type": "suppression_list",
                "exclusion_reason": "suppression_list",
            },
        }

    # Check historical data
    for hist_lead in historical_data:
        hist_email = (hist_lead.get("email") or "").lower().strip()
        if hist_email and normalized_email == hist_email:
            email_status = hist_lead.get("email_status", "")
            exclusion_reason = "previously_contacted"

            if email_status == "bounced":
                exclusion_reason = "bounced"
            elif email_status == "unsubscribed" or email_status == "complained":
                exclusion_reason = "unsubscribed"

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Email match found: {exclusion_reason}",
                    }
                ],
                "data": {
                    "matched": True,
                    "match_type": "email",
                    "campaign_id": hist_lead.get("campaign_id"),
                    "email_status": email_status,
                    "exclusion_reason": exclusion_reason,
                    "last_contacted_at": hist_lead.get("last_contacted_at"),
                },
            }

    return {
        "content": [{"type": "text", "text": "No email match found"}],
        "data": {"matched": False},
    }


@tool(
    name="check_fuzzy_name_company",
    description=(
        "Check if name+company fuzzy matches any historical leads. "
        "Uses configurable similarity threshold (default 85%)."
    ),
    input_schema={
        "first_name": str,
        "last_name": str,
        "company_name": str,
        "historical_data": list,
        "threshold": float,
    },
)
async def check_fuzzy_name_company_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for fuzzy matching name+company against historical data.

    Args:
        args: Tool arguments with name, company, historical_data, threshold.

    Returns:
        Tool result with match status and confidence.
    """
    first_name = args.get("first_name", "")
    last_name = args.get("last_name", "")
    company_name = args.get("company_name", "")
    historical_data = args.get("historical_data", [])
    threshold = args.get("threshold", 0.85)

    if not (first_name or last_name) or not company_name:
        return {
            "content": [{"type": "text", "text": "Insufficient data for fuzzy matching"}],
            "data": {"matched": False, "reason": "insufficient_data"},
        }

    best_match = None
    best_score = 0.0

    for hist_lead in historical_data:
        is_match, score = name_company_match(
            first_name,
            last_name,
            company_name,
            hist_lead.get("first_name"),
            hist_lead.get("last_name"),
            hist_lead.get("company_name"),
            threshold,
        )
        if is_match and score > best_score:
            best_match = hist_lead
            best_score = score

    if best_match:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Fuzzy match found with {best_score:.1%} confidence",
                }
            ],
            "data": {
                "matched": True,
                "match_type": "fuzzy_name_company",
                "confidence": best_score,
                "campaign_id": best_match.get("campaign_id"),
                "matched_name": f"{best_match.get('first_name', '')} {best_match.get('last_name', '')}".strip(),
                "matched_company": best_match.get("company_name"),
            },
        }

    return {
        "content": [{"type": "text", "text": "No fuzzy match found"}],
        "data": {"matched": False},
    }


@tool(
    name="batch_check_exclusions",
    description=(
        "Batch check multiple leads against all exclusion criteria. "
        "Efficient for processing large lead batches."
    ),
    input_schema={
        "leads": list,
        "historical_data": list,
        "suppression_list": list,
        "fuzzy_threshold": float,
    },
)
async def batch_check_exclusions_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for batch checking leads against all exclusion criteria.

    This is the main workhorse tool that efficiently processes leads in batches.

    Args:
        args: Tool arguments with leads, historical_data, suppression_list, threshold.

    Returns:
        Tool result with exclusions and passed leads.
    """
    leads = args.get("leads", [])
    historical_data = args.get("historical_data", [])
    suppression_list = args.get("suppression_list", [])
    fuzzy_threshold = args.get("fuzzy_threshold", 0.85)

    if not leads:
        return {
            "content": [{"type": "text", "text": "No leads to process"}],
            "is_error": True,
        }

    # Build lookup indices for efficient matching
    suppression_set = {e.lower().strip() for e in suppression_list if e}
    linkedin_index: dict[str, dict[str, Any]] = {}
    email_index: dict[str, dict[str, Any]] = {}

    for hist in historical_data:
        linkedin_url = (hist.get("linkedin_url") or "").lower().rstrip("/")
        if linkedin_url:
            linkedin_index[linkedin_url] = hist

        email = (hist.get("email") or "").lower().strip()
        if email:
            email_index[email] = hist

    exclusions: list[dict[str, Any]] = []
    passed_ids: list[str] = []

    # Counters
    previously_contacted = 0
    bounced = 0
    unsubscribed = 0
    suppression = 0
    fuzzy_matches = 0

    for lead in leads:
        lead_id = str(lead.get("id", ""))
        excluded = False
        exclusion_info: dict[str, Any] | None = None

        # Check suppression list (email) - highest priority
        email = (lead.get("email") or "").lower().strip()
        if email and email in suppression_set:
            exclusion_info = {
                "lead_id": lead_id,
                "exclusion_reason": "suppression_list",
                "matched_identifier": email,
                "match_confidence": 1.0,
            }
            excluded = True
            suppression += 1

        # Check LinkedIn URL match
        if not excluded:
            linkedin_url = (lead.get("linkedin_url") or "").lower().rstrip("/")
            if linkedin_url and linkedin_url in linkedin_index:
                hist = linkedin_index[linkedin_url]
                email_status = hist.get("email_status", "")
                reason = "previously_contacted"
                if email_status == "bounced":
                    reason = "bounced"
                    bounced += 1
                elif email_status in ("unsubscribed", "complained"):
                    reason = "unsubscribed"
                    unsubscribed += 1
                else:
                    previously_contacted += 1

                exclusion_info = {
                    "lead_id": lead_id,
                    "exclusion_reason": reason,
                    "excluded_due_to_campaign": hist.get("campaign_id"),
                    "matched_identifier": linkedin_url,
                    "match_confidence": 1.0,
                }
                excluded = True

        # Check email match
        if not excluded and email and email in email_index:
            hist = email_index[email]
            email_status = hist.get("email_status", "")
            reason = "previously_contacted"
            if email_status == "bounced":
                reason = "bounced"
                bounced += 1
            elif email_status in ("unsubscribed", "complained"):
                reason = "unsubscribed"
                unsubscribed += 1
            else:
                previously_contacted += 1

            exclusion_info = {
                "lead_id": lead_id,
                "exclusion_reason": reason,
                "excluded_due_to_campaign": hist.get("campaign_id"),
                "matched_identifier": email,
                "match_confidence": 1.0,
            }
            excluded = True

        # Fuzzy name+company match (slowest, done last)
        if not excluded:
            first_name = lead.get("first_name", "")
            last_name = lead.get("last_name", "")
            company_name = lead.get("company_name", "")

            if (first_name or last_name) and company_name:
                for hist in historical_data:
                    is_match, score = name_company_match(
                        first_name,
                        last_name,
                        company_name,
                        hist.get("first_name"),
                        hist.get("last_name"),
                        hist.get("company_name"),
                        fuzzy_threshold,
                    )
                    if is_match:
                        matched_id = f"{hist.get('first_name', '')} {hist.get('last_name', '')} @ {hist.get('company_name', '')}"
                        exclusion_info = {
                            "lead_id": lead_id,
                            "exclusion_reason": "fuzzy_match",
                            "excluded_due_to_campaign": hist.get("campaign_id"),
                            "matched_identifier": matched_id,
                            "match_confidence": score,
                        }
                        excluded = True
                        fuzzy_matches += 1
                        break

        if excluded and exclusion_info:
            exclusions.append(exclusion_info)
        else:
            passed_ids.append(lead_id)

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Processed {len(leads)} leads: "
                    f"{len(exclusions)} excluded, {len(passed_ids)} passed"
                ),
            }
        ],
        "data": {
            "exclusions": exclusions,
            "passed_lead_ids": passed_ids,
            "counts": {
                "total_checked": len(leads),
                "previously_contacted": previously_contacted,
                "bounced_excluded": bounced,
                "unsubscribed_excluded": unsubscribed,
                "suppression_list_excluded": suppression,
                "fuzzy_match_excluded": fuzzy_matches,
                "remaining": len(passed_ids),
            },
        },
    }


# =============================================================================
# Cross-Campaign Dedup Agent
# =============================================================================


class CrossCampaignDedupAgent:
    """
    Cross-Campaign Deduplication Agent - Phase 2, Agent 2.4.

    Uses Claude Agent SDK to orchestrate cross-campaign deduplication:
    1. Historical matching (LinkedIn URL, email)
    2. Fuzzy matching (name + company)
    3. Exclusion rules (recently contacted, bounced, unsubscribed, suppression)

    This agent is pure (no side effects). It returns exclusion data that the
    orchestrator persists to the database.

    Attributes:
        name: Agent name for logging.
        model: Claude model to use.
        max_tokens: Maximum tokens for Claude responses.
        lookback_days: Days to look back for historical contacts.
        fuzzy_threshold: Minimum similarity for fuzzy matching (0.0-1.0).
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        lookback_days: int = 90,
        fuzzy_threshold: float = 0.85,
    ) -> None:
        """
        Initialize Cross-Campaign Dedup Agent.

        Args:
            model: Claude model to use.
            max_tokens: Maximum tokens for responses.
            lookback_days: Days to look back for historical contacts.
            fuzzy_threshold: Minimum similarity for fuzzy matching.
        """
        self.name = "cross_campaign_dedup"
        self.model = model
        self.max_tokens = max_tokens
        self.lookback_days = lookback_days
        self.fuzzy_threshold = fuzzy_threshold

        logger.info(
            f"[{self.name}] Agent initialized "
            f"(model={model}, lookback={lookback_days}d, fuzzy_threshold={fuzzy_threshold})"
        )

    @property
    def system_prompt(self) -> str:
        """System prompt for the Claude agent."""
        return f"""You are a Cross-Campaign Deduplication agent for cold email campaigns.

Your job is to identify leads that should be excluded from a campaign because they:
1. Exist in other campaigns (historical matching)
2. Have been recently contacted (within {self.lookback_days} days)
3. Have bounced, unsubscribed, or complained
4. Are on the global suppression list
5. Fuzzy match with historical leads (name + company, {int(self.fuzzy_threshold * 100)}% threshold)

AVAILABLE TOOLS:
1. batch_check_exclusions - Efficiently check multiple leads against all criteria
2. check_linkedin_url_history - Check single LinkedIn URL
3. check_email_history - Check single email
4. check_fuzzy_name_company - Check name+company fuzzy match

STRATEGY:
1. Use batch_check_exclusions for efficient bulk processing
2. Process leads in batches of 1000 for memory efficiency
3. Return all exclusions with detailed reasons

RULES:
- ALWAYS use batch_check_exclusions for processing leads
- Include matched_identifier and confidence for each exclusion
- Return passed_lead_ids for leads that are not excluded
- Report accurate counts by exclusion reason

OUTPUT:
Return a summary with exclusion counts and the complete list of excluded leads."""

    async def run(
        self,
        campaign_id: str,
        leads: list[dict[str, Any]],
        historical_data: list[dict[str, Any]],
        suppression_list: list[str],
        lookback_days: int | None = None,
        fuzzy_threshold: float | None = None,
    ) -> CrossCampaignDedupResult:
        """
        Execute cross-campaign deduplication for a campaign.

        This method processes leads against historical data and suppression lists
        to identify leads that should be excluded.

        Args:
            campaign_id: Campaign UUID for logging.
            leads: List of lead dictionaries to check.
            historical_data: Historical leads from other campaigns.
            suppression_list: List of suppressed email addresses.
            lookback_days: Override default lookback period.
            fuzzy_threshold: Override default fuzzy threshold.

        Returns:
            CrossCampaignDedupResult with exclusions and passed leads.
        """
        import time

        start_time = time.time()
        effective_lookback = lookback_days or self.lookback_days
        effective_threshold = fuzzy_threshold or self.fuzzy_threshold

        result = CrossCampaignDedupResult(
            started_at=datetime.now(),
            lookback_days=effective_lookback,
            fuzzy_threshold=effective_threshold,
        )

        logger.info(
            f"[{self.name}] Starting cross-campaign dedup for campaign {campaign_id} "
            f"({len(leads)} leads, {len(historical_data)} historical, "
            f"{len(suppression_list)} suppressed)"
        )

        if not leads:
            result.success = True
            result.status = "completed"
            result.completed_at = datetime.now()
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            result.warnings.append("No leads to process")
            return result

        try:
            # Directly process using batch_check_exclusions (more efficient than Claude)
            # This follows the pattern of LeadListBuilderAgent's _direct_scrape fallback
            dedup_result = await self._process_leads_directly(
                leads=leads,
                historical_data=historical_data,
                suppression_list=suppression_list,
                fuzzy_threshold=effective_threshold,
            )

            # Populate result
            result.total_checked = dedup_result["total_checked"]
            result.previously_contacted = dedup_result["previously_contacted"]
            result.bounced_excluded = dedup_result["bounced_excluded"]
            result.unsubscribed_excluded = dedup_result["unsubscribed_excluded"]
            result.suppression_list_excluded = dedup_result["suppression_list_excluded"]
            result.fuzzy_match_excluded = dedup_result["fuzzy_match_excluded"]
            result.remaining_leads = dedup_result["remaining_leads"]

            # Convert exclusions to ExclusionResult objects
            for exc in dedup_result["exclusions"]:
                result.exclusions.append(
                    ExclusionResult(
                        lead_id=exc["lead_id"],
                        exclusion_reason=exc["exclusion_reason"],
                        excluded_due_to_campaign=exc.get("excluded_due_to_campaign"),
                        matched_identifier=exc.get("matched_identifier"),
                        match_confidence=exc.get("match_confidence", 1.0),
                    )
                )

            result.passed_lead_ids = dedup_result["passed_lead_ids"]
            result.success = True
            result.status = "completed"

            logger.info(
                f"[{self.name}] Cross-campaign dedup completed: "
                f"{result.total_checked} checked, {len(result.exclusions)} excluded, "
                f"{result.remaining_leads} passed "
                f"(previously_contacted={result.previously_contacted}, "
                f"bounced={result.bounced_excluded}, "
                f"unsubscribed={result.unsubscribed_excluded}, "
                f"suppression={result.suppression_list_excluded}, "
                f"fuzzy={result.fuzzy_match_excluded})"
            )

        except Exception as e:
            logger.error(f"[{self.name}] Cross-campaign dedup failed: {e}")
            result.success = False
            result.status = "failed"
            result.errors.append(
                {
                    "type": type(e).__name__,
                    "message": str(e),
                }
            )

        result.completed_at = datetime.now()
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    async def _process_leads_directly(
        self,
        leads: list[dict[str, Any]],
        historical_data: list[dict[str, Any]],
        suppression_list: list[str],
        fuzzy_threshold: float,
    ) -> dict[str, Any]:
        """
        Process leads directly without Claude orchestration.

        This is more efficient for pure data processing tasks.
        Uses the same logic as batch_check_exclusions_tool.
        """
        # Build lookup indices for efficient matching
        suppression_set = {e.lower().strip() for e in suppression_list if e}
        linkedin_index: dict[str, dict[str, Any]] = {}
        email_index: dict[str, dict[str, Any]] = {}

        for hist in historical_data:
            linkedin_url = (hist.get("linkedin_url") or "").lower().rstrip("/")
            if linkedin_url:
                linkedin_index[linkedin_url] = hist

            email = (hist.get("email") or "").lower().strip()
            if email:
                email_index[email] = hist

        exclusions: list[dict[str, Any]] = []
        passed_ids: list[str] = []

        # Counters
        previously_contacted = 0
        bounced = 0
        unsubscribed = 0
        suppression = 0
        fuzzy_matches = 0

        for lead in leads:
            lead_id = str(lead.get("id", ""))
            excluded = False
            exclusion_info: dict[str, Any] | None = None

            # Check suppression list (email) - highest priority
            email = (lead.get("email") or "").lower().strip()
            if email and email in suppression_set:
                exclusion_info = {
                    "lead_id": lead_id,
                    "exclusion_reason": "suppression_list",
                    "matched_identifier": email,
                    "match_confidence": 1.0,
                }
                excluded = True
                suppression += 1

            # Check LinkedIn URL match
            if not excluded:
                linkedin_url = (lead.get("linkedin_url") or "").lower().rstrip("/")
                if linkedin_url and linkedin_url in linkedin_index:
                    hist = linkedin_index[linkedin_url]
                    email_status = hist.get("email_status", "")
                    reason = "previously_contacted"
                    if email_status == "bounced":
                        reason = "bounced"
                        bounced += 1
                    elif email_status in ("unsubscribed", "complained"):
                        reason = "unsubscribed"
                        unsubscribed += 1
                    else:
                        previously_contacted += 1

                    exclusion_info = {
                        "lead_id": lead_id,
                        "exclusion_reason": reason,
                        "excluded_due_to_campaign": hist.get("campaign_id"),
                        "matched_identifier": linkedin_url,
                        "match_confidence": 1.0,
                    }
                    excluded = True

            # Check email match
            if not excluded and email and email in email_index:
                hist = email_index[email]
                email_status = hist.get("email_status", "")
                reason = "previously_contacted"
                if email_status == "bounced":
                    reason = "bounced"
                    bounced += 1
                elif email_status in ("unsubscribed", "complained"):
                    reason = "unsubscribed"
                    unsubscribed += 1
                else:
                    previously_contacted += 1

                exclusion_info = {
                    "lead_id": lead_id,
                    "exclusion_reason": reason,
                    "excluded_due_to_campaign": hist.get("campaign_id"),
                    "matched_identifier": email,
                    "match_confidence": 1.0,
                }
                excluded = True

            # Fuzzy name+company match (slowest, done last)
            if not excluded:
                first_name = lead.get("first_name", "")
                last_name = lead.get("last_name", "")
                company_name = lead.get("company_name", "")

                if (first_name or last_name) and company_name:
                    for hist in historical_data:
                        is_match, score = name_company_match(
                            first_name,
                            last_name,
                            company_name,
                            hist.get("first_name"),
                            hist.get("last_name"),
                            hist.get("company_name"),
                            fuzzy_threshold,
                        )
                        if is_match:
                            matched_id = (
                                f"{hist.get('first_name', '')} "
                                f"{hist.get('last_name', '')} @ "
                                f"{hist.get('company_name', '')}"
                            )
                            exclusion_info = {
                                "lead_id": lead_id,
                                "exclusion_reason": "fuzzy_match",
                                "excluded_due_to_campaign": hist.get("campaign_id"),
                                "matched_identifier": matched_id,
                                "match_confidence": score,
                            }
                            excluded = True
                            fuzzy_matches += 1
                            break

            if excluded and exclusion_info:
                exclusions.append(exclusion_info)
            else:
                passed_ids.append(lead_id)

        return {
            "exclusions": exclusions,
            "passed_lead_ids": passed_ids,
            "total_checked": len(leads),
            "previously_contacted": previously_contacted,
            "bounced_excluded": bounced,
            "unsubscribed_excluded": unsubscribed,
            "suppression_list_excluded": suppression,
            "fuzzy_match_excluded": fuzzy_matches,
            "remaining_leads": len(passed_ids),
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def cross_campaign_dedup(
    campaign_id: str,
    leads: list[dict[str, Any]],
    historical_data: list[dict[str, Any]],
    suppression_list: list[str],
    lookback_days: int = 90,
    fuzzy_threshold: float = 0.85,
) -> CrossCampaignDedupResult:
    """
    Convenience function for cross-campaign deduplication.

    Args:
        campaign_id: Campaign UUID.
        leads: Leads to check.
        historical_data: Historical leads from other campaigns.
        suppression_list: Suppressed email addresses.
        lookback_days: Days to look back.
        fuzzy_threshold: Minimum similarity for fuzzy matching.

    Returns:
        CrossCampaignDedupResult with exclusions and passed leads.
    """
    agent = CrossCampaignDedupAgent(
        lookback_days=lookback_days,
        fuzzy_threshold=fuzzy_threshold,
    )
    return await agent.run(
        campaign_id=campaign_id,
        leads=leads,
        historical_data=historical_data,
        suppression_list=suppression_list,
    )
