"""Fixtures for SerpApi integration tests."""

from typing import Any

# Sample web search response with all result types
SAMPLE_WEB_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "search_abc123",
        "status": "Success",
        "created_at": "2024-12-21 10:00:00 UTC",
        "processed_at": "2024-12-21 10:00:01 UTC",
        "total_time_taken": 1.23,
        "google_url": "https://www.google.com/search?q=AI+startups+2024",
        "raw_html_file": "https://serpapi.com/html/abc123",
    },
    "search_information": {
        "query_displayed": "AI startups 2024",
        "total_results": 1250000000,
        "time_taken_displayed": 0.52,
        "organic_results_state": "Results for exact spelling",
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Top 10 AI Startups to Watch in 2024",
            "link": "https://techcrunch.com/ai-startups-2024",
            "snippet": "Discover the most innovative AI startups that are revolutionizing...",
            "displayed_link": "https://techcrunch.com › ai-startups",
            "favicon": "https://techcrunch.com/favicon.ico",
            "date": "Dec 15, 2024",
            "cached_page_link": "https://webcache.googleusercontent.com/...",
            "sitelinks": {
                "inline": [
                    {"title": "AI News", "link": "https://techcrunch.com/ai"},
                    {"title": "Funding", "link": "https://techcrunch.com/funding"},
                ]
            },
        },
        {
            "position": 2,
            "title": "AI Startup Landscape Report 2024",
            "link": "https://venturebeat.com/ai-report-2024",
            "snippet": "Comprehensive analysis of the AI startup ecosystem...",
            "displayed_link": "https://venturebeat.com › reports",
            "rich_snippet": {
                "bottom": {
                    "extensions": ["5 min read", "Updated Dec 2024"],
                }
            },
        },
        {
            "position": 3,
            "title": "How to Invest in AI Startups",
            "link": "https://forbes.com/ai-investing",
            "snippet": "Expert guide on identifying promising AI investments...",
            "displayed_link": "https://forbes.com",
            "source": "Forbes",
        },
    ],
    "ads": [
        {
            "position": 1,
            "title": "AI Solutions for Enterprise - Free Demo",
            "link": "https://ai-enterprise.com/demo",
            "tracking_link": "https://www.googleadservices.com/...",
            "displayed_link": "https://ai-enterprise.com",
            "description": "Transform your business with AI. Get started with a free demo today.",
            "sitelinks": [
                {"title": "Pricing", "link": "https://ai-enterprise.com/pricing"},
            ],
            "extensions": ["Free Demo", "24/7 Support"],
        },
    ],
    "knowledge_graph": {
        "title": "Artificial Intelligence",
        "type": "Technology",
        "description": "Artificial intelligence (AI) is intelligence demonstrated by machines...",
        "entity_type": "Thing",
        "kgmid": "/m/0mkz",
        "source": {
            "name": "Wikipedia",
            "link": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        },
        "header_images": [
            {"image": "https://upload.wikimedia.org/ai-image.jpg"},
        ],
        "website": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "attributes": {
            "Field": "Computer Science",
            "Founded": "1956",
        },
    },
    "answer_box": {
        "type": "organic_result",
        "title": "What are AI startups?",
        "snippet": "AI startups are companies that develop and commercialize artificial "
        "intelligence technologies, including machine learning, natural language "
        "processing, and computer vision solutions.",
        "link": "https://example.com/ai-startups-definition",
        "displayed_link": "https://example.com",
        "highlighted_words": ["AI startups", "artificial intelligence"],
    },
    "related_questions": [
        {
            "question": "Which AI startup is best to invest in?",
            "snippet": "The best AI startups to invest in include companies focused on...",
            "title": "Best AI Startups for Investment",
            "link": "https://investor.com/ai-startups",
            "displayed_link": "https://investor.com",
        },
        {
            "question": "How do I start an AI startup?",
            "snippet": "Starting an AI startup requires technical expertise, market research...",
            "title": "How to Start an AI Startup",
            "link": "https://entrepreneur.com/ai-startup-guide",
        },
    ],
    "related_searches": [
        {"query": "AI companies to invest in 2024", "link": "https://google.com/..."},
        {"query": "best AI stocks", "link": "https://google.com/..."},
        {"query": "AI startup funding rounds", "link": "https://google.com/..."},
        {"query": "emerging AI technologies"},
    ],
    "serpapi_pagination": {
        "current": 1,
        "next": "https://serpapi.com/search?...",
        "other_pages": {
            "2": "https://serpapi.com/search?...",
            "3": "https://serpapi.com/search?...",
        },
    },
}

# Sample image search response
SAMPLE_IMAGE_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "image_abc123",
        "status": "Success",
    },
    "images_results": [
        {
            "position": 1,
            "title": "Humanoid AI Robot",
            "thumbnail": "https://images.example.com/ai-robot-1-thumb.jpg",
            "original": "https://images.example.com/ai-robot-1.jpg",
            "source": "Robotics Today",
            "link": "https://roboticstoday.com/humanoid-robots",
            "is_product": False,
        },
        {
            "position": 2,
            "title": "AI Assistant Robot",
            "thumbnail": "https://images.example.com/ai-robot-2-thumb.jpg",
            "original": "https://images.example.com/ai-robot-2.jpg",
            "source": "Tech Weekly",
            "link": "https://techweekly.com/ai-assistants",
            "is_product": True,
        },
        {
            "position": 3,
            "title": "Industrial AI Robot",
            "thumbnail": "https://images.example.com/ai-robot-3-thumb.jpg",
            "original": "https://images.example.com/ai-robot-3.jpg",
            "source": "Manufacturing Daily",
            "link": "https://manufacturingdaily.com/industrial-ai",
        },
    ],
}

# Sample news search response
SAMPLE_NEWS_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "news_abc123",
        "status": "Success",
    },
    "news_results": [
        {
            "position": 1,
            "title": "OpenAI Announces GPT-5 Release Date",
            "link": "https://news.example.com/gpt5-announcement",
            "snippet": "OpenAI has announced that GPT-5 will be released in Q1 2025...",
            "source": "AI News Daily",
            "date": "2 hours ago",
            "thumbnail": "https://news.example.com/gpt5-image.jpg",
        },
        {
            "position": 2,
            "title": "Google DeepMind Achieves Breakthrough in Protein Folding",
            "link": "https://news.example.com/deepmind-proteins",
            "snippet": "DeepMind's AlphaFold 3 can now predict protein structures with...",
            "source": "Science Today",
            "date": "1 day ago",
            "thumbnail": "https://news.example.com/alphafold-image.jpg",
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

# Sample shopping search response
SAMPLE_SHOPPING_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "shop_abc123",
        "status": "Success",
    },
    "shopping_results": [
        {
            "position": 1,
            "title": "Roborock S8 Pro Ultra Robot Vacuum",
            "link": "https://amazon.com/roborock-s8-pro",
            "price": "$1,099.99",
            "extracted_price": 1099.99,
            "source": "Amazon",
            "rating": 4.7,
            "reviews": 3500,
            "thumbnail": "https://amazon.com/images/roborock-s8.jpg",
            "delivery": "Free delivery",
        },
        {
            "position": 2,
            "title": "iRobot Roomba j9+ Self-Emptying Robot Vacuum",
            "link": "https://bestbuy.com/roomba-j9",
            "price": "$899.99",
            "extracted_price": 899.99,
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
            "extracted_price": 1199.00,
            "source": "Walmart",
            "rating": 4.6,
            "reviews": 890,
        },
    ],
}

# Sample local/places search response
SAMPLE_LOCAL_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "local_abc123",
        "status": "Success",
    },
    "local_results": [
        {
            "position": 1,
            "title": "Blue Bottle Coffee",
            "place_id": "ChIJ0zQtYiw...",
            "address": "66 Mint St, San Francisco, CA 94103",
            "phone": "+1-415-555-0123",
            "website": "https://bluebottlecoffee.com",
            "rating": 4.6,
            "reviews": 2150,
            "type": "Coffee Shop",
            "hours": "Open ⋅ Closes 6PM",
            "gps_coordinates": {
                "latitude": 37.7823,
                "longitude": -122.4056,
            },
            "thumbnail": "https://maps.example.com/blue-bottle.jpg",
        },
        {
            "position": 2,
            "title": "Sightglass Coffee",
            "place_id": "ChIJ8z4rPiw...",
            "address": "270 7th St, San Francisco, CA 94103",
            "rating": 4.5,
            "reviews": 1820,
            "type": "Coffee Roaster",
            "gps_coordinates": {
                "latitude": 37.7768,
                "longitude": -122.4081,
            },
        },
    ],
}

# Sample video search response
SAMPLE_VIDEO_SEARCH_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "video_abc123",
        "status": "Success",
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Complete AI Tutorial for Beginners - YouTube",
            "link": "https://www.youtube.com/watch?v=abc123",
            "snippet": "Learn everything about AI in this comprehensive tutorial...",
            "displayed_link": "https://www.youtube.com",
            "rich_snippet": {
                "video": {
                    "duration": "1:42:30",
                    "channel": "AI Academy",
                    "date": "2 months ago",
                }
            },
        },
        {
            "position": 2,
            "title": "AI Tools Every Developer Should Know",
            "link": "https://www.youtube.com/watch?v=def456",
            "snippet": "Top 10 AI tools that will boost your productivity...",
            "displayed_link": "https://www.youtube.com",
        },
    ],
}

# Sample account info response
SAMPLE_ACCOUNT_INFO_RESPONSE: dict[str, Any] = {
    "account_email": "user@example.com",
    "plan_name": "Developer",
    "plan_searches_left": 4850,
    "searches_per_month": 5000,
    "api_key": "abc...xyz",  # Truncated for security  # pragma: allowlist secret
    "total_searches_used": 150,
}

# Error responses
SAMPLE_ERROR_RESPONSE_401: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

SAMPLE_ERROR_RESPONSE_429: dict[str, Any] = {
    "error": "Rate limit exceeded. Please wait a moment before retrying.",
}

SAMPLE_ERROR_RESPONSE_500: dict[str, Any] = {
    "error": "Internal server error. Please try again later.",
}

SAMPLE_ERROR_RESPONSE_QUOTA: dict[str, Any] = {
    "error": "Monthly quota exceeded. Please upgrade your plan at https://serpapi.com/pricing",
}

# Empty response (no results)
SAMPLE_EMPTY_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "empty_abc123",
        "status": "Success",
    },
    "search_information": {
        "query_displayed": "xyzzy123nonsense",
        "total_results": 0,
        "organic_results_state": "No results found",
    },
    "organic_results": [],
}

# Response with only ads (no organic)
SAMPLE_ADS_ONLY_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "ads_abc123",
        "status": "Success",
    },
    "ads": [
        {
            "position": 1,
            "title": "Buy Now - Special Offer",
            "link": "https://shop.example.com",
            "description": "Limited time offer. Shop now!",
        },
    ],
    "top_ads": [
        {
            "position": 2,
            "title": "Premium Product - Best Prices",
            "link": "https://premium.example.com",
            "description": "Premium quality at affordable prices.",
        },
    ],
    "organic_results": [],
}

# Test data for various search scenarios
SAMPLE_QUERIES: list[str] = [
    "AI startups 2024",
    "best CRM software",
    "machine learning tutorial",
    "coffee shops near me",
    "iPhone 16 Pro Max",
    "climate change research papers",
    "how to start a business",
]

SAMPLE_COUNTRIES: list[str] = ["us", "uk", "de", "fr", "jp", "au", "ca", "in"]

SAMPLE_LANGUAGES: list[str] = ["en", "de", "fr", "es", "ja", "zh", "pt", "it"]

TIME_FILTERS: dict[str, str] = {
    "past_hour": "qdr:h",
    "past_day": "qdr:d",
    "past_week": "qdr:w",
    "past_month": "qdr:m",
    "past_year": "qdr:y",
}

# Search engines supported
SEARCH_ENGINES: list[str] = [
    "google",
    "bing",
    "yahoo",
    "duckduckgo",
    "baidu",
    "yandex",
]
