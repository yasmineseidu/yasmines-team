"""Test fixtures for Notion API integration."""

from datetime import UTC, datetime

# Sample database ID (without hyphens, as Notion API uses both formats)
DATABASE_ID = "6d05f2e8e5ed45d1a65cde7e5e71e50f"
DATABASE_ID_WITH_HYPHENS = "6d05f2e8-e5ed-45d1-a65c-de7e5e71e50f"

# Sample page ID
PAGE_ID = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
PAGE_ID_WITH_HYPHENS = "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6"

# Sample block ID
BLOCK_ID = "z9y8x7w6v5u4t3s2r1q0p1o2n3m4l5k6"
BLOCK_ID_WITH_HYPHENS = "z9y8x7w6-v5u4-t3s2-r1q0-p1o2n3m4l5k6"

# Sample user ID (test fixture only)
USER_ID = "b5d2e0b7-38b8-4f04-a3ff-e79a2c0c28f0"  # pragma: allowlist secret

# Current timestamp
NOW = datetime.now(UTC).isoformat()


def get_sample_database() -> dict:
    """Get sample database response from Notion API."""
    return {
        "object": "database",
        "id": DATABASE_ID_WITH_HYPHENS,
        "created_time": "2024-01-01T12:00:00.000Z",
        "last_edited_time": "2024-01-15T14:30:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "title": [
            {
                "type": "text",
                "text": {"content": "Sample Database", "link": None},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
                "plain_text": "Sample Database",
                "href": None,
            }
        ],
        "description": [],
        "is_inline": False,
        "properties": {
            "Name": {
                "id": "title",
                "name": "Name",
                "type": "title",
                "title": {},
            },
            "Status": {
                "id": "select",
                "name": "Status",
                "type": "select",
                "select": {
                    "options": [
                        {"id": "opt1", "name": "Active", "color": "green"},
                        {"id": "opt2", "name": "Inactive", "color": "red"},
                    ]
                },
            },
        },
        "parent": {"type": "workspace", "workspace": True},
        "url": f"https://www.notion.so/{DATABASE_ID}",
        "public_url": None,
        "icon": None,
        "cover": None,
    }


def get_sample_page() -> dict:
    """Get sample page response from Notion API."""
    return {
        "object": "page",
        "id": PAGE_ID_WITH_HYPHENS,
        "created_time": "2024-01-10T10:00:00.000Z",
        "last_edited_time": "2024-01-15T15:30:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "archived": False,
        "icon": None,
        "cover": None,
        "properties": {
            "Name": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Sample Page", "link": None},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default",
                        },
                        "plain_text": "Sample Page",
                        "href": None,
                    }
                ],
            },
            "Status": {
                "id": "select",
                "type": "select",
                "select": {"id": "opt1", "name": "Active", "color": "green"},
            },
        },
        "parent": {"type": "database_id", "database_id": DATABASE_ID_WITH_HYPHENS},
        "url": f"https://www.notion.so/{PAGE_ID}",
        "public_url": None,
    }


def get_sample_block() -> dict:
    """Get sample block response from Notion API."""
    return {
        "object": "block",
        "id": BLOCK_ID_WITH_HYPHENS,
        "created_time": "2024-01-10T10:00:00.000Z",
        "last_edited_time": "2024-01-15T15:30:00.000Z",
        "created_by": {"object": "user", "id": USER_ID},
        "last_edited_by": {"object": "user", "id": USER_ID},
        "parent": {"type": "page_id", "page_id": PAGE_ID_WITH_HYPHENS},
        "type": "paragraph",
        "archived": False,
        "has_children": False,
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "This is a sample paragraph block.", "link": None},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                    "plain_text": "This is a sample paragraph block.",
                    "href": None,
                }
            ],
            "color": "default",
        },
    }


def get_sample_user() -> dict:
    """Get sample user response from Notion API."""
    return {
        "object": "user",
        "id": USER_ID,
        "type": "person",
        "person": {"email": "user@example.com"},
        "name": "Sample User",
        "avatar_url": None,
    }


def get_sample_query_result() -> dict:
    """Get sample database query response."""
    return {
        "object": "list",
        "results": [get_sample_page(), get_sample_page()],
        "next_cursor": None,
        "has_more": False,
    }


def get_sample_search_result() -> dict:
    """Get sample search response."""
    return {
        "object": "list",
        "results": [get_sample_database(), get_sample_page()],
        "next_cursor": None,
        "has_more": False,
    }


def get_auth_error_response() -> dict:
    """Get sample 401 authentication error response."""
    return {
        "object": "error",
        "status": 401,
        "code": "unauthorized",
        "message": "API token invalid",
    }


def get_rate_limit_error_response() -> dict:
    """Get sample 429 rate limit error response."""
    return {
        "object": "error",
        "status": 429,
        "code": "rate_limited",
        "message": "Rate limited because you sent too many requests in short succession",
    }


def get_not_found_error_response() -> dict:
    """Get sample 404 not found error response."""
    return {
        "object": "error",
        "status": 404,
        "code": "object_not_found",
        "message": "Could not find database with ID: invalid-id",
    }


def get_validation_error_response() -> dict:
    """Get sample 400 validation error response."""
    return {
        "object": "error",
        "status": 400,
        "code": "validation_error",
        "message": "Invalid request body",
    }
