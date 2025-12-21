"""
Base integration client for third-party API integrations.

Provides common functionality for all API clients:
- Lazy HTTP client creation with connection pooling
- Bearer token authentication
- Exponential backoff retry logic
- Rate limiting support
- Structured error handling

Example:
    >>> class MyClient(BaseIntegrationClient):
    ...     def __init__(self, api_key: str):
    ...         super().__init__(
    ...             name="my_service",
    ...             base_url="https://api.example.com/v1",
    ...             api_key=api_key,
    ...         )
    ...
    ...     async def get_data(self) -> dict[str, Any]:
    ...         return await self.get("/data")
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for all integration errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class RateLimitError(IntegrationError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(IntegrationError):
    """Raised when API authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class PaymentRequiredError(IntegrationError):
    """Raised when API requires payment or credits."""

    def __init__(
        self,
        message: str = "Payment required or insufficient credits",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=402, **kwargs)


class BaseIntegrationClient:
    """
    Abstract base class for third-party API integrations.

    Provides common HTTP functionality with retry logic, error handling,
    and connection pooling. All I/O operations are async.

    Attributes:
        name: Integration name for logging and identification.
        base_url: Base URL for all API requests.
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_base_delay: Base delay for exponential backoff in seconds.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize the integration client.

        Args:
            name: Integration name for logging.
            base_url: Base URL for API requests.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            retry_base_delay: Base delay for exponential backoff.
        """
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """
        Lazy HTTP client creation with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """
        Get default headers for API requests.

        Override this method to customize headers for specific integrations.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON response data.

        Raises:
            AuthenticationError: For 401 responses.
            PaymentRequiredError: For 402 responses.
            RateLimitError: For 429 responses.
            IntegrationError: For other error responses.
        """
        data: dict[str, Any]
        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text}

        if response.status_code == 401:
            raise AuthenticationError(
                message=f"[{self.name}] Authentication failed",
                response_data=data,
            )

        if response.status_code == 402:
            raise PaymentRequiredError(
                message=f"[{self.name}] Payment required or insufficient credits",
                response_data=data,
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message=f"[{self.name}] Rate limit exceeded",
                status_code=429,
                retry_after=int(retry_after) if retry_after else None,
                response_data=data,
            )

        if response.status_code >= 400:
            error_message = data.get("error", data.get("message", "Unknown error"))
            raise IntegrationError(
                message=f"[{self.name}] API error: {error_message}",
                status_code=response.status_code,
                response_data=data,
            )

        return data

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable.

        Args:
            error: The exception to check.

        Returns:
            True if the error is retryable, False otherwise.
        """
        if isinstance(error, httpx.TimeoutException | httpx.NetworkError):
            return True
        if isinstance(error, IntegrationError):
            # Retry on 5xx errors (server errors)
            if error.status_code and 500 <= error.status_code < 600:
                return True
            # Retry on rate limit (with exponential backoff)
            if isinstance(error, RateLimitError):
                return True
        return False

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            endpoint: API endpoint path.
            **kwargs: Additional arguments for httpx request.

        Returns:
            Parsed JSON response data.

        Raises:
            IntegrationError: After all retries exhausted.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Merge custom headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )
                return await self._handle_response(response)

            except Exception as error:
                last_error = error
                is_retryable = self._is_retryable_error(error)

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[{self.name}] Request failed: {error}",
                        extra={
                            "integration": self.name,
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = self.retry_base_delay * (2**attempt)
                # Add jitter (10-50% of delay)
                jitter = delay * (0.1 + 0.4 * (attempt / self.max_retries))
                delay += jitter

                logger.warning(
                    f"[{self.name}] Request failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {error}",
                    extra={
                        "integration": self.name,
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "delay": delay,
                    },
                )
                await asyncio.sleep(delay)

        # This should not be reached, but just in case
        if last_error:
            raise last_error
        raise IntegrationError(f"[{self.name}] Request failed after {self.max_retries} retries")

    async def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make GET request to API.

        Args:
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.
        """
        return await self._request_with_retry("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make POST request to API.

        Args:
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.
        """
        return await self._request_with_retry("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make PUT request to API.

        Args:
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.
        """
        return await self._request_with_retry("PUT", endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make PATCH request to API.

        Args:
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.
        """
        return await self._request_with_retry("PATCH", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make DELETE request to API.

        Args:
            endpoint: API endpoint path.
            **kwargs: Additional request arguments.

        Returns:
            Parsed JSON response data.
        """
        return await self._request_with_retry("DELETE", endpoint, **kwargs)

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug(f"[{self.name}] HTTP client closed")

    async def __aenter__(self) -> "BaseIntegrationClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def health_check(self) -> dict[str, Any]:
        """
        Check integration health/connectivity.

        Override this method to implement integration-specific health checks.

        Returns:
            Health check status with name and healthy status.
        """
        return {
            "name": self.name,
            "healthy": True,
            "message": "Health check not implemented",
        }
