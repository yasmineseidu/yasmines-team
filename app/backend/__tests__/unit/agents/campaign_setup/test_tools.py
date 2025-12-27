"""
Unit tests for Campaign Setup Agent tools.

Tests tool functions for prerequisite validation, Instantly campaign creation,
warmup configuration, lead upload, and notifications.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.campaign_setup.tools import (
    _create_content,
    add_leads_to_campaign,
    configure_warmup,
    create_instantly_campaign,
    send_setup_notification,
    update_campaign_setup_complete,
    validate_campaign_prerequisites,
)

# Access the handler functions from SdkMcpTool objects
# The @tool decorator wraps the function in SdkMcpTool, so we need to access .handler
# Pattern from LEARN-017: @tool decorator lacks type stubs
_validate_campaign_prerequisites = validate_campaign_prerequisites.handler  # type: ignore[attr-defined]
_create_instantly_campaign = create_instantly_campaign.handler  # type: ignore[attr-defined]
_configure_warmup = configure_warmup.handler  # type: ignore[attr-defined]
_add_leads_to_campaign = add_leads_to_campaign.handler  # type: ignore[attr-defined]
_update_campaign_setup_complete = update_campaign_setup_complete.handler  # type: ignore[attr-defined]
_send_setup_notification = send_setup_notification.handler  # type: ignore[attr-defined]


class TestCreateContent:
    """Tests for _create_content helper function."""

    def test_creates_success_content(self) -> None:
        """Test creating success content."""
        result = _create_content("Test message")

        assert result["is_error"] is False
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Test message"

    def test_creates_error_content(self) -> None:
        """Test creating error content."""
        result = _create_content("Error occurred", is_error=True)

        assert result["is_error"] is True
        assert result["content"][0]["text"] == "Error occurred"


class TestValidateCampaignPrerequisites:
    """Tests for validate_campaign_prerequisites tool."""

    @pytest.fixture
    def campaign_id(self) -> str:
        """Generate a test campaign UUID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_id_missing(self) -> None:
        """Test that missing campaign_id returns error."""
        result = await _validate_campaign_prerequisites({})

        assert result["is_error"] is True
        assert "campaign_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_uuid_format(self) -> None:
        """Test that invalid UUID format returns error."""
        result = await _validate_campaign_prerequisites({"campaign_id": "invalid-uuid"})

        assert result["is_error"] is True
        assert "Invalid campaign_id format" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_validates_campaign_not_found(self, campaign_id: str) -> None:
        """Test validation when campaign doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch(
            "src.agents.campaign_setup.tools.get_session",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
        ):
            result = await _validate_campaign_prerequisites({"campaign_id": campaign_id})

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["valid"] is False
        assert "Campaign not found" in data["errors"]

    @pytest.mark.asyncio
    async def test_validates_campaign_status_not_approved(self, campaign_id: str) -> None:
        """Test validation when campaign status is not approved."""
        mock_campaign = MagicMock()
        mock_campaign.name = "Test Campaign"
        mock_campaign.sending_status = "building"
        mock_campaign.status = "building"

        mock_session = AsyncMock()
        mock_campaign_result = MagicMock()
        mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

        mock_lead_count_result = MagicMock()
        mock_lead_count_result.scalar.return_value = 100

        mock_session.execute.side_effect = [
            mock_campaign_result,  # Campaign query
            mock_lead_count_result,  # Lead count with emails
            mock_lead_count_result,  # Total lead count
        ]

        with (
            patch(
                "src.agents.campaign_setup.tools.get_session",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch.dict("os.environ", {"INSTANTLY_API_KEY": ""}),
        ):
            result = await _validate_campaign_prerequisites({"campaign_id": campaign_id})

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["valid"] is False
        assert any("not approved" in error for error in data["errors"])

    @pytest.mark.asyncio
    async def test_validates_no_leads_with_emails(self, campaign_id: str) -> None:
        """Test validation when no leads have emails."""
        mock_campaign = MagicMock()
        mock_campaign.name = "Test Campaign"
        mock_campaign.sending_status = "ready"

        mock_session = AsyncMock()
        mock_campaign_result = MagicMock()
        mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

        mock_lead_count_result = MagicMock()
        mock_lead_count_result.scalar.return_value = 0

        mock_total_count_result = MagicMock()
        mock_total_count_result.scalar.return_value = 50

        mock_session.execute.side_effect = [
            mock_campaign_result,
            mock_lead_count_result,
            mock_total_count_result,
        ]

        with (
            patch(
                "src.agents.campaign_setup.tools.get_session",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch.dict("os.environ", {"INSTANTLY_API_KEY": ""}),
        ):
            result = await _validate_campaign_prerequisites({"campaign_id": campaign_id})

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["valid"] is False
        assert any("No leads" in error for error in data["errors"])


class TestCreateInstantlyCampaign:
    """Tests for create_instantly_campaign tool."""

    @pytest.fixture
    def valid_args(self) -> dict[str, Any]:
        """Generate valid arguments for create campaign."""
        return {
            "campaign_id": str(uuid4()),
            "campaign_name": "Test Campaign",
            "sequence_steps_json": json.dumps(
                [
                    {
                        "step_number": 1,
                        "subject": "Hello",
                        "body": "Test body",
                        "delay_days": 0,
                    }
                ]
            ),
            "schedule_json": json.dumps(
                {
                    "name": "Business Hours",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "timezone": "America/New_York",
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                    "saturday": False,
                    "sunday": False,
                }
            ),
            "sending_account_emails": "sender1@example.com,sender2@example.com",
            "daily_limit": 50,
            "email_gap_minutes": 5,
        }

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_name_missing(self) -> None:
        """Test that missing campaign_name returns error."""
        result = await _create_instantly_campaign({"campaign_id": str(uuid4())})

        assert result["is_error"] is True
        assert "campaign_name is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_sequence_json(self) -> None:
        """Test that invalid sequence JSON returns error."""
        result = await _create_instantly_campaign(
            {
                "campaign_id": str(uuid4()),
                "campaign_name": "Test",
                "sequence_steps_json": "invalid json",
                "schedule_json": "{}",
                "sending_account_emails": "test@example.com",
            }
        )

        assert result["is_error"] is True
        assert "Invalid sequence_steps_json" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_when_api_key_missing(self, valid_args: dict[str, Any]) -> None:
        """Test that missing API key returns error."""
        with patch.dict("os.environ", {"INSTANTLY_API_KEY": ""}, clear=True):
            result = await _create_instantly_campaign(valid_args)

        assert result["is_error"] is True
        assert "INSTANTLY_API_KEY not configured" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_creates_campaign_successfully(self, valid_args: dict[str, Any]) -> None:
        """Test successful campaign creation."""
        mock_campaign = MagicMock()
        mock_campaign.id = str(uuid4())
        mock_campaign.name = "Test Campaign"
        mock_status = MagicMock()
        mock_status.name = "DRAFT"
        mock_campaign.status = mock_status

        mock_client = AsyncMock()
        mock_client.create_campaign.return_value = mock_campaign
        mock_client.close = AsyncMock()

        with (
            patch.dict("os.environ", {"INSTANTLY_API_KEY": "test-key"}),  # pragma: allowlist secret
            patch(
                "src.integrations.instantly.InstantlyClient",
                return_value=mock_client,
            ),
        ):
            result = await _create_instantly_campaign(valid_args)

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["instantly_campaign_id"] == mock_campaign.id


class TestConfigureWarmup:
    """Tests for configure_warmup tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_emails_missing(self) -> None:
        """Test that missing account_emails returns error."""
        result = await _configure_warmup({})

        assert result["is_error"] is True
        assert "account_emails is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_when_api_key_missing(self) -> None:
        """Test that missing API key returns error."""
        with patch.dict("os.environ", {"INSTANTLY_API_KEY": ""}, clear=True):
            result = await _configure_warmup({"account_emails": "test@example.com"})

        assert result["is_error"] is True
        assert "INSTANTLY_API_KEY not configured" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_enables_warmup_successfully(self) -> None:
        """Test successful warmup enable."""
        mock_job = MagicMock()
        mock_job.job_id = str(uuid4())

        mock_client = AsyncMock()
        mock_client.enable_warmup_for_accounts.return_value = mock_job
        mock_client.close = AsyncMock()

        with (
            patch.dict("os.environ", {"INSTANTLY_API_KEY": "test-key"}),  # pragma: allowlist secret
            patch(
                "src.integrations.instantly.InstantlyClient",
                return_value=mock_client,
            ),
        ):
            result = await _configure_warmup(
                {"account_emails": "sender1@example.com,sender2@example.com"}
            )

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["accounts_configured"] == 2
        assert data["job_id"] == mock_job.job_id


class TestAddLeadsToCampaign:
    """Tests for add_leads_to_campaign tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_ids_missing(self) -> None:
        """Test that missing campaign IDs returns error."""
        result = await _add_leads_to_campaign({})

        assert result["is_error"] is True
        assert "required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_campaign_id_format(self) -> None:
        """Test that invalid UUID format returns error."""
        result = await _add_leads_to_campaign(
            {
                "internal_campaign_id": "invalid",
                "instantly_campaign_id": str(uuid4()),
            }
        )

        assert result["is_error"] is True
        assert "Invalid internal_campaign_id format" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_adds_leads_successfully(self) -> None:
        """Test successful lead addition."""
        internal_id = str(uuid4())
        instantly_id = str(uuid4())

        # Mock lead data
        mock_lead = MagicMock()
        mock_lead.email = "test@example.com"
        mock_lead.first_name = "John"
        mock_lead.last_name = "Doe"
        mock_lead.company_name = "Acme"
        mock_lead.website = "https://acme.com"
        mock_lead.title = "CEO"
        mock_lead.linkedin_url = "https://linkedin.com/in/johndoe"
        mock_lead.lead_tier = "A"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_lead]
        mock_session.execute.return_value = mock_result

        mock_bulk_result = MagicMock()
        mock_bulk_result.created_count = 1
        mock_bulk_result.updated_count = 0
        mock_bulk_result.failed_count = 0

        mock_client = AsyncMock()
        mock_client.bulk_add_leads.return_value = mock_bulk_result
        mock_client.close = AsyncMock()

        with (
            patch(
                "src.agents.campaign_setup.tools.get_session",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch.dict("os.environ", {"INSTANTLY_API_KEY": "test-key"}),  # pragma: allowlist secret
            patch(
                "src.integrations.instantly.InstantlyClient",
                return_value=mock_client,
            ),
        ):
            result = await _add_leads_to_campaign(
                {
                    "internal_campaign_id": internal_id,
                    "instantly_campaign_id": instantly_id,
                    "batch_size": 1000,
                }
            )

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["leads_added"] == 1


class TestUpdateCampaignSetupComplete:
    """Tests for update_campaign_setup_complete tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_id_missing(self) -> None:
        """Test that missing campaign_id returns error."""
        result = await _update_campaign_setup_complete({})

        assert result["is_error"] is True
        assert "campaign_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_uuid_format(self) -> None:
        """Test that invalid UUID format returns error."""
        result = await _update_campaign_setup_complete({"campaign_id": "invalid"})

        assert result["is_error"] is True
        assert "Invalid campaign_id format" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_updates_campaign_successfully(self) -> None:
        """Test successful campaign update."""
        campaign_id = str(uuid4())

        mock_campaign = MagicMock()
        mock_campaign.import_summary = {}

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_campaign
        mock_session.execute.return_value = mock_result

        with patch(
            "src.agents.campaign_setup.tools.get_session",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
        ):
            result = await _update_campaign_setup_complete(
                {
                    "campaign_id": campaign_id,
                    "instantly_campaign_id": str(uuid4()),
                    "leads_added": 100,
                    "sending_accounts": 5,
                    "warmup_enabled": True,
                }
            )

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["status"] == "campaign_created"


class TestSendSetupNotification:
    """Tests for send_setup_notification tool."""

    @pytest.mark.asyncio
    async def test_skips_when_slack_token_missing(self) -> None:
        """Test that missing Slack token skips notification."""
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": ""}, clear=True):
            result = await _send_setup_notification(
                {
                    "campaign_name": "Test",
                    "instantly_campaign_id": str(uuid4()),
                    "leads_added": 100,
                    "sending_accounts": 5,
                    "daily_limit": 50,
                }
            )

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["sent"] is False
        assert "not configured" in data["reason"]

    @pytest.mark.asyncio
    async def test_sends_notification_successfully(self) -> None:
        """Test successful notification send."""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = {"ts": "12345.67890"}
        mock_client.close = AsyncMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "SLACK_BOT_TOKEN": "test-token",
                    "SLACK_NOTIFICATION_CHANNEL": "#test-channel",
                },
            ),
            patch(
                "src.integrations.slack.SlackClient",
                return_value=mock_client,
            ),
        ):
            result = await _send_setup_notification(
                {
                    "campaign_name": "Test Campaign",
                    "instantly_campaign_id": str(uuid4()),
                    "leads_added": 100,
                    "sending_accounts": 5,
                    "daily_limit": 50,
                }
            )

        assert result["is_error"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["sent"] is True
        assert data["channel"] == "#test-channel"
