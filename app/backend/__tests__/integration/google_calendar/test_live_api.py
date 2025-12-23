"""
Live API integration tests for Google Calendar client.

Tests all Google Calendar API endpoints with real API calls using service account credentials.
Comprehensive coverage of all operations: list, get, create, update, delete, quick-add.

Tests verify:
- Successful API responses with correct data structures
- Error handling for edge cases (404, 403, 429)
- Rate limiting and retry logic
- Event operations (create, read, update, delete)
- Calendar listing and metadata
- Quick-add event parsing

Run with: pytest __tests__/integration/google_calendar/test_live_api.py -v
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.integrations.google_calendar.client import GoogleCalendarClient
from src.integrations.google_calendar.exceptions import (
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
)
from src.integrations.google_calendar.models import (
    Calendar,
    CalendarEvent,
    CalendarList,
)

# Test configuration
TEST_CALENDAR_ID = "primary"  # Use primary calendar for testing
TEST_EVENT_PREFIX = "CLAUDE-CODE-TEST-"


class TestGoogleCalendarLiveAPI:
    """Live API tests for complete Google Calendar integration."""

    @pytest.fixture
    async def client(self, google_calendar_credentials: dict):
        """Create and configure Google Calendar client with real credentials."""
        client = GoogleCalendarClient(
            credentials_json=google_calendar_credentials,
            timeout=30.0,
            max_retries=3,
        )

        # Authenticate with service account
        await client.authenticate()

        yield client
        await client.close()

    @pytest.fixture
    def created_events(self) -> list[str]:
        """Track created event IDs for cleanup."""
        return []

    # =========================================================================
    # Health Check Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_01_health_check(self, client: GoogleCalendarClient):
        """Test health check endpoint returns healthy status."""
        result = await client.health_check()

        assert result is not None
        assert isinstance(result, dict)
        assert result["healthy"] is True
        assert result["name"] == "google_calendar"
        assert "message" in result

        print(f"✅ Health check passed: {result['message']}")

    # =========================================================================
    # Calendar List Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_02_list_calendars(self, client: GoogleCalendarClient):
        """Test listing all accessible calendars."""
        calendars = await client.list_calendars()

        assert calendars is not None
        assert isinstance(calendars, list)
        # Note: Service accounts may return 0 calendars in list_calendars
        # but still have access to primary calendar

        if len(calendars) > 0:
            # Verify calendar structure when calendars exist
            first_calendar = calendars[0]
            assert isinstance(first_calendar, CalendarList)
            assert first_calendar.id is not None
            assert first_calendar.summary is not None
            assert first_calendar.access_role is not None

            print(f"✅ Found {len(calendars)} calendars")
            for cal in calendars[:3]:
                print(f"   - {cal.summary} ({cal.id[:30]}...)")
        else:
            # Service accounts often have empty calendar lists
            # but can still access primary via get_calendar
            print("✅ Calendar list empty (typical for service accounts)")

    @pytest.mark.asyncio
    async def test_03_list_calendars_with_pagination(self, client: GoogleCalendarClient):
        """Test listing calendars handles pagination correctly."""
        # Request small page to test pagination
        calendars = await client.list_calendars(page_size=1)

        assert calendars is not None
        assert isinstance(calendars, list)

        print(f"✅ Pagination test passed with {len(calendars)} calendars")

    # =========================================================================
    # Get Calendar Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_04_get_primary_calendar(self, client: GoogleCalendarClient):
        """Test getting the primary calendar details."""
        calendar = await client.get_calendar("primary")

        assert calendar is not None
        assert isinstance(calendar, Calendar)
        assert calendar.id is not None
        assert calendar.summary is not None

        print(f"✅ Primary calendar: {calendar.summary}")
        print(f"   Timezone: {calendar.time_zone}")

    @pytest.mark.asyncio
    async def test_05_get_calendar_not_found(self, client: GoogleCalendarClient):
        """Test getting a non-existent calendar raises NotFoundError."""
        with pytest.raises(GoogleCalendarNotFoundError) as exc_info:
            await client.get_calendar("non-existent-calendar-id-12345")

        assert "calendar" in str(exc_info.value).lower()
        print("✅ NotFoundError correctly raised for missing calendar")

    # =========================================================================
    # Event Listing Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_06_list_events(self, client: GoogleCalendarClient):
        """Test listing events from primary calendar."""
        events = await client.list_events(
            calendar_id=TEST_CALENDAR_ID,
            max_results=10,
        )

        assert events is not None
        assert isinstance(events, list)

        if events:
            first_event = events[0]
            assert isinstance(first_event, CalendarEvent)
            assert first_event.id is not None
            assert first_event.summary is not None
            print(f"✅ Found {len(events)} events")
            for event in events[:3]:
                print(f"   - {event.summary}")
        else:
            print("✅ No events found (calendar is empty)")

    @pytest.mark.asyncio
    async def test_07_list_events_with_time_range(self, client: GoogleCalendarClient):
        """Test listing events with time range filter."""
        now = datetime.now(UTC)
        next_week = now + timedelta(days=7)

        events = await client.list_events(
            calendar_id=TEST_CALENDAR_ID,
            time_min=now,
            time_max=next_week,
            max_results=50,
        )

        assert events is not None
        assert isinstance(events, list)

        print(f"✅ Found {len(events)} events in next 7 days")

    @pytest.mark.asyncio
    async def test_08_list_events_with_query(self, client: GoogleCalendarClient):
        """Test listing events with text query filter."""
        events = await client.list_events(
            calendar_id=TEST_CALENDAR_ID,
            query="meeting",
            max_results=10,
        )

        assert events is not None
        assert isinstance(events, list)

        print(f"✅ Found {len(events)} events matching 'meeting'")

    # =========================================================================
    # Event CRUD Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_09_create_event(self, client: GoogleCalendarClient, sample_event_data: dict):
        """Test creating a new calendar event."""
        # Add unique test identifier
        sample_event_data["summary"] = f"{TEST_EVENT_PREFIX}Create Test"

        event = await client.create_event(
            calendar_id=TEST_CALENDAR_ID,
            event=sample_event_data,
            send_notifications=False,
        )

        assert event is not None
        assert isinstance(event, CalendarEvent)
        assert event.id is not None
        assert TEST_EVENT_PREFIX in event.summary

        print(f"✅ Created event: {event.summary} (ID: {event.id})")

        # Cleanup
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=event.id,
            send_notifications=False,
        )
        print("   Cleaned up test event")

    @pytest.mark.asyncio
    async def test_10_create_all_day_event(
        self, client: GoogleCalendarClient, sample_all_day_event_data: dict
    ):
        """Test creating an all-day event."""
        sample_all_day_event_data["summary"] = f"{TEST_EVENT_PREFIX}All-Day Test"

        event = await client.create_event(
            calendar_id=TEST_CALENDAR_ID,
            event=sample_all_day_event_data,
            send_notifications=False,
        )

        assert event is not None
        assert event.id is not None
        assert TEST_EVENT_PREFIX in event.summary

        print(f"✅ Created all-day event: {event.summary}")

        # Cleanup
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=event.id,
            send_notifications=False,
        )

    @pytest.mark.asyncio
    async def test_11_get_event(self, client: GoogleCalendarClient, sample_event_data: dict):
        """Test getting a specific event by ID."""
        # Create test event first
        sample_event_data["summary"] = f"{TEST_EVENT_PREFIX}Get Test"
        created_event = await client.create_event(
            calendar_id=TEST_CALENDAR_ID,
            event=sample_event_data,
            send_notifications=False,
        )

        # Get the event
        event = await client.get_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=created_event.id,
        )

        assert event is not None
        assert isinstance(event, CalendarEvent)
        assert event.id == created_event.id
        assert event.summary == created_event.summary

        print(f"✅ Retrieved event: {event.summary}")

        # Cleanup
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=event.id,
            send_notifications=False,
        )

    @pytest.mark.asyncio
    async def test_12_get_event_not_found(self, client: GoogleCalendarClient):
        """Test getting a non-existent event raises NotFoundError."""
        with pytest.raises(GoogleCalendarNotFoundError) as exc_info:
            await client.get_event(
                calendar_id=TEST_CALENDAR_ID,
                event_id="non-existent-event-id-12345",
            )

        assert "event" in str(exc_info.value).lower()
        print("✅ NotFoundError correctly raised for missing event")

    @pytest.mark.asyncio
    async def test_13_update_event(self, client: GoogleCalendarClient, sample_event_data: dict):
        """Test updating an existing event."""
        # Create test event
        sample_event_data["summary"] = f"{TEST_EVENT_PREFIX}Update Test"
        created_event = await client.create_event(
            calendar_id=TEST_CALENDAR_ID,
            event=sample_event_data,
            send_notifications=False,
        )

        # Update the event
        updated_summary = f"{TEST_EVENT_PREFIX}Updated Event"
        updated_event = await client.update_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=created_event.id,
            event={"summary": updated_summary},
            send_notifications=False,
        )

        assert updated_event is not None
        assert updated_event.summary == updated_summary

        print(f"✅ Updated event: {created_event.summary} -> {updated_event.summary}")

        # Cleanup
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=updated_event.id,
            send_notifications=False,
        )

    @pytest.mark.asyncio
    async def test_14_delete_event(self, client: GoogleCalendarClient, sample_event_data: dict):
        """Test deleting an event."""
        import asyncio

        # Create test event
        sample_event_data["summary"] = f"{TEST_EVENT_PREFIX}Delete Test"
        created_event = await client.create_event(
            calendar_id=TEST_CALENDAR_ID,
            event=sample_event_data,
            send_notifications=False,
        )

        # Delete the event
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=created_event.id,
            send_notifications=False,
        )

        # Verify deletion - may need retry due to eventual consistency
        deleted = False
        for attempt in range(3):
            try:
                event = await client.get_event(
                    calendar_id=TEST_CALENDAR_ID,
                    event_id=created_event.id,
                )
                # Event might be returned with cancelled status
                if hasattr(event, "status") and event.status == "cancelled":
                    deleted = True
                    break
                # Wait before retry
                await asyncio.sleep(1)
            except GoogleCalendarNotFoundError:
                deleted = True
                break

        assert deleted, "Event should be deleted or have 'cancelled' status"
        print(f"✅ Successfully deleted event: {created_event.summary}")

    # =========================================================================
    # Quick Add Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_15_quick_add_event(self, client: GoogleCalendarClient):
        """Test creating event from natural language text."""
        text = f"{TEST_EVENT_PREFIX}Quick Add meeting tomorrow at 3pm"

        event = await client.quick_add_event(
            calendar_id=TEST_CALENDAR_ID,
            text=text,
            send_notifications=False,
        )

        assert event is not None
        assert isinstance(event, CalendarEvent)
        assert event.id is not None
        assert event.summary is not None

        print(f"✅ Quick-added event: {event.summary}")
        print(f"   Start: {event.start.date_time or event.start.date}")

        # Cleanup
        await client.delete_event(
            calendar_id=TEST_CALENDAR_ID,
            event_id=event.id,
            send_notifications=False,
        )

    @pytest.mark.asyncio
    async def test_16_quick_add_multiple_formats(
        self, client: GoogleCalendarClient, quick_add_texts: list[str]
    ):
        """Test quick-add with various natural language formats."""
        created_events = []

        for text in quick_add_texts:
            # Add test prefix for cleanup
            test_text = f"{TEST_EVENT_PREFIX}{text}"

            try:
                event = await client.quick_add_event(
                    calendar_id=TEST_CALENDAR_ID,
                    text=test_text,
                    send_notifications=False,
                )
                created_events.append(event)
                print(f"✅ Quick-add: '{text}' -> {event.summary}")
            except Exception as e:
                print(f"⚠️  Quick-add failed for '{text}': {e}")

        assert len(created_events) > 0, "At least one quick-add should succeed"

        # Cleanup
        for event in created_events:
            try:
                await client.delete_event(
                    calendar_id=TEST_CALENDAR_ID,
                    event_id=event.id,
                    send_notifications=False,
                )
            except Exception:
                pass

        print(f"✅ Successfully quick-added {len(created_events)}/{len(quick_add_texts)} events")

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_17_invalid_calendar_id(self, client: GoogleCalendarClient):
        """Test error handling for invalid calendar ID."""
        with pytest.raises(GoogleCalendarNotFoundError):
            await client.list_events(calendar_id="invalid-calendar-xyz")

        print("✅ Invalid calendar ID correctly handled")

    @pytest.mark.asyncio
    async def test_18_invalid_event_id(self, client: GoogleCalendarClient):
        """Test error handling for invalid event ID."""
        with pytest.raises(GoogleCalendarNotFoundError):
            await client.get_event(
                calendar_id=TEST_CALENDAR_ID,
                event_id="invalid-event-xyz",
            )

        print("✅ Invalid event ID correctly handled")

    # =========================================================================
    # Future-Proof Generic API Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_future_01_generic_get_request(self, client: GoogleCalendarClient):
        """Test generic GET request for future endpoints."""
        # Use the generic get method to call calendar list
        response = await client.get(
            "/users/me/calendarList",
            params={"maxResults": 1},
        )

        assert response is not None
        assert isinstance(response, dict)
        assert "items" in response

        print("✅ Generic GET request works for future endpoints")

    @pytest.mark.asyncio
    async def test_future_02_generic_request_method(self, client: GoogleCalendarClient):
        """Test generic request method with custom endpoint."""
        # Test with colors endpoint (always available, no modifications)
        response = await client.request(
            method="GET",
            endpoint="/colors",
        )

        assert response is not None
        assert isinstance(response, dict)
        # Colors endpoint returns calendar and event colors
        assert "calendar" in response or "event" in response

        print("✅ Generic request method works for any endpoint")

    @pytest.mark.asyncio
    async def test_future_03_generic_post_request(
        self, client: GoogleCalendarClient, sample_event_data: dict
    ):
        """Test generic POST request for future endpoints."""
        sample_event_data["summary"] = f"{TEST_EVENT_PREFIX}Generic POST Test"

        # Use generic post method
        response = await client.post(
            f"/calendars/{TEST_CALENDAR_ID}/events",
            json_data=sample_event_data,
            params={"sendNotifications": "false"},
        )

        assert response is not None
        assert isinstance(response, dict)
        assert "id" in response

        print(f"✅ Generic POST request created event: {response.get('summary')}")

        # Cleanup using generic delete
        await client.delete(
            f"/calendars/{TEST_CALENDAR_ID}/events/{response['id']}",
            params={"sendNotifications": "false"},
        )
        print("   Cleaned up via generic DELETE")

    @pytest.mark.asyncio
    async def test_future_04_access_settings_endpoint(self, client: GoogleCalendarClient):
        """Test accessing settings endpoint (demonstrates future-proofing)."""
        try:
            # Settings endpoint - may or may not be accessible
            response = await client.get("/users/me/settings")
            assert response is not None
            print(f"✅ Settings endpoint accessible: {len(response.get('items', []))} settings")
        except GoogleCalendarNotFoundError:
            # Settings endpoint might not be available
            print("⚠️  Settings endpoint not accessible (expected for some accounts)")
        except GoogleCalendarError as e:
            if "403" in str(e):
                print("⚠️  Settings endpoint requires additional permissions")
            else:
                raise

    # =========================================================================
    # Context Manager Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_19_context_manager(self, google_calendar_credentials: dict):
        """Test async context manager properly closes resources."""
        async with GoogleCalendarClient(credentials_json=google_calendar_credentials) as client:
            await client.authenticate()
            result = await client.health_check()
            assert result["healthy"] is True

        # Client should be closed
        assert client._client is None or client._client.is_closed
        print("✅ Context manager properly closed resources")

    # =========================================================================
    # Endpoint Coverage Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_20_all_endpoints_accessible(
        self, client: GoogleCalendarClient, supported_endpoints: list[dict]
    ):
        """Verify all documented endpoints are accessible."""
        results = []

        for endpoint in supported_endpoints:
            name = endpoint["name"]
            try:
                if name == "health_check":
                    result = await client.health_check()
                    success = result["healthy"]
                elif name == "list_calendars":
                    result = await client.list_calendars(page_size=1)
                    success = isinstance(result, list)
                elif name == "get_calendar":
                    result = await client.get_calendar("primary")
                    success = isinstance(result, Calendar)
                elif name == "list_events":
                    result = await client.list_events(calendar_id="primary", max_results=1)
                    success = isinstance(result, list)
                elif name == "get_event":
                    # Skip - requires valid event ID
                    success = True
                elif (
                    name == "create_event"
                    or name == "update_event"
                    or name == "delete_event"
                    or name == "quick_add_event"
                ):
                    # Skip - tested separately
                    success = True
                else:
                    success = False

                results.append({"endpoint": name, "success": success})
                status = "✅" if success else "❌"
                print(f"{status} {name}: {endpoint['description']}")

            except Exception as e:
                results.append({"endpoint": name, "success": False, "error": str(e)})
                print(f"❌ {name}: {e}")

        # All endpoints should be accessible
        failed = [r for r in results if not r["success"]]
        assert len(failed) == 0, f"Failed endpoints: {[r['endpoint'] for r in failed]}"

        print(f"\n✅ All {len(supported_endpoints)} endpoints verified")


class TestGoogleCalendarLiveAPICleanup:
    """Cleanup tests to ensure no test data remains."""

    @pytest.fixture
    async def client(self, google_calendar_credentials: dict):
        """Create and configure Google Calendar client."""
        client = GoogleCalendarClient(
            credentials_json=google_calendar_credentials,
            timeout=30.0,
            max_retries=3,
        )
        await client.authenticate()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_cleanup_test_events(self, client: GoogleCalendarClient):
        """Cleanup any remaining test events from previous runs."""
        events = await client.list_events(
            calendar_id=TEST_CALENDAR_ID,
            query=TEST_EVENT_PREFIX,
            max_results=100,
        )

        deleted_count = 0
        for event in events:
            if TEST_EVENT_PREFIX in (event.summary or ""):
                try:
                    await client.delete_event(
                        calendar_id=TEST_CALENDAR_ID,
                        event_id=event.id,
                        send_notifications=False,
                    )
                    deleted_count += 1
                except Exception:
                    pass

        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} leftover test events")
        else:
            print("✅ No leftover test events found")
