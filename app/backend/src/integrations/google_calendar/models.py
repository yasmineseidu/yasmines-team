"""Pydantic models for Google Calendar API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventDateTime(BaseModel):
    """Google Calendar event date/time model.

    Supports both dateTime (specific time) and date (all-day events).
    """

    model_config = ConfigDict(populate_by_name=True)

    date_time: datetime | None = Field(default=None, alias="dateTime")
    date: str | None = None  # Format: YYYY-MM-DD for all-day events
    time_zone: str | None = Field(default=None, alias="timeZone")


class EventAttendee(BaseModel):
    """Google Calendar event attendee model."""

    model_config = ConfigDict(populate_by_name=True)

    email: str
    display_name: str | None = Field(default=None, alias="displayName")
    response_status: str | None = Field(default=None, alias="responseStatus")
    optional: bool = False
    organizer: bool = False
    self_: bool = Field(default=False, alias="self")
    comment: str | None = None


class EventReminder(BaseModel):
    """Google Calendar event reminder model."""

    model_config = ConfigDict(populate_by_name=True)

    method: str  # 'email', 'popup'
    minutes: int


class EventReminders(BaseModel):
    """Google Calendar event reminders configuration."""

    model_config = ConfigDict(populate_by_name=True)

    use_default: bool = Field(default=True, alias="useDefault")
    overrides: list[EventReminder] | None = None


class ConferenceData(BaseModel):
    """Google Calendar conference/meeting data."""

    model_config = ConfigDict(populate_by_name=True)

    conference_id: str | None = Field(default=None, alias="conferenceId")
    conference_solution: dict[str, Any] | None = Field(default=None, alias="conferenceSolution")
    entry_points: list[dict[str, Any]] | None = Field(default=None, alias="entryPoints")
    notes: str | None = None


class CalendarEvent(BaseModel):
    """Google Calendar event model.

    Represents a single event with all associated metadata,
    attendees, reminders, and conference data.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    summary: str
    description: str | None = None
    location: str | None = None
    start: EventDateTime
    end: EventDateTime
    status: str = "confirmed"  # confirmed, tentative, cancelled
    html_link: str | None = Field(default=None, alias="htmlLink")
    created: datetime | None = None
    updated: datetime | None = None
    creator: dict[str, Any] | None = None
    organizer: dict[str, Any] | None = None
    attendees: list[EventAttendee] | None = None
    reminders: EventReminders | None = None
    conference_data: ConferenceData | None = Field(default=None, alias="conferenceData")
    recurring_event_id: str | None = Field(default=None, alias="recurringEventId")
    recurrence: list[str] | None = None
    transparency: str | None = None  # opaque, transparent
    visibility: str | None = None  # default, public, private, confidential
    i_cal_uid: str | None = Field(default=None, alias="iCalUID")
    sequence: int | None = None
    color_id: str | None = Field(default=None, alias="colorId")
    event_type: str | None = Field(default=None, alias="eventType")

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Validate event summary is not empty and within length limits."""
        if not v or not v.strip():
            raise ValueError("Event summary cannot be empty")
        if len(v) > 255:
            raise ValueError("Event summary cannot exceed 255 characters")
        return v.strip()


class CalendarEventCreate(BaseModel):
    """Model for creating a new calendar event.

    Contains only the fields that can be set during event creation.
    """

    model_config = ConfigDict(populate_by_name=True)

    summary: str
    description: str | None = None
    location: str | None = None
    start: EventDateTime
    end: EventDateTime
    attendees: list[str] | None = None  # List of email addresses
    send_notifications: bool = Field(default=True, alias="sendNotifications")
    reminders: EventReminders | None = None
    conference_data: ConferenceData | None = Field(default=None, alias="conferenceData")
    recurrence: list[str] | None = None
    visibility: str | None = None
    color_id: str | None = Field(default=None, alias="colorId")

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Validate event summary is not empty and within length limits."""
        if not v or not v.strip():
            raise ValueError("Event summary cannot be empty")
        if len(v) > 255:
            raise ValueError("Event summary cannot exceed 255 characters")
        return v.strip()


class CalendarEventUpdate(BaseModel):
    """Model for updating an existing calendar event.

    All fields are optional to allow partial updates.
    """

    model_config = ConfigDict(populate_by_name=True)

    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: EventDateTime | None = None
    end: EventDateTime | None = None
    attendees: list[str] | None = None
    send_notifications: bool = Field(default=True, alias="sendNotifications")
    reminders: EventReminders | None = None
    conference_data: ConferenceData | None = Field(default=None, alias="conferenceData")
    recurrence: list[str] | None = None
    status: str | None = None
    visibility: str | None = None
    color_id: str | None = Field(default=None, alias="colorId")

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str | None) -> str | None:
        """Validate event summary if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Event summary cannot be empty")
        if len(v) > 255:
            raise ValueError("Event summary cannot exceed 255 characters")
        return v.strip()


class Calendar(BaseModel):
    """Google Calendar model.

    Represents calendar metadata including access level and settings.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    summary: str
    description: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")
    location: str | None = None
    primary: bool = False
    selected: bool = True
    access_role: str | None = Field(default=None, alias="accessRole")
    default_reminders: list[EventReminder] | None = Field(default=None, alias="defaultReminders")
    background_color: str | None = Field(default=None, alias="backgroundColor")
    foreground_color: str | None = Field(default=None, alias="foregroundColor")
    hidden: bool = False
    deleted: bool = False
    conference_properties: dict[str, Any] | None = Field(default=None, alias="conferenceProperties")


class CalendarList(BaseModel):
    """Google Calendar list entry model.

    Represents a calendar as it appears in the user's calendar list.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    summary: str
    summary_override: str | None = Field(default=None, alias="summaryOverride")
    description: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")
    color_id: str | None = Field(default=None, alias="colorId")
    background_color: str | None = Field(default=None, alias="backgroundColor")
    foreground_color: str | None = Field(default=None, alias="foregroundColor")
    access_role: str = Field(alias="accessRole")  # freeBusyReader, reader, writer, owner
    primary: bool = False
    selected: bool = True
    hidden: bool = False
    deleted: bool = False
    default_reminders: list[EventReminder] | None = Field(default=None, alias="defaultReminders")


class EventsListResponse(BaseModel):
    """Response model for listing calendar events."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[CalendarEvent] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    next_sync_token: str | None = Field(default=None, alias="nextSyncToken")
    summary: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")
    updated: datetime | None = None


class CalendarListResponse(BaseModel):
    """Response model for listing calendars."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[CalendarList] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    next_sync_token: str | None = Field(default=None, alias="nextSyncToken")
