# Task: Create Phase 1 Database Tables

**Priority:** CRITICAL (Blocking)
**Domain:** Database
**Affects:** All Phase 1 agents (1.1, 1.2, 1.3)

## Summary

Create the 7 database tables required by Phase 1 agents. Without these tables, agents cannot persist research data or read from previous agent runs.

## Tables to Create

### 1. `niches` table
```sql
CREATE TABLE niches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    industry JSONB NOT NULL DEFAULT '[]',
    job_titles JSONB NOT NULL DEFAULT '[]',
    company_size JSONB NOT NULL DEFAULT '[]',
    location JSONB NOT NULL DEFAULT '[]',
    pain_points JSONB DEFAULT '[]',
    value_propositions JSONB DEFAULT '[]',
    messaging_tone VARCHAR(50),
    research_folder_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'researching',
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(255),
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_niches_slug ON niches(slug);
CREATE INDEX ix_niches_status ON niches(status);
```

### 2. `niche_scores` table
```sql
CREATE TABLE niche_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    market_size_score INTEGER CHECK (market_size_score >= 0 AND market_size_score <= 100),
    competition_score INTEGER CHECK (competition_score >= 0 AND competition_score <= 100),
    reachability_score INTEGER CHECK (reachability_score >= 0 AND reachability_score <= 100),
    pain_intensity_score INTEGER CHECK (pain_intensity_score >= 0 AND pain_intensity_score <= 100),
    budget_authority_score INTEGER CHECK (budget_authority_score >= 0 AND budget_authority_score <= 100),
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    recommendation VARCHAR(20) NOT NULL CHECK (recommendation IN ('proceed', 'review', 'reject')),
    scoring_details JSONB,
    research_sources JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(niche_id)
);

CREATE INDEX ix_niche_scores_niche_id ON niche_scores(niche_id);
```

### 3. `niche_research_data` table
```sql
CREATE TABLE niche_research_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID NOT NULL REFERENCES niches(id) ON DELETE CASCADE,

    -- Market Size Research
    market_size_estimate TEXT,
    company_count_estimate INTEGER,
    persona_count_estimate INTEGER,
    growth_rate TEXT,
    market_data_sources JSONB,

    -- Competition Research
    competitors_found JSONB,
    saturation_level VARCHAR(20),
    differentiation_opportunities JSONB,
    inbox_fatigue_indicators JSONB,

    -- Reachability Research
    linkedin_presence VARCHAR(20),
    data_availability VARCHAR(20),
    email_findability VARCHAR(20),
    public_presence_level VARCHAR(50),
    data_sources_found JSONB,

    -- Pain Points Research
    pain_points_detailed JSONB,
    pain_intensity VARCHAR(20),
    pain_urgency VARCHAR(20),
    pain_point_quotes JSONB,
    evidence_sources JSONB,

    -- Budget Authority Research
    has_budget_authority BOOLEAN,
    typical_budget_range TEXT,
    decision_process VARCHAR(50),
    buying_triggers JSONB,

    -- Meta
    research_duration_ms INTEGER,
    tools_used JSONB,
    queries_executed JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(niche_id)
);
```

### 4. `personas` table
```sql
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    job_titles JSONB NOT NULL DEFAULT '[]',
    seniority_level VARCHAR(20) NOT NULL,
    department VARCHAR(100),
    pain_points JSONB NOT NULL DEFAULT '[]',
    goals JSONB DEFAULT '[]',
    objections JSONB DEFAULT '[]',
    language_patterns JSONB DEFAULT '[]',
    trigger_events JSONB DEFAULT '[]',
    messaging_angles JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_personas_niche_id ON personas(niche_id);
```

### 5. `persona_research_data` table
```sql
CREATE TABLE persona_research_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_url TEXT,
    content_type VARCHAR(50),
    raw_content TEXT,
    extracted_insights JSONB,
    language_samples JSONB,
    pain_point_quotes JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_persona_research_persona_id ON persona_research_data(persona_id);
```

### 6. `industry_fit_scores` table
```sql
CREATE TABLE industry_fit_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
    industry VARCHAR(100) NOT NULL,
    fit_score INTEGER NOT NULL CHECK (fit_score >= 0 AND fit_score <= 100),
    reasoning TEXT,
    pain_point_alignment JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(niche_id, industry)
);

CREATE INDEX ix_industry_fit_scores_niche_id ON industry_fit_scores(niche_id);
```

### 7. `workflow_checkpoints` table
```sql
CREATE TABLE workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    step_id VARCHAR(100) NOT NULL,
    step_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(workflow_id, step_id)
);

CREATE INDEX ix_workflow_checkpoints_workflow_id ON workflow_checkpoints(workflow_id);
```

## Checklist

- [ ] Create Alembic migration file: `alembic revision -m "create_phase1_research_tables"`
- [ ] Add all 7 table definitions with proper constraints
- [ ] Add indexes for foreign keys and common queries
- [ ] Create SQLAlchemy ORM models in `src/database/models.py`
- [ ] Test migration: `alembic upgrade head`
- [ ] Test rollback: `alembic downgrade -1`
- [ ] Update tests if any

## Verification

```bash
# Run migration
cd app/backend
alembic upgrade head

# Verify tables exist (connect to DB)
\dt  # Should show all 7 new tables
```

## Dependencies

- None (this is a blocking dependency for all Phase 1 work)

## Notes

- All JSONB columns use `DEFAULT '{}'` or `DEFAULT '[]'` for safety
- Foreign keys use `ON DELETE CASCADE` for cleanup
- Indexes added for all FK columns and common query patterns
