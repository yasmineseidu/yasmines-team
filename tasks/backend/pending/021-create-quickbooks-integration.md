# Task: Create QuickBooks Integration Client

**Status:** Pending
**Domain:** backend
**Source:** direct input
**Created:** 2025-12-21

## Summary

Implement a QuickBooks integration client that provides methods to interact with the QuickBooks Online API. This includes managing customers, invoices, expenses, and financial data synchronization.

## Files to Create/Modify

- [ ] `app/backend/src/integrations/quickbooks.py`
- [ ] `app/backend/tests/integrations/test_quickbooks.py`

## Implementation Checklist

- [ ] Create `QuickBooksClient` class with OAuth2 authentication
- [ ] Implement method to fetch customers
- [ ] Implement method to create a new customer
- [ ] Implement method to fetch invoices
- [ ] Implement method to create an invoice
- [ ] Implement method to fetch expenses
- [ ] Implement method to create an expense
- [ ] Implement method to fetch company info
- [ ] Handle OAuth2 token refresh
- [ ] Implement error handling and retry logic
- [ ] Add type hints for all methods
- [ ] Write unit tests with mocked API responses
- [ ] Add integration tests (if live API testing required)
- [ ] Document usage in docstrings

## Verification

```bash
# Run tests
cd /Users/yasmineseidu/Desktop/Coding/yasmines-team
python -m pytest app/backend/tests/integrations/test_quickbooks.py -v

# Check type hints
python -m mypy app/backend/src/integrations/quickbooks.py --strict

# Check code quality
python -m ruff check app/backend/src/integrations/quickbooks.py
```

## Notes

- QuickBooks uses OAuth2 for authentication - implement token storage and refresh
- Reference existing integration patterns in `app/backend/src/integrations/reddit.py` and `tavily.py`
- Use `httpx` or `requests` library for API calls
- Store OAuth credentials securely in environment variables
- Handle realm ID (company ID) parameter for multi-tenant support
- API responses may require entity expansion (includes parameter)
- Implement query-based filtering for list endpoints
