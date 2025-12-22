# Task: Setup OpenAI Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement OpenAI integration for GPT-4 and GPT-3.5 Turbo models. This is a foundational service required for agent reasoning and content generation across all agents.

## Files to Create/Modify

- [ ] `src/integrations/openai.py` - OpenAI client implementation
- [ ] `src/integrations/__init__.py` - Export OpenAI client
- [ ] `tests/unit/integrations/test_openai.py` - Unit tests
- [ ] `.env.example` - Add OPENAI_API_KEY and OPENAI_ORG_ID
- [ ] `docs/integrations/openai-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create OpenAI client extending `BaseIntegrationClient`
- [ ] Implement model selection (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
- [ ] Add rate limiting (10k TPM for Tier 1)
- [ ] Add retry logic with exponential backoff
- [ ] Implement token usage tracking
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Document API key setup in docs
- [ ] Update .env.example with required variables
- [ ] Test with actual OpenAI API (optional integration test)

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_openai.py -v --cov=src/integrations/openai --cov-report=term-missing

# Verify coverage >90%
uv run pytest tests/unit/integrations/test_openai.py --cov=src/integrations/openai --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/openai

# Verify environment variables
grep OPENAI .env.example
```

## Notes

- **Cost:** ~$0.01-0.03/1K tokens (input), $0.03-0.06/1K tokens (output)
- **Rate Limit:** 10k TPM for Tier 1 (auto-upgrade at Tier 5 to 10M TPM)
- **Models:** gpt-4-turbo (recommended), gpt-4, gpt-3.5-turbo (fallback)
- **Phase:** Phase 0 (AI Model Providers - Week 1)
- **Depends On:** BaseIntegrationClient implementation
