# Google Drive Integration - Authentication Guide

**Complete guide to authenticate and test Google Drive integration without user OAuth.**

## Overview

The Google Drive client supports three authentication methods:

1. **Service Account (Recommended for Production)** ✅ No user interaction needed
2. **OAuth 2.0 User Authorization** ✅ Standard Google OAuth flow
3. **Pre-generated Access Token** ✅ Simple token reuse

---

## Option 1: Service Account Authentication (Recommended for Production)

Service account authentication is **perfect for production** because:
- ✅ No user interaction required
- ✅ Credentials stored securely on server
- ✅ Can be used in CI/CD pipelines
- ✅ Automatic token refresh
- ✅ Works server-to-server

### Prerequisites
- `pip install google-auth`

### Setup Steps

#### Step 1: Create Service Account in Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Go to **Service Accounts** (search in top bar)
4. Click **Create Service Account**
5. Fill in service account name and description
6. Click **Create and Continue**
7. Grant the service account these roles:
   - **Editor** (for full Drive access)
   - OR **Basic > Editor** for minimal permissions
8. Click **Continue** then **Done**

#### Step 2: Create and Download JSON Key

1. In Service Accounts, click on the newly created account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Click **Create**
6. **Save the downloaded JSON file** somewhere safe

#### Step 3: Grant Drive Access to Service Account

The service account email (in the JSON file) needs Drive access:

1. Open your Google Drive
2. Find or create a shared folder
3. Right-click → **Share**
4. Add the service account email (from JSON file)
5. Grant **Editor** access
6. Click **Share**

#### Step 4: Set Up Environment

```bash
# Save the service account JSON file
mv ~/Downloads/your-service-account-key.json ./google_service_account.json

# Set environment variable
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"

# Or add to .env
echo 'GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"' >> .env
```

#### Step 5: Run Tests

```bash
# Set the environment variable
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"

# Run integration tests
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

**Expected Result**: All 25 tests pass ✅

---

## Option 2: OAuth 2.0 User Authorization

Use this if you want user-based authentication (like a web app where users authorize access).

### Setup Steps

#### Step 1: Get Authorization Code (1 minute)

Visit this URL in your browser:
```
https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline
```

Steps:
1. Click the link above
2. Log in with your Google account
3. Click **Grant** to authorize Claude Code to access Google Drive
4. You'll be redirected to: `http://localhost:8000/api/google/callback?code=XXXXXX...`
5. **Copy the code** (the long string after `code=`)

#### Step 2: Exchange Code for Token (30 seconds)

```bash
# Set credentials
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}"

# Exchange code for token
python3 app/backend/scripts/exchange_oauth_code.py <your-code-here>
```

Example:
```bash
python3 app/backend/scripts/exchange_oauth_code.py 4/0AX4XfWiXxQp2_vwkK9z...
```

This will:
- ✅ Exchange your code for an access token
- ✅ Save token to `.google_drive_token.json`
- ✅ Display your token for verification

#### Step 3: Run Tests

```bash
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

**Expected Result**: All 25 tests pass ✅

---

## Option 3: Pre-generated Access Token

Use this if you already have an access token from either method above.

### Setup Steps

#### Step 1: Create Token File

Create `.google_drive_token.json`:

```json
{
  "access_token": "ya29.a0AfH6SMBx...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Where:
- `access_token` = Your Google Drive access token
- `token_type` = Always "Bearer"
- `expires_in` = Token lifetime in seconds

#### Step 2: Run Tests

```bash
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

**Expected Result**: All 25 tests pass ✅

---

## Comparison of Methods

| Feature | Service Account | OAuth 2.0 | Pre-generated Token |
|---------|-----------------|-----------|-------------------|
| **Production Ready** | ✅ Yes | ⚠️ Requires refresh token | ⚠️ Limited by expiry |
| **No User Interaction** | ✅ Yes | ❌ Need auth once | ✅ Yes |
| **Automatic Refresh** | ✅ Yes | ✅ Yes (with refresh token) | ❌ No |
| **CI/CD Friendly** | ✅ Yes | ⚠️ Need refresh token | ⚠️ Need token rotation |
| **Setup Complexity** | ⭐⭐⭐ Moderate | ⭐⭐ Simple | ⭐ Simplest |
| **Best For** | Production servers | User-facing apps | Testing/development |

---

## Choosing the Right Method

### Use Service Account if:
- ✅ Running on production server
- ✅ Need fully automated testing
- ✅ Using in CI/CD pipeline
- ✅ Server needs Drive access 24/7
- ✅ No user interaction wanted

### Use OAuth 2.0 if:
- ✅ Web app with user authorization
- ✅ User wants to connect their own Drive
- ✅ User-specific access needed
- ✅ Privacy/security important (user controls)

### Use Pre-generated Token if:
- ✅ Quick testing/development
- ✅ Short-term access needed
- ✅ Already have a valid token
- ✅ Want simplest setup

---

## Testing All Three Methods

### Test Service Account
```bash
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

### Test OAuth 2.0
```bash
# After running exchange_oauth_code.py
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

### Test Pre-generated Token
```bash
# With .google_drive_token.json created
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

---

## Troubleshooting

### Error: "Service account authentication failed"

**Cause**: Service account JSON file invalid or missing permissions

**Solution**:
1. Verify file path is correct
2. Check file is valid JSON
3. Verify service account has Drive access
4. Try re-downloading the key

### Error: "Not authenticated. Call authenticate() first"

**Cause**: Token is missing or invalid

**Solution**:
1. Regenerate token using your chosen method
2. Verify token file format
3. Check token hasn't expired
4. Ensure environment variables are set

### Error: "Permission denied: 403"

**Cause**: Service account doesn't have access to the file/folder

**Solution**:
1. Check service account email has Drive access
2. Verify folder is shared with service account
3. Grant Editor role (not Viewer)
4. Try accessing a shared folder instead

### Error: "google-auth not installed"

**Cause**: google-auth library not installed

**Solution**:
```bash
pip install google-auth
```

---

## Security Considerations

### Service Account Keys
- ✅ Keep JSON file **PRIVATE** (never commit to git)
- ✅ Rotate keys regularly (every 6 months)
- ✅ Use environment variables (not hardcoded paths)
- ✅ Limit service account permissions to minimum needed
- ✅ Monitor service account usage in Cloud Console

### OAuth Tokens
- ✅ Keep tokens **PRIVATE** (never commit to git)
- ✅ Tokens expire automatically (1 hour)
- ✅ Use refresh tokens for long-lived access
- ✅ Revoke access if compromised
- ✅ Never log or display full tokens

### Pre-generated Tokens
- ✅ Keep tokens **PRIVATE** (never commit to git)
- ✅ Rotate frequently (daily or weekly)
- ✅ Use with short expiry times
- ✅ Not recommended for production

---

## Production Deployment

### Recommended: Service Account + Environment Variables

```bash
# 1. Create service account in Google Cloud Console
# 2. Download JSON key
# 3. Set environment variable (securely)
export GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/key.json"

# 4. Code automatically uses it
client = GoogleDriveClient(credentials_json={
    "type": "service_account",
    "client_id": "...",
    "client_secret": "..."
})
await client.authenticate()  # Automatically generates token
```

### For Kubernetes/Docker

```dockerfile
# Dockerfile
FROM python:3.11

# Copy service account key
COPY google_service_account.json /app/keys/

ENV GOOGLE_SERVICE_ACCOUNT_FILE=/app/keys/google_service_account.json

# Run app
CMD ["python", "app.py"]
```

### For GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create service account key
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
        run: echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > google_service_account.json

      - name: Run tests
        env:
          GOOGLE_SERVICE_ACCOUNT_FILE: ./google_service_account.json
        run: pytest app/backend/__tests__/integration/google_drive/ -v
```

---

## Quick Start Commands

### Method 1: Service Account (Fastest Production Setup)
```bash
# Create service account in Google Cloud Console and download key
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

### Method 2: OAuth 2.0 (Easy Manual Setup)
```bash
# Visit URL, authorize, copy code
python3 app/backend/scripts/exchange_oauth_code.py <code>
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

### Method 3: Pre-generated Token (Simplest)
```bash
# Create .google_drive_token.json with access_token
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

---

## Additional Resources

- [Google Cloud Console](https://console.cloud.google.com/)
- [Service Accounts Documentation](https://cloud.google.com/iam/docs/service-accounts)
- [Google Drive API v3](https://developers.google.com/drive/api/v3)
- [Google Auth Library for Python](https://google-auth.readthedocs.io/)
- [OAuth 2.0 Flow](https://developers.google.com/identity/protocols/oauth2)

---

## Support

For issues:
1. Check the **Troubleshooting** section above
2. Review test output for error messages
3. Verify environment variables are set correctly
4. Check that credentials file is valid JSON

---

**Created**: December 22, 2024
**Updated**: December 22, 2024
**Status**: ✅ Production Ready
