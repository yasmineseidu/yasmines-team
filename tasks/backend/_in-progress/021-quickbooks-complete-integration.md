# Task: Complete QuickBooks Integration

**Status:** Pending
**Domain:** backend
**Source:** direct input
**Created:** 2025-12-21

## Summary

Implement complete QuickBooks integration for financial management, including client, operations, error handling, retry logic, comprehensive testing, and live API validation. This covers the full development lifecycle from client implementation through production deployment.

## Files to Create/Modify

- [ ] `src/integrations/quickbooks/__init__.py`
- [ ] `src/integrations/quickbooks/client.py`
- [ ] `src/integrations/quickbooks/models.py`
- [ ] `src/integrations/quickbooks/exceptions.py`
- [ ] `src/integrations/quickbooks/operations.py`
- [ ] `src/integrations/quickbooks/token_manager.py`
- [ ] `tests/integrations/quickbooks/__init__.py`
- [ ] `tests/integrations/quickbooks/conftest.py`
- [ ] `tests/integrations/quickbooks/test_client.py`
- [ ] `tests/integrations/quickbooks/test_operations.py`
- [ ] `tests/integrations/quickbooks/test_error_handling.py`
- [ ] `tests/integrations/quickbooks/test_live_api.py`

## Implementation Checklist

### Phase 1: Client & Models
- [ ] Create QuickBooksClient class with OAuth2 authentication
- [ ] Implement OAuth2 token refresh mechanism
- [ ] Create Pydantic models: Customer, Invoice, Expense, CompanyInfo, JournalEntry
- [ ] Define custom exception types (QuickBooksError, QuickBooksAuthError, QuickBooksRateLimitError)
- [ ] Implement realm ID (company ID) parameter handling
- [ ] Add logging infrastructure

### Phase 2: Core Operations
- [ ] Implement fetch customers (with filtering, pagination)
- [ ] Implement create customer
- [ ] Implement update customer
- [ ] Implement fetch invoices (with filtering, pagination)
- [ ] Implement create invoice
- [ ] Implement update invoice
- [ ] Implement fetch expenses (with filtering, pagination)
- [ ] Implement create expense
- [ ] Implement update expense
- [ ] Implement fetch company info
- [ ] Implement query-based filtering for list endpoints
- [ ] Register operations as MCP tools for agent use

### Phase 3: Error Handling & Resilience
- [ ] Implement exponential backoff with jitter (1s, 2s, 4s, 8s, 16s, 32s)
- [ ] Add retry decorator for transient failures
- [ ] Implement circuit breaker pattern for cascading failures
- [ ] Handle all HTTP error codes (400, 401, 403, 404, 429, 500, 502, 503, 504)
- [ ] Detect and handle rate limit responses (429 status, retry-after headers)
- [ ] Handle OAuth2 token expiration and refresh
- [ ] Handle realm ID (company ID) validation
- [ ] Add detailed error logging with request/response sanitization
- [ ] Create recovery mechanisms for partial failures

### Phase 4: Unit Testing (>90% coverage)
- [ ] Create test fixtures and mocks for all API responses
- [ ] Test client initialization (valid/invalid credentials, OAuth2 flow)
- [ ] Test OAuth2 token refresh mechanism
- [ ] Test customer operations (fetch, create, update)
- [ ] Test invoice operations (fetch, create, update)
- [ ] Test expense operations (fetch, create, update)
- [ ] Test company info retrieval
- [ ] Test error handling for all HTTP errors
- [ ] Test retry logic: verify backoff timing, max retries, jitter distribution
- [ ] Test rate limit detection and handling
- [ ] Test circuit breaker: success, failure threshold, recovery
- [ ] Test concurrent API operations
- [ ] Achieve >90% code coverage (src/integrations/quickbooks/)

### Phase 5: Integration Testing
- [ ] Test end-to-end workflow: create customer → create invoice → record expense
- [ ] Test data flow through MCP tools
- [ ] Test error recovery across multiple operations
- [ ] Test concurrent operations
- [ ] Test OAuth2 token refresh during operations
- [ ] Test multi-tenant support (realm ID handling)
- [ ] Test data consistency across operations

### Phase 6: Live API Testing
- [ ] Set up test QuickBooks Online account
- [ ] Test with real API credentials from .env (QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET, QUICKBOOKS_REALM_ID)
- [ ] Validate OAuth2 authentication flow
- [ ] Create real test customer and verify response
- [ ] Create real test invoice and verify calculation
- [ ] Create real test expense and verify recording
- [ ] Test OAuth2 token refresh behavior
- [ ] Test rate limiting behavior
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
python -m pytest tests/integrations/quickbooks/test_client.py tests/integrations/quickbooks/test_operations.py tests/integrations/quickbooks/test_error_handling.py -v

# Check coverage
python -m pytest tests/integrations/quickbooks/ --cov=src/integrations/quickbooks --cov-report=term-missing --cov-fail-under=90

# Integration tests (mocked API)
python -m pytest tests/integrations/quickbooks/ -v -m "not live_api"

# Live API tests (requires QUICKBOOKS_* credentials in .env)
python -m pytest tests/integrations/quickbooks/test_live_api.py -v -m "live_api"

# Type checking
mypy src/integrations/quickbooks/ --strict

# Linting
ruff check src/integrations/quickbooks/ tests/integrations/quickbooks/

# All checks before commit
python -m pytest tests/integrations/quickbooks/ --cov=src/integrations/quickbooks --cov-fail-under=90 && mypy src/integrations/quickbooks/ --strict && ruff check src/integrations/quickbooks/
```

## Live API Testing Setup

**Prerequisites:**
- QuickBooks Online account with API access
- OAuth2 credentials in `.env`: `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`
- Realm ID (company ID) in `.env`: `QUICKBOOKS_REALM_ID`
- Test company setup with clean data

**Test Cases:**
- OAuth2 authentication and token refresh
- Customer CRUD operations
- Invoice creation and verification
- Expense recording
- Data consistency validation

## Notes

- **API Base URL:** https://quickbooks.api.intuit.com/
- **OAuth2 Scopes:** com.intuit.quickbooks.accounting
- **Credential Storage:** Use `.env` variables (QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET, QUICKBOOKS_REALM_ID)
- **All credentials in `.env` must be excluded from git commits**
- **Live API tests marked with `@pytest.mark.live_api` decorator**
- **Test data cleanup ensures no test artifacts remain in QuickBooks account**
- **Entity expansion:** Use `includes` parameter for detailed responses
- **Query filtering:** Implement JPQL-style query filtering for list endpoints
