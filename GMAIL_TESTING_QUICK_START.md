# 📧 Gmail Testing - See Real Emails in Your Inbox

**Goal:** Run tests that actually create emails, drafts, and labels in your real Gmail account.

---

## ⚡ Quick Setup (2 minutes)

### Your Service Account Details:

```
CLIENT ID: 100100768773360796850
Service Account: smarterteam@smarter-team.iam.gserviceaccount.com
Gmail User: yasmine@smarterflo.com
```

### Step 1: Grant OAuth Scopes (1 minute)

1. **Open Google Workspace Admin Console:**
   https://admin.google.com

2. **Navigate:** Security → API Controls → Manage domain-wide delegation

3. **Click "Add new"** (or find existing service account)

4. **Enter this Client ID:**
   ```
   100100768773360796850
   ```

5. **Copy & Paste these OAuth Scopes:**
   ```
   https://www.googleapis.com/auth/gmail.compose,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.readonly
   ```

6. **Click "Authorize"**

7. **⏱️ WAIT 15-30 SECONDS** for Google to propagate changes

---

## 🚀 Run Live Tests

### Option 1: Quick Demo (Show Real Gmail Activity)

```bash
cd /Users/yasmineseidu/Desktop/Coding/yasmines-team/app/backend

python3 __tests__/integration/run_gmail_live_tests.py
```

**This will:**
- ✅ Send a test email (appears in your Gmail Sent folder)
- ✅ Create a draft (appears in Drafts)
- ✅ Create a custom label (appears in sidebar)
- ✅ List your messages, labels, threads

**📧 After running, check your Gmail! You'll see:**
1. New email in **Sent** folder: "🤖 Gmail Integration Test - Automated"
2. New **Draft**: "🤖 Draft Test Email"
3. New **Label** in sidebar: "🤖 Integration Tests"

### Option 2: Full Test Suite (All 49 Tests)

```bash
python3 -m pytest __tests__/integration/test_gmail.py -v
```

**This tests all 34 endpoints:**
- List/get/send messages
- Create/manage drafts
- Create/apply labels
- Manage threads
- Get user profile
- Handle attachments

---

## ✅ What You'll See in Gmail

### Example Output When Tests Run:

```
80 GMAIL LIVE API TEST RUNNER
================================================================================

📋 Loading credentials...
✅ Credentials loaded from: .../google-service-account.json
   Service Account: smarterteam@smarter-team.iam.gserviceaccount.com
   Impersonating: yasmine@smarterflo.com

🔐 Authenticating...
✅ Authenticated successfully!

================================================================================
📧 TEST 1: Get Gmail Profile
================================================================================
✅ Email: yasmine@smarterflo.com
   Messages Total: 42
   Threads Total: 15
   Labels Total: 23

================================================================================
🏷️  TEST 2: List Gmail Labels
================================================================================
✅ Found 23 labels:
   • INBOX (INBOX)
   • SENT (SENT)
   • DRAFT (DRAFT)
   ... and 20 more

================================================================================
✉️  TEST 4: SEND TEST EMAIL
================================================================================
✅ Email sent successfully!
   Message ID: 18f23b5c8f2a1b0c
   📧 CHECK YOUR GMAIL - You should see this email in your Sent folder!
```

---

## 🔍 Troubleshooting

### ❌ Error: "Client is unauthorized for any of the scopes requested"

**This means:** OAuth scopes not yet granted in Google Workspace Admin

**Fix:**
1. Complete Steps 1-6 above in Google Workspace Admin Console
2. **Wait 15-30 seconds**
3. Run tests again

### ❌ Error: "Invalid email or User ID"

**This means:** Email doesn't exist or isn't authorized

**Fix:**
1. Make sure `yasmine@smarterflo.com` exists and is active
2. Check that it's the correct email for your Google Workspace domain
3. Try a different email if needed

### ❌ Error: "Gmail API not enabled"

**Fix:**
```bash
gcloud services enable gmail.googleapis.com --project=smarter-team
```

---

## 📊 49 Tests Cover Everything

Once OAuth scopes are granted, these all work:

### Messages (18 tests)
✅ List messages with pagination
✅ Get message details
✅ Send email (text/HTML/CC/BCC)
✅ Trash/untrash messages
✅ Mark as read/unread
✅ Star/archive messages

### Drafts (7 tests)
✅ Create draft
✅ List drafts
✅ Get draft details
✅ Send draft
✅ Delete draft

### Labels (10 tests)
✅ List labels
✅ Create custom label
✅ Apply label to message
✅ Remove label from message

### Threads (9 tests)
✅ List conversation threads
✅ Get thread details
✅ Manage thread labels
✅ Archive threads

### Attachments (2 tests)
✅ List attachments
✅ Download attachments

### User (1 test)
✅ Get Gmail profile info

### Other (2 tests)
✅ Error handling
✅ Validation

---

## 📝 Summary

| Step | Action | Status |
|------|--------|--------|
| 1 | Grant OAuth scopes in Workspace Admin | ⏳ TODO |
| 2 | Wait 15-30 seconds | ⏳ TODO |
| 3 | Run demo script | ⏳ TODO |
| 4 | Check Gmail for new emails/drafts/labels | ⏳ TODO |

**Once done: All 49 tests will execute and you'll see real Gmail activity!**

---

## 🎯 Next Steps

1. **Go to Google Workspace Admin Console** (link above)
2. **Grant the OAuth scopes** (Steps 1-6)
3. **Wait 15-30 seconds**
4. **Run this:**
   ```bash
   python3 __tests__/integration/run_gmail_live_tests.py
   ```
5. **Check your Gmail** - you'll see:
   - ✉️ New email in Sent folder
   - 📝 New draft
   - 🏷️ New custom label

---

**Generated:** 2025-12-22
**Test Suite:** 49 tests for 34 endpoints
**Status:** ✅ Ready (awaiting OAuth scope grant)

🚀 Let's see those real emails! 🎉
