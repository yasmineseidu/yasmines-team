"""Test fixtures for Google Contacts API integration.

Provides sample data, mock credentials, and fixtures for unit and integration tests.
"""

from typing import Any

# pragma: allowlist secret
# Sample service account credentials (fake, for testing)
SAMPLE_CREDENTIALS = {  # pragma: allowlist secret
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id-123456",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
    "MIIEpAIBAAKCAQEA0Z3VS5JJcds3VGxqEJVvJVQq1lJYJLNZqVzPT5T5dIz/ZRTL\n"  # pragma: allowlist secret
    "yz+c0x/N5X5p5B5kzZ5a5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5\n"  # pragma: allowlist secret
    "Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5\n"  # pragma: allowlist secret
    "Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5\n"  # pragma: allowlist secret
    "Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5\n"  # pragma: allowlist secret
    "Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5Z5V5\n"  # pragma: allowlist secret
    "QIDAQABAoIBAH/xZsVKLYFMVXvX+A5pN5kX5L8YSh5pN4N5A5B5C5D5E5F5G5H5\n"  # pragma: allowlist secret
    "I5J5K5L5M5N5O5P5Q5R5S5T5U5V5W5X5Y5Z5a5b5c5d5e5f5g5h5i5j5k5l5m5\n"  # pragma: allowlist secret
    "n5o5p5q5r5s5t5u5v5w5x5y5z5A5B5C5D5E5F5G5H5I5J5K5L5M5N5O5P5Q5R5\n"  # pragma: allowlist secret
    "-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
    "client_email": "test-service-account@test-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}

INVALID_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project",
    # Missing required fields
}

# Sample contact data
SAMPLE_CONTACT_MINIMAL = {
    "resource_name": "people/c1234567890",
    "etag": "%EAE.AEw0xZBcD5HdBxLw4xLc/",
    "names": [{"givenName": "John", "familyName": "Doe"}],
}

SAMPLE_CONTACT_FULL = {
    "resource_name": "people/c1234567890",
    "etag": "%EAE.AEw0xZBcD5HdBxLw4xLc/",
    "names": [
        {
            "metadata": {"primary": True, "source": {"type": "CONTACT"}},
            "displayName": "John Doe",
            "familyName": "Doe",
            "givenName": "John",
        }
    ],
    "emailAddresses": [
        {
            "metadata": {"primary": True, "source": {"type": "CONTACT"}},
            "value": "john.doe@example.com",
            "type": "work",
        }
    ],
    "phoneNumbers": [
        {
            "metadata": {"primary": True, "source": {"type": "CONTACT"}},
            "value": "+1-555-123-4567",
            "canonicalForm": "+15551234567",
            "type": "mobile",
        }
    ],
    "addresses": [
        {
            "metadata": {"primary": True, "source": {"type": "CONTACT"}},
            "formattedValue": "123 Main St, Springfield, IL 62701",
            "streetAddress": "123 Main St",
            "city": "Springfield",
            "region": "IL",
            "postalCode": "62701",
            "country": "United States",
            "countryCode": "US",
            "type": "home",
        }
    ],
    "organizations": [
        {
            "metadata": {"source": {"type": "CONTACT"}},
            "name": "Acme Corporation",
            "title": "Senior Developer",
            "type": "work",
        }
    ],
}

# Sample contact group
SAMPLE_CONTACT_GROUP = {
    "resourceName": "contactGroups/c1234567890",
    "etag": "%EAE.AEw0xZBcD5HdBxLw4xLc/",
    "name": "Friends",
    "groupType": "USER_CONTACT_GROUP",
    "memberCount": 5,
}

# API response samples
CONTACTS_LIST_RESPONSE = {
    "connections": [SAMPLE_CONTACT_FULL],
    "nextPageToken": None,
}

CONTACT_GROUPS_LIST_RESPONSE = {
    "contactGroups": [SAMPLE_CONTACT_GROUP],
    "nextPageToken": None,
}

# Create contact request data
CREATE_CONTACT_DATA = {
    "given_name": "Jane",
    "family_name": "Smith",
    "email_address": "jane.smith@example.com",
    "phone_number": "+1-555-987-6543",
    "organization": "Tech Corp",
    "job_title": "Product Manager",
}

# Update contact request data
UPDATE_CONTACT_DATA = {
    "resource_name": "people/c1234567890",
    "given_name": "Janet",
    "family_name": "Smith",
    "email_address": "janet.smith@example.com",
    "phone_number": "+1-555-555-5555",
    "organization": "Tech Corp",
    "job_title": "Senior Product Manager",
}

# API error responses
ERROR_RESPONSE_404 = {
    "error": {
        "code": 404,
        "message": "Person not found",
        "status": "NOT_FOUND",
    }
}

ERROR_RESPONSE_429 = {
    "error": {
        "code": 429,
        "message": "Rate Limit Exceeded",
        "status": "RESOURCE_EXHAUSTED",
    }
}

ERROR_RESPONSE_403_QUOTA = {
    "error": {
        "code": 403,
        "message": "The caller does not have permission",
        "status": "PERMISSION_DENIED",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "PERMISSION_DENIED",
                "domain": "googleapis.com",
                "metadata": {
                    "consumer": "projects/test-project",
                    "service": "people.googleapis.com",
                },
            }
        ],
    }
}

# Test contact list data
TEST_CONTACTS: list[dict[str, Any]] = [
    {
        "resource_name": "people/c1111111111",
        "names": [{"givenName": "Alice", "familyName": "Johnson"}],
        "emailAddresses": [{"value": "alice@example.com"}],
    },
    {
        "resource_name": "people/c2222222222",
        "names": [{"givenName": "Bob", "familyName": "Wilson"}],
        "emailAddresses": [{"value": "bob@example.com"}],
    },
    {
        "resource_name": "people/c3333333333",
        "names": [{"givenName": "Charlie", "familyName": "Brown"}],
        "emailAddresses": [{"value": "charlie@example.com"}],
    },
]
