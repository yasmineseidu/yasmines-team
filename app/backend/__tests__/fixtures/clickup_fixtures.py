"""Test fixtures for ClickUp API integration testing."""

from typing import Any

# Sample workspace data for testing
SAMPLE_WORKSPACES = [
    {
        "id": 12345,
        "name": "Marketing Team",
        "color": "#FF0000",
        "avatar": "https://example.com/avatar1.png",
    },
    {
        "id": 67890,
        "name": "Engineering Team",
        "color": "#0000FF",
        "avatar": "https://example.com/avatar2.png",
    },
]

# Sample space data for testing
SAMPLE_SPACES = [
    {
        "id": 111,
        "name": "Campaign Planning",
        "color": "#FF00FF",
        "private": False,
        "avatar": "https://example.com/space1.png",
    },
    {
        "id": 222,
        "name": "Internal Projects",
        "color": "#00FF00",
        "private": True,
        "avatar": None,
    },
]

# Sample list data for testing
SAMPLE_LISTS = [
    {
        "id": "list_1",
        "name": "To Do",
        "folder": {"id": 100},
        "space": {"id": 111},
        "color": "#FF00FF",
        "private": False,
    },
    {
        "id": "list_2",
        "name": "In Progress",
        "folder": None,
        "space": {"id": 111},
        "color": "#00FF00",
        "private": True,
    },
    {
        "id": "list_3",
        "name": "Done",
        "folder": {"id": 100},
        "space": {"id": 222},
        "color": "#0000FF",
        "private": False,
    },
]

# Sample task data for testing
SAMPLE_TASKS = [
    {
        "id": "task_1",
        "custom_id": None,
        "name": "Design new landing page",
        "description": "Create a new responsive landing page design",
        "status": {"status": "open"},
        "priority": {"priority": 2},
        "due_date": 1704067200000,
        "start_date": 1703980800000,
        "assignees": [{"id": 1, "username": "user1", "email": "user1@example.com"}],
        "tags": [{"name": "design"}, {"name": "urgent"}],
        "list": {"id": "list_1"},
        "folder": {"id": 100},
        "space": {"id": 111},
        "date_created": 1703980800000,
        "date_updated": 1703980800000,
    },
    {
        "id": "task_2",
        "custom_id": "TASK-123",
        "name": "Fix authentication bug",
        "description": "OAuth login not working on mobile",
        "status": {"status": "in_progress"},
        "priority": {"priority": 1},
        "due_date": 1704153600000,
        "start_date": 1703980800000,
        "assignees": [
            {"id": 2, "username": "user2", "email": "user2@example.com"},
            {"id": 3, "username": "user3", "email": "user3@example.com"},
        ],
        "tags": [{"name": "bug"}, {"name": "backend"}],
        "list": {"id": "list_2"},
        "folder": None,
        "space": {"id": 111},
        "date_created": 1703896400000,
        "date_updated": 1704000000000,
    },
    {
        "id": "task_3",
        "custom_id": None,
        "name": "Write documentation",
        "description": "Complete API documentation",
        "status": {"status": "closed"},
        "priority": None,
        "due_date": None,
        "start_date": None,
        "assignees": [],
        "tags": [{"name": "documentation"}],
        "list": {"id": "list_3"},
        "folder": None,
        "space": {"id": 222},
        "date_created": 1703812000000,
        "date_updated": 1703900000000,
    },
]

# Response schemas for validation
EXPECTED_WORKSPACE_SCHEMA = {
    "id": str,
    "name": str,
    "color": str | None,
    "avatar": str | None,
}

EXPECTED_SPACE_SCHEMA = {
    "id": str,
    "name": str,
    "color": str | None,
    "private": bool,
    "avatar": str | None,
}

EXPECTED_LIST_SCHEMA = {
    "id": str,
    "name": str,
    "folder_id": str | None,
    "space_id": str | None,
    "color": str | None,
    "private": bool,
}

EXPECTED_TASK_SCHEMA = {
    "id": str,
    "custom_id": str | None,
    "name": str,
    "description": str | None,
    "status": str | None,
    "priority": int | None,
    "due_date": int | None,
    "start_date": int | None,
    "assignees": list,
    "tags": list,
    "list_id": str | None,
    "folder_id": str | None,
    "space_id": str | None,
    "created_at": int | None,
    "updated_at": int | None,
}


def get_sample_workspace(workspace_id: str = "12345") -> dict[str, Any]:
    """Get a sample workspace by ID."""
    for ws in SAMPLE_WORKSPACES:
        if str(ws["id"]) == workspace_id:
            return ws
    return SAMPLE_WORKSPACES[0]


def get_sample_space(space_id: str = "111") -> dict[str, Any]:
    """Get a sample space by ID."""
    for space in SAMPLE_SPACES:
        if str(space["id"]) == space_id:
            return space
    return SAMPLE_SPACES[0]


def get_sample_list(list_id: str = "list_1") -> dict[str, Any]:
    """Get a sample list by ID."""
    for lst in SAMPLE_LISTS:
        if lst["id"] == list_id:
            return lst
    return SAMPLE_LISTS[0]


def get_sample_task(task_id: str = "task_1") -> dict[str, Any]:
    """Get a sample task by ID."""
    for task in SAMPLE_TASKS:
        if task["id"] == task_id:
            return task
    return SAMPLE_TASKS[0]
