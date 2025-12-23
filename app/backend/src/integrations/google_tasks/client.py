"""Google Tasks API client with domain-wide delegation support.

Provides async access to Google Tasks REST API v1 including:
- OAuth2 service account authentication with domain-wide delegation
- Task CRUD operations (create, read, update, delete, list)
- Task list management (create, list)
- Comprehensive error handling and retry logic

Rate Limits (per user):
- 1,000,000 queries per day
- 50,000 queries per day (courtesy limit)
- 429 = Too many requests (rate limited)
- 403 = Quota exceeded or permission denied

Example:
    >>> from src.integrations.google_tasks.client import GoogleTasksAPIClient
    >>> client = GoogleTasksAPIClient(credentials_json={...})
    >>> await client.authenticate()
    >>> task_lists = await client.list_task_lists()
    >>> tasks = await client.list_tasks(task_list_id="@default")
"""

import asyncio
import json
import logging
import os
import random
from typing import Any

import httpx

from src.integrations.google_tasks.exceptions import (
    GoogleTasksAPIError,
    GoogleTasksAuthError,
    GoogleTasksConfigError,
    GoogleTasksNotFoundError,
    GoogleTasksQuotaExceeded,
    GoogleTasksRateLimitError,
    GoogleTasksValidationError,
)
from src.integrations.google_tasks.models import (
    Task,
    TaskCreate,
    TaskList,
    TaskListCreate,
    TaskListsResponse,
    TasksListResponse,
    TaskUpdate,
)

logger = logging.getLogger(__name__)


class GoogleTasksAPIClient:
    """Async client for Google Tasks API v1.

    Supports task CRUD operations, task list management, and comprehensive
    error handling with exponential backoff retry logic.

    Attributes:
        credentials_json: OAuth2 service account credentials
        access_token: Current OAuth2 access token
        scopes: OAuth2 scopes for Tasks access
    """

    # Google Tasks API endpoints
    TASKS_API_BASE = "https://tasks.googleapis.com/tasks/v1"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # For domain-wide delegation, use single broad scope
    # (requesting multiple scopes when only some are authorized causes 400 error)
    DELEGATION_SCOPE = "https://www.googleapis.com/auth/tasks"

    # Default scopes when not using delegation
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/tasks",
        "https://www.googleapis.com/auth/tasks.readonly",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        credentials_path: str | None = None,
        access_token: str | None = None,
        delegated_user: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize Google Tasks API client.

        Args:
            credentials_json: OAuth2 service account credentials as dict
            credentials_str: OAuth2 service account credentials as JSON string
            credentials_path: Path to service account credentials JSON file
            access_token: Pre-obtained OAuth2 access token (optional)
            delegated_user: Email of user to impersonate (domain-wide delegation)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)

        Raises:
            GoogleTasksConfigError: If credentials are invalid or missing
        """
        # Load credentials from various sources
        if credentials_str and not credentials_json:
            try:
                credentials_json = json.loads(credentials_str)
            except json.JSONDecodeError as e:
                raise GoogleTasksConfigError(f"Invalid JSON in credentials string: {e}") from e

        if credentials_path and not credentials_json:
            credentials_json = self._load_credentials_from_path(credentials_path)

        if not credentials_json and not access_token:
            # Try to load from environment variable
            env_path = os.getenv("GOOGLE_TASKS_CREDENTIALS_JSON")
            if env_path:
                credentials_json = self._load_credentials_from_path(env_path)
            else:
                raise GoogleTasksConfigError(
                    "Credentials required. Provide credentials_json, credentials_str, "
                    "credentials_path, or set GOOGLE_TASKS_CREDENTIALS_JSON environment variable."
                )

        self.name = "google_tasks"
        self.base_url = self.TASKS_API_BASE
        self.credentials_json = credentials_json or {}
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

        # Determine which scopes to use
        if delegated_user:
            self.scopes = [self.DELEGATION_SCOPE]
        else:
            self.scopes = self.DEFAULT_SCOPES

        # Validate credentials structure if provided
        if self.credentials_json:
            self._validate_credentials(self.credentials_json)

        logger.info("Initialized Google Tasks API client")

    def _load_credentials_from_path(self, path: str) -> dict[str, Any]:
        """Load credentials from a file path.

        Args:
            path: Path to service account credentials JSON file

        Returns:
            Parsed credentials dictionary

        Raises:
            GoogleTasksConfigError: If file cannot be read or parsed
        """
        try:
            with open(path) as f:
                creds: dict[str, Any] = json.load(f)
                return creds
        except FileNotFoundError as e:
            raise GoogleTasksConfigError(f"Credentials file not found: {path}") from e
        except json.JSONDecodeError as e:
            raise GoogleTasksConfigError(f"Invalid JSON in credentials file: {e}") from e

    def _validate_credentials(self, creds: dict[str, Any]) -> None:
        """Validate credentials have required fields.

        Args:
            creds: Credentials dictionary

        Raises:
            GoogleTasksConfigError: If credentials are invalid
        """
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing = [f for f in required_fields if f not in creds]
        if missing:
            raise GoogleTasksConfigError(f"Credentials missing required fields: {missing}")

        if creds.get("type") != "service_account":
            raise GoogleTasksConfigError(f"Invalid credentials type: {creds.get('type')}")

    async def authenticate(self) -> None:
        """Authenticate and obtain access token using service account.

        Raises:
            GoogleTasksAuthError: If authentication fails
        """
        if self.access_token:
            logger.info("Using provided access token")
            return

        if not self.credentials_json:
            raise GoogleTasksAuthError("No credentials available for authentication")

        try:
            self.access_token = await self._get_access_token()
            logger.info("Successfully authenticated with service account")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleTasksAuthError(f"Failed to authenticate: {e}") from e

    async def _get_access_token(self) -> str:
        """Get access token using service account credentials.

        Returns:
            Access token string

        Raises:
            GoogleTasksAuthError: If token request fails
        """
        # Import here to avoid circular dependency
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials

        try:
            # Create credentials from service account JSON
            credentials = Credentials.from_service_account_info(
                self.credentials_json,
                scopes=self.scopes,
                subject=self.delegated_user,
            )

            # Refresh to get access token
            request = Request()
            credentials.refresh(request)

            return credentials.token or ""
        except Exception as e:
            raise GoogleTasksAuthError(f"Token request failed: {e}") from e

    async def __aenter__(self) -> "GoogleTasksAPIClient":
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Closed Google Tasks API client")

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON response

        Raises:
            GoogleTasksAPIError: If request fails
        """
        client = self._get_http_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, endpoint, **kwargs)

                # Handle specific status codes
                if response.status_code == 401:
                    raise GoogleTasksAuthError("Unauthorized - invalid or expired token")
                elif response.status_code == 403:
                    raise GoogleTasksQuotaExceeded(
                        "Forbidden - quota exceeded or permission denied"
                    )
                elif response.status_code == 404:
                    raise GoogleTasksNotFoundError("Task or task list not found")
                elif response.status_code == 429:
                    # Rate limited - retry with backoff
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries - 1:
                        wait_time = min(
                            retry_after,
                            self.retry_base_delay * (2**attempt) + random.uniform(0, 1),
                        )
                        logger.warning(f"Rate limited. Retrying in {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        continue
                    raise GoogleTasksRateLimitError("Rate limit exceeded - max retries exhausted")
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Server error {response.status_code}. " f"Retrying in {wait_time:.2f}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise GoogleTasksAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                # Handle 204 No Content (delete operations return no body)
                if response.status_code == 204:
                    return {}
                result: dict[str, Any] = response.json()
                return result

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
            ) as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(f"Network error: {e}. Retrying in {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise GoogleTasksAPIError(f"Network error after retries: {e}") from e
            except (
                GoogleTasksAuthError,
                GoogleTasksNotFoundError,
                GoogleTasksQuotaExceeded,
                GoogleTasksRateLimitError,
            ):
                raise

        raise GoogleTasksAPIError("Request failed after all retries")

    async def list_task_lists(self, max_results: int = 100) -> TaskListsResponse:
        """List all task lists.

        Args:
            max_results: Maximum results to return (default: 100)

        Returns:
            TaskListsResponse containing task lists and pagination info

        Raises:
            GoogleTasksAPIError: If API request fails
        """
        try:
            data = await self._request(
                "GET", "/users/@me/lists", params={"maxResults": max_results}
            )
            return TaskListsResponse(**data)
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to list task lists: {e}")
            raise GoogleTasksAPIError(f"Failed to list task lists: {e}") from e

    async def create_task_list(self, title: str) -> TaskList:
        """Create a new task list.

        Args:
            title: Title for the new task list

        Returns:
            Created TaskList object

        Raises:
            GoogleTasksAPIError: If API request fails
            GoogleTasksValidationError: If title is invalid
        """
        try:
            task_list = TaskListCreate(title=title)
            data = await self._request(
                "POST",
                "/users/@me/lists",
                json={"title": task_list.title},
            )
            return TaskList(**data)
        except GoogleTasksValidationError:
            raise
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to create task list: {e}")
            raise GoogleTasksAPIError(f"Failed to create task list: {e}") from e

    async def list_tasks(
        self,
        task_list_id: str = "@default",
        max_results: int = 100,
        show_completed: bool = True,
        show_deleted: bool = False,
        show_hidden: bool = False,
    ) -> TasksListResponse:
        """List tasks in a task list.

        Args:
            task_list_id: ID of task list (default: "@default")
            max_results: Maximum results to return (default: 100)
            show_completed: Include completed tasks (default: True)
            show_deleted: Include deleted tasks (default: False)
            show_hidden: Include hidden tasks (default: False)

        Returns:
            TasksListResponse containing tasks and pagination info

        Raises:
            GoogleTasksAPIError: If API request fails
        """
        try:
            params = {
                "maxResults": max_results,
                "showCompleted": show_completed,
                "showDeleted": show_deleted,
                "showHidden": show_hidden,
            }
            data = await self._request(
                "GET",
                f"/lists/{task_list_id}/tasks",
                params=params,
            )
            return TasksListResponse(**data)
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            raise GoogleTasksAPIError(f"Failed to list tasks: {e}") from e

    async def create_task(self, task_list_id: str, task: TaskCreate) -> Task:
        """Create a new task in a task list.

        Args:
            task_list_id: ID of task list
            task: TaskCreate object with task details

        Returns:
            Created Task object

        Raises:
            GoogleTasksAPIError: If API request fails
            GoogleTasksValidationError: If task data is invalid
        """
        try:
            task_data = task.model_dump(exclude_none=True)
            data = await self._request(
                "POST",
                f"/lists/{task_list_id}/tasks",
                json=task_data,
            )
            return Task(**data)
        except GoogleTasksValidationError:
            raise
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise GoogleTasksAPIError(f"Failed to create task: {e}") from e

    async def get_task(self, task_list_id: str, task_id: str) -> Task:
        """Get a specific task.

        Args:
            task_list_id: ID of task list containing the task
            task_id: ID of the task

        Returns:
            Task object

        Raises:
            GoogleTasksAPIError: If API request fails
            GoogleTasksNotFoundError: If task not found
        """
        try:
            data = await self._request("GET", f"/lists/{task_list_id}/tasks/{task_id}")
            return Task(**data)
        except GoogleTasksNotFoundError:
            raise
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            raise GoogleTasksAPIError(f"Failed to get task: {e}") from e

    async def update_task(self, task_list_id: str, task_id: str, task: TaskUpdate) -> Task:
        """Update an existing task.

        Args:
            task_list_id: ID of task list containing the task
            task_id: ID of the task
            task: TaskUpdate object with fields to update

        Returns:
            Updated Task object

        Raises:
            GoogleTasksAPIError: If API request fails
            GoogleTasksValidationError: If task data is invalid
        """
        try:
            task_data = task.model_dump(exclude_none=True)
            data = await self._request(
                "PATCH",
                f"/lists/{task_list_id}/tasks/{task_id}",
                json=task_data,
            )
            return Task(**data)
        except GoogleTasksValidationError:
            raise
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            raise GoogleTasksAPIError(f"Failed to update task: {e}") from e

    async def delete_task(self, task_list_id: str, task_id: str) -> None:
        """Delete a task.

        Args:
            task_list_id: ID of task list containing the task
            task_id: ID of the task to delete

        Raises:
            GoogleTasksAPIError: If API request fails
        """
        try:
            await self._request("DELETE", f"/lists/{task_list_id}/tasks/{task_id}")
            logger.info(f"Deleted task {task_id} from list {task_list_id}")
        except GoogleTasksAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            raise GoogleTasksAPIError(f"Failed to delete task: {e}") from e
