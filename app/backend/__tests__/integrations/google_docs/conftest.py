"""Fixtures for Google Docs API tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.google_docs import GoogleDocsClient

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


@pytest.fixture
def google_docs_credentials() -> dict | None:
    """Get Google Docs credentials from .env.

    Returns None if credentials not configured (tests will be skipped).
    """
    credentials_json = os.getenv("GOOGLE_DOCS_CREDENTIALS")
    if not credentials_json:
        return None

    import json

    try:
        return json.loads(credentials_json)
    except Exception:
        return None


@pytest.fixture
async def google_docs_client(
    google_docs_credentials: dict | None,
) -> GoogleDocsClient | None:
    """Create Google Docs client with live credentials.

    Returns None if credentials not configured (tests will be skipped).
    If GOOGLE_DOCS_CREDENTIALS not available, tries to build from GOOGLE_CLIENT_ID/SECRET.
    """
    if not google_docs_credentials:
        # Try to build credentials from GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if client_id and client_secret:
            # Create test credentials with OAuth2 tokens
            google_docs_credentials = {
                "type": "service_account",
                "client_id": client_id,
                "client_secret": client_secret,
                "project_id": "smarter-team",
                "private_key": "test-key",  # pragma: allowlist secret
                "access_token": f"test_access_token_for_{client_id}",  # pragma: allowlist secret
            }
        else:
            return None

    return GoogleDocsClient(credentials_json=google_docs_credentials)


@pytest.fixture
def live_api_enabled() -> bool:
    """Check if live API tests should run.

    Live API tests require GOOGLE_DOCS_CREDENTIALS in .env.
    """
    return "GOOGLE_DOCS_CREDENTIALS" in os.environ


# Sample test data for Google Docs API testing
SAMPLE_TEST_DATA = {
    "document_title": "Test Document - Claude Docs Integration",
    "sample_text": "Hello World! This is a test document.",
    "formatted_text": "Bold Text",
    "table_rows": 3,
    "table_columns": 2,
    "share_email": "test@example.com",
}
