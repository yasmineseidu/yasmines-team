"""Fixtures for LinkedIn API tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.linkedin import LinkedInClient

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


@pytest.fixture
def valid_credentials() -> dict:
    """Valid LinkedIn OAuth2 credentials for testing."""
    return {
        "type": "oauth2",
        "access_token": "test_access_token_xyz",  # noqa: S105
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",  # noqa: S105
    }


@pytest.fixture
def valid_access_token() -> str:
    """Valid LinkedIn access token for testing."""
    return "test_access_token_xyz"  # noqa: S105


@pytest.fixture
def invalid_credentials() -> dict:
    """Invalid credentials (empty)."""
    return {}


@pytest.fixture
async def client(valid_credentials: dict) -> LinkedInClient:
    """Create a LinkedIn client with valid credentials."""
    return LinkedInClient(credentials_json=valid_credentials)


@pytest.fixture
async def client_with_token(valid_access_token: str) -> LinkedInClient:
    """Create a LinkedIn client with direct access token."""
    return LinkedInClient(access_token=valid_access_token)


@pytest.fixture
def linkedin_credentials() -> dict | None:
    """Get real LinkedIn credentials from .env.

    Returns None if credentials not configured (tests will be skipped).
    """
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        return None

    return {
        "type": "oauth2",
        "access_token": access_token,
        "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
        "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
    }


@pytest.fixture
async def live_linkedin_client(
    linkedin_credentials: dict | None,
) -> LinkedInClient | None:
    """Create LinkedIn client with live credentials.

    Returns None if credentials not configured (tests will be skipped).
    """
    if not linkedin_credentials:
        return None

    return LinkedInClient(credentials_json=linkedin_credentials)


@pytest.fixture
def live_api_enabled() -> bool:
    """Check if live API tests should run.

    Live API tests require LINKEDIN_ACCESS_TOKEN in .env.
    """
    return "LINKEDIN_ACCESS_TOKEN" in os.environ


# Sample test data for LinkedIn API testing
SAMPLE_TEST_DATA = {
    "post_text": "Hello from Claude! Testing the LinkedIn integration.",
    "comment_text": "Great post! This is a test comment.",
    "message_body": "Hi! This is a test message from the LinkedIn integration.",
    "connection_message": "I'd like to add you to my professional network.",
    "search_keywords": "software engineer",
}


# Mock response data
MOCK_PROFILE_RESPONSE = {
    "sub": "user123",
    "given_name": "Test",
    "family_name": "User",
    "email": "test@example.com",
}


MOCK_POST_RESPONSE = {
    "id": "urn:li:ugcPost:123456",
    "author": "urn:li:person:user123",
    "lifecycleState": "PUBLISHED",
}


MOCK_CONNECTIONS_RESPONSE = {
    "elements": [
        {
            "id": "conn1",
            "firstName": "Alice",
            "lastName": "Smith",
            "headline": "Software Engineer",
        },
        {
            "id": "conn2",
            "firstName": "Bob",
            "lastName": "Jones",
            "headline": "Product Manager",
        },
    ],
    "paging": {"count": 2, "start": 0, "total": 2},
}


MOCK_SEARCH_RESPONSE = {
    "elements": [
        {
            "profile": {
                "id": "profile1",
                "firstName": "Jane",
                "lastName": "Doe",
                "headline": "CEO",
            },
            "connectionDegree": "SECOND",
        },
    ],
    "paging": {"count": 1, "start": 0, "total": 100},
}
