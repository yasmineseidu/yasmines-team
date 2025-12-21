# Anymailfinder API Endpoints

## Overview

- **Base URL:** `https://api.anymailfinder.com/v5.1`
- **Authentication:** API Key (from `.env` as `ANYMAILFINDER_API_KEY`)
- **Rate Limits:** None (system auto-scales)
- **Timeout:** 180 seconds recommended (real-time SMTP verification)
- **API Version:** v5.1

## Integration Client

**Location:** `app/backend/src/integrations/anymailfinder.py`

```python
from src.integrations import AnymailfinderClient

async with AnymailfinderClient(api_key="your-key") as client:
    result = await client.find_person_email(
        first_name="John",
        last_name="Doe",
        domain="example.com"
    )
```

## Endpoints

### 1. Find Person's Email

**Method:** `POST`
**Path:** `/v5.1/find-email/person`
**Description:** Find a person's email by name and company domain.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `first_name` | string | Optional* | Person's first name |
| `last_name` | string | Optional* | Person's last name |
| `full_name` | string | Optional* | Full name (alternative to first+last) |
| `domain` | string | Optional** | Company domain (e.g., "microsoft.com") |
| `company_name` | string | Optional** | Company name |

*At least one of `full_name` or both `first_name` and `last_name` required.
**At least one of `domain` or `company_name` required.

**Response Schema:**

```json
{
  "email": "john.doe@microsoft.com",
  "email_status": "valid",
  "valid_email": "john.doe@microsoft.com"
}
```

**`email_status` values:**
- `valid` - Email is deliverable and verified (1 credit)
- `risky` - Email existence inconclusive (free)
- `not_found` - No email found (free)
- `blacklisted` - Domain is blacklisted (free)

**Example Request:**

```python
result = await client.find_person_email(
    first_name="John",
    last_name="Doe",
    domain="microsoft.com"
)
print(result.email)  # "john.doe@microsoft.com"
print(result.is_valid)  # True
```

**Error Codes:**
- `400` - Bad Request (missing required parameters)
- `401` - Unauthorized (invalid API key)
- `402` - Payment Required (insufficient credits)

**Test Status:** PASSED (Unit tests)

---

### 2. Find Decision Maker's Email

**Method:** `POST`
**Path:** `/v5.1/find-email/decision-maker`
**Description:** Find a decision maker's email at a company.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | Yes | Company domain |
| `job_title` | string | No | Target job title (e.g., "CEO") |
| `department` | string | No | Target department |
| `seniority` | string | No | Seniority level (e.g., "C-Level") |

**Example Request:**

```python
result = await client.find_decision_maker_email(
    domain="startup.com",
    job_title="CEO",
    seniority="C-Level"
)
```

**Test Status:** PASSED (Unit tests)

---

### 3. Find All Emails at Company

**Method:** `POST`
**Path:** `/v5.1/find-email/company`
**Description:** Find all emails at a company domain.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | Yes | Company domain |
| `limit` | integer | No | Maximum emails to return |

**Response Schema:**

```json
{
  "domain": "microsoft.com",
  "emails": [
    {
      "email": "john.doe@microsoft.com",
      "email_status": "valid",
      "valid_email": "john.doe@microsoft.com"
    }
  ]
}
```

**Example Request:**

```python
results = await client.find_company_emails(
    domain="microsoft.com",
    limit=10
)
for result in results:
    print(result.email)
```

**Test Status:** PASSED (Unit tests)

---

### 4. Verify Email

**Method:** `POST`
**Path:** `/v5.1/verify-email`
**Description:** Verify if an email address is valid and deliverable.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | Email address to verify |

**Response Schema:**

```json
{
  "email_status": "valid"
}
```

**`email_status` values:**
- `valid` - Email is deliverable (0.2 credits)
- `risky` - Email may bounce (0.2 credits)
- `invalid` - Email is not deliverable (0.2 credits)

**Example Request:**

```python
result = await client.verify_email("test@example.com")
print(result.is_valid)  # True/False
print(result.is_deliverable)  # True if valid or risky
```

**Test Status:** PASSED (Unit tests)

---

### 5. Get Account Info

**Method:** `GET`
**Path:** `/v5.1/account`
**Description:** Get account details including remaining credits.

**Response Schema:**

```json
{
  "email": "user@company.com",
  "credits_remaining": 1000
}
```

**Example Request:**

```python
account = await client.get_account_info()
print(f"Credits remaining: {account.credits_remaining}")
```

**Test Status:** PASSED (Unit tests)

---

## Future-Proof Design

This client supports calling new endpoints dynamically:

```python
# Call any new endpoint without code changes
result = await client.call_endpoint(
    "/new-feature",
    method="POST",
    json={"param": "value"}
)
```

## Pricing

| Operation | Cost | Notes |
|-----------|------|-------|
| Find email (valid) | 1 credit | Only charged for valid results |
| Find email (risky/not_found) | Free | No charge for inconclusive results |
| Verify email | 0.2 credits | All results |
| Duplicate search (30 days) | Free | Cached results |

## Testing

### Unit Tests

```bash
cd app/backend
uv run pytest __tests__/unit/integrations/test_anymailfinder.py -v
```

Coverage: 90.91%

### Live API Tests

```bash
# Requires ANYMAILFINDER_API_KEY in .env
cd app/backend
uv run pytest __tests__/integration/test_anymailfinder_live.py -v -m live_api
```

## Sample Data

Sample data for testing is available in:
- `__tests__/fixtures/anymailfinder_fixtures.py`

## Error Handling

All methods raise `AnymailfinderError` on failure with:
- `message` - Error description
- `status_code` - HTTP status code
- `response_data` - Raw API response

```python
try:
    result = await client.find_person_email(...)
except AnymailfinderError as e:
    print(f"Error: {e.message}")
    print(f"Status: {e.status_code}")
```

## Retry Logic

Built-in exponential backoff retry for:
- Timeout errors
- Network errors
- 5xx server errors
- 429 rate limit errors (though API has no limits)

Default: 3 retries with exponential backoff + jitter.
