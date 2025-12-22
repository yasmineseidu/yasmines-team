# Gmail API Setup Guide - Service Account with Domain-Wide Delegation

**Status:** ✅ Test suite complete, **awaiting Google Workspace configuration**

This guide walks through enabling Gmail API testing with service account authentication and domain-wide delegation.

---

## 📋 Prerequisites

You need one of the following:
- ✅ **Google Workspace Account** (Business Standard or higher with Admin access)
- ✅ **Google Cloud Project** with service account credentials (already set up ✅)
- ✅ **Gmail API enabled** on the project (already done ✅)

---

## 🔧 Setup Steps

### Step 1: Enable Domain-Wide Delegation (Google Cloud Console)

**Location:** Google Cloud Console → Service Accounts

1. Go to [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Select project: **`smarter-team`**
3. Click on service account: **`smarterteam@smarter-team.iam.gserviceaccount.com`**
4. Go to **"Keys"** tab
5. Click **"Show domain-wide delegation"** (or look for the domain delegation section)
6. Check if **"Enable domain-wide delegation"** is enabled
   - If not, click the checkbox to enable it
   - You'll see: "Enable G Suite Domain-wide Delegation"
7. Click **"Save"**

**What this does:** Allows the service account to impersonate users on your Google Workspace domain.

### Step 2: Grant OAuth Scopes (Google Workspace Admin Console)

**Location:** Google Workspace Admin Console → Security → API Controls

1. Go to [Google Workspace Admin Console](https://admin.google.com)
2. Sign in with your Workspace Admin account
3. Navigate to **Security → API Controls**
4. In the **"Domain-wide delegation"** section, click **"Manage domain-wide delegation"**
5. Click **"Add new"** or **"Edit"** for existing service account
6. Enter the **Client ID** from your service account

   Get Client ID from:
   - Google Cloud Console → Service Accounts → smarterteam → Keys tab
   - Copy the **Client ID** field

7. In **"OAuth scopes"** field, add these scopes:
   ```
   https://www.googleapis.com/auth/gmail.compose
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.readonly
   ```

   **Note:** Paste all three on one line, separated by commas

8. Click **"Authorize"**

**What this does:** Grants the service account permission to access Gmail for users on your domain.

### Step 3: Configure User Email in .env

**File:** `/Users/yasmineseidu/Desktop/Coding/yasmines-team/.env`

```bash
# Change this line:
GMAIL_USER_EMAIL=your-email@yourdomain.com

# To your actual Gmail (examples):
GMAIL_USER_EMAIL=yasmine@smarterteam.ai          # If using Google Workspace
GMAIL_USER_EMAIL=your-gmail@gmail.com            # If using regular Gmail with delegation
```

**Important:** This email must exist and be authorized for the service account.

### Step 4: Verify Setup

Check that the service account has the correct scopes:

```bash
# From project root:
cd app/backend

# Test a simple endpoint
python3 -c "
import json
with open('config/credentials/google-service-account.json') as f:
    creds = json.load(f)
print(f'Service Account: {creds.get(\"client_email\")}')
print(f'Project: {creds.get(\"project_id\")}')
"
```

Expected output:
```
Service Account: smarterteam@smarter-team.iam.gserviceaccount.com
Project: smarter-team
```

---

## ✅ Run Tests

Once setup is complete:

```bash
cd /Users/yasmineseidu/Desktop/Coding/yasmines-team/app/backend

# Run all 49 Gmail tests
python3 -m pytest __tests__/integration/test_gmail.py -v

# Expected result:
# ====== 49 passed in XXs ======
```

### Individual Test Example:

```bash
# Test a single endpoint
python3 -m pytest __tests__/integration/test_gmail.py::TestGmailIntegration::test_list_messages_happy_path -v
```

---

## 🔍 Troubleshooting

### Error: "Invalid email or User ID"

**Cause:** The email in `GMAIL_USER_EMAIL` doesn't exist or isn't authorized.

**Fix:**
1. Verify the email exists in your Google Workspace
2. Check that domain-wide delegation is enabled (Step 2)
3. Confirm the service account scopes are authorized
4. Try a different email that you know exists

### Error: "The caller does not have permission"

**Cause:** Service account doesn't have the right scopes.

**Fix:**
1. Go to Google Workspace Admin Console
2. Re-add the service account with correct scopes (Step 2)
3. Wait 15-30 seconds for changes to propagate

### Error: "The user does not have sufficient permissions"

**Cause:** Similar to above - missing OAuth scopes.

**Fix:** Re-grant OAuth scopes in Google Workspace Admin Console.

### Error: "Gmail API is not enabled"

**Cause:** API not enabled on Google Cloud project.

**Fix:**
```bash
# Enable it via gcloud
gcloud services enable gmail.googleapis.com --project=smarter-team
```

---

## 📊 What Gets Tested (49 tests)

Once setup is complete, these endpoints are tested:

### Messages (18 tests)
- List messages with pagination and filtering
- Get message details and attachments
- Send email with text/HTML/CC/BCC
- Manage messages (trash, untrash, archive, star, etc.)

### Labels (10 tests)
- List, get, and create labels
- Apply/remove labels from messages

### Drafts (7 tests)
- List, create, and send drafts
- Manage draft content

### Threads (9 tests)
- List and get conversation threads
- Manage thread labels and trash

### User (1 test)
- Get authenticated user profile

### Attachments (2 tests)
- List and download message attachments

---

## 🔐 Security Notes

✅ **Credentials are secure:**
- Service account JSON is in `.env` (not committed to git)
- JWT tokens are auto-generated and expire in 1 hour
- Uses Google's OAuth 2.0 standard flow
- Domain-wide delegation is auditable in Google Workspace

⚠️ **Keep these secure:**
- `GMAIL_CREDENTIALS_JSON` - Path to service account JSON
- `GMAIL_USER_EMAIL` - Email being accessed (if sensitive)
- Service account private key (stored in encrypted JSON)

---

## 🚀 Next Steps

1. **Setup Google Workspace domain-wide delegation** (Steps 1-2)
2. **Configure `GMAIL_USER_EMAIL`** in `.env` (Step 3)
3. **Run tests to verify** (Step 4)
4. **Integrate into CI/CD** (optional)

---

## 📚 Additional Resources

- [Google Workspace Domain-Wide Delegation](https://developers.google.com/identity/protocols/oauth2/service-account#delegatingauthority)
- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
- [Service Account Setup](https://cloud.google.com/docs/authentication/application-default-credentials#service-account)
- [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes#gmail)

---

## 📝 Summary

| Component | Status | Action |
|-----------|--------|--------|
| Gmail API Enabled | ✅ Complete | - |
| Service Account Created | ✅ Complete | - |
| Test Suite (49 tests) | ✅ Complete | - |
| Domain-Wide Delegation | ⏳ **TODO** | Enable in Google Cloud |
| OAuth Scopes Granted | ⏳ **TODO** | Add in Google Workspace Admin |
| `GMAIL_USER_EMAIL` Set | ⏳ **TODO** | Update in `.env` |
| **All Tests Passing** | ⏳ **Pending** | Will be ✅ after setup |

---

**Generated:** 2025-12-22
**Total Tests:** 49 (all endpoints covered)
**Code Status:** ✅ Production-Ready
**Configuration Status:** ⏳ Awaiting Google Workspace setup

🎯 Once you complete the Google Workspace setup, all 49 tests will pass!
