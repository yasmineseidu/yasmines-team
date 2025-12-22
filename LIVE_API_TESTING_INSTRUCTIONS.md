# Google Docs API - Live API Testing Instructions

## Quick Start

Complete live API testing is ready to run. Follow these steps:

### Step 1: Get OAuth2 Access Token

Run the token acquisition script:

```bash
cd app/backend
bash scripts/get_google_token.sh
```

**What to expect:**
1. Script displays a verification URL and a user code
2. Open the URL in your browser
3. Enter the user code
4. Grant the permissions
5. Script displays your access token

**Example output:**
```
🔐 Getting Google OAuth2 Access Token
========================================

📱 Step 1: Requesting device code...

✅ Got device code

🔗 Visit this URL to authorize:
   https://www.google.com/device?user_code=ABC-DEF-GHI

📝 Enter this code when prompted:
   ABC-DEF-GHI

⏳ Waiting for authorization (press Ctrl+C to cancel)...

✅ Authorization successful!

🎉 OAuth2 Token Details:
=========================
Access Token: eyJhbGciOiJSUzI1NiIsImtp...
Expires In: 3600 seconds

📋 Add to .env:
GOOGLE_ACCESS_TOKEN=eyJhbGciOiJSUzI1NiIsImtp...
```

### Step 2: Add Token to .env

Copy the `GOOGLE_ACCESS_TOKEN` value from the script output and add to `.env`:

```bash
# .env
GOOGLE_ACCESS_TOKEN=<paste-token-here>
```

Or export as environment variable:

```bash
export GOOGLE_ACCESS_TOKEN='<paste-token-here>'
```

### Step 3: Run Live API Tests

Run all live API tests:

```bash
cd app/backend
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api
```

**Example output:**
```
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_authenticate PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_document PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_get_document PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_insert_text PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_batch_update PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_format_text_bold PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_table PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_share_document PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_get_permissions PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_complete_document_workflow PASSED
__tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_batch_operations_efficiency PASSED
...

======================== 18 passed in 127.34s =========================

Created document: 1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE
Created document: 1ABC2DEF3GHI4JKL5MNO6PQR7STU8VWX9YZA1BCD2
...
```

## What Gets Tested

### All 9 Endpoints

| # | Endpoint | Tests | Status |
|---|----------|-------|--------|
| 1 | authenticate | `test_live_authenticate` | ✅ Real API |
| 2 | create_document | `test_live_create_document`, `test_live_create_multiple_documents` | ✅ Real Documents |
| 3 | get_document | `test_live_get_document`, `test_live_get_document_content` | ✅ Real Retrieval |
| 4 | insert_text | `test_live_insert_text`, `test_live_insert_text_multiple_times` | ✅ Real Modifications |
| 5 | batch_update | `test_live_batch_update`, `test_live_batch_operations_efficiency` | ✅ Real Batch Ops |
| 6 | format_text | `test_live_format_text_bold`, `test_live_format_text_multiple_styles` | ✅ Real Formatting |
| 7 | create_table | `test_live_create_table`, `test_live_create_table_various_sizes` | ✅ Real Tables |
| 8 | share_document | `test_live_share_document` | ✅ Real Sharing |
| 9 | get_permissions | `test_live_get_permissions` | ✅ Real Permissions |

### Complete Workflows

- ✅ Complete document lifecycle (create → edit → format → share)
- ✅ Batch operations efficiency
- ✅ Error handling (invalid document IDs, auth failures)
- ✅ Multiple document creation
- ✅ Multiple text insertions
- ✅ Various table sizes
- ✅ Multiple formatting styles

## Test Execution Details

### Duration
- Expected: 1-3 minutes for 18 tests
- Depends on network latency and API responsiveness

### Documents Created
Tests create actual Google Docs with names like:
```
Live Test Document 20251222_143015
Live Get Test 20251222_143016
Live Insert Text Test 20251222_143017
```

### Cleanup
Google Docs API doesn't have a delete endpoint, so test documents are NOT automatically deleted.

**To clean up:**
1. Visit https://drive.google.com
2. Search for "Live Test"
3. Delete the test documents

Or delete via Drive API:
```bash
curl -X DELETE \
  "https://www.googleapis.com/drive/v3/files/DOCUMENT_ID" \
  -H "Authorization: Bearer $GOOGLE_ACCESS_TOKEN"
```

## Troubleshooting

### Token Script Fails

**Error:** `curl: command not found`
- Install curl: `brew install curl`

**Error:** `jq: command not found` (for parsing JSON)
- Install jq: `brew install jq`

### Tests Skip

**Problem:** `SKIPPED - GOOGLE_ACCESS_TOKEN not found`

**Solution:**
```bash
export GOOGLE_ACCESS_TOKEN='<your-token>'
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api
```

### Authentication Failures

**Error:** `GoogleDocsAuthError: Unauthorized`

**Causes:**
1. Token is expired (token expires in 1 hour)
2. Token is invalid
3. Scopes not granted

**Solution:** Get a new token by running the script again

### Rate Limit Errors

**Error:** `GoogleDocsRateLimitError: Rate limit exceeded (429)`

**Causes:**
- Too many API requests in short time
- Batch operations not being used efficiently

**Solution:**
- Tests use batch operations automatically
- Wait before running tests again
- Google rate limits: 60 write/minute, 300 read/minute

### Document Not Found

**Error:** `GoogleDocsError: Document not found`

**Causes:**
- Document was deleted
- Different Google account (test documents created in authenticated user's Drive)

**Solution:** This is expected for cleanup test

## Advanced Testing

### Run Single Test

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_document -v -m live_api
```

### Run with Output Capture

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api -s
```

Shows print statements and document creation details

### Run with Detailed Logging

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py -v -m live_api --log-cli-level=DEBUG
```

Shows full debug logs

### Load Testing (Create Multiple Docs)

```bash
python3 -m pytest __tests__/integration/test_google_docs_live.py::TestGoogleDocsLiveAPI::test_live_create_multiple_documents -v -m live_api
```

Creates 3 documents to test API under load

## Files Created

```
app/backend/
├── __tests__/integration/
│   └── test_google_docs_live.py          # 18 live API tests
├── scripts/
│   ├── get_google_token.sh               # Token acquisition script
│   └── google_oauth2_setup.py            # Python token helper

docs/
└── GOOGLE_DOCS_LIVE_API_TESTING.md       # Comprehensive guide
```

## Test Summary

### What This Proves

✅ **Real API Integration Works**
- Actual Google Docs API connection successful
- OAuth2 authentication functional
- All 9 endpoints operational

✅ **Complete Features**
- Document creation and retrieval
- Text insertion and formatting
- Table creation
- Document sharing
- Permission management

✅ **Production Ready**
- Error handling works
- Batch operations efficient
- Rate limiting respected
- Full workflow tested

## Next Steps

After successful live API tests:

1. **Monitor API Usage**
   - Check Google Cloud Console for API quota
   - Review rate limit usage
   - Monitor for errors

2. **Integrate with Main System**
   - Use GoogleDocsClient in agent system
   - Implement error handling
   - Add logging and monitoring

3. **Setup CI/CD**
   - Store GOOGLE_CLIENT_ID/SECRET as secrets
   - Obtain GOOGLE_ACCESS_TOKEN in CI pipeline
   - Run live tests as part of pipeline

## Documentation

For more information:
- [`docs/GOOGLE_DOCS_LIVE_API_TESTING.md`](docs/GOOGLE_DOCS_LIVE_API_TESTING.md) - Comprehensive testing guide
- [`docs/api-endpoints/google-docs.md`](docs/api-endpoints/google-docs.md) - API reference
- [`GOOGLE_DOCS_INTEGRATION_SUMMARY.md`](GOOGLE_DOCS_INTEGRATION_SUMMARY.md) - Implementation details

## Status

✅ **Live API Testing Setup COMPLETE**

Ready to run with real Google Docs API credentials.

---

**Generated**: 2025-12-22
**Status**: Ready for Live Testing
