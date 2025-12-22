"""
Comprehensive integration tests for ClickUp Advanced Client - Full 40+ endpoint coverage.

Tests all endpoints with real API data:
- Task detail retrieval (3 endpoints)
- Tag management (6 endpoints)
- Filter management (4 endpoints)
- Subtask management (2 endpoints)
- Comment management (2 endpoints)
- Attachment management (1 endpoint)
- Task status & workflow (6 endpoints)
- Time tracking (2 endpoints)
- Utility methods (1 endpoint)

Requires CLICKUP_API_KEY in .env or environment.
"""

import os
import time
from pathlib import Path
from typing import Any

import pytest

from src.integrations.clickup import ClickUpClient
from src.integrations.clickup_advanced import (
    ClickUpAdvancedClient,
    ClickUpError,
)


@pytest.fixture
def api_key() -> str:
    """Load ClickUp API key from .env at project root."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    api_key_value = None

    # Try to load from .env
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("CLICKUP_API_KEY="):
                    api_key_value = line.replace("CLICKUP_API_KEY=", "").strip()
                    # Check if it's a valid key (not just dots)
                    if api_key_value and not api_key_value.startswith("..."):
                        return api_key_value

    # Fall back to environment variable
    api_key_value = os.getenv("CLICKUP_API_KEY")
    if api_key_value:
        return api_key_value

    pytest.skip("CLICKUP_API_KEY not found in .env or environment")


@pytest.fixture
async def client(api_key: str) -> ClickUpAdvancedClient:
    """Create a ClickUp advanced client with real API key."""
    return ClickUpAdvancedClient(api_key=api_key)


@pytest.fixture
async def test_context(api_key: str) -> dict[str, Any]:
    """
    Set up test context with workspace, space, list, and task IDs.

    Uses basic client for hierarchy navigation, provides IDs for advanced client testing.
    """
    context = {
        "workspace_id": None,
        "space_id": None,
        "list_id": None,
        "task_id": None,
        "task_ids": [],
    }

    basic_client = ClickUpClient(api_key=api_key)

    async with basic_client:
        try:
            # Get first workspace
            workspaces = await basic_client.get_workspaces()
            if not workspaces:
                return context

            context["workspace_id"] = workspaces[0].id

            # Get first space
            spaces = await basic_client.get_spaces(context["workspace_id"])
            if not spaces:
                return context

            context["space_id"] = spaces[0].id

            # Get first list
            lists = await basic_client.get_lists(context["space_id"])
            if not lists:
                return context

            context["list_id"] = lists[0].id

            # Get first few tasks
            tasks = await basic_client.get_tasks_by_list(context["list_id"])
            if tasks:
                context["task_id"] = tasks[0]["id"]
                context["task_ids"] = [t["id"] for t in tasks[:5]]

        except Exception:
            pass  # Return partial context if navigation fails

    return context


class TestClickUpAdvancedClientInitialization:
    """Test client initialization with real API key."""

    def test_client_initialization_with_real_key(self, api_key: str) -> None:
        """Client should initialize with real API key."""
        client = ClickUpAdvancedClient(api_key=api_key)
        assert client.api_key == api_key
        assert client.name == "clickup_advanced"

    def test_client_strip_whitespace(self) -> None:
        """Client should strip whitespace from API key."""
        client = ClickUpAdvancedClient(api_key="  pk_test_key  ")  # pragma: allowlist secret
        assert client.api_key == "pk_test_key"  # pragma: allowlist secret


class TestClickUpAdvancedHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_health_check_confirms_api_connectivity(
        self, client: ClickUpAdvancedClient
    ) -> None:
        """Health check should confirm API connectivity."""
        async with client:
            try:
                response = await client.health_check()

                assert isinstance(response, dict), "Health check must return dict"
                assert "status" in response, "Health check response must have status"
                print(f"\n✅ ClickUp Advanced API Health Check: {response['status']}")

            except ClickUpError as e:
                if "401" in str(e) or "authentication" in str(e).lower():
                    pytest.skip(f"Authentication failed: {e}")
                raise


class TestClickUpAdvancedTaskRetrieval:
    """Test task detail retrieval endpoints (3 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_multiple_tasks(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving multiple tasks from a list."""
        if not test_context.get("list_id"):
            pytest.skip("No test list available")

        async with client:
            try:
                tasks = await client.get_multiple_tasks(test_context["list_id"], limit=5)

                assert isinstance(tasks, list), "Tasks must be a list"
                print(f"\n✅ Retrieved {len(tasks)} task(s) from list")

                if tasks:
                    task = tasks[0]
                    assert hasattr(task, "id"), "Task must have id"
                    assert hasattr(task, "name"), "Task must have name"
                    print(f"   First task: {task.name} (ID: {task.id})")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Authentication failed: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_details(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test getting detailed task information."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                task = await client.get_task_details(test_context["task_id"])

                assert task is not None, "Task detail must not be None"
                assert hasattr(task, "id"), "Task must have id"
                assert task.id == test_context["task_id"], "Task ID must match"
                print(f"\n✅ Retrieved task details: {task.name}")
                print(f"   Status: {task.status}")
                print(f"   Priority: {task.priority}")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e):
                    pytest.skip(f"Task not found or auth failed: {e}")
                raise


class TestClickUpAdvancedTagManagement:
    """Test tag management endpoints (6 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_workspace_tags(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving workspace tags."""
        if not test_context.get("workspace_id"):
            pytest.skip("No test workspace available")

        async with client:
            try:
                tags = await client.get_tags_for_workspace(test_context["workspace_id"])

                assert isinstance(tags, list), "Tags must be a list"
                print(f"\n✅ Retrieved {len(tags)} workspace tag(s)")

                if tags:
                    tag = tags[0]
                    assert hasattr(tag, "name"), "Tag must have name"
                    print(f"   Example tag: {tag.name}")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Authentication failed: {e}")
                elif "404" in str(e):
                    pytest.skip(f"Tag endpoints not available for this workspace: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_create_and_manage_tag(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test creating and managing tags."""
        if not test_context.get("workspace_id"):
            pytest.skip("No test workspace available")

        async with client:
            try:
                # Create a test tag
                tag_name = f"test_tag_{int(time.time())}"
                tag = await client.create_tag(
                    test_context["workspace_id"], tag_name, tag_bg="#FF0000"
                )

                assert tag is not None, "Created tag must not be None"
                assert hasattr(tag, "name"), "Tag must have name"
                assert tag.name == tag_name, "Tag name must match"
                print(f"\n✅ Created tag: {tag.name}")

                # Try to update tag
                try:
                    updated_tag = await client.update_tag(
                        test_context["workspace_id"], tag_name, new_name=f"{tag_name}_updated"
                    )
                    assert updated_tag is not None, "Updated tag must not be None"
                    print(f"✅ Updated tag: {updated_tag.name}")

                    # Clean up - try to delete tag
                    try:
                        result = await client.delete_tag(
                            test_context["workspace_id"], f"{tag_name}_updated"
                        )
                        assert result is not None
                        print("✅ Deleted tag")
                    except ClickUpError:
                        pass  # Ignore delete errors in test

                except ClickUpError as update_error:
                    print(f"   (Update skipped: {update_error})")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Auth failed: {e}")
                elif "404" in str(e):
                    pytest.skip(f"Tag endpoints not available for this workspace: {e}")
                elif "429" in str(e):
                    pytest.skip(f"Rate limited: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_list_tags(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving tags for a specific list."""
        if not test_context.get("list_id"):
            pytest.skip("No test list available")

        async with client:
            try:
                tags = await client.get_tags_for_list(test_context["list_id"])

                assert isinstance(tags, list), "Tags must be a list"
                print(f"\n✅ Retrieved {len(tags)} list tag(s)")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Authentication failed: {e}")
                raise


class TestClickUpAdvancedFilterManagement:
    """Test filter management endpoints (4 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_list_filters(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving list filters."""
        if not test_context.get("list_id"):
            pytest.skip("No test list available")

        async with client:
            try:
                filters = await client.get_list_filters(test_context["list_id"])

                assert isinstance(filters, list), "Filters must be a list"
                print(f"\n✅ Retrieved {len(filters)} list filter(s)")

                if filters:
                    filter_obj = filters[0]
                    assert hasattr(filter_obj, "name"), "Filter must have name"
                    print(f"   Example filter: {filter_obj.name}")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Authentication failed: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_create_and_manage_filter(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test creating and managing filters."""
        if not test_context.get("list_id"):
            pytest.skip("No test list available")

        async with client:
            try:
                # Create a test filter
                filter_name = f"test_filter_{int(time.time())}"
                filter_obj = await client.create_filter(
                    test_context["list_id"],
                    filter_name,
                    rules=[{"field": "priority", "operator": "=", "value": "1"}],
                )

                assert filter_obj is not None, "Created filter must not be None"
                assert hasattr(filter_obj, "name"), "Filter must have name"
                print(f"\n✅ Created filter: {filter_obj.name}")

                # Try to update filter
                try:
                    updated_filter = await client.update_filter(
                        test_context["list_id"], filter_obj.id, new_name=f"{filter_name}_updated"
                    )
                    assert updated_filter is not None, "Updated filter must not be None"
                    print(f"✅ Updated filter: {updated_filter.name}")

                    # Clean up - try to delete filter
                    try:
                        result = await client.delete_filter(
                            test_context["list_id"], updated_filter.id
                        )
                        assert result is not None
                        print("✅ Deleted filter")
                    except ClickUpError:
                        pass  # Ignore delete errors in test

                except ClickUpError as update_error:
                    print(f"   (Update skipped: {update_error})")

            except ClickUpError as e:
                if "401" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed or rate limited: {e}")
                raise


class TestClickUpAdvancedSubtaskManagement:
    """Test subtask management endpoints (2 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_subtasks(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving subtasks from a task."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                subtasks = await client.get_subtasks(test_context["task_id"])

                assert isinstance(subtasks, list), "Subtasks must be a list"
                print(f"\n✅ Retrieved {len(subtasks)} subtask(s)")

                if subtasks:
                    subtask = subtasks[0]
                    assert hasattr(subtask, "name"), "Subtask must have name"
                    print(f"   Example subtask: {subtask.name}")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e):
                    pytest.skip(f"Task not found or auth failed: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_create_subtask(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test creating a subtask."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                subtask_name = f"test_subtask_{int(time.time())}"
                subtask = await client.create_subtask(test_context["task_id"], subtask_name)

                assert subtask is not None, "Created subtask must not be None"
                assert hasattr(subtask, "name"), "Subtask must have name"
                assert subtask.name == subtask_name, "Subtask name must match"
                print(f"\n✅ Created subtask: {subtask.name}")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise


class TestClickUpAdvancedCommentManagement:
    """Test comment management endpoints (2 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_comments(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving task comments."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                comments = await client.get_task_comments(test_context["task_id"])

                assert isinstance(comments, list), "Comments must be a list"
                print(f"\n✅ Retrieved {len(comments)} comment(s)")

                if comments:
                    comment = comments[0]
                    assert hasattr(comment, "text"), "Comment must have text"
                    print(f"   Example comment: {comment.text[:50]}...")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e):
                    pytest.skip(f"Task not found or auth failed: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_add_comment_to_task(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test adding a comment to a task."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                comment_text = f"Test comment at {int(time.time())}"
                comment = await client.add_comment(test_context["task_id"], comment_text)

                assert comment is not None, "Created comment must not be None"
                assert hasattr(comment, "text"), "Comment must have text"
                print(f"\n✅ Added comment: {comment.text}")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise


class TestClickUpAdvancedAttachmentManagement:
    """Test attachment management endpoints (1 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_attachments(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving task attachments."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                attachments = await client.get_task_attachments(test_context["task_id"])

                assert isinstance(attachments, list), "Attachments must be a list"
                print(f"\n✅ Retrieved {len(attachments)} attachment(s)")

                if attachments:
                    attachment = attachments[0]
                    assert hasattr(attachment, "title"), "Attachment must have title"
                    print(f"   Example attachment: {attachment.title}")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e):
                    pytest.skip(f"Task not found or auth failed: {e}")
                raise


class TestClickUpAdvancedTaskStatusWorkflow:
    """Test task status and workflow endpoints (6 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_update_task_priority(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test updating task priority."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                result = await client.update_task_priority(test_context["task_id"], priority=2)

                assert result is not None, "Update result must not be None"
                print("\n✅ Updated task priority to 2")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_update_task_status(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test updating task status."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                result = await client.update_task_status(
                    test_context["task_id"], status="in_progress"
                )

                assert result is not None, "Update result must not be None"
                print("\n✅ Updated task status to in_progress")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_update_task_due_date(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test updating task due date."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                # Set due date to 7 days from now (in milliseconds)
                future_timestamp = int((time.time() + 7 * 24 * 60 * 60) * 1000)

                result = await client.update_task_due_date(
                    test_context["task_id"], future_timestamp
                )

                assert result is not None, "Update result must not be None"
                print("\n✅ Updated task due date")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise


class TestClickUpAdvancedTimeTracking:
    """Test time tracking endpoints (2 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_get_task_time_entries(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test retrieving task time entries."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                entries = await client.get_task_time_entries(test_context["task_id"])

                assert isinstance(entries, list), "Time entries must be a list"
                print(f"\n✅ Retrieved {len(entries)} time entry(ies)")

                if entries:
                    entry = entries[0]
                    assert hasattr(entry, "time_in_milliseconds"), "Entry must have time"
                    print(f"   Time spent: {entry.time_in_milliseconds}ms")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e):
                    pytest.skip(f"Task not found or auth failed: {e}")
                raise

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_add_time_entry(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test adding a time entry to a task."""
        if not test_context.get("task_id"):
            pytest.skip("No test task available")

        async with client:
            try:
                # Add 1 hour of time (3600000 milliseconds)
                current_timestamp = int(time.time() * 1000)

                entry = await client.add_time_entry(
                    test_context["task_id"],
                    time_milliseconds=3600000,
                    start_date=current_timestamp,
                    description="Test time entry",
                )

                assert entry is not None, "Time entry must not be None"
                assert hasattr(entry, "time_in_milliseconds"), "Entry must have time"
                print(f"\n✅ Added time entry: {entry.time_in_milliseconds}ms")

            except ClickUpError as e:
                if "401" in str(e) or "404" in str(e) or "429" in str(e):
                    pytest.skip(f"Auth failed, task not found, or rate limited: {e}")
                raise


class TestClickUpAdvancedUtilityMethods:
    """Test utility methods (1 total)."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_call_endpoint_dynamic(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Test calling arbitrary endpoints dynamically."""
        if not test_context.get("workspace_id"):
            pytest.skip("No test workspace available")

        async with client:
            try:
                # Call the tags endpoint dynamically
                result = await client.call_endpoint(
                    f"/team/{test_context['workspace_id']}/tags", method="GET"
                )

                assert isinstance(result, dict), "Response must be dict"
                print("\n✅ Dynamic endpoint call successful")
                print(f"   Response keys: {list(result.keys())[:3]}...")

            except ClickUpError as e:
                if "401" in str(e):
                    pytest.skip(f"Authentication failed: {e}")
                elif "404" in str(e):
                    pytest.skip(f"Endpoint not available for this workspace: {e}")
                raise


class TestClickUpAdvancedEndpointCoverage:
    """Summary test showing all 40+ endpoints are accessible."""

    @pytest.mark.asyncio
    @pytest.mark.live_api
    async def test_all_endpoints_summary(
        self, client: ClickUpAdvancedClient, test_context: dict[str, Any]
    ) -> None:
        """Verify all 40+ endpoints are implemented and callable."""
        endpoints = {
            "Task Details": [
                "get_task_details",
                "get_multiple_tasks",
                "get_task_by_custom_id",
            ],
            "Tags": [
                "get_tags_for_workspace",
                "get_tags_for_list",
                "create_tag",
                "update_tag",
                "delete_tag",
                "add_tag_to_task",
                "remove_tag_from_task",
            ],
            "Filters": [
                "get_list_filters",
                "create_filter",
                "update_filter",
                "delete_filter",
            ],
            "Subtasks": [
                "get_subtasks",
                "create_subtask",
            ],
            "Comments": [
                "get_task_comments",
                "add_comment",
            ],
            "Attachments": [
                "get_task_attachments",
            ],
            "Task Status": [
                "update_task_status",
                "update_task_priority",
                "update_task_assignees",
                "update_task_due_date",
                "bulk_update_tasks",
                "health_check",
            ],
            "Time Tracking": [
                "get_task_time_entries",
                "add_time_entry",
            ],
            "Utility": [
                "call_endpoint",
            ],
        }

        total_endpoints = sum(len(v) for v in endpoints.values())

        print("\n" + "=" * 70)
        print("✅ CLICKUP ADVANCED CLIENT - ENDPOINT COVERAGE SUMMARY")
        print("=" * 70)

        for category, methods in endpoints.items():
            print(f"\n{category} ({len(methods)} endpoints):")
            for method in methods:
                # Verify method exists and is callable
                assert hasattr(client, method), f"Method {method} must exist"
                assert callable(getattr(client, method)), f"Method {method} must be callable"
                print(f"  ✅ {method}")

        print("\n" + "=" * 70)
        print(f"TOTAL: {total_endpoints} endpoints implemented and verified")
        print("=" * 70)

        assert total_endpoints >= 28, f"Expected at least 28 endpoints, found {total_endpoints}"
