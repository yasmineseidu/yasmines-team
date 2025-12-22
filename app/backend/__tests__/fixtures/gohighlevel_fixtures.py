"""Test fixtures and sample data for GoHighLevel API tests."""

from src.integrations.gohighlevel import Contact, Deal

# Sample contact data for testing
SAMPLE_CONTACT = Contact(
    id="contact_123",
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    phone="+1234567890",
    status="lead",
    source="api",
    tags=["important", "vip"],
    custom_fields={"industry": "Technology"},
    address="123 Main St",
    city="San Francisco",
    state="CA",
    postal_code="94105",
    website="https://johndoe.com",
    timezone="America/Los_Angeles",
)

SAMPLE_CONTACT_CREATION_DATA = {
    "firstName": "Jane",
    "lastName": "Smith",
    "email": "jane@example.com",
    "phone": "+9876543210",
    "source": "api",
    "status": "lead",
    "tags": ["sales"],
}

SAMPLE_CONTACT_UPDATE_DATA = {
    "firstName": "Jane",
    "lastName": "Johnson",
    "status": "customer",
}

# Sample deal data for testing
SAMPLE_DEAL = Deal(
    id="deal_123",
    name="Enterprise Contract",
    value=50000.00,
    status="open",
    contact_id="contact_123",
    stage="negotiation",
    probability=75,
    expected_close_date="2025-12-31",
)

SAMPLE_DEAL_CREATION_DATA = {
    "name": "New Opportunity",
    "value": 10000.00,
    "status": "open",
    "contactId": "contact_123",
    "stage": "qualification",
}

SAMPLE_DEAL_UPDATE_DATA = {
    "value": 15000.00,
    "status": "won",
    "probability": 100,
}

# API response formats
SAMPLE_CONTACT_API_RESPONSE = {
    "id": "contact_123",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "status": "lead",
    "source": "api",
    "tags": ["important"],
    "customFields": {"field1": "value1"},
    "createdAt": "2025-12-22T00:00:00Z",
    "updatedAt": "2025-12-22T01:00:00Z",
}

SAMPLE_CONTACTS_LIST_RESPONSE = {
    "contacts": [
        {
            "id": "contact_1",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
        },
        {
            "id": "contact_2",
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "jane@example.com",
        },
    ],
    "total": 2,
}

SAMPLE_DEAL_API_RESPONSE = {
    "id": "deal_123",
    "name": "Enterprise Contract",
    "value": 50000.00,
    "status": "open",
    "contactId": "contact_123",
    "stage": "negotiation",
    "probability": 75,
    "expectedCloseDate": "2025-12-31",
    "createdAt": "2025-12-22T00:00:00Z",
    "updatedAt": "2025-12-22T01:00:00Z",
}

SAMPLE_DEALS_LIST_RESPONSE = {
    "deals": [
        {
            "id": "deal_1",
            "name": "Deal 1",
            "value": 10000.00,
            "status": "open",
        },
        {
            "id": "deal_2",
            "name": "Deal 2",
            "value": 20000.00,
            "status": "won",
        },
    ],
    "total": 2,
}

SAMPLE_LOCATION_INFO = {
    "id": "location_123",
    "name": "My Business Location",
    "email": "info@mycompany.com",
    "phone": "+1234567890",
    "timezone": "America/Los_Angeles",
}

SAMPLE_EMAIL_SEND_RESPONSE = {
    "success": True,
    "messageId": "msg_123",
    "contactId": "contact_123",
}

SAMPLE_SMS_SEND_RESPONSE = {
    "success": True,
    "messageId": "sms_123",
    "contactId": "contact_123",
}

SAMPLE_WEBHOOK_RESPONSE = {
    "id": "webhook_123",
    "url": "https://example.com/webhook",
    "events": ["contact.created", "contact.updated", "deal.created"],
    "isActive": True,
}

# Test data for different scenarios
ERROR_RESPONSE = {
    "statusCode": 400,
    "message": "Invalid request",
    "errors": ["Field required: firstName"],
}

UNAUTHORIZED_RESPONSE = {
    "statusCode": 401,
    "message": "Unauthorized",
}

RATE_LIMIT_RESPONSE = {
    "statusCode": 429,
    "message": "Too many requests",
}

# ============================================================================
# COMPREHENSIVE SAMPLE DATA FOR REAL API TESTING
# ============================================================================

# Test contacts with realistic scenarios
TEST_CONTACTS_FOR_CREATION = [
    {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice@techcorp.com",
        "phone": "+1-555-0101",
        "source": "api",
        "status": "lead",
        "tags": ["prospect", "tech"],
    },
    {
        "first_name": "Bob",
        "last_name": "Smith",
        "email": "bob@innovations.io",
        "phone": "+1-555-0102",
        "source": "form",
        "status": "customer",
        "tags": ["client"],
    },
    {
        "first_name": "Carol",
        "last_name": "Williams",
        "email": "carol@startup.co",
        "phone": "+1-555-0103",
        "source": "import",
        "status": "opportunity",
        "tags": ["enterprise", "vip"],
    },
]

# Test deals with realistic scenarios
TEST_DEALS_FOR_CREATION = [
    {
        "name": "Small Project",
        "value": 5000.00,
        "status": "open",
        "stage": "discovery",
    },
    {
        "name": "Mid-Market Contract",
        "value": 50000.00,
        "status": "open",
        "stage": "proposal",
        "probability": 60,
    },
    {
        "name": "Enterprise Deal",
        "value": 250000.00,
        "status": "open",
        "stage": "negotiation",
        "probability": 75,
        "expected_close_date": "2025-12-31",
    },
]

# Expected API responses from GoHighLevel
SUCCESSFUL_CONTACT_RESPONSE = {
    "contact": {
        "id": "cls_abc123def456",
        "firstName": "Test",
        "lastName": "Contact",
        "email": "test@example.com",
        "phone": None,
        "status": "lead",
        "source": "api",
        "tags": [],
        "customFields": {},
        "createdAt": "2025-12-22T12:00:00Z",
        "updatedAt": "2025-12-22T12:00:00Z",
    }
}

SUCCESSFUL_DEAL_RESPONSE = {
    "deal": {
        "id": "opp_xyz789uvw012",
        "name": "Test Deal",
        "value": 50000.00,
        "status": "open",
        "stage": "proposal",
        "probability": 50,
        "contactId": "cls_abc123def456",
        "expectedCloseDate": None,
        "createdAt": "2025-12-22T12:00:00Z",
        "updatedAt": "2025-12-22T12:00:00Z",
    }
}

# Test scenarios and edge cases
TEST_SCENARIOS = {
    "valid_email": "test@example.com",
    "invalid_email": "not-an-email",
    "phone_with_formatting": "+1 (555) 123-4567",
    "phone_without_formatting": "+15551234567",
    "long_name": "A" * 100,
    "special_characters": "José García-López",
    "unicode_name": "李明",
    "empty_string": "",
    "large_deal_value": 999999999.99,
    "negative_deal_value": -10000.00,
    "zero_deal_value": 0.00,
}
