# Task: Complete Gmail Integration

**Status:** Pending
**Domain:** backend
**Source:** direct input
**Created:** 2025-12-22

## Summary

Implement complete Gmail integration for email agent, including OAuth client, all endpoint tools, error handling, retry logic, comprehensive testing, and live API validation with real Gmail account. This covers the full development lifecycle from implementation through production deployment. All live API tests will send real test emails to your Gmail inbox to verify all endpoints work correctly.

## Files to Create/Modify

- [ ] `src/integrations/gmail/__init__.py`
- [ ] `src/integrations/gmail/client.py`
- [ ] `src/integrations/gmail/models.py`
- [ ] `src/integrations/gmail/exceptions.py`
- [ ] `src/integrations/gmail/tools.py`
- [ ] `src/integrations/gmail/email_processor.py`
- [ ] `src/integrations/gmail/oauth_handler.py`
- [ ] `tests/integrations/gmail/__init__.py`
- [ ] `tests/integrations/gmail/conftest.py`
- [ ] `tests/integrations/gmail/test_client.py`
- [ ] `tests/integrations/gmail/test_tools.py`
- [ ] `tests/integrations/gmail/test_error_handling.py`
- [ ] `tests/integrations/gmail/test_oauth.py`
- [ ] `tests/integrations/gmail/test_live_api.py`

## Implementation Checklist

### Phase 1: OAuth & Client Setup
- [ ] Implement OAuth 2.0 authentication flow with Google (using test credentials from `.env`)
- [ ] Create GmailClient class with OAuth credentials handling
- [ ] Set up credentials file management and refresh token handling
- [ ] Implement token caching and auto-refresh
- [ ] Create Pydantic models: Message, Thread, Label, Draft, Attachment, UserProfile
- [ ] Define custom exception types (GmailError, GmailAuthError, GmailRateLimitError, GmailQuotaExceeded)
- [ ] Add logging infrastructure with request/response sanitization
- [ ] Use `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from `.env` for OAuth setup

### Phase 2: Tools Implementation - Core Email Operations
- [ ] Create `list_messages()` tool to retrieve emails with filtering by label, sender, date range
- [ ] Create `get_message()` tool to retrieve full message details including headers and body
- [ ] Create `send_message()` tool to send emails with support for HTML/plain text
- [ ] Create `create_draft()` tool to create draft emails
- [ ] Create `send_draft()` tool to send existing drafts
- [ ] Create `delete_message()` tool with permanent/trash support
- [ ] Create `trash_message()` tool to move messages to trash
- [ ] Create `untrash_message()` tool to restore messages from trash
- [ ] Create `mark_as_read()` tool to mark messages as read
- [ ] Create `mark_as_unread()` tool to mark messages as unread
- [ ] Create `star_message()` tool to star/flag messages
- [ ] Create `unstar_message()` tool to remove star from messages
- [ ] Create `archive_message()` tool to archive emails
- [ ] Create `unarchive_message()` tool to restore archived emails

### Phase 3: Tools Implementation - Labels & Organization
- [ ] Create `list_labels()` tool to retrieve all available labels
- [ ] Create `create_label()` tool to create custom labels
- [ ] Create `delete_label()` tool to remove labels
- [ ] Create `get_label()` tool to retrieve label details
- [ ] Create `add_label()` tool to apply labels to messages
- [ ] Create `remove_label()` tool to remove labels from messages
- [ ] Create `modify_message()` tool for batch label operations

### Phase 4: Tools Implementation - Attachments & Content
- [ ] Create `get_message_attachments()` tool to list message attachments
- [ ] Create `download_attachment()` tool to retrieve attachment content
- [ ] Create `send_message_with_attachment()` tool to send emails with file attachments
- [ ] Implement MIME multipart message handling
- [ ] Handle various attachment types and encodings

### Phase 5: Tools Implementation - User & Thread Management
- [ ] Create `get_user_profile()` tool to retrieve authenticated user details
- [ ] Create `list_threads()` tool to retrieve email threads with filtering
- [ ] Create `get_thread()` tool to retrieve complete thread with all messages
- [ ] Create `delete_thread()` tool to delete entire conversation thread
- [ ] Create `trash_thread()` tool to move thread to trash
- [ ] Create `untrash_thread()` tool to restore thread from trash
- [ ] Handle thread pagination for large conversations

### Phase 6: Tools Registration & Configuration
- [ ] Register all tools as MCP tools for agent use
- [ ] Implement response caching for labels and user profile
- [ ] Set up tool parameter validation
- [ ] Create tool documentation with examples
- [ ] Configure pagination defaults for list operations
- [ ] Set message batch size limits

### Phase 7: Error Handling & Resilience
- [ ] Implement exponential backoff with jitter (1s, 2s, 4s, 8s, 16s, 32s)
- [ ] Add retry decorator for transient failures
- [ ] Implement circuit breaker pattern for cascading failures
- [ ] Handle all HTTP error codes (4xx, 5xx)
- [ ] Detect and handle rate limit responses (429 status, quota exceeded)
- [ ] Handle auth failures and automatic token refresh
- [ ] Add detailed error logging with request/response sanitization
- [ ] Create recovery mechanisms for partial failures
- [ ] Handle message size limits (25MB for Gmail)
- [ ] Implement timeout handling for large operations

### Phase 8: Unit Testing (>90% coverage)
- [ ] Create test fixtures and mocks for all Gmail API responses
- [ ] Test OAuth flow (valid/invalid credentials, token refresh)
- [ ] Test client initialization with various credential sources
- [ ] Test list_messages with filters, pagination, sorting
- [ ] Test get_message with various message types
- [ ] Test send_message with HTML and plain text
- [ ] Test draft creation and sending
- [ ] Test message deletion, trash, and untrash
- [ ] Test mark_as_read/unread operations
- [ ] Test star and archive operations
- [ ] Test label creation, deletion, listing
- [ ] Test label application and removal
- [ ] Test attachment retrieval and download
- [ ] Test send_message_with_attachment with various file types
- [ ] Test thread operations
- [ ] Test user profile retrieval
- [ ] Test error handling for all HTTP errors (400, 401, 403, 404, 429, 500, 502, 503, 504)
- [ ] Test retry logic: verify backoff timing, max retries, jitter distribution
- [ ] Test rate limit and quota exceeded handling
- [ ] Test circuit breaker: success, failure threshold, recovery
- [ ] Test token refresh on expired credentials
- [ ] Test concurrent requests
- [ ] Test message size validation
- [ ] Achieve >90% code coverage (src/integrations/gmail/)

### Phase 9: Integration Testing
- [ ] Test end-to-end workflow: list emails → read → reply → archive
- [ ] Test data flow through MCP tools
- [ ] Test error recovery across multiple tool calls
- [ ] Test concurrent email operations
- [ ] Test thread-based operations with multiple messages
- [ ] Test label organization workflows
- [ ] Test attachment handling with various file types
- [ ] Verify email formatting for downstream processing
- [ ] Test batch operations on multiple messages

### Phase 10: Live API Testing with Real Gmail Account
- [ ] Set up test Gmail account (or use personal account with test labels)
- [ ] Test OAuth flow with real credentials from `.env`
- [ ] Validate authentication with actual Google account
- [ ] **Send real test emails to your Gmail inbox:**
  - [ ] Send plain text email and verify received in inbox
  - [ ] Send HTML email and verify formatting
  - [ ] Send email with attachment and verify attachment received
  - [ ] Send email to multiple recipients and verify delivery
- [ ] **Test all email operations on real messages:**
  - [ ] List messages from inbox
  - [ ] Get complete message details
  - [ ] Mark message as read
  - [ ] Star message and verify in Gmail UI
  - [ ] Archive message and verify removed from inbox
  - [ ] Move to trash and verify in trash folder
  - [ ] Create draft and send draft
  - [ ] Reply to received email
- [ ] **Test label operations:**
  - [ ] Create custom test label
  - [ ] Apply label to received test email
  - [ ] Create multiple labels and organize messages
  - [ ] Remove labels from messages
  - [ ] Delete test label
  - [ ] List all labels and verify custom labels present
- [ ] **Test attachment operations:**
  - [ ] Send email with PDF attachment
  - [ ] Send email with image attachment
  - [ ] Send email with document attachment
  - [ ] Download attachments from received emails
  - [ ] Verify attachment content integrity
- [ ] **Test thread operations:**
  - [ ] List threads from inbox
  - [ ] Get complete thread with all messages
  - [ ] Archive entire conversation thread
  - [ ] Delete thread from trash
- [ ] **Test user profile:**
  - [ ] Retrieve authenticated user profile
  - [ ] Verify profile contains correct email address
- [ ] **Verify all operations on real Gmail:**
  - [ ] Check Gmail inbox for all sent test emails
  - [ ] Verify labels appear in Gmail label list
  - [ ] Verify message states (read/unread, starred, archived)
  - [ ] Verify attachments appear in Gmail with correct names
- [ ] Test rate limiting behavior on live API
- [ ] Document any discovered API quirks or limitations
- [ ] Clean up test emails, drafts, and labels after validation

### Phase 11: Live API Test Verification Report
- [ ] Document all test emails sent and received
- [ ] Screenshot Gmail inbox showing received test emails
- [ ] List all endpoints tested and their results
- [ ] Record any API quirks or limitations discovered
- [ ] Verify all 20+ endpoints working correctly
- [ ] Confirm attachment handling works end-to-end
- [ ] Confirm thread operations work correctly
- [ ] Create test result summary file

### Phase 12: Commit & Merge
- [ ] Run all tests: unit, integration, and live API
- [ ] Verify >90% code coverage
- [ ] Fix any linting issues (Ruff)
- [ ] Verify type checking passes (MyPy strict)
- [ ] Clean up test data (emails, labels, drafts) from Gmail
- [ ] Create comprehensive commit message with test results
- [ ] Push to feature branch
- [ ] Create GitHub pull request with test results and live API verification
- [ ] Address any code review feedback
- [ ] Merge to main branch

## Verification

```bash
# Unit tests
python -m pytest tests/integrations/gmail/test_client.py tests/integrations/gmail/test_tools.py tests/integrations/gmail/test_error_handling.py -v

# Check coverage
python -m pytest tests/integrations/gmail/ --cov=src/integrations/gmail --cov-report=term-missing --cov-fail-under=90

# Integration tests (mocked API)
python -m pytest tests/integrations/gmail/ -v -m "not live_api"

# Live API tests (requires Google OAuth credentials in .env)
python -m pytest tests/integrations/gmail/test_live_api.py -v -m "live_api"

# Type checking
mypy src/integrations/gmail/ --strict

# Linting
ruff check src/integrations/gmail/ tests/integrations/gmail/

# All checks before commit
python -m pytest tests/integrations/gmail/ --cov=src/integrations/gmail --cov-fail-under=90 && mypy src/integrations/gmail/ --strict && ruff check src/integrations/gmail/
```

## Live API Testing Setup

**Prerequisites:**
- Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials (Client ID and Client Secret)
- Credentials stored in `.env` as:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
- Test Gmail account credentials or personal Gmail account
- Test labels created in Gmail inbox (optional, for organization testing)

**Test Cases (Real Gmail Inbox):**
- Valid OAuth authentication and token refresh
- Sending plain text emails
- Sending HTML formatted emails
- Sending emails with attachments
- Listing messages with various filters
- Reading complete message details
- Marking messages as read/unread
- Starring and unstarring messages
- Archiving and unarchiving messages
- Moving messages to/from trash
- Creating and sending drafts
- Creating custom labels
- Applying labels to messages
- Listing all labels
- Downloading attachments
- Thread listing and retrieval
- User profile retrieval
- Rate limit and quota handling
- Error recovery on transient failures

**Expected Results:**
- All test emails appear in real Gmail inbox
- All email operations reflected in Gmail UI
- Custom test labels visible in Gmail label list
- Attachments received with correct names and sizes
- Message states (read/unread, starred) match API operations

## Notes

- Gmail API docs: https://developers.google.com/gmail/api/guides
- Gmail Python Client: https://github.com/googleapis/google-api-python-client
- Use environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- OAuth tokens have expiration - implement auto-refresh
- All credentials in `.env` must be excluded from git commits
- Live API tests marked with `@pytest.mark.live_api` decorator
- Test data cleanup ensures no test artifacts remain in Gmail (delete sent test emails, remove test labels)
- Gmail API batch operations require proper error handling
- Message size limit: 25MB including attachments
- Rate limits vary by account type - implement proper backoff
- Draft IDs expire - test with fresh drafts
- Label scope testing: system labels vs custom labels have different behavior
- Thread IDs include all related messages - test conversation threads thoroughly
- MIME handling for multipart messages is critical for attachment support
