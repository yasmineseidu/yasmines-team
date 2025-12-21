"""Fixtures for Serper API integration tests."""

from typing import Any

# Sample web search response with all result types
SAMPLE_WEB_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "AI startups 2024",
        "gl": "us",
        "hl": "en",
        "num": 10,
        "type": "search",
    },
    "organic": [
        {
            "position": 1,
            "title": "Top 10 AI Startups to Watch in 2024",
            "link": "https://techcrunch.com/ai-startups-2024",
            "snippet": "Discover the most innovative AI startups that are revolutionizing...",
            "displayedLink": "techcrunch.com",
            "date": "Dec 15, 2024",
            "sitelinks": [
                {"title": "AI News", "link": "https://techcrunch.com/ai"},
                {"title": "Funding", "link": "https://techcrunch.com/funding"},
            ],
        },
        {
            "position": 2,
            "title": "AI Startup Landscape Report 2024",
            "link": "https://venturebeat.com/ai-report-2024",
            "snippet": "Comprehensive analysis of the AI startup ecosystem...",
            "displayedLink": "venturebeat.com",
        },
        {
            "position": 3,
            "title": "How to Invest in AI Startups",
            "link": "https://forbes.com/ai-investing",
            "snippet": "Expert guide on identifying promising AI investments...",
            "displayedLink": "forbes.com",
        },
    ],
    "knowledgeGraph": {
        "title": "Artificial Intelligence",
        "type": "Technology",
        "description": "Artificial intelligence (AI) is intelligence demonstrated by machines...",
        "website": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "imageUrl": "https://upload.wikimedia.org/ai-image.jpg",
        "attributes": {
            "Field": "Computer Science",
            "Founded": "1956",
            "Key people": "Alan Turing, John McCarthy",
        },
    },
    "answerBox": {
        "title": "What are AI startups?",
        "snippet": "AI startups are companies that develop and commercialize artificial "
        "intelligence technologies, including machine learning, natural language "
        "processing, and computer vision solutions.",
        "link": "https://example.com/ai-startups-definition",
    },
    "peopleAlsoAsk": [
        {
            "question": "Which AI startup is best to invest in?",
            "snippet": "The best AI startups to invest in include companies focused on...",
            "title": "Best AI Startups for Investment",
            "link": "https://investor.com/ai-startups",
        },
        {
            "question": "How do I start an AI startup?",
            "snippet": "Starting an AI startup requires technical expertise, market research...",
            "title": "How to Start an AI Startup",
            "link": "https://entrepreneur.com/ai-startup-guide",
        },
        {
            "question": "What is the most valuable AI startup?",
            "snippet": "OpenAI remains the most valuable AI startup with a valuation of...",
            "title": "Most Valuable AI Startups",
            "link": "https://businessinsider.com/valuable-ai-startups",
        },
    ],
    "relatedSearches": [
        {"query": "AI companies to invest in 2024"},
        {"query": "best AI stocks"},
        {"query": "AI startup funding rounds"},
        {"query": "emerging AI technologies"},
    ],
}

# Sample image search response
SAMPLE_IMAGE_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "AI robot",
        "type": "images",
    },
    "images": [
        {
            "position": 1,
            "title": "Humanoid AI Robot",
            "imageUrl": "https://images.example.com/ai-robot-1.jpg",
            "source": "Robotics Today",
            "link": "https://roboticstoday.com/humanoid-robots",
            "thumbnailUrl": "https://images.example.com/ai-robot-1-thumb.jpg",
        },
        {
            "position": 2,
            "title": "AI Assistant Robot",
            "imageUrl": "https://images.example.com/ai-robot-2.jpg",
            "source": "Tech Weekly",
            "link": "https://techweekly.com/ai-assistants",
            "thumbnailUrl": "https://images.example.com/ai-robot-2-thumb.jpg",
        },
        {
            "position": 3,
            "title": "Industrial AI Robot",
            "imageUrl": "https://images.example.com/ai-robot-3.jpg",
            "source": "Manufacturing Daily",
            "link": "https://manufacturingdaily.com/industrial-ai",
        },
    ],
}

# Sample news search response
SAMPLE_NEWS_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "AI news",
        "type": "news",
    },
    "news": [
        {
            "position": 1,
            "title": "OpenAI Announces GPT-5 Release Date",
            "link": "https://news.example.com/gpt5-announcement",
            "snippet": "OpenAI has announced that GPT-5 will be released in Q1 2025...",
            "source": "AI News Daily",
            "date": "2 hours ago",
            "imageUrl": "https://news.example.com/gpt5-image.jpg",
        },
        {
            "position": 2,
            "title": "Google DeepMind Achieves Breakthrough in Protein Folding",
            "link": "https://news.example.com/deepmind-proteins",
            "snippet": "DeepMind's AlphaFold 3 can now predict protein structures with...",
            "source": "Science Today",
            "date": "1 day ago",
            "imageUrl": "https://news.example.com/alphafold-image.jpg",
        },
        {
            "position": 3,
            "title": "AI Regulation Bill Passes Senate",
            "link": "https://news.example.com/ai-regulation",
            "snippet": "The US Senate passed a comprehensive AI regulation bill...",
            "source": "Political Wire",
            "date": "3 days ago",
        },
    ],
}

# Sample places search response
SAMPLE_PLACES_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "coffee shops in San Francisco",
        "type": "places",
    },
    "places": [
        {
            "position": 1,
            "title": "Blue Bottle Coffee",
            "address": "66 Mint St, San Francisco, CA 94103",
            "rating": 4.6,
            "reviewsCount": 2150,
            "phone": "+1-415-555-0123",
            "website": "https://bluebottlecoffee.com",
            "category": "Coffee Shop",
            "latitude": 37.7823,
            "longitude": -122.4056,
        },
        {
            "position": 2,
            "title": "Sightglass Coffee",
            "address": "270 7th St, San Francisco, CA 94103",
            "rating": 4.5,
            "reviews": 1820,
            "phoneNumber": "+1-415-555-0456",
            "type": "Coffee Roaster",
            "lat": 37.7768,
            "lng": -122.4081,
        },
        {
            "position": 3,
            "title": "Ritual Coffee Roasters",
            "address": "432 Octavia St, San Francisco, CA 94102",
            "rating": 4.4,
            "reviewsCount": 980,
            "phone": "+1-415-555-0789",
            "website": "https://ritualroasters.com",
            "category": "Coffee Roaster",
        },
    ],
}

# Sample video search response
SAMPLE_VIDEO_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "how to use AI",
        "type": "videos",
    },
    "videos": [
        {
            "position": 1,
            "title": "Complete AI Tutorial for Beginners",
            "link": "https://www.youtube.com/watch?v=abc123",
            "snippet": "Learn everything about AI in this comprehensive tutorial...",
            "duration": "1:42:30",
            "channel": "AI Academy",
            "date": "2 months ago",
            "thumbnailUrl": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
        },
        {
            "position": 2,
            "title": "AI Tools Every Developer Should Know",
            "link": "https://www.youtube.com/watch?v=def456",
            "snippet": "Top 10 AI tools that will boost your productivity...",
            "duration": "15:30",
            "channel": "Developer Tips",
            "date": "1 week ago",
            "thumbnail": "https://i.ytimg.com/vi/def456/maxresdefault.jpg",
        },
    ],
}

# Sample shopping search response
SAMPLE_SHOPPING_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "AI robot vacuum",
        "type": "shopping",
    },
    "shopping": [
        {
            "position": 1,
            "title": "Roborock S8 Pro Ultra Robot Vacuum",
            "link": "https://amazon.com/roborock-s8-pro",
            "price": "$1,099.99",
            "source": "Amazon",
            "rating": 4.7,
            "reviewsCount": 3500,
            "imageUrl": "https://amazon.com/images/roborock-s8.jpg",
        },
        {
            "position": 2,
            "title": "iRobot Roomba j9+ Self-Emptying Robot Vacuum",
            "link": "https://bestbuy.com/roomba-j9",
            "price": "$899.99",
            "source": "Best Buy",
            "rating": 4.5,
            "reviews": 2100,
            "thumbnail": "https://bestbuy.com/images/roomba-j9.jpg",
        },
        {
            "position": 3,
            "title": "Ecovacs Deebot X2 Omni",
            "link": "https://walmart.com/ecovacs-x2",
            "price": "$1,199.00",
            "source": "Walmart",
            "rating": 4.6,
            "reviewsCount": 890,
        },
    ],
}

# Sample scholar search response
SAMPLE_SCHOLAR_SEARCH_RESPONSE: dict[str, Any] = {
    "searchParameters": {
        "q": "deep learning neural networks",
        "type": "scholar",
    },
    "organic": [
        {
            "position": 1,
            "title": "Deep Learning: A Comprehensive Survey",
            "link": "https://arxiv.org/abs/2001.00001",
            "snippet": "This paper provides a comprehensive survey of deep learning...",
            "publicationInfo": "Journal of Machine Learning Research, 2024",
            "citedByCount": 1250,
            "citedByLink": "https://scholar.google.com/scholar?cites=12345",
            "relatedArticlesLink": "https://scholar.google.com/scholar?related=12345",
            "pdfLink": "https://arxiv.org/pdf/2001.00001.pdf",
        },
        {
            "position": 2,
            "title": "Attention Is All You Need",
            "link": "https://arxiv.org/abs/1706.03762",
            "snippet": "The dominant sequence transduction models are based on complex...",
            "publication": "NeurIPS 2017",
            "citedBy": 85000,
            "citedByLink": "https://scholar.google.com/scholar?cites=67890",
        },
    ],
}

# Sample autocomplete response
SAMPLE_AUTOCOMPLETE_RESPONSE: dict[str, Any] = {
    "suggestions": [
        {"value": "artificial intelligence"},
        {"value": "artificial intelligence definition"},
        {"value": "artificial intelligence examples"},
        "artificial intelligence jobs",
        "artificial intelligence course",
    ],
}

# Sample error responses
SAMPLE_ERROR_RESPONSE_401: dict[str, Any] = {
    "error": "Invalid API key provided",
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

# Test data for various search scenarios
SAMPLE_QUERIES: list[str] = [
    "AI startups 2024",
    "best CRM software",
    "machine learning tutorial",
    "coffee shops near me",
    "iPhone 15 Pro Max",
    "climate change research papers",
    "how to start a business",
]

SAMPLE_COUNTRIES: list[str] = ["us", "uk", "de", "fr", "jp", "au", "ca", "in"]

SAMPLE_LANGUAGES: list[str] = ["en", "de", "fr", "es", "ja", "zh", "pt", "it"]

TIME_PERIODS: dict[str, str] = {
    "past_hour": "qdr:h",
    "past_day": "qdr:d",
    "past_week": "qdr:w",
    "past_month": "qdr:m",
    "past_year": "qdr:y",
}
