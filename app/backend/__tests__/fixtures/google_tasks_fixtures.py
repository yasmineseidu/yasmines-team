"""Test fixtures for Google Tasks API integration.

Provides sample data, credentials, and expected response schemas for comprehensive testing.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

# Current timestamp for dynamic test data
NOW = datetime.now(UTC)
TOMORROW = NOW + timedelta(days=1)
NEXT_WEEK = NOW + timedelta(weeks=1)

# Sample test data
SAMPLE_DATA = {
    # Task list identifiers
    "default_task_list_id": "@default",
    "custom_task_list_id": "test-list-123",
    # Task identifiers
    "task_id": "task-abc-123",
    "parent_task_id": "parent-task-456",
    # Task details
    "task_title": "Test Task",
    "task_description": "This is a test task created by automated tests",
    "task_notes": "Additional notes for the task",
    # Task list details
    "task_list_title": "Test Task List",
    "task_list_title_update": "Updated Task List",
    # Due dates
    "due_date": TOMORROW.date().isoformat(),
    "due_datetime": TOMORROW.isoformat(),
    # Status values
    "status_needs_action": "needsAction",
    "status_completed": "completed",
    # Pagination
    "page_size": 10,
    "max_results": 100,
}

# Mock service account credentials for testing
MOCK_SERVICE_ACCOUNT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "key-id-456",
    "private_key": "mock_rsa_key_for_testing_only",  # pragma: allowlist secret
    "client_email": "test-service@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789012345678901",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test-service%40test-project-123.iam.gserviceaccount.com",
}

# Invalid credentials for testing error handling
INVALID_CREDENTIALS = {
    "missing_type": {"project_id": "test"},
    "wrong_type": {"type": "invalid_type"},
    "missing_fields": {"type": "service_account"},
    "invalid_json": "not a valid json",
}

# Expected response schemas (field structure and types)
RESPONSE_SCHEMAS = {
    "task_list": {
        "id": str,
        "title": str,
        "updated": str,
        "etag": str,
        "kind": str,
    },
    "task": {
        "id": str,
        "title": str,
        "status": str,
        "updated": str,
        "kind": str,
    },
    "task_lists_list": {
        "items": list,
        "kind": str,
        "etag": str,
    },
    "tasks_list": {
        "items": list,
        "kind": str,
        "etag": str,
    },
}

# Mock API responses
MOCK_RESPONSES = {
    "task_list_created": {
        "kind": "tasks#taskList",
        "id": "test-list-123",
        "etag": "test-etag-123",
        "title": "Test Task List",
        "updated": NOW.isoformat(),
        "selfLink": "https://www.googleapis.com/tasks/v1/users/@me/lists/test-list-123",
    },
    "task_lists_list": {
        "kind": "tasks#taskLists",
        "etag": "test-etag-456",
        "items": [
            {
                "kind": "tasks#taskList",
                "id": "@default",
                "etag": "default-etag",
                "title": "My Tasks",
                "updated": NOW.isoformat(),
                "selfLink": "https://www.googleapis.com/tasks/v1/users/@me/lists/%40default",
            },
            {
                "kind": "tasks#taskList",
                "id": "test-list-123",
                "etag": "test-etag",
                "title": "Test Task List",
                "updated": NOW.isoformat(),
                "selfLink": "https://www.googleapis.com/tasks/v1/users/@me/lists/test-list-123",
            },
        ],
    },
    "task_created": {
        "kind": "tasks#task",
        "id": "task-abc-123",
        "etag": "task-etag-123",
        "title": "Test Task",
        "description": "This is a test task",
        "updated": NOW.isoformat(),
        "webViewLink": "https://tasks.google.com",
        "status": "needsAction",
        "due": TOMORROW.date().isoformat(),
    },
    "task_completed": {
        "kind": "tasks#task",
        "id": "task-abc-123",
        "etag": "task-etag-456",
        "title": "Test Task",
        "description": "This is a test task",
        "updated": NOW.isoformat(),
        "webViewLink": "https://tasks.google.com",
        "status": "completed",
        "completed": NOW.isoformat(),
        "due": TOMORROW.date().isoformat(),
    },
    "tasks_list": {
        "kind": "tasks#tasks",
        "etag": "tasks-etag-123",
        "items": [
            {
                "kind": "tasks#task",
                "id": "task-1",
                "etag": "etag-1",
                "title": "Task 1",
                "updated": NOW.isoformat(),
                "webViewLink": "https://tasks.google.com",
                "status": "needsAction",
            },
            {
                "kind": "tasks#task",
                "id": "task-2",
                "etag": "etag-2",
                "title": "Task 2",
                "updated": NOW.isoformat(),
                "webViewLink": "https://tasks.google.com",
                "status": "completed",
                "completed": NOW.isoformat(),
            },
        ],
    },
}

# Error responses
ERROR_RESPONSES = {
    "not_found": {
        "error": {
            "code": 404,
            "message": "Task not found.",
            "errors": [{"message": "Task not found.", "domain": "global", "reason": "notFound"}],
        }
    },
    "rate_limited": {
        "error": {
            "code": 429,
            "message": "Rate Limit Exceeded",
            "errors": [
                {
                    "message": "Rate Limit Exceeded",
                    "domain": "usageLimits",
                    "reason": "rateLimitExceeded",
                }
            ],
        }
    },
    "quota_exceeded": {
        "error": {
            "code": 403,
            "message": "User Rate Limit Exceeded",
            "errors": [
                {
                    "message": "User Rate Limit Exceeded",
                    "domain": "usageLimits",
                    "reason": "userRateLimitExceeded",
                }
            ],
        }
    },
    "unauthorized": {
        "error": {
            "code": 401,
            "message": "Invalid Credentials",
            "errors": [
                {"message": "Invalid Credentials", "domain": "global", "reason": "authError"}
            ],
        }
    },
}


def get_credentials_from_env() -> dict[str, Any] | None:
    """Get real credentials from .env file if available.

    Returns:
        Parsed credentials dictionary, or None if not available
    """
    env_path = os.getenv("GOOGLE_TASKS_CREDENTIALS_JSON")
    if not env_path:
        return None

    try:
        with open(env_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_delegated_user_from_env() -> str | None:
    """Get delegated user email from .env file if available.

    Returns:
        Email string, or None if not available
    """
    return os.getenv("GOOGLE_WORKSPACE_DOMAIN_USER")
