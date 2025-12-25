# Task: Implement Lead Scoring Agent (2.5)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_5_lead_scoring.yaml
**Created:** 2025-12-25
**Priority:** High - Fifth agent in Phase 2 pipeline

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns
- [ ] Review niche and persona research from Phase 1 outputs
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Weighted scoring calculations
  - [ ] Job title matching and fuzzy matching
  - [ ] Data completeness scoring
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Implement the Lead Scoring Agent that scores each lead based on fit with target personas, industry alignment, company size match, seniority level, and data completeness. Uses a weighted scoring model to assign tier (A/B/C/D).

## Files to Create/Modify

- [ ] `src/agents/lead_scoring/agent.py` - Main agent class
- [ ] `src/agents/lead_scoring/__init__.py` - Module exports
- [ ] `src/agents/lead_scoring/tools.py` - Scoring tools
- [ ] `src/agents/lead_scoring/schemas.py` - Input/output schemas
- [ ] `src/agents/lead_scoring/scoring_model.py` - Scoring calculations
- [ ] `src/agents/lead_scoring/job_title_matcher.py` - Job title matching
- [ ] `__tests__/unit/agents/lead_scoring/test_agent.py` - Unit tests
- [ ] `__tests__/unit/agents/lead_scoring/test_scoring_model.py` - Scoring tests
- [ ] `__tests__/unit/agents/lead_scoring/test_job_title_matcher.py` - Matcher tests

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `LeadScoringAgent` class using Claude Agent SDK
- [ ] Implement `load_scoring_context` tool - load niche, personas, industry scores
- [ ] Implement `score_leads` tool - score leads in parallel batches
- [ ] Implement `aggregate_results` tool - compile scoring statistics

### Scoring Model (src/agents/lead_scoring/scoring_model.py)

**Total Score: 0-100 points**

| Component | Weight | Max Points | Description |
|-----------|--------|------------|-------------|
| Job Title Match | 30% | 30 | Match against target personas |
| Seniority Match | 20% | 20 | Decision-making level |
| Company Size Match | 15% | 15 | Within target range |
| Industry Fit | 20% | 20 | Based on industry_fit_scores |
| Location Match | 10% | 10 | Geographic alignment |
| Data Completeness | 5% | 5 | Email, phone, domain available |

- [ ] `calculate_job_title_score()` - fuzzy match with synonyms
- [ ] `calculate_seniority_score()` - extract and compare levels
- [ ] `calculate_company_size_score()` - range comparison
- [ ] `calculate_industry_score()` - lookup from industry_fit_scores
- [ ] `calculate_location_score()` - geographic comparison
- [ ] `calculate_completeness_score()` - count filled fields
- [ ] `calculate_total_score()` - weighted sum
- [ ] `determine_tier()` - based on thresholds

### Tier Thresholds

```python
TIER_THRESHOLDS = {
    "A": 80,  # 80+ = High-priority leads
    "B": 60,  # 60-79 = Good leads
    "C": 40,  # 40-59 = Moderate leads
    "D": 0,   # <40 = Low-priority leads
}
```

### Job Title Matcher (src/agents/lead_scoring/job_title_matcher.py)
- [ ] Implement fuzzy matching with 80% threshold
- [ ] Support job title synonyms
- [ ] Extract seniority level from title
- [ ] Match against persona job titles

**Synonyms Example:**
```python
TITLE_SYNONYMS = {
    "VP Marketing": ["Vice President Marketing", "VP of Marketing", "Marketing VP"],
    "Marketing Director": ["Director of Marketing", "Director, Marketing"],
    "Head of Marketing": ["Marketing Lead", "Marketing Head"],
}
```

**Seniority Levels:**
```python
SENIORITY_LEVELS = {
    "c_suite": 6,
    "vp": 5,
    "director": 4,
    "senior_manager": 3,
    "manager": 2,
    "senior": 1,
    "ic": 0,
}
```

### Database Operations
- [ ] Load campaign, niche, personas, industry_fit_scores
- [ ] Load leads in batches of 2000
- [ ] Update leads: `lead_score`, `score_breakdown`, `lead_tier`, `persona_tags`
- [ ] Update campaign: `leads_scored`, `avg_lead_score`, tier counts

### Parallel Execution
- [ ] Process 2000 leads per batch
- [ ] Max 10 parallel batches
- [ ] Checkpoint after every 5 batches

## Score Breakdown Schema

```python
{
    "job_title_match": {
        "score": 25,
        "max": 30,
        "matched_persona": "Marketing Director",
        "similarity": 0.92
    },
    "seniority_match": {
        "score": 15,
        "max": 20,
        "detected": "director",
        "target": "vp"
    },
    "company_size_match": {
        "score": 15,
        "max": 15,
        "detected": "201-500",
        "target": ["201-500", "501-1000"]
    },
    "industry_fit": {
        "score": 18,
        "max": 20,
        "industry": "SaaS",
        "fit_score": 85
    },
    "location_match": {
        "score": 10,
        "max": 10,
        "country": "United States"
    },
    "data_completeness": {
        "score": 5,
        "max": 5,
        "fields_present": ["email", "linkedin_url", "company_domain", "phone"]
    }
}
```

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/lead_scoring/ -v

# Test scoring model
pytest __tests__/unit/agents/lead_scoring/test_scoring_model.py -v

# Test job title matcher
pytest __tests__/unit/agents/lead_scoring/test_job_title_matcher.py -v
```

## Handoff

When complete, this agent hands off to Import Finalizer Agent (2.6) with:
- `campaign_id`: Campaign UUID
- `total_scored`: Total leads scored
- `tier_a_count`: Count of Tier A leads

Handoff conditions:
- `total_scored >= 1000`
- `tier_a_count >= 100`

## Success Criteria

- Hard: `total_scored == inputs.available_leads`
- Hard: `tier_a_count >= 100`
- Soft: `avg_score >= 50`
- Soft: `(tier_a + tier_b) / total >= 0.5` (50% Tier A+B)

## Notes

- Uses `LeadRepository.bulk_update_scores()` for database updates
- Uses `LeadRepository.get_tier_counts()` for statistics
- persona_tags stored as PostgreSQL ARRAY type
