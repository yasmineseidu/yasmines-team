# Task: Implement Lead List Builder Agent (2.1)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_1_lead_list_builder.yaml
**Created:** 2025-12-25
**Priority:** High - First agent in Phase 2 pipeline

## Summary

Implement the Lead List Builder Agent that scrapes 50K+ leads using Apify Leads Finder actor. This agent orchestrates parallel scraping jobs, streams results to the database, and tracks costs/progress.

## Files to Create/Modify

- [ ] `src/agents/lead_list_builder/agent.py` - Main agent class
- [ ] `src/agents/lead_list_builder/__init__.py` - Module exports
- [ ] `src/agents/lead_list_builder/tools.py` - Apify integration tools
- [ ] `src/agents/lead_list_builder/schemas.py` - Input/output schemas
- [ ] `src/integrations/apify/leads_finder.py` - Apify Leads Finder client
- [ ] `__tests__/unit/agents/lead_list_builder/test_agent.py` - Unit tests
- [ ] `__tests__/integration/agents/test_lead_list_builder.py` - Integration tests

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `LeadListBuilderAgent` class using Claude Agent SDK
- [ ] Implement agent initialization with Apify credentials
- [ ] Create `build_search_criteria` tool - construct Apify input from niche/personas
- [ ] Create `validate_scraping_feasibility` tool - check niche research data
- [ ] Create `launch_apify_runs` tool - start parallel Apify actor runs
- [ ] Create `stream_results` tool - stream results to database in batches
- [ ] Create `finalize_import` tool - complete import with summary

### Apify Integration (src/integrations/apify/)
- [ ] Create `ApifyLeadsFinderClient` class
- [ ] Implement async polling for results (check every 5 minutes)
- [ ] Implement chunked result fetching (1000 leads per chunk)
- [ ] Implement rate limiting (500ms pause between chunks)
- [ ] Add circuit breaker for actor failures
- [ ] Implement retry logic with exponential backoff

### Database Operations
- [ ] Implement campaign creation on start
- [ ] Implement bulk lead insertion (batch size 500, parallel batches 5)
- [ ] Implement campaign finalization on complete
- [ ] Handle duplicate linkedin_url conflicts (DO_NOTHING)

### Parallel Execution
- [ ] Implement search criteria splitting (geographic, company size, seniority)
- [ ] Support up to 10 concurrent Apify actor runs
- [ ] Implement checkpoint/resume capability
- [ ] Save Apify run IDs for resume

### Cost Controls
- [ ] Track cost per lead ($0.0015 = $1.50/1000)
- [ ] Enforce max budget per campaign ($500 default)
- [ ] Alert at 80% budget usage
- [ ] Stop gracefully when budget exceeded

### Error Handling
- [ ] Handle `ApifyActorFailedError` with retry
- [ ] Handle `InsufficientCreditsError` with fail
- [ ] Handle partial results on timeout
- [ ] Implement circuit breaker (3 failures = open)

## LEARN References

- LEARN-002: Use tuple syntax for tenacity retry `(Error1, Error2)`
- LEARN-003: Create Apify client inside @tool function, not via DI
- LEARN-005: Use natural language for WebSearch, not `site:` operators

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/lead_list_builder/ -v

# Run integration tests (requires Apify API key)
pytest __tests__/integration/agents/test_lead_list_builder.py -v --run-integration

# Test with mock Apify
pytest __tests__/unit/agents/lead_list_builder/ -v -k "mock"
```

## Handoff

When complete, this agent hands off to Data Validation Agent (2.2) with:
- `campaign_id`: UUID of created campaign
- `total_leads`: Number of leads inserted

Handoff condition: `total_inserted >= 1000` (configurable via Phase2Config)

## Notes

- Apify Leads Finder actor ID: `IoSHqwTR9YGhzccez`
- Actor URL: https://console.apify.com/actors/IoSHqwTR9YGhzccez/input
- Results are NOT instant - async polling required
- Free plan limited to 100 leads per run
