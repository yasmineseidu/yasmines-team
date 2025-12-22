# Task: Setup Reoon Email Deliverability Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Reoon integration for email deliverability monitoring. Tracks bounce rates, spam complaints, and inbox placement to ensure Instantly.ai campaigns reach inboxes.

## Files to Create/Modify

- [ ] `src/integrations/reoon.py` - Reoon client implementation
- [ ] `src/integrations/__init__.py` - Export Reoon client
- [ ] `tests/unit/integrations/test_reoon.py` - Unit tests
- [ ] `.env.example` - Add REOON_API_KEY
- [ ] `docs/integrations/reoon-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Reoon client extending `BaseIntegrationClient`
- [ ] Implement email verification endpoint
- [ ] Implement domain reputation check
- [ ] Implement bounce rate monitoring
- [ ] Implement spam complaint tracking
- [ ] Implement inbox placement testing
- [ ] Implement email list validation (bulk)
- [ ] Implement historical bounce data retrieval
- [ ] Implement real-time delivery alerts
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >80% coverage
- [ ] Add health check endpoint
- [ ] Create deliverability dashboard
- [ ] Integration with Instantly for campaign monitoring
- [ ] Alert thresholds for bounce rates

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_reoon.py -v --cov=src/integrations/reoon --cov-report=term-missing

# Verify coverage >80%
uv run pytest tests/unit/integrations/test_reoon.py --cov=src/integrations/reoon --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/reoon

# Test email verification
python -c "from src.integrations import ReoonClient; client = ReoonClient(...); result = client.verify_email('test@example.com')"

# Check domain reputation
curl http://localhost:8000/integrations/reoon/domain/reputation
```

## Notes

- **Cost:** Pay-per-verification (typically $0.001-0.01 per email)
- **Setup:** Requires API key from Reoon dashboard
- **Use Case:** Email list validation, deliverability monitoring
- **Integration:** Works with Instantly.ai to monitor campaign health
- **Monitoring:** Real-time bounce and complaint tracking
- **Alerts:** Notify when bounce rate exceeds threshold
- **Phase:** Lead Generation & Campaign Management (HIGH PRIORITY)
- **Critical For:** Ensuring high deliverability rates for cold email campaigns
