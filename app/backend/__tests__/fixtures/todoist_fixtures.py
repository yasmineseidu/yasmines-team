"""Sample data fixtures for Todoist API testing."""

# Sample project responses
SAMPLE_PROJECT = {
    "id": "2203306141",
    "name": "Test Project",
    "color": "charcoal",
    "parent_id": None,
    "order": 1,
    "comment_count": 0,
    "is_shared": False,
    "is_favorite": False,
    "is_inbox_project": False,
    "is_team_inbox": False,
    "view_style": "list",
    "url": "https://todoist.com/showProject?id=2203306141",
}

SAMPLE_PROJECTS_RESPONSE = [
    SAMPLE_PROJECT,
    {
        "id": "2203306142",
        "name": "Work Project",
        "color": "blue",
        "parent_id": None,
        "order": 2,
        "comment_count": 5,
        "is_shared": True,
        "is_favorite": False,
        "is_inbox_project": False,
        "is_team_inbox": False,
        "view_style": "list",
        "url": "https://todoist.com/showProject?id=2203306142",
    },
]

# Sample task responses
SAMPLE_TASK = {
    "id": "4088838091",
    "content": "Buy groceries",
    "project_id": "2203306141",
    "section_id": None,
    "parent_id": None,
    "order": 1,
    "priority": 1,
    "is_completed": False,
    "due": {
        "date": "2025-01-01",
        "datetime": None,
        "string": "2025-01-01",
        "timezone": None,
    },
    "created_at": "2025-12-22T10:00:00.000000Z",
    "creator_id": "123456",
    "url": "https://todoist.com/showTask?id=4088838091",
    "comment_count": 0,
    "labels": ["shopping", "home"],
    "duration": None,
    "description": "Buy milk, eggs, and bread",
}

SAMPLE_TASKS_RESPONSE = [
    SAMPLE_TASK,
    {
        "id": "4088838092",
        "content": "Write API tests",
        "project_id": "2203306141",
        "section_id": "123456",
        "parent_id": None,
        "order": 2,
        "priority": 3,
        "is_completed": False,
        "due": {
            "date": "2025-01-05",
            "datetime": None,
            "string": "2025-01-05",
            "timezone": None,
        },
        "created_at": "2025-12-22T11:00:00.000000Z",
        "creator_id": "123456",
        "url": "https://todoist.com/showTask?id=4088838092",
        "comment_count": 2,
        "labels": ["work"],
        "duration": {"amount": 60, "unit": "minute"},
        "description": "Test all Todoist API endpoints",
    },
]

SAMPLE_TASK_COMPLETED = {
    "id": "4088838091",
    "content": "Buy groceries",
    "project_id": "2203306141",
    "section_id": None,
    "parent_id": None,
    "order": 1,
    "priority": 1,
    "is_completed": True,
    "due": {
        "date": "2025-01-01",
        "datetime": None,
        "string": "2025-01-01",
        "timezone": None,
    },
    "created_at": "2025-12-22T10:00:00.000000Z",
    "creator_id": "123456",
    "url": "https://todoist.com/showTask?id=4088838091",
    "comment_count": 0,
    "labels": ["shopping", "home"],
    "duration": None,
    "description": "Buy milk, eggs, and bread",
}

# Sample section responses
SAMPLE_SECTION = {
    "id": "123456",
    "name": "Backlog",
    "project_id": "2203306141",
    "order": 1,
}

SAMPLE_SECTIONS_RESPONSE = [
    SAMPLE_SECTION,
    {
        "id": "123457",
        "name": "In Progress",
        "project_id": "2203306141",
        "order": 2,
    },
    {
        "id": "123458",
        "name": "Done",
        "project_id": "2203306141",
        "order": 3,
    },
]

# Sample comment responses
SAMPLE_COMMENT = {
    "id": "123456789",
    "content": "This is a comment",
    "task_id": "4088838091",
    "project_id": None,
    "posted_at": "2025-12-22T12:00:00.000000Z",
    "posted_uid": "123456",
    "updated_at": "2025-12-22T12:00:00.000000Z",
}

SAMPLE_COMMENTS_RESPONSE = [
    SAMPLE_COMMENT,
    {
        "id": "123456790",
        "content": "Another comment",
        "task_id": "4088838091",
        "project_id": None,
        "posted_at": "2025-12-22T13:00:00.000000Z",
        "posted_uid": "654321",
        "updated_at": "2025-12-22T13:00:00.000000Z",
    },
]

# Sample label responses
SAMPLE_LABEL = {
    "id": "label_id_1",
    "name": "work",
    "color": "red",
    "order": 1,
    "is_favorite": False,
}

SAMPLE_LABELS_RESPONSE = [
    SAMPLE_LABEL,
    {
        "id": "label_id_2",
        "name": "shopping",
        "color": "blue",
        "order": 2,
        "is_favorite": False,
    },
    {
        "id": "label_id_3",
        "name": "urgent",
        "color": "yellow",
        "order": 3,
        "is_favorite": True,
    },
]

# Error responses
ERROR_401_RESPONSE = {
    "error": "Unauthorized",
    "message": "Invalid or expired API token",
}

ERROR_429_RESPONSE = {
    "error": "Too Many Requests",
    "message": "Rate limit exceeded. Max 1000 requests per 15 minutes",
}

ERROR_400_RESPONSE = {
    "error": "Invalid Request",
    "message": "Invalid project_id provided",
}

ERROR_500_RESPONSE = {
    "error": "Internal Server Error",
    "message": "An error occurred processing your request",
}
