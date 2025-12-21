"""Test fixtures for HeyReach integration tests."""

from typing import Any

# Sample campaign data
SAMPLE_CAMPAIGN_DATA: dict[str, Any] = {
    "id": "campaign-123",
    "name": "Q1 LinkedIn Outreach",
    "status": "ACTIVE",
    "description": "Outreach campaign for Q1 2024",
    "createdAt": "2024-01-01T10:00:00Z",
    "updatedAt": "2024-01-15T14:30:00Z",
    "campaignAccountIds": ["account-1", "account-2"],
}

SAMPLE_DRAFT_CAMPAIGN: dict[str, Any] = {
    "id": "campaign-456",
    "name": "Draft Campaign",
    "status": "DRAFT",
    "description": None,
}

SAMPLE_PAUSED_CAMPAIGN: dict[str, Any] = {
    "id": "campaign-789",
    "name": "Paused Campaign",
    "status": "PAUSED",
}

# Sample lead data
SAMPLE_LEAD_DATA: dict[str, Any] = {
    "id": "lead-123",
    "firstName": "John",
    "lastName": "Doe",
    "emailAddress": "john.doe@example.com",
    "profileUrl": "https://www.linkedin.com/in/johndoe",
    "companyName": "Acme Corporation",
    "position": "Chief Executive Officer",
    "location": "San Francisco, CA",
    "summary": "CEO at Acme Corp | 15+ years in SaaS",
    "about": "I help companies scale their operations.",
    "status": "contacted",
    "campaignId": "campaign-123",
    "createdAt": "2024-01-10T09:00:00Z",
    "customUserFields": [
        {"name": "industry", "value": "Technology"},
        {"name": "company_size", "value": "500-1000"},
        {"name": "funding_stage", "value": "Series B"},
    ],
}

SAMPLE_LEAD_MINIMAL: dict[str, Any] = {
    "firstName": "Jane",
    "lastName": "Smith",
    "profileUrl": "https://www.linkedin.com/in/janesmith",
}

# Sample list data
SAMPLE_LIST_DATA: dict[str, Any] = {
    "id": "list-123",
    "name": "CEO Target List",
    "type": "lead",
    "leadCount": 250,
    "createdAt": "2024-01-05T08:00:00Z",
}

SAMPLE_COMPANY_LIST: dict[str, Any] = {
    "id": "list-456",
    "name": "Target Companies",
    "type": "company",
    "leadCount": 100,
}

# Sample analytics data
SAMPLE_ANALYTICS_DATA: dict[str, Any] = {
    "campaignId": "campaign-123",
    "totalLeads": 500,
    "contacted": 400,
    "replied": 100,
    "connected": 75,
    "responseRate": 25.0,
    "connectionRate": 18.75,
}

# Sample message template
SAMPLE_TEMPLATE_DATA: dict[str, Any] = {
    "id": "template-123",
    "name": "Connection Request",
    "content": "Hi {{firstName}}, I noticed we share an interest in {{industry}}. Would love to connect!",
    "type": "connection",
    "variables": ["firstName", "industry"],
}

SAMPLE_FOLLOWUP_TEMPLATE: dict[str, Any] = {
    "id": "template-456",
    "name": "Follow-up Message",
    "content": "Hi {{firstName}}, thanks for connecting! I wanted to reach out because...",
    "type": "message",
    "variables": ["firstName"],
}

# Sample conversation data
SAMPLE_CONVERSATION_DATA: dict[str, Any] = {
    "id": "conv-123",
    "leadId": "lead-123",
    "linkedinUrl": "https://www.linkedin.com/in/johndoe",
    "lastMessage": "Thanks for the introduction! Let's schedule a call.",
    "lastMessageAt": "2024-01-20T16:30:00Z",
    "messageCount": 5,
}

# Sample social action data
SAMPLE_SOCIAL_ACTION: dict[str, Any] = {
    "id": "action-123",
    "type": "like",
    "status": "completed",
    "targetUrl": "https://www.linkedin.com/posts/johndoe-123456",
    "scheduledAt": "2024-01-20T10:00:00Z",
}

# Sample bulk add result
SAMPLE_BULK_ADD_SUCCESS: dict[str, Any] = {
    "success": True,
    "addedCount": 10,
    "failedCount": 0,
    "failedLeads": [],
}

SAMPLE_BULK_ADD_PARTIAL: dict[str, Any] = {
    "success": True,
    "addedCount": 8,
    "failedCount": 2,
    "failedLeads": [
        {"email": "invalid1@test.com", "reason": "Invalid LinkedIn URL"},
        {"email": "invalid2@test.com", "reason": "Duplicate entry"},
    ],
}

# Sample overall stats
SAMPLE_OVERALL_STATS: dict[str, Any] = {
    "totalCampaigns": 15,
    "activeCampaigns": 5,
    "totalLeads": 10000,
    "totalConnections": 2500,
    "totalReplies": 1500,
    "averageResponseRate": 15.0,
    "averageConnectionRate": 25.0,
}

# API error responses
ERROR_UNAUTHORIZED: dict[str, Any] = {
    "error": "Unauthorized",
    "message": "Invalid API key provided",
    "status": 401,
}

ERROR_RATE_LIMITED: dict[str, Any] = {
    "error": "Too Many Requests",
    "message": "Rate limit exceeded. Please try again later.",
    "status": 429,
    "retryAfter": 60,
}

ERROR_NOT_FOUND: dict[str, Any] = {
    "error": "Not Found",
    "message": "Campaign not found",
    "status": 404,
}

ERROR_VALIDATION: dict[str, Any] = {
    "error": "Validation Error",
    "message": "Invalid request body",
    "details": [
        {"field": "name", "message": "Name is required"},
        {"field": "leads", "message": "At least one lead is required"},
    ],
    "status": 400,
}

# Paginated response examples
PAGINATED_CAMPAIGNS: dict[str, Any] = {
    "items": [SAMPLE_CAMPAIGN_DATA, SAMPLE_DRAFT_CAMPAIGN],
    "total": 15,
    "page": 1,
    "limit": 50,
    "hasMore": False,
}

PAGINATED_LEADS: dict[str, Any] = {
    "items": [SAMPLE_LEAD_DATA],
    "total": 500,
    "page": 1,
    "limit": 50,
    "hasMore": True,
}


def get_sample_leads_for_bulk_add(count: int = 5) -> list[dict[str, Any]]:
    """Generate sample leads for bulk add operations."""
    return [
        {
            "firstName": f"Test{i}",
            "lastName": f"User{i}",
            "profileUrl": f"https://www.linkedin.com/in/testuser{i}",
            "companyName": f"Company {i}",
            "position": "Manager",
            "emailAddress": f"test{i}@example.com",
            "customUserFields": [
                {"name": "source", "value": "API Test"},
            ],
        }
        for i in range(count)
    ]


def get_sample_campaigns(count: int = 3) -> list[dict[str, Any]]:
    """Generate sample campaigns list."""
    statuses = ["ACTIVE", "PAUSED", "DRAFT"]
    return [
        {
            "id": f"campaign-{i}",
            "name": f"Campaign {i}",
            "status": statuses[i % len(statuses)],
            "createdAt": f"2024-01-0{i+1}T10:00:00Z",
        }
        for i in range(count)
    ]
