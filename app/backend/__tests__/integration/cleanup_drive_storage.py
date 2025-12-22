#!/usr/bin/env python3
"""Clean up Google Drive storage to free quota.

Safely deletes old test files to free up storage.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.integrations.google_drive.client import GoogleDriveClient


async def cleanup_drive() -> None:
    """Clean up old test files from Drive."""
    print("\n📊 GOOGLE DRIVE STORAGE CLEANUP")
    print("=" * 60)

    # Load credentials
    env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
    cred_path = "app/backend/config/credentials/google-service-account.json"
    cred_file = Path("/Users/yasmineseidu/Desktop/Coding/yasmines-team") / cred_path

    with open(cred_file) as f:
        credentials = json.load(f)

    # Generate token
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    creds = service_account.Credentials.from_service_account_info(
        credentials,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    request = Request()
    creds.refresh(request)

    # Initialize client
    client = GoogleDriveClient(
        credentials_json={"type": "oauth2"},
        access_token=creds.token,
    )

    # List all files
    print("\n📂 Scanning Drive for test files...")
    all_files = []
    page_token = None

    while True:
        result = await client.list_files(
            page_size=1000,
            page_token=page_token,
            fields="files(id,name,createdTime,mimeType,size)",
        )

        all_files.extend(result.get("files", []))
        page_token = result.get("nextPageToken")

        if not page_token:
            break

    print(f"✅ Found {len(all_files)} files total")

    # Calculate storage usage
    total_size = sum(int(f.get("size", 0)) for f in all_files)
    total_gb = total_size / (1024 ** 3)
    print(f"   Total storage: {total_gb:.2f} GB")

    # Delete test files (keep important ones)
    test_patterns = [
        "Test Document",
        "test-upload",
        "Test ",
        "Live API",
    ]

    deleted_count = 0
    freed_space = 0

    print(f"\n🗑️  Deleting test files...")

    for file in all_files:
        name = file.get("name", "")
        file_id = file.get("id", "")
        size = int(file.get("size", 0))

        # Check if file matches test patterns
        is_test_file = any(pattern in name for pattern in test_patterns)

        if is_test_file:
            try:
                await client.delete_file(file_id, permanently=True)
                deleted_count += 1
                freed_space += size
                print(f"   ✅ Deleted: {name[:50]}")
            except Exception as e:
                print(f"   ⚠️  Failed to delete {name}: {e}")

    freed_gb = freed_space / (1024 ** 3)
    print(f"\n✅ Cleanup complete!")
    print(f"   Files deleted: {deleted_count}")
    print(f"   Space freed: {freed_gb:.2f} GB")

    await client.close()


if __name__ == "__main__":
    asyncio.run(cleanup_drive())
