# Approval Workflow Examples

## Basic Usage

### Send a Budget Approval

```python
import asyncio
from src.agents.approval_agent import ApprovalAgent

async def main():
    async with ApprovalAgent() as agent:
        request_id = await agent.send_budget_approval(
            title="Q4 Marketing Budget",
            amount=50000.00,
            department="Marketing",
            description="Budget allocation for Q4 marketing campaigns including:\n- Digital advertising\n- Events\n- Content creation",
            requester_id=123456789,  # Your Telegram user ID
            approver_id=987654321,   # Approver's Telegram user ID
            chat_id=987654321,       # Where to send (usually approver's chat)
        )
        print(f"Created request: {request_id}")

asyncio.run(main())
```

### Send a Document for Review

```python
async with ApprovalAgent() as agent:
    request_id = await agent.send_document_approval(
        title="Partnership Agreement - Acme Corp",
        description="Please review the partnership agreement with Acme Corp. Key points:\n- Revenue share: 70/30\n- Term: 2 years\n- Exclusivity clause in Section 5",
        file_url="https://drive.google.com/file/d/abc123/view",
        document_type="Contract",
        requester_id=123456789,
        approver_id=987654321,
        chat_id=987654321,
    )
```

### Send Content for Approval

```python
blog_post = """
# 10 Tips for Remote Work Productivity

Remote work has become the new normal. Here are proven strategies...

## 1. Create a Dedicated Workspace
Having a dedicated workspace helps...

## 2. Set Clear Boundaries
Communicate your working hours...
"""

async with ApprovalAgent() as agent:
    request_id = await agent.send_content_approval(
        title="Blog Post: Remote Work Tips",
        content_text=blog_post,
        tags=["productivity", "remote-work", "tips"],
        requester_id=123456789,
        approver_id=987654321,
        chat_id=987654321,
    )
```

## Polling Mode (Long-running Bot)

```python
import asyncio
from src.agents.approval_agent import ApprovalAgent

async def run_approval_bot():
    agent = ApprovalAgent()
    await agent.initialize()

    print(f"Bot connected, starting polling...")

    # Start polling in background
    await agent.start_polling(timeout=30)

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(60)
            health = await agent.health_check()
            print(f"Health: {health}")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await agent.stop_polling()
        await agent.close()

asyncio.run(run_approval_bot())
```

## Webhook Mode (Production)

### FastAPI Integration

```python
from fastapi import FastAPI, Request, HTTPException
from src.agents.approval_agent import ApprovalAgent
from src.integrations.telegram import Update

app = FastAPI()
agent: ApprovalAgent | None = None

@app.on_event("startup")
async def startup():
    global agent
    agent = ApprovalAgent()
    await agent.initialize()

    # Set webhook
    webhook_url = "https://your-domain.com/webhook/telegram"
    await agent.telegram_client.set_webhook(
        url=webhook_url,
        secret_token="your-secret-token",
    )

@app.on_event("shutdown")
async def shutdown():
    if agent:
        await agent.close()

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    # Verify secret token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != "your-secret-token":
        raise HTTPException(401, "Invalid token")

    # Parse and process update
    data = await request.json()
    update = Update.from_dict(data)
    await agent.process_update(update)

    return {"ok": True}
```

## Custom Approval Types

```python
# Custom approval with structured data
async with ApprovalAgent() as agent:
    request_id = await agent.send_approval(
        title="Server Access Request",
        content="Requesting SSH access to production servers for deployment.",
        requester_id=123456789,
        approver_id=987654321,
        chat_id=987654321,
        content_type="custom",
        data={
            "servers": ["prod-web-01", "prod-web-02"],
            "access_level": "read-write",
            "duration": "24 hours",
            "reason": "Emergency deployment",
            "ticket_id": "INC-12345",
        },
    )
```

## Handling Approval Status

```python
async def check_and_handle_status(agent: ApprovalAgent, request_id: str):
    request = await agent.get_request(request_id)
    status = request["status"]

    if status == "approved":
        print(f"Request approved at {request['approved_at']}")
        # Proceed with action
        await execute_approved_action(request)

    elif status == "disapproved":
        reason = request.get("disapproval_reason", "No reason provided")
        print(f"Request disapproved: {reason}")
        # Handle rejection
        await notify_requester_rejection(request, reason)

    elif status == "editing":
        print("Request is being edited, waiting for resubmission...")

    elif status == "pending":
        print("Request still pending approval")
```

## Batch Approvals

```python
async def send_batch_approvals(
    agent: ApprovalAgent,
    items: list[dict],
    approver_id: int,
    chat_id: int,
):
    """Send multiple approval requests."""
    request_ids = []

    for item in items:
        request_id = await agent.send_approval(
            title=item["title"],
            content=item["content"],
            requester_id=item["requester_id"],
            approver_id=approver_id,
            chat_id=chat_id,
            content_type=item.get("type", "custom"),
            data=item.get("data", {}),
        )
        request_ids.append(request_id)

        # Respect rate limits
        await asyncio.sleep(1)

    return request_ids
```

## Monitoring Pending Approvals

```python
async def get_approval_stats(agent: ApprovalAgent, approver_id: int):
    """Get statistics for an approver."""
    pending = await agent.list_pending(approver_id)

    stats = {
        "total_pending": len(pending),
        "by_type": {},
        "oldest": None,
    }

    for req in pending:
        content_type = req["content_type"]
        stats["by_type"][content_type] = stats["by_type"].get(content_type, 0) + 1

        if stats["oldest"] is None or req["created_at"] < stats["oldest"]:
            stats["oldest"] = req["created_at"]

    return stats

# Usage
stats = await get_approval_stats(agent, approver_id=987654321)
print(f"Pending: {stats['total_pending']}")
print(f"By type: {stats['by_type']}")
print(f"Oldest: {stats['oldest']}")
```

## Integration with Other Systems

### Slack Notification on Approval

```python
import httpx

async def on_approval_complete(request: dict):
    """Send Slack notification when approval completes."""
    status = request["status"]
    title = request["title"]

    if status == "approved":
        message = f"✅ Approved: {title}"
        color = "#36a64f"
    else:
        reason = request.get("disapproval_reason", "")
        message = f"❌ Disapproved: {title}\nReason: {reason}"
        color = "#ff0000"

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://hooks.slack.com/services/...",
            json={
                "attachments": [{
                    "color": color,
                    "text": message,
                }]
            },
        )
```

### Database Integration

```python
from src.services.approval_service import ApprovalService, DatabaseConnection

class PostgresDatabase(DatabaseConnection):
    """Real PostgreSQL database implementation."""

    def __init__(self, pool):
        self.pool = pool

    async def save_request(self, request):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO approval_requests (id, title, content, ...)
                VALUES ($1, $2, $3, ...)
                """,
                request.id, request.title, request.content, ...
            )

    # ... implement other methods

# Use with real database
db = PostgresDatabase(connection_pool)
service = ApprovalService(
    telegram_client=telegram_client,
    db=db,
)
```

## Testing

### Mock Telegram Client

```python
from unittest.mock import AsyncMock, MagicMock
from src.services.approval_service import ApprovalService

def create_mock_telegram():
    client = MagicMock()
    client.send_message = AsyncMock(return_value=MagicMock(message_id=42))
    client.edit_message_text = AsyncMock()
    client.answer_callback_query = AsyncMock()
    return client

async def test_approval_flow():
    mock_telegram = create_mock_telegram()
    service = ApprovalService(telegram_client=mock_telegram)

    # Send request
    request_id = await service.send_approval_request({
        "title": "Test",
        "content": "Test content",
        "requester_id": 123,
        "approver_id": 456,
        "telegram_chat_id": 789,
        "content_type": "custom",
        "data": {},
    })

    # Verify message was sent
    mock_telegram.send_message.assert_called_once()

    # Verify request was created
    request = await service.get_approval_request(request_id)
    assert request.status.value == "pending"
```
