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
