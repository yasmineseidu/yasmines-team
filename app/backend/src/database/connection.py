"""
Database connection management.

Provides async database connection using SQLAlchemy with asyncpg driver.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base


def get_database_url() -> str:
    """
    Get database URL from environment, converting to async driver format.

    Returns:
        Database URL with asyncpg driver.
    """
    url = os.getenv("DATABASE_URL", "")

    if not url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Convert postgresql:// to postgresql+asyncpg:// for async support
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


def get_sync_database_url() -> str:
    """
    Get synchronous database URL for Alembic migrations.

    Returns:
        Database URL with psycopg2 driver.
    """
    url = os.getenv("DATABASE_URL", "")

    if not url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Ensure it uses standard postgresql:// for sync operations
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


# Create async engine (lazy initialization)
_engine = None
_session_factory = None


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=os.getenv("DEBUG", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)

    Yields:
        AsyncSession for database operations.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_database() -> None:
    """
    Initialize database - create tables if they don't exist.

    Note: In production, use Alembic migrations instead.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


class AsyncDatabaseAdapter:
    """
    Async database adapter for the ApprovalService.

    Implements the DatabaseConnection protocol using SQLAlchemy async.
    Provides all methods needed by ApprovalService for full database persistence.
    """

    def __init__(self) -> None:
        """Initialize the adapter."""
        self._session_factory = get_session_factory()

    async def execute(self, query: str, *args: Any) -> Any:
        """Execute a query."""
        async with get_session() as session:
            result = await session.execute(text(query), args)
            return result

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row."""
        async with get_session() as session:
            result = await session.execute(text(query), args)
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows."""
        async with get_session() as session:
            result = await session.execute(text(query), args)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def insert_request(self, data: dict[str, Any]) -> str:
        """
        Insert a new approval request.

        Args:
            data: Request data dictionary.

        Returns:
            Generated UUID string for the request.
        """
        from src.database.models import ApprovalRequestModel

        async with get_session() as session:
            request = ApprovalRequestModel(
                title=data.get("title"),
                content=data.get("content"),
                content_type=data.get("content_type", "custom"),
                status="pending",
                requester_id=data.get("requester_id"),
                approver_id=data.get("approver_id"),
                telegram_chat_id=data.get("telegram_chat_id"),
                telegram_message_id=data.get("telegram_message_id"),
                data=data.get("data", {}),
                expires_at=data.get("expires_at"),
            )
            session.add(request)
            await session.flush()
            return str(request.id)

    async def get_request(self, request_id: str) -> dict[str, Any] | None:
        """
        Get an approval request by ID.

        Args:
            request_id: UUID string of the request.

        Returns:
            Request data as dictionary, or None if not found.
        """
        from uuid import UUID

        from sqlalchemy import select

        from src.database.models import ApprovalRequestModel

        async with get_session() as session:
            try:
                uuid_id = UUID(request_id)
            except ValueError:
                return None

            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.id == uuid_id)
            )
            request = result.scalar_one_or_none()
            if request:
                return request.to_dict()
            return None

    async def update_request(self, request_id: str, updates: dict[str, Any]) -> bool:
        """
        Update an approval request.

        Args:
            request_id: UUID string of the request.
            updates: Dictionary of fields to update.

        Returns:
            True if update succeeded, False if request not found.
        """
        from uuid import UUID

        from sqlalchemy import select

        from src.database.models import ApprovalRequestModel

        async with get_session() as session:
            try:
                uuid_id = UUID(request_id)
            except ValueError:
                return False

            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.id == uuid_id)
            )
            request = result.scalar_one_or_none()
            if not request:
                return False

            for key, value in updates.items():
                if hasattr(request, key):
                    setattr(request, key, value)

            return True

    async def insert_history(self, data: dict[str, Any]) -> str:
        """
        Insert a history record.

        Args:
            data: History data dictionary.

        Returns:
            Generated UUID string for the history record.
        """
        from uuid import UUID

        from src.database.models import ApprovalHistoryModel

        async with get_session() as session:
            history = ApprovalHistoryModel(
                request_id=UUID(data.get("request_id")),
                action=data.get("action"),
                actor_id=data.get("actor_id"),
                actor_username=data.get("actor_username"),
                comment=data.get("comment"),
                edited_data=data.get("edited_data"),
                previous_status=data.get("previous_status"),
                new_status=data.get("new_status"),
                telegram_callback_query_id=data.get("telegram_callback_query_id"),
            )
            session.add(history)
            await session.flush()
            return str(history.id)

    async def get_pending_by_approver(self, approver_id: int) -> list[dict[str, Any]]:
        """
        Get all pending requests for an approver.

        Args:
            approver_id: User ID of the approver.

        Returns:
            List of pending request dictionaries.
        """
        from sqlalchemy import select

        from src.database.models import ApprovalRequestModel

        async with get_session() as session:
            result = await session.execute(
                select(ApprovalRequestModel)
                .where(ApprovalRequestModel.approver_id == approver_id)
                .where(ApprovalRequestModel.status == "pending")
                .order_by(ApprovalRequestModel.created_at.desc())
            )
            requests = result.scalars().all()
            return [r.to_dict() for r in requests]

    async def get_request_by_edit_token(self, token: str) -> dict[str, Any] | None:
        """
        Get a request by its edit token.

        Args:
            token: Edit token string.

        Returns:
            Request data as dictionary, or None if not found.
        """
        from sqlalchemy import select

        from src.database.models import ApprovalRequestModel

        async with get_session() as session:
            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.edit_token == token)
            )
            request = result.scalar_one_or_none()
            if request:
                return request.to_dict()
            return None
