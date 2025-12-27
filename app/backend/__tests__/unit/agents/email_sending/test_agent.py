"""
Unit tests for Email Sending Agent.

Tests agent initialization, configuration, result handling,
and SDK integration patterns.
"""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agents.email_sending.agent import (
    DirectEmailUploader,
    EmailSendingAgent,
    EmailSendingConfig,
)
from src.agents.email_sending.schemas import (
    BatchResult,
    EmailSendingResult,
    SendingProgress,
)

# =============================================================================
# Schema Tests
# =============================================================================


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_creation(self) -> None:
        """Test creating a BatchResult."""
        result = BatchResult(
            batch_number=1,
            leads_uploaded=95,
            leads_failed=5,
            lead_ids=["id1", "id2"],
        )
        assert result.batch_number == 1
        assert result.leads_uploaded == 95
        assert result.leads_failed == 5
        assert len(result.lead_ids) == 2

    def test_batch_result_success_rate(self) -> None:
        """Test success rate calculation."""
        result = BatchResult(
            batch_number=1,
            leads_uploaded=90,
            leads_failed=10,
        )
        assert result.success_rate == 90.0

    def test_batch_result_success_rate_zero_total(self) -> None:
        """Test success rate with zero total."""
        result = BatchResult(
            batch_number=1,
            leads_uploaded=0,
            leads_failed=0,
        )
        assert result.success_rate == 0.0

    def test_batch_result_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = BatchResult(
            batch_number=1,
            leads_uploaded=100,
            leads_failed=0,
        )
        data = result.to_dict()
        assert data["batch_number"] == 1
        assert data["leads_uploaded"] == 100
        assert data["success_rate"] == 100.0


class TestSendingProgress:
    """Tests for SendingProgress dataclass."""

    def test_sending_progress_creation(self) -> None:
        """Test creating a SendingProgress."""
        progress = SendingProgress(
            total_leads=1000,
            leads_uploaded=500,
            batches_completed=5,
        )
        assert progress.total_leads == 1000
        assert progress.leads_uploaded == 500
        assert progress.upload_rate == 50.0

    def test_sending_progress_upload_rate_zero_leads(self) -> None:
        """Test upload rate with zero total leads."""
        progress = SendingProgress(total_leads=0, leads_uploaded=0)
        assert progress.upload_rate == 0.0

    def test_sending_progress_to_dict(self) -> None:
        """Test converting to dictionary."""
        progress = SendingProgress(
            total_leads=100,
            leads_uploaded=90,
            tier_a_uploaded=30,
            tier_b_uploaded=40,
            tier_c_uploaded=20,
        )
        data = progress.to_dict()
        assert data["upload_rate"] == 90.0
        assert data["tier_a_uploaded"] == 30


class TestEmailSendingResult:
    """Tests for EmailSendingResult dataclass."""

    def test_email_sending_result_creation(self) -> None:
        """Test creating an EmailSendingResult."""
        campaign_id = str(uuid4())
        result = EmailSendingResult(
            success=True,
            campaign_id=campaign_id,
            total_uploaded=100,
            sending_started=True,
        )
        assert result.success is True
        assert result.campaign_id == campaign_id
        assert result.total_uploaded == 100

    def test_email_sending_result_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = EmailSendingResult(
            success=True,
            campaign_id="test-id",
            instantly_campaign_id="instantly-id",
            total_uploaded=100,
            total_leads=100,
            sending_started=True,
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["campaign_id"] == "test-id"
        assert data["instantly_campaign_id"] == "instantly-id"

    def test_email_sending_result_handoff_data(self) -> None:
        """Test getting handoff data for next agent."""
        result = EmailSendingResult(
            success=True,
            campaign_id="test-campaign",
            instantly_campaign_id="instantly-campaign",
            total_uploaded=100,
            tier_a_uploaded=30,
            tier_b_uploaded=40,
            tier_c_uploaded=30,
        )
        handoff = result.get_handoff_data()
        assert handoff["campaign_id"] == "test-campaign"
        assert handoff["instantly_campaign_id"] == "instantly-campaign"
        assert handoff["total_uploaded"] == 100
        assert handoff["tier_breakdown"]["tier_a_uploaded"] == 30


# =============================================================================
# Configuration Tests
# =============================================================================


class TestEmailSendingConfig:
    """Tests for EmailSendingConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = EmailSendingConfig()
        assert config.batch_size == 100
        assert config.max_parallel_batches == 5
        assert config.delay_between_batches_seconds == 2.0
        assert config.stagger_start_seconds == 0.5
        assert config.checkpoint_interval_leads == 500
        assert config.max_budget_per_campaign == 100.0

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = EmailSendingConfig(
            batch_size=50,
            max_parallel_batches=3,
            max_budget_per_campaign=50.0,
        )
        assert config.batch_size == 50
        assert config.max_parallel_batches == 3
        assert config.max_budget_per_campaign == 50.0


# =============================================================================
# Agent Tests
# =============================================================================


class TestEmailSendingAgentInitialization:
    """Tests for EmailSendingAgent initialization."""

    def test_agent_has_correct_name(self) -> None:
        """Test agent has correct name."""
        agent = EmailSendingAgent()
        assert agent.name == "email_sending_agent"

    def test_agent_has_description(self) -> None:
        """Test agent has description."""
        agent = EmailSendingAgent()
        assert "Instantly" in agent.description

    def test_agent_system_prompt_contains_key_elements(self) -> None:
        """Test system prompt contains key operational elements."""
        agent = EmailSendingAgent()
        prompt = agent.system_prompt

        # Check for key elements from YAML spec
        assert "batch" in prompt.lower()
        assert "tier" in prompt.lower()
        assert "upload" in prompt.lower()
        assert "instantly" in prompt.lower()

    def test_agent_removes_anthropic_api_key(self) -> None:
        """Test agent removes ANTHROPIC_API_KEY from environment (LEARN-001)."""
        import os

        os.environ["ANTHROPIC_API_KEY"] = "test-key"  # pragma: allowlist secret
        agent = EmailSendingAgent()
        assert "ANTHROPIC_API_KEY" not in os.environ
        assert agent is not None

    def test_agent_with_custom_config(self) -> None:
        """Test agent with custom configuration."""
        config = EmailSendingConfig(batch_size=50)
        agent = EmailSendingAgent(config=config)
        assert agent.config.batch_size == 50


class TestEmailSendingAgentExecution:
    """Tests for EmailSendingAgent execution."""

    @pytest.fixture
    def agent(self) -> EmailSendingAgent:
        """Create agent fixture."""
        return EmailSendingAgent()

    @pytest.mark.asyncio
    async def test_send_emails_handles_cli_not_found(self, agent: EmailSendingAgent) -> None:
        """Test handling of CLINotFoundError."""
        from claude_agent_sdk import CLINotFoundError

        with patch(
            "src.agents.email_sending.agent.query",
            side_effect=CLINotFoundError("CLI not found"),
        ):
            result = await agent.send_emails("campaign-id", "instantly-id")

        assert result.success is False
        assert "CLI not installed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_send_emails_handles_process_error(self, agent: EmailSendingAgent) -> None:
        """Test handling of ProcessError."""
        from claude_agent_sdk import ProcessError

        with patch(
            "src.agents.email_sending.agent.query",
            side_effect=ProcessError(
                message="Process failed",
                exit_code=1,
                stderr="Process failed",
            ),
        ):
            result = await agent.send_emails("campaign-id", "instantly-id")

        assert result.success is False
        assert "Process error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_send_emails_handles_sdk_error(self, agent: EmailSendingAgent) -> None:
        """Test handling of ClaudeSDKError."""
        from claude_agent_sdk import ClaudeSDKError

        with patch(
            "src.agents.email_sending.agent.query",
            side_effect=ClaudeSDKError("SDK error"),
        ):
            result = await agent.send_emails("campaign-id", "instantly-id")

        assert result.success is False
        assert "SDK error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_send_emails_handles_generic_exception(self, agent: EmailSendingAgent) -> None:
        """Test handling of generic exception."""
        with patch(
            "src.agents.email_sending.agent.query",
            side_effect=Exception("Unexpected error"),
        ):
            result = await agent.send_emails("campaign-id", "instantly-id")

        assert result.success is False
        assert "Unexpected error" in (result.error or "")


class TestEmailSendingAgentProgressTracking:
    """Tests for progress tracking in EmailSendingAgent."""

    @pytest.fixture
    def agent(self) -> EmailSendingAgent:
        """Create agent fixture."""
        return EmailSendingAgent()

    def test_reset_progress(self, agent: EmailSendingAgent) -> None:
        """Test progress reset."""
        agent._progress.leads_uploaded = 100
        agent._progress.total_leads = 200
        agent._reset_progress()
        assert agent._progress.leads_uploaded == 0
        assert agent._progress.total_leads == 0

    def test_update_progress_from_response_total_leads(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from response with total_leads."""
        agent._update_progress_from_response({"total_leads": 500})
        assert agent._progress.total_leads == 500

    def test_update_progress_from_response_leads_uploaded(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from response with leads_uploaded."""
        agent._update_progress_from_response({"leads_uploaded": 50})
        agent._update_progress_from_response({"leads_uploaded": 50})
        assert agent._progress.leads_uploaded == 100

    def test_update_progress_from_response_by_tier(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from response with tier data."""
        agent._update_progress_from_response(
            {"by_tier": {"tier_a": 30, "tier_b": 40, "tier_c": 30}}
        )
        assert agent._progress.tier_a_uploaded == 30
        assert agent._progress.tier_b_uploaded == 40
        assert agent._progress.tier_c_uploaded == 30

    def test_update_progress_from_response_batch_success(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from successful batch."""
        agent._update_progress_from_response({"success": True, "batch_number": 1})
        assert agent._progress.batches_completed == 1

    def test_update_progress_from_response_batch_failure(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from failed batch."""
        agent._update_progress_from_response({"is_error": True, "batch_number": 1})
        assert agent._progress.batches_failed == 1

    def test_update_progress_from_response_cost(self, agent: EmailSendingAgent) -> None:
        """Test updating progress from response with cost."""
        agent._update_progress_from_response({"cost_incurred": 0.1})
        assert agent._progress.cost_incurred == 0.1


class TestEmailSendingAgentJsonExtraction:
    """Tests for JSON extraction in EmailSendingAgent."""

    def test_extract_json_data_valid(self) -> None:
        """Test extracting valid JSON from text."""
        text = 'Here is the result: {"success": true, "count": 100}'
        result = EmailSendingAgent._extract_json_data(text)
        assert result is not None
        assert result["success"] is True
        assert result["count"] == 100

    def test_extract_json_data_no_json(self) -> None:
        """Test extracting from text without JSON."""
        text = "This is plain text without JSON"
        result = EmailSendingAgent._extract_json_data(text)
        assert result is None

    def test_extract_json_data_invalid_json(self) -> None:
        """Test extracting invalid JSON."""
        text = "Here is invalid: {success: true}"
        result = EmailSendingAgent._extract_json_data(text)
        assert result is None


# =============================================================================
# Direct Uploader Tests
# =============================================================================


class TestDirectEmailUploader:
    """Tests for DirectEmailUploader."""

    def test_uploader_initialization(self) -> None:
        """Test uploader initialization."""
        uploader = DirectEmailUploader()
        assert uploader.name == "direct_email_uploader"

    def test_uploader_with_custom_config(self) -> None:
        """Test uploader with custom configuration."""
        config = EmailSendingConfig(batch_size=50)
        uploader = DirectEmailUploader(config=config)
        assert uploader.config.batch_size == 50

    @pytest.mark.asyncio
    async def test_upload_batch_success(self) -> None:
        """Test successful batch upload."""
        uploader = DirectEmailUploader()

        mock_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "batch_number": 1,
                            "leads_uploaded": 10,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

        with patch(
            "src.agents.email_sending.tools.upload_to_instantly_impl",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await uploader.upload_batch(
                instantly_campaign_id="instantly-id",
                campaign_id="campaign-id",
                leads=[{"id": "1", "email": "test@example.com"}],
                batch_number=1,
            )

        assert result["success"] is True
        assert result["leads_uploaded"] == 10

    @pytest.mark.asyncio
    async def test_upload_batch_failure(self) -> None:
        """Test failed batch upload."""
        uploader = DirectEmailUploader()

        mock_result = {
            "content": [{"type": "text", "text": '{"error": "API error"}'}],
            "is_error": True,
        }

        with patch(
            "src.agents.email_sending.tools.upload_to_instantly_impl",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await uploader.upload_batch(
                instantly_campaign_id="instantly-id",
                campaign_id="campaign-id",
                leads=[{"id": "1", "email": "test@example.com"}],
                batch_number=1,
            )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_upload_parallel_batches(self) -> None:
        """Test parallel batch upload."""
        config = EmailSendingConfig(
            max_parallel_batches=2,
            stagger_start_seconds=0.01,
            delay_between_batches_seconds=0.01,
        )
        uploader = DirectEmailUploader(config=config)

        mock_result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "leads_uploaded": 10,
                        }
                    ),
                }
            ],
            "is_error": False,
        }

        batches = [
            [{"id": "1", "email": "test1@example.com"}],
            [{"id": "2", "email": "test2@example.com"}],
            [{"id": "3", "email": "test3@example.com"}],
        ]

        with patch(
            "src.agents.email_sending.tools.upload_to_instantly_impl",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            results = await uploader.upload_parallel_batches(
                instantly_campaign_id="instantly-id",
                campaign_id="campaign-id",
                batches=batches,
            )

        assert len(results) == 3
        assert all(r.get("success") for r in results)
