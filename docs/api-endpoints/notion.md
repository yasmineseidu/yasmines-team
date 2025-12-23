# Notion API Endpoints

## Overview

- **Base URL:** `https://api.notion.com/v1`
- **Authentication:** Bearer token (from `NOTION_API_KEY` environment variable)
- **Rate Limits:** 3 requests per second per integration
- **API Version:** 2025-09-03 (latest)
- **Response Format:** JSON

## Setup

### Getting API Token

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create new integration
3. Copy the "Internal Integration Token"
4. Store in `.env` as: `NOTION_API_KEY=ntn_xxxxxxxxxxxxx`

### Authentication

All requests require the Authorization header:

```
Authorization: Bearer {NOTION_API_KEY}
Notion-Version: 2025-09-03
Content-Type: application/json
```

## Endpoints

### Database Endpoints

#### Query Database

Query pages from a Notion database with optional filtering and sorting.

**Method:** `POST`
**Endpoint:** `/databases/{database_id}/query`

**Request:**

```python
result = await client.query_database(
    database_id="6d05f2e8-e5ed-45d1-a65c-de7e5e71e50f",
    filter={
        "property": "Status",
        "select": {"equals": "Active"}
    },
    sorts=[
        {
            "property": "Name",
            "direction": "ascending"
        }
    ],
    page_size=50
)
```

**Response:**

```json
{
  "object": "list",
  "results": [
    {
      "id": "page-id",
      "object": "page",
      "created_time": "2024-01-10T10:00:00.000Z",
      "last_edited_time": "2024-01-15T15:30:00.000Z",
      "archived": false,
      "properties": {
        "Name": {
          "id": "title",
          "type": "title",
          "title": [{"type": "text", "text": {"content": "Sample Page"}}]
        }
      }
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

**Parameters:**
- `database_id` (string, required): ID of the database
- `filter` (object, optional): Filter criteria
- `sorts` (array, optional): Sort order
- `start_cursor` (string, optional): Cursor for pagination
- `page_size` (int, optional): Results per page (1-100, default: 100)

#### Get Database

Retrieve database metadata.

**Method:** `GET`
**Endpoint:** `/databases/{database_id}`

**Request:**

```python
db = await client.get_database("6d05f2e8-e5ed-45d1-a65c-de7e5e71e50f")
print(db.title_text)  # Get plain text title
```

**Response:** Database object with schema, title, properties.

#### Create Database

Create a new database in a page or workspace.

**Method:** `POST`
**Endpoint:** `/databases`

**Request:**

```python
db = await client.create_database(
    parent={"page_id": "page-id"},
    title="My Database",
    properties={
        "Name": {"title": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "Active"},
                    {"name": "Inactive"}
                ]
            }
        }
    }
)
```

#### Update Database

Update database title and properties.

**Method:** `PATCH`
**Endpoint:** `/databases/{database_id}`

**Request:**

```python
db = await client.update_database(
    database_id="...",
    title="Updated Title",
    properties={"Status": {"select": {"options": [...]}}}
)
```

---

### Page Endpoints

#### Get Page

Retrieve a page with properties.

**Method:** `GET`
**Endpoint:** `/pages/{page_id}`

**Request:**

```python
page = await client.get_page("a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6")  # pragma: allowlist secret
print(page.archived)
```

#### Create Page

Create a new page in a database or as a child page.

**Method:** `POST`
**Endpoint:** `/pages`

**Request:**

```python
page = await client.create_page(
    parent={"database_id": "db-id"},
    properties={
        "Name": {
            "title": [{"text": {"content": "New Page"}}]
        },
        "Status": {
            "select": {"name": "Active"}
        }
    },
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Page content"}}
                ]
            }
        }
    ]
)
```

#### Update Page

Update page properties (title, fields, etc).

**Method:** `PATCH`
**Endpoint:** `/pages/{page_id}`

**Request:**

```python
page = await client.update_page(
    page_id="...",
    properties={
        "Status": {"select": {"name": "Completed"}},
        "Name": {
            "title": [{"text": {"content": "Updated Name"}}]
        }
    }
)
```

#### Archive Page

Archive (soft delete) a page.

**Method:** `PATCH`
**Endpoint:** `/pages/{page_id}`

**Request:**

```python
page = await client.archive_page("page-id")
```

---

### Block Endpoints

#### Get Block

Retrieve a block.

**Method:** `GET`
**Endpoint:** `/blocks/{block_id}`

**Request:**

```python
block = await client.get_block("block-id")
print(block.type)  # e.g., "paragraph", "heading_1", etc.
```

#### Get Block Children

Retrieve child blocks of a parent block (page or block).

**Method:** `GET`
**Endpoint:** `/blocks/{block_id}/children`

**Request:**

```python
children = await client.get_block_children(
    block_id="page-id",
    page_size=50
)
for block in children:
    print(f"Block type: {block.type}")
```

#### Append Block Children

Add blocks as children of a parent block.

**Method:** `PATCH`
**Endpoint:** `/blocks/{block_id}/children`

**Request:**

```python
blocks = await client.append_block_children(
    block_id="page-id",
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "New paragraph"}}
                ]
            }
        },
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Heading"}}
                ]
            }
        }
    ]
)
```

#### Update Block

Update block content (depends on block type).

**Method:** `PATCH`
**Endpoint:** `/blocks/{block_id}`

**Request:**

```python
block = await client.update_block(
    block_id="...",
    block_data={
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": "Updated text"}}
            ]
        }
    }
)
```

#### Delete Block

Delete (archive) a block.

**Method:** `DELETE`
**Endpoint:** `/blocks/{block_id}`

**Request:**

```python
block = await client.delete_block("block-id")
```

---

### User Endpoints

#### Get User

Retrieve user by ID.

**Method:** `GET`
**Endpoint:** `/users/{user_id}`

**Request:**

```python
user = await client.get_user("user-id")
print(user["name"])
```

#### List Users

List all users in workspace.

**Method:** `GET`
**Endpoint:** `/users`

**Request:**

```python
response = await client.list_users(page_size=50)
for user in response["results"]:
    print(user["name"])
```

#### Get Bot User

Get the integration's bot user (current integration).

**Method:** `GET`
**Endpoint:** `/users/me`

**Request:**

```python
bot = await client.get_bot_user()
print(f"Bot name: {bot['name']}")
```

---

### Search Endpoint

#### Search

Search for pages and databases by title.

**Method:** `POST`
**Endpoint:** `/search`

**Request:**

```python
result = await client.search(
    query="meeting notes",
    filter_type="page",  # or "database"
    page_size=50
)
for item in result.results:
    print(f"{item['id']}: {item['object']}")
```

**Response:**

```json
{
  "object": "list",
  "results": [
    {
      "id": "page-id",
      "object": "page",
      "created_time": "2024-01-10T10:00:00.000Z",
      "last_edited_time": "2024-01-15T15:30:00.000Z",
      "archived": false,
      "properties": {...}
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

---

## Error Codes

| Status | Code | Meaning |
|--------|------|---------|
| 400 | `validation_error` | Request body doesn't match expected schema |
| 401 | `unauthorized` | Bearer token is invalid or expired |
| 403 | `restricted_resource` | Insufficient permissions for operation |
| 404 | `object_not_found` | Resource doesn't exist or isn't shared |
| 409 | `conflict_error` | Transaction couldn't complete (data collision) |
| 429 | `rate_limited` | Rate limit exceeded - wait before retrying |
| 500 | `internal_server_error` | Unexpected Notion server error |
| 503 | `service_unavailable` | Notion temporarily unavailable |
| 504 | `gateway_timeout` | Notion timed out (max 60 seconds) |

## Error Handling

All errors are automatically retried with exponential backoff:

```python
try:
    result = await client.query_database(database_id="...")
except NotionAuthError:
    # Handle authentication failure
    pass
except NotionRateLimitError as e:
    # Rate limit exceeded - retry after e.retry_after seconds
    await asyncio.sleep(e.retry_after or 5)
except NotionNotFoundError:
    # Resource doesn't exist
    pass
except NotionValidationError:
    # Invalid request parameters
    pass
except NotionAPIError as e:
    # Other API errors
    print(f"API error: {e.message} (status: {e.status_code})")
```

## Rate Limiting

- **Limit:** 3 requests per second per integration
- **HTTP Status:** 429 Too Many Requests
- **Retry-After:** Check response header for wait time
- **Automatic Retry:** Built-in exponential backoff with jitter

## Testing

All endpoints are tested with real Notion API:

```bash
cd app/backend
pytest __tests__/unit/integrations/notion/ -v          # Unit tests
pytest __tests__/integration/notion/ -v -m live_api    # Live API tests
```

## Example Workflow

```python
import os
import asyncio
from src.integrations.notion import NotionClient

async def main():
    # Initialize client (pragma: allowlist secret)
    client = NotionClient(api_token=os.environ["NOTION_API_KEY"])

    try:
        # Get databases
        databases = await client.search(filter_type="database")
        print(f"Found {len(databases.results)} databases")

        if databases.results:
            db_id = databases.results[0]["id"]

            # Query database
            pages = await client.query_database(
                database_id=db_id,
                filter={"property": "Status", "select": {"equals": "Active"}}
            )
            print(f"Found {len(pages.results)} active pages")

            # Create new page
            new_page = await client.create_page(
                parent={"database_id": db_id},
                properties={
                    "Name": {
                        "title": [{"text": {"content": "Test Page"}}]
                    }
                }
            )
            print(f"Created page: {new_page.id}")

    finally:
        await client.close()

asyncio.run(main())
```

---

## References

- [Notion API Documentation](https://developers.notion.com/)
- [Notion API Reference](https://developers.notion.com/reference/intro)
- [Client Implementation](../../src/integrations/notion/client.py)
- [Unit Tests](../../__tests__/unit/integrations/notion/)

## Support

For issues or questions:
1. Check the error message and code
2. Review the unit tests for usage examples
3. Check `.claude/context/SELF-HEALING.md` for known patterns
4. Consult official Notion API documentation
