# Task: Cold Email API Documentation (Swagger)

**Status:** Pending
**Domain:** backend
**Phase:** Documentation
**Source:** All agent tasks 001-020
**Created:** 2025-12-23

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)

- [ ] Create complete Swagger/OpenAPI 3.0 spec
- [ ] Document all endpoints from all 20 agents
- [ ] Include request/response schemas
- [ ] Include authentication requirements
- [ ] Include error responses

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Documentation] - [Error Description]`

---

## Summary

Create comprehensive API documentation for all cold email workflow agents in Swagger/OpenAPI format.

---

## Files to Create

- [ ] `docs/api/cold-email-workflow.yaml` - Main Swagger spec
- [ ] `docs/api/schemas/` - Shared schema definitions

---

## Swagger Structure

```yaml
openapi: 3.0.0
info:
  title: Cold Email Workflow API
  version: 1.0.0
  description: API for 20-agent cold email workflow system

servers:
  - url: https://api.smarterteam.com/v1
    description: Production

paths:
  # Phase 1: Market Intelligence
  /agents/niche-research/start:
    post:
      summary: Start niche research
      tags: [Phase 1 - Market Intelligence]
      requestBody: ...
      responses: ...

  /agents/niche-research/{niche_id}:
    get:
      summary: Get niche research results
      tags: [Phase 1 - Market Intelligence]
      responses: ...

  /agents/persona-research/start:
    post:
      summary: Start persona research
      tags: [Phase 1 - Market Intelligence]
      requestBody: ...
      responses: ...

  /agents/research-export/{niche_id}:
    post:
      summary: Export research to Google Docs
      tags: [Phase 1 - Market Intelligence]
      responses: ...

  # Phase 2: Lead Acquisition
  /agents/lead-list-builder/start:
    post:
      summary: Start lead scraping
      tags: [Phase 2 - Lead Acquisition]
      requestBody: ...
      responses: ...

  # ... continue for all 20 agents

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    NicheResearchRequest:
      type: object
      required: [niche_name, industry, job_titles]
      properties:
        niche_name: ...
        industry: ...
        job_titles: ...

    NicheResearchResponse:
      type: object
      properties:
        niche_id: ...
        overall_score: ...
        # ...
```

---

## Required Endpoints

### Phase 1 (Market Intelligence)
1. POST /agents/niche-research/start
2. GET /agents/niche-research/{niche_id}
3. GET /agents/niche-research/status/{job_id}
4. POST /agents/persona-research/start
5. GET /agents/persona-research/{persona_id}
6. POST /agents/research-export/start
7. GET /agents/research-export/{export_id}

### Phase 2 (Lead Acquisition)
8. POST /agents/lead-list-builder/start
9. GET /agents/lead-list-builder/{campaign_id}/status
10. POST /agents/data-validation/start
11. POST /agents/duplicate-detection/start
12. POST /agents/cross-campaign-dedup/start
13. POST /agents/lead-scoring/start
14. POST /agents/import-finalizer/export

### Phase 3 (Email Verification)
15. POST /agents/email-verification/start
16. GET /agents/email-verification/{job_id}/status
17. POST /agents/waterfall-enrichment/start
18. POST /agents/verification-finalizer/export

### Phase 4 (Personalization)
19. POST /agents/company-research/start
20. POST /agents/lead-research/start
21. POST /agents/email-generation/start
22. POST /agents/personalization-finalizer/export

### Phase 5 (Campaign Execution)
23. POST /agents/campaign-setup/start
24. POST /agents/email-sending/upload
25. GET /agents/email-sending/{campaign_id}/status
26. POST /agents/reply-monitoring/start
27. GET /agents/reply-monitoring/{campaign_id}/replies
28. POST /agents/campaign-analytics/generate
29. GET /agents/campaign-analytics/{campaign_id}/report

---

## Verification

```bash
# Validate Swagger spec
spectral lint docs/api/cold-email-workflow.yaml

# Or using swagger-cli
swagger-cli validate docs/api/cold-email-workflow.yaml
```
