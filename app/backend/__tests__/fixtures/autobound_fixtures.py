"""
Test fixtures for Autobound integration tests.

Contains sample data for testing all Autobound API endpoints:
- Content generation (email, call script, LinkedIn, SMS, custom)
- Insights generation
- Various writing styles and models

These fixtures use real-world-like data for comprehensive testing.
"""

from typing import Any

# =============================================================================
# TEST CONTACTS - Real companies/executives for best personalization results
# =============================================================================

# Primary test contacts - well-known executives with public data
TEST_CONTACTS = {
    "tech_ceo": {
        "email": "satya.nadella@microsoft.com",
        "name": "Satya Nadella",
        "company": "Microsoft",
        "title": "CEO",
    },
    "tech_founder": {
        "email": "brian.chesky@airbnb.com",
        "name": "Brian Chesky",
        "company": "Airbnb",
        "title": "CEO & Co-Founder",
    },
    "sales_leader": {
        "email": "marc.benioff@salesforce.com",
        "name": "Marc Benioff",
        "company": "Salesforce",
        "title": "CEO",
    },
    "startup_founder": {
        "email": "elon@tesla.com",
        "name": "Elon Musk",
        "company": "Tesla",
        "title": "CEO",
    },
    "finance_exec": {
        "email": "jamie.dimon@jpmorgan.com",
        "name": "Jamie Dimon",
        "company": "JPMorgan Chase",
        "title": "CEO",
    },
}

# Test sender emails
TEST_SENDERS = {
    "sales_rep": "sales.rep@acme-solutions.com",
    "account_exec": "account.executive@techstartup.io",
    "bdr": "bdr@growth-company.com",
    "founder": "founder@my-startup.com",
}

# Fallback test contact (generic but works)
DEFAULT_TEST_CONTACT = TEST_CONTACTS["tech_ceo"]["email"]
DEFAULT_TEST_SENDER = TEST_SENDERS["sales_rep"]


# =============================================================================
# CONTENT TYPE CONFIGURATIONS
# =============================================================================

CONTENT_TYPES = {
    "email": {
        "type": "email",
        "description": "Personalized cold email",
        "typical_word_count": 100,
    },
    "email_sequence": {
        "type": "email sequence",
        "description": "Multi-email sequence",
        "typical_word_count": 300,
    },
    "call_script": {
        "type": "call script",
        "description": "Phone call talking points",
        "typical_word_count": 200,
    },
    "linkedin": {
        "type": "LinkedIn connection request",
        "description": "LinkedIn connection message",
        "typical_word_count": 50,
    },
    "sms": {
        "type": "SMS",
        "description": "Short text message",
        "typical_word_count": 30,
    },
    "opener": {
        "type": "opener",
        "description": "Conversation opener",
        "typical_word_count": 25,
    },
    "custom": {
        "type": "custom",
        "description": "Custom content type",
        "typical_word_count": 150,
    },
}


# =============================================================================
# WRITING STYLES
# =============================================================================

WRITING_STYLES = {
    "cxo_pitch": {
        "style": "cxo_pitch",
        "description": "Executive-level, strategic pitch",
        "best_for": ["CEOs", "C-Suite", "VPs"],
    },
    "friendly": {
        "style": "friendly",
        "description": "Warm, approachable tone",
        "best_for": ["Peers", "SMB owners", "Startup founders"],
    },
    "professional": {
        "style": "professional",
        "description": "Business professional tone",
        "best_for": ["Enterprise", "Corporate", "Finance"],
    },
    "casual": {
        "style": "casual",
        "description": "Relaxed, conversational tone",
        "best_for": ["Tech startups", "Creative industries"],
    },
    "formal": {
        "style": "formal",
        "description": "Highly formal, traditional tone",
        "best_for": ["Legal", "Government", "Traditional industries"],
    },
}


# =============================================================================
# AI MODELS
# =============================================================================

AI_MODELS = {
    "gpt4o": {
        "model": "gpt4o",
        "description": "GPT-4 Omni - Best quality",
        "speed": "medium",
    },
    "gpt4": {
        "model": "gpt4",
        "description": "GPT-4 - High quality",
        "speed": "slow",
    },
    "sonnet": {
        "model": "sonnet",
        "description": "Claude Sonnet - Fast & good",
        "speed": "fast",
    },
    "opus": {
        "model": "opus",
        "description": "Claude Opus - Highest quality",
        "speed": "slow",
    },
    "fine_tuned": {
        "model": "fine_tuned",
        "description": "Autobound fine-tuned model",
        "speed": "fast",
    },
}


# =============================================================================
# CUSTOM PROMPTS FOR TESTING
# =============================================================================

CUSTOM_PROMPTS = {
    "pain_point_analysis": {
        "prompt": "Write a 3-bullet pain point analysis for this prospect based on their company and role",
        "expected_format": "bullet points",
    },
    "value_proposition": {
        "prompt": "Create a compelling value proposition statement tailored to this prospect's industry",
        "expected_format": "paragraph",
    },
    "meeting_agenda": {
        "prompt": "Draft a meeting agenda for a 30-minute discovery call with this prospect",
        "expected_format": "numbered list",
    },
    "objection_handling": {
        "prompt": "List 3 potential objections this prospect might have and responses to each",
        "expected_format": "Q&A format",
    },
    "case_study_match": {
        "prompt": "Suggest which customer success story would resonate most with this prospect and why",
        "expected_format": "recommendation",
    },
}


# =============================================================================
# INSIGHT TYPES
# =============================================================================

INSIGHT_TYPES = [
    "news",
    "social_media",
    "job_posts",
    "tech_stack",
    "financial",
    "podcast",
    "shared_connections",
    "company_info",
    "press_releases",
    "awards",
]


# =============================================================================
# EXPECTED API RESPONSES (for validation)
# =============================================================================


def get_expected_content_response() -> dict[str, Any]:
    """Get expected structure for content generation response."""
    return {
        "content": str,  # The generated content
        "model": str,  # Model used (optional)
        "insightsUsed": list,  # Insights used (optional)
    }


def get_expected_insights_response() -> dict[str, Any]:
    """Get expected structure for insights generation response."""
    return {
        "insights": list,  # List of insight objects
    }


def get_expected_insight_structure() -> dict[str, Any]:
    """Get expected structure for a single insight."""
    return {
        "type": str,  # Insight type
        "title": str,  # Insight title
        "description": str,  # Insight description
        "relevanceScore": float,  # 0.0 to 1.0 (optional)
        "source": str,  # Source of insight (optional)
        "date": str,  # Date of insight (optional)
    }


# =============================================================================
# TEST SCENARIOS
# =============================================================================

TEST_SCENARIOS = {
    "basic_email": {
        "description": "Generate a basic cold email",
        "contact": DEFAULT_TEST_CONTACT,
        "sender": DEFAULT_TEST_SENDER,
        "content_type": "email",
    },
    "executive_pitch": {
        "description": "C-level executive pitch email",
        "contact": TEST_CONTACTS["tech_ceo"]["email"],
        "sender": TEST_SENDERS["founder"],
        "content_type": "email",
        "writing_style": "cxo_pitch",
    },
    "linkedin_outreach": {
        "description": "LinkedIn connection request",
        "contact": TEST_CONTACTS["startup_founder"]["email"],
        "sender": TEST_SENDERS["bdr"],
        "content_type": "LinkedIn connection request",
    },
    "discovery_call": {
        "description": "Call script for discovery call",
        "contact": TEST_CONTACTS["sales_leader"]["email"],
        "sender": TEST_SENDERS["account_exec"],
        "content_type": "call script",
    },
    "custom_analysis": {
        "description": "Custom pain point analysis",
        "contact": TEST_CONTACTS["finance_exec"]["email"],
        "sender": TEST_SENDERS["sales_rep"],
        "content_type": "custom",
        "custom_prompt": CUSTOM_PROMPTS["pain_point_analysis"]["prompt"],
    },
    "friendly_email": {
        "description": "Friendly, warm outreach email",
        "contact": TEST_CONTACTS["startup_founder"]["email"],
        "sender": TEST_SENDERS["bdr"],
        "content_type": "email",
        "writing_style": "friendly",
    },
    "professional_email": {
        "description": "Professional formal email",
        "contact": TEST_CONTACTS["sales_leader"]["email"],
        "sender": TEST_SENDERS["account_exec"],
        "content_type": "email",
        "writing_style": "professional",
    },
    "sms_message": {
        "description": "Short SMS message",
        "contact": TEST_CONTACTS["tech_ceo"]["email"],
        "sender": TEST_SENDERS["sales_rep"],
        "content_type": "SMS",
    },
    "email_sequence": {
        "description": "Multi-email outreach sequence",
        "contact": TEST_CONTACTS["tech_ceo"]["email"],
        "sender": TEST_SENDERS["founder"],
        "content_type": "email sequence",
    },
    "insights_research": {
        "description": "Research insights on prospect",
        "contact": DEFAULT_TEST_CONTACT,
        "max_insights": 10,
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_test_contact(contact_type: str = "tech_ceo") -> dict[str, str]:
    """Get a test contact by type."""
    return TEST_CONTACTS.get(contact_type, TEST_CONTACTS["tech_ceo"])


def get_test_sender(sender_type: str = "sales_rep") -> str:
    """Get a test sender email by type."""
    return TEST_SENDERS.get(sender_type, TEST_SENDERS["sales_rep"])


def validate_content_response(response: dict[str, Any]) -> bool:
    """Validate that a content response has expected structure."""
    # Content must exist and be non-empty
    if "content" not in response:
        return False
    content = response.get("content", "")
    if isinstance(content, dict):
        content = content.get("content", "")
    return bool(content and len(str(content).strip()) > 0)


def validate_insights_response(response: dict[str, Any]) -> bool:
    """Validate that an insights response has expected structure."""
    return "insights" in response and isinstance(response["insights"], list)
