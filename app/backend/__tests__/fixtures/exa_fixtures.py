"""Fixtures for Exa API integration tests."""

from typing import Any

# Sample search response
SAMPLE_SEARCH_RESPONSE: dict[str, Any] = {
    "requestId": "req_abc123",
    "costCredits": 0.1,
    "autopromptString": "companies building AI agents for enterprise",
    "results": [
        {
            "id": "exa_id_001",
            "url": "https://example.com/ai-agents-startup",
            "title": "Top AI Agent Startups Revolutionizing Enterprise",
            "score": 0.95,
            "publishedDate": "2024-12-15",
            "author": "Tech Analyst",
            "text": "These AI agent startups are changing how enterprises operate...",
            "highlights": [
                "AI agents are automating complex workflows",
                "Enterprise adoption is accelerating rapidly",
            ],
            "highlightScores": [0.92, 0.88],
            "summary": "Overview of top AI agent companies targeting enterprise market.",
            "image": "https://example.com/images/ai-agents.jpg",
            "favicon": "https://example.com/favicon.ico",
        },
        {
            "id": "exa_id_002",
            "url": "https://techcrunch.com/ai-agent-funding",
            "title": "AI Agent Companies Raise Record Funding in 2024",
            "score": 0.91,
            "publishedDate": "2024-12-10",
            "author": "Startup Reporter",
            "highlights": [
                "$5B invested in AI agent startups this year",
            ],
            "highlightScores": [0.89],
        },
        {
            "id": "exa_id_003",
            "url": "https://venturebeat.com/ai-automation",
            "title": "How AI Agents Are Transforming Business Automation",
            "score": 0.87,
            "publishedDate": "2024-12-05",
        },
    ],
}

# Sample search response without autoprompt
SAMPLE_SEARCH_RESPONSE_NO_AUTOPROMPT: dict[str, Any] = {
    "requestId": "req_def456",
    "costCredits": 0.05,
    "results": [
        {
            "id": "exa_id_010",
            "url": "https://example.com/article1",
            "title": "Article One",
            "score": 0.80,
        },
        {
            "id": "exa_id_011",
            "url": "https://example.com/article2",
            "title": "Article Two",
            "score": 0.75,
        },
    ],
}

# Sample find similar response
SAMPLE_FIND_SIMILAR_RESPONSE: dict[str, Any] = {
    "requestId": "req_similar_001",
    "costCredits": 0.1,
    "results": [
        {
            "id": "sim_001",
            "url": "https://competitor1.com/similar-article",
            "title": "Similar Content Found at Competitor Site",
            "score": 0.93,
            "publishedDate": "2024-12-01",
        },
        {
            "id": "sim_002",
            "url": "https://blog.example.com/related-post",
            "title": "Related Blog Post on Same Topic",
            "score": 0.88,
            "publishedDate": "2024-11-28",
        },
        {
            "id": "sim_003",
            "url": "https://news.example.com/coverage",
            "title": "News Coverage of Similar Subject",
            "score": 0.82,
        },
    ],
}

# Sample contents response
SAMPLE_CONTENTS_RESPONSE: dict[str, Any] = {
    "requestId": "req_contents_001",
    "costCredits": 0.15,
    "results": [
        {
            "id": "exa_id_001",
            "url": "https://example.com/ai-agents-startup",
            "title": "Top AI Agent Startups Revolutionizing Enterprise",
            "text": "Full article text here... These AI agent startups are changing how "
            "enterprises operate by automating complex workflows and decision making. "
            "The market is growing rapidly with enterprise adoption accelerating.",
            "highlights": [
                "AI agents are automating complex workflows",
                "Enterprise adoption is accelerating",
            ],
            "highlightScores": [0.92, 0.88],
            "summary": "Comprehensive overview of AI agent startups targeting enterprise market.",
        },
        {
            "id": "exa_id_002",
            "url": "https://techcrunch.com/ai-agent-funding",
            "title": "AI Agent Companies Raise Record Funding",
            "text": "AI agent companies have raised over $5 billion in funding this year...",
            "highlights": ["$5B invested in AI agent startups"],
            "highlightScores": [0.89],
        },
    ],
}

# Sample company search response
SAMPLE_COMPANY_SEARCH_RESPONSE: dict[str, Any] = {
    "requestId": "req_company_001",
    "costCredits": 0.1,
    "autopromptString": "AI healthcare startups company homepage",
    "results": [
        {
            "id": "company_001",
            "url": "https://healthai.com",
            "title": "HealthAI - AI-Powered Healthcare Solutions",
            "score": 0.94,
            "favicon": "https://healthai.com/favicon.ico",
        },
        {
            "id": "company_002",
            "url": "https://medtech-ai.io",
            "title": "MedTech AI - Transforming Medical Diagnostics",
            "score": 0.91,
        },
        {
            "id": "company_003",
            "url": "https://aicare.health",
            "title": "AI Care - Intelligent Patient Management",
            "score": 0.88,
        },
    ],
}

# Sample research paper search response
SAMPLE_RESEARCH_SEARCH_RESPONSE: dict[str, Any] = {
    "requestId": "req_research_001",
    "costCredits": 0.1,
    "results": [
        {
            "id": "paper_001",
            "url": "https://arxiv.org/abs/2024.12345",
            "title": "Advances in Large Language Model Agents",
            "score": 0.96,
            "publishedDate": "2024-12-01",
            "author": "Research Team",
        },
        {
            "id": "paper_002",
            "url": "https://papers.nips.cc/paper/2024/agent-learning",
            "title": "Agent Learning in Complex Environments",
            "score": 0.93,
            "publishedDate": "2024-11-15",
        },
    ],
}

# Sample news search response
SAMPLE_NEWS_SEARCH_RESPONSE: dict[str, Any] = {
    "requestId": "req_news_001",
    "costCredits": 0.05,
    "results": [
        {
            "id": "news_001",
            "url": "https://reuters.com/tech/ai-regulation",
            "title": "New AI Regulations Proposed by EU",
            "score": 0.92,
            "publishedDate": "2024-12-20",
        },
        {
            "id": "news_002",
            "url": "https://bbc.com/business/ai-investment",
            "title": "AI Investment Hits Record High",
            "score": 0.89,
            "publishedDate": "2024-12-19",
        },
    ],
}

# Empty response
SAMPLE_EMPTY_RESPONSE: dict[str, Any] = {
    "requestId": "req_empty_001",
    "costCredits": 0.01,
    "results": [],
}

# Error responses
SAMPLE_ERROR_RESPONSE_401: dict[str, Any] = {
    "error": "Invalid API key",
    "code": 401,
}

SAMPLE_ERROR_RESPONSE_429: dict[str, Any] = {
    "error": "Rate limit exceeded",
    "code": 429,
    "retryAfter": 60,
}

SAMPLE_ERROR_RESPONSE_500: dict[str, Any] = {
    "error": "Internal server error",
    "code": 500,
}

# Test data for search scenarios
SAMPLE_QUERIES: list[str] = [
    "AI startup funding trends 2024",
    "companies building autonomous agents",
    "latest research in machine learning",
    "SaaS tools for content marketing",
    "healthcare technology innovations",
]

SAMPLE_URLS: list[str] = [
    "https://techcrunch.com/ai-article",
    "https://arxiv.org/abs/2024.12345",
    "https://blog.openai.com/gpt-5",
    "https://news.ycombinator.com/item?id=12345",
]

SAMPLE_DOMAINS: list[str] = [
    "techcrunch.com",
    "venturebeat.com",
    "arxiv.org",
    "github.com",
    "linkedin.com",
]

# Category options
CATEGORIES: list[str] = [
    "company",
    "research paper",
    "news",
    "linkedin profile",
    "github",
    "tweet",
    "pdf",
]

