"""
Document templates for Research Export Agent.

Provides template rendering functions for creating professionally formatted
Google Docs from niche and persona research data.

Templates:
- Niche Overview: Executive summary, market analysis, competitive landscape
- Persona Profiles: Detailed buyer personas with pain points and goals
- Pain Points Analysis: Consolidated pain points with evidence
- Messaging Angles: Value propositions and messaging strategies
"""

from datetime import datetime
from typing import Any


def _safe_get(data: dict[str, Any] | None, key: str, default: Any = "Not available") -> Any:
    """
    Safely get value from dictionary with default.

    Args:
        data: Dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found

    Returns:
        Value from dictionary or default
    """
    if data is None:
        return default
    return data.get(key, default)


def _format_list(items: list[Any] | None, separator: str = ", ") -> str:
    """
    Format list as comma-separated string.

    Args:
        items: List of items
        separator: Separator string

    Returns:
        Formatted string
    """
    if not items:
        return "Not specified"
    return separator.join(str(item) for item in items)


def _format_percentage(value: float | None) -> str:
    """
    Format decimal as percentage.

    Args:
        value: Decimal value (0-1)

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    return f"{int(value * 100)}%"


def render_niche_overview_doc(
    niche: dict[str, Any],
    scores: dict[str, Any],
    research_data: dict[str, Any],
) -> str:
    """
    Render Niche Overview document.

    Args:
        niche: Niche metadata from niches table
        scores: Scoring data from niche_scores table
        research_data: Research findings from niche_research_data table

    Returns:
        Formatted document content
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    niche_name = niche.get("name", "Unknown Niche")

    content = f"""# Niche Overview: {niche_name}

**Generated:** {timestamp}
**Status:** Pending Review

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Overall Score | {scores.get('overall_score', 'N/A')}/100 |
| Recommendation | {scores.get('recommendation', 'N/A').upper()} |
| Confidence | {_format_percentage(scores.get('confidence'))} |

---

## Target Market

**Industries:** {_format_list(niche.get('industry'))}

**Job Titles:** {_format_list(niche.get('job_titles'))}

**Company Size:** {_format_list(niche.get('company_size'))}

**Location:** {_format_list(niche.get('location'))}

---

## Market Size & Opportunity

| Metric | Estimate |
|--------|----------|
| Market Size | {_safe_get(research_data, 'market_size_estimate')} |
| Company Count | {_safe_get(research_data, 'company_count_estimate', 'Not available')} |
| Persona Count | {_safe_get(research_data, 'persona_count_estimate', 'Not available')} |
| Growth Rate | {_safe_get(research_data, 'growth_rate', 'Not available')} |

"""

    # Add market data sources if available
    if research_data.get("market_data_sources"):
        content += f"\n**Data Sources:**\n```\n{research_data['market_data_sources']}\n```\n"

    content += "\n---\n\n## Competitive Landscape\n\n"

    # Add competitors if available
    competitors = research_data.get("competitors_found", [])
    if competitors:
        content += "### Competitors Identified\n\n"
        for i, competitor in enumerate(competitors, 1):
            comp_name = competitor.get("name", f"Competitor {i}")
            comp_position = competitor.get("position", "Unknown")
            comp_strengths = competitor.get("strengths", "N/A")
            comp_weaknesses = competitor.get("weaknesses", "N/A")
            content += f"{i}. **{comp_name}**\n"
            content += f"   - Market Position: {comp_position}\n"
            content += f"   - Strengths: {comp_strengths}\n"
            content += f"   - Weaknesses: {comp_weaknesses}\n\n"

        content += f"\n### Saturation Level\n{_safe_get(research_data, 'saturation_level')}\n"
    else:
        content += "**No competitor data available**\n"

    content += "\n---\n\n## Differentiation Opportunities\n\n"

    # Add differentiation opportunities
    opportunities = research_data.get("differentiation_opportunities", [])
    if opportunities:
        for i, opp in enumerate(opportunities, 1):
            content += f"{i}. {opp}\n"
    else:
        content += "**No differentiation opportunities documented**\n"

    content += "\n---\n\n## Inbox Fatigue Indicators\n\n"

    # Add inbox fatigue indicators
    fatigue_indicators = research_data.get("inbox_fatigue_indicators", [])
    if fatigue_indicators:
        for indicator in fatigue_indicators:
            content += f"- {indicator}\n"
    else:
        content += "**No inbox fatigue data available**\n"

    content += "\n---\n\n## Scoring Breakdown\n\n"
    content += "| Dimension | Score | Weight |\n"
    content += "|-----------|-------|--------|\n"
    content += f"| Market Size | {scores.get('market_size_score', 'N/A')}/100 | 20% |\n"
    content += f"| Competition | {scores.get('competition_score', 'N/A')}/100 | 20% |\n"
    content += f"| Reachability | {scores.get('reachability_score', 'N/A')}/100 | 20% |\n"
    content += f"| Pain Intensity | {scores.get('pain_intensity_score', 'N/A')}/100 | 25% |\n"
    content += f"| Budget Authority | {scores.get('budget_authority_score', 'N/A')}/100 | 15% |\n"

    content += "\n---\n\n## Pain Points Identified\n\n"

    # Add pain points from niche
    pain_points = niche.get("pain_points", [])
    if pain_points:
        for i, pain in enumerate(pain_points, 1):
            if isinstance(pain, dict):
                pain_desc = pain.get("pain", pain.get("description", "Unknown"))
                intensity = pain.get("intensity", "N/A")
                quote = pain.get("quote", "No quote available")
                source = pain.get("source", "Unknown")
                content += f"{i}. **{pain_desc}**\n"
                content += f"   - Intensity: {intensity}/10\n"
                content += f'   - Quote: "{quote}"\n'
                content += f"   - Source: {source}\n\n"
            else:
                content += f"{i}. {pain}\n"
    else:
        content += "**No pain points documented**\n"

    content += "\n---\n\n## Value Propositions\n\n"

    # Add value propositions
    value_props = niche.get("value_propositions", [])
    if value_props:
        for prop in value_props:
            content += f"- {prop}\n"
    else:
        content += "**No value propositions documented**\n"

    content += f"\n---\n\n## Recommended Messaging Tone\n\n{niche.get('messaging_tone', 'Professional').capitalize()}\n"

    # Add scoring details if available
    scoring_details = scores.get("scoring_details")
    if scoring_details:
        content += "\n---\n\n## Scoring Details\n\n"
        content += f"```json\n{scoring_details}\n```\n"

    return content


def render_persona_profiles_doc(
    niche: dict[str, Any],
    personas: list[dict[str, Any]],
) -> str:
    """
    Render Persona Profiles document.

    Args:
        niche: Niche metadata
        personas: List of personas from personas table

    Returns:
        Formatted document content
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    niche_name = niche.get("name", "Unknown Niche")

    content = f"""# Buyer Personas: {niche_name}

**Generated:** {timestamp}
**Total Personas:** {len(personas)}

---

"""

    for i, persona in enumerate(personas, 1):
        persona_name = persona.get("name", f"Persona {i}")

        content += f"## Persona {i}: {persona_name}\n\n"

        # Identity section
        content += "### Identity\n\n"
        content += "| Attribute | Value |\n"
        content += "|-----------|-------|\n"
        content += f"| Job Titles | {_format_list(persona.get('job_titles'))} |\n"
        seniority = persona.get("seniority_level", "not_specified").replace("_", " ").title()
        content += f"| Seniority | {seniority} |\n"
        content += f"| Department | {persona.get('department', 'Not specified')} |\n\n"

        # Pain Points section
        content += "### Pain Points (Ranked by Intensity)\n\n"
        pain_points = persona.get("pain_points", [])
        if pain_points:
            # Sort by intensity if available
            sorted_pains = sorted(
                pain_points,
                key=lambda p: p.get("intensity", 0) if isinstance(p, dict) else 0,
                reverse=True,
            )

            for j, pain in enumerate(sorted_pains, 1):
                if isinstance(pain, dict):
                    pain_desc = pain.get("pain", pain.get("description", "Unknown"))
                    intensity = pain.get("intensity", "N/A")
                    quote = pain.get("quote", "No quote available")
                    source = pain.get("source", "Research")

                    content += f"**{j}. {pain_desc}** (Intensity: {intensity}/10)\n\n"
                    content += f'> "{quote}"\n'
                    content += f"> — Source: {source}\n\n"
                else:
                    content += f"{j}. {pain}\n\n"
        else:
            content += "No pain points documented\n\n"

        # Professional Goals section
        content += "### Professional Goals\n\n"
        goals = persona.get("goals", [])
        if goals:
            for goal in goals:
                content += f"- {goal}\n"
        else:
            content += "No goals documented\n"
        content += "\n"

        # Objections section
        content += "### Common Objections & Counters\n\n"
        objections = persona.get("objections", [])
        if objections:
            for objection in objections:
                if isinstance(objection, dict):
                    obj_text = objection.get("objection", "Unknown objection")
                    real_meaning = objection.get("real_meaning", "N/A")
                    counter = objection.get("counter", "N/A")

                    content += f'**Objection:** "{obj_text}"\n'
                    content += f"- **Real Meaning:** {real_meaning}\n"
                    content += f"- **Counter Approach:** {counter}\n\n"
                else:
                    content += f"- {objection}\n"
        else:
            content += "No objections documented\n"
        content += "\n"

        # Language Patterns section
        content += "### Language Patterns\n\n"
        content += "Phrases they use:\n"
        language_patterns = persona.get("language_patterns", [])
        if language_patterns:
            for pattern in language_patterns:
                content += f'- "{pattern}"\n'
        else:
            content += "- No language patterns documented\n"
        content += "\n"

        # Trigger Events section
        content += "### Trigger Events\n\n"
        content += "When they're most likely to buy:\n"
        trigger_events = persona.get("trigger_events", [])
        if trigger_events:
            for trigger in trigger_events:
                content += f"- {trigger}\n"
        else:
            content += "- No trigger events documented\n"
        content += "\n"

        # Messaging Angles section
        content += "### Messaging Angles\n\n"
        messaging_angles = persona.get("messaging_angles", {})
        if messaging_angles:
            # Primary angle
            primary = messaging_angles.get("primary", {})
            if primary:
                content += "**Primary Angle:**\n"
                content += f"- Angle: {primary.get('angle', 'N/A')}\n"
                content += f"- Hook: \"{primary.get('hook', 'N/A')}\"\n"
                if primary.get("supporting_pain"):
                    content += f"- Supporting Pain: {primary.get('supporting_pain')}\n"
                content += "\n"

            # Secondary angle
            secondary = messaging_angles.get("secondary", {})
            if secondary:
                content += "**Secondary Angle:**\n"
                content += f"- Angle: {secondary.get('angle', 'N/A')}\n"
                content += f"- Hook: \"{secondary.get('hook', 'N/A')}\"\n\n"

            # Angles to avoid
            avoid = messaging_angles.get("avoid", [])
            if avoid:
                content += "**Angles to Avoid:**\n"
                for angle in avoid:
                    content += f"- {angle}\n"
                content += "\n"
        else:
            content += "No messaging angles documented\n\n"

        content += "---\n\n"

    return content


def render_pain_points_doc(
    niche: dict[str, Any],
    consolidated_pain_points: list[str],
    niche_research_data: dict[str, Any],
    persona_research_data: list[dict[str, Any]],
    industry_scores: list[dict[str, Any]],
) -> str:
    """
    Render Pain Points Analysis document.

    Args:
        niche: Niche metadata
        consolidated_pain_points: Consolidated pain points from handoff
        niche_research_data: Research data from niche_research_data table
        persona_research_data: Research data from persona_research_data table
        industry_scores: Industry fit scores

    Returns:
        Formatted document content
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    niche_name = niche.get("name", "Unknown Niche")

    content = f"""# Pain Points Analysis: {niche_name}

**Generated:** {timestamp}
"""

    # Add overall pain metrics if available
    if niche_research_data.get("pain_intensity"):
        content += f"**Overall Pain Intensity:** {niche_research_data['pain_intensity']}\n"
    if niche_research_data.get("pain_urgency"):
        content += f"**Pain Urgency:** {niche_research_data['pain_urgency']}\n"

    content += "\n---\n\n## Consolidated Pain Points\n\n"

    if consolidated_pain_points:
        for i, pain in enumerate(consolidated_pain_points, 1):
            content += f"{i}. {pain}\n\n"
    else:
        content += "**No consolidated pain points available**\n"

    content += "\n---\n\n## Detailed Pain Points (from Niche Research)\n\n"

    # Add detailed pain points from niche research
    detailed_pains = niche_research_data.get("pain_points_detailed", [])
    if detailed_pains:
        for i, pain_detail in enumerate(detailed_pains, 1):
            if isinstance(pain_detail, dict):
                title = pain_detail.get("title", pain_detail.get("pain", f"Pain Point {i}"))
                description = pain_detail.get("description", "N/A")
                frequency = pain_detail.get("frequency", "N/A")
                intensity = pain_detail.get("intensity", "N/A")

                content += f"### {i}. {title}\n\n"
                content += f"**Description:** {description}\n\n"
                content += f"**Frequency:** {frequency}\n\n"
                content += f"**Intensity:** {intensity}\n\n"
            else:
                content += f"{i}. {pain_detail}\n\n"
    else:
        content += "*No detailed pain points available from niche research*\n"

    content += "\n---\n\n## Pain Point Quotes by Source\n\n"

    # Quotes from Niche Research
    content += "### From Niche Research (Market Intelligence)\n\n"
    niche_quotes = niche_research_data.get("pain_point_quotes", [])
    if niche_quotes:
        for quote_data in niche_quotes:
            if isinstance(quote_data, dict):
                quote_text = quote_data.get("quote", quote_data.get("content", ""))
                source = quote_data.get("source", "Market Research")
                context = quote_data.get("context")

                content += f'> "{quote_text}"\n'
                content += f"> — {source}\n"
                if context:
                    content += f"> *Context:* {context}\n"
                content += "\n"
            else:
                content += f'> "{quote_data}"\n\n'
    else:
        content += "*No quotes available from niche research*\n"

    # Quotes from Persona Research - Reddit
    content += "\n### From Persona Research - Reddit\n\n"
    reddit_quotes = [
        p
        for p in persona_research_data
        if p.get("content_type") == "reddit" or p.get("research_type") == "reddit"
    ]
    if reddit_quotes:
        for quote_data in reddit_quotes[:5]:  # Limit to 5 quotes
            quotes = quote_data.get("pain_point_quotes", [])
            source_url = quote_data.get("source_url", "Reddit")
            if quotes:
                content += f'> "{quotes[0]}"\n'
                content += f"> — {source_url}\n\n"
    else:
        content += "*No Reddit quotes available*\n"

    # Quotes from LinkedIn & Professional Sources
    content += "\n### From Persona Research - LinkedIn & Professional Sources\n\n"
    linkedin_quotes = [
        p
        for p in persona_research_data
        if p.get("content_type") == "linkedin" or p.get("research_type") == "linkedin"
    ]
    if linkedin_quotes:
        for quote_data in linkedin_quotes[:5]:  # Limit to 5 quotes
            quotes = quote_data.get("pain_point_quotes", [])
            source_url = quote_data.get("source_url", "LinkedIn")
            if quotes:
                content += f'> "{quotes[0]}"\n'
                content += f"> — {source_url}\n\n"
    else:
        content += "*No LinkedIn quotes available*\n"

    # Industry Reports & Articles
    content += "\n### From Persona Research - Industry Reports & Articles\n\n"
    article_quotes = [
        p
        for p in persona_research_data
        if p.get("content_type") == "article" or p.get("research_type") == "article"
    ]
    if article_quotes:
        for quote_data in article_quotes[:5]:  # Limit to 5 quotes
            quotes = quote_data.get("pain_point_quotes", [])
            source_url = quote_data.get("source_url", "Industry Article")
            if quotes:
                content += f'> "{quotes[0]}"\n'
                content += f"> — {source_url}\n\n"
    else:
        content += "*No article quotes available*\n"

    content += "\n---\n\n## Evidence Sources\n\n"

    # Add evidence sources
    evidence_sources = niche_research_data.get("evidence_sources", [])
    if evidence_sources:
        for source in evidence_sources:
            if isinstance(source, dict):
                source_type = source.get("type", "Source")
                source_url = source.get("url", source.get("name", "N/A"))
                content += f"- {source_type}: {source_url}\n"
            else:
                content += f"- {source}\n"
    else:
        content += "*No evidence sources documented*\n"

    content += "\n---\n\n## Budget Authority & Decision Process\n\n"

    # Add budget and decision info
    has_budget = niche_research_data.get("has_budget_authority")
    if has_budget is not None:
        content += f"**Has Budget Authority:** {has_budget}\n\n"

    budget_range = niche_research_data.get("typical_budget_range")
    if budget_range:
        content += f"**Typical Budget Range:** {budget_range}\n\n"

    decision_process = niche_research_data.get("decision_process")
    if decision_process:
        content += f"**Decision Process:** {decision_process}\n\n"

    content += "---\n\n## Buying Triggers\n\n"

    # Add buying triggers
    buying_triggers = niche_research_data.get("buying_triggers", [])
    if buying_triggers:
        for i, trigger in enumerate(buying_triggers, 1):
            content += f"{i}. {trigger}\n"
    else:
        content += "*No buying triggers documented*\n"

    content += "\n---\n\n## Industry Fit Scores\n\n"

    # Add industry fit scores
    if industry_scores:
        content += "| Industry | Fit Score | Reasoning |\n"
        content += "|----------|-----------|-----------||\n"
        for score in industry_scores:
            industry = score.get("industry", "Unknown")
            fit_score = score.get("fit_score", "N/A")
            reasoning = score.get("reasoning", "N/A")
            content += f"| {industry} | {fit_score}/100 | {reasoning} |\n"
    else:
        content += "*No industry fit scores available*\n"

    return content


def render_messaging_angles_doc(
    niche: dict[str, Any],
    personas: list[dict[str, Any]],
    niche_research_data: dict[str, Any],
) -> str:
    """
    Render Messaging Angles document.

    Args:
        niche: Niche metadata
        personas: List of personas
        niche_research_data: Research data

    Returns:
        Formatted document content
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    niche_name = niche.get("name", "Unknown Niche")
    messaging_tone = niche.get("messaging_tone", "Professional").capitalize()

    content = f"""# Messaging Angles: {niche_name}

**Generated:** {timestamp}
**Recommended Tone:** {messaging_tone}

---

## Value Propositions

"""

    # Add value propositions
    value_props = niche.get("value_propositions", [])
    if value_props:
        for i, prop in enumerate(value_props, 1):
            content += f"{i}. {prop}\n"
    else:
        content += "*No value propositions documented*\n"

    content += "\n---\n\n## Differentiation Opportunities\n\n"

    # Add differentiation opportunities from research
    opportunities = niche_research_data.get("differentiation_opportunities", [])
    if opportunities:
        content += "Based on market research, here are proven differentiation angles:\n\n"
        for i, opp in enumerate(opportunities, 1):
            content += f"{i}. {opp}\n"
    else:
        content += "*No differentiation opportunities documented*\n"

    content += "\n---\n\n## Messaging by Persona\n\n"

    # Add messaging for each persona
    for persona in personas:
        persona_name = persona.get("name", "Unknown Persona")
        content += f"### {persona_name}\n\n"

        messaging_angles = persona.get("messaging_angles", {})

        if messaging_angles:
            # Primary approach
            primary = messaging_angles.get("primary", {})
            if primary:
                content += "**Primary Approach:**\n"
                content += f"- **Angle:** {primary.get('angle', 'N/A')}\n"
                content += f"- **Hook:** \"{primary.get('hook', 'N/A')}\"\n"
                if primary.get("supporting_pain"):
                    content += f"- **Supporting Pain:** {primary.get('supporting_pain')}\n"
                content += "\n"

            # Secondary approach
            secondary = messaging_angles.get("secondary", {})
            if secondary:
                content += "**Secondary Approach:**\n"
                content += f"- **Angle:** {secondary.get('angle', 'N/A')}\n"
                content += f"- **Hook:** \"{secondary.get('hook', 'N/A')}\"\n\n"

            # Do NOT use
            avoid = messaging_angles.get("avoid", [])
            if avoid:
                content += "**Do NOT Use:**\n"
                for angle in avoid:
                    content += f"- {angle}\n"
                content += "\n"
        else:
            content += "No messaging angles documented for this persona.\n\n"

        content += "---\n\n"

    content += "## Language to Use\n\n"
    content += "### Power Phrases (from their own words)\n\n"

    # Collect language patterns from all personas
    all_patterns = []
    for persona in personas:
        patterns = persona.get("language_patterns", [])
        all_patterns.extend(patterns[:5])  # Take top 5 from each

    if all_patterns:
        for pattern in all_patterns:
            content += f'- "{pattern}"\n'
    else:
        content += "- No language patterns documented\n"

    content += "\n### Words/Phrases to Avoid\n\n"
    content += "- Generic corporate speak\n"
    content += '- "Revolutionary" or "game-changing"\n'
    content += "- Anything that sounds like a sales pitch\n"
    content += "- Assumptions about their problems\n"

    return content
