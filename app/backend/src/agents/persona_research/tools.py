"""
SDK MCP Tools for Persona Research Agent.

Defines tool functions for:
- Reddit pain point mining
- Language pattern extraction
- Quote collection
- Persona synthesis
- Industry fit scoring

All tools are self-contained following the SDK pattern.
These functions can be registered with the Claude Agent SDK
using the create_sdk_mcp_server function.
"""

import logging
import os
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Pain Point Indicator Lists
# ============================================================================

PAIN_INDICATORS = [
    "struggling with",
    "frustrated by",
    "biggest challenge",
    "hate when",
    "wish i could",
    "if only",
    "anyone else deal with",
    "drives me crazy",
    "nightmare",
    "pain in the",
    "waste of time",
    "so annoying",
    "fed up with",
    "sick of",
    "tired of",
    "help me",
    "need advice",
    "any advice",
    "how do you handle",
]

EMOTIONAL_WORDS = [
    "frustrated",
    "annoying",
    "nightmare",
    "hate",
    "terrible",
    "awful",
    "ridiculous",
    "insane",
    "crazy",
    "impossible",
    "exhausting",
    "overwhelming",
    "stressful",
]


# ============================================================================
# SDK MCP Tools
# ============================================================================


async def mine_reddit_pain_points_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for mining Reddit pain points.

    This tool creates its own Reddit client using provided credentials,
    following the SDK pattern where tools are self-contained.

    Args:
        args: Tool arguments

    Returns:
        Tool result with pain points and quotes
    """
    from src.agents.persona_research.reddit_miner import RedditMiner, RedditMinerError

    try:
        job_titles = args.get("job_titles", ["manager"])
        industry = args.get("industry", "technology")
        max_results = args.get("max_results", 20)

        # Security: Only read credentials from environment, never accept as parameters
        # (see SDK_PATTERNS.md LEARN-003)
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")

        if not client_id or not client_secret:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables not set",
                    }
                ],
                "is_error": True,
            }

        # Create Reddit miner
        miner = RedditMiner(
            client_id=client_id,
            client_secret=client_secret,
        )

        # Mine for persona data
        result = await miner.mine_for_persona(
            job_titles=job_titles,
            industry=industry,
            max_subreddits=5,
            posts_per_subreddit=25,
        )

        # Format pain points for response
        pain_points = [
            {
                "pain": pp.pain,
                "quote": pp.quote,
                "intensity": pp.intensity,
                "source": pp.source,
                "engagement": pp.engagement_score,
            }
            for pp in result.pain_points[:max_results]
        ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(pain_points)} pain points from Reddit",
                }
            ],
            "data": {
                "pain_points": pain_points,
                "posts_analyzed": result.posts_analyzed,
                "comments_analyzed": result.comments_analyzed,
                "subreddit_relevance": result.subreddit_relevance,
            },
        }

    except RedditMinerError as e:
        logger.error(f"Reddit mining failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Reddit mining failed: {e}"}],
            "is_error": True,
        }

    except Exception as e:
        logger.error(f"Unexpected error in mine_reddit_pain_points: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }


async def extract_language_patterns_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for extracting language patterns.

    Args:
        args: Tool arguments with posts and max_patterns

    Returns:
        Tool result with extracted patterns
    """
    import re

    posts = args.get("posts", [])
    max_patterns = args.get("max_patterns", 30)

    # Collect all text
    all_text: list[str] = []
    for post in posts:
        if isinstance(post, dict):
            all_text.append(post.get("title", ""))
            all_text.append(post.get("content", ""))
        else:
            all_text.append(str(post))

    # Count phrase frequencies
    phrase_counter: Counter[str] = Counter()

    for text in all_text:
        # Clean text
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\'-]", "", text)

        # Extract 3-5 word phrases
        words = text.split()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i : i + 3]).lower()
            if len(phrase) > 10:
                phrase_counter[phrase] += 1

    # Build patterns list
    patterns = []
    for phrase, count in phrase_counter.most_common(max_patterns):
        if count >= 2:  # Only include phrases seen 2+ times
            category = "general"

            # Categorize
            phrase_lower = phrase.lower()
            if any(word in phrase_lower for word in EMOTIONAL_WORDS):
                category = "emotional"
            elif any(ind in phrase_lower for ind in PAIN_INDICATORS):
                category = "pain"
            elif any(word in phrase_lower for word in ["want", "need", "goal"]):
                category = "goal"
            else:
                category = "jargon"

            patterns.append(
                {
                    "phrase": phrase,
                    "category": category,
                    "frequency": count,
                }
            )

    return {
        "content": [
            {
                "type": "text",
                "text": f"Extracted {len(patterns)} language patterns",
            }
        ],
        "data": {"patterns": patterns},
    }


async def synthesize_persona_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for synthesizing a complete persona.

    Args:
        args: Tool arguments with persona components

    Returns:
        Tool result with synthesized persona
    """
    import uuid

    name = args.get("name", "Buyer Persona")
    job_titles = args.get("job_titles", [])
    seniority_level = args.get("seniority_level", "manager")
    department = args.get("department", "")
    pain_points = args.get("pain_points", [])
    goals = args.get("goals", [])
    language_patterns = args.get("language_patterns", [])
    industry = args.get("industry", "")

    # Build objections based on pain points
    objections = []
    for pp in pain_points[:3]:
        pain = pp.get("pain", "") if isinstance(pp, dict) else str(pp)
        objections.append(
            {
                "objection": "We don't have budget for this right now",
                "real_meaning": f"I'm not convinced this solves {pain}",
                "counter": f"Show ROI on addressing {pain}",
            }
        )

    # Build trigger events
    trigger_events = [
        "New job or promotion",
        "Funding round announcement",
        "Hiring spike in the team",
        "Competitor pressure",
        "Quarter end approaching",
    ]

    # Build messaging angles
    primary_angle = {
        "angle": "Pain-focused",
        "hook": pain_points[0].get("pain", "") if pain_points else "Your biggest challenge",
        "supporting_pain": pain_points[0].get("quote", "") if pain_points else "",
    }

    secondary_angle = {
        "angle": "Goal-focused",
        "hook": goals[0] if goals else "Achieve your goals faster",
        "supporting_pain": pain_points[1].get("pain", "") if len(pain_points) > 1 else "",
    }

    # Build persona
    persona = {
        "id": str(uuid.uuid4()),
        "name": name,
        "job_titles": job_titles,
        "seniority_level": seniority_level,
        "department": department,
        "pain_points": pain_points,
        "goals": goals,
        "objections": objections,
        "language_patterns": [
            p.get("phrase", "") if isinstance(p, dict) else str(p) for p in language_patterns[:10]
        ],
        "trigger_events": trigger_events,
        "messaging_angles": {
            "primary": primary_angle,
            "secondary": secondary_angle,
        },
        "angles_to_avoid": [
            "Generic productivity claims",
            "Price-focused messaging",
            "Technical jargon overload",
        ],
        "industry": industry,
    }

    return {
        "content": [
            {
                "type": "text",
                "text": f"Synthesized persona: {name}",
            }
        ],
        "data": {"persona": persona},
    }


async def calculate_industry_fit_score_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for calculating industry fit scores.

    Args:
        args: Tool arguments

    Returns:
        Tool result with fit score
    """
    industry = args.get("industry", "")
    niche_pain_points = args.get("niche_pain_points", [])
    persona_pain_points = args.get("persona_pain_points", [])
    accessibility_score = args.get("accessibility_score", 0.5)
    budget_indicators = args.get("budget_indicators", 0.5)

    # Calculate pain point alignment
    niche_set = {str(p).lower() for p in niche_pain_points}
    persona_set = {
        str(p.get("pain", p) if isinstance(p, dict) else p).lower() for p in persona_pain_points
    }

    # Find overlapping pain points
    overlap = niche_set.intersection(persona_set)
    alignment_score = len(overlap) / max(len(niche_set), 1)

    # Calculate overall score (0-100)
    score = int((alignment_score * 0.4 + accessibility_score * 0.3 + budget_indicators * 0.3) * 100)

    # Build reasoning
    reasoning = f"Industry {industry} scores {score}/100. "
    reasoning += f"Pain alignment: {len(overlap)} matching pain points. "
    reasoning += f"Accessibility: {accessibility_score:.0%}. "
    reasoning += f"Budget indicators: {budget_indicators:.0%}."

    return {
        "content": [
            {
                "type": "text",
                "text": f"Industry fit score for {industry}: {score}/100",
            }
        ],
        "data": {
            "industry": industry,
            "score": score,
            "reasoning": reasoning,
            "alignment": list(overlap)[:10],
        },
    }


async def consolidate_pain_points_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for consolidating pain points from multiple sources.

    Args:
        args: Tool arguments with pain points from different sources

    Returns:
        Tool result with consolidated pain points
    """
    reddit_pp = args.get("reddit_pain_points", [])
    linkedin_pp = args.get("linkedin_pain_points", [])
    industry_pp = args.get("industry_pain_points", [])
    max_consolidated = args.get("max_consolidated", 10)

    # Collect all pain points with source weighting
    weighted_pain_points: dict[str, dict[str, Any]] = {}

    # Reddit pain points (highest weight - real conversations)
    for pp in reddit_pp:
        pain = pp.get("pain", str(pp)) if isinstance(pp, dict) else str(pp)
        pain_lower = pain.lower().strip()

        if pain_lower not in weighted_pain_points:
            weighted_pain_points[pain_lower] = {
                "pain": pain,
                "weight": 0,
                "sources": [],
            }

        weighted_pain_points[pain_lower]["weight"] += 3  # Reddit = 3x weight
        weighted_pain_points[pain_lower]["sources"].append("reddit")

    # LinkedIn pain points (medium weight - professional context)
    for pp in linkedin_pp:
        pain = pp.get("pain", str(pp)) if isinstance(pp, dict) else str(pp)
        pain_lower = pain.lower().strip()

        if pain_lower not in weighted_pain_points:
            weighted_pain_points[pain_lower] = {
                "pain": pain,
                "weight": 0,
                "sources": [],
            }

        weighted_pain_points[pain_lower]["weight"] += 2  # LinkedIn = 2x weight
        weighted_pain_points[pain_lower]["sources"].append("linkedin")

    # Industry pain points (lower weight - general)
    for pp in industry_pp:
        pain = pp.get("pain", str(pp)) if isinstance(pp, dict) else str(pp)
        pain_lower = pain.lower().strip()

        if pain_lower not in weighted_pain_points:
            weighted_pain_points[pain_lower] = {
                "pain": pain,
                "weight": 0,
                "sources": [],
            }

        weighted_pain_points[pain_lower]["weight"] += 1  # Industry = 1x weight
        weighted_pain_points[pain_lower]["sources"].append("industry")

    # Sort by weight and get top consolidated
    sorted_pain_points = sorted(
        weighted_pain_points.values(),
        key=lambda x: x["weight"],
        reverse=True,
    )

    consolidated = [
        {
            "pain": pp["pain"],
            "weight": pp["weight"],
            "sources": list(set(pp["sources"])),
            "multi_source": len(set(pp["sources"])) > 1,
        }
        for pp in sorted_pain_points[:max_consolidated]
    ]

    return {
        "content": [
            {
                "type": "text",
                "text": f"Consolidated {len(consolidated)} pain points from {len(reddit_pp) + len(linkedin_pp) + len(industry_pp)} sources",
            }
        ],
        "data": {
            "consolidated_pain_points": consolidated,
            "multi_source_count": sum(1 for pp in consolidated if pp["multi_source"]),
        },
    }


# ============================================================================
# Tool Registry
# ============================================================================

PERSONA_RESEARCH_TOOLS = [
    mine_reddit_pain_points_tool,
    extract_language_patterns_tool,
    synthesize_persona_tool,
    calculate_industry_fit_score_tool,
    consolidate_pain_points_tool,
]
