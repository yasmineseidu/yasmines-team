# Task: Research Export Agent (Agent 1.3)

**Status:** Pending
**Domain:** backend
**Phase:** 1 - Market Intelligence
**Source:** cold-email-agents/agents/phase1/agent_1_3_research_export.yaml
**Created:** 2025-12-23
**Depends On:** Task 002

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
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings (CRITICAL for Drive/Docs)

- [ ] Agent MUST use Python Claude Agent SDK patterns
- [ ] Reuse Google Drive/Docs integrations from `app/backend/src/integrations/google_drive/` and `google_docs/`
- [ ] For Google services: use JSON credentials from .env (NOT client_id/client_secret)
- [ ] Create Swagger documentation in `docs/api/`
- [ ] All tests: unit >90%, integration live API with .env keys
- [ ] Code quality: ruff, mypy strict, pre-commit pass
- [ ] Run claude-sdk-reviewer and get approval

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Google Drive/Docs API authentication
  - [ ] JSON credential loading
  - [ ] Google API quota limits
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Include: error description, root cause, fix applied, code snippet
  - [ ] Format: `## [Agent Name] - [Error Description]`
  - [ ] This helps future agents avoid the same issues

---

## Summary

Implement Research Export Agent - compiles niche and persona research into formatted Google Docs for human review. Creates folder with 4 documents: Niche Overview, Persona Profiles, Pain Points Analysis, Messaging Angles.

**Triggers:** Human Gate for approval before Phase 2.

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/research_export/agent.py`
- `app/backend/src/agents/research_export/docs_builder.py`
- `app/backend/src/agents/research_export/templates.py`
- `app/backend/__tests__/unit/agents/test_research_export_agent.py`
- `app/backend/__tests__/integration/agents/test_research_export_agent_live.py`
- `docs/api/research-export-agent.yaml`

### Existing to Reuse
- `app/backend/src/integrations/google_drive/` - Check and reuse
- `app/backend/src/integrations/google_docs/` - Check and reuse

---

## Implementation Checklist

- [ ] Database READ: Load from `niche_research_data` table (competitors_found, differentiation_opportunities, pain_points_detailed, etc.)
- [ ] Create Google Drive folder structure
- [ ] Create 4 documents with Jinja2 templates:
  - Niche Overview (includes market size, competitors, differentiation opportunities)
  - Persona Profiles (from personas table)
  - Pain Points Analysis (includes detailed pain points with quotes from both tables)
  - Messaging Angles (includes differentiation opportunities from research)
- [ ] Update niche with research_folder_url
- [ ] Send Slack notification (optional)
- [ ] Human gate: approve/reject/request_revision
- [ ] Auto-approve if score >=85, confidence >=90%, personas >=2

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_research_export_agent.py -v --cov=app/backend/src/agents/research_export --cov-report=term-missing
ruff check app/backend/src/agents/research_export/
mypy app/backend/src/agents/research_export/ --strict
pytest app/backend/__tests__/integration/agents/test_research_export_agent_live.py -v -s
```

---

## Output

```json
{
  "folder_url": "https://drive.google.com/...",
  "documents": [{"name": "1. Niche Overview", "url": "..."}, ...],
  "notification_sent": true
}
```
