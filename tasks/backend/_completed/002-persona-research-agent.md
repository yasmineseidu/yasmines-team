# Task: Persona Research Agent (Agent 1.2)

**Status:** Pending
**Domain:** backend
**Phase:** 1 - Market Intelligence
**Source:** cold-email-agents/agents/phase1/agent_1_2_persona_research.yaml
**Created:** 2025-12-23
**Depends On:** Task 001

---

## MUST-DO CHECKLIST (Complete before marking task done)

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md` - File locations and task flow
  - [ ] `CODE_QUALITY_RULES.md` - Linting, formatting, naming standards
  - [ ] `TESTING_RULES.md` - Test structure and coverage (>90% tools, >85% agents)
  - [ ] `PROJECT_CONTEXT.md` - Architecture and tech stack
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Agent MUST use Python Claude Agent SDK patterns
- [ ] Reuse existing tools from `app/backend/src/integrations/`
- [ ] Create Swagger documentation in `docs/api/`
- [ ] All tests: unit >90%, integration live API with .env keys
- [ ] Code quality: ruff, mypy strict, pre-commit pass
- [ ] Run claude-sdk-reviewer and get approval

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Reddit API integration and rate limits
  - [ ] LinkedIn scraping patterns
  - [ ] Parallel execution with Claude SDK
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Include: error description, root cause, fix applied, code snippet
  - [ ] Format: `## [Agent Name] - [Error Description]`
  - [ ] This helps future agents avoid the same issues

---

## Summary

Implement Persona Research Agent - deep-dives into target personas using Reddit mining (PRIORITY), LinkedIn scraping, and industry content analysis.

**Key:** Reddit is GOLD - extract EXACT quotes with emotional language.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/persona_research/agent.py`
- `app/backend/src/agents/persona_research/tools.py`
- `app/backend/src/agents/persona_research/reddit_miner.py`
- `app/backend/src/agents/persona_research/schemas.py`
- `app/backend/__tests__/unit/agents/test_persona_research_agent.py`
- `app/backend/__tests__/integration/agents/test_persona_research_agent_live.py`
- `app/backend/__tests__/fixtures/persona_research_fixtures.py`
- `docs/api/persona-research-agent.yaml`

---

## Implementation Checklist

- [ ] Database READ: Load from `niche_research_data` table (competitors_found, pain_points_detailed, differentiation_opportunities, etc.)
- [ ] Reddit deep dive: pain points, language patterns, quotes by engagement
- [ ] LinkedIn research: profiles, posts, thought leadership
- [ ] Industry content: reports, surveys, KPIs, buying behavior
- [ ] Persona synthesis: 2-3 personas with exact quotes
- [ ] Database WRITE: personas, persona_research_data, industry_fit_scores
- [ ] Reddit circuit breaker (strict rate limits)

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_persona_research_agent.py -v --cov=app/backend/src/agents/persona_research --cov-report=term-missing
ruff check app/backend/src/agents/persona_research/
mypy app/backend/src/agents/persona_research/ --strict
pytest app/backend/__tests__/integration/agents/test_persona_research_agent_live.py -v -s
```

---

## Output Schema

```json
{
  "persona_ids": ["uuid"],
  "personas": [{"name": "The Scaling VP", "job_titles": [...], "pain_points": [...], "language_patterns": [...], "messaging_angles": {...}}],
  "consolidated_pain_points": [...],
  "industry_scores": [...]
}
```
