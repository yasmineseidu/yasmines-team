"""
Database module.

Provides database connection, models, and utilities.
"""

from src.database.connection import (
    AsyncDatabaseAdapter,
    close_database,
    get_database_url,
    get_session,
    get_sync_database_url,
    init_database,
)
from src.database.models import (
    ApprovalHistoryModel,
    ApprovalRequestModel,
    Base,
)

__all__ = [
    "Base",
    "ApprovalRequestModel",
    "ApprovalHistoryModel",
    "get_database_url",
    "get_sync_database_url",
    "get_session",
    "init_database",
    "close_database",
    "AsyncDatabaseAdapter",
]
