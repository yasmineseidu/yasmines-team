"""Pytest configuration and fixtures for Google Drive integration tests.

Provides fixtures for OAuth token management and test data configuration.
"""

import asyncio
import json
import os

# Add parent directory to path for oauth_helper
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from oauth_helper import get_access_token_for_testing  # pragma: allowlist secret


@pytest.fixture(scope="session")
def google_client_id() -> str:
    """Get Google Client ID from environment."""
    return os.getenv("GOOGLE_CLIENT_ID", "")


@pytest.fixture(scope="session")
def google_client_secret() -> str:
    """Get Google Client Secret from environment."""
    return os.getenv("GOOGLE_CLIENT_SECRET", "")


@pytest.fixture(scope="session")
def google_redirect_uri() -> str:
    """Get Google Redirect URI from environment."""
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback")


@pytest.fixture(scope="session")
def google_access_token() -> str:
    """Get Google access token for integration tests.

    Supports three authentication methods:
    1. Service Account JSON file (GOOGLE_SERVICE_ACCOUNT_FILE env var)
    2. Pre-generated token from .google_drive_token.json
    3. OAuth flow with refresh token
    """
    # Method 1: Check for service account JSON file
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file and os.path.exists(sa_file):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials

            with open(sa_file) as f:
                sa_info = json.load(f)

            credentials = Credentials.from_service_account_info(
                sa_info,
                scopes=[
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/drive.file",
                ],
            )
            request = Request()
            credentials.refresh(request)
            return credentials.token
        except Exception as e:
            pytest.skip(
                f"Service account authentication failed: {e}\n\n"
                "Ensure GOOGLE_SERVICE_ACCOUNT_FILE points to a valid JSON file"
            )

    # Method 2: Try to load pre-generated token
    try:
        token = asyncio.run(get_access_token_for_testing())
        return token
    except Exception as e:
        pytest.skip(
            f"Google Drive authentication skipped: {str(e)}\n\n"
            "To run live API tests, choose one option:\n\n"
            "OPTION 1: Service Account (Recommended for Production)\n"
            "  1. Create service account in Google Cloud Console\n"
            "  2. Download JSON key file\n"
            "  3. Set: export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json\n"
            "  4. Run tests\n\n"
            "OPTION 2: OAuth 2.0 (User Authorization)\n"
            "  1. Visit: https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline\n"
            "  2. Grant permissions\n"
            "  3. Copy the code\n"
            "  4. Run: python3 app/backend/scripts/exchange_oauth_code.py <code>\n\n"
            "OPTION 3: Pre-generated Token\n"
            "  1. Generate token using either method above\n"
            "  2. Create .google_drive_token.json with access_token field"
        )


@pytest.fixture
def oauth_credentials(
    google_client_id: str, google_client_secret: str, google_access_token: str
) -> dict:
    """Fixture providing OAuth credentials with real access token."""
    return {
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "type": "oauth",
        "access_token": google_access_token,
    }


@pytest.fixture
def test_file_names() -> dict:
    """Fixture providing standard test file names."""
    return {
        "folder": "claude-code-test-folder",
        "document": "claude-code-test-document",
        "spreadsheet": "claude-code-test-spreadsheet",
        "upload": "claude-code-test-upload",
    }


@pytest.fixture
def export_formats() -> list[str]:
    """Fixture providing all supported export formats."""
    return [
        "pdf",
        "docx",
        "xlsx",
        "csv",
        "json",
        "odt",
        "ods",
        "rtf",
        "txt",
        "zip",
    ]


@pytest.fixture
def mime_types() -> dict:
    """Fixture providing standard MIME types for Google Drive."""
    return {
        "document": "application/vnd.google-apps.document",
        "spreadsheet": "application/vnd.google-apps.spreadsheet",
        "presentation": "application/vnd.google-apps.presentation",
        "folder": "application/vnd.google-apps.folder",
        "pdf": "application/pdf",
        "text": "text/plain",
        "image": "image/jpeg",
    }


@pytest.fixture
def sample_test_content() -> str:
    """Fixture providing sample document content for testing."""
    return """
# Claude Code - Google Drive Integration Test

This document was automatically created by the integration test suite.

## Test Sections

### Overview
This test verifies complete Google Drive API functionality including:
- File listing and filtering
- File metadata retrieval
- Document creation and editing
- File sharing and permissions
- Export to multiple formats
- Error handling and retry logic

### Features Tested
- ✅ List files with pagination
- ✅ Get file metadata
- ✅ Create documents and folders
- ✅ Upload files
- ✅ Delete files (soft and permanent)
- ✅ Share with other users
- ✅ Export to multiple formats
- ✅ Read document content
- ✅ Error handling
- ✅ Rate limiting and retries

### Test Results
All endpoints verified and working correctly with 100% coverage.

### Future Extensibility
The client implementation is designed to support:
- New Google Drive API endpoints
- Additional export formats
- New MIME types
- Custom retry strategies
- Extended permission models

### Conclusion
Integration testing complete. All Google Drive API operations functional.
""".strip()


@pytest.fixture
def rate_limit_config() -> dict:
    """Fixture providing rate limit configuration."""
    return {
        "requests_per_minute": 12000,
        "requests_per_day": 750_000_000,  # in bytes (750GB)
        "max_retries": 3,
        "initial_backoff_seconds": 1,
        "max_backoff_seconds": 32,
    }
