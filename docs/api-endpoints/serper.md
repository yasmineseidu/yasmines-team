# Serper API Endpoints

## Overview

- **Base URL:** `https://google.serper.dev`
- **Authentication:** API Key via `X-API-KEY` header
- **Rate Limits:**
  - Starter: 50 QPS
  - Standard: 100 QPS
  - Scale: 200 QPS
  - Ultimate: 300 QPS (default limit for high-tier)
- **Pricing:** $0.30 - $1.00 per 1,000 queries (2,500 free queries included)
- **Response Time:** 1-2 seconds typical

## Endpoints

### 1. Web Search

**Method:** `POST`
**Path:** `/search`
**Description:** Perform a Google web search with organic results, knowledge graph, answer box, and more.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results (1-100, default 10) |
| `page` | int | No | Page number for pagination |
| `gl` | string | No | Country code (default "us") |
| `hl` | string | No | Language code (default "en") |
| `location` | string | No | Specific location for local results |
| `tbs` | string | No | Time filter (qdr:h, qdr:d, qdr:w, qdr:m, qdr:y) |
| `safe` | string | No | Safe search ("off" to disable) |

**Response Schema:**
```json
{
  "searchParameters": {
    "q": "string",
    "gl": "string",
    "hl": "string",
    "num": 10,
    "type": "search"
  },
  "organic": [
    {
      "position": 1,
      "title": "string",
      "link": "string",
      "snippet": "string",
      "displayedLink": "string",
      "date": "string",
      "sitelinks": []
    }
  ],
  "knowledgeGraph": {
    "title": "string",
    "type": "string",
    "description": "string",
    "website": "string",
    "imageUrl": "string",
    "attributes": {}
  },
  "answerBox": {
    "title": "string",
    "snippet": "string",
    "link": "string"
  },
  "peopleAlsoAsk": [
    {
      "question": "string",
      "snippet": "string",
      "title": "string",
      "link": "string"
    }
  ],
  "relatedSearches": [
    {"query": "string"}
  ]
}
```

**Example Request:**
```python
result = await client.search(
    "best CRM software 2024",
    num=10,
    country="us",
    language="en"
)
```

**Test Status:** ✅ PASSED (7 live API tests)

---

### 2. Image Search

**Method:** `POST`
**Path:** `/images`
**Description:** Search for images using Google Images.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results (1-100, default 10) |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |
| `safe` | string | No | Safe search ("off" to disable) |

**Response Schema:**
```json
{
  "images": [
    {
      "position": 1,
      "title": "string",
      "imageUrl": "string",
      "source": "string",
      "link": "string",
      "thumbnailUrl": "string"
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_images("sunset beach", num=20)
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 3. News Search

**Method:** `POST`
**Path:** `/news`
**Description:** Search for news articles using Google News.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |
| `tbs` | string | No | Time filter |

**Response Schema:**
```json
{
  "news": [
    {
      "position": 1,
      "title": "string",
      "link": "string",
      "snippet": "string",
      "source": "string",
      "date": "string",
      "imageUrl": "string"
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_news("AI announcements", time_period="qdr:d")
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 4. Places Search

**Method:** `POST`
**Path:** `/places`
**Description:** Search for local businesses and places using Google Places.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |
| `location` | string | No | Specific location |

**Response Schema:**
```json
{
  "places": [
    {
      "position": 1,
      "title": "string",
      "address": "string",
      "rating": 4.5,
      "reviewsCount": 250,
      "phone": "string",
      "website": "string",
      "category": "string",
      "latitude": 40.7128,
      "longitude": -74.0060
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_places("coffee shops", location="San Francisco, CA")
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 5. Maps Search

**Method:** `POST`
**Path:** `/maps`
**Description:** Search for locations using Google Maps.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |
| `location` | string | No | Specific location |

**Response Schema:**
Same as Places Search - returns `places` array.

**Example Request:**
```python
result = await client.search_maps("hotels in Los Angeles")
```

**Test Status:** ✅ PASSED (1 live API test)

---

### 6. Video Search

**Method:** `POST`
**Path:** `/videos`
**Description:** Search for videos using Google Videos (primarily YouTube).

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |

**Response Schema:**
```json
{
  "videos": [
    {
      "position": 1,
      "title": "string",
      "link": "string",
      "snippet": "string",
      "duration": "10:30",
      "channel": "string",
      "date": "string",
      "thumbnailUrl": "string"
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_videos("python tutorial")
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 7. Shopping Search

**Method:** `POST`
**Path:** `/shopping`
**Description:** Search for products using Google Shopping.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |

**Response Schema:**
```json
{
  "shopping": [
    {
      "position": 1,
      "title": "string",
      "link": "string",
      "price": "$99.99",
      "source": "string",
      "rating": 4.5,
      "reviewsCount": 100,
      "imageUrl": "string"
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_shopping("wireless headphones")
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 8. Scholar Search

**Method:** `POST`
**Path:** `/scholar`
**Description:** Search for academic papers using Google Scholar.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `as_ylo` | int | No | Minimum publication year |
| `as_yhi` | int | No | Maximum publication year |

**Response Schema:**
```json
{
  "organic": [
    {
      "position": 1,
      "title": "string",
      "link": "string",
      "snippet": "string",
      "publicationInfo": "string",
      "citedByCount": 500,
      "citedByLink": "string",
      "relatedArticlesLink": "string",
      "pdfLink": "string"
    }
  ]
}
```

**Example Request:**
```python
result = await client.search_scholar(
    "deep learning neural networks",
    year_low=2020,
    year_high=2024
)
```

**Test Status:** ✅ PASSED (2 live API tests)

---

### 9. Patents Search

**Method:** `POST`
**Path:** `/patents`
**Description:** Search for patents using Google Patents.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `num` | int | No | Number of results |
| `gl` | string | No | Country code |

**Response Schema:**
Returns `organic` array with patent information.

**Example Request:**
```python
result = await client.search_patents("artificial intelligence")
```

**Test Status:** ✅ PASSED (1 live API test)

---

### 10. Autocomplete

**Method:** `POST`
**Path:** `/autocomplete`
**Description:** Get search query suggestions.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Partial search query |
| `gl` | string | No | Country code |
| `hl` | string | No | Language code |

**Response Schema:**
```json
{
  "suggestions": [
    {"value": "string"},
    "string"
  ]
}
```

**Example Request:**
```python
result = await client.autocomplete("how to learn prog")
```

**Test Status:** ✅ PASSED (2 live API tests)

---

## Future-Proof Design

This client supports calling new endpoints dynamically:

```python
# Call any new endpoint without code changes
result = await client.call_endpoint(
    "/new-endpoint",
    method="POST",
    json={"q": "query", "param": "value"}
)
```

## Error Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Invalid API key |
| `402` | Payment Required - Insufficient credits |
| `429` | Rate Limit Exceeded |
| `500` | Internal Server Error |

## Testing

All endpoints are tested with real API keys from `.env`:

- **Unit Tests:** `__tests__/unit/integrations/test_serper.py` (43 tests)
- **Live API Tests:** `__tests__/integration/test_serper_live.py` (26 tests)
- **Test Coverage:** 86.32%
- **Pass Rate:** 100% (no exceptions)

## Sample Data

Sample data for testing is available in:
- `__tests__/fixtures/serper_fixtures.py`

## Client Usage

```python
from src.integrations import SerperClient

async def main():
    client = SerperClient(api_key="your-api-key")

    # Web search
    result = await client.search("best CRM software")

    # Access results
    for item in result.organic:
        print(f"{item.position}. {item.title}")
        print(f"   URL: {item.link}")
        print(f"   Snippet: {item.snippet}")

    # Knowledge graph (if available)
    if result.knowledge_graph:
        print(f"Knowledge Graph: {result.knowledge_graph.title}")

    # Close client when done
    await client.close()
```

## Resources

- [Serper.dev](https://serper.dev/) - Official website
- [API Documentation](https://serper.dev/docs) - Official docs
- [Pricing](https://serper.dev/pricing) - Pricing tiers
