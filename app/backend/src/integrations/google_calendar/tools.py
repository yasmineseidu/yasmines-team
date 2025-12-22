"""
Google Calendar tools for agent integration.

Provides MCP tools for agents to interact with Google Calendar API.
Supports listing calendars, CRUD operations on events, and quick add.
"""

import logging
from datetime import datetime
from typing import Any

from src.integrations.google_calendar.client import GoogleCalendarClient
from src.integrations.google_calendar.models import EventDateTime

logger = logging.getLogger(__name__)


async def list_calendars_tool() -> dict[str, Any]:
    """
    List all accessible Google Calendars.

    Returns:
        Dictionary with calendars list containing id, summary, and accessRole

    Raises:
        GoogleCalendarAPIError: If operation fails
    """
    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        calendars = await client.list_calendars()
        return {
            "success": True,
            "calendars": [
                {
                    "id": cal.id,
                    "summary": cal.summary,
                    "description": cal.description,
                    "accessRole": cal.access_role,
                    "primary": cal.primary,
                    "timeZone": cal.time_zone,
                }
                for cal in calendars
            ],
            "count": len(calendars),
        }
    finally:
        await client.close()


async def get_calendar_tool(calendar_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific calendar.

    Args:
        calendar_id: Calendar ID or 'primary' for the primary calendar

    Returns:
        Calendar details including timezone, accessibility, etc.

    Raises:
        GoogleCalendarNotFoundError: If calendar not found
        GoogleCalendarAPIError: If operation fails
    """
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        calendar = await client.get_calendar(calendar_id.strip())
        return {
            "success": True,
            "calendar": {
                "id": calendar.id,
                "summary": calendar.summary,
                "description": calendar.description,
                "timeZone": calendar.time_zone,
                "location": calendar.location,
                "primary": calendar.primary,
                "accessRole": calendar.access_role,
            },
        }
    finally:
        await client.close()


async def list_events_tool(
    calendar_id: str = "primary",
    start_date: str | None = None,
    end_date: str | None = None,
    search_query: str | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """
    List events from a calendar with optional date range filtering.

    Args:
        calendar_id: Calendar ID or 'primary' (default)
        start_date: Lower bound for event start time (ISO 8601 format)
        end_date: Upper bound for event start time (ISO 8601 format)
        search_query: Free-text search query
        max_results: Maximum events to return (default 10, max 250)

    Returns:
        List of events with key details

    Raises:
        GoogleCalendarAPIError: If operation fails
        GoogleCalendarNotFoundError: If calendar not found
    """
    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        # Parse dates
        time_min = None
        time_max = None

        if start_date:
            try:
                time_min = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                return {"success": False, "error": f"Invalid start_date format: {start_date}"}

        if end_date:
            try:
                time_max = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                return {"success": False, "error": f"Invalid end_date format: {end_date}"}

        events = await client.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            query=search_query,
            max_results=min(max_results, 250),
        )

        return {
            "success": True,
            "events": [
                {
                    "id": event.id,
                    "summary": event.summary,
                    "description": event.description,
                    "location": event.location,
                    "start": _format_event_datetime(event.start),
                    "end": _format_event_datetime(event.end),
                    "status": event.status,
                    "htmlLink": event.html_link,
                    "attendees": [
                        {"email": a.email, "responseStatus": a.response_status}
                        for a in (event.attendees or [])
                    ],
                }
                for event in events
            ],
            "count": len(events),
        }
    finally:
        await client.close()


async def get_event_tool(calendar_id: str, event_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific event.

    Args:
        calendar_id: Calendar ID or 'primary'
        event_id: Event ID

    Returns:
        Complete event information including attendees, description, etc.

    Raises:
        GoogleCalendarNotFoundError: If event not found
        GoogleCalendarAPIError: If operation fails
    """
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}
    if not event_id or not event_id.strip():
        return {"success": False, "error": "event_id is required"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        event = await client.get_event(calendar_id.strip(), event_id.strip())
        return {
            "success": True,
            "event": {
                "id": event.id,
                "summary": event.summary,
                "description": event.description,
                "location": event.location,
                "start": _format_event_datetime(event.start),
                "end": _format_event_datetime(event.end),
                "status": event.status,
                "htmlLink": event.html_link,
                "created": event.created.isoformat() if event.created else None,
                "updated": event.updated.isoformat() if event.updated else None,
                "creator": event.creator,
                "organizer": event.organizer,
                "attendees": [
                    {
                        "email": a.email,
                        "displayName": a.display_name,
                        "responseStatus": a.response_status,
                        "optional": a.optional,
                    }
                    for a in (event.attendees or [])
                ],
                "recurrence": event.recurrence,
                "visibility": event.visibility,
            },
        }
    finally:
        await client.close()


async def create_event_tool(
    calendar_id: str,
    title: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    send_notifications: bool = True,
) -> dict[str, Any]:
    """
    Create a new event in a calendar.

    Args:
        calendar_id: Calendar ID or 'primary'
        title: Event title (1-255 characters)
        start_time: Start time (ISO 8601 format with timezone)
        end_time: End time (must be after start_time)
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
        send_notifications: Send invitations to attendees (default: True)

    Returns:
        Created event with full details

    Raises:
        GoogleCalendarValidationError: If input is invalid
        GoogleCalendarAPIError: If operation fails
    """
    # Validate required fields
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}
    if not title or not title.strip():
        return {"success": False, "error": "title is required"}
    if len(title) > 255:
        return {"success": False, "error": "title cannot exceed 255 characters"}
    if not start_time:
        return {"success": False, "error": "start_time is required"}
    if not end_time:
        return {"success": False, "error": "end_time is required"}

    # Parse times
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        return {"success": False, "error": f"Invalid start_time format: {start_time}"}

    try:
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        return {"success": False, "error": f"Invalid end_time format: {end_time}"}

    if start_dt >= end_dt:
        return {"success": False, "error": "start_time must be before end_time"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        event_data = {
            "summary": title.strip(),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }

        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if attendees:
            event_data["attendees"] = attendees

        event = await client.create_event(
            calendar_id=calendar_id.strip(),
            event=event_data,
            send_notifications=send_notifications,
        )

        logger.info(f"Created event: {event.id}")
        return {
            "success": True,
            "event": {
                "id": event.id,
                "summary": event.summary,
                "htmlLink": event.html_link,
                "start": _format_event_datetime(event.start),
                "end": _format_event_datetime(event.end),
            },
        }
    finally:
        await client.close()


async def update_event_tool(
    calendar_id: str,
    event_id: str,
    title: str | None = None,
    description: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
    send_notifications: bool = True,
) -> dict[str, Any]:
    """
    Update an existing event in a calendar.

    Supports partial updates - only provided fields will be updated.

    Args:
        calendar_id: Calendar ID or 'primary'
        event_id: Event ID to update
        title: New event title (optional)
        description: New description (optional)
        start_time: New start time (optional)
        end_time: New end time (optional)
        location: New location (optional)
        send_notifications: Notify attendees of changes (default: True)

    Returns:
        Updated event details

    Raises:
        GoogleCalendarNotFoundError: If event not found
        GoogleCalendarValidationError: If input is invalid
        GoogleCalendarAPIError: If operation fails
    """
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}
    if not event_id or not event_id.strip():
        return {"success": False, "error": "event_id is required"}

    if title is not None and len(title) > 255:
        return {"success": False, "error": "title cannot exceed 255 characters"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        event_data: dict[str, Any] = {}

        if title is not None:
            event_data["summary"] = title.strip()
        if description is not None:
            event_data["description"] = description
        if location is not None:
            event_data["location"] = location

        if start_time is not None:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                event_data["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
            except ValueError:
                return {"success": False, "error": f"Invalid start_time format: {start_time}"}

        if end_time is not None:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                event_data["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}
            except ValueError:
                return {"success": False, "error": f"Invalid end_time format: {end_time}"}

        if not event_data:
            return {"success": False, "error": "At least one field to update is required"}

        event = await client.update_event(
            calendar_id=calendar_id.strip(),
            event_id=event_id.strip(),
            event=event_data,
            send_notifications=send_notifications,
        )

        logger.info(f"Updated event: {event.id}")
        return {
            "success": True,
            "event": {
                "id": event.id,
                "summary": event.summary,
                "htmlLink": event.html_link,
                "start": _format_event_datetime(event.start),
                "end": _format_event_datetime(event.end),
            },
        }
    finally:
        await client.close()


async def delete_event_tool(
    calendar_id: str,
    event_id: str,
    send_notifications: bool = True,
) -> dict[str, Any]:
    """
    Delete an event from a calendar.

    Args:
        calendar_id: Calendar ID or 'primary'
        event_id: Event ID to delete
        send_notifications: Send cancellation notices to attendees (default: True)

    Returns:
        Confirmation message with event ID

    Raises:
        GoogleCalendarNotFoundError: If event not found
        GoogleCalendarAPIError: If operation fails
    """
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}
    if not event_id or not event_id.strip():
        return {"success": False, "error": "event_id is required"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        await client.delete_event(
            calendar_id=calendar_id.strip(),
            event_id=event_id.strip(),
            send_notifications=send_notifications,
        )

        logger.info(f"Deleted event: {event_id}")
        return {
            "success": True,
            "message": f"Event deleted: {event_id}",
            "event_id": event_id,
        }
    finally:
        await client.close()


async def quick_add_event_tool(
    calendar_id: str,
    text: str,
    send_notifications: bool = True,
) -> dict[str, Any]:
    """
    Create an event using natural language.

    Google Calendar parses the text to extract event details.
    Examples:
    - "Meeting tomorrow at 2pm"
    - "Lunch with John next Tuesday at noon for 1 hour"
    - "All-day event next Friday"

    Args:
        calendar_id: Calendar ID or 'primary'
        text: Natural language event description

    Returns:
        Created event details

    Raises:
        GoogleCalendarValidationError: If text cannot be parsed
        GoogleCalendarAPIError: If operation fails
    """
    if not calendar_id or not calendar_id.strip():
        return {"success": False, "error": "calendar_id is required"}
    if not text or not text.strip():
        return {"success": False, "error": "text is required"}

    client = GoogleCalendarClient()
    await client.authenticate()

    try:
        event = await client.quick_add_event(
            calendar_id=calendar_id.strip(),
            text=text.strip(),
            send_notifications=send_notifications,
        )

        logger.info(f"Quick-added event: {event.id}")
        return {
            "success": True,
            "event": {
                "id": event.id,
                "summary": event.summary,
                "htmlLink": event.html_link,
                "start": _format_event_datetime(event.start),
                "end": _format_event_datetime(event.end),
            },
            "parsedText": text,
        }
    finally:
        await client.close()


def _format_event_datetime(dt: EventDateTime) -> dict[str, Any]:
    """Format EventDateTime for tool response."""
    if dt.date_time:
        return {
            "dateTime": dt.date_time.isoformat(),
            "timeZone": dt.time_zone,
        }
    elif dt.date:
        return {
            "date": dt.date,
            "timeZone": dt.time_zone,
        }
    return {}


# Tool definitions for MCP integration
GOOGLE_CALENDAR_TOOLS = {
    "list_calendars": {
        "name": "list_calendars",
        "description": "List all accessible Google Calendars",
        "function": list_calendars_tool,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    "get_calendar": {
        "name": "get_calendar",
        "description": "Get detailed information about a specific calendar",
        "function": get_calendar_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary' for the primary calendar",
                }
            },
            "required": ["calendar_id"],
        },
    },
    "list_events": {
        "name": "list_events",
        "description": "List events from a calendar with optional date range filtering",
        "function": list_events_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                    "default": "primary",
                },
                "start_date": {
                    "type": "string",
                    "description": "Lower bound for event start time (ISO 8601 format)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Upper bound for event start time (ISO 8601 format)",
                },
                "search_query": {
                    "type": "string",
                    "description": "Free-text search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum events to return (default 10, max 250)",
                    "default": 10,
                },
            },
        },
    },
    "get_event": {
        "name": "get_event",
        "description": "Get detailed information about a specific event",
        "function": get_event_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID",
                },
            },
            "required": ["calendar_id", "event_id"],
        },
    },
    "create_event": {
        "name": "create_event",
        "description": "Create a new event in a calendar",
        "function": create_event_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                },
                "title": {
                    "type": "string",
                    "description": "Event title (1-255 characters)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time (ISO 8601 format with timezone)",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time (must be after start_time)",
                },
                "description": {
                    "type": "string",
                    "description": "Event description",
                },
                "location": {
                    "type": "string",
                    "description": "Event location",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses",
                },
                "send_notifications": {
                    "type": "boolean",
                    "description": "Send invitations to attendees",
                    "default": True,
                },
            },
            "required": ["calendar_id", "title", "start_time", "end_time"],
        },
    },
    "update_event": {
        "name": "update_event",
        "description": "Update an existing event in a calendar",
        "function": update_event_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New event title",
                },
                "description": {
                    "type": "string",
                    "description": "New description",
                },
                "start_time": {
                    "type": "string",
                    "description": "New start time",
                },
                "end_time": {
                    "type": "string",
                    "description": "New end time",
                },
                "location": {
                    "type": "string",
                    "description": "New location",
                },
                "send_notifications": {
                    "type": "boolean",
                    "description": "Notify attendees of changes",
                    "default": True,
                },
            },
            "required": ["calendar_id", "event_id"],
        },
    },
    "delete_event": {
        "name": "delete_event",
        "description": "Delete an event from a calendar",
        "function": delete_event_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID to delete",
                },
                "send_notifications": {
                    "type": "boolean",
                    "description": "Send cancellation notices to attendees",
                    "default": True,
                },
            },
            "required": ["calendar_id", "event_id"],
        },
    },
    "quick_add_event": {
        "name": "quick_add_event",
        "description": "Create an event using natural language (e.g., 'Meeting tomorrow at 3pm')",
        "function": quick_add_event_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary'",
                },
                "text": {
                    "type": "string",
                    "description": "Natural language event description",
                },
                "send_notifications": {
                    "type": "boolean",
                    "description": "Send notifications to attendees",
                    "default": True,
                },
            },
            "required": ["calendar_id", "text"],
        },
    },
}
