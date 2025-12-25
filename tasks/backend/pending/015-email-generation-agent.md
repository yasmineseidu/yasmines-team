# Task: Email Generation Agent (Agent 4.3)

**Status:** Pending
**Domain:** backend
**Phase:** 4 - Research & Personalization
**Source:** cold-email-agents/agents/phase4/agent_4_3_email_generation.yaml
**Created:** 2025-12-23
**Depends On:** Task 014

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse integrations
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

Generate personalized cold emails using frameworks (PAS, BAB, AIDA). Tier-based personalization depth. Quality scoring 0-100. Regenerate low-quality emails.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/email_generation/agent.py`
- `app/backend/src/agents/email_generation/frameworks.py`
- `app/backend/src/agents/email_generation/scorers.py`
- `app/backend/__tests__/unit/agents/test_email_generation_agent.py`
- `docs/api/email-generation-agent.yaml`

---

## Implementation Checklist

- [ ] Email frameworks: PAS, BAB, AIDA
- [ ] Tier A: Full personalization (company + lead research)
- [ ] Tier B: Standard personalization (company research)
- [ ] Tier C: Basic personalization (industry only)
- [ ] Quality scoring: relevance, personalization, tone
- [ ] Regenerate if score < 60
- [ ] Store in generated_emails table

---

## Output

```json
{
  "emails_generated": 32100,
  "quality_distribution": {
    "high (80-100)": 18500,
    "medium (60-79)": 11200,
    "low (0-59)": 2400
  },
  "regenerated": 2400,
  "final_average_quality": 76.5
}
```
