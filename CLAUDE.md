# Project Context & Configuration

## Critical: Read These Before Any Development Work

**These files contain project-specific rules, patterns, and conventions:**

1. **[.claude/context/TASK_RULES.md](.claude/context/TASK_RULES.md)** - Where code belongs and task workflow
2. **[.claude/context/CODE_QUALITY_RULES.md](.claude/context/CODE_QUALITY_RULES.md)** - Linting, formatting, naming standards
3. **[.claude/context/TESTING_RULES.md](.claude/context/TESTING_RULES.md)** - Test structure and coverage (>90% required)
4. **[.claude/context/PROJECT_CONTEXT.md](.claude/context/PROJECT_CONTEXT.md)** - Architecture and tech stack
5. **[.claude/context/SDK_PATTERNS.md](.claude/context/SDK_PATTERNS.md)** - Claude Agent SDK patterns
6. **[.claude/context/SELF-HEALING.md](.claude/context/SELF-HEALING.md)** - Mistakes to avoid, known solutions, setup references
7. **[.claude/context/GOOGLE_INTEGRATIONS_LEARNING.md](.claude/context/GOOGLE_INTEGRATIONS_LEARNING.md)** - Google Tasks & Contacts learnings log

**Read these BEFORE starting any task.** They prevent duplicate work and bugs.

---

## Project Overview

**Stack:** Python 3.10+ backend, Claude Agent SDK, FastAPI, PostgreSQL
**Domain:** Multi-agent team automation with 76+ planned agents
**Current Focus:** Google Workspace integrations (Calendar, Meet, Docs, Gmail, Drive, Tasks, Contacts)

---

## Quick Navigation

### Active Tasks
- `tasks/backend/pending/` - Queued work items
- `tasks/backend/_in-progress/` - Current work
- `tasks/backend/_completed/` - Completed tasks (with commit references)

### Specifications
- `specs/agents/` - Agent specifications
- `specs/integrations/` - Integration API specs
- `specs/database-schema/` - Database schemas

### Implementation
- `app/backend/integrations/` - API clients and services
- `app/backend/__tests__/unit/` - Unit tests
- `app/backend/__tests__/integration/` - Live API tests
- `app/backend/__tests__/fixtures/` - Test data and mocks

---

## Key Patterns

### Google API Domain-Wide Delegation

**Critical:** See `.claude/context/SELF-HEALING.md` (lines 7-196) for complete guide.

**Key rule:** When using domain-wide delegation, request **single broad scope**, not multiple scopes.

```python
# CORRECT
if delegated_user:
    scopes = ["https://www.googleapis.com/auth/calendar"]  # Single broad scope
else:
    scopes = self.DEFAULT_SCOPES  # Multiple scopes for service account
```

**Current Service Account:** `smarterteam@smarter-team.iam.gserviceaccount.com`
**Authorized Scopes:** See `.claude/context/SELF-HEALING.md` lines 264-278

---

## Quality Gates (Non-Negotiable)

- ✅ All context files read before starting work
- ✅ Unit test coverage >90% for tools
- ✅ Integration tests pass with LIVE API testing
- ✅ Code passes Ruff linting
- ✅ Code passes MyPy type checking
- ✅ Pre-commit hooks pass (no errors, no vulnerabilities)
- ✅ No .env or API keys in commits
- ✅ Only production code committed (no test files)

Test failures = BLOCKERS. Fix before proceeding.

---

## Development Workflow

### Task Execution
1. Pick task from `tasks/backend/pending/`
2. Move to `tasks/backend/_in-progress/`
3. Follow the checklist in the task file
4. All tests must pass
5. Pre-commit must pass
6. Commit to GitHub
7. Move task to `tasks/backend/_completed/`

### Context Usage
Every task starts with:
- [ ] Read `.claude/context/TASK_RULES.md`
- [ ] Read `.claude/context/CODE_QUALITY_RULES.md`
- [ ] Read `.claude/context/TESTING_RULES.md`
- [ ] Read `.claude/context/PROJECT_CONTEXT.md`
- [ ] Read `.claude/context/SDK_PATTERNS.md`

This is not optional.

---

## Active Integrations

### Implemented
- ✅ Google Calendar (full CRUD + events)
- ✅ Google Meet (space creation + delegation)
- ✅ Google Docs (read/write with delegation)

### In Progress
- 🔄 Google Tasks (`tasks/backend/pending/019-implement-google-tasks-integration.md`)
- 🔄 Google Contacts (`tasks/backend/pending/020-implement-google-contacts-integration.md`)

### Planned
- Google Gmail
- Google Drive
- Google Sheets
- Slack
- Microsoft Teams
- Zoom
- Cal.com
- Calendly

---

## Learning & Continuous Improvement

All mistakes and learnings are documented in:
- **`.claude/context/SELF-HEALING.md`** - Known Google API patterns, common errors, scope references
- **`.claude/context/GOOGLE_INTEGRATIONS_LEARNING.md`** - Specific learnings from Tasks & Contacts implementation

**When you encounter an error:**
1. Document it in the learning log
2. Capture the root cause
3. Record the fix applied
4. Next agent will benefit from this knowledge

---

## No Verbosity Rule

All documentation is:
- ✅ Concise and actionable
- ✅ Scannable (short lines, bullets)
- ✅ Problem → Solution focused
- ✅ Linked to actual code locations
- ❌ No fluff or explanation
- ❌ No "nice to know" information
- ❌ No philosophical discussion

This is for the next agent to learn efficiently.

---

## Commands

**Extract tasks from spec:**
```bash
/yasmine:extract-tasks specs/integrations/google_tasks_api.md
```

**View task details:**
```bash
cat tasks/backend/pending/019-implement-google-tasks-integration.md
```

**Run live API tests:**
```bash
pytest app/backend/__tests__/integration/google_tasks/ -v -s
```

**Check pre-commit:**
```bash
pre-commit run --all-files
```

**Commit and push:**
```bash
git add app/backend/integrations/google_tasks/
git add app/backend/__tests__/fixtures/google_tasks_fixtures.py
git status  # Verify .env not included
pre-commit run --all-files
git commit -m "feat(google-tasks): add complete Google Tasks API integration"
git push origin main
```

---

## Support

**Questions?** Check:
1. `.claude/context/` files (most answers there)
2. `.claude/context/SELF-HEALING.md` (known solutions)
3. Task files (detailed checklists)
4. Recent commits (how similar features were done)

---

**Last Updated:** 2025-12-23
**Context Files Version:** Current (all 7 files)
**Status:** Ready for Google Tasks & Contacts implementation
