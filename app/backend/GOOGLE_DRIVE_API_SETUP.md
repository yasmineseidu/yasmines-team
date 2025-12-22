# 🔧 Google Drive API Setup for Live Testing

## Status: ✅ Authentication Working!

Your credentials and JWT token generation are working perfectly. Now you need to **enable the Google Drive API** in your Google Cloud project.

## Quick Setup (2 minutes)

### Step 1: Enable Google Drive API

1. **Open Google Cloud Console:**
   - Go to: https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=247543540942

2. **Click "ENABLE" button** (top of the page)

3. **Wait 30-60 seconds** for it to propagate

4. **Run tests again:**
   ```bash
   cd app/backend
   python3 __tests__/integration/run_google_drive_live_tests.py
   ```

### Step 2: Verify Setup

After enabling, you should see:
```
✅ Credentials loaded successfully
✅ Token generated via google-auth
✅ Client initialized with access token
🧪 RUNNING LIVE API TESTS
   ▶️  Testing: health_check
   ✅ PASSED
```

---

## What This Setup Does

| Component | Status | Details |
|-----------|--------|---------|
| **Service Account Credentials** | ✅ Loaded | `smarterteam@smarter-team.iam.gserviceaccount.com` |
| **JWT Token Generation** | ✅ Working | Generates 1024-char access tokens |
| **API Authentication** | ✅ Valid | Tokens properly signed and formatted |
| **Google Drive API** | ❌ Disabled | **NEEDS ENABLING** (see Step 1) |

---

## Live Testing Features

Once API is enabled, tests will automatically:

1. **✅ Health Check** - Verify API connectivity
2. **✅ List Files** - Retrieve files from your Drive
3. **✅ Create Documents** - Create test Google Docs
4. **✅ Get Metadata** - Retrieve file information
5. **✅ Share Files** - Test permission management
6. **✅ Export Documents** - Export to PDF, DOCX, etc.
7. **✅ Upload Files** - Test file uploads
8. **✅ Delete Files** - Clean up test data
9. **✅ Auto-Cleanup** - Remove all test files after testing

---

## Project Configuration

```json
{
  "project_id": "smarter-team",
  "service_account": "smarterteam@smarter-team.iam.gserviceaccount.com",
  "credentials_file": "app/backend/config/credentials/google-service-account.json",
  "scopes": ["https://www.googleapis.com/auth/drive"],
  "test_endpoints": 10,
  "test_cases": 8
}
```

---

## Troubleshooting

### Issue: "API has not been used in project"

**Solution:** Enable the Google Drive API (see Step 1 above)

### Issue: "Permission denied"

**Solution:** Make sure service account has Drive scope in Google Cloud Console:
1. Go to Service Accounts
2. Click the service account email
3. Go to "Keys" tab
4. Verify the key exists (it's already configured)

### Issue: "Invalid token"

**Solution:** Token expires after 1 hour. Tests automatically generate a fresh token each run.

---

## Testing After Setup

### Run All Live Tests

```bash
cd app/backend
python3 __tests__/integration/run_google_drive_live_tests.py
```

### Expected Output

```
📋 LOADING CREDENTIALS
✅ Credentials loaded successfully
   Type: service_account
   Project: smarter-team
   Email: smarterteam@smarter-team.iam.gserviceaccount.com

🔐 GENERATING ACCESS TOKEN
✅ Token generated via google-auth
   Token length: 1024 chars

🔗 INITIALIZING CLIENT
✅ Client initialized with access token
   Health check: Google Drive API is accessible

🧪 RUNNING LIVE API TESTS
▶️  Testing: health_check
   ✅ PASSED
▶️  Testing: list_files
   ✅ PASSED
▶️  Testing: create_document
   ✅ PASSED
▶️  Testing: get_file_metadata
   ✅ PASSED
▶️  Testing: share_file
   ✅ PASSED
▶️  Testing: export_document
   ✅ PASSED
▶️  Testing: upload_file
   ✅ PASSED
▶️  Testing: delete_file
   ✅ PASSED

🧹 CLEANING UP TEST DATA
✅ Deleted test file: [file_id]

📊 LIVE API TEST REPORT
🎯 RESULTS
   Passed: 8/8
   Failed: 0/8

   ✅ 100% SUCCESS RATE - ALL ENDPOINTS PASSING!

📋 ENDPOINT STATUS
✅ PASS                  health_check
✅ PASS                  list_files
✅ PASS                  create_document
✅ PASS                  get_file_metadata
✅ PASS                  share_file
✅ PASS                  export_document
✅ PASS                  upload_file
✅ PASS                  delete_file
```

---

## What Happens During Testing

### Data Creation
- Creates test documents and files
- Tests all operations on live Drive
- Generates realistic test data

### Auto-Cleanup
- All created files are automatically deleted
- No orphaned test data left behind
- Reports what was created and cleaned up

### Error Handling
- Tests proper error responses
- Validates error messages
- Checks status codes

### Future-Proofing
- Tests auto-discover new endpoints
- Extensible test framework
- Sample data for new endpoint types

---

## Next Steps

1. **Enable Google Drive API** (Step 1 above)
2. **Run live tests:** `python3 __tests__/integration/run_google_drive_live_tests.py`
3. **Verify 100% pass rate** ✅
4. **Review test report:** `__tests__/integration/LIVE_TEST_REPORT.json`

---

## API Limits (FYI)

- ✅ 12,000 requests per 60 seconds (tests use ~8)
- ✅ 750 GB daily upload limit
- ✅ 5 TB max file size
- ✅ No rate limiting issues for tests

---

Generated: 2025-12-22

🤖 Ready for live testing with Claude Code
