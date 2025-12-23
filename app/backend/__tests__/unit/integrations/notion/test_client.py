"""Unit tests for Notion API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from __tests__.fixtures.notion_fixtures import (
    BLOCK_ID_WITH_HYPHENS,
    DATABASE_ID_WITH_HYPHENS,
    PAGE_ID_WITH_HYPHENS,
    get_auth_error_response,
    get_not_found_error_response,
    get_rate_limit_error_response,
    get_sample_block,
    get_sample_database,
    get_sample_page,
    get_sample_query_result,
    get_sample_search_result,
    get_sample_user,
    get_validation_error_response,
)
from src.integrations.notion.client import NotionClient
from src.integrations.notion.exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)
from src.integrations.notion.models import Block, Database, Page


class TestNotionClientInitialization:
    """Tests for client initialization."""

    def test_init_with_api_token(self) -> None:
        """Test initialization with provided API token."""
        client = NotionClient(api_token="test-token")
        assert client.api_token == "test-token"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_init_missing_api_token(self) -> None:
        """Test initialization fails without API token."""
        with patch.dict("os.environ", {}, clear=True), pytest.raises(NotionAuthError):
            NotionClient()

    @patch.dict("os.environ", {"NOTION_API_KEY": "env-token"})  # pragma: allowlist secret
    def test_init_from_environment(self) -> None:
        """Test initialization reads API token from environment."""
        client = NotionClient()
        assert client.api_token == "env-token"

    def test_init_custom_timeout_and_retries(self) -> None:
        """Test initialization with custom timeout and retries."""
        client = NotionClient(
            api_token="test-token",
            timeout=60.0,
            max_retries=5,
            retry_base_delay=2.0,
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0


class TestNotionClientHeaders:
    """Tests for HTTP header generation."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    def test_get_headers(self, client: NotionClient) -> None:
        """Test header generation includes authorization."""
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"
        assert "Notion-Version" in headers


class TestNotionClientDatabase:
    """Tests for database operations."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_get_database_success(self, client: NotionClient) -> None:
        """Test successful database retrieval."""
        sample_data = get_sample_database()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_database(DATABASE_ID_WITH_HYPHENS)
            assert isinstance(result, Database)
            assert result.id == DATABASE_ID_WITH_HYPHENS
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_validation(self, client: NotionClient) -> None:
        """Test database retrieval validates input."""
        with pytest.raises(NotionValidationError):
            await client.get_database("")

    @pytest.mark.asyncio
    async def test_query_database_success(self, client: NotionClient) -> None:
        """Test successful database query."""
        query_result = get_sample_query_result()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = query_result
            result = await client.query_database(DATABASE_ID_WITH_HYPHENS)
            assert len(result.results) == 2
            assert result.has_more is False
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_database_with_filter(self, client: NotionClient) -> None:
        """Test database query with filter."""
        query_result = get_sample_query_result()
        filter_obj = {"property": "Status", "select": {"equals": "Active"}}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = query_result
            await client.query_database(DATABASE_ID_WITH_HYPHENS, filter=filter_obj)
            call_kwargs = mock.call_args[1]
            assert "json" in call_kwargs
            assert call_kwargs["json"]["filter"] == filter_obj

    @pytest.mark.asyncio
    async def test_create_database_success(self, client: NotionClient) -> None:
        """Test successful database creation."""
        sample_data = get_sample_database()
        parent = {"type": "workspace", "workspace": True}
        properties = {"Name": {"title": {}}}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.create_database(parent, "Test DB", properties)
            assert isinstance(result, Database)
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_validation(self, client: NotionClient) -> None:
        """Test database creation validates required fields."""
        with pytest.raises(NotionValidationError):
            await client.create_database({}, "", {})

    @pytest.mark.asyncio
    async def test_update_database_success(self, client: NotionClient) -> None:
        """Test successful database update."""
        sample_data = get_sample_database()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.update_database(DATABASE_ID_WITH_HYPHENS, title="New Title")
            assert isinstance(result, Database)
            mock.assert_called_once()


class TestNotionClientPage:
    """Tests for page operations."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_get_page_success(self, client: NotionClient) -> None:
        """Test successful page retrieval."""
        sample_data = get_sample_page()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_page(PAGE_ID_WITH_HYPHENS)
            assert isinstance(result, Page)
            assert result.id == PAGE_ID_WITH_HYPHENS

    @pytest.mark.asyncio
    async def test_create_page_success(self, client: NotionClient) -> None:
        """Test successful page creation."""
        sample_data = get_sample_page()
        parent = {"database_id": DATABASE_ID_WITH_HYPHENS}
        properties = {"Name": {"title": [{"text": {"content": "Test Page"}}]}}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.create_page(parent, properties)
            assert isinstance(result, Page)

    @pytest.mark.asyncio
    async def test_update_page_success(self, client: NotionClient) -> None:
        """Test successful page update."""
        sample_data = get_sample_page()
        properties = {"Status": {"select": {"name": "Active"}}}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.update_page(PAGE_ID_WITH_HYPHENS, properties=properties)
            assert isinstance(result, Page)

    @pytest.mark.asyncio
    async def test_archive_page_success(self, client: NotionClient) -> None:
        """Test successful page archival."""
        sample_data = get_sample_page()
        sample_data["archived"] = True
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.archive_page(PAGE_ID_WITH_HYPHENS)
            assert isinstance(result, Page)


class TestNotionClientBlock:
    """Tests for block operations."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_get_block_success(self, client: NotionClient) -> None:
        """Test successful block retrieval."""
        sample_data = get_sample_block()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_block(BLOCK_ID_WITH_HYPHENS)
            assert isinstance(result, Block)
            assert result.id == BLOCK_ID_WITH_HYPHENS

    @pytest.mark.asyncio
    async def test_get_block_children_success(self, client: NotionClient) -> None:
        """Test successful block children retrieval."""
        sample_data = {"results": [get_sample_block()]}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_block_children(PAGE_ID_WITH_HYPHENS)
            assert len(result) == 1
            assert isinstance(result[0], Block)

    @pytest.mark.asyncio
    async def test_append_block_children_success(self, client: NotionClient) -> None:
        """Test successful block children append."""
        sample_data = {"results": [get_sample_block()]}
        children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.append_block_children(PAGE_ID_WITH_HYPHENS, children)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_update_block_success(self, client: NotionClient) -> None:
        """Test successful block update."""
        sample_data = get_sample_block()
        block_data = {"paragraph": {"rich_text": []}}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.update_block(BLOCK_ID_WITH_HYPHENS, block_data)
            assert isinstance(result, Block)

    @pytest.mark.asyncio
    async def test_delete_block_success(self, client: NotionClient) -> None:
        """Test successful block deletion."""
        sample_data = get_sample_block()
        sample_data["archived"] = True
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.delete_block(BLOCK_ID_WITH_HYPHENS)
            assert isinstance(result, Block)


class TestNotionClientUser:
    """Tests for user operations."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_get_user_success(self, client: NotionClient) -> None:
        """Test successful user retrieval."""
        sample_data = get_sample_user()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_user("user-id")
            assert result["id"] == sample_data["id"]

    @pytest.mark.asyncio
    async def test_list_users_success(self, client: NotionClient) -> None:
        """Test successful user list retrieval."""
        sample_data = {"results": [get_sample_user()], "has_more": False}
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.list_users()
            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_get_bot_user_success(self, client: NotionClient) -> None:
        """Test successful bot user retrieval."""
        sample_data = get_sample_user()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.get_bot_user()
            assert result["id"] == sample_data["id"]


class TestNotionClientSearch:
    """Tests for search operations."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_search_success(self, client: NotionClient) -> None:
        """Test successful search."""
        sample_data = get_sample_search_result()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.search(query="test")
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_search_with_filter(self, client: NotionClient) -> None:
        """Test search with type filter."""
        sample_data = get_sample_search_result()
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = sample_data
            result = await client.search(filter_type="database")
            assert len(result.results) == 2


class TestNotionClientErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> NotionClient:
        """Create test client."""
        return NotionClient(api_token="test-token")

    @pytest.mark.asyncio
    async def test_handle_auth_error(self, client: NotionClient) -> None:
        """Test authentication error handling."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        response.json.return_value = get_auth_error_response()

        with pytest.raises(NotionAuthError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, client: NotionClient) -> None:
        """Test rate limit error handling."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "5"}
        response.json.return_value = get_rate_limit_error_response()

        with pytest.raises(NotionRateLimitError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handle_not_found_error(self, client: NotionClient) -> None:
        """Test not found error handling."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 404
        response.json.return_value = get_not_found_error_response()

        with pytest.raises(NotionNotFoundError):
            await client._handle_response(response)

    @pytest.mark.asyncio
    async def test_handle_validation_error(self, client: NotionClient) -> None:
        """Test validation error handling."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        response.json.return_value = get_validation_error_response()

        with pytest.raises(NotionValidationError):
            await client._handle_response(response)

    def test_is_retryable_timeout(self, client: NotionClient) -> None:
        """Test timeout errors are retryable."""
        error = httpx.TimeoutException("Timeout")
        assert client._is_retryable_error(error) is True

    def test_is_retryable_network(self, client: NotionClient) -> None:
        """Test network errors are retryable."""
        error = httpx.NetworkError("Network error")
        assert client._is_retryable_error(error) is True

    def test_is_retryable_server_error(self, client: NotionClient) -> None:
        """Test 5xx errors are retryable."""
        error = NotionAPIError("Server error", status_code=500)
        assert client._is_retryable_error(error) is True

    def test_is_retryable_rate_limit(self, client: NotionClient) -> None:
        """Test rate limit errors are retryable."""
        error = NotionRateLimitError()
        assert client._is_retryable_error(error) is True

    def test_is_not_retryable_auth(self, client: NotionClient) -> None:
        """Test auth errors are not retryable."""
        error = NotionAuthError()
        assert client._is_retryable_error(error) is False


class TestNotionClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_closes_client(self) -> None:
        """Test close method closes HTTP client."""
        client = NotionClient(api_token="test-token")
        # Initialize client
        _ = client.client
        assert client._client is not None
        # Close client
        await client.close()
        assert client._client is None
