# ClickUp API Endpoints

## Overview

- **Base URL:** `https://api.clickup.com/api/v2`
- **Authentication:** Personal API Token (or OAuth 2.0 token)
- **Authentication Header:** `Authorization: {api_key}` for personal tokens, or `Authorization: Bearer {token}` for OAuth
- **Rate Limits:** Generous limits (500+ requests/minute for most endpoints)
- **Version:** ClickUp API v2 (with some v3 endpoints available)
- **Status:** Production-ready

## Authentication

Personal tokens begin with `pk_` and are added to the Authorization header directly without "Bearer" prefix.

OAuth 2.0 tokens are obtained through the authorization flow and are added with "Bearer" prefix.

## Endpoints Implemented

### 1. Get Workspaces (Teams)
**Method:** `GET`
**Path:** `/team`
**Description:** Get all workspaces accessible to the authenticated user.

**Response Schema:**
```json
{
  "teams": [
    {
      "id": 12345,
      "name": "Marketing Team",
      "color": "#FF0000",
      "avatar": "https://example.com/avatar.png",
      "members": [...],
      "owned_by_user": {...}
    }
  ]
}
```

**Python Implementation:**
```python
client = ClickUpClient(api_key="pk_12345...")
workspaces = await client.get_workspaces()
for workspace in workspaces:
    print(f"Workspace: {workspace.name} ({workspace.id})")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful fetch and parse
- Empty workspaces handling
- Error handling

---

### 2. Get Spaces
**Method:** `GET`
**Path:** `/team/{team_id}/space`
**Description:** Get all spaces in a workspace (team).

**Parameters:**
- `team_id` (path, required): ID of the team/workspace

**Response Schema:**
```json
{
  "spaces": [
    {
      "id": 111,
      "name": "Marketing Campaigns",
      "color": "#FF00FF",
      "private": false,
      "avatar": "https://example.com/space.png",
      "archived": false
    }
  ]
}
```

**Python Implementation:**
```python
spaces = await client.get_spaces(workspace_id="12345")
for space in spaces:
    print(f"Space: {space.name} (Private: {space.private})")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful fetch and parse
- Parameter validation
- Error handling

---

### 3. Get Lists
**Method:** `GET`
**Path:** `/space/{space_id}/list`
**Description:** Get all lists in a space.

**Parameters:**
- `space_id` (path, required): ID of the space

**Response Schema:**
```json
{
  "lists": [
    {
      "id": "list_1",
      "name": "To Do",
      "color": "#FF00FF",
      "private": false,
      "archived": false,
      "folder": {
        "id": 100,
        "name": "Planning"
      },
      "space": {
        "id": 111
      },
      "owner": {...},
      "members": [...]
    }
  ]
}
```

**Python Implementation:**
```python
lists = await client.get_lists(space_id="111")
for list_item in lists:
    print(f"List: {list_item.name} (Folder: {list_item.folder_id})")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful fetch and parse
- Nested object handling
- Error handling

---

### 4. Create Task
**Method:** `POST`
**Path:** `/list/{list_id}/task`
**Description:** Create a new task in a list.

**Parameters:**
- `list_id` (path, required): ID of the list
- `name` (body, required): Task name/title
- `description` (body, optional): Task description
- `priority` (body, optional): Priority level (1-5, 1=urgent)
- `due_date` (body, optional): Due date in milliseconds since epoch
- `start_date` (body, optional): Start date in milliseconds since epoch
- `assignees` (body, optional): List of assignee IDs
- `tags` (body, optional): List of tags

**Request Body:**
```json
{
  "name": "Design new landing page",
  "description": "Create responsive design",
  "priority": 2,
  "due_date": 1704067200000,
  "start_date": 1703980800000,
  "assignees": [1, 2],
  "tags": ["design", "urgent"]
}
```

**Response Schema:**
```json
{
  "id": "task_123",
  "custom_id": null,
  "name": "Design new landing page",
  "description": "Create responsive design",
  "status": {
    "status": "open",
    "color": "#87CEEB",
    "orderindex": 0
  },
  "priority": {
    "priority": 2,
    "color": "#FF00FF"
  },
  "due_date": 1704067200000,
  "start_date": 1703980800000,
  "assignees": [...],
  "tags": [{...}],
  "list": {
    "id": "list_1"
  },
  "space": {
    "id": 111
  },
  "date_created": 1703980800000,
  "date_updated": 1703980800000
}
```

**Python Implementation:**
```python
task = await client.create_task(
    list_id="list_1",
    name="Design new landing page",
    description="Create responsive design",
    priority=2,
    assignee_ids=[1, 2],
    tags=["design", "urgent"]
)
print(f"Task created: {task.id} - {task.name}")
```

**Test Status:** ✅ UNIT TESTED (4 tests)
- Successful creation with all fields
- Required field validation
- Error handling

---

### 5. Get Task
**Method:** `GET`
**Path:** `/task/{task_id}`
**Description:** Get details of a specific task.

**Parameters:**
- `task_id` (path, required): ID of the task

**Response Schema:**
```json
{
  "id": "task_123",
  "custom_id": "CUSTOM-123",
  "name": "Design new landing page",
  "description": "Create responsive design",
  "status": {
    "status": "in_progress"
  },
  "priority": {
    "priority": 2
  },
  "due_date": 1704067200000,
  "start_date": 1703980800000,
  "assignees": [...],
  "tags": [{...}],
  "list": {
    "id": "list_1"
  },
  "date_created": 1703980800000,
  "date_updated": 1703980800000
}
```

**Python Implementation:**
```python
task = await client.get_task(task_id="task_123")
print(f"Task: {task.name}")
print(f"Status: {task.status}")
print(f"Priority: {task.priority}")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful fetch and parse
- Parameter validation
- Error handling

---

### 6. Update Task
**Method:** `PUT`
**Path:** `/task/{task_id}`
**Description:** Update an existing task's properties.

**Parameters:**
- `task_id` (path, required): ID of the task to update
- `name` (body, optional): New task name
- `description` (body, optional): New task description
- `status` (body, optional): New task status
- `priority` (body, optional): New priority level
- `due_date` (body, optional): New due date in milliseconds

**Request Body:**
```json
{
  "name": "Updated task name",
  "status": "in_progress",
  "priority": 1,
  "due_date": 1704153600000
}
```

**Response Schema:** Same as Get Task response

**Python Implementation:**
```python
task = await client.update_task(
    task_id="task_123",
    name="Updated task name",
    status="in_progress",
    priority=1
)
print(f"Task updated: {task.name} - Status: {task.status}")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful update with partial fields
- Parameter validation
- Error handling

---

### 7. Delete Task
**Method:** `DELETE`
**Path:** `/task/{task_id}`
**Description:** Delete a task permanently.

**Parameters:**
- `task_id` (path, required): ID of the task to delete

**Response Schema:**
```json
{
  "success": true
}
```

**Python Implementation:**
```python
response = await client.delete_task(task_id="task_123")
if response.get("success"):
    print("Task deleted successfully")
```

**Test Status:** ✅ UNIT TESTED (3 tests)
- Successful deletion
- Parameter validation
- Error handling

---

### 8. Get Tasks by List
**Method:** `GET`
**Path:** `/list/{list_id}/task`
**Description:** Get all tasks in a list with optional pagination.

**Parameters:**
- `list_id` (path, required): ID of the list
- `limit` (query, optional): Maximum tasks to return (default: 100)
- `page` (query, optional): Page number for pagination
- `order_by` (query, optional): Field to sort by

**Response Schema:**
```json
{
  "tasks": [
    {
      "id": "task_1",
      "name": "Task 1",
      "status": {
        "status": "open"
      },
      "priority": {
        "priority": 2
      },
      ...
    },
    {
      "id": "task_2",
      "name": "Task 2",
      ...
    }
  ]
}
```

**Python Implementation:**
```python
# Get first 50 tasks from a list
tasks = await client.get_tasks_by_list(
    list_id="list_1",
    limit=50
)
print(f"Found {len(tasks)} tasks")
for task in tasks:
    print(f"  - {task.name} ({task.status})")
```

**Test Status:** ✅ UNIT TESTED (4 tests)
- Successful fetch with default limit
- Custom limit parameter
- Parameter validation
- Error handling

---

### 9. Health Check
**Method:** `GET`
**Path:** `/team` (via internal method)
**Description:** Verify ClickUp API connectivity and authentication.

**Response Schema:**
```json
{
  "status": "healthy",
  "workspaces_count": 2
}
```

**Python Implementation:**
```python
health = await client.health_check()
if health["status"] == "healthy":
    print(f"ClickUp API is healthy - {health['workspaces_count']} workspaces")
```

**Test Status:** ✅ UNIT TESTED (2 tests)
- Successful health check
- Error handling

---

## Error Handling

All endpoints raise `ClickUpError` with descriptive messages on failures:

```python
try:
    task = await client.get_task("invalid_task_id")
except ClickUpError as e:
    print(f"Error: {e.message}")
    print(f"Status code: {e.status_code}")
```

### Common Error Responses

**401 Unauthorized:**
```json
{
  "err": "OAuth token is not valid",
  "ECODE": "OAUTH_TOKEN_INVALID"
}
```

**404 Not Found:**
```json
{
  "err": "The requested object does not exist",
  "ECODE": "NOT_FOUND"
}
```

**429 Too Many Requests:**
```json
{
  "err": "You have exceeded the rate limit. Please retry after some time.",
  "ECODE": "RATE_LIMIT_EXCEEDED"
}
```

## Future-Proof Design

The client supports dynamic endpoint calls for new API endpoints without code changes:

```python
# Call any endpoint without modifying client code
response = await client.call_endpoint(
    "/v2/new-endpoint",
    method="POST",
    json={"param": "value"}
)
```

This allows the client to support new ClickUp API endpoints as they're released.

## Implementation Details

### File Location
- **Client:** `app/backend/src/integrations/clickup.py`
- **Tests:** `app/backend/__tests__/unit/integrations/test_clickup.py`
- **Live Tests:** `app/backend/__tests__/integration/test_clickup_live.py`
- **Fixtures:** `app/backend/__tests__/fixtures/clickup_fixtures.py`

### Data Classes

**ClickUpWorkspace:**
- `id`: Workspace ID
- `name`: Workspace name
- `color`: Color code (optional)
- `avatar`: Avatar URL (optional)

**ClickUpSpace:**
- `id`: Space ID
- `name`: Space name
- `color`: Color code (optional)
- `private`: Privacy flag
- `avatar`: Avatar URL (optional)

**ClickUpList:**
- `id`: List ID
- `name`: List name
- `folder_id`: Parent folder ID (optional)
- `space_id`: Parent space ID (optional)
- `color`: Color code (optional)
- `private`: Privacy flag

**ClickUpTask:**
- `id`: Task ID
- `custom_id`: Custom identifier (optional)
- `name`: Task name
- `description`: Task description (optional)
- `status`: Task status
- `priority`: Priority level (optional)
- `due_date`: Due date in milliseconds (optional)
- `start_date`: Start date in milliseconds (optional)
- `assignees`: List of assignee objects
- `tags`: List of tags
- `list_id`: Parent list ID (optional)
- `folder_id`: Parent folder ID (optional)
- `space_id`: Parent space ID (optional)
- `created_at`: Creation timestamp
- `updated_at`: Update timestamp

## Testing

### Unit Tests (34 tests - 100% pass)
- Initialization and validation
- Header generation
- Workspace operations
- Space operations
- List operations
- Task CRUD operations
- Health checks
- Error handling

### Integration Tests
Live API tests are available in `test_clickup_live.py` for testing with real ClickUp API keys:
- Workspace retrieval
- Space and list operations
- Task creation, retrieval, update, deletion
- Error handling with real API responses

### Running Tests

```bash
# Run unit tests only
python3 -m pytest __tests__/unit/integrations/test_clickup.py -v

# Run with coverage
python3 -m pytest __tests__/unit/integrations/test_clickup.py --cov=src/integrations/clickup

# Run live API tests (requires valid API key in .env)
python3 -m pytest __tests__/integration/test_clickup_live.py -v -m live_api
```

## Source URLs

- [ClickUp Developer Portal](https://developer.clickup.com/)
- [ClickUp API Documentation](https://clickup.readme.io/docs/index)
- [ClickUp API Authentication](https://developer.clickup.com/docs/authentication)
- [ClickUp API Reference](https://developer.clickup.com/reference)
