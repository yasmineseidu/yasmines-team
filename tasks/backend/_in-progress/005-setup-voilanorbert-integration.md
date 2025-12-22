# Task: Setup VoilaNorbert Email Finding Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement VoilaNorbert integration for email finding, especially effective for common names. Fourth in waterfall strategy.

## Files to Create/Modify

- [ ] `src/integrations/voilanorbert.py` - VoilaNorbert client implementation
- [ ] `src/integrations/__init__.py` - Export VoilaNorbert client
- [ ] `tests/unit/integrations/test_voilanorbert.py` - Unit tests
- [ ] `.env.example` - Add VOILANORBERT_API_KEY
- [ ] `docs/integrations/voilanorbert-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create VoilaNorbert client extending `BaseIntegrationClient`
- [ ] Implement email finder endpoint
- [ ] Implement company search
- [ ] Implement bulk email finding
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall

## Verification

```bash
uv run pytest tests/unit/integrations/test_voilanorbert.py -v --cov=src/integrations/voilanorbert --cov-report=term-missing

curl http://localhost:8000/health/integrations/voilanorbert

python -c "from src.integrations import VoilaNorbertClient; client = VoilaNorbertClient(...); email = client.find_email('John', 'Smith', 'example.com')"
```

## Notes

- **Cost:** Pay-per-lookup
- **Strength:** Common names, good coverage
- **Waterfall Position:** 4th
- **Phase:** Lead Generation - CRITICAL
