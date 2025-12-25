"""
Circuit Breaker - Resilience pattern for external service calls.

Prevents cascading failures by temporarily blocking calls to failing services.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failing, requests blocked immediately
- HALF_OPEN: Testing if service recovered

Usage:
    breaker = CircuitBreaker(
        name="tomba",
        failure_threshold=5,
        recovery_timeout_seconds=300,
    )

    async def call_with_breaker():
        if not breaker.can_execute():
            raise CircuitBreakerError(...)

        try:
            result = await call_external_service()
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            raise
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for external service resilience.

    Tracks failures and temporarily blocks requests to prevent
    cascading failures when a service is down.
    """

    name: str
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout_seconds: int = 300  # Time before testing recovery
    success_threshold: int = 2  # Successes in half-open before closing

    # Internal state
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: datetime | None = field(default=None)
    last_state_change: datetime = field(default_factory=lambda: datetime.now(UTC))

    def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Returns:
            True if request should proceed, False if blocked
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_recovery():
                self._transition_to_half_open()
                return True
            return False

        # Allow limited requests in half-open state
        return self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(
                f"CircuitBreaker[{self.name}]: Success in half-open "
                f"({self.success_count}/{self.success_threshold})"
            )

            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
                logger.debug(f"CircuitBreaker[{self.name}]: Failure count reset")

    def record_failure(self, error: Exception | None = None) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        error_msg = str(error) if error else "Unknown error"
        logger.warning(
            f"CircuitBreaker[{self.name}]: Failure recorded "
            f"({self.failure_count}/{self.failure_threshold}) - {error_msg}"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open reopens the circuit
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self._transition_to_open()

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "last_state_change": self.last_state_change.isoformat(),
            "recovery_time": self._get_recovery_time().isoformat()
            if self.state == CircuitState.OPEN
            else None,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now(UTC)
        logger.info(f"CircuitBreaker[{self.name}]: Reset to closed state")

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True

        recovery_time = self._get_recovery_time()
        return datetime.now(UTC) >= recovery_time

    def _get_recovery_time(self) -> datetime:
        """Get the time when recovery can be attempted."""
        if not self.last_failure_time:
            return datetime.now(UTC)
        return self.last_failure_time + timedelta(seconds=self.recovery_timeout_seconds)

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.last_state_change = datetime.now(UTC)
        logger.warning(
            f"CircuitBreaker[{self.name}]: OPENED - "
            f"Service blocked for {self.recovery_timeout_seconds}s"
        )

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now(UTC)
        logger.info(f"CircuitBreaker[{self.name}]: Testing recovery (half-open)")

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now(UTC)
        logger.info(f"CircuitBreaker[{self.name}]: CLOSED - Service recovered")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        registry.register("tomba", failure_threshold=5)
        registry.register("hunter", failure_threshold=3)

        breaker = registry.get("tomba")
        if breaker.can_execute():
            ...
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 300,
        success_threshold: int = 2,
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        if name in self._breakers:
            return self._breakers[name]

        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            success_threshold=success_threshold,
        )
        self._breakers[name] = breaker
        logger.debug(f"CircuitBreakerRegistry: Registered breaker '{name}'")
        return breaker

    def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 300,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            return self.register(name, failure_threshold, recovery_timeout_seconds)
        return self._breakers[name]

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get state of all circuit breakers."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def get_open_circuits(self) -> list[str]:
        """Get names of all open circuit breakers."""
        return [
            name for name, breaker in self._breakers.items() if breaker.state == CircuitState.OPEN
        ]
