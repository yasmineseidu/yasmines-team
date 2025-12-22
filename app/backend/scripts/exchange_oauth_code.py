#!/usr/bin/env python3
"""Exchange Google OAuth authorization code for access token.

Usage:
    python3 exchange_oauth_code.py <authorization_code>

Example:
    python3 exchange_oauth_code.py 4/0AX4XfWiXxQp...
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from __tests__.integration.google_drive.oauth_helper import GoogleOAuthHelper


async def main():
    """Exchange authorization code for access token."""
    if len(sys.argv) != 2:
        print("Usage: python3 exchange_oauth_code.py <authorization_code>")
        print()
        print("Steps:")
        print("1. Visit Google OAuth URL")
        print("2. Grant permissions")
        print("3. Copy the 'code' parameter from redirect URL")
        print("4. Run this script with that code")
        sys.exit(1)

    code = sys.argv[1]

    # Get credentials from environment  # pragma: allowlist secret
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback")

    if not client_id or not client_secret:
        print("❌ Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set in environment")
        print()
        print("Set them with:")
        print("export GOOGLE_CLIENT_ID='your-client-id'")  # pragma: allowlist secret
        print("export GOOGLE_CLIENT_SECRET='your-client-secret'")  # pragma: allowlist secret
        sys.exit(1)

    print("🔐 Exchanging OAuth Code for Access Token")
    print("=" * 60)
    print()

    try:
        oauth = GoogleOAuthHelper(client_id, client_secret, redirect_uri)
        access_token, refresh_token = await oauth.get_access_token_from_code(code)
        oauth.save_token_to_file(".google_drive_token.json")

        print("✅ Success!")
        print("=" * 60)
        print(f"Access Token: {access_token[:50]}...")
        if refresh_token:
            print(f"Refresh Token: {refresh_token[:50]}...")
        print()
        print("✅ Token saved to: .google_drive_token.json")
        print()
        print("Now you can run integration tests:")
        print("pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v")

    except Exception as e:
        print(f"❌ Error exchanging code: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
