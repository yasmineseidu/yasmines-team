# Task: Implement Cross-Campaign Dedup Agent (2.4)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_4_cross_campaign_dedup.yaml
**Created:** 2025-12-25
**Priority:** High - Fourth agent in Phase 2 pipeline

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns
- [ ] Review database repositories for existing query patterns
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Cross-dataset matching patterns
  - [ ] Exclusion rule logic
  - [ ] Historical contact tracking
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Implement the Cross-Campaign Dedup Agent that checks new leads against all historical campaigns to identify people who have already been contacted. Respects exclusion rules (recent contact, unsubscribed, bounced) and prevents contact fatigue.

## Files to Create/Modify

- [ ] `src/agents/cross_campaign_dedup/agent.py` - Main agent class
- [ ] `src/agents/cross_campaign_dedup/__init__.py` - Module exports
- [ ] `src/agents/cross_campaign_dedup/tools.py` - Detection tools
- [ ] `src/agents/cross_campaign_dedup/schemas.py` - Input/output schemas
- [ ] `src/agents/cross_campaign_dedup/exclusions.py` - Exclusion rule logic
- [ ] `__tests__/unit/agents/cross_campaign_dedup/test_agent.py` - Unit tests
- [ ] `__tests__/unit/agents/cross_campaign_dedup/test_exclusions.py` - Exclusion tests

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `CrossCampaignDedupAgent` class using Claude Agent SDK
- [ ] Implement `load_data` tool - load new leads, historical, exclusions in parallel
- [ ] Implement `match_historical` tool - match against historical campaigns
- [ ] Implement `apply_exclusions` tool - apply exclusion rules
- [ ] Implement `update_records` tool - mark excluded leads

### Exclusion Rules (src/agents/cross_campaign_dedup/exclusions.py)
- [ ] `check_recently_contacted()` - within lookback_days (default 90)
- [ ] `check_bounced()` - email_status in ['bounced', 'invalid']
- [ ] `check_unsubscribed()` - email_status in ['unsubscribed', 'complained', 'spam_reported']
- [ ] `check_suppression_list()` - global do-not-contact list
- [ ] `apply_all_exclusions()` - apply all rules, return exclusions by reason

### Historical Matching
- [ ] Primary match: linkedin_url (exact, case-insensitive)
- [ ] Secondary match: email (exact, case-insensitive)
- [ ] Fallback match: name + company (90% fuzzy threshold)
- [ ] Partition by email domain for parallel execution (20 partitions)

### Database Operations
- [ ] Load new campaign leads (status NOT IN ['duplicate', 'invalid'])
- [ ] Load historical leads (contacted recently OR bounced/unsubscribed)
- [ ] Load global suppression list
- [ ] Mark excluded leads: `status = 'cross_campaign_duplicate'`
- [ ] Set `exclusion_reason` and `excluded_due_to_campaign`
- [ ] Log to `cross_campaign_dedup_logs` table
- [ ] Update campaign stats

### SQL Query for Historical Contacts

```sql
SELECT id, campaign_id, linkedin_url, email, first_name, last_name,
       company_name, company_domain, email_status, last_contacted_at
FROM leads
WHERE campaign_id != :campaign_id
  AND status NOT IN ('duplicate', 'invalid')
  AND (
    last_contacted_at > NOW() - INTERVAL :lookback_days days
    OR email_status IN ('bounced', 'unsubscribed', 'complained')
  )
```

Note: Use `make_interval(days => :lookback_days)` for parameterized interval.

### Parallel Execution
- [ ] Load all data sources in parallel
- [ ] Partition matching by email domain
- [ ] 20 parallel partitions for matching
- [ ] Batch updates by 5000 leads

## Exclusion Reasons

| Reason | Description |
|--------|-------------|
| `contacted_recently` | Last contacted within lookback_days |
| `email_bounced` | Email previously bounced |
| `unsubscribed` | Contact unsubscribed from emails |
| `suppression_list` | On global do-not-contact list |

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/cross_campaign_dedup/ -v

# Test exclusion rules
pytest __tests__/unit/agents/cross_campaign_dedup/test_exclusions.py -v
```

## Handoff

When complete, this agent hands off to Lead Scoring Agent (2.5) with:
- `campaign_id`: Campaign UUID
- `available_leads`: Count of leads remaining after exclusions

Handoff condition: `remaining_leads >= 1000` (configurable)

## Success Criteria

- Hard: `total_checked == inputs.unique_leads`
- Hard: `remaining_leads >= 1000`
- Soft: `exclusion_rate < 0.30` (less than 30% excluded)

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 90 | Don't contact if contacted within this many days |
| `exclude_bounced` | bool | true | Exclude previously bounced emails |
| `exclude_unsubscribed` | bool | true | Exclude unsubscribed contacts |

## Notes

- Uses `LeadRepository.check_historical_contacts()` method
- Uses `LeadRepository.get_suppression_list()` method
- Uses `LeadRepository.bulk_mark_cross_duplicates()` for updates
- Uses `CampaignRepository.create_cross_campaign_dedup_log()` for logging
