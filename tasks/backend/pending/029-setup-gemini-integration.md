# Task: Setup Gemini Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** CRITICAL

## Summary

Implement Google Gemini integration for multimodal AI tasks including vision and long-context operations. Complements OpenAI as a fallback provider with better long-context pricing.

## Files to Create/Modify

- [ ] `src/integrations/gemini.py` - Gemini client implementation
- [ ] `src/integrations/__init__.py` - Export Gemini client
- [ ] `tests/unit/integrations/test_gemini.py` - Unit tests
- [ ] `.env.example` - Add GEMINI_API_KEY and GOOGLE_AI_STUDIO_PROJECT_ID
- [ ] `docs/integrations/gemini-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Gemini client extending `BaseIntegrationClient`
- [ ] Implement model selection (gemini-1.5-pro, gemini-1.5-flash, gemini-ultra)
- [ ] Add rate limiting (360 req/min for free tier, 1000 req/min for paid)
- [ ] Add retry logic with exponential backoff
- [ ] Implement vision/image handling
- [ ] Add token usage tracking
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >90% coverage
- [ ] Add health check endpoint
- [ ] Document API key setup
- [ ] Test multimodal capabilities
- [ ] Create fallback logic for OpenAI when Gemini fails

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_gemini.py -v --cov=src/integrations/gemini --cov-report=term-missing

# Verify coverage >90%
uv run pytest tests/unit/integrations/test_gemini.py --cov=src/integrations/gemini --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/gemini

# Test vision capability
python -c "from src.integrations import GeminiClient; client = GeminiClient(...); print(client.analyze_image(...))"
```

## Notes

- **Cost:** ~$0.00025-0.0125/1K tokens (cheapest option)
- **Rate Limit:** 360 req/min (free), 1000 req/min (paid)
- **Models:** gemini-1.5-pro (recommended), gemini-1.5-flash (fast, cheap), gemini-ultra (most capable)
- **Strength:** Long context windows (1M+ tokens), multimodal capabilities
- **Phase:** Phase 0 (AI Model Providers - Week 1)
- **Depends On:** BaseIntegrationClient implementation
