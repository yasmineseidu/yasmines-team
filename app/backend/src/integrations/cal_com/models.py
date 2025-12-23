"""Cal.com API data models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalComEvent(BaseModel):
    """Cal.com event/booking model."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str | int | None = Field(None, description="Unique event identifier")
    title: str | None = Field(None, description="Event title")
    description: str | None = Field(None, description="Event description")
    start_time: datetime | str | None = Field(None, description="Event start time")
    end_time: datetime | str | None = Field(None, description="Event end time")
    location: str | None = Field(None, description="Event location")
    organizer_id: str | int | None = Field(None, description="ID of the event organizer")
    attendees: list[str] = Field(default_factory=list, description="List of attendee emails")
    event_type_id: str | int | None = Field(None, description="Associated event type ID")
    calendar_id: str | int | None = Field(None, description="Calendar ID for the event")
    status: str = Field(
        default="confirmed",
        description="Event status: confirmed, tentative, or cancelled",
    )
    created_at: datetime | str | None = Field(None, description="When the event was created")
    updated_at: datetime | str | None = Field(None, description="When the event was last updated")


class EventType(BaseModel):
    """Cal.com event type model for scheduling configuration."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str | int | None = Field(None, description="Unique event type identifier")
    title: str | None = Field(None, description="Event type title")
    slug: str | None = Field(None, description="URL-friendly identifier")
    description: str | None = Field(None, description="Event type description")
    length: int | None = Field(None, description="Duration in minutes")
    owner_id: str | int | None = Field(None, description="ID of the event type owner")
    is_active: bool = Field(default=True, description="Whether event type is active")
    scheduling_type: str = Field(
        default="collective", description="Scheduling type: collective, round_robin, etc."
    )


class User(BaseModel):
    """Cal.com user model."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str | int = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    username: str = Field(..., description="Username for public profiles")
    timezone: str = Field(
        default="UTC", alias="timeZone", description="User timezone (IANA format)"
    )
    locale: str | None = Field(None, description="User locale/language")
    created_at: datetime | None = Field(None, description="Account creation timestamp")
    avatar_url: str | None = Field(None, alias="avatarUrl", description="User avatar URL")
    bio: str | None = Field(None, description="User bio/description")
    time_format: int | None = Field(
        None, alias="timeFormat", description="Time format preference (12 or 24)"
    )
    default_schedule_id: int | str | None = Field(
        None, alias="defaultScheduleId", description="Default schedule ID"
    )
    week_start: str | None = Field(None, alias="weekStart", description="First day of week")
    organization_id: str | int | None = Field(
        None, alias="organizationId", description="Organization ID"
    )


class Team(BaseModel):
    """Cal.com team model."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Team name")
    slug: str = Field(..., description="URL-friendly team identifier")
    logo: str | None = Field(None, description="Team logo URL")
    bio: str | None = Field(None, description="Team description")
    members: list[str] = Field(default_factory=list, description="List of team member IDs")


class Availability(BaseModel):
    """Cal.com availability slot model."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    user_id: str = Field(..., description="User ID for availability")
    start_time: datetime = Field(..., description="Slot start time")
    end_time: datetime = Field(..., description="Slot end time")
    is_available: bool = Field(default=True, description="Whether slot is available for booking")


class BookingConfirmation(BaseModel):
    """Cal.com booking confirmation model."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    event_id: str = Field(..., description="Associated event ID")
    booking_id: str = Field(..., description="Unique booking identifier")
    confirmed_at: datetime = Field(..., description="Confirmation timestamp")
    confirmation_url: str | None = Field(None, description="URL to confirm/manage booking")
