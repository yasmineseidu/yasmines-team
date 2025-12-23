"""Pydantic models for Google Meet API responses.

Based on Google Meet REST API v2:
- Spaces: Meeting rooms that can be reused
- ConferenceRecords: Historical records of meetings
- Participants: Users who joined meetings
- Recordings: Meeting recordings stored in Drive
- Transcripts: Meeting transcripts stored in Docs
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SpaceAccessType(str, Enum):
    """Access type for a meeting space."""

    ACCESS_TYPE_UNSPECIFIED = "ACCESS_TYPE_UNSPECIFIED"
    OPEN = "OPEN"  # Anyone with the link can join
    TRUSTED = "TRUSTED"  # Only invited users can join directly
    RESTRICTED = "RESTRICTED"  # Only invited users can join, others must knock


class EntryPointAccess(str, Enum):
    """Entry point access for a meeting space."""

    ENTRY_POINT_ACCESS_UNSPECIFIED = "ENTRY_POINT_ACCESS_UNSPECIFIED"
    ALL = "ALL"  # All entry points enabled
    CREATOR_APP_ONLY = "CREATOR_APP_ONLY"  # Only creator's app can join


class RecordingState(str, Enum):
    """State of a recording."""

    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    STARTED = "STARTED"
    ENDED = "ENDED"
    FILE_GENERATED = "FILE_GENERATED"


class TranscriptState(str, Enum):
    """State of a transcript."""

    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    STARTED = "STARTED"
    ENDED = "ENDED"
    FILE_GENERATED = "FILE_GENERATED"


class SpaceConfig(BaseModel):
    """Configuration for a meeting space."""

    model_config = ConfigDict(populate_by_name=True)

    access_type: SpaceAccessType | None = Field(default=None, alias="accessType")
    entry_point_access: EntryPointAccess | None = Field(default=None, alias="entryPointAccess")


class ActiveConference(BaseModel):
    """Reference to the active conference in a space."""

    model_config = ConfigDict(populate_by_name=True)

    conference_record: str | None = Field(
        default=None,
        alias="conferenceRecord",
        description="Resource name of the conference record",
    )


class Space(BaseModel):
    """Google Meet space (meeting room).

    A space is a reusable meeting room. The meeting URI and code
    remain stable, allowing users to rejoin the same room.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: spaces/{space_id}",
    )
    meeting_uri: str | None = Field(
        default=None,
        alias="meetingUri",
        description="URI to join the meeting (e.g., https://meet.google.com/abc-defg-hij)",
    )
    meeting_code: str | None = Field(
        default=None,
        alias="meetingCode",
        description="Meeting code (e.g., abc-defg-hij)",
    )
    config: SpaceConfig | None = None
    active_conference: ActiveConference | None = Field(default=None, alias="activeConference")


class SpaceCreate(BaseModel):
    """Model for creating a new meeting space."""

    model_config = ConfigDict(populate_by_name=True)

    config: SpaceConfig | None = None


class SpaceUpdate(BaseModel):
    """Model for updating a meeting space."""

    model_config = ConfigDict(populate_by_name=True)

    config: SpaceConfig | None = None


class SignedInUser(BaseModel):
    """A signed-in Google user."""

    model_config = ConfigDict(populate_by_name=True)

    user: str | None = Field(
        default=None,
        description="Resource name: users/{user_id}",
    )
    display_name: str | None = Field(default=None, alias="displayName")


class AnonymousUser(BaseModel):
    """An anonymous user (not signed in)."""

    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = Field(default=None, alias="displayName")


class PhoneUser(BaseModel):
    """A user who joined via phone."""

    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = Field(default=None, alias="displayName")


class Participant(BaseModel):
    """A participant in a Google Meet conference.

    Represents someone who joined a meeting, including their
    join/leave times and identity information.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: conferenceRecords/{id}/participants/{participant_id}",
    )
    earliest_start_time: datetime | None = Field(default=None, alias="earliestStartTime")
    latest_end_time: datetime | None = Field(default=None, alias="latestEndTime")
    signedin_user: SignedInUser | None = Field(default=None, alias="signedinUser")
    anonymous_user: AnonymousUser | None = Field(default=None, alias="anonymousUser")
    phone_user: PhoneUser | None = Field(default=None, alias="phoneUser")


class ParticipantSession(BaseModel):
    """A single session for a participant (they may join/leave multiple times)."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: conferenceRecords/{id}/participants/{id}/participantSessions/{session_id}",
    )
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")


class DriveDestination(BaseModel):
    """Recording destination in Google Drive."""

    model_config = ConfigDict(populate_by_name=True)

    file: str | None = Field(
        default=None,
        description="Drive file resource name",
    )
    export_uri: str | None = Field(
        default=None,
        alias="exportUri",
        description="URI to download the recording",
    )


class Recording(BaseModel):
    """A Google Meet recording.

    Recordings are stored in Google Drive and linked to the
    conference record they belong to.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: conferenceRecords/{id}/recordings/{recording_id}",
    )
    state: RecordingState | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    drive_destination: DriveDestination | None = Field(default=None, alias="driveDestination")


class DocsDestination(BaseModel):
    """Transcript destination in Google Docs."""

    model_config = ConfigDict(populate_by_name=True)

    document: str | None = Field(
        default=None,
        description="Docs document resource name",
    )
    export_uri: str | None = Field(
        default=None,
        alias="exportUri",
        description="URI to view the transcript",
    )


class Transcript(BaseModel):
    """A Google Meet transcript.

    Transcripts are stored in Google Docs and linked to the
    conference record they belong to.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: conferenceRecords/{id}/transcripts/{transcript_id}",
    )
    state: TranscriptState | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    docs_destination: DocsDestination | None = Field(default=None, alias="docsDestination")


class TranscriptEntry(BaseModel):
    """A single entry in a transcript (one speaker turn)."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name",
    )
    participant: str | None = Field(
        default=None,
        description="Resource name of the participant who spoke",
    )
    text: str | None = Field(
        default=None,
        description="The spoken text",
    )
    language_code: str | None = Field(
        default=None,
        alias="languageCode",
        description="BCP-47 language code",
    )
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")


class ConferenceRecord(BaseModel):
    """A Google Meet conference record.

    A conference record represents a single meeting session.
    It's created when someone joins a space and ends when
    everyone leaves.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        description="Resource name: conferenceRecords/{conference_id}",
    )
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    expire_time: datetime | None = Field(
        default=None,
        alias="expireTime",
        description="When this record will be deleted",
    )
    space: str | None = Field(
        default=None,
        description="Resource name of the space where this conference occurred",
    )


# Response models for list operations


class SpacesListResponse(BaseModel):
    """Response model for listing spaces."""

    model_config = ConfigDict(populate_by_name=True)

    spaces: list[Space] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class ConferenceRecordsListResponse(BaseModel):
    """Response model for listing conference records."""

    model_config = ConfigDict(populate_by_name=True)

    conference_records: list[ConferenceRecord] = Field(
        default_factory=list, alias="conferenceRecords"
    )
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class ParticipantsListResponse(BaseModel):
    """Response model for listing participants."""

    model_config = ConfigDict(populate_by_name=True)

    participants: list[Participant] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    total_size: int | None = Field(default=None, alias="totalSize")


class ParticipantSessionsListResponse(BaseModel):
    """Response model for listing participant sessions."""

    model_config = ConfigDict(populate_by_name=True)

    participant_sessions: list[ParticipantSession] = Field(
        default_factory=list, alias="participantSessions"
    )
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class RecordingsListResponse(BaseModel):
    """Response model for listing recordings."""

    model_config = ConfigDict(populate_by_name=True)

    recordings: list[Recording] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class TranscriptsListResponse(BaseModel):
    """Response model for listing transcripts."""

    model_config = ConfigDict(populate_by_name=True)

    transcripts: list[Transcript] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class TranscriptEntriesListResponse(BaseModel):
    """Response model for listing transcript entries."""

    model_config = ConfigDict(populate_by_name=True)

    transcript_entries: list[TranscriptEntry] = Field(
        default_factory=list, alias="transcriptEntries"
    )
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
