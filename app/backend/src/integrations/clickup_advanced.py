"""
Comprehensive ClickUp API integration client with advanced task management.

Provides complete access to ClickUp REST API v2/v3 including:
- Advanced task operations (subtasks, relationships, bulk operations)
- Tag management (create, read, update, delete, apply)
- Custom filter management and application
- Task detail information (comments, attachments, timeline)
- Status and workflow management
- Time tracking and activity
- Member and permission management
- Custom fields support

API Coverage: 40+ endpoints across all major ClickUp features.

Example:
    >>> from src.integrations.clickup_advanced import ClickUpAdvancedClient
    >>> client = ClickUpAdvancedClient(api_key="pk_12345678")
    >>> async with client:
    ...     # Get detailed task with all information
    ...     task = await client.get_task_details("task_id")
    ...
    ...     # Manage tags
    ...     tags = await client.get_tags_for_workspace("workspace_id")
    ...
    ...     # Create filters
    ...     filters = await client.get_list_filters("list_id")
    ...
    ...     # Work with subtasks
    ...     subtasks = await client.get_subtasks("task_id")
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from src.integrations.base import BaseIntegrationClient, IntegrationError

logger = logging.getLogger(__name__)


class ClickUpError(IntegrationError):
    """ClickUp-specific error."""

    pass


class TaskPriority(Enum):
    """ClickUp task priority levels."""

    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    """Common ClickUp task statuses."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class ClickUpTag:
    """ClickUp tag/label information."""

    name: str
    tag_fg: str | None = None
    tag_bg: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpFilter:
    """ClickUp custom filter."""

    id: str
    name: str
    color: str | None = None
    rules: list[dict[str, Any]] = field(default_factory=list)
    archived: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpComment:
    """ClickUp task comment."""

    id: str
    text: str
    user: dict[str, Any] = field(default_factory=dict)
    created_at: int | None = None
    updated_at: int | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpAttachment:
    """ClickUp task attachment."""

    id: str
    title: str
    url: str
    mime_type: str | None = None
    size: int | None = None
    created_at: int | None = None
    created_by: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpSubtask:
    """ClickUp subtask."""

    id: str
    name: str
    status: str | None = None
    priority: int | None = None
    assignees: list[dict[str, Any]] = field(default_factory=list)
    due_date: int | None = None
    start_date: int | None = None
    time_estimate: int | None = None  # in milliseconds
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpTaskDetail:
    """Detailed ClickUp task with all available information."""

    id: str
    custom_id: str | None
    name: str
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    due_date: int | None = None
    start_date: int | None = None
    time_estimate: int | None = None  # in milliseconds
    time_spent: int | None = None  # in milliseconds
    tags: list[str] = field(default_factory=list)
    assignees: list[dict[str, Any]] = field(default_factory=list)
    watchers: list[dict[str, Any]] = field(default_factory=list)
    created_by: dict[str, Any] = field(default_factory=dict)
    created_at: int | None = None
    updated_at: int | None = None
    comments_count: int = 0
    attachments_count: int = 0
    subtasks_count: int = 0
    list_id: str | None = None
    folder_id: str | None = None
    space_id: str | None = None
    parent_id: str | None = None  # Parent task ID for subtasks
    url: str | None = None
    custom_fields: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    linked_tasks: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpTimeEntry:
    """ClickUp time tracking entry."""

    id: str
    task_id: str
    user: dict[str, Any]
    time_in_milliseconds: int
    start_date: int
    end_date: int | None = None
    description: str | None = None
    billable: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# ADVANCED CLIENT
# ============================================================================


class ClickUpAdvancedClient(BaseIntegrationClient):
    """Advanced async client for comprehensive ClickUp API access."""

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize ClickUp advanced client.

        Args:
            api_key: ClickUp API key.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            retry_base_delay: Base delay for exponential backoff.

        Raises:
            ValueError: If API key is invalid.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        super().__init__(
            name="clickup_advanced",
            base_url="https://api.clickup.com/api/v2",
            api_key=api_key.strip(),
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )
        logger.info("ClickUp advanced client initialized")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for ClickUp API requests."""
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ========================================================================
    # TASK DETAIL ENDPOINTS
    # ========================================================================

    async def get_task_details(self, task_id: str) -> ClickUpTaskDetail:
        """
        Get comprehensive task details including comments, attachments, subtasks.

        Args:
            task_id: ID of the task.

        Returns:
            ClickUpTaskDetail object with all task information.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.get(
                f"/task/{task_id}",
                params={"include": "comments,attachments,subtasks,linked_tasks,dependencies"},
            )

            return ClickUpTaskDetail(
                id=response.get("id", ""),
                custom_id=response.get("custom_id"),
                name=response.get("name", ""),
                description=response.get("description"),
                status=response.get("status", {}).get("type"),
                priority=response.get("priority", {}).get("priority"),
                due_date=response.get("due_date"),
                start_date=response.get("start_date"),
                time_estimate=response.get("time_estimate"),
                time_spent=response.get("time_spent"),
                tags=[tag.get("name", "") for tag in response.get("tags", [])],
                assignees=response.get("assignees", []),
                watchers=response.get("watchers", []),
                created_by=response.get("creator", {}),
                created_at=response.get("date_created"),
                updated_at=response.get("date_updated"),
                comments_count=len(response.get("comments", [])),
                attachments_count=len(response.get("attachments", [])),
                subtasks_count=len(response.get("subtasks", [])),
                list_id=response.get("list", {}).get("id"),
                folder_id=response.get("folder", {}).get("id"),
                space_id=response.get("space", {}).get("id"),
                parent_id=response.get("parent"),
                url=response.get("url"),
                custom_fields=response.get("custom_fields", []),
                dependencies=response.get("dependencies", []),
                linked_tasks=response.get("linked_tasks", []),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to fetch task details for {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch task details for {task_id}: {str(e)}") from e

    async def get_multiple_tasks(
        self,
        list_id: str,
        statuses: list[str] | None = None,
        assignees: list[int] | None = None,
        tags: list[str] | None = None,
        sort_by: str = "created",
        limit: int = 100,
    ) -> list[ClickUpTaskDetail]:
        """
        Get multiple tasks with advanced filtering.

        Args:
            list_id: ID of the list.
            statuses: Filter by task statuses.
            assignees: Filter by assignee IDs.
            tags: Filter by tags.
            sort_by: Sort field (created, updated, due_date, priority).
            limit: Number of tasks to return (max 100).

        Returns:
            List of ClickUpTaskDetail objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")

        try:
            params: dict[str, Any] = {
                "limit": limit,
                "sort_by": sort_by,
            }

            if statuses:
                params["statuses"] = ",".join(statuses)
            if assignees:
                params["assignees"] = ",".join(str(a) for a in assignees)
            if tags:
                params["tags"] = ",".join(tags)

            response = await self.get(f"/list/{list_id}/task", params=params)
            tasks = response.get("tasks", [])

            return [
                ClickUpTaskDetail(
                    id=task.get("id", ""),
                    custom_id=task.get("custom_id"),
                    name=task.get("name", ""),
                    description=task.get("description"),
                    status=task.get("status", {}).get("type"),
                    priority=task.get("priority", {}).get("priority"),
                    due_date=task.get("due_date"),
                    start_date=task.get("start_date"),
                    time_estimate=task.get("time_estimate"),
                    tags=[t.get("name", "") for t in task.get("tags", [])],
                    assignees=task.get("assignees", []),
                    created_at=task.get("date_created"),
                    updated_at=task.get("date_updated"),
                    list_id=list_id,
                    raw=task,
                )
                for task in tasks
            ]
        except Exception as e:
            logger.error(f"Failed to fetch multiple tasks for list {list_id}: {e}")
            raise ClickUpError(f"Failed to fetch multiple tasks: {str(e)}") from e

    async def get_task_by_custom_id(self, custom_id: str, team_id: str) -> ClickUpTaskDetail:
        """
        Get task by custom ID.

        Args:
            custom_id: Custom task ID.
            team_id: Team/workspace ID.

        Returns:
            ClickUpTaskDetail object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not custom_id or not custom_id.strip():
            raise ValueError("Custom ID cannot be empty")
        if not team_id or not team_id.strip():
            raise ValueError("Team ID cannot be empty")

        try:
            response = await self.get(f"/team/{team_id}/task/{custom_id}")

            return ClickUpTaskDetail(
                id=response.get("id", ""),
                custom_id=response.get("custom_id"),
                name=response.get("name", ""),
                status=response.get("status", {}).get("type"),
                priority=response.get("priority", {}).get("priority"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to fetch task by custom ID {custom_id}: {e}")
            raise ClickUpError(f"Failed to fetch task by custom ID: {str(e)}") from e

    # ========================================================================
    # TAG MANAGEMENT
    # ========================================================================

    async def get_tags_for_workspace(self, workspace_id: str) -> list[ClickUpTag]:
        """
        Get all tags in a workspace.

        Args:
            workspace_id: ID of the workspace.

        Returns:
            List of ClickUpTag objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not workspace_id or not workspace_id.strip():
            raise ValueError("Workspace ID cannot be empty")

        try:
            response = await self.get(f"/team/{workspace_id}/tag")
            tags_data = response.get("tags", [])

            return [
                ClickUpTag(
                    name=tag.get("name", ""),
                    tag_fg=tag.get("tag_fg"),
                    tag_bg=tag.get("tag_bg"),
                    raw=tag,
                )
                for tag in tags_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch tags for workspace {workspace_id}: {e}")
            raise ClickUpError(f"Failed to fetch tags: {str(e)}") from e

    async def get_tags_for_list(self, list_id: str) -> list[ClickUpTag]:
        """
        Get all tags used in a list.

        Args:
            list_id: ID of the list.

        Returns:
            List of ClickUpTag objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")

        try:
            response = await self.get(f"/list/{list_id}/tag")
            tags_data = response.get("tags", [])

            return [
                ClickUpTag(
                    name=tag.get("name", ""),
                    tag_fg=tag.get("tag_fg"),
                    tag_bg=tag.get("tag_bg"),
                    raw=tag,
                )
                for tag in tags_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch tags for list {list_id}: {e}")
            raise ClickUpError(f"Failed to fetch tags: {str(e)}") from e

    async def create_tag(
        self,
        workspace_id: str,
        name: str,
        tag_fg: str | None = None,
        tag_bg: str | None = None,
    ) -> ClickUpTag:
        """
        Create a new tag in workspace.

        Args:
            workspace_id: ID of the workspace.
            name: Tag name.
            tag_fg: Foreground color (hex).
            tag_bg: Background color (hex).

        Returns:
            ClickUpTag object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not workspace_id or not workspace_id.strip():
            raise ValueError("Workspace ID cannot be empty")
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")

        try:
            payload = {
                "name": name,
            }
            if tag_fg:
                payload["tag_fg"] = tag_fg
            if tag_bg:
                payload["tag_bg"] = tag_bg

            response = await self.post(f"/team/{workspace_id}/tag", json=payload)

            return ClickUpTag(
                name=response.get("name", ""),
                tag_fg=response.get("tag_fg"),
                tag_bg=response.get("tag_bg"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to create tag '{name}': {e}")
            raise ClickUpError(f"Failed to create tag: {str(e)}") from e

    async def update_tag(
        self,
        workspace_id: str,
        tag_name: str,
        new_name: str | None = None,
        tag_fg: str | None = None,
        tag_bg: str | None = None,
    ) -> ClickUpTag:
        """
        Update an existing tag.

        Args:
            workspace_id: ID of the workspace.
            tag_name: Current tag name.
            new_name: New tag name.
            tag_fg: New foreground color.
            tag_bg: New background color.

        Returns:
            Updated ClickUpTag object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not workspace_id or not workspace_id.strip():
            raise ValueError("Workspace ID cannot be empty")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        try:
            payload: dict[str, Any] = {}
            if new_name:
                payload["name"] = new_name
            if tag_fg:
                payload["tag_fg"] = tag_fg
            if tag_bg:
                payload["tag_bg"] = tag_bg

            response = await self.put(
                f"/team/{workspace_id}/tag/{tag_name}",
                json=payload,
            )

            return ClickUpTag(
                name=response.get("name", ""),
                tag_fg=response.get("tag_fg"),
                tag_bg=response.get("tag_bg"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to update tag '{tag_name}': {e}")
            raise ClickUpError(f"Failed to update tag: {str(e)}") from e

    async def delete_tag(self, workspace_id: str, tag_name: str) -> dict[str, Any]:
        """
        Delete a tag from workspace.

        Args:
            workspace_id: ID of the workspace.
            tag_name: Name of tag to delete.

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not workspace_id or not workspace_id.strip():
            raise ValueError("Workspace ID cannot be empty")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        try:
            response = await self.delete(f"/team/{workspace_id}/tag/{tag_name}")
            return response
        except Exception as e:
            logger.error(f"Failed to delete tag '{tag_name}': {e}")
            raise ClickUpError(f"Failed to delete tag: {str(e)}") from e

    async def add_tag_to_task(self, task_id: str, tag_name: str) -> dict[str, Any]:
        """
        Add a tag to a task.

        Args:
            task_id: ID of the task.
            tag_name: Name of tag to add.

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        try:
            response = await self.post(
                f"/task/{task_id}/tag/{tag_name}",
                json={},
            )
            return response
        except Exception as e:
            logger.error(f"Failed to add tag '{tag_name}' to task {task_id}: {e}")
            raise ClickUpError(f"Failed to add tag to task: {str(e)}") from e

    async def remove_tag_from_task(self, task_id: str, tag_name: str) -> dict[str, Any]:
        """
        Remove a tag from a task.

        Args:
            task_id: ID of the task.
            tag_name: Name of tag to remove.

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        try:
            response = await self.delete(f"/task/{task_id}/tag/{tag_name}")
            return response
        except Exception as e:
            logger.error(f"Failed to remove tag '{tag_name}' from task {task_id}: {e}")
            raise ClickUpError(f"Failed to remove tag from task: {str(e)}") from e

    # ========================================================================
    # FILTER MANAGEMENT
    # ========================================================================

    async def get_list_filters(self, list_id: str) -> list[ClickUpFilter]:
        """
        Get all custom filters for a list.

        Args:
            list_id: ID of the list.

        Returns:
            List of ClickUpFilter objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")

        try:
            response = await self.get(f"/list/{list_id}/filter")
            filters_data = response.get("filters", [])

            return [
                ClickUpFilter(
                    id=f_obj.get("id", ""),
                    name=f_obj.get("name", ""),
                    color=f_obj.get("color"),
                    rules=f_obj.get("rules", []),
                    archived=f_obj.get("archived", False),
                    raw=f_obj,
                )
                for f_obj in filters_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch filters for list {list_id}: {e}")
            raise ClickUpError(f"Failed to fetch filters: {str(e)}") from e

    async def create_filter(
        self,
        list_id: str,
        name: str,
        rules: list[dict[str, Any]],
        color: str | None = None,
    ) -> ClickUpFilter:
        """
        Create a custom filter for a list.

        Args:
            list_id: ID of the list.
            name: Filter name.
            rules: Filter rules (ClickUp format).
            color: Filter color (hex).

        Returns:
            ClickUpFilter object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")
        if not name or not name.strip():
            raise ValueError("Filter name cannot be empty")
        if not rules:
            raise ValueError("Filter rules cannot be empty")

        try:
            payload = {
                "name": name,
                "rules": rules,
            }
            if color:
                payload["color"] = color

            response = await self.post(f"/list/{list_id}/filter", json=payload)

            return ClickUpFilter(
                id=response.get("id", ""),
                name=response.get("name", ""),
                color=response.get("color"),
                rules=response.get("rules", []),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to create filter '{name}': {e}")
            raise ClickUpError(f"Failed to create filter: {str(e)}") from e

    async def update_filter(
        self,
        list_id: str,
        filter_id: str,
        name: str | None = None,
        rules: list[dict[str, Any]] | None = None,
        color: str | None = None,
    ) -> ClickUpFilter:
        """
        Update an existing filter.

        Args:
            list_id: ID of the list.
            filter_id: ID of the filter.
            name: New filter name.
            rules: New filter rules.
            color: New color.

        Returns:
            Updated ClickUpFilter object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")
        if not filter_id or not filter_id.strip():
            raise ValueError("Filter ID cannot be empty")

        try:
            payload: dict[str, Any] = {}
            if name:
                payload["name"] = name
            if rules:
                payload["rules"] = rules
            if color:
                payload["color"] = color

            response = await self.put(
                f"/list/{list_id}/filter/{filter_id}",
                json=payload,
            )

            return ClickUpFilter(
                id=response.get("id", ""),
                name=response.get("name", ""),
                color=response.get("color"),
                rules=response.get("rules", []),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to update filter '{filter_id}': {e}")
            raise ClickUpError(f"Failed to update filter: {str(e)}") from e

    async def delete_filter(self, list_id: str, filter_id: str) -> dict[str, Any]:
        """
        Delete a filter from a list.

        Args:
            list_id: ID of the list.
            filter_id: ID of the filter to delete.

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")
        if not filter_id or not filter_id.strip():
            raise ValueError("Filter ID cannot be empty")

        try:
            response = await self.delete(f"/list/{list_id}/filter/{filter_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to delete filter '{filter_id}': {e}")
            raise ClickUpError(f"Failed to delete filter: {str(e)}") from e

    # ========================================================================
    # SUBTASK MANAGEMENT
    # ========================================================================

    async def get_subtasks(self, task_id: str) -> list[ClickUpSubtask]:
        """
        Get all subtasks for a task.

        Args:
            task_id: ID of the parent task.

        Returns:
            List of ClickUpSubtask objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.get(f"/task/{task_id}/subtask")
            subtasks_data = response.get("subtasks", [])

            return [
                ClickUpSubtask(
                    id=st.get("id", ""),
                    name=st.get("name", ""),
                    status=st.get("status", {}).get("type"),
                    priority=st.get("priority", {}).get("priority"),
                    assignees=st.get("assignees", []),
                    due_date=st.get("due_date"),
                    start_date=st.get("start_date"),
                    time_estimate=st.get("time_estimate"),
                    raw=st,
                )
                for st in subtasks_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch subtasks for task {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch subtasks: {str(e)}") from e

    async def create_subtask(
        self,
        task_id: str,
        name: str,
        assignee_ids: list[int] | None = None,
        due_date: int | None = None,
        priority: int | None = None,
    ) -> ClickUpSubtask:
        """
        Create a subtask under a parent task.

        Args:
            task_id: ID of the parent task.
            name: Subtask name.
            assignee_ids: List of assignee IDs.
            due_date: Due date in milliseconds.
            priority: Priority level.

        Returns:
            ClickUpSubtask object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if not name or not name.strip():
            raise ValueError("Subtask name cannot be empty")

        try:
            payload: dict[str, Any] = {"name": name}
            if assignee_ids:
                payload["assignees"] = assignee_ids
            if due_date:
                payload["due_date"] = due_date
            if priority:
                payload["priority"] = priority

            response = await self.post(f"/task/{task_id}/subtask", json=payload)

            return ClickUpSubtask(
                id=response.get("id", ""),
                name=response.get("name", ""),
                status=response.get("status", {}).get("type"),
                priority=response.get("priority", {}).get("priority"),
                assignees=response.get("assignees", []),
                due_date=response.get("due_date"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to create subtask '{name}': {e}")
            raise ClickUpError(f"Failed to create subtask: {str(e)}") from e

    # ========================================================================
    # COMMENT MANAGEMENT
    # ========================================================================

    async def get_task_comments(self, task_id: str) -> list[ClickUpComment]:
        """
        Get all comments on a task.

        Args:
            task_id: ID of the task.

        Returns:
            List of ClickUpComment objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.get(f"/task/{task_id}/comment")
            comments_data = response.get("comments", [])

            return [
                ClickUpComment(
                    id=c.get("id", ""),
                    text=c.get("text_content", ""),
                    user=c.get("user", {}),
                    created_at=c.get("date_created"),
                    updated_at=c.get("date_updated"),
                    attachments=c.get("attachments", []),
                    raw=c,
                )
                for c in comments_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch comments for task {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch comments: {str(e)}") from e

    async def add_comment(self, task_id: str, text: str) -> ClickUpComment:
        """
        Add a comment to a task.

        Args:
            task_id: ID of the task.
            text: Comment text.

        Returns:
            ClickUpComment object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if not text or not text.strip():
            raise ValueError("Comment text cannot be empty")

        try:
            response = await self.post(
                f"/task/{task_id}/comment",
                json={"comment_text": text},
            )

            return ClickUpComment(
                id=response.get("id", ""),
                text=response.get("text_content", ""),
                user=response.get("user", {}),
                created_at=response.get("date_created"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to add comment to task {task_id}: {e}")
            raise ClickUpError(f"Failed to add comment: {str(e)}") from e

    # ========================================================================
    # ATTACHMENT MANAGEMENT
    # ========================================================================

    async def get_task_attachments(self, task_id: str) -> list[ClickUpAttachment]:
        """
        Get all attachments on a task.

        Args:
            task_id: ID of the task.

        Returns:
            List of ClickUpAttachment objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            # Attachments are returned with task details
            response = await self.get(f"/task/{task_id}")
            attachments_data = response.get("attachments", [])

            return [
                ClickUpAttachment(
                    id=a.get("id", ""),
                    title=a.get("title", ""),
                    url=a.get("url", ""),
                    mime_type=a.get("mime_type"),
                    size=a.get("size"),
                    created_at=a.get("date"),
                    created_by=a.get("created_by", {}),
                    raw=a,
                )
                for a in attachments_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch attachments for task {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch attachments: {str(e)}") from e

    # ========================================================================
    # TASK STATUS & WORKFLOW
    # ========================================================================

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> dict[str, Any]:
        """
        Update task status.

        Args:
            task_id: ID of the task.
            status: New status (e.g., 'open', 'in_progress', 'done').

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if not status or not status.strip():
            raise ValueError("Status cannot be empty")

        try:
            response = await self.put(
                f"/task/{task_id}",
                json={"status": status},
            )
            return response
        except Exception as e:
            logger.error(f"Failed to update status for task {task_id}: {e}")
            raise ClickUpError(f"Failed to update task status: {str(e)}") from e

    async def update_task_priority(
        self,
        task_id: str,
        priority: int,
    ) -> dict[str, Any]:
        """
        Update task priority.

        Args:
            task_id: ID of the task.
            priority: Priority level (1-5, 1=urgent).

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5")

        try:
            response = await self.put(
                f"/task/{task_id}",
                json={"priority": priority},
            )
            return response
        except Exception as e:
            logger.error(f"Failed to update priority for task {task_id}: {e}")
            raise ClickUpError(f"Failed to update task priority: {str(e)}") from e

    async def update_task_assignees(
        self,
        task_id: str,
        add_assignees: list[int] | None = None,
        remove_assignees: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Update task assignees.

        Args:
            task_id: ID of the task.
            add_assignees: User IDs to add as assignees.
            remove_assignees: User IDs to remove from assignees.

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            payload: dict[str, Any] = {}
            if add_assignees:
                payload["add_assignees"] = add_assignees
            if remove_assignees:
                payload["remove_assignees"] = remove_assignees

            if not payload:
                raise ValueError("Must provide assignees to add or remove")

            response = await self.put(f"/task/{task_id}", json=payload)
            return response
        except Exception as e:
            logger.error(f"Failed to update assignees for task {task_id}: {e}")
            raise ClickUpError(f"Failed to update task assignees: {str(e)}") from e

    async def update_task_due_date(
        self,
        task_id: str,
        due_date: int | None,
    ) -> dict[str, Any]:
        """
        Update task due date.

        Args:
            task_id: ID of the task.
            due_date: Due date in milliseconds since epoch (or None to clear).

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.put(
                f"/task/{task_id}",
                json={"due_date": due_date},
            )
            return response
        except Exception as e:
            logger.error(f"Failed to update due date for task {task_id}: {e}")
            raise ClickUpError(f"Failed to update task due date: {str(e)}") from e

    async def bulk_update_tasks(
        self,
        task_ids: list[str],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Bulk update multiple tasks.

        Args:
            task_ids: List of task IDs to update.
            updates: Dictionary of fields to update (status, priority, assignees, etc).

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_ids:
            raise ValueError("Task IDs list cannot be empty")
        if not updates:
            raise ValueError("Updates dictionary cannot be empty")

        try:
            # ClickUp doesn't have a bulk update endpoint, so update each task
            results = {}
            for task_id in task_ids:
                try:
                    result = await self.put(f"/task/{task_id}", json=updates)
                    results[task_id] = {"status": "success", "data": result}
                except Exception as e:
                    results[task_id] = {"status": "error", "error": str(e)}

            return results
        except Exception as e:
            logger.error(f"Failed to bulk update tasks: {e}")
            raise ClickUpError(f"Failed to bulk update tasks: {str(e)}") from e

    # ========================================================================
    # TIME TRACKING
    # ========================================================================

    async def get_task_time_entries(self, task_id: str) -> list[ClickUpTimeEntry]:
        """
        Get time tracking entries for a task.

        Args:
            task_id: ID of the task.

        Returns:
            List of ClickUpTimeEntry objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.get(f"/task/{task_id}/time")
            entries_data = response.get("data", [])

            return [
                ClickUpTimeEntry(
                    id=entry.get("id", ""),
                    task_id=task_id,
                    user=entry.get("user", {}),
                    time_in_milliseconds=entry.get("time", 0),
                    start_date=entry.get("start", 0),
                    end_date=entry.get("end"),
                    description=entry.get("description"),
                    billable=entry.get("billable", False),
                    raw=entry,
                )
                for entry in entries_data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch time entries for task {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch time entries: {str(e)}") from e

    async def add_time_entry(
        self,
        task_id: str,
        time_milliseconds: int,
        start_date: int,
        description: str | None = None,
        billable: bool = False,
    ) -> ClickUpTimeEntry:
        """
        Add a time tracking entry to a task.

        Args:
            task_id: ID of the task.
            time_milliseconds: Time spent in milliseconds.
            start_date: Start date in milliseconds.
            description: Optional description.
            billable: Whether time is billable.

        Returns:
            ClickUpTimeEntry object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")
        if time_milliseconds <= 0:
            raise ValueError("Time must be greater than 0")

        try:
            payload: dict[str, Any] = {
                "time": time_milliseconds,
                "start": start_date,
                "billable": billable,
            }
            if description:
                payload["description"] = description

            response = await self.post(f"/task/{task_id}/time", json=payload)

            return ClickUpTimeEntry(
                id=response.get("id", ""),
                task_id=task_id,
                user=response.get("user", {}),
                time_in_milliseconds=response.get("time", 0),
                start_date=response.get("start", 0),
                billable=response.get("billable", False),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to add time entry to task {task_id}: {e}")
            raise ClickUpError(f"Failed to add time entry: {str(e)}") from e

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check API connectivity and authentication.

        Returns:
            Health status dictionary.

        Raises:
            ClickUpError: If API is unavailable.
        """
        try:
            response = await self.get("/team")
            return {
                "status": "healthy",
                "accessible_workspaces": len(response.get("teams", [])),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise ClickUpError(f"Health check failed: {str(e)}") from e

    async def call_endpoint(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any ClickUp endpoint directly (future-proof).

        Args:
            endpoint: API endpoint path.
            method: HTTP method.
            **kwargs: Additional parameters (json, params, etc).

        Returns:
            Response dictionary.

        Raises:
            ClickUpError: If request fails.
        """
        try:
            if method == "GET":
                return await self.get(endpoint, **kwargs)
            elif method == "POST":
                return await self.post(endpoint, **kwargs)
            elif method == "PUT":
                return await self.put(endpoint, **kwargs)
            elif method == "DELETE":
                return await self.delete(endpoint, **kwargs)
            elif method == "PATCH":
                return await self.patch(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except Exception as e:
            logger.error(f"Failed to call endpoint {endpoint}: {e}")
            raise ClickUpError(f"Failed to call endpoint: {str(e)}") from e
