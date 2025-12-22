# Task: Setup Tomba Email Finding Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Tomba integration for domain-wide email discovery and verification. Excellent for finding multiple emails from same domain.

## Files to Create/Modify

- [ ] `src/integrations/tomba.py` - Tomba client implementation
- [ ] `src/integrations/__init__.py` - Export Tomba client
- [ ] `tests/unit/integrations/test_tomba.py` - Unit tests
- [ ] `.env.example` - Add TOMBA_API_KEY
- [ ] `docs/integrations/tomba-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Tomba client extending `BaseIntegrationClient`
- [ ] Implement domain search endpoint
- [ ] Implement email finder endpoint
- [ ] Implement bulk email listing by domain
- [ ] Implement email verification
- [ ] Implement domain verification
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall

## Verification

```bash
uv run pytest tests/unit/integrations/test_tomba.py -v --cov=src/integrations/tomba --cov-report=term-missing

curl http://localhost:8000/health/integrations/tomba

python -c "from src.integrations import TombaClient; client = TombaClient(...); emails = client.find_emails_by_domain('example.com')"
```

## Notes

- **Cost:** Pay-per-lookup (~$0.15-0.25)
- **Strength:** Domain-wide searches, multiple contacts from same company
- **Waterfall Position:** 3rd
- **Phase:** Lead Generation - CRITICAL
