"""Notion API integration client for database and page management.

Provides async access to Notion REST API including:
- Database CRUD operations (query, retrieve, create, update)
- Page operations (create, retrieve, update, archive)
- Block operations (append children, retrieve, update, delete)
- User operations (retrieve, list)
- Search functionality

Rate Limits:
- 3 requests per second per integration
- HTTP 429 = Rate limited

Example:
    >>> from src.integrations.notion.client import NotionClient
    >>> client = NotionClient(api_token=os.environ["NOTION_API_KEY"])
    >>> databases = await client.search(filter_type="database")
    >>> pages = await client.query_database(database_id="...", filter={})
"""

import asyncio
import logging
import os
from typing import Any

import httpx

from src.integrations.notion.exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)
from src.integrations.notion.models import Block, Database, Page, QueryResult, SearchResult

logger = logging.getLogger(__name__)


class NotionClient:
    """Async client for Notion API.

    Supports database queries, page operations, block manipulation,
    and search with comprehensive error handling and exponential backoff retry logic.

    Attributes:
        api_token: Notion integration token.
        api_version: Notion API version (default: 2025-09-03).
    """

    # Notion API endpoints
    API_BASE = "https://api.notion.com/v1"
    NOTION_API_VERSION = "2025-09-03"

    # Rate limiting (3 requests per second)
    RATE_LIMIT_REQUESTS = 3
    RATE_LIMIT_WINDOW = 1.0

    def __init__(
        self,
        api_token: str | None = None,
        api_version: str = NOTION_API_VERSION,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize Notion client.

        Args:
            api_token: Notion integration token. If None, reads from NOTION_API_KEY env var.
            api_version: Notion API version to use.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            retry_base_delay: Base delay for exponential backoff.

        Raises:
            NotionAuthError: If no API token is provided.
        """
        self.api_token = api_token or os.getenv("NOTION_API_KEY")
        if not self.api_token:
            raise NotionAuthError("NOTION_API_KEY not provided or found in environment")

        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

        logger.info("Initialized Notion client")

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy HTTP client creation with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON response data.

        Raises:
            NotionAuthError: For 401 responses.
            NotionRateLimitError: For 429 responses.
            NotionNotFoundError: For 404 responses.
            NotionValidationError: For 400 responses.
            NotionError: For other error responses.
        """
        data: dict[str, Any]
        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text}

        if response.status_code == 401:
            raise NotionAuthError(
                message="Authentication failed - invalid or expired API token",
                response_data=data,
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise NotionRateLimitError(
                message="Rate limit exceeded - wait before retrying",
                retry_after=int(retry_after) if retry_after else None,
                response_data=data,
            )

        if response.status_code == 404:
            raise NotionNotFoundError(
                message="Resource not found",
                response_data=data,
            )

        if response.status_code == 400:
            error_message = data.get("message", "Validation error")
            raise NotionValidationError(
                message=f"Validation error: {error_message}",
                response_data=data,
            )

        if response.status_code >= 400:
            error_message = data.get("message", data.get("error", "Unknown error"))
            raise NotionAPIError(
                message=f"API error: {error_message}",
                status_code=response.status_code,
                response_data=data,
            )

        return data

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable.

        Args:
            error: The exception to check.

        Returns:
            True if the error is retryable, False otherwise.
        """
        if isinstance(error, httpx.TimeoutException | httpx.NetworkError):
            return True
        if isinstance(error, NotionError):
            # Retry on 5xx errors (server errors)
            if error.status_code and 500 <= error.status_code < 600:
                return True
            # Retry on rate limit (with exponential backoff)
            if isinstance(error, NotionRateLimitError):
                return True
        return False

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE, etc.).
            endpoint: API endpoint path.
            **kwargs: Additional arguments for httpx request.

        Returns:
            Parsed JSON response data.

        Raises:
            NotionError: After all retries exhausted.
        """
        url = f"{self.API_BASE}{endpoint}"
        headers = self._get_headers()

        # Merge custom headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )
                return await self._handle_response(response)

            except Exception as error:
                last_error = error
                is_retryable = self._is_retryable_error(error)

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[Notion] Request failed: {error}",
                        extra={
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = self.retry_base_delay * (2**attempt)
                jitter = delay * (0.1 + 0.4 * (attempt / self.max_retries))
                delay += jitter

                logger.warning(
                    f"[Notion] Request failed (attempt {attempt + 1}), retrying in {delay:.2f}s...",
                )
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise NotionError("Unknown error during request")

    async def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> QueryResult:
        """Query a Notion database.

        Args:
            database_id: ID of the database to query.
            filter: Filter object for querying.
            sorts: Sort criteria.
            start_cursor: Cursor for pagination.
            page_size: Number of results per page (max 100).

        Returns:
            QueryResult containing pages and pagination info.

        Raises:
            NotionValidationError: If database_id is invalid.
            NotionError: If API request fails.
        """
        if not database_id:
            raise NotionValidationError("database_id is required")

        payload: dict[str, Any] = {}
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
        if start_cursor:
            payload["start_cursor"] = start_cursor
        if page_size:
            payload["page_size"] = min(page_size, 100)

        response_data = await self._request_with_retry(
            "POST",
            f"/databases/{database_id}/query",
            json=payload,
        )

        # Convert to QueryResult model with parsed pages
        results = [Page(**page) for page in response_data.get("results", [])]
        return QueryResult(
            object=response_data.get("object", "list"),
            results=results,
            next_cursor=response_data.get("next_cursor"),
            has_more=response_data.get("has_more", False),
        )

    async def get_database(self, database_id: str) -> Database:
        """Retrieve a Notion database.

        Args:
            database_id: ID of the database.

        Returns:
            Database object.

        Raises:
            NotionNotFoundError: If database doesn't exist.
            NotionError: If API request fails.
        """
        if not database_id:
            raise NotionValidationError("database_id is required")

        response_data = await self._request_with_retry(
            "GET",
            f"/databases/{database_id}",
        )

        return Database(**response_data)

    async def create_database(
        self,
        parent: dict[str, Any],
        title: str,
        properties: dict[str, Any],
        icon: dict[str, Any] | None = None,
        cover: dict[str, Any] | None = None,
    ) -> Database:
        """Create a new Notion database.

        Args:
            parent: Parent object (page_id or workspace).
            title: Database title.
            properties: Database property schema.
            icon: Optional icon for database.
            cover: Optional cover image for database.

        Returns:
            Created Database object.

        Raises:
            NotionValidationError: If required fields are missing.
            NotionError: If API request fails.
        """
        if not title or not properties:
            raise NotionValidationError("title and properties are required")

        payload: dict[str, Any] = {
            "parent": parent,
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover

        response_data = await self._request_with_retry(
            "POST",
            "/databases",
            json=payload,
        )

        return Database(**response_data)

    async def update_database(
        self,
        database_id: str,
        title: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> Database:
        """Update a Notion database.

        Args:
            database_id: ID of the database.
            title: New title (optional).
            properties: Updated properties (optional).

        Returns:
            Updated Database object.

        Raises:
            NotionValidationError: If no update fields provided.
            NotionError: If API request fails.
        """
        if not database_id:
            raise NotionValidationError("database_id is required")

        if not title and not properties:
            raise NotionValidationError("At least one of title or properties must be provided")

        payload: dict[str, Any] = {}
        if title:
            payload["title"] = [{"type": "text", "text": {"content": title}}]
        if properties:
            payload["properties"] = properties

        response_data = await self._request_with_retry(
            "PATCH",
            f"/databases/{database_id}",
            json=payload,
        )

        return Database(**response_data)

    async def get_page(self, page_id: str) -> Page:
        """Retrieve a Notion page.

        Args:
            page_id: ID of the page.

        Returns:
            Page object.

        Raises:
            NotionNotFoundError: If page doesn't exist.
            NotionError: If API request fails.
        """
        if not page_id:
            raise NotionValidationError("page_id is required")

        response_data = await self._request_with_retry(
            "GET",
            f"/pages/{page_id}",
        )

        return Page(**response_data)

    async def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
        icon: dict[str, Any] | None = None,
        cover: dict[str, Any] | None = None,
    ) -> Page:
        """Create a new Notion page.

        Args:
            parent: Parent object (database_id, page_id, or workspace).
            properties: Page properties (must match database schema).
            children: Optional child blocks.
            icon: Optional page icon.
            cover: Optional page cover.

        Returns:
            Created Page object.

        Raises:
            NotionValidationError: If required fields are missing.
            NotionError: If API request fails.
        """
        if not parent or not properties:
            raise NotionValidationError("parent and properties are required")

        payload: dict[str, Any] = {
            "parent": parent,
            "properties": properties,
        }
        if children:
            payload["children"] = children
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover

        response_data = await self._request_with_retry(
            "POST",
            "/pages",
            json=payload,
        )

        return Page(**response_data)

    async def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        icon: dict[str, Any] | None = None,
        cover: dict[str, Any] | None = None,
    ) -> Page:
        """Update a Notion page.

        Args:
            page_id: ID of the page.
            properties: Updated properties.
            icon: Updated icon.
            cover: Updated cover.

        Returns:
            Updated Page object.

        Raises:
            NotionValidationError: If no update fields provided.
            NotionError: If API request fails.
        """
        if not page_id:
            raise NotionValidationError("page_id is required")

        if not properties and not icon and not cover:
            raise NotionValidationError("At least one update field must be provided")

        payload: dict[str, Any] = {}
        if properties:
            payload["properties"] = properties
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover

        response_data = await self._request_with_retry(
            "PATCH",
            f"/pages/{page_id}",
            json=payload,
        )

        return Page(**response_data)

    async def archive_page(self, page_id: str) -> Page:
        """Archive a Notion page.

        Args:
            page_id: ID of the page to archive.

        Returns:
            Updated Page object.

        Raises:
            NotionError: If API request fails.
        """
        if not page_id:
            raise NotionValidationError("page_id is required")

        response_data = await self._request_with_retry(
            "PATCH",
            f"/pages/{page_id}",
            json={"archived": True},
        )

        return Page(**response_data)

    async def get_block(self, block_id: str) -> Block:
        """Retrieve a Notion block.

        Args:
            block_id: ID of the block.

        Returns:
            Block object.

        Raises:
            NotionNotFoundError: If block doesn't exist.
            NotionError: If API request fails.
        """
        if not block_id:
            raise NotionValidationError("block_id is required")

        response_data = await self._request_with_retry(
            "GET",
            f"/blocks/{block_id}",
        )

        return Block(**response_data)

    async def get_block_children(
        self,
        block_id: str,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> list[Block]:
        """Retrieve children blocks of a parent block.

        Args:
            block_id: ID of the parent block.
            start_cursor: Cursor for pagination.
            page_size: Number of results per page.

        Returns:
            List of Block objects.

        Raises:
            NotionError: If API request fails.
        """
        if not block_id:
            raise NotionValidationError("block_id is required")

        params: dict[str, Any] = {"page_size": min(page_size, 100)}
        if start_cursor:
            params["start_cursor"] = start_cursor

        response_data = await self._request_with_retry(
            "GET",
            f"/blocks/{block_id}/children",
            params=params,
        )

        blocks = [Block(**block) for block in response_data.get("results", [])]
        return blocks

    async def append_block_children(
        self,
        block_id: str,
        children: list[dict[str, Any]],
    ) -> list[Block]:
        """Append child blocks to a parent block.

        Args:
            block_id: ID of the parent block.
            children: List of block objects to append.

        Returns:
            List of created Block objects.

        Raises:
            NotionValidationError: If children list is empty.
            NotionError: If API request fails.
        """
        if not block_id or not children:
            raise NotionValidationError("block_id and children are required")

        response_data = await self._request_with_retry(
            "PATCH",
            f"/blocks/{block_id}/children",
            json={"children": children},
        )

        blocks = [Block(**block) for block in response_data.get("results", [])]
        return blocks

    async def update_block(
        self,
        block_id: str,
        block_data: dict[str, Any],
    ) -> Block:
        """Update a Notion block.

        Args:
            block_id: ID of the block.
            block_data: Updated block data (depends on block type).

        Returns:
            Updated Block object.

        Raises:
            NotionError: If API request fails.
        """
        if not block_id or not block_data:
            raise NotionValidationError("block_id and block_data are required")

        response_data = await self._request_with_retry(
            "PATCH",
            f"/blocks/{block_id}",
            json=block_data,
        )

        return Block(**response_data)

    async def delete_block(self, block_id: str) -> Block:
        """Delete a Notion block.

        Args:
            block_id: ID of the block.

        Returns:
            Deleted Block object.

        Raises:
            NotionError: If API request fails.
        """
        if not block_id:
            raise NotionValidationError("block_id is required")

        response_data = await self._request_with_retry(
            "DELETE",
            f"/blocks/{block_id}",
        )

        return Block(**response_data)

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Retrieve a Notion user.

        Args:
            user_id: ID of the user.

        Returns:
            User object as dictionary.

        Raises:
            NotionError: If API request fails.
        """
        if not user_id:
            raise NotionValidationError("user_id is required")

        return await self._request_with_retry(
            "GET",
            f"/users/{user_id}",
        )

    async def list_users(
        self,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """List all Notion users.

        Args:
            start_cursor: Cursor for pagination.
            page_size: Number of results per page.

        Returns:
            Dictionary with users list and pagination info.

        Raises:
            NotionError: If API request fails.
        """
        params: dict[str, Any] = {"page_size": min(page_size, 100)}
        if start_cursor:
            params["start_cursor"] = start_cursor

        return await self._request_with_retry(
            "GET",
            "/users",
            params=params,
        )

    async def get_bot_user(self) -> dict[str, Any]:
        """Retrieve the bot user (integration).

        Returns:
            Bot user object.

        Raises:
            NotionError: If API request fails.
        """
        return await self._request_with_retry(
            "GET",
            "/users/me",
        )

    async def search(
        self,
        query: str | None = None,
        filter_type: str | None = None,
        sort: dict[str, Any] | None = None,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> SearchResult:
        """Search Notion by title.

        Args:
            query: Search query string.
            filter_type: "page", "data_source" (databases), or None for all.
                Note: In API v2025-09-03+, "database" was replaced with "data_source".
            sort: Sort criteria.
            start_cursor: Cursor for pagination.
            page_size: Number of results per page.

        Returns:
            SearchResult containing matching pages/databases.

        Raises:
            NotionError: If API request fails.
        """
        payload: dict[str, Any] = {}
        if query:
            payload["query"] = query
        if filter_type:
            # Map old "database" to new "data_source" for API v2025-09-03+
            mapped_type = "data_source" if filter_type == "database" else filter_type
            payload["filter"] = {"value": mapped_type, "property": "object"}
        if sort:
            payload["sort"] = sort
        if start_cursor:
            payload["start_cursor"] = start_cursor
        if page_size:
            payload["page_size"] = min(page_size, 100)

        response_data = await self._request_with_retry(
            "POST",
            "/search",
            json=payload,
        )

        return SearchResult(
            object=response_data.get("object", "list"),
            results=response_data.get("results", []),
            next_cursor=response_data.get("next_cursor"),
            has_more=response_data.get("has_more", False),
        )

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling new endpoints that may be released in the future
        without requiring code changes to this client.

        Args:
            endpoint: Endpoint path (e.g., "/users/me", "/v1/new-endpoint").
            method: HTTP method (GET, POST, PATCH, DELETE, etc.). Default: GET.
            **kwargs: Request parameters (json, params, headers, etc.).

        Returns:
            API response as dictionary.

        Raises:
            NotionError: If API request fails.

        Example:
            >>> result = await client.call_endpoint(
            ...     "/users/me",
            ...     method="GET"
            ... )
            >>> new_data = await client.call_endpoint(
            ...     "/databases/future-id/future-action",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
        """
        return await self._request_with_retry(method, endpoint, **kwargs)

    async def close(self) -> None:
        """Close the HTTP client connection.

        Should be called when done with the client.
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
