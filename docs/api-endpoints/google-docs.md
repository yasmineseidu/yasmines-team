# Google Docs API Integration

## Overview

Complete async client for Google Docs API v1 with comprehensive error handling, retry logic, rate limiting, and batch operations support.

- **Base URL**: `https://docs.googleapis.com/v1`
- **Drive API**: `https://www.googleapis.com/drive/v3`
- **Authentication**: OAuth2 with service account credentials
- **Rate Limits**:
  - Read: 300 requests/min per user
  - Write: 60 requests/min per user
  - Batch operations count as 1 request regardless of subrequests
- **API Version**: v1
- **Last Updated**: 2025-12-22

## Authentication

### Setup

1. Create Google Workspace service account
2. Enable Google Docs API and Google Drive API
3. Set `GOOGLE_DOCS_CREDENTIALS` in `.env` with service account JSON:

```bash
GOOGLE_DOCS_CREDENTIALS='{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "access_token": "..."
}'
```

### OAuth2 Scopes

- `https://www.googleapis.com/auth/documents` - Full document access
- `https://www.googleapis.com/auth/drive.file` - File and folder access

## Endpoints

### 1. Create Document

**Method**: POST
**Path**: `/drive/v3/files`
**Description**: Create a new Google Doc

**Request Parameters**:
- `title` (string, required): Document title
- `parent_folder_id` (string, optional): Google Drive folder ID

**Response Schema**:
```json
{
  "documentId": "string",
  "title": "string",
  "mimeType": "application/vnd.google-apps.document"
}
```

**Example Request**:
```python
from src.integrations.google_docs import GoogleDocsClient

client = GoogleDocsClient(credentials_json=credentials)
await client.authenticate()

doc = await client.create_document(
    title="My Proposal",
    parent_folder_id="folder-123"
)
print(f"Created document: {doc['documentId']}")
```

**Example Response**:
```json
{
  "documentId": "1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
  "title": "My Proposal",
  "mimeType": "application/vnd.google-apps.document"
}
```

**Error Codes**:
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Invalid credentials
- `403`: Forbidden - Insufficient permissions
- `429`: Rate Limit Exceeded
- `500`: Internal Server Error

**Test Status**: ✅ PASSED (Unit tests)

---

### 2. Get Document

**Method**: GET
**Path**: `/v1/documents/{documentId}`
**Description**: Retrieve document metadata and content

**Request Parameters**:
- `document_id` (string, required): Google Doc ID

**Response Schema**:
```json
{
  "documentId": "string",
  "title": "string",
  "body": {
    "content": []
  },
  "revisionId": "string"
}
```

**Example Request**:
```python
doc = await client.get_document(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE"
)
print(f"Document: {doc['title']}")
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 3. Insert Text

**Method**: POST
**Path**: `/v1/documents/{documentId}:batchUpdate`
**Description**: Insert text at specified position in document

**Request Parameters**:
- `document_id` (string, required): Google Doc ID
- `text` (string, required): Text to insert
- `index` (int, optional): Position (1-based, default: 1)

**Response Schema**:
```json
{
  "documentId": "string",
  "replies": []
}
```

**Example Request**:
```python
result = await client.insert_text(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
    text="Hello World!",
    index=1
)
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 4. Batch Update

**Method**: POST
**Path**: `/v1/documents/{documentId}:batchUpdate`
**Description**: Execute multiple update operations in single request

**Request Parameters**:
- `document_id` (string, required): Google Doc ID
- `requests` (list, required): List of update request objects

**Supported Operations**:
- `insertText` - Insert text at position
- `updateTextStyle` - Apply formatting (bold, italic, colors)
- `insertTable` - Create table
- `deleteContentRange` - Delete content
- `insertInlineImage` - Insert image
- `createParagraphBullets` - Create bulleted list

**Response Schema**:
```json
{
  "documentId": "string",
  "replies": []
}
```

**Example Request**:
```python
requests = [
    {
        "insertText": {
            "text": "Hello ",
            "location": {"index": 1}
        }
    },
    {
        "updateTextStyle": {
            "range": {"startIndex": 1, "endIndex": 6},
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    }
]

result = await client.batch_update(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
    requests=requests
)
```

**Note**: Batch operations count as 1 API request regardless of number of subrequests.

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 5. Format Text

**Method**: POST
**Path**: `/v1/documents/{documentId}:batchUpdate`
**Description**: Apply formatting to text (bold, italic, colors, etc)

**Request Parameters**:
- `document_id` (string, required): Google Doc ID
- `start_index` (int, required): Start position (0-based)
- `end_index` (int, required): End position (0-based)
- `bold` (bool, optional): Apply bold formatting
- `italic` (bool, optional): Apply italic formatting
- `underline` (bool, optional): Apply underline
- `font_size` (int, optional): Font size in points
- `text_color` (dict, optional): RGB color

**Response Schema**:
```json
{
  "documentId": "string",
  "replies": []
}
```

**Example Request**:
```python
result = await client.format_text(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
    start_index=0,
    end_index=11,
    bold=True,
    text_color={"red": 0.0, "green": 0.0, "blue": 0.0}
)
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 6. Create Table

**Method**: POST
**Path**: `/v1/documents/{documentId}:batchUpdate`
**Description**: Insert table into document

**Request Parameters**:
- `document_id` (string, required): Google Doc ID
- `rows` (int, required): Number of rows
- `columns` (int, required): Number of columns
- `index` (int, optional): Position in document (default: 1)

**Response Schema**:
```json
{
  "documentId": "string",
  "replies": []
}
```

**Example Request**:
```python
result = await client.create_table(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
    rows=3,
    columns=2
)
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 7. Share Document

**Method**: POST
**Path**: `/drive/v3/files/{documentId}/permissions`
**Description**: Share document with users or groups

**Request Parameters**:
- `document_id` (string, required): Google Doc ID
- `email` (string, required): Email address or group
- `role` (string, optional): "reader", "commenter", or "writer" (default: "reader")

**Response Schema**:
```json
{
  "kind": "drive#permission",
  "id": "string",
  "type": "user",
  "emailAddress": "string",
  "role": "string"
}
```

**Example Request**:
```python
result = await client.share_document(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE",
    email="collaborator@example.com",
    role="writer"
)
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

### 8. Get Document Permissions

**Method**: GET
**Path**: `/drive/v3/files/{documentId}/permissions`
**Description**: List all sharing permissions on document

**Request Parameters**:
- `document_id` (string, required): Google Doc ID

**Response Schema**:
```json
{
  "permissions": [
    {
      "kind": "drive#permission",
      "id": "string",
      "type": "user",
      "role": "owner"
    }
  ]
}
```

**Example Request**:
```python
permissions = await client.get_document_permissions(
    document_id="1BxiMVs0XRA5nFMKUVo64-JsEi9bs2-srA4KyLBgwtQE"
)
for perm in permissions:
    print(f"{perm['type']}: {perm['role']}")
```

**Error Codes**:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `429`: Rate Limit Exceeded

**Test Status**: ✅ PASSED (Unit tests)

---

## Error Handling

### Custom Exceptions

```python
from src.integrations.google_docs import (
    GoogleDocsError,           # Base exception
    GoogleDocsAuthError,       # Authentication failed (401)
    GoogleDocsRateLimitError,  # Rate limited (429)
    GoogleDocsQuotaError,      # Quota exceeded
)
```

### Error Handling Example

```python
try:
    doc = await client.create_document(title="Test")
except GoogleDocsAuthError:
    print("Authentication failed - check credentials")
except GoogleDocsRateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after} seconds")
except GoogleDocsError as e:
    print(f"Error: {e.message} (status: {e.status_code})")
```

## Resilience Features

### Exponential Backoff

All operations include automatic exponential backoff retry:
- Base delay: 1 second
- Max retries: 3
- Backoff multiplier: 2x
- Jitter: ±10%

### Rate Limiting

Automatic rate limiting respects Google Docs API limits:
- Read: 300 requests/min per user
- Write: 60 requests/min per user

### Retry Behavior

- **4xx Errors**: Not retried (except 429)
- **5xx Errors**: Retried with exponential backoff
- **429 Rate Limit**: Retried with exponential backoff
- **Network Timeouts**: Retried with exponential backoff

## Testing

### Unit Tests

All methods have comprehensive unit test coverage (25 tests, 100% passing):

```bash
cd app/backend
python -m pytest __tests__/integrations/google_docs/test_client.py -v
```

### Live API Tests

Live API tests require `GOOGLE_DOCS_CREDENTIALS` in `.env`:

```bash
python -m pytest __tests__/integrations/google_docs/test_live_api.py -v -m live_api
```

## Sample Code

### Complete Workflow

```python
from src.integrations.google_docs import GoogleDocsClient

# Initialize client
client = GoogleDocsClient(credentials_json=credentials)

# Authenticate
await client.authenticate()

# Create document
doc = await client.create_document(title="My Proposal")
doc_id = doc["documentId"]

# Add title
await client.insert_text(doc_id, "My Proposal\n")

# Format title as bold
await client.format_text(
    doc_id,
    start_index=0,
    end_index=11,
    bold=True,
    font_size=16
)

# Add content
await client.insert_text(doc_id, "This is my proposal content.\n")

# Create table
await client.create_table(doc_id, rows=2, columns=2)

# Share with collaborator
await client.share_document(
    doc_id,
    email="collaborator@example.com",
    role="writer"
)

print(f"Document created: {doc_id}")
```

## References

- [Official Google Docs API Documentation](https://developers.google.com/workspace/docs/api/reference/rest)
- [Google Docs API Guides](https://developers.google.com/workspace/docs/api/how-tos/overview)
- [OAuth2 Authentication](https://developers.google.com/identity/protocols/oauth2)
- [Rate Limiting Documentation](https://developers.google.com/workspace/docs/api/limits)
