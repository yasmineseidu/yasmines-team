# Google Drive OAuth Token Setup Guide

This guide explains how to obtain a real Google OAuth access token for running the complete integration test suite with the live Google Drive API.

## Overview

The integration tests in `app/backend/__tests__/integration/google_drive/` can run in two modes:

1. **Unit Tests Only** (32 tests) - Mocked, no API calls needed
   ```bash
   pytest app/backend/__tests__/unit/integrations/google_drive/ -v
   ```

2. **Full Integration Tests** (21 tests + 4 endpoint coverage tests) - Real API calls
   ```bash
   pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
   ```

## Step 1: Get Authorization Code

### Option A: Manual Browser Method (Recommended)

1. Copy this URL (replace placeholders if needed):
   ```
   https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline
   ```

2. Open the URL in your browser

3. Grant the requested permissions to Claude Code app

4. You'll be redirected to: `http://localhost:8000/api/google/callback?code=<AUTHORIZATION_CODE>&scope=...`

5. **Copy the `code` parameter** (the long string after `code=`)

### Step 2: Exchange Code for Access Token

Using the authorization code you copied, run:

```bash
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}"
export GOOGLE_REDIRECT_URI="http://localhost:8000/api/google/callback"

python3 app/backend/scripts/exchange_oauth_code.py <your-authorization-code>
```

Example:
```bash
python3 app/backend/scripts/exchange_oauth_code.py 4/0AX4XfWiXxQp2...
```

**What this does:**
- Exchanges your authorization code for an access token
- Saves the token to `.google_drive_token.json`
- Displays your access token (first 50 chars shown for security)

### Step 3: Verify Token Was Saved

Check that the token file was created:
```bash
ls -la .google_drive_token.json
cat .google_drive_token.json
```

You should see a JSON file with:
```json
{
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0gRx..."
}
```

## Step 4: Run Integration Tests

Now you can run the full integration test suite:

```bash
# Run all integration tests
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v

# Or run with output
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v -s

# Or run specific test
pytest app/backend/__tests__/integration/google_drive/test_live_api.py::TestGoogleDriveLiveAPI::test_01_health_check -v
```

## Expected Test Output

When running with a valid token, you should see:

```
============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-9.0.1
collected 25 items

app/backend/__tests__/integration/google_drive/test_live_api.py::TestGoogleDriveLiveAPI::test_01_health_check PASSED [  4%]
app/backend/__tests__/integration/google_drive/test_live_api.py::TestGoogleDriveLiveAPI::test_02_list_files_no_filter PASSED [  8%]
app/backend/__tests__/integration/google_drive/test_live_api.py::TestGoogleDriveLiveAPI::test_03_list_files_with_query PASSED [ 12%]
... [more tests] ...

======================== 25 passed in 45.23s ========================
```

## Troubleshooting

### Issue: "No valid Google access token found"

**Cause:** Token file doesn't exist or credentials not set in environment

**Solution:**
1. Make sure `.google_drive_token.json` exists in the project root
2. Or run the authorization flow again

```bash
python3 app/backend/scripts/exchange_oauth_code.py <code>
```

### Issue: "Permission denied: 403"

**Cause:** OAuth scopes don't include Drive access

**Solution:**
- Revoke the app's access at https://myaccount.google.com/permissions
- Re-authorize using the URL above (it requests `drive` and `drive.file` scopes)

### Issue: "Authentication required"

**Cause:** OAuth credentials not set in environment

**Solution:**
```bash
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}"
export GOOGLE_REDIRECT_URI="http://localhost:8000/api/google/callback"
```

### Issue: "Rate limited: 429"

**Cause:** Too many requests to Google Drive API too quickly

**Solution:**
- Wait 1-2 minutes before retrying
- The client automatically retries with exponential backoff
- Tests implement delays between operations

## Token Refresh

If your token expires, the client will automatically refresh it using the `refresh_token` saved in `.google_drive_token.json`.

If refresh fails (e.g., refresh_token revoked), repeat Step 1-3 to get a new token.

## Tokens & Security

- Access tokens expire in ~1 hour
- Refresh tokens don't expire but can be revoked
- **Never commit `.google_drive_token.json` to git** (already in .gitignore)
- Tokens are stored locally only and not sent anywhere except Google APIs

## All 25 Tests Explained

### Integration Tests (21)
1. **Health Check** - Verify API connectivity
2. **List Files** - List all files in Drive
3. **List with Query** - Filter by MIME type
4. **List with Pagination** - Test page tokens
5. **List with Ordering** - Custom sort order
6. **Create Folder** - Create directory
7. **Create Document** - Create Google Docs
8. **Get Metadata** - Retrieve file information
9. **Get Non-existent** - Test 404 handling
10. **Read Content** - Extract text from documents
11. **Upload File** - Upload file to Drive
12. **Export to PDF** - PDF export
13. **Export to DOCX** - Word export
14. **Export to CSV** - Spreadsheet export
15. **All Export Formats** - Test all 10 formats
16. **Share File** - Permission management
17. **Delete to Trash** - Soft delete
18. **Delete Permanently** - Hard delete
19. **Future Extensibility** - Architecture verification
20. **Error Handling** - Error scenario testing
21. **Context Manager** - Async context manager

### Endpoint Coverage (4)
- **Endpoint Completeness** - All 9 methods present
- **Base URL Configuration** - Correct API endpoint
- **Export Format Extensibility** - Easy to add formats
- **MIME Type Extensibility** - Easy to add MIME types

## What Gets Tested with Real API

### 9 Core Methods
✅ list_files() - List with filtering, pagination, ordering
✅ get_file_metadata() - Get file information
✅ read_document_content() - Extract text from documents
✅ create_document() - Create documents and folders
✅ upload_file() - Upload files to Drive
✅ delete_file() - Delete files (soft and permanent)
✅ share_file() - Share and manage permissions
✅ export_document() - Export to multiple formats
✅ health_check() - Verify API connectivity

### 10 Export Formats
PDF • DOCX • XLSX • CSV • JSON • ODT • ODS • RTF • TXT • ZIP

### Error Scenarios
- 401 (Authentication) → GoogleDriveAuthError
- 403 (Quota Exceeded) → GoogleDriveQuotaExceeded
- 403 (Permission Denied) → GoogleDriveError
- 404 (Not Found) → GoogleDriveError
- 429 (Rate Limited) → GoogleDriveRateLimitError
- Timeout → Automatic retry
- Network errors → Automatic retry

## Running All Tests Together

To verify complete implementation with both unit and integration tests:

```bash
# Unit tests (32 tests, 0.03s, no API calls)
pytest app/backend/__tests__/unit/integrations/google_drive/ -v

# Integration tests (25 tests, 45-60s, real API)
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v

# All tests together (57 total)
pytest app/backend/__tests__/unit/integrations/google_drive/ \
        app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

## Success Criteria

You've successfully completed the setup when you see:

```
======================== 25 passed in 45.23s ========================
```

All tests passing means:
✅ 100% endpoint coverage verified with real API
✅ All 10 export formats working
✅ All 7 error scenarios handled correctly
✅ Retry logic functioning properly
✅ No exceptions or failures

## Next Steps

Once integration tests pass:

1. **Review Results** - Check test output for any warnings
2. **Clean Up Test Files** - Optionally delete test-created files from Google Drive
3. **Integrate into CI/CD** - Add to GitHub Actions or other CI pipeline
4. **Production Deployment** - Deploy with confidence that all endpoints work

---

**Created**: December 22, 2024
**Last Updated**: December 22, 2024
