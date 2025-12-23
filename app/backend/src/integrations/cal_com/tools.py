"""Cal.com SDK tools for Claude Agent SDK integration.

Provides 11 callable tools for agents to interact with Cal.com:
1. get_user_profile - Get authenticated user info
2. list_event_types - List available event types
3. get_event_type - Get specific event type details
4. list_availability - Get available time slots
5. list_bookings - List all bookings/events
6. get_booking - Get booking details
7. create_booking - Create new booking
8. reschedule_booking - Reschedule existing booking
9. cancel_booking - Cancel booking
10. list_teams - List user's teams
11. get_team - Get team details
"""

import os
from datetime import datetime
from typing import Any

from src.integrations.cal_com.client import CalComClient
from src.integrations.cal_com.exceptions import CalComError

# Initialize client at module level (lazy loaded)
_client: CalComClient | None = None


def _get_client() -> CalComClient:
    """Get or create Cal.com client instance.

    Returns:
        CalComClient instance.

    Raises:
        ValueError: If API key not configured.
    """
    global _client
    if _client is None:
        api_key = os.getenv("CAL_COM_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "CAL_COM_API_KEY environment variable not set. " "Please configure it in .env file."
            )
        _client = CalComClient(api_key=api_key)
    return _client


# Tool 1: Get User Profile
async def get_user_profile() -> dict[str, Any]:
    """Get the authenticated user's Cal.com profile.

    Returns:
        User profile with name, email, timezone, locale.

    Example:
        >>> profile = await get_user_profile()
        >>> print(f"Name: {profile['name']}")
    """
    try:
        client = _get_client()
        user = await client.get_user()
        return {
            "success": True,
            "data": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "username": user.username,
                "timezone": user.timezone,
                "locale": user.locale,
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 2: List Event Types
async def list_event_types(
    owner_id: str | None = None,
    team_id: str | None = None,
) -> dict[str, Any]:
    """List all available event types for booking.

    Args:
        owner_id: Optional user/owner ID to filter by.
        team_id: Optional team ID to filter by.

    Returns:
        List of event types with title, slug, duration, description.

    Example:
        >>> types = await list_event_types()
        >>> for et in types['data']:
        ...     print(f"{et['title']} ({et['length']} min)")
    """
    try:
        client = _get_client()
        event_types = await client.list_event_types(
            owner_id=owner_id,
            team_id=team_id,
        )
        return {
            "success": True,
            "data": [
                {
                    "id": et.id,
                    "title": et.title,
                    "slug": et.slug,
                    "description": et.description,
                    "length": et.length,
                    "schedulingType": et.scheduling_type,
                }
                for et in event_types
            ],
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 3: Get Event Type Details
async def get_event_type(event_type_id: str) -> dict[str, Any]:
    """Get detailed information about a specific event type.

    Args:
        event_type_id: The event type identifier.

    Returns:
        Full event type configuration.

    Raises:
        ValueError: If event_type_id is empty.

    Example:
        >>> details = await get_event_type("evt_123")
        >>> print(f"Available: {details['data']['isActive']}")
    """
    if not event_type_id or not event_type_id.strip():
        return {"success": False, "error": "event_type_id is required"}

    try:
        client = _get_client()
        event_type = await client.get_event_type(event_type_id)
        return {
            "success": True,
            "data": {
                "id": event_type.id,
                "title": event_type.title,
                "slug": event_type.slug,
                "description": event_type.description,
                "length": event_type.length,
                "ownerId": event_type.owner_id,
                "isActive": event_type.is_active,
                "schedulingType": event_type.scheduling_type,
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 4: List Availability Slots
async def list_availability(
    user_id: str,
    start_date: str,
    end_date: str,
    event_type_id: str | None = None,
) -> dict[str, Any]:
    """Get available time slots for a user within a date range.

    Args:
        user_id: User identifier.
        start_date: Range start date (ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
        end_date: Range end date (ISO 8601 format).
        event_type_id: Optional specific event type for availability.

    Returns:
        List of available time slots with start/end times.

    Example:
        >>> slots = await list_availability(
        ...     user_id="user_123",
        ...     start_date="2024-01-15",
        ...     end_date="2024-01-20"
        ... )
        >>> for slot in slots['data']:
        ...     print(f"{slot['startTime']} to {slot['endTime']}")
    """
    if not user_id or not start_date or not end_date:
        return {"success": False, "error": "user_id, start_date, and end_date are required"}

    try:
        # Parse dates flexibly
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            start = datetime.fromisoformat(f"{start_date}T00:00:00")

        try:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            end = datetime.fromisoformat(f"{end_date}T23:59:59")

        client = _get_client()
        availability = await client.list_availability(user_id, start, end)

        return {
            "success": True,
            "data": [
                {
                    "userId": avail.user_id,
                    "startTime": avail.start_time.isoformat(),
                    "endTime": avail.end_time.isoformat(),
                    "isAvailable": avail.is_available,
                }
                for avail in availability
            ],
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}
    except (ValueError, AttributeError) as e:
        return {"success": False, "error": f"Invalid date format: {e}"}


# Tool 5: List Bookings/Events
async def list_bookings(
    limit: int = 10,
    skip: int = 0,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """List all bookings and events with optional filtering.

    Args:
        limit: Maximum results (default 10, max 100).
        skip: Skip N results for pagination (default 0).
        status: Filter by status (confirmed, tentative, cancelled).
        start_date: Filter by start date (ISO 8601).
        end_date: Filter by end date (ISO 8601).

    Returns:
        List of bookings with title, start/end times, attendees.

    Example:
        >>> bookings = await list_bookings(limit=20)
        >>> for booking in bookings['data']:
        ...     print(f"{booking['title']} @ {booking['startTime']}")
    """
    try:
        limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
        skip = max(skip, 0)

        filters = {}
        if status:
            filters["status"] = status
        if start_date:
            filters["startDate"] = start_date
        if end_date:
            filters["endDate"] = end_date

        client = _get_client()
        bookings = await client.list_bookings(limit=limit, skip=skip, filters=filters)

        return {
            "success": True,
            "data": [
                {
                    "id": booking.id,
                    "title": booking.title,
                    "description": booking.description,
                    "startTime": booking.start_time.isoformat(),
                    "endTime": booking.end_time.isoformat(),
                    "location": booking.location,
                    "organizerId": booking.organizer_id,
                    "attendees": booking.attendees,
                    "status": booking.status,
                }
                for booking in bookings
            ],
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 6: Get Booking Details
async def get_booking(booking_id: str) -> dict[str, Any]:
    """Get detailed information about a specific booking.

    Args:
        booking_id: The booking identifier.

    Returns:
        Complete booking information including all attendees.

    Example:
        >>> booking = await get_booking("booking_123")
        >>> print(f"Attendees: {booking['data']['attendees']}")
    """
    if not booking_id or not booking_id.strip():
        return {"success": False, "error": "booking_id is required"}

    try:
        client = _get_client()
        booking = await client.get_booking(booking_id)
        return {
            "success": True,
            "data": {
                "id": booking.id,
                "title": booking.title,
                "description": booking.description,
                "startTime": booking.start_time.isoformat(),
                "endTime": booking.end_time.isoformat(),
                "location": booking.location,
                "organizerId": booking.organizer_id,
                "attendees": booking.attendees,
                "eventTypeId": booking.event_type_id,
                "status": booking.status,
                "createdAt": booking.created_at.isoformat(),
                "updatedAt": booking.updated_at.isoformat(),
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 7: Create Booking
async def create_booking(
    event_type_id: str,
    start_time: str,
    end_time: str,
    attendee_name: str | None = None,
    attendee_email: str | None = None,
    attendee_timezone: str | None = None,
    notes: str | None = None,
    send_confirmation: bool = True,
) -> dict[str, Any]:
    """Create a new booking for an event type.

    Args:
        event_type_id: The event type to book.
        start_time: Booking start time (ISO 8601).
        end_time: Booking end time (ISO 8601).
        attendee_name: Attendee name (optional).
        attendee_email: Attendee email (optional).
        attendee_timezone: Attendee timezone in IANA format (optional).
        notes: Additional notes (optional).
        send_confirmation: Send confirmation email (default true).

    Returns:
        Created booking with confirmation details.

    Example:
        >>> booking = await create_booking(
        ...     event_type_id="evt_123",
        ...     start_time="2024-01-15T14:00:00",
        ...     end_time="2024-01-15T15:00:00",
        ...     attendee_email="user@example.com"
        ... )
        >>> print(f"Booking ID: {booking['data']['id']}")
    """
    if not event_type_id or not start_time or not end_time:
        return {
            "success": False,
            "error": "event_type_id, start_time, and end_time are required",
        }

    try:
        # Parse ISO 8601 datetimes
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError as e:
            return {"success": False, "error": f"Invalid datetime format: {e}"}

        client = _get_client()
        booking = await client.create_booking(
            event_type_id=event_type_id,
            start_time=start,
            end_time=end,
            attendee_name=attendee_name,
            attendee_email=attendee_email,
            attendee_timezone=attendee_timezone,
            notes=notes,
            send_confirmation=send_confirmation,
        )

        return {
            "success": True,
            "data": {
                "id": booking.id,
                "title": booking.title,
                "startTime": booking.start_time.isoformat(),
                "endTime": booking.end_time.isoformat(),
                "attendees": booking.attendees,
                "status": booking.status,
                "message": "Booking created successfully. Confirmation email sent to attendees.",
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 8: Reschedule Booking
async def reschedule_booking(
    booking_id: str,
    new_start_time: str,
    new_end_time: str,
    send_notification: bool = True,
) -> dict[str, Any]:
    """Reschedule an existing booking to a new date/time.

    Args:
        booking_id: The booking to reschedule.
        new_start_time: New start time (ISO 8601).
        new_end_time: New end time (ISO 8601).
        send_notification: Notify attendees (default true).

    Returns:
        Updated booking details.

    Example:
        >>> result = await reschedule_booking(
        ...     booking_id="booking_123",
        ...     new_start_time="2024-01-16T14:00:00",
        ...     new_end_time="2024-01-16T15:00:00"
        ... )
    """
    if not booking_id or not new_start_time or not new_end_time:
        return {
            "success": False,
            "error": "booking_id, new_start_time, and new_end_time are required",
        }

    try:
        # Parse ISO 8601 datetimes
        try:
            start = datetime.fromisoformat(new_start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(new_end_time.replace("Z", "+00:00"))
        except ValueError as e:
            return {"success": False, "error": f"Invalid datetime format: {e}"}

        client = _get_client()
        booking = await client.reschedule_event(
            booking_id=booking_id,
            new_start=start,
            new_end=end,
            send_notification=send_notification,
        )

        return {
            "success": True,
            "data": {
                "id": booking.id,
                "title": booking.title,
                "newStartTime": booking.start_time.isoformat(),
                "newEndTime": booking.end_time.isoformat(),
                "attendees": booking.attendees,
                "message": "Booking rescheduled successfully. Notification sent to attendees.",
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 9: Cancel Booking
async def cancel_booking(
    booking_id: str,
    cancellation_reason: str | None = None,
    send_notification: bool = True,
) -> dict[str, Any]:
    """Cancel an existing booking.

    Args:
        booking_id: The booking to cancel.
        cancellation_reason: Reason for cancellation (optional).
        send_notification: Notify attendees (default true).

    Returns:
        Confirmation of cancellation.

    Example:
        >>> result = await cancel_booking(
        ...     booking_id="booking_123",
        ...     cancellation_reason="Rescheduling needed"
        ... )
    """
    if not booking_id or not booking_id.strip():
        return {"success": False, "error": "booking_id is required"}

    try:
        client = _get_client()
        await client.cancel_event(
            booking_id=booking_id,
            reason=cancellation_reason,
        )

        return {
            "success": True,
            "data": {
                "bookingId": booking_id,
                "status": "cancelled",
                "reason": cancellation_reason,
                "message": f"Booking {booking_id} cancelled successfully. Notification sent to attendees.",
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 10: List Teams
async def list_teams() -> dict[str, Any]:
    """List all teams the user is a member of.

    Returns:
        List of teams with member counts and slugs.

    Example:
        >>> teams = await list_teams()
        >>> for team in teams['data']:
        ...     print(f"Team: {team['name']} ({len(team['members'])} members)")
    """
    try:
        client = _get_client()
        teams = await client.list_teams()
        return {
            "success": True,
            "data": [
                {
                    "id": team.id,
                    "name": team.name,
                    "slug": team.slug,
                    "logo": team.logo,
                    "bio": team.bio,
                    "memberCount": len(team.members),
                    "members": team.members,
                }
                for team in teams
            ],
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}


# Tool 11: Get Team Details
async def get_team(team_id: str) -> dict[str, Any]:
    """Get detailed information about a team.

    Args:
        team_id: The team identifier.

    Returns:
        Team information including members and settings.

    Example:
        >>> team = await get_team("team_123")
        >>> print(f"Team: {team['data']['name']} with {team['data']['memberCount']} members")
    """
    if not team_id or not team_id.strip():
        return {"success": False, "error": "team_id is required"}

    try:
        client = _get_client()
        team = await client.get_team(team_id)
        return {
            "success": True,
            "data": {
                "id": team.id,
                "name": team.name,
                "slug": team.slug,
                "logo": team.logo,
                "bio": team.bio,
                "memberCount": len(team.members),
                "members": team.members,
            },
        }
    except CalComError as e:
        return {"success": False, "error": str(e)}
