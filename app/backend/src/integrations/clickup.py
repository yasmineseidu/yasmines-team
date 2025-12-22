"""
ClickUp API integration client for task and workspace management.

Provides async access to ClickUp's REST API v2/v3 for:
- Workspace and team management
- Space management
- List creation and operations
- Task CRUD operations (create, read, update, delete)
- Folder management
- Member and permission operations

API Documentation:
- ClickUp API: https://developer.clickup.com/
- API Reference: https://clickup.readme.io/docs/index
- Authentication: https://developer.clickup.com/docs

Authentication:
- Uses Bearer token authentication via API key
- Token is passed in Authorization header
- No rate limiting concerns documented (generous limits)

Example:
    >>> from src.integrations.clickup import ClickUpClient
    >>> client = ClickUpClient(api_key="pk_12345678")
    >>> async with client:
    ...     workspaces = await client.get_workspaces()
    ...     for workspace in workspaces:
    ...         print(f"Workspace: {workspace['name']}")
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class ClickUpError(IntegrationError):
    """ClickUp-specific error."""

    pass


class ClickUpAuthError(AuthenticationError):
    """ClickUp authentication error."""

    pass


class ClickUpRateLimitError(RateLimitError):
    """ClickUp rate limit error."""

    pass


@dataclass
class ClickUpWorkspace:
    """ClickUp workspace information."""

    id: str
    name: str
    color: str | None = None
    avatar: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpSpace:
    """ClickUp space information."""

    id: str
    name: str
    color: str | None = None
    private: bool = False
    avatar: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpList:
    """ClickUp list information."""

    id: str
    name: str
    folder_id: str | None = None
    space_id: str | None = None
    color: str | None = None
    private: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClickUpTask:
    """ClickUp task information."""

    id: str
    custom_id: str | None
    name: str
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    due_date: int | None = None
    start_date: int | None = None
    assignees: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    list_id: str | None = None
    folder_id: str | None = None
    space_id: str | None = None
    created_at: int | None = None
    updated_at: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ClickUpClient(BaseIntegrationClient):
    """Async client for ClickUp API (v2/v3)."""

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize ClickUp client.

        Args:
            api_key: ClickUp API key (personal or OAuth token).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            retry_base_delay: Base delay for exponential backoff in seconds.

        Raises:
            ValueError: If API key is empty or invalid.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        super().__init__(
            name="clickup",
            base_url="https://api.clickup.com/api/v2",
            api_key=api_key.strip(),
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )
        logger.info("ClickUp client initialized")

    def _get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers for ClickUp API requests.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Authorization": self.api_key,  # ClickUp uses direct key in Authorization header
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_workspaces(self) -> list[ClickUpWorkspace]:
        """
        Get all workspaces accessible to the authenticated user.

        Returns:
            List of ClickUpWorkspace objects.

        Raises:
            ClickUpError: If API request fails.
        """
        try:
            response = await self.get("/team")
            teams = response.get("teams", [])
            return [
                ClickUpWorkspace(
                    id=str(team.get("id", "")),
                    name=team.get("name", ""),
                    color=team.get("color"),
                    avatar=team.get("avatar"),
                    raw=team,
                )
                for team in teams
            ]
        except Exception as e:
            logger.error(f"Failed to fetch workspaces: {e}")
            raise ClickUpError(f"Failed to fetch workspaces: {str(e)}") from e

    async def get_spaces(self, workspace_id: str) -> list[ClickUpSpace]:
        """
        Get all spaces in a workspace.

        Args:
            workspace_id: ID of the workspace.

        Returns:
            List of ClickUpSpace objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not workspace_id or not workspace_id.strip():
            raise ValueError("Workspace ID cannot be empty")

        try:
            response = await self.get(f"/team/{workspace_id}/space")
            spaces = response.get("spaces", [])
            return [
                ClickUpSpace(
                    id=str(space.get("id", "")),
                    name=space.get("name", ""),
                    color=space.get("color"),
                    private=space.get("private", False),
                    avatar=space.get("avatar"),
                    raw=space,
                )
                for space in spaces
            ]
        except Exception as e:
            logger.error(f"Failed to fetch spaces for workspace {workspace_id}: {e}")
            raise ClickUpError(
                f"Failed to fetch spaces for workspace {workspace_id}: {str(e)}"
            ) from e

    async def get_lists(self, space_id: str) -> list[ClickUpList]:
        """
        Get all lists in a space.

        Args:
            space_id: ID of the space.

        Returns:
            List of ClickUpList objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not space_id or not space_id.strip():
            raise ValueError("Space ID cannot be empty")

        try:
            response = await self.get(f"/space/{space_id}/list")
            lists = response.get("lists", [])
            return [
                ClickUpList(
                    id=str(list_item.get("id", "")),
                    name=list_item.get("name", ""),
                    folder_id=str(list_item.get("folder", {}).get("id"))
                    if list_item.get("folder")
                    else None,
                    space_id=str(list_item.get("space", {}).get("id"))
                    if list_item.get("space")
                    else None,
                    color=list_item.get("color"),
                    private=list_item.get("private", False),
                    raw=list_item,
                )
                for list_item in lists
            ]
        except Exception as e:
            logger.error(f"Failed to fetch lists for space {space_id}: {e}")
            raise ClickUpError(f"Failed to fetch lists for space {space_id}: {str(e)}") from e

    async def create_task(
        self,
        list_id: str,
        name: str,
        description: str | None = None,
        priority: int | None = None,
        due_date: int | None = None,
        start_date: int | None = None,
        assignee_ids: list[int] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> ClickUpTask:
        """
        Create a new task in a list.

        Args:
            list_id: ID of the list to create task in.
            name: Task name/title.
            description: Task description.
            priority: Priority level (1-5, 1=urgent).
            due_date: Due date in milliseconds since epoch.
            start_date: Start date in milliseconds since epoch.
            assignee_ids: List of assignee user IDs.
            tags: List of tags to apply.
            **kwargs: Additional task fields.

        Returns:
            ClickUpTask object representing the created task.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        try:
            payload: dict[str, Any] = {
                "name": name,
                **kwargs,
            }

            if description:
                payload["description"] = description
            if priority is not None:
                payload["priority"] = priority
            if due_date is not None:
                payload["due_date"] = due_date
            if start_date is not None:
                payload["start_date"] = start_date
            if assignee_ids:
                payload["assignees"] = assignee_ids
            if tags:
                payload["tags"] = tags

            response = await self.post(f"/list/{list_id}/task", json=payload)
            return ClickUpTask(
                id=str(response.get("id", "")),
                custom_id=response.get("custom_id"),
                name=response.get("name", ""),
                description=response.get("description"),
                status=response.get("status", {}).get("status") if response.get("status") else None,
                priority=response.get("priority", {}).get("priority")
                if response.get("priority")
                else None,
                due_date=response.get("due_date"),
                start_date=response.get("start_date"),
                assignees=response.get("assignees", []),
                tags=[tag.get("name", "") for tag in response.get("tags", [])],
                list_id=str(response.get("list", {}).get("id")) if response.get("list") else None,
                folder_id=str(response.get("folder", {}).get("id"))
                if response.get("folder")
                else None,
                space_id=str(response.get("space", {}).get("id"))
                if response.get("space")
                else None,
                created_at=response.get("date_created"),
                updated_at=response.get("date_updated"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to create task in list {list_id}: {e}")
            raise ClickUpError(f"Failed to create task in list {list_id}: {str(e)}") from e

    async def get_task(self, task_id: str) -> ClickUpTask:
        """
        Get details of a specific task.

        Args:
            task_id: ID of the task to retrieve.

        Returns:
            ClickUpTask object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.get(f"/task/{task_id}")
            return ClickUpTask(
                id=str(response.get("id", "")),
                custom_id=response.get("custom_id"),
                name=response.get("name", ""),
                description=response.get("description"),
                status=response.get("status", {}).get("status") if response.get("status") else None,
                priority=response.get("priority", {}).get("priority")
                if response.get("priority")
                else None,
                due_date=response.get("due_date"),
                start_date=response.get("start_date"),
                assignees=response.get("assignees", []),
                tags=[tag.get("name", "") for tag in response.get("tags", [])],
                list_id=str(response.get("list", {}).get("id")) if response.get("list") else None,
                folder_id=str(response.get("folder", {}).get("id"))
                if response.get("folder")
                else None,
                space_id=str(response.get("space", {}).get("id"))
                if response.get("space")
                else None,
                created_at=response.get("date_created"),
                updated_at=response.get("date_updated"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to fetch task {task_id}: {e}")
            raise ClickUpError(f"Failed to fetch task {task_id}: {str(e)}") from e

    async def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        due_date: int | None = None,
        **kwargs: Any,
    ) -> ClickUpTask:
        """
        Update an existing task.

        Args:
            task_id: ID of the task to update.
            name: New task name.
            description: New task description.
            status: New task status.
            priority: New priority level.
            due_date: New due date in milliseconds.
            **kwargs: Additional fields to update.

        Returns:
            Updated ClickUpTask object.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            payload: dict[str, Any] = {}

            if name is not None:
                payload["name"] = name
            if description is not None:
                payload["description"] = description
            if status is not None:
                payload["status"] = status
            if priority is not None:
                payload["priority"] = priority
            if due_date is not None:
                payload["due_date"] = due_date

            payload.update(kwargs)

            response = await self.put(f"/task/{task_id}", json=payload)
            return ClickUpTask(
                id=str(response.get("id", "")),
                custom_id=response.get("custom_id"),
                name=response.get("name", ""),
                description=response.get("description"),
                status=response.get("status", {}).get("status") if response.get("status") else None,
                priority=response.get("priority", {}).get("priority")
                if response.get("priority")
                else None,
                due_date=response.get("due_date"),
                start_date=response.get("start_date"),
                assignees=response.get("assignees", []),
                tags=[tag.get("name", "") for tag in response.get("tags", [])],
                list_id=str(response.get("list", {}).get("id")) if response.get("list") else None,
                folder_id=str(response.get("folder", {}).get("id"))
                if response.get("folder")
                else None,
                space_id=str(response.get("space", {}).get("id"))
                if response.get("space")
                else None,
                created_at=response.get("date_created"),
                updated_at=response.get("date_updated"),
                raw=response,
            )
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise ClickUpError(f"Failed to update task {task_id}: {str(e)}") from e

    async def delete_task(self, task_id: str) -> dict[str, Any]:
        """
        Delete a task.

        Args:
            task_id: ID of the task to delete.

        Returns:
            Response from the delete operation.

        Raises:
            ClickUpError: If API request fails.
        """
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty")

        try:
            response = await self.delete(f"/task/{task_id}")
            logger.info(f"Task {task_id} deleted successfully")
            return response
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise ClickUpError(f"Failed to delete task {task_id}: {str(e)}") from e

    async def get_tasks_by_list(self, list_id: str, limit: int = 100) -> list[ClickUpTask]:
        """
        Get all tasks in a list.

        Args:
            list_id: ID of the list.
            limit: Maximum number of tasks to return (default 100).

        Returns:
            List of ClickUpTask objects.

        Raises:
            ClickUpError: If API request fails.
        """
        if not list_id or not list_id.strip():
            raise ValueError("List ID cannot be empty")

        try:
            response = await self.get(f"/list/{list_id}/task", params={"limit": limit})
            tasks = response.get("tasks", [])
            return [
                ClickUpTask(
                    id=str(task.get("id", "")),
                    custom_id=task.get("custom_id"),
                    name=task.get("name", ""),
                    description=task.get("description"),
                    status=task.get("status", {}).get("status") if task.get("status") else None,
                    priority=task.get("priority", {}).get("priority")
                    if task.get("priority")
                    else None,
                    due_date=task.get("due_date"),
                    start_date=task.get("start_date"),
                    assignees=task.get("assignees", []),
                    tags=[tag.get("name", "") for tag in task.get("tags", [])],
                    list_id=str(task.get("list", {}).get("id")) if task.get("list") else None,
                    folder_id=str(task.get("folder", {}).get("id")) if task.get("folder") else None,
                    space_id=str(task.get("space", {}).get("id")) if task.get("space") else None,
                    created_at=task.get("date_created"),
                    updated_at=task.get("date_updated"),
                    raw=task,
                )
                for task in tasks
            ]
        except Exception as e:
            logger.error(f"Failed to fetch tasks from list {list_id}: {e}")
            raise ClickUpError(f"Failed to fetch tasks from list {list_id}: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check ClickUp API connectivity and authentication.

        Returns:
            API response confirming connectivity.

        Raises:
            ClickUpError: If health check fails.
        """
        try:
            response = await self.get_workspaces()
            logger.info("ClickUp health check passed")
            return {"status": "healthy", "workspaces_count": len(response)}
        except Exception as e:
            logger.error(f"ClickUp health check failed: {e}")
            raise ClickUpError(f"Health check failed: {str(e)}") from e
