# Task: Waterfall Enrichment Agent (Agent 3.2)

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** cold-email-agents/agents/phase3/agent_3_2_waterfall_enrichment.yaml
**Created:** 2025-12-23
**Depends On:** Task 010

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Check `app/backend/src/integrations/` for Clearbit, Apollo, web search - REUSE
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

Enrich leads with company/contact data. Tier-based depth: A=full, B=standard, C=basic. Use web search for free enrichment, Clearbit/Apollo for paid.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/waterfall_enrichment/agent.py`
- `app/backend/src/agents/waterfall_enrichment/enrichers.py`
- `app/backend/__tests__/unit/agents/test_waterfall_enrichment_agent.py`
- `docs/api/waterfall-enrichment-agent.yaml`

### Check Existing
- `app/backend/src/integrations/` - Look for clearbit, apollo

---

## Implementation Checklist

- [ ] Tier A (full): company revenue, employee count, tech stack, funding, social links
- [ ] Tier B (standard): company description, industry, location, employee count range
- [ ] Tier C (basic): web search minimal data
- [ ] Free enrichment: WebSearch for company info
- [ ] Paid enrichment: Clearbit, Apollo (tier A/B only)
- [ ] Update leads table with enriched fields

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_waterfall_enrichment_agent.py -v --cov=app/backend/src/agents/waterfall_enrichment --cov-report=term-missing
ruff check app/backend/src/agents/waterfall_enrichment/
```

---

## Output

```json
{
  "total_enriched": 38500,
  "enrichment_by_tier": {
    "A": {"full": 8200, "partial": 300},
    "B": {"standard": 14800, "partial": 400},
    "C": {"basic": 12000, "partial": 800}
  },
  "total_cost": 450.00
}
```
