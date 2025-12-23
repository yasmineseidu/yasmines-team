"""Pytest configuration for Google Meet integration tests.

These tests require:
1. Service account credentials at: config/credentials/google-service-account.json
   OR set via GOOGLE_MEET_CREDENTIALS_JSON env var (path to JSON file)

2. For domain-wide delegation tests:
   - GOOGLE_MEET_DELEGATED_USER env var (e.g., yasmine@smarterflo.com)
   - The scope 'https://www.googleapis.com/auth/meetings.space.created' must be
     authorized in the Google Workspace Admin Console for the service account

See ~/.claude/context/SELF-HEALING.md for Admin Console setup instructions.
"""

import json
import os
from typing import Any

import pytest

# Determine paths relative to this file
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INTEGRATION_DIR = os.path.dirname(TESTS_DIR)
TESTS_ROOT = os.path.dirname(INTEGRATION_DIR)
BACKEND_ROOT = os.path.dirname(TESTS_ROOT)
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_ROOT))


def resolve_credentials_path(path: str) -> str | None:
    """Resolve credentials path, handling various path formats."""
    paths_to_try = []

    if os.path.isabs(path):
        paths_to_try.append(path)
    else:
        # Try relative to backend root
        paths_to_try.append(os.path.join(BACKEND_ROOT, path))

        # Handle 'app/backend/' prefix (path from project root)
        if path.startswith("app/backend/"):
            stripped = path[len("app/backend/") :]
            paths_to_try.append(os.path.join(BACKEND_ROOT, stripped))

    for p in paths_to_try:
        if os.path.exists(p):
            return p
    return None


@pytest.fixture(scope="session")
def google_meet_credentials() -> dict[str, Any]:
    """Load Google Meet service account credentials.

    Looks for credentials in this order:
    1. GOOGLE_MEET_CREDENTIALS_JSON env var (path to JSON file)
    2. GOOGLE_CALENDAR_CREDENTIALS_JSON env var (shared credentials)
    3. Default path: config/credentials/google-service-account.json
    """
    # Try environment variables
    for env_var in [
        "GOOGLE_MEET_CREDENTIALS_JSON",
        "GOOGLE_CALENDAR_CREDENTIALS_JSON",
    ]:
        creds_path = os.environ.get(env_var)
        if creds_path:
            resolved = resolve_credentials_path(creds_path)
            if resolved:
                with open(resolved) as f:
                    return json.load(f)

    # Try default path
    default_path = os.path.join(
        BACKEND_ROOT, "config", "credentials", "google-service-account.json"
    )
    if os.path.exists(default_path):
        with open(default_path) as f:
            return json.load(f)

    pytest.skip("Google Meet credentials not found. Set GOOGLE_MEET_CREDENTIALS_JSON.")
    return {}


@pytest.fixture(scope="session")
def delegated_user() -> str | None:
    """Get the delegated user email for domain-wide delegation tests."""
    return os.environ.get("GOOGLE_MEET_DELEGATED_USER")


@pytest.fixture
async def meet_client(google_meet_credentials: dict[str, Any]):
    """Create authenticated Google Meet client."""
    from src.integrations.google_meet import GoogleMeetClient

    client = GoogleMeetClient(credentials_json=google_meet_credentials)
    await client.authenticate()
    yield client
    await client.close()


@pytest.fixture
async def delegated_meet_client(
    google_meet_credentials: dict[str, Any],
    delegated_user: str | None,
):
    """Create authenticated client with domain-wide delegation."""
    if not delegated_user:
        pytest.skip(
            "GOOGLE_MEET_DELEGATED_USER not set. "
            "Set this env var to test domain-wide delegation."
        )

    from src.integrations.google_meet import GoogleMeetClient

    client = GoogleMeetClient(
        credentials_json=google_meet_credentials,
        delegated_user=delegated_user,
    )
    await client.authenticate()
    yield client
    await client.close()
