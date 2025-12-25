"""
Retry Utilities - Resilient retry patterns for agent workflows.

Provides configurable retry decorators with:
- Exponential backoff with jitter
- Specific exception handling
- Logging and metrics
- Circuit breaker integration

Usage:
    @with_agent_retry(agent_id="data_validation", max_attempts=3)
    async def run_validation():
        ...

    @with_service_retry(service_name="tomba", max_attempts=5)
    async def call_tomba():
        ...
"""

import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.agents.circuit_breaker import CircuitBreaker
from src.agents.exceptions import (
    AgentExecutionError,
    AgentTimeoutError,
    CircuitBreakerError,
    ExternalServiceError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Retry Configuration
# =============================================================================


class RetryConfig:
    """Configuration for retry behavior."""

    # Agent retry defaults
    AGENT_MAX_ATTEMPTS = 3
    AGENT_INITIAL_WAIT = 1.0  # seconds
    AGENT_MAX_WAIT = 30.0  # seconds
    AGENT_JITTER = 2.0  # seconds

    # Service retry defaults
    SERVICE_MAX_ATTEMPTS = 5
    SERVICE_INITIAL_WAIT = 2.0  # seconds
    SERVICE_MAX_WAIT = 60.0  # seconds
    SERVICE_JITTER = 5.0  # seconds

    # Rate limit specific
    RATE_LIMIT_WAIT = 60.0  # Wait time when rate limited


# =============================================================================
# Retry Decorators
# =============================================================================


def with_agent_retry(
    agent_id: str,
    max_attempts: int = RetryConfig.AGENT_MAX_ATTEMPTS,
    initial_wait: float = RetryConfig.AGENT_INITIAL_WAIT,
    max_wait: float = RetryConfig.AGENT_MAX_WAIT,
    jitter: float = RetryConfig.AGENT_JITTER,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying agent execution with exponential backoff.

    Args:
        agent_id: Agent identifier for logging
        max_attempts: Maximum retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        jitter: Random jitter to add
        retryable_exceptions: Tuple of exceptions to retry on

    Usage:
        @with_agent_retry(agent_id="data_validation")
        async def _run_data_validation(self, campaign_id: str):
            ...
    """
    if retryable_exceptions is None:
        retryable_exceptions = (
            AgentExecutionError,
            ExternalServiceError,
            ServiceUnavailableError,
            asyncio.TimeoutError,
            ConnectionError,
            OSError,
        )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0

            async for attempt_state in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(
                    initial=initial_wait,
                    max=max_wait,
                    jitter=jitter,
                ),
                retry=retry_if_exception_type(retryable_exceptions),
                reraise=True,
            ):
                with attempt_state:
                    attempt += 1
                    if attempt > 1:
                        logger.info(f"Agent[{agent_id}]: Retry attempt {attempt}/{max_attempts}")

                    try:
                        return await func(*args, **kwargs)
                    except retryable_exceptions as e:
                        logger.warning(f"Agent[{agent_id}]: Attempt {attempt} failed: {e}")
                        raise

        return wrapper  # type: ignore[return-value]

    return decorator


def with_service_retry(
    service_name: str,
    max_attempts: int = RetryConfig.SERVICE_MAX_ATTEMPTS,
    initial_wait: float = RetryConfig.SERVICE_INITIAL_WAIT,
    max_wait: float = RetryConfig.SERVICE_MAX_WAIT,
    jitter: float = RetryConfig.SERVICE_JITTER,
    circuit_breaker: CircuitBreaker | None = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying external service calls with circuit breaker support.

    Args:
        service_name: Service identifier for logging
        max_attempts: Maximum retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        jitter: Random jitter to add
        circuit_breaker: Optional circuit breaker instance

    Usage:
        @with_service_retry(service_name="tomba", circuit_breaker=breaker)
        async def call_tomba_api():
            ...
    """
    retryable_exceptions = (
        ExternalServiceError,
        ServiceUnavailableError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check circuit breaker first
            if circuit_breaker and not circuit_breaker.can_execute():
                raise CircuitBreakerError(
                    service_name=service_name,
                    failure_count=circuit_breaker.failure_count,
                    recovery_time=circuit_breaker._get_recovery_time(),
                )

            attempt = 0

            try:
                async for attempt_state in AsyncRetrying(
                    stop=stop_after_attempt(max_attempts),
                    wait=wait_exponential_jitter(
                        initial=initial_wait,
                        max=max_wait,
                        jitter=jitter,
                    ),
                    retry=retry_if_exception_type(retryable_exceptions),
                    reraise=True,
                ):
                    with attempt_state:
                        attempt += 1
                        if attempt > 1:
                            logger.info(
                                f"Service[{service_name}]: Retry attempt {attempt}/{max_attempts}"
                            )

                        try:
                            result = await func(*args, **kwargs)
                            # Record success
                            if circuit_breaker:
                                circuit_breaker.record_success()
                            return result
                        except RateLimitError as e:
                            # Special handling for rate limits
                            wait_time = e.retry_after_seconds or RetryConfig.RATE_LIMIT_WAIT
                            logger.warning(
                                f"Service[{service_name}]: Rate limited, waiting {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            raise
                        except retryable_exceptions as e:
                            logger.warning(
                                f"Service[{service_name}]: Attempt {attempt} failed: {e}"
                            )
                            raise

            except RetryError as e:
                # All retries exhausted
                if circuit_breaker:
                    exc = e.last_attempt.exception()
                    circuit_breaker.record_failure(exc if isinstance(exc, Exception) else None)
                raise

            except Exception as e:
                # Non-retryable exception
                if circuit_breaker:
                    circuit_breaker.record_failure(e)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


# =============================================================================
# Async Retry Helpers
# =============================================================================


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 30.0,
    jitter: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_attempts: Maximum retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        jitter: Random jitter to add
        retryable_exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback on retry (attempt, exception)
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        Last exception if all retries exhausted
    """
    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_attempts:
                logger.error(f"All {max_attempts} attempts exhausted: {e}")
                raise

            # Calculate wait time with exponential backoff and jitter
            wait_time = min(initial_wait * (2 ** (attempt - 1)), max_wait)
            wait_time += random.uniform(0, jitter)

            if on_retry:
                on_retry(attempt, e)

            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. " f"Retrying in {wait_time:.1f}s"
            )
            await asyncio.sleep(wait_time)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly")


async def execute_with_timeout(
    func: Callable[..., Any],
    *args: Any,
    timeout_seconds: float,
    agent_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute async function with timeout.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        timeout_seconds: Timeout in seconds
        agent_id: Optional agent ID for error context
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        AgentTimeoutError: If execution times out
    """
    try:
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=timeout_seconds,
        )
    except TimeoutError as e:
        if agent_id:
            raise AgentTimeoutError(
                agent_id=agent_id,
                timeout_seconds=timeout_seconds,
            ) from e
        raise
