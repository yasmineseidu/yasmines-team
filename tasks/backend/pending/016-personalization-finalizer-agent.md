# Task: Personalization Finalizer Agent (Agent 4.4)

**Status:** Pending
**Domain:** backend
**Phase:** 4 - Research & Personalization
**Source:** cold-email-agents/agents/phase4/agent_4_4_personalization_finalizer.yaml
**Created:** 2025-12-23
**Depends On:** Task 015

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse Google Sheets, Drive integrations
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Google Docs API with JSON credentials
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Finalize emails, export samples to Google Docs. Update campaign. Trigger Human Gate before Phase 5.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/personalization_finalizer/agent.py`
- `app/backend/src/agents/personalization_finalizer/exporter.py`
- `app/backend/__tests__/unit/agents/test_personalization_finalizer_agent.py`
- `docs/api/personalization-finalizer-agent.yaml`

---

## Implementation Checklist

- [ ] Export email samples to Google Docs
- [ ] Samples by tier and quality
- [ ] Update campaigns table
- [ ] Set status: "pending_campaign_approval"
- [ ] Human gate: approve/reject
- [ ] Slack notification

---

## Output

```json
{
  "campaign_id": "uuid",
  "final_emails": 32100,
  "docs_url": "https://docs.google.com/...",
  "samples_by_tier": {
    "A": 10,
    "B": 10,
    "C": 5
  },
  "notification_sent": true
}
```
