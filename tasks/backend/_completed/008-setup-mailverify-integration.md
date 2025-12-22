# Task: Setup MailVerify Email Verification Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement MailVerify integration for email verification and deliverability checking. Seventh in waterfall, ensures email validity before sending.

## Files to Create/Modify

- [ ] `src/integrations/mailverify.py` - MailVerify client implementation
- [ ] `src/integrations/__init__.py` - Export MailVerify client
- [ ] `tests/unit/integrations/test_mailverify.py` - Unit tests
- [ ] `.env.example` - Add MAILVERIFY_API_KEY
- [ ] `docs/integrations/mailverify-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create MailVerify client extending `BaseIntegrationClient`
- [ ] Implement email verification endpoint
- [ ] Implement deliverability check
- [ ] Implement domain validation
- [ ] Implement SMTP verification
- [ ] Implement bulk email verification
- [ ] Implement verification score/confidence
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Integration with lead enrichment waterfall

## Verification

```bash
uv run pytest tests/unit/integrations/test_mailverify.py -v --cov=src/integrations/mailverify --cov-report=term-missing

curl http://localhost:8000/health/integrations/mailverify

python -c "from src.integrations import MailVerifyClient; client = MailVerifyClient(...); result = client.verify_email('test@example.com')"
```

## Notes

- **Cost:** Pay-per-verification (typically $0.001-0.01)
- **Strength:** Email validity checking, deliverability validation
- **Waterfall Position:** 7th
- **Phase:** Lead Generation - CRITICAL
