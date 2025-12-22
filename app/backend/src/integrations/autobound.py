"""
Autobound API integration client.

Provides AI-powered sales personalization including:
- Personalized email generation
- Call scripts and LinkedIn messages
- Prospect insights and research
- Multi-model support (GPT-4, Claude, fine-tuned)

API Documentation: https://autobound-api.readme.io/docs/introduction
Authentication: X-API-KEY header

Example:
    >>> from src.integrations.autobound import AutoboundClient
    >>> client = AutoboundClient(api_key="your_api_key")  # pragma: allowlist secret
    >>> async with client:
    ...     content = await client.generate_email(
    ...         contact_email="prospect@company.com",
    ...         user_email="sales@mycompany.com",
    ...     )
    ...     print(content.content)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class AutoboundError(IntegrationError):
    """Base exception for Autobound API errors."""

    pass


class AutoboundAuthError(AutoboundError, AuthenticationError):
    """Authentication error for Autobound API."""

    pass


class AutoboundRateLimitError(AutoboundError):
    """Rate limit exceeded for Autobound API."""

    pass


class AutoboundContentType(str, Enum):
    """Content types for Autobound generation."""

    EMAIL = "email"
    EMAIL_SEQUENCE = "email sequence"
    CALL_SCRIPT = "call script"
    LINKEDIN_CONNECTION = "LinkedIn connection request"
    SMS = "SMS"
    OPENER = "opener"
    CUSTOM = "custom"


class AutoboundWritingStyle(str, Enum):
    """Writing styles for content generation."""

    CXO_PITCH = "cxo_pitch"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FORMAL = "formal"


class AutoboundModel(str, Enum):
    """AI models available for content generation."""

    GPT4O = "gpt4o"
    GPT4 = "gpt4"
    OPUS = "opus"
    SONNET = "sonnet"
    FINE_TUNED = "fine_tuned"


class AutoboundInsightType(str, Enum):
    """Types of insights that can be enabled/disabled."""

    PODCAST = "podcast"
    SHARED_CONNECTIONS = "shared_connections"
    FINANCIAL = "financial"
    NEWS = "news"
    JOB_POSTS = "job_posts"
    TECH_STACK = "tech_stack"
    SOCIAL_MEDIA = "social_media"
    COMPANY_INFO = "company_info"


@dataclass
class AutoboundContent:
    """Generated content from Autobound."""

    content: str
    content_type: str
    contact_email: str
    model_used: str | None = None
    insights_used: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutoboundInsight:
    """A single insight about a contact/company."""

    type: str
    title: str
    description: str
    relevance_score: float | None = None
    source: str | None = None
    date: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutoboundInsightsResult:
    """Result from generate insights endpoint."""

    contact_email: str
    insights: list[AutoboundInsight]
    total_count: int
    raw: dict[str, Any] = field(default_factory=dict)


class AutoboundClient(BaseIntegrationClient):
    """
    Async client for Autobound AI-powered sales personalization API.

    Provides methods for generating personalized sales content and
    retrieving prospect insights using AI.

    Example:
        >>> async with AutoboundClient(api_key="key") as client:  # pragma: allowlist secret
        ...     email = await client.generate_email(
        ...         contact_email="ceo@techcompany.com",
        ...         user_email="rep@sales.com",
        ...         writing_style=AutoboundWritingStyle.CXO_PITCH,
        ...     )
        ...     print(email.content)
    """

    API_BASE_URL = "https://api.autobound.ai/api/external"
    CONTENT_VERSION = "v3.6"
    INSIGHTS_VERSION = "v1.4"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,  # Longer timeout for AI generation
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Autobound client.

        Args:
            api_key: Autobound API key from settings.
            timeout: Request timeout in seconds (default 60s for AI generation).
            max_retries: Maximum retry attempts for failed requests.
        """
        super().__init__(
            name="autobound",
            base_url=self.API_BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: Any) -> dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON response.

        Raises:
            AutoboundAuthError: For 401/403 responses.
            AutoboundRateLimitError: For 429 responses.
            AutoboundError: For other error responses.
        """
        status_code = response.status_code

        if status_code == 401:
            raise AutoboundAuthError(
                message="Invalid API key",
            )

        if status_code == 403:
            raise AutoboundAuthError(
                message="Access forbidden - check API key permissions",
            )

        if status_code == 429:
            raise AutoboundRateLimitError(
                message="Rate limit exceeded",
                status_code=status_code,
            )

        if status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get("message", response.text)
            except Exception:
                error_message = response.text

            raise AutoboundError(
                message=f"API error: {error_message}",
                status_code=status_code,
            )

        # Handle empty responses
        if not response.text:
            return {}

        try:
            result: dict[str, Any] = response.json()
            return result
        except Exception:
            # Some endpoints return plain text
            return {"content": response.text}

    async def generate_content(
        self,
        contact_email: str,
        user_email: str,
        content_type: AutoboundContentType | str = AutoboundContentType.EMAIL,
        custom_content_type: str | None = None,
        writing_style: AutoboundWritingStyle | str | None = None,
        word_count: int | None = None,
        language: str = "english",
        additional_context: str | None = None,
        model: AutoboundModel | str | None = None,
        enabled_insights: list[str] | None = None,
        disabled_insights: list[str] | None = None,
    ) -> AutoboundContent:
        """
        Generate personalized sales content.

        Args:
            contact_email: Target prospect's email address.
            user_email: Requester's email address.
            content_type: Type of content to generate.
            custom_content_type: Natural language description for custom content.
            writing_style: Style of writing to use.
            word_count: Target word count for generated content.
            language: Language for content (default: english).
            additional_context: Custom context like meeting details.
            model: AI model to use for generation.
            enabled_insights: List of insight types to include.
            disabled_insights: List of insight types to exclude.

        Returns:
            AutoboundContent with generated content.

        Raises:
            ValueError: If contact_email or user_email is empty.
            AutoboundError: If API request fails.
        """
        if not contact_email or not contact_email.strip():
            raise ValueError("contact_email is required")
        if not user_email or not user_email.strip():
            raise ValueError("user_email is required")

        # Convert enum to string value
        content_type_str = (
            content_type.value if isinstance(content_type, AutoboundContentType) else content_type
        )

        payload: dict[str, Any] = {
            "contactEmail": contact_email.strip(),
            "userEmail": user_email.strip(),
            "contentType": content_type_str,
        }

        if content_type_str == "custom" and custom_content_type:
            payload["customContentType"] = custom_content_type

        if writing_style:
            style_str = (
                writing_style.value
                if isinstance(writing_style, AutoboundWritingStyle)
                else writing_style
            )
            payload["writingStyle"] = style_str

        if word_count:
            payload["wordCount"] = str(word_count)

        if language:
            payload["language"] = language

        if additional_context:
            payload["additionalContext"] = additional_context

        if model:
            model_str = model.value if isinstance(model, AutoboundModel) else model
            payload["model"] = model_str

        if enabled_insights:
            payload["enabledInsights"] = enabled_insights

        if disabled_insights:
            payload["disabledInsights"] = disabled_insights

        endpoint = f"/generate-content/{self.CONTENT_VERSION}"
        response = await self.post(endpoint, json=payload)

        # Parse response
        content_text = response.get("content", "")
        if isinstance(content_text, dict):
            # Some responses wrap content in nested structure
            content_text = content_text.get("content", str(content_text))

        return AutoboundContent(
            content=content_text,
            content_type=content_type_str,
            contact_email=contact_email,
            model_used=response.get("model"),
            insights_used=response.get("insightsUsed", []),
            raw=response,
        )

    async def generate_email(
        self,
        contact_email: str,
        user_email: str,
        writing_style: AutoboundWritingStyle | str | None = None,
        word_count: int | None = None,
        additional_context: str | None = None,
        model: AutoboundModel | str | None = None,
    ) -> AutoboundContent:
        """
        Generate a personalized email for a prospect.

        Convenience method for generate_content with EMAIL type.

        Args:
            contact_email: Target prospect's email address.
            user_email: Requester's email address.
            writing_style: Style of writing to use.
            word_count: Target word count.
            additional_context: Custom context.
            model: AI model to use.

        Returns:
            AutoboundContent with generated email.
        """
        return await self.generate_content(
            contact_email=contact_email,
            user_email=user_email,
            content_type=AutoboundContentType.EMAIL,
            writing_style=writing_style,
            word_count=word_count,
            additional_context=additional_context,
            model=model,
        )

    async def generate_call_script(
        self,
        contact_email: str,
        user_email: str,
        writing_style: AutoboundWritingStyle | str | None = None,
        additional_context: str | None = None,
        model: AutoboundModel | str | None = None,
    ) -> AutoboundContent:
        """
        Generate a personalized call script for a prospect.

        Args:
            contact_email: Target prospect's email address.
            user_email: Requester's email address.
            writing_style: Style of writing to use.
            additional_context: Custom context like meeting topic.
            model: AI model to use.

        Returns:
            AutoboundContent with generated call script.
        """
        return await self.generate_content(
            contact_email=contact_email,
            user_email=user_email,
            content_type=AutoboundContentType.CALL_SCRIPT,
            writing_style=writing_style,
            additional_context=additional_context,
            model=model,
        )

    async def generate_linkedin_message(
        self,
        contact_email: str,
        user_email: str,
        writing_style: AutoboundWritingStyle | str | None = None,
        model: AutoboundModel | str | None = None,
    ) -> AutoboundContent:
        """
        Generate a personalized LinkedIn connection request.

        Args:
            contact_email: Target prospect's email address.
            user_email: Requester's email address.
            writing_style: Style of writing to use.
            model: AI model to use.

        Returns:
            AutoboundContent with generated LinkedIn message.
        """
        return await self.generate_content(
            contact_email=contact_email,
            user_email=user_email,
            content_type=AutoboundContentType.LINKEDIN_CONNECTION,
            writing_style=writing_style,
            word_count=300,  # LinkedIn has character limits
            model=model,
        )

    async def generate_custom_content(
        self,
        contact_email: str,
        user_email: str,
        custom_prompt: str,
        writing_style: AutoboundWritingStyle | str | None = None,
        word_count: int | None = None,
        model: AutoboundModel | str | None = None,
    ) -> AutoboundContent:
        """
        Generate custom personalized content with a natural language prompt.

        Args:
            contact_email: Target prospect's email address.
            user_email: Requester's email address.
            custom_prompt: Natural language description of desired output.
            writing_style: Style of writing to use.
            word_count: Target word count.
            model: AI model to use.

        Returns:
            AutoboundContent with generated custom content.

        Raises:
            ValueError: If custom_prompt is empty.
        """
        if not custom_prompt or not custom_prompt.strip():
            raise ValueError("custom_prompt is required for custom content")

        return await self.generate_content(
            contact_email=contact_email,
            user_email=user_email,
            content_type=AutoboundContentType.CUSTOM,
            custom_content_type=custom_prompt,
            writing_style=writing_style,
            word_count=word_count,
            model=model,
        )

    async def generate_insights(
        self,
        contact_email: str,
        max_insights: int = 20,
    ) -> AutoboundInsightsResult:
        """
        Generate insights about a prospect/contact.

        Returns ranked insights including news, social media, job posts,
        tech stacks, and other relevant information.

        Args:
            contact_email: Email of the contact to research.
            max_insights: Maximum number of insights to return (default 20).

        Returns:
            AutoboundInsightsResult with ranked insights.

        Raises:
            ValueError: If contact_email is empty.
            AutoboundError: If API request fails.
        """
        if not contact_email or not contact_email.strip():
            raise ValueError("contact_email is required")

        payload = {
            "contactEmail": contact_email.strip(),
            "maxInsights": min(max(1, max_insights), 25),  # API max is 25
        }

        endpoint = f"/generate-insights/{self.INSIGHTS_VERSION}"
        response = await self.post(endpoint, json=payload)

        # Parse insights from response
        insights_data = response.get("insights", [])
        insights = []

        for insight_raw in insights_data:
            insight = AutoboundInsight(
                type=insight_raw.get("type", "unknown"),
                title=insight_raw.get("title", ""),
                description=insight_raw.get("description", ""),
                relevance_score=insight_raw.get("relevanceScore"),
                source=insight_raw.get("source"),
                date=insight_raw.get("date"),
                raw=insight_raw,
            )
            insights.append(insight)

        return AutoboundInsightsResult(
            contact_email=contact_email,
            insights=insights,
            total_count=len(insights),
            raw=response,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check if the Autobound API is accessible.

        Returns:
            Health status dictionary with:
                - healthy: bool
                - name: str
                - error: str (if unhealthy)
        """
        try:
            # Make a simple request to verify API key is valid
            # Use a test email that won't consume credits
            await self.post(
                f"/generate-insights/{self.INSIGHTS_VERSION}",
                json={"contactEmail": "test@autobound-health-check.invalid"},
            )
            return {
                "healthy": True,
                "name": self.name,
                "api_url": self.API_BASE_URL,
            }
        except (AutoboundAuthError, AuthenticationError) as e:
            return {
                "healthy": False,
                "name": self.name,
                "error": str(e),
                "api_url": self.API_BASE_URL,
            }
        except Exception as e:
            # Any non-auth error means the API is reachable
            return {
                "healthy": True,
                "name": self.name,
                "api_url": self.API_BASE_URL,
                "note": f"API reachable but test failed: {e}",
            }
