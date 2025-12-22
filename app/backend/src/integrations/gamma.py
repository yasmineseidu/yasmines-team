"""
Gamma API integration client for presentation generation from notes.

Provides async access to Gamma's REST API v1.0 for:
- Presentation creation from text content (notes, prompts, structured content)
- Slide generation with automatic formatting
- Theme and template management
- Presentation retrieval and listing
- Slide updates and modifications

API Documentation:
- Gamma Developer Portal: https://developers.gamma.app/
- API v1.0 (GA): Available since November 5, 2025
- Deprecated: v0.2 (sunset January 16, 2026)

Authentication:
- API key authentication via X-API-KEY header
- OAuth support coming soon
- Requires Pro, Ultra, Team, or Business account

Rate Limits:
- Generous limits: hundreds of requests/hour, thousands/day
- Much higher than deprecated v0.2 (50 requests/day)
- Returns 429 Too Many Requests when exceeded

Features:
- Generate presentations from text content (notes, prompts, etc.)
- Create from template API for structured content
- Support for custom themes (pre-created in Gamma)
- Automatic slide formatting and styling
- Batch slide operations

Example:
    >>> from src.integrations.gamma import GammaClient
    >>> client = GammaClient(api_key="sk_gamma_12345678")
    >>> async with client:
    ...     # Create presentation from meeting notes
    ...     presentation = await client.create_presentation(
    ...         input_text="Meeting notes: Discussed Q4 goals...",
    ...         presentation_type="slides"
    ...     )
    ...     print(f"Created: {presentation['id']}")
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Classes
# ============================================================================


class GammaError(IntegrationError):
    """Base exception for Gamma API errors."""

    pass


class GammaAuthError(AuthenticationError):
    """Gamma authentication error (invalid API key, expired credentials)."""

    pass


class GammaRateLimitError(RateLimitError):
    """Gamma rate limit error (too many requests)."""

    pass


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class GammaPresentation:
    """Gamma presentation information."""

    id: str
    title: str
    """Presentation title."""
    state: str
    """Presentation state (e.g., 'draft', 'published')."""
    updated_at: int
    """Last update timestamp."""
    created_at: int
    """Creation timestamp."""
    slide_count: int | None = None
    """Number of slides in presentation."""
    theme_id: str | None = None
    """Theme ID used for this presentation."""
    folder_id: str | None = None
    """Folder ID if presentation is organized."""
    url: str | None = None
    """Public URL of presentation."""
    raw: dict[str, Any] = field(default_factory=dict)
    """Raw API response data."""


@dataclass
class GammaSlide:
    """Gamma slide information."""

    id: str
    title: str
    """Slide title/heading."""
    content: str
    """Slide content (text, formatted)."""
    slide_number: int
    """Position in presentation (0-indexed)."""
    notes: str | None = None
    """Speaker notes for this slide."""
    raw: dict[str, Any] = field(default_factory=dict)
    """Raw API response data."""


@dataclass
class GammaTheme:
    """Gamma presentation theme information."""

    id: str
    name: str
    """Theme display name."""
    description: str | None = None
    """Theme description."""
    preview_url: str | None = None
    """URL to theme preview image."""
    raw: dict[str, Any] = field(default_factory=dict)
    """Raw API response data."""


# ============================================================================
# Gamma Client
# ============================================================================


class GammaClient(BaseIntegrationClient):
    """Async client for Gamma API v1.0.

    Handles presentation generation, slide management, and theme operations
    with built-in error handling, retry logic, and rate limiting.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize Gamma client.

        Args:
            api_key: Gamma API key (from account settings).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            retry_base_delay: Base delay for exponential backoff in seconds.

        Raises:
            ValueError: If API key is empty or invalid.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        super().__init__(
            name="gamma",
            base_url="https://api.gamma.app/v1.0",
            api_key=api_key.strip(),
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )
        logger.info("Initialized Gamma client")

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for Gamma API requests.

        Gamma uses X-API-KEY header (not Authorization).

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_presentation(
        self,
        input_text: str,
        presentation_type: str = "slides",
        theme_id: str | None = None,
        title: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a new presentation from text content.

        Generates a presentation from provided text (notes, prompts, structured
        content). Gamma automatically formats content into slides with styling.

        Args:
            input_text: Content to generate presentation from (notes, prompts,
                or structured content). Should contain actual content to display,
                not instructions on how to create the presentation.
            presentation_type: Type of content to create ('slides', 'document',
                'webpage', 'social'). Default is 'slides'.
            theme_id: Optional theme ID for presentation styling.
                Get available themes via list_themes().
            title: Optional presentation title. If not provided, Gamma will
                generate one from content.
            **kwargs: Additional parameters for API (passed through).

        Returns:
            Dictionary containing:
            - id: Presentation ID
            - title: Presentation title
            - state: Current state (e.g., 'draft')
            - url: Public presentation URL
            - created_at: Creation timestamp
            - ... (other Gamma fields)

        Raises:
            GammaAuthError: If authentication fails (invalid API key).
            GammaRateLimitError: If rate limit exceeded.
            GammaError: For other API errors.

        Example:
            >>> client = GammaClient(api_key="sk_gamma_...")
            >>> async with client:
            ...     result = await client.create_presentation(
            ...         input_text="Q4 Planning Meeting: Goals, timeline, budget",
            ...         presentation_type="slides",
            ...         title="Q4 Planning"
            ...     )
            ...     print(f"Created presentation: {result['id']}")
        """
        payload: dict[str, Any] = {
            "inputText": input_text,
            "outputFormat": presentation_type,
        }

        if theme_id:
            payload["themeId"] = theme_id

        if title:
            payload["title"] = title

        # Add any additional parameters
        payload.update(kwargs)

        try:
            logger.info(f"Creating {presentation_type} from text content")
            response = await self.post("/presentations/generate", json=payload)
            logger.info(f"Successfully created presentation: {response.get('id')}")
            return response
        except Exception as e:
            logger.error(f"Failed to create presentation: {e}")
            raise

    async def create_presentation_from_template(
        self,
        template_id: str,
        title: str,
        content: dict[str, Any],
        theme_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create presentation from template with structured content.

        Uses a pre-defined template to create a presentation with structured
        content (sections, slides, specific layouts).

        Args:
            template_id: ID of the template to use.
            title: Presentation title.
            content: Structured content for the template
                (format depends on template).
            theme_id: Optional theme ID for styling.
            **kwargs: Additional parameters.

        Returns:
            Dictionary with presentation details.

        Raises:
            GammaAuthError: If authentication fails.
            GammaRateLimitError: If rate limit exceeded.
            GammaError: For other API errors.
        """
        payload: dict[str, Any] = {
            "templateId": template_id,
            "title": title,
            "content": content,
        }

        if theme_id:
            payload["themeId"] = theme_id

        payload.update(kwargs)

        try:
            logger.info(f"Creating presentation from template: {template_id}")
            response = await self.post("/presentations/createFromTemplate", json=payload)
            logger.info(f"Successfully created from template: {response.get('id')}")
            return response
        except Exception as e:
            logger.error(f"Failed to create from template: {e}")
            raise

    async def get_presentation(self, presentation_id: str) -> dict[str, Any]:
        """
        Retrieve presentation details.

        Args:
            presentation_id: ID of presentation to retrieve.

        Returns:
            Dictionary with presentation information:
            - id, title, state, created_at, updated_at
            - slide_count, theme_id, url, etc.

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: If presentation not found or API error.
        """
        try:
            logger.info(f"Retrieving presentation: {presentation_id}")
            response = await self.get(f"/presentations/{presentation_id}")
            logger.info(f"Retrieved presentation: {response.get('title')}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve presentation: {e}")
            raise

    async def list_presentations(self, limit: int = 50, skip: int = 0) -> dict[str, Any]:
        """
        List user's presentations with pagination.

        Args:
            limit: Maximum presentations to return (default 50).
            skip: Number of presentations to skip for pagination.

        Returns:
            Dictionary containing:
            - presentations: List of presentation objects
            - total: Total count of presentations
            - limit, skip: Pagination parameters

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: For API errors.
        """
        try:
            logger.info(f"Listing presentations (limit={limit}, skip={skip})")
            response = await self.get("/presentations", params={"limit": limit, "skip": skip})
            logger.info(f"Retrieved {len(response.get('presentations', []))} " "presentations")
            return response
        except Exception as e:
            logger.error(f"Failed to list presentations: {e}")
            raise

    async def add_slides(
        self,
        presentation_id: str,
        slides_content: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Add slides to existing presentation.

        Each slide can contain text, bullet points, images, or mixed content.
        Gamma automatically formats and styles content.

        Args:
            presentation_id: ID of target presentation.
            slides_content: List of slide objects, each containing:
                - title: Slide heading
                - content: Text, bullet points, or formatted content
                - notes (optional): Speaker notes

        Returns:
            Dictionary with updated presentation details.

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: For API errors.

        Example:
            >>> slides = [
            ...     {
            ...         "title": "Agenda",
            ...         "content": "• Q4 Goals\n• Timeline\n• Budget"
            ...     },
            ...     {
            ...         "title": "Key Metrics",
            ...         "content": "Revenue target: $2M\nGrowth rate: 25%"
            ...     }
            ... ]
            >>> result = await client.add_slides(
            ...     presentation_id="pres_123",
            ...     slides_content=slides
            ... )
        """
        payload = {
            "slides": slides_content,
        }

        try:
            logger.info(
                f"Adding {len(slides_content)} slides to " f"presentation: {presentation_id}"
            )
            response = await self.post(f"/presentations/{presentation_id}/slides", json=payload)
            logger.info(f"Successfully added {len(slides_content)} slides")
            return response
        except Exception as e:
            logger.error(f"Failed to add slides: {e}")
            raise

    async def update_slide(
        self,
        presentation_id: str,
        slide_index: int,
        title: str | None = None,
        content: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Update existing slide in presentation.

        Args:
            presentation_id: ID of presentation.
            slide_index: Zero-based position of slide in presentation.
            title: New slide title (optional).
            content: New slide content (optional).
            notes: New speaker notes (optional).

        Returns:
            Dictionary with updated slide details.

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: For API errors.
        """
        payload: dict[str, Any] = {}

        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if notes is not None:
            payload["notes"] = notes

        if not payload:
            raise ValueError("At least one of title, content, or notes must be provided")

        try:
            logger.info(f"Updating slide {slide_index} in presentation: {presentation_id}")
            response = await self.patch(
                f"/presentations/{presentation_id}/slides/{slide_index}",
                json=payload,
            )
            logger.info(f"Successfully updated slide {slide_index}")
            return response
        except Exception as e:
            logger.error(f"Failed to update slide: {e}")
            raise

    async def list_themes(self) -> dict[str, Any]:
        """
        List available presentation themes.

        Themes must be pre-created in Gamma account and are referenced by ID
        in presentation creation. This endpoint retrieves available themes
        for your account.

        Returns:
            Dictionary containing:
            - themes: List of theme objects with id, name, description
            - total: Total count of themes

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: For API errors.

        Example:
            >>> result = await client.list_themes()
            >>> for theme in result['themes']:
            ...     print(f"{theme['id']}: {theme['name']}")
        """
        try:
            logger.info("Listing available themes")
            response = await self.get("/themes")
            logger.info(f"Retrieved {len(response.get('themes', []))} themes")
            return response
        except Exception as e:
            logger.error(f"Failed to list themes: {e}")
            raise

    async def delete_presentation(self, presentation_id: str) -> dict[str, Any]:
        """
        Delete a presentation.

        Permanently deletes the presentation and all its slides.

        Args:
            presentation_id: ID of presentation to delete.

        Returns:
            Dictionary with deletion confirmation.

        Raises:
            GammaAuthError: If authentication fails.
            GammaError: For API errors.
        """
        try:
            logger.info(f"Deleting presentation: {presentation_id}")
            response = await self.delete(f"/presentations/{presentation_id}")
            logger.info(f"Successfully deleted presentation: {presentation_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to delete presentation: {e}")
            raise

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generic request method for future-proof API calls.

        Allows calling new endpoints without code changes.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint: API endpoint path (e.g., "/presentations/123").
            **kwargs: Request parameters (json, params, etc.).

        Returns:
            API response as dictionary.

        Raises:
            GammaAuthError: For authentication errors.
            GammaRateLimitError: For rate limit errors.
            GammaError: For other API errors.
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                **kwargs,
            )

            # Handle response
            if response.status_code == 401:
                raise GammaAuthError(
                    message="Authentication failed - invalid API key",
                    status_code=401,
                )
            if response.status_code == 429:
                raise GammaRateLimitError(
                    message="Rate limit exceeded",
                    status_code=429,
                    retry_after=int(response.headers.get("Retry-After", 60)),
                )
            if response.status_code >= 400:
                raise GammaError(
                    message=f"API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json() if response.text else {}
        except (GammaAuthError, GammaRateLimitError, GammaError):
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise GammaError(f"Request failed: {str(e)}") from e

    async def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request with retry logic."""
        return await self._request_with_retry("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make POST request with retry logic."""
        return await self._request_with_retry("POST", endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make PATCH request with retry logic."""
        return await self._request_with_retry("PATCH", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make DELETE request with retry logic."""
        return await self._request_with_retry("DELETE", endpoint, **kwargs)

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make request with exponential backoff retry logic.

        Retries on transient errors (5xx, timeouts) but not on 4xx errors
        (except 429 which is handled as rate limit).

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            **kwargs: Request parameters.

        Returns:
            API response.

        Raises:
            GammaAuthError: For authentication errors (not retried).
            GammaRateLimitError: For rate limit (retried with Retry-After).
            GammaError: For other errors.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._request(method, endpoint, **kwargs)
            except GammaAuthError:
                # Don't retry authentication errors
                raise
            except GammaRateLimitError as e:
                # Handle rate limit with Retry-After header
                if attempt < self.max_retries:
                    retry_after = e.retry_after or (self.retry_base_delay * (2**attempt))
                    # Add jitter to prevent thundering herd
                    retry_after += random.uniform(0, 1)
                    logger.warning(
                        f"Rate limited. Retrying after {retry_after:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    import asyncio

                    await asyncio.sleep(retry_after)
                    last_error = e
                    continue
                raise
            except GammaError as e:
                # Retry on transient errors (5xx, timeouts)
                if e.status_code and 500 <= e.status_code < 600:
                    if attempt < self.max_retries:
                        delay = self.retry_base_delay * (2**attempt)
                        # Add jitter
                        delay += random.uniform(0, 1)
                        logger.warning(
                            f"Transient error {e.status_code}. Retrying in "
                            f"{delay:.2f}s (attempt {attempt + 1}/"
                            f"{self.max_retries + 1})"
                        )
                        import asyncio

                        await asyncio.sleep(delay)
                        last_error = e
                        continue
                    raise
                # Don't retry 4xx errors (except 429 which is caught above)
                if e.status_code and 400 <= e.status_code < 500:
                    raise
                # For other errors, retry
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)
                    delay += random.uniform(0, 1)
                    logger.warning(
                        f"Error occurred. Retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    import asyncio

                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                raise
            except Exception as e:
                # Unexpected error - try to retry
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)
                    delay += random.uniform(0, 1)
                    logger.warning(f"Unexpected error: {e}. Retrying in {delay:.2f}s")
                    import asyncio

                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                raise GammaError(f"All retry attempts failed: {str(e)}") from e

        # Should not reach here, but raise last error if all retries exhausted
        if last_error:
            raise GammaError(f"Max retries exceeded: {str(last_error)}") from last_error
        raise GammaError("Request failed: Unknown error")
