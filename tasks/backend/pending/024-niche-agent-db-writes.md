# Task: Add Database Writes to Niche Research Agent

**Priority:** HIGH
**Domain:** Backend
**Depends On:** `database/pending/001-phase1-database-tables.md`

## Summary

Update Niche Research Agent (1.1) to write results to the database as specified in the YAML spec, instead of just returning a dataclass.

## Current State

The agent returns `NicheResearchResult` dataclass but doesn't persist anything:
- `app/backend/src/agents/niche_research_agent/agent.py` (line ~end)
- Returns result object but no database operations

## Required Changes

### 1. Add Database Repository

Create `app/backend/src/agents/niche_research_agent/repository.py`:

```python
"""Database operations for Niche Research Agent."""

from sqlalchemy.ext.asyncio import AsyncSession

class NicheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_niche(self, niche_data: dict) -> str:
        """Create niche record, return niche_id."""
        pass

    async def create_niche_scores(self, niche_id: str, scores: dict) -> None:
        """Create scoring breakdown."""
        pass

    async def create_niche_research_data(self, niche_id: str, research: dict) -> None:
        """Store full research findings."""
        pass

    async def update_niche_status(self, niche_id: str, status: str) -> None:
        """Update niche status after research."""
        pass
```

### 2. Update Agent to Use Repository

Modify `agent.py` to accept optional repository and persist:

```python
class NicheResearchAgent:
    def __init__(
        self,
        repository: NicheRepository | None = None,
        ...
    ):
        self.repository = repository

    async def run(self, ...) -> NicheResearchResult:
        result = await self._research(...)

        if self.repository:
            # Persist to database
            niche_id = await self.repository.create_niche({
                'name': niche_name,
                'slug': slugify(niche_name),
                'industry': industry,
                'job_titles': job_titles,
                ...
            })

            await self.repository.create_niche_scores(niche_id, {
                'overall_score': result.overall_score,
                ...
            })

            await self.repository.create_niche_research_data(niche_id, {
                'market_size_estimate': result.market_size_estimate,
                ...
            })

            result.niche_id = niche_id

        return result
```

## Checklist

- [ ] Create SQLAlchemy models for `niches`, `niche_scores`, `niche_research_data`
- [ ] Create `NicheRepository` class with all CRUD operations
- [ ] Update `NicheResearchAgent.__init__` to accept repository
- [ ] Add database writes after research completion
- [ ] Handle upsert (ON CONFLICT) for idempotency
- [ ] Add transaction handling with rollback on error
- [ ] Update result object with generated `niche_id`
- [ ] Write unit tests with mocked repository
- [ ] Write integration test with real database

## Verification

```bash
# Run tests
make test-unit

# Check database after agent run
SELECT * FROM niches WHERE slug = 'saas-marketing-directors';
SELECT * FROM niche_scores WHERE niche_id = '<id>';
SELECT * FROM niche_research_data WHERE niche_id = '<id>';
```
