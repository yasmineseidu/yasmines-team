# Approval Workflow Troubleshooting Guide

## Common Issues

### Bot Not Responding

**Symptoms:**
- Messages sent but no response
- Buttons don't work
- No error messages

**Checklist:**
1. Verify bot token is valid:
   ```python
   from src.integrations.telegram import TelegramClient

   client = TelegramClient(bot_token="YOUR_TOKEN")
   info = await client.get_me()
   print(f"Bot: @{info.username}")
   ```

2. Check if webhook is set (conflicts with polling):
   ```python
   info = await client.get_webhook_info()
   if info.get("url"):
       print(f"Webhook active: {info['url']}")
       # Delete webhook if using polling
       await client.delete_webhook()
   ```

3. Verify polling is running:
   ```python
   health = await agent.health_check()
   print(f"Polling active: {health['polling_active']}")
   ```

4. Check bot permissions in chat

### Buttons Not Working

**Symptoms:**
- Clicking buttons shows loading but nothing happens
- "Query is too old" error

**Solutions:**

1. **Query timeout**: Callback queries expire after ~30 seconds. Ensure `answer_callback_query` is called promptly:
   ```python
   # Must respond quickly
   await telegram_client.answer_callback_query(callback_query_id)
   ```

2. **Wrong callback data format**: Ensure format is `action_requestid`:
   ```python
   # Correct format
   callback_data = f"approve_{request_id}"  # e.g., "approve_550e8400-..."
   ```

3. **Request not found**: Check request exists in database:
   ```python
   request = await service.get_approval_request(request_id)
   ```

### Message Edit Fails

**Symptoms:**
- "Message not modified" error
- Old content remains after approval

**Causes:**

1. **Same content**: Telegram rejects edits with identical content
   ```python
   # Ensure new content is different
   new_text = format_approved_message(request)  # Must differ from original
   ```

2. **Message too old**: Messages older than 48 hours may not be editable

3. **Bot not message owner**: Bot can only edit its own messages

### Authorization Errors

**Symptoms:**
- "Unauthorized" when clicking buttons
- Only certain users can approve

**Solution:**
Verify approver_id matches the clicking user:
```python
# In handler
if callback_query.from_user.id != request.approver_id:
    await telegram_client.answer_callback_query(
        callback_query.id,
        text="You are not authorized to approve this request",
        show_alert=True,
    )
    return
```

### Webhook Issues

**Symptoms:**
- Webhook not receiving updates
- SSL errors
- 401 Unauthorized

**Checklist:**

1. **HTTPS required**: Telegram only sends to HTTPS URLs
   ```
   ✅ https://api.example.com/webhook
   ❌ http://api.example.com/webhook
   ```

2. **Valid SSL certificate**: Self-signed certificates require special setup

3. **Secret token verification**:
   ```python
   @app.post("/webhook")
   async def webhook(request: Request):
       token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
       if token != EXPECTED_TOKEN:
           raise HTTPException(401)
   ```

4. **Respond with 200**: Always return 200, even on errors
   ```python
   # Telegram retries on non-200 responses
   return {"ok": True}  # Always 200
   ```

5. **Check webhook status**:
   ```python
   info = await client.get_webhook_info()
   print(f"URL: {info.get('url')}")
   print(f"Pending: {info.get('pending_update_count')}")
   print(f"Last error: {info.get('last_error_message')}")
   ```

### Rate Limiting

**Symptoms:**
- 429 Too Many Requests
- Messages delayed or dropped

**Limits:**
- 1 message/second per chat
- 30 messages/second globally
- 20 messages/minute in groups

**Solutions:**

1. **Add delays between messages**:
   ```python
   for request in requests:
       await send_approval(request)
       await asyncio.sleep(1.1)  # Slightly over 1 second
   ```

2. **Use bulk operations**: Send to different chats in parallel, same chat sequentially

3. **Implement exponential backoff**:
   ```python
   async def send_with_retry(func, *args, max_retries=3):
       for attempt in range(max_retries):
           try:
               return await func(*args)
           except TelegramError as e:
               if "429" in str(e):
                   wait = 2 ** attempt
                   await asyncio.sleep(wait)
               else:
                   raise
   ```

### Database Issues

**Symptoms:**
- Request not found after creation
- Status not updating

**Checklist:**

1. **Using InMemoryDatabase**: Data is lost on restart
   ```python
   # Default uses in-memory - fine for testing
   service = ApprovalService(telegram_client=client)

   # For production, provide real database
   service = ApprovalService(
       telegram_client=client,
       db=real_database,
   )
   ```

2. **Check request ID format**: Must be valid UUID
   ```python
   import uuid
   try:
       uuid.UUID(request_id)
   except ValueError:
       print("Invalid UUID")
   ```

3. **Verify database connection**:
   ```python
   async with pool.acquire() as conn:
       await conn.execute("SELECT 1")
   ```

### Edit Token Issues

**Symptoms:**
- "Token expired" errors
- Can't access edit form

**Solutions:**

1. **Token expiration**: Default is 24 hours
   ```python
   # Extend expiration if needed
   service = ApprovalService(
       telegram_client=client,
       edit_token_expiry_hours=48,  # 48 hours
   )
   ```

2. **Token already used**: Tokens may be single-use

3. **Regenerate token**:
   ```python
   new_url = await service.generate_edit_token(request_id)
   ```

## Debugging Tips

### Enable Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or specific loggers
logging.getLogger("src.agents.approval_agent").setLevel(logging.DEBUG)
logging.getLogger("src.services.approval_service").setLevel(logging.DEBUG)
logging.getLogger("src.integrations").setLevel(logging.DEBUG)
```

### Inspect Raw Updates

```python
async def debug_handler(update: Update):
    print(f"Update ID: {update.update_id}")
    print(f"Raw: {update.raw}")

    if update.callback_query:
        cq = update.callback_query
        print(f"Callback data: {cq.data}")
        print(f"From user: {cq.from_user.id}")
        print(f"Message ID: {cq.message.message_id}")
```

### Test Connectivity

```python
async def diagnose():
    client = TelegramClient(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"))

    # Test 1: Bot info
    try:
        info = await client.get_me()
        print(f"✅ Bot connected: @{info.username}")
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        return

    # Test 2: Webhook status
    webhook = await client.get_webhook_info()
    if webhook.get("url"):
        print(f"ℹ️ Webhook active: {webhook['url']}")
    else:
        print("ℹ️ No webhook set (using polling)")

    # Test 3: Send test message
    chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
    if chat_id:
        try:
            msg = await client.send_message(int(chat_id), "Test message")
            print(f"✅ Message sent: {msg.message_id}")
            await client.delete_message(int(chat_id), msg.message_id)
        except Exception as e:
            print(f"❌ Message failed: {e}")

    await client.close()
```

## Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `Bad Request: chat not found` | Invalid chat_id | Verify chat_id exists |
| `Forbidden: bot was blocked` | User blocked bot | User must unblock |
| `Bad Request: message not modified` | Edit with same content | Ensure content differs |
| `Bad Request: query is too old` | Callback query expired | Process callbacks faster |
| `Unauthorized` | Invalid bot token | Check TELEGRAM_BOT_TOKEN |
| `Too Many Requests` | Rate limited | Add delays, implement backoff |
| `Bad Request: BUTTON_DATA_INVALID` | callback_data > 64 bytes | Shorten callback data |

## Getting Help

1. Check Telegram Bot API docs: https://core.telegram.org/bots/api
2. Review bot logs for error details
3. Test with minimal example
4. Verify environment variables are set
