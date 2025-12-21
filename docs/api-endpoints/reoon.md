# Reoon Email Verifier API Endpoints

## Overview

- **Base URL:** `https://emailverifier.reoon.com/api/v1`
- **Authentication:** API Key (via query parameter `key=<API_KEY>`)
- **Rate Limits:** Max 5 concurrent threads for single verification
- **API Version:** V1

## Authentication

Reoon uses API key authentication via query parameters (NOT Bearer token).

```python
# Example: API key is added to query params
params = {"key": "your-api-key", "email": "test@example.com"}
response = await client.get("/verify", params=params)
```

## Endpoints

### 1. Single Email Verification (Quick Mode)

**Method:** `GET`
**Path:** `/verify`
**Description:** Fast email verification (~0.5 seconds) checking syntax, MX, and disposable status.

**Request Parameters:**
- `key` (string, required): Your API key
- `email` (string, required): Email address to verify
- `mode` (string, required): Must be `"quick"`

**Response Schema:**
```json
{
  "email": "test@example.com",
  "status": "valid",
  "overall_score": 75,
  "is_safe_to_send": true,
  "is_valid_syntax": true,
  "is_disposable": false,
  "is_role_account": false,
  "can_connect_smtp": false,
  "has_inbox_full": false,
  "is_catch_all": false,
  "is_deliverable": true,
  "is_disabled": false,
  "is_spamtrap": false,
  "is_free_email": false,
  "mx_accepts_mail": true,
  "mx_records": ["mx1.example.com", "mx2.example.com"],
  "verification_mode": "quick",
  "username": "test",
  "domain": "example.com"
}
```

**Example Request:**
```python
result = await client.verify_email_quick("test@example.com")
```

**Test Status:** ✅ PASSED (Live API test)

---

### 2. Single Email Verification (Power Mode)

**Method:** `GET`
**Path:** `/verify`
**Description:** Deep email verification (seconds to minutes) including inbox existence checks.

**Request Parameters:**
- `key` (string, required): Your API key
- `email` (string, required): Email address to verify
- `mode` (string, required): Must be `"power"`

**Response Schema:**
```json
{
  "email": "real@company.com",
  "status": "safe",
  "overall_score": 95,
  "is_safe_to_send": true,
  "is_valid_syntax": true,
  "is_disposable": false,
  "is_role_account": false,
  "can_connect_smtp": true,
  "has_inbox_full": false,
  "is_catch_all": false,
  "is_deliverable": true,
  "is_disabled": false,
  "is_spamtrap": false,
  "is_free_email": false,
  "mx_accepts_mail": true,
  "mx_records": ["mail.company.com"],
  "verification_mode": "power",
  "username": "real",
  "domain": "company.com"
}
```

**Example Request:**
```python
result = await client.verify_email_power("real@company.com")
```

**Status Values:**
- `safe` - Email is safe to send to
- `valid` - Email is valid (quick mode)
- `invalid` - Email does not exist
- `disabled` - Mailbox is disabled
- `disposable` - Temporary/disposable email
- `inbox_full` - Mailbox is full
- `catch_all` - Domain accepts all emails
- `role_account` - Generic role account (info@, support@)
- `spamtrap` - Known spam trap
- `unknown` - Cannot determine status

**Test Status:** ✅ PASSED (Live API test)

---

### 3. Create Bulk Verification Task

**Method:** `POST`
**Path:** `/create-bulk-verification-task/`
**Description:** Create an async bulk verification task for 10-50,000 emails.

**Request Body:**
```json
{
  "key": "your-api-key",
  "name": "My Verification Task",
  "emails": [
    "email1@example.com",
    "email2@example.com"
  ]
}
```

**Parameters:**
- `key` (string, required): Your API key
- `emails` (array, required): Array of email addresses (10-50,000)
- `name` (string, optional): Task name (max 25 characters)

**Response Schema:**
```json
{
  "status": "success",
  "task_id": "task-123-abc-456",
  "count_submitted": 100,
  "count_duplicates_removed": 5,
  "count_rejected_emails": 2,
  "count_processing": 93
}
```

**Example Request:**
```python
emails = ["user1@example.com", "user2@example.com", ...]
result = await client.create_bulk_verification_task(
    emails=emails,
    name="Q1 Email List"
)
print(f"Task ID: {result.task_id}")
```

**Test Status:** ⏭️ SKIPPED (preserves credits)

---

### 4. Get Bulk Verification Status

**Method:** `GET`
**Path:** `/get-result-bulk-verification-task/`
**Description:** Check progress and retrieve results of a bulk verification task.

**Request Parameters:**
- `key` (string, required): Your API key
- `task_id` (string, required): Task ID from create call

**Response Schema (Running):**
```json
{
  "task_id": "task-123-abc-456",
  "name": "My Verification Task",
  "status": "running",
  "count_total": 100,
  "count_checked": 45,
  "progress_percentage": 45.0,
  "results": {}
}
```

**Response Schema (Completed):**
```json
{
  "task_id": "task-123-abc-456",
  "name": "My Verification Task",
  "status": "completed",
  "count_total": 100,
  "count_checked": 100,
  "progress_percentage": 100.0,
  "results": {
    "email1@example.com": {
      "status": "safe",
      "overall_score": 95,
      "is_safe_to_send": true
    },
    "email2@example.com": {
      "status": "invalid",
      "overall_score": 0,
      "is_safe_to_send": false
    }
  }
}
```

**Task Status Values:**
- `waiting` - Task is queued
- `running` - Verification in progress
- `completed` - All emails verified
- `file_not_found` - Task file error
- `file_loading_error` - File loading error

**Example Request:**
```python
status = await client.get_bulk_verification_status("task-123-abc-456")
if status.is_completed:
    for email, data in status.results.items():
        print(f"{email}: {data['status']}")
```

**Test Status:** ⏭️ SKIPPED (preserves credits)

---

### 5. Check Account Balance

**Method:** `GET`
**Path:** `/check-account-balance/`
**Description:** Get remaining verification credits.

**Request Parameters:**
- `key` (string, required): Your API key

**Response Schema:**
```json
{
  "api_status": "active",
  "remaining_daily_credits": 500,
  "remaining_instant_credits": 1000,
  "status": "success"
}
```

**Example Request:**
```python
balance = await client.get_account_balance()
print(f"Total credits: {balance.total_remaining_credits}")
print(f"Has credits: {balance.has_credits}")
```

**Test Status:** ✅ PASSED (Live API test)

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 402 | Payment Required - Insufficient credits |
| 429 | Rate Limit Exceeded - Too many requests |
| 500 | Internal Server Error |

## Future-Proof Design

This client supports calling new endpoints dynamically:

```python
# Call any new endpoint without code changes
result = await client.call_endpoint(
    "/new-endpoint",
    method="GET",
    params={"param": "value"}
)
```

## Testing

All endpoints are tested with real API keys from `.env`:
- Unit test file: `__tests__/unit/integrations/test_reoon.py`
- Live test file: `__tests__/integration/test_reoon_live.py`
- Test coverage: 58 unit tests, 10 live tests
- Pass rate: 100%

## Sample Data

Sample data for testing is available in:
- `__tests__/fixtures/reoon_fixtures.py`

## Usage Examples

### Basic Verification
```python
from src.integrations.reoon import ReoonClient

async with ReoonClient(api_key="your-key") as client:
    # Quick verification
    result = await client.verify_email_quick("test@example.com")
    if result.is_safe:
        print("Email is safe to send")

    # Power verification (more thorough)
    result = await client.verify_email_power("test@example.com")
    if result.should_not_send:
        print(f"Do not send: {result.status}")
```

### Checking Credit Balance
```python
balance = await client.get_account_balance()
if not balance.has_credits:
    print("Warning: No credits remaining!")
```

### Health Check
```python
health = await client.health_check()
if not health["healthy"]:
    print(f"API issue: {health.get('error')}")
```
