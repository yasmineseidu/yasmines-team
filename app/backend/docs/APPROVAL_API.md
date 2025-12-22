# Approval API Reference

## REST Endpoints

Base path: `/api/v1/approvals`

### Create Approval Request

**POST** `/api/v1/approvals/`

Create a new approval request and send to Telegram.

**Request Body:**
```json
{
  "title": "Q4 Marketing Budget",
  "content": "Budget allocation for Q4 marketing campaigns",
  "content_type": "budget",
  "requester_id": 123456789,
  "approver_id": 987654321,
  "telegram_chat_id": 456789012,
  "data": {
    "amount": 50000,
    "department": "Marketing"
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Q4 Marketing Budget",
  "content": "Budget allocation for Q4 marketing campaigns",
  "content_type": "budget",
  "status": "pending",
  "requester_id": 123456789,
  "approver_id": 987654321,
  "telegram_chat_id": 456789012,
  "telegram_message_id": 42,
  "data": {"amount": 50000, "department": "Marketing"},
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Get Approval Request

**GET** `/api/v1/approvals/{request_id}`

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Q4 Marketing Budget",
  "status": "pending",
  ...
}
```

### Update Approval Status

**PATCH** `/api/v1/approvals/{request_id}`

Update status programmatically (for internal use).

**Request Body:**
```json
{
  "status": "approved",
  "reason": "Budget approved as requested"
}
```

**Response:** `200 OK`

### List Approval Requests

**GET** `/api/v1/approvals/`

Query parameters:
- `approver_id` (int): Filter by approver
- `status` (string): Filter by status (pending, approved, etc.)
- `content_type` (string): Filter by type
- `limit` (int): Max results (default 100)
- `offset` (int): Pagination offset

**Response:** `200 OK`
```json
{
  "items": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

### Generate Edit Token

**POST** `/api/v1/approvals/{request_id}/edit-token`

Generate a secure edit token for web-based modifications.

**Response:** `200 OK`
```json
{
  "edit_url": "https://app.example.com/approvals/edit?id=...&token=abc123",
  "expires_at": "2025-01-16T10:30:00Z"
}
```

### Get Request by Edit Token

**GET** `/api/v1/approvals/by-token/{token}`

Retrieve request using edit token (for edit form).

**Response:** `200 OK` (request data) or `404 Not Found`

---

## Telegram Webhook Endpoints

Base path: `/api/v1/telegram`

### Webhook Handler

**POST** `/api/v1/telegram/webhook`

Receives Telegram updates. Called by Telegram servers.

**Headers:**
- `X-Telegram-Bot-Api-Secret-Token`: Webhook secret

**Request Body:** Telegram Update object

**Response:** `200 OK` (always, per Telegram requirements)

### Get Webhook Info

**GET** `/api/v1/telegram/webhook/info`

Get current webhook configuration.

**Response:** `200 OK`
```json
{
  "url": "https://api.example.com/api/v1/telegram/webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0
}
```

### Set Webhook

**POST** `/api/v1/telegram/webhook/set`

Configure Telegram webhook.

**Request Body:**
```json
{
  "url": "https://api.example.com/api/v1/telegram/webhook",
  "secret_token": "your-secret-token"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Webhook set successfully"
}
```

### Delete Webhook

**DELETE** `/api/v1/telegram/webhook`

Remove webhook configuration.

**Response:** `200 OK`

### Health Check

**GET** `/api/v1/telegram/health`

Check Telegram bot connectivity.

**Response:** `200 OK`
```json
{
  "name": "telegram",
  "healthy": true,
  "message": "Telegram bot @your_bot is online"
}
```

---

## ApprovalAgent Python API

### Initialization

```python
from src.agents.approval_agent import ApprovalAgent

# Option 1: Manual initialization
agent = ApprovalAgent(bot_token="...", edit_form_base_url="...")
await agent.initialize()

# Option 2: Context manager
async with ApprovalAgent() as agent:
    ...
```

### Sending Approvals

```python
# Generic approval
request_id = await agent.send_approval(
    title="Request Title",
    content="Description",
    requester_id=123,
    approver_id=456,
    chat_id=789,
    content_type="custom",
    data={"key": "value"},
)

# Budget approval (convenience method)
request_id = await agent.send_budget_approval(
    title="Q4 Budget",
    amount=50000.00,
    department="Marketing",
    description="Budget for Q4 campaigns",
    requester_id=123,
    approver_id=456,
    chat_id=789,
)

# Document approval
request_id = await agent.send_document_approval(
    title="Contract Review",
    description="Partnership agreement",
    file_url="https://...",
    document_type="Contract",
    requester_id=123,
    approver_id=456,
    chat_id=789,
)

# Content approval
request_id = await agent.send_content_approval(
    title="Blog Post",
    content_text="# Article content...",
    tags=["tech", "ai"],
    requester_id=123,
    approver_id=456,
    chat_id=789,
)
```

### Querying Requests

```python
# Get single request
request = await agent.get_request(request_id)

# List pending for approver
pending = await agent.list_pending(approver_id=456)
```

### Polling Mode

```python
# Start polling (background task)
await agent.start_polling(timeout=30)

# Stop polling
await agent.stop_polling()
```

### Health Check

```python
health = await agent.health_check()
# {"name": "approval_agent", "healthy": True, "polling_active": False}
```

---

## ApprovalService Python API

Lower-level service for custom integrations.

```python
from src.services.approval_service import ApprovalService

service = ApprovalService(
    telegram_client=telegram_client,
    db=database,  # Optional, uses InMemoryDatabase if not provided
    edit_form_base_url="https://...",
    edit_token_expiry_hours=24,
)

# Send request
request_id = await service.send_approval_request(request_data={...})

# Update status
await service.update_approval_status(
    request_id=request_id,
    new_status=ApprovalStatus.APPROVED,
    actor_id=456,
    reason="Approved",
)

# Generate edit URL
edit_url = await service.generate_edit_token(request_id)

# Get by edit token
request = await service.get_request_by_edit_token(token)
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request data |
| 401 | Unauthorized (invalid webhook token) |
| 404 | Request not found |
| 409 | Conflict (request already processed) |
| 429 | Rate limited |
| 500 | Internal server error |
| 502 | Telegram API error |

## Rate Limits

- Telegram: 1 message/second per chat
- Telegram: 30 messages/second global
- API: Configurable per endpoint
