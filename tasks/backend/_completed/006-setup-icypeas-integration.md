# Task: Setup Icypeas Email Enrichment Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Icypeas integration for lead enrichment and email finding, especially strong for European contacts. Fifth in waterfall strategy.

## Files to Create/Modify

- [ ] `src/integrations/icypeas.py` - Icypeas client implementation
- [ ] `src/integrations/__init__.py` - Export Icypeas client
- [ ] `tests/unit/integrations/test_icypeas.py` - Unit tests
- [ ] `.env.example` - Add ICYPEAS_API_KEY
- [ ] `docs/integrations/icypeas-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Icypeas client extending `BaseIntegrationClient`
- [ ] Implement lead enrichment endpoint
- [ ] Implement email finder
- [ ] Implement contact data enrichment
- [ ] Implement company information
- [ ] Implement bulk enrichment
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall

## Verification

```bash
uv run pytest tests/unit/integrations/test_icypeas.py -v --cov=src/integrations/icypeas --cov-report=term-missing

curl http://localhost:8000/health/integrations/icypeas

python -c "from src.integrations import IcypeasClient; client = IcypeasClient(...); enriched = client.enrich_contact('contact@example.com')"
```

## Notes

- **Cost:** Pay-per-enrichment
- **Strength:** European contacts, comprehensive data
- **Waterfall Position:** 5th
- **Phase:** Lead Generation - CRITICAL
