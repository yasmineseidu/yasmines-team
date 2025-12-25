"""
Rate limiting utilities for API calls.

Provides token bucket rate limiter and circuit breaker pattern implementations
for resilient API integration.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API calls.

    Implements the token bucket algorithm where:
    - Bucket has a maximum capacity of tokens
    - Tokens refill at a constant rate
    - Each request consumes one or more tokens
    - Requests wait if insufficient tokens available

    Supports two initialization styles:
    1. Rate-based: TokenBucketRateLimiter(rate_limit=60, rate_window=60)
    2. Capacity-based: TokenBucketRateLimiter(capacity=10, refill_rate=1.0)
    """

    def __init__(
        self,
        rate_limit: int | None = None,
        rate_window: int | None = None,
        service_name: str = "API",
        *,
        capacity: int | None = None,
        refill_rate: float | None = None,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            rate_limit: Maximum requests per rate window (use with rate_window)
            rate_window: Window size in seconds (use with rate_limit)
            service_name: Name of the service for logging
            capacity: Maximum tokens / burst capacity (alternative to rate_limit)
            refill_rate: Tokens per second (alternative to rate_window calculation)

        Either use (rate_limit, rate_window) OR (capacity, refill_rate).
        Defaults to 60 requests per 60 seconds if no parameters provided.
        """
        # Support both initialization styles
        if capacity is not None and refill_rate is not None:
            # Capacity-based initialization
            self.capacity = capacity
            self.refill_rate = refill_rate
            self.rate_window = int(capacity / refill_rate) if refill_rate > 0 else 60
        else:
            # Rate-based initialization (original style)
            effective_rate_limit = rate_limit if rate_limit is not None else 60
            effective_rate_window = rate_window if rate_window is not None else 60
            self.capacity = effective_rate_limit
            self.rate_window = effective_rate_window
            self.refill_rate = effective_rate_limit / effective_rate_window

        self.service_name = service_name
        self.tokens = float(self.capacity)
        self.last_update = time.time()
        self._lock: asyncio.Lock | None = None

    async def _get_lock(self) -> asyncio.Lock:
        """Get or create the asyncio lock."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        lock = await self._get_lock()
        async with lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Calculate wait time for token refill
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            logger.debug(f"{self.service_name} rate limit: waiting {wait_time:.2f}s for tokens")
            await asyncio.sleep(wait_time)

            # After waiting, refill based on elapsed time (not full capacity!)
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_update = now
            self.tokens -= tokens


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascade failures by opening the circuit after
    a threshold of failures, allowing the system to recover.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        service_name: str = "API",
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before allowing retry
            service_name: Name of the service for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.service_name = service_name
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"{self.service_name} circuit breaker opened after {self.failures} failures"
            )

    def record_success(self) -> None:
        """Record a success and reset the failure count."""
        self.failures = 0
        self.state = "closed"
        logger.debug(f"{self.service_name} circuit breaker reset")

    def can_proceed(self) -> bool:
        """
        Check if a request can proceed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        if self.state == "closed":
            return True

        if self.state == "open" and self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"{self.service_name} circuit breaker entering half-open state")
                return True

        return False
