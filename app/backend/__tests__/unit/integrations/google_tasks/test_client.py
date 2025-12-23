"""Unit tests for Google Tasks API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from __tests__.fixtures.google_tasks_fixtures import (
    INVALID_CREDENTIALS,
    MOCK_RESPONSES,
    MOCK_SERVICE_ACCOUNT_CREDENTIALS,
    SAMPLE_DATA,
)
from src.integrations.google_tasks.client import GoogleTasksAPIClient
from src.integrations.google_tasks.exceptions import (
    GoogleTasksAPIError,
    GoogleTasksAuthError,
    GoogleTasksConfigError,
    GoogleTasksNotFoundError,
    GoogleTasksQuotaExceeded,
    GoogleTasksValidationError,
)
from src.integrations.google_tasks.models import TaskCreate, TaskUpdate


class TestGoogleTasksClientInitialization:
    """Tests for GoogleTasksAPIClient initialization."""

    def test_init_with_credentials_json(self) -> None:
        """Client should initialize with credentials_json dict."""
        client = GoogleTasksAPIClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.name == "google_tasks"
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS
        assert client.access_token is None

    def test_init_with_credentials_str(self) -> None:
        """Client should initialize with credentials JSON string."""
        import json

        creds_str = json.dumps(MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        client = GoogleTasksAPIClient(credentials_str=creds_str)
        assert client.credentials_json == MOCK_SERVICE_ACCOUNT_CREDENTIALS

    def test_init_with_access_token(self) -> None:
        """Client should initialize with pre-obtained access token."""
        client = GoogleTasksAPIClient(access_token="test-token-123")
        assert client.access_token == "test-token-123"

    def test_init_with_delegation_uses_single_scope(self) -> None:
        """When delegated_user set, should use single scope."""
        client = GoogleTasksAPIClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            delegated_user="user@example.com",
        )
        assert client.scopes == [GoogleTasksAPIClient.DELEGATION_SCOPE]

    def test_init_without_delegation_uses_default_scopes(self) -> None:
        """Without delegated_user, should use default scopes."""
        client = GoogleTasksAPIClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)
        assert client.scopes == GoogleTasksAPIClient.DEFAULT_SCOPES

    def test_init_raises_on_missing_credentials(self) -> None:
        """Should raise GoogleTasksConfigError if no credentials provided."""
        with pytest.raises(GoogleTasksConfigError):
            GoogleTasksAPIClient()

    def test_init_raises_on_invalid_credentials_dict(self) -> None:
        """Should raise GoogleTasksConfigError if credentials dict invalid."""
        with pytest.raises(GoogleTasksConfigError):
            GoogleTasksAPIClient(credentials_json=INVALID_CREDENTIALS["missing_type"])

    def test_init_raises_on_invalid_credentials_str(self) -> None:
        """Should raise GoogleTasksConfigError if credentials string invalid."""
        with pytest.raises(GoogleTasksConfigError):
            GoogleTasksAPIClient(credentials_str="not valid json")

    def test_init_validates_credentials_type(self) -> None:
        """Should validate credentials type is service_account."""
        with pytest.raises(GoogleTasksConfigError):
            GoogleTasksAPIClient(credentials_json=INVALID_CREDENTIALS["wrong_type"])

    def test_init_validates_required_fields(self) -> None:
        """Should validate all required credential fields present."""
        with pytest.raises(GoogleTasksConfigError):
            GoogleTasksAPIClient(credentials_json=INVALID_CREDENTIALS["missing_fields"])


class TestGoogleTasksClientAuthentication:
    """Tests for authentication flow."""

    @pytest.mark.asyncio
    async def test_authenticate_with_access_token(self) -> None:
        """authenticate() should skip if access_token already set."""
        client = GoogleTasksAPIClient(access_token="test-token-123")
        await client.authenticate()
        assert client.access_token == "test-token-123"

    @pytest.mark.asyncio
    async def test_authenticate_gets_token_from_credentials(self) -> None:
        """authenticate() should get token using service account credentials."""
        client = GoogleTasksAPIClient(credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS)

        with patch("src.integrations.google_tasks.client.Credentials") as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.token = "test-token-456"
            mock_creds_class.from_service_account_info.return_value = mock_creds

            await client.authenticate()

            assert client.access_token == "test-token-456"

    @pytest.mark.asyncio
    async def test_authenticate_raises_on_missing_credentials(self) -> None:
        """authenticate() should raise if no credentials available."""
        client = GoogleTasksAPIClient(access_token="token")
        client.credentials_json = {}  # Clear credentials
        client.access_token = None  # Clear token

        with pytest.raises(GoogleTasksAuthError):
            await client.authenticate()


class TestGoogleTasksClientTaskLists:
    """Tests for task list operations."""

    @pytest.fixture
    def client(self) -> GoogleTasksAPIClient:
        """Create client with mock credentials."""
        return GoogleTasksAPIClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            access_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_list_task_lists_success(self, client: GoogleTasksAPIClient) -> None:
        """list_task_lists() should return TaskListsResponse."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_lists_list"]

            response = await client.list_task_lists()

            assert len(response.items) == 2
            assert response.items[0].id == "@default"
            assert response.items[1].id == "test-list-123"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_task_lists_with_max_results(self, client: GoogleTasksAPIClient) -> None:
        """list_task_lists() should accept max_results parameter."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_lists_list"]

            await client.list_task_lists(max_results=50)

            # Verify max_results was passed
            assert mock_request.call_args[1]["params"]["maxResults"] == 50

    @pytest.mark.asyncio
    async def test_create_task_list_success(self, client: GoogleTasksAPIClient) -> None:
        """create_task_list() should return created TaskList."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_list_created"]

            task_list = await client.create_task_list("Test Task List")

            assert task_list.id == "test-list-123"
            assert task_list.title == "Test Task List"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_list_raises_on_empty_title(
        self, client: GoogleTasksAPIClient
    ) -> None:
        """create_task_list() should raise on empty title."""
        with pytest.raises(GoogleTasksValidationError):
            await client.create_task_list("")


class TestGoogleTasksClientTasks:
    """Tests for task operations."""

    @pytest.fixture
    def client(self) -> GoogleTasksAPIClient:
        """Create client with mock credentials."""
        return GoogleTasksAPIClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            access_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_list_tasks_success(self, client: GoogleTasksAPIClient) -> None:
        """list_tasks() should return TasksListResponse."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["tasks_list"]

            response = await client.list_tasks(SAMPLE_DATA["default_task_list_id"])

            assert len(response.items) == 2
            assert response.items[0].title == "Task 1"
            assert response.items[1].title == "Task 2"

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, client: GoogleTasksAPIClient) -> None:
        """list_tasks() should accept show_completed, show_deleted, show_hidden."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["tasks_list"]

            await client.list_tasks(
                task_list_id=SAMPLE_DATA["default_task_list_id"],
                show_completed=False,
                show_deleted=True,
                show_hidden=False,
            )

            params = mock_request.call_args[1]["params"]
            assert params["showCompleted"] is False
            assert params["showDeleted"] is True
            assert params["showHidden"] is False

    @pytest.mark.asyncio
    async def test_create_task_success(self, client: GoogleTasksAPIClient) -> None:
        """create_task() should return created Task."""
        task_create = TaskCreate(
            title=SAMPLE_DATA["task_title"],
            description=SAMPLE_DATA["task_description"],
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_created"]

            task = await client.create_task(SAMPLE_DATA["default_task_list_id"], task_create)

            assert task.id == "task-abc-123"
            assert task.title == SAMPLE_DATA["task_title"]

    @pytest.mark.asyncio
    async def test_get_task_success(self, client: GoogleTasksAPIClient) -> None:
        """get_task() should return Task."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_created"]

            task = await client.get_task(
                SAMPLE_DATA["default_task_list_id"], SAMPLE_DATA["task_id"]
            )

            assert task.id == "task-abc-123"
            assert task.title == SAMPLE_DATA["task_title"]

    @pytest.mark.asyncio
    async def test_get_task_raises_on_not_found(self, client: GoogleTasksAPIClient) -> None:
        """get_task() should raise GoogleTasksNotFoundError if not found."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GoogleTasksNotFoundError("Task not found")

            with pytest.raises(GoogleTasksNotFoundError):
                await client.get_task(SAMPLE_DATA["default_task_list_id"], "nonexistent-task")

    @pytest.mark.asyncio
    async def test_update_task_success(self, client: GoogleTasksAPIClient) -> None:
        """update_task() should return updated Task."""
        task_update = TaskUpdate(status=SAMPLE_DATA["status_completed"])

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_RESPONSES["task_completed"]

            task = await client.update_task(
                SAMPLE_DATA["default_task_list_id"],
                SAMPLE_DATA["task_id"],
                task_update,
            )

            assert task.status == SAMPLE_DATA["status_completed"]

    @pytest.mark.asyncio
    async def test_delete_task_success(self, client: GoogleTasksAPIClient) -> None:
        """delete_task() should successfully delete task."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = None

            await client.delete_task(SAMPLE_DATA["default_task_list_id"], SAMPLE_DATA["task_id"])

            mock_request.assert_called_once()


class TestGoogleTasksClientErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.fixture
    def client(self) -> GoogleTasksAPIClient:
        """Create client with mock credentials."""
        return GoogleTasksAPIClient(
            credentials_json=MOCK_SERVICE_ACCOUNT_CREDENTIALS,
            access_token="test-token",
            max_retries=2,
            retry_base_delay=0.1,
        )

    @pytest.mark.asyncio
    async def test_request_raises_on_401_unauthorized(self, client: GoogleTasksAPIClient) -> None:
        """_request() should raise GoogleTasksAuthError on 401."""
        with patch("httpx.AsyncClient.request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            with pytest.raises(GoogleTasksAuthError):
                await client._request("GET", "/users/@me/lists")

    @pytest.mark.asyncio
    async def test_request_raises_on_403_forbidden(self, client: GoogleTasksAPIClient) -> None:
        """_request() should raise GoogleTasksQuotaExceeded on 403."""
        with patch("httpx.AsyncClient.request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_request.return_value = mock_response

            with pytest.raises(GoogleTasksQuotaExceeded):
                await client._request("GET", "/users/@me/lists")

    @pytest.mark.asyncio
    async def test_request_raises_on_404_not_found(self, client: GoogleTasksAPIClient) -> None:
        """_request() should raise GoogleTasksNotFoundError on 404."""
        with patch("httpx.AsyncClient.request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_request.return_value = mock_response

            with pytest.raises(GoogleTasksNotFoundError):
                await client._request("GET", "/users/@me/lists/nonexistent")

    @pytest.mark.asyncio
    async def test_request_retries_on_429_rate_limit(self, client: GoogleTasksAPIClient) -> None:
        """_request() should retry on 429 rate limit with backoff."""
        with patch("httpx.AsyncClient.request") as mock_request:
            # First response: rate limited
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"Retry-After": "1"}

            # Second response: success
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"items": []}

            mock_request.side_effect = [mock_response_429, mock_response_200]

            result = await client._request("GET", "/users/@me/lists")

            assert result == {"items": []}
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_retries_on_500_server_error(self, client: GoogleTasksAPIClient) -> None:
        """_request() should retry on 500 server error with backoff."""
        with patch("httpx.AsyncClient.request") as mock_request:
            # First response: server error
            mock_response_500 = MagicMock()
            mock_response_500.status_code = 500

            # Second response: success
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"items": []}

            mock_request.side_effect = [mock_response_500, mock_response_200]

            result = await client._request("GET", "/users/@me/lists")

            assert result == {"items": []}
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_retries_on_timeout(self, client: GoogleTasksAPIClient) -> None:
        """_request() should retry on timeout."""
        import httpx

        with patch("httpx.AsyncClient.request") as mock_request:
            # First response: timeout
            # Second response: success
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": []}

            mock_request.side_effect = [
                httpx.TimeoutException("timeout"),
                mock_response,
            ]

            result = await client._request("GET", "/users/@me/lists")

            assert result == {"items": []}
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_raises_after_max_retries(self, client: GoogleTasksAPIClient) -> None:
        """_request() should raise after exhausting retries."""
        import httpx

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.side_effect = httpx.TimeoutException("timeout")

            with pytest.raises(GoogleTasksAPIError):
                await client._request("GET", "/users/@me/lists")

            # Should try max_retries times
            assert mock_request.call_count == client.max_retries
