# Task: Campaign Setup Agent (Agent 5.1)

**Status:** Pending
**Domain:** backend
**Phase:** 5 - Campaign Execution
**Source:** cold-email-agents/agents/phase5/agent_5_1_campaign_setup.yaml
**Created:** 2025-12-23
**Depends On:** Task 016 (Human Gate Approval)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Check `app/backend/src/integrations/` for Instantly.ai - create if missing
- [ ] For any integration: use JSON credentials for Google, API keys from .env
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API with .env keys
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Instantly.ai API integration
  - [ ] Campaign and sequence setup
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Set up campaigns in Instantly.ai. Create campaign, configure 4-step email sequence, set sending schedule, configure warmup.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/campaign_setup/agent.py`
- `app/backend/src/agents/campaign_setup/instantly_client.py`
- `app/backend/src/agents/campaign_setup/sequence_builder.py`
- `app/backend/__tests__/unit/agents/test_campaign_setup_agent.py`
- `app/backend/__tests__/integration/agents/test_campaign_setup_agent_live.py`
- `docs/api/campaign-setup-agent.yaml`

### Check or Create Integration
- `app/backend/src/integrations/instantly.py` - Create if doesn't exist

---

## Implementation Checklist

- [ ] Create Instantly.ai integration if not exists
- [ ] Create campaign in Instantly.ai
- [ ] Configure 4-step email sequence:
  - Step 1: Initial cold email (generated emails)
  - Step 2: Follow-up (2 days later)
  - Step 3: Second follow-up (4 days later)
  - Step 4: Break-up email (7 days later)
- [ ] Set sending schedule (business hours, timezone)
- [ ] Configure warmup settings
- [ ] Map Instantly campaign_id to internal campaign

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_campaign_setup_agent.py -v --cov=app/backend/src/agents/campaign_setup --cov-report=term-missing
ruff check app/backend/src/agents/campaign_setup/
mypy app/backend/src/agents/campaign_setup/ --strict
pytest app/backend/__tests__/integration/agents/test_campaign_setup_agent_live.py -v -s
```

---

## Output

```json
{
  "campaign_id": "uuid",
  "instantly_campaign_id": "inst_xxx",
  "instantly_campaign_url": "https://app.instantly.ai/campaigns/xxx",
  "sequence_configured": true,
  "warmup_configured": true
}
```
