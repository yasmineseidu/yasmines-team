# Google Docs API - Live API Testing Guide

Complete guide to running live API tests against real Google Docs service.

## Overview

The live API tests will:
- ✅ Create real Google Docs documents
- ✅ Test all 9 endpoints against live API
- ✅ Perform actual document operations
- ✅ Verify complete workflows
- ✅ Clean up test documents after testing

## Prerequisites

1. **Google OAuth2 Credentials**
   - `GOOGLE_CLIENT_ID` - Already in .env
   - `GOOGLE_CLIENT_SECRET` - Already in .env
   - `GOOGLE_ACCESS_TOKEN` - Need to obtain

2. **Google Account**
   - Account must have Google Docs access
   - Drive API enabled in Google Cloud Project

## Getting Access Token

### Option 1: Device Flow (No Browser Required)

```bash
cd app/backend
bash scripts/get_google_token.sh
```

**Steps:**
1. Script will display a verification URL and user code
2. Visit the URL and enter the code
3. Authorize the application
4. Script will display the access token
5. Copy `GOOGLE_ACCESS_TOKEN` value
6. Add to `.env` file

### Option 2: Manual OAuth2 Device Flow

```bash
# Request device code
curl -X POST "https://oauth2.googleapis.com/device/code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "scope=https://www.googleapis.com/auth/documents%20https://www.googleapis.com/auth/drive.file"

# You'll get a response with device_code, user_code, and verification_url
# Visit the verification_url and enter the user_code

# Then poll for token
curl -X POST "https://oauth2.googleapis.com/token" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "device_code=DEVICE_CODE" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code"
```

### Option 3: Using Python Helper

```bash
cd app/backend
python3 scripts/google_oauth2_setup.py --method user-oauth
```

## Setting Up Environment

### Add to .env

After obtaining the access token:

```bash
# Add to .env file
GOOGLE_ACCESS_TOKEN=<your-access-token-here>
```

Or export as environment variable:

```bash
export GOOGLE_ACCESS_TOKEN='<your-access-token-here>'
```

## Running Live API Tests

### Run All Live Tests

```bash
cd app/backend
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api
```

### Run Specific Test

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_document -v -m live_api
```

### Run with Output Capture

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api -s
```

### Run with Detailed Logging

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api --log-cli-level=DEBUG
```

## Test Endpoints Covered

| # | Endpoint | Test | Status |
|---|----------|------|--------|
| 1 | authenticate | `test_live_authenticate` | ✅ |
| 2 | create_document | `test_live_create_document`, `test_live_create_multiple_documents` | ✅ |
| 3 | get_document | `test_live_get_document`, `test_live_get_document_content` | ✅ |
| 4 | insert_text | `test_live_insert_text`, `test_live_insert_text_multiple_times` | ✅ |
| 5 | batch_update | `test_live_batch_update`, `test_live_batch_operations_efficiency` | ✅ |
| 6 | format_text | `test_live_format_text_bold`, `test_live_format_text_multiple_styles` | ✅ |
| 7 | create_table | `test_live_create_table`, `test_live_create_table_various_sizes` | ✅ |
| 8 | share_document | `test_live_share_document` | ✅ |
| 9 | get_document_permissions | `test_live_get_permissions` | ✅ |

## Test Results Interpretation

### Success Output Example

```
test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_document PASSED
test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_get_document PASSED
test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_insert_text PASSED
...

======================== 12 passed in 45.23s =========================

Created document: 1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE
Created document: 1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T
...
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `GOOGLE_ACCESS_TOKEN not set` | Missing token in .env | Run `get_google_token.sh` to obtain token |
| `GoogleDocsAuthError: Unauthorized` | Invalid or expired token | Get a new token using device flow |
| `googleapiclient.errors.HttpError 403` | Insufficient permissions | Ensure scopes include documents and drive.file |
| `googleapiclient.errors.HttpError 404` | Document not found | Document may have been deleted |
| `googleapiclient.errors.HttpError 429` | Rate limited | Wait before retrying or use batch operations |

## Test Document Cleanup

The tests create real Google Documents for testing. These documents are created with names like:

```
Live Test Document 20251222_143015
Live Get Test 20251222_143016
Live Insert Text Test 20251222_143017
```

### Manual Cleanup

Test documents are NOT automatically deleted. To clean up:

1. **Option 1: Via Google Drive UI**
   - Visit https://drive.google.com
   - Search for "Live Test"
   - Delete the test documents

2. **Option 2: Via Script (creates cleanup script)**
   - Tests output document IDs at the end
   - Use `gcloud` or Google Drive API to delete:
   ```bash
   # Using Drive API
   curl -X DELETE \
     "https://www.googleapis.com/drive/v3/files/DOCUMENT_ID" \
     -H "Authorization: Bearer $GOOGLE_ACCESS_TOKEN"
   ```

## Interpreting Test Output

### Complete Workflow Test Example

```
test_live_complete_document_workflow PASSED

Completed full workflow for document: 1ABC...
  - Created document
  - Added text
  - Applied formatting
  - Created table
  - Retrieved final document
```

### Batch Operations Test Example

```
test_live_batch_operations_efficiency PASSED

Batch operation efficiency test passed: 1DEF...
  - 3 operations in 1 batch request
  - Efficient API quota usage
```

## Performance Considerations

### Rate Limits

Google Docs API has rate limits:
- **Read**: 300 requests/minute per user
- **Write**: 60 requests/minute per user
- **Batch operations**: Count as 1 request regardless of sub-operations

Live tests respect these limits:
- Batch operations are used for efficiency
- Tests are not run in parallel (sequential execution)
- Each test waits for previous to complete

### Expected Test Duration

- 12 tests: ~45-60 seconds
- 25 tests: ~2-3 minutes
- Full suite: ~3-5 minutes

## Continuous Integration

### GitHub Actions Example

```yaml
name: Live API Tests

on: [push, pull_request]

jobs:
  live-api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run live API tests
        env:
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_ACCESS_TOKEN: ${{ secrets.GOOGLE_ACCESS_TOKEN }}
        run: |
          cd app/backend
          pytest __tests__/integration/test_google_docs_live.py -v -m live_api
```

## Troubleshooting

### Tests Skip Instead of Running

```
SKIPPED - GOOGLE_ACCESS_TOKEN not found
```

**Solution**: Set `GOOGLE_ACCESS_TOKEN` environment variable

```bash
export GOOGLE_ACCESS_TOKEN='<token>'
pytest __tests__/integration/test_google_docs_live.py -v -m live_api
```

### Authentication Failures

```
GoogleDocsAuthError: Unauthorized
```

**Solutions**:
1. Token may be expired - get new token
2. Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct
3. Verify OAuth2 scopes are granted

### Document Not Found Errors

```
GoogleDocsError: Document not found: doc-123
```

**Causes**:
- Document was deleted
- Document ID is incorrect
- Document doesn't have sharing permission

### Rate Limit Errors

```
GoogleDocsRateLimitError: Rate limit exceeded
```

**Solutions**:
1. Use batch operations to reduce requests
2. Add delays between requests
3. Wait before retrying (exponential backoff)

## Advanced Testing

### Load Testing

Create multiple documents in sequence:

```bash
pytest __tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_multiple_documents -v -m live_api
```

### Concurrent Operations

All tests run sequentially. For concurrent testing, modify the test file to use `asyncio.gather()`:

```python
# Create multiple documents concurrently
tasks = [
    self.client.create_document(title=f"Doc {i}")
    for i in range(5)
]
results = await asyncio.gather(*tasks)
```

### Performance Profiling

```bash
pytest __tests__/integration/test_google_docs_live.py -v -m live_api --profile
```

## Documentation

For complete API documentation, see:
- [`docs/api-endpoints/google-docs.md`](api-endpoints/google-docs.md) - API reference
- [`GOOGLE_DOCS_INTEGRATION_SUMMARY.md`](../GOOGLE_DOCS_INTEGRATION_SUMMARY.md) - Implementation overview
- [`app/backend/__tests__/integration/TEST_REPORT_google_docs.md`](../app/backend/__tests__/integration/TEST_REPORT_google_docs.md) - Unit/integration test report

## References

- [Google Docs API Documentation](https://developers.google.com/workspace/docs/api)
- [OAuth2 Device Flow](https://developers.google.com/identity/protocols/oauth2/limited-input-device)
- [Google Drive API Documentation](https://developers.google.com/drive/api)

---

**Last Updated**: 2025-12-22
**Status**: Ready for Live Testing
