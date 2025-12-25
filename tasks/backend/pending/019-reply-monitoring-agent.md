# Task: Reply Monitoring Agent (Agent 5.3)

**Status:** Pending
**Domain:** backend
**Phase:** 5 - Campaign Execution
**Source:** cold-email-agents/agents/phase5/agent_5_3_reply_monitoring.yaml
**Created:** 2025-12-23
**Depends On:** Task 018

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse Instantly.ai integration, Slack integration
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Monitor and categorize replies using AI. Detect: interested, not interested, OOO, auto-reply. Trigger actions: Slack notifications, CRM updates.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/reply_monitoring/agent.py`
- `app/backend/src/agents/reply_monitoring/classifier.py`
- `app/backend/src/agents/reply_monitoring/actions.py`
- `app/backend/__tests__/unit/agents/test_reply_monitoring_agent.py`
- `docs/api/reply-monitoring-agent.yaml`

---

## Implementation Checklist

- [ ] Poll Instantly.ai for replies (every 5 minutes)
- [ ] AI classify replies: interested, not interested, OOO, auto-reply, other
- [ ] Extract intent from interested replies
- [ ] Actions:
  - Interested: Slack notification to sales team, update lead status
  - Not interested: update lead status, track reason
  - OOO: schedule follow-up
  - Auto-reply: flag for review
- [ ] Store in replies table
- [ ] Generate reply analytics

---

## Output

```json
{
  "replies_processed": 2500,
  "classification": {
    "interested": 320,
    "not_interested": 1100,
    "ooo": 180,
    "auto_reply": 450,
    "other": 450
  },
  "actions_taken": {
    "slack_notifications": 320,
    "crm_updates": 2050
  }
}
```
