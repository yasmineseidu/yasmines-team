"""Test fixtures for Gmail API integration.

Provides sample data, expected response schemas, and canned responses
for comprehensive Gmail API testing.
"""

from typing import Any

# ==================== SAMPLE DATA ====================

SAMPLE_DATA = {
    # Authentication
    "user_email": "yasmine@smarterteam.ai",
    "test_recipient": "test@example.com",
    # Message operations
    "message_query": "subject:test",
    "message_page_size": 10,
    "message_id": "18a456bb0f29cb53",
    # Email sending
    "email_to": "test@example.com",
    "email_subject": "Test Email Subject",
    "email_body": "This is a test email body.",
    "email_html_body": "<html><body><p>This is a test email with HTML.</p></body></html>",
    "email_cc": "cc@example.com",
    "email_bcc": "bcc@example.com",
    "email_reply_to": "reply@example.com",
    # Draft operations
    "draft_id": "r123456",
    # Label operations
    "label_id": "Label_1",
    "label_name": "TestLabel",
    "label_list_visibility": "labelShow",
    "label_message_visibility": "show",
    # Thread operations
    "thread_id": "1234567890abcdef",
    "thread_query": "from:test@example.com",
    # Attachment operations
    "attachment_id": "ANGjdJ_example",
    # Format types
    "format_minimal": "minimal",
    "format_full": "full",
    "format_raw": "raw",
}

# ==================== RESPONSE SCHEMAS ====================

RESPONSE_SCHEMAS = {
    "message": {
        "id": str,
        "threadId": str,
        "labelIds": list,
    },
    "message_list": {
        "messages": list,
        "resultSizeEstimate": int,
    },
    "draft": {
        "id": str,
        "message": dict,
    },
    "draft_list": {
        "drafts": list,
        "resultSizeEstimate": int,
    },
    "label": {
        "id": str,
        "name": str,
        "labelListVisibility": str,
        "messageListVisibility": str,
    },
    "label_list": {
        "labels": list,
    },
    "thread": {
        "id": str,
        "messages": list,
        "snippet": str,
    },
    "thread_list": {
        "threads": list,
        "resultSizeEstimate": int,
    },
    "send_response": {
        "id": str,
        "threadId": str,
    },
    "user_profile": {
        "emailAddress": str,
        "messagesTotal": int,
        "messagesUnread": int,
        "historyId": str,
    },
    "attachment_metadata": {
        "id": str,
        "filename": str,
        "mimeType": str,
    },
    "attachment_list": list,
}

# ==================== SAMPLE RESPONSES ====================
# These are typical API responses used for response validation

SAMPLE_RESPONSES: dict[str, Any] = {
    "list_messages": {
        "messages": [
            {
                "id": "18a456bb0f29cb53",
                "threadId": "1234567890abcdef",
                "labelIds": ["INBOX", "IMPORTANT"],
            },
            {
                "id": "18a456bb0f29cb54",
                "threadId": "1234567890abcde0",
                "labelIds": ["INBOX"],
            },
        ],
        "resultSizeEstimate": 2,
    },
    "get_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
        "payload": {
            "partId": "",
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "yasmine@smarterteam.ai"},
                {"name": "Subject", "value": "Test Subject"},
            ],
            "body": {"size": 100, "data": "VGhpcyBpcyB0aGUgZW1haWwgYm9keQ=="},
        },
        "sizeEstimate": 2000,
    },
    "send_message": {
        "id": "18a456bb0f29cb55",
        "threadId": "1234567890abcde1",
        "labelIds": ["SENT"],
    },
    "send_message_with_attachment": {
        "id": "18a456bb0f29cb56",
        "threadId": "1234567890abcde2",
        "labelIds": ["SENT"],
    },
    "mark_as_read": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
    },
    "mark_as_unread": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX", "UNREAD"],
    },
    "star_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX", "STARRED"],
    },
    "unstar_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
    },
    "archive_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": [],
    },
    "unarchive_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
    },
    "trash_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["TRASH"],
    },
    "untrash_message": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
    },
    "list_labels": {
        "labels": [
            {
                "id": "INBOX",
                "name": "INBOX",
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "type": "system",
            },
            {
                "id": "Label_1",
                "name": "TestLabel",
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "type": "user",
            },
        ]
    },
    "get_label": {
        "id": "Label_1",
        "name": "TestLabel",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "type": "user",
        "threadsTotal": 5,
        "threadsUnread": 2,
        "messagesTotal": 10,
        "messagesUnread": 3,
    },
    "create_label": {
        "id": "Label_2",
        "name": "TestLabel",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "type": "user",
    },
    "add_label": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX", "Label_1"],
    },
    "remove_label": {
        "id": "18a456bb0f29cb53",
        "threadId": "1234567890abcdef",
        "labelIds": ["INBOX"],
    },
    "list_drafts": {
        "drafts": [
            {
                "id": "r123456",
                "message": {
                    "id": "18a456bb0f29cb57",
                    "threadId": "1234567890abcde3",
                    "labelIds": ["DRAFT"],
                },
            }
        ],
        "resultSizeEstimate": 1,
    },
    "get_draft": {
        "id": "r123456",
        "message": {
            "id": "18a456bb0f29cb57",
            "threadId": "1234567890abcde3",
            "labelIds": ["DRAFT"],
            "payload": {
                "partId": "",
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "yasmine@smarterteam.ai"},
                    {"name": "To", "value": "test@example.com"},
                    {"name": "Subject", "value": "Draft Subject"},
                ],
            },
        },
    },
    "create_draft": {
        "id": "r123457",
        "message": {
            "id": "18a456bb0f29cb58",
            "threadId": "1234567890abcde4",
            "labelIds": ["DRAFT"],
        },
    },
    "send_draft": {
        "id": "18a456bb0f29cb58",
        "threadId": "1234567890abcde4",
        "labelIds": ["SENT"],
    },
    "list_threads": {
        "threads": [
            {
                "id": "1234567890abcdef",
                "snippet": "Test message snippet...",
                "messages": [
                    {
                        "id": "18a456bb0f29cb53",
                        "threadId": "1234567890abcdef",
                        "labelIds": ["INBOX"],
                    }
                ],
            }
        ],
        "resultSizeEstimate": 1,
    },
    "get_thread": {
        "id": "1234567890abcdef",
        "snippet": "Test message snippet...",
        "messages": [
            {
                "id": "18a456bb0f29cb53",
                "threadId": "1234567890abcdef",
                "labelIds": ["INBOX"],
                "payload": {
                    "partId": "",
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "To", "value": "yasmine@smarterteam.ai"},
                        {"name": "Subject", "value": "Thread Subject"},
                    ],
                },
            }
        ],
    },
    "modify_thread": {
        "id": "1234567890abcdef",
        "snippet": "Test message snippet...",
        "messages": [
            {
                "id": "18a456bb0f29cb53",
                "threadId": "1234567890abcdef",
                "labelIds": ["INBOX", "Label_1"],
            }
        ],
    },
    "trash_thread": {
        "id": "1234567890abcdef",
        "snippet": "Test message snippet...",
        "messages": [
            {
                "id": "18a456bb0f29cb53",
                "threadId": "1234567890abcdef",
                "labelIds": ["TRASH"],
            }
        ],
    },
    "untrash_thread": {
        "id": "1234567890abcdef",
        "snippet": "Test message snippet...",
        "messages": [
            {
                "id": "18a456bb0f29cb53",
                "threadId": "1234567890abcdef",
                "labelIds": ["INBOX"],
            }
        ],
    },
    "get_user_profile": {
        "emailAddress": "yasmine@smarterteam.ai",
        "messagesTotal": 100,
        "messagesUnread": 5,
        "historyId": "1234567",
    },
    "get_message_attachments": [
        {
            "id": "ANGjdJ_example1",
            "filename": "document.pdf",
            "mimeType": "application/pdf",
        },
        {
            "id": "ANGjdJ_example2",
            "filename": "image.jpg",
            "mimeType": "image/jpeg",
        },
    ],
    "download_attachment": b"PDF content or image bytes here",
}

# ==================== ERROR RESPONSES ====================

ERROR_RESPONSES = {
    "unauthorized_401": {
        "error": {
            "code": 401,
            "message": "Unauthorized",
            "errors": [
                {
                    "domain": "global",
                    "reason": "authError",
                    "message": "Invalid Credentials",
                }
            ],
        }
    },
    "not_found_404": {
        "error": {
            "code": 404,
            "message": "Not Found",
            "errors": [
                {
                    "domain": "global",
                    "reason": "notFound",
                    "message": "Message not found",
                }
            ],
        }
    },
    "quota_exceeded_403": {
        "error": {
            "code": 403,
            "message": "Quota Exceeded",
            "errors": [
                {
                    "domain": "global",
                    "reason": "quotaExceeded",
                    "message": "Daily quota exceeded",
                }
            ],
        }
    },
    "rate_limit_429": {
        "error": {
            "code": 429,
            "message": "Too Many Requests",
            "errors": [
                {
                    "domain": "global",
                    "reason": "rateLimitExceeded",
                    "message": "Rate limit exceeded",
                }
            ],
        }
    },
}

# ==================== TEST DATA GENERATORS ====================


def get_test_recipients() -> list[str]:
    """Get list of test recipient emails."""
    return [
        "test@example.com",
        "test2@example.com",
        "test3@example.com",
    ]


def get_test_message_queries() -> list[str]:
    """Get list of test Gmail search queries."""
    return [
        "subject:test",
        "from:test@example.com",
        "has:attachment",
        "is:unread",
        "label:INBOX",
    ]


def get_test_label_names() -> list[str]:
    """Get list of test label names."""
    return [
        "Important",
        "Urgent",
        "Follow-up",
        "Review",
        "Archive",
    ]


def get_invalid_email_addresses() -> list[str]:
    """Get list of invalid email addresses for validation testing."""
    return [
        "",
        "not-an-email",
        "test@",
        "@example.com",
        "test @example.com",  # space in email
    ]


def get_invalid_ids() -> list[str]:
    """Get list of invalid IDs for error testing."""
    return [
        "",
        "invalid_id_that_does_not_exist",
        "test/slash",
        "test@special",
    ]
