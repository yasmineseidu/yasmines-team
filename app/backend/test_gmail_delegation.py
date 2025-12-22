#!/usr/bin/env python3
"""
Test Gmail service account with domain-wide delegation.

Usage:
    cd app/backend
    uv run python test_gmail_delegation.py

This test requires:
1. Service account JSON at config/credentials/gmail-service-account.json
2. Domain-wide delegation enabled in Google Cloud
3. Gmail scopes granted in Google Workspace Admin console
4. Replace 'yasmine@smarterteam.ai' with your actual workspace email
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.credentials_loader import load_gmail_service_account
from src.integrations.gmail import GmailClient


async def test_delegation():
    """Test Gmail service account with domain-wide delegation."""

    print("=" * 60)
    print("Gmail Domain-Wide Delegation Test")
    print("=" * 60)

    # Step 1: Load service account
    print("\n[Step 1] Loading service account credentials...")
    creds = load_gmail_service_account()

    if not creds:
        print("❌ FAILED: No credentials found")
        print("   Check: Is service account JSON at config/credentials/gmail-service-account.json?")
        return False

    print("✅ Credentials loaded")
    print(f"   Service Account: {creds.get('client_email')}")
    print(f"   Project: {creds.get('project_id')}")

    # Step 2: Create client with delegation
    user_email = "yasmine@smarterteam.ai"  # ← Change to your workspace email
    print(f"\n[Step 2] Creating client with domain-wide delegation...")
    print(f"   Impersonating: {user_email}")

    try:
        client = GmailClient(
            credentials_json=creds,
            user_email=user_email  # ← This enables domain-wide delegation
        )
        print("✅ Client created with delegation")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

    # Step 3: Authenticate
    print(f"\n[Step 3] Authenticating with domain-wide delegation...")
    try:
        await client.authenticate()
        print("✅ Authentication successful")
        print(f"   Access Token: {client.access_token[:30]}..." if client.access_token else "   Token: (JWT bearer)")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\nPossible causes:")
        print("  1. Domain-wide delegation not enabled in Google Cloud")
        print("  2. Gmail scopes not granted in Google Workspace Admin")
        print("  3. User email does not exist in workspace")
        print("  4. Changes not yet propagated (wait 10-15 minutes)")
        return False

    # Step 4: Test API call
    print(f"\n[Step 4] Testing API call (get_user_profile)...")
    try:
        profile = await client.get_user_profile()
        print("✅ API call successful!")
        print(f"   Email: {profile['emailAddress']}")
        print(f"   Messages: {profile['messagesTotal']}")
        print(f"   Threads: {profile['threadsTotal']}")
    except Exception as e:
        print(f"❌ FAILED: API error: {e}")
        print("\nPossible causes:")
        print("  1. User email is not accessible (permissions)")
        print("  2. User email doesn't exist in workspace")
        print("  3. Gmail scopes not properly granted")
        return False
    finally:
        await client.close()

    # Success!
    print("\n" + "=" * 60)
    print("✅ SUCCESS - Domain-wide delegation is working!")
    print("=" * 60)
    print(f"\nYou can now access Gmail for: {user_email}")
    print("\nNext steps:")
    print(f"  • Access other users: change user_email to their email")
    print(f"  • Send emails: await client.send_message(...)")
    print(f"  • List messages: await client.list_messages(...)")
    print(f"  • Manage labels: await client.list_labels()")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_delegation())
    sys.exit(0 if success else 1)
