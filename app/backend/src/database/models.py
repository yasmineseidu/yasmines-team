"""
SQLAlchemy models for database tables.

Defines ORM models for approval workflow and other database entities.
"""

from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Enum values for database
APPROVAL_STATUS_VALUES = ("pending", "approved", "disapproved", "editing", "expired", "cancelled")
APPROVAL_CONTENT_TYPE_VALUES = ("budget", "document", "content", "custom")
APPROVAL_ACTION_VALUES = ("approve", "disapprove", "edit", "cancel", "expire", "resubmit", "notify")


class ApprovalRequestModel(Base):
    """
    SQLAlchemy model for approval_requests table.

    Stores approval request data including Telegram message references.
    """

    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(
        Enum(*APPROVAL_CONTENT_TYPE_VALUES, name="approval_content_type"),
        nullable=False,
        default="custom",
    )
    status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status"),
        nullable=False,
        default="pending",
        index=True,
    )
    requester_id = Column(BigInteger, nullable=False)
    approver_id = Column(BigInteger, nullable=False, index=True)
    telegram_chat_id = Column(BigInteger, nullable=False)
    telegram_message_id = Column(BigInteger, nullable=True, index=True)
    data = Column(JSONB, nullable=False, default=dict)
    edit_token = Column(String(64), nullable=True, unique=True)
    edit_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship to history entries
    history = relationship(
        "ApprovalHistoryModel",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ApprovalHistoryModel.created_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("ix_approval_requests_approver_created", "approver_id", "created_at"),
        Index("ix_approval_requests_status_created", "status", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "status": self.status,
            "requester_id": self.requester_id,
            "approver_id": self.approver_id,
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_message_id": self.telegram_message_id,
            "data": self.data or {},
            "edit_token": self.edit_token,
            "edit_token_expires_at": self.edit_token_expires_at,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ApprovalHistoryModel(Base):
    """
    SQLAlchemy model for approval_history table.

    Tracks all actions taken on approval requests for audit trail.
    """

    __tablename__ = "approval_history"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(
        Enum(*APPROVAL_ACTION_VALUES, name="approval_action"),
        nullable=False,
    )
    actor_id = Column(BigInteger, nullable=False)
    actor_username = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    edited_data = Column(JSONB, nullable=True)
    previous_status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status", create_type=False),
        nullable=True,
    )
    new_status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status", create_type=False),
        nullable=True,
    )
    telegram_callback_query_id = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship to request
    request = relationship("ApprovalRequestModel", back_populates="history")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "comment": self.comment,
            "edited_data": self.edited_data,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "telegram_callback_query_id": self.telegram_callback_query_id,
            "created_at": self.created_at,
        }
