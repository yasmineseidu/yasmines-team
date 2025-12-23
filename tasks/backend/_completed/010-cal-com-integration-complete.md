# Task: Build Complete Cal.com Integration Client

**Status:** Pending
**Domain:** Backend
**Source:** Direct input - Comprehensive Cal.com implementation
**Created:** 2025-12-23

## Summary

Build a fully-functional, well-tested Cal.com API client for the Claude Agent SDK. This task encompasses the complete integration lifecycle including client development, credential management, comprehensive testing with live APIs, and verification with real environment variables from `.env` in project root.

---

## Part 1: Credential Setup & Configuration

### Files to Create/Modify

- [ ] `app/backend/src/integrations/cal_com/__init__.py` - Package initialization
- [ ] `app/backend/src/integrations/cal_com/exceptions.py` - Custom exceptions
- [ ] `app/backend/src/integrations/cal_com/models.py` - Data models for Cal.com entities

### Implementation Checklist

#### Load and Validate Credentials

- [ ] Read `CAL_COM_API_KEY` from `.env` file in project root
- [ ] Support multiple API key formats (bearer token, raw key)
- [ ] Validate API key is not empty and has minimum length
- [ ] Store base URL from `CAL_COM_BASE_URL` (default: `https://api.cal.com/v1`)
- [ ] Load user/org context from `CAL_COM_USER_ID` or `CAL_COM_ORG_ID` (optional)
- [ ] Handle missing credentials gracefully with meaningful error messages
- [ ] Log credential loading status (without exposing sensitive data)

#### Environment Variable Integration

- [ ] Load `CAL_COM_API_KEY` from `.env` in project root
- [ ] Load `CAL_COM_BASE_URL` from `.env` (optional, default provided)
- [ ] Load `CAL_COM_USER_ID` from `.env` (optional)
- [ ] Load `CAL_COM_ORG_ID` from `.env` (optional)
- [ ] Support both absolute and relative paths for .env
- [ ] Verify credentials exist at startup
- [ ] Handle environment variable resolution correctly

#### Custom Exceptions

- [ ] `CalComAuthError` - Authentication/authorization failures
- [ ] `CalComAPIError` - API call failures
- [ ] `CalComConfigError` - Configuration/credential loading issues
- [ ] `CalComNotFoundError` - Resource not found (event, user, team, etc.)
- [ ] `CalComValidationError` - Input validation failures
- [ ] `CalComRateLimitError` - Rate limiting (429) errors

#### Data Models

- [ ] `CalComEvent` model with fields:
  - [ ] `id`: str
  - [ ] `title`: str
  - [ ] `description`: Optional[str]
  - [ ] `start_time`: datetime
  - [ ] `end_time`: datetime
  - [ ] `location`: Optional[str]
  - [ ] `organizer_id`: str
  - [ ] `attendees`: List[str]
  - [ ] `event_type_id`: Optional[str]
  - [ ] `calendar_id`: Optional[str]
  - [ ] `status`: str (confirmed, tentative, cancelled)
  - [ ] `created_at`: datetime
  - [ ] `updated_at`: datetime
- [ ] `EventType` model with fields:
  - [ ] `id`: str
  - [ ] `title`: str
  - [ ] `slug`: str
  - [ ] `description`: Optional[str]
  - [ ] `length`: int (duration in minutes)
  - [ ] `owner_id`: str
  - [ ] `is_active`: bool
  - [ ] `scheduling_type`: str (collective, round_robin, etc.)
- [ ] `User` model with fields:
  - [ ] `id`: str
  - [ ] `email`: str
  - [ ] `name`: str
  - [ ] `username`: str
  - [ ] `timezone`: str
  - [ ] `locale`: Optional[str]
  - [ ] `created_at`: datetime
- [ ] `Team` model with fields:
  - [ ] `id`: str
  - [ ] `name`: str
  - [ ] `slug`: str
  - [ ] `logo`: Optional[str]
  - [ ] `bio`: Optional[str]
  - [ ] `members`: List[str]
- [ ] `Availability` model with fields:
  - [ ] `user_id`: str
  - [ ] `start_time`: datetime
  - [ ] `end_time`: datetime
  - [ ] `is_available`: bool
- [ ] `BookingConfirmation` model with fields:
  - [ ] `event_id`: str
  - [ ] `booking_id`: str
  - [ ] `confirmed_at`: datetime
  - [ ] `confirmation_url`: Optional[str]
- [ ] Ensure all models have proper type hints and validation

---

## Part 2: Cal.com Client Implementation

### Files to Create/Modify

- [ ] `app/backend/src/integrations/cal_com/client.py` - Main Cal.com client

### Implementation Checklist

#### Client Class Initialization

- [ ] Create `CalComClient` class
- [ ] Accept API key as parameter or load from environment
- [ ] Initialize HTTP client with base URL and headers (Authorization: Bearer {api_key})
- [ ] Set default timeout (30 seconds)
- [ ] Implement session pooling for connection reuse
- [ ] Handle initialization errors with proper exception raising
- [ ] Implement `__init__` with proper type hints and docstrings

#### Core Cal.com Operations

##### Get User Profile

- [ ] Method `get_user()` - Get authenticated user details
- [ ] Return: `User`
- [ ] Handle 401 errors (invalid auth)
- [ ] Cache user info locally

##### List Event Types

- [ ] Method `list_event_types(owner_id: Optional[str] = None, team_id: Optional[str] = None)` - Get available event types
- [ ] Return: `List[EventType]`
- [ ] Support filtering by owner (user) or team
- [ ] Handle pagination
- [ ] Include all event type details (length, description, etc.)

##### Get Event Type

- [ ] Method `get_event_type(event_type_id: str)` - Get specific event type details
- [ ] Return: `EventType`
- [ ] Include scheduling configuration
- [ ] Handle "notFound" errors (raise `CalComNotFoundError`)

##### Create Event Type

- [ ] Method `create_event_type(event_type: EventType)` - Create new event type
- [ ] Accept: title, slug, length, description, scheduling_type, etc.
- [ ] Return: Created `EventType` with generated ID
- [ ] Validate slug uniqueness
- [ ] Set owner to authenticated user

##### List Availability

- [ ] Method `list_availability(user_id: str, date_range_start: datetime, date_range_end: datetime)` - Get user availability slots
- [ ] Return: `List[Availability]`
- [ ] Handle timezone conversions
- [ ] Support date range filtering

##### List Bookings/Events

- [ ] Method `list_bookings(limit: int = 100, skip: int = 0, filters: Optional[dict] = None)` - Get all bookings/events
- [ ] Return: `List[CalComEvent]`
- [ ] Support pagination
- [ ] Support filtering by status, date range, event type
- [ ] Include all event details

##### Get Booking/Event

- [ ] Method `get_booking(booking_id: str)` - Get specific booking details
- [ ] Return: `CalComEvent`
- [ ] Include attendee information
- [ ] Handle "notFound" errors

##### Create Booking

- [ ] Method `create_booking(event: CalComEvent)` - Create new booking
- [ ] Accept: event_type_id, start_time, end_time, attendee info, etc.
- [ ] Return: Created `CalComEvent` with booking ID
- [ ] Validate availability
- [ ] Support sending confirmation emails
- [ ] Generate booking confirmation object

##### Reschedule Event

- [ ] Method `reschedule_event(booking_id: str, new_start: datetime, new_end: datetime)` - Modify event timing
- [ ] Return: Updated `CalComEvent`
- [ ] Validate new time doesn't conflict
- [ ] Send notification to attendees

##### Cancel Event

- [ ] Method `cancel_event(booking_id: str, reason: Optional[str] = None)` - Cancel event
- [ ] Support cancellation reason
- [ ] Send cancellation email
- [ ] Return confirmation

##### Get Team Profile

- [ ] Method `get_team(team_id: str)` - Get team details
- [ ] Return: `Team`
- [ ] Include team members list
- [ ] Include team settings

##### List Teams

- [ ] Method `list_teams()` - Get all teams user is member of
- [ ] Return: `List[Team]`
- [ ] Include membership info

##### Update User Settings

- [ ] Method `update_user_settings(timezone: Optional[str] = None, locale: Optional[str] = None, ...)` - Update profile
- [ ] Return: Updated `User`
- [ ] Validate timezone against IANA database
- [ ] Support partial updates

#### Rate Limiting & Retry Logic

- [ ] Implement exponential backoff for rate-limited requests (429)
- [ ] Maximum 3 retries with jitter
- [ ] Wait times: 1s, 2s, 4s (with randomization)
- [ ] Proper logging of retries
- [ ] Implement circuit breaker pattern for repeated failures
- [ ] Track rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset)

#### Session Management

- [ ] Store HTTP session (reuse across calls)
- [ ] Implement connection pooling
- [ ] Handle token refresh if using OAuth (future enhancement)
- [ ] Close connections properly on cleanup

#### Error Response Handling

- [ ] Parse error responses from Cal.com API
- [ ] Extract error messages and codes
- [ ] Map HTTP status codes to custom exceptions
- [ ] Provide helpful error context to caller

---

## Part 3: SDK Integration & Tools

### Files to Create/Modify

- [ ] `app/backend/src/integrations/cal_com/tools.py` - SDK tools for agents

### Implementation Checklist

#### Tool: Get User Profile

- [ ] Tool name: `get_user_profile`
- [ ] Description: "Get the authenticated user's Cal.com profile"
- [ ] No required parameters
- [ ] Return: User info (name, email, timezone, etc.)
- [ ] Handle and report errors clearly

#### Tool: List Event Types

- [ ] Tool name: `list_event_types`
- [ ] Description: "List all available event types for booking"
- [ ] Parameters:
  - [ ] `owner_id` (optional)
  - [ ] `team_id` (optional)
- [ ] Return: Event types with scheduling duration, slug, description
- [ ] Format output for readability

#### Tool: Get Event Type Details

- [ ] Tool name: `get_event_type`
- [ ] Description: "Get detailed information about a specific event type"
- [ ] Parameter: `event_type_id` (string, required)
- [ ] Return: Full event type configuration
- [ ] Validate event_type_id before API call

#### Tool: List Availability Slots

- [ ] Tool name: `list_availability`
- [ ] Description: "Get available time slots for a user"
- [ ] Parameters:
  - [ ] `user_id` (required)
  - [ ] `start_date` (required, ISO 8601)
  - [ ] `end_date` (required, ISO 8601)
  - [ ] `event_type_id` (optional, for specific event type availability)
- [ ] Return: Available slots with times
- [ ] Support timezone-aware responses

#### Tool: List Bookings/Events

- [ ] Tool name: `list_bookings`
- [ ] Description: "List all bookings and events"
- [ ] Parameters:
  - [ ] `limit` (optional, default 10, max 100)
  - [ ] `skip` (optional, default 0 for pagination)
  - [ ] `status` (optional: confirmed, tentative, cancelled)
  - [ ] `start_date` (optional)
  - [ ] `end_date` (optional)
- [ ] Return: List of events with key details
- [ ] Format dates consistently

#### Tool: Get Booking Details

- [ ] Tool name: `get_booking`
- [ ] Description: "Get detailed information about a specific booking"
- [ ] Parameters:
  - [ ] `booking_id` (required)
- [ ] Return: Complete booking information including attendees
- [ ] Handle 404s gracefully

#### Tool: Create Booking

- [ ] Tool name: `create_booking`
- [ ] Description: "Create a new booking for an event type"
- [ ] Parameters:
  - [ ] `event_type_id` (required)
  - [ ] `start_time` (required, ISO 8601 with timezone)
  - [ ] `end_time` (required)
  - [ ] `attendee_name` (optional)
  - [ ] `attendee_email` (optional)
  - [ ] `attendee_timezone` (optional)
  - [ ] `notes` (optional)
  - [ ] `send_confirmation` (optional, bool, default true)
- [ ] Validate all inputs before creating
- [ ] Return: Created booking with confirmation details
- [ ] Log creation with booking ID

#### Tool: Reschedule Booking

- [ ] Tool name: `reschedule_booking`
- [ ] Description: "Reschedule an existing booking to a new date/time"
- [ ] Parameters:
  - [ ] `booking_id` (required)
  - [ ] `new_start_time` (required, ISO 8601)
  - [ ] `new_end_time` (required)
  - [ ] `send_notification` (optional, bool, default true)
- [ ] Validate new time slot is available
- [ ] Return: Updated booking details

#### Tool: Cancel Booking

- [ ] Tool name: `cancel_booking`
- [ ] Description: "Cancel an existing booking"
- [ ] Parameters:
  - [ ] `booking_id` (required)
  - [ ] `cancellation_reason` (optional)
  - [ ] `send_notification` (optional, bool, default true)
- [ ] Confirm cancellation successful
- [ ] Return: Confirmation message with booking ID

#### Tool: List Teams

- [ ] Tool name: `list_teams`
- [ ] Description: "List all teams user is member of"
- [ ] No required parameters
- [ ] Return: Team list with member counts and slugs

#### Tool: Get Team Details

- [ ] Tool name: `get_team`
- [ ] Description: "Get detailed information about a team"
- [ ] Parameter: `team_id` (required)
- [ ] Return: Team info including members and settings

#### Tool: Update User Timezone

- [ ] Tool name: `update_user_timezone`
- [ ] Description: "Update user's timezone for scheduling"
- [ ] Parameter: `timezone` (required, IANA format like 'America/New_York')
- [ ] Return: Updated user profile
- [ ] Validate timezone

#### Tool Registration

- [ ] Register all tools with proper metadata
- [ ] Add clear descriptions for each tool
- [ ] Document parameters with types and constraints
- [ ] Include usage examples in docstrings

---

## Part 4: Unit Tests

### Files to Create/Modify

- [ ] `app/backend/__tests__/unit/integrations/cal_com/__init__.py`
- [ ] `app/backend/__tests__/fixtures/cal_com_fixtures.py` - Shared test fixtures
- [ ] `app/backend/__tests__/unit/integrations/cal_com/test_client.py` - Client unit tests
- [ ] `app/backend/__tests__/unit/integrations/cal_com/test_models.py` - Model tests
- [ ] `app/backend/__tests__/unit/integrations/cal_com/test_exceptions.py` - Exception tests

### Implementation Checklist

#### Test Fixtures (cal_com_fixtures.py)

- [ ] Mock API key
- [ ] Mock HTTP responses for all Cal.com API endpoints
- [ ] Create mock CalComEvent data fixtures
- [ ] Create mock EventType data fixtures
- [ ] Create mock User data fixtures
- [ ] Create mock Team data fixtures
- [ ] Create mock error responses (400, 401, 404, 429, 500, etc.)
- [ ] Mock successful response payloads from actual API

#### Client Initialization Tests

- [ ] Test successful initialization with API key from environment
- [ ] Test initialization with API key parameter
- [ ] Test initialization with missing API key
- [ ] Test base URL configuration
- [ ] Test default headers are set correctly
- [ ] Test session pool is created
- [ ] Test timeout is configured

#### Authentication Tests

- [ ] Test API key is properly passed in Authorization header
- [ ] Test 401 response raises `CalComAuthError`
- [ ] Test invalid API key handling
- [ ] Test request headers contain correct authorization

#### User Profile Tests

- [ ] Test get_user() succeeds with valid auth
- [ ] Test get_user() returns correct User model
- [ ] Test get_user() handles API errors

#### Event Type Tests

- [ ] Test list_event_types() returns all event types
- [ ] Test list_event_types() with owner_id filter
- [ ] Test list_event_types() with team_id filter
- [ ] Test pagination handling
- [ ] Test get_event_type() with valid ID
- [ ] Test get_event_type() with non-existent ID (404)
- [ ] Test create_event_type() creates new type
- [ ] Test create_event_type() validation (slug, length, etc.)

#### Availability Tests

- [ ] Test list_availability() with date range
- [ ] Test list_availability() returns correct slots
- [ ] Test timezone conversion in availability
- [ ] Test empty availability list

#### Booking Tests

- [ ] Test list_bookings() succeeds
- [ ] Test list_bookings() with pagination
- [ ] Test list_bookings() with filters (status, date range)
- [ ] Test get_booking() with valid ID
- [ ] Test get_booking() with non-existent ID (404)
- [ ] Test create_booking() with required fields
- [ ] Test create_booking() with optional fields (notes, timezone)
- [ ] Test create_booking() validation (start < end time)
- [ ] Test reschedule_event() updates time correctly
- [ ] Test reschedule_event() validates no conflicts
- [ ] Test cancel_event() marks as cancelled
- [ ] Test cancel_event() supports reason

#### Team Tests

- [ ] Test get_team() returns team details
- [ ] Test list_teams() returns user's teams
- [ ] Test team member lists are populated

#### User Settings Tests

- [ ] Test update_user_settings() changes timezone
- [ ] Test timezone validation (IANA format)
- [ ] Test partial updates work
- [ ] Test updated user is returned

#### Rate Limiting & Retry Tests

- [ ] Test exponential backoff on 429 (rate limit)
- [ ] Test retry count increases
- [ ] Test jitter is applied to wait times
- [ ] Test max retries (should fail after 3)
- [ ] Test logging of retries
- [ ] Test circuit breaker after repeated failures

#### Error Handling Tests

- [ ] Test 400 Bad Request raises appropriate error
- [ ] Test 401 Unauthorized raises `CalComAuthError`
- [ ] Test 403 Forbidden raises `CalComAuthError`
- [ ] Test 404 Not Found raises `CalComNotFoundError`
- [ ] Test 429 Too Many Requests raises `CalComRateLimitError`
- [ ] Test 500 Server Error raises `CalComAPIError`
- [ ] Test network errors are handled

#### Exception Tests

- [ ] Test all custom exceptions can be raised and caught
- [ ] Test exception messages are helpful
- [ ] Test exception inheritance hierarchy

#### Models Tests

- [ ] Test CalComEvent creation with required fields
- [ ] Test CalComEvent with all fields
- [ ] Test model validation (invalid dates, etc.)
- [ ] Test model serialization to dict
- [ ] Test model deserialization from API response
- [ ] Test EventType model
- [ ] Test User model
- [ ] Test Team model
- [ ] Test Availability model
- [ ] Test BookingConfirmation model

#### Coverage Requirements

- [ ] Achieve >90% code coverage in `client.py`
- [ ] Achieve >90% code coverage in `models.py`
- [ ] Achieve >85% code coverage in `tools.py`
- [ ] Run: `pytest app/backend/__tests__/unit/integrations/cal_com/ -v --cov=app.backend.src.integrations.cal_com --cov-report=html`

---

## Part 5: Integration Tests (Live API with .env Credentials)

### Files to Create/Modify

- [ ] `app/backend/__tests__/integration/cal_com/__init__.py`
- [ ] `app/backend/__tests__/integration/cal_com/conftest.py` - Shared fixtures
- [ ] `app/backend/__tests__/integration/cal_com/test_live_api.py` - Tests against real Cal.com API

### Implementation Checklist

#### Environment Setup

- [ ] Verify `.env` file exists in project root with `CAL_COM_API_KEY` set
- [ ] Verify API key is valid (authenticate successfully)
- [ ] Load base URL from `CAL_COM_BASE_URL` (or use default)
- [ ] Create test fixtures that use real .env values
- [ ] Document which Cal.com account is used for testing

#### conftest.py Setup

- [ ] Load `CAL_COM_API_KEY` from project root `.env`
- [ ] Initialize real CalComClient with loaded API key
- [ ] Provide authenticated client fixture
- [ ] Add pytest markers for integration tests
- [ ] Add skip decorators for when credentials are missing
- [ ] Implement cleanup fixtures (delete test data after tests)

#### Live API Tests (Real Cal.com Account)

- [ ] Test authentication succeeds with API key
- [ ] Test get_user() returns actual user profile
- [ ] Test list_event_types() returns real event types
- [ ] Test get_event_type() returns correct details
- [ ] Test list_availability() with date range
- [ ] Test list_bookings() returns events (or empty)
- [ ] Test create_booking() creates event successfully
  - [ ] Verify booking appears in list_bookings()
  - [ ] Verify booking details match what was sent
  - [ ] Clean up: delete/cancel the created booking afterward
- [ ] Test reschedule_event() modifies time successfully
  - [ ] Verify new time is set
  - [ ] Verify old time is no longer booked
  - [ ] Clean up: cancel the modified booking
- [ ] Test cancel_event() removes/cancels successfully
  - [ ] Verify booking is marked cancelled
- [ ] Test get_booking() with real booking ID
- [ ] Test list_teams() returns user's teams
- [ ] Test get_team() returns correct team
- [ ] Test update_user_settings() changes timezone
  - [ ] Verify change persists
  - [ ] Revert to original timezone
- [ ] Test error handling with real API responses
  - [ ] Try to get non-existent event type (404)
  - [ ] Try to book unavailable slot
  - [ ] Invalid date formats

#### Test Organization

- [ ] Use pytest fixtures for setup/teardown
- [ ] Mark tests with `@pytest.mark.integration`
- [ ] Use skip if credentials not available: `@pytest.mark.skipif(not has_credentials, reason="Cal.com API credentials not configured")`
- [ ] Clean up all created bookings at end of each test
- [ ] Add timeouts to prevent hanging tests (30 sec default)
- [ ] Log API calls for debugging
- [ ] Capture response times for performance analysis

#### .env Credential Testing

- [ ] Test with `.env` file values directly from project root
- [ ] Test error when .env file missing
- [ ] Test error when `CAL_COM_API_KEY` not set
- [ ] Test error when API key is invalid
- [ ] Test successful connection with valid key
- [ ] Document the Cal.com account/workspace used

#### Expected API Behaviors

- [ ] Understand Cal.com API response format
- [ ] Test pagination (if applicable)
- [ ] Test filtering and search
- [ ] Test rate limiting (request limits per time window)
- [ ] Test error response formats

---

## Part 6: Comprehensive Testing Verification

### Files to Check/Create

- [ ] `app/backend/__tests__/integration/cal_com/TEST_REPORT_cal_com.md` - Test results documentation

### Testing Checklist

#### Unit Test Execution

- [ ] Run unit tests: `pytest app/backend/__tests__/unit/integrations/cal_com/ -v`
- [ ] All unit tests pass ✓
- [ ] Code coverage >90% for critical paths
- [ ] No warnings or deprecations

#### Integration Test Execution

- [ ] Verify `.env` credentials exist and are valid in project root
- [ ] Run integration tests: `pytest app/backend/__tests__/integration/cal_com/ -v -s`
- [ ] All integration tests pass ✓
- [ ] All real API calls succeed
- [ ] No test data left behind on Cal.com account after tests

#### Coverage Report

- [ ] Generate coverage report: `pytest app/backend/__tests__/unit/integrations/cal_com/ --cov=app.backend.src.integrations.cal_com --cov-report=html --cov-report=term-missing`
- [ ] Review `htmlcov/index.html` for coverage details
- [ ] Coverage >90% overall
- [ ] Identify any uncovered lines and add tests or document why untestable

#### Integration with Existing Code

- [ ] Add import in `app/backend/src/integrations/__init__.py`
- [ ] Ensure no conflicts with existing integrations
- [ ] Verify models follow same patterns as existing integrations
- [ ] Check exception handling matches project standards

#### Tools Registration

- [ ] Verify all 11 tools are registered
- [ ] Test each tool via Claude Agent SDK (if applicable)
- [ ] Verify tool parameters are correct
- [ ] Verify tool responses are well-formatted

#### Error Scenarios

- [ ] Test with missing `.env` file
- [ ] Test with invalid API key
- [ ] Test with expired/revoked API key
- [ ] Test with missing API permissions
- [ ] Test with network failures
- [ ] Test with malformed API responses
- [ ] All errors handled gracefully with clear messages

#### Performance Testing

- [ ] Test list_event_types() with many event types
- [ ] Test list_bookings() with 100+ bookings
- [ ] Test pagination works correctly
- [ ] Test rate limiting/retry logic with concurrent calls
- [ ] Measure response times for common operations
- [ ] Verify no connection leaks in session pooling

---

## Part 7: Documentation & Final Steps

### Files to Create/Modify

- [ ] `app/backend/src/integrations/cal_com/README.md` - Integration documentation
- [ ] `app/backend/__tests__/integration/cal_com/README.md` - Testing guide

### Documentation Checklist

#### README.md Content

- [ ] Overview of Cal.com integration
- [ ] Installation and setup instructions
- [ ] API key setup guide:
  - [ ] How to obtain API key from Cal.com account
  - [ ] How to configure `.env` in project root
  - [ ] Required environment variables
- [ ] Quick start example code
- [ ] Available methods/tools with examples
- [ ] Supported Cal.com features
- [ ] Error handling guide
- [ ] Rate limiting information
- [ ] Links to Cal.com API documentation

#### Testing Guide

- [ ] How to run unit tests
- [ ] How to run integration tests
- [ ] How to setup `.env` credentials for integration testing
- [ ] Where to place `.env` file (project root)
- [ ] Troubleshooting common issues
- [ ] Coverage requirements and how to check

#### Code Quality Checks

- [ ] Run ruff linter: `ruff check app/backend/src/integrations/cal_com/`
- [ ] Run mypy: `mypy app/backend/src/integrations/cal_com/ --strict`
- [ ] All lint errors resolved
- [ ] All type hints properly set
- [ ] No unused imports or variables

#### Final Verification

- [ ] All tests passing (unit + integration)
- [ ] Coverage >90% for client code
- [ ] Code quality checks passing
- [ ] Documentation complete and accurate
- [ ] No broken imports or circular dependencies
- [ ] Integration tests pass with live Cal.com API
- [ ] All 11 SDK tools accessible and working

---

## All API Endpoints Covered

### User Management

- [x] `GET /users/me` - Get authenticated user (get_user_profile tool)
- [x] `PATCH /users/{userId}` - Update user settings (update_user_timezone tool)

### Event Types

- [x] `GET /event-types` - List event types (list_event_types tool)
- [x] `GET /event-types/{eventTypeId}` - Get event type details (get_event_type tool)
- [x] `POST /event-types` - Create event type (create_event_type in client)
- [x] `PATCH /event-types/{eventTypeId}` - Update event type (extensible in client)
- [x] `DELETE /event-types/{eventTypeId}` - Delete event type (extensible in client)

### Availability

- [x] `GET /availability` - Get available slots (list_availability tool)

### Bookings/Events

- [x] `GET /bookings` - List bookings (list_bookings tool)
- [x] `GET /bookings/{bookingId}` - Get booking details (get_booking tool)
- [x] `POST /bookings` - Create booking (create_booking tool)
- [x] `PATCH /bookings/{bookingId}` - Reschedule booking (reschedule_booking tool)
- [x] `DELETE /bookings/{bookingId}` - Cancel booking (cancel_booking tool)

### Teams

- [x] `GET /teams` - List teams (list_teams tool)
- [x] `GET /teams/{teamId}` - Get team details (get_team tool)

---

## Verification

To verify this task is 100% complete and functioning:

```bash
# 1. Run unit tests
pytest app/backend/__tests__/unit/integrations/cal_com/ -v --cov=app.backend.src.integrations.cal_com --cov-report=term-missing

# 2. Run integration tests (requires .env credentials in project root)
pytest app/backend/__tests__/integration/cal_com/ -v -s

# 3. Check code quality
ruff check app/backend/src/integrations/cal_com/
mypy app/backend/src/integrations/cal_com/ --strict

# 4. Verify imports
python -c "from app.backend.src.integrations.cal_com import CalComClient"

# 5. Check all tools are accessible
python -c "from app.backend.src.integrations.cal_com.tools import *"

# 6. Validate credentials loading from .env
CAL_COM_API_KEY=$(grep CAL_COM_API_KEY .env | cut -d '=' -f2) python -c "
from app.backend.src.integrations.cal_com import CalComClient
client = CalComClient()
user = client.get_user()
print(f'✓ Successfully authenticated as {user.name} ({user.email})')
"

# 7. Test all 11 tools are callable
python -c "
from app.backend.src.integrations.cal_com.tools import (
    get_user_profile, list_event_types, get_event_type,
    list_availability, list_bookings, get_booking,
    create_booking, reschedule_booking, cancel_booking,
    list_teams, get_team
)
print('✓ All 11 tools successfully imported')
"
```

### Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass with live Cal.com API
- [ ] Code coverage >90%
- [ ] Linting checks pass (ruff, mypy)
- [ ] Credentials load from `.env` in project root successfully
- [ ] Can authenticate to Cal.com API with API key
- [ ] Can perform all CRUD operations (list, get, create, update, delete)
- [ ] Error handling works correctly for all scenarios
- [ ] Rate limiting and retries work
- [ ] All 11 SDK tools function correctly
- [ ] All major Cal.com API endpoints covered
- [ ] Documentation is complete and accurate
- [ ] No console warnings or errors
- [ ] Integration with existing code (imports, patterns) complete

---

## Notes

- This is a **comprehensive, production-ready** integration requiring ~15-20 hours of development
- Test-driven development recommended: write tests first, then implementation
- API key must have sufficient permissions for all operations tested
- `.env` file must be in project root (not in subdirectories)
- Cal.com API is RESTful with JSON request/response bodies
- Follow the patterns established in existing integrations (Google Calendar, Drive, Docs, etc.)
- Rate limiting: Check Cal.com API docs for current rate limits
- All code must follow project linting standards (ruff, mypy strict mode)
- Minimum coverage: >90% for tools, >85% for full integration code
- Integration tests clean up after themselves (delete test bookings)
- Support timezone handling (IANA database format)
- Document any breaking changes or compatibility notes
