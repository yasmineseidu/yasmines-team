# Task: Email Verification Agent (Agent 3.1)

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** cold-email-agents/agents/phase3/agent_3_1_email_verification.yaml
**Created:** 2025-12-23
**Depends On:** Task 009 (Human Gate Approval)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Check `app/backend/src/integrations/` for: Tomba, Hunter, Findymail, Apollo, Reoon - REUSE if exists
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API with .env keys
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Email finder APIs (Tomba, Hunter, Findymail, Apollo)
  - [ ] Email verification APIs (Reoon)
  - [ ] Waterfall pattern with fallback
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Find and verify emails via waterfall: Tomba → Hunter → Findymail → Apollo (cheapest first). Verification via Reoon. Track costs per provider.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/email_verification/agent.py`
- `app/backend/src/agents/email_verification/waterfall.py`
- `app/backend/src/agents/email_verification/providers.py`
- `app/backend/__tests__/unit/agents/test_email_verification_agent.py`
- `docs/api/email-verification-agent.yaml`

### Check Existing Integrations
- Look in `app/backend/src/integrations/` for: tomba, hunter, findymail, apollo, reoon

---

## Implementation Checklist

- [ ] Check/create email finder integrations (Tomba, Hunter, Findymail, Apollo)
- [ ] Check/create email verifier integration (Reoon)
- [ ] Waterfall: try cheapest first, fallback to next
- [ ] Per-lead cost tracking
- [ ] Verify found emails (deliverable, risky, invalid)
- [ ] Update leads table with email and verification status
- [ ] Parallel processing for tier A/B leads first

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_email_verification_agent.py -v --cov=app/backend/src/agents/email_verification --cov-report=term-missing
ruff check app/backend/src/agents/email_verification/
mypy app/backend/src/agents/email_verification/ --strict
```

---

## Output

```json
{
  "total_processed": 42100,
  "emails_found": 38500,
  "emails_verified": {
    "deliverable": 32100,
    "risky": 4200,
    "invalid": 2200
  },
  "total_cost": 1150.50,
  "cost_by_provider": {...}
}
```
