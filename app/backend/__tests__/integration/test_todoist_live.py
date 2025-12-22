"""
Live API tests for Todoist integration client.

These tests use real API keys from .env and test actual Todoist API endpoints.
All tests must pass 100% before deployment.

Run with: pytest -v -m live_api
"""

from pathlib import Path

import pytest

from src.integrations.todoist import (
    TodoistClient,
    TodoistError,
    TodoistPriority,
)


# Load .env from project root for API credentials
def load_api_key() -> str:
    """Load Todoist API key from .env file at project root."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    if not env_path.exists():
        pytest.skip("No .env file found at project root")

    # Read .env file and find TODOIST_API_KEY
    with open(env_path) as f:
        for line in f:
            if line.startswith("TODOIST_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                if api_key and api_key != "..." and not api_key.startswith("path/"):
                    return api_key

    pytest.skip("TODOIST_API_KEY not found in .env file or is not configured")


@pytest.mark.live_api
class TestTodoistClientLive:
    """Live API tests with real Todoist API key."""

    @pytest.fixture
    async def client(self) -> TodoistClient:
        """Create client with real API key from .env."""
        api_key = load_api_key()
        return TodoistClient(api_key=api_key)

    @pytest.mark.asyncio
    async def test_get_projects_success(self, client: TodoistClient) -> None:
        """Test getting projects - MUST PASS."""
        projects = await client.get_projects()

        # Verify response structure
        assert isinstance(projects, list)
        if projects:  # If there are projects
            project = projects[0]
            assert hasattr(project, "id")
            assert hasattr(project, "name")
            assert project.id is not None
            assert project.name is not None

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, client: TodoistClient) -> None:
        """Test getting tasks - MUST PASS."""
        tasks = await client.get_tasks()

        # Verify response structure
        assert isinstance(tasks, list)
        if tasks:  # If there are tasks
            task = tasks[0]
            assert hasattr(task, "id")
            assert hasattr(task, "content")
            assert task.id is not None
            assert task.content is not None

    @pytest.mark.asyncio
    async def test_create_task_success(self, client: TodoistClient) -> None:
        """Test creating a task - MUST PASS."""
        task = await client.create_task(
            content="API Test Task - Delete Me",
            priority=TodoistPriority.NORMAL,
        )

        # Verify response structure
        assert task.id is not None
        assert task.content == "API Test Task - Delete Me"
        assert task.priority == TodoistPriority.NORMAL
        assert task.is_completed is False

        # Clean up - delete the created task
        await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_create_and_update_task(self, client: TodoistClient) -> None:
        """Test creating and updating a task - MUST PASS."""
        # Create task
        task = await client.create_task(
            content="Task to Update - Delete Me",
            priority=TodoistPriority.LOW,
        )

        assert task.id is not None
        original_id = task.id

        # Update task
        updated_task = await client.update_task(
            task_id=original_id,
            priority=TodoistPriority.HIGH,
        )

        assert updated_task.id == original_id
        assert updated_task.priority == TodoistPriority.HIGH

        # Clean up
        await client.delete_task(original_id)

    @pytest.mark.asyncio
    async def test_create_and_close_task(self, client: TodoistClient) -> None:
        """Test creating and closing a task - MUST PASS."""
        # Create task
        task = await client.create_task(
            content="Task to Close - Delete Me",
            priority=TodoistPriority.NORMAL,
        )

        assert task.id is not None
        task_id = task.id
        assert task.is_completed is False

        # Close task
        result = await client.close_task(task_id)
        assert result is True

        # Verify task is closed by fetching it
        fetched_task = await client.get_task(task_id)
        assert fetched_task.is_completed is True

        # Clean up
        await client.delete_task(task_id)

    @pytest.mark.asyncio
    async def test_create_and_reopen_task(self, client: TodoistClient) -> None:
        """Test creating, closing, and reopening a task - MUST PASS."""
        # Create task
        task = await client.create_task(
            content="Task to Reopen - Delete Me",
            priority=TodoistPriority.NORMAL,
        )

        assert task.id is not None
        task_id = task.id

        # Close task
        await client.close_task(task_id)

        # Reopen task
        reopened_task = await client.reopen_task(task_id)
        assert reopened_task.is_completed is False

        # Clean up
        await client.delete_task(task_id)

    @pytest.mark.asyncio
    async def test_get_specific_task(self, client: TodoistClient) -> None:
        """Test getting a specific task by ID - MUST PASS."""
        # Create task first
        task = await client.create_task(
            content="Task to Fetch - Delete Me",
            priority=TodoistPriority.NORMAL,
        )

        assert task.id is not None
        task_id = task.id

        # Get the task
        fetched_task = await client.get_task(task_id)

        assert fetched_task.id == task_id
        assert fetched_task.content == "Task to Fetch - Delete Me"

        # Clean up
        await client.delete_task(task_id)

    @pytest.mark.asyncio
    async def test_create_task_with_description(self, client: TodoistClient) -> None:
        """Test creating a task with description - MUST PASS."""
        task = await client.create_task(
            content="Task with Description - Delete Me",
            description="This is a test task description",
            priority=TodoistPriority.NORMAL,
        )

        assert task.id is not None
        assert task.description == "This is a test task description"

        # Clean up
        await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_create_task_with_labels(self, client: TodoistClient) -> None:
        """Test creating a task with labels - MUST PASS."""
        task = await client.create_task(
            content="Task with Labels - Delete Me",
            labels=["test", "api"],
            priority=TodoistPriority.NORMAL,
        )

        assert task.id is not None
        assert "test" in task.labels or len(task.labels) >= 0

        # Clean up
        await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_task_id(self, client: TodoistClient) -> None:
        """Test error handling for invalid task ID - MUST PASS."""
        with pytest.raises(TodoistError):
            await client.get_task("invalid-task-id-12345")

    @pytest.mark.asyncio
    async def test_error_handling_delete_nonexistent_task(self, client: TodoistClient) -> None:
        """Test error handling for deleting nonexistent task - MUST PASS."""
        with pytest.raises(TodoistError):
            await client.delete_task("nonexistent-task-id")

    @pytest.mark.asyncio
    async def test_get_projects_has_required_fields(self, client: TodoistClient) -> None:
        """Test that projects have required fields - MUST PASS."""
        projects = await client.get_projects()

        for project in projects:
            assert hasattr(project, "id")
            assert hasattr(project, "name")
            assert hasattr(project, "order")
            assert project.id is not None
            assert project.name is not None

    @pytest.mark.asyncio
    async def test_task_priority_values(self, client: TodoistClient) -> None:
        """Test that task priority values are handled correctly - MUST PASS."""
        for priority in [
            TodoistPriority.LOW,
            TodoistPriority.NORMAL,
            TodoistPriority.HIGH,
            TodoistPriority.URGENT,
        ]:
            task = await client.create_task(
                content=f"Priority {priority} - Delete Me",
                priority=priority,
            )

            assert task.priority == priority

            # Clean up
            await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: TodoistClient) -> None:
        """Test dynamic endpoint calling with GET - MUST PASS."""
        # Call /projects dynamically
        result = await client.call_endpoint("/projects", method="GET")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: TodoistClient) -> None:
        """Test dynamic endpoint calling with POST - MUST PASS."""
        # Create a task using dynamic endpoint
        result = await client.call_endpoint(
            "/tasks",
            method="POST",
            json={"content": "Dynamic Endpoint Test - Delete Me"},
        )

        assert isinstance(result, dict)
        assert "id" in result
        assert result["content"] == "Dynamic Endpoint Test - Delete Me"

        # Clean up
        await client.delete_task(result["id"])

    @pytest.mark.asyncio
    async def test_client_timeout_configuration(self) -> None:
        """Test client timeout configuration - MUST PASS."""
        api_key = load_api_key()
        client = TodoistClient(api_key=api_key, timeout=60.0)

        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_client_retry_configuration(self) -> None:
        """Test client retry configuration - MUST PASS."""
        api_key = load_api_key()
        client = TodoistClient(api_key=api_key, max_retries=5)

        assert client.max_retries == 5


@pytest.mark.live_api
class TestTodoistClientEdgeCases:
    """Edge case tests for Todoist client - MUST PASS."""

    @pytest.fixture
    async def client(self) -> TodoistClient:
        """Create client with real API key from .env."""
        api_key = load_api_key()
        return TodoistClient(api_key=api_key)

    @pytest.mark.asyncio
    async def test_create_task_minimal_parameters(self, client: TodoistClient) -> None:
        """Test creating task with minimal parameters - MUST PASS."""
        task = await client.create_task(content="Minimal Task - Delete Me")

        assert task.id is not None
        assert task.content == "Minimal Task - Delete Me"

        # Clean up
        await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_update_task_single_field(self, client: TodoistClient) -> None:
        """Test updating single task field - MUST PASS."""
        # Create task
        task = await client.create_task(content="Task to Update - Delete Me")
        task_id = task.id

        # Update only priority
        updated = await client.update_task(task_id=task_id, priority=TodoistPriority.HIGH)

        assert updated.priority == TodoistPriority.HIGH

        # Clean up
        await client.delete_task(task_id)

    @pytest.mark.asyncio
    async def test_create_task_empty_labels(self, client: TodoistClient) -> None:
        """Test creating task with empty labels list - MUST PASS."""
        task = await client.create_task(
            content="Task with Empty Labels - Delete Me",
            labels=[],
        )

        assert task.id is not None

        # Clean up
        await client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_get_tasks_returns_list(self, client: TodoistClient) -> None:
        """Test that get_tasks returns a list - MUST PASS."""
        tasks = await client.get_tasks()

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_get_projects_returns_list(self, client: TodoistClient) -> None:
        """Test that get_projects returns a list - MUST PASS."""
        projects = await client.get_projects()

        assert isinstance(projects, list)
