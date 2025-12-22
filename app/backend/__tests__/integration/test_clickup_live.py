"""Live API tests for ClickUp integration - test with real API keys."""

import os
from pathlib import Path

import pytest

from src.integrations.clickup import ClickUpClient, ClickUpError


@pytest.fixture
def api_key() -> str:
    """Load ClickUp API key from .env file at project root."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    # Try to load from .env if it exists
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("CLICKUP_API_KEY="):
                    key = line.replace("CLICKUP_API_KEY=", "").strip()
                    if key and not key.startswith("..."):
                        return key

    # Fall back to environment variable
    key = os.getenv("CLICKUP_API_KEY")
    if not key:
        pytest.skip("CLICKUP_API_KEY not found in .env or environment")

    return key


@pytest.fixture
async def client(api_key: str) -> ClickUpClient:
    """Create a ClickUp client with real API key."""
    return ClickUpClient(api_key=api_key)


class TestClickUpClientLiveGetWorkspaces:
    """Live API tests for getting workspaces."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_workspaces_live(self, client: ClickUpClient) -> None:
        """Get workspaces from real API - MUST PASS."""
        async with client:
            workspaces = await client.get_workspaces()

            # Verify response structure
            assert isinstance(workspaces, list)
            if len(workspaces) > 0:
                # If workspaces exist, verify structure
                ws = workspaces[0]
                assert hasattr(ws, "id")
                assert hasattr(ws, "name")
                assert ws.id is not None
                assert ws.name is not None
                assert isinstance(ws.id, str)
                assert isinstance(ws.name, str)

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_health_check_live(self, client: ClickUpClient) -> None:
        """Health check with real API - MUST PASS."""
        async with client:
            response = await client.health_check()

            assert isinstance(response, dict)
            assert "status" in response
            assert response["status"] == "healthy"
            assert "workspaces_count" in response


class TestClickUpClientLiveGetSpaces:
    """Live API tests for getting spaces."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_spaces_live(self, client: ClickUpClient) -> None:
        """Get spaces from real API - MUST PASS."""
        async with client:
            # First get a workspace
            workspaces = await client.get_workspaces()

            if not workspaces:
                pytest.skip("No workspaces available for testing")

            workspace = workspaces[0]

            # Then get spaces in that workspace
            spaces = await client.get_spaces(workspace.id)

            # Verify response structure
            assert isinstance(spaces, list)
            if len(spaces) > 0:
                # If spaces exist, verify structure
                space = spaces[0]
                assert hasattr(space, "id")
                assert hasattr(space, "name")
                assert space.id is not None
                assert space.name is not None
                assert isinstance(space.id, str)
                assert isinstance(space.name, str)
                assert isinstance(space.private, bool)


class TestClickUpClientLiveGetLists:
    """Live API tests for getting lists."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_lists_live(self, client: ClickUpClient) -> None:
        """Get lists from real API - MUST PASS."""
        async with client:
            # First get a workspace
            workspaces = await client.get_workspaces()

            if not workspaces:
                pytest.skip("No workspaces available for testing")

            # Then get spaces
            spaces = await client.get_spaces(workspaces[0].id)

            if not spaces:
                pytest.skip("No spaces available for testing")

            # Then get lists in that space
            lists = await client.get_lists(spaces[0].id)

            # Verify response structure
            assert isinstance(lists, list)
            if len(lists) > 0:
                # If lists exist, verify structure
                lst = lists[0]
                assert hasattr(lst, "id")
                assert hasattr(lst, "name")
                assert lst.id is not None
                assert lst.name is not None
                assert isinstance(lst.id, str)
                assert isinstance(lst.name, str)


class TestClickUpClientLiveTaskOperations:
    """Live API tests for task operations."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_create_and_delete_task_live(self, client: ClickUpClient) -> None:
        """Create and delete a task with real API - MUST PASS."""
        async with client:
            # Get workspace, space, and list
            workspaces = await client.get_workspaces()
            if not workspaces:
                pytest.skip("No workspaces available for testing")

            spaces = await client.get_spaces(workspaces[0].id)
            if not spaces:
                pytest.skip("No spaces available for testing")

            lists = await client.get_lists(spaces[0].id)
            if not lists:
                pytest.skip("No lists available for testing")

            list_id = lists[0].id

            # Create task
            task = await client.create_task(
                list_id=list_id,
                name="Live API Test Task - DELETE ME",
                description="This is a test task created by live API tests",
                priority=3,
            )

            # Verify task was created
            assert task.id is not None
            assert task.name == "Live API Test Task - DELETE ME"
            assert task.description == "This is a test task created by live API tests"
            assert task.priority == 3

            # Delete the task
            response = await client.delete_task(task.id)
            assert response is not None

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_live(self, client: ClickUpClient) -> None:
        """Get a task with real API - MUST PASS."""
        async with client:
            # Get workspace, space, and list
            workspaces = await client.get_workspaces()
            if not workspaces:
                pytest.skip("No workspaces available for testing")

            spaces = await client.get_spaces(workspaces[0].id)
            if not spaces:
                pytest.skip("No spaces available for testing")

            lists = await client.get_lists(spaces[0].id)
            if not lists:
                pytest.skip("No lists available for testing")

            list_id = lists[0].id

            # Create a task
            created_task = await client.create_task(
                list_id=list_id,
                name="Test Get Task - DELETE ME",
                description="Task for testing get_task method",
            )

            # Get the task by ID
            retrieved_task = await client.get_task(created_task.id)

            # Verify retrieved task matches created task
            assert retrieved_task.id == created_task.id
            assert retrieved_task.name == "Test Get Task - DELETE ME"

            # Clean up
            await client.delete_task(created_task.id)

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_update_task_live(self, client: ClickUpClient) -> None:
        """Update a task with real API - MUST PASS."""
        async with client:
            # Get workspace, space, and list
            workspaces = await client.get_workspaces()
            if not workspaces:
                pytest.skip("No workspaces available for testing")

            spaces = await client.get_spaces(workspaces[0].id)
            if not spaces:
                pytest.skip("No spaces available for testing")

            lists = await client.get_lists(spaces[0].id)
            if not lists:
                pytest.skip("No lists available for testing")

            list_id = lists[0].id

            # Create a task
            created_task = await client.create_task(
                list_id=list_id,
                name="Test Update Task - DELETE ME",
                description="Original description",
                priority=5,
            )

            # Update the task
            updated_task = await client.update_task(
                task_id=created_task.id,
                name="Updated Task Name",
                description="Updated description",
                priority=1,
            )

            # Verify updates
            assert updated_task.id == created_task.id
            assert updated_task.name == "Updated Task Name"
            assert updated_task.description == "Updated description"
            assert updated_task.priority == 1

            # Clean up
            await client.delete_task(created_task.id)

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_tasks_by_list_live(self, client: ClickUpClient) -> None:
        """Get tasks from a list with real API - MUST PASS."""
        async with client:
            # Get workspace, space, and list
            workspaces = await client.get_workspaces()
            if not workspaces:
                pytest.skip("No workspaces available for testing")

            spaces = await client.get_spaces(workspaces[0].id)
            if not spaces:
                pytest.skip("No spaces available for testing")

            lists = await client.get_lists(spaces[0].id)
            if not lists:
                pytest.skip("No lists available for testing")

            list_id = lists[0].id

            # Get tasks from the list
            tasks = await client.get_tasks_by_list(list_id, limit=50)

            # Verify response structure
            assert isinstance(tasks, list)
            if len(tasks) > 0:
                # If tasks exist, verify structure
                task = tasks[0]
                assert hasattr(task, "id")
                assert hasattr(task, "name")
                assert task.id is not None
                assert task.name is not None
                assert isinstance(task.id, str)
                assert isinstance(task.name, str)


class TestClickUpClientLiveErrorHandling:
    """Live API tests for error handling."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_invalid_workspace_id_error(self, client: ClickUpClient) -> None:
        """Should raise error for invalid workspace ID - MUST PASS."""
        async with client:
            with pytest.raises(ClickUpError):
                await client.get_spaces("invalid_workspace_id_12345")

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_invalid_space_id_error(self, client: ClickUpClient) -> None:
        """Should raise error for invalid space ID - MUST PASS."""
        async with client:
            with pytest.raises(ClickUpError):
                await client.get_lists("invalid_space_id_12345")

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_invalid_task_id_error(self, client: ClickUpClient) -> None:
        """Should raise error for invalid task ID - MUST PASS."""
        async with client:
            with pytest.raises(ClickUpError):
                await client.get_task("invalid_task_id_12345")


# Sample data for future-proof endpoint testing
SAMPLE_API_CALL_DATA = {
    "list_id": "123456789",
    "task_name": "Live API Test Task",
    "task_description": "This is a test task created by live API tests",
}
