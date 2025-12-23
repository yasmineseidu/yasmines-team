# Task: Build Complete Google Calendar Integration Client

**Status:** Pending
**Domain:** Backend
**Source:** Direct input - Comprehensive Google Calendar implementation
**Created:** 2025-12-22

## Summary

Build a fully-functional, well-tested Google Calendar API client for the Claude Agent SDK. This task encompasses the complete integration lifecycle including client development, credential management, comprehensive testing, and verification with real environment variables.

---

## Part 1: Credential Setup & Configuration

### Files to Create/Modify

- [ ] `app/backend/config/credentials/google-service-account.json` - Service account credentials file (already configured in .env)
- [ ] `app/backend/src/integrations/google_calendar/__init__.py` - Package initialization
- [ ] `app/backend/src/integrations/google_calendar/exceptions.py` - Custom exceptions
- [ ] `app/backend/src/integrations/google_calendar/models.py` - Data models for Calendar entities

### Implementation Checklist

#### Load and Validate Credentials
- [ ] Read `google-service-account.json` from the path specified in `.env` variable `GOOGLE_CALENDAR_CREDENTIALS_JSON`
- [ ] Validate JSON structure contains required fields:
  - [ ] `type` = "service_account"
  - [ ] `project_id`
  - [ ] `private_key_id`
  - [ ] `private_key`
  - [ ] `client_email`
  - [ ] `client_id`
  - [ ] `auth_uri`
  - [ ] `token_uri`
  - [ ] `auth_provider_x509_cert_url`
  - [ ] `client_x509_cert_url`
- [ ] Handle missing or invalid credentials gracefully with meaningful error messages
- [ ] Log credential loading status (without exposing sensitive data)

#### Environment Variable Integration
- [ ] Load `GOOGLE_CALENDAR_CREDENTIALS_JSON` from `.env`
- [ ] Support both absolute and relative paths
- [ ] Verify file exists at startup
- [ ] Handle path resolution correctly on different operating systems

#### Custom Exceptions
- [ ] `GoogleCalendarAuthError` - Authentication/authorization failures
- [ ] `GoogleCalendarAPIError` - API call failures
- [ ] `GoogleCalendarConfigError` - Configuration/credential loading issues
- [ ] `GoogleCalendarNotFoundError` - Resource not found (event, calendar, etc.)
- [ ] `GoogleCalendarValidationError` - Input validation failures

#### Data Models
- [ ] `CalendarEvent` model with fields:
  - [ ] `id`: str
  - [ ] `summary`: str
  - [ ] `description`: Optional[str]
  - [ ] `start`: datetime
  - [ ] `end`: datetime
  - [ ] `location`: Optional[str]
  - [ ] `attendees`: List[str]
  - [ ] `status`: str (confirmed, tentative, cancelled)
  - [ ] `organizer`: Optional[str]
  - [ ] `created`: datetime
  - [ ] `updated`: datetime
- [ ] `Calendar` model with fields:
  - [ ] `id`: str
  - [ ] `summary`: str
  - [ ] `description`: Optional[str]
  - [ ] `timezone`: str
  - [ ] `primary`: bool
  - [ ] `accessible`: bool
- [ ] `CalendarList` model with fields:
  - [ ] `id`: str
  - [ ] `summary`: str
  - [ ] `accessRole`: str (freeBusyReader, reader, writer, owner)
  - [ ] `primary`: bool
- [ ] Ensure all models have proper type hints and validation

---

## Part 2: Google Calendar Client Implementation

### Files to Create/Modify

- [ ] `app/backend/src/integrations/google_calendar/client.py` - Main Google Calendar client

### Implementation Checklist

#### Client Class Initialization
- [ ] Create `GoogleCalendarClient` class
- [ ] Accept credentials JSON path as parameter (or load from environment)
- [ ] Initialize Google auth using `google.oauth2.service_account.Credentials`
- [ ] Build service using `googleapiclient.discovery.build('calendar', 'v3', credentials=...)`
- [ ] Handle initialization errors with proper exception raising
- [ ] Implement `__init__` with proper type hints and docstrings

#### Core Calendar Operations

##### List Calendars
- [ ] Method `list_calendars()` - Get all accessible calendars
- [ ] Return: `List[Calendar]`
- [ ] Handle pagination for large calendar lists
- [ ] Filter by accessibility (readable, writable, owned)
- [ ] Proper error handling and retry logic

##### Get Calendar
- [ ] Method `get_calendar(calendar_id: str)` - Get specific calendar details
- [ ] Return: `Calendar`
- [ ] Handle "notFound" errors (raise `GoogleCalendarNotFoundError`)
- [ ] Validate calendar_id parameter

##### List Events
- [ ] Method `list_events(calendar_id: str, time_min: Optional[datetime] = None, time_max: Optional[datetime] = None, limit: int = 100)`
- [ ] Return: `List[CalendarEvent]`
- [ ] Support filtering by date range
- [ ] Handle pagination
- [ ] Support `search_terms` parameter for text search
- [ ] Support ordering (ascending/descending by startTime or updated)
- [ ] Filter out cancelled events by default (configurable)

##### Get Event
- [ ] Method `get_event(calendar_id: str, event_id: str)` - Get specific event details
- [ ] Return: `CalendarEvent`
- [ ] Handle "notFound" errors appropriately
- [ ] Include all event details (attendees, creator, etc.)

##### Create Event
- [ ] Method `create_event(calendar_id: str, event: CalendarEvent)` - Create new event
- [ ] Accept event details: title, description, start time, end time, location, attendees, etc.
- [ ] Return: Created `CalendarEvent` with generated ID
- [ ] Support timezone handling
- [ ] Support sending invitations to attendees
- [ ] Validate event data (e.g., start time before end time)
- [ ] Handle conflicts gracefully

##### Update Event
- [ ] Method `update_event(calendar_id: str, event_id: str, event: CalendarEvent)` - Modify existing event
- [ ] Update only provided fields
- [ ] Return: Updated `CalendarEvent`
- [ ] Handle version conflicts
- [ ] Support notifying attendees of changes

##### Delete Event
- [ ] Method `delete_event(calendar_id: str, event_id: str)` - Remove event
- [ ] Support `sendNotifications` parameter
- [ ] Handle "notFound" errors
- [ ] Return confirmation

##### Quick Add Event
- [ ] Method `quick_add_event(calendar_id: str, text: str)` - Create event from natural language
- [ ] Parse text like "Meeting tomorrow at 2pm"
- [ ] Return: Created `CalendarEvent`
- [ ] Handle parsing errors gracefully

#### Rate Limiting & Retry Logic
- [ ] Implement exponential backoff for rate-limited requests (429)
- [ ] Maximum 3 retries with jitter
- [ ] Wait times: 1s, 2s, 4s (with randomization)
- [ ] Proper logging of retries
- [ ] Implement circuit breaker pattern for repeated failures

#### Session Management
- [ ] Store service instance (reuse across calls)
- [ ] Implement connection pooling
- [ ] Handle token refresh automatically
- [ ] Close connections properly

---

## Part 3: SDK Integration & Tools

### Files to Create/Modify

- [ ] `app/backend/src/integrations/google_calendar/tools.py` - SDK tools for agents

### Implementation Checklist

#### Tool: List Calendars
- [ ] Tool name: `list_calendars`
- [ ] Description: "List all accessible Google Calendars"
- [ ] Return available calendars with IDs and summaries
- [ ] No required parameters
- [ ] Handle and report errors clearly

#### Tool: Get Calendar Details
- [ ] Tool name: `get_calendar`
- [ ] Description: "Get detailed information about a specific calendar"
- [ ] Parameter: `calendar_id` (string, required)
- [ ] Return: Calendar details including timezone, accessibility, etc.
- [ ] Validate calendar_id before API call

#### Tool: List Events
- [ ] Tool name: `list_events`
- [ ] Description: "List events from a calendar with optional date range filtering"
- [ ] Parameters:
  - [ ] `calendar_id` (required)
  - [ ] `start_date` (optional, ISO 8601 format)
  - [ ] `end_date` (optional, ISO 8601 format)
  - [ ] `search_query` (optional, text search)
  - [ ] `max_results` (optional, default 10, max 250)
- [ ] Return: List of events with key details
- [ ] Format dates consistently

#### Tool: Get Event Details
- [ ] Tool name: `get_event`
- [ ] Description: "Get detailed information about a specific event"
- [ ] Parameters:
  - [ ] `calendar_id` (required)
  - [ ] `event_id` (required)
- [ ] Return: Complete event information including attendees, description, etc.
- [ ] Handle 404s gracefully

#### Tool: Create Event
- [ ] Tool name: `create_event`
- [ ] Description: "Create a new event in a calendar"
- [ ] Parameters:
  - [ ] `calendar_id` (required)
  - [ ] `title` (required, min 1 char, max 255)
  - [ ] `start_time` (required, ISO 8601 with timezone)
  - [ ] `end_time` (required, must be after start_time)
  - [ ] `description` (optional)
  - [ ] `location` (optional)
  - [ ] `attendees` (optional, list of email addresses)
  - [ ] `send_notifications` (optional, bool, default true)
- [ ] Validate all inputs before creating
- [ ] Return: Created event with full details
- [ ] Log creation with event ID

#### Tool: Update Event
- [ ] Tool name: `update_event`
- [ ] Description: "Update an existing event in a calendar"
- [ ] Parameters:
  - [ ] `calendar_id` (required)
  - [ ] `event_id` (required)
  - [ ] `title` (optional)
  - [ ] `description` (optional)
  - [ ] `start_time` (optional)
  - [ ] `end_time` (optional)
  - [ ] `location` (optional)
  - [ ] `send_notifications` (optional)
- [ ] Support partial updates
- [ ] Validate time constraints (start before end)
- [ ] Return: Updated event details

#### Tool: Delete Event
- [ ] Tool name: `delete_event`
- [ ] Description: "Delete an event from a calendar"
- [ ] Parameters:
  - [ ] `calendar_id` (required)
  - [ ] `event_id` (required)
  - [ ] `send_notifications` (optional, default true)
- [ ] Confirm deletion successful
- [ ] Return: Confirmation message with event ID

#### Tool: Quick Add Event
- [ ] Tool name: `quick_add_event`
- [ ] Description: "Create an event using natural language (e.g., 'Meeting tomorrow at 3pm')"
- [ ] Parameter: `calendar_id` (required), `text` (required)
- [ ] Return: Created event details
- [ ] Handle parse failures with helpful error messages

#### Tool Registration
- [ ] Register all tools with proper metadata
- [ ] Add clear descriptions for each tool
- [ ] Document parameters with types and constraints
- [ ] Include usage examples in docstrings

---

## Part 4: Unit Tests

### Files to Create/Modify

- [ ] `app/backend/__tests__/unit/integrations/google_calendar/__init__.py`
- [ ] `app/backend/__tests__/unit/integrations/google_calendar/test_client.py` - Client unit tests
- [ ] `app/backend/__tests__/unit/integrations/google_calendar/test_models.py` - Model tests
- [ ] `app/backend/__tests__/unit/integrations/google_calendar/test_exceptions.py` - Exception tests

### Implementation Checklist

#### Test Fixtures
- [ ] Create mock service account credentials JSON
- [ ] Create mock credentials object
- [ ] Create mock Google API service
- [ ] Mock CalendarEvent data fixtures
- [ ] Mock Calendar data fixtures
- [ ] Mock error responses (404, 401, 429, etc.)

#### Client Initialization Tests
- [ ] Test successful initialization with valid credentials
- [ ] Test initialization with missing credentials file
- [ ] Test initialization with invalid JSON in credentials file
- [ ] Test initialization with missing required fields in JSON
- [ ] Test that service is created correctly
- [ ] Test environment variable loading
- [ ] Test path resolution (absolute and relative paths)

#### Authentication Tests
- [ ] Test credentials are properly loaded from JSON
- [ ] Test credentials validation
- [ ] Test that API calls use correct authentication
- [ ] Test handling of expired credentials (token refresh)
- [ ] Test `GoogleCalendarAuthError` is raised on auth failures

#### List Calendars Tests
- [ ] Test successful list_calendars() call
- [ ] Test pagination handling (mock >10 calendars)
- [ ] Test empty calendar list
- [ ] Test API errors are properly caught and raised
- [ ] Test correct transformation to Calendar models
- [ ] Test filtering by accessibility

#### Get Calendar Tests
- [ ] Test successful get_calendar() with valid ID
- [ ] Test get_calendar() with non-existent calendar (404)
- [ ] Test get_calendar() with invalid ID format
- [ ] Test `GoogleCalendarNotFoundError` is raised correctly
- [ ] Test timezone information is included

#### List Events Tests
- [ ] Test successful list_events() call
- [ ] Test list_events() with date range filter
- [ ] Test list_events() with search query
- [ ] Test pagination (>100 events)
- [ ] Test max_results parameter
- [ ] Test filtering out cancelled events
- [ ] Test empty event list
- [ ] Test API errors

#### Create Event Tests
- [ ] Test successful event creation with required fields
- [ ] Test event creation with all optional fields
- [ ] Test validation: title required
- [ ] Test validation: start_time < end_time
- [ ] Test validation: title length constraints
- [ ] Test attendee handling
- [ ] Test timezone handling
- [ ] Test error handling for API failures
- [ ] Test returned event includes generated ID

#### Update Event Tests
- [ ] Test successful partial update
- [ ] Test update with only title changed
- [ ] Test update with time change
- [ ] Test validation: new start_time < end_time
- [ ] Test error on non-existent event
- [ ] Test notification sending parameter
- [ ] Test returned updated event data

#### Delete Event Tests
- [ ] Test successful deletion
- [ ] Test deletion of non-existent event (404)
- [ ] Test notification parameter
- [ ] Test confirmation message

#### Quick Add Tests
- [ ] Test "Meeting tomorrow at 3pm"
- [ ] Test "Lunch with John next Tuesday"
- [ ] Test "All-day event next Friday"
- [ ] Test error on unparseable text
- [ ] Test with custom timezone

#### Rate Limiting & Retry Tests
- [ ] Test exponential backoff on 429 (rate limit)
- [ ] Test retry count increases
- [ ] Test jitter is applied to wait times
- [ ] Test max retries (should fail after 3)
- [ ] Test logging of retries
- [ ] Test circuit breaker after repeated failures

#### Exception Tests
- [ ] Test all custom exceptions can be raised and caught
- [ ] Test exception messages are helpful
- [ ] Test exception inheritance hierarchy

#### Models Tests
- [ ] Test CalendarEvent model creation with required fields
- [ ] Test CalendarEvent model with all fields
- [ ] Test model validation (invalid dates, etc.)
- [ ] Test model serialization to dict
- [ ] Test model deserialization from API response
- [ ] Test Calendar model
- [ ] Test CalendarList model

#### Coverage Requirements
- [ ] Achieve >90% code coverage in `client.py`
- [ ] Achieve >90% code coverage in `models.py`
- [ ] Achieve >85% code coverage in `tools.py`
- [ ] Run: `pytest app/backend/__tests__/unit/integrations/google_calendar/ -v --cov=app.backend.src.integrations.google_calendar --cov-report=html`

---

## Part 5: Integration Tests

### Files to Create/Modify

- [ ] `app/backend/__tests__/integration/google_calendar/__init__.py`
- [ ] `app/backend/__tests__/integration/google_calendar/conftest.py` - Shared fixtures
- [ ] `app/backend/__tests__/integration/google_calendar/test_live_api.py` - Tests against real API with .env credentials

### Implementation Checklist

#### Environment Setup
- [ ] Verify `.env` file exists with `GOOGLE_CALENDAR_CREDENTIALS_JSON` set
- [ ] Verify credentials file exists at specified path
- [ ] Verify credentials are valid service account credentials
- [ ] Create test fixtures that use real .env values

#### conftest.py Setup
- [ ] Load credentials from `.env` path
- [ ] Initialize real GoogleCalendarClient with loaded credentials
- [ ] Provide calendar_id fixture (primary or specified test calendar)
- [ ] Add pytest markers for integration tests
- [ ] Add skip decorators for when credentials are missing

#### Live API Tests (Real Service Account)
- [ ] Test authentication succeeds with service account credentials
- [ ] Test list_calendars() returns actual calendars
- [ ] Test get_calendar() returns correct calendar details
- [ ] Test list_events() returns events (or empty list if no events)
- [ ] Test create_event() creates event successfully
  - [ ] Verify event appears in list_events()
  - [ ] Verify event details match what was sent
  - [ ] Clean up: delete the created event afterward
- [ ] Test update_event() modifies event successfully
  - [ ] Verify updated fields change
  - [ ] Verify other fields unchanged
  - [ ] Clean up: delete the modified event
- [ ] Test delete_event() removes event successfully
  - [ ] Verify event no longer appears in list
- [ ] Test quick_add_event() creates event from text
  - [ ] Verify event is created with parsed details
  - [ ] Clean up: delete created event
- [ ] Test error handling with real API responses
  - [ ] Try to delete non-existent event (404)
  - [ ] Try to access invalid calendar ID (403)

#### Test Organization
- [ ] Use pytest fixtures for setup/teardown
- [ ] Mark tests with `@pytest.mark.integration`
- [ ] Use skip if credentials not available: `@pytest.mark.skipif(not has_credentials, reason="Google Calendar credentials not configured")`
- [ ] Clean up all created events at end of each test
- [ ] Add timeouts to prevent hanging tests
- [ ] Log API calls for debugging

#### .env Credential Testing
- [ ] Test with `.env` file values directly
- [ ] Test path resolution from `.env` relative paths
- [ ] Test error when .env credentials missing
- [ ] Test error when credentials JSON is invalid
- [ ] Document which Google account/workspace the service account has access to

---

## Part 6: Comprehensive Testing Verification

### Files to Check/Create

- [ ] `app/backend/__tests__/integration/google_calendar/TEST_REPORT_google_calendar.md` - Test results documentation

### Testing Checklist

#### Unit Test Execution
- [ ] Run unit tests: `pytest app/backend/__tests__/unit/integrations/google_calendar/ -v`
- [ ] All unit tests pass ✓
- [ ] Code coverage >90% for critical paths
- [ ] No warnings or deprecations

#### Integration Test Execution
- [ ] Verify `.env` credentials exist and are valid
- [ ] Run integration tests: `pytest app/backend/__tests__/integration/google_calendar/ -v -s`
- [ ] All integration tests pass ✓
- [ ] All real API calls succeed
- [ ] No events left behind in calendar after tests

#### Coverage Report
- [ ] Generate coverage report: `pytest app/backend/__tests__/unit/integrations/google_calendar/ --cov=app.backend.src.integrations.google_calendar --cov-report=html --cov-report=term-missing`
- [ ] Review `htmlcov/index.html` for coverage details
- [ ] Coverage >90% overall
- [ ] Identify any uncovered lines and add tests or document why untestable

#### Integration with Existing Code
- [ ] Add import in `app/backend/src/integrations/__init__.py`
- [ ] Ensure no conflicts with existing Google integrations (gmail, drive, docs, etc.)
- [ ] Verify models follow same patterns as existing integrations
- [ ] Check exception handling matches project standards

#### Tools Registration
- [ ] Verify all 9 tools are registered
- [ ] Test each tool via Claude Agent SDK (if applicable)
- [ ] Verify tool parameters are correct
- [ ] Verify tool responses are well-formatted

#### Error Scenarios
- [ ] Test with invalid .env path
- [ ] Test with corrupted credentials JSON
- [ ] Test with revoked/expired service account
- [ ] Test with missing API permissions
- [ ] Test with network failures
- [ ] Test with malformed API responses
- [ ] All errors handled gracefully with clear messages

#### Performance Testing
- [ ] Test list_calendars() with 50+ calendars
- [ ] Test list_events() with 1000+ events
- [ ] Test pagination works correctly
- [ ] Test rate limiting/retry logic with concurrent calls
- [ ] Measure response times for common operations

---

## Part 7: Documentation & Final Steps

### Files to Create/Modify

- [ ] `app/backend/src/integrations/google_calendar/README.md` - Integration documentation
- [ ] `app/backend/__tests__/integration/google_calendar/README.md` - Testing guide

### Documentation Checklist

#### README.md Content
- [ ] Overview of Google Calendar integration
- [ ] Installation and setup instructions
- [ ] Credential setup guide:
  - [ ] How to create service account
  - [ ] How to download credentials JSON
  - [ ] How to configure .env
- [ ] Quick start example code
- [ ] Available methods/tools
- [ ] Error handling guide
- [ ] Rate limiting information
- [ ] Links to Google Calendar API docs

#### Testing Guide
- [ ] How to run unit tests
- [ ] How to run integration tests
- [ ] How to setup credentials for integration testing
- [ ] Troubleshooting common issues
- [ ] Coverage requirements and how to check

#### Code Quality Checks
- [ ] Run ruff linter: `ruff check app/backend/src/integrations/google_calendar/`
- [ ] Run mypy: `mypy app/backend/src/integrations/google_calendar/ --strict`
- [ ] All lint errors resolved
- [ ] All type hints properly set
- [ ] No unused imports or variables

#### Final Verification
- [ ] All tests passing (unit + integration)
- [ ] Coverage >90% for client code
- [ ] Code quality checks passing
- [ ] Documentation complete
- [ ] No broken imports or circular dependencies

---

## Verification

To verify this task is 100% complete and functioning:

```bash
# 1. Run unit tests
pytest app/backend/__tests__/unit/integrations/google_calendar/ -v --cov=app.backend.src.integrations.google_calendar --cov-report=term-missing

# 2. Run integration tests (requires .env credentials)
pytest app/backend/__tests__/integration/google_calendar/ -v -s

# 3. Check code quality
ruff check app/backend/src/integrations/google_calendar/
mypy app/backend/src/integrations/google_calendar/ --strict

# 4. Verify imports
python -c "from app.backend.src.integrations.google_calendar import GoogleCalendarClient"

# 5. Check all tools are accessible
python -c "from app.backend.src.integrations.google_calendar.tools import *"

# 6. Validate credentials loading
GOOGLE_CALENDAR_CREDENTIALS_JSON=app/backend/config/credentials/google-service-account.json python -c "
from app.backend.src.integrations.google_calendar import GoogleCalendarClient
client = GoogleCalendarClient()
calendars = client.list_calendars()
print(f'✓ Successfully connected to {len(calendars)} calendars')
"
```

### Success Criteria
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage >90%
- [ ] Linting checks pass (ruff, mypy)
- [ ] Credentials load from .env successfully
- [ ] Can authenticate to Google Calendar API
- [ ] Can perform all CRUD operations
- [ ] Error handling works correctly
- [ ] Rate limiting and retries work
- [ ] All 9 SDK tools function correctly
- [ ] Documentation is complete and accurate
- [ ] No console warnings or errors

---

## Notes

- This is a **comprehensive, production-ready** integration requiring ~15-20 hours of development
- Test-driven development recommended: write tests first, then implementation
- The service account JSON must have Calendar API permissions enabled
- Coordinate with existing Gmail, Drive, and Docs integrations for consistency
- Follow the patterns established in those integrations for models, exceptions, and tools
- Rate limiting: Google Calendar API allows 1000 requests per 100 seconds per user
- Token refresh is automatic with service account credentials (no manual refresh needed)
- All code must follow project linting standards (ruff, mypy strict mode)
- Minimum coverage: >90% for tools, >85% for full integration code
