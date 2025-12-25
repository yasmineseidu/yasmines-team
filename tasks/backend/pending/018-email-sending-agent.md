# Task: Email Sending Agent (Agent 5.2)

**Status:** Pending
**Domain:** backend
**Phase:** 5 - Campaign Execution
**Source:** cold-email-agents/agents/phase5/agent_5_2_email_sending.yaml
**Created:** 2025-12-23
**Depends On:** Task 017

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse Instantly.ai integration
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Instantly.ai bulk upload operations
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Upload leads to Instantly.ai and manage sending. Tier-prioritized sending (A first, then B, then C). Track sending status.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/email_sending/agent.py`
- `app/backend/src/agents/email_sending/uploader.py`
- `app/backend/__tests__/unit/agents/test_email_sending_agent.py`
- `docs/api/email-sending-agent.yaml`

### Reuse Existing
- `app/backend/src/integrations/instantly.py`

---

## Implementation Checklist

- [ ] Batch upload leads to Instantly (max 1000 per batch)
- [ ] Tier priority: upload A first, then B, then C
- [ ] Map generated emails to Instantly leads
- [ ] Track upload status
- [ ] Monitor sending progress
- [ ] Update leads table with instantly_lead_id
- [ ] Handle upload errors and retries

---

## Output

```json
{
  "campaign_id": "uuid",
  "leads_uploaded": 32100,
  "upload_batches": 32,
  "tier_breakdown": {
    "A": 8500,
    "B": 15200,
    "C": 8400
  },
  "sending_started": true
}
```
