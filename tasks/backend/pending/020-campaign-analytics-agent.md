# Task: Campaign Analytics Agent (Agent 5.4)

**Status:** Pending
**Domain:** backend
**Phase:** 5 - Campaign Execution
**Source:** cold-email-agents/agents/phase5/agent_5_4_campaign_analytics.yaml
**Created:** 2025-12-23
**Depends On:** Task 019

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Python Claude Agent SDK patterns
- [ ] Reuse Instantly.ai integration
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration live API
- [ ] Code quality: ruff, mypy strict, pre-commit
- [ ] Run claude-sdk-reviewer

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Agent Name] - [Error Description]`

---

## Summary

Track metrics and generate reports. Hourly metric collection. Daily/weekly reports. Benchmark comparison. Alert triggering (bounce rate, open rate).

---

## Files to Create/Modify

### New Files
- `app/backend/src/agents/campaign_analytics/agent.py`
- `app/backend/src/agents/campaign_analytics/collector.py`
- `app/backend/src/agents/campaign_analytics/reporter.py`
- `app/backend/__tests__/unit/agents/test_campaign_analytics_agent.py`
- `docs/api/campaign-analytics-agent.yaml`

---

## Implementation Checklist

- [ ] Poll Instantly.ai for metrics (hourly)
- [ ] Metrics: sent, delivered, opened, clicked, replied, bounced
- [ ] Store in campaign_metrics table
- [ ] Generate daily reports
- [ ] Generate weekly reports
- [ ] Compare to benchmarks:
  - Open rate: >20% good, <10% alert
  - Reply rate: >5% good, <2% alert
  - Bounce rate: <5% good, >10% alert
- [ ] Trigger alerts if thresholds exceeded
- [ ] Slack notification for reports

---

## Output

```json
{
  "campaign_id": "uuid",
  "metrics": {
    "sent": 32100,
    "delivered": 30800,
    "opened": 6150,
    "clicked": 920,
    "replied": 320,
    "bounced": 1300
  },
  "rates": {
    "open_rate": 19.9,
    "click_rate": 3.0,
    "reply_rate": 1.0,
    "bounce_rate": 4.2
  },
  "alerts_triggered": ["low_reply_rate"]
}
```
