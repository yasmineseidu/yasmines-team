# Exa Live Integration Tests

## Overview
Comprehensive live integration tests for Exa API client with **42 test cases** covering all endpoints.

## Test Coverage

### ✅ Search Endpoint (13 tests)
- Basic search
- Semantic search with various queries (5 parameterized tests)
- Neural vs keyword search types
- Autoprompt functionality
- Domain filtering (include/exclude)
- Category filtering
- Date filtering
- Max results handling

### ✅ Find Similar Endpoint (4 tests)
- Basic find similar
- URL samples (parameterized)
- Domain exclusion/inclusion

### ✅ Get Contents Endpoint (3 tests)
- Basic content extraction
- Highlights extraction
- AI summary extraction

### ✅ Search and Contents (3 tests)
- Combined search + content
- With highlights
- With summary

### ✅ Find Similar and Contents (1 test)
- Combined similar + content extraction

### ✅ Convenience Methods (6 tests)
- search_companies() (3 parameterized)
- search_research_papers() (2 parameterized)
- search_news() (2 parameterized)

### ✅ Health Check & Utilities (3 tests)
- Health check
- Cache clearing
- Caching functionality

### ✅ Future-Proof Endpoint (3 tests)
- call_endpoint() with /search
- call_endpoint() with /findSimilar
- call_endpoint() with /contents

### ✅ Error Handling (4 tests)
- Invalid query validation
- Invalid num_results validation
- Invalid URL validation
- Empty IDs validation

## Running Tests

### Prerequisites
- Valid EXA_API_KEY from https://dashboard.exa.ai
- Internet connectivity
- API credits available

### Option 1: Set in .env file
```bash
# Edit .env file at project root
EXA_API_KEY=your_actual_api_key_here

# Run tests
cd app/backend
uv run pytest __tests__/integration/test_exa_live.py -v
```

### Option 2: Environment variable
```bash
export EXA_API_KEY=your_actual_api_key_here
cd app/backend
uv run pytest __tests__/integration/test_exa_live.py -v
```

### Option 3: Helper script
```bash
cd app/backend/__tests__/integration
./run_exa_tests.sh your_actual_api_key_here
```

## Expected Results
When run with a valid API key, all **42 tests should pass 100%** with no exceptions.

## Future-Proof Design
The `call_endpoint()` method allows calling any Exa API endpoint, including future endpoints not yet wrapped:
```python
# Example: Call a new endpoint
response = await client.call_endpoint(
    "/new-endpoint",
    method="POST",
    json={"param": "value"}
)
```

## Sample Test Data
The test suite includes comprehensive sample data:
- 5 semantic search queries
- 3 company search queries
- 2 research paper queries
- 2 news search queries
- 4 URLs for similarity search
- Multiple test domains for filtering

All tests use realistic, production-like queries and data.
