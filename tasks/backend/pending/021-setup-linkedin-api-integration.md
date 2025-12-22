# Task: Setup LinkedIn API Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** HIGH

## Summary

Implement LinkedIn API integration for direct LinkedIn operations including posting, profile data access, and connection management.

## Files to Create/Modify

- [ ] `src/integrations/linkedin.py` - LinkedIn API client implementation
- [ ] `src/integrations/linkedin_oauth.py` - LinkedIn OAuth handler
- [ ] `src/integrations/__init__.py` - Export LinkedIn client
- [ ] `tests/unit/integrations/test_linkedin.py` - Unit tests
- [ ] `.env.example` - Add LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI
- [ ] `docs/integrations/linkedin-setup.md` - Setup and OAuth documentation

## Implementation Checklist

- [ ] Create LinkedIn OAuth client with proper PKCE flow
- [ ] Implement authorization URL generation
- [ ] Implement token exchange and refresh logic
- [ ] Create LinkedIn API client extending `BaseIntegrationClient`
- [ ] Implement post creation endpoint
- [ ] Implement profile data retrieval
- [ ] Implement connection request management
- [ ] Add rate limiting (100 calls/day for free tier, 500 for paid)
- [ ] Add token encryption for secure storage
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Document scopes: r_basicprofile, w_member_social, r_organization_social
- [ ] Create integration with Apify for LinkedIn scraping fallback

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_linkedin.py -v --cov=src/integrations/linkedin --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_linkedin.py --cov=src/integrations/linkedin --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/linkedin

# Test OAuth flow (manual)
# 1. Visit authorization URL
# 2. Exchange code for token
# 3. Test post creation
```

## Notes

- **Rate Limit:** 100 calls/day (free tier), 500 calls/day (paid tier)
- **OAuth:** Requires Client ID and Client Secret from LinkedIn Developer Portal
- **Scopes:** r_basicprofile (profile data), w_member_social (post creation), r_organization_social (org data)
- **Complements:** Apify for scraping tasks (waterfall approach)
- **Phase:** Phase 1 (Social & Google Workspace - Week 1-2)
- **Depends On:** OAuth 2.0 infrastructure, token encryption
