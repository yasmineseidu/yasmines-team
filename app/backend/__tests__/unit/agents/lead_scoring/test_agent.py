"""Unit tests for Lead Scoring Agent."""

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from src.agents.lead_scoring.agent import (
    DEFAULT_MODEL,
    InsufficientLeadsError,
    LeadScoringAgent,
    LeadScoringAgentError,
    LeadScoringResult,
    score_leads,
)


class TestLeadScoringAgentError:
    """Tests for LeadScoringAgentError exception."""

    def test_error_message(self) -> None:
        error = LeadScoringAgentError("Test error")
        assert error.message == "Test error"
        assert error.details == {}
        assert str(error) == "Test error"

    def test_error_with_details(self) -> None:
        details = {"campaign_id": "123", "lead_count": 10}
        error = LeadScoringAgentError("Test error", details=details)
        assert error.message == "Test error"
        assert error.details == details


class TestInsufficientLeadsError:
    """Tests for InsufficientLeadsError exception."""

    def test_default_message(self) -> None:
        error = InsufficientLeadsError()
        assert error.message == "No leads available for scoring"

    def test_custom_message(self) -> None:
        error = InsufficientLeadsError("Custom message")
        assert error.message == "Custom message"


class TestLeadScoringResult:
    """Tests for LeadScoringResult dataclass."""

    def test_default_values(self) -> None:
        result = LeadScoringResult()

        assert result.success is True
        assert result.status == "completed"
        assert result.total_scored == 0
        assert result.avg_score == 0.0
        assert result.tier_a_count == 0
        assert result.tier_b_count == 0
        assert result.tier_c_count == 0
        assert result.tier_d_count == 0
        assert result.score_distribution == {}
        assert result.lead_scores == []
        assert result.execution_time_ms == 0
        assert result.errors == []
        assert result.warnings == []

    def test_with_values(self) -> None:
        started = datetime.now()
        completed = datetime.now()

        result = LeadScoringResult(
            success=True,
            status="completed",
            total_scored=100,
            avg_score=72.5,
            tier_a_count=25,
            tier_b_count=35,
            tier_c_count=30,
            tier_d_count=10,
            score_distribution={"70-79": 30, "80-89": 25},
            lead_scores=[{"lead_id": "1", "score": 85}],
            execution_time_ms=1500,
            started_at=started,
            completed_at=completed,
            errors=[],
            warnings=["Some warning"],
        )

        assert result.total_scored == 100
        assert result.avg_score == 72.5
        assert result.tier_a_count == 25
        assert result.tier_b_count == 35
        assert result.tier_c_count == 30
        assert result.tier_d_count == 10
        assert result.execution_time_ms == 1500
        assert len(result.warnings) == 1

    def test_to_dict(self) -> None:
        result = LeadScoringResult(
            success=True,
            status="completed",
            total_scored=50,
            avg_score=65.75,
            tier_a_count=10,
            tier_b_count=20,
            tier_c_count=15,
            tier_d_count=5,
            score_distribution={"60-69": 20},
            lead_scores=[{"lead_id": "1", "score": 65}],
            execution_time_ms=1000,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["status"] == "completed"
        assert d["total_scored"] == 50
        assert d["avg_score"] == 65.75  # Rounded to 2 decimals
        assert d["tier_a_count"] == 10
        assert d["tier_b_count"] == 20
        assert d["tier_c_count"] == 15
        assert d["tier_d_count"] == 5
        assert d["score_distribution"] == {"60-69": 20}
        assert len(d["lead_scores"]) == 1
        assert d["execution_time_ms"] == 1000
        assert d["errors"] == []
        assert d["warnings"] == []


class TestLeadScoringAgentInitialization:
    """Tests for LeadScoringAgent initialization."""

    def test_default_values(self) -> None:
        agent = LeadScoringAgent()

        assert agent.name == "lead_scoring"
        assert agent.model == DEFAULT_MODEL
        assert agent.batch_size == 2000
        assert agent.job_title_threshold == 0.80

    def test_custom_values(self) -> None:
        agent = LeadScoringAgent(
            model="claude-haiku-3-20250310",
            batch_size=1000,
            job_title_threshold=0.75,
        )

        assert agent.model == "claude-haiku-3-20250310"
        assert agent.batch_size == 1000
        assert agent.job_title_threshold == 0.75

    def test_system_prompt(self) -> None:
        agent = LeadScoringAgent()
        prompt = agent.system_prompt

        assert "lead scoring specialist" in prompt
        assert "Job Title Match (30" in prompt
        assert "Seniority Match (20" in prompt
        assert "Company Size Match (15" in prompt
        assert "Industry Fit (20" in prompt
        assert "Location Match (10" in prompt
        assert "Data Completeness (5" in prompt
        assert "Tier A (80+)" in prompt
        assert "Tier B (60-79)" in prompt
        assert "Tier C (40-59)" in prompt
        assert "Tier D (<40)" in prompt


class TestLeadScoringAgentRun:
    """Tests for LeadScoringAgent.run() method."""

    @pytest.fixture
    def agent(self) -> LeadScoringAgent:
        return LeadScoringAgent(batch_size=10)

    @pytest.fixture
    def scoring_context(self) -> dict[str, Any]:
        return {
            "niche": {
                "id": "niche-1",
                "name": "SaaS Marketing",
                "industries": ["SaaS", "Software"],
                "company_sizes": ["201-500", "501-1000"],
                "job_titles": ["VP Marketing", "CMO"],
            },
            "personas": [
                {
                    "id": "persona-1",
                    "name": "Marketing Leader",
                    "job_titles": ["VP Marketing", "Marketing Director"],
                    "seniority_levels": ["vp", "director"],
                    "company_sizes": ["201-500", "501-1000"],
                },
            ],
            "industry_fit_scores": [
                {"industry": "SaaS", "fit_score": 95},
                {"industry": "Software", "fit_score": 85},
            ],
            "target_countries": ["United States"],
        }

    @pytest.fixture
    def sample_leads(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "lead-1",
                "title": "VP Marketing",
                "seniority": "vp",
                "company_name": "Acme Corp",
                "company_size": "201-500",
                "company_industry": "SaaS",
                "country": "United States",
                "email": "vp@acme.com",
                "phone": "555-1234",
                "company_domain": "acme.com",
                "linkedin_url": "https://linkedin.com/in/vp",
            },
            {
                "id": "lead-2",
                "title": "Marketing Manager",
                "seniority": "manager",
                "company_name": "Small Co",
                "company_size": "11-50",
                "company_industry": "Consulting",
                "country": "Canada",
                "email": "manager@small.com",
            },
            {
                "id": "lead-3",
                "title": "Software Engineer",
                "company_name": "Tech Corp",
                "company_industry": "Unknown",
            },
        ]

    @pytest.mark.asyncio
    async def test_run_with_no_leads(
        self, agent: LeadScoringAgent, scoring_context: dict[str, Any]
    ) -> None:
        result = await agent.run(
            campaign_id="campaign-1",
            leads=[],
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert result.status == "completed"
        assert result.total_scored == 0
        # Execution time may be 0 if completes in < 1ms
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_run_without_scoring_context(
        self, agent: LeadScoringAgent, sample_leads: list[dict[str, Any]]
    ) -> None:
        result = await agent.run(
            campaign_id="campaign-1",
            leads=sample_leads,
            scoring_context=None,
        )

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) == 1
        assert result.errors[0]["type"] == "MissingScoringContext"

    @pytest.mark.asyncio
    async def test_run_direct_mode(
        self,
        agent: LeadScoringAgent,
        sample_leads: list[dict[str, Any]],
        scoring_context: dict[str, Any],
    ) -> None:
        result = await agent.run(
            campaign_id="campaign-1",
            leads=sample_leads,
            scoring_context=scoring_context,
            use_claude=False,
        )

        assert result.success is True
        assert result.status == "completed"
        assert result.total_scored == 3
        assert len(result.lead_scores) == 3
        assert result.avg_score > 0
        assert result.execution_time_ms > 0

        # Check that all tiers add up to total
        tier_sum = (
            result.tier_a_count + result.tier_b_count + result.tier_c_count + result.tier_d_count
        )
        assert tier_sum == result.total_scored

    @pytest.mark.asyncio
    async def test_run_scores_high_quality_lead_highly(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        # A perfect lead matching all criteria
        leads = [
            {
                "id": "lead-perfect",
                "title": "VP Marketing",
                "seniority": "vp",
                "company_name": "Perfect Corp",
                "company_size": "201-500",
                "company_industry": "SaaS",
                "country": "United States",
                "email": "vp@perfect.com",
                "phone": "555-9999",
                "company_domain": "perfect.com",
                "linkedin_url": "https://linkedin.com/in/vp-perfect",
            }
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert result.total_scored == 1
        assert result.tier_a_count == 1  # Should be tier A

        # Check individual score
        lead_score = result.lead_scores[0]
        assert lead_score["lead_id"] == "lead-perfect"
        assert lead_score["score"] >= 80
        assert lead_score["tier"] == "A"

    @pytest.mark.asyncio
    async def test_run_scores_low_quality_lead_lowly(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        # A poor lead with minimal data
        leads = [
            {
                "id": "lead-poor",
                "title": "Intern",
                "company_name": "Unknown Corp",
            }
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert result.total_scored == 1
        assert result.tier_d_count == 1  # Should be tier D

        # Check individual score
        lead_score = result.lead_scores[0]
        assert lead_score["lead_id"] == "lead-poor"
        assert lead_score["score"] < 40
        assert lead_score["tier"] == "D"

    @pytest.mark.asyncio
    async def test_run_handles_exception(
        self,
        agent: LeadScoringAgent,
        sample_leads: list[dict[str, Any]],
        scoring_context: dict[str, Any],
    ) -> None:
        # Patch _run_direct to raise an exception
        with patch.object(agent, "_run_direct", side_effect=ValueError("Test error")):
            result = await agent.run(
                campaign_id="campaign-1",
                leads=sample_leads,
                scoring_context=scoring_context,
                use_claude=False,
            )

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) == 1
        assert result.errors[0]["type"] == "ValueError"
        assert "Test error" in result.errors[0]["message"]


class TestLeadScoringAgentRunDirect:
    """Tests for LeadScoringAgent._run_direct() method."""

    @pytest.fixture
    def agent(self) -> LeadScoringAgent:
        return LeadScoringAgent(batch_size=2)  # Small batch for testing

    @pytest.fixture
    def scoring_context(self) -> dict[str, Any]:
        return {
            "niche": {
                "id": "niche-1",
                "name": "SaaS Marketing",
                "industries": ["SaaS"],
                "company_sizes": ["201-500"],
                "job_titles": ["VP Marketing"],
            },
            "personas": [
                {
                    "id": "persona-1",
                    "name": "Marketing Leader",
                    "job_titles": ["VP Marketing"],
                    "seniority_levels": ["vp"],
                    "company_sizes": ["201-500"],
                },
            ],
            "industry_fit_scores": [
                {"industry": "SaaS", "fit_score": 95},
            ],
            "target_countries": ["United States"],
        }

    @pytest.mark.asyncio
    async def test_run_direct_processes_batches(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        # Create 5 leads - should be processed in 3 batches with batch_size=2
        leads = [
            {"id": f"lead-{i}", "title": "VP Marketing", "company_industry": "SaaS"}
            for i in range(5)
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert result.total_scored == 5
        assert len(result.lead_scores) == 5

    @pytest.mark.asyncio
    async def test_run_direct_calculates_distribution(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        leads = [
            {
                "id": "lead-1",
                "title": "VP Marketing",
                "seniority": "vp",
                "company_size": "201-500",
                "company_industry": "SaaS",
                "country": "United States",
                "email": "vp@test.com",
                "phone": "555-1234",
            },
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert result.score_distribution is not None
        # Should have entries like "0-9", "10-19", etc.
        assert "0-9" in result.score_distribution or "80-89" in result.score_distribution


class TestLeadScoringAgentBuildTaskPrompt:
    """Tests for LeadScoringAgent._build_task_prompt() method."""

    def test_build_task_prompt_includes_campaign_id(self) -> None:
        agent = LeadScoringAgent()
        prompt = agent._build_task_prompt("campaign-123", 100, 5)

        assert "campaign-123" in prompt
        assert "100" in prompt  # Lead count
        assert "5" in prompt  # Batch count

    def test_build_task_prompt_includes_batch_size(self) -> None:
        agent = LeadScoringAgent(batch_size=500)
        prompt = agent._build_task_prompt("campaign-1", 1000, 2)

        assert "batch_size=500" in prompt

    def test_build_task_prompt_includes_threshold(self) -> None:
        agent = LeadScoringAgent(job_title_threshold=0.85)
        prompt = agent._build_task_prompt("campaign-1", 50, 1)

        assert "0.85" in prompt

    def test_build_task_prompt_includes_instructions(self) -> None:
        agent = LeadScoringAgent()
        prompt = agent._build_task_prompt("campaign-1", 100, 5)

        assert "load_scoring_context" in prompt
        assert "score_leads_batch" in prompt
        assert "aggregate_scoring_results" in prompt
        assert "get_scoring_summary" in prompt


class TestScoreLeadsConvenienceFunction:
    """Tests for score_leads() convenience function."""

    @pytest.fixture
    def scoring_context(self) -> dict[str, Any]:
        return {
            "niche": {
                "id": "niche-1",
                "name": "Test Niche",
                "industries": ["Tech"],
                "company_sizes": ["51-200"],
                "job_titles": ["CTO"],
            },
            "personas": [
                {
                    "id": "persona-1",
                    "name": "Tech Leader",
                    "job_titles": ["CTO"],
                    "seniority_levels": ["c_suite"],
                    "company_sizes": ["51-200"],
                },
            ],
            "industry_fit_scores": [
                {"industry": "Tech", "fit_score": 90},
            ],
            "target_countries": ["United States"],
        }

    @pytest.mark.asyncio
    async def test_score_leads_success(self, scoring_context: dict[str, Any]) -> None:
        leads = [
            {"id": "lead-1", "title": "CTO", "company_industry": "Tech"},
            {"id": "lead-2", "title": "CEO", "company_industry": "Tech"},
        ]

        result = await score_leads(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
            batch_size=10,
            use_claude=False,
        )

        assert result.success is True
        assert result.total_scored == 2

    @pytest.mark.asyncio
    async def test_score_leads_with_custom_batch_size(
        self, scoring_context: dict[str, Any]
    ) -> None:
        leads = [{"id": f"lead-{i}", "title": "CTO"} for i in range(10)]

        result = await score_leads(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
            batch_size=3,  # Small batch size
            use_claude=False,
        )

        assert result.success is True
        assert result.total_scored == 10


class TestLeadScoringAgentLeadScoreBreakdown:
    """Tests for lead score breakdown in results."""

    @pytest.fixture
    def agent(self) -> LeadScoringAgent:
        return LeadScoringAgent()

    @pytest.fixture
    def scoring_context(self) -> dict[str, Any]:
        return {
            "niche": {
                "id": "niche-1",
                "name": "SaaS Marketing",
                "industries": ["SaaS"],
                "company_sizes": ["201-500"],
                "job_titles": ["VP Marketing"],
            },
            "personas": [
                {
                    "id": "persona-1",
                    "name": "Marketing Leader",
                    "job_titles": ["VP Marketing"],
                    "seniority_levels": ["vp"],
                    "company_sizes": ["201-500"],
                },
            ],
            "industry_fit_scores": [
                {"industry": "SaaS", "fit_score": 95},
            ],
            "target_countries": ["United States"],
        }

    @pytest.mark.asyncio
    async def test_lead_scores_include_breakdown(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        leads = [
            {
                "id": "lead-1",
                "title": "VP Marketing",
                "seniority": "vp",
                "company_size": "201-500",
                "company_industry": "SaaS",
                "country": "United States",
                "email": "vp@test.com",
            },
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        assert len(result.lead_scores) == 1

        lead_score = result.lead_scores[0]
        breakdown = lead_score["breakdown"]

        assert "job_title_match" in breakdown
        assert "seniority_match" in breakdown
        assert "company_size_match" in breakdown
        assert "industry_fit" in breakdown
        assert "location_match" in breakdown
        assert "data_completeness" in breakdown

    @pytest.mark.asyncio
    async def test_lead_scores_include_persona_tags(
        self,
        agent: LeadScoringAgent,
        scoring_context: dict[str, Any],
    ) -> None:
        leads = [
            {
                "id": "lead-1",
                "title": "VP Marketing",
                "seniority": "vp",
            },
        ]

        result = await agent.run(
            campaign_id="campaign-1",
            leads=leads,
            scoring_context=scoring_context,
        )

        assert result.success is True
        lead_score = result.lead_scores[0]

        assert "persona_tags" in lead_score
        tags = lead_score["persona_tags"]
        assert isinstance(tags, list)
        # Should have tier tag
        assert any("tier_" in tag for tag in tags)
