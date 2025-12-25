# Task: Cold Email Infrastructure & Database Schema

**Status:** Pending
**Domain:** backend
**Phase:** Infrastructure
**Source:** cold-email-agents/ + infrastructure/retry.py
**Created:** 2025-12-23

---

## MUST-DO CHECKLIST

### Context & SDK Requirements (NON-NEGOTIABLE)
- [ ] Read ALL files in `.claude/context/` before writing any code
  - [ ] `TASK_RULES.md`, `CODE_QUALITY_RULES.md`, `TESTING_RULES.md`, `PROJECT_CONTEXT.md`
  - [ ] `SDK_PATTERNS.md` - Claude Agent SDK patterns (Python version)
  - [ ] `SELF_HEALING.md` - Known errors and solutions (READ before coding, ADD to when you solve issues)
  - [ ] `GOOGLE_INTEGRATIONS_LEARNING.md` - Google API learnings

- [ ] Follow database migration patterns from specs/database-schema/migrations/
- [ ] Swagger docs in `docs/api/`
- [ ] Tests: unit >90%, integration tests
- [ ] Code quality: ruff, mypy strict, pre-commit

### Self-Healing & Learning (NON-NEGOTIABLE)
- [ ] **READ SELF_HEALING.md before starting** - Check for known errors/solutions
- [ ] **If you encounter any error and find a solution:**
  - [ ] Document it immediately in `.claude/context/SELF_HEALING.md`
  - [ ] Format: `## [Infrastructure] - [Error Description]`

---

## Summary

Create infrastructure components and database schema for cold email workflow. Includes retry module, database tables, and base agent classes.

---

## Files to Create/Modify

### Infrastructure
- [ ] `app/backend/src/infrastructure/retry.py` - Copy from cold-email-agents/infrastructure/retry.py
- [ ] `app/backend/src/agents/base.py` - Base agent class with Claude SDK patterns

### Database Migrations
- [ ] `specs/database-schema/migrations/020_cold_email_tables.sql`

---

## Database Tables Required

```sql
-- Niches
CREATE TABLE niches (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  industry JSONB,
  job_titles JSONB,
  company_size JSONB,
  location JSONB,
  pain_points JSONB,
  value_propositions JSONB,
  messaging_tone TEXT,
  research_folder_url TEXT,
  status TEXT,
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Niche Scores
CREATE TABLE niche_scores (
  id UUID PRIMARY KEY,
  niche_id UUID REFERENCES niches(id),
  overall_score INTEGER,
  market_size_score INTEGER,
  competition_score INTEGER,
  reachability_score INTEGER,
  pain_intensity_score INTEGER,
  budget_authority_score INTEGER,
  confidence FLOAT,
  recommendation TEXT,
  scoring_details JSONB,
  research_sources JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Niche Research Data (full research findings for downstream agents)
CREATE TABLE niche_research_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id UUID NOT NULL REFERENCES niches(id) ON DELETE CASCADE,

  -- Market Size Research
  market_size_estimate TEXT,
  company_count_estimate INTEGER,
  persona_count_estimate INTEGER,
  growth_rate TEXT,
  market_data_sources JSONB DEFAULT '{}'::jsonb,

  -- Competition Research
  competitors_found JSONB DEFAULT '{}'::jsonb,
  saturation_level TEXT,
  differentiation_opportunities JSONB DEFAULT '[]'::jsonb,
  inbox_fatigue_indicators JSONB DEFAULT '[]'::jsonb,

  -- Reachability Research
  linkedin_presence TEXT,
  data_availability TEXT,
  email_findability TEXT,
  public_presence_level TEXT,
  data_sources_found JSONB DEFAULT '{}'::jsonb,

  -- Pain Points Research
  pain_points_detailed JSONB DEFAULT '[]'::jsonb,
  pain_intensity TEXT,
  pain_urgency TEXT,
  pain_point_quotes JSONB DEFAULT '[]'::jsonb,
  evidence_sources JSONB DEFAULT '{}'::jsonb,

  -- Budget Authority Research
  has_budget_authority BOOLEAN,
  typical_budget_range TEXT,
  decision_process TEXT,
  buying_triggers JSONB DEFAULT '[]'::jsonb,

  -- Meta
  research_duration_ms INTEGER,
  tools_used JSONB DEFAULT '[]'::jsonb,
  queries_executed JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(niche_id)
);

-- Index for niche_research_data
CREATE INDEX idx_niche_research_data_niche_id ON niche_research_data(niche_id);

-- Personas
CREATE TABLE personas (
  id UUID PRIMARY KEY,
  niche_id UUID REFERENCES niches(id),
  name TEXT NOT NULL,
  job_titles JSONB,
  seniority_level TEXT,
  department TEXT,
  pain_points JSONB,
  goals JSONB,
  objections JSONB,
  language_patterns JSONB,
  trigger_events JSONB,
  messaging_angles JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Persona Research Data
CREATE TABLE persona_research_data (
  id UUID PRIMARY KEY,
  persona_id UUID REFERENCES personas(id),
  source TEXT,
  source_url TEXT,
  content_type TEXT,
  raw_content TEXT,
  extracted_insights JSONB,
  language_samples JSONB,
  pain_point_quotes JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Industry Fit Scores
CREATE TABLE industry_fit_scores (
  id UUID PRIMARY KEY,
  niche_id UUID REFERENCES niches(id),
  industry TEXT,
  fit_score INTEGER,
  reasoning TEXT,
  pain_point_alignment JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(niche_id, industry)
);

-- Campaigns
CREATE TABLE campaigns (
  id UUID PRIMARY KEY,
  niche_id UUID REFERENCES niches(id),
  name TEXT NOT NULL,
  status TEXT,
  target_leads INTEGER,
  total_leads_scraped INTEGER,
  scraping_cost NUMERIC,
  instantly_campaign_id TEXT,
  instantly_campaign_url TEXT,
  total_sent INTEGER,
  total_opened INTEGER,
  total_replied INTEGER,
  total_bounced INTEGER,
  -- From Agent 2.2 (Data Validation)
  total_leads_valid INTEGER,
  total_leads_invalid INTEGER,
  validation_completed_at TIMESTAMPTZ,
  -- From Agent 2.3 (Duplicate Detection)
  total_duplicates_found INTEGER,
  total_leads_unique INTEGER,
  dedup_completed_at TIMESTAMPTZ,
  -- From Agent 2.4 (Cross-Campaign Dedup)
  total_cross_duplicates INTEGER,
  total_leads_available INTEGER,
  cross_dedup_completed_at TIMESTAMPTZ,
  -- From Agent 2.5 (Lead Scoring)
  leads_scored INTEGER,
  avg_lead_score NUMERIC,
  leads_tier_a INTEGER,
  leads_tier_b INTEGER,
  leads_tier_c INTEGER,
  scoring_completed_at TIMESTAMPTZ,
  -- From Agent 2.6 (Import Finalizer)
  lead_list_url TEXT,
  import_summary JSONB DEFAULT '{}'::jsonb,
  import_completed_at TIMESTAMPTZ,
  leads_approved_at TIMESTAMPTZ,
  leads_approved_by VARCHAR,
  -- From Agent 3.1 (Email Verification)
  emails_found INTEGER,
  emails_verified INTEGER,
  -- From Agent 3.2 (Waterfall Enrichment)
  leads_enriched INTEGER,
  enrichment_cost NUMERIC DEFAULT 0,
  enrichment_completed_at TIMESTAMPTZ,
  -- From Agent 3.3 (Verification Finalizer)
  verified_lead_list_url TEXT,
  verification_summary JSONB DEFAULT '{}'::jsonb,
  total_leads_ready INTEGER,
  verification_completed_at TIMESTAMPTZ,
  -- From Agent 4.4 (Personalization Finalizer)
  email_samples_url TEXT,
  personalization_summary JSONB DEFAULT '{}'::jsonb,
  total_emails_generated INTEGER,
  avg_email_quality NUMERIC,
  personalization_completed_at TIMESTAMPTZ,
  sending_approved_at TIMESTAMPTZ,
  sending_approved_by VARCHAR,
  sending_scope VARCHAR,
  -- From Agent 5.1-5.2 (Campaign Execution)
  sending_status VARCHAR,
  setup_completed_at TIMESTAMPTZ,
  leads_queued INTEGER,
  -- Research folder URL (from Agent 1.3)
  research_folder_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Leads
CREATE TABLE leads (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id),
  linkedin_url TEXT,
  linkedin_id TEXT,
  first_name TEXT,
  last_name TEXT,
  full_name TEXT,
  headline TEXT,
  job_title TEXT,
  seniority TEXT,
  department TEXT,
  company_name TEXT,
  company_linkedin_url TEXT,
  company_domain TEXT,
  company_size TEXT,
  company_industry TEXT,
  location TEXT,
  city TEXT,
  state TEXT,
  country TEXT,
  email TEXT,
  email_status TEXT,
  email_verified BOOLEAN,
  source TEXT,
  source_url TEXT,
  status TEXT,
  lead_score INTEGER DEFAULT 0,
  lead_tier TEXT,
  score_breakdown JSONB DEFAULT '{}'::jsonb,
  persona_tags TEXT[] DEFAULT '{}'::text[],
  -- From Agent 3.1 (Email Verification)
  email_provider VARCHAR,
  email_confidence NUMERIC,
  email_verified_at TIMESTAMPTZ,
  -- From Agent 3.2 (Waterfall Enrichment)
  company_description TEXT,
  company_employee_count INTEGER,
  company_revenue_range VARCHAR,
  company_founded_year INTEGER,
  company_tech_stack JSONB DEFAULT '{}'::jsonb,
  company_keywords JSONB DEFAULT '[]'::jsonb,
  enrichment_data JSONB DEFAULT '{}'::jsonb,
  enrichment_status VARCHAR,
  enrichment_cost NUMERIC DEFAULT 0,
  enrichment_completed_at TIMESTAMPTZ,
  -- From Agent 4.1-4.3 (Research & Generation)
  company_research_id UUID REFERENCES company_research(id),
  lead_research_id UUID REFERENCES lead_research(id),
  generated_email_id UUID REFERENCES generated_emails(id),
  email_generation_status VARCHAR,
  -- From Agent 5.2-5.3 (Campaign Execution)
  sending_status VARCHAR,
  instantly_lead_id VARCHAR,
  queued_at TIMESTAMPTZ,
  reply_status VARCHAR,
  replied_at TIMESTAMPTZ,
  reply_count INTEGER DEFAULT 0,
  duplicate_of UUID REFERENCES leads(id),
  exclusion_reason TEXT,
  excluded_due_to_campaign UUID REFERENCES campaigns(id),
  last_contacted_at TIMESTAMPTZ,
  merged_from JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Company Research
CREATE TABLE company_research (
  id UUID PRIMARY KEY,
  company_name TEXT NOT NULL,
  company_domain TEXT UNIQUE,
  company_description TEXT,
  recent_news JSONB DEFAULT '{}'::jsonb,
  funding_info JSONB DEFAULT '{}'::jsonb,
  hiring_signals JSONB DEFAULT '{}'::jsonb,
  growth_metrics JSONB DEFAULT '{}'::jsonb,
  personalization_hooks JSONB DEFAULT '[]'::jsonb,
  talking_points JSONB DEFAULT '[]'::jsonb,
  research_sources JSONB DEFAULT '[]'::jsonb,
  researched_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lead Research
CREATE TABLE lead_research (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID UNIQUE REFERENCES leads(id),
  linkedin_posts JSONB DEFAULT '[]'::jsonb,
  articles JSONB DEFAULT '[]'::jsonb,
  podcasts JSONB DEFAULT '[]'::jsonb,
  talks JSONB DEFAULT '[]'::jsonb,
  opening_line TEXT,
  personalization_hooks JSONB DEFAULT '[]'::jsonb,
  opening_line_suggestions JSONB DEFAULT '[]'::jsonb,
  research_depth VARCHAR,
  researched_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated Emails
CREATE TABLE generated_emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  campaign_id UUID REFERENCES campaigns(id),
  subject_line TEXT,
  opening_line TEXT,
  body TEXT,
  cta TEXT,
  full_email TEXT,
  framework_used VARCHAR,
  personalization_level VARCHAR,
  quality_score INTEGER DEFAULT 0,
  score_breakdown JSONB DEFAULT '{}'::jsonb,
  generation_prompt TEXT,
  generation_model VARCHAR,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Replies (email_replies)
CREATE TABLE replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  campaign_id UUID NOT NULL REFERENCES campaigns(id),
  instantly_reply_id VARCHAR,
  reply_text TEXT,
  reply_subject TEXT,
  category VARCHAR,
  confidence NUMERIC,
  sentiment VARCHAR,
  action_taken VARCHAR,
  received_at TIMESTAMPTZ,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign Metrics
CREATE TABLE campaign_metrics (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id),
  metric_type TEXT,
  sent INTEGER,
  delivered INTEGER,
  opened INTEGER,
  clicked INTEGER,
  replied INTEGER,
  bounced INTEGER,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deduplication Logs
CREATE TABLE dedup_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  total_checked INTEGER NOT NULL,
  exact_duplicates INTEGER NOT NULL DEFAULT 0,
  fuzzy_duplicates INTEGER NOT NULL DEFAULT 0,
  total_merged INTEGER NOT NULL DEFAULT 0,
  detection_details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for dedup_logs
CREATE INDEX idx_dedup_logs_campaign_id ON dedup_logs(campaign_id);

-- Suppression List (global exclusions - do not contact)
CREATE TABLE suppression_list (
  email VARCHAR PRIMARY KEY,
  suppressed_at TIMESTAMPTZ,
  added_by VARCHAR,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cross Campaign Dedup Logs
CREATE TABLE cross_campaign_dedup_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  total_checked INTEGER NOT NULL,
  previously_contacted INTEGER NOT NULL DEFAULT 0,
  bounced_excluded INTEGER NOT NULL DEFAULT 0,
  unsubscribed_excluded INTEGER NOT NULL DEFAULT 0,
  suppression_list_excluded INTEGER NOT NULL DEFAULT 0,
  remaining_leads INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for cross_campaign_dedup_logs
CREATE INDEX idx_cross_campaign_dedup_logs_campaign_id ON cross_campaign_dedup_logs(campaign_id);

-- Phase 5 Tables (Campaign Execution)

-- Email Accounts (sending accounts)
CREATE TABLE email_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR UNIQUE NOT NULL,
  display_name VARCHAR,
  provider VARCHAR,
  status VARCHAR DEFAULT 'active',
  warmup_status VARCHAR,
  daily_limit INTEGER DEFAULT 50,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Instantly Campaigns (integration tracking)
CREATE TABLE instantly_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  instantly_campaign_id VARCHAR UNIQUE NOT NULL,
  instantly_campaign_url TEXT,
  status VARCHAR DEFAULT 'created',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reply Monitoring State (tracking state)
CREATE TABLE reply_monitoring_state (
  campaign_id UUID PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
  last_reply_id VARCHAR,
  last_checked_at TIMESTAMPTZ,
  total_replies INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sending Logs (batch upload tracking)
CREATE TABLE sending_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  batch_number INTEGER NOT NULL,
  leads_uploaded INTEGER NOT NULL,
  status VARCHAR DEFAULT 'uploaded',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign Alerts (monitoring alerts)
CREATE TABLE campaign_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  alert_type VARCHAR NOT NULL,
  severity VARCHAR,
  message TEXT,
  action_taken VARCHAR,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow Checkpoints
CREATE TABLE workflow_checkpoints (
  id UUID PRIMARY KEY,
  agent_id TEXT,
  campaign_id UUID REFERENCES campaigns(id),
  step_id TEXT,
  checkpoint_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign Audit Log
CREATE TABLE campaign_audit_log (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id),
  action TEXT,
  actor TEXT,
  actor_type TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Verification

```bash
# Run migration
psql -h localhost -U postgres -d smarter_team -f specs/database-schema/migrations/020_cold_email_tables.sql

# Verify tables
psql -h localhost -U postgres -d smarter_team -c "\dt"

# Run tests
pytest app/backend/__tests__/unit/infrastructure/test_retry.py -v
```

---

## Next Steps

After this infrastructure task is complete, the 20 agent tasks (001-020) can be implemented in order.
