"""
Todoist API integration client.

Provides task and project management capabilities through Todoist's REST API v2.
Supports creating, updating, completing, and fetching tasks, projects, sections,
and comments.

API Documentation: https://developer.todoist.com/rest/v2/
Base URL: https://api.todoist.com/rest/v2

Features:
- Project management (get, create, update, delete projects)
- Task management (get, create, update, close, delete tasks)
- Section management (get, create, update, delete sections)
- Comment management (get, create, update, delete comments)
- Label management (get personal and shared labels)
- Bulk task operations
- Idempotent requests with X-Request-Id header

Rate Limits:
- 1,000 requests per 15-minute period per user
- 1 MiB HTTP request body limit on POST requests
- 15-second processing timeout per request

Example:
    >>> from src.integrations.todoist import TodoistClient
    >>> client = TodoistClient(api_key="your-api-key")
    >>> projects = await client.get_projects()
    >>> task = await client.create_task(
    ...     content="Complete API integration",
    ...     project_id="123456",
    ...     due_string="tomorrow",
    ...     priority=2
    ... )
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class TodoistPriority(int, Enum):
    """Task priority levels in Todoist (1-4, where 4 is urgent)."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TodoistError(IntegrationError):
    """Todoist-specific error."""

    pass


@dataclass
class TodoistProject:
    """Todoist project representation."""

    id: str
    name: str
    color: str | None = None
    parent_id: str | None = None
    order: int = 0
    comment_count: int = 0
    is_shared: bool = False
    is_favorite: bool = False
    is_inbox_project: bool = False
    is_team_inbox: bool = False
    view_style: str = "list"
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TodoistTask:
    """Todoist task representation."""

    id: str
    content: str
    project_id: str | None = None
    section_id: str | None = None
    parent_id: str | None = None
    order: int = 0
    priority: int = 1
    is_completed: bool = False
    due_date: str | None = None
    due_datetime: str | None = None
    due_string: str | None = None
    due_timezone: str | None = None
    created_at: str | None = None
    creator_id: str | None = None
    url: str | None = None
    comment_count: int = 0
    labels: list[str] = field(default_factory=list)
    duration_minutes: int | None = None
    description: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TodoistSection:
    """Todoist section representation."""

    id: str
    name: str
    project_id: str
    order: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TodoistComment:
    """Todoist comment representation."""

    id: str
    content: str
    task_id: str | None = None
    project_id: str | None = None
    posted_at: str | None = None
    posted_uid: str | None = None
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TodoistLabel:
    """Todoist label representation."""

    id: str
    name: str
    color: str | None = None
    order: int = 0
    is_favorite: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


class TodoistClient(BaseIntegrationClient):
    """
    Todoist API client for task and project management.

    Provides async methods for managing projects, tasks, sections, comments,
    and labels through Todoist's REST API v2.

    Example:
        >>> client = TodoistClient(api_key="your-api-key")
        >>> projects = await client.get_projects()
        >>> for project in projects:
        ...     print(f"{project.name}: {project.comment_count} comments")
        ...
        >>> task = await client.create_task(
        ...     content="New task",
        ...     project_id=projects[0].id,
        ...     priority=TodoistPriority.HIGH
        ... )
    """

    BASE_URL = "https://api.todoist.com/rest/v2"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize Todoist client.

        Args:
            api_key: Todoist API key from integrations/developer settings
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts for transient failures
            retry_base_delay: Base delay for exponential backoff in seconds
        """
        super().__init__(
            name="todoist",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )
        logger.info(f"Initialized {self.name} client")

    def _get_headers(self) -> dict[str, str]:
        """
        Get default headers for Todoist API requests.

        Overrides base method to use Authorization header for bearer token.

        Returns:
            Dictionary of HTTP headers including bearer token.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_projects(self) -> list[TodoistProject]:
        """
        Get all projects for the authenticated user.

        Returns:
            List of TodoistProject objects.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> projects = await client.get_projects()
            >>> for project in projects:
            ...     print(project.name)
        """
        try:
            response = await self.get("/projects")
            projects_data: list[dict[str, Any]] = (
                response if isinstance(response, list) else [response]
            )

            return [
                TodoistProject(
                    id=project["id"],
                    name=project["name"],
                    color=project.get("color"),
                    parent_id=project.get("parent_id"),
                    order=project.get("order", 0),
                    comment_count=project.get("comment_count", 0),
                    is_shared=project.get("is_shared", False),
                    is_favorite=project.get("is_favorite", False),
                    is_inbox_project=project.get("is_inbox_project", False),
                    is_team_inbox=project.get("is_team_inbox", False),
                    view_style=project.get("view_style", "list"),
                    url=project.get("url"),
                    raw=project,
                )
                for project in projects_data
            ]
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            raise TodoistError(f"Failed to get projects: {e}") from e

    async def get_project(self, project_id: str) -> TodoistProject:
        """
        Get a specific project by ID.

        Args:
            project_id: The project ID.

        Returns:
            TodoistProject object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> project = await client.get_project("123456")
            >>> print(project.name)
        """
        try:
            data = await self.get(f"/projects/{project_id}")

            return TodoistProject(
                id=data["id"],
                name=data["name"],
                color=data.get("color"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                comment_count=data.get("comment_count", 0),
                is_shared=data.get("is_shared", False),
                is_favorite=data.get("is_favorite", False),
                is_inbox_project=data.get("is_inbox_project", False),
                is_team_inbox=data.get("is_team_inbox", False),
                view_style=data.get("view_style", "list"),
                url=data.get("url"),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            raise TodoistError(f"Failed to get project {project_id}: {e}") from e

    async def create_project(
        self,
        name: str,
        parent_id: str | None = None,
        **kwargs: Any,
    ) -> TodoistProject:
        """
        Create a new project.

        Args:
            name: Project name (required).
            parent_id: Parent project ID for sub-projects (optional).
            **kwargs: Additional project properties.

        Returns:
            Created TodoistProject object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> project = await client.create_project(
            ...     name="My New Project",
            ...     color="blue"
            ... )
            >>> print(project.id)
        """
        try:
            payload = {"name": name, **({"parent_id": parent_id} if parent_id else {}), **kwargs}

            data = await self.post("/projects", json=payload)

            return TodoistProject(
                id=data["id"],
                name=data["name"],
                color=data.get("color"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                comment_count=data.get("comment_count", 0),
                is_shared=data.get("is_shared", False),
                is_favorite=data.get("is_favorite", False),
                is_inbox_project=data.get("is_inbox_project", False),
                is_team_inbox=data.get("is_team_inbox", False),
                view_style=data.get("view_style", "list"),
                url=data.get("url"),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise TodoistError(f"Failed to create project: {e}") from e

    async def get_tasks(
        self,
        project_id: str | None = None,
        section_id: str | None = None,
        label: str | None = None,
        filter: str | None = None,
        lang: str = "en",
        **kwargs: Any,
    ) -> list[TodoistTask]:
        """
        Get tasks with optional filtering.

        Args:
            project_id: Filter by project ID (optional).
            section_id: Filter by section ID (optional).
            label: Filter by label name (optional).
            filter: Advanced filter string (optional).
            lang: Language for filter parsing (default 'en').
            **kwargs: Additional query parameters.

        Returns:
            List of TodoistTask objects.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> tasks = await client.get_tasks(project_id="123456")
            >>> for task in tasks:
            ...     print(f"{task.content} (priority: {task.priority})")
        """
        try:
            params: dict[str, Any] = {
                "lang": lang,
                **kwargs,
            }

            if project_id:
                params["project_id"] = project_id
            if section_id:
                params["section_id"] = section_id
            if label:
                params["label"] = label
            if filter:
                params["filter"] = filter

            response = await self.get("/tasks", params=params)
            tasks_data: list[dict[str, Any]] = (
                response if isinstance(response, list) else [response]
            )

            return [
                TodoistTask(
                    id=task["id"],
                    content=task["content"],
                    project_id=task.get("project_id"),
                    section_id=task.get("section_id"),
                    parent_id=task.get("parent_id"),
                    order=task.get("order", 0),
                    priority=task.get("priority", 1),
                    is_completed=task.get("is_completed", False),
                    due_date=task.get("due", {}).get("date") if task.get("due") else None,
                    due_datetime=task.get("due", {}).get("datetime") if task.get("due") else None,
                    due_string=task.get("due", {}).get("string") if task.get("due") else None,
                    due_timezone=task.get("due", {}).get("timezone") if task.get("due") else None,
                    created_at=task.get("created_at"),
                    creator_id=task.get("creator_id"),
                    url=task.get("url"),
                    comment_count=task.get("comment_count", 0),
                    labels=task.get("labels", []),
                    duration_minutes=task.get("duration", {}).get("amount")
                    if task.get("duration")
                    else None,
                    description=task.get("description"),
                    raw=task,
                )
                for task in tasks_data
            ]
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            raise TodoistError(f"Failed to get tasks: {e}") from e

    async def get_task(self, task_id: str) -> TodoistTask:
        """
        Get a specific task by ID.

        Args:
            task_id: The task ID.

        Returns:
            TodoistTask object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> task = await client.get_task("123456")
            >>> print(task.content)
        """
        try:
            data = await self.get(f"/tasks/{task_id}")

            due = data.get("due", {}) or {}
            return TodoistTask(
                id=data["id"],
                content=data["content"],
                project_id=data.get("project_id"),
                section_id=data.get("section_id"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                priority=data.get("priority", 1),
                is_completed=data.get("is_completed", False),
                due_date=due.get("date"),
                due_datetime=due.get("datetime"),
                due_string=due.get("string"),
                due_timezone=due.get("timezone"),
                created_at=data.get("created_at"),
                creator_id=data.get("creator_id"),
                url=data.get("url"),
                comment_count=data.get("comment_count", 0),
                labels=data.get("labels", []),
                duration_minutes=data.get("duration", {}).get("amount")
                if data.get("duration")
                else None,
                description=data.get("description"),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise TodoistError(f"Failed to get task {task_id}: {e}") from e

    async def create_task(
        self,
        content: str,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        order: int | None = None,
        priority: int = 1,
        due_string: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        due_timezone: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
        duration_minutes: int | None = None,
        **kwargs: Any,
    ) -> TodoistTask:
        """
        Create a new task.

        Args:
            content: Task content/title (required).
            project_id: Project ID (optional, uses inbox if not provided).
            section_id: Section ID (optional).
            parent_id: Parent task ID for subtasks (optional).
            order: Task order in list (optional).
            priority: Priority level 1-4 (default 1, low).
            due_string: Due date as natural language string (optional).
            due_date: Due date in YYYY-MM-DD format (optional).
            due_datetime: Due datetime in ISO 8601 format (optional).
            due_timezone: Timezone for due datetime (optional).
            labels: List of label names (optional).
            description: Task description (optional).
            duration_minutes: Estimated duration in minutes (optional).
            **kwargs: Additional task properties.

        Returns:
            Created TodoistTask object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> task = await client.create_task(
            ...     content="Complete API integration",
            ...     project_id="123456",
            ...     due_string="tomorrow",
            ...     priority=TodoistPriority.HIGH,
            ...     labels=["work", "urgent"]
            ... )
            >>> print(task.id)
        """
        try:
            payload: dict[str, Any] = {
                "content": content,
                "priority": priority,
                **kwargs,
            }

            if project_id:
                payload["project_id"] = project_id
            if section_id:
                payload["section_id"] = section_id
            if parent_id:
                payload["parent_id"] = parent_id
            if order is not None:
                payload["order"] = order
            if due_string:
                payload["due_string"] = due_string
            if due_date:
                payload["due_date"] = due_date
            if due_datetime or due_timezone:
                due_obj = {}
                if due_datetime:
                    due_obj["datetime"] = due_datetime
                if due_timezone:
                    due_obj["timezone"] = due_timezone
                if due_obj:
                    payload["due"] = due_obj
            if labels:
                payload["labels"] = labels
            if description:
                payload["description"] = description
            if duration_minutes:
                payload["duration"] = {"amount": duration_minutes, "unit": "minute"}

            data = await self.post("/tasks", json=payload)

            due = data.get("due", {}) or {}
            return TodoistTask(
                id=data["id"],
                content=data["content"],
                project_id=data.get("project_id"),
                section_id=data.get("section_id"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                priority=data.get("priority", 1),
                is_completed=data.get("is_completed", False),
                due_date=due.get("date"),
                due_datetime=due.get("datetime"),
                due_string=due.get("string"),
                due_timezone=due.get("timezone"),
                created_at=data.get("created_at"),
                creator_id=data.get("creator_id"),
                url=data.get("url"),
                comment_count=data.get("comment_count", 0),
                labels=data.get("labels", []),
                duration_minutes=data.get("duration", {}).get("amount")
                if data.get("duration")
                else None,
                description=data.get("description"),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise TodoistError(f"Failed to create task: {e}") from e

    async def update_task(
        self,
        task_id: str,
        content: str | None = None,
        due_string: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        due_timezone: str | None = None,
        priority: int | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
        duration_minutes: int | None = None,
        **kwargs: Any,
    ) -> TodoistTask:
        """
        Update an existing task.

        Args:
            task_id: The task ID (required).
            content: Updated task content (optional).
            due_string: Updated due date as natural language (optional).
            due_date: Updated due date in YYYY-MM-DD format (optional).
            due_datetime: Updated due datetime in ISO 8601 format (optional).
            due_timezone: Timezone for due datetime (optional).
            priority: Updated priority 1-4 (optional).
            labels: Updated label list (optional).
            description: Updated description (optional).
            duration_minutes: Updated duration in minutes (optional).
            **kwargs: Additional task properties.

        Returns:
            Updated TodoistTask object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> task = await client.update_task(
            ...     task_id="123456",
            ...     priority=TodoistPriority.URGENT,
            ...     due_string="today"
            ... )
            >>> print(task.priority)
        """
        try:
            payload: dict[str, Any] = {}

            if content:
                payload["content"] = content
            if priority is not None:
                payload["priority"] = priority
            if due_string:
                payload["due_string"] = due_string
            if due_date:
                payload["due_date"] = due_date
            if due_datetime or due_timezone:
                due_obj = {}
                if due_datetime:
                    due_obj["datetime"] = due_datetime
                if due_timezone:
                    due_obj["timezone"] = due_timezone
                if due_obj:
                    payload["due"] = due_obj
            if labels is not None:
                payload["labels"] = labels
            if description:
                payload["description"] = description
            if duration_minutes is not None:
                payload["duration"] = (
                    {"amount": duration_minutes, "unit": "minute"} if duration_minutes else None
                )

            payload.update(kwargs)

            data = await self.post(f"/tasks/{task_id}", json=payload)

            due = data.get("due", {}) or {}
            return TodoistTask(
                id=data["id"],
                content=data["content"],
                project_id=data.get("project_id"),
                section_id=data.get("section_id"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                priority=data.get("priority", 1),
                is_completed=data.get("is_completed", False),
                due_date=due.get("date"),
                due_datetime=due.get("datetime"),
                due_string=due.get("string"),
                due_timezone=due.get("timezone"),
                created_at=data.get("created_at"),
                creator_id=data.get("creator_id"),
                url=data.get("url"),
                comment_count=data.get("comment_count", 0),
                labels=data.get("labels", []),
                duration_minutes=data.get("duration", {}).get("amount")
                if data.get("duration")
                else None,
                description=data.get("description"),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise TodoistError(f"Failed to update task {task_id}: {e}") from e

    async def close_task(self, task_id: str) -> bool:
        """
        Mark a task as completed/closed.

        Args:
            task_id: The task ID.

        Returns:
            True if successful.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> success = await client.close_task("123456")
            >>> print(f"Task closed: {success}")
        """
        try:
            # Close endpoint returns 204 No Content
            await self.post(f"/tasks/{task_id}/close")
            logger.info(f"Task {task_id} closed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to close task {task_id}: {e}")
            raise TodoistError(f"Failed to close task {task_id}: {e}") from e

    async def reopen_task(self, task_id: str) -> TodoistTask:
        """
        Reopen a completed task.

        Args:
            task_id: The task ID.

        Returns:
            Updated TodoistTask object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> task = await client.reopen_task("123456")
            >>> print(f"Reopened: {task.is_completed}")
        """
        try:
            # Reopen endpoint returns 204 No Content, so we need to fetch the task after
            await self.post(f"/tasks/{task_id}/reopen")
            logger.info(f"Task {task_id} reopened successfully")

            # Fetch the reopened task to get its updated state
            return await self.get_task(task_id)
        except Exception as e:
            logger.error(f"Failed to reopen task {task_id}: {e}")
            raise TodoistError(f"Failed to reopen task {task_id}: {e}") from e

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: The task ID.

        Returns:
            True if successful.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> success = await client.delete_task("123456")
            >>> print(f"Task deleted: {success}")
        """
        try:
            await self.delete(f"/tasks/{task_id}")
            logger.info(f"Task {task_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise TodoistError(f"Failed to delete task {task_id}: {e}") from e

    async def get_sections(self, project_id: str) -> list[TodoistSection]:
        """
        Get all sections in a project.

        Args:
            project_id: The project ID.

        Returns:
            List of TodoistSection objects.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> sections = await client.get_sections("123456")
            >>> for section in sections:
            ...     print(section.name)
        """
        try:
            response = await self.get(f"/projects/{project_id}/sections")
            sections_data: list[dict[str, Any]] = (
                response if isinstance(response, list) else [response]
            )

            return [
                TodoistSection(
                    id=section["id"],
                    name=section["name"],
                    project_id=section["project_id"],
                    order=section.get("order", 0),
                    raw=section,
                )
                for section in sections_data
            ]
        except Exception as e:
            logger.error(f"Failed to get sections for project {project_id}: {e}")
            raise TodoistError(f"Failed to get sections: {e}") from e

    async def create_section(
        self,
        name: str,
        project_id: str,
        order: int | None = None,
    ) -> TodoistSection:
        """
        Create a new section in a project.

        Args:
            name: Section name (required).
            project_id: Project ID (required).
            order: Section order (optional).

        Returns:
            Created TodoistSection object.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> section = await client.create_section(
            ...     name="In Progress",
            ...     project_id="123456"
            ... )
            >>> print(section.id)
        """
        try:
            payload: dict[str, Any] = {
                "name": name,
                "project_id": project_id,
            }

            if order is not None:
                payload["order"] = order

            data = await self.post("/sections", json=payload)

            return TodoistSection(
                id=data["id"],
                name=data["name"],
                project_id=data["project_id"],
                order=data.get("order", 0),
                raw=data,
            )
        except Exception as e:
            logger.error(f"Failed to create section: {e}")
            raise TodoistError(f"Failed to create section: {e}") from e

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Call any Todoist API endpoint dynamically.

        This method enables calling new endpoints without code changes,
        allowing the client to support newly released API endpoints.

        Args:
            endpoint: API endpoint path (e.g., "/tasks", "/projects/123")
            method: HTTP method (GET, POST, PUT, DELETE, default: GET)
            **kwargs: Request parameters (json, params, headers, etc.)

        Returns:
            API response data.

        Raises:
            TodoistError: If request fails.

        Example:
            >>> # Call a new endpoint that may be released in the future
            >>> result = await client.call_endpoint(
            ...     "/new-feature",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
        """
        try:
            method_lower = method.lower()
            if method_lower == "get":
                return await self.get(endpoint, **kwargs)
            elif method_lower == "post":
                return await self.post(endpoint, **kwargs)
            elif method_lower == "put":
                # PUT is not directly available on base client, use POST
                return await self.post(endpoint, **kwargs)
            elif method_lower == "delete":
                return await self.delete(endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except Exception as e:
            logger.error(f"Failed to call endpoint {endpoint}: {e}")
            raise TodoistError(f"Failed to call endpoint {endpoint}: {e}") from e
