# Task: Add Database Reads to Research Export Agent

**Priority:** MEDIUM
**Domain:** Backend
**Depends On:** `database/pending/001-phase1-database-tables.md`

## Summary

Update Research Export Agent (1.3) to read data from database instead of receiving all data as parameters.

## Current State

The agent's `export_research()` method receives all data as parameters:
- `niche_data`, `niche_scores`, `niche_research_data`, `personas`, etc.
- File: `app/backend/src/agents/research_export/agent.py`

This works but requires the orchestrator to manually pass all data.

## Required Changes

### 1. Add Database Repository

Create `app/backend/src/agents/research_export/repository.py`:

```python
"""Database operations for Research Export Agent."""

class ResearchExportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_niche_full(self, niche_id: str) -> dict:
        """Load complete niche data (REQUIRED)."""
        pass

    async def get_niche_scores(self, niche_id: str) -> dict:
        """Load niche scores (REQUIRED)."""
        pass

    async def get_personas(self, niche_id: str) -> list[dict]:
        """Load all personas for niche (REQUIRED)."""
        pass

    async def get_persona_research(self, persona_ids: list[str]) -> list[dict]:
        """Load persona research data (optional)."""
        pass

    async def get_industry_fit_scores(self, niche_id: str) -> list[dict]:
        """Load industry fit scores (optional)."""
        pass

    async def get_niche_research_data(self, niche_id: str) -> dict | None:
        """Load full research findings (optional)."""
        pass

    async def update_niche_folder(self, niche_id: str, folder_url: str) -> None:
        """Update niche with research folder URL."""
        pass

    async def log_export(self, niche_id: str, folder_url: str, documents: list) -> None:
        """Log export action to audit log."""
        pass
```

### 2. Add Simplified Entry Point

```python
class ResearchExportAgent:
    async def run(self, niche_id: str, persona_ids: list[str], consolidated_pain_points: list[str]) -> dict:
        """
        Run export agent with database reads.

        This is the handoff-compatible entry point.
        """
        # Load all data from database
        niche_data = await self.repository.get_niche_full(niche_id)
        niche_scores = await self.repository.get_niche_scores(niche_id)
        niche_research = await self.repository.get_niche_research_data(niche_id)
        personas = await self.repository.get_personas(niche_id)
        persona_research = await self.repository.get_persona_research(persona_ids)
        industry_scores = await self.repository.get_industry_fit_scores(niche_id)

        # Call existing export logic
        result = await self.export_research(
            niche_id=niche_id,
            niche_data=niche_data,
            niche_scores=niche_scores,
            niche_research_data=niche_research,
            personas=personas,
            persona_research_data=persona_research,
            industry_scores=industry_scores,
            consolidated_pain_points=consolidated_pain_points,
        )

        # Update database
        await self.repository.update_niche_folder(niche_id, result['folder_url'])
        await self.repository.log_export(niche_id, result['folder_url'], result['documents'])

        return result
```

## Checklist

- [ ] Create `ResearchExportRepository` class
- [ ] Add `run()` method that loads from database
- [ ] Keep `export_research()` for flexibility
- [ ] Update niche status to 'pending_approval' after export
- [ ] Add audit log entry if `campaign_audit_log` table exists
- [ ] Write unit tests
- [ ] Write integration test

## Verification

```bash
make test-unit

# After export
SELECT research_folder_url, status FROM niches WHERE id = '<id>';
# Should show folder URL and 'pending_approval' status
```
