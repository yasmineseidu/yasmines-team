"""
Unit tests for Data Validation Agent.

Tests the main agent class including:
- Batch processing
- Result aggregation
- Handoff generation
"""

import pytest

from src.agents.data_validation.agent import DataValidationAgent, validate_leads
from src.agents.data_validation.schemas import (
    BatchValidationResult,
    DataValidationResult,
    LeadValidationResult,
    ValidationHandoff,
)


class TestDataValidationAgent:
    """Tests for DataValidationAgent class."""

    def test_agent_initialization(self) -> None:
        """Test agent initialization with defaults."""
        agent = DataValidationAgent()

        assert agent.name == "data_validation"
        assert agent.batch_size == 1000
        assert agent.max_parallel_batches == 10
        assert agent.use_claude is False

    def test_agent_custom_config(self) -> None:
        """Test agent initialization with custom config."""
        agent = DataValidationAgent(
            batch_size=500,
            max_parallel_batches=5,
            use_claude=True,
        )

        assert agent.batch_size == 500
        assert agent.max_parallel_batches == 5
        assert agent.use_claude is True

    def test_batch_validation_sync(self) -> None:
        """Test synchronous batch validation."""
        agent = DataValidationAgent()

        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
            },
            {
                "id": "lead-2",
                "linkedin_url": None,  # Invalid - missing required field
                "first_name": "Jane",
                "last_name": "Smith",
                "company_name": "Tech Inc",
                "job_title": "Manager",
            },
        ]

        result = agent._validate_batch_sync(leads, batch_number=1)

        assert isinstance(result, BatchValidationResult)
        assert result.batch_number == 1
        assert result.batch_size == 2
        assert result.valid_count == 1
        assert result.invalid_count == 1
        assert len(result.results) == 2

    def test_batch_validation_all_valid(self) -> None:
        """Test batch where all leads are valid."""
        agent = DataValidationAgent()

        leads = [
            {
                "id": f"lead-{i}",
                "linkedin_url": f"https://linkedin.com/in/user{i}",
                "first_name": f"User{i}",
                "last_name": "Test",
                "company_name": "Test Company",
                "job_title": "Test Engineer",
                "email": f"user{i}@test.com",
            }
            for i in range(5)
        ]

        result = agent._validate_batch_sync(leads, batch_number=1)

        assert result.valid_count == 5
        assert result.invalid_count == 0

    def test_batch_validation_all_invalid(self) -> None:
        """Test batch where all leads are invalid."""
        agent = DataValidationAgent()

        leads = [
            {
                "id": f"lead-{i}",
                "linkedin_url": None,  # Missing required
                "first_name": None,  # Missing required
                "last_name": None,  # Missing required
                "company_name": None,  # Missing required
                "job_title": None,  # Missing required
            }
            for i in range(3)
        ]

        result = agent._validate_batch_sync(leads, batch_number=1)

        assert result.valid_count == 0
        assert result.invalid_count == 3

    def test_error_categorization(self) -> None:
        """Test error message categorization."""
        agent = DataValidationAgent()

        assert agent._categorize_error("linkedin_url is required") == "missing_linkedin"
        assert agent._categorize_error("first_name is required") == "missing_first_name"
        assert agent._categorize_error("last_name is required") == "missing_last_name"
        assert agent._categorize_error("company_name is required") == "missing_company"
        assert agent._categorize_error("job_title is required") == "missing_job_title"
        assert agent._categorize_error("email format is invalid") == "invalid_email"
        assert agent._categorize_error("unknown error") == "other"


class TestDataValidationAgentAsync:
    """Async tests for DataValidationAgent."""

    @pytest.mark.asyncio
    async def test_run_empty_leads(self) -> None:
        """Test running with empty leads list."""
        agent = DataValidationAgent()
        result = await agent.run("campaign-123", [])

        assert result.success
        assert result.status == "completed"
        assert result.total_processed == 0

    @pytest.mark.asyncio
    async def test_run_with_leads(self) -> None:
        """Test running with valid leads."""
        agent = DataValidationAgent(batch_size=2)

        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
            },
            {
                "id": "lead-2",
                "linkedin_url": "https://linkedin.com/in/janesmith",
                "first_name": "Jane",
                "last_name": "Smith",
                "company_name": "Tech Inc",
                "job_title": "Manager",
            },
        ]

        result = await agent.run("campaign-123", leads)

        assert result.success
        assert result.status == "completed"
        assert result.total_processed == 2
        assert result.total_valid == 2
        assert result.campaign_id == "campaign-123"

    @pytest.mark.asyncio
    async def test_run_with_mixed_validity(self) -> None:
        """Test running with mix of valid and invalid leads."""
        agent = DataValidationAgent(batch_size=5)

        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
            },
            {
                "id": "lead-2",
                "linkedin_url": None,  # Invalid
                "first_name": "Jane",
                "last_name": "Smith",
                "company_name": "Tech Inc",
                "job_title": "Manager",
            },
            {
                "id": "lead-3",
                "linkedin_url": "https://linkedin.com/in/bob",
                "first_name": "Bob",
                "last_name": None,  # Invalid
                "company_name": "Corp Inc",
                "job_title": "Designer",
            },
        ]

        result = await agent.run("campaign-123", leads)

        assert result.success
        assert result.status == "completed"
        assert result.total_processed == 3
        assert result.total_valid == 1
        assert result.total_invalid == 2
        assert 0 < result.validation_rate < 1

    @pytest.mark.asyncio
    async def test_handoff_generation(self) -> None:
        """Test generating handoff data."""
        agent = DataValidationAgent()

        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
            },
        ]

        result = await agent.run("campaign-123", leads)
        handoff = agent.get_handoff(result)

        assert isinstance(handoff, ValidationHandoff)
        assert handoff.campaign_id == "campaign-123"
        assert handoff.total_valid_leads == 1
        assert handoff.should_proceed is True

    @pytest.mark.asyncio
    async def test_needs_enrichment_tracking(self) -> None:
        """Test tracking leads that need email enrichment."""
        agent = DataValidationAgent()

        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
                # No email - needs enrichment
            },
            {
                "id": "lead-2",
                "linkedin_url": "https://linkedin.com/in/janesmith",
                "first_name": "Jane",
                "last_name": "Smith",
                "company_name": "Tech Inc",
                "job_title": "Manager",
                "email": "jane@tech.com",  # Has email
            },
        ]

        result = await agent.run("campaign-123", leads)

        assert result.needs_enrichment == 1  # Only lead-1


class TestConvenienceFunction:
    """Tests for validate_leads() convenience function."""

    @pytest.mark.asyncio
    async def test_validate_leads_function(self) -> None:
        """Test the convenience function."""
        leads = [
            {
                "id": "lead-1",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "job_title": "Engineer",
            },
        ]

        result = await validate_leads("campaign-123", leads)

        assert isinstance(result, DataValidationResult)
        assert result.success
        assert result.total_valid == 1


class TestSchemas:
    """Tests for schema classes."""

    def test_lead_validation_result(self) -> None:
        """Test LeadValidationResult."""
        result = LeadValidationResult(
            lead_id="lead-123",
            is_valid=True,
            status="valid",
            errors=[],
            warnings=["email missing"],
            needs_email_enrichment=True,
        )

        d = result.to_dict()
        assert d["lead_id"] == "lead-123"
        assert d["is_valid"] is True
        assert d["needs_email_enrichment"] is True

    def test_batch_validation_result(self) -> None:
        """Test BatchValidationResult."""
        result = BatchValidationResult(
            batch_number=1,
            batch_size=100,
            valid_count=95,
            invalid_count=5,
        )

        d = result.to_dict()
        assert d["batch_number"] == 1
        assert d["valid_count"] == 95

    def test_data_validation_result(self) -> None:
        """Test DataValidationResult."""
        result = DataValidationResult(
            success=True,
            campaign_id="campaign-123",
            total_processed=1000,
            total_valid=950,
            total_invalid=50,
            validation_rate=0.95,
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["total_processed"] == 1000
        assert d["validation_rate"] == 0.95

    def test_validation_handoff(self) -> None:
        """Test ValidationHandoff."""
        handoff = ValidationHandoff(
            campaign_id="campaign-123",
            total_valid_leads=950,
            validation_rate=0.95,
            needs_enrichment_count=100,
        )

        assert handoff.should_proceed is True

        d = handoff.to_dict()
        assert d["campaign_id"] == "campaign-123"
        assert d["should_proceed"] is True

    def test_handoff_should_not_proceed(self) -> None:
        """Test handoff when no valid leads."""
        handoff = ValidationHandoff(
            campaign_id="campaign-123",
            total_valid_leads=0,
            validation_rate=0.0,
            needs_enrichment_count=0,
        )

        assert handoff.should_proceed is False
