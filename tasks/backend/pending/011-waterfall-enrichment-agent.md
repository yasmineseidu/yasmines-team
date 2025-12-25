# Task: Waterfall Enrichment Agent (Agent 3.2)

**Status:** Pending
**Domain:** backend
**Phase:** 3 - Email Verification & Enrichment
**Source:** cold-email-agents/agents/phase3/agent_3_2_waterfall_enrichment.yaml
**Created:** 2025-12-23
**Updated:** 2025-12-25
**Depends On:** Task 010 (Email Verification Agent)

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Python Claude Agent SDK patterns (ClaudeSDKClient for orchestration)
- [ ] Check `app/backend/src/integrations/` for existing providers - REUSE if exists
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`

---

## Summary

Enrich leads with company and contact data using tiered strategy. Free providers first (WebSearch, WebFetch), then paid (Clearbit, Apollo, ZoomInfo, BuiltWith).

**Enrichment Provider Tiers:**
- **Tier 1 (Free):** Claude WebSearch, Claude WebFetch (company news, website scraping)
- **Tier 2 (Cheap):** Clearbit ($0.05/lookup), Apollo ($0.02/lookup)
- **Tier 3 (Moderate):** ZoomInfo ($0.15/lookup - intent), BuiltWith ($0.10/lookup - tech stack)

**Enrichment Strategy by Lead Tier:**
- **Tier A (Full):** All data - revenue, tech stack, funding, org chart, intent signals
- **Tier B (Standard):** Company data, industry, location, employee count, recent news
- **Tier C (Basic):** Minimal - company name verification, industry, basic website info

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/waterfall_enrichment/agent.py` - Main agent class
- `app/backend/src/agents/waterfall_enrichment/tools.py` - SDK tools for enrichment
- `app/backend/src/agents/waterfall_enrichment/enrichers.py` - Provider-specific enrichers
- `app/backend/src/agents/waterfall_enrichment/strategies.py` - Tier-based enrichment strategies
- `app/backend/__tests__/unit/agents/waterfall_enrichment/test_agent.py`
- `app/backend/__tests__/unit/agents/waterfall_enrichment/test_tools.py`
- `app/backend/__tests__/unit/agents/waterfall_enrichment/test_enrichers.py`

### Existing Integrations to Use
Check `app/backend/src/integrations/` for:
- `clearbit/` - Company data enrichment
- `apollo/` - Company and contact data
- `zoominfo/` - Intent data and org charts
- `builtwith/` - Tech stack detection

### Repository APIs (Already Implemented)
Use these from `src/database/repositories/`:
- `LeadRepository.get_campaign_leads(campaign_id, has_verified_email=True, is_enriched=False, tier="A")` - Get leads needing enrichment
- `LeadRepository.update_enrichment_data()` - Update lead with enriched data
- `CampaignRepository.update_enrichment_results()` - Update campaign metrics

---

## Implementation Checklist

### Phase 1: Setup & Provider Registry
- [ ] Create provider registry with costs, rate limits
- [ ] Implement tier-based provider selection
- [ ] Configure parallel execution limits per provider

### Phase 2: Free Enrichment (Tier 1)
- [ ] Implement WebSearch tool for company news, funding
- [ ] Implement WebFetch tool for website scraping
- [ ] Parse about pages, contact pages for data extraction
- [ ] Parallel processing with limit of 10

### Phase 3: Paid Enrichment (Tier 2-3)
- [ ] Clearbit integration for company data
- [ ] Apollo integration for contact data
- [ ] ZoomInfo integration for intent signals (Tier A only)
- [ ] BuiltWith integration for tech stack (Tier A only)

### Phase 4: Tier-Based Strategy
- [ ] Tier A: Run all enrichers, maximum data collection
- [ ] Tier B: Standard enrichers only (Clearbit, Apollo, WebSearch)
- [ ] Tier C: Free enrichers only (WebSearch, WebFetch)

### Phase 5: Database Updates
- [ ] Update leads with enriched fields
- [ ] Track enrichment costs per provider
- [ ] Update campaign metrics via CampaignRepository

### Phase 6: Testing
- [ ] Unit tests with mocked providers (>90% coverage)
- [ ] Integration tests with real API keys
- [ ] Tier-based enrichment strategy tests
- [ ] Cost tracking verification tests

---

## Verification

```bash
pytest app/backend/__tests__/unit/agents/waterfall_enrichment/ -v --cov=app/backend/src/agents/waterfall_enrichment --cov-report=term-missing
ruff check app/backend/src/agents/waterfall_enrichment/
mypy app/backend/src/agents/waterfall_enrichment/ --strict
```

---

## Output

```json
{
  "total_enriched": 38500,
  "enrichment_by_tier": {
    "A": {"full": 8200, "partial": 300},
    "B": {"standard": 14800, "partial": 400},
    "C": {"basic": 12000, "partial": 800}
  },
  "provider_usage": {
    "web_search": 38500,
    "web_fetch": 25000,
    "clearbit": 23500,
    "apollo": 23500,
    "zoominfo": 8500,
    "builtwith": 8500
  },
  "total_cost": 2875.00,
  "cost_by_provider": {
    "web_search": 0.00,
    "web_fetch": 0.00,
    "clearbit": 1175.00,
    "apollo": 470.00,
    "zoominfo": 1275.00,
    "builtwith": 850.00
  }
}
```
