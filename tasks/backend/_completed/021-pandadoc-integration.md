# Task: Implement PandaDoc API Integration

**Status:** Pending
**Domain:** Backend
**Created:** 2025-12-23
**Priority:** High
**Complexity:** High

## Summary

Implement complete PandaDoc API client with document template management, PDF generation, e-signature workflows, and recipient management. Build production-ready integration with comprehensive testing, live API validation, and quality assurance.

---

## MANDATORY: Context Files Reading

**BEFORE ANY WORK STARTS, read ALL of these in order:**

- [ ] `.claude/context/TASK_RULES.md` - Understand file locations and task workflow
- [ ] `.claude/context/CODE_QUALITY_RULES.md` - Linting, formatting, type safety standards
- [ ] `.claude/context/TESTING_RULES.md` - Test structure and >90% coverage requirements
- [ ] `.claude/context/PROJECT_CONTEXT.md` - Architecture, tech stack, directory structure
- [ ] `.claude/context/SDK_PATTERNS.md` - Claude Agent SDK patterns and custom tools
- [ ] `.claude/context/SELF-HEALING.md` - Known patterns, common errors, solutions
- [ ] `CLAUDE.md` - Project overview and integration guidelines

**NO EXCEPTIONS.** These files prevent duplicate work and bugs.

---

## Files to Create/Modify

### Core Integration
- [ ] `app/backend/src/integrations/pandadoc/__init__.py`
- [ ] `app/backend/src/integrations/pandadoc/client.py` - PandaDoc API client
- [ ] `app/backend/src/integrations/pandadoc/models.py` - Data models (Document, Template, Recipient, Signature)
- [ ] `app/backend/src/integrations/pandadoc/exceptions.py` - Custom exceptions
- [ ] `app/backend/src/integrations/pandadoc/auth.py` - API key and token management

### Testing - Unit Tests (>90% coverage required)
- [ ] `app/backend/__tests__/unit/integrations/pandadoc/__init__.py`
- [ ] `app/backend/__tests__/unit/integrations/pandadoc/test_client.py` - Client unit tests
- [ ] `app/backend/__tests__/unit/integrations/pandadoc/test_models.py` - Data model tests
- [ ] `app/backend/__tests__/unit/integrations/pandadoc/test_auth.py` - Auth flow tests

### Testing - Fixtures
- [ ] `app/backend/__tests__/fixtures/pandadoc_fixtures.py` - Mock data and fixtures

### Testing - Integration Tests (Live API)
- [ ] `app/backend/__tests__/integration/pandadoc/__init__.py`
- [ ] `app/backend/__tests__/integration/pandadoc/test_pandadoc_live.py` - Live API tests (all endpoints)
- [ ] `app/backend/__tests__/integration/pandadoc/test_pandadoc_templates.py` - Template CRUD tests
- [ ] `app/backend/__tests__/integration/pandadoc/test_pandadoc_documents.py` - Document creation/status tests
- [ ] `app/backend/__tests__/integration/pandadoc/test_pandadoc_recipients.py` - Recipient and e-signature tests

### Documentation
- [ ] `docs/api-endpoints/pandadoc.md` - PandaDoc API endpoint documentation
- [ ] `specs/integrations/pandadoc_api.md` - Integration specification

---

## Implementation Checklist

### Phase 1: Setup & Architecture
- [ ] Read ALL context files (.claude/context/*) - NO EXCEPTIONS
- [ ] Create directory structure: `app/backend/src/integrations/pandadoc/`
- [ ] Design data models (Document, Template, Recipient, Signature, DocumentStatus)
- [ ] Define exception hierarchy (PandaDocException, AuthError, APIError, RateLimitError)
- [ ] Plan API key management and token strategy

### Phase 2: Core Client Implementation
- [ ] Implement `PandaDocClient.__init__()` with API key support
- [ ] Implement template operations: `list_templates()`, `get_template()`, `create_template()`, `delete_template()`
- [ ] Implement document operations: `create_document()`, `get_document()`, `list_documents()`, `download_document()`, `send_document()`
- [ ] Implement recipient operations: `add_recipient()`, `update_recipient()`, `remove_recipient()`, `get_recipient_status()`
- [ ] Implement e-signature flow: `get_signature_requests()`, `update_signature_request()`, `cancel_signature_request()`
- [ ] Implement webhook management: `create_webhook()`, `list_webhooks()`, `delete_webhook()`
- [ ] Implement document status polling: `get_document_status()` with automatic status updates
- [ ] Add request/response logging and error handling
- [ ] Implement retry logic with exponential backoff
- [ ] Add rate limiting compliance (PandaDoc: check API docs for limits)

### Phase 3: Data Models & Serialization
- [ ] Create model classes: Document, Template, Recipient, Signature, DocumentStatus, Webhook
- [ ] Implement JSON serialization/deserialization
- [ ] Add type hints to all models (MyPy strict)
- [ ] Implement model validation
- [ ] Handle date/datetime fields properly (ISO 8601 format)

### Phase 4: Authentication & Token Management
- [ ] Implement API key authentication (Bearer token in headers)
- [ ] Implement token validation
- [ ] Handle invalid/expired credentials gracefully
- [ ] Add logging for auth failures

### Phase 5: Unit Testing (>90% coverage required)
- [ ] Write unit tests for PandaDocClient (mocked API calls)
- [ ] Write tests for data model serialization
- [ ] Write tests for error handling and retries
- [ ] Write tests for API key validation
- [ ] Test edge cases: empty results, malformed responses, auth failures, webhook payloads
- [ ] Run: `pytest app/backend/__tests__/unit/integrations/pandadoc/ -v --cov=app/backend/src/integrations/pandadoc`
- [ ] **REQUIREMENT:** Coverage >90% for tools. If below, add tests until passing.

### Phase 6: Live API Testing (using .env credentials)
- [ ] Setup .env with PandaDoc API key: `PANDADOC_API_KEY=xxx`
- [ ] Create test templates in PandaDoc account (or use dedicated test workspace)
- [ ] Implement live API tests in `test_pandadoc_live.py`
- [ ] Test ALL endpoints:
  - Template listing, creation, retrieval, deletion
  - Document creation with template variables
  - Document status polling
  - Document download
  - Recipient addition and status tracking
  - E-signature request creation and updates
  - Webhook creation and management
  - Document sending
- [ ] Run: `pytest app/backend/__tests__/integration/pandadoc/ -v -s`
- [ ] **REQUIREMENT:** ALL tests MUST PASS. If any fail, debug and FIX ORIGINAL CODE before proceeding.
- [ ] Verify no API rate limits exceeded
- [ ] Verify all responses match expected structure
- [ ] Test webhook signature verification (if applicable)

### Phase 7: Code Quality Assurance
- [ ] Run Ruff linter: `ruff check app/backend/src/integrations/pandadoc/`
  - **REQUIREMENT:** Zero linting errors
- [ ] Run MyPy type checker: `mypy app/backend/src/integrations/pandadoc/ --strict`
  - **REQUIREMENT:** Zero type errors in strict mode
- [ ] Fix any violations in original code (not test code)
- [ ] Ensure no .env or API keys are visible in code

### Phase 8: Pre-commit Validation
- [ ] Run pre-commit: `pre-commit run --all-files`
  - **REQUIREMENT:** All checks must pass (no errors, no security vulnerabilities)
- [ ] Fix any formatting issues automatically or manually
- [ ] Verify no secrets are committed

### Phase 9: Documentation & Learning
- [ ] Document any mistakes/learnings in `.claude/context/SELF-HEALING.md`
  - Common PandaDoc API quirks discovered
  - Rate limit behaviors and handling
  - E-signature workflow edge cases
  - Webhook payload structures
  - Any workarounds implemented
  - PDF generation timing considerations
- [ ] Keep documentation brief and actionable (next agent should learn, not read essay)
- [ ] Create `docs/api-endpoints/pandadoc.md` with endpoint examples
- [ ] Document in `specs/integrations/pandadoc_api.md`

### Phase 10: Commit & Push
- [ ] Verify git status: `git status`
  - **REQUIREMENT:** .env NOT in staging area
  - **REQUIREMENT:** Only production code committed (no test files unless they're fixtures)
- [ ] Add integration code: `git add app/backend/src/integrations/pandadoc/`
- [ ] Add fixtures: `git add app/backend/__tests__/fixtures/pandadoc_fixtures.py`
- [ ] Commit: `git commit -m "feat(pandadoc): add complete PandaDoc API integration"`
- [ ] Push: `git push origin main`
- [ ] **REQUIREMENT:** No test files (test_*.py) in commit, only fixture files
- [ ] Verify commit on GitHub has no API keys in diff

---

## Verification Commands

### Run All Checks (Execute in Order)

```bash
# 1. Context files check (manual - read all files first)
echo "✓ Read all .claude/context files"

# 2. Unit tests
pytest app/backend/__tests__/unit/integrations/pandadoc/ -v --cov=app/backend/src/integrations/pandadoc
# Must show: coverage ≥ 90%

# 3. Live API tests (requires .env with PANDADOC_API_KEY)
pytest app/backend/__tests__/integration/pandadoc/ -v -s
# Must show: all tests PASSED

# 4. Linting
ruff check app/backend/src/integrations/pandadoc/
# Must show: 0 errors

# 5. Type checking
mypy app/backend/src/integrations/pandadoc/ --strict
# Must show: 0 errors

# 6. Pre-commit
pre-commit run --all-files
# Must show: all checks passed

# 7. Git status verification
git status
# Must show: .env NOT in staging

# 8. Final verification
echo "✓ Integration complete and tested"
```

### Quick Status Check

```bash
# Check coverage
pytest app/backend/__tests__/unit/integrations/pandadoc/ --cov --cov-report=term-missing

# Check linting status
ruff check app/backend/src/integrations/pandadoc/ && echo "✓ Linting passed"

# Check type safety
mypy app/backend/src/integrations/pandadoc/ --strict && echo "✓ Types passed"
```

---

## Known Patterns & Gotchas

**PandaDoc API specifics:**
- Use `Bearer token` authentication in Authorization header
- API key format: typically long alphanumeric string
- All timestamps are ISO 8601 strings (parse to datetime)
- Document status field can have values: `document.draft`, `document.sent`, `document.viewed`, `document.completed`, `document.declined`, `document.expired`
- Webhook payloads include signatures for security verification
- PDF generation is asynchronous - use polling or webhooks to track completion
- Template variable names use `{{variable_name}}` syntax
- Recipients must have valid email addresses
- Rate limits vary by plan (check PandaDoc API docs for your account)

See `.claude/context/SELF-HEALING.md` for other integration patterns.

---

## Success Criteria

✅ ALL of the following MUST be true:

- [ ] All context files read completely
- [ ] All unit tests pass (>90% coverage)
- [ ] All live API tests pass (100% endpoints)
- [ ] Ruff linting: 0 errors
- [ ] MyPy type checking: 0 errors (strict mode)
- [ ] Pre-commit validation: all checks pass
- [ ] .env file NOT committed
- [ ] No test files (test_*.py) committed (fixtures OK)
- [ ] Code committed to GitHub
- [ ] Learnings documented in SELF-HEALING.md
- [ ] Documentation complete (docs/ and specs/)

If ANY of these are false, task is not complete.

---

## Notes

- PandaDoc API documentation: https://developers.pandadoc.com/
- Store API key in .env as: `PANDADOC_API_KEY`
- Live API testing uses actual PandaDoc account (test templates/documents)
- All errors during testing MUST be fixed in original code, not worked around
- Webhook testing may require tunneling tool (ngrok) for local development
- Next agent will benefit from learnings documented in SELF-HEALING.md
