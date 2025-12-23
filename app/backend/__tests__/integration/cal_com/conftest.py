"""Integration test configuration for Cal.com API."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.cal_com import CalComClient

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


@pytest.fixture
def cal_com_api_key() -> str | None:
    """Get Cal.com API key from environment."""
    return os.getenv("CAL_COM_API_KEY")


@pytest.fixture
def has_cal_com_credentials() -> bool:
    """Check if Cal.com credentials are configured."""
    return bool(os.getenv("CAL_COM_API_KEY", "").strip())


@pytest.fixture
async def cal_com_client(cal_com_api_key: str | None) -> CalComClient | None:
    """Create Cal.com client with real API key.

    Yields:
        CalComClient instance or None if credentials not available.
    """
    if not cal_com_api_key:
        pytest.skip("CAL_COM_API_KEY not configured in .env")

    try:
        client = CalComClient(api_key=cal_com_api_key)
        yield client
        await client.close()
    except Exception as e:
        pytest.skip(f"Failed to initialize Cal.com client: {e}")


@pytest.fixture
def integration_marker() -> str:
    """Marker for integration tests."""
    return "integration"
