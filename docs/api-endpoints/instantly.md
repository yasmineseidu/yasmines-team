# Instantly.ai API Endpoints

## Overview

- **Base URL**: `https://api.instantly.ai/api/v2`
- **Authentication**: Bearer token via API key from Instantly dashboard
- **API Version**: V2
- **Rate Limits**: Soft throttle at ~100 req/min (no hard limit, system auto-scales)
- **Plan Required**: Growth plan or above for API V2 access

## Client Configuration

```python
from src.integrations import InstantlyClient

client = InstantlyClient(
    api_key="your-api-key",  # From Instantly dashboard
    timeout=30.0,            # Default: 30 seconds
    max_retries=3,           # Default: 3 retries with exponential backoff
)
```

## Campaign Endpoints

### 1. Create Campaign

**Method**: `POST`
**Path**: `/api/v2/campaigns`
**Description**: Create a new email campaign

**Request Parameters**:
- `name` (string, required): Campaign name
- `campaign_schedule` (object, required): Schedule configuration with timing, days, timezone

**Response Schema**:
```json
{
  "id": "camp-uuid",
  "name": "Campaign Name",
  "status": 0,
  "workspace_id": "ws-uuid",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**Example Request**:
```python
campaign = await client.create_campaign(
    name="Q1 Outreach",
    campaign_schedule={
        "schedules": [{
            "timing": {"from": "09:00", "to": "17:00"},
            "days": {"monday": True, "tuesday": True},
            "timezone": "America/New_York"
        }]
    }
)
```

**Status**: ✅ Implemented and tested

---

### 2. List Campaigns

**Method**: `GET`
**Path**: `/api/v2/campaigns`
**Description**: List campaigns with filtering and pagination

**Query Parameters**:
- `limit` (int, 1-100): Maximum campaigns to return
- `starting_after` (string): Pagination cursor
- `search` (string): Search by campaign name
- `status` (int): Filter by status code
- `tag_ids` (string): Filter by tag IDs (comma-separated)

**Response Schema**:
```json
{
  "items": [
    {
      "id": "camp-uuid",
      "name": "Campaign Name",
      "status": 1
    }
  ]
}
```

**Example Request**:
```python
campaigns = await client.list_campaigns(
    limit=50,
    search="outreach",
    status=CampaignStatus.ACTIVE
)
```

**Status**: ✅ Implemented and tested

---

### 3. Get Campaign

**Method**: `GET`
**Path**: `/api/v2/campaigns/{id}`
**Description**: Get single campaign details

**Response Schema**: Campaign object

**Example Request**:
```python
campaign = await client.get_campaign("camp-123")
```

**Status**: ✅ Implemented and tested

---

### 4. Update Campaign

**Method**: `PATCH`
**Path**: `/api/v2/campaigns/{id}`
**Description**: Update campaign fields

**Example Request**:
```python
campaign = await client.update_campaign(
    campaign_id="camp-123",
    name="Updated Name"
)
```

**Status**: ✅ Implemented and tested

---

### 5. Delete Campaign

**Method**: `DELETE`
**Path**: `/api/v2/campaigns/{id}`
**Description**: Delete a campaign

**Example Request**:
```python
success = await client.delete_campaign("camp-123")
```

**Status**: ✅ Implemented and tested

---

### 6. Activate Campaign

**Method**: `POST`
**Path**: `/api/v2/campaigns/{id}/activate`
**Description**: Start or resume campaign sending

**Example Request**:
```python
campaign = await client.activate_campaign("camp-123")
```

**Status**: ✅ Implemented and tested

---

### 7. Pause Campaign

**Method**: `POST`
**Path**: `/api/v2/campaigns/{id}/pause`
**Description**: Pause active campaign

**Example Request**:
```python
campaign = await client.pause_campaign("camp-123")
```

**Status**: ✅ Implemented and tested

---

### 8. Duplicate Campaign

**Method**: `POST`
**Path**: `/api/v2/campaigns/{id}/duplicate`
**Description**: Create a copy of existing campaign

**Example Request**:
```python
new_campaign = await client.duplicate_campaign("camp-123")
```

**Status**: ✅ Implemented and tested

---

## Lead Endpoints

### 9. Create Lead

**Method**: `POST`
**Path**: `/api/v2/leads`
**Description**: Create a new lead

**Request Parameters**:
- `email` (string, required): Lead's email address
- `campaign` (string): Campaign ID to add lead to
- `list_id` (string): Lead list ID to add lead to
- `first_name` (string): Lead's first name
- `last_name` (string): Lead's last name
- `company_name` (string): Lead's company
- `website` (string): Lead's website
- `phone` (string): Lead's phone number
- `custom_variables` (object): Custom fields

**Note**: Either `campaign` or `list_id` must be provided.

**Example Request**:
```python
lead = await client.create_lead(
    email="john@example.com",
    campaign_id="camp-123",
    first_name="John",
    last_name="Doe"
)
```

**Status**: ✅ Implemented and tested

---

### 10. List Leads

**Method**: `POST`
**Path**: `/api/v2/leads/list`
**Description**: List leads with filtering and pagination

**Request Parameters**:
- `campaign` (string): Filter by campaign
- `list_id` (string): Filter by lead list
- `search` (string): Search by email or name
- `limit` (int, 1-100): Maximum leads to return
- `starting_after` (string): Pagination cursor

**Example Request**:
```python
leads = await client.list_leads(
    campaign_id="camp-123",
    limit=50
)
```

**Status**: ✅ Implemented and tested

---

### 11. Get Lead

**Method**: `GET`
**Path**: `/api/v2/leads/{id}`
**Description**: Get single lead details

**Example Request**:
```python
lead = await client.get_lead("lead-123")
```

**Status**: ✅ Implemented and tested

---

### 12. Update Lead

**Method**: `PATCH`
**Path**: `/api/v2/leads/{id}`
**Description**: Update lead fields

**Example Request**:
```python
lead = await client.update_lead(
    lead_id="lead-123",
    first_name="Johnny"
)
```

**Status**: ✅ Implemented and tested

---

### 13. Delete Lead

**Method**: `DELETE`
**Path**: `/api/v2/leads/{id}`
**Description**: Delete a lead

**Example Request**:
```python
success = await client.delete_lead("lead-123")
```

**Status**: ✅ Implemented and tested

---

### 14. Bulk Add Leads

**Method**: `POST`
**Path**: `/api/v2/leads/add`
**Description**: Bulk add up to 1000 leads at once

**Request Parameters**:
- `leads` (array, required): List of lead data (max 1000)
- `campaign` (string): Campaign ID
- `list_id` (string): Lead list ID

**Response Schema**:
```json
{
  "created_count": 3,
  "updated_count": 0,
  "failed_count": 0,
  "created_leads": ["lead-1", "lead-2", "lead-3"],
  "failed_leads": []
}
```

**Example Request**:
```python
result = await client.bulk_add_leads(
    leads=[
        {"email": "john@example.com", "first_name": "John"},
        {"email": "jane@example.com", "first_name": "Jane"}
    ],
    campaign_id="camp-123"
)
```

**Status**: ✅ Implemented and tested

---

### 15. Update Lead Interest Status

**Method**: `POST`
**Path**: `/api/v2/leads/update-interest-status`
**Description**: Update lead's interest status

**Request Parameters**:
- `lead_email` (string, required): Lead's email
- `interest_value` (string, required): Interest status value

**Interest Status Values**:
- `interested`
- `not_interested`
- `meeting_booked`
- `meeting_completed`
- `closed`
- `out_of_office`
- `wrong_person`

**Example Request**:
```python
job = await client.update_lead_interest_status(
    lead_email="john@example.com",
    interest_status=LeadInterestStatus.MEETING_BOOKED
)
```

**Status**: ✅ Implemented and tested

---

### 16. Move Leads

**Method**: `POST`
**Path**: `/api/v2/leads/move`
**Description**: Move leads between campaigns/lists

**Request Parameters**:
- `lead_ids` (array, required): List of lead UUIDs
- `destination_campaign` (string): Target campaign
- `destination_list_id` (string): Target list

**Example Request**:
```python
job = await client.move_leads(
    lead_ids=["lead-1", "lead-2"],
    destination_campaign_id="camp-456"
)
```

**Status**: ✅ Implemented and tested

---

## Analytics Endpoints

### 17. Get Campaign Analytics

**Method**: `GET`
**Path**: `/api/v2/campaigns/analytics`
**Description**: Get campaign performance metrics

**Query Parameters**:
- `id` (string): Specific campaign ID (optional)

**Response Schema**:
```json
{
  "total_leads": 100,
  "contacted": 80,
  "emails_sent": 200,
  "emails_opened": 50,
  "emails_clicked": 20,
  "emails_replied": 10,
  "emails_bounced": 5,
  "unsubscribed": 2
}
```

**Example Request**:
```python
analytics = await client.get_campaign_analytics("camp-123")
print(f"Open rate: {analytics.open_rate}%")
print(f"Reply rate: {analytics.reply_rate}%")
```

**Status**: ✅ Implemented and tested

---

### 18. Get Campaign Analytics Overview

**Method**: `GET`
**Path**: `/api/v2/campaigns/analytics/overview`
**Description**: Get high-level analytics summary

**Example Request**:
```python
overview = await client.get_campaign_analytics_overview()
```

**Status**: ✅ Implemented and tested

---

### 19. Get Daily Campaign Analytics

**Method**: `GET`
**Path**: `/api/v2/campaigns/analytics/daily`
**Description**: Get daily time-series analytics

**Query Parameters**:
- `campaign_id` (string): Specific campaign
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)

**Example Request**:
```python
daily_data = await client.get_campaign_daily_analytics(
    campaign_id="camp-123",
    start_date="2025-01-01",
    end_date="2025-01-31"
)
```

**Status**: ✅ Implemented and tested

---

## Campaign Status Codes

| Status | Value | Description |
|--------|-------|-------------|
| `DRAFT` | 0 | Campaign created but not started |
| `ACTIVE` | 1 | Campaign actively sending |
| `PAUSED` | 2 | Campaign paused |
| `COMPLETED` | 3 | Campaign finished |
| `RUNNING_SUBSEQUENCES` | 4 | Running follow-up sequences |
| `ACCOUNT_SUSPENDED` | -99 | Account suspended |
| `ACCOUNTS_UNHEALTHY` | -1 | Email accounts unhealthy |
| `BOUNCE_PROTECT` | -2 | Bounce protection active |

---

## Error Codes

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| `400` | Bad Request | Invalid parameters |
| `401` | Unauthorized | Invalid or missing API key |
| `402` | Payment Required | Subscription required for API V2 |
| `403` | Forbidden | Access denied |
| `404` | Not Found | Resource not found |
| `429` | Rate Limited | Too many requests |
| `500` | Server Error | Internal server error |

---

## Future-Proof Design

The client supports calling new endpoints dynamically:

```python
# Call any new endpoint without code changes
result = await client.call_endpoint(
    "/v2/new-endpoint",
    method="POST",
    json={"param": "value"}
)
```

---

## Testing

- **Test file**: `__tests__/unit/integrations/test_instantly.py`
- **Test count**: 70 tests
- **Coverage**: ~80%
- **Pass rate**: 100%

All endpoints are tested with mocked responses covering:
- Success scenarios
- Error scenarios
- Parameter validation
- Dataclass properties
