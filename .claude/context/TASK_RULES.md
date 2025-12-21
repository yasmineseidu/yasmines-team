# Task Rules

## File Placement by Domain

### Backend Domain (app/backend/)
| File Type | Location | Example |
|-----------|----------|---------|
| Agent implementations | `src/agents/[agent_name]/` | `src/agents/lead_generation/agent.py` |
| Integration clients | `src/integrations/[service].py` | `src/integrations/instantly.py` |
| Celery tasks | `src/tasks/[category]_tasks.py` | `src/tasks/orchestration_tasks.py` |
| Webhook handlers | `src/webhooks/[service].py` | `src/webhooks/stripe.py` |
| Unit tests | `__tests__/unit/[module]/test_*.py` | `__tests__/unit/agents/test_base_agent.py` |
| Integration tests | `__tests__/integration/test_*.py` | `__tests__/integration/test_agent_handoff.py` |
| Test fixtures | `__tests__/fixtures/[module]_fixtures.py` | `__tests__/fixtures/agent_fixtures.py` |
| Migration scripts | `create_[system]_tables.py` or `run_[system]_migration.py` | `create_meeting_management_tables.py` |

### Frontend Domain (app/frontend/)
| File Type | Location | Example |
|-----------|----------|---------|
| Pages (App Router) | `app/[route]/page.tsx` | `app/dashboard/page.tsx` |
| Layouts | `app/[route]/layout.tsx` | `app/layout.tsx` |
| React components | `components/[feature]/[Component].tsx` | `components/ui/Button.tsx` |
| Custom hooks | `hooks/use[Name].ts` | `hooks/useLeads.ts` |
| Unit tests | `__tests__/unit/[module].test.tsx` | `__tests__/unit/page.test.tsx` |

### Specs & Plans
| File Type | Location | Example |
|-----------|----------|---------|
| Agent plans (rough) | `plan/agents/[category]-[name].md` | `plan/agents/campaign-copywriting.md` |
| Agent specs (locked) | `specs/agents/[category]-[name].md` | `specs/agents/campaign-copywriting.md` |
| Database specs | `specs/database-schema/` | `specs/database-schema/core-schema.md` |
| SQL migrations | `specs/database-schema/migrations/[NNN]_*.sql` | `specs/database-schema/migrations/008_meeting_management_system.sql` |

### Task Management
| Status | Location | Notes |
|--------|----------|-------|
| Pending | `tasks/[domain]/pending/` | Pick from here |
| In Progress | `tasks/[domain]/_in-progress/` | Move here when starting |
| Completed | `tasks/[domain]/_completed/` | Move here when done |
| Task Log | `tasks/TASK-LOG.md` | Update chronologically |

**Domains**: `backend`, `frontend`, `database`, `deployment`

## Task Workflow

```
1. Pick task from tasks/[domain]/pending/
         ↓
2. Move to tasks/[domain]/_in-progress/
         ↓
3. Read relevant spec from specs/
         ↓
4. Implement with tests
         ↓
5. Run quality checks (make check)
         ↓
6. Move to tasks/[domain]/_completed/
         ↓
7. Update tasks/TASK-LOG.md
```

## Agent Categories (76 agents)

| Category | Count | Examples |
|----------|-------|----------|
| Research | 6 | niche, persona, lead, company research |
| Lead Generation & Data | 7 | lead list builder, email verification, data validation |
| Campaign & Outreach | 11 | A/B testing, copywriting, send-time optimization |
| Response Management | 5+ | email handler, knowledge base, check-ins |
| Meeting Management | 9 | lifecycle orchestrator, scheduler, Fathom integration |
| Proposal & Closing | 5 | transcript processing, proposal creation |
| Payment & Finance | 4 | invoice generation, Stripe processing |
| Onboarding | 3 | orchestrator, stuck detector |
| Delivery & PM | 6 | project management, QA |
| Client Success | 5 | churn risk, upsell detection |
| Offboarding & Nurture | 5 | knowledge transfer, reactivation |
| System & Admin | 10+ | database manager, error monitoring |

## Naming Conventions

### Files
- **Python**: `snake_case.py` (e.g., `base_agent.py`, `lead_generation.py`)
- **TypeScript**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **Tests Backend**: `test_[module].py` (e.g., `test_base_agent.py`)
- **Tests Frontend**: `[module].test.tsx` (e.g., `page.test.tsx`)

### Agent Plans/Specs
Format: `[category]-[specific-function].md`
- `campaign-copywriting.md`
- `leadgen-email-verification.md`
- `meeting-fathom-integration.md`
- `system-database-manager.md`

### Database Migrations
Format: `[NNN]_[description].sql`
- `001_core_tables.sql`
- `007_learning_system.sql`
- `008_meeting_management_system.sql`
