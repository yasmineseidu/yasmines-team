# Task: Phase 5.1 - Campaign Setup Agent

**Status:** Pending
**Domain:** backend
**Source:** `cold-email-agents/agents/phase5/agent_5_1_campaign_setup.yaml`
**Created:** 2025-12-27
**Phase:** 5 - Campaign Execution

## Summary

Implement the Campaign Setup Agent that sets up email campaigns in Instantly.ai including campaign creation, sequence configuration, sending schedule, and warmup settings. This agent receives approved campaigns from Phase 4 and prepares them for execution.

## Files to Create/Modify

- [ ] `app/backend/src/agents/campaign_setup/agent.py` - Main agent class
- [ ] `app/backend/src/agents/campaign_setup/tools.py` - Agent tools
- [ ] `app/backend/src/agents/campaign_setup/__init__.py` - Module exports
- [ ] `app/backend/__tests__/unit/agents/campaign_setup/test_agent.py` - Agent tests
- [ ] `app/backend/__tests__/unit/agents/campaign_setup/test_tools.py` - Tools tests
- [ ] `app/backend/__tests__/fixtures/campaign_setup_fixtures.py` - Test fixtures

## Implementation Checklist

### Agent Core
- [ ] Create `CampaignSetupAgent` class using Claude Agent SDK
- [ ] Implement system prompt from YAML spec
- [ ] Add circuit breaker for Instantly API (threshold: 3, recovery: 120s)
- [ ] Implement global circuit breaker (threshold: 5)
- [ ] Add cost controls with Slack alerts on budget exceeded

### Tools Implementation
- [ ] `validate_prerequisites` - Verify campaign approved, has leads, has sending accounts
- [ ] `create_instantly_campaign` - Create campaign in Instantly.ai
- [ ] `configure_sequence` - Set up 4-step email sequence
- [ ] `configure_warmup` - Configure warmup settings if enabled
- [ ] `finalize_setup` - Complete setup and prepare for handoff

### Database Operations
- [ ] Read from `campaigns` table (status = approved_for_sending)
- [ ] Read from `email_accounts` table (active accounts)
- [ ] Read lead counts from `leads` table
- [ ] Write to `instantly_campaigns` table
- [ ] Update `campaigns` table with instantly_campaign_id

### Error Handling
- [ ] Retry with exponential jitter (max 3 attempts, 5-60s delay)
- [ ] Provider override for Instantly API (max 5 attempts)
- [ ] Human-in-the-loop budget alerts via Slack

### Handoff
- [ ] Prepare handoff data for Email Sending Agent (5.2)
- [ ] Include: campaign_id, instantly_campaign_id, total_leads

## Verification

```bash
# Run unit tests
cd app/backend && python -m pytest __tests__/unit/agents/campaign_setup/ -v

# Check coverage
python -m pytest __tests__/unit/agents/campaign_setup/ --cov=src/agents/campaign_setup --cov-report=term-missing

# Verify >90% coverage for tools, >85% for agent
```

## Dependencies

- Instantly API integration (`src/integrations/instantly/`)
- Database connection (`src/database/connection.py`)
- Slack integration for alerts

## Notes

- Campaign config includes 4-step sequence: initial, followup_1, followup_2, breakup
- Schedule: Mon-Fri, 9am-5pm EST, respect recipient timezone
- Warmup: 14 days minimum, 20 daily limit, +2/day increase
