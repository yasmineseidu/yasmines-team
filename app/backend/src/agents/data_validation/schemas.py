"""
Schemas for Data Validation Agent.

Defines input/output data structures using dataclasses for type safety
and clear API contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# =============================================================================
# Lead Validation Schemas
# =============================================================================


@dataclass
class LeadValidationResult:
    """
    Result of validating a single lead.

    Attributes:
        lead_id: UUID of the lead.
        is_valid: Whether the lead passed validation.
        status: 'valid' or 'invalid'.
        errors: List of validation errors.
        warnings: List of warnings (non-blocking).
        normalized_data: Dictionary of normalized field values.
    """

    lead_id: str
    is_valid: bool
    status: str  # 'valid' or 'invalid'
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_data: dict[str, Any] = field(default_factory=dict)
    needs_email_enrichment: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database update."""
        return {
            "lead_id": self.lead_id,
            "is_valid": self.is_valid,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "normalized_data": self.normalized_data,
            "needs_email_enrichment": self.needs_email_enrichment,
        }


@dataclass
class BatchValidationResult:
    """
    Result of validating a batch of leads.

    Attributes:
        batch_number: Batch number (1-indexed).
        batch_size: Number of leads in this batch.
        valid_count: Number of valid leads.
        invalid_count: Number of invalid leads.
        results: List of individual lead validation results.
        processing_time_ms: Time to process this batch.
    """

    batch_number: int
    batch_size: int
    valid_count: int = 0
    invalid_count: int = 0
    results: list[LeadValidationResult] = field(default_factory=list)
    processing_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_number": self.batch_number,
            "batch_size": self.batch_size,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "processing_time_ms": self.processing_time_ms,
        }


# =============================================================================
# Agent Result Schemas
# =============================================================================


@dataclass
class DataValidationResult:
    """
    Result of Data Validation Agent execution.

    This is the main output returned to the orchestrator.

    Attributes:
        success: Whether the agent completed successfully.
        campaign_id: Campaign UUID.
        total_processed: Total leads processed.
        total_valid: Total valid leads.
        total_invalid: Total invalid leads.
        validation_rate: Ratio of valid to total (0-1).
        needs_enrichment: Count of leads flagged for email enrichment.
        error_breakdown: Count of each error type.
        execution_time_ms: Total execution time.
        batch_results: List of batch results.
        errors: List of agent-level errors.
    """

    # Status
    success: bool = True
    campaign_id: str = ""
    status: str = "completed"  # 'completed', 'partial', 'failed'

    # Counts
    total_processed: int = 0
    total_valid: int = 0
    total_invalid: int = 0
    validation_rate: float = 0.0
    needs_enrichment: int = 0

    # Error breakdown
    error_breakdown: dict[str, int] = field(default_factory=dict)

    # Timing
    execution_time_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Batch details
    total_batches: int = 0
    batch_results: list[BatchValidationResult] = field(default_factory=list)

    # Errors
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for orchestrator consumption."""
        return {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "status": self.status,
            "total_processed": self.total_processed,
            "total_valid": self.total_valid,
            "total_invalid": self.total_invalid,
            "validation_rate": self.validation_rate,
            "needs_enrichment": self.needs_enrichment,
            "error_breakdown": self.error_breakdown,
            "execution_time_ms": self.execution_time_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_batches": self.total_batches,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Handoff Schema
# =============================================================================


@dataclass
class ValidationHandoff:
    """
    Data passed to Duplicate Detection Agent (2.3).

    Per YAML spec, handoff requires:
    - campaign_id: Campaign UUID
    - total_valid_leads: Count of valid leads

    Conditions:
    - Proceed with whatever valid leads we have (total_valid >= 1)
    """

    campaign_id: str
    total_valid_leads: int
    validation_rate: float
    needs_enrichment_count: int

    @property
    def should_proceed(self) -> bool:
        """Check if handoff conditions are met."""
        return self.total_valid_leads >= 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for handoff."""
        return {
            "campaign_id": self.campaign_id,
            "total_valid_leads": self.total_valid_leads,
            "validation_rate": self.validation_rate,
            "needs_enrichment_count": self.needs_enrichment_count,
            "should_proceed": self.should_proceed,
        }


# =============================================================================
# Tool Input/Output Schemas (for SDK MCP tools)
# =============================================================================


@dataclass
class LoadLeadsInput:
    """Input for load_leads tool."""

    campaign_id: str
    batch_size: int = 1000
    status_filter: str = "new"


@dataclass
class LoadLeadsOutput:
    """Output from load_leads tool."""

    total_leads: int
    total_batches: int
    batch_size: int
    campaign_id: str


@dataclass
class ValidateBatchInput:
    """Input for validate_batch tool."""

    leads: list[dict[str, Any]]
    batch_number: int


@dataclass
class ValidateBatchOutput:
    """Output from validate_batch tool."""

    batch_number: int
    valid_count: int
    invalid_count: int
    results: list[dict[str, Any]]
    processing_time_ms: int


@dataclass
class AggregateResultsInput:
    """Input for aggregate_results tool."""

    batch_results: list[dict[str, Any]]


@dataclass
class AggregateResultsOutput:
    """Output from aggregate_results tool."""

    total_processed: int
    total_valid: int
    total_invalid: int
    validation_rate: float
    error_breakdown: dict[str, int]
