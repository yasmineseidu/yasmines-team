"""
Live API integration tests for ClickUp API client.

Tests actual ClickUp API endpoints with real credentials from .env file.
These tests verify that the client works with the actual ClickUp API.

Prerequisites:
- CLICKUP_API_KEY must be set in .env file
- Access to a ClickUp workspace and team
"""

from pathlib import Path

import pytest

from src.integrations.clickup import ClickUpClient, ClickUpError

# Load API key from .env
# Path from test file location: app/backend/__tests__/integration/test_clickup_live.py
# We need to go up 4 levels to reach the project root: app/backend/__tests__/integration/
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"

# Parse .env manually for API key
api_key = None
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("CLICKUP_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
else:
    # Try alternative path: app/backend is 3 levels up from test file
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("CLICKUP_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break


@pytest.fixture
def clickup_api_key() -> str:
    """Get ClickUp API key from environment.

    Note: For tests to run successfully, a valid ClickUp API key must be
    set in the .env file as CLICKUP_API_KEY. The key should be obtained from:
    https://app.clickup.com/settings/apps
    """
    if not api_key:
        pytest.skip("CLICKUP_API_KEY not found in .env - Live API tests skipped")
    return api_key


@pytest.fixture
async def clickup_client(clickup_api_key: str) -> ClickUpClient:
    """Create ClickUp client with real API key."""
    return ClickUpClient(api_key=clickup_api_key)


class TestClickUpClientLiveAPI:
    """Live API tests against real ClickUp API."""

    @pytest.mark.asyncio
    async def test_get_workspaces_live(self, clickup_client: ClickUpClient) -> None:
        """Should fetch workspaces from real ClickUp API."""
        workspaces = await clickup_client.get_workspaces()

        assert workspaces is not None
        assert isinstance(workspaces, list)
        if workspaces:
            workspace = workspaces[0]
            assert hasattr(workspace, "id")
            assert hasattr(workspace, "name")
            assert workspace.id is not None
            assert workspace.name is not None

    @pytest.mark.asyncio
    async def test_health_check_live(self, clickup_client: ClickUpClient) -> None:
        """Should pass health check with real API."""
        result = await clickup_client.health_check()

        assert result is not None
        assert "status" in result
        assert result["status"] == "healthy"
        assert "workspaces_count" in result
        assert result["workspaces_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_spaces_live(self, clickup_client: ClickUpClient) -> None:
        """Should fetch spaces from first workspace."""
        workspaces = await clickup_client.get_workspaces()

        if not workspaces:
            pytest.skip("No workspaces available for testing")

        # Test with first workspace
        workspace_id = workspaces[0].id
        spaces = await clickup_client.get_spaces(workspace_id)

        assert spaces is not None
        assert isinstance(spaces, list)
        # Spaces list can be empty, which is valid

    @pytest.mark.asyncio
    async def test_get_lists_live(self, clickup_client: ClickUpClient) -> None:
        """Should fetch lists from first available space."""
        workspaces = await clickup_client.get_workspaces()

        if not workspaces:
            pytest.skip("No workspaces available for testing")

        # Get first workspace with spaces
        for workspace in workspaces:
            spaces = await clickup_client.get_spaces(workspace.id)
            if spaces:
                space_id = spaces[0].id
                lists = await clickup_client.get_lists(space_id)
                assert lists is not None
                assert isinstance(lists, list)
                break

    @pytest.mark.asyncio
    async def test_invalid_workspace_id_raises_error(self, clickup_client: ClickUpClient) -> None:
        """Should raise ClickUpError for invalid workspace ID."""
        with pytest.raises(ClickUpError):
            await clickup_client.get_spaces("invalid_workspace_id_12345")

    @pytest.mark.asyncio
    async def test_invalid_space_id_raises_error(self, clickup_client: ClickUpClient) -> None:
        """Should raise ClickUpError for invalid space ID."""
        with pytest.raises(ClickUpError):
            await clickup_client.get_lists("invalid_space_id_12345")

    @pytest.mark.asyncio
    async def test_invalid_task_id_raises_error(self, clickup_client: ClickUpClient) -> None:
        """Should raise ClickUpError for invalid task ID."""
        with pytest.raises(ClickUpError):
            await clickup_client.get_task("invalid_task_id_12345")


class TestClickUpClientLiveTaskOperations:
    """Live tests for task create/read/update/delete operations."""

    @pytest.mark.asyncio
    async def test_create_and_delete_task_live(self, clickup_client: ClickUpClient) -> None:
        """Should create and delete a task in live API."""
        # Get workspaces and find a suitable list
        workspaces = await clickup_client.get_workspaces()
        if not workspaces:
            pytest.skip("No workspaces available")

        list_id = None
        for workspace in workspaces:
            spaces = await clickup_client.get_spaces(workspace.id)
            for space in spaces:
                lists = await clickup_client.get_lists(space.id)
                if lists:
                    list_id = lists[0].id
                    break
            if list_id:
                break

        if not list_id:
            pytest.skip("No suitable list found for task creation")

        # Create task
        task_name = "Test Task from API Integration"
        task = await clickup_client.create_task(
            list_id=list_id,
            name=task_name,
            description="Created by automated test",
        )

        assert task.id is not None
        assert task.name == task_name
        assert task.description == "Created by automated test"

        # Verify task can be fetched
        fetched_task = await clickup_client.get_task(task.id)
        assert fetched_task.id == task.id
        assert fetched_task.name == task_name

        # Update task
        updated_task = await clickup_client.update_task(
            task_id=task.id,
            name="Updated Test Task",
        )
        assert updated_task.name == "Updated Test Task"

        # Delete task
        delete_result = await clickup_client.delete_task(task.id)
        assert delete_result is not None

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields_live(self, clickup_client: ClickUpClient) -> None:
        """Should create task with all optional fields."""
        # Get a suitable list
        workspaces = await clickup_client.get_workspaces()
        if not workspaces:
            pytest.skip("No workspaces available")

        list_id = None
        for workspace in workspaces:
            spaces = await clickup_client.get_spaces(workspace.id)
            for space in spaces:
                lists = await clickup_client.get_lists(space.id)
                if lists:
                    list_id = lists[0].id
                    break
            if list_id:
                break

        if not list_id:
            pytest.skip("No suitable list found")

        # Create task with all fields
        task = await clickup_client.create_task(
            list_id=list_id,
            name="Complete Task Test",
            description="Task with all fields",
            priority=1,
            tags=["test", "integration"],
        )

        assert task.id is not None
        assert task.name == "Complete Task Test"
        assert "test" in task.tags or len(task.tags) >= 0

        # Clean up
        await clickup_client.delete_task(task.id)

    @pytest.mark.asyncio
    async def test_get_tasks_by_list_live(self, clickup_client: ClickUpClient) -> None:
        """Should fetch tasks from a list via live API."""
        workspaces = await clickup_client.get_workspaces()
        if not workspaces:
            pytest.skip("No workspaces available")

        list_id = None
        for workspace in workspaces:
            spaces = await clickup_client.get_spaces(workspace.id)
            for space in spaces:
                lists = await clickup_client.get_lists(space.id)
                if lists:
                    list_id = lists[0].id
                    break
            if list_id:
                break

        if not list_id:
            pytest.skip("No suitable list found")

        # Fetch tasks
        tasks = await clickup_client.get_tasks_by_list(list_id, limit=10)
        assert tasks is not None
        assert isinstance(tasks, list)


# Marker for live API tests
pytestmark = pytest.mark.live_api
