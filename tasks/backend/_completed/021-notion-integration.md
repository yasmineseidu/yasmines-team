# Task: Implement Notion API Integration

**Status:** Pending
**Domain:** Backend
**Created:** 2025-12-23
**Priority:** High
**Complexity:** High

## Summary

Implement complete Notion API client with full database CRUD operations, block manipulation, page templates, and workspace integration. Build production-ready integration with comprehensive testing, live API validation, and quality assurance.

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
- [ ] `app/backend/src/integrations/notion/__init__.py`
- [ ] `app/backend/src/integrations/notion/client.py` - Notion API client
- [ ] `app/backend/src/integrations/notion/models.py` - Data models (Database, Page, Block, User)
- [ ] `app/backend/src/integrations/notion/exceptions.py` - Custom exceptions
- [ ] `app/backend/src/integrations/notion/auth.py` - OAuth2 and token management

### Testing - Unit Tests (>90% coverage required)
- [ ] `app/backend/__tests__/unit/integrations/notion/__init__.py`
- [ ] `app/backend/__tests__/unit/integrations/notion/test_client.py` - Client unit tests
- [ ] `app/backend/__tests__/unit/integrations/notion/test_models.py` - Data model tests
- [ ] `app/backend/__tests__/unit/integrations/notion/test_auth.py` - Auth flow tests

### Testing - Fixtures
- [ ] `app/backend/__tests__/fixtures/notion_fixtures.py` - Mock data and fixtures

### Testing - Integration Tests (Live API)
- [ ] `app/backend/__tests__/integration/notion/__init__.py`
- [ ] `app/backend/__tests__/integration/notion/test_notion_live.py` - Live API tests (all endpoints)
- [ ] `app/backend/__tests__/integration/notion/test_notion_databases.py` - Database CRUD tests
- [ ] `app/backend/__tests__/integration/notion/test_notion_pages.py` - Page creation/update tests
- [ ] `app/backend/__tests__/integration/notion/test_notion_blocks.py` - Block manipulation tests

### Documentation
- [ ] `docs/api-endpoints/notion.md` - Notion API endpoint documentation
- [ ] `specs/integrations/notion_api.md` - Integration specification

---

## Implementation Checklist

### Phase 1: Setup & Architecture
- [ ] Read ALL context files (.claude/context/*) - NO EXCEPTIONS
- [ ] Create directory structure: `app/backend/src/integrations/notion/`
- [ ] Design data models (Database, Page, Block, User, QueryResult)
- [ ] Define exception hierarchy (NotionException, AuthError, APIError, RateLimitError)
- [ ] Plan OAuth2 token management and refresh strategy

### Phase 2: Core Client Implementation
- [ ] Implement `NotionClient.__init__()` with token/auth support
- [ ] Implement database queries: `query_database()`, `get_database()`, `create_database()`
- [ ] Implement page operations: `get_page()`, `create_page()`, `update_page()`, `archive_page()`
- [ ] Implement block operations: `get_block()`, `update_block()`, `append_block_children()`
- [ ] Implement user operations: `get_user()`, `list_users()`
- [ ] Implement search: `search()` endpoint
- [ ] Add request/response logging and error handling
- [ ] Implement retry logic with exponential backoff
- [ ] Add rate limiting compliance (Notion: 3 req/second)

### Phase 3: Data Models & Serialization
- [ ] Create model classes: Database, Page, Block, User, QueryResult
- [ ] Implement JSON serialization/deserialization
- [ ] Add type hints to all models (MyPy strict)
- [ ] Implement model validation

### Phase 4: Authentication & OAuth2
- [ ] Implement OAuth2 token request flow
- [ ] Implement token refresh mechanism
- [ ] Store tokens securely (use environment variables, not hardcoded)
- [ ] Add token expiration handling

### Phase 5: Unit Testing (>90% coverage required)
- [ ] Write unit tests for NotionClient (mocked API calls)
- [ ] Write tests for data model serialization
- [ ] Write tests for error handling and retries
- [ ] Write tests for OAuth2 token management
- [ ] Test edge cases: empty results, malformed responses, auth failures
- [ ] Run: `pytest app/backend/__tests__/unit/integrations/notion/ -v --cov=app/backend/src/integrations/notion`
- [ ] **REQUIREMENT:** Coverage >90% for tools. If below, add tests until passing.

### Phase 6: Live API Testing (using .env credentials)
- [ ] Setup .env with Notion integration token: `NOTION_API_KEY=xxx`
- [ ] Create test database in Notion workspace (or use dedicated test database)
- [ ] Implement live API tests in `test_notion_live.py`
- [ ] Test ALL endpoints:
  - Database queries (filter, sort, pagination)
  - Page CRUD operations
  - Block manipulation (append, update, delete)
  - User enumeration
  - Search functionality
- [ ] Run: `pytest app/backend/__tests__/integration/notion/ -v -s`
- [ ] **REQUIREMENT:** ALL tests MUST PASS. If any fail, debug and FIX ORIGINAL CODE before proceeding.
- [ ] Verify no API rate limits exceeded
- [ ] Verify all responses match expected structure

### Phase 7: Code Quality Assurance
- [ ] Run Ruff linter: `ruff check app/backend/src/integrations/notion/`
  - **REQUIREMENT:** Zero linting errors
- [ ] Run MyPy type checker: `mypy app/backend/src/integrations/notion/ --strict`
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
  - Common Notion API quirks discovered
  - Rate limit behaviors
  - Token refresh edge cases
  - Any workarounds implemented
- [ ] Keep documentation brief and actionable (next agent should learn, not read essay)
- [ ] Create `docs/api-endpoints/notion.md` with endpoint examples
- [ ] Document in `specs/integrations/notion_api.md`

### Phase 10: Commit & Push
- [ ] Verify git status: `git status`
  - **REQUIREMENT:** .env NOT in staging area
  - **REQUIREMENT:** Only production code committed (no test files unless they're fixtures)
- [ ] Add integration code: `git add app/backend/src/integrations/notion/`
- [ ] Add fixtures: `git add app/backend/__tests__/fixtures/notion_fixtures.py`
- [ ] Commit: `git commit -m "feat(notion): add complete Notion API integration"`
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
pytest app/backend/__tests__/unit/integrations/notion/ -v --cov=app/backend/src/integrations/notion
# Must show: coverage ≥ 90%

# 3. Live API tests (requires .env with NOTION_API_KEY)
pytest app/backend/__tests__/integration/notion/ -v -s
# Must show: all tests PASSED

# 4. Linting
ruff check app/backend/src/integrations/notion/
# Must show: 0 errors

# 5. Type checking
mypy app/backend/src/integrations/notion/ --strict
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
pytest app/backend/__tests__/unit/integrations/notion/ --cov --cov-report=term-missing

# Check linting status
ruff check app/backend/src/integrations/notion/ && echo "✓ Linting passed"

# Check type safety
mypy app/backend/src/integrations/notion/ --strict && echo "✓ Types passed"
```

---

## Known Patterns & Gotchas

**Notion API specifics:**
- Use `Bearer token` authentication in Authorization header
- All timestamps are ISO 8601 strings (parse to datetime)
- Database object IDs use hyphens in Notion UI but without hyphens in API (`6d05f2e8-e5ed-45d1-a65c-de7e5e71e50f` vs `6d05f2e8e5ed45d1a65cde7e5e71e50f`)
- Page properties can be complex nested structures
- Pagination: use `start_cursor` and `page_size` (max 100)
- Rate limits: 3 requests per second per integration

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

- Notion API documentation: https://developers.notion.com/reference/intro
- Store API token in .env as: `NOTION_API_KEY`
- Live API testing uses actual Notion workspace (test database)
- All errors during testing MUST be fixed in original code, not worked around
- Next agent will benefit from learnings documented in SELF-HEALING.md
