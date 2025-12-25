# Task: Verification Finalizer Agent (Agent 3.3)

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** cold-email-agents/agents/phase3/agent_3_3_verification_finalizer.yaml
**Created:** 2025-12-23
**Updated:** 2025-12-25
**Depends On:** Task 011 (Waterfall Enrichment Agent)
**Triggers:** Human Gate for Phase 4 approval

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns (ClaudeSDKClient for orchestration)
- [ ] Check `app/backend/src/integrations/` for existing integrations - REUSE if exists
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`

---

## Summary

Finalize Phase 3, generate quality reports, export enriched lead data to Google Sheets, and trigger human approval gate before Phase 4 (Personalization).

**Key Responsibilities:**
1. Calculate final lead counts by tier (A, B, C)
2. Generate quality assessment report
3. Export verified leads to Google Sheets for review
4. Send Slack notification for human approval
5. Wait for approval before Phase 4 begins

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/verification_finalizer/agent.py` - Main agent class
- `app/backend/src/agents/verification_finalizer/tools.py` - SDK tools
- `app/backend/src/agents/verification_finalizer/reports.py` - Quality report generation
- `app/backend/src/agents/verification_finalizer/exports.py` - Google Sheets export
- `app/backend/__tests__/unit/agents/verification_finalizer/test_agent.py`
- `app/backend/__tests__/unit/agents/verification_finalizer/test_tools.py`
- `app/backend/__tests__/unit/agents/verification_finalizer/test_reports.py`

### Existing Integrations to Use
Check `app/backend/src/integrations/` for:
- `google/sheets/` - Google Sheets API for export
- `slack/` - Slack API for approval notifications
- `telegram/` - Telegram API (fallback notification)

### Repository APIs (Already Implemented)
Use these from `src/database/repositories/`:
- `LeadRepository.get_campaign_leads(campaign_id, has_verified_email=True, tier="A")` - Get verified leads by tier
- `LeadRepository.get_lead_counts_by_tier()` - Get lead counts
- `CampaignRepository.update_verification_results()` - Update campaign with final results

---

## Implementation Checklist

### Phase 1: Data Collection
- [ ] Query verified leads by tier (A, B, C)
- [ ] Calculate totals: verified, enriched, ready for personalization
- [ ] Identify leads with missing data (partial enrichment)

### Phase 2: Quality Report Generation
- [ ] Generate report with metrics:
  - [ ] Total leads by tier
  - [ ] Email verification success rate
  - [ ] Enrichment completion rate
  - [ ] Data quality scores
- [ ] Store quality report in campaign metadata

### Phase 3: Google Sheets Export
- [ ] Create new sheet or update existing
- [ ] Export columns: name, email, company, tier, verification status, enrichment status
- [ ] Format with conditional formatting for easy review
- [ ] Generate shareable link

### Phase 4: Approval Gate
- [ ] Send Slack notification with:
  - [ ] Campaign summary
  - [ ] Lead counts by tier
  - [ ] Quality report link
  - [ ] Sheets link for review
  - [ ] Approve/Reject buttons
- [ ] Record approval state in database
- [ ] Block Phase 4 until approval received

### Phase 5: Testing
- [ ] Unit tests with mocked integrations (>90% coverage)
- [ ] Integration tests with real API keys
- [ ] Approval flow tests
- [ ] Error handling tests

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/verification_finalizer/ -v --cov=app/backend/src/agents/verification_finalizer --cov-report=term-missing
ruff check app/backend/src/agents/verification_finalizer/
mypy app/backend/src/agents/verification_finalizer/ --strict
```

---

## Output

```json
{
  "phase3_complete": true,
  "total_verified": 38500,
  "lead_breakdown": {
    "tier_a": {
      "total": 8500,
      "verified": 8200,
      "enriched": 8100,
      "ready": 8000
    },
    "tier_b": {
      "total": 15200,
      "verified": 14800,
      "enriched": 14500,
      "ready": 14200
    },
    "tier_c": {
      "total": 14800,
      "verified": 12800,
      "enriched": 12000,
      "ready": 11800
    }
  },
  "quality_scores": {
    "email_verification_rate": 0.92,
    "enrichment_completion_rate": 0.89,
    "data_quality_score": 0.85
  },
  "exports": {
    "sheets_url": "https://docs.google.com/spreadsheets/d/...",
    "quality_report_url": "https://docs.google.com/spreadsheets/d/..."
  },
  "approval_status": "pending",
  "slack_notification_sent": true,
  "total_cost": {
    "phase3_email_verification": 1150.50,
    "phase3_enrichment": 2875.00,
    "total": 4025.50
  }
}
```
