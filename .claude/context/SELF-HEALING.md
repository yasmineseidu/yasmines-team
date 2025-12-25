# Self-Healing and Continuous Learning System

## Overview

The Smarter Team backend includes a sophisticated **self-healing and continuous learning system** that allows agents to:
1. Document every mistake and error
2. Learn from failures automatically
3. Improve decision-making over time
4. Prevent repeated errors

This system operates across three layers:
- **Error Tracking** - All agent failures are captured with full context
- **Learning Storage** - Mistakes are analyzed and stored as learning rules
- **Agent Memory** - Agents read previous mistakes before making decisions

## Architecture

### Three-Layer System

```
┌─────────────────────────────────────────────┐
│ Agent Execution Layer                       │
│ - Agent performs task                       │
│ - Task succeeds or fails                    │
│ - All outcomes logged                       │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│ Error Capture & Analysis Layer              │
│ - Capture error details                     │
│ - Analyze root cause                        │
│ - Store in error_logs table                 │
│ - Trigger learning extraction               │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│ Learning Storage & Retrieval Layer          │
│ - Extract learnings from errors             │
│ - Store in knowledge_base table             │
│ - Retrieve during future decisions          │
│ - Update agent behavior dynamically         │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│ Agent Feedback Loop                         │
│ - Agent reads learned mistakes              │
│ - Applies learnings to new tasks            │
│ - Reduces error repetition                  │
│ - Improves confidence scores                │
└─────────────────────────────────────────────┘
```

## Database Schema (From Migration 007)

### error_logs Table
Captures every agent failure with complete context:

```sql
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    error_context JSONB,           -- Full error details
    stack_trace TEXT,
    affected_entities JSONB,       -- Lead IDs, etc. that were affected
    recovery_action VARCHAR(255),  -- What we did to recover
    recovery_success BOOLEAN,
    severity ENUM('low', 'medium', 'high', 'critical'),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    learning_extracted BOOLEAN DEFAULT FALSE,
    INDEX (agent_name, created_at),
    INDEX (error_type, severity)
);
```

**Key Fields:**
- `error_context` - Full JSONB with input parameters, expected vs actual output
- `affected_entities` - Which leads/campaigns/etc were impacted
- `recovery_action` - How the system recovered (retry, fallback, human escalation)
- `learning_extracted` - Flag for whether learnings were captured
- `severity` - Critical errors get immediate attention

### knowledge_base Table
Stores learned patterns from mistakes:

```sql
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    pattern VARCHAR(255) NOT NULL,        -- What we learned
    rule_type ENUM('avoid', 'always', 'never', 'validate', 'retry'),
    rule_condition TEXT,                  -- When this applies
    rule_action TEXT,                     -- What to do about it
    confidence FLOAT DEFAULT 0.5,          -- How confident (0-1)
    times_applied INT DEFAULT 0,           -- How many times used
    times_successful INT DEFAULT 0,        -- How many times it worked
    source_error_id UUID REFERENCES error_logs(id),
    metadata JSONB,                        -- Additional context
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX (agent_name, rule_type),
    INDEX (confidence DESC)
);
```

**Example Rules:**
```json
{
    "agent_name": "lead_qualifier",
    "error_type": "INVALID_EMAIL",
    "pattern": "Email domain contains typo",
    "rule_type": "validate",
    "rule_condition": "IF domain matches common_typos THEN flag as needs_review",
    "rule_action": "Run email verification before qualification",
    "confidence": 0.87,
    "times_applied": 142,
    "times_successful": 123
}
```

### response_tracking Table
Monitors agent decision quality:

```sql
CREATE TABLE response_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    response_type VARCHAR(100),            -- Decision type
    response_quality ENUM('excellent', 'good', 'fair', 'poor'),
    confidence_score FLOAT,                -- Agent's confidence (0-1)
    actual_outcome ENUM('success', 'failure', 'partial'),
    feedback_provided BOOLEAN DEFAULT FALSE,
    user_feedback TEXT,                    -- Human review
    learning_generated BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX (agent_name, created_at),
    INDEX (confidence_score)
);
```

### agent_learning Table
Per-agent learning progression:

```sql
CREATE TABLE agent_learning (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) NOT NULL,
    learning_area VARCHAR(100),            -- What aspect improved
    improvement_delta FLOAT,               -- How much better (percent)
    error_count_before INT,
    error_count_after INT,
    success_rate_before FLOAT,
    success_rate_after FLOAT,
    learning_date TIMESTAMP DEFAULT NOW(),
    last_applied TIMESTAMP,
    metadata JSONB,
    INDEX (agent_name, learning_date)
);
```

## Error Capture Process

### Step 1: Error Occurs

```python
# In any agent or integration client
try:
    result = await some_operation()
except Exception as e:
    await capture_error(
        agent_name="lead_qualifier",
        task_id="task_123",
        error_type="RATE_LIMIT_EXCEEDED",
        error=e,
        context={
            "input": {"lead_id": "123", "email": "test@example.com"},
            "expected": {"status": "qualified"},
            "actual": {"error": "429 Too Many Requests"}
        },
        affected_entities={"lead_id": "123"},
        recovery_action="queued_for_retry"
    )
```

### Step 2: Error Analysis

```python
async def analyze_error(error_log: ErrorLog) -> None:
    """
    Analyze error and extract learnings.

    Process:
    1. Categorize error type
    2. Assess severity
    3. Determine if learnable
    4. Extract generalizable patterns
    5. Store in knowledge_base
    """

    # Categorize
    if error_log.error_type == "RATE_LIMIT_EXCEEDED":
        severity = "medium"
        learnable = True
        pattern = "API rate limits reached"

    # Assess impact
    if error_log.affected_entities:
        severity = escalate_severity(severity)

    # Extract learning
    if learnable:
        learning = extract_learning_from_error(error_log)
        await store_learning(learning)
```

### Step 3: Learning Storage

```python
# Extracted learning rule
learning_rule = {
    "agent_name": "email_sender",
    "error_type": "RATE_LIMIT_EXCEEDED",
    "pattern": "Instantly API hits rate limits after 200 emails/minute",
    "rule_type": "validate",
    "rule_condition": "IF emails_sent_this_minute > 180 THEN",
    "rule_action": "queue remaining emails until next minute",
    "confidence": 0.92,  # Based on 15 similar errors
    "source_error_id": "uuid-of-error"
}

await knowledge_base.insert(learning_rule)
```

### Step 4: Agent Retrieves Learning

```python
async def process_task(self, task: dict) -> dict:
    """
    Agent retrieves relevant learnings before acting.
    """

    # Get learnings for this task type
    learnings = await self.get_learnings_for_task(
        agent_name=self.name,
        task_type=task["type"]
    )

    # Add learnings to system prompt
    for learning in learnings:
        self.system_prompt += f"\n\nLEARNING: {learning['rule_action']}"

    # Agent now acts with knowledge of past mistakes
    result = await self.claude_client.query(
        prompt=self.system_prompt,
        task_data=task
    )

    return result
```

## Learning Types

### 1. Validation Rules
**Prevent errors before they happen**

```json
{
    "rule_type": "validate",
    "pattern": "Email format appears invalid",
    "rule_action": "Run validation check before sending",
    "trigger": "When recipient email contains suspicious patterns",
    "success_rate": 0.94
}
```

### 2. Avoid Rules
**Don't do things that fail**

```json
{
    "rule_type": "avoid",
    "pattern": "Don't call API when rate limit near",
    "rule_action": "Check rate limit quota first",
    "trigger": "When rate limit < 10% remaining",
    "success_rate": 0.98
}
```

### 3. Always Rules
**Do things that work**

```json
{
    "rule_type": "always",
    "pattern": "Always verify company size before outreach",
    "rule_action": "Request company headcount from DB",
    "trigger": "Before sending B2B cold email",
    "success_rate": 0.96
}
```

### 4. Retry Rules
**How to recover from failures**

```json
{
    "rule_type": "retry",
    "pattern": "Exponential backoff on API failures",
    "rule_action": "Wait 1s, then 2s, then 4s, then 8s",
    "trigger": "On 5xx errors or timeouts",
    "max_attempts": 3,
    "success_rate": 0.87
}
```

### 5. Escalation Rules
**When to ask for human help**

```json
{
    "rule_type": "escalate",
    "pattern": "Customer unresponsive after 3 attempts",
    "rule_action": "Route to human sales rep",
    "trigger": "After 3 failed contact attempts",
    "success_rate": 0.92
}
```

## Continuous Learning Flow

### Daily Learning Cycle

```
09:00 - Overnight Error Analysis
  ├─ Read all errors from last 24 hours
  ├─ Group by type and agent
  ├─ Extract patterns (>5 similar errors = pattern)
  └─ Store new learnings

10:00 - Learning Validation
  ├─ Calculate confidence scores
  ├─ Compare success rates before/after
  ├─ Flag low-confidence learnings for review
  └─ Update agent decision trees

12:00 - Agent Update
  ├─ Push new learnings to agents
  ├─ Update system prompts with learnings
  ├─ Log effectiveness metrics
  └─ Notify of critical changes

18:00 - Performance Review
  ├─ Measure success rate improvements
  ├─ Identify emerging patterns
  ├─ Flag persistent problem areas
  └─ Update training materials
```

### Weekly Learning Review

```
Monday 09:00 - Weekly Learning Analysis
  ├─ Analyze all learnings from past week
  ├─ Calculate impact of each learning
  ├─ Identify conflicting learnings
  ├─ Find high-confidence rules (>0.9)
  └─ Generate improvement report

Tuesday - Manual Review
  ├─ Review low-confidence rules (<0.6)
  ├─ Validate critical learnings (>5 hours impact)
  ├─ Adjust confidence scores based on results
  └─ Document rationale for changes
```

## Preventing Repeated Errors

### Error Deduplication

```python
async def should_capture_error(error: Exception) -> bool:
    """
    Check if this is a new error or repeat of known issue.
    """

    # Hash the error
    error_hash = hash_error(error)

    # Check if seen before in last 24 hours
    recent_similar = await error_logs.find(
        error_hash=error_hash,
        created_at > NOW() - 24hours
    )

    if recent_similar:
        # Increment repeat counter
        await error_logs.increment_repeat_count(recent_similar.id)

        # If repeated 5+ times, escalate
        if recent_similar.repeat_count > 5:
            await escalate_to_human_review(recent_similar)

        return False  # Don't capture duplicate

    return True  # New error, capture it
```

### Error Prevention Logic

```python
async def apply_learnings_before_action(agent_name: str, action: str) -> dict:
    """
    Check if action violates known learnings.
    """

    # Get all learnings for this agent
    learnings = await knowledge_base.find(agent_name=agent_name)

    # Filter to relevant learnings
    relevant = [
        l for l in learnings
        if l.rule_type == "avoid" and l.rule_condition in action
    ]

    # Check for violations
    violations = []
    for learning in relevant:
        if violates_learning(action, learning):
            violations.append(learning)

    if violations:
        # Block action and log prevention
        await log_error_prevention(agent_name, action, violations)
        return {"blocked": True, "reasons": violations}

    return {"allowed": True}
```

## Integration Points

### Agent Base Class Integration

```python
class BaseAgent:
    async def process_task(self, task: dict) -> dict:
        """
        Override to include learning retrieval.
        """
        # Get learnings
        learnings = await self.get_learnings()

        # Add to context
        context = self.system_prompt + self.format_learnings(learnings)

        # Process
        result = await self.claude_client.query(context, task)

        # Evaluate and potentially learn
        if self.should_analyze_result(result):
            await self.extract_learning(task, result)

        return result
```

### Integration Client Integration

```python
class BaseIntegrationClient:
    async def request(self, method: str, endpoint: str, **kwargs):
        """
        Override to capture and learn from failures.
        """
        try:
            response = await self._request(method, endpoint, **kwargs)
            return response

        except Exception as e:
            # Capture error with full context
            await capture_error(
                agent_name=self.name,
                error=e,
                context={"method": method, "endpoint": endpoint}
            )

            # Try recovery based on learnings
            learning = await get_learning_for_error(type(e).__name__)
            if learning:
                return await self.recover_using_learning(learning)

            raise
```

## Monitoring Learning Health

### Key Metrics

```python
# Learning effectiveness
learning_success_rate = (
    successful_applications / total_applications
)

# Error prevention rate
errors_prevented = (
    escalations_caught_by_learnings / total_potential_errors
)

# Learning quality
avg_confidence_score = (
    avg(learning.confidence for learning in active_learnings)
)

# Learning adoption
learnings_applied = (
    learnings_used_in_decisions / total_learnings
)
```

### Dashboards

**Error Trends Dashboard**
- Errors by type (rate limiting, validation, timeout, etc.)
- Errors by agent (which agents have most issues)
- Error severity distribution
- Recovery success rates

**Learning Dashboard**
- Active learnings count
- Average confidence scores
- Learning application rates
- Improvement metrics by agent

**Effectiveness Dashboard**
- Success rate trend (improving over time)
- Error prevention rate
- Repeated errors (should decrease)
- Knowledge base coverage (% of tasks with learnings)

## Implementation Checklist

### Phase 1: Error Capture (Foundation)
- [ ] Implement error_logs table (migration 005)
- [ ] Create capture_error() function
- [ ] Add error context capture in all agents
- [ ] Add error context capture in all integrations
- [ ] Implement error analysis system

### Phase 2: Knowledge Storage (Learning)
- [ ] Implement knowledge_base table (migration 007)
- [ ] Create learning extraction rules
- [ ] Implement confidence scoring
- [ ] Create learning validation system
- [ ] Add learning update mechanism

### Phase 3: Agent Integration (Application)
- [ ] Modify BaseAgent to retrieve learnings
- [ ] Add learnings to system prompts
- [ ] Implement error prevention checks
- [ ] Create feedback loop for agents
- [ ] Test learning effectiveness

### Phase 4: Monitoring & Dashboards (Visibility)
- [ ] Create monitoring queries
- [ ] Build error trend dashboard
- [ ] Build learning effectiveness dashboard
- [ ] Implement alerting for critical patterns
- [ ] Create weekly learning reports

## Example: Lead Qualifier Learning

### Scenario
Lead qualifier agent fails 15 times due to invalid email formats not being caught.

### Error Capture
```
error_type: INVALID_EMAIL_FORMAT
agent_name: lead_qualifier
affected_entities: [15 lead IDs]
error_context: {
    "input_email": "test@example.c",
    "validation": "TLD too short",
    "expected": "valid email",
    "actual": "validation error later"
}
```

### Learning Extraction
```
Rule created:
- agent_name: lead_qualifier
- error_type: INVALID_EMAIL_FORMAT
- pattern: "15 similar email validation failures"
- rule_type: validate
- rule_action: "Run email regex check BEFORE qualification"
- confidence: 0.93
```

### Agent Application
System prompt now includes:
```
LEARNING: Always validate email format before qualification.
Check: TLD is 2+ chars, contains @, no spaces, valid domain.
If invalid, request corrected email before proceeding.
```

### Result
- Next 100 lead qualification tasks: 0 email-related errors
- Confidence increases to 0.99
- Learning applied 100+ times
- Saved 5+ hours of error recovery

## Best Practices

1. **Document Everything** - Capture every error with full context
2. **Extract Patterns Early** - After 3 similar errors, investigate pattern
3. **Validate Learnings** - Ensure rules actually improve success rates
4. **Review Regularly** - Weekly learning analysis to catch conflicts
5. **Monitor Effectiveness** - Track success rate improvements
6. **Build Confidence** - Start with high-confidence rules
7. **Iterate** - Continuously refine learnings based on outcomes
8. **Share Across Agents** - Common learnings apply to similar agents
9. **Archive Old Learnings** - Remove rules that stop working
10. **Explain Decisions** - Log why each learning was created

## Related Tables

- `audit_logs` - Complete action history
- `error_logs` - Captured errors (migration 005)
- `health_checks` - System health status
- `api_usage` - API performance metrics
- `knowledge_base` - Learned rules (migration 007)
- `response_tracking` - Decision quality tracking (migration 007)
- `agent_learning` - Per-agent improvement metrics (migration 007)
- `faq_management` - Frequently answered questions (migration 007)

## Future Enhancements

- [ ] Automatic A/B testing of learnings
- [ ] ML-based confidence scoring
- [ ] Conflicting learning detection
- [ ] Cross-agent learning transfer
- [ ] Gradual learning deprecation
- [ ] Learning impact analysis
- [ ] Predictive error detection
- [ ] Multi-level learning (agent, team, org)

---

## Documented Error Learnings

### Claude Agent SDK Errors

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-001 | ANTHROPIC_API_KEY conflicts | Critical | `Command failed with exit code 1` | SDK uses `claude` CLI with own auth; env var conflicts | Having `ANTHROPIC_API_KEY` set in environment | `os.environ.pop("ANTHROPIC_API_KEY", None)` before SDK calls | All Claude SDK agents using `query()` |
| LEARN-003 | SDK tools reject dependencies | High | `Tool signature mismatch` | SDK @tool functions must be self-contained, no DI | `@tool async def fn(query: str, client: Client)` | `@tool async def fn(query: str):` then create client inside function body | All @tool decorated functions |
| LEARN-005 | WebSearch ignores site: | Low | Search returns generic results | WebSearch is not Google; operators ignored | `prompt = "site:reddit.com AI tools"` | `prompt = "Reddit discussions about AI tools"` | All WebSearch/WebFetch prompts |
| LEARN-011 | mcp_servers must be dict | Critical | Tools not available to agent | SDK expects `{"name": server}` not `[server]` | `mcp_servers=[mcp_server]` | `mcp_servers={"lead_tools": mcp_server}` | All ClaudeAgentOptions with MCP |
| LEARN-012 | query() is async iterator | Critical | `TypeError: 'async_generator' object is not awaitable` | `query()` yields messages, doesn't return response object | `response = await query(...); for msg in response.messages:` | `async for message in query(...):` | All agents using SDK query() |
| LEARN-013 | allowed_tools required | High | Agent can't use any tools | SDK requires explicit tool allowlist | `ClaudeAgentOptions(mcp_servers={...})` (no allowed_tools) | `ClaudeAgentOptions(mcp_servers={...}, allowed_tools=["mcp__name__tool"])` | All ClaudeAgentOptions with tools |
| LEARN-014 | system_prompt in options | Med | System prompt ignored | `query()` has no `system` param; goes in options | `query(prompt=..., system=self.system_prompt)` | `ClaudeAgentOptions(system_prompt=self.system_prompt)` | All SDK agent configurations |
| LEARN-015 | Use JSON Schema for tools | Med | MyPy errors, weak validation | Python types (list, int) lack validation constraints | `input_schema={"max_leads": int}` | `input_schema={"type": "object", "properties": {"max_leads": {"type": "integer", "minimum": 1}}}` | All @tool input_schema |
| LEARN-016 | json.loads returns Any | Low | MyPy `no-any-return` error | Must validate type before returning from typed function | `return json.loads(content)` | `parsed = json.loads(content); if isinstance(parsed, dict): return parsed` | All JSON parsing in typed functions |

### Python/Library Errors

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-002 | Tenacity tuple syntax | High | `incompatible type "type[A] \| type[B]"` | `retry_if_exception_type` expects tuple, not union | `retry_if_exception_type(RateLimitError \| APIError)` | `retry_if_exception_type((RateLimitError, APIError))` | All tenacity retry decorators |
| LEARN-004 | Mixed type attributes | Med | `AttributeError: 'X' has no attribute 'y'` | Data from APIs/SDK can be dict or object with varying attr names | `subscriber_count = sub.subscribers` | `subscriber_count = getattr(sub, 'subscribers', None) or getattr(sub, 'subscriber_count', 0)` | All agents processing external API/SDK data |
| LEARN-017 | @tool decorator untyped | Med | `Untyped decorator makes function untyped [misc]` | pre-commit mypy v1.14.1 lacks SDK type stubs; local v1.19.1 differs | `@tool(name="x", ...)` | `@tool(  # type: ignore[misc]` | All @tool decorated functions |
| LEARN-021 | scalar_one_or_none returns Any | Low | MyPy `Returning Any from function` | SQLAlchemy `scalar_one_or_none()` return type not narrowed | `return result.scalar_one_or_none()` | `return result.scalar_one_or_none()  # type: ignore[return-value]` | All repository methods returning single model |
| LEARN-022 | RetryError.last_attempt.exception() | Med | `record_failure expects Exception, got BaseException \| None` | tenacity's `last_attempt.exception()` can return `BaseException` | `circuit_breaker.record_failure(e.last_attempt.exception())` | `exc = e.last_attempt.exception(); circuit_breaker.record_failure(exc if isinstance(exc, Exception) else None)` | All retry utilities with circuit breakers |
| LEARN-023 | datetime.now() naive timezone | Med | Inconsistent timestamps, comparison failures | `datetime.now()` is timezone-naive; UTC required for consistency | `datetime.now()` | `from datetime import UTC; datetime.now(UTC)` | All timestamp fields in orchestrators |

### Google API Errors

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-006 | Google Drive quota exceeded | Critical | `GoogleDocsQuotaError: Quota exceeded: The user's Drive storage quota has been exceeded` | Service accounts have NO storage quota; files must be created in a user's Drive via domain-wide delegation | Not setting `delegated_user` parameter when initializing GoogleDriveClient/GoogleDocsClient | Set `GOOGLE_DELEGATED_USER=user@domain.com` in .env and pass to clients: `GoogleDriveClient(delegated_user=os.getenv('GOOGLE_DELEGATED_USER'))` | All agents using GoogleDriveClient, GoogleDocsClient (ResearchExportAgent, etc.) |

**LEARN-006 Details:**

**Full Problem:**
Service accounts don't have their own Google Drive storage. When creating files without domain-wide delegation, they hit quota errors immediately because they're trying to create files in non-existent service account storage.

**Complete Solution:**
1. **Backend Code:**
   - Add `delegated_user` parameter to agent `__init__`
   - Pass `delegated_user` to GoogleDriveClient and GoogleDocsClient
   - Read from `GOOGLE_DELEGATED_USER` environment variable

   ```python
   # In ResearchExportAgent.__init__()
   self.delegated_user = delegated_user or os.getenv("GOOGLE_DELEGATED_USER")

   self.drive_client = GoogleDriveClient(
       credentials_json=credentials,
       delegated_user=self.delegated_user,
   )

   self.docs_client = GoogleDocsClient(
       credentials_json=credentials,
       delegated_user=self.delegated_user,
   )
   ```

2. **Environment Configuration:**
   ```bash
   # In .env file
   GOOGLE_DELEGATED_USER=yasmine@smarterflo.com
   ```

3. **Google Workspace Admin Console:**
   - Navigate to: Security → API Controls → Domain-wide Delegation
   - Add service account Client ID: `100100768773360796850`
   - Authorize scopes (comma-separated on one line):
     ```
     https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents
     ```

4. **Google Drive Sharing:**
   - Share parent folder with service account email
   - Service account email format: `projectname@projectid.iam.gserviceaccount.com`

**Related Bugs Fixed:**
- **GoogleDocsClient scope error**: When using `delegated_user`, client was only requesting `documents` scope but also needs `drive.file` scope for document creation via Drive API
  ```python
  # In GoogleDocsClient._authenticate_service_account()
  if self.delegated_user:
      scopes = [
          "https://www.googleapis.com/auth/documents",
          "https://www.googleapis.com/auth/drive.file",  # REQUIRED!
      ]
  ```

- **GoogleDriveClient metadata validation error**: `get_file_metadata(fields="parents")` returns partial response but code tried to validate as full `DriveMetadata` model
  ```python
  # In GoogleDriveClient.get_file_metadata()
  # Return raw dict for partial field requests, not DriveMetadata
  if fields == default_fields:
      return DriveMetadata(**response)
  else:
      return response  # Return dict for custom fields
  ```

**Testing:**
- Integration tests: 4/4 passing with real Google API
- Unit tests: 14/14 passing
- Quality checks: All passing (lint, format, type, security)

**Prevention:**
Always use domain-wide delegation for service accounts that need to create Google Workspace assets (Drive files, Docs, Sheets, etc.). Service accounts can only own temporary/system files in their own storage space (~16GB limit), not user-facing documents.

### Multi-Agent Ecosystem Errors

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-007 | Agents not persisting data | Critical | Agents return results but DB stays empty | Agents designed to be pure (no side effects); no layer handling persistence | `result = await agent.run(); return result` | Create orchestrator that calls agent THEN persists via repository | All multi-agent pipelines |
| LEARN-008 | Missing SQLAlchemy models | High | `AttributeError` when trying to query tables | Tables exist in Supabase but no ORM models in codebase | Querying tables that don't have models | Create SQLAlchemy models matching Supabase schema exactly | All agents needing DB access |
| LEARN-009 | Alembic vs Supabase drift | Med | Alembic shows 1 migration but DB has 100+ tables | Tables created via Supabase dashboard, not Alembic | Assuming Alembic is source of truth | Check `DATABASE_TABLES.txt` export for actual schema | New developers, schema changes |
| LEARN-010 | Missing FK columns | High | Agent expects `personas.niche_id` but column missing | YAML spec defined relationship but schema didn't have FK | `persona.niche_id = niche_id` (fails) | Add FK column: `ALTER TABLE personas ADD COLUMN niche_id UUID REFERENCES niches(id)` | All agents with cross-table relationships |
| LEARN-024 | Repository API drift | High | `TypeError` or `AttributeError` at runtime | Orchestrator calls repository method with wrong params/name | `lead_repo.update_lead(id, data)` | Verify method signature before calling; use IDE autocomplete or read repository source | All orchestrators calling repositories |
| LEARN-025 | MyPy hooks check ALL files | Med | Pre-commit blocks on unrelated file errors | MyPy pre-commit hook validates entire codebase, not just staged files | Commit blocked by errors in untracked/unstaged files | Fix untracked file errors OR use `SKIP=mypy` for security-passing commits | All commits when codebase has type errors |
| LEARN-026 | SDK now has type stubs | Low | `Unused "type: ignore" comment` warnings | Claude Agent SDK added proper type stubs; `# type: ignore[misc]` on `@tool` no longer needed | `@tool(  # type: ignore[misc]` shows unused | Can remove `# type: ignore[misc]` from `@tool` decorators; SDK stubs now provide types | All `@tool` decorated functions |
| LEARN-027 | Duplicate utility classes | Med | Maintenance burden, subtle behavioral drift | Same utility (rate limiter, circuit breaker) implemented multiple times in different agents | Local `class TokenBucketRateLimiter` in each agent | Use shared `from src.utils.rate_limiter import TokenBucketRateLimiter` | All agents needing rate limiting |

**LEARN-007 Details:**

**Problem:**
Claude Agent SDK agents are designed to be **pure functions** - they take inputs, do research, return results. They don't handle database persistence. This is good design (testable, composable), but means you need an **orchestrator layer** to:
1. Call the agent
2. Take the result
3. Persist to database via repository
4. Pass handoff data to next agent

**Wrong Pattern:**
```python
# Agent handles everything (breaks single responsibility)
class NicheResearchAgent:
    async def run(self, niche_name: str, session: AsyncSession):
        result = await self._research(niche_name)
        await session.execute(insert(niches).values(...))  # BAD: agent shouldn't know about DB
        return result
```

**Correct Pattern:**
```python
# Agent is pure
class NicheResearchAgent:
    async def run(self, niche_name: str) -> NicheResearchResult:
        return await self._research(niche_name)  # Just returns result

# Orchestrator handles persistence
class Phase1Orchestrator:
    async def run(self, niche_name: str):
        result = await self.niche_agent.run(niche_name)
        await self.niche_repo.create_niche(result)  # Orchestrator persists
        await self.niche_repo.create_niche_scores(result)
        return result
```

**LEARN-008 Details:**

**Problem:**
Tables exist in Supabase (created via dashboard) but the Python codebase has no SQLAlchemy models. This means:
- Can't use ORM queries
- Can't use relationships
- No type safety for DB operations

**Solution:**
1. Export schema: `DATABASE_TABLES_WITH_FIELDS.txt`
2. Create SQLAlchemy models matching exact column names/types
3. Use `ARRAY(Text)` for Postgres arrays
4. Use `JSONB` for JSON columns
5. Add `to_dict()` method for agent compatibility

```python
class NicheModel(Base):
    __tablename__ = "niches"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(ARRAY(Text), nullable=True)  # Match exact Supabase type
    # ... etc
```

**LEARN-010 Details:**

**Problem:**
YAML spec defines agent handoffs with fields like `niche_id`, but the actual database table is missing the foreign key column.

**Detection:**
```bash
# Check if column exists
grep "niche_id" DATABASE_TABLES_WITH_FIELDS.txt | grep personas
# If no output, column is missing
```

**Fix:**
```sql
-- Add missing FK
ALTER TABLE personas ADD COLUMN niche_id UUID REFERENCES niches(id);
CREATE INDEX ix_personas_niche_id ON personas(niche_id);
```

**Prevention:**
Before building multi-agent systems:
1. Validate all YAML specs against actual database schema
2. Create migration for any missing columns
3. Update SQLAlchemy models to match

**LEARN-011 Details:**

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-011 | ClaudeAgentOptions missing allowed_tools | Critical | Claude cannot invoke any MCP tools | SDK defaults to no tools when `allowed_tools` not specified | `ClaudeAgentOptions(mcp_servers={...})` | `ClaudeAgentOptions(mcp_servers={...}, allowed_tools=["mcp__server__tool"])` | All SDK agents using MCP tools |

**Problem:**
When creating `ClaudeAgentOptions` with MCP servers but without `allowed_tools`, Claude cannot invoke ANY tools. The SDK requires explicit tool permissions.

**Fix:**
```python
# Tool names follow pattern: mcp__{server_name}__{tool_name}
tool_names = [
    "mcp__my_server__my_tool",
    "mcp__my_server__other_tool",
]

options = ClaudeAgentOptions(
    model=self.model,
    system_prompt=self.system_prompt,
    mcp_servers={"my_server": mcp_server},
    allowed_tools=tool_names,  # REQUIRED for tool access
)
```

**LEARN-012 Details:**

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-012 | Missing setting_sources | High | CLAUDE.md instructions not loaded | SDK doesn't load project settings by default | `ClaudeAgentOptions(...)` | `ClaudeAgentOptions(..., setting_sources=["project"])` | All SDK agents needing project context |

**Problem:**
Without `setting_sources=["project"]`, the SDK does not read CLAUDE.md instructions. Agents miss critical project-specific guidance.

**Fix:**
```python
options = ClaudeAgentOptions(
    model=self.model,
    system_prompt=self.system_prompt,
    setting_sources=["project"],  # Loads CLAUDE.md
    mcp_servers={...},
    allowed_tools=[...],
)
```

**LEARN-013 Details:**

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-013 | @tool decorator mypy handling | Low | `Untyped decorator` OR `Unused "type: ignore"` | SDK @tool decorator lacks type stubs; behavior varies by mypy config | See below | See below | All @tool decorated functions |

**Problem:**
The `@tool` decorator from `claude_agent_sdk` doesn't have type stubs. Mypy behavior depends on configuration:
- With `--ignore-missing-imports`: No error, `# type: ignore[misc]` causes "unused" warning
- Without that flag: "Untyped decorator" error requires the ignore comment

**Fix:**
```python
# When running mypy WITH --ignore-missing-imports (recommended):
@tool(
    name="my_tool",
    description="...",
    input_schema={...},  # Use JSON Schema format per LEARN-015
)
async def my_tool(args: dict[str, Any]) -> dict[str, Any]:
    ...

# When running mypy WITHOUT --ignore-missing-imports:
@tool(  # type: ignore[misc]
    name="my_tool",
    ...
)
```

**Recommendation:** Use `--ignore-missing-imports` in pyproject.toml and omit the type: ignore comment.

**LEARN-014 Details:**

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-014 | Testing SDK tools directly | Med | `TypeError: 'SdkMcpTool' object is not callable` | @tool returns SdkMcpTool wrapper, not function | `await my_tool({...})` | `await my_tool.handler({...})` | All unit tests for SDK MCP tools |

**Problem:**
The `@tool` decorator wraps the async function in an `SdkMcpTool` object. To test the tool directly, access `.handler`.

**Fix:**
```python
from my_module import my_tool

# Access the underlying handler for testing
_my_tool = my_tool.handler

@pytest.mark.asyncio
async def test_my_tool():
    result = await _my_tool({"arg": "value"})
    assert result["content"][0]["text"] == "expected"
```

---

**LEARN-024 Details:**

**Problem:**
Orchestrators (Phase1, Phase2, Phase3, Master) call repository methods, but the method signatures and names drift during development. Common mismatches:

1. **Method name changes**: `mark_as_cross_campaign_duplicate` → `mark_cross_campaign_duplicate`
2. **Parameter name changes**: `score_breakdown` → `breakdown`
3. **Attribute name changes**: `linkedin_leads` → `primary_actor_leads`
4. **Extra parameters**: Passing parameters repository doesn't accept
5. **Missing methods**: Calling methods that don't exist

**Examples Fixed:**
```python
# WRONG - extra parameters
await lead_repo.update_lead_validation(
    lead_id=id, is_valid=True, validation_errors=[],
    validation_status="valid",  # DOESN'T EXIST
    normalized_data={}          # DOESN'T EXIST
)

# CORRECT - only accepted params
await lead_repo.update_lead_validation(
    lead_id=id, is_valid=True, validation_errors=[]
)

# WRONG - old method name
await lead_repo.mark_as_cross_campaign_duplicate(...)

# CORRECT - actual method name
await lead_repo.mark_cross_campaign_duplicate(...)

# WRONG - old attribute name
result.linkedin_leads

# CORRECT - actual attribute name
result.primary_actor_leads
```

**Prevention:**
1. Read repository source before calling methods
2. Use IDE autocomplete for method signatures
3. Run type checker after connecting orchestrator to repository
4. Add integration tests that exercise full orchestrator → repository flow

---

**LEARN-018 Details:**

| ID | Error | Sev | Symptom | Root Cause | Wrong Code | Correct Code | Affects |
|----|-------|-----|---------|------------|------------|--------------|---------|
| LEARN-018 | YAML duplicate keys | Med | `found duplicate key "X" with value` | Same key appears twice under same parent | Two `output:` blocks in one step | Merge duplicates or rename | All YAML agent specs |
| LEARN-019 | YAML block collection | Med | `did not find expected '-' indicator` | Sibling key at wrong indent after list | `conditions:\n  - "x"\n  description:` | `conditions:\n  - "x"  # comment` | YAML specs with conditions |
| LEARN-020 | YAML flow mapping brackets | Low | `did not find expected ',' or '}'` | Special chars like `[]` in inline dict | `type: text[]` | `type: "text[]"` | YAML with PostgreSQL array types |

**Problem:**
YAML specs can fail pre-commit checks due to subtle syntax issues. Common problems:
1. **Duplicate keys** - Two keys with same name at same level (e.g., two `output:` blocks)
2. **Block collection misalignment** - A key after a list item at wrong indentation
3. **Unquoted special characters** - PostgreSQL types like `text[]` need quoting

**Fix Examples:**
```yaml
# WRONG - description is sibling to list item
conditions:
  - "total >= 1"
  description: "Some text"

# CORRECT - use comment instead
conditions:
  - "total >= 1"  # Some text

# WRONG - special chars unquoted
persona_tags: { type: text[] }

# CORRECT - quote special chars
persona_tags: { type: "text[]" }
```
