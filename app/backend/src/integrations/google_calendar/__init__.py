"""Google Calendar API integration for event and calendar management."""

from src.integrations.google_calendar.client import GoogleCalendarClient
from src.integrations.google_calendar.exceptions import (
    GoogleCalendarAPIError,
    GoogleCalendarAuthError,
    GoogleCalendarConfigError,
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaExceeded,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)
from src.integrations.google_calendar.models import (
    Calendar,
    CalendarEvent,
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarList,
    CalendarListResponse,
    ConferenceData,
    EventAttendee,
    EventDateTime,
    EventReminder,
    EventReminders,
    EventsListResponse,
)
from src.integrations.google_calendar.tools import (
    GOOGLE_CALENDAR_TOOLS,
    create_event_tool,
    delete_event_tool,
    get_calendar_tool,
    get_event_tool,
    list_calendars_tool,
    list_events_tool,
    quick_add_event_tool,
    update_event_tool,
)

__all__ = [
    # Client
    "GoogleCalendarClient",
    # Exceptions
    "GoogleCalendarError",
    "GoogleCalendarAuthError",
    "GoogleCalendarAPIError",
    "GoogleCalendarConfigError",
    "GoogleCalendarNotFoundError",
    "GoogleCalendarValidationError",
    "GoogleCalendarRateLimitError",
    "GoogleCalendarQuotaExceeded",
    # Models
    "Calendar",
    "CalendarList",
    "CalendarListResponse",
    "CalendarEvent",
    "CalendarEventCreate",
    "CalendarEventUpdate",
    "EventDateTime",
    "EventAttendee",
    "EventReminder",
    "EventReminders",
    "EventsListResponse",
    "ConferenceData",
    # Tools
    "GOOGLE_CALENDAR_TOOLS",
    "list_calendars_tool",
    "get_calendar_tool",
    "list_events_tool",
    "get_event_tool",
    "create_event_tool",
    "update_event_tool",
    "delete_event_tool",
    "quick_add_event_tool",
]
