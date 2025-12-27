"""
Unit tests for Email Sending Agent tools.

Tests SDK MCP tools for lead upload, batch processing,
verification, and campaign management.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.email_sending.tools import (
    _format_lead_for_instantly,
    _retry_with_exponential_backoff,
    check_resume_state_impl,
    get_campaign_cost,
    load_leads_impl,
    reset_cost_tracker,
    start_sending_impl,
    update_sending_stats_impl,
    upload_to_instantly_impl,
    verify_upload_impl,
)

# =============================================================================
# Helper Function Tests
# =============================================================================


class TestFormatLeadForInstantly:
    """Tests for _format_lead_for_instantly helper."""

    def test_formats_lead_with_all_fields(self) -> None:
        """Test formatting lead with all fields."""
        lead = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Corp",
        }
        email_data = {
            "subject_line": "Quick question",
            "full_email": "Hi John, test email body",
        }

        result = _format_lead_for_instantly(lead, email_data)

        assert result["email"] == "test@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["company_name"] == "Acme Corp"
        assert result["custom_variables"]["subject"] == "Quick question"
        assert result["custom_variables"]["body"] == "Hi John, test email body"

    def test_formats_lead_with_missing_fields(self) -> None:
        """Test formatting lead with missing optional fields."""
        lead = {"email": "test@example.com"}
        email_data = {}

        result = _format_lead_for_instantly(lead, email_data)

        assert result["email"] == "test@example.com"
        assert result["first_name"] == ""
        assert result["custom_variables"]["subject"] == ""


class TestRetryWithExponentialBackoff:
    """Tests for _retry_with_exponential_backoff helper."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self) -> None:
        """Test successful function on first attempt."""
        mock_func = AsyncMock(return_value={"success": True})

        result = await _retry_with_exponential_backoff(mock_func, max_attempts=3)

        assert result["success"] is True
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self) -> None:
        """Test successful function after transient failures."""
        mock_func = AsyncMock(
            side_effect=[
                ConnectionError("Connection failed"),
                TimeoutError("Timeout"),
                {"success": True},
            ]
        )

        result = await _retry_with_exponential_backoff(
            mock_func,
            max_attempts=5,
            base_delay=0.01,
            max_delay=0.1,
        )

        assert result["success"] is True
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self) -> None:
        """Test retry exhausts all attempts."""
        mock_func = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with pytest.raises(ConnectionError):
            await _retry_with_exponential_backoff(
                mock_func,
                max_attempts=3,
                base_delay=0.01,
                max_delay=0.1,
            )

        assert mock_func.call_count == 3


# =============================================================================
# Cost Tracker Tests
# =============================================================================


class TestCostTracker:
    """Tests for cost tracking functions."""

    def test_get_campaign_cost_empty(self) -> None:
        """Test getting cost for unknown campaign."""
        reset_cost_tracker()
        cost = get_campaign_cost("unknown-campaign")
        assert cost == 0.0

    def test_reset_cost_tracker_all(self) -> None:
        """Test resetting all cost tracking."""
        reset_cost_tracker()
        # Cost would be tracked during upload_to_instantly
        cost = get_campaign_cost("test-campaign")
        assert cost == 0.0


# =============================================================================
# Tool Implementation Tests
# =============================================================================


class TestCheckResumeStateImpl:
    """Tests for check_resume_state_impl."""

    @pytest.fixture
    def mock_session_factory(self) -> Any:
        """Create a factory for mock sessions."""

        def factory(mock_row: Any = None, side_effect: Exception | None = None) -> Any:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_row

            mock_session = AsyncMock()
            if side_effect:
                mock_session.execute = AsyncMock(side_effect=side_effect)
            else:
                mock_session.execute = AsyncMock(return_value=mock_result)

            # Create async context manager
            cm = AsyncMock()
            cm.__aenter__.return_value = mock_session
            cm.__aexit__.return_value = None
            return cm

        return factory

    @pytest.mark.asyncio
    async def test_check_resume_state_fresh_start(self, mock_session_factory: Any) -> None:
        """Test checking resume state for fresh campaign."""
        mock_row = MagicMock()
        mock_row.batches_completed = 0
        mock_row.leads_uploaded = 0
        mock_row.last_batch = 0

        mock_cm = mock_session_factory(mock_row)

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await check_resume_state_impl({"campaign_id": str(uuid4())})

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["is_resuming"] is False
        assert content["start_from_batch"] == 1

    @pytest.mark.asyncio
    async def test_check_resume_state_resuming(self, mock_session_factory: Any) -> None:
        """Test checking resume state for resuming campaign."""
        mock_row = MagicMock()
        mock_row.batches_completed = 5
        mock_row.leads_uploaded = 500
        mock_row.last_batch = 5

        mock_cm = mock_session_factory(mock_row)

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await check_resume_state_impl({"campaign_id": str(uuid4())})

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["is_resuming"] is True
        assert content["start_from_batch"] == 6
        assert content["previously_uploaded"] == 500

    @pytest.mark.asyncio
    async def test_check_resume_state_error(self, mock_session_factory: Any) -> None:
        """Test handling database error."""
        mock_cm = mock_session_factory(side_effect=Exception("DB error"))

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await check_resume_state_impl({"campaign_id": str(uuid4())})

        assert result["is_error"] is True
        content = json.loads(result["content"][0]["text"])
        assert "error" in content


class TestLoadLeadsImpl:
    """Tests for load_leads_impl."""

    @pytest.fixture
    def mock_session_factory(self) -> Any:
        """Create a factory for mock sessions."""

        def factory(
            mock_rows: list[Any] | None = None,
            side_effect: Exception | None = None,
        ) -> Any:
            mock_result = MagicMock()
            mock_result.fetchall.return_value = mock_rows or []

            mock_session = AsyncMock()
            if side_effect:
                mock_session.execute = AsyncMock(side_effect=side_effect)
            else:
                mock_session.execute = AsyncMock(return_value=mock_result)

            cm = AsyncMock()
            cm.__aenter__.return_value = mock_session
            cm.__aexit__.return_value = None
            return cm

        return factory

    @pytest.mark.asyncio
    async def test_load_leads_success(self, mock_session_factory: Any) -> None:
        """Test successful lead loading."""
        # Create mock rows
        mock_rows = []
        for i, tier in enumerate(["A", "B", "C"]):
            row = MagicMock()
            row.id = str(uuid4())
            row.email = f"test{i}@example.com"
            row.first_name = "John"
            row.last_name = "Doe"
            row.company_name = "Acme"
            row.lead_tier = tier
            row.generated_email_id = str(uuid4())
            row.lead_score = 80
            row.subject_line = "Subject"
            row.full_email = "Body"
            row.quality_score = 75
            mock_rows.append(row)

        mock_cm = mock_session_factory(mock_rows)

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await load_leads_impl(
                {
                    "campaign_id": str(uuid4()),
                    "batch_size": 100,
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["total_leads"] == 3
        assert content["by_tier"]["tier_a"] == 1
        assert content["by_tier"]["tier_b"] == 1
        assert content["by_tier"]["tier_c"] == 1

    @pytest.mark.asyncio
    async def test_load_leads_empty(self, mock_session_factory: Any) -> None:
        """Test loading with no leads."""
        mock_cm = mock_session_factory([])

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await load_leads_impl({"campaign_id": str(uuid4())})

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["total_leads"] == 0


class TestUploadToInstantlyImpl:
    """Tests for upload_to_instantly_impl."""

    @pytest.mark.asyncio
    async def test_upload_success(self) -> None:
        """Test successful batch upload."""
        from src.integrations.instantly import BulkAddResult

        mock_bulk_result = BulkAddResult(
            created_count=10,
            updated_count=0,
            failed_count=0,
            created_leads=["id1", "id2"],
            failed_leads=[],
        )

        mock_client = MagicMock()
        mock_client.bulk_add_leads = AsyncMock(return_value=mock_bulk_result)

        leads = [
            {
                "id": str(uuid4()),
                "email": "test@example.com",
                "first_name": "John",
                "email_data": {"subject_line": "Test", "full_email": "Body"},
            }
        ]

        with (
            patch(
                "src.agents.email_sending.tools._get_instantly_client",
                return_value=mock_client,
            ),
            patch(
                "src.agents.email_sending.tools._log_batch_to_database",
                new_callable=AsyncMock,
            ),
            patch(
                "src.agents.email_sending.tools._update_leads_status",
                new_callable=AsyncMock,
            ),
        ):
            result = await upload_to_instantly_impl(
                {
                    "instantly_campaign_id": str(uuid4()),
                    "campaign_id": str(uuid4()),
                    "batch_number": 1,
                    "leads": leads,
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["success"] is True
        assert content["leads_uploaded"] == 10

    @pytest.mark.asyncio
    async def test_upload_empty_leads(self) -> None:
        """Test upload with no leads."""
        result = await upload_to_instantly_impl(
            {
                "instantly_campaign_id": str(uuid4()),
                "campaign_id": str(uuid4()),
                "batch_number": 1,
                "leads": [],
            }
        )

        assert result["is_error"] is True
        content = json.loads(result["content"][0]["text"])
        assert "No leads provided" in content["error"]

    @pytest.mark.asyncio
    async def test_upload_circuit_breaker_open(self) -> None:
        """Test upload when circuit breaker is open."""
        from src.agents.email_sending.tools import _instantly_circuit_breaker

        # Simulate circuit breaker open
        original_state = _instantly_circuit_breaker.state
        _instantly_circuit_breaker.state = "open"
        _instantly_circuit_breaker.last_failure_time = None

        try:
            result = await upload_to_instantly_impl(
                {
                    "instantly_campaign_id": str(uuid4()),
                    "campaign_id": str(uuid4()),
                    "batch_number": 1,
                    "leads": [{"id": "1", "email": "test@example.com"}],
                }
            )

            assert result["is_error"] is True
            content = json.loads(result["content"][0]["text"])
            assert "Circuit breaker" in content["error"]
        finally:
            _instantly_circuit_breaker.state = original_state


class TestVerifyUploadImpl:
    """Tests for verify_upload_impl."""

    @pytest.mark.asyncio
    async def test_verify_upload_success(self) -> None:
        """Test successful verification."""
        from src.integrations.instantly import Campaign, CampaignAnalytics, CampaignStatus

        mock_analytics = CampaignAnalytics(
            campaign_id="test-id",
            total_leads=100,
            emails_sent=0,
        )
        mock_campaign = Campaign(
            id="test-id",
            name="Test Campaign",
            status=CampaignStatus.ACTIVE,
        )

        mock_client = MagicMock()
        mock_client.get_campaign_analytics = AsyncMock(return_value=mock_analytics)
        mock_client.get_campaign = AsyncMock(return_value=mock_campaign)

        with patch(
            "src.agents.email_sending.tools._get_instantly_client",
            return_value=mock_client,
        ):
            result = await verify_upload_impl(
                {
                    "instantly_campaign_id": "test-id",
                    "expected_count": 100,
                    "tolerance_percent": 5,
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["verification_passed"] is True
        assert content["discrepancy"] == 0

    @pytest.mark.asyncio
    async def test_verify_upload_discrepancy(self) -> None:
        """Test verification with discrepancy beyond tolerance."""
        from src.integrations.instantly import Campaign, CampaignAnalytics, CampaignStatus

        mock_analytics = CampaignAnalytics(
            campaign_id="test-id",
            total_leads=80,  # 20% less than expected
        )
        mock_campaign = Campaign(
            id="test-id",
            name="Test Campaign",
            status=CampaignStatus.ACTIVE,
        )

        mock_client = MagicMock()
        mock_client.get_campaign_analytics = AsyncMock(return_value=mock_analytics)
        mock_client.get_campaign = AsyncMock(return_value=mock_campaign)

        with patch(
            "src.agents.email_sending.tools._get_instantly_client",
            return_value=mock_client,
        ):
            result = await verify_upload_impl(
                {
                    "instantly_campaign_id": "test-id",
                    "expected_count": 100,
                    "tolerance_percent": 5,
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["verification_passed"] is False
        assert content["discrepancy"] == 20


class TestStartSendingImpl:
    """Tests for start_sending_impl."""

    @pytest.mark.asyncio
    async def test_start_sending_success(self) -> None:
        """Test successful campaign start."""
        from src.integrations.instantly import Campaign, CampaignStatus

        mock_campaign = Campaign(
            id="test-id",
            name="Test Campaign",
            status=CampaignStatus.ACTIVE,
        )

        mock_client = MagicMock()
        mock_client.activate_campaign = AsyncMock(return_value=mock_campaign)

        with (
            patch(
                "src.agents.email_sending.tools._get_instantly_client",
                return_value=mock_client,
            ),
            patch(
                "src.agents.email_sending.tools._update_campaign_status",
                new_callable=AsyncMock,
            ),
        ):
            result = await start_sending_impl(
                {
                    "instantly_campaign_id": "test-id",
                    "campaign_id": str(uuid4()),
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["sending_started"] is True
        assert content["campaign_status"] == "ACTIVE"


class TestUpdateSendingStatsImpl:
    """Tests for update_sending_stats_impl."""

    @pytest.fixture
    def mock_session_factory(self) -> Any:
        """Create a factory for mock sessions."""

        def factory(side_effect: Exception | None = None) -> Any:
            mock_session = AsyncMock()
            if side_effect:
                mock_session.execute = AsyncMock(side_effect=side_effect)
            else:
                mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()

            cm = AsyncMock()
            cm.__aenter__.return_value = mock_session
            cm.__aexit__.return_value = None
            return cm

        return factory

    @pytest.mark.asyncio
    async def test_update_stats_success(self, mock_session_factory: Any) -> None:
        """Test successful stats update."""
        mock_cm = mock_session_factory()

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await update_sending_stats_impl(
                {
                    "campaign_id": str(uuid4()),
                    "total_uploaded": 100,
                    "tier_a_uploaded": 30,
                    "tier_b_uploaded": 40,
                    "tier_c_uploaded": 30,
                    "cost_incurred": 0.1,
                }
            )

        assert result["is_error"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["success"] is True
        assert content["total_uploaded"] == 100

    @pytest.mark.asyncio
    async def test_update_stats_error(self, mock_session_factory: Any) -> None:
        """Test stats update with database error."""
        mock_cm = mock_session_factory(side_effect=Exception("DB error"))

        with patch(
            "src.database.connection.get_session",
            return_value=mock_cm,
        ):
            result = await update_sending_stats_impl(
                {
                    "campaign_id": str(uuid4()),
                    "total_uploaded": 100,
                }
            )

        assert result["is_error"] is True
