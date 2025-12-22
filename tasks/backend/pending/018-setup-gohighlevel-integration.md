# Task: Setup GoHighLevel CRM Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** HIGH

## Summary

Implement GoHighLevel integration for unified CRM, funnel management, and marketing automation. Replaces multiple specialized tools (HubSpot, Salesforce, ActiveCampaign, Mailchimp) with a single all-in-one solution.

## Files to Create/Modify

- [ ] `src/integrations/gohighlevel.py` - GoHighLevel client implementation
- [ ] `src/integrations/__init__.py` - Export GoHighLevel client
- [ ] `tests/unit/integrations/test_gohighlevel.py` - Unit tests
- [ ] `.env.example` - Add GOHIGHLEVEL_API_KEY, GOHIGHLEVEL_LOCATION_ID
- [ ] `docs/integrations/gohighlevel-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create GoHighLevel client extending `BaseIntegrationClient`
- [ ] Implement contact creation/retrieval/update
- [ ] Implement lead management operations
- [ ] Implement pipeline and opportunity management
- [ ] Implement funnel creation and configuration
- [ ] Implement email campaign management
- [ ] Implement SMS campaign management
- [ ] Implement contact segmentation and tagging
- [ ] Add rate limiting (per API key quota)
- [ ] Implement location-based operations
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Document API key setup from GoHighLevel dashboard
- [ ] Create location and permission management

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_gohighlevel.py -v --cov=src/integrations/gohighlevel --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_gohighlevel.py --cov=src/integrations/gohighlevel --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/gohighlevel

# Test contact creation
python -c "from src.integrations import GoHighLevelClient; client = GoHighLevelClient(...); contact = client.create_contact('John Doe', 'john@example.com')"
```

## Notes

- **Cost:** $297-497/month (Agency Unlimited plan, includes all features)
- **Rate Limit:** Varies by plan (typically 100+ req/10sec)
- **Setup:** Requires API key and Location ID from GoHighLevel account
- **Replaces:** HubSpot, Salesforce, Pipedrive, ActiveCampaign, Mailchimp
- **Features:** Leads, contacts, pipelines, funnels, emails, SMS, automation
- **Phase:** Phase 2 (CRM & Communication - Week 3-4)
- **Integration:** Central hub for all lead and customer management
