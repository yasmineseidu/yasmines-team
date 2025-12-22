# Gmail API Integration Research (2025)

**Date:** 2025-12-22
**Task:** 036-gmail-complete-integration.md
**Research Phase:** Complete

---

## Executive Summary

Gmail API v1 is stable and production-ready for integration with Smarter Team's async Python backend. This research provides:
- Complete endpoint documentation (5 main resource types, 20+ methods)
- Error handling strategies with exponential backoff
- OAuth 2.0 authentication patterns
- MIME/attachment handling patterns
- Rate limiting specifications
- Implementation patterns from existing integrations (Google Drive, LinkedIn)

---

## 1. Gmail API v1 Endpoints (Complete List)

### 1.1 Users.messages (Email Operations)

| Method | Endpoint | HTTP | Purpose |
|--------|----------|------|---------|
| list | `/gmail/v1/users/{userId}/messages` | GET | List messages in mailbox with filtering |
| get | `/gmail/v1/users/{userId}/messages/{id}` | GET | Retrieve full message with headers & body |
| send | `/gmail/v1/users/{userId}/messages/send` | POST | Send email to recipients |
| insert | `/gmail/v1/users/{userId}/messages` | POST | Insert message directly (bypass scanning) |
| delete | `/gmail/v1/users/{userId}/messages/{id}` | DELETE | Permanently delete message |
| trash | `/gmail/v1/users/{userId}/messages/{id}/trash` | POST | Move message to trash |
| modify | `/gmail/v1/users/{userId}/messages/{id}/modify` | POST | Add/remove labels from message |

**Key Parameters:**
- `userId`: "me" for authenticated user (always use "me")
- `q`: Query filter (from:, to:, subject:, label:, etc.)
- `pageSize`: Number of results (1-500, default 10)
- `pageToken`: For pagination
- `labelIds`: Filter by specific labels

**Message Object Fields:**
```
id, threadId, labelIds, historyId, internalDate, snippet,
payload (headers, mimeType, parts, filename, data)
```

### 1.2 Users.drafts (Draft Email Management)

| Method | Endpoint | HTTP | Purpose |
|--------|----------|------|---------|
| list | `/gmail/v1/users/{userId}/drafts` | GET | List draft messages |
| get | `/gmail/v1/users/{userId}/drafts/{id}` | GET | Retrieve specific draft |
| create | `/gmail/v1/users/{userId}/drafts` | POST | Create new draft with DRAFT label |
| send | `/gmail/v1/users/{userId}/drafts/{id}/send` | POST | Send existing draft |
| delete | `/gmail/v1/users/{userId}/drafts/{id}` | DELETE | Permanently delete draft |

**Key Feature:** Draft IDs expire - test with fresh drafts, don't cache

### 1.3 Users.labels (Label Management)

| Method | Endpoint | HTTP | Purpose |
|--------|----------|------|---------|
| list | `/gmail/v1/users/{userId}/labels` | GET | List all available labels |
| get | `/gmail/v1/users/{userId}/labels/{id}` | GET | Retrieve specific label details |
| create | `/gmail/v1/users/{userId}/labels` | POST | Create new custom label |
| delete | `/gmail/v1/users/{userId}/labels/{id}` | DELETE | Permanently delete label |
| patch | `/gmail/v1/users/{userId}/labels/{id}` | PATCH | Update label properties |

**System Labels:** INBOX, SENT_MAIL, DRAFT, SPAM, TRASH, UNREAD, STARRED, IMPORTANT, ALL_MAIL, CATEGORY_*

**Custom Labels:** User-created labels for organization

### 1.4 Users.threads (Thread/Conversation Management)

| Method | Endpoint | HTTP | Purpose |
|--------|----------|------|---------|
| list | `/gmail/v1/users/{userId}/threads` | GET | List conversation threads |
| get | `/gmail/v1/users/{userId}/threads/{id}` | GET | Retrieve complete thread with all messages |
| delete | `/gmail/v1/users/{userId}/threads/{id}` | DELETE | Permanently delete entire thread |
| trash | `/gmail/v1/users/{userId}/threads/{id}/trash` | POST | Move thread to trash |
| modify | `/gmail/v1/users/{userId}/threads/{id}/modify` | POST | Add/remove labels from all thread messages |

**Thread Operations:** All messages in thread grouped by conversation ID

### 1.5 Users.getProfile (User Information)

| Method | Endpoint | HTTP | Purpose |
|--------|----------|------|---------|
| getProfile | `/gmail/v1/users/{userId}/profile` | GET | Get authenticated user's Gmail profile |

**Profile Fields:** `emailAddress, messagesTotal, threadsTotal, historyId`

---

## 2. Error Handling (Comprehensive Strategy)

### 2.1 HTTP Status Codes & Recovery

| Status | Meaning | Recovery | Example |
|--------|---------|----------|---------|
| **400** | Bad Request | Fix request parameters | Missing required field in send |
| **401** | Invalid Credentials | Refresh access token or re-authorize | Expired token |
| **403** | Usage Limit Exceeded | Check quota in Google Console | Daily limits exceeded |
| **429** | Too Many Requests | Exponential backoff + retry | Rate limit hit |
| **500-504** | Server Error | Exponential backoff + retry | Transient failure |

### 2.2 Rate Limiting (429 Status)

**Three Distinct Limits:**
1. **Mail Sending**: Per-user daily limits shared across all clients
2. **Bandwidth**: Per-user upload/download limits
3. **Concurrent Requests**: Per-user parallel request ceiling

**Batch Guidance:** Do not send batches larger than 50 requests. Gmail may not handle larger batches well.

**Implementation Strategy:**
- Implement exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s with jitter
- Check `Retry-After` header in 429 responses
- Daily limits may block requests for multiple hours after hitting limit

### 2.3 Quota Limits (403 Status)

**403 Daily Limit Exceeded:**
- Request additional quota through Google API Console > Quotas tab
- Different quota for different scopes (compose, modify, readonly)

### 2.4 Token Expiration (401 Status)

**Automatic Handling:**
- Access tokens expire in 1 hour
- Use refresh_token to get new access_token
- Store refresh_token securely (env variable or database)
- Implement automatic token refresh before expiration

---

## 3. OAuth 2.0 Authentication Pattern

### 3.1 Google OAuth Flow

```
User
  ↓
1. Request authorization (consent screen)
  ↓
2. User grants permission
  ↓
3. Receive authorization code
  ↓
4. Exchange code for tokens (access_token + refresh_token)
  ↓
5. Use access_token for API calls
  ↓
6. When expired, use refresh_token to get new access_token
```

### 3.2 Scopes Required

```python
# Core scopes
"https://www.googleapis.com/auth/gmail.compose"      # Send emails
"https://www.googleapis.com/auth/gmail.modify"       # Modify, label, archive
"https://www.googleapis.com/auth/gmail.readonly"     # Read-only access

# Can combine as needed
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
]
```

### 3.3 Implementation Pattern

**Follow existing pattern from `google_drive/client.py`:**

```python
class GmailClient(BaseIntegrationClient):
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.readonly"
    ]

    def __init__(
        self,
        credentials_json: dict | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        # Parse from env vars or passed credentials
        # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        # Support both service account and user OAuth flows
```

**Token Refresh Pattern:**
- Store refresh_token in environment or secure storage
- Check token expiration before each request
- Automatically refresh before making API call
- Handle 401 errors by triggering refresh + retry

---

## 4. MIME/Attachment Handling

### 4.1 Email Message Structure

Gmail API expects messages to be sent as base64url-encoded RFC 5322 format:

```
From: sender@example.com
To: recipient@example.com
Subject: Test Email
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="UTF-8"

Plain text body
--boundary123
Content-Type: application/pdf; name="document.pdf"
Content-Disposition: attachment; filename="document.pdf"
Content-Transfer-Encoding: base64

[base64-encoded-file-data]
--boundary123--
```

### 4.2 Python Implementation (email.mime module)

```python
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64

# Create message
message = MIMEMultipart()
message["To"] = "recipient@example.com"
message["From"] = "sender@example.com"
message["Subject"] = "Test with attachment"

# Add body
body = MIMEText("Email body text")
message.attach(body)

# Add attachment
with open("document.pdf", "rb") as attachment:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment; filename= document.pdf"
    )
    message.attach(part)

# Encode as base64url for Gmail API
raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
```

### 4.3 Supported Attachment Types

- **Documents**: PDF, Word (.doc, .docx), Excel (.xls, .xlsx), PowerPoint (.ppt, .pptx)
- **Images**: JPG, PNG, GIF, BMP, SVG
- **Archives**: ZIP, RAR, 7Z
- **Other**: TXT, CSV, JSON, and most file types

**Limitations:**
- Max message size: 25MB (including attachments)
- Gmail API enforces standard email size limits
- Some file types may be blocked by recipient's email server

---

## 5. Implementation Patterns from Existing Integrations

### 5.1 Exception Hierarchy (Follow `base.py`)

```python
# File: src/integrations/base.py (existing pattern)
class IntegrationError(Exception):
    """Base exception for all integration errors"""

# For Gmail, create:
class GmailError(IntegrationError):
    """Base exception for Gmail API errors"""

class GmailAuthError(GmailError):
    """Authentication/authorization failed (401)"""

class GmailRateLimitError(GmailError):
    """Rate limit exceeded (429) - includes retry_after"""
    def __init__(self, message: str, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(message)

class GmailQuotaExceeded(GmailError):
    """Daily/usage quota exceeded (403)"""
```

### 5.2 Pydantic Models Pattern

Follow `google_drive/models.py` pattern:

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class GmailMessage(BaseModel):
    """Gmail message model"""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    thread_id: str = Field(alias="threadId")
    label_ids: list[str] = Field(default_factory=list, alias="labelIds")
    snippet: str
    payload: dict[str, Any] | None = None
    internal_date: int | None = Field(default=None, alias="internalDate")
    size_estimate: int | None = Field(default=None, alias="sizeEstimate")
    history_id: str | None = Field(default=None, alias="historyId")

class GmailLabel(BaseModel):
    """Gmail label model"""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    label_list_visibility: str = Field(alias="labelListVisibility")
    message_list_visibility: str = Field(alias="messageListVisibility")

class GmailAttachment(BaseModel):
    """Email attachment model"""
    filename: str | None = None
    mime_type: str = Field(alias="mimeType")
    size: int | None = None
    data: str | None = None  # Base64-encoded content
    attachment_id: str | None = Field(default=None, alias="attachmentId")
```

### 5.3 Async Client Pattern

Follow `base.py` BaseIntegrationClient pattern:

```python
class GmailClient(BaseIntegrationClient):
    """Gmail API async client with OAuth support"""

    def __init__(self, ...):
        super().__init__(
            name="gmail",
            base_url="https://gmail.googleapis.com",
            api_key=access_token,
            timeout=30.0,
            max_retries=3,
            retry_base_delay=1.0
        )
        self.user_id = "me"  # Always use "me" for authenticated user

    async def list_messages(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        page_size: int = 10,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List messages from authenticated user's mailbox"""
        params = {
            "userId": self.user_id,
            "pageSize": page_size,
        }
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if page_token:
            params["pageToken"] = page_token

        return await self.get("/v1/users/{userId}/messages", params=params)
```

### 5.4 Tool Registration Pattern

Follow `linkedin/tools.py` pattern:

```python
async def list_messages_tool(
    query: str | None = None,
    label_ids: list[str] | None = None,
    page_size: int = 10,
    page_token: str | None = None,
) -> dict[str, Any]:
    """List messages from Gmail inbox with optional filtering.

    Args:
        query: Gmail search query (e.g., "from:user@example.com", "label:INBOX")
        label_ids: Filter by specific label IDs
        page_size: Number of results per page (1-500)
        page_token: Token for pagination

    Returns:
        Dict containing messages list and next page token
    """
    client = GmailClient()
    await client.authenticate()

    try:
        result = await client.list_messages(
            query=query,
            label_ids=label_ids,
            page_size=page_size,
            page_token=page_token,
        )
        return result
    finally:
        await client.close()
```

---

## 6. Rate Limiting Implementation Strategy

### 6.1 Exponential Backoff Formula

**Recommended by Google:**
```
delay = min((2^n + random(0, 1000ms)), 32000ms)
where n = attempt number (0, 1, 2, 3...)

Sequence: 1s, 2s, 4s, 8s, 16s, 32s (with jitter)
```

### 6.2 Implementation in BaseIntegrationClient

Already implemented in `base.py` at lines 236-314. For Gmail:
- max_retries = 3
- retry_base_delay = 1.0 (1 second)
- Total backoff time: ~63 seconds (1+2+4+8+16+32)

### 6.3 429 Response Handling

```python
async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
    """Override to handle Gmail-specific errors"""

    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            retry_after_seconds = int(retry_after)

        raise GmailRateLimitError(
            f"Rate limit exceeded",
            retry_after=retry_after_seconds
        )

    # Handle other Gmail-specific codes...
```

---

## 7. Implementation Checklist

### Phase 1: Foundations
- [ ] Create exception hierarchy (GmailError, GmailAuthError, GmailRateLimitError, GmailQuotaExceeded)
- [ ] Create Pydantic models (Message, Label, Thread, Draft, Attachment, UserProfile)
- [ ] Implement GmailClient extending BaseIntegrationClient

### Phase 2-5: Tools Implementation
- [ ] Core email operations (list, get, send, create, delete, trash, modify)
- [ ] Label operations (create, delete, list, get, add, remove)
- [ ] Thread operations (list, get, delete, trash, modify)
- [ ] Attachment operations (get attachments, download, send with attachments)
- [ ] Draft operations (create, list, get, send, delete)
- [ ] User profile retrieval

### Phase 6-7: Error Handling & Resilience
- [ ] Implement exponential backoff (1, 2, 4, 8, 16, 32s with jitter)
- [ ] Implement circuit breaker for cascading failures
- [ ] Handle all HTTP error codes (400, 401, 403, 429, 500-504)
- [ ] Implement token refresh on 401
- [ ] Log all errors with sanitization

### Phase 8-9: Testing
- [ ] Unit tests for all methods (>90% coverage)
- [ ] Error handling tests (all HTTP codes, retry logic)
- [ ] Integration tests (multi-step workflows)
- [ ] Mock all external API calls

### Phase 10-11: Live API Testing
- [ ] Test OAuth flow with real Gmail account
- [ ] Send test emails (plain text, HTML, with attachments)
- [ ] Verify message operations (read, star, archive, trash)
- [ ] Test label operations (create, apply, remove)
- [ ] Verify attachments end-to-end
- [ ] Test thread operations
- [ ] Document all test results

### Phase 12: Commit & Deploy
- [ ] All tests pass (unit, integration, live API)
- [ ] Coverage >90% for tools
- [ ] Type checking passes (mypy strict)
- [ ] Linting passes (ruff)
- [ ] Commit with comprehensive message
- [ ] Create GitHub PR

---

## 8. Environment Variables Required

```bash
# OAuth credentials (from Google Cloud Console)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# For live testing
GMAIL_TEST_EMAIL=your-test-email@gmail.com
GMAIL_REFRESH_TOKEN=...  # Obtained after first OAuth flow
```

---

## 9. Key Differences from Other Integrations

| Feature | Google Drive | LinkedIn | Gmail (New) |
|---------|--------------|----------|-----------|
| OAuth Type | Service Account | User OAuth | User OAuth |
| Rate Limit | 1000 requests/day | 300 requests/10s | 250 msgs/s + per-user limits |
| Attachment Handling | File IDs | N/A | MIME + base64url encoding |
| Thread Support | N/A | N/A | Full thread/conversation support |
| Draft Support | N/A | N/A | Draft creation & sending |
| Message Parsing | File content | Profile data | Full MIME parsing required |

---

## 10. References

**Official Documentation:**
- [Gmail API Reference (REST)](https://developers.google.com/workspace/gmail/api/reference/rest)
- [Gmail API Error Handling Guide](https://developers.google.com/workspace/gmail/api/guides/handle-errors)
- [Google OAuth 2.0 for Web Server](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Gmail API Sending Guide](https://developers.google.com/gmail/api/guides/sending)

**Python Libraries:**
- [google-auth async support](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.credentials_async.html)
- [python-httpx async patterns](https://www.python-httpx.org/async/)
- [Python email.mime documentation](https://docs.python.org/3/library/email.mime.html)

**Implementation Examples:**
- [HTTPX AsyncClient patterns](https://betterstack.com/community/guides/scaling-python/httpx-explained/)
- [Gmail API Python Guide](https://thepythoncode.com/article/use-gmail-api-in-python)

---

## Summary

Gmail API integration is straightforward with existing patterns from Google Drive and LinkedIn integrations. Key implementation focuses:
1. **OAuth 2.0** with automatic token refresh
2. **Exponential backoff** for rate limiting (already in BaseIntegrationClient)
3. **MIME encoding** for attachment handling
4. **Error handling** for 401/403/429 status codes
5. **20+ async tools** following existing tool patterns
6. **Live API testing** with real Gmail credentials

Estimated implementation time: **4-5 hours** for complete integration with full testing and documentation.
