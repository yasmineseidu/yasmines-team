"""Pytest configuration for integration tests.

Handles setup of environment variables, fixtures, and test database.
"""

import os
import pytest
from pathlib import Path

from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables from .env file."""
    # Load from project root .env
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@pytest.fixture(scope="session")
def google_drive_credentials() -> dict | None:
    """Get Google Drive credentials from environment."""
    from __tests__.fixtures.google_drive_fixtures import get_test_credentials

    try:
        return get_test_credentials()
    except ValueError:
        return None


@pytest.fixture(scope="session")
def google_drive_access_token() -> str | None:
    """Get pre-generated access token from environment."""
    from __tests__.fixtures.google_drive_fixtures import get_test_access_token

    return get_test_access_token()
