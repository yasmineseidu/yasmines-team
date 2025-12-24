"""Unit tests for Research Export Agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.research_export.agent import (
    DocumentCreationError,
    FolderCreationError,
    ResearchExportAgent,
    ResearchExportAgentError,
)
from src.agents.research_export.templates import (
    render_messaging_angles_doc,
    render_niche_overview_doc,
    render_pain_points_doc,
    render_persona_profiles_doc,
)
from src.integrations.google_docs.client import GoogleDocsError
from src.integrations.google_drive.exceptions import GoogleDriveError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def google_credentials() -> dict[str, str]:
    """Mock Google service account credentials."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",  # pragma: allowlist secret
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


@pytest.fixture
def niche_data() -> dict[str, any]:
    """Sample niche data."""
    return {
        "id": "niche-123",
        "name": "SaaS Founders",
        "slug": "saas-founders",
        "industry": ["Technology", "Software"],
        "job_titles": ["CEO", "CTO", "Founder"],
        "company_size": ["1-50", "51-200"],
        "location": ["United States", "Europe"],
        "pain_points": [
            {
                "pain": "Difficulty scaling customer acquisition",
                "intensity": 9,
                "quote": "We're struggling to find a repeatable sales process",
                "source": "Reddit r/startups",
            }
        ],
        "value_propositions": [
            "Automated lead generation",
            "Personalized outreach at scale",
        ],
        "messaging_tone": "professional",
    }


@pytest.fixture
def niche_scores() -> dict[str, any]:
    """Sample niche scores."""
    return {
        "overall_score": 85,
        "market_size_score": 90,
        "competition_score": 75,
        "reachability_score": 88,
        "pain_intensity_score": 92,
        "budget_authority_score": 80,
        "confidence": 0.9,
        "recommendation": "pursue",
        "scoring_details": json.dumps({"details": "test"}),
    }


@pytest.fixture
def niche_research_data() -> dict[str, any]:
    """Sample niche research data."""
    return {
        "market_size_estimate": "$500M - $1B",
        "company_count_estimate": 50000,
        "persona_count_estimate": 150000,
        "growth_rate": "15% YoY",
        "competitors_found": [
            {
                "name": "Competitor A",
                "position": "Market Leader",
                "strengths": "Brand recognition",
                "weaknesses": "High price point",
            }
        ],
        "saturation_level": "Medium",
        "differentiation_opportunities": [
            "Focus on SMB market",
            "Better onboarding experience",
        ],
        "inbox_fatigue_indicators": ["High email volume in industry"],
        "pain_points_detailed": [
            {
                "title": "Lead Quality Issues",
                "description": "Poor lead quality from existing sources",
                "frequency": "Very common",
                "intensity": "High",
            }
        ],
        "pain_point_quotes": [
            {
                "quote": "We waste so much time on unqualified leads",
                "source": "Industry Survey 2024",
                "context": "B2B SaaS companies",
            }
        ],
        "has_budget_authority": True,
        "typical_budget_range": "$5K - $20K/month",
        "decision_process": "2-3 stakeholders, 30-60 day cycle",
        "buying_triggers": [
            "Fundraising completion",
            "Poor conversion rates",
        ],
        "evidence_sources": [{"type": "Report", "url": "https://example.com/report"}],
    }


@pytest.fixture
def personas() -> list[dict[str, any]]:
    """Sample personas."""
    return [
        {
            "id": "persona-1",
            "name": "Technical Founder",
            "job_titles": ["CTO", "VP Engineering"],
            "seniority_level": "executive",
            "department": "Engineering",
            "pain_points": [
                {
                    "pain": "Scaling technical infrastructure",
                    "intensity": 8,
                    "quote": "We're always firefighting",
                    "source": "Interview",
                }
            ],
            "goals": ["Build scalable systems", "Hire top talent"],
            "objections": [
                {
                    "objection": "Too expensive",
                    "real_meaning": "Not sure of ROI",
                    "counter": "Show ROI calculator",
                }
            ],
            "language_patterns": ["Technical debt", "Scale"],
            "trigger_events": ["Funding round", "Product launch"],
            "messaging_angles": {
                "primary": {
                    "angle": "Efficiency",
                    "hook": "Cut development time in half",
                    "supporting_pain": "Limited engineering resources",
                },
                "secondary": {
                    "angle": "Quality",
                    "hook": "Ship faster without bugs",
                },
                "avoid": ["Sales-y language", "Buzzwords"],
            },
        }
    ]


@pytest.fixture
def agent(google_credentials: dict[str, str]) -> ResearchExportAgent:
    """Create ResearchExportAgent instance."""
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": json.dumps(google_credentials)}):
        return ResearchExportAgent(google_credentials=google_credentials)


# ============================================================================
# Tests: Initialization
# ============================================================================


class TestResearchExportAgentInitialization:
    """Tests for ResearchExportAgent initialization."""

    def test_init_with_credentials(self, google_credentials: dict[str, str]) -> None:
        """Agent should initialize with provided credentials."""
        agent = ResearchExportAgent(google_credentials=google_credentials)

        assert agent.parent_folder_id == "1q2CuAABTE9HLML8cMd5YaOC3Y1ev6JC4"
        assert agent.drive_client is not None
        assert agent.docs_client is not None

    def test_init_loads_credentials_from_env(self, google_credentials: dict[str, str]) -> None:
        """Agent should load credentials from environment."""
        with patch.dict(
            "os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": json.dumps(google_credentials)}
        ):
            agent = ResearchExportAgent()

            assert agent.drive_client is not None
            assert agent.docs_client is not None

    def test_init_raises_on_missing_credentials(self) -> None:
        """Agent should raise error if credentials not found."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ResearchExportAgentError) as exc_info:
                ResearchExportAgent()

            assert "GOOGLE_SERVICE_ACCOUNT_JSON" in str(exc_info.value)

    def test_init_raises_on_invalid_json_credentials(self) -> None:
        """Agent should raise error if credentials JSON is invalid."""
        with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": "invalid json"}):
            with pytest.raises(ResearchExportAgentError) as exc_info:
                ResearchExportAgent()

            assert "Invalid GOOGLE_SERVICE_ACCOUNT_JSON" in str(exc_info.value)


# ============================================================================
# Tests: Folder Creation
# ============================================================================


class TestCreateResearchFolder:
    """Tests for create_research_folder method."""

    @pytest.mark.asyncio
    async def test_creates_folder_successfully(self, agent: ResearchExportAgent) -> None:
        """Should create folder and return ID and URL."""
        with (
            patch.object(agent.drive_client, "authenticate", new_callable=AsyncMock),
            patch.object(
                agent.drive_client, "create_folder", new_callable=AsyncMock
            ) as mock_create,
            patch.object(agent.drive_client, "share_file", new_callable=AsyncMock) as mock_share,
        ):
            mock_create.return_value = {"id": "folder-123"}

            folder_id, folder_url = await agent.create_research_folder(
                niche_name="Test Niche",
                niche_slug="test-niche",
            )

            assert folder_id == "folder-123"
            assert folder_url == "https://drive.google.com/drive/folders/folder-123"

            # Verify folder created with correct params
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert "Test Niche" in call_args.kwargs["name"]
            assert call_args.kwargs["parent_id"] == "1q2CuAABTE9HLML8cMd5YaOC3Y1ev6JC4"

            # Verify file shared
            mock_share.assert_called_once_with(
                file_id="folder-123",
                role="reader",
                share_type="anyone",
            )

    @pytest.mark.asyncio
    async def test_raises_on_drive_error(self, agent: ResearchExportAgent) -> None:
        """Should raise FolderCreationError on Drive API error."""
        with (
            patch.object(agent.drive_client, "authenticate", new_callable=AsyncMock),
            patch.object(
                agent.drive_client, "create_folder", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.side_effect = GoogleDriveError("API error")

            with pytest.raises(FolderCreationError) as exc_info:
                await agent.create_research_folder(
                    niche_name="Test Niche",
                    niche_slug="test-niche",
                )

            assert "Test Niche" in str(exc_info.value)


# ============================================================================
# Tests: Document Creation
# ============================================================================


class TestCreateDocumentFromContent:
    """Tests for create_document_from_content method."""

    @pytest.mark.asyncio
    async def test_creates_document_successfully(self, agent: ResearchExportAgent) -> None:
        """Should create document and return metadata."""
        with (
            patch.object(agent.docs_client, "authenticate", new_callable=AsyncMock),
            patch.object(
                agent.docs_client, "create_document", new_callable=AsyncMock
            ) as mock_create,
            patch.object(agent.docs_client, "insert_text", new_callable=AsyncMock) as mock_insert,
            patch.object(
                agent.drive_client, "move_file_to_folder", new_callable=AsyncMock
            ) as mock_move,
            patch.object(agent.drive_client, "share_file", new_callable=AsyncMock),
        ):
            mock_create.return_value = {"documentId": "doc-123"}

            result = await agent.create_document_from_content(
                title="Test Document",
                content="# Test Content",
                folder_id="folder-123",
            )

            assert result["doc_id"] == "doc-123"
            assert result["doc_url"] == "https://docs.google.com/document/d/doc-123/edit"
            assert result["name"] == "Test Document"

            # Verify document created
            mock_create.assert_called_once_with(title="Test Document")

            # Verify content inserted
            mock_insert.assert_called_once_with(
                document_id="doc-123",
                text="# Test Content",
                index=1,
            )

            # Verify moved to folder
            mock_move.assert_called_once_with(
                file_id="doc-123",
                folder_id="folder-123",
            )

    @pytest.mark.asyncio
    async def test_raises_on_docs_error(self, agent: ResearchExportAgent) -> None:
        """Should raise DocumentCreationError on Docs API error."""
        with (
            patch.object(agent.docs_client, "authenticate", new_callable=AsyncMock),
            patch.object(
                agent.docs_client, "create_document", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.side_effect = GoogleDocsError("API error")

            with pytest.raises(DocumentCreationError) as exc_info:
                await agent.create_document_from_content(
                    title="Test Document",
                    content="Content",
                    folder_id="folder-123",
                )

            assert "Test Document" in str(exc_info.value)


# ============================================================================
# Tests: Export Research
# ============================================================================


class TestExportResearch:
    """Tests for export_research method."""

    @pytest.mark.asyncio
    async def test_exports_research_successfully(
        self,
        agent: ResearchExportAgent,
        niche_data: dict[str, any],
        niche_scores: dict[str, any],
        niche_research_data: dict[str, any],
        personas: list[dict[str, any]],
    ) -> None:
        """Should export complete research to Google Docs."""
        with (
            patch.object(agent, "create_research_folder", new_callable=AsyncMock) as mock_folder,
            patch.object(agent, "create_document_from_content", new_callable=AsyncMock) as mock_doc,
        ):
            mock_folder.return_value = ("folder-123", "https://drive.google.com/folders/folder-123")
            mock_doc.side_effect = [
                {"doc_id": "doc-1", "doc_url": "url-1", "name": "Niche Overview"},
                {"doc_id": "doc-2", "doc_url": "url-2", "name": "Persona Profiles"},
                {"doc_id": "doc-3", "doc_url": "url-3", "name": "Pain Points"},
                {"doc_id": "doc-4", "doc_url": "url-4", "name": "Messaging"},
            ]

            result = await agent.export_research(
                niche_id="niche-123",
                niche_data=niche_data,
                niche_scores=niche_scores,
                niche_research_data=niche_research_data,
                personas=personas,
                persona_research_data=[],
                industry_scores=[],
                consolidated_pain_points=["Pain 1", "Pain 2"],
            )

            assert result["folder_url"] == "https://drive.google.com/folders/folder-123"
            assert len(result["documents"]) == 4
            assert result["notification_sent"] is False

            # Verify folder created
            mock_folder.assert_called_once()

            # Verify 4 documents created
            assert mock_doc.call_count == 4

    @pytest.mark.asyncio
    async def test_cleans_up_on_failure(
        self,
        agent: ResearchExportAgent,
        niche_data: dict[str, any],
        niche_scores: dict[str, any],
        personas: list[dict[str, any]],
    ) -> None:
        """Should cleanup folder on export failure."""
        with (
            patch.object(agent, "create_research_folder", new_callable=AsyncMock) as mock_folder,
            patch.object(agent, "create_document_from_content", new_callable=AsyncMock) as mock_doc,
            patch.object(agent.drive_client, "delete_file", new_callable=AsyncMock) as mock_delete,
        ):
            mock_folder.return_value = ("folder-123", "url")
            mock_doc.side_effect = GoogleDocsError("Failed to create doc")

            with pytest.raises(ResearchExportAgentError):
                await agent.export_research(
                    niche_id="niche-123",
                    niche_data=niche_data,
                    niche_scores=niche_scores,
                    niche_research_data=None,
                    personas=personas,
                    persona_research_data=[],
                    industry_scores=[],
                    consolidated_pain_points=[],
                )

            # Verify cleanup attempted
            mock_delete.assert_called_once_with("folder-123")


# ============================================================================
# Tests: Templates
# ============================================================================


class TestTemplates:
    """Tests for template rendering functions."""

    def test_render_niche_overview_doc(
        self,
        niche_data: dict[str, any],
        niche_scores: dict[str, any],
        niche_research_data: dict[str, any],
    ) -> None:
        """Should render niche overview document."""
        content = render_niche_overview_doc(
            niche=niche_data,
            scores=niche_scores,
            research_data=niche_research_data,
        )

        assert "Niche Overview: SaaS Founders" in content
        assert "85/100" in content  # Overall score
        assert "PURSUE" in content  # Recommendation
        assert "$500M - $1B" in content  # Market size

    def test_render_persona_profiles_doc(
        self,
        niche_data: dict[str, any],
        personas: list[dict[str, any]],
    ) -> None:
        """Should render persona profiles document."""
        content = render_persona_profiles_doc(
            niche=niche_data,
            personas=personas,
        )

        assert "Buyer Personas: SaaS Founders" in content
        assert "Technical Founder" in content
        assert "CTO" in content
        assert "Scaling technical infrastructure" in content

    def test_render_pain_points_doc(
        self,
        niche_data: dict[str, any],
        niche_research_data: dict[str, any],
    ) -> None:
        """Should render pain points analysis document."""
        content = render_pain_points_doc(
            niche=niche_data,
            consolidated_pain_points=["Pain 1", "Pain 2"],
            niche_research_data=niche_research_data,
            persona_research_data=[],
            industry_scores=[],
        )

        assert "Pain Points Analysis: SaaS Founders" in content
        assert "Pain 1" in content
        assert "Lead Quality Issues" in content

    def test_render_messaging_angles_doc(
        self,
        niche_data: dict[str, any],
        personas: list[dict[str, any]],
        niche_research_data: dict[str, any],
    ) -> None:
        """Should render messaging angles document."""
        content = render_messaging_angles_doc(
            niche=niche_data,
            personas=personas,
            niche_research_data=niche_research_data,
        )

        assert "Messaging Angles: SaaS Founders" in content
        assert "Automated lead generation" in content
        assert "Focus on SMB market" in content
