"""Google Meet API integration for meeting space and conference management.

This module provides comprehensive access to Google Meet REST API v2:
- Create and manage meeting spaces (reusable meeting rooms)
- Access conference records (historical meeting data)
- View participants and their sessions
- Access recordings and transcripts

Supports domain-wide delegation for accessing user meetings.
See ~/.claude/context/SELF-HEALING.md for delegation patterns.
"""

from src.integrations.google_meet.client import GoogleMeetClient
from src.integrations.google_meet.exceptions import (
    GoogleMeetAPIError,
    GoogleMeetAuthError,
    GoogleMeetConfigError,
    GoogleMeetError,
    GoogleMeetNotFoundError,
    GoogleMeetPermissionError,
    GoogleMeetQuotaExceeded,
    GoogleMeetRateLimitError,
    GoogleMeetValidationError,
)
from src.integrations.google_meet.models import (
    ActiveConference,
    AnonymousUser,
    ConferenceRecord,
    ConferenceRecordsListResponse,
    DocsDestination,
    DriveDestination,
    EntryPointAccess,
    Participant,
    ParticipantSession,
    ParticipantSessionsListResponse,
    ParticipantsListResponse,
    PhoneUser,
    Recording,
    RecordingsListResponse,
    RecordingState,
    SignedInUser,
    Space,
    SpaceAccessType,
    SpaceConfig,
    SpaceCreate,
    SpacesListResponse,
    SpaceUpdate,
    Transcript,
    TranscriptEntriesListResponse,
    TranscriptEntry,
    TranscriptsListResponse,
    TranscriptState,
)

__all__ = [
    # Client
    "GoogleMeetClient",
    # Exceptions
    "GoogleMeetError",
    "GoogleMeetAuthError",
    "GoogleMeetAPIError",
    "GoogleMeetConfigError",
    "GoogleMeetNotFoundError",
    "GoogleMeetValidationError",
    "GoogleMeetRateLimitError",
    "GoogleMeetQuotaExceeded",
    "GoogleMeetPermissionError",
    # Enums
    "SpaceAccessType",
    "EntryPointAccess",
    "RecordingState",
    "TranscriptState",
    # Models - Space
    "Space",
    "SpaceConfig",
    "SpaceCreate",
    "SpaceUpdate",
    "ActiveConference",
    "SpacesListResponse",
    # Models - Conference Records
    "ConferenceRecord",
    "ConferenceRecordsListResponse",
    # Models - Participants
    "Participant",
    "ParticipantSession",
    "SignedInUser",
    "AnonymousUser",
    "PhoneUser",
    "ParticipantsListResponse",
    "ParticipantSessionsListResponse",
    # Models - Recordings
    "Recording",
    "DriveDestination",
    "RecordingsListResponse",
    # Models - Transcripts
    "Transcript",
    "TranscriptEntry",
    "DocsDestination",
    "TranscriptsListResponse",
    "TranscriptEntriesListResponse",
]
