# Task: Implement Import Finalizer Agent (2.6)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_6_import_finalizer.yaml
**Created:** 2025-12-25
**Priority:** High - Final agent in Phase 2 pipeline

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google Sheets API patterns

- [ ] Python Claude Agent SDK patterns
- [ ] Review LEARN-006 Google Sheets domain-wide delegation pattern
- [ ] Check for existing Google Sheets integration - REUSE if exists
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Google Sheets API quota issues (LEARN-006)
  - [ ] Service account delegation patterns
  - [ ] Spreadsheet creation and sharing
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Implement the Import Finalizer Agent that generates comprehensive summary reports, exports lead list to Google Sheets for review, and triggers human approval gate before proceeding to Phase 3 (email verification).

## Files to Create/Modify

- [ ] `src/agents/import_finalizer/agent.py` - Main agent class
- [ ] `src/agents/import_finalizer/__init__.py` - Module exports
- [ ] `src/agents/import_finalizer/tools.py` - Export tools
- [ ] `src/agents/import_finalizer/schemas.py` - Input/output schemas
- [ ] `src/agents/import_finalizer/summary_builder.py` - Summary compilation
- [ ] `src/agents/import_finalizer/sheets_exporter.py` - Google Sheets export
- [ ] `__tests__/unit/agents/import_finalizer/test_agent.py` - Unit tests
- [ ] `__tests__/unit/agents/import_finalizer/test_sheets_exporter.py` - Export tests

## CRITICAL: LEARN-006 - Google Domain-Wide Delegation

**Service accounts have NO storage quota. You MUST configure domain-wide delegation.**

### Required Environment Variables
```bash
GOOGLE_DELEGATED_USER=your-email@yourdomain.com
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Implementation Pattern
```python
from google.oauth2 import service_account

def get_sheets_client():
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    # CRITICAL: Impersonate a real user for quota
    delegated_creds = credentials.with_subject(
        os.getenv("GOOGLE_DELEGATED_USER")
    )
    return build("sheets", "v4", credentials=delegated_creds)
```

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `ImportFinalizerAgent` class using Claude Agent SDK
- [ ] Implement `compile_summary` tool - gather all import stats
- [ ] Implement `export_to_sheets` tool - create Google Sheets
- [ ] Implement `send_notification` tool - Slack notification (optional)

### Summary Builder (src/agents/import_finalizer/summary_builder.py)
- [ ] `build_scraping_summary()` - target, scraped, cost
- [ ] `build_validation_summary()` - valid, invalid, rate
- [ ] `build_dedup_summary()` - within-campaign, cross-campaign
- [ ] `build_scoring_summary()` - scored, avg, tier breakdown
- [ ] `build_full_summary()` - complete import summary

### Google Sheets Export (src/agents/import_finalizer/sheets_exporter.py)
- [ ] `create_spreadsheet()` - create new spreadsheet with LEARN-006 delegation
- [ ] `create_summary_sheet()` - summary tab
- [ ] `create_tier_a_sheet()` - Tier A leads tab
- [ ] `create_tier_b_sheet()` - Tier B leads tab
- [ ] `create_all_leads_sheet()` - all leads tab
- [ ] `set_sharing_permissions()` - anyone with link can view
- [ ] `get_spreadsheet_url()` - return shareable URL

**Fallback:** Export to CSV if Google Sheets fails

### Slack Notification (optional)
- [ ] `send_approval_notification()` - send to #campaign-approvals
- [ ] Include campaign stats, tier breakdown, sheet URL
- [ ] Add approve/reject buttons

### Database Operations
- [ ] Load full campaign stats
- [ ] Load niche info
- [ ] Load lead sample (top 100 by score)
- [ ] Load tier breakdown
- [ ] Update campaign: `lead_list_url`, `import_summary`, `status`
- [ ] Log to `campaign_audit_log`

## Summary Sections

### 1. Scraping Summary
- Target leads
- Total scraped
- Scraping cost
- Cost per lead

### 2. Validation Summary
- Total valid
- Total invalid
- Validity rate

### 3. Deduplication Summary
- Within-campaign duplicates
- Cross-campaign duplicates
- Available after dedup

### 4. Scoring Summary
- Total scored
- Average score
- Tier A count
- Tier B count
- Tier C count

## Google Sheets Structure

| Sheet Name | Content |
|------------|---------|
| Summary | Campaign stats, tier distribution |
| Tier A Leads | High-priority leads (score 80+) |
| Tier B Leads | Good leads (score 60-79) |
| All Leads | All available leads by score |

**Columns:** first_name, last_name, email, job_title, company_name, company_domain, lead_score, lead_tier

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/import_finalizer/ -v

# Test with mock Google Sheets
pytest __tests__/unit/agents/import_finalizer/test_sheets_exporter.py -v

# Integration test (requires Google credentials)
pytest __tests__/integration/agents/test_import_finalizer.py -v --run-integration
```

## Human Gate

This agent triggers a human approval gate:

| Action | Description | Next Step |
|--------|-------------|-----------|
| Approve | Proceed to Phase 3 | Email verification |
| Request More Leads | Need more leads | Re-run Phase 2 |
| Reject | Stop campaign | End |

**Auto-approve conditions (optional):**
- Tier A leads >= 500
- Total leads >= 10000
- Average score >= 60

## Success Criteria

- Hard: `sheet_url IS NOT NULL` (sheet created)
- Hard: `summary IS NOT NULL` (summary generated)
- Soft: `notification_sent = true` (Slack sent)

## Notes

- Timeout: 600 seconds (10 minutes)
- Single execution mode (not parallel)
- Fallback to CSV if Sheets fails
- Share settings: anyone with link can view
