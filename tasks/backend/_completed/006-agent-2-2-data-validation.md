# Task: Implement Data Validation Agent (2.2)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_2_data_validation.yaml
**Created:** 2025-12-25
**Priority:** High - Second agent in Phase 2 pipeline

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse existing utilities and validators
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Data validation patterns
  - [ ] Normalization logic
  - [ ] Bulk database operations
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Implement the Data Validation Agent that validates, normalizes, and cleans scraped lead data. Performs context-aware validation based on niche research data, normalizes names and company names, validates URLs and emails.

## Files to Create/Modify

- [ ] `src/agents/data_validation/agent.py` - Main agent class
- [ ] `src/agents/data_validation/__init__.py` - Module exports
- [ ] `src/agents/data_validation/tools.py` - Validation tools
- [ ] `src/agents/data_validation/schemas.py` - Input/output schemas
- [ ] `src/agents/data_validation/normalizers.py` - Field normalization functions
- [ ] `src/agents/data_validation/validators.py` - Field validation functions
- [ ] `__tests__/unit/agents/data_validation/test_agent.py` - Unit tests
- [ ] `__tests__/unit/agents/data_validation/test_normalizers.py` - Normalizer tests
- [ ] `__tests__/unit/agents/data_validation/test_validators.py` - Validator tests

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `DataValidationAgent` class using Claude Agent SDK
- [ ] Implement `load_leads` tool - paginated lead loading (batch 1000)
- [ ] Implement `validate_batch` tool - validate lead batch
- [ ] Implement `aggregate_results` tool - compile validation stats

### Field Validators (src/agents/data_validation/validators.py)
- [ ] `validate_linkedin_url()` - regex pattern, normalize URL
- [ ] `validate_email()` - format validation, lowercase
- [ ] `validate_name()` - min/max length, character check
- [ ] `validate_company_name()` - min/max length
- [ ] `validate_company_size()` - enum validation
- [ ] `cross_field_validation()` - full_name consistency, domain derivation

### Field Normalizers (src/agents/data_validation/normalizers.py)
- [ ] `normalize_name()` - trim, title case, remove special chars
- [ ] `normalize_job_title()` - expand abbreviations (VP -> Vice President)
- [ ] `normalize_company_name()` - remove legal suffixes (Inc, LLC, Ltd)
- [ ] `derive_full_name()` - from first_name + last_name
- [ ] `derive_domain()` - from company LinkedIn URL
- [ ] `parse_location()` - extract city, state, country

### Context-Aware Validation
- [ ] Load niche_research_data for validation context
- [ ] Adjust email requirement based on `email_findability`
  - easy: required
  - moderate: optional
  - difficult: optional with warning
- [ ] Adjust validation strictness based on `data_availability`
  - good: strict
  - moderate: normal
  - poor: lenient
- [ ] Adjust LinkedIn URL validation based on `linkedin_presence`

### Database Operations
- [ ] Bulk update leads with validation results
- [ ] Set `validation_status` (valid/invalid)
- [ ] Store `validation_errors` as JSONB
- [ ] Update `status` to 'validated' or 'invalid'
- [ ] Update campaign validation stats

### Parallel Execution
- [ ] Process leads in batches of 1000
- [ ] Max 10 parallel batches
- [ ] Checkpoint after every 10 batches

## Job Title Mappings

```python
JOB_TITLE_MAPPINGS = {
    "VP": "Vice President",
    "SVP": "Senior Vice President",
    "Dir": "Director",
    "Mgr": "Manager",
    "CEO": "Chief Executive Officer",
    "CFO": "Chief Financial Officer",
    "CTO": "Chief Technology Officer",
    "CMO": "Chief Marketing Officer",
}
```

## Seniority Patterns

```python
SENIORITY_PATTERNS = {
    "c_suite": ["Chief", "CEO", "CFO", "CTO", "CMO", "COO"],
    "vp": ["Vice President", "VP", "SVP", "EVP"],
    "director": ["Director", "Dir"],
    "manager": ["Manager", "Mgr", "Head of"],
    "senior": ["Senior", "Sr", "Lead", "Principal"],
}
```

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/data_validation/ -v

# Test normalizers
pytest __tests__/unit/agents/data_validation/test_normalizers.py -v

# Test validators
pytest __tests__/unit/agents/data_validation/test_validators.py -v
```

## Handoff

When complete, this agent hands off to Duplicate Detection Agent (2.3) with:
- `campaign_id`: Campaign UUID
- `total_valid_leads`: Count of valid leads

Handoff condition: `total_valid >= 1000` (configurable)

## Success Criteria

- Hard: `total_valid >= 1000`
- Hard: `total_processed == inputs.total_leads`
- Soft: `validation_rate >= 0.95` (95% valid)

## Notes

- Required fields: linkedin_url, first_name, last_name, company_name
- Important fields: job_title, location (always required)
- Context-dependent: email, company_domain
