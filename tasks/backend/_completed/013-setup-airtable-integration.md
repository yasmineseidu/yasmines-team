# Task: Setup Airtable Database Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Airtable integration for database management, lead storage, and structured data. Central hub for storing leads, campaigns, and contact data.

## Files to Create/Modify

- [ ] `src/integrations/airtable.py` - Airtable client implementation
- [ ] `src/integrations/__init__.py` - Export Airtable client
- [ ] `tests/unit/integrations/test_airtable.py` - Unit tests
- [ ] `.env.example` - Add AIRTABLE_API_KEY, AIRTABLE_BASE_ID
- [ ] `docs/integrations/airtable-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Airtable client extending `BaseIntegrationClient`
- [ ] Implement record creation (leads, contacts, campaigns)
- [ ] Implement record retrieval and querying
- [ ] Implement record update
- [ ] Implement record deletion
- [ ] Implement table listing
- [ ] Implement field management
- [ ] Implement view management (filtered views)
- [ ] Implement attachment handling
- [ ] Implement batch operations (create/update multiple records)
- [ ] Implement filtering and sorting
- [ ] Add rate limiting (5 req/sec)
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Create schema definitions for:
  - Leads table
  - Contacts table
  - Campaigns table
  - Results tracking
- [ ] Integration with lead enrichment for data storage

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_airtable.py -v --cov=src/integrations/airtable --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_airtable.py --cov=src/integrations/airtable --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/airtable

# Test record creation
python -c "from src.integrations import AirtableClient; client = AirtableClient(...); record = client.create_record('Leads', {'Name': 'John Doe', 'Email': 'john@example.com'})"

# Query records
curl http://localhost:8000/integrations/airtable/tables/Leads/records?filterBy=Status%3Dactive
```

## Schema Design

### Leads Table
- Name (Text)
- Email (Email)
- Company (Text)
- Domain (Text)
- Source (Dropdown: Reddit, Serper, Tavily, etc.)
- Status (Dropdown: New, Contacted, Qualified, etc.)
- Found By (Dropdown: Anymailfinder, Findymail, etc.)
- Confidence Score (Number: 0-100)
- Created Date (Date)
- Last Updated (Date)
- Notes (Long Text)
- Linked to Contact

### Contacts Table
- Email (Email)
- First Name (Text)
- Last Name (Text)
- Title (Text)
- Company (Text)
- LinkedIn URL (URL)
- Phone (Phone)
- Verified (Checkbox)
- Data Quality Score (Number)
- Linked to Leads

### Campaigns Table
- Name (Text)
- Type (Dropdown: Email, LinkedIn, etc.)
- Status (Dropdown: Planning, Active, Completed)
- Platform (Dropdown: Instantly.ai, HeyReach, etc.)
- Start Date (Date)
- End Date (Date)
- Budget (Currency)
- Leads Target (Number)
- Contacts Reached (Number)
- Responses (Number)
- Conversion Rate (Percent)
- Linked to Leads

## Notes

- **Cost:** FREE for base tier, paid for higher usage
- **Rate Limit:** 5 req/sec
- **Setup:** Requires API key from Airtable account settings
- **Use Case:** Lead storage, campaign tracking, data management
- **Central Hub:** All enriched leads stored here
- **Phase:** Lead Generation & Data Management - CRITICAL
- **Integration:** Central data store for all integrations
