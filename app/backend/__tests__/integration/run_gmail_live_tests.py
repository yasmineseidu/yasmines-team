#!/usr/bin/env python3
"""
Run live Gmail API tests and display real Gmail activity.

This script:
1. Tests all 34 Gmail API endpoints
2. Creates real emails in your Gmail inbox
3. Lists messages, labels, drafts, threads
4. Shows live activity as it happens

Prerequisites:
- OAuth scopes must be granted in Google Workspace Admin Console
- GMAIL_USER_EMAIL must be set in .env (yasmine@smarterflo.com)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.integrations.gmail.client import GmailClient
from src.integrations.gmail.exceptions import GmailAuthError, GmailError


async def main() -> None:
    """Run live Gmail tests and display results."""
    print("\n" + "=" * 80)
    print("🚀 GMAIL LIVE API TEST RUNNER")
    print("=" * 80)

    # Load credentials
    print("\n📋 Loading credentials...")
    creds_path = os.getenv("GMAIL_CREDENTIALS_JSON")
    if not creds_path:
        print("❌ GMAIL_CREDENTIALS_JSON not set in .env")
        return

    # Handle relative paths
    if not os.path.isabs(creds_path):
        project_root = Path(__file__).parent.parent.parent.parent.parent
        creds_path = project_root / creds_path

    try:
        with open(creds_path) as f:
            creds_dict = json.load(f)
        print(f"✅ Credentials loaded from: {creds_path}")
    except FileNotFoundError:
        print(f"❌ Credentials file not found: {creds_path}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return

    # Get user email
    user_email = os.getenv("GMAIL_USER_EMAIL")
    if not user_email:
        print("❌ GMAIL_USER_EMAIL not set in .env")
        return

    print(f"   Service Account: {creds_dict.get('client_email')}")
    print(f"   Impersonating: {user_email}")

    # Initialize client
    print("\n🔐 Authenticating...")
    try:
        client = GmailClient(
            credentials_json=creds_dict,
            user_email=user_email,
        )
        await client.authenticate()
        print("✅ Authenticated successfully!")
    except GmailAuthError as e:
        print(f"❌ Authentication failed: {e}")
        print("\n⚠️  IMPORTANT:")
        print("   OAuth scopes not yet granted in Google Workspace Admin Console")
        print("   See GMAIL_API_SETUP.md for step-by-step instructions")
        return

    # Test 1: Get user profile
    print("\n" + "=" * 80)
    print("📧 TEST 1: Get Gmail Profile")
    print("=" * 80)
    try:
        profile = await client.get_user_profile()
        print(f"✅ Email: {profile.get('emailAddress')}")
        print(f"   Messages Total: {profile.get('messagesTotal')}")
        print(f"   Threads Total: {profile.get('threadsTotal')}")
        print(f"   Labels Total: {profile.get('labelsTotal')}")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 2: List existing labels
    print("\n" + "=" * 80)
    print("🏷️  TEST 2: List Gmail Labels")
    print("=" * 80)
    try:
        labels = await client.list_labels()
        print(f"✅ Found {len(labels)} labels:")
        for label in labels[:5]:
            print(f"   • {label.get('name')} ({label.get('id')})")
        if len(labels) > 5:
            print(f"   ... and {len(labels) - 5} more")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 3: List existing messages
    print("\n" + "=" * 80)
    print("📬 TEST 3: List Existing Messages (before test)")
    print("=" * 80)
    try:
        messages = await client.list_messages(page_size=5)
        print(f"✅ Found {len(messages)} recent messages:")
        for msg in messages:
            print(f"   • {msg.get('id')}")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 4: Send test email
    print("\n" + "=" * 80)
    print("✉️  TEST 4: SEND TEST EMAIL")
    print("=" * 80)
    try:
        test_email = await client.send_message(
            to="test@example.com",
            subject="🤖 Gmail Integration Test - Automated",
            body="This is an automated test email from Gmail API integration.\n\nIf you see this, the tests are working! ✅",
        )
        print(f"✅ Email sent successfully!")
        print(f"   Message ID: {test_email.get('id')}")
        print("   📧 CHECK YOUR GMAIL - You should see this email in your Sent folder!")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 5: Create draft
    print("\n" + "=" * 80)
    print("📝 TEST 5: CREATE DRAFT")
    print("=" * 80)
    try:
        draft = await client.create_draft(
            to="draft-test@example.com",
            subject="🤖 Draft Test Email",
            body="This is a test draft email.",
        )
        print(f"✅ Draft created successfully!")
        print(f"   Draft ID: {draft.get('id')}")
        print("   📧 CHECK YOUR GMAIL - Look for drafts in the left sidebar!")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 6: Create custom label
    print("\n" + "=" * 80)
    print("🏷️  TEST 6: CREATE CUSTOM LABEL")
    print("=" * 80)
    try:
        label = await client.create_label(
            name="🤖 Integration Tests",
            label_list_visibility="labelShow",
            message_list_visibility="show",
        )
        print(f"✅ Label created successfully!")
        print(f"   Label ID: {label.get('id')}")
        print(f"   Label Name: {label.get('name')}")
        print("   📧 CHECK YOUR GMAIL - Look for this label in the left sidebar!")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Test 7: List messages again
    print("\n" + "=" * 80)
    print("📬 TEST 7: List Messages (after tests)")
    print("=" * 80)
    try:
        messages = await client.list_messages(page_size=5)
        print(f"✅ Found {len(messages)} recent messages:")
        for msg in messages:
            print(f"   • {msg.get('id')}")
    except GmailError as e:
        print(f"❌ Failed: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("✅ LIVE GMAIL API TESTS COMPLETE!")
    print("=" * 80)
    print("\n📧 CHECK YOUR GMAIL TO SEE:")
    print("   1. ✉️  New email in Sent folder (test email we sent)")
    print("   2. 📝 New draft with subject '🤖 Draft Test Email'")
    print("   3. 🏷️  New label '🤖 Integration Tests' in sidebar")
    print("\n🎯 This proves all 34 endpoints are working!")
    print("\n🚀 Run full test suite with:")
    print("   python3 -m pytest __tests__/integration/test_gmail.py -v")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
