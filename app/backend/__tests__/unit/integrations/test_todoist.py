"""Unit tests for Todoist API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from __tests__.fixtures.todoist_fixtures import (
    SAMPLE_PROJECT,
    SAMPLE_PROJECTS_RESPONSE,
    SAMPLE_SECTION,
    SAMPLE_SECTIONS_RESPONSE,
    SAMPLE_TASK,
    SAMPLE_TASKS_RESPONSE,
)
from src.integrations.todoist import (
    TodoistClient,
    TodoistError,
    TodoistPriority,
    TodoistProject,
    TodoistSection,
    TodoistTask,
)


class TestTodoistClientInitialization:
    """Tests for TodoistClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have correct name."""
        client = TodoistClient(api_key="test-key")
        assert client.name == "todoist"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = TodoistClient(api_key="test-key")
        assert client.base_url == "https://api.todoist.com/rest/v2"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        client = TodoistClient(api_key="my-todoist-key")  # pragma: allowlist secret
        assert client.api_key == "my-todoist-key"  # pragma: allowlist secret

    def test_default_timeout(self) -> None:
        """Client should have default timeout of 30 seconds."""
        client = TodoistClient(api_key="test-key")
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = TodoistClient(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0

    def test_default_max_retries(self) -> None:
        """Client should have default max retries of 3."""
        client = TodoistClient(api_key="test-key")
        assert client.max_retries == 3

    def test_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = TodoistClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5


class TestTodoistClientHeaders:
    """Tests for TodoistClient header handling."""

    def test_uses_bearer_token(self) -> None:
        """Client should use bearer token for authentication."""
        client = TodoistClient(api_key="my-token")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer my-token"  # pragma: allowlist secret

    def test_content_type_json(self) -> None:
        """Headers should include Content-Type: application/json."""
        client = TodoistClient(api_key="test-key")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_accept_json(self) -> None:
        """Headers should include Accept: application/json."""
        client = TodoistClient(api_key="test-key")
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestTodoistClientProjects:
    """Tests for TodoistClient project methods."""

    @pytest.fixture
    def client(self) -> TodoistClient:
        """Create test client instance."""
        return TodoistClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_projects_success(self, client: TodoistClient) -> None:
        """get_projects() should return list of projects on success."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_PROJECTS_RESPONSE

            projects = await client.get_projects()

            assert len(projects) == 2
            assert projects[0].id == "2203306141"
            assert projects[0].name == "Test Project"
            assert projects[1].id == "2203306142"
            assert projects[1].name == "Work Project"
            mock.assert_called_once_with("/projects")

    @pytest.mark.asyncio
    async def test_get_projects_empty(self, client: TodoistClient) -> None:
        """get_projects() should handle empty list."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = []

            projects = await client.get_projects()

            assert projects == []

    @pytest.mark.asyncio
    async def test_get_project_success(self, client: TodoistClient) -> None:
        """get_project() should return single project."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_PROJECT

            project = await client.get_project("2203306141")

            assert project.id == "2203306141"
            assert project.name == "Test Project"
            mock.assert_called_once_with("/projects/2203306141")

    @pytest.mark.asyncio
    async def test_create_project_success(self, client: TodoistClient) -> None:
        """create_project() should return created project."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_PROJECT

            project = await client.create_project(
                name="Test Project",
                color="charcoal",
            )

            assert project.id == "2203306141"
            assert project.name == "Test Project"
            mock.assert_called_once()


class TestTodoistClientTasks:
    """Tests for TodoistClient task methods."""

    @pytest.fixture
    def client(self) -> TodoistClient:
        """Create test client instance."""
        return TodoistClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, client: TodoistClient) -> None:
        """get_tasks() should return list of tasks."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_TASKS_RESPONSE

            tasks = await client.get_tasks(project_id="2203306141")

            assert len(tasks) == 2
            assert tasks[0].id == "4088838091"
            assert tasks[0].content == "Buy groceries"
            assert tasks[1].id == "4088838092"
            assert tasks[1].content == "Write API tests"
            assert tasks[1].priority == 3

    @pytest.mark.asyncio
    async def test_get_tasks_with_filters(self, client: TodoistClient) -> None:
        """get_tasks() should support filtering."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = []

            await client.get_tasks(
                project_id="2203306141",
                label="work",
                filter="priority > 1",
            )

            mock.assert_called_once()
            call_args = mock.call_args
            assert call_args[1]["params"]["project_id"] == "2203306141"
            assert call_args[1]["params"]["label"] == "work"
            assert call_args[1]["params"]["filter"] == "priority > 1"

    @pytest.mark.asyncio
    async def test_get_task_success(self, client: TodoistClient) -> None:
        """get_task() should return single task."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_TASK

            task = await client.get_task("4088838091")

            assert task.id == "4088838091"
            assert task.content == "Buy groceries"
            assert task.priority == 1
            assert task.is_completed is False
            assert "shopping" in task.labels
            mock.assert_called_once_with("/tasks/4088838091")

    @pytest.mark.asyncio
    async def test_create_task_success(self, client: TodoistClient) -> None:
        """create_task() should return created task."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_TASK

            task = await client.create_task(
                content="Buy groceries",
                project_id="2203306141",
                priority=1,
                due_string="2025-01-01",
                labels=["shopping", "home"],
            )

            assert task.id == "4088838091"
            assert task.content == "Buy groceries"
            assert task.priority == 1
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_duration(self, client: TodoistClient) -> None:
        """create_task() should support duration parameter."""
        task_response = SAMPLE_TASK.copy()
        task_response["duration"] = {"amount": 60, "unit": "minute"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = task_response

            task = await client.create_task(
                content="Write API tests",
                duration_minutes=60,
            )

            assert task.duration_minutes == 60

    @pytest.mark.asyncio
    async def test_update_task_success(self, client: TodoistClient) -> None:
        """update_task() should return updated task."""
        updated_task = SAMPLE_TASK.copy()
        updated_task["priority"] = 3
        updated_task["content"] = "Buy groceries (URGENT)"

        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = updated_task

            task = await client.update_task(
                task_id="4088838091",
                priority=3,
                content="Buy groceries (URGENT)",
            )

            assert task.priority == 3
            assert task.content == "Buy groceries (URGENT)"

    @pytest.mark.asyncio
    async def test_close_task_success(self, client: TodoistClient) -> None:
        """close_task() should mark task as completed."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await client.close_task("4088838091")

            assert result is True
            mock.assert_called_once_with("/tasks/4088838091/close")

    @pytest.mark.asyncio
    async def test_reopen_task_success(self, client: TodoistClient) -> None:
        """reopen_task() should reopen a completed task."""
        with (
            patch.object(client, "post", new_callable=AsyncMock) as mock_post,
            patch.object(client, "get_task", new_callable=AsyncMock) as mock_get,
        ):
            reopened_task = SAMPLE_TASK.copy()
            reopened_task["is_completed"] = False
            mock_post.return_value = None
            mock_get.return_value = TodoistTask(
                id=reopened_task["id"],
                content=reopened_task["content"],
                is_completed=reopened_task["is_completed"],
            )

            task = await client.reopen_task("4088838091")

            assert task.is_completed is False
            mock_post.assert_called_once_with("/tasks/4088838091/reopen")

    @pytest.mark.asyncio
    async def test_delete_task_success(self, client: TodoistClient) -> None:
        """delete_task() should delete a task."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await client.delete_task("4088838091")

            assert result is True
            mock.assert_called_once_with("/tasks/4088838091")


class TestTodoistClientSections:
    """Tests for TodoistClient section methods."""

    @pytest.fixture
    def client(self) -> TodoistClient:
        """Create test client instance."""
        return TodoistClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_sections_success(self, client: TodoistClient) -> None:
        """get_sections() should return list of sections."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_SECTIONS_RESPONSE

            sections = await client.get_sections("2203306141")

            assert len(sections) == 3
            assert sections[0].id == "123456"
            assert sections[0].name == "Backlog"
            assert sections[1].name == "In Progress"
            assert sections[2].name == "Done"
            mock.assert_called_once_with("/projects/2203306141/sections")

    @pytest.mark.asyncio
    async def test_create_section_success(self, client: TodoistClient) -> None:
        """create_section() should return created section."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = SAMPLE_SECTION

            section = await client.create_section(
                name="Backlog",
                project_id="2203306141",
            )

            assert section.id == "123456"
            assert section.name == "Backlog"
            assert section.project_id == "2203306141"
            mock.assert_called_once()


class TestTodoistClientErrors:
    """Tests for TodoistClient error handling."""

    @pytest.fixture
    def client(self) -> TodoistClient:
        """Create test client instance."""
        return TodoistClient(api_key="test-api-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_projects_raises_on_error(self, client: TodoistClient) -> None:
        """get_projects() should raise TodoistError on API error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API error")

            with pytest.raises(TodoistError):
                await client.get_projects()

    @pytest.mark.asyncio
    async def test_get_task_raises_on_error(self, client: TodoistClient) -> None:
        """get_task() should raise TodoistError on API error."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Task not found")

            with pytest.raises(TodoistError):
                await client.get_task("invalid-id")

    @pytest.mark.asyncio
    async def test_create_task_raises_on_error(self, client: TodoistClient) -> None:
        """create_task() should raise TodoistError on API error."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Invalid parameters")

            with pytest.raises(TodoistError):
                await client.create_task(content="Test")

    @pytest.mark.asyncio
    async def test_close_task_raises_on_error(self, client: TodoistClient) -> None:
        """close_task() should raise TodoistError on API error."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Task not found")

            with pytest.raises(TodoistError):
                await client.close_task("invalid-id")


class TestTodoistPriority:
    """Tests for TodoistPriority enum."""

    def test_priority_values(self) -> None:
        """Priority enum should have correct values."""
        assert TodoistPriority.LOW == 1
        assert TodoistPriority.NORMAL == 2
        assert TodoistPriority.HIGH == 3
        assert TodoistPriority.URGENT == 4

    def test_priority_int_conversion(self) -> None:
        """Priority enum should convert to int."""
        assert int(TodoistPriority.URGENT) == 4
        assert int(TodoistPriority.LOW) == 1


class TestTodoistDataclasses:
    """Tests for Todoist data classes."""

    def test_task_dataclass(self) -> None:
        """TodoistTask dataclass should parse correctly."""
        task = TodoistTask(
            id="123",
            content="Test task",
            priority=2,
            is_completed=False,
        )

        assert task.id == "123"
        assert task.content == "Test task"
        assert task.priority == 2
        assert task.is_completed is False

    def test_project_dataclass(self) -> None:
        """TodoistProject dataclass should parse correctly."""
        project = TodoistProject(
            id="456",
            name="Test Project",
            color="blue",
        )

        assert project.id == "456"
        assert project.name == "Test Project"
        assert project.color == "blue"

    def test_section_dataclass(self) -> None:
        """TodoistSection dataclass should parse correctly."""
        section = TodoistSection(
            id="789",
            name="Test Section",
            project_id="456",
        )

        assert section.id == "789"
        assert section.name == "Test Section"
        assert section.project_id == "456"
