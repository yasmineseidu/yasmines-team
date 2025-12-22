# Task: Complete Google Drive Integration

**Status:** Pending
**Domain:** backend
**Source:** direct input
**Created:** 2025-12-22

## Summary

Implement complete Google Drive integration for document management agent, including OAuth client, tools, error handling, retry logic, comprehensive testing, and live API validation. This covers the full development lifecycle from implementation through production deployment.

## Files to Create/Modify

- [ ] `src/integrations/google_drive/__init__.py`
- [ ] `src/integrations/google_drive/client.py`
- [ ] `src/integrations/google_drive/models.py`
- [ ] `src/integrations/google_drive/exceptions.py`
- [ ] `src/integrations/google_drive/tools.py`
- [ ] `src/integrations/google_drive/document_processor.py`
- [ ] `src/integrations/google_drive/oauth_handler.py`
- [ ] `tests/integrations/google_drive/__init__.py`
- [ ] `tests/integrations/google_drive/conftest.py`
- [ ] `tests/integrations/google_drive/test_client.py`
- [ ] `tests/integrations/google_drive/test_tools.py`
- [ ] `tests/integrations/google_drive/test_error_handling.py`
- [ ] `tests/integrations/google_drive/test_oauth.py`
- [ ] `tests/integrations/google_drive/test_live_api.py`

## Implementation Checklist

### Phase 1: OAuth & Client Setup
- [ ] Implement OAuth 2.0 authentication flow with Google
- [ ] Create GoogleDriveClient class with OAuth credentials handling
- [ ] Set up credentials file management and refresh token handling
- [ ] Implement token caching and auto-refresh
- [ ] Create Pydantic models: File, Folder, DriveMetadata, Permission
- [ ] Define custom exception types (GoogleDriveError, GoogleDriveAuthError, GoogleDriveRateLimitError, GoogleDriveQuotaExceeded)
- [ ] Add logging infrastructure with request/response sanitization

### Phase 2: Tools Implementation
- [ ] Create `list_files()` tool to retrieve files with filtering by name, type, folder
- [ ] Create `get_file_metadata()` tool to extract file details (name, size, modified, owner)
- [ ] Create `read_document_content()` tool to retrieve text from Docs/Sheets/PDFs
- [ ] Create `create_document()` tool to create new Google Docs/Sheets
- [ ] Create `upload_file()` tool to upload files from bytes/streams
- [ ] Create `delete_file()` tool with soft delete support
- [ ] Create `share_file()` tool to manage permissions and sharing
- [ ] Create `export_document()` tool to export as PDF/CSV/DOCX
- [ ] Implement pagination for large file lists
- [ ] Support filtering by date range, file type, ownership
- [ ] Handle folder hierarchy and nested queries
- [ ] Register tools as MCP tools for agent use
- [ ] Implement response caching for file metadata

### Phase 3: Error Handling & Resilience
- [ ] Implement exponential backoff with jitter (1s, 2s, 4s, 8s, 16s, 32s)
- [ ] Add retry decorator for transient failures
- [ ] Implement circuit breaker pattern for cascading failures
- [ ] Handle all HTTP error codes (4xx, 5xx)
- [ ] Detect and handle rate limit responses (403 quota exceeded, 429 rate limit)
- [ ] Handle auth failures and automatic token refresh
- [ ] Add detailed error logging with request/response sanitization
- [ ] Create recovery mechanisms for partial failures
- [ ] Handle large file timeouts (implement chunked uploads/downloads)

### Phase 4: Unit Testing (>90% coverage)
- [ ] Create test fixtures and mocks for all Google Drive API responses
- [ ] Test OAuth flow (valid/invalid credentials, token refresh)
- [ ] Test client initialization with various credential sources
- [ ] Test list_files with filters, pagination, sorting
- [ ] Test get_file_metadata with various file types
- [ ] Test read_document_content for Docs, Sheets, PDFs
- [ ] Test create_document with various types and properties
- [ ] Test upload_file with various file sizes and types
- [ ] Test delete_file with permanent and soft delete
- [ ] Test share_file with different permission levels
- [ ] Test export_document for different formats
- [ ] Test error handling for all HTTP errors (400, 401, 403, 404, 429, 500, 502, 503, 504)
- [ ] Test retry logic: verify backoff timing, max retries, jitter distribution
- [ ] Test rate limit and quota exceeded handling
- [ ] Test circuit breaker: success, failure threshold, recovery
- [ ] Test token refresh on expired credentials
- [ ] Test concurrent requests
- [ ] Test large file handling (chunked operations)
- [ ] Achieve >90% code coverage (src/integrations/google_drive/)

### Phase 5: Integration Testing
- [ ] Test end-to-end workflow: list files → read document → export → share
- [ ] Test data flow through MCP tools
- [ ] Test error recovery across multiple tool calls
- [ ] Test concurrent file operations
- [ ] Test with various document types (Docs, Sheets, PDFs)
- [ ] Test folder hierarchy navigation
- [ ] Test permission changes and sharing workflows
- [ ] Test large file uploads and downloads
- [ ] Verify content formatting for downstream processing

### Phase 6: Live API Testing
- [ ] Set up test Google Drive account with sample documents
- [ ] Test OAuth flow with real credentials
- [ ] Validate authentication with actual Google account
- [ ] List files from real Google Drive
- [ ] Test document reading across different file types
- [ ] Create test documents and verify creation
- [ ] Upload files and verify file storage
- [ ] Test sharing and permission changes
- [ ] Export documents in various formats
- [ ] Test rate limiting behavior on live API
- [ ] Verify quota handling and reset behavior
- [ ] Document any discovered API quirks or limitations
- [ ] Clean up test data after validation

### Phase 7: Commit & Merge
- [ ] Run all tests: unit, integration, and live API
- [ ] Verify >90% code coverage
- [ ] Fix any linting issues (Ruff)
- [ ] Verify type checking passes (MyPy strict)
- [ ] Create comprehensive commit message
- [ ] Push to feature branch
- [ ] Create GitHub pull request with test results
- [ ] Address any code review feedback
- [ ] Merge to main branch

## Verification

```bash
# Unit tests
python -m pytest tests/integrations/google_drive/test_client.py tests/integrations/google_drive/test_tools.py tests/integrations/google_drive/test_error_handling.py -v

# Check coverage
python -m pytest tests/integrations/google_drive/ --cov=src/integrations/google_drive --cov-report=term-missing --cov-fail-under=90

# Integration tests (mocked API)
python -m pytest tests/integrations/google_drive/ -v -m "not live_api"

# Live API tests (requires Google Drive credentials)
python -m pytest tests/integrations/google_drive/test_live_api.py -v -m "live_api"

# Type checking
mypy src/integrations/google_drive/ --strict

# Linting
ruff check src/integrations/google_drive/ tests/integrations/google_drive/

# All checks before commit
python -m pytest tests/integrations/google_drive/ --cov=src/integrations/google_drive --cov-fail-under=90 && mypy src/integrations/google_drive/ --strict && ruff check src/integrations/google_drive/
```

## Live API Testing Setup

**Prerequisites:**
- Google Cloud Project with Drive API enabled
- OAuth 2.0 credentials (service account or user credentials)
- Credentials stored in `.env` as `GOOGLE_DRIVE_CREDENTIALS_JSON`
- Test documents available in test Google Drive
- Test folder created for integration testing

**Test Cases:**
- Valid OAuth authentication and token refresh
- File listing with various filters
- Document reading from multiple file types
- Document creation
- File upload and storage verification
- Permission management and sharing
- Document export in multiple formats
- Rate limit and quota handling
- Error recovery on transient failures

## Notes

- Google Drive API docs: https://developers.google.com/drive/api/guides/about-sdk
- Google Workspace SDK: https://github.com/googleapis/google-api-python-client
- Use environment variables: `GOOGLE_DRIVE_CREDENTIALS_JSON`
- All credentials in `.env` must be excluded from git commits
- Live API tests marked with `@pytest.mark.live_api` decorator
- Test data cleanup ensures no test artifacts remain in Google Drive
- OAuth tokens have expiration - implement auto-refresh
- Different scopes needed for read vs. write operations
