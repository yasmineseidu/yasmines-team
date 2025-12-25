# Task: Lead Research Agent (Agent 4.2)

**Status:** Pending
**Domain:** backend
**Phase:** 4 - Research & Personalization
**Source:** cold-email-agents/agents/phase4/agent_4_2_lead_research.yaml
**Created:** 2025-12-23
**Depends On:** Task 013

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

Individual lead research. LinkedIn posts/activity, articles, podcasts, talks. Generate opening lines.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/lead_research/agent.py`
- `app/backend/src/agents/lead_research/linkedin_scraper.py`
- `app/backend/__tests__/unit/agents/test_lead_research_agent.py`
- `docs/api/lead-research-agent.yaml`

---

## Implementation Checklist

- [ ] LinkedIn posts (recent activity)
- [ ] Articles published
- [ ] Podcast appearances
- [ ] Conference talks
- [ ] Opening line generation (personalized)
- [ ] Store in lead_research table

---

## Output

```json
{
  "leads_researched": 10000,
  "opening_lines_generated": 9500,
  "research_sources": {
    "linkedin_posts": 5000,
    "articles": 2500,
    "podcasts": 1200,
    "talks": 800
  }
}
```
