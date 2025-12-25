# Task: Implement Duplicate Detection Agent (2.3)

**Status:** Pending
**Domain:** backend
**Source:** cold-email-agents/agents/phase2/agent_2_3_duplicate_detection.yaml
**Created:** 2025-12-25
**Priority:** High - Third agent in Phase 2 pipeline

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns
- [ ] Install and test jellyfish library (Jaro-Winkler)
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions related to:
  - [ ] Fuzzy matching algorithms
  - [ ] Duplicate detection patterns
  - [ ] Data merging strategies
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Implement the Duplicate Detection Agent that identifies and merges duplicate leads within the campaign using exact matching (LinkedIn URL, email) and fuzzy matching (name + company with Jaro-Winkler similarity).

## Files to Create/Modify

- [ ] `src/agents/duplicate_detection/agent.py` - Main agent class
- [ ] `src/agents/duplicate_detection/__init__.py` - Module exports
- [ ] `src/agents/duplicate_detection/tools.py` - Detection tools
- [ ] `src/agents/duplicate_detection/schemas.py` - Input/output schemas
- [ ] `src/agents/duplicate_detection/matching.py` - Matching algorithms
- [ ] `src/agents/duplicate_detection/merge.py` - Merge strategies
- [ ] `__tests__/unit/agents/duplicate_detection/test_agent.py` - Unit tests
- [ ] `__tests__/unit/agents/duplicate_detection/test_matching.py` - Matching tests
- [ ] `__tests__/unit/agents/duplicate_detection/test_merge.py` - Merge tests

## Implementation Checklist

### Core Agent Implementation
- [ ] Create `DuplicateDetectionAgent` class using Claude Agent SDK
- [ ] Implement `load_leads` tool - load leads for deduplication
- [ ] Implement `exact_match_detection` tool - find exact duplicates
- [ ] Implement `fuzzy_match_detection` tool - find fuzzy duplicates
- [ ] Implement `merge_duplicates` tool - merge duplicate groups
- [ ] Implement `update_records` tool - update database records

### Exact Matching (src/agents/duplicate_detection/matching.py)
- [ ] `find_linkedin_duplicates()` - exact match on linkedin_url
- [ ] `find_email_duplicates()` - exact match on email (case-insensitive)
- [ ] Use hash partitioning for parallel execution (10 partitions)
- [ ] Create indexes for fast lookup

### Fuzzy Matching (src/agents/duplicate_detection/matching.py)
- [ ] Implement Jaro-Winkler similarity algorithm
- [ ] `calculate_name_similarity()` - first_name + last_name (weight 0.6)
- [ ] `calculate_company_similarity()` - company_name (weight 0.4)
- [ ] `calculate_composite_score()` - combined similarity
- [ ] Threshold: 0.85 minimum for match
- [ ] Use blocking keys: first_name_soundex, company_name_first3

### Merge Strategy (src/agents/duplicate_detection/merge.py)
- [ ] `select_primary_record()` - prefer record with email, more fields, created first
- [ ] `merge_fields()` - first non-null wins for email/phone
- [ ] `longest_value()` - for job_title
- [ ] `most_specific()` - for location
- [ ] Store merged_from IDs in primary record

### Database Operations
- [ ] Mark duplicates: `status = 'duplicate'`, `duplicate_of = primary_id`
- [ ] Update primary: `merged_from = [dup_ids]`
- [ ] Log results to `dedup_logs` table
- [ ] Update campaign: `total_duplicates_found`, `total_leads_unique`

### Parallel Execution
- [ ] Partition leads by hash for exact matching
- [ ] Use blocking keys for fuzzy matching
- [ ] Process merges sequentially (data integrity)

## Jaro-Winkler Implementation

```python
def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """
    Calculate Jaro-Winkler similarity between two strings.
    Returns value between 0.0 and 1.0.
    """
    # Can use jellyfish library: pip install jellyfish
    import jellyfish
    return jellyfish.jaro_winkler_similarity(s1.lower(), s2.lower())
```

## Composite Matching Rule

```python
def is_duplicate(lead1, lead2) -> tuple[bool, float]:
    """Check if two leads are duplicates using composite matching."""
    # First name similarity (weight 0.3)
    fn_sim = jaro_winkler(lead1.first_name, lead2.first_name)

    # Last name similarity (weight 0.3)
    ln_sim = jaro_winkler(lead1.last_name, lead2.last_name)

    # Company similarity (weight 0.4)
    co_sim = jaro_winkler(lead1.company_name, lead2.company_name)

    composite = (fn_sim * 0.3) + (ln_sim * 0.3) + (co_sim * 0.4)

    return composite >= 0.85, composite
```

## Verification

```bash
# Run unit tests
pytest __tests__/unit/agents/duplicate_detection/ -v

# Test matching algorithms
pytest __tests__/unit/agents/duplicate_detection/test_matching.py -v

# Test merge strategies
pytest __tests__/unit/agents/duplicate_detection/test_merge.py -v
```

## Handoff

When complete, this agent hands off to Cross-Campaign Dedup Agent (2.4) with:
- `campaign_id`: Campaign UUID
- `unique_leads`: Count of unique leads after dedup

Handoff condition: `unique_leads >= 1000` (configurable)

## Success Criteria

- Hard: `total_checked == inputs.total_valid_leads`
- Hard: `unique_leads >= 1000`
- Soft: `duplicate_rate < 0.15` (less than 15% duplicates)

## Dependencies

```bash
pip install jellyfish  # For Jaro-Winkler similarity
```

## Notes

- Exact matches are 100% confidence
- Fuzzy matches require 85%+ composite score
- Merge operations are sequential for data integrity
- Use blocking keys to reduce comparison space
