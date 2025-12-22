# Task: Setup Instantly.ai Campaign Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Instantly.ai integration for cold email automation and campaign management. Enables agents to create, manage, and monitor email campaigns at scale.

## Files to Create/Modify

- [ ] `src/integrations/instantly.py` - Instantly.ai client implementation
- [ ] `src/integrations/__init__.py` - Export Instantly client
- [ ] `tests/unit/integrations/test_instantly.py` - Unit tests
- [ ] `.env.example` - Add INSTANTLY_API_KEY
- [ ] `docs/integrations/instantly-setup.md` - Setup documentation
- [ ] `docs/integrations/cold-email-best-practices.md` - Cold email guide

## Implementation Checklist

- [ ] Create Instantly client extending `BaseIntegrationClient`
- [ ] Implement campaign creation
- [ ] Implement campaign list and retrieval
- [ ] Implement campaign update and clone
- [ ] Implement contact list management
- [ ] Implement email template upload and management
- [ ] Implement campaign execution (start/pause/stop)
- [ ] Implement campaign metrics retrieval (opens, clicks, replies)
- [ ] Implement A/B testing setup
- [ ] Implement warmup domain management
- [ ] Implement bounce and unsubscribe handling
- [ ] Add rate limiting (100 req/min typical)
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Create campaign analytics dashboard
- [ ] Document API key setup from Instantly dashboard
- [ ] Implement integration with lead enrichment for list building

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_instantly.py -v --cov=src/integrations/instantly --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_instantly.py --cov=src/integrations/instantly --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/instantly

# Test campaign creation
python -c "from src.integrations import InstantlyClient; client = InstantlyClient(...); campaign = client.create_campaign('Q1 Outreach')"

# Get campaign metrics
curl http://localhost:8000/integrations/instantly/campaigns/123/metrics
```

## Notes

- **Cost:** $200-400/month (included in subscription)
- **Rate Limit:** 100 req/min (no hard limit, soft throttle)
- **Setup:** Requires API key from Instantly dashboard
- **Use Case:** Cold email campaigns, LinkedIn lead follow-up via email
- **Integration:** Works with lead enrichment and LinkedIn API
- **Warm-up:** Domain warmup service to increase deliverability
- **Metrics:** Real-time campaign performance tracking (opens, clicks, replies)
- **Phase:** Lead Generation & Campaign Management (HIGH PRIORITY)
- **A/B Testing:** Built-in support for subject lines and email variants
