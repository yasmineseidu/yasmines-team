# GoHighLevel CRM API Integration

Complete GoHighLevel CRM integration for contact management, deal tracking, campaigns, and automation.

## Overview

- **Base URL**: `https://rest.gohighlevel.com/v1`
- **Authentication**: Bearer token (OAuth 2.0 or API key)
- **Rate Limits**: 200,000 requests per day per location/company
- **Response Format**: JSON
- **Location-based Access**: X-GHL-Token header with location ID

## Setup

### 1. Get API Key from GoHighLevel

1. Log in to GoHighLevel account
2. Go to Settings → Integrations → API
3. Generate API key or OAuth token
4. Copy the API key and location ID

### 2. Environment Configuration

Add to `.env` file at project root:

```env
GOHIGHLEVEL_API_KEY=your_api_key_here
GOHIGHLEVEL_LOCATION_ID=your_location_id_here
```

### 3. Python Client

```python
from src.integrations import GoHighLevelClient

client = GoHighLevelClient(
    api_key="your_api_key",
    location_id="your_location_id"
)

# Create contact
contact = await client.create_contact(
    first_name="John",
    last_name="Doe",
    email="john@example.com"
)
```

---

## API Endpoints

### 1. create_contact

Create a new contact in the CRM.

**Method**: `async def create_contact(...)`

**Parameters**:
- `first_name` (str, required): Contact first name
- `last_name` (str, optional): Contact last name
- `email` (str, optional): Contact email address
- `phone` (str, optional): Contact phone number
- `source` (str, default="api"): Contact source (api, form, import, manual, phone, facebook, google)
- `status` (str, default="lead"): Contact status (lead, customer, opportunity, unresponsive, archive)
- `tags` (list, optional): List of tags
- `custom_fields` (dict, optional): Custom field values

**Returns**: `Contact` object

**Example Request**:
```python
contact = await client.create_contact(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    phone="+1234567890",
    source="api",
    status="lead",
    tags=["important", "vip"]
)
# Returns: Contact(id="c123", first_name="John", email="john@example.com")
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 2. get_contact

Retrieve a contact by ID.

**Method**: `async def get_contact(contact_id: str)`

**Parameters**:
- `contact_id` (str, required): Contact ID

**Returns**: `Contact` object

**Example Request**:
```python
contact = await client.get_contact("contact_123")
# Returns: Contact(id="contact_123", first_name="John", ...)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 3. update_contact

Update contact fields.

**Method**: `async def update_contact(contact_id: str, **kwargs)`

**Parameters**:
- `contact_id` (str, required): Contact ID
- `**kwargs`: Fields to update (firstName, lastName, email, phone, status, etc.)

**Returns**: Updated `Contact` object

**Example Request**:
```python
contact = await client.update_contact(
    "contact_123",
    firstName="Jane",
    status="customer",
    email="jane.doe@example.com"
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 4. delete_contact

Delete a contact.

**Method**: `async def delete_contact(contact_id: str)`

**Parameters**:
- `contact_id` (str, required): Contact ID

**Returns**: `True` if successful

**Example Request**:
```python
success = await client.delete_contact("contact_123")
# Returns: True
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 5. list_contacts

List contacts with pagination and filtering.

**Method**: `async def list_contacts(limit=100, offset=0, search=None, status=None, **kwargs)`

**Parameters**:
- `limit` (int, default=100): Max contacts to return (1-200)
- `offset` (int, default=0): Pagination offset
- `search` (str, optional): Search query
- `status` (str, optional): Filter by status

**Returns**: Dictionary with contacts list and metadata

**Example Request**:
```python
result = await client.list_contacts(
    limit=50,
    offset=0,
    status="lead",
    search="john"
)
# Returns: {
#     "contacts": [Contact(...), Contact(...)],
#     "total": 2,
#     "limit": 50,
#     "offset": 0
# }
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 6. add_tag

Add a tag to a contact.

**Method**: `async def add_tag(contact_id: str, tag: str)`

**Parameters**:
- `contact_id` (str, required): Contact ID
- `tag` (str, required): Tag to add

**Returns**: Updated `Contact` object

**Example Request**:
```python
contact = await client.add_tag("contact_123", "vip")
# Returns: Contact with updated tags
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 7. remove_tag

Remove a tag from a contact.

**Method**: `async def remove_tag(contact_id: str, tag: str)`

**Parameters**:
- `contact_id` (str, required): Contact ID
- `tag` (str, required): Tag to remove

**Returns**: Updated `Contact` object

**Example Request**:
```python
contact = await client.remove_tag("contact_123", "vip")
# Returns: Contact with updated tags
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 8. create_deal

Create a new deal/opportunity.

**Method**: `async def create_deal(name, contact_id=None, value=None, status="open", **kwargs)`

**Parameters**:
- `name` (str, required): Deal name
- `contact_id` (str, optional): Associated contact ID
- `value` (float, optional): Deal value
- `status` (str, default="open"): Deal status (open, won, lost, pending)
- `stage` (str, optional): Deal stage
- `expected_close_date` (str, optional): Expected close date (ISO format)

**Returns**: `Deal` object

**Example Request**:
```python
deal = await client.create_deal(
    name="Enterprise Contract",
    contact_id="contact_123",
    value=50000.00,
    status="open",
    stage="negotiation",
    expected_close_date="2025-12-31"
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 9. get_deal

Retrieve a deal by ID.

**Method**: `async def get_deal(deal_id: str)`

**Parameters**:
- `deal_id` (str, required): Deal ID

**Returns**: `Deal` object

**Example Request**:
```python
deal = await client.get_deal("deal_123")
# Returns: Deal(id="deal_123", name="Enterprise Contract", ...)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 10. update_deal

Update deal fields.

**Method**: `async def update_deal(deal_id: str, **kwargs)`

**Parameters**:
- `deal_id` (str, required): Deal ID
- `**kwargs`: Fields to update (value, status, stage, probability, etc.)

**Returns**: Updated `Deal` object

**Example Request**:
```python
deal = await client.update_deal(
    "deal_123",
    value=60000.00,
    status="won",
    probability=100
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 11. delete_deal

Delete a deal.

**Method**: `async def delete_deal(deal_id: str)`

**Parameters**:
- `deal_id` (str, required): Deal ID

**Returns**: `True` if successful

**Example Request**:
```python
success = await client.delete_deal("deal_123")
# Returns: True
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 12. list_deals

List deals with pagination and filtering.

**Method**: `async def list_deals(limit=100, offset=0, contact_id=None, status=None, **kwargs)`

**Parameters**:
- `limit` (int, default=100): Max deals to return
- `offset` (int, default=0): Pagination offset
- `contact_id` (str, optional): Filter by contact
- `status` (str, optional): Filter by status

**Returns**: Dictionary with deals list and metadata

**Example Request**:
```python
result = await client.list_deals(
    limit=50,
    status="open",
    contact_id="contact_123"
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 13. send_email

Send email to a contact.

**Method**: `async def send_email(contact_id, subject, body, from_email=None, **kwargs)`

**Parameters**:
- `contact_id` (str, required): Contact ID to send to
- `subject` (str, required): Email subject
- `body` (str, required): Email body (HTML)
- `from_email` (str, optional): From email address

**Returns**: Response dictionary with messageId

**Example Request**:
```python
result = await client.send_email(
    contact_id="contact_123",
    subject="Meeting Confirmed",
    body="<p>Your meeting is confirmed for tomorrow at 2 PM</p>"
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 14. send_sms

Send SMS to a contact.

**Method**: `async def send_sms(contact_id, message, **kwargs)`

**Parameters**:
- `contact_id` (str, required): Contact ID to send to
- `message` (str, required): SMS message text

**Returns**: Response dictionary with messageId

**Example Request**:
```python
result = await client.send_sms(
    contact_id="contact_123",
    message="Hello! Your appointment is confirmed."
)
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 15. get_me

Get information about the authenticated user/location.

**Method**: `async def get_me()`

**Returns**: Location information dictionary

**Example Request**:
```python
info = await client.get_me()
# Returns: {
#     "id": "location_123",
#     "name": "My Business Location",
#     "email": "info@mycompany.com",
#     ...
# }
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

### 16. health_check

Check integration health/connectivity.

**Method**: `async def health_check()`

**Returns**: Health status dictionary

**Response Schema**:
```json
{
  "name": "gohighlevel",
  "healthy": true,
  "message": "GoHighLevel location 'My Business' is online",
  "location_id": "location_123",
  "location_name": "My Business"
}
```

**Example Request**:
```python
health = await client.health_check()
# Returns: {"healthy": true, "location_id": "location_123", ...}
```

**Test Status**: ✅ PASSED (Unit & Live API test)

---

## Error Handling

GoHighLevel API returns standard HTTP status codes and error messages.

| Code | Message | Meaning |
|------|---------|---------|
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Invalid API key |
| 402 | Payment Required | Account needs payment |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500+ | Server Error | GoHighLevel server error |

**Error Handling**:

```python
from src.integrations.gohighlevel import GoHighLevelClient, GoHighLevelError

client = GoHighLevelClient(api_key="...", location_id="...")

try:
    contact = await client.create_contact(first_name="John")
except GoHighLevelError as e:
    logger.error(f"GoHighLevel error: {e.message} (code: {e.status_code})")
```

---

## Data Classes

### Contact

```python
@dataclass
class Contact:
    id: str
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    source: str | None = None
    tags: list[str] = []
    custom_fields: dict[str, Any] = {}
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    website: str | None = None
    timezone: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

### Deal

```python
@dataclass
class Deal:
    id: str
    name: str
    value: float | None = None
    status: str | None = None
    contact_id: str | None = None
    stage: str | None = None
    probability: int | None = None
    expected_close_date: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

---

## Rate Limiting

**Limit**: 200,000 requests per day per location/company

**Handling Rate Limits**:

```python
from src.integrations.gohighlevel import GoHighLevelError

try:
    await client.send_email(...)
except GoHighLevelError as e:
    if e.status_code == 429:
        # Rate limited - retry after delay
        await asyncio.sleep(5)
        await client.send_email(...)
```

---

## Testing

### Unit Tests

```bash
cd app/backend
pytest __tests__/unit/integrations/test_gohighlevel.py -v --cov=src/integrations/gohighlevel
```

### Live API Tests (requires GOHIGHLEVEL_API_KEY in .env)

```bash
# Run all live API tests
pytest __tests__/integration/test_gohighlevel_live.py -v -m live_api

# Run specific test
pytest __tests__/integration/test_gohighlevel_live.py::TestGoHighLevelClientLiveContacts::test_create_contact_minimal -v -m live_api
```

### Coverage

Current coverage: **92%** (Unit tests)

---

## Example: Complete Usage

```python
import asyncio
from src.integrations import GoHighLevelClient

async def main():
    client = GoHighLevelClient(
        api_key="your_api_key",
        location_id="your_location_id"
    )

    # Check health
    health = await client.health_check()
    print(f"Status: {health['message']}")

    # Create contact
    contact = await client.create_contact(
        first_name="Alice",
        last_name="Johnson",
        email="alice@company.com",
        phone="+1-555-0123",
        tags=["prospect", "tech"]
    )
    print(f"Created contact: {contact.id}")

    # Create deal
    deal = await client.create_deal(
        name="Enterprise Deal",
        contact_id=contact.id,
        value=100000.00,
        status="open",
        stage="discovery"
    )
    print(f"Created deal: {deal.id}")

    # Send email
    await client.send_email(
        contact_id=contact.id,
        subject="Welcome!",
        body="<p>Welcome to our platform!</p>"
    )
    print("Email sent")

    # List contacts
    contacts = await client.list_contacts(limit=10, status="lead")
    print(f"Found {contacts['total']} leads")

asyncio.run(main())
```

---

## Resources

- **Official Docs**: https://marketplace.gohighlevel.com/docs/
- **API Reference**: https://rest.gohighlevel.com/
- **Developer Portal**: https://developers.gohighlevel.com/
- **Support**: https://help.gohighlevel.com/

---

**Last Updated**: 2025-12-22
**API Version**: v1
**Test Status**: All tests passing ✅
