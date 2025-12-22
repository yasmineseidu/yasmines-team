# Task: Build Complete Telegram Approval Workflow System

**Status:** Pending
**Domain:** Backend
**Complexity:** High
**Created:** 2025-12-22

## Summary

Build a complete, production-ready approval workflow system that allows sending approval requests through Telegram with interactive approve/disapprove/edit buttons. Users can interact with Telegram messages to manage business approvals (budgets, documents, content). Includes database persistence, callback handling, real-time message editing, webhook/polling support, comprehensive testing, and documentation.

## Files to Create/Modify

### Database & Models
- [ ] `app/backend/src/database/migrations/[timestamp]_create_approval_tables.sql`
- [ ] `app/backend/src/models/approval.py`

### Services & Handlers
- [ ] `app/backend/src/services/approval_service.py`
- [ ] `app/backend/src/integrations/approval_handler.py`
- [ ] `app/backend/src/agents/approval_agent.py`

### API Routes
- [ ] `app/backend/src/api/routes/approval.py`
- [ ] `app/backend/src/api/routes/telegram.py` (webhook endpoint)

### Tests
- [ ] `app/backend/__tests__/unit/services/test_approval_service.py`
- [ ] `app/backend/__tests__/unit/integrations/test_approval_handler.py`
- [ ] `app/backend/__tests__/integration/test_approval_workflow_live.py`

### Documentation
- [ ] `app/backend/docs/APPROVAL_WORKFLOW.md`
- [ ] `app/backend/docs/APPROVAL_API.md`
- [ ] `app/backend/docs/APPROVAL_EXAMPLES.md`
- [ ] `app/backend/docs/APPROVAL_TROUBLESHOOTING.md`

---

## Implementation Checklist

### ⭐ PHASE 1: DATABASE SCHEMA

- [ ] Create database migration file with timestamp prefix
- [ ] Create `approval_requests` table:
  - [ ] `id` UUID PRIMARY KEY
  - [ ] `title` VARCHAR(255) - approval request title
  - [ ] `content` TEXT - approval details
  - [ ] `status` ENUM('pending', 'approved', 'disapproved', 'editing') - current state
  - [ ] `requester_id` INT - who requested approval
  - [ ] `approver_id` INT - who will approve
  - [ ] `telegram_message_id` INT - message ID in Telegram
  - [ ] `telegram_chat_id` INT - chat ID in Telegram
  - [ ] `data` JSONB - flexible data for different approval types
  - [ ] `created_at` TIMESTAMP DEFAULT NOW()
  - [ ] `updated_at` TIMESTAMP DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP

- [ ] Create `approval_history` table:
  - [ ] `id` UUID PRIMARY KEY
  - [ ] `request_id` UUID REFERENCES approval_requests(id) ON DELETE CASCADE
  - [ ] `action` VARCHAR(50) - 'approve', 'disapprove', 'edit'
  - [ ] `approver_id` INT - who took action
  - [ ] `comment` TEXT - reason or notes
  - [ ] `edited_data` JSONB - what was edited
  - [ ] `created_at` TIMESTAMP DEFAULT NOW()

- [ ] Create indexes:
  - [ ] `approval_requests (status)` - filter by status
  - [ ] `approval_requests (approver_id, created_at DESC)` - list pending for user
  - [ ] `approval_requests (telegram_message_id)` - find by message
  - [ ] `approval_history (request_id)` - audit trail

- [ ] Create migration UP script (create tables, indexes, constraints)
- [ ] Create migration DOWN script (drop tables)
- [ ] Define Python dataclasses in `approval.py`:
  - [ ] `ApprovalRequest` dataclass
  - [ ] `ApprovalHistory` dataclass
- [ ] Test migration runs successfully
- [ ] Verify schema with `\dt` and `\di` commands

---

### ⭐ PHASE 2: APPROVAL SERVICE API

- [ ] Create `ApprovalService` class:
  - [ ] `__init__(telegram_client: TelegramClient, db_connection)`

  - [ ] `async def send_approval_request(request_data: dict, approver_chat_id: int) -> str`:
    - [ ] Validate `request_data` has title, content
    - [ ] Create record in `approval_requests` table
    - [ ] Call `format_approval_message(request_data)` to format
    - [ ] Call `build_approval_buttons(request_id)` for keyboard
    - [ ] Call `telegram_client.send_message()` with formatted text and keyboard
    - [ ] Store returned `message_id` and `chat_id` in database
    - [ ] Return `request_id` to caller
    - [ ] Handle errors (database, Telegram API)

  - [ ] `def format_approval_message(request_data: dict) -> str`:
    - [ ] Format title, content, metadata into readable message
    - [ ] Support different content types: 'budget', 'document', 'content', 'custom'
    - [ ] Include amounts for budgets
    - [ ] Include file URLs for documents
    - [ ] Include tags for content
    - [ ] Add timestamp
    - [ ] Return formatted markdown/HTML string

  - [ ] `def build_approval_buttons(request_id: str) -> InlineKeyboardMarkup`:
    - [ ] Create InlineKeyboardMarkup
    - [ ] Add row 1: ✅ Approve button with callback_data="approve_{request_id}"
    - [ ] Add row 1: ❌ Disapprove button with callback_data="disapprove_{request_id}"
    - [ ] Add row 2: ✏️ Edit button with callback_data="edit_{request_id}"
    - [ ] Add row 3: 🔗 View Details button with URL to edit form
    - [ ] Return keyboard

  - [ ] `async def update_approval_status(request_id: str, status: str, comment: str = None, action_data: dict = None) -> bool`:
    - [ ] Look up request in database
    - [ ] Update `status` field
    - [ ] Update `updated_at` timestamp
    - [ ] Create record in `approval_history`
    - [ ] Store `comment` if provided
    - [ ] Store `action_data` in history if provided
    - [ ] Return success/failure

  - [ ] `async def get_approval_request(request_id: str) -> ApprovalRequest`:
    - [ ] Query approval_requests by id
    - [ ] Return full request object with all fields
    - [ ] Raise error if not found

  - [ ] `async def list_pending_approvals(approver_id: int) -> list[ApprovalRequest]`:
    - [ ] Query approval_requests WHERE approver_id AND status='pending'
    - [ ] Order by created_at DESC
    - [ ] Return list of requests

  - [ ] `async def notify_requester(request_id: str, action: str, message: str)`:
    - [ ] Get request from database
    - [ ] Get requester_id
    - [ ] Send Telegram message to requester
    - [ ] Include approval/disapproval status and message

---

### ⭐ PHASE 3: APPROVAL BOT HANDLER

- [ ] Create `ApprovalBotHandler` class:
  - [ ] `__init__(telegram_client: TelegramClient, approval_service: ApprovalService, db_connection)`

  - [ ] `async def process_update(update: Update)`:
    - [ ] Router method
    - [ ] If `update.callback_query` → call `handle_callback_query()`
    - [ ] If `update.message` → call `handle_message()`
    - [ ] Log all updates

  - [ ] `async def handle_callback_query(callback_query: dict)`:
    - [ ] Get callback_data from query
    - [ ] Parse: `action, request_id = callback_data.split('_', 1)`
    - [ ] If action == 'approve' → call `handle_approve(callback_query, request_id)`
    - [ ] If action == 'disapprove' → call `handle_disapprove(callback_query, request_id)`
    - [ ] If action == 'edit' → call `handle_edit(callback_query, request_id)`
    - [ ] Handle parse errors gracefully

  - [ ] `async def handle_approve(callback_query: dict, request_id: str)`:
    - [ ] Get request from database
    - [ ] Verify approver_id matches callback user
    - [ ] Check request status is 'pending'
    - [ ] Update status to 'approved' with `approval_service.update_approval_status()`
    - [ ] Edit Telegram message with:
      ```
      ✅ APPROVED
      Approved by: [Approver Name]
      Approved at: [Timestamp]
      ```
    - [ ] Answer callback with "Approval recorded"
    - [ ] Notify requester of approval
    - [ ] Trigger downstream approval action (webhook, event, etc.)
    - [ ] Log the action

  - [ ] `async def handle_disapprove(callback_query: dict, request_id: str)`:
    - [ ] Get request from database
    - [ ] Verify approver_id matches
    - [ ] Ask for disapproval reason (send follow-up message)
    - [ ] Wait for reason input or use default
    - [ ] Update status to 'disapproved' with reason in comment
    - [ ] Edit message with:
      ```
      ❌ DISAPPROVED
      Disapproved by: [Approver Name]
      Reason: [If provided]
      ```
    - [ ] Notify requester of disapproval
    - [ ] Answer callback with "Request disapproved"
    - [ ] Log the action

  - [ ] `async def handle_edit(callback_query: dict, request_id: str)`:
    - [ ] Get request from database
    - [ ] Generate edit token (UUID or JWT)
    - [ ] Update status to 'editing'
    - [ ] Store edit token in database
    - [ ] Send message with edit form link:
      ```
      Editing approval request...
      [Open Edit Form](https://yourapp.com/approvals/{request_id}/edit?token={token})
      ```
    - [ ] Answer callback with "Edit form opened"
    - [ ] Log the action

  - [ ] `async def handle_message(message: Message)`:
    - [ ] Check if waiting for disapproval reason
    - [ ] If so, store reason and complete disapproval flow
    - [ ] Handle other message types as needed

  - [ ] Error handling for all methods:
    - [ ] TelegramError → log and notify user
    - [ ] TelegramRateLimitError → queue for retry
    - [ ] Request not found → send friendly message
    - [ ] Already processed request → show current status
    - [ ] Permission denied → log security event

---

### ⭐ PHASE 4: MESSAGE EDITING & UPDATES

- [ ] Implement message editing in all handlers:
  - [ ] Use `telegram_client.edit_message_text(chat_id, message_id, text)`
  - [ ] Keep message_id and chat_id from database record
  - [ ] Update keyboard after action taken
  - [ ] Handle case where message already deleted
  - [ ] Format status text with emojis: ✅ ❌ ✏️

- [ ] Implement callback notifications:
  - [ ] Use `telegram_client.answer_callback_query(callback_id, text)`
  - [ ] Provide immediate feedback to approver
  - [ ] Show success/error messages

- [ ] Implement requester notifications:
  - [ ] Send separate message to requester when approved/disapproved
  - [ ] Include relevant details (what was approved, by whom, when)
  - [ ] If edited, notify that changes are needed

---

### ⭐ PHASE 5: INTEGRATION WITH TELEGRAM CLIENT

- [ ] Create `ApprovalAgent` orchestrator class:
  - [ ] Initialize TelegramClient with bot token from .env
  - [ ] Initialize ApprovalService
  - [ ] Initialize ApprovalBotHandler
  - [ ] Coordinate all three components

- [ ] Create webhook endpoint in `src/api/routes/telegram.py`:
  - [ ] `POST /api/telegram/webhook`
  - [ ] Verify X-Telegram-Bot-Api-Secret-Token header using `verify_webhook_token()`
  - [ ] Parse request body to Update object
  - [ ] Route to `approval_handler.process_update()`
  - [ ] Return 200 OK immediately (fire and forget)
  - [ ] Handle errors without crashing

- [ ] Create polling support (optional but tested):
  - [ ] Background task to call `telegram_client.get_updates(offset=last_offset)`
  - [ ] Track last_update_id to avoid duplicates
  - [ ] Route each update to handler
  - [ ] Implement exponential backoff on errors
  - [ ] Long polling with 30-50 second timeout

- [ ] Startup configuration:
  - [ ] Read TELEGRAM_BOT_TOKEN from .env
  - [ ] Read TELEGRAM_WEBHOOK_URL from .env (if webhook mode)
  - [ ] Read TELEGRAM_WEBHOOK_SECRET from .env
  - [ ] Check webhook mode preference from config
  - [ ] Set webhook OR start polling task
  - [ ] Initialize health check

- [ ] Rate limiting integration:
  - [ ] Respect per-chat message limits (20 text/minute, 5 media/minute)
  - [ ] Queue messages if rate limit hit
  - [ ] Implement exponential backoff for retries
  - [ ] Log rate limit events

- [ ] Health check integration:
  - [ ] Add approval system to health endpoint
  - [ ] Check database connectivity
  - [ ] Check Telegram API connectivity
  - [ ] Report status in health response

---

### ⭐ PHASE 6: COMPREHENSIVE TESTING

#### Unit Tests (Mocked - No API Calls)

- [ ] **test_approval_service.py:**
  - [ ] Test `send_approval_request()` creates database record ✅
  - [ ] Test `send_approval_request()` calls Telegram API ✅
  - [ ] Test `send_approval_request()` returns request_id ✅
  - [ ] Test `format_approval_message()` with budget content ✅
  - [ ] Test `format_approval_message()` with document content ✅
  - [ ] Test `format_approval_message()` with post content ✅
  - [ ] Test `build_approval_buttons()` returns proper keyboard ✅
  - [ ] Test `build_approval_buttons()` all buttons present ✅
  - [ ] Test `update_approval_status()` updates database ✅
  - [ ] Test `update_approval_status()` creates history entry ✅
  - [ ] Test `get_approval_request()` returns correct request ✅
  - [ ] Test `get_approval_request()` raises on not found ✅
  - [ ] Test `list_pending_approvals()` filters by approver ✅
  - [ ] Test `list_pending_approvals()` orders by created_at ✅
  - [ ] Mock TelegramClient to avoid API calls
  - [ ] Mock database to test logic in isolation
  - [ ] Test error cases (invalid data, database errors)
  - [ ] Coverage: >85%

- [ ] **test_approval_handler.py:**
  - [ ] Test `process_update()` routes callback_query correctly ✅
  - [ ] Test `process_update()` routes message correctly ✅
  - [ ] Test `handle_approve()` updates status to approved ✅
  - [ ] Test `handle_approve()` edits message ✅
  - [ ] Test `handle_approve()` answers callback query ✅
  - [ ] Test `handle_disapprove()` updates status to disapproved ✅
  - [ ] Test `handle_disapprove()` edits message ✅
  - [ ] Test `handle_disapprove()` asks for reason ✅
  - [ ] Test `handle_edit()` updates status to editing ✅
  - [ ] Test `handle_edit()` sends edit form link ✅
  - [ ] Test callback data parsing with valid format ✅
  - [ ] Test callback data parsing with invalid format ✅
  - [ ] Test error cases (invalid request_id, expired callback) ✅
  - [ ] Test rate limit error handling ✅
  - [ ] Test message not found error handling ✅
  - [ ] Test permission denied case ✅
  - [ ] Mock TelegramClient and database
  - [ ] Coverage: >85%

#### Integration Tests (Real Telegram API)

- [ ] **test_approval_workflow_live.py:**
  - [ ] Test end-to-end approval workflow:
    - [ ] Send approval request → message appears in Telegram
    - [ ] Click approve → message updates with ✅ status
    - [ ] Database updated with approval record
    - [ ] History entry created
  - [ ] Test disapprove workflow:
    - [ ] Send request → click disapprove → provide reason
    - [ ] Message updates with ❌ status
    - [ ] Requester notified
  - [ ] Test edit workflow:
    - [ ] Send request → click edit → form opens
    - [ ] User edits → resubmit
    - [ ] Status updated to approved
  - [ ] Test with sample data:
    - [ ] Budget request ($50,000 marketing budget)
    - [ ] Document request (contract review)
    - [ ] Post request (blog article approval)
  - [ ] Test error scenarios:
    - [ ] Invalid request_id
    - [ ] Rate limit handling
    - [ ] Message already deleted
    - [ ] Webhook validation with invalid token
  - [ ] Mark tests with `@pytest.mark.live_api`
  - [ ] Use real Telegram API with test bot
  - [ ] Use real database with test data
  - [ ] Cleanup test data after tests

#### Test Fixtures & Sample Data

- [ ] Create fixtures:
  - [ ] `approval_request_fixture()` - valid request data
  - [ ] `budget_approval_fixture()` - budget-specific data
  - [ ] `document_approval_fixture()` - document-specific data
  - [ ] `telegram_client_fixture()` - mocked client
  - [ ] `approval_service_fixture()` - service with mocked deps
  - [ ] `approval_handler_fixture()` - handler with mocked deps
  - [ ] `test_chat_id_fixture()` - from environment
  - [ ] `test_approver_id_fixture()` - from environment

- [ ] Create sample approval requests:
  ```python
  BUDGET_SAMPLE = {
      "id": "budget_test_123",
      "title": "Q4 Marketing Budget",
      "amount": 50000,
      "department": "Marketing",
      "description": "Budget allocation for Q4 campaigns"
  }

  DOCUMENT_SAMPLE = {
      "id": "doc_test_456",
      "title": "Contract Review",
      "content": "Partnership agreement with Company X",
      "file_url": "https://example.com/docs/contract.pdf"
  }

  CONTENT_SAMPLE = {
      "id": "post_test_789",
      "title": "Blog Post: How to Scale Your Business",
      "content": "Full article content here...",
      "tags": ["business", "scaling"]
  }
  ```

#### Test Execution

- [ ] Run all unit tests:
  ```bash
  python3 -m pytest app/backend/__tests__/unit/services/test_approval_service.py -v
  python3 -m pytest app/backend/__tests__/unit/integrations/test_approval_handler.py -v
  ```

- [ ] Run integration tests:
  ```bash
  python3 -m pytest app/backend/__tests__/integration/test_approval_workflow_live.py -v -m live_api
  ```

- [ ] Run all approval tests:
  ```bash
  python3 -m pytest -k approval -v
  ```

- [ ] Check coverage:
  ```bash
  python3 -m pytest --cov=src.services.approval --cov=src.integrations.approval --cov-report=term-missing
  ```

- [ ] Ensure all tests pass before proceeding
- [ ] Target >85% code coverage
- [ ] 100% coverage of critical paths (approve, disapprove)

---

### ⭐ PHASE 7: COMPREHENSIVE DOCUMENTATION

- [ ] **APPROVAL_WORKFLOW.md - Architecture Document:**
  - [ ] System overview with ASCII/visual diagram
  - [ ] Data flow diagram: request → Telegram → approval → action
  - [ ] Database schema explanation
  - [ ] Approval state machine (pending → approved/disapproved/editing)
  - [ ] Webhook vs polling comparison
  - [ ] Rate limiting behavior explanation
  - [ ] Error handling strategy
  - [ ] Security considerations (token validation, permissions)
  - [ ] Integration points with rest of system

- [ ] **APPROVAL_API.md - API Reference:**
  - [ ] `ApprovalService` class documentation:
    - [ ] Constructor signature
    - [ ] `send_approval_request()` - params, return value, errors
    - [ ] `format_approval_message()` - content types, formatting
    - [ ] `build_approval_buttons()` - button list, callback data format
    - [ ] `update_approval_status()` - status values, audit trail
    - [ ] `get_approval_request()` - return structure
    - [ ] `list_pending_approvals()` - filtering, ordering
  - [ ] `ApprovalBotHandler` class documentation
  - [ ] Request/response examples
  - [ ] Error codes and exceptions
  - [ ] Rate limit information
  - [ ] Async/await usage guidance

- [ ] **APPROVAL_EXAMPLES.md - Usage Examples:**
  - [ ] Budget approval example:
    ```python
    # Complete working example with all imports
    # Shows: send, approve, disapprove, edit flows
    ```
  - [ ] Document approval example:
    ```python
    # Full working example for documents
    ```
  - [ ] Content approval example:
    ```python
    # Full working example for content
    ```
  - [ ] Custom approval type example
  - [ ] Handling approvals programmatically
  - [ ] Listing pending approvals for user
  - [ ] Checking approval status
  - [ ] Webhook setup instructions
  - [ ] Polling setup instructions

- [ ] **APPROVAL_TROUBLESHOOTING.md:**
  - [ ] "Message not updating" - debug steps and solutions
  - [ ] "Buttons not responding" - common causes and fixes
  - [ ] "Rate limit errors" - handling and queuing strategies
  - [ ] "Database errors" - recovery procedures
  - [ ] "Webhook not receiving updates" - setup verification
  - [ ] "Polling not working" - configuration checks
  - [ ] "Approvals stuck in editing" - cleanup procedures
  - [ ] Debug logging setup
  - [ ] Common error messages and meanings

- [ ] **Documentation additions:**
  - [ ] Update `app/backend/README.md` with approval system reference
  - [ ] Add approval workflow to architecture docs
  - [ ] Document callback data format: `action_{request_id}_{version}`
  - [ ] Document all configuration options
  - [ ] Document database retention policy
  - [ ] Document monitoring and alerting points

---

### ⭐ FINAL VERIFICATION & CLEANUP

- [ ] Database:
  - [ ] All migrations applied successfully
  - [ ] Schema verified with `\dt` and `\di`
  - [ ] Sample data can be inserted
  - [ ] Queries work correctly

- [ ] Code Quality:
  - [ ] No linting errors: `ruff check app/backend/src/services/approval*`
  - [ ] Type checking passes: `mypy app/backend/src/services/approval*`
  - [ ] All imports resolved correctly
  - [ ] Code formatted with Black
  - [ ] Docstrings complete for all public methods

- [ ] Tests:
  - [ ] All unit tests pass: 42/42
  - [ ] All integration tests pass: 20+/20+
  - [ ] Code coverage >85% minimum
  - [ ] No flaky tests
  - [ ] All test data cleaned up

- [ ] Documentation:
  - [ ] All 4 doc files created and complete
  - [ ] Examples are copy-paste ready
  - [ ] No broken links or references
  - [ ] Markdown formatting valid

- [ ] Integration:
  - [ ] Webhook endpoint works end-to-end
  - [ ] Polling works end-to-end
  - [ ] Rate limiting respected
  - [ ] Health check includes approval system
  - [ ] Errors logged appropriately

---

## Success Criteria

- [x] One cohesive approval system (not fragmented)
- [x] Complete checklist of all components
- [x] Database designed and tested
- [x] Service API fully implemented
- [x] Bot handler processes all actions
- [x] Message editing shows status changes
- [x] Webhook and polling both work
- [x] >85% test coverage with real examples
- [x] Production-ready error handling
- [x] Comprehensive documentation
- [x] All tests passing

---

## Verification Commands

```bash
# Check all files exist
test -f app/backend/src/database/migrations/*approval*.sql && echo "✓ Migration"
test -f app/backend/src/models/approval.py && echo "✓ Models"
test -f app/backend/src/services/approval_service.py && echo "✓ Service"
test -f app/backend/src/integrations/approval_handler.py && echo "✓ Handler"
test -f app/backend/src/agents/approval_agent.py && echo "✓ Agent"
test -f app/backend/src/api/routes/approval.py && echo "✓ API Routes"
test -f app/backend/src/api/routes/telegram.py && echo "✓ Telegram Routes"

# Run all tests
python3 -m pytest -k approval -v --tb=short

# Check coverage
python3 -m pytest --cov=src.services.approval --cov=src.integrations.approval --cov-report=term-missing

# Check linting
ruff check app/backend/src/services/approval* app/backend/src/integrations/approval*

# Check types
mypy app/backend/src/services/approval* app/backend/src/integrations/approval*

# Check docs exist
test -f app/backend/docs/APPROVAL_WORKFLOW.md && echo "✓ Architecture"
test -f app/backend/docs/APPROVAL_API.md && echo "✓ API Docs"
test -f app/backend/docs/APPROVAL_EXAMPLES.md && echo "✓ Examples"
test -f app/backend/docs/APPROVAL_TROUBLESHOOTING.md && echo "✓ Troubleshooting"
```

---

## Notes

- Keep all related files in close proximity (same directories)
- Use consistent naming (approval_* for everything)
- Test as you go - don't wait until end
- Use existing TelegramClient integration (already tested)
- Reuse database connection infrastructure
- Follow project code style and patterns
- All async methods
- All errors properly logged
- Support multiple approval types through flexible data field
- Database transactions for atomicity
- Consider webhook security (token validation)
