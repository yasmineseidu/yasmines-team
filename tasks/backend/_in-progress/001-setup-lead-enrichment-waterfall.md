# Task: Setup Lead Enrichment Waterfall Strategy

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement lead enrichment waterfall strategy with tiered email finding services. Uses a cascade approach to maximize accuracy while minimizing costs - only call expensive services if cheaper ones fail.

## Waterfall Strategy (In Order)

1. **Anymailfinder** - Best for C-level executives
2. **Findymail** - Best for tech companies
3. **Tomba** - Best for domain-wide search
4. **VoilaNorbert** - Best for common names
5. **Icypeas** - Best for European contacts
6. **Muraena** - Email verification, validation
7. **Nimbler** - B2B contact enrichment
8. **MailVerify** - Email verification, deliverability check

## Files to Create/Modify

- [ ] `src/integrations/lead_enrichment.py` - Waterfall orchestrator
- [ ] `src/integrations/anymailfinder.py` - Anymailfinder client
- [ ] `src/integrations/findymail.py` - Findymail client
- [ ] `src/integrations/tomba.py` - Tomba client
- [ ] `src/integrations/voilanorbert.py` - VoilaNorbert client
- [ ] `src/integrations/icypeas.py` - Icypeas client
- [ ] `src/integrations/muraena.py` - Muraena client
- [ ] `src/integrations/nimbler.py` - Nimbler client
- [ ] `src/integrations/mailverify.py` - MailVerify client
- [ ] `src/integrations/__init__.py` - Export all clients
- [ ] `tests/unit/integrations/test_lead_enrichment.py` - Waterfall tests
- [ ] `.env.example` - Add all API keys
- [ ] `docs/integrations/lead-enrichment-strategy.md` - Waterfall documentation

## Implementation Checklist

- [ ] Create waterfall orchestrator extending `BaseIntegrationClient`
- [ ] Implement lead enrichment request routing
- [ ] Implement tiered fallback logic (retry on failure)
- [ ] Add cost tracking per service to optimize waterfall order
- [ ] Implement result caching (avoid duplicate lookups)
- [ ] Implement batch processing for multiple leads
- [ ] Add rate limiting per service
- [ ] Implement success/failure tracking for each service
- [ ] Add comprehensive error handling
- [ ] Create cost analysis dashboard
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint for each service
- [ ] Create monitoring for service uptime
- [ ] Document waterfall strategy and tuning
- [ ] Create fallback to secondary services
- [ ] Implement A/B testing for order optimization

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_lead_enrichment.py -v --cov=src/integrations/lead_enrichment --cov-report=term-missing

# Verify coverage >90%
uv run pytest tests/unit/integrations/test_lead_enrichment.py --cov=src/integrations/lead_enrichment --cov-report=html

# Check health endpoints
curl http://localhost:8000/health/integrations/lead_enrichment

# Test lead enrichment
python -c "from src.integrations import LeadEnrichmentWaterfall; enricher = LeadEnrichmentWaterfall(...); result = enricher.find_email('john@company.com', 'John Doe')"

# Check cost optimization
curl http://localhost:8000/metrics/lead_enrichment/cost_analysis
```

## Cost Analysis

**Per Lead Enrichment (Average Case):**
- Success on service 1 (Anymailfinder): $0.05-0.10
- Success on service 2 (Findymail): $0.10-0.15
- Success on service 3-5: $0.15-0.25
- **Overall average:** ~$0.10-0.15 per successful enrichment

**Monthly Estimate (1000 leads/month):**
- Waterfall cost: $100-150
- Single expensive service: $500-800
- **Savings:** 70-80% cost reduction

## Notes

- **Strategy:** Cascade through services by cost and success rate
- **Caching:** Critical for cost optimization - cache results for 30 days
- **Monitoring:** Track success rate by service and geographic region
- **Tuning:** Reorder waterfall based on actual performance metrics
- **Phase:** Lead Generation & Research (HIGH PRIORITY)
- **Integration:** Central hub for all lead enrichment operations
- **Cost:** ~$100-150/month for 1000 leads (vs $500+ for single service)
