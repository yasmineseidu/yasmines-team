# Task: Niche Research Agent (Agent 1.1)

**Status:** Pending
**Domain:** backend
**Phase:** 1 - Market Intelligence
**Source:** cold-email-agents/agents/phase1/agent_1_1_niche_research.yaml
**Created:** 2025-12-23

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
  - [ ] Tool integrations (brave, exa, reddit, etc.)
  - [ ] Parallel execution patterns
  - [ ] Claude Agent SDK patterns
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Include: error description, root cause, fix applied, code snippet
  - [ ] Format: `## [Agent Name] - [Error Description]`
  - [ ] This helps future agents avoid the same issues

---

## Summary

Implement Niche Research Agent - analyzes market viability using multi-source parallel research with tool priority tiers (FREE → CHEAP → MODERATE → EXPENSIVE).

**Tool Priority:**
1. FREE: claude_web_search, claude_web_fetch, reddit_api
2. CHEAP: tavily_search, brave_search, serper_search (~$0.001/call)
3. MODERATE: perplexity_search (~$0.005/call)
4. EXPENSIVE: exa_search (~$0.01/call)

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/niche_research/agent.py`
- `app/backend/src/agents/niche_research/tools.py`
- `app/backend/src/agents/niche_research/schemas.py`
- `app/backend/src/agents/niche_research/prompts.py`
- `app/backend/__tests__/unit/agents/test_niche_research_agent.py`
- `app/backend/__tests__/integration/agents/test_niche_research_agent_live.py`
- `app/backend/__tests__/fixtures/niche_research_fixtures.py`
- `docs/api/niche-research-agent.yaml`

### Existing to Check/Extend
- `app/backend/src/integrations/brave.py`
- `app/backend/src/integrations/exa.py`
- `app/backend/src/integrations/firecrawl.py`

---

## Implementation Checklist

- [ ] Tool discovery at startup with availability cache
- [ ] Parallel search execution (asyncio.gather)
- [ ] Research steps: Market Size, Competition, Reachability, Pain Points, Budget Authority
- [ ] Scoring: 0-100 per dimension (Market 20%, Competition 20%, Reachability 20%, Pain 25%, Budget 15%)
- [ ] Database: niches, niche_scores, niche_research_data tables
- [ ] Write full research findings to `niche_research_data` table (ALL step outputs)
- [ ] Retry with exponential backoff + jitter
- [ ] Per-tool circuit breakers

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_niche_research_agent.py -v --cov=app/backend/src/agents/niche_research --cov-report=term-missing
ruff check app/backend/src/agents/niche_research/
mypy app/backend/src/agents/niche_research/ --strict
pytest app/backend/__tests__/integration/agents/test_niche_research_agent_live.py -v -s
pre-commit run --all-files
```

---

## Output Schema

```json
{
  "niche_id": "uuid",
  "overall_score": 78,
  "scores": {"market_size": 80, "competition": 75, "reachability": 70, "pain_intensity": 85, "budget_authority": 72},
  "recommendation": "proceed|review|reject",
  "confidence": 0.85,
  "discovered_pain_points": [...],
  "sources_used": [...]
}
```
