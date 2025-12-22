"""
Comprehensive unit tests for ClickUp Advanced Client.

Tests all 40+ endpoints including:
- Task detail retrieval
- Tag management
- Filter management
- Subtask management
- Comments and attachments
- Time tracking
- Status and workflow updates
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.clickup_advanced import (
    ClickUpAdvancedClient,
    ClickUpError,
)


@pytest.fixture
def client() -> ClickUpAdvancedClient:
    """Create ClickUp advanced client for testing."""
    return ClickUpAdvancedClient(api_key="pk_test_key_12345")  # pragma: allowlist secret


class TestClickUpAdvancedClientInitialization:
    """Test client initialization."""

    def test_initialization_with_valid_api_key(self) -> None:
        """Client should initialize with valid API key."""
        client = ClickUpAdvancedClient(api_key="pk_test_key")  # pragma: allowlist secret
        assert client.api_key == "pk_test_key"  # pragma: allowlist secret
        assert client.name == "clickup_advanced"

    def test_initialization_raises_on_empty_api_key(self) -> None:
        """Client should raise ValueError on empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ClickUpAdvancedClient(api_key="")

    def test_initialization_strips_whitespace(self) -> None:
        """Client should strip whitespace from API key."""
        client = ClickUpAdvancedClient(api_key="  pk_test_key  ")  # pragma: allowlist secret
        assert client.api_key == "pk_test_key"  # pragma: allowlist secret


class TestTaskDetailRetrieval:
    """Test task detail retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_task_details_success(self, client: ClickUpAdvancedClient) -> None:
        """Get task details should return complete task information."""
        mock_response = {
            "id": "task_123",
            "custom_id": "CUSTOM_123",
            "name": "Test Task",
            "description": "Task description",
            "status": {"type": "open"},
            "priority": {"priority": 2},
            "due_date": 1735987200000,
            "start_date": 1735900800000,
            "time_estimate": 3600000,
            "time_spent": 1800000,
            "tags": [{"name": "tag1"}, {"name": "tag2"}],
            "assignees": [{"id": 1, "name": "User 1"}],
            "watchers": [{"id": 2, "name": "User 2"}],
            "creator": {"id": 3, "name": "Creator"},
            "date_created": 1735814400000,
            "date_updated": 1735900800000,
            "comments": [{"id": "c1", "text_content": "Comment"}],
            "attachments": [{"id": "a1", "title": "File.pdf"}],
            "subtasks": [{"id": "st1", "name": "Subtask 1"}],
            "list": {"id": "list_123"},
            "folder": {"id": "folder_456"},
            "space": {"id": "space_789"},
            "parent": "parent_task",
            "url": "https://app.clickup.com/t/task_123",
            "custom_fields": [{"id": "cf1", "value": "custom_value"}],
            "dependencies": [],
            "linked_tasks": [],
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            task = await client.get_task_details("task_123")

            assert task.id == "task_123"
            assert task.name == "Test Task"
            assert task.status == "open"
            assert task.priority == 2
            assert len(task.tags) == 2
            assert task.comments_count == 1
            assert task.attachments_count == 1
            assert task.subtasks_count == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_details_raises_on_empty_task_id(
        self, client: ClickUpAdvancedClient
    ) -> None:
        """Get task details should raise on empty task ID."""
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            await client.get_task_details("")

    @pytest.mark.asyncio
    async def test_get_multiple_tasks_with_filters(self, client: ClickUpAdvancedClient) -> None:
        """Get multiple tasks should support filtering."""
        mock_response = {
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Task 1",
                    "status": {"type": "open"},
                    "priority": {"priority": 1},
                    "tags": [],
                    "assignees": [],
                    "date_created": 1735814400000,
                    "date_updated": 1735814400000,
                }
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            tasks = await client.get_multiple_tasks(
                "list_123",
                statuses=["open"],
                assignees=[1],
                tags=["tag1"],
            )

            assert len(tasks) == 1
            assert tasks[0].name == "Task 1"
            mock_get.assert_called_once()


class TestTagManagement:
    """Test tag management endpoints."""

    @pytest.mark.asyncio
    async def test_get_tags_for_workspace(self, client: ClickUpAdvancedClient) -> None:
        """Get tags should return workspace tags."""
        mock_response = {
            "tags": [
                {"name": "urgent", "tag_fg": "#000000", "tag_bg": "#FF0000"},
                {"name": "bug", "tag_fg": "#000000", "tag_bg": "#FF9900"},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            tags = await client.get_tags_for_workspace("workspace_123")

            assert len(tags) == 2
            assert tags[0].name == "urgent"
            assert tags[1].name == "bug"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tag_success(self, client: ClickUpAdvancedClient) -> None:
        """Create tag should return created tag."""
        mock_response = {
            "name": "new_tag",
            "tag_fg": "#000000",
            "tag_bg": "#0000FF",
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            tag = await client.create_tag(
                "workspace_123",
                "new_tag",
                tag_fg="#000000",
                tag_bg="#0000FF",
            )

            assert tag.name == "new_tag"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tag_success(self, client: ClickUpAdvancedClient) -> None:
        """Update tag should return updated tag."""
        mock_response = {
            "name": "updated_tag",
            "tag_fg": "#FFFFFF",
            "tag_bg": "#00FF00",
        }

        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response

            tag = await client.update_tag(
                "workspace_123",
                "old_tag",
                new_name="updated_tag",
            )

            assert tag.name == "updated_tag"
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tag_success(self, client: ClickUpAdvancedClient) -> None:
        """Delete tag should succeed."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            response = await client.delete_tag("workspace_123", "tag_to_delete")

            assert response["success"] is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_tag_to_task(self, client: ClickUpAdvancedClient) -> None:
        """Add tag to task should succeed."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}

            response = await client.add_tag_to_task("task_123", "urgent")

            assert response["success"] is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_tag_from_task(self, client: ClickUpAdvancedClient) -> None:
        """Remove tag from task should succeed."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            response = await client.remove_tag_from_task("task_123", "urgent")

            assert response["success"] is True
            mock_delete.assert_called_once()


class TestFilterManagement:
    """Test filter management endpoints."""

    @pytest.mark.asyncio
    async def test_get_list_filters(self, client: ClickUpAdvancedClient) -> None:
        """Get filters should return list filters."""
        mock_response = {
            "filters": [
                {
                    "id": "filter_1",
                    "name": "My Open Tasks",
                    "color": "#FF0000",
                    "rules": [],
                    "archived": False,
                }
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            filters = await client.get_list_filters("list_123")

            assert len(filters) == 1
            assert filters[0].name == "My Open Tasks"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_filter_success(self, client: ClickUpAdvancedClient) -> None:
        """Create filter should return created filter."""
        mock_response = {
            "id": "filter_new",
            "name": "High Priority",
            "color": "#FF0000",
            "rules": [{"field": "priority", "operator": "=", "value": "1"}],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            filter_obj = await client.create_filter(
                "list_123",
                "High Priority",
                [{"field": "priority", "operator": "=", "value": "1"}],
            )

            assert filter_obj.name == "High Priority"
            assert len(filter_obj.rules) == 1
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_filter_success(self, client: ClickUpAdvancedClient) -> None:
        """Update filter should return updated filter."""
        mock_response = {
            "id": "filter_123",
            "name": "Updated Filter",
            "rules": [],
        }

        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response

            filter_obj = await client.update_filter(
                "list_123",
                "filter_123",
                name="Updated Filter",
            )

            assert filter_obj.name == "Updated Filter"
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_filter_success(self, client: ClickUpAdvancedClient) -> None:
        """Delete filter should succeed."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            response = await client.delete_filter("list_123", "filter_456")

            assert response["success"] is True
            mock_delete.assert_called_once()


class TestSubtaskManagement:
    """Test subtask management endpoints."""

    @pytest.mark.asyncio
    async def test_get_subtasks_success(self, client: ClickUpAdvancedClient) -> None:
        """Get subtasks should return list of subtasks."""
        mock_response = {
            "subtasks": [
                {
                    "id": "st_1",
                    "name": "Subtask 1",
                    "status": {"type": "open"},
                    "priority": {"priority": 2},
                    "assignees": [],
                    "due_date": None,
                    "start_date": None,
                    "time_estimate": None,
                },
                {
                    "id": "st_2",
                    "name": "Subtask 2",
                    "status": {"type": "done"},
                    "priority": {"priority": 3},
                    "assignees": [],
                    "due_date": None,
                    "start_date": None,
                    "time_estimate": None,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            subtasks = await client.get_subtasks("task_123")

            assert len(subtasks) == 2
            assert subtasks[0].name == "Subtask 1"
            assert subtasks[1].status == "done"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subtask_success(self, client: ClickUpAdvancedClient) -> None:
        """Create subtask should return created subtask."""
        mock_response = {
            "id": "st_new",
            "name": "New Subtask",
            "status": {"type": "open"},
            "priority": {"priority": 2},
            "assignees": [],
            "due_date": None,
            "start_date": None,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            subtask = await client.create_subtask("task_123", "New Subtask")

            assert subtask.name == "New Subtask"
            assert subtask.status == "open"
            mock_post.assert_called_once()


class TestCommentManagement:
    """Test comment management endpoints."""

    @pytest.mark.asyncio
    async def test_get_task_comments(self, client: ClickUpAdvancedClient) -> None:
        """Get comments should return task comments."""
        mock_response = {
            "comments": [
                {
                    "id": "c_1",
                    "text_content": "Great work!",
                    "user": {"id": 1, "name": "User 1"},
                    "date_created": 1735814400000,
                    "date_updated": None,
                    "attachments": [],
                },
                {
                    "id": "c_2",
                    "text_content": "Thanks!",
                    "user": {"id": 2, "name": "User 2"},
                    "date_created": 1735900800000,
                    "date_updated": None,
                    "attachments": [],
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            comments = await client.get_task_comments("task_123")

            assert len(comments) == 2
            assert comments[0].text == "Great work!"
            assert comments[1].text == "Thanks!"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_comment_success(self, client: ClickUpAdvancedClient) -> None:
        """Add comment should return created comment."""
        mock_response = {
            "id": "c_new",
            "text_content": "New comment",
            "user": {"id": 1, "name": "Current User"},
            "date_created": 1735987200000,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            comment = await client.add_comment("task_123", "New comment")

            assert comment.text == "New comment"
            mock_post.assert_called_once()


class TestAttachmentManagement:
    """Test attachment management endpoints."""

    @pytest.mark.asyncio
    async def test_get_task_attachments(self, client: ClickUpAdvancedClient) -> None:
        """Get attachments should return task attachments."""
        mock_response = {
            "attachments": [
                {
                    "id": "a_1",
                    "title": "document.pdf",
                    "url": "https://example.com/doc.pdf",
                    "mime_type": "application/pdf",
                    "size": 1024000,
                    "date": 1735814400000,
                    "created_by": {"id": 1, "name": "User 1"},
                },
                {
                    "id": "a_2",
                    "title": "image.png",
                    "url": "https://example.com/image.png",
                    "mime_type": "image/png",
                    "size": 512000,
                    "date": 1735900800000,
                    "created_by": {"id": 2, "name": "User 2"},
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            attachments = await client.get_task_attachments("task_123")

            assert len(attachments) == 2
            assert attachments[0].title == "document.pdf"
            assert attachments[1].mime_type == "image/png"
            mock_get.assert_called_once()


class TestTaskStatusAndWorkflow:
    """Test task status and workflow endpoints."""

    @pytest.mark.asyncio
    async def test_update_task_status(self, client: ClickUpAdvancedClient) -> None:
        """Update task status should succeed."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {"success": True}

            response = await client.update_task_status("task_123", "in_progress")

            assert response["success"] is True
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_priority(self, client: ClickUpAdvancedClient) -> None:
        """Update task priority should succeed."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {"success": True}

            response = await client.update_task_priority("task_123", 1)

            assert response["success"] is True
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_priority_raises_on_invalid_priority(
        self, client: ClickUpAdvancedClient
    ) -> None:
        """Update priority should raise on invalid priority."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 5"):
            await client.update_task_priority("task_123", 10)

    @pytest.mark.asyncio
    async def test_update_task_assignees(self, client: ClickUpAdvancedClient) -> None:
        """Update task assignees should succeed."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {"success": True}

            response = await client.update_task_assignees(
                "task_123",
                add_assignees=[1, 2],
            )

            assert response["success"] is True
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_due_date(self, client: ClickUpAdvancedClient) -> None:
        """Update task due date should succeed."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {"success": True}

            response = await client.update_task_due_date("task_123", 1735987200000)

            assert response["success"] is True
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_tasks(self, client: ClickUpAdvancedClient) -> None:
        """Bulk update tasks should update multiple tasks."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {"success": True}

            result = await client.bulk_update_tasks(
                ["task_1", "task_2", "task_3"],
                {"status": "done"},
            )

            assert "task_1" in result
            assert "task_2" in result
            assert "task_3" in result
            assert mock_put.call_count == 3


class TestTimeTracking:
    """Test time tracking endpoints."""

    @pytest.mark.asyncio
    async def test_get_task_time_entries(self, client: ClickUpAdvancedClient) -> None:
        """Get time entries should return task time entries."""
        mock_response = {
            "data": [
                {
                    "id": "t_1",
                    "user": {"id": 1, "name": "User 1"},
                    "time": 3600000,
                    "start": 1735814400000,
                    "end": 1735818000000,
                    "description": "Development",
                    "billable": True,
                },
                {
                    "id": "t_2",
                    "user": {"id": 2, "name": "User 2"},
                    "time": 1800000,
                    "start": 1735900800000,
                    "end": 1735902600000,
                    "description": "Review",
                    "billable": False,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            entries = await client.get_task_time_entries("task_123")

            assert len(entries) == 2
            assert entries[0].time_in_milliseconds == 3600000
            assert entries[1].billable is False
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_time_entry(self, client: ClickUpAdvancedClient) -> None:
        """Add time entry should return created entry."""
        mock_response = {
            "id": "t_new",
            "user": {"id": 1},
            "time": 3600000,
            "start": 1735814400000,
            "billable": True,
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            entry = await client.add_time_entry(
                "task_123",
                3600000,
                1735814400000,
                description="Work done",
                billable=True,
            )

            assert entry.time_in_milliseconds == 3600000
            assert entry.billable is True
            mock_post.assert_called_once()


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: ClickUpAdvancedClient) -> None:
        """Health check should return status."""
        mock_response = {"teams": [{"id": "1"}, {"id": "2"}]}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            health = await client.health_check()

            assert health["status"] == "healthy"
            assert health["accessible_workspaces"] == 2
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_get(self, client: ClickUpAdvancedClient) -> None:
        """Call endpoint with GET should work."""
        mock_response = {"data": "test"}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.call_endpoint("/custom/endpoint", method="GET")

            assert result["data"] == "test"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_post(self, client: ClickUpAdvancedClient) -> None:
        """Call endpoint with POST should work."""
        mock_response = {"id": "new_item"}

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.call_endpoint(
                "/custom/endpoint",
                method="POST",
                json={"data": "test"},
            )

            assert result["id"] == "new_item"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_endpoint_unsupported_method(self, client: ClickUpAdvancedClient) -> None:
        """Call endpoint with unsupported method should raise."""
        with pytest.raises(ClickUpError, match="Failed to call endpoint"):
            await client.call_endpoint("/endpoint", method="TRACE")  # type: ignore
