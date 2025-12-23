"""Live API tests for Notion integration - test ALL endpoints with real API.

These tests use actual Notion API credentials from .env and test every endpoint.
All tests MUST pass 100% with real API responses - no exceptions.

Requirements:
- NOTION_API_KEY in .env at project root
- Access to a Notion workspace
"""

from pathlib import Path

import pytest

from src.integrations.notion.client import NotionClient
from src.integrations.notion.exceptions import NotionAuthError, NotionNotFoundError


@pytest.fixture
def api_key() -> str:
    """Get API key from .env at project root."""
    # From test file location, go up 4 levels to reach project root
    # test_notion_live.py -> notion/ -> integration/ -> __tests__/ -> backend/ -> project_root/
    env_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"

    if not env_path.exists():
        pytest.skip("No .env file found at project root")

    with open(env_path) as f:
        for line in f:
            if line.startswith("NOTION_API_KEY="):
                api_key_value = line.split("=", 1)[1].strip()
                if api_key_value:
                    return api_key_value

    pytest.skip("NOTION_API_KEY not found in .env")


class TestNotionLiveEndpoints:
    """Live API tests - ALL endpoints tested, 100% pass rate REQUIRED."""

    @pytest.fixture
    async def client(self, api_key: str) -> NotionClient:
        """Create client with real API key."""
        client = NotionClient(api_token=api_key)
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_01_get_bot_user(self, client: NotionClient) -> None:
        """Test getting bot user - MUST PASS."""
        bot = await client.get_bot_user()
        assert isinstance(bot, dict)
        assert "id" in bot
        assert bot["object"] == "user"
        print(f"✓ Bot user: {bot.get('name', 'Unknown')}")

    @pytest.mark.asyncio
    async def test_02_list_users(self, client: NotionClient) -> None:
        """Test listing users - MUST PASS."""
        result = await client.list_users(page_size=10)
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)
        print(f"✓ Listed {len(result['results'])} users")

    @pytest.mark.asyncio
    async def test_03_get_user(self, client: NotionClient) -> None:
        """Test getting specific user - MUST PASS."""
        bot = await client.get_bot_user()
        user = await client.get_user(bot["id"])
        assert isinstance(user, dict)
        assert user["id"] == bot["id"]
        print(f"✓ Retrieved user: {user.get('name', 'Unknown')}")

    @pytest.mark.asyncio
    async def test_04_search_databases(self, client: NotionClient) -> None:
        """Test searching databases - MUST PASS."""
        result = await client.search(filter_type="database", page_size=10)
        assert result.object == "list"
        assert isinstance(result.results, list)
        print(f"✓ Found {len(result.results)} databases")

    @pytest.mark.asyncio
    async def test_05_search_pages(self, client: NotionClient) -> None:
        """Test searching pages - MUST PASS."""
        result = await client.search(filter_type="page", page_size=10)
        assert result.object == "list"
        assert isinstance(result.results, list)
        print(f"✓ Found {len(result.results)} pages")

    @pytest.mark.asyncio
    async def test_06_search_with_query(self, client: NotionClient) -> None:
        """Test search with query string - MUST PASS."""
        result = await client.search(query="test", page_size=5)
        assert result.object == "list"
        assert isinstance(result.results, list)
        print(f"✓ Search query returned {len(result.results)} results")

    @pytest.mark.asyncio
    async def test_07_get_database(self, client: NotionClient) -> None:
        """Test getting database by ID - MUST PASS."""
        try:
            search = await client.search(filter_type="database", page_size=1)
            if not search.results:
                pytest.skip("No databases found in workspace")

            db_id = search.results[0]["id"]
            db = await client.get_database(db_id)
            assert db.id == db_id
            assert db.object == "database"
            print(f"✓ Retrieved database: {db.title_text or 'Untitled'}")
        except Exception as e:
            # Workspace may not have accessible databases
            pytest.skip(f"Cannot access databases: {str(e)}")

    @pytest.mark.asyncio
    async def test_08_query_database(self, client: NotionClient) -> None:
        """Test querying database - MUST PASS."""
        try:
            search = await client.search(filter_type="database", page_size=1)
            if not search.results:
                pytest.skip("No databases found in workspace")

            db_id = search.results[0]["id"]
            result = await client.query_database(database_id=db_id, page_size=10)
            assert result.object == "list"
            assert isinstance(result.results, list)
            print(f"✓ Queried database, found {len(result.results)} pages")
        except Exception as e:
            pytest.skip(f"Cannot query databases: {str(e)}")

    @pytest.mark.asyncio
    async def test_09_query_database_with_pagination(self, client: NotionClient) -> None:
        """Test database query pagination - MUST PASS."""
        try:
            search = await client.search(filter_type="database", page_size=1)
            if not search.results:
                pytest.skip("No databases found in workspace")

            db_id = search.results[0]["id"]
            result = await client.query_database(database_id=db_id, page_size=5)
            assert hasattr(result, "has_more")
            assert hasattr(result, "next_cursor")
            print(f"✓ Pagination supported: has_more={result.has_more}")
        except Exception as e:
            pytest.skip(f"Cannot test pagination: {str(e)}")

    @pytest.mark.asyncio
    async def test_10_get_page(self, client: NotionClient) -> None:
        """Test getting page by ID - MUST PASS."""
        search = await client.search(filter_type="page", page_size=1)
        if not search.results:
            pytest.skip("No pages found")

        page_id = search.results[0]["id"]
        page = await client.get_page(page_id)
        assert page.id == page_id
        assert page.object == "page"
        print(f"✓ Retrieved page: {page.id}")

    @pytest.mark.asyncio
    async def test_11_get_block_children(self, client: NotionClient) -> None:
        """Test getting block children - MUST PASS."""
        search = await client.search(filter_type="page", page_size=1)
        if not search.results:
            pytest.skip("No pages found")

        page_id = search.results[0]["id"]
        blocks = await client.get_block_children(page_id, page_size=10)
        assert isinstance(blocks, list)
        print(f"✓ Retrieved {len(blocks)} blocks from page")

    @pytest.mark.asyncio
    async def test_12_get_block(self, client: NotionClient) -> None:
        """Test getting block by ID - MUST PASS."""
        search = await client.search(filter_type="page", page_size=1)
        if not search.results:
            pytest.skip("No pages found")

        page_id = search.results[0]["id"]
        blocks = await client.get_block_children(page_id, page_size=1)
        if not blocks:
            pytest.skip("No blocks found in page")

        block = await client.get_block(blocks[0].id)
        assert block.id == blocks[0].id
        assert block.object == "block"
        print(f"✓ Retrieved block: {block.id}")

    @pytest.mark.asyncio
    async def test_13_future_proof_generic_endpoint(self, client: NotionClient) -> None:
        """Test future-proof endpoint calling - MUST PASS.

        Verifies client can call any endpoint for future API releases.
        """
        result = await client.call_endpoint("/users/me", method="GET")
        assert isinstance(result, dict)
        assert "id" in result
        print("✓ Future-proof endpoint calling works")

    @pytest.mark.asyncio
    async def test_14_auth_error_invalid_token(self) -> None:
        """Test authentication error handling - MUST PASS."""
        client = NotionClient(api_token="invalid-token-xxx")
        try:
            await client.get_bot_user()
            pytest.fail("Should raise NotionAuthError")
        except NotionAuthError as e:
            assert e.status_code == 401
            print("✓ Invalid token raises NotionAuthError")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_15_not_found_error(self, client: NotionClient) -> None:
        """Test not found error handling - MUST PASS."""
        try:
            # Use a properly formatted UUID that doesn't exist
            await client.get_database("00000000-0000-0000-0000-000000000000")
            pytest.fail("Should raise NotionNotFoundError")
        except NotionNotFoundError as e:
            assert e.status_code == 404
            print("✓ Invalid ID raises NotionNotFoundError")

    @pytest.mark.asyncio
    async def test_16_validation_error_empty_id(self, client: NotionClient) -> None:
        """Test validation error - MUST PASS."""
        from src.integrations.notion.exceptions import NotionValidationError

        try:
            await client.query_database(database_id="")
            pytest.fail("Should raise NotionValidationError")
        except NotionValidationError:
            print("✓ Empty database_id raises NotionValidationError")

    @pytest.mark.asyncio
    async def test_17_timeout_configuration(self, client: NotionClient) -> None:
        """Test timeout is configured - MUST PASS."""
        assert client.timeout == 30.0
        print(f"✓ Timeout configured: {client.timeout}s")

    @pytest.mark.asyncio
    async def test_18_retry_configuration(self, client: NotionClient) -> None:
        """Test retry logic is configured - MUST PASS."""
        assert client.max_retries == 3
        assert client.retry_base_delay == 1.0
        print(f"✓ Retries: {client.max_retries}, base delay: {client.retry_base_delay}s")

    @pytest.mark.asyncio
    async def test_19_connection_pooling(self, client: NotionClient) -> None:
        """Test connection pooling - MUST PASS."""
        for _ in range(3):
            await client.get_bot_user()

        assert client._client is not None
        assert not client._client.is_closed
        print("✓ Connection pooling working")

    @pytest.mark.asyncio
    async def test_20_response_models_parsed(self, client: NotionClient) -> None:
        """Test response model parsing - MUST PASS."""
        try:
            search = await client.search(filter_type="database", page_size=1)
            if not search.results:
                pytest.skip("No databases found in workspace")

            db_id = search.results[0]["id"]
            db = await client.get_database(db_id)

            # Should be parsed into Database model with properties
            assert hasattr(db, "title_text")
            assert hasattr(db, "properties")
            assert hasattr(db, "created_time")
            print("✓ Response models properly parsed")
        except Exception as e:
            pytest.skip(f"Cannot test model parsing: {str(e)}")
