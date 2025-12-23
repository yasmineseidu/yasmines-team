#!/usr/bin/env python3
"""Diagnostic tests for Gmail delegation setup."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.integrations.gmail.client import GmailClient


async def test_service_account_without_delegation() -> None:
    """Test service account authentication WITHOUT delegation."""
    print("\n" + "=" * 60)
    print("🔍 TEST 1: Service Account WITHOUT Delegation")
    print("=" * 60)

    # Load credentials
    cred_path = (
        Path("/Users/yasmineseidu/Desktop/Coding/yasmines-team")
        / "app/backend/config/credentials/google-service-account.json"
    )

    with open(cred_path) as f:
        credentials = json.load(f)

    try:
        # Create client WITHOUT user_email (no delegation)
        client = GmailClient(credentials_json=credentials)
        print("✅ Client created")

        # Authenticate
        await client.authenticate()
        print("✅ Authentication successful (no delegation)")

        # Get profile
        profile = await client.get_user_profile()
        print("✅ Profile retrieved!")
        print(f"   Email: {profile.get('emailAddress', 'N/A')}")
        print(f"   Messages: {profile.get('messagesTotal', 0)}")

        await client.close()

    except Exception as e:
        print(f"❌ Failed: {e}")


async def test_with_different_workspaces() -> None:
    """Test delegation with different possible workspace domain variations."""
    print("\n" + "=" * 60)
    print("🔍 TEST 2: Testing Different Workspace Domains")
    print("=" * 60)

    # Load credentials
    cred_path = (
        Path("/Users/yasmineseidu/Desktop/Coding/yasmines-team")
        / "app/backend/config/credentials/google-service-account.json"
    )

    with open(cred_path) as f:
        credentials = json.load(f)

    # List of possible workspace emails to try
    test_emails = [
        "yasmine@smarterteam.ai",
        "yasmine@smarterflo.com",
        "admin@smarterteam.ai",
        "admin@smarterflo.com",
        "support@smarterteam.ai",
        "smarterteam@smarterteam.ai",
    ]

    print("\nAttempting delegation with various workspace emails:\n")

    for email in test_emails:
        print(f"📧 Testing: {email}")
        try:
            client = GmailClient(credentials_json=credentials, user_email=email)
            await client.authenticate()

            profile = await client.get_user_profile()
            print(f"   ✅ SUCCESS - Email: {profile.get('emailAddress')}")
            await client.close()
            return  # Found working email

        except Exception as e:
            error_msg = str(e)
            if "invalid_grant" in error_msg:
                print("   ❌ Invalid email or not delegated")
            elif "invalid" in error_msg.lower():
                print(f"   ❌ Invalid format or setup: {error_msg[:50]}...")
            else:
                print(f"   ❌ Error: {error_msg[:50]}...")

    print("\n💡 HINT: None of the tested emails worked.")
    print("   This could mean:")
    print("   1. Domain-wide delegation isn't fully set up")
    print("   2. The tested emails don't exist in your workspace")
    print("   3. Required scopes weren't granted in Google Workspace Admin")


async def check_delegation_setup() -> None:
    """Check if service account has delegation enabled."""
    print("\n" + "=" * 60)
    print("🔍 TEST 3: Check Service Account Delegation Setup")
    print("=" * 60)

    cred_path = (
        Path("/Users/yasmineseidu/Desktop/Coding/yasmines-team")
        / "app/backend/config/credentials/google-service-account.json"
    )

    with open(cred_path) as f:
        credentials = json.load(f)

    print("\n✅ Service Account Details:")
    print(f"   Type: {credentials.get('type')}")
    print(f"   Email: {credentials.get('client_email')}")
    print(f"   Project: {credentials.get('project_id')}")
    print(f"   Client ID: {credentials.get('client_id')}")

    # Check for delegation-specific fields
    has_private_key = "private_key" in credentials
    print("\n✅ Required fields for delegation:")
    print(f"   Has private_key: {has_private_key}")
    print(f"   Has client_email: {'client_email' in credentials}")
    print(f"   Has token_uri: {'token_uri' in credentials}")

    print("\n📋 To complete delegation setup:")
    print("   1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts")
    print(f"   2. Click on: {credentials.get('client_email')}")
    print("   3. Go to 'Keys' tab")
    print("   4. Enable 'Domain-wide delegation' if not already enabled")
    print("   5. Copy the Client ID")
    print("   6. Go to: https://admin.google.com")
    print("   7. Security → Access and data control → API controls → Manage domain-wide delegation")
    print("   8. Add the Client ID and grant these Gmail scopes:")
    print("      - https://www.googleapis.com/auth/gmail.readonly")
    print("      - https://www.googleapis.com/auth/gmail.modify")
    print("      - https://www.googleapis.com/auth/gmail.send")


async def main() -> None:
    """Run all diagnostic tests."""
    print("\n" + "=" * 60)
    print("🧪 GMAIL DELEGATION DIAGNOSTIC TESTS")
    print("=" * 60)

    # Test 1: Service account without delegation
    await test_service_account_without_delegation()

    # Test 2: Try different workspace emails
    await test_with_different_workspaces()

    # Test 3: Check delegation setup
    await check_delegation_setup()

    print("\n" + "=" * 60)
    print("⚠️  If all tests failed, check the hints above and follow the setup guide")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
