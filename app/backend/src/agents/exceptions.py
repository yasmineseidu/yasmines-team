"""
Agent Exceptions - Custom exception hierarchy for agent workflows.

Provides granular error handling for:
- Agent execution failures
- External service failures
- Rate limiting
- Circuit breaker states
- Validation errors

Usage:
    try:
        result = await agent.run(...)
    except AgentExecutionError as e:
        logger.error(f"Agent {e.agent_id} failed: {e}")
        # Handle agent-specific failure
    except ExternalServiceError as e:
        logger.error(f"Service {e.service_name} failed: {e}")
        # Handle service failure with retry/circuit breaker
"""

from datetime import datetime
from typing import Any


class AgentBaseError(Exception):
    """Base exception for all agent-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()


# =============================================================================
# Agent Execution Errors
# =============================================================================


class AgentExecutionError(AgentBaseError):
    """Error during agent execution."""

    def __init__(
        self,
        message: str,
        agent_id: str,
        step_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.agent_id = agent_id
        self.step_id = step_id

    def __str__(self) -> str:
        return f"[{self.agent_id}] {self.message}"


class AgentTimeoutError(AgentExecutionError):
    """Agent execution exceeded timeout."""

    def __init__(
        self,
        agent_id: str,
        timeout_seconds: float,
        step_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Execution timed out after {timeout_seconds}s",
            agent_id=agent_id,
            step_id=step_id,
            details={"timeout_seconds": timeout_seconds},
        )
        self.timeout_seconds = timeout_seconds


class AgentValidationError(AgentExecutionError):
    """Agent input or output validation failed."""

    def __init__(
        self,
        agent_id: str,
        validation_errors: list[str],
        step_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Validation failed: {', '.join(validation_errors)}",
            agent_id=agent_id,
            step_id=step_id,
            details={"validation_errors": validation_errors},
        )
        self.validation_errors = validation_errors


# =============================================================================
# External Service Errors
# =============================================================================


class ExternalServiceError(AgentBaseError):
    """Error from external service (API, database, etc.)."""

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: int | None = None,
        retryable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.service_name = service_name
        self.status_code = status_code
        self.retryable = retryable

    def __str__(self) -> str:
        status = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"[{self.service_name}]{status} {self.message}"


class RateLimitError(ExternalServiceError):
    """Rate limit exceeded for external service."""

    def __init__(
        self,
        service_name: str,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            "Rate limit exceeded"
            + (f", retry after {retry_after_seconds}s" if retry_after_seconds else ""),
            service_name=service_name,
            status_code=429,
            retryable=True,
            details=details,
        )
        self.retry_after_seconds = retry_after_seconds


class ServiceUnavailableError(ExternalServiceError):
    """External service is temporarily unavailable."""

    def __init__(
        self,
        service_name: str,
        status_code: int = 503,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            "Service temporarily unavailable",
            service_name=service_name,
            status_code=status_code,
            retryable=True,
            details=details,
        )


class ServiceAuthenticationError(ExternalServiceError):
    """Authentication failed for external service."""

    def __init__(
        self,
        service_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            "Authentication failed",
            service_name=service_name,
            status_code=401,
            retryable=False,  # Don't retry auth errors
            details=details,
        )


# =============================================================================
# Circuit Breaker Errors
# =============================================================================


class CircuitBreakerError(AgentBaseError):
    """Circuit breaker is open, service calls blocked."""

    def __init__(
        self,
        service_name: str,
        failure_count: int,
        recovery_time: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        recovery_msg = f", recovers at {recovery_time.isoformat()}" if recovery_time else ""
        super().__init__(
            f"Circuit breaker open for {service_name} ({failure_count} failures){recovery_msg}",
            details=details,
        )
        self.service_name = service_name
        self.failure_count = failure_count
        self.recovery_time = recovery_time


# =============================================================================
# Workflow Errors
# =============================================================================


class WorkflowError(AgentBaseError):
    """Error in workflow orchestration."""

    def __init__(
        self,
        message: str,
        workflow_id: str,
        phase: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.workflow_id = workflow_id
        self.phase = phase

    def __str__(self) -> str:
        phase_str = f" (Phase: {self.phase})" if self.phase else ""
        return f"[Workflow {self.workflow_id}]{phase_str} {self.message}"


class WorkflowThresholdError(WorkflowError):
    """Workflow stopped due to threshold not met."""

    def __init__(
        self,
        workflow_id: str,
        threshold_name: str,
        actual_value: int,
        required_value: int,
        phase: str | None = None,
    ) -> None:
        super().__init__(
            f"Threshold not met: {threshold_name} ({actual_value} < {required_value})",
            workflow_id=workflow_id,
            phase=phase,
            details={
                "threshold_name": threshold_name,
                "actual_value": actual_value,
                "required_value": required_value,
            },
        )
        self.threshold_name = threshold_name
        self.actual_value = actual_value
        self.required_value = required_value


class HumanGateTimeoutError(WorkflowError):
    """Human gate approval timed out."""

    def __init__(
        self,
        workflow_id: str,
        gate_id: str,
        timeout_hours: int,
        phase: str | None = None,
    ) -> None:
        super().__init__(
            f"Human gate {gate_id} timed out after {timeout_hours} hours",
            workflow_id=workflow_id,
            phase=phase,
            details={"gate_id": gate_id, "timeout_hours": timeout_hours},
        )
        self.gate_id = gate_id
        self.timeout_hours = timeout_hours


# =============================================================================
# Budget Errors
# =============================================================================


class BudgetExceededError(AgentBaseError):
    """Budget limit exceeded."""

    def __init__(
        self,
        budget_type: str,
        spent: float,
        limit: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"{budget_type} budget exceeded: ${spent:.2f} / ${limit:.2f}",
            details=details,
        )
        self.budget_type = budget_type
        self.spent = spent
        self.limit = limit


# =============================================================================
# Data Errors
# =============================================================================


class DataNotFoundError(AgentBaseError):
    """Required data not found."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"{entity_type} not found: {entity_id}",
            details=details,
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class DataIntegrityError(AgentBaseError):
    """Data integrity violation."""

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.entity_type = entity_type
