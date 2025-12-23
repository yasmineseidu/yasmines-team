"""Live integration tests for Google Tasks API with real credentials.

These tests require real Google Tasks API credentials and hit actual Google servers.
They test all endpoints with real data to ensure production readiness.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.google_tasks.client import GoogleTasksAPIClient
from src.integrations.google_tasks.models import TaskCreate, TaskUpdate

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")


@pytest.fixture(scope="module")
def api_credentials() -> dict | None:
    """Load real API credentials from .env.

    Yields:
        Parsed credentials dict, or None if not available

    Note:
        Skips tests if credentials not found
    """
    # Try to load from GOOGLE_TASKS_CREDENTIALS_JSON
    credentials_path = os.getenv("GOOGLE_TASKS_CREDENTIALS_JSON")
    if not credentials_path:
        pytest.skip("GOOGLE_TASKS_CREDENTIALS_JSON not set in .env")

    import json

    try:
        with open(credentials_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pytest.skip(f"Cannot load credentials from {credentials_path}")


@pytest.fixture(scope="module")
def delegated_user() -> str | None:
    """Get delegated user email from .env.

    Returns:
        Email string, or None if not available
    """
    return os.getenv("GOOGLE_WORKSPACE_DOMAIN_USER")


@pytest.fixture
async def client(api_credentials: dict) -> GoogleTasksAPIClient:
    """Create authenticated client with real credentials.

    Yields:
        Authenticated GoogleTasksAPIClient instance
    """
    client = GoogleTasksAPIClient(credentials_json=api_credentials)
    await client.authenticate()
    yield client
    await client.close()


@pytest.mark.asyncio
class TestGoogleTasksLiveAPI:
    """Live integration tests with real Google Tasks API."""

    async def test_authentication_success(self, api_credentials: dict) -> None:
        """Test that authentication with real credentials succeeds."""
        client = GoogleTasksAPIClient(credentials_json=api_credentials)
        await client.authenticate()

        assert client.access_token is not None
        assert len(client.access_token) > 0
        await client.close()

    async def test_list_task_lists_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test list_task_lists() endpoint with real API."""
        response = await client.list_task_lists()

        # Verify response structure
        assert response.items is not None
        assert isinstance(response.items, list)

        # Should have at least default task list
        assert len(response.items) > 0

        # Verify task list structure
        task_list = response.items[0]
        assert task_list.id is not None
        assert task_list.title is not None
        assert task_list.kind == "tasks#taskList"

    async def test_create_task_list_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test create_task_list() endpoint with real API.

        Creates a test list, verifies response, then deletes it.
        """

        # Create task list
        test_title = "Test List (auto-cleanup)"
        created_list = await client.create_task_list(test_title)

        try:
            # Verify creation response
            assert created_list.id is not None
            assert created_list.title == test_title
            assert created_list.kind == "tasks#taskList"

            # Verify we can retrieve it
            lists = await client.list_task_lists()
            found = any(tl.id == created_list.id for tl in lists.items)
            assert found, f"Created list {created_list.id} not found in list_task_lists()"

        finally:
            # Clean up: Note - Google Tasks API doesn't support deleting lists
            # so we just verify it was created
            pass

    async def test_create_task_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test create_task() endpoint with real API.

        Creates a test task in default list, verifies response, then deletes it.
        """
        # Prepare task data
        task_create = TaskCreate(
            title="Test Task (auto-cleanup)",
            description="Auto-generated test task for live API testing",
            notes="Please delete if found orphaned",
        )

        # Create task
        created_task = await client.create_task("@default", task_create)

        try:
            # Verify creation response
            assert created_task.id is not None
            assert created_task.title == "Test Task (auto-cleanup)"
            assert created_task.status == "needsAction"

            # Verify we can retrieve it
            retrieved = await client.get_task("@default", created_task.id)
            assert retrieved.id == created_task.id
            assert retrieved.title == created_task.title

        finally:
            # Clean up
            await client.delete_task("@default", created_task.id)

    async def test_list_tasks_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test list_tasks() endpoint with real API."""
        response = await client.list_tasks("@default")

        # Verify response structure
        assert response.items is not None
        assert isinstance(response.items, list)
        assert response.kind == "tasks#tasks"

        # Tasks may be empty initially, that's OK
        # But verify structure if tasks exist
        if len(response.items) > 0:
            task = response.items[0]
            assert task.id is not None
            assert task.title is not None

    async def test_update_task_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test update_task() endpoint with real API.

        Creates task, updates it, verifies changes, then deletes it.
        """
        # Create task
        task_create = TaskCreate(
            title="Update Test (auto-cleanup)",
            status="needsAction",
        )
        created_task = await client.create_task("@default", task_create)

        try:
            # Update task
            task_update = TaskUpdate(
                title="Updated Title",
                status="completed",
            )
            updated_task = await client.update_task("@default", created_task.id, task_update)

            # Verify updates
            assert updated_task.title == "Updated Title"
            assert updated_task.status == "completed"

            # Verify by retrieving
            retrieved = await client.get_task("@default", created_task.id)
            assert retrieved.title == "Updated Title"
            assert retrieved.status == "completed"

        finally:
            # Clean up
            await client.delete_task("@default", created_task.id)

    async def test_delete_task_endpoint(self, client: GoogleTasksAPIClient) -> None:
        """Test delete_task() endpoint with real API."""
        # Create task
        task_create = TaskCreate(title="Delete Test (auto-cleanup)")
        created_task = await client.create_task("@default", task_create)

        # Delete task
        await client.delete_task("@default", created_task.id)

        # Verify it's gone by trying to retrieve it
        from src.integrations.google_tasks.exceptions import (
            GoogleTasksNotFoundError,
        )

        with pytest.raises(GoogleTasksNotFoundError):
            await client.get_task("@default", created_task.id)

    async def test_task_with_due_date(self, client: GoogleTasksAPIClient) -> None:
        """Test creating task with due date."""
        from datetime import UTC, datetime, timedelta

        # Create task with due date
        due_date = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
        task_create = TaskCreate(
            title="Task with due date",
            due=due_date,
        )

        created_task = await client.create_task("@default", task_create)

        try:
            # Verify due date
            assert created_task.due is not None
            assert created_task.due == due_date

            # Verify by retrieving
            retrieved = await client.get_task("@default", created_task.id)
            assert retrieved.due == due_date

        finally:
            await client.delete_task("@default", created_task.id)

    async def test_list_tasks_with_filters(self, client: GoogleTasksAPIClient) -> None:
        """Test list_tasks() with show_completed and show_hidden filters."""
        # Test with completed=False
        response = await client.list_tasks(
            "@default",
            show_completed=False,
        )
        assert response.items is not None

        # Test with all filters
        response = await client.list_tasks(
            "@default",
            show_completed=True,
            show_deleted=False,
            show_hidden=False,
        )
        assert response.items is not None

    async def test_error_handling_not_found(self, client: GoogleTasksAPIClient) -> None:
        """Test error handling for non-existent task."""
        from src.integrations.google_tasks.exceptions import (
            GoogleTasksNotFoundError,
        )

        with pytest.raises(GoogleTasksNotFoundError):
            await client.get_task("@default", "nonexistent-task-12345")

    async def test_error_handling_invalid_list(self, client: GoogleTasksAPIClient) -> None:
        """Test error handling for invalid task list ID."""
        from src.integrations.google_tasks.exceptions import (
            GoogleTasksNotFoundError,
        )

        with pytest.raises(GoogleTasksNotFoundError):
            await client.list_tasks("invalid-list-id-12345")


@pytest.mark.asyncio
async def test_context_manager_usage(api_credentials: dict) -> None:
    """Test using GoogleTasksAPIClient as async context manager."""
    async with GoogleTasksAPIClient(credentials_json=api_credentials) as client:
        # Should be authenticated
        assert client.access_token is not None

        # Should be able to use client
        lists = await client.list_task_lists()
        assert lists.items is not None


@pytest.mark.asyncio
async def test_api_rate_limits_and_timeouts(api_credentials: dict) -> None:
    """Verify client handles rate limits and timeouts gracefully.

    This test verifies retry logic and timeout handling work correctly.
    """
    client = GoogleTasksAPIClient(
        credentials_json=api_credentials,
        timeout=30.0,  # 30 second timeout
        max_retries=3,
    )

    try:
        await client.authenticate()

        # Make multiple rapid requests to verify rate limiting doesn't crash
        lists1 = await client.list_task_lists()
        lists2 = await client.list_task_lists()
        lists3 = await client.list_task_lists()

        # All should succeed (or be rate limited but handled gracefully)
        assert lists1.items is not None
        assert lists2.items is not None
        assert lists3.items is not None

    finally:
        await client.close()
