"""Unit tests for Verification Finalizer tools module.

Note: The @tool decorator wraps functions in SdkMcpTool objects.
To test them directly, we access the .handler attribute which is the async function.
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.verification_finalizer.tools import (
    _build_approval_keyboard,
    _build_notification_message,
    _get_email_stats,
    _get_tier_stats,
    _lead_model_to_dict,
    _reconstruct_report_from_dict,
    export_leads_to_sheets,
    generate_quality_report,
    get_campaign_verification_stats,
    send_approval_notification,
    update_campaign_verification_complete,
)

# Access the handler functions from SdkMcpTool objects
# The @tool decorator wraps the function in SdkMcpTool, so we need to access .handler
_get_campaign_verification_stats = get_campaign_verification_stats.handler
_generate_quality_report = generate_quality_report.handler
_export_leads_to_sheets = export_leads_to_sheets.handler
_send_approval_notification = send_approval_notification.handler
_update_campaign_verification_complete = update_campaign_verification_complete.handler


class TestGetCampaignVerificationStats:
    """Tests for get_campaign_verification_stats tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_id_missing(self) -> None:
        """Should return error when campaign_id is not provided."""
        result = await _get_campaign_verification_stats({})
        assert result["is_error"] is True
        assert "campaign_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_not_found(self) -> None:
        """Should return error when campaign not found."""
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_campaign_with_niche = AsyncMock(return_value=None)

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with (
            patch(
                "src.agents.verification_finalizer.tools.get_session",
                mock_get_session,
            ),
            patch(
                "src.agents.verification_finalizer.tools.CampaignRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _get_campaign_verification_stats({"campaign_id": "nonexistent"})

        assert result["is_error"] is True
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_stats_on_success(self) -> None:
        """Should return stats when campaign exists."""
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_campaign_with_niche = AsyncMock(
            return_value={
                "campaign": {"id": "test-123", "name": "Test Campaign"},
                "niche": {"name": "SaaS Founders"},
            }
        )

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with (
            patch(
                "src.agents.verification_finalizer.tools.get_session",
                mock_get_session,
            ),
            patch(
                "src.agents.verification_finalizer.tools.CampaignRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.agents.verification_finalizer.tools._get_email_stats",
                new_callable=AsyncMock,
                return_value=[{"email_status": "valid", "count": 100}],
            ),
            patch(
                "src.agents.verification_finalizer.tools._get_tier_stats",
                new_callable=AsyncMock,
                return_value=[{"lead_tier": "A", "total": 50}],
            ),
        ):
            result = await _get_campaign_verification_stats({"campaign_id": "test-123"})

        assert "is_error" not in result or result.get("is_error") is not True
        data = json.loads(result["content"][0]["text"])
        assert "campaign" in data
        assert "niche" in data
        assert "email_stats" in data
        assert "tier_stats" in data

    @pytest.mark.asyncio
    async def test_handles_exception(self) -> None:
        """Should handle exceptions gracefully."""

        @asynccontextmanager
        async def mock_get_session():
            raise Exception("Database error")
            yield  # Make it a generator

        with patch(
            "src.agents.verification_finalizer.tools.get_session",
            mock_get_session,
        ):
            result = await _get_campaign_verification_stats({"campaign_id": "test-123"})

        assert result["is_error"] is True
        assert "Error" in result["content"][0]["text"]


class TestGetEmailStats:
    """Tests for _get_email_stats helper."""

    @pytest.mark.asyncio
    async def test_returns_email_stats(self) -> None:
        """Should return email statistics from query."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("valid", 100, 85.5),
            ("invalid", 20, 45.0),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await _get_email_stats(mock_session, "test-123")

        assert len(result) == 2
        assert result[0]["email_status"] == "valid"
        assert result[0]["count"] == 100
        assert result[0]["avg_score"] == 85.5

    @pytest.mark.asyncio
    async def test_handles_null_avg_score(self) -> None:
        """Should handle NULL average score."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("unknown", 5, None)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await _get_email_stats(mock_session, "test-123")

        assert result[0]["avg_score"] == 0


class TestGetTierStats:
    """Tests for _get_tier_stats helper."""

    @pytest.mark.asyncio
    async def test_returns_tier_stats(self) -> None:
        """Should return tier statistics from query."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("A", 100, 90, 85, 80, 90.0),
            ("B", 200, 180, 170, 160, 75.0),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await _get_tier_stats(mock_session, "test-123")

        assert len(result) == 2
        assert result[0]["lead_tier"] == "A"
        assert result[0]["total"] == 100
        assert result[0]["valid_email"] == 90

    @pytest.mark.asyncio
    async def test_handles_null_tier(self) -> None:
        """Should handle NULL tier."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(None, 10, 5, 3, 2, None)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await _get_tier_stats(mock_session, "test-123")

        assert result[0]["lead_tier"] == "Unknown"
        assert result[0]["avg_score"] == 0


class TestGenerateQualityReport:
    """Tests for generate_quality_report tool."""

    @pytest.mark.asyncio
    async def test_generates_report(self) -> None:
        """Should generate quality report from data."""
        args = {
            "campaign_data": {"id": "test-123", "name": "Test"},
            "niche_data": {"name": "SaaS"},
            "email_stats": [{"email_status": "valid", "count": 100, "avg_score": 80}],
            "tier_stats": [
                {
                    "lead_tier": "A",
                    "total": 50,
                    "valid_email": 45,
                    "has_description": 40,
                    "avg_score": 90,
                }
            ],
        }

        result = await _generate_quality_report(args)

        assert "is_error" not in result or result.get("is_error") is not True
        data = json.loads(result["content"][0]["text"])
        assert "campaign_id" in data
        assert "verification_summary" in data

    @pytest.mark.asyncio
    async def test_handles_empty_data(self) -> None:
        """Should handle empty input data."""
        result = await _generate_quality_report({})

        assert "is_error" not in result or result.get("is_error") is not True
        data = json.loads(result["content"][0]["text"])
        assert data["total_leads"] == 0


class TestExportLeadsToSheets:
    """Tests for export_leads_to_sheets tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_missing_params(self) -> None:
        """Should return error when required params missing."""
        result = await _export_leads_to_sheets({})

        assert result["is_error"] is True
        assert "required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_exports_leads_successfully(self) -> None:
        """Should export leads and return spreadsheet info."""
        report_dict = {
            "campaign_id": "test-123",
            "campaign_name": "Test Campaign",
            "niche_name": "SaaS",
            "total_leads": 100,
            "total_ready": 90,
            "verification_summary": {
                "emails_found": 100,
                "emails_verified": 95,
                "emails_valid": 90,
            },
            "tier_breakdowns": {},
            "cost_summary": {"scraping_cost": 50.0, "enrichment_cost": 100.0},
        }

        mock_lead = MagicMock()
        mock_lead.id = "lead-1"
        mock_lead.first_name = "John"
        mock_lead.last_name = "Doe"
        mock_lead.email = "john@example.com"
        mock_lead.title = "CEO"
        mock_lead.company_name = "Example Inc"
        mock_lead.company_domain = "example.com"
        mock_lead.company_description = "A company"
        mock_lead.lead_score = 90
        mock_lead.lead_tier = "A"
        mock_lead.email_status = "valid"

        mock_session = AsyncMock()
        mock_lead_repo = MagicMock()
        mock_lead_repo.get_campaign_leads = AsyncMock(return_value=[mock_lead])

        mock_exporter = AsyncMock()
        mock_exporter.export_verified_leads.return_value = {
            "spreadsheet_id": "test-id",
            "spreadsheet_url": "https://sheets.google.com/test-id",
        }
        mock_exporter.close = AsyncMock()

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with (
            patch(
                "src.agents.verification_finalizer.tools.get_session",
                mock_get_session,
            ),
            patch(
                "src.agents.verification_finalizer.tools.LeadRepository",
                return_value=mock_lead_repo,
            ),
            patch(
                "src.agents.verification_finalizer.tools.VerifiedLeadsExporter",
                return_value=mock_exporter,
            ),
        ):
            result = await _export_leads_to_sheets(
                {
                    "campaign_id": "test-123",
                    "report_json": json.dumps(report_dict),
                }
            )

        assert "is_error" not in result or result.get("is_error") is not True
        data = json.loads(result["content"][0]["text"])
        assert "spreadsheet_id" in data
        assert "spreadsheet_url" in data


class TestSendApprovalNotification:
    """Tests for send_approval_notification tool."""

    @pytest.mark.asyncio
    async def test_returns_not_sent_when_no_credentials(self) -> None:
        """Should return not sent when Telegram not configured."""
        with patch.dict("os.environ", {}, clear=True):
            result = await _send_approval_notification(
                {
                    "campaign_id": "test-123",
                    "campaign_name": "Test",
                    "total_ready": 100,
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["sent"] is False
        assert "not configured" in data["reason"]

    @pytest.mark.asyncio
    async def test_sends_notification_successfully(self) -> None:
        """Should send notification when configured."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_client.send_message = AsyncMock(return_value=mock_message)

        with (
            patch.dict(
                "os.environ",
                {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_APPROVALS_CHAT_ID": "123"},
            ),
            patch(
                "src.agents.verification_finalizer.tools.TelegramClient",
                return_value=mock_client,
            ),
        ):
            result = await _send_approval_notification(
                {
                    "campaign_id": "test-123",
                    "campaign_name": "Test Campaign",
                    "total_ready": 100,
                    "tier_a_ready": 50,
                    "tier_b_ready": 40,
                    "sheets_url": "https://sheets.google.com/test",
                    "total_cost": 150.0,
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["sent"] is True
        assert data["message_id"] == 12345


class TestBuildNotificationMessage:
    """Tests for _build_notification_message helper."""

    def test_builds_message_with_all_fields(self) -> None:
        """Should build message with all fields formatted."""
        message = _build_notification_message(
            campaign_name="Test Campaign",
            total_ready=1000,
            tier_a_ready=400,
            tier_b_ready=500,
            sheets_url="https://sheets.google.com/test",
            total_cost=250.50,
        )

        assert "Test Campaign" in message
        assert "1,000" in message
        assert "400" in message
        assert "500" in message
        assert "$250.50" in message
        assert "https://sheets.google.com/test" in message

    def test_formats_numbers_with_commas(self) -> None:
        """Should format large numbers with comma separators."""
        message = _build_notification_message(
            campaign_name="Big Campaign",
            total_ready=10000,
            tier_a_ready=5000,
            tier_b_ready=4000,
            sheets_url="https://example.com",
            total_cost=1500.00,
        )

        assert "10,000" in message
        assert "5,000" in message
        assert "$1,500.00" in message


class TestBuildApprovalKeyboard:
    """Tests for _build_approval_keyboard helper."""

    def test_builds_keyboard_with_campaign_id(self) -> None:
        """Should build keyboard with campaign ID in callback data."""
        keyboard = _build_approval_keyboard("campaign-123")

        assert "inline_keyboard" in keyboard
        assert len(keyboard["inline_keyboard"]) == 3

        # Check callback data includes campaign ID
        first_button = keyboard["inline_keyboard"][0][0]
        assert "approve_full_campaign-123" in first_button["callback_data"]

    def test_has_all_approval_options(self) -> None:
        """Should have all approval button options."""
        keyboard = _build_approval_keyboard("test")

        buttons_text = []
        for row in keyboard["inline_keyboard"]:
            for button in row:
                buttons_text.append(button["text"])

        assert "Start Full Personalization" in buttons_text
        assert "Tier A Only" in buttons_text
        assert "Need More Data" in buttons_text
        assert "Reject" in buttons_text


class TestUpdateCampaignVerificationComplete:
    """Tests for update_campaign_verification_complete tool."""

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_id_missing(self) -> None:
        """Should return error when campaign_id not provided."""
        result = await _update_campaign_verification_complete({})

        assert result["is_error"] is True
        assert "campaign_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_error_when_campaign_not_found(self) -> None:
        """Should return error when campaign not found."""
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.update_campaign = AsyncMock(return_value=None)

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with (
            patch(
                "src.agents.verification_finalizer.tools.get_session",
                mock_get_session,
            ),
            patch(
                "src.agents.verification_finalizer.tools.CampaignRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _update_campaign_verification_complete({"campaign_id": "nonexistent"})

        assert result["is_error"] is True
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_updates_campaign_successfully(self) -> None:
        """Should update campaign and return success."""
        mock_session = AsyncMock()
        mock_campaign = MagicMock()
        mock_campaign.id = "test-123"
        mock_repo = MagicMock()
        mock_repo.update_campaign = AsyncMock(return_value=mock_campaign)

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with (
            patch(
                "src.agents.verification_finalizer.tools.get_session",
                mock_get_session,
            ),
            patch(
                "src.agents.verification_finalizer.tools.CampaignRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.agents.verification_finalizer.tools._log_verification_complete",
                new_callable=AsyncMock,
            ),
        ):
            result = await _update_campaign_verification_complete(
                {
                    "campaign_id": "test-123",
                    "sheets_url": "https://sheets.google.com/test",
                    "total_ready": 100,
                    "report_json": "{}",
                }
            )

        assert "is_error" not in result or result.get("is_error") is not True
        data = json.loads(result["content"][0]["text"])
        assert data["updated"] is True
        assert data["status"] == "verification_complete"


class TestLeadModelToDict:
    """Tests for _lead_model_to_dict helper."""

    def test_converts_lead_model_to_dict(self) -> None:
        """Should convert lead model to dictionary."""
        mock_lead = MagicMock()
        mock_lead.id = "lead-123"
        mock_lead.first_name = "John"
        mock_lead.last_name = "Doe"
        mock_lead.email = "john@example.com"
        mock_lead.title = "CEO"
        mock_lead.company_name = "Example Inc"
        mock_lead.company_domain = "example.com"
        mock_lead.company_description = "A great company"
        mock_lead.lead_score = 90
        mock_lead.lead_tier = "A"
        mock_lead.email_status = "valid"

        result = _lead_model_to_dict(mock_lead)

        assert result["id"] == "lead-123"
        assert result["first_name"] == "John"
        assert result["email"] == "john@example.com"
        assert result["lead_score"] == 90


class TestReconstructReportFromDict:
    """Tests for _reconstruct_report_from_dict helper."""

    def test_reconstructs_full_report(self) -> None:
        """Should reconstruct complete report from dictionary."""
        data = {
            "campaign_id": "test-123",
            "campaign_name": "Test Campaign",
            "niche_name": "SaaS Founders",
            "total_leads": 1000,
            "total_ready": 850,
            "verification_summary": {
                "emails_found": 1000,
                "emails_verified": 950,
                "emails_valid": 850,
                "emails_invalid": 80,
                "emails_risky": 10,
                "emails_catchall": 10,
            },
            "tier_breakdowns": {
                "A": {
                    "total": 300,
                    "verified": 280,
                    "enriched": 270,
                    "ready": 260,
                    "avg_score": 90.0,
                    "avg_enrichment_cost": 0.05,
                }
            },
            "cost_summary": {
                "scraping_cost": 100.0,
                "enrichment_cost": 250.0,
                "verification_cost": 50.0,
            },
        }

        report = _reconstruct_report_from_dict(data)

        assert report.campaign_id == "test-123"
        assert report.campaign_name == "Test Campaign"
        assert report.total_leads == 1000
        assert report.verification_summary.emails_valid == 850
        assert "A" in report.tier_breakdowns
        assert report.tier_breakdowns["A"].total == 300
        assert report.cost_summary.total_cost == 400.0

    def test_handles_empty_data(self) -> None:
        """Should handle empty dictionary with defaults."""
        report = _reconstruct_report_from_dict({})

        assert report.campaign_id == ""
        assert report.total_leads == 0
        assert report.verification_summary.emails_found == 0
        assert len(report.tier_breakdowns) == 0
