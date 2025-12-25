# Task: Email Verification Agent (Agent 3.1)

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** cold-email-agents/agents/phase3/agent_3_1_email_verification.yaml
**Created:** 2025-12-23
**Updated:** 2025-12-25
**Depends On:** Task 009 (Import Finalizer / Human Gate Approval)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns (ClaudeSDKClient for orchestration)
- [ ] Check `app/backend/src/integrations/` for existing providers - REUSE if exists
- [ ] Tests: unit >90%, integration live API with .env keys
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Email finder APIs (Tomba, Muraena, Voila Norbert, Nimbler, Icypeas, Anymailfinder, Findymail)
  - [ ] Email verification APIs (Reoon, MailVerify)
  - [ ] Waterfall pattern with fallback
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`

---

## Summary

Find and verify emails via waterfall pattern (cheapest/fastest first). Verification via Reoon (primary) and MailVerify (catchall handler). Track costs per provider.

**Email Finder Waterfall (Priority Order):**
1. Tomba IO (primary, cheapest)
2. Muraena
3. Voila Norbert
4. Nimbler
5. Icypeas
6. Anymailfinder
7. Findymail (fallback)

**Email Verification:**
- Reoon (primary verifier)
- MailVerify (secondary + catchall specialist)

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/email_verification/agent.py` - Main agent class
- `app/backend/src/agents/email_verification/tools.py` - SDK tools for email finding/verification
- `app/backend/src/agents/email_verification/waterfall.py` - Waterfall logic (use `src/utils/search_waterfall.py` as reference)
- `app/backend/src/agents/email_verification/providers.py` - Provider registry
- `app/backend/__tests__/unit/agents/email_verification/test_agent.py`
- `app/backend/__tests__/unit/agents/email_verification/test_tools.py`
- `app/backend/__tests__/unit/agents/email_verification/test_waterfall.py`

### Existing Integrations to Use
Check `app/backend/src/integrations/` for:
- `tomba/` - Tomba IO email finder
- `muraena/` - Muraena email finder
- `voila_norbert/` - Voila Norbert email finder
- `nimbler/` - Nimbler email finder
- `icypeas/` - Icypeas email finder
- `anymailfinder/` - AnyMailFinder email finder
- `findymail/` - Findymail email finder (fallback)
- `reoon/` - Reoon email verifier
- `mailverify/` - MailVerify email verifier

### Repository APIs (Already Implemented)
Use these from `src/database/repositories/`:
- `LeadRepository.get_campaign_leads(campaign_id, needs_email=True, tier="A")` - Get leads needing emails
- `LeadRepository.update_email_verification()` - Update lead with email and status
- `CampaignRepository.update_email_verification_results()` - Update campaign metrics

---

## Implementation Checklist

### Phase 1: Setup & Integration Check
- [ ] Verify all 7 email finder integrations exist
- [ ] Verify both verification integrations exist (Reoon, MailVerify)
- [ ] Create provider registry with costs, rate limits, accuracy

### Phase 2: Waterfall Implementation
- [ ] Implement waterfall pattern from `search_waterfall.py`
- [ ] Start with Tomba (cheapest), fallback through tiers
- [ ] Circuit breaker per provider (use `src/agents/circuit_breaker.py`)
- [ ] Retry with exponential backoff (use `src/agents/retry_utils.py`)

### Phase 3: Email Finding
- [ ] Create `find_email` tool that runs waterfall
- [ ] Per-lead cost tracking
- [ ] Stop on first valid email found
- [ ] Log provider used for each successful find

### Phase 4: Email Verification
- [ ] Verify found emails with Reoon (primary)
- [ ] Handle catchall domains with MailVerify
- [ ] Return status: deliverable, risky, catchall, invalid
- [ ] Track verification costs separately

### Phase 5: Database Updates
- [ ] Update leads table with email and verification status
- [ ] Update campaign metrics via CampaignRepository
- [ ] Priority processing: Tier A first, then B, then C

### Phase 6: Testing
- [ ] Unit tests with mocked providers (>90% coverage)
- [ ] Integration tests with real API keys
- [ ] Waterfall fallback scenario tests
- [ ] Error handling and circuit breaker tests

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/email_verification/ -v --cov=app/backend/src/agents/email_verification --cov-report=term-missing
ruff check app/backend/src/agents/email_verification/
mypy app/backend/src/agents/email_verification/ --strict
```

---

## Output

```json
{
  "total_processed": 42100,
  "emails_found": 38500,
  "find_breakdown": {
    "tomba": 18000,
    "muraena": 8500,
    "voila_norbert": 5200,
    "nimbler": 3100,
    "icypeas": 2100,
    "anymailfinder": 1200,
    "findymail": 400
  },
  "emails_verified": {
    "deliverable": 32100,
    "risky": 4200,
    "catchall": 1500,
    "invalid": 700
  },
  "total_cost": 1150.50,
  "cost_by_provider": {
    "tomba": 36.00,
    "muraena": 102.00,
    "voila_norbert": 78.00,
    "nimbler": 62.00,
    "icypeas": 42.00,
    "anymailfinder": 36.00,
    "findymail": 16.00,
    "reoon": 650.00,
    "mailverify": 128.50
  }
}
```
