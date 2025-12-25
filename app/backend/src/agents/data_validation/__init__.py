"""
Data Validation Agent - Phase 2, Agent 2.2.

Validates and normalizes scraped lead data. Checks required fields,
normalizes company names and job titles, validates URLs and emails,
flags incomplete records, and prepares data for deduplication.

Usage:
    from src.agents.data_validation import DataValidationAgent, validate_leads

    # Using the agent class
    agent = DataValidationAgent(batch_size=1000)
    result = await agent.run(campaign_id, leads)

    # Using the convenience function
    result = await validate_leads(campaign_id, leads)

    # Get handoff data for next agent
    handoff = agent.get_handoff(result)
    if handoff.should_proceed:
        # Proceed to Duplicate Detection Agent (2.3)
        pass
"""

from src.agents.data_validation.agent import (
    DataValidationAgent,
    DataValidationAgentError,
    ValidationBatchError,
    log_tool_execution,
    validate_leads,
    validate_tool_inputs,
)
from src.agents.data_validation.normalizers import (
    derive_full_name,
    normalize_company_name,
    normalize_job_title,
    normalize_lead,
    normalize_name,
    parse_location,
)
from src.agents.data_validation.schemas import (
    BatchValidationResult,
    DataValidationResult,
    LeadValidationResult,
    ValidationHandoff,
)
from src.agents.data_validation.tools import (
    DATA_VALIDATION_TOOLS,
    aggregate_validation_results_tool,
    validate_lead_batch_tool,
    validate_single_lead_tool,
)
from src.agents.data_validation.validators import (
    ValidationResult,
    validate_company_name,
    validate_company_size,
    validate_email,
    validate_full_name_consistency,
    validate_job_title,
    validate_lead,
    validate_linkedin_url,
    validate_name,
)

__all__ = [
    # Agent
    "DataValidationAgent",
    "DataValidationAgentError",
    "ValidationBatchError",
    "validate_leads",
    # Security Hooks
    "validate_tool_inputs",
    "log_tool_execution",
    # Schemas
    "DataValidationResult",
    "BatchValidationResult",
    "LeadValidationResult",
    "ValidationHandoff",
    "ValidationResult",
    # Validators
    "validate_lead",
    "validate_linkedin_url",
    "validate_email",
    "validate_name",
    "validate_company_name",
    "validate_job_title",
    "validate_company_size",
    "validate_full_name_consistency",
    # Normalizers
    "normalize_lead",
    "normalize_name",
    "normalize_job_title",
    "normalize_company_name",
    "derive_full_name",
    "parse_location",
    # Tools
    "DATA_VALIDATION_TOOLS",
    "validate_lead_batch_tool",
    "aggregate_validation_results_tool",
    "validate_single_lead_tool",
]
