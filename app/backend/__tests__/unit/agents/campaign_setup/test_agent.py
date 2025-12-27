"""
Unit tests for Campaign Setup Agent.

Tests the CampaignSetupAgent class, configuration, and result parsing.
"""

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.campaign_setup.agent import (
    CampaignSetupAgent,
    CampaignSetupConfig,
    run_campaign_setup,
)
from src.agents.campaign_setup.schemas import (
    CampaignSetupResult,
    EmailSequenceStep,
    SendingSchedule,
)


class TestCampaignSetupConfig:
    """Tests for CampaignSetupConfig dataclass."""

    def test_default_config_has_correct_values(self) -> None:
        """Test that default config has expected values."""
        config = CampaignSetupConfig()

        assert config.daily_limit == 50
        assert config.email_gap_minutes == 5
        assert config.enable_warmup is True
        assert config.send_notification is True
        assert config.lead_batch_size == 1000

    def test_default_sequence_has_four_steps(self) -> None:
        """Test that default sequence has 4 steps."""
        config = CampaignSetupConfig()

        assert len(config.default_sequence) == 4
        assert config.default_sequence[0].step_number == 1
        assert config.default_sequence[0].delay_days == 0
        assert config.default_sequence[3].step_number == 4
        assert config.default_sequence[3].delay_days == 7

    def test_default_schedule_is_weekdays_only(self) -> None:
        """Test that default schedule is weekdays only."""
        config = CampaignSetupConfig()
        schedule = config.default_schedule

        assert schedule.monday is True
        assert schedule.tuesday is True
        assert schedule.wednesday is True
        assert schedule.thursday is True
        assert schedule.friday is True
        assert schedule.saturday is False
        assert schedule.sunday is False

    def test_default_schedule_timezone_is_est(self) -> None:
        """Test that default schedule uses EST timezone."""
        config = CampaignSetupConfig()

        assert config.default_schedule.timezone == "America/New_York"

    def test_custom_config_overrides_defaults(self) -> None:
        """Test that custom config values override defaults."""
        config = CampaignSetupConfig(
            daily_limit=100,
            email_gap_minutes=10,
            enable_warmup=False,
            send_notification=False,
        )

        assert config.daily_limit == 100
        assert config.email_gap_minutes == 10
        assert config.enable_warmup is False
        assert config.send_notification is False


class TestEmailSequenceStep:
    """Tests for EmailSequenceStep schema."""

    def test_to_instantly_format_basic(self) -> None:
        """Test converting step to Instantly format."""
        step = EmailSequenceStep(
            step_number=1,
            subject="Hello {{firstName}}",
            body="Test body",
            delay_days=0,
        )

        result = step.to_instantly_format()

        assert result["type"] == "email"
        assert result["delay"] == 0
        assert len(result["variants"]) == 1
        assert result["variants"][0]["subject"] == "Hello {{firstName}}"
        assert result["variants"][0]["body"] == "Test body"

    def test_to_instantly_format_with_delay(self) -> None:
        """Test step with delay converts correctly."""
        step = EmailSequenceStep(
            step_number=2,
            subject="Follow up",
            body="Just checking in",
            delay_days=3,
        )

        result = step.to_instantly_format()

        assert result["delay"] == 3

    def test_to_instantly_format_with_variants(self) -> None:
        """Test step with A/B variants converts correctly."""
        step = EmailSequenceStep(
            step_number=1,
            subject="Version A",
            body="Body A",
            delay_days=0,
            variants=[{"subject": "Version B", "body": "Body B"}],
        )

        result = step.to_instantly_format()

        assert len(result["variants"]) == 2
        assert result["variants"][0]["subject"] == "Version A"
        assert result["variants"][1]["subject"] == "Version B"


class TestSendingSchedule:
    """Tests for SendingSchedule schema."""

    def test_to_instantly_format(self) -> None:
        """Test converting schedule to Instantly format."""
        schedule = SendingSchedule(
            name="Test Schedule",
            start_time="08:00",
            end_time="18:00",
            timezone="America/Los_Angeles",
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            saturday=True,
            sunday=False,
        )

        result = schedule.to_instantly_format()

        assert result["name"] == "Test Schedule"
        assert result["timing"]["from"] == "08:00"
        assert result["timing"]["to"] == "18:00"
        assert result["timezone"] == "America/Los_Angeles"
        assert result["days"]["0"] is True  # Monday
        assert result["days"]["5"] is True  # Saturday
        assert result["days"]["6"] is False  # Sunday


class TestCampaignSetupResult:
    """Tests for CampaignSetupResult schema."""

    def test_to_dict_includes_all_fields(self) -> None:
        """Test that to_dict includes all result fields."""
        result = CampaignSetupResult(
            success=True,
            campaign_id="test-id",
            instantly_campaign_id="instantly-id",
            campaign_name="Test Campaign",
            leads_added=100,
            sending_accounts=5,
            warmup_enabled=True,
            warmup_job_id="job-123",
            sequence_steps=4,
            daily_limit=50,
            created_at=datetime.now(UTC),
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["campaign_id"] == "test-id"
        assert data["instantly_campaign_id"] == "instantly-id"
        assert data["campaign_name"] == "Test Campaign"
        assert data["leads_added"] == 100
        assert data["sending_accounts"] == 5
        assert data["warmup_enabled"] is True
        assert data["warmup_job_id"] == "job-123"
        assert data["sequence_steps"] == 4
        assert data["daily_limit"] == 50

    def test_to_dict_handles_none_values(self) -> None:
        """Test that to_dict handles None values correctly."""
        result = CampaignSetupResult(
            success=False,
            campaign_id="test-id",
            error="Something went wrong",
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["instantly_campaign_id"] is None
        assert data["error"] == "Something went wrong"
        assert data["created_at"] is None


class TestCampaignSetupAgent:
    """Tests for CampaignSetupAgent class."""

    @pytest.fixture
    def agent(self) -> CampaignSetupAgent:
        """Create an agent instance for testing."""
        return CampaignSetupAgent()

    @pytest.fixture
    def campaign_id(self) -> str:
        """Generate a test campaign UUID."""
        return str(uuid4())

    def test_agent_initializes_with_default_config(self, agent: CampaignSetupAgent) -> None:
        """Test that agent initializes with default config."""
        assert agent.config is not None
        assert agent.config.daily_limit == 50
        assert len(agent.config.default_sequence) == 4

    def test_agent_initializes_with_custom_config(self) -> None:
        """Test that agent initializes with custom config."""
        config = CampaignSetupConfig(daily_limit=100)
        agent = CampaignSetupAgent(config=config)

        assert agent.config.daily_limit == 100

    def test_agent_removes_anthropic_api_key(self) -> None:
        """Test that agent removes ANTHROPIC_API_KEY from environment."""
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "test-key"},  # pragma: allowlist secret
        ):
            import os

            # Before creating agent
            assert "ANTHROPIC_API_KEY" in os.environ

            _agent = CampaignSetupAgent()  # noqa: F841 - side effect removes key

            # After creating agent - should be removed
            assert "ANTHROPIC_API_KEY" not in os.environ

    def test_agent_has_correct_system_prompt(self, agent: CampaignSetupAgent) -> None:
        """Test that agent has correct system prompt."""
        assert "Campaign Setup agent" in agent.SYSTEM_PROMPT
        assert "Phase 5.1" in agent.SYSTEM_PROMPT
        assert "Instantly" in agent.SYSTEM_PROMPT

    def test_parse_agent_response_extracts_json(
        self, agent: CampaignSetupAgent, campaign_id: str
    ) -> None:
        """Test parsing JSON from agent response."""
        response_text = """
        I've completed the setup. Here's the result:
        {"success": true, "instantly_campaign_id": "instant-123", "leads_added": 50}
        """

        result = agent._parse_agent_response(campaign_id, response_text)

        assert result.success is True
        assert result.instantly_campaign_id == "instant-123"
        assert result.leads_added == 50

    def test_parse_agent_response_handles_success_indicators(
        self, agent: CampaignSetupAgent, campaign_id: str
    ) -> None:
        """Test parsing when JSON is missing but success indicators present."""
        response_text = "Campaign setup complete. Leads added successfully."

        result = agent._parse_agent_response(campaign_id, response_text)

        assert result.success is True

    def test_parse_agent_response_handles_failure_indicators(
        self, agent: CampaignSetupAgent, campaign_id: str
    ) -> None:
        """Test parsing when failure indicators are present."""
        response_text = "Prerequisites fail: No leads found in campaign."

        result = agent._parse_agent_response(campaign_id, response_text)

        assert result.success is False

    def test_parse_agent_response_handles_invalid_json(
        self, agent: CampaignSetupAgent, campaign_id: str
    ) -> None:
        """Test parsing when JSON is invalid."""
        response_text = "{invalid json structure"

        result = agent._parse_agent_response(campaign_id, response_text)

        # Should not crash and should return a result
        assert result.campaign_id == campaign_id


class TestCampaignSetupAgentIntegration:
    """Integration-style tests for CampaignSetupAgent (mocked SDK)."""

    @pytest.fixture
    def campaign_id(self) -> str:
        """Generate a test campaign UUID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_setup_campaign_handles_cli_not_found(self, campaign_id: str) -> None:
        """Test handling of CLI not found error."""
        from claude_agent_sdk import CLINotFoundError

        agent = CampaignSetupAgent()

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=CLINotFoundError("CLI not found"),
        ):
            result = await agent.setup_campaign(campaign_id)

        assert result.success is False
        assert "CLI not installed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_setup_campaign_handles_process_error(self, campaign_id: str) -> None:
        """Test handling of process error."""
        from claude_agent_sdk import ProcessError

        agent = CampaignSetupAgent()

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=ProcessError(
                message="Process failed",
                exit_code=1,
                stderr="Error message",
            ),
        ):
            result = await agent.setup_campaign(campaign_id)

        assert result.success is False
        assert "process error" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_setup_campaign_handles_sdk_error(self, campaign_id: str) -> None:
        """Test handling of generic SDK error."""
        from claude_agent_sdk import ClaudeSDKError

        agent = CampaignSetupAgent()

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=ClaudeSDKError("SDK error"),
        ):
            result = await agent.setup_campaign(campaign_id)

        assert result.success is False
        assert "SDK error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_setup_campaign_handles_unexpected_error(self, campaign_id: str) -> None:
        """Test handling of unexpected errors."""
        agent = CampaignSetupAgent()

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = await agent.setup_campaign(campaign_id)

        assert result.success is False
        assert result.error is not None


class TestRunCampaignSetup:
    """Tests for run_campaign_setup convenience function."""

    @pytest.fixture
    def campaign_id(self) -> str:
        """Generate a test campaign UUID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_run_campaign_setup_creates_agent(self, campaign_id: str) -> None:
        """Test that run_campaign_setup creates and runs agent."""
        from claude_agent_sdk import CLINotFoundError

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=CLINotFoundError("CLI not found"),
        ):
            result = await run_campaign_setup(campaign_id)

        assert result.campaign_id == campaign_id
        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_campaign_setup_with_custom_config(self, campaign_id: str) -> None:
        """Test run_campaign_setup with custom config."""
        from claude_agent_sdk import CLINotFoundError

        config = CampaignSetupConfig(daily_limit=100)

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=CLINotFoundError("CLI not found"),
        ):
            result = await run_campaign_setup(campaign_id, config=config)

        assert result.campaign_id == campaign_id

    @pytest.mark.asyncio
    async def test_run_campaign_setup_with_custom_sequence(self, campaign_id: str) -> None:
        """Test run_campaign_setup with custom sequence."""
        from claude_agent_sdk import CLINotFoundError

        custom_sequence = [
            EmailSequenceStep(
                step_number=1,
                subject="Custom Subject",
                body="Custom body",
                delay_days=0,
            )
        ]

        with patch(
            "src.agents.campaign_setup.agent.query",
            side_effect=CLINotFoundError("CLI not found"),
        ):
            result = await run_campaign_setup(campaign_id, sequence=custom_sequence)

        assert result.campaign_id == campaign_id


class TestCampaignSetupAgentSuccessFlow:
    """Tests for successful agent execution flow."""

    @pytest.fixture
    def campaign_id(self) -> str:
        """Generate a test campaign UUID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_successful_setup_flow(self, campaign_id: str) -> None:
        """Test complete successful setup flow."""
        from claude_agent_sdk import AssistantMessage, TextBlock

        agent = CampaignSetupAgent()

        # Mock successful response
        mock_message = MagicMock(spec=AssistantMessage)
        mock_text_block = MagicMock(spec=TextBlock)
        mock_text_block.text = json.dumps(
            {
                "success": True,
                "instantly_campaign_id": "inst-123",
                "leads_added": 100,
                "sending_accounts": 5,
                "warmup_enabled": True,
            }
        )
        mock_message.content = [mock_text_block]

        async def mock_query(*args: Any, **kwargs: Any) -> Any:
            yield mock_message

        with patch("src.agents.campaign_setup.agent.query", mock_query):
            result = await agent.setup_campaign(campaign_id)

        assert result.success is True
        assert result.instantly_campaign_id == "inst-123"
        assert result.leads_added == 100
        assert result.sending_accounts == 5
        assert result.warmup_enabled is True
