# Google Drive Integration - Production Setup Guide

**Production-ready authentication without user OAuth. Server-to-server using Google Service Account.**

---

## The Right Way: Service Account Authentication

For production, use **Google Service Account** - no user interaction required, secure, automated.

---

## Quick Setup (5 minutes)

### Step 1: Create Service Account in Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Search for "Service Accounts"
4. Click **Create Service Account**
5. Name: `claude-drive` (or your choice)
6. Click **Create and Continue**
7. On roles page, select **Editor** (or more specific role)
8. Click **Continue** then **Done**

### Step 2: Create and Download JSON Key

1. In Service Accounts, click the service account you just created
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Click **Create**
6. File downloads automatically as `[projectid]-[keyid].json`
7. **Save this file securely** - it's your service account credentials

### Step 3: Grant Service Account Drive Access

Service account needs permission to access your Drive:

1. Open [Google Drive](https://drive.google.com/)
2. Create a shared folder for the app (e.g., "Claude Drive Access")
3. Right-click folder → **Share**
4. In the JSON file you downloaded, find the email like: `claude-drive@projectid.iam.gserviceaccount.com`
5. Copy that email and paste it in the Share dialog
6. Grant **Editor** access
7. Click **Share**

### Step 4: Set Environment Variable

```bash
# Save the JSON file to your project
mv ~/Downloads/[projectid]-[keyid].json ./google_service_account.json

# Add to .env or set in environment
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"

# For production, add to Docker/Kubernetes secrets instead
```

### Step 5: Test It

```bash
# Install google-auth library (one-time)
pip install google-auth

# Set environment variable
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"

# Run integration tests
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

**Expected output:**
```
======================== 25 passed in 45.23s ========================
```

---

## Use in Production Code

### Simple Usage

```python
from src.integrations.google_drive.client import GoogleDriveClient

# Client automatically uses GOOGLE_SERVICE_ACCOUNT_FILE if set
# No manual token management needed
client = GoogleDriveClient(credentials_json={
    "type": "service_account",
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
})

# Authenticate (generates token automatically)
await client.authenticate()

# Use it
files = await client.list_files(page_size=10)
```

### With Context Manager

```python
from src.integrations.google_drive.client import GoogleDriveClient

async with GoogleDriveClient(
    credentials_json={
        "type": "service_account",
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
    }
) as client:
    await client.authenticate()
    files = await client.list_files()
```

---

## Environment Setup for Production

### Option 1: .env File (Development)

```env
GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"
```

### Option 2: Docker (Recommended)

```dockerfile
FROM python:3.11

WORKDIR /app

# Copy service account key
COPY google_service_account.json /app/secrets/

ENV GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/google_service_account.json

COPY . .
RUN pip install -r requirements.txt

CMD ["python", "app.py"]
```

### Option 3: Kubernetes Secrets (Best Practice)

```bash
# Create secret from service account JSON
kubectl create secret generic google-drive-sa \
  --from-file=google_service_account.json

# Reference in deployment
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:latest
    env:
    - name: GOOGLE_SERVICE_ACCOUNT_FILE
      value: /secrets/google_service_account.json
    volumeMounts:
    - name: google-sa
      mountPath: /secrets
      readOnly: true
  volumes:
  - name: google-sa
    secret:
      secretName: google-drive-sa
```

### Option 4: AWS Secrets Manager

```python
import boto3
import json

# Fetch from Secrets Manager
sm = boto3.client('secretsmanager')
secret = sm.get_secret_value(SecretId='google-drive-sa')
sa_json = json.loads(secret['SecretString'])

client = GoogleDriveClient(credentials_json=sa_json)
await client.authenticate()
```

### Option 5: GitHub Actions

```yaml
name: Google Drive Tests

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create service account secret
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
        run: echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > google_service_account.json

      - name: Run tests
        env:
          GOOGLE_SERVICE_ACCOUNT_FILE: ./google_service_account.json
        run: pytest app/backend/__tests__/integration/google_drive/ -v
```

**Note:** Add your service account JSON as a GitHub Actions secret (repo settings → secrets)

---

## Verification

### Verify Service Account Has Drive Access

```bash
# Run this to test authentication works
export GOOGLE_SERVICE_ACCOUNT_FILE="./google_service_account.json"
python3 app/backend/scripts/generate_service_account_token.py
```

Expected output:
```
🔐 Generating Access Token from Service Account
============================================================

✅ Success!

Access Token: ya29.a0AfH6SMBx...
Token Type: Bearer
Expires In: 3600 seconds

💾 Token saved to: .google_drive_token.json

Now you can run integration tests:
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

### Run Full Test Suite

```bash
# Unit tests (no API calls)
pytest app/backend/__tests__/unit/integrations/google_drive/ -v

# Integration tests (with API)
pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v

# Everything
pytest app/backend/__tests__/unit/integrations/google_drive/ \
        app/backend/__tests__/integration/google_drive/test_live_api.py -v
```

Expected: **57 tests passing** ✅

---

## Security Best Practices

### ✅ DO

- ✅ Store JSON file **outside** version control (add to .gitignore)
- ✅ Use environment variables for file path
- ✅ Limit service account permissions to minimum needed (not Editor)
- ✅ Rotate keys regularly (every 6 months)
- ✅ Audit service account usage in Cloud Console
- ✅ Monitor Drive access logs

### ❌ DON'T

- ❌ Don't commit JSON file to git
- ❌ Don't hardcode file paths
- ❌ Don't grant more permissions than needed
- ❌ Don't leave old keys lying around
- ❌ Don't use same account for all environments

### Recommended Permissions

Instead of **Editor**, use a more restrictive role:

```json
{
  "role": "roles/drive.fileEditor"
}
```

Or create a custom role with only needed permissions:
- `drive.files.list`
- `drive.files.get`
- `drive.files.create`
- `drive.files.delete`
- `drive.files.update`

---

## Troubleshooting

### Error: "Service account authentication failed"

```
Cause: JSON file invalid or missing
Solution:
  1. Check file exists: ls -la ./google_service_account.json
  2. Verify JSON is valid: python3 -m json.tool google_service_account.json
  3. Check file has "type": "service_account"
  4. Re-download key from Google Cloud Console
```

### Error: "Permission denied: 403"

```
Cause: Service account doesn't have Drive access
Solution:
  1. Find service account email in JSON file
  2. Share the Drive folder with that email
  3. Grant Editor role (not Viewer)
  4. Wait a few seconds for permissions to propagate
  5. Try again
```

### Error: "Not authenticated"

```
Cause: authenticate() not called
Solution:
  await client.authenticate()  # Call this first
  files = await client.list_files()
```

### Error: "google-auth library not found"

```
Cause: google-auth not installed
Solution:
  pip install google-auth
```

---

## Monitoring & Maintenance

### Check Service Account Usage

1. In Google Cloud Console
2. Go to **Service Accounts**
3. Click on your service account
4. View **Activity** to see when it's used

### View Drive Audit Log

1. In Google Cloud Console
2. Go to **Logs** → **Log Explorer**
3. Filter for your service account
4. Monitor for errors or unusual access

### Rotate Keys Regularly

Every 6 months:
1. Create new JSON key (same steps as above)
2. Update in production with new file
3. Delete old key in Cloud Console

---

## Complete Production Checklist

- [ ] Service account created in Google Cloud
- [ ] JSON key downloaded and stored securely
- [ ] Service account email shared with Drive folder
- [ ] GOOGLE_SERVICE_ACCOUNT_FILE environment variable set
- [ ] google-auth library installed
- [ ] Unit tests passing (pytest unit/)
- [ ] Integration tests passing (pytest integration/)
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Backup/disaster recovery plan
- [ ] Security audit completed

---

## Support Resources

- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Google Drive API v3](https://developers.google.com/drive/api/v3)
- [Google Auth Library](https://google-auth.readthedocs.io/)
- [Google Cloud Console](https://console.cloud.google.com/)

---

## Next Steps

1. **Create service account** (5 minutes) - Follow Step 1 above
2. **Download JSON key** (1 minute) - Follow Step 2 above
3. **Grant Drive access** (2 minutes) - Follow Step 3 above
4. **Run tests** (1 minute) - Follow Step 5 above
5. **Deploy to production** - Use one of the environment setup options

**Total time: ~10 minutes to production-ready setup** ✅

---

**Status**: Production Ready
**Created**: December 22, 2024
**Last Updated**: December 22, 2024
