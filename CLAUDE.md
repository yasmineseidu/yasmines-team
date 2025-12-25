# Smarter Team

Multi-agent AI system that autonomously orchestrates end-to-end cold email marketing and lead generation with 76+ specialized agents across 5 phases: Market Intelligence → Lead Acquisition → Email Verification → Research & Personalization → Campaign Execution.

## Project Structure

```
app/backend/                         # Main FastAPI application
├── src/
│   ├── agents/                      # 76+ agent implementations
│   ├── integrations/                # 40+ third-party API clients
│   ├── api/                         # REST endpoints
│   ├── models/                      # SQLAlchemy ORM models
│   ├── database/                    # Alembic migrations (8 files)
│   ├── tasks/                       # Celery background tasks
│   └── config.py                    # Pydantic configuration
├── __tests__/
│   ├── unit/                        # Unit tests
│   └── integration/                 # Integration tests
├── pyproject.toml                   # Dependencies (Python 3.11+)
├── Makefile                         # Development commands
└── README.md                        # Backend documentation

cold-email-agents/                   # 5-phase agent YAML specifications
├── agents/
│   ├── phase1/                      # Niche Research & Persona Definition
│   ├── phase2/                      # Lead Discovery & List Building
│   ├── phase3/                      # Email Verification & Enrichment
│   ├── phase4/                      # Research & Personalization
│   └── phase5/                      # Campaign Execution & Analytics
└── infrastructure/                  # Shared retry logic

tasks/                               # Task tracking system
├── backend/
│   ├── pending/                     # Not started (22 agents waiting)
│   ├── _in-progress/                # Currently building
│   └── _completed/                  # Done (1 agent: Niche Research)
└── TASK-LOG.md                      # Chronological task record

.claude/                             # Claude Code configuration
├── context/                         # Critical context files (read before building)
│   ├── TASK_RULES.md               # File locations & task flow
│   ├── CODE_QUALITY_RULES.md       # Linting, formatting, types
│   ├── TESTING_RULES.md            # Test structure & coverage
│   ├── PROJECT_CONTEXT.md          # Architecture & decisions
│   ├── SDK_PATTERNS.md             # Claude Agent SDK patterns
│   └── SELF-HEALING.md             # Error tracking system
├── commands/                        # 10+ custom CLI commands
└── skills/                          # Custom automation workflows

specs/                               # Locked-in specifications
├── agents/                          # Agent specs (20 completed)
└── database-schema/                 # Database schema (8 migrations)

docs/                                # Integration guides & API docs
└── [18 directories, 40+ integration guides]
```

## Tech Stack

**Backend:** Python 3.11+ | FastAPI 0.115 | SQLAlchemy 2.0 | Alembic migrations
**Queue:** Celery 5.4 | Redis 5.2
**Database:** PostgreSQL (Supabase) | 30+ tables, 8 migrations
**AI:** Claude Agent SDK (primary) | Anthropic 0.52
**Memory:** Pinecone 5.4 | Zep 2.0
**Integrations:** 40+ (Gmail, Notion, Cal.com, GoHighLevel, ClickUp, Stripe, etc.)
**Quality:** Ruff, MyPy strict, Pytest (>90% tools, >85% agents), pre-commit

## Code Quality - Zero Tolerance

After editing ANY file, run:

```bash
make check      # All quality checks (lint, format, type, security)
make test       # Tests with coverage
```

**Fix ALL errors/warnings before continuing.** Quality gates are non-negotiable.

### Pre-commit Hooks (Mandatory)
```bash
make setup      # Install hooks once
```

These run automatically before commits:
- Trailing whitespace cleanup
- Large file detection (>5MB blocked)
- Secret detection
- Ruff linting (auto-fix)
- Code formatting (auto-fix)
- MyPy type checking
- Bandit security scanning

## Development Workflow

### Before Starting Any Task
1. Read critical context files: `.claude/context/TASK_RULES.md` and others
2. Check `tasks/TASK-LOG.md` for recent work
3. Create/update task in `tasks/backend/pending/` or move to `_in-progress/`

### Running the Application
```bash
make install    # First time: install dependencies
make run        # Start server (localhost:8000)
make migrate    # Apply database migrations
```

### Making Changes
1. Work on the feature/fix
2. Run `make check` frequently (catch issues early)
3. Run `make test` to verify coverage meets minimums
4. Commit with clear message
5. Move task to `_completed/`, update `TASK-LOG.md`

### Testing
```bash
make test-unit      # Unit tests only
make test-int       # Integration tests only
make test-cov       # With coverage report (>90% tools, >85% agents required)
make test-watch     # Watch mode for development
```

## Key Concepts

### Agent System
- **20 agents planned** across 5 phases (1 implemented: Niche Research Agent)
- **Each agent** is a Claude Agent SDK instance with custom tools
- **Tools** are MCP servers registered dynamically per agent
- **Handoffs** between agents use Celery task queues
- **Memory** uses Zep for long-term context across conversations

### Database Architecture
- **8 migrations** define schema (migrations/*.sql)
- **30+ tables** organized by function: leads, campaigns, conversations, meetings, etc.
- **Self-healing system** logs errors to `error_logs`, learns patterns in `knowledge_base`
- **Audit logging** of all agent actions to `audit_logs`

### Integration Pattern
- All 40+ integrations follow `BaseIntegrationClient` pattern
- Located in `src/integrations/[service_name]/`
- Async HTTP clients with rate limit tracking
- Bearer token authentication by default
- Test files in `__tests__/unit/integrations/`

## Self-Healing & Error Tracking

**CRITICAL: Document ALL errors in `.claude/context/SELF-HEALING.md` using table format.**

### Error Learning Table Format

Add errors to the appropriate category table with these columns:

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|

### Current Learnings (check before building)

| ID | Error | Fix |
|----|-------|-----|
| LEARN-001 | ANTHROPIC_API_KEY conflicts with SDK | `os.environ.pop("ANTHROPIC_API_KEY", None)` |
| LEARN-002 | Tenacity retry syntax | Use tuple `(A, B)` not union `A \| B` |
| LEARN-003 | SDK tools reject dependencies | Create clients inside @tool, no DI |
| LEARN-004 | Mixed type attributes | Use `getattr(obj, 'attr', default)` |
| LEARN-005 | WebSearch ignores site: | Use natural language, not `site:` operator |
| LEARN-006 | Google Drive quota exceeded | Set `GOOGLE_DELEGATED_USER` env var, use domain-wide delegation |
| LEARN-017 | @tool decorator untyped | Add `# type: ignore[misc]` to @tool decorators (SDK lacks stubs) |
| LEARN-021 | scalar_one_or_none returns Any | Add `# type: ignore[return-value]` to repository methods |
| LEARN-022 | RetryError exception() returns BaseException | Check `isinstance(exc, Exception)` before passing to record_failure |
| LEARN-023 | datetime.now() is timezone-naive | Use `datetime.now(UTC)` from `datetime` module |
| LEARN-024 | Repository API drift | Read repository source before calling; verify method signatures |

Full details with code examples in `.claude/context/SELF-HEALING.md`

## Critical Files

**MUST READ before building:**
- `.claude/context/TASK_RULES.md` - File organization rules
- `.claude/context/CODE_QUALITY_RULES.md` - Code standards
- `.claude/context/TESTING_RULES.md` - Test coverage requirements
- `.claude/context/PROJECT_CONTEXT.md` - Full architecture
- `.claude/context/SDK_PATTERNS.md` - Agent SDK patterns (1400+ lines)

**Project Status:**
- `tasks/TASK-LOG.md` - What's been done, what's planned
- `cold-email-agents/README.md` - Agent system overview
- `app/backend/README.md` - Backend documentation

## Workflow Commands

```bash
# Check everything
make check              # lint + format + type + security

# Development
make install            # Install dependencies
make dev                # Install dev dependencies
make run                # Start server
make migrate            # Apply migrations

# Code Quality
make lint               # Ruff linting
make format             # Format code
make type               # MyPy type checking
make security           # Security scans

# Testing
make test               # All tests
make test-cov           # With coverage report
make clean              # Remove build artifacts
```

## Important Notes

1. **Quality is non-negotiable** - All code must pass `make check` before commit
2. **Coverage minimums** - Tools >90%, Agents >85%, overall >80%
3. **Test failures block progress** - Fix before proceeding
4. **Use context files** - `.claude/context/` contains critical project rules
5. **Task tracking** - Update `tasks/TASK-LOG.md` when starting/completing work
6. **Environment variables** - Copy `.env.example` to `.env` and fill in credentials
7. **Database** - Alembic migrations apply automatically on server start (see config)
8. **Async throughout** - All database, HTTP, and task operations are async
9. **Error documentation** - Any issues/mistakes impacting NERDS builds MUST be added to `.claude/context/SELF-HEALING.md`

## For More Information

- **Agent architecture:** `cold-email-agents/README.md` + `.claude/context/SDK_PATTERNS.md`
- **Database schema:** `specs/database-schema/` + `.claude/context/PROJECT_CONTEXT.md`
- **Integrations:** `docs/` directory (40+ integration guides)
- **API endpoints:** `app/backend/src/api/` and `app/backend/docs/`
- **Task system:** `tasks/TASK-LOG.md` for chronological record
