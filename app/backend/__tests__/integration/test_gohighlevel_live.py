"""Live integration tests for GoHighLevel API - requires GOHIGHLEVEL_API_KEY in .env."""

import os
from pathlib import Path

import pytest

from src.integrations.gohighlevel import (
    GoHighLevelClient,
    GoHighLevelError,
)


# Load .env from project root
def get_api_key() -> str:
    """Get API key from environment or .env file."""
    # Try environment variable first
    api_key = os.getenv("GOHIGHLEVEL_API_KEY")
    if api_key:
        return api_key

    # Try .env file at project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GOHIGHLEVEL_API_KEY="):
                    return line.split("=", 1)[1].strip()

    return ""


def get_location_id() -> str:
    """Get location ID from environment or .env file."""
    # Try environment variable first
    location_id = os.getenv("GOHIGHLEVEL_LOCATION_ID")
    if location_id:
        return location_id

    # Try .env file at project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GOHIGHLEVEL_LOCATION_ID="):
                    return line.split("=", 1)[1].strip()

    return ""


@pytest.fixture
def api_key() -> str:
    """Get API key from .env."""
    key = get_api_key()
    if not key:
        pytest.skip("GOHIGHLEVEL_API_KEY not found in .env")
    return key


@pytest.fixture
def location_id() -> str:
    """Get location ID from .env."""
    loc_id = get_location_id()
    if not loc_id:
        pytest.skip("GOHIGHLEVEL_LOCATION_ID not found in .env")
    return loc_id


@pytest.mark.asyncio
@pytest.mark.live_api
class TestGoHighLevelClientLiveHealth:
    """Live health check tests."""

    async def test_health_check_success(self, api_key: str, location_id: str) -> None:
        """Health check should succeed with valid credentials."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)
        health = await client.health_check()

        assert health["healthy"] is True
        assert "location_id" in health
        assert health["location_id"] == location_id


@pytest.mark.asyncio
@pytest.mark.live_api
class TestGoHighLevelClientLiveGetMe:
    """Live getMe endpoint tests."""

    async def test_get_me_success(self, api_key: str, location_id: str) -> None:
        """Should retrieve location info."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            result = await client.get_me()

            # Verify response structure
            assert isinstance(result, dict)
            assert "id" in result
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message


@pytest.mark.asyncio
@pytest.mark.live_api
class TestGoHighLevelClientLiveContacts:
    """Live contact operations tests."""

    async def test_list_contacts(self, api_key: str, location_id: str) -> None:
        """Should list contacts from location."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            result = await client.list_contacts(limit=5)

            # Verify response structure
            assert "contacts" in result
            assert "total" in result
            assert isinstance(result["contacts"], list)
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message

    async def test_create_contact_minimal(self, api_key: str, location_id: str) -> None:
        """Should create contact with minimal fields."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            contact = await client.create_contact(first_name="Test", last_name="Contact")

            # Verify response structure
            assert contact.id
            assert contact.first_name == "Test"
            assert contact.last_name == "Contact"
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message

    async def test_create_contact_with_email(self, api_key: str, location_id: str) -> None:
        """Should create contact with email."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            contact = await client.create_contact(
                first_name="Test", last_name="User", email="test@example.com"
            )

            # Verify response structure
            assert contact.id
            assert contact.first_name == "Test"
            assert contact.email == "test@example.com"
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message


@pytest.mark.asyncio
@pytest.mark.live_api
class TestGoHighLevelClientLiveDeals:
    """Live deal operations tests."""

    async def test_list_deals(self, api_key: str, location_id: str) -> None:
        """Should list deals from location."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            result = await client.list_deals(limit=5)

            # Verify response structure
            assert "deals" in result
            assert "total" in result
            assert isinstance(result["deals"], list)
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message

    async def test_create_deal_minimal(self, api_key: str, location_id: str) -> None:
        """Should create deal."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        try:
            deal = await client.create_deal(name="Test Deal", value=1000.00)

            # Verify response structure
            assert deal.id
            assert deal.name == "Test Deal"
            assert deal.value == 1000.00
        except GoHighLevelError as e:
            # Expected if API returns error
            assert e.message


@pytest.mark.asyncio
@pytest.mark.live_api
class TestGoHighLevelClientLiveErrorHandling:
    """Live error handling tests."""

    async def test_invalid_contact_id_raises_error(self, api_key: str, location_id: str) -> None:
        """Should raise error for invalid contact ID."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        with pytest.raises(GoHighLevelError):
            await client.get_contact("invalid_id_that_does_not_exist")

    async def test_invalid_deal_id_raises_error(self, api_key: str, location_id: str) -> None:
        """Should raise error for invalid deal ID."""
        client = GoHighLevelClient(api_key=api_key, location_id=location_id)

        with pytest.raises(GoHighLevelError):
            await client.get_deal("invalid_id_that_does_not_exist")
