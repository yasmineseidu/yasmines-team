# Task: Company Research Agent (Agent 4.1)

**Status:** Pending
**Domain:** backend
**Phase:** 4 - Research & Personalization
**Source:** cold-email-agents/agents/phase4/agent_4_1_company_research.yaml
**Created:** 2025-12-23
**Depends On:** Task 012 (Human Gate Approval)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse WebSearch, WebFetch, Brave, Exa integrations
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

Deep research on target companies. Recent news, funding, hiring signals. Generate personalization hooks. Parallel research on 20+ companies.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/company_research/agent.py`
- `app/backend/src/agents/company_research/researchers.py`
- `app/backend/__tests__/unit/agents/test_company_research_agent.py`
- `docs/api/company-research-agent.yaml`

---

## Implementation Checklist

- [ ] Recent news (last 3-6 months)
- [ ] Funding announcements
- [ ] Hiring signals (job postings)
- [ ] Growth metrics
- [ ] Personalization hook generation
- [ ] Parallel processing (20+ companies)
- [ ] Store in company_research table

---

## Output

```json
{
  "companies_researched": 1500,
  "personalization_hooks": {
    "funding": 150,
    "hiring": 320,
    "news": 450,
    "growth": 200
  }
}
```
