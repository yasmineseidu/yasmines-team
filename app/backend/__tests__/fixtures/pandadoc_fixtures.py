"""Test fixtures and mock data for PandaDoc API tests."""

from datetime import datetime
from typing import Any

from src.integrations.pandadoc.models import (
    Document,
    DocumentsListResponse,
    Recipient,
    Signature,
    Template,
    TemplatesListResponse,
)

# ============== TEMPLATE FIXTURES ==============

SAMPLE_TEMPLATE: Template = Template(
    id="tpl_123456abcdef",
    name="Service Agreement",
    created_at=datetime(2025, 1, 1, 10, 0, 0),
    updated_at=datetime(2025, 1, 1, 10, 0, 0),
    url="https://pandadoc.com/templates/tpl_123456abcdef",
    access_type="owner",
    folder="templates",
    owner={"name": "Admin", "email": "admin@example.com"},
    tags=["agreement", "service"],
)

SAMPLE_TEMPLATE_DICT: dict[str, Any] = {
    "id": "tpl_123456abcdef",
    "name": "Service Agreement",
    "created_at": "2025-01-01T10:00:00",
    "updated_at": "2025-01-01T10:00:00",
    "url": "https://pandadoc.com/templates/tpl_123456abcdef",
    "access_type": "owner",
    "folder": "templates",
    "owner": {"name": "Admin", "email": "admin@example.com"},
    "tags": ["agreement", "service"],
}

TEMPLATES_LIST_RESPONSE: TemplatesListResponse = TemplatesListResponse(
    templates=[SAMPLE_TEMPLATE],
    count=1,
    offset=0,
    limit=50,
)

TEMPLATES_LIST_RESPONSE_DICT: dict[str, Any] = {
    "templates": [SAMPLE_TEMPLATE_DICT],
    "count": 1,
    "offset": 0,
    "limit": 50,
}


# ============== DOCUMENT FIXTURES ==============

SAMPLE_RECIPIENT: Recipient = Recipient(
    email="john@example.com",
    name="John Doe",
    role="signer",
    signing_order=1,
)

SAMPLE_SIGNATURE: Signature = Signature(
    email="john@example.com",
    name="John Doe",
    status="pending",
)

COMPLETED_SIGNATURE: Signature = Signature(
    email="john@example.com",
    name="John Doe",
    status="completed",
    signed_at=datetime(2025, 1, 2, 15, 30, 0),
)

SAMPLE_DOCUMENT: Document = Document(
    id="doc_123456abcdef",
    name="John Doe - Service Agreement",
    status="sent",
    template_id="tpl_123456abcdef",
    created_at=datetime(2025, 1, 1, 12, 0, 0),
    updated_at=datetime(2025, 1, 1, 12, 30, 0),
    sent_at=datetime(2025, 1, 1, 12, 30, 0),
    url="https://pandadoc.com/documents/doc_123456abcdef",
    recipients=[SAMPLE_SIGNATURE],
    page_count=5,
)

COMPLETED_DOCUMENT: Document = Document(
    id="doc_123456abcdef",
    name="John Doe - Service Agreement",
    status="completed",
    template_id="tpl_123456abcdef",
    created_at=datetime(2025, 1, 1, 12, 0, 0),
    updated_at=datetime(2025, 1, 2, 15, 30, 0),
    sent_at=datetime(2025, 1, 1, 12, 30, 0),
    completed_at=datetime(2025, 1, 2, 15, 30, 0),
    url="https://pandadoc.com/documents/doc_123456abcdef",
    recipients=[COMPLETED_SIGNATURE],
    page_count=5,
)

SAMPLE_DOCUMENT_DICT: dict[str, Any] = {
    "id": "doc_123456abcdef",
    "name": "John Doe - Service Agreement",
    "status": "sent",
    "template_id": "tpl_123456abcdef",
    "created_at": "2025-01-01T12:00:00",
    "updated_at": "2025-01-01T12:30:00",
    "sent_at": "2025-01-01T12:30:00",
    "url": "https://pandadoc.com/documents/doc_123456abcdef",
    "recipients": [
        {
            "email": "john@example.com",
            "name": "John Doe",
            "status": "pending",
        }
    ],
    "page_count": 5,
}

COMPLETED_DOCUMENT_DICT: dict[str, Any] = {
    "id": "doc_123456abcdef",
    "name": "John Doe - Service Agreement",
    "status": "completed",
    "template_id": "tpl_123456abcdef",
    "created_at": "2025-01-01T12:00:00",
    "updated_at": "2025-01-02T15:30:00",
    "sent_at": "2025-01-01T12:30:00",
    "completed_at": "2025-01-02T15:30:00",
    "url": "https://pandadoc.com/documents/doc_123456abcdef",
    "recipients": [
        {
            "email": "john@example.com",
            "name": "John Doe",
            "status": "completed",
            "signed_at": "2025-01-02T15:30:00",
        }
    ],
    "page_count": 5,
}

DOCUMENTS_LIST_RESPONSE: DocumentsListResponse = DocumentsListResponse(
    documents=[SAMPLE_DOCUMENT],
    count=1,
    offset=0,
    limit=50,
)

DOCUMENTS_LIST_RESPONSE_DICT: dict[str, Any] = {
    "documents": [SAMPLE_DOCUMENT_DICT],
    "count": 1,
    "offset": 0,
    "limit": 50,
}


# ============== WEBHOOK FIXTURES ==============

SAMPLE_WEBHOOK_CREATED: dict[str, Any] = {
    "id": "wh_123456abcdef",
    "url": "https://example.com/webhook",
    "events": ["document.sent", "document.completed"],
    "created_at": "2025-01-01T10:00:00",
}

SAMPLE_WEBHOOK_EVENT_SENT: dict[str, Any] = {
    "event": "document.sent",
    "data": {
        "document_id": "doc_123456abcdef",
        "template_id": "tpl_123456abcdef",
        "status": "sent",
        "recipients": [
            {
                "email": "john@example.com",
                "name": "John Doe",
                "status": "pending",
            }
        ],
    },
    "timestamp": "2025-01-01T12:30:00Z",
}

SAMPLE_WEBHOOK_EVENT_COMPLETED: dict[str, Any] = {
    "event": "document.completed",
    "data": {
        "document_id": "doc_123456abcdef",
        "template_id": "tpl_123456abcdef",
        "status": "completed",
        "recipients": [
            {
                "email": "john@example.com",
                "name": "John Doe",
                "status": "completed",
                "signed_at": "2025-01-02T15:30:00Z",
            }
        ],
    },
    "timestamp": "2025-01-02T15:30:00Z",
}


# ============== ERROR RESPONSE FIXTURES ==============

ERROR_404_RESPONSE: dict[str, Any] = {
    "error": "Not Found",
    "message": "Document not found",
}

ERROR_429_RESPONSE: dict[str, Any] = {
    "error": "Too Many Requests",
    "message": "Rate limit exceeded",
}

ERROR_401_RESPONSE: dict[str, Any] = {
    "error": "Unauthorized",
    "message": "Invalid API key",
}
