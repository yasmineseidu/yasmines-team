# Google Workspace Domain-Wide Delegation Setup

Complete guide for setting up service account access to Gmail via domain-wide delegation.

**Purpose:** Allow service account to impersonate users in your Google Workspace domain.

---

## Prerequisites

✅ Google Cloud project with Gmail API enabled
✅ Service account created (`smarterteam@smarter-team.iam.gserviceaccount.com`)
✅ Google Workspace domain (`smarterteam.ai`)
✅ Admin access to both Google Cloud Console AND Google Workspace Admin Console

---

## Step 1: Enable Domain-Wide Delegation (Google Cloud Console)

This allows the service account to be delegated authority to access Gmail.

### 1a. Go to Service Accounts

```
https://console.cloud.google.com/iam-admin/serviceaccounts
```

### 1b. Find Your Service Account

Click on: `smarterteam@smarter-team.iam.gserviceaccount.com`

### 1c. Go to "Keys" Tab

Look for the "Keys" section on the service account page.

### 1d. Enable Domain-Wide Delegation

1. Scroll down to find "Domain-wide delegation" section
2. Click "Enable domain-wide delegation" button
3. You'll see a popup asking to confirm:
   - Service account: `smarterteam@smarter-team.iam.gserviceaccount.com`
   - Click "Enable domain-wide delegation"

### 1e. Copy the Client ID

After enabling, you'll see:
- **Client ID:** `123456789...` (copy this - you need it for Step 2)

---

## Step 2: Grant Gmail Scopes (Google Workspace Admin Console)

This grants the service account permission to access Gmail.

### 2a. Go to Admin Console

```
https://admin.google.com
```

### 2b. Navigate to Domain-Wide Delegation

1. Click **Security** (left sidebar)
2. Click **Access and data control**
3. Click **API controls**
4. Click **Manage Domain-wide delegation** (or "Manage all" if you see it)

### 2c. Add Service Account to Delegation

1. Click **Add new** (or the plus button)
2. Paste the **Client ID** from Step 1e
3. In **OAuth scopes** field, paste these Gmail scopes (comma-separated):

```
https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.compose,https://www.googleapis.com/auth/gmail.labels
```

Or add individually (newline-separated):
```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.labels
```

### 2d. Authorize

Click **Authorize** button

### 2e. Verify

You should see the service account listed under "Domain-wide delegation" with the scopes listed.

---

## Step 3: Update Your Code

Once delegation is enabled, update your Gmail client to specify which user to impersonate.

### Option A: Pass user_email to GmailClient

```python
from src.integrations.gmail import GmailClient
from config.credentials_loader import load_gmail_service_account

# Load service account credentials
creds = load_gmail_service_account()

# Create client with user_email parameter for delegation
client = GmailClient(
    credentials_json=creds,
    user_email="yasmine@smarterteam.ai"  # ← Your Google Workspace email
)

# Authenticate (JWT will be generated for this user)
await client.authenticate()

# Now you can access that user's Gmail
profile = await client.get_user_profile()
```

### Option B: Set in Environment Variable

```bash
# In .env
GMAIL_USER_EMAIL=yasmine@smarterteam.ai
```

Then in code:
```python
import os
from config.credentials_loader import get_gmail_client_config

config = get_gmail_client_config()
config['user_email'] = os.getenv('GMAIL_USER_EMAIL')

client = GmailClient(**config)
await client.authenticate()
```

### Option C: For Multiple Users (Batch Processing)

```python
async def process_user_gmail(user_email: str) -> dict:
    """Process Gmail for a specific workspace user."""
    creds = load_gmail_service_account()

    client = GmailClient(
        credentials_json=creds,
        user_email=user_email  # Different user each call
    )

    await client.authenticate()
    profile = await client.get_user_profile()

    return {
        'user': user_email,
        'email_address': profile['emailAddress'],
        'messages': profile['messagesTotal'],
        'threads': profile['threadsTotal']
    }

# Process multiple users
users = [
    'yasmine@smarterteam.ai',
    'team@smarterteam.ai',
    'support@smarterteam.ai'
]

results = []
for user in users:
    result = await process_user_gmail(user)
    results.append(result)
```

---

## Step 4: Test the Setup

Update your test to use a workspace email:

```python
#!/usr/bin/env python3
"""Test Gmail with domain-wide delegation."""

import asyncio
from config.credentials_loader import load_gmail_service_account
from src.integrations.gmail import GmailClient

async def test_delegation():
    """Test service account delegation."""

    print("=" * 60)
    print("Gmail Domain-Wide Delegation Test")
    print("=" * 60)

    # Load service account
    creds = load_gmail_service_account()
    if not creds:
        print("❌ No service account credentials found")
        return False

    # Create client with delegation
    user_email = "yasmine@smarterteam.ai"  # ← Change to your email
    print(f"\n[Step 1] Creating client for: {user_email}")

    client = GmailClient(
        credentials_json=creds,
        user_email=user_email  # ← Delegate to this user
    )
    print("✅ Client created")

    # Authenticate
    print(f"\n[Step 2] Authenticating...")
    try:
        await client.authenticate()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

    # Get profile
    print(f"\n[Step 3] Getting user profile...")
    try:
        profile = await client.get_user_profile()
        print(f"✅ Profile retrieved!")
        print(f"   Email: {profile['emailAddress']}")
        print(f"   Messages: {profile['messagesTotal']}")
        print(f"   Threads: {profile['threadsTotal']}")
    except Exception as e:
        print(f"❌ Failed to get profile: {e}")
        return False
    finally:
        await client.close()

    print("\n" + "=" * 60)
    print("✅ Domain-wide delegation is working!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    asyncio.run(test_delegation())
```

---

## Step 5: Handle JWT Token Generation in Client

The GmailClient needs to be updated to handle the `user_email` parameter for JWT delegation.

### Update `__init__` to accept user_email:

```python
class GmailClient(BaseIntegrationClient):
    def __init__(
        self,
        credentials_json: dict | str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_email: str | None = None,  # ← Add this
    ):
        """Initialize Gmail client.

        Args:
            credentials_json: Service account dict or JSON string or file path
            access_token: Pre-generated OAuth access token
            refresh_token: OAuth refresh token
            client_id: OAuth client ID
            client_secret: OAuth client secret
            user_email: For domain-wide delegation, the email to impersonate
        """
        self.user_email = user_email  # Store for delegation
        # ... rest of init
```

### Update `_authenticate_service_account` to use delegation:

```python
async def _authenticate_service_account(self) -> None:
    """Authenticate using service account with JWT and domain-wide delegation."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials

        # Create credentials with scopes
        credentials = Credentials.from_service_account_info(
            self.credentials_dict,
            scopes=self.DEFAULT_SCOPES,
        )

        # If user_email specified, set subject for delegation
        if self.user_email:
            credentials = credentials.with_subject(self.user_email)
            logger.info(f"Using domain-wide delegation for: {self.user_email}")

        # Get access token
        request = Request()
        credentials.refresh(request)
        self.access_token = credentials.token

    except ImportError as e:
        # Fallback or error handling
        raise GmailAuthError(
            "google-auth library required for service account authentication. "
            "Install with: pip install google-auth"
        ) from None
```

---

## Troubleshooting

### Error: "Invalid Credentials" or "Not Authorized"

**Cause:** Domain-wide delegation not enabled

**Solution:**
1. Go back to Step 1 - verify "Enable domain-wide delegation" is on
2. Verify Client ID is correct in Step 2
3. Wait 10-15 minutes for changes to propagate in Google Workspace

### Error: "Insufficient Permissions"

**Cause:** Scopes not granted in Workspace Admin

**Solution:**
1. Go to Step 2 - verify all 5 Gmail scopes are listed
2. Re-authorize the service account
3. Wait 10-15 minutes for propagation

### Error: "resource 'unknown' not found"

**Cause:** Missing `user_email` parameter

**Solution:**
```python
# Wrong ❌
client = GmailClient(credentials_json=creds)

# Correct ✅
client = GmailClient(
    credentials_json=creds,
    user_email="yasmine@smarterteam.ai"
)
```

### Error: "Invalid User Email"

**Cause:** Email doesn't exist in Workspace domain

**Solution:**
1. Verify email is an actual user in admin.google.com
2. Make sure domain matches: `user@smarterteam.ai` not `user@gmail.com`

### Changes Not Taking Effect

**Cause:** Google takes time to propagate changes

**Solution:**
1. Wait 10-15 minutes after enabling delegation
2. Wait 10-15 minutes after granting scopes
3. Try again with fresh authentication

---

## Security Best Practices

⚠️ **Domain-Wide Delegation is Powerful:**

1. **Restrict service accounts** - Only enable for accounts that need it
2. **Limit scopes** - Only grant scopes actually needed (we use 5, not all Gmail scopes)
3. **Audit access** - Monitor what the service account accesses
4. **Rotate keys** - Regularly rotate service account keys
5. **Document usage** - Keep track of which service accounts impersonate which users

---

## What's Happening Under the Hood

### Without Domain-Wide Delegation (OAuth)
```
User logs in → Gets OAuth token → Token accesses their own Gmail
```

### With Domain-Wide Delegation (JWT)
```
Service Account has private key →
Creates JWT signed with key →
Requests access token for User A →
Accesses User A's Gmail (even though service account requested)
```

The key difference: **The service account is trusted to act on behalf of users.**

---

## Next Steps

1. ✅ Enable domain-wide delegation in Google Cloud
2. ✅ Grant Gmail scopes in Workspace Admin
3. ✅ Update GmailClient code to support `user_email`
4. ✅ Update your test to pass `user_email`
5. ✅ Run test to verify it works
6. ✅ Start accessing Gmail for workspace users

---

## Complete Example (All Together)

```python
# main.py
import asyncio
from config.credentials_loader import load_gmail_service_account
from src.integrations.gmail import GmailClient

async def main():
    # Load service account
    creds = load_gmail_service_account()

    # Create client with delegation
    client = GmailClient(
        credentials_json=creds,
        user_email="yasmine@smarterteam.ai"
    )

    try:
        # Authenticate (generates JWT for yasmine@smarterteam.ai)
        await client.authenticate()

        # Access Yasmine's Gmail
        messages = await client.list_messages(max_results=10)
        print(f"Found {len(messages)} messages")

        # Send email as Yasmine
        await client.send_message(
            to_addresses=["recipient@example.com"],
            subject="Hello from automation",
            body="This email was sent by a service account acting as Yasmine"
        )

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## References

- [Google Cloud Domain-Wide Delegation](https://developers.google.com/identity/protocols/oauth2/service-account#delegating_domain-wide_authority_to_the_service_account)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)
- [google-auth-library-python](https://github.com/googleapis/google-auth-library-python)
