"""Cal.com API integration client for Claude Agent SDK.

This module provides a comprehensive async client for Cal.com's REST API v2,
including full CRUD operations for scheduling, bookings, event types, and team
management. The client supports authenticated access via API keys, exponential
backoff retry logic, and rate limiting.

Example:
    >>> import os
    >>> from app.backend.src.integrations.cal_com import CalComClient
    >>>
    >>> api_key = os.getenv("CAL_COM_API_KEY")
    >>> async with CalComClient(api_key=api_key) as client:
    ...     user = await client.get_user()
    ...     event_types = await client.list_event_types()
"""

from src.integrations.cal_com.client import CalComClient
from src.integrations.cal_com.exceptions import (
    CalComAPIError,
    CalComAuthError,
    CalComConfigError,
    CalComError,
    CalComNotFoundError,
    CalComRateLimitError,
    CalComValidationError,
)
from src.integrations.cal_com.models import (
    Availability,
    BookingConfirmation,
    CalComEvent,
    EventType,
    Team,
    User,
)

__all__ = [
    "CalComClient",
    "CalComError",
    "CalComAuthError",
    "CalComAPIError",
    "CalComConfigError",
    "CalComNotFoundError",
    "CalComValidationError",
    "CalComRateLimitError",
    "Availability",
    "BookingConfirmation",
    "CalComEvent",
    "EventType",
    "Team",
    "User",
]
