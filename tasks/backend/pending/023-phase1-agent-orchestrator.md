# Task: Create Phase 1 Agent Orchestrator

**Priority:** CRITICAL
**Domain:** Backend
**Depends On:** `database/pending/001-phase1-database-tables.md`

## Summary

Create an orchestrator that chains Phase 1 agents together, handling the data handoff between agents and persisting results to the database.

## Current State

Each agent runs independently:
- `NicheResearchAgent.run()` returns `NicheResearchResult`
- `PersonaResearchAgent.run()` takes `niche_data` as parameter
- `ResearchExportAgent.export_research()` takes all data as parameters

**Problem:** No code connects these agents or persists their outputs.

## Required Implementation

### File: `app/backend/src/agents/phase1_orchestrator.py`

```python
"""
Phase 1 Orchestrator - Market Intelligence Pipeline.

Chains together:
1. Niche Research Agent (1.1)
2. Persona Research Agent (1.2)
3. Research Export Agent (1.3)

Handles database persistence and handoffs between agents.
"""

class Phase1Orchestrator:
    """Orchestrates the complete Phase 1 market intelligence pipeline."""

    async def run(
        self,
        niche_name: str,
        industry: list[str],
        job_titles: list[str],
        company_size: list[str] | None = None,
        location: list[str] | None = None,
    ) -> Phase1Result:
        """
        Execute complete Phase 1 pipeline.

        Steps:
        1. Run Niche Research Agent → save to DB
        2. Check if recommendation is 'reject' → stop if so
        3. Run Persona Research Agent → save to DB
        4. Run Research Export Agent → create Google Docs
        5. Return folder URL for human approval
        """
        pass
```

### Database Operations

The orchestrator must:

1. **After Niche Research (1.1):**
   - INSERT into `niches` table
   - INSERT into `niche_scores` table
   - INSERT into `niche_research_data` table

2. **Check Recommendation:**
   - If `recommendation == 'reject'`: Update niche status, end workflow
   - If `recommendation in ['proceed', 'review']`: Continue to Agent 1.2

3. **After Persona Research (1.2):**
   - BULK INSERT into `personas` table
   - BULK INSERT into `persona_research_data` table
   - BULK INSERT into `industry_fit_scores` table
   - UPDATE `niches` with consolidated pain points

4. **After Research Export (1.3):**
   - UPDATE `niches` with `research_folder_url` and `status = 'pending_approval'`
   - INSERT into `campaign_audit_log` (if exists)

## Checklist

- [ ] Create `Phase1Orchestrator` class with proper async methods
- [ ] Implement database repository pattern for each table
- [ ] Add checkpoint save/restore for crash recovery
- [ ] Handle agent failures gracefully (update status, log error)
- [ ] Add proper logging with structured fields
- [ ] Write unit tests for orchestrator logic
- [ ] Write integration tests for full pipeline
- [ ] Add observability (metrics, tracing)

## Verification

```bash
# Run unit tests
make test-unit

# Test full pipeline (requires Reddit API keys)
python -c "
from src.agents.phase1_orchestrator import Phase1Orchestrator
import asyncio

async def test():
    orchestrator = Phase1Orchestrator()
    result = await orchestrator.run(
        niche_name='SaaS Marketing Directors',
        industry=['SaaS', 'Software'],
        job_titles=['Marketing Director', 'VP Marketing'],
    )
    print(f'Folder: {result.folder_url}')

asyncio.run(test())
"
```

## Notes

- Use dependency injection for database session
- Implement idempotency using niche slug + date
- Add timeout handling (10 min for 1.1, 15 min for 1.2, 5 min for 1.3)
- Consider Celery task for async execution in production
