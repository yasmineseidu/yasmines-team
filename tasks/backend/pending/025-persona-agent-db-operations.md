# Task: Add Database Operations to Persona Research Agent

**Priority:** HIGH
**Domain:** Backend
**Depends On:** `database/pending/001-phase1-database-tables.md`

## Summary

Update Persona Research Agent (1.2) to:
1. Read niche data from database (instead of parameter)
2. Write personas and research data to database

## Current State

- Agent receives `niche_data` as parameter instead of reading from DB
- Agent returns `PersonaResearchResult` but doesn't persist
- File: `app/backend/src/agents/persona_research/agent.py`

## Required Changes

### 1. Add Database Repository

Create `app/backend/src/agents/persona_research/repository.py`:

```python
"""Database operations for Persona Research Agent."""

class PersonaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_niche(self, niche_id: str) -> dict | None:
        """Load niche details (REQUIRED)."""
        pass

    async def get_niche_scores(self, niche_id: str) -> dict | None:
        """Load niche scores (optional)."""
        pass

    async def get_niche_research_data(self, niche_id: str) -> dict | None:
        """Load full research findings (optional)."""
        pass

    async def create_personas(self, personas: list[dict]) -> list[str]:
        """Bulk insert personas, return persona_ids."""
        pass

    async def create_persona_research_data(self, data: list[dict]) -> None:
        """Bulk insert research data for audit trail."""
        pass

    async def create_industry_fit_scores(self, scores: list[dict]) -> None:
        """Bulk insert/upsert industry fit scores."""
        pass

    async def update_niche_consolidated(self, niche_id: str, data: dict) -> None:
        """Update niche with consolidated findings."""
        pass
```

### 2. Update Agent

Modify `agent.py` to use repository:

```python
class PersonaResearchAgent:
    async def run(
        self,
        niche_id: str,
        ...
    ) -> PersonaResearchResult:
        # Read from database instead of parameter
        niche_data = await self.repository.get_niche(niche_id)
        if not niche_data:
            raise NicheNotFoundError(niche_id)

        niche_scores = await self.repository.get_niche_scores(niche_id)
        niche_research = await self.repository.get_niche_research_data(niche_id)

        # Run research with loaded data
        result = await self.research(config, niche_data)

        # Persist results
        persona_ids = await self.repository.create_personas([...])
        await self.repository.create_persona_research_data([...])
        await self.repository.create_industry_fit_scores([...])
        await self.repository.update_niche_consolidated(niche_id, {...})

        result.persona_ids = persona_ids
        return result
```

## Checklist

- [ ] Create SQLAlchemy models for `personas`, `persona_research_data`, `industry_fit_scores`
- [ ] Create `PersonaRepository` class with all operations
- [ ] Update agent to read niche from database
- [ ] Add database writes after persona synthesis
- [ ] Handle NicheNotFoundError properly
- [ ] Add transaction handling
- [ ] Update niche table with consolidated pain points
- [ ] Write unit tests with mocked repository
- [ ] Write integration test

## Verification

```bash
make test-unit

# After agent run
SELECT * FROM personas WHERE niche_id = '<id>';
SELECT * FROM persona_research_data WHERE persona_id IN (...);
SELECT * FROM industry_fit_scores WHERE niche_id = '<id>';
```
