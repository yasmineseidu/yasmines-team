"""Fixtures for Google Meet API integration tests."""

# Mock service account credentials for testing
MOCK_SERVICE_ACCOUNT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "key-123",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA2mKq...\n-----END RSA PRIVATE KEY-----\n",
    "client_email": "test@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project-123.iam.gserviceaccount.com",
}

# Sample API responses
SAMPLE_RESPONSES = {
    "space": {
        "name": "spaces/abc123",
        "meetingUri": "https://meet.google.com/abc-defg-hij",
        "meetingCode": "abc-defg-hij",
        "config": {
            "accessType": "OPEN",
            "entryPointAccess": "ALL",
        },
        "activeConference": None,
    },
    "space_with_conference": {
        "name": "spaces/def456",
        "meetingUri": "https://meet.google.com/klm-nopq-rst",
        "meetingCode": "klm-nopq-rst",
        "config": {
            "accessType": "TRUSTED",
            "entryPointAccess": "ALL",
        },
        "activeConference": {
            "conferenceRecord": "conferenceRecords/conf-123",
        },
    },
    "conference_record": {
        "name": "conferenceRecords/conf-123",
        "startTime": "2024-12-20T10:00:00Z",
        "endTime": "2024-12-20T11:00:00Z",
        "expireTime": "2025-01-20T11:00:00Z",
        "space": "spaces/abc123",
    },
    "conference_record_active": {
        "name": "conferenceRecords/conf-456",
        "startTime": "2024-12-22T14:00:00Z",
        "endTime": None,
        "expireTime": None,
        "space": "spaces/def456",
    },
    "participant_signed_in": {
        "name": "conferenceRecords/conf-123/participants/part-001",
        "earliestStartTime": "2024-12-20T10:00:00Z",
        "latestEndTime": "2024-12-20T11:00:00Z",
        "signedinUser": {
            "user": "users/123456789",
            "displayName": "John Doe",
        },
    },
    "participant_anonymous": {
        "name": "conferenceRecords/conf-123/participants/part-002",
        "earliestStartTime": "2024-12-20T10:15:00Z",
        "latestEndTime": "2024-12-20T10:45:00Z",
        "anonymousUser": {
            "displayName": "Anonymous User",
        },
    },
    "participant_phone": {
        "name": "conferenceRecords/conf-123/participants/part-003",
        "earliestStartTime": "2024-12-20T10:30:00Z",
        "latestEndTime": "2024-12-20T11:00:00Z",
        "phoneUser": {
            "displayName": "+1 555-123-4567",
        },
    },
    "participant_session": {
        "name": "conferenceRecords/conf-123/participants/part-001/participantSessions/sess-001",
        "startTime": "2024-12-20T10:00:00Z",
        "endTime": "2024-12-20T10:30:00Z",
    },
    "recording": {
        "name": "conferenceRecords/conf-123/recordings/rec-001",
        "state": "FILE_GENERATED",
        "startTime": "2024-12-20T10:00:00Z",
        "endTime": "2024-12-20T11:00:00Z",
        "driveDestination": {
            "file": "files/drive-file-123",
            "exportUri": "https://drive.google.com/open?id=drive-file-123",
        },
    },
    "recording_in_progress": {
        "name": "conferenceRecords/conf-456/recordings/rec-002",
        "state": "STARTED",
        "startTime": "2024-12-22T14:00:00Z",
        "endTime": None,
        "driveDestination": None,
    },
    "transcript": {
        "name": "conferenceRecords/conf-123/transcripts/trans-001",
        "state": "FILE_GENERATED",
        "startTime": "2024-12-20T10:00:00Z",
        "endTime": "2024-12-20T11:00:00Z",
        "docsDestination": {
            "document": "documents/docs-file-123",
            "exportUri": "https://docs.google.com/document/d/docs-file-123",
        },
    },
    "transcript_entry": {
        "name": "conferenceRecords/conf-123/transcripts/trans-001/entries/entry-001",
        "participant": "conferenceRecords/conf-123/participants/part-001",
        "text": "Hello everyone, let's get started with the meeting.",
        "languageCode": "en-US",
        "startTime": "2024-12-20T10:00:30Z",
        "endTime": "2024-12-20T10:00:35Z",
    },
    "spaces_list": {
        "spaces": [
            {
                "name": "spaces/abc123",
                "meetingUri": "https://meet.google.com/abc-defg-hij",
                "meetingCode": "abc-defg-hij",
            },
            {
                "name": "spaces/def456",
                "meetingUri": "https://meet.google.com/klm-nopq-rst",
                "meetingCode": "klm-nopq-rst",
            },
        ],
        "nextPageToken": None,
    },
    "conference_records_list": {
        "conferenceRecords": [
            {
                "name": "conferenceRecords/conf-123",
                "startTime": "2024-12-20T10:00:00Z",
                "endTime": "2024-12-20T11:00:00Z",
                "space": "spaces/abc123",
            },
            {
                "name": "conferenceRecords/conf-124",
                "startTime": "2024-12-19T14:00:00Z",
                "endTime": "2024-12-19T15:30:00Z",
                "space": "spaces/abc123",
            },
        ],
        "nextPageToken": None,
    },
    "participants_list": {
        "participants": [
            {
                "name": "conferenceRecords/conf-123/participants/part-001",
                "earliestStartTime": "2024-12-20T10:00:00Z",
                "latestEndTime": "2024-12-20T11:00:00Z",
                "signedinUser": {
                    "user": "users/123456789",
                    "displayName": "John Doe",
                },
            },
            {
                "name": "conferenceRecords/conf-123/participants/part-002",
                "earliestStartTime": "2024-12-20T10:15:00Z",
                "latestEndTime": "2024-12-20T10:45:00Z",
                "anonymousUser": {
                    "displayName": "Anonymous User",
                },
            },
        ],
        "nextPageToken": None,
        "totalSize": 2,
    },
    "recordings_list": {
        "recordings": [
            {
                "name": "conferenceRecords/conf-123/recordings/rec-001",
                "state": "FILE_GENERATED",
                "startTime": "2024-12-20T10:00:00Z",
                "endTime": "2024-12-20T11:00:00Z",
            },
        ],
        "nextPageToken": None,
    },
    "transcripts_list": {
        "transcripts": [
            {
                "name": "conferenceRecords/conf-123/transcripts/trans-001",
                "state": "FILE_GENERATED",
                "startTime": "2024-12-20T10:00:00Z",
                "endTime": "2024-12-20T11:00:00Z",
            },
        ],
        "nextPageToken": None,
    },
    "transcript_entries_list": {
        "transcriptEntries": [
            {
                "name": "conferenceRecords/conf-123/transcripts/trans-001/entries/entry-001",
                "participant": "conferenceRecords/conf-123/participants/part-001",
                "text": "Hello everyone.",
                "languageCode": "en-US",
            },
            {
                "name": "conferenceRecords/conf-123/transcripts/trans-001/entries/entry-002",
                "participant": "conferenceRecords/conf-123/participants/part-002",
                "text": "Hi! Thanks for joining.",
                "languageCode": "en-US",
            },
        ],
        "nextPageToken": None,
    },
    "empty_list": {
        "items": [],
        "nextPageToken": None,
    },
}

# Error responses
ERROR_RESPONSES = {
    "not_found": {
        "error": {
            "code": 404,
            "message": "Resource not found",
            "status": "NOT_FOUND",
        }
    },
    "permission_denied": {
        "error": {
            "code": 403,
            "message": "The caller does not have permission",
            "status": "PERMISSION_DENIED",
        }
    },
    "quota_exceeded": {
        "error": {
            "code": 403,
            "message": "Quota exceeded for project",
            "status": "RESOURCE_EXHAUSTED",
        }
    },
    "rate_limited": {
        "error": {
            "code": 429,
            "message": "Rate limit exceeded",
            "status": "RESOURCE_EXHAUSTED",
        }
    },
    "unauthorized": {
        "error": {
            "code": 401,
            "message": "Request had invalid authentication credentials",
            "status": "UNAUTHENTICATED",
        }
    },
    "invalid_argument": {
        "error": {
            "code": 400,
            "message": "Invalid argument: meetingCode",
            "status": "INVALID_ARGUMENT",
        }
    },
}

# Data for creating/updating resources
SPACE_CREATE_DATA = {
    "open_access": {
        "config": {
            "accessType": "OPEN",
        }
    },
    "trusted_access": {
        "config": {
            "accessType": "TRUSTED",
        }
    },
    "restricted_access": {
        "config": {
            "accessType": "RESTRICTED",
        }
    },
}

# Pagination test data
PAGINATED_RESPONSES = {
    "conference_records_page1": {
        "conferenceRecords": [
            {"name": f"conferenceRecords/conf-{i}", "space": "spaces/abc123"} for i in range(1, 11)
        ],
        "nextPageToken": "token-page-2",
    },
    "conference_records_page2": {
        "conferenceRecords": [
            {"name": f"conferenceRecords/conf-{i}", "space": "spaces/abc123"} for i in range(11, 16)
        ],
        "nextPageToken": None,
    },
    "participants_page1": {
        "participants": [
            {
                "name": f"conferenceRecords/conf-123/participants/part-{i:03d}",
                "signedinUser": {"displayName": f"User {i}"},
            }
            for i in range(1, 11)
        ],
        "nextPageToken": "token-page-2",
        "totalSize": 15,
    },
    "participants_page2": {
        "participants": [
            {
                "name": f"conferenceRecords/conf-123/participants/part-{i:03d}",
                "signedinUser": {"displayName": f"User {i}"},
            }
            for i in range(11, 16)
        ],
        "nextPageToken": None,
        "totalSize": 15,
    },
}
