"""
Test fixtures for Company Research Agent.

Provides sample data, mock responses, and test utilities for unit and
integration testing of the Company Research Agent.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

# =============================================================================
# Sample UUIDs for testing
# =============================================================================

SAMPLE_CAMPAIGN_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_LEAD_ID = UUID("22222222-2222-2222-2222-222222222222")
SAMPLE_RESEARCH_ID = UUID("33333333-3333-3333-3333-333333333333")


# =============================================================================
# Sample Companies
# =============================================================================

SAMPLE_COMPANIES = [
    {
        "lead_id": uuid4(),
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "company_linkedin_url": "https://linkedin.com/company/acme",
        "company_industry": "Technology",
        "company_size": "51-200",
        "lead_count": 5,
        "max_lead_score": 85,
    },
    {
        "lead_id": uuid4(),
        "company_name": "TechStart Inc",
        "company_domain": "techstart.io",
        "company_linkedin_url": "https://linkedin.com/company/techstart",
        "company_industry": "Software",
        "company_size": "11-50",
        "lead_count": 3,
        "max_lead_score": 72,
    },
    {
        "lead_id": uuid4(),
        "company_name": "BigCo Industries",
        "company_domain": "bigco.com",
        "company_linkedin_url": None,
        "company_industry": "Manufacturing",
        "company_size": "1001-5000",
        "lead_count": 10,
        "max_lead_score": 65,
    },
]


# =============================================================================
# Sample Search Results
# =============================================================================

SAMPLE_NEWS_RESULTS = [
    {
        "title": "Acme Corp Announces $50M Series C Funding",
        "snippet": "Acme Corp has raised $50 million in Series C funding led by Sequoia Capital.",
        "url": "https://techcrunch.com/acme-series-c",
        "date": (datetime.now(UTC) - timedelta(days=15)).strftime("%Y-%m-%d"),
        "source": "TechCrunch",
    },
    {
        "title": "Acme Corp Launches AI-Powered Analytics Platform",
        "snippet": "The new platform uses machine learning to provide real-time insights.",
        "url": "https://venturebeat.com/acme-ai-platform",
        "date": (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d"),
        "source": "VentureBeat",
    },
    {
        "title": "Acme Corp Expands to European Market",
        "snippet": "The company opened new offices in London and Berlin.",
        "url": "https://businesswire.com/acme-europe",
        "date": (datetime.now(UTC) - timedelta(days=45)).strftime("%Y-%m-%d"),
        "source": "BusinessWire",
    },
]

SAMPLE_FUNDING_RESULTS = [
    {
        "title": "Acme Corp - Crunchbase Funding History",
        "snippet": "Acme Corp has raised a total of $75M across 3 funding rounds.",
        "url": "https://crunchbase.com/organization/acme",
        "position": 1,
    },
    {
        "title": "Acme Series C: What It Means for the Industry",
        "snippet": "Analysts weigh in on the implications of Acme's latest raise.",
        "url": "https://forbes.com/acme-series-c-analysis",
        "position": 2,
    },
]

SAMPLE_HIRING_RESULTS = [
    {
        "title": "Acme Corp Careers - Open Positions",
        "snippet": "We're hiring engineers, product managers, and sales representatives.",
        "url": "https://acme.com/careers",
        "position": 1,
    },
    {
        "title": "Acme Corp Jobs on LinkedIn",
        "snippet": "25 open positions at Acme Corp including Senior Engineer and VP Sales.",
        "url": "https://linkedin.com/company/acme/jobs",
        "position": 2,
    },
]

SAMPLE_TECH_RESULTS = [
    {
        "title": "Acme Launches New API Developer Platform",
        "snippet": "Developers can now integrate Acme's services via a new REST API.",
        "url": "https://acme.com/blog/api-launch",
        "position": 1,
    },
    {
        "title": "Acme Partners with AWS for Cloud Infrastructure",
        "snippet": "Strategic partnership to enhance cloud capabilities.",
        "url": "https://aws.amazon.com/partners/acme",
        "position": 2,
    },
]


# =============================================================================
# Mock Tool Responses
# =============================================================================

MOCK_NEWS_SEARCH_RESPONSE = {
    "content": [{"type": "text", "text": "Found 3 news articles for Acme Corp"}],
    "data": {
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "query": "Acme Corp news 2025",
        "results": SAMPLE_NEWS_RESULTS,
        "result_count": 3,
        "tool_used": "serper_search",
        "cost": 0.001,
        "processing_time_ms": 150,
    },
}

MOCK_FUNDING_SEARCH_RESPONSE = {
    "content": [{"type": "text", "text": "Found 2 funding-related results for Acme Corp"}],
    "data": {
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "query": "Acme Corp funding investment growth",
        "results": SAMPLE_FUNDING_RESULTS,
        "result_count": 2,
        "tool_used": "serper_search",
        "cost": 0.001,
        "processing_time_ms": 120,
    },
}

MOCK_HIRING_SEARCH_RESPONSE = {
    "content": [{"type": "text", "text": "Found 2 hiring-related results for Acme Corp"}],
    "data": {
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "query": "Acme Corp hiring careers jobs",
        "results": SAMPLE_HIRING_RESULTS,
        "result_count": 2,
        "tool_used": "serper_search",
        "cost": 0.001,
        "processing_time_ms": 110,
    },
}

MOCK_TECH_SEARCH_RESPONSE = {
    "content": [{"type": "text", "text": "Found 2 tech-related results for Acme Corp"}],
    "data": {
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "query": "Acme Corp product launch technology",
        "results": SAMPLE_TECH_RESULTS,
        "result_count": 2,
        "tool_used": "serper_search",
        "cost": 0.001,
        "processing_time_ms": 130,
    },
}

MOCK_ERROR_RESPONSE = {
    "content": [{"type": "text", "text": "Search error: API rate limit exceeded"}],
    "is_error": True,
}


# =============================================================================
# Sample Extracted Facts
# =============================================================================

SAMPLE_EXTRACTED_FACTS = [
    {
        "fact_text": "Acme Corp raised $50 million in Series C funding led by Sequoia Capital.",
        "category": "funding",
        "source_type": "news",
        "source_url": "https://techcrunch.com/acme-series-c",
        "fact_date": (datetime.now(UTC) - timedelta(days=15)).isoformat(),
        "recency_days": 15,
        "recency_score": 0.833,
        "specificity_score": 0.9,
        "business_relevance_score": 0.8,
        "emotional_hook_score": 0.7,
        "total_score": 0.815,
    },
    {
        "fact_text": "Acme Corp is hiring 25 new positions including Senior Engineer and VP Sales.",
        "category": "hiring",
        "source_type": "web_search",
        "source_url": "https://linkedin.com/company/acme/jobs",
        "fact_date": None,
        "recency_days": None,
        "recency_score": 0.5,
        "specificity_score": 0.8,
        "business_relevance_score": 0.7,
        "emotional_hook_score": 0.5,
        "total_score": 0.625,
    },
    {
        "fact_text": "Acme Corp launched a new AI-powered analytics platform.",
        "category": "product",
        "source_type": "news",
        "source_url": "https://venturebeat.com/acme-ai-platform",
        "fact_date": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
        "recency_days": 30,
        "recency_score": 0.667,
        "specificity_score": 0.6,
        "business_relevance_score": 0.8,
        "emotional_hook_score": 0.6,
        "total_score": 0.665,
    },
]


# =============================================================================
# Sample Research Results
# =============================================================================

SAMPLE_RESEARCH_RESULT = {
    "company_domain": "acme.com",
    "company_name": "Acme Corp",
    "headline": "Acme Corp raised $50 million in Series C funding led by Sequoia Capital.",
    "summary": "Acme Corp raised $50M Series C | Hiring 25 new positions | Launched AI platform",
    "primary_hook": "Acme Corp raised $50 million in Series C funding led by Sequoia Capital.",
    "relevance_score": 0.815,
    "has_recent_news": True,
    "has_funding": True,
    "has_hiring": True,
    "has_product_launch": True,
    "facts": SAMPLE_EXTRACTED_FACTS,
    "fact_count": 3,
    "personalization_hooks": {
        "news": ["Acme Corp Announces $50M Series C Funding"],
        "funding": ["Acme Corp raised $50 million in Series C"],
        "hiring": ["25 open positions at Acme Corp"],
        "product": ["Acme Launches New API Developer Platform"],
    },
    "source_urls": [
        "https://techcrunch.com/acme-series-c",
        "https://venturebeat.com/acme-ai-platform",
        "https://acme.com/careers",
    ],
    "total_cost": 0.004,
    "cost_by_tool": {"serper_search": 0.004},
    "tools_used": ["serper_search"],
    "processing_time_ms": 510,
}


# =============================================================================
# Sample Agent Output
# =============================================================================

SAMPLE_AGENT_OUTPUT = {
    "campaign_id": str(SAMPLE_CAMPAIGN_ID),
    "total_companies": 100,
    "companies_researched": 95,
    "companies_failed": 5,
    "facts_extracted": 285,
    "hooks_generated": 380,
    "personalization_hooks": {
        "funding": 45,
        "hiring": 80,
        "news": 120,
        "product": 50,
    },
    "research_cost": 0.40,
    "cost_by_tool": {
        "serper_search": 0.38,
        "perplexity_search": 0.02,
    },
    "avg_fact_score": 0.65,
    "avg_relevance_score": 0.72,
    "circuit_breaker_trips": 0,
    "success": True,
    "duration_seconds": 45.5,
}


# =============================================================================
# Test Utilities
# =============================================================================


def create_mock_lead(
    campaign_id: UUID = SAMPLE_CAMPAIGN_ID,
    company_name: str = "Test Company",
    company_domain: str = "test.com",
) -> dict:
    """Create a mock lead dictionary for testing."""
    return {
        "id": uuid4(),
        "campaign_id": campaign_id,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@test.com",
        "email_status": "valid",
        "company_name": company_name,
        "company_domain": company_domain,
        "company_industry": "Technology",
        "company_size": "51-200",
        "lead_score": 75,
    }


def create_mock_company_research(
    campaign_id: UUID = SAMPLE_CAMPAIGN_ID,
    company_domain: str = "test.com",
) -> dict:
    """Create a mock company research record for testing."""
    return {
        "id": uuid4(),
        "campaign_id": campaign_id,
        "company_domain": company_domain,
        "company_name": "Test Company",
        "headline": "Test Company raises $10M Series A",
        "summary": "Test Company is growing rapidly",
        "relevance_score": 0.75,
        "has_recent_news": True,
        "has_funding": True,
        "has_hiring": False,
        "has_product_launch": False,
        "research_cost": 0.004,
        "created_at": datetime.now(UTC),
    }


def create_mock_extracted_fact(
    company_research_id: UUID = SAMPLE_RESEARCH_ID,
    category: str = "news",
    total_score: float = 0.7,
) -> dict:
    """Create a mock extracted fact for testing."""
    return {
        "id": uuid4(),
        "company_research_id": company_research_id,
        "fact_text": f"Sample {category} fact for testing",
        "category": category,
        "source_type": "web_search",
        "recency_days": 30,
        "recency_score": 0.67,
        "specificity_score": 0.7,
        "business_relevance_score": 0.7,
        "emotional_hook_score": 0.6,
        "total_score": total_score,
        "created_at": datetime.now(UTC),
    }
