#!/usr/bin/env python3
"""
Google OAuth2 Setup Helper

Helps obtain Google OAuth2 access tokens for testing and integration.
Supports both service account and user OAuth2 flows.

Usage:
    python scripts/google_oauth2_setup.py --method service-account --key-file credentials.json
    python scripts/google_oauth2_setup.py --method user-oauth
"""

import argparse
import json
import os
import sys

try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False


def setup_service_account(key_file: str, scopes: list[str]) -> dict[str, str]:
    """Set up OAuth2 credentials using service account key file.

    Args:
        key_file: Path to service account JSON key file
        scopes: OAuth2 scopes to request

    Returns:
        Dictionary with credentials info
    """
    if not GOOGLE_AUTH_AVAILABLE:
        print("ERROR: google-auth library required. Install with: pip install google-auth")
        sys.exit(1)

    try:
        with open(key_file) as f:
            key_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Key file not found: {key_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in key file: {key_file}")
        sys.exit(1)

    try:
        credentials = service_account.Credentials.from_service_account_info(key_data, scopes=scopes)
        # Refresh to get valid token
        request = Request()
        credentials.refresh(request)

        return {
            "type": "service_account",
            "project_id": key_data.get("project_id", ""),
            "access_token": credentials.token,
            "token_expiry": str(credentials.expiry),
            "scopes": json.dumps(scopes),
        }
    except Exception as e:
        print(f"ERROR: Failed to create service account credentials: {e}")
        sys.exit(1)


def setup_user_oauth(client_id: str, client_secret: str, scopes: list[str]) -> dict[str, str]:
    """Set up OAuth2 credentials using user OAuth2 flow.

    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        scopes: OAuth2 scopes to request

    Returns:
        Dictionary with credentials info
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        print(
            "ERROR: google-auth-oauthlib library required. Install with: pip install google-auth-oauthlib"
        )
        sys.exit(1)

    try:
        flow = InstalledAppFlow.from_client_secrets_info(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes,
        )

        credentials = flow.run_local_server(port=0)

        return {
            "type": "user_oauth",
            "client_id": client_id,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token or "",
            "token_expiry": str(credentials.expiry),
            "scopes": json.dumps(scopes),
        }
    except Exception as e:
        print(f"ERROR: OAuth2 flow failed: {e}")
        sys.exit(1)


def setup_from_env() -> dict[str, str] | None:
    """Try to set up credentials from environment variables.

    Returns:
        Dictionary with credentials info or None if not possible
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ]

    print("Setting up OAuth2 with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET...")
    return setup_user_oauth(client_id, client_secret, scopes)


def save_credentials(credentials: dict[str, str], output_file: str | None = None) -> None:
    """Save credentials to file and print export commands.

    Args:
        credentials: Credentials dictionary
        output_file: Optional file to save JSON credentials
    """
    print("\n" + "=" * 70)
    print("SUCCESS! OAuth2 Credentials Obtained")
    print("=" * 70)

    if output_file:
        with open(output_file, "w") as f:
            json.dump(credentials, f, indent=2)
        print(f"\n✅ Saved to: {output_file}")

    # Print export commands
    print("\n📋 Add these environment variables to .env:")
    print("-" * 70)

    for key, value in credentials.items():
        if key == "scopes":
            continue
        if "\n" in value or len(value) > 100:
            print(f'export GOOGLE_{key.upper()}="<long-value>"')
        else:
            print(f'export GOOGLE_{key.upper()}="{value}"')

    # Also show as single JSON string option
    print("\n📋 Or as GOOGLE_DOCS_CREDENTIALS JSON:")
    print("-" * 70)
    creds_json = {
        "type": credentials.get("type", "service_account"),
        "project_id": credentials.get("project_id", "smarter-team"),
        "access_token": credentials["access_token"],
        "client_id": credentials.get("client_id", ""),
        "client_secret": credentials.get("client_secret", ""),
        "private_key": credentials.get("private_key", ""),
    }
    print(f"export GOOGLE_DOCS_CREDENTIALS='{json.dumps(creds_json)}'")

    print("\n" + "=" * 70)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Get Google OAuth2 access tokens for testing")
    parser.add_argument(
        "--method",
        choices=["service-account", "user-oauth", "auto"],
        default="auto",
        help="OAuth2 method to use",
    )
    parser.add_argument(
        "--key-file",
        help="Service account key file (for service-account method)",
    )
    parser.add_argument(
        "--output",
        help="Save credentials to JSON file",
    )

    args = parser.parse_args()

    scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ]

    if args.method == "auto":
        # Try to use service account key file if available
        if os.path.exists("credentials.json"):
            print("Found credentials.json, using service account flow...")
            credentials = setup_service_account("credentials.json", scopes)
        else:
            # Fall back to user OAuth2
            print("Using user OAuth2 flow...")
            print("This will open a browser window for authentication.")
            credentials = setup_from_env()
            if not credentials:
                print("ERROR: Need GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
                sys.exit(1)
    elif args.method == "service-account":
        if not args.key_file:
            print("ERROR: --key-file required for service-account method")
            sys.exit(1)
        credentials = setup_service_account(args.key_file, scopes)
    elif args.method == "user-oauth":
        credentials = setup_from_env()
        if not credentials:
            print("ERROR: Need GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
            sys.exit(1)

    save_credentials(credentials, args.output)


if __name__ == "__main__":
    main()
