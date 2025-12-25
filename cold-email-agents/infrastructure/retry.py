# ==============================================================================
# RETRY MODULE - Production-Grade Retry Logic
# ==============================================================================
"""
Provides robust retry functionality with:
- Exponential backoff with decorrelated jitter
- Async-native implementation
- Conditional retry based on exception type
- Budget-aware retry limiting
- Observability hooks for monitoring

Usage:
    @async_retry(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2,
        jitter=True,
        retry_on=[ConnectionError, TimeoutError, RateLimitError],
        on_retry=log_retry_attempt
    )
    async def call_api():
        ...
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    Sequence,
    Type,
    TypeVar,
)
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self, message: str, last_exception: Exception, attempts: int, total_time: float
    ):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts
        self.total_time = total_time


class RetryStrategy(Enum):
    """Available retry backoff strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    DECORRELATED_JITTER = "decorrelated_jitter"  # AWS recommended
    LINEAR = "linear"


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (including first try)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff (typically 2)
        jitter: Whether to add randomness to delays
        jitter_range: Range for jitter as fraction of delay (0.0 to 1.0)
        strategy: Backoff strategy to use
        retry_on: Exception types to retry on
        dont_retry_on: Exception types to never retry on (overrides retry_on)
        timeout_total: Total timeout for all attempts combined
        on_retry: Callback function called before each retry
        on_success: Callback function called on successful completion
        on_failure: Callback function called when retries exhausted
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.5
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    retry_on: Sequence[Type[Exception]] = field(default_factory=lambda: [Exception])
    dont_retry_on: Sequence[Type[Exception]] = field(
        default_factory=lambda: [KeyboardInterrupt, SystemExit]
    )
    timeout_total: Optional[float] = None
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    on_success: Optional[Callable[[int, float], None]] = None
    on_failure: Optional[Callable[[int, Exception, float], None]] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= self.jitter_range <= 1:
            raise ValueError("jitter_range must be between 0 and 1")


class RetryState:
    """Tracks state across retry attempts."""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.start_time = time.monotonic()
        self.last_delay = config.base_delay
        self.exceptions: list[Exception] = []

    @property
    def elapsed_time(self) -> float:
        """Total elapsed time since first attempt."""
        return time.monotonic() - self.start_time

    @property
    def attempts_remaining(self) -> int:
        """Number of retry attempts remaining."""
        return max(0, self.config.max_attempts - self.attempt)

    @property
    def should_continue(self) -> bool:
        """Whether more retries should be attempted."""
        if self.attempt >= self.config.max_attempts:
            return False
        if self.config.timeout_total and self.elapsed_time >= self.config.timeout_total:
            return False
        return True

    def calculate_delay(self) -> float:
        """Calculate delay before next retry based on strategy."""
        config = self.config
        attempt = self.attempt

        if config.strategy == RetryStrategy.FIXED:
            delay = config.base_delay

        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * attempt

        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.exponential_base ** (attempt - 1))

        elif config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # Standard exponential with uniform jitter
            base_delay = config.base_delay * (config.exponential_base ** (attempt - 1))
            if config.jitter:
                jitter = random.uniform(0, config.jitter_range * base_delay)
                delay = base_delay + jitter
            else:
                delay = base_delay

        elif config.strategy == RetryStrategy.DECORRELATED_JITTER:
            # AWS recommended: sleep = min(cap, random_between(base, sleep * 3))
            delay = min(
                config.max_delay, random.uniform(config.base_delay, self.last_delay * 3)
            )
            self.last_delay = delay

        else:
            delay = config.base_delay

        # Apply max delay cap
        delay = min(delay, config.max_delay)

        # Ensure we don't exceed total timeout
        if config.timeout_total:
            remaining = config.timeout_total - self.elapsed_time
            delay = min(delay, max(0, remaining - 0.1))  # Leave 100ms buffer

        return delay

    def should_retry_exception(self, exc: Exception) -> bool:
        """Check if exception type should be retried."""
        # Never retry these
        for exc_type in self.config.dont_retry_on:
            if isinstance(exc, exc_type):
                return False

        # Check if in retry list
        for exc_type in self.config.retry_on:
            if isinstance(exc, exc_type):
                return True

        return False


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
    retry_on: Optional[Sequence[Type[Exception]]] = None,
    dont_retry_on: Optional[Sequence[Type[Exception]]] = None,
    timeout_total: Optional[float] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for async functions with retry logic.

    Example:
        @async_retry(
            max_attempts=5,
            base_delay=2.0,
            retry_on=[ConnectionError, TimeoutError],
            on_retry=lambda attempt, exc, delay: logger.warning(
                f"Retry {attempt}: {exc}, waiting {delay}s"
            )
        )
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                return await session.get(url)
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        strategy=strategy,
        retry_on=retry_on or [Exception],
        dont_retry_on=dont_retry_on or [KeyboardInterrupt, SystemExit],
        timeout_total=timeout_total,
        on_retry=on_retry,
    )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            state = RetryState(config)

            while True:
                state.attempt += 1

                try:
                    result = await func(*args, **kwargs)

                    # Success callback
                    if config.on_success:
                        config.on_success(state.attempt, state.elapsed_time)

                    return result

                except Exception as exc:
                    state.exceptions.append(exc)

                    # Check if we should retry this exception
                    if not state.should_retry_exception(exc):
                        logger.debug(
                            f"Not retrying {func.__name__}: {type(exc).__name__} "
                            f"not in retry list"
                        )
                        raise

                    # Check if we have attempts remaining
                    if not state.should_continue:
                        if config.on_failure:
                            config.on_failure(state.attempt, exc, state.elapsed_time)

                        raise RetryExhaustedError(
                            f"Failed after {state.attempt} attempts: {exc}",
                            last_exception=exc,
                            attempts=state.attempt,
                            total_time=state.elapsed_time,
                        ) from exc

                    # Calculate delay
                    delay = state.calculate_delay()

                    # Retry callback
                    if config.on_retry:
                        config.on_retry(state.attempt, exc, delay)

                    logger.info(
                        f"Retry {state.attempt}/{config.max_attempts} for "
                        f"{func.__name__}: {type(exc).__name__}: {exc}. "
                        f"Waiting {delay:.2f}s"
                    )

                    # Wait before retry
                    await asyncio.sleep(delay)

        # Attach config for introspection
        wrapper.retry_config = config  # type: ignore
        return wrapper

    return decorator


def retry_with_backoff(config: RetryConfig):
    """
    Decorator factory using RetryConfig object.

    Example:
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.DECORRELATED_JITTER,
            retry_on=[APIError, TimeoutError]
        )

        @retry_with_backoff(config)
        async def call_service():
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        return async_retry(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=config.jitter,
            strategy=config.strategy,
            retry_on=list(config.retry_on),
            dont_retry_on=list(config.dont_retry_on),
            timeout_total=config.timeout_total,
            on_retry=config.on_retry,
        )(func)

    return decorator


def create_retry_decorator(
    name: str, **default_kwargs: Any
) -> Callable[
    ..., Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]
]:
    """
    Create a named retry decorator with custom defaults.

    Example:
        # Create service-specific retry decorators
        api_retry = create_retry_decorator(
            "api",
            max_attempts=5,
            base_delay=2.0,
            retry_on=[APIError, RateLimitError]
        )

        db_retry = create_retry_decorator(
            "database",
            max_attempts=3,
            base_delay=0.5,
            retry_on=[ConnectionError]
        )

        @api_retry(timeout_total=30)
        async def call_api():
            ...
    """

    def factory(**override_kwargs: Any):
        merged_kwargs = {**default_kwargs, **override_kwargs}

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            # Add logging with decorator name
            original_on_retry = merged_kwargs.get("on_retry")

            def on_retry_with_name(attempt: int, exc: Exception, delay: float):
                logger.warning(
                    f"[{name}] Retry {attempt}: {type(exc).__name__}: {exc}. "
                    f"Waiting {delay:.2f}s"
                )
                if original_on_retry:
                    original_on_retry(attempt, exc, delay)

            merged_kwargs["on_retry"] = on_retry_with_name
            return async_retry(**merged_kwargs)(func)

        return decorator

    return factory


# Pre-configured retry decorators for common scenarios
# ==============================================================================

# For external API calls (moderate retries, longer delays)
api_retry = create_retry_decorator(
    "api",
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL_JITTER,
)

# For database operations (quick retries, short delays)
db_retry = create_retry_decorator(
    "database",
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    strategy=RetryStrategy.EXPONENTIAL_JITTER,
)

# For critical operations (aggressive retries)
critical_retry = create_retry_decorator(
    "critical",
    max_attempts=10,
    base_delay=5.0,
    max_delay=300.0,
    strategy=RetryStrategy.DECORRELATED_JITTER,
)

# For rate-limited services
rate_limit_retry = create_retry_decorator(
    "rate_limit",
    max_attempts=5,
    base_delay=60.0,  # Start with 1 minute
    max_delay=300.0,
    strategy=RetryStrategy.EXPONENTIAL,
)
