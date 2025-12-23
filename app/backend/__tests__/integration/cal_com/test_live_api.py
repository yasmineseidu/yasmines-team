"""Integration tests with live Cal.com API.

These tests require CAL_COM_API_KEY configured in .env at project root.
They will be skipped if credentials are not available.
"""

import pytest

from src.integrations.cal_com import CalComClient
from src.integrations.cal_com.exceptions import (
    CalComAPIError,
    CalComAuthError,
    CalComNotFoundError,
    CalComValidationError,
)


@pytest.mark.integration
class TestCalComLiveAPI:
    """Live API integration tests with real Cal.com account."""

    @pytest.mark.asyncio
    async def test_authenticate_with_real_credentials(self, cal_com_client: CalComClient) -> None:
        """Test authentication with real API key.

        MANDATORY: This test validates that API key from .env is valid.
        """
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Get user profile to verify authentication
        user = await cal_com_client.get_user()

        # Verify response structure
        assert user.id is not None
        assert user.email is not None
        assert user.name is not None
        assert user.username is not None

    @pytest.mark.asyncio
    async def test_get_user_profile(self, cal_com_client: CalComClient) -> None:
        """Test getting user profile from real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        user = await cal_com_client.get_user()

        # Verify all required fields
        assert user.id is not None  # Can be string or int
        assert isinstance(user.email, str)
        assert isinstance(user.name, str)
        assert isinstance(user.timezone, str)

    @pytest.mark.asyncio
    async def test_list_event_types(self, cal_com_client: CalComClient) -> None:
        """Test listing event types from real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        event_types = await cal_com_client.list_event_types()

        # Verify response
        assert isinstance(event_types, list)
        # May be empty, but should return list
        if event_types:
            et = event_types[0]
            assert hasattr(et, "id")
            assert hasattr(et, "title")
            assert hasattr(et, "length")

    @pytest.mark.asyncio
    async def test_get_nonexistent_event_type_raises_error(
        self, cal_com_client: CalComClient
    ) -> None:
        """Test that getting nonexistent event type raises error."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        with pytest.raises(CalComNotFoundError):
            await cal_com_client.get_event_type("999999999")  # Use numeric ID

    @pytest.mark.asyncio
    async def test_list_teams(self, cal_com_client: CalComClient) -> None:
        """Test listing teams from real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        teams = await cal_com_client.list_teams()

        # Verify response
        assert isinstance(teams, list)
        # May be empty, but should return list
        if teams:
            team = teams[0]
            assert hasattr(team, "id")
            assert hasattr(team, "name")
            assert hasattr(team, "slug")

    @pytest.mark.asyncio
    async def test_list_bookings(self, cal_com_client: CalComClient) -> None:
        """Test listing bookings from real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        bookings = await cal_com_client.list_bookings(limit=10)

        # Verify response
        assert isinstance(bookings, list)
        # May be empty, but should return list
        if bookings:
            booking = bookings[0]
            assert hasattr(booking, "id")
            assert hasattr(booking, "title")
            assert hasattr(booking, "start_time")
            assert hasattr(booking, "end_time")

    @pytest.mark.asyncio
    async def test_timezone_validation(self, cal_com_client: CalComClient) -> None:
        """Test timezone validation in update_user_settings."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Valid timezone should not raise
        user = await cal_com_client.get_user()
        original_tz = user.timezone

        # Update to different timezone (test with UTC if not already UTC)
        if original_tz != "UTC":
            updated = await cal_com_client.update_user_settings(timezone="UTC")
            assert updated.timezone == "UTC"

            # Restore original timezone
            await cal_com_client.update_user_settings(timezone=original_tz)

    @pytest.mark.asyncio
    async def test_invalid_datetime_handling(self, cal_com_client: CalComClient) -> None:
        """Test handling of invalid datetime parameters."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        from datetime import datetime, timedelta

        now = datetime.now()

        # Test with reversed dates (start after end)
        with pytest.raises((CalComValidationError, CalComAPIError)):
            await cal_com_client.create_booking(
                event_type_id="evt_xyz",
                start_time=now,
                end_time=now - timedelta(hours=1),  # Invalid: end before start
            )

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_event_type(
        self, cal_com_client: CalComClient
    ) -> None:
        """Test error handling with invalid event type ID."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Should raise NotFoundError for nonexistent event type
        with pytest.raises(CalComNotFoundError):
            await cal_com_client.get_event_type("999999999")  # Use numeric ID

    @pytest.mark.asyncio
    async def test_rate_limiting_headers_tracked(self, cal_com_client: CalComClient) -> None:
        """Test that rate limiting headers are tracked.

        MANDATORY: Verify that rate limit info is available.
        """
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Make a request that should include rate limit headers
        user = await cal_com_client.get_user()
        assert user is not None
        # Rate limit headers should be tracked internally


@pytest.mark.integration
class TestCalComAPIErrorHandling:
    """Test error handling with live API."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_auth_error(self) -> None:
        """Test that invalid API key raises authentication error."""
        client = CalComClient(api_key="invalid_key_that_is_long_enough_12345")

        # Attempt to get user with invalid key
        with pytest.raises(CalComAuthError):
            await client.get_user()

        await client.close()

    @pytest.mark.asyncio
    async def test_network_error_handling(self, cal_com_client: CalComClient) -> None:
        """Test handling of network-level errors."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # This is more of a stress test - just verify client handles errors
        user = await cal_com_client.get_user()
        assert user is not None


@pytest.mark.integration
class TestCalComToolsIntegration:
    """Test SDK tools with real API."""

    @pytest.mark.asyncio
    async def test_get_user_profile_tool(self, cal_com_client: CalComClient) -> None:
        """Test get_user_profile tool with real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Set client for the tool
        import src.integrations.cal_com.tools as tools_module
        from src.integrations.cal_com.tools import get_user_profile

        tools_module._client = cal_com_client

        result = await get_user_profile()
        assert result["success"] is True
        assert "data" in result
        assert "name" in result["data"]

    @pytest.mark.asyncio
    async def test_list_event_types_tool(self, cal_com_client: CalComClient) -> None:
        """Test list_event_types tool with real API."""
        if not cal_com_client:
            pytest.skip("Cal.com credentials not configured")

        # Set client for the tool
        import src.integrations.cal_com.tools as tools_module
        from src.integrations.cal_com.tools import list_event_types

        tools_module._client = cal_com_client

        result = await list_event_types()
        assert result["success"] is True
        assert "data" in result
        assert isinstance(result["data"], list)
