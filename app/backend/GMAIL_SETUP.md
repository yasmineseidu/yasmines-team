# Gmail API Setup Guide

<!-- pragma: allowlist secret -->
<!-- This document contains example code and test credentials for documentation purposes only. -->
<!-- See [Security Best Practices](#security-best-practices) section below. -->

Complete guide for setting up Gmail API with service account authentication.

**Note:** This document contains example code and test credentials for documentation purposes only. See [Security Best Practices](#security-best-practices) section below.

---

## Quick Start

### 1. Get Service Account JSON from Google Cloud

Follow the [Google Cloud Setup Guide](../../docs/GOOGLE_CLOUD_SERVICE_ACCOUNT_SETUP.md) to:
- Create a Google Cloud project
- Enable Gmail API
- Create a service account
- Download the `service-account.json` file

### 2. Place Service Account File

```bash
# Copy your downloaded service-account.json to the credentials folder
cp ~/Downloads/service-account.json app/backend/config/credentials/gmail-service-account.json

# Verify it's there
ls app/backend/config/credentials/
# Output should show: gmail-service-account.json, .gitkeep
```

### 3. Set Up Environment

```bash
# Copy the example environment file
cp app/backend/.env.example app/backend/.env

# The .env file will use the credentials file automatically
# (No need to set GMAIL_SERVICE_ACCOUNT_PATH if using default location)
```

### 4. Use in Your Code

**Option A: Using the credentials loader utility**

```python
from config.credentials_loader import load_gmail_service_account
from src.integrations.gmail import GmailClient

async def setup_gmail():
    # Load credentials from file or environment
    creds = load_gmail_service_account()
    if not creds:
        raise Exception("Gmail credentials not found")

    # Create client
    client = GmailClient(credentials_json=creds)
    await client.authenticate()

    return client

# Use it
gmail = await setup_gmail()
messages = await gmail.list_messages()
```

**Option B: Direct file path**

```python
from src.integrations.gmail import GmailClient

async def setup_gmail():
    client = GmailClient(credentials_json="config/credentials/gmail-service-account.json")
    await client.authenticate()
    return client
```

**Option C: From environment variable**

```bash
# In .env
GMAIL_SERVICE_ACCOUNT_JSON=$(cat config/credentials/gmail-service-account.json)
```

---

## File Locations

```
app/backend/
├── config/
│   ├── credentials/                    # All credentials here
│   │   ├── .gitkeep                    # Keep folder in git
│   │   └── gmail-service-account.json  # ← Place your file here
│   │                                   #   (ignored by .gitignore)
│   └── credentials_loader.py           # Utility to load credentials
├── .env                                # Local config (not in git)
├── .env.example                        # Template for team
└── GMAIL_SETUP.md                      # This file
```

---

## Three Ways to Provide Credentials

### Method 1: Service Account File (Recommended for Production)

```python
# Automatically loads from default location
creds = load_gmail_service_account()

# Or specify path explicitly
client = GmailClient(credentials_json="config/credentials/gmail-service-account.json")
```

**Best for:** Backend services, scheduled jobs, server applications

### Method 2: OAuth 2.0 Tokens (User-Specific)

```python
# Load from environment variables
client = GmailClient(
    access_token=os.getenv("GMAIL_ACCESS_TOKEN"),
    refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
)
```

**Best for:** User-specific access, web applications

### Method 3: Pre-generated Token (Development Only)

```python
# Simple token for testing
client = GmailClient(access_token="ya29...")
```

**Best for:** Development, testing, short-lived tokens

---

## Environment Variables

### Available Options in .env

```bash
# Service Account (Method 1)
GMAIL_SERVICE_ACCOUNT_PATH=config/credentials/gmail-service-account.json
# OR
GMAIL_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# OAuth 2.0 (Method 2)
GMAIL_ACCESS_TOKEN=ya29...
GMAIL_REFRESH_TOKEN=1//...
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=secret...

# Testing
TEST_EMAIL=your-test-email@gmail.com
```

### Loading from Code

```python
import os

# Service account path
service_account_path = os.getenv("GMAIL_SERVICE_ACCOUNT_PATH", "config/credentials/gmail-service-account.json")

# OAuth tokens
access_token = os.getenv("GMAIL_ACCESS_TOKEN")
refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
```

---

## For Team Members

### Setup Steps

1. **Get the template**
   ```bash
   cp app/backend/.env.example app/backend/.env
   ```

2. **Add your credentials** (one method only):
   - **Service Account:** Get JSON from Google Cloud, save to `config/credentials/gmail-service-account.json`
   - **OAuth 2.0:** Get tokens from Google, add to `.env`
   - **Pre-generated Token:** Get token, add to `.env`

3. **Verify it works**
   ```python
   from config.credentials_loader import load_gmail_service_account

   creds = load_gmail_service_account()
   print(creds)  # Should print your credentials dict
   ```

---

## Security Best Practices

⚠️ **CRITICAL - Never commit credentials to git:**

```bash
# Your .env file and credentials are ignored:
app/backend/.env                              # ✅ Ignored
app/backend/config/credentials/*.json         # ✅ Ignored

# These will trigger git warnings:
# - Committing .env files
# - Committing JSON files with private keys
# - Committing credentials in code
```

### For Production Deployment

```bash
# Option 1: Use environment variables
export GMAIL_SERVICE_ACCOUNT_JSON=$(cat service-account.json)

# Option 2: Use secrets manager
# AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, etc.

# Option 3: Docker volumes
docker run -v /secure/path/creds.json:/app/config/credentials/gmail-service-account.json app
```

---

## Troubleshooting

### "File not found" Error

```
FileNotFoundError: config/credentials/gmail-service-account.json
```

**Solution:** Make sure your service account JSON is in the correct location:
```bash
ls -la app/backend/config/credentials/
```

### "Invalid credentials" Error

```
GmailAuthError: Failed to authenticate
```

**Solution:**
1. Verify the JSON file is valid (not corrupted)
2. Check that `private_key` field starts with `-----BEGIN PRIVATE KEY-----`
3. Ensure all required fields are present: `type`, `private_key`, `client_email`, `token_uri`

### "No credentials found" Warning

```
WARNING: Gmail credentials not found
```

**Solution:**
1. Check `.env` file exists
2. Verify service account JSON is at `config/credentials/gmail-service-account.json`
3. Or set `GMAIL_SERVICE_ACCOUNT_JSON` environment variable

### "google-auth library not found"

```
ImportError: No module named 'google.auth'
```

**Solution:**
```bash
pip install google-auth
```

---

## Example: Full Setup

```bash
# 1. Download from Google Cloud Console
# Save as: ~/Downloads/service-account-123456.json

# 2. Copy to project
cp ~/Downloads/service-account-123456.json \
   app/backend/config/credentials/gmail-service-account.json

# 3. Create .env
cp app/backend/.env.example app/backend/.env

# 4. Verify
python3 -c "
from config.credentials_loader import load_gmail_service_account
creds = load_gmail_service_account()
print(f'✅ Loaded credentials for: {creds[\"client_email\"]}')
"
```

---

## Testing Your Setup

```python
# test_gmail_setup.py
import asyncio
from config.credentials_loader import get_gmail_client_config
from src.integrations.gmail import GmailClient

async def test_gmail_setup():
    # Get config from environment or file
    config = get_gmail_client_config()

    if not config:
        print("❌ No Gmail credentials found")
        return

    # Create and authenticate client
    client = GmailClient(**config)
    await client.authenticate()

    # Test basic operation
    profile = await client.get_user_profile()
    print(f"✅ Successfully authenticated as: {profile['emailAddress']}")
    print(f"   Total messages: {profile['messagesTotal']}")
    print(f"   Total threads: {profile['threadsTotal']}")

# Run test
if __name__ == "__main__":
    asyncio.run(test_gmail_setup())
```

Run it:
```bash
cd app/backend
python test_gmail_setup.py
```

---

## Next Steps

- [Read Gmail Messages](../src/integrations/gmail/README.md#listing-messages)
- [Send Emails](../src/integrations/gmail/README.md#sending-messages)
- [Manage Labels](../src/integrations/gmail/README.md#managing-labels)
- [Full API Reference](../src/integrations/gmail/README.md)
