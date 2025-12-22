# Task: Setup HeyReach LinkedIn Automation Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement HeyReach integration for LinkedIn automation including connection requests, message sequences, and profile engagement. Complements LinkedIn API for broader reach.

## Files to Create/Modify

- [ ] `src/integrations/heyreach.py` - HeyReach client implementation
- [ ] `src/integrations/__init__.py` - Export HeyReach client
- [ ] `tests/unit/integrations/test_heyreach.py` - Unit tests
- [ ] `.env.example` - Add HEYREACH_API_KEY
- [ ] `docs/integrations/heyreach-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create HeyReach client extending `BaseIntegrationClient`
- [ ] Implement connection request automation
- [ ] Implement message sequence creation and scheduling
- [ ] Implement profile engagement tracking
- [ ] Implement response rate monitoring
- [ ] Implement list management (create, update, monitor)
- [ ] Implement campaign creation with templates
- [ ] Implement A/B testing setup
- [ ] Implement connection acceptance rate tracking
- [ ] Implement message personalization
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >80% coverage
- [ ] Add health check endpoint
- [ ] Create LinkedIn campaign analytics
- [ ] Integration with CRM (GoHighLevel) for follow-up
- [ ] Document best practices for LinkedIn sequences

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_heyreach.py -v --cov=src/integrations/heyreach --cov-report=term-missing

# Verify coverage >80%
uv run pytest tests/unit/integrations/test_heyreach.py --cov=src/integrations/heyreach --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/heyreach

# Test campaign creation
python -c "from src.integrations import HeyReachClient; client = HeyReachClient(...); campaign = client.create_campaign('Q1 Outreach')"
```

## Notes

- **Cost:** Included in subscription (typically $200+/month)
- **Setup:** Requires API key from HeyReach dashboard
- **Use Case:** LinkedIn connection automation, message sequences
- **Rate Limiting:** Account-based limits (typically 100s per day)
- **Integration:** Works with LinkedIn API and Instantly.ai
- **Personalization:** Supports dynamic variables in messages
- **Analytics:** Real-time campaign performance tracking
- **Phase:** Lead Generation & Campaign Management (HIGH PRIORITY)
- **Compliance:** Follows LinkedIn's automation guidelines
