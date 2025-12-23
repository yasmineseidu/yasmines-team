#!/usr/bin/env python3
"""
Test Gmail service account credentials end-to-end.

Usage:
    cd app/backend
    python test_gmail_credentials.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.credentials_loader import get_gmail_client_config, load_gmail_service_account
from src.integrations.gmail import GmailClient


async def test_credentials():
    """Test Gmail credentials loading and authentication."""

    print("=" * 60)
    print("Gmail Credentials Verification Test")
    print("=" * 60)

    # Step 1: Load credentials from file or environment
    print("\n[Step 1] Loading credentials...")
    creds = load_gmail_service_account()

    if not creds:
        print("❌ FAILED: No credentials found")
        print("   Check:")
        print(
            "   - Is service account JSON at: app/backend/config/credentials/gmail-service-account.json?"
        )
        print("   - Or is GMAIL_SERVICE_ACCOUNT_JSON environment variable set?")
        return False

    print("✅ Credentials loaded successfully")
    print(f"   Service Account: {creds.get('client_email', 'UNKNOWN')}")
    print(f"   Project ID: {creds.get('project_id', 'UNKNOWN')}")

    # Step 2: Get complete client configuration
    print("\n[Step 2] Building client configuration...")
    config = get_gmail_client_config()

    if not config:
        print("❌ FAILED: Could not build client config")
        return False

    print("✅ Configuration ready")
    print("   Auth Method: service_account")

    # Step 3: Initialize Gmail client
    print("\n[Step 3] Initializing Gmail client...")
    try:
        client = GmailClient(**config)
        print("✅ Gmail client initialized")
        print(f"   Client ID: {id(client)}")
    except Exception as e:
        print(f"❌ FAILED: Could not initialize client: {e}")
        return False

    # Step 4: Authenticate
    print("\n[Step 4] Authenticating with Gmail API...")
    try:
        await client.authenticate()
        print("✅ Authentication successful")
        print(
            f"   Access Token: {client.access_token[:20]}..."
            if client.access_token
            else "   Access Token: (using service account JWT)"
        )
    except Exception as e:
        print(f"❌ FAILED: Authentication error: {e}")
        print("   Tip: Make sure google-auth library is installed: pip install google-auth")
        return False

    # Step 5: Test API call
    print("\n[Step 5] Testing API call (get_user_profile)...")
    try:
        profile = await client.get_user_profile()
        print("✅ API call successful!")
        print(f"   Email: {profile['emailAddress']}")
        print(f"   Total Messages: {profile['messagesTotal']}")
        print(f"   Total Threads: {profile['threadsTotal']}")
    except Exception as e:
        print(f"❌ FAILED: API call error: {e}")
        return False
    finally:
        await client.close()

    # Success!
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Gmail integration is working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_credentials())
    sys.exit(0 if success else 1)
