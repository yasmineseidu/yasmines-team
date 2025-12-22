"""
Approval workflow data models.

Defines dataclasses for approval requests and history records.
These models are used throughout the approval workflow system.

Example:
    >>> from src.models.approval import ApprovalRequest, ApprovalStatus
    >>> request = ApprovalRequest(
    ...     id="uuid-here",
    ...     title="Q4 Marketing Budget",
    ...     content="$50,000 for Q4 marketing campaigns",
    ...     status=ApprovalStatus.PENDING,
    ...     requester_id=123,
    ...     approver_id=456,
    ...     telegram_chat_id=789,
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    """Approval request status states."""

    PENDING = "pending"
    APPROVED = "approved"
    DISAPPROVED = "disapproved"
    EDITING = "editing"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalContentType(str, Enum):
    """Types of approval content."""

    BUDGET = "budget"
    DOCUMENT = "document"
    CONTENT = "content"
    CUSTOM = "custom"


class ApprovalAction(str, Enum):
    """Actions that can be taken on an approval request."""

    APPROVE = "approve"
    DISAPPROVE = "disapprove"
    EDIT = "edit"
    CANCEL = "cancel"
    EXPIRE = "expire"
    RESUBMIT = "resubmit"
    NOTIFY = "notify"


@dataclass
class ApprovalRequest:
    """
    Represents an approval request.

    Attributes:
        id: Unique identifier (UUID).
        title: Short title for the approval request.
        content: Detailed content/description.
        content_type: Type of approval (budget, document, content, custom).
        status: Current status of the request.
        requester_id: User ID who requested approval.
        approver_id: User ID who should approve.
        telegram_chat_id: Telegram chat ID where approval was sent.
        telegram_message_id: Message ID in Telegram (for editing).
        data: Flexible JSONB data for type-specific fields.
        edit_token: Token for secure web-based editing.
        edit_token_expires_at: When the edit token expires.
        created_at: When the request was created.
        updated_at: When the request was last updated.
        expires_at: When the request expires (optional).
    """

    id: str
    title: str
    content: str
    requester_id: int
    approver_id: int
    telegram_chat_id: int
    content_type: ApprovalContentType = ApprovalContentType.CUSTOM
    status: ApprovalStatus = ApprovalStatus.PENDING
    telegram_message_id: int | None = None
    data: dict[str, Any] = field(default_factory=dict)
    edit_token: str | None = None
    edit_token_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None

    def is_pending(self) -> bool:
        """Check if request is still pending."""
        return self.status == ApprovalStatus.PENDING

    def is_completed(self) -> bool:
        """Check if request has been completed (approved or disapproved)."""
        return self.status in (ApprovalStatus.APPROVED, ApprovalStatus.DISAPPROVED)

    def is_actionable(self) -> bool:
        """Check if request can still be acted upon."""
        return self.status in (ApprovalStatus.PENDING, ApprovalStatus.EDITING)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type.value,
            "status": self.status.value,
            "requester_id": self.requester_id,
            "approver_id": self.approver_id,
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_message_id": self.telegram_message_id,
            "data": self.data,
            "edit_token": self.edit_token,
            "edit_token_expires_at": (
                self.edit_token_expires_at.isoformat() if self.edit_token_expires_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequest":
        """Create from dictionary (e.g., database row)."""
        return cls(
            id=str(data["id"]),
            title=data["title"],
            content=data["content"],
            content_type=ApprovalContentType(data.get("content_type", "custom")),
            status=ApprovalStatus(data.get("status", "pending")),
            requester_id=data["requester_id"],
            approver_id=data["approver_id"],
            telegram_chat_id=data["telegram_chat_id"],
            telegram_message_id=data.get("telegram_message_id"),
            data=data.get("data", {}),
            edit_token=data.get("edit_token"),
            edit_token_expires_at=data.get("edit_token_expires_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            expires_at=data.get("expires_at"),
        )


@dataclass
class ApprovalHistory:
    """
    Represents an entry in the approval history audit trail.

    Attributes:
        id: Unique identifier (UUID).
        request_id: ID of the associated approval request.
        action: Action that was taken (approve, disapprove, edit, etc.).
        actor_id: User ID who took the action.
        actor_username: Username of the actor (for display).
        comment: Optional comment/reason for the action.
        edited_data: What was changed (for edit actions).
        previous_status: Status before the action.
        new_status: Status after the action.
        telegram_callback_query_id: Callback query ID from Telegram.
        created_at: When the action was taken.
    """

    id: str
    request_id: str
    action: ApprovalAction
    actor_id: int
    actor_username: str | None = None
    comment: str | None = None
    edited_data: dict[str, Any] | None = None
    previous_status: ApprovalStatus | None = None
    new_status: ApprovalStatus | None = None
    telegram_callback_query_id: str | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "action": self.action.value,
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "comment": self.comment,
            "edited_data": self.edited_data,
            "previous_status": self.previous_status.value if self.previous_status else None,
            "new_status": self.new_status.value if self.new_status else None,
            "telegram_callback_query_id": self.telegram_callback_query_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalHistory":
        """Create from dictionary (e.g., database row)."""
        return cls(
            id=str(data["id"]),
            request_id=str(data["request_id"]),
            action=ApprovalAction(data["action"]),
            actor_id=data["actor_id"],
            actor_username=data.get("actor_username"),
            comment=data.get("comment"),
            edited_data=data.get("edited_data"),
            previous_status=(
                ApprovalStatus(data["previous_status"]) if data.get("previous_status") else None
            ),
            new_status=ApprovalStatus(data["new_status"]) if data.get("new_status") else None,
            telegram_callback_query_id=data.get("telegram_callback_query_id"),
            created_at=data.get("created_at"),
        )


@dataclass
class ApprovalRequestCreate:
    """
    Data required to create a new approval request.

    This is the input model for the send_approval_request method.
    """

    title: str
    content: str
    requester_id: int
    approver_id: int
    telegram_chat_id: int
    content_type: ApprovalContentType = ApprovalContentType.CUSTOM
    data: dict[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None

    def validate(self) -> list[str]:
        """
        Validate the request data.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.title or len(self.title) < 1:
            errors.append("Title is required")
        elif len(self.title) > 255:
            errors.append("Title must be 255 characters or less")

        if not self.content or len(self.content) < 1:
            errors.append("Content is required")

        if self.requester_id <= 0:
            errors.append("Invalid requester_id")

        if self.approver_id <= 0:
            errors.append("Invalid approver_id")

        if self.telegram_chat_id == 0:
            errors.append("Invalid telegram_chat_id")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type.value,
            "requester_id": self.requester_id,
            "approver_id": self.approver_id,
            "telegram_chat_id": self.telegram_chat_id,
            "data": self.data,
            "expires_at": self.expires_at,
        }
