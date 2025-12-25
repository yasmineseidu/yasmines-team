# Task: Phase 3 Orchestrator

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** app/backend/src/agents/phase3_orchestrator.py (already created)
**Created:** 2025-12-25
**Depends On:** Tasks 010, 011, 012 (Phase 3 agents)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions

- [ ] Use existing Phase 3 orchestrator as base (`src/agents/phase3_orchestrator.py`)
- [ ] Use existing utilities: `circuit_breaker.py`, `retry_utils.py`, `exceptions.py`
- [ ] Tests: unit >90%, integration tests
- [ ] Code quality: ruff, mypy strict, pre-commit

---

## Summary

The Phase 3 Orchestrator coordinates all three Phase 3 agents in sequence:
1. **Agent 3.1:** Email Verification Agent (find + verify emails)
2. **Agent 3.2:** Waterfall Enrichment Agent (enrich leads)
3. **Agent 3.3:** Verification Finalizer Agent (report + approval gate)

**Already Implemented:**
- `Phase3Orchestrator` class with `run()` method
- `Phase3Result` and `EmailVerificationResult` dataclasses
- Circuit breakers and retry utilities
- Repository integration for database updates

**Needs Implementation:**
- Agent instantiation and invocation
- Error handling and saga compensation
- Progress tracking and checkpointing

---

## Files to Modify

### Existing Files
- `app/backend/src/agents/phase3_orchestrator.py` - Complete agent orchestration

### New Files
- `app/backend/__tests__/unit/agents/test_phase3_orchestrator.py`
- `app/backend/__tests__/integration/agents/test_phase3_flow.py`

### Repository APIs (Already Implemented)
- `LeadRepository.get_campaign_leads()` - With Phase 3 filter params
- `CampaignRepository.update_email_verification_results()`
- `CampaignRepository.update_enrichment_results()`
- `CampaignRepository.update_verification_results()`

---

## Implementation Checklist

### Phase 1: Agent Integration
- [ ] Create/import Agent 3.1 (Email Verification)
- [ ] Create/import Agent 3.2 (Waterfall Enrichment)
- [ ] Create/import Agent 3.3 (Verification Finalizer)
- [ ] Wire agents into orchestrator `run()` method

### Phase 2: Error Handling
- [ ] Implement saga compensation for failures
- [ ] Add circuit breaker checks before each agent
- [ ] Implement retry with exponential backoff for transient failures
- [ ] Add graceful degradation (continue with partial results)

### Phase 3: Progress Tracking
- [ ] Add checkpointing between agent runs
- [ ] Implement resume capability from checkpoints
- [ ] Track and report progress to calling orchestrator

### Phase 4: Database Integration
- [ ] Call repository update methods after each agent
- [ ] Track costs per agent/provider
- [ ] Update campaign status after Phase 3 complete

### Phase 5: Testing
- [ ] Unit tests for orchestrator logic (>90% coverage)
- [ ] Mocked agent tests
- [ ] Integration tests with real agents
- [ ] Failure scenario tests (partial completion, rollback)

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/test_phase3_orchestrator.py -v --cov=app/backend/src/agents/phase3_orchestrator --cov-report=term-missing
ruff check app/backend/src/agents/phase3_orchestrator.py
mypy app/backend/src/agents/phase3_orchestrator.py --strict
```

---

## Output

```json
{
  "phase": 3,
  "campaign_id": "uuid",
  "status": "completed",
  "agents_run": [
    {"agent": "3.1", "status": "completed", "duration_seconds": 3600},
    {"agent": "3.2", "status": "completed", "duration_seconds": 1800},
    {"agent": "3.3", "status": "completed", "duration_seconds": 300}
  ],
  "result": {
    "emails_found": 38500,
    "emails_verified": 35000,
    "leads_enriched": 34000,
    "tier_a_ready": 8000,
    "tier_b_ready": 14200,
    "tier_c_ready": 11800,
    "total_ready": 34000
  },
  "costs": {
    "email_verification": 1150.50,
    "enrichment": 2875.00,
    "total": 4025.50
  },
  "approval_status": "pending"
}
```
