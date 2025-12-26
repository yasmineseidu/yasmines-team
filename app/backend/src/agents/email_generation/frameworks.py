"""
Email Frameworks - Templates and structure for different email formats.

Provides framework-specific prompts and guidance for generating
cold emails using PAS, BAB, AIDA, and Question-based approaches.
"""

from dataclasses import dataclass
from typing import Any

from src.agents.email_generation.schemas import EmailFramework


@dataclass
class FrameworkTemplate:
    """Template for an email framework."""

    name: str
    framework: EmailFramework
    structure: list[str]
    description: str
    example_structure: str
    best_for: list[str]


# =============================================================================
# Framework Definitions
# =============================================================================


PAS_TEMPLATE = FrameworkTemplate(
    name="Pain-Agitate-Solution",
    framework=EmailFramework.PAS,
    structure=["personalization_hook", "pain", "agitate", "solution", "cta"],
    description="Identifies a pain point, amplifies its consequences, then offers a solution.",
    example_structure="""
Opening: [Personalized hook referencing their work/content]
Pain: [Identify a specific pain point they likely face]
Agitate: [Amplify the consequences of not solving this]
Solution: [Brief intro to how you can help]
CTA: [Soft, low-friction question]
""",
    best_for=["high_pain_intensity", "tier_a", "complex_problems"],
)


BAB_TEMPLATE = FrameworkTemplate(
    name="Before-After-Bridge",
    framework=EmailFramework.BAB,
    structure=["personalization_hook", "before", "after", "bridge", "cta"],
    description="Paints the current state, shows the desired future, then bridges the gap.",
    example_structure="""
Opening: [Personalized hook]
Before: [Their current challenging situation]
After: [The ideal state they want to achieve]
Bridge: [How you can help them get there]
CTA: [Soft, low-friction question]
""",
    best_for=["aspirational_messaging", "tier_b", "transformation_focused"],
)


AIDA_TEMPLATE = FrameworkTemplate(
    name="Attention-Interest-Desire-Action",
    framework=EmailFramework.AIDA,
    structure=["attention", "interest", "desire", "action"],
    description="Grabs attention, builds interest, creates desire, calls to action.",
    example_structure="""
Attention: [Hook that grabs attention]
Interest: [Relevant insight that builds curiosity]
Desire: [Benefit that creates want]
Action: [Clear, soft CTA]
""",
    best_for=["shorter_emails", "tier_c", "direct_approach"],
)


QUESTION_TEMPLATE = FrameworkTemplate(
    name="Question-Based",
    framework=EmailFramework.QUESTION,
    structure=["personalized_question", "context", "value", "cta"],
    description="Opens with a question to engage, then provides context and value.",
    example_structure="""
Question: [Personalized question that resonates]
Context: [Why you're asking / relevance]
Value: [Brief value proposition]
CTA: [Soft question to continue conversation]
""",
    best_for=["engagement_focused", "curious_recipients", "conversational"],
)


# Framework lookup
FRAMEWORK_TEMPLATES: dict[EmailFramework, FrameworkTemplate] = {
    EmailFramework.PAS: PAS_TEMPLATE,
    EmailFramework.BAB: BAB_TEMPLATE,
    EmailFramework.AIDA: AIDA_TEMPLATE,
    EmailFramework.QUESTION: QUESTION_TEMPLATE,
}


def get_framework_template(framework: EmailFramework) -> FrameworkTemplate:
    """Get the template for a framework."""
    return FRAMEWORK_TEMPLATES[framework]


# =============================================================================
# Avoid Patterns - Common mistakes to avoid
# =============================================================================


AVOID_PATTERNS: list[str] = [
    "I hope this email finds you well",
    "I hope this message finds you well",
    "I'd love to pick your brain",
    "As a [title], you probably",
    "My name is",  # Don't start with this
    "I came across your profile",
    "I noticed you work at",
    "I saw that you",
    "I'm reaching out because",
    "I wanted to reach out",
    "Just following up",
    "Per my last email",
    "touching base",
    "circle back",
    "synergy",
    "leverage",
    "deep dive",
]


EXCESSIVE_FLATTERY_PATTERNS: list[str] = [
    "impressive",
    "amazing work",
    "big fan",
    "love your",
    "incredible",
    "outstanding",
]


# =============================================================================
# CTA Examples by Softness
# =============================================================================


SOFT_CTAS: list[str] = [
    "Would you be open to a quick chat?",
    "Worth a 15-minute call?",
    "Is this something you're exploring?",
    "Would it make sense to connect?",
    "Curious if this resonates?",
    "Does this hit home at all?",
    "Any interest in learning more?",
    "Mind if I share a few ideas?",
]


# =============================================================================
# Generation Prompt Builder
# =============================================================================


def build_generation_prompt(
    framework: EmailFramework,
    lead_context: dict[str, Any],
    persona_context: dict[str, Any],
    niche_context: dict[str, Any],
    lead_research: dict[str, Any] | None = None,
    company_research: dict[str, Any] | None = None,
    proven_lines: list[str] | None = None,
    max_words: int = 150,
    personalization_level: str = "personalized",
) -> str:
    """
    Build the generation prompt for the LLM.

    Args:
        framework: Email framework to use.
        lead_context: Lead information.
        persona_context: Persona messaging context.
        niche_context: Niche pain points and value props.
        lead_research: Optional lead research data.
        company_research: Optional company research data.
        proven_lines: Optional list of proven opening lines.
        max_words: Maximum word count for body.
        personalization_level: Level of personalization.

    Returns:
        Complete prompt for email generation.
    """
    template = get_framework_template(framework)

    # Build lead info section
    lead_info = f"""## Lead Information
- Name: {lead_context.get("first_name", "")} {lead_context.get("last_name", "")}
- Title: {lead_context.get("title", "Unknown")}
- Company: {lead_context.get("company_name", "Unknown")}
- Tier: {lead_context.get("lead_tier", "C")}"""

    # Build research section
    research_section = ""
    if lead_research:
        research_section += f"""
## Lead Research
- Headline: {lead_research.get("headline", "N/A")}
- Key Interests: {", ".join(lead_research.get("key_interests", [])[:3])}
- Recent Activity: {lead_research.get("recent_posts", "N/A")[:200] if lead_research.get("recent_posts") else "N/A"}"""

    if company_research:
        research_section += f"""
## Company Research
- Summary: {company_research.get("summary", "N/A")[:200]}
- Personalization Angle: {company_research.get("personalization_angle", "N/A")}"""

    # Build persona section
    persona_section = f"""
## Persona Context
- Pain Points: {", ".join(persona_context.get("challenges", [])[:3])}
- Goals: {", ".join(persona_context.get("goals", [])[:3])}
- Messaging Tone: {persona_context.get("messaging_tone", "professional")}"""

    # Build proven lines section
    proven_section = ""
    if proven_lines:
        proven_section = f"""
## Proven Opening Lines (for inspiration)
{chr(10).join(f'- "{line}"' for line in proven_lines[:5])}"""

    # Build avoid patterns section
    avoid_section = f"""
## Patterns to AVOID
- {chr(10).join(f'"{p}"' for p in AVOID_PATTERNS[:5])}
- Excessive flattery
- Long paragraphs
- Starting with "My name is..."
- Multiple CTAs"""

    # Framework guidance
    framework_section = f"""
## Framework: {template.name}
{template.description}

Structure to follow:
{template.example_structure}"""

    # Output requirements
    output_section = f"""
## Requirements
- Use {template.name} framework structure
- Personalization level: {personalization_level}
- Maximum {max_words} words for body
- Tone: {persona_context.get("messaging_tone", "conversational but professional")}
- CTA: Soft, low-friction question (see examples below)

## Soft CTA Examples
{chr(10).join(f'- "{cta}"' for cta in SOFT_CTAS[:4])}

## Output Format (JSON)
Return ONLY valid JSON with no markdown:
{{
  "subject_line": "Short, personalized subject (max 50 chars)",
  "opening_line": "Personalized hook that grabs attention",
  "body": "Main email body following {template.name} structure",
  "cta": "Soft, low-friction closing question",
  "full_email": "Complete email combining opening, body, and CTA"
}}"""

    # Combine all sections
    prompt = f"""You are an expert cold email copywriter specializing in B2B outreach.
Generate a personalized cold email that sounds human, not like AI.

{lead_info}
{research_section}
{persona_section}
{proven_section}
{framework_section}
{avoid_section}
{output_section}

Write the email now. Be specific, not generic. Focus on THEIR problems."""

    return prompt


def select_framework_for_tier(tier: str, variation: int = 0) -> EmailFramework:
    """
    Select the best framework for a lead tier.

    Args:
        tier: Lead tier (A, B, C).
        variation: Index for variation (0 or 1).

    Returns:
        Selected framework.
    """
    tier_frameworks = {
        "A": [EmailFramework.PAS, EmailFramework.BAB],
        "B": [EmailFramework.BAB, EmailFramework.AIDA],
        "C": [EmailFramework.AIDA, EmailFramework.QUESTION],
    }
    frameworks = tier_frameworks.get(tier, tier_frameworks["C"])
    return frameworks[variation % len(frameworks)]
