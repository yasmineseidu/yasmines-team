#!/usr/bin/env python3
"""Generate Google service account access token.

This script generates an access token from a service account JSON file
for production server-to-server authentication.

Usage:
    GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json python3 generate_service_account_token.py

Requirements:
    pip install google-auth
"""

import json
import os
import sys
from datetime import datetime, timedelta

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Error: google-auth library not installed")
    print()
    print("Install it with:")
    print("  pip install google-auth")
    sys.exit(1)


def main():
    """Generate access token from service account file."""
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if not sa_file or not os.path.exists(sa_file):
        print("🔐 Google Service Account Token Generation")
        print("=" * 60)
        print()
        print("To generate a token, you need a service account JSON file:")
        print()
        print("1. Create service account in Google Cloud Console:")
        print("   - Go to https://console.cloud.google.com/")
        print("   - Create a new project or select existing")
        print("   - Go to Service Accounts")
        print("   - Create a new service account")
        print("   - Grant it Editor role")
        print()
        print("2. Create and download JSON key:")
        print("   - Click on the service account")
        print("   - Go to Keys tab")
        print("   - Add Key > Create new key")
        print("   - Choose JSON format")
        print("   - Save the file")
        print()
        print("3. Set environment variable:")
        print("   export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json")
        print()
        print("4. Run this script again:")
        print("   python3 generate_service_account_token.py")
        sys.exit(1)

    print("🔐 Generating Access Token from Service Account")
    print("=" * 60)
    print()

    try:
        # Load service account credentials
        with open(sa_file) as f:
            sa_info = json.load(f)

        # Create credentials object
        credentials = Credentials.from_service_account_info(
            sa_info,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            ],
        )

        # Get access token
        request = Request()
        credentials.refresh(request)

        # Display results
        print("✅ Success!")
        print()
        print(f"Access Token: {credentials.token[:50]}...")
        print("Token Type: Bearer")
        print("Expires In: 3600 seconds")
        print()

        # Save to file
        output_file = ".google_drive_token.json"
        token_data = {
            "access_token": credentials.token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": (datetime.now() + timedelta(seconds=3600)).isoformat(),
        }

        with open(output_file, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"💾 Token saved to: {output_file}")
        print()
        print("Now you can run integration tests:")
        print("pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
