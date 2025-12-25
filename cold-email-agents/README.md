# Cold Email Workflow v2.0.0 - Agent Specifications

## Overview

This directory contains complete YAML specifications for 20 AI agents that orchestrate an end-to-end cold email workflow. The agents are organized into 5 phases with human approval gates between major phases.

## Key Features

- **Dynamic Tool Discovery**: Agents check which tools are available at runtime
- **Priority-Based Tool Selection**: Free tools (WebSearch, WebFetch) first, expensive tools last
- **Parallel Execution**: Fan-out searches, parallel batch processing
- **Multi-Source Enrichment**: Combines results from multiple search providers
- **Cost Controls**: Budget limits, cost tracking, cheapest-first selection
- **Retry & Circuit Breakers**: Exponential backoff, per-tool circuit breakers
- **Human Gates**: Approval checkpoints between phases

---

## Tool Priority Order (Cheapest First)

### FREE (Always Use First)
1. `claude_web_search` - Claude Agent SDK built-in WebSearch
2. `claude_web_fetch` - Claude Agent SDK built-in WebFetch
3. `reddit_api` - Reddit public search API

### CHEAP (Use for Enrichment)
4. `tavily_search` - ~$0.001/call
5. `brave_search` - ~$0.001/call
6. `serper_search` - ~$0.001/call

### MODERATE (Use Selectively)
7. `perplexity_search` - ~$0.005/call (great for synthesis)

### EXPENSIVE (Last Resort Only)
8. `exa_search` - ~$0.01/call (semantic search)

---

## Phase 1: Market Intelligence

### Agent 1.1: Niche Research Agent
**File**: `phase1/agent_1_1_niche_research.yaml`
**Purpose**: Analyze market viability of target niche
**Features**:
- Parallel searches across 5+ tools simultaneously
- Market size, competition, reachability scoring
- Pain point discovery from Reddit
- 0-100 scoring with proceed/review/reject recommendations

### Agent 1.2: Persona Research Agent
**File**: `phase1/agent_1_2_persona_research.yaml`
**Purpose**: Deep-dive into target personas
**Features**:
- Reddit mining for real pain point quotes
- LinkedIn/professional content analysis
- Language pattern extraction
- Persona profiles with messaging angles

### Agent 1.3: Research Export Agent
**File**: `phase1/agent_1_3_research_export.yaml`
**Purpose**: Export research to Google Docs, trigger approval
**Triggers**: Human Gate - Approve Niche & Personas

---

## Phase 2: Lead Acquisition

### Agent 2.1: Lead List Builder Agent
**File**: `phase2/agent_2_1_lead_list_builder.yaml`
**Purpose**: Scrape 50K+ leads via Apify LinkedIn Sales Navigator
**Features**:
- Parallel Apify actor runs (up to 10 concurrent)
- Streaming database inserts
- Cost tracking and budget controls

### Agent 2.2: Data Validation Agent
**File**: `phase2/agent_2_2_data_validation.yaml`
**Purpose**: Validate and normalize lead data
**Features**:
- Required field validation
- Job title/company name normalization
- Field derivation (domain from LinkedIn, etc.)

### Agent 2.3: Duplicate Detection Agent
**File**: `phase2/agent_2_3_duplicate_detection.yaml`
**Purpose**: Detect duplicates within campaign
**Features**:
- Exact matching (LinkedIn URL, email)
- Fuzzy matching (name + company, 85%+ threshold)
- Intelligent record merging

### Agent 2.4: Cross-Campaign Dedup Agent
**File**: `phase2/agent_2_4_cross_campaign_dedup.yaml`
**Purpose**: Check against historical campaigns
**Features**:
- Recently contacted exclusion (90 days)
- Bounced/unsubscribed exclusion
- Global exclusion list

### Agent 2.5: Lead Scoring Agent
**File**: `phase2/agent_2_5_lead_scoring.yaml`
**Purpose**: Score leads based on fit
**Features**:
- Job title matching (30%)
- Seniority matching (20%)
- Company size matching (15%)
- Industry fit (20%)
- Location/data completeness (15%)
- Tier A/B/C/D classification

### Agent 2.6: Import Finalizer Agent
**File**: `phase2/agent_2_6_import_finalizer.yaml`
**Purpose**: Finalize import, export to Sheets
**Triggers**: Human Gate - Approve Lead List

---

## Phase 3: Email Verification & Enrichment

### Agent 3.1: Email Verification Agent
**File**: `phase3/agent_3_1_email_verification.yaml`
**Purpose**: Find and verify emails via waterfall
**Features**:
- Waterfall across 7+ email finder providers
- Cheapest first (Tomba, Hunter -> Findymail -> Apollo)
- Verification via Reoon

### Agent 3.2: Waterfall Enrichment Agent
**File**: `phase3/agent_3_2_waterfall_enrichment.yaml`
**Purpose**: Enrich leads with company/contact data
**Features**:
- Tier-based enrichment depth (A=full, B=standard, C=basic)
- Web search for free enrichment
- Clearbit/Apollo for paid enrichment

### Agent 3.3: Verification Finalizer Agent
**File**: `phase3/agent_3_3_verification_finalizer.yaml`
**Purpose**: Finalize verification, export results
**Triggers**: Human Gate - Approve for Personalization

---

## Phase 4: Research & Personalization

### Agent 4.1: Company Research Agent
**File**: `phase4/agent_4_1_company_research.yaml`
**Purpose**: Deep research on target companies
**Features**:
- Recent news, funding, hiring signals
- Personalization hook generation
- Parallel research on 20+ companies

### Agent 4.2: Lead Research Agent
**File**: `phase4/agent_4_2_lead_research.yaml`
**Purpose**: Individual lead research
**Features**:
- LinkedIn posts/activity mining
- Articles, podcasts, talks discovery
- Opening line generation

### Agent 4.3: Email Generation Agent
**File**: `phase4/agent_4_3_email_generation.yaml`
**Purpose**: Generate personalized cold emails
**Features**:
- Multiple frameworks (PAS, BAB, AIDA)
- Tier-based personalization depth
- Quality scoring (0-100)
- Regeneration for low-quality emails

### Agent 4.4: Personalization Finalizer Agent
**File**: `phase4/agent_4_4_personalization_finalizer.yaml`
**Purpose**: Finalize emails, export samples
**Triggers**: Human Gate - Approve Email Campaign

---

## Phase 5: Campaign Execution

### Agent 5.1: Campaign Setup Agent
**File**: `phase5/agent_5_1_campaign_setup.yaml`
**Purpose**: Set up campaigns in Instantly.ai
**Features**:
- Campaign creation
- 4-step email sequence configuration
- Sending schedule setup
- Warmup configuration

### Agent 5.2: Email Sending Agent
**File**: `phase5/agent_5_2_email_sending.yaml`
**Purpose**: Upload leads and manage sending
**Features**:
- Batch upload to Instantly
- Tier-prioritized sending
- Sending status tracking

### Agent 5.3: Reply Monitoring Agent
**File**: `phase5/agent_5_3_reply_monitoring.yaml`
**Purpose**: Monitor and categorize replies
**Features**:
- AI-powered reply classification
- Interested/not interested/OOO detection
- Automated actions (Slack notifications, CRM updates)

### Agent 5.4: Campaign Analytics Agent
**File**: `phase5/agent_5_4_campaign_analytics.yaml`
**Purpose**: Track metrics and generate reports
**Features**:
- Hourly metric collection
- Daily/weekly report generation
- Benchmark comparison
- Alert triggering (bounce rate, open rate)

---

## Human Gates

| Gate | Location | Purpose |
|------|----------|---------|
| Gate 1 | After Phase 1 | Approve niche and personas |
| Gate 2 | After Phase 2 | Approve lead list |
| Gate 3 | After Phase 3 | Approve for personalization |
| Gate 4 | After Phase 4 | Approve email campaign |

---

## Directory Structure

```
cold-email-agents/
├── agents/
│   ├── phase1/
│   │   ├── agent_1_1_niche_research.yaml
│   │   ├── agent_1_2_persona_research.yaml
│   │   └── agent_1_3_research_export.yaml
│   ├── phase2/
│   │   ├── agent_2_1_lead_list_builder.yaml
│   │   ├── agent_2_2_data_validation.yaml
│   │   ├── agent_2_3_duplicate_detection.yaml
│   │   ├── agent_2_4_cross_campaign_dedup.yaml
│   │   ├── agent_2_5_lead_scoring.yaml
│   │   └── agent_2_6_import_finalizer.yaml
│   ├── phase3/
│   │   ├── agent_3_1_email_verification.yaml
│   │   ├── agent_3_2_waterfall_enrichment.yaml
│   │   └── agent_3_3_verification_finalizer.yaml
│   ├── phase4/
│   │   ├── agent_4_1_company_research.yaml
│   │   ├── agent_4_2_lead_research.yaml
│   │   ├── agent_4_3_email_generation.yaml
│   │   └── agent_4_4_personalization_finalizer.yaml
│   └── phase5/
│       ├── agent_5_1_campaign_setup.yaml
│       ├── agent_5_2_email_sending.yaml
│       ├── agent_5_3_reply_monitoring.yaml
│       └── agent_5_4_campaign_analytics.yaml
├── infrastructure/
│   └── retry.py (exponential backoff, circuit breakers)
└── README.md (this file)
```

---

## Usage

These YAML specifications define the complete behavior of each agent. They can be:

1. **Converted to Python code** using Claude Agent SDK
2. **Used as configuration** for an agent orchestration framework
3. **Referenced during implementation** as detailed specifications

Each agent YAML includes:
- Tool configuration with priority tiers
- Parallel execution settings
- Database read/write operations
- Step-by-step execution logic
- System prompts for LLM behavior
- Output schemas
- Success criteria
- Handoff conditions to next agent

---

## Version History

- **v2.0.0** (Current): Dynamic tool discovery, parallel execution, multi-source enrichment
- **v1.0.0**: Initial specification with fixed tool assignments
