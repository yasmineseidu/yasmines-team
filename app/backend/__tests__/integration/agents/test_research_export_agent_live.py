"""
Live API integration tests for Research Export Agent.

**MANDATORY**: These tests use real Google API credentials from .env file.
**REQUIREMENT**: 100% pass rate before proceeding to review.

Tests verify:
- Google Drive folder creation with actual API
- Google Docs document creation with actual API
- Full research export workflow
- Error handling with real API responses
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.agents.research_export.agent import FolderCreationError, ResearchExportAgent

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(project_root / ".env")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def google_credentials() -> dict[str, str]:
    """
    Load Google service account credentials from .env.

    Raises:
        pytest.skip: If credentials not found in .env
    """
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not credentials_json:
        pytest.skip("GOOGLE_SERVICE_ACCOUNT_JSON not found in .env")

    try:
        return json.loads(credentials_json)
    except json.JSONDecodeError:
        pytest.skip("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON")


@pytest.fixture
def agent(google_credentials: dict[str, str]) -> ResearchExportAgent:
    """Create ResearchExportAgent with real credentials."""
    # Use None as parent_id to create folders in service account's root
    # In production, parent folder must be shared with service account
    agent = ResearchExportAgent(google_credentials=google_credentials)
    agent.parent_folder_id = None  # Create in root for testing
    return agent


@pytest.fixture
def sample_niche_data() -> dict[str, any]:
    """Sample niche data for testing."""
    return {
        "id": "test-niche-123",
        "name": "AI Tool Builders [TEST]",
        "slug": "ai-tool-builders-test",
        "industry": ["Technology", "Artificial Intelligence"],
        "job_titles": ["AI Engineer", "ML Engineer", "Product Manager"],
        "company_size": ["1-50", "51-200"],
        "location": ["United States", "Remote"],
        "pain_points": [
            {
                "pain": "Difficulty building reliable AI agents",
                "intensity": 9,
                "quote": "Our AI agents are too unpredictable for production",
                "source": "Reddit r/MachineLearning",
            },
            {
                "pain": "Integration complexity",
                "intensity": 8,
                "quote": "Too many APIs to integrate",
                "source": "Hacker News discussion",
            },
        ],
        "value_propositions": [
            "Reliable, production-ready AI agents",
            "Simple integration with existing tools",
            "Pre-built templates for common use cases",
        ],
        "messaging_tone": "technical_but_friendly",
    }


@pytest.fixture
def sample_niche_scores() -> dict[str, any]:
    """Sample niche scores."""
    return {
        "overall_score": 92,
        "market_size_score": 95,
        "competition_score": 85,
        "reachability_score": 90,
        "pain_intensity_score": 94,
        "budget_authority_score": 88,
        "confidence": 0.95,
        "recommendation": "strongly_pursue",
        "scoring_details": json.dumps(
            {
                "analysis": "High potential niche with strong pain points",
                "risks": "Competitive market",
                "opportunities": "Growing demand for AI tooling",
            }
        ),
    }


@pytest.fixture
def sample_niche_research_data() -> dict[str, any]:
    """Sample niche research data."""
    return {
        "market_size_estimate": "$2B - $5B (AI tooling market)",
        "company_count_estimate": 100000,
        "persona_count_estimate": 500000,
        "growth_rate": "35% YoY",
        "market_data_sources": "Gartner, CB Insights, Company surveys",
        "competitors_found": [
            {
                "name": "LangChain",
                "position": "Market Leader",
                "strengths": "Strong community, open source",
                "weaknesses": "Complex for beginners",
            },
            {
                "name": "AutoGPT",
                "position": "Challenger",
                "strengths": "Autonomous agents",
                "weaknesses": "Reliability issues",
            },
        ],
        "saturation_level": "Medium - Growing market with room for differentiation",
        "differentiation_opportunities": [
            "Focus on reliability and production-readiness",
            "Better developer experience",
            "Enterprise-grade security and compliance",
            "Vertical-specific solutions",
        ],
        "inbox_fatigue_indicators": [
            "Many generic AI tool emails",
            "Oversaturation of ChatGPT wrappers",
        ],
        "linkedin_presence": "High - Active developer community",
        "data_availability": "Good - Public GitHub repos, tech blogs",
        "email_findability": "Moderate - Use LinkedIn + Hunter.io",
        "pain_points_detailed": [
            {
                "title": "Agent Reliability in Production",
                "description": "AI agents fail unpredictably, causing production issues",
                "frequency": "Very common (80%+ of teams)",
                "intensity": "Critical - blocks deployment",
            },
            {
                "title": "Integration Complexity",
                "description": "Too many APIs and tools to integrate",
                "frequency": "Common (60%+ of teams)",
                "intensity": "High - slows development",
            },
        ],
        "pain_point_quotes": [
            {
                "quote": "We built an AI agent that worked great in testing but failed completely in production",
                "source": "Reddit r/MachineLearning",
                "context": "Discussion on production AI systems",
            },
            {
                "quote": "The integration overhead is killing our velocity",
                "source": "Hacker News",
                "context": "Thread on AI developer tools",
            },
        ],
        "has_budget_authority": True,
        "typical_budget_range": "$10K - $50K/month for AI tooling",
        "decision_process": "Technical evaluation first, then business buy-in (2-4 weeks)",
        "buying_triggers": [
            "Production AI agent failure",
            "New AI project kickoff",
            "Scaling existing AI features",
        ],
        "evidence_sources": [
            {"type": "Report", "url": "https://www.gartner.com/ai-tools"},
            {"type": "Survey", "url": "https://example.com/ai-survey-2024"},
        ],
    }


@pytest.fixture
def sample_personas() -> list[dict[str, any]]:
    """Sample personas."""
    return [
        {
            "id": "persona-test-1",
            "name": "AI Engineering Lead",
            "job_titles": ["AI Engineer", "ML Engineer", "AI Team Lead"],
            "seniority_level": "mid_senior",
            "department": "Engineering",
            "pain_points": [
                {
                    "pain": "Agent reliability in production",
                    "intensity": 10,
                    "quote": "Our agents crash in production weekly",
                    "source": "Customer interview",
                },
                {
                    "pain": "Debugging AI agent failures",
                    "intensity": 9,
                    "quote": "It's impossible to debug why agents fail",
                    "source": "Reddit discussion",
                },
            ],
            "goals": [
                "Deploy reliable AI agents to production",
                "Reduce debugging time",
                "Scale AI features across products",
            ],
            "objections": [
                {
                    "objection": "We already use LangChain",
                    "real_meaning": "Switching cost concerns",
                    "counter": "Gradual migration path, start with one use case",
                },
                {
                    "objection": "Too expensive",
                    "real_meaning": "Need to prove ROI",
                    "counter": "ROI calculator showing time saved on debugging",
                },
            ],
            "language_patterns": [
                "production-ready",
                "reliability",
                "scale",
                "debugging nightmare",
                "agent hallucination",
            ],
            "trigger_events": [
                "Production AI agent failure",
                "Scaling AI team",
                "New AI project kickoff",
            ],
            "messaging_angles": {
                "primary": {
                    "angle": "Reliability",
                    "hook": "AI agents that work in production, not just demos",
                    "supporting_pain": "Agent reliability issues",
                },
                "secondary": {
                    "angle": "Developer Experience",
                    "hook": "Debug AI agents in minutes, not days",
                },
                "avoid": [
                    "Another ChatGPT wrapper",
                    "Generic AI buzzwords",
                    "Overpromising capabilities",
                ],
            },
        },
        {
            "id": "persona-test-2",
            "name": "AI Product Manager",
            "job_titles": ["Product Manager", "AI Product Lead", "Head of AI Product"],
            "seniority_level": "senior",
            "department": "Product",
            "pain_points": [
                {
                    "pain": "AI features taking too long to ship",
                    "intensity": 8,
                    "quote": "We planned 2 months, it's been 6 months",
                    "source": "Customer interview",
                },
            ],
            "goals": [
                "Ship AI features faster",
                "Reduce technical debt",
                "Improve product-market fit",
            ],
            "objections": [
                {
                    "objection": "Engineers will resist change",
                    "real_meaning": "Change management concerns",
                    "counter": "Start with pilot project, show quick wins",
                },
            ],
            "language_patterns": [
                "time to market",
                "velocity",
                "product-market fit",
                "user experience",
            ],
            "trigger_events": [
                "Competitor launches AI feature",
                "Quarterly planning",
                "Poor NPS scores",
            ],
            "messaging_angles": {
                "primary": {
                    "angle": "Speed",
                    "hook": "Ship AI features in weeks, not months",
                    "supporting_pain": "Slow AI feature development",
                },
                "secondary": {
                    "angle": "Quality",
                    "hook": "Better user experience with reliable AI",
                },
                "avoid": [
                    "Too technical jargon",
                    "Promising unrealistic timelines",
                ],
            },
        },
    ]


# ============================================================================
# Live API Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestResearchExportAgentLive:
    """Live API tests with real Google credentials."""

    async def test_create_folder_with_real_api(self, agent: ResearchExportAgent) -> None:
        """
        Test folder creation with real Google Drive API.

        MUST PASS: Folder created successfully in parent folder.
        """
        # Authenticate first
        await agent.drive_client.authenticate()

        # Create test folder
        folder_id, folder_url = await agent.create_research_folder(
            niche_name="Live API Test - Folder Creation",
            niche_slug="live-api-test-folder",
        )

        # Verify folder created
        assert folder_id is not None
        assert len(folder_id) > 0
        assert "https://drive.google.com/drive/folders/" in folder_url
        assert folder_id in folder_url

        # Cleanup: Delete test folder
        await agent.drive_client.delete_file(folder_id)

    async def test_create_document_with_real_api(self, agent: ResearchExportAgent) -> None:
        """
        Test document creation with real Google Docs API.

        MUST PASS: Document created successfully with content.
        """
        # Authenticate
        await agent.drive_client.authenticate()
        await agent.docs_client.authenticate()

        # Create folder first
        folder_id, folder_url = await agent.create_research_folder(
            niche_name="Live API Test - Document",
            niche_slug="live-api-test-doc",
        )

        try:
            # Create test document
            doc = await agent.create_document_from_content(
                title="Live API Test Document",
                content="# Test Document\n\nThis is a test document created by live API tests.",
                folder_id=folder_id,
            )

            # Verify document created
            assert doc["doc_id"] is not None
            assert doc["doc_url"] is not None
            assert "https://docs.google.com/document/d/" in doc["doc_url"]
            assert doc["name"] == "Live API Test Document"

        finally:
            # Cleanup: Delete folder (deletes documents inside)
            await agent.drive_client.delete_file(folder_id)

    async def test_full_research_export_with_real_api(
        self,
        agent: ResearchExportAgent,
        sample_niche_data: dict[str, any],
        sample_niche_scores: dict[str, any],
        sample_niche_research_data: dict[str, any],
        sample_personas: list[dict[str, any]],
    ) -> None:
        """
        Test complete research export workflow with real API.

        MUST PASS: All 4 documents created successfully.
        """
        # Authenticate
        await agent.drive_client.authenticate()
        await agent.docs_client.authenticate()

        # Execute full export
        result = await agent.export_research(
            niche_id="test-niche-live-api",
            niche_data=sample_niche_data,
            niche_scores=sample_niche_scores,
            niche_research_data=sample_niche_research_data,
            personas=sample_personas,
            persona_research_data=[],
            industry_scores=[],
            consolidated_pain_points=[
                "Agent reliability issues",
                "Integration complexity",
                "Slow time to production",
            ],
        )

        try:
            # Verify folder created
            assert result["folder_url"] is not None
            assert "https://drive.google.com/drive/folders/" in result["folder_url"]

            # Verify all 4 documents created
            assert len(result["documents"]) == 4

            # Verify each document
            doc_names = [doc["name"] for doc in result["documents"]]
            assert any("Niche Overview" in name for name in doc_names)
            assert any("Persona Profiles" in name for name in doc_names)
            assert any("Pain Points" in name for name in doc_names)
            assert any("Messaging Angles" in name for name in doc_names)

            # Verify all documents have URLs
            for doc in result["documents"]:
                assert doc["doc_id"] is not None
                assert doc["doc_url"] is not None
                assert "https://docs.google.com/document/d/" in doc["doc_url"]

            # Verify notification status
            assert "notification_sent" in result
            assert result["notification_sent"] is False  # Slack not implemented yet

        finally:
            # Cleanup: Delete test folder and all documents
            if result.get("folder_id"):
                await agent.drive_client.delete_file(result["folder_id"])

    async def test_error_handling_with_invalid_credentials(self) -> None:
        """
        Test error handling with invalid credentials.

        MUST PASS: Proper error raised for authentication failure.
        """
        invalid_credentials = {
            "type": "service_account",
            "project_id": "invalid",
            "private_key": "-----BEGIN PRIVATE KEY-----\ninvalid\n-----END PRIVATE KEY-----\n",  # pragma: allowlist secret
            "client_email": "invalid@invalid.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        agent = ResearchExportAgent(google_credentials=invalid_credentials)

        # Attempt to create folder should fail authentication
        with pytest.raises(
            FolderCreationError
        ):  # Will raise auth error wrapped in FolderCreationError
            await agent.create_research_folder(
                niche_name="Should Fail",
                niche_slug="should-fail",
            )
