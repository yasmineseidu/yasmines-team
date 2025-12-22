# Task: Setup OpenRouter Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** HIGH

## Summary

Implement OpenRouter integration for multi-model routing and fallback capabilities. Provides unified API access to 100+ models including OpenAI, Anthropic, Google, Meta, and open-source models with cost optimization.

## Files to Create/Modify

- [ ] `src/integrations/openrouter.py` - OpenRouter client implementation
- [ ] `src/integrations/__init__.py` - Export OpenRouter client
- [ ] `tests/unit/integrations/test_openrouter.py` - Unit tests
- [ ] `.env.example` - Add OPENROUTER_API_KEY, OPENROUTER_APP_NAME, OPENROUTER_SITE_URL
- [ ] `docs/integrations/openrouter-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create OpenRouter client extending `BaseIntegrationClient`
- [ ] Implement model routing strategy (cost vs quality)
- [ ] Add rate limiting (no hard limit, but respect per-model limits)
- [ ] Implement fallback chain across models
- [ ] Add cost tracking and optimization
- [ ] Implement model comparison logic
- [ ] Add A/B testing capabilities
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Document supported models and costs
- [ ] Create cost analysis reporting

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_openrouter.py -v --cov=src/integrations/openrouter --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_openrouter.py --cov=src/integrations/openrouter --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/openrouter

# Test model routing
python -c "from src.integrations import OpenRouterClient; client = OpenRouterClient(...); print(client.get_best_model('reasoning'))"
```

## Notes

- **Cost:** +10% markup on underlying model costs (routing fee)
- **Access:** 100+ models via unified API
- **Models:** gpt-4-turbo, gpt-4o, claude-3-opus, llama-2-70b, and many more
- **Strength:** Cost optimization, model fallback, A/B testing
- **Phase:** Phase 0 (AI Model Providers - Week 1)
- **Integration:** Works with cost optimizer to select cheapest model that meets quality threshold
