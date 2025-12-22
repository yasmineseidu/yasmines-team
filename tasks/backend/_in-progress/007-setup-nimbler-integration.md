# Task: Setup Nimbler B2B Contact Enrichment Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Nimbler integration for B2B contact enrichment with comprehensive business data. Sixth in waterfall strategy.

## Files to Create/Modify

- [ ] `src/integrations/nimbler.py` - Nimbler client implementation
- [ ] `src/integrations/__init__.py` - Export Nimbler client
- [ ] `tests/unit/integrations/test_nimbler.py` - Unit tests
- [ ] `.env.example` - Add NIMBLER_API_KEY
- [ ] `docs/integrations/nimbler-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Nimbler client extending `BaseIntegrationClient`
- [ ] Implement contact enrichment endpoint
- [ ] Implement company data enrichment
- [ ] Implement contact finding by company
- [ ] Implement B2B contact verification
- [ ] Implement bulk enrichment
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall

## Verification

```bash
uv run pytest tests/unit/integrations/test_nimbler.py -v --cov=src/integrations/nimbler --cov-report=term-missing

curl http://localhost:8000/health/integrations/nimbler

python -c "from src.integrations import NimblerClient; client = NimblerClient(...); data = client.enrich_contact('contact@example.com')"
```

## Notes

- **Cost:** Pay-per-enrichment
- **Strength:** B2B contacts, company data accuracy
- **Waterfall Position:** 6th
- **Phase:** Lead Generation - CRITICAL
