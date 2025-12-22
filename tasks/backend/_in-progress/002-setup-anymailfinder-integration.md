# Task: Setup Anymailfinder Email Finding Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Anymailfinder integration for high-accuracy email finding, especially for C-level executives and corporate professionals. First in waterfall strategy due to highest accuracy.

## Files to Create/Modify

- [ ] `src/integrations/anymailfinder.py` - Anymailfinder client implementation
- [ ] `src/integrations/__init__.py` - Export Anymailfinder client
- [ ] `tests/unit/integrations/test_anymailfinder.py` - Unit tests
- [ ] `.env.example` - Add ANYMAILFINDER_API_KEY
- [ ] `docs/integrations/anymailfinder-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Anymailfinder client extending `BaseIntegrationClient`
- [ ] Implement email finder endpoint (first name, last name, domain)
- [ ] Implement domain search endpoint
- [ ] Implement LinkedIn profile to email lookup
- [ ] Implement bulk email finding
- [ ] Implement verification score tracking
- [ ] Implement rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall
- [ ] Document confidence scores and accuracy metrics

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_anymailfinder.py -v --cov=src/integrations/anymailfinder --cov-report=term-missing

# Verify coverage >90%
uv run pytest tests/unit/integrations/test_anymailfinder.py --cov=src/integrations/anymailfinder --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/anymailfinder

# Test email finder
python -c "from src.integrations import AnymailfinderClient; client = AnymailfinderClient(...); email = client.find_email('John', 'Doe', 'example.com')"
```

## Notes

- **Cost:** Pay-per-verification (typically $0.05-0.10 per successful lookup)
- **Setup:** Requires API key from Anymailfinder dashboard
- **Use Case:** Email finding, lead enrichment
- **Accuracy:** Highest for C-level executives (first in waterfall)
- **Waterfall Position:** 1st (Primary service)
- **Phase:** Lead Generation - CRITICAL
