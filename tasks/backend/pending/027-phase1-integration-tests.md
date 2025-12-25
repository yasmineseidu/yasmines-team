# Task: Create Phase 1 Integration Tests

**Priority:** HIGH
**Domain:** Backend
**Depends On:** All Phase 1 tasks (023-026)

## Summary

Create comprehensive integration tests that verify the Phase 1 agent pipeline works end-to-end.

## Test Scenarios

### 1. Full Pipeline Success Test

```python
async def test_phase1_pipeline_success():
    """Test complete Phase 1 from niche input to Google Docs folder."""
    orchestrator = Phase1Orchestrator(
        niche_repo=...,
        persona_repo=...,
        export_repo=...,
    )

    result = await orchestrator.run(
        niche_name="SaaS Marketing Directors",
        industry=["SaaS", "Software"],
        job_titles=["Marketing Director", "VP Marketing"],
    )

    # Verify database state
    assert await niche_exists_in_db(result.niche_id)
    assert await personas_exist_in_db(result.persona_ids)

    # Verify Google Docs created
    assert result.folder_url.startswith("https://drive.google.com")
    assert len(result.documents) == 4

    # Verify niche status
    niche = await get_niche(result.niche_id)
    assert niche['status'] == 'pending_approval'
```

### 2. Niche Rejection Test

```python
async def test_phase1_niche_rejected():
    """Test pipeline stops when niche is rejected."""
    # Use a niche that will score poorly
    result = await orchestrator.run(
        niche_name="Underwater Basket Weavers",
        industry=["Crafts"],
        job_titles=["Basket Weaver"],
    )

    assert result.recommendation == 'reject'
    assert result.niche_id is not None
    assert result.persona_ids == []  # No personas created
    assert result.folder_url is None  # No export

    niche = await get_niche(result.niche_id)
    assert niche['status'] == 'rejected'
```

### 3. Agent Handoff Data Contract Test

```python
async def test_handoff_1_1_to_1_2():
    """Verify data contract between Niche and Persona agents."""
    niche_result = await niche_agent.run(...)

    # Verify all required handoff fields exist
    assert niche_result.niche_id is not None

    # These should be valid for Persona agent
    persona_result = await persona_agent.run(
        niche_id=niche_result.niche_id,
        pain_points_hint=[pp.pain for pp in niche_result.pain_points],
        competitors_hint=niche_result.competitors,
    )

    assert persona_result.persona_ids
    assert len(persona_result.consolidated_pain_points) >= 1

async def test_handoff_1_2_to_1_3():
    """Verify data contract between Persona and Export agents."""
    # ... similar pattern
```

### 4. Database Consistency Test

```python
async def test_database_consistency():
    """Verify all database writes are consistent."""
    result = await orchestrator.run(...)

    # Check all tables have matching niche_id
    niche = await get_niche(result.niche_id)
    scores = await get_niche_scores(result.niche_id)
    research = await get_niche_research_data(result.niche_id)
    personas = await get_personas(result.niche_id)

    assert niche is not None
    assert scores is not None
    assert scores['niche_id'] == result.niche_id
    assert all(p['niche_id'] == result.niche_id for p in personas)
```

### 5. Failure Recovery Test

```python
async def test_checkpoint_recovery():
    """Test pipeline resumes from checkpoint after failure."""
    # Start pipeline
    # Simulate failure after step 2
    # Resume pipeline
    # Verify it doesn't redo step 1 and 2
```

## Checklist

- [ ] Set up test fixtures with database session
- [ ] Create mock data for each agent stage
- [ ] Implement full pipeline success test
- [ ] Implement niche rejection test
- [ ] Implement handoff data contract tests
- [ ] Implement database consistency test
- [ ] Implement checkpoint recovery test
- [ ] Add CI/CD integration

## Verification

```bash
# Run integration tests
make test-int

# Or specifically
pytest app/backend/__tests__/integration/agents/test_phase1_pipeline.py -v
```

## Notes

- Use real Reddit API with limited queries for realistic tests
- Use test Google Drive folder for export tests
- Mark slow tests with `@pytest.mark.slow`
