# Perplexity AI API Endpoints

## Overview
- **Base URL:** `https://api.perplexity.ai`
- **Authentication:** Bearer Token (API Key from `.env` as `PERPLEXITY_API_KEY`)
- **Rate Limits:** Varies by plan (contact Perplexity for details)
- **API Version:** Current (2024/2025)

## Available Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `sonar` | Lightweight, fast search | Quick queries, cost-effective |
| `sonar-pro` | Advanced search with larger context | Complex research, detailed answers |
| `sonar-reasoning-pro` | Premier reasoning capabilities | Advanced analysis, multi-step logic |
| `sonar-deep-research` | Exhaustive multi-step research | Comprehensive research projects |

## Endpoints

### 1. Chat Completions
**Method:** `POST`
**Path:** `/chat/completions`
**Description:** Generate AI responses with web search capabilities

**Request Parameters:**
- `model` (string, required): Model ID (e.g., "sonar", "sonar-pro")
- `messages` (array, required): Array of message objects with `role` and `content`
- `temperature` (float, optional): Randomness 0-2 (default: 0.2)
- `max_tokens` (int, optional): Maximum response tokens
- `stream` (bool, optional): Enable streaming (default: false)

**Web Search Options:**
- `web_search_options.search_mode` (string, optional): "web", "academic", or "sec"
- `web_search_options.search_recency_filter` (string, optional): Time filter
- `web_search_options.search_after_date_filter` (string, optional): Date filter (MM/DD/YYYY)

**Other Options:**
- `search_disabled` (bool, optional): Disable web search
- `response_language` (string, optional): Response language (sonar/sonar-pro only)
- `reasoning_effort` (string, optional): "low", "medium", "high" (deep-research only)

**Response Schema:**
```json
{
  "id": "chatcmpl-abc123",
  "model": "sonar",
  "created": 1234567890,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 200,
    "total_tokens": 250,
    "citation_tokens": 30,
    "num_search_queries": 3
  },
  "search_results": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "date": "2024-12-15",
      "snippet": "Article excerpt..."
    }
  ]
}
```

**Example Request:**
```python
from src.integrations import PerplexityClient

async with PerplexityClient(api_key=os.environ["PERPLEXITY_API_KEY"]) as client:
    result = await client.research(
        "What are the best SaaS pricing models?",
        model=PerplexityModel.SONAR_PRO,
        max_tokens=500,
    )
    print(result.content)
    for citation in result.citations:
        print(f"  - {citation.url}")
```

**Error Codes:**
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Invalid API key
- `429`: Rate Limit Exceeded - Too many requests
- `500`: Internal Server Error

**Test Status:** ✅ PASSED (Live API test)

---

## Client Methods

### research()
**Purpose:** One-off research queries with web search

```python
result = await client.research(
    query="What is quantum computing?",
    model=PerplexityModel.SONAR,
    search_mode=PerplexitySearchMode.WEB,
    max_tokens=500,
    temperature=0.2,
    response_language="English",
    search_recency_filter="month",
)
```

**Test Status:** ✅ PASSED

---

### chat()
**Purpose:** Multi-turn conversations with context

```python
conv = PerplexityConversation(
    system_prompt="You are a market research analyst."
)
result1 = await client.chat("What are top CRM platforms?", conversation=conv)
result2 = await client.chat("How do they compare on pricing?", conversation=conv)
```

**Test Status:** ✅ PASSED

---

### research_with_system_prompt()
**Purpose:** Research with custom persona

```python
result = await client.research_with_system_prompt(
    query="What are API best practices?",
    system_prompt="You are a software architect. Answer in bullet points.",
    max_tokens=300,
)
```

**Test Status:** ✅ PASSED

---

### academic_search()
**Purpose:** Search academic papers and research

```python
result = await client.academic_search(
    query="machine learning in healthcare",
    max_tokens=500,
)
```

**Test Status:** ✅ PASSED

---

### financial_research()
**Purpose:** Search SEC filings for financial research

```python
result = await client.financial_research(
    query="Apple quarterly earnings 2024",
    max_tokens=500,
)
```

**Test Status:** ✅ PASSED (via unit tests)

---

### deep_research()
**Purpose:** Exhaustive multi-step research

```python
result = await client.deep_research(
    query="comprehensive analysis of AI industry",
    reasoning_effort="high",
    max_tokens=1000,
)
```

**Test Status:** ✅ PASSED (via unit tests)

---

### health_check()
**Purpose:** Verify API connectivity

```python
status = await client.health_check()
# {"name": "perplexity", "healthy": true, "base_url": "...", "default_model": "sonar"}
```

**Test Status:** ✅ PASSED

---

### call_endpoint()
**Purpose:** Call any endpoint dynamically (future-proof)

```python
result = await client.call_endpoint(
    "/chat/completions",
    method="POST",
    json={
        "model": "sonar",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 50,
    }
)
```

**Test Status:** ✅ PASSED

---

## Search Modes

| Mode | Value | Description |
|------|-------|-------------|
| Web | `web` | Standard web search (default) |
| Academic | `academic` | Academic papers and research |
| SEC | `sec` | SEC filings for financial research |

---

## Conversation Management

The `PerplexityConversation` class manages multi-turn conversations:

```python
from src.integrations import PerplexityConversation

# Create conversation with optional system prompt
conv = PerplexityConversation(
    system_prompt="You are a helpful assistant."
)

# Use with chat method (automatically tracks context)
result1 = await client.chat("Hello", conversation=conv)
result2 = await client.chat("Follow up question", conversation=conv)

# Clear conversation
conv.clear()
```

---

## Error Handling

The client raises `PerplexityError` for all API failures:

```python
from src.integrations import PerplexityError

try:
    result = await client.research("query")
except PerplexityError as e:
    print(f"Error: {e.message}")
    print(f"Status: {e.status_code}")
    print(f"Data: {e.response_data}")
```

---

## Testing

### Unit Tests
```bash
uv run pytest __tests__/unit/integrations/test_perplexity.py -v
```
- **53 tests** - All passing
- **Coverage:** ~80%

### Live API Tests
```bash
uv run pytest __tests__/integration/test_perplexity_live.py -v -m live_api
```
- **13 tests** - All passing
- **100% pass rate** with real API

---

## Pricing Notes

- **sonar:** ~$0.20/1M input, $0.60/1M output + request fees
- **sonar-pro:** ~$3/1M input, $15/1M output + request fees
- Request fees vary by search context size (Low/Medium/High)
- Citations in responses count toward token costs

---

## Sample Data

Test fixtures available in:
- `__tests__/unit/integrations/test_perplexity.py` - Mock response fixtures
- `__tests__/integration/test_perplexity_live.py` - Live test scenarios
