"""Unit tests for ClickUp API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.clickup import (
    ClickUpClient,
    ClickUpError,
    ClickUpWorkspace,
)


class TestClickUpClientInitialization:
    """Tests for ClickUp client initialization."""

    def test_initialization_with_valid_api_key(self) -> None:
        """Client should initialize with valid API key."""
        client = ClickUpClient(api_key="pk_test_api_key_123")  # pragma: allowlist secret
        assert client.api_key == "pk_test_api_key_123"  # pragma: allowlist secret
        assert client.name == "clickup"
        assert client.base_url == "https://api.clickup.com/api/v2"

    def test_initialization_with_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = ClickUpClient(api_key="pk_test_key", timeout=60.0)  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_initialization_raises_on_empty_api_key(self) -> None:
        """Client should raise ValueError for empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ClickUpClient(api_key="")

    def test_initialization_raises_on_whitespace_api_key(self) -> None:
        """Client should raise ValueError for whitespace-only API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ClickUpClient(api_key="   ")

    def test_initialization_strips_whitespace(self) -> None:
        """Client should strip whitespace from API key."""
        client = ClickUpClient(api_key="  pk_test_key  ")  # pragma: allowlist secret
        assert client.api_key == "pk_test_key"  # pragma: allowlist secret


class TestClickUpClientHeaders:
    """Tests for HTTP headers generation."""

    def test_headers_include_authorization(self) -> None:
        """Headers should include Authorization header with API key."""
        client = ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret
        headers = client._get_headers()

        assert headers["Authorization"] == "pk_test_key"  # pragma: allowlist secret
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestClickUpClientGetWorkspaces:
    """Tests for get_workspaces method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_workspaces_success(self, client: ClickUpClient) -> None:
        """Should fetch and parse workspaces successfully."""
        mock_response = {
            "teams": [
                {
                    "id": 12345,
                    "name": "Test Workspace",
                    "color": "#FF00FF",
                    "avatar": "https://example.com/avatar.png",
                },
                {
                    "id": 67890,
                    "name": "Another Workspace",
                    "color": "#00FF00",
                    "avatar": None,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            workspaces = await client.get_workspaces()

            assert len(workspaces) == 2
            assert workspaces[0].id == "12345"
            assert workspaces[0].name == "Test Workspace"
            assert workspaces[0].color == "#FF00FF"
            assert workspaces[1].id == "67890"
            assert workspaces[1].name == "Another Workspace"
            mock_get.assert_called_once_with("/team")

    @pytest.mark.asyncio
    async def test_get_workspaces_empty_response(self, client: ClickUpClient) -> None:
        """Should handle empty workspaces list."""
        mock_response = {"teams": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            workspaces = await client.get_workspaces()

            assert workspaces == []

    @pytest.mark.asyncio
    async def test_get_workspaces_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.get_workspaces()


class TestClickUpClientGetSpaces:
    """Tests for get_spaces method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_spaces_success(self, client: ClickUpClient) -> None:
        """Should fetch and parse spaces successfully."""
        mock_response = {
            "spaces": [
                {
                    "id": 111,
                    "name": "Space 1",
                    "color": "#FF0000",
                    "private": False,
                    "avatar": "https://example.com/space1.png",
                },
                {
                    "id": 222,
                    "name": "Space 2",
                    "color": "#0000FF",
                    "private": True,
                    "avatar": None,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            spaces = await client.get_spaces("12345")

            assert len(spaces) == 2
            assert spaces[0].id == "111"
            assert spaces[0].name == "Space 1"
            assert spaces[0].private is False
            assert spaces[1].id == "222"
            assert spaces[1].private is True
            mock_get.assert_called_once_with("/team/12345/space")

    @pytest.mark.asyncio
    async def test_get_spaces_raises_on_empty_workspace_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty workspace ID."""
        with pytest.raises(ValueError, match="Workspace ID cannot be empty"):
            await client.get_spaces("")

    @pytest.mark.asyncio
    async def test_get_spaces_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.get_spaces("12345")


class TestClickUpClientGetLists:
    """Tests for get_lists method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_lists_success(self, client: ClickUpClient) -> None:
        """Should fetch and parse lists successfully."""
        mock_response = {
            "lists": [
                {
                    "id": "list_1",
                    "name": "To Do",
                    "folder": {"id": 100},
                    "space": {"id": 111},
                    "color": "#FF00FF",
                    "private": False,
                },
                {
                    "id": "list_2",
                    "name": "In Progress",
                    "folder": None,
                    "space": {"id": 111},
                    "color": "#00FF00",
                    "private": True,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            lists = await client.get_lists("111")

            assert len(lists) == 2
            assert lists[0].id == "list_1"
            assert lists[0].name == "To Do"
            assert lists[0].folder_id == "100"
            assert lists[0].space_id == "111"
            assert lists[1].folder_id is None
            mock_get.assert_called_once_with("/space/111/list")

    @pytest.mark.asyncio
    async def test_get_lists_raises_on_empty_space_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty space ID."""
        with pytest.raises(ValueError, match="Space ID cannot be empty"):
            await client.get_lists("")

    @pytest.mark.asyncio
    async def test_get_lists_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.get_lists("111")


class TestClickUpClientCreateTask:
    """Tests for create_task method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_create_task_success(self, client: ClickUpClient) -> None:
        """Should create a task successfully."""
        mock_response = {
            "id": "task_123",
            "custom_id": None,
            "name": "New Task",
            "description": "Task description",
            "status": {"status": "open"},
            "priority": {"priority": 2},
            "due_date": 1704067200000,
            "start_date": 1703980800000,
            "assignees": [{"id": 1, "username": "user1"}],
            "tags": [{"name": "urgent"}],
            "list": {"id": "list_1"},
            "folder": {"id": "folder_1"},
            "space": {"id": "111"},
            "date_created": 1703980800000,
            "date_updated": 1703980800000,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            task = await client.create_task(
                list_id="list_1",
                name="New Task",
                description="Task description",
                priority=2,
            )

            assert task.id == "task_123"
            assert task.name == "New Task"
            assert task.description == "Task description"
            assert task.status == "open"
            assert task.priority == 2
            assert "urgent" in task.tags
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_raises_on_empty_list_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty list ID."""
        with pytest.raises(ValueError, match="List ID cannot be empty"):
            await client.create_task(list_id="", name="Task")

    @pytest.mark.asyncio
    async def test_create_task_raises_on_empty_name(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty task name."""
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            await client.create_task(list_id="list_1", name="")

    @pytest.mark.asyncio
    async def test_create_task_with_all_optional_params(self, client: ClickUpClient) -> None:
        """Should create task with all optional parameters."""
        mock_response = {
            "id": "task_456",
            "custom_id": None,
            "name": "Full Task",
            "description": "Complete description",
            "status": {"status": "open"},
            "priority": {"priority": 1},
            "due_date": 1704067200000,
            "start_date": 1703980800000,
            "assignees": [{"id": 1, "username": "user1"}, {"id": 2, "username": "user2"}],
            "tags": [{"name": "feature"}, {"name": "backend"}],
            "list": {"id": "list_1"},
            "folder": None,
            "space": {"id": "111"},
            "date_created": 1703980800000,
            "date_updated": 1703980800000,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            task = await client.create_task(
                list_id="list_1",
                name="Full Task",
                description="Complete description",
                priority=1,
                due_date=1704067200000,
                start_date=1703980800000,
                assignee_ids=[1, 2],
                tags=["feature", "backend"],
            )

            assert task.id == "task_456"
            assert len(task.assignees) == 2
            assert len(task.tags) == 2
            assert "feature" in task.tags

    @pytest.mark.asyncio
    async def test_create_task_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.create_task(list_id="list_1", name="Task")


class TestClickUpClientGetTask:
    """Tests for get_task method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_task_success(self, client: ClickUpClient) -> None:
        """Should fetch a task successfully."""
        mock_response = {
            "id": "task_123",
            "custom_id": "CUSTOM-123",
            "name": "Test Task",
            "description": "Test description",
            "status": {"status": "in_progress"},
            "priority": {"priority": 1},
            "due_date": 1704067200000,
            "start_date": 1703980800000,
            "assignees": [{"id": 1, "username": "user1"}],
            "tags": [{"name": "bug"}],
            "list": {"id": "list_1"},
            "folder": {"id": "folder_1"},
            "space": {"id": "111"},
            "date_created": 1703980800000,
            "date_updated": 1703980800000,
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            task = await client.get_task("task_123")

            assert task.id == "task_123"
            assert task.custom_id == "CUSTOM-123"
            assert task.name == "Test Task"
            assert task.status == "in_progress"
            mock_get.assert_called_once_with("/task/task_123")

    @pytest.mark.asyncio
    async def test_get_task_raises_on_empty_task_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty task ID."""
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            await client.get_task("")

    @pytest.mark.asyncio
    async def test_get_task_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.get_task("task_123")


class TestClickUpClientUpdateTask:
    """Tests for update_task method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_update_task_success(self, client: ClickUpClient) -> None:
        """Should update a task successfully."""
        mock_response = {
            "id": "task_123",
            "custom_id": None,
            "name": "Updated Task",
            "description": "Updated description",
            "status": {"status": "closed"},
            "priority": {"priority": 3},
            "due_date": 1704067200000,
            "start_date": 1703980800000,
            "assignees": [],
            "tags": [],
            "list": {"id": "list_1"},
            "folder": None,
            "space": {"id": "111"},
            "date_created": 1703980800000,
            "date_updated": 1704000000000,
        }

        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response
            task = await client.update_task(
                task_id="task_123", name="Updated Task", status="closed"
            )

            assert task.id == "task_123"
            assert task.name == "Updated Task"
            assert task.status == "closed"
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_raises_on_empty_task_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty task ID."""
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            await client.update_task(task_id="", name="Updated")

    @pytest.mark.asyncio
    async def test_update_task_with_all_fields(self, client: ClickUpClient) -> None:
        """Should update task with all fields."""
        mock_response = {
            "id": "task_123",
            "custom_id": None,
            "name": "Fully Updated Task",
            "description": "New description",
            "status": {"status": "in_progress"},
            "priority": {"priority": 1},
            "due_date": 1704153600000,
            "start_date": 1704067200000,
            "assignees": [],
            "tags": [],
            "list": {"id": "list_1"},
            "folder": None,
            "space": {"id": "111"},
            "date_created": 1703980800000,
            "date_updated": 1704000000000,
        }

        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response
            task = await client.update_task(
                task_id="task_123",
                name="Fully Updated Task",
                description="New description",
                status="in_progress",
                priority=1,
                due_date=1704153600000,
            )

            assert task.id == "task_123"
            assert task.name == "Fully Updated Task"
            assert task.description == "New description"
            assert task.status == "in_progress"
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.update_task(task_id="task_123", name="Updated")


class TestClickUpClientDeleteTask:
    """Tests for delete_task method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_delete_task_success(self, client: ClickUpClient) -> None:
        """Should delete a task successfully."""
        mock_response = {"success": True}

        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response
            response = await client.delete_task("task_123")

            assert response["success"] is True
            mock_delete.assert_called_once_with("/task/task_123")

    @pytest.mark.asyncio
    async def test_delete_task_raises_on_empty_task_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty task ID."""
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            await client.delete_task("")

    @pytest.mark.asyncio
    async def test_delete_task_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.delete_task("task_123")


class TestClickUpClientGetTasksByList:
    """Tests for get_tasks_by_list method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_tasks_by_list_success(self, client: ClickUpClient) -> None:
        """Should fetch tasks from a list successfully."""
        mock_response = {
            "tasks": [
                {
                    "id": "task_1",
                    "custom_id": None,
                    "name": "Task 1",
                    "description": None,
                    "status": {"status": "open"},
                    "priority": None,
                    "due_date": None,
                    "start_date": None,
                    "assignees": [],
                    "tags": [],
                    "list": {"id": "list_1"},
                    "folder": None,
                    "space": {"id": "111"},
                    "date_created": 1703980800000,
                    "date_updated": 1703980800000,
                },
                {
                    "id": "task_2",
                    "custom_id": None,
                    "name": "Task 2",
                    "description": None,
                    "status": {"status": "closed"},
                    "priority": None,
                    "due_date": None,
                    "start_date": None,
                    "assignees": [],
                    "tags": [],
                    "list": {"id": "list_1"},
                    "folder": None,
                    "space": {"id": "111"},
                    "date_created": 1703980800000,
                    "date_updated": 1703980800000,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            tasks = await client.get_tasks_by_list("list_1")

            assert len(tasks) == 2
            assert tasks[0].id == "task_1"
            assert tasks[0].name == "Task 1"
            assert tasks[1].id == "task_2"
            assert tasks[1].status == "closed"
            mock_get.assert_called_once_with("/list/list_1/task", params={"limit": 100})

    @pytest.mark.asyncio
    async def test_get_tasks_by_list_with_custom_limit(self, client: ClickUpClient) -> None:
        """Should fetch tasks with custom limit."""
        mock_response = {"tasks": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get_tasks_by_list("list_1", limit=50)

            mock_get.assert_called_once_with("/list/list_1/task", params={"limit": 50})

    @pytest.mark.asyncio
    async def test_get_tasks_by_list_raises_on_empty_list_id(self, client: ClickUpClient) -> None:
        """Should raise ValueError for empty list ID."""
        with pytest.raises(ValueError, match="List ID cannot be empty"):
            await client.get_tasks_by_list("")

    @pytest.mark.asyncio
    async def test_get_tasks_by_list_raises_on_error(self, client: ClickUpClient) -> None:
        """Should raise ClickUpError on API failure."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")
            with pytest.raises(ClickUpError):
                await client.get_tasks_by_list("list_1")


class TestClickUpClientHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def client(self) -> ClickUpClient:
        """Create a ClickUp client for testing."""
        return ClickUpClient(api_key="pk_test_key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: ClickUpClient) -> None:
        """Health check should return successful status."""
        workspaces = [
            ClickUpWorkspace(id="1", name="Workspace 1"),
            ClickUpWorkspace(id="2", name="Workspace 2"),
        ]

        with patch.object(client, "get_workspaces", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = workspaces
            response = await client.health_check()

            assert response["status"] == "healthy"
            assert response["workspaces_count"] == 2

    @pytest.mark.asyncio
    async def test_health_check_raises_on_error(self, client: ClickUpClient) -> None:
        """Health check should raise ClickUpError on failure."""
        with patch.object(client, "get_workspaces", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.side_effect = Exception("Connection failed")
            with pytest.raises(ClickUpError):
                await client.health_check()
