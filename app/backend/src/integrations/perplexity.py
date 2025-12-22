"""
Perplexity AI API integration client.

Provides AI-powered research capabilities with real-time web search
and source citations. Useful for market research, competitive analysis,
and knowledge synthesis.

API Documentation: https://docs.perplexity.ai/
Base URL: https://api.perplexity.ai

Features:
- AI-powered Q&A with web search
- Source citations with URLs
- Multiple search modes (web, academic, SEC filings)
- Conversation context management
- Streaming support
- Follow-up question handling

Models:
- sonar: Lightweight, fast search (cheapest)
- sonar-pro: Advanced search with larger context
- sonar-reasoning-pro: Premier reasoning capabilities
- sonar-deep-research: Exhaustive multi-step research

Pricing (per request + tokens):
- sonar: ~$0.20/1M input, $0.60/1M output
- sonar-pro: ~$3/1M input, $15/1M output
- Request fees vary by search context size

Example:
    >>> from src.integrations.perplexity import PerplexityClient
    >>> client = PerplexityClient(api_key="your-api-key")
    >>> result = await client.research("What are top SaaS pricing models?")
    >>> print(result.content)
    >>> for source in result.citations:
    ...     print(f"Source: {source.url}")
"""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.integrations.base import (
    BaseIntegrationClient,
    IntegrationError,
)

logger = logging.getLogger(__name__)


class PerplexityModel(str, Enum):
    """Available Perplexity AI models."""

    SONAR = "sonar"
    SONAR_PRO = "sonar-pro"
    SONAR_REASONING_PRO = "sonar-reasoning-pro"
    SONAR_DEEP_RESEARCH = "sonar-deep-research"


class PerplexitySearchMode(str, Enum):
    """Search modes for Perplexity API."""

    WEB = "web"  # Standard web search
    ACADEMIC = "academic"  # Academic papers and research
    SEC = "sec"  # SEC filings for financial research


class PerplexityError(IntegrationError):
    """Perplexity-specific error."""

    pass


@dataclass
class PerplexityCitation:
    """Citation/source from a Perplexity response."""

    url: str
    title: str | None = None
    date: str | None = None
    snippet: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerplexityUsage:
    """Token usage statistics from a Perplexity response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    citation_tokens: int = 0
    num_search_queries: int = 0


@dataclass
class PerplexityMessage:
    """A message in the conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class PerplexityResponse:
    """Complete response from Perplexity API."""

    id: str
    model: str
    content: str
    citations: list[PerplexityCitation] = field(default_factory=list)
    usage: PerplexityUsage = field(default_factory=PerplexityUsage)
    finish_reason: str | None = None
    created: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerplexityConversation:
    """Manages a multi-turn conversation with Perplexity."""

    messages: list[PerplexityMessage] = field(default_factory=list)
    system_prompt: str | None = None

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append(PerplexityMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to the conversation."""
        self.messages.append(PerplexityMessage(role="assistant", content=content))

    def to_api_messages(self) -> list[dict[str, str]]:
        """Convert conversation to API format."""
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend({"role": msg.role, "content": msg.content} for msg in self.messages)
        return messages

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []


class PerplexityClient(BaseIntegrationClient):
    """
    Perplexity AI API client for research and Q&A.

    Provides AI-powered answers with real-time web search and source citations.
    Supports multiple models, search modes, and conversation management.

    Example:
        >>> async with PerplexityClient(api_key="key") as client:  # pragma: allowlist secret
        ...     # Simple research query
        ...     result = await client.research("What is quantum computing?")
        ...     print(result.content)
        ...     for citation in result.citations:
        ...         print(f"  - {citation.url}")
        ...
        ...     # Multi-turn conversation
        ...     conv = PerplexityConversation(
        ...         system_prompt="You are a market research analyst."
        ...     )
        ...     result = await client.chat(
        ...         "What are the top CRM platforms?",
        ...         conversation=conv
        ...     )
        ...     result2 = await client.chat(
        ...         "How do they compare on pricing?",
        ...         conversation=conv
        ...     )
    """

    BASE_URL = "https://api.perplexity.ai"

    def __init__(
        self,
        api_key: str,
        default_model: PerplexityModel = PerplexityModel.SONAR,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Perplexity client.

        Args:
            api_key: Perplexity API key from dashboard
            default_model: Default model for requests (default: sonar)
            timeout: Request timeout in seconds (default 60s for research)
            max_retries: Maximum retry attempts for transient failures
        """
        super().__init__(
            name="perplexity",
            base_url=self.BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.default_model = default_model

    async def research(
        self,
        query: str,
        *,
        model: PerplexityModel | None = None,
        search_mode: PerplexitySearchMode = PerplexitySearchMode.WEB,
        max_tokens: int | None = None,
        temperature: float = 0.2,
        response_language: str | None = None,
        search_recency_filter: str | None = None,
        search_after_date: str | None = None,
    ) -> PerplexityResponse:
        """
        Perform a research query with web search.

        This is the primary method for one-off research questions.
        Returns AI-generated answers with source citations.

        Args:
            query: Research question or topic
            model: Model to use (default: client's default_model)
            search_mode: Type of search (web, academic, sec)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-2, default 0.2)
            response_language: Preferred response language
            search_recency_filter: Filter by date (e.g., "month", "week", "day")
            search_after_date: Only include content after this date (MM/DD/YYYY)

        Returns:
            PerplexityResponse with content and citations

        Raises:
            PerplexityError: If research query fails
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        messages = [{"role": "user", "content": query.strip()}]

        return await self._chat_completion(
            messages=messages,
            model=model,
            search_mode=search_mode,
            max_tokens=max_tokens,
            temperature=temperature,
            response_language=response_language,
            search_recency_filter=search_recency_filter,
            search_after_date=search_after_date,
        )

    async def chat(
        self,
        message: str,
        *,
        conversation: PerplexityConversation | None = None,
        model: PerplexityModel | None = None,
        search_mode: PerplexitySearchMode = PerplexitySearchMode.WEB,
        max_tokens: int | None = None,
        temperature: float = 0.2,
        response_language: str | None = None,
        search_disabled: bool = False,
    ) -> PerplexityResponse:
        """
        Send a chat message, optionally with conversation context.

        Use this for multi-turn conversations where follow-up questions
        need context from previous messages.

        Args:
            message: User message to send
            conversation: Conversation context for follow-ups
            model: Model to use (default: client's default_model)
            search_mode: Type of search (web, academic, sec)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-2, default 0.2)
            response_language: Preferred response language
            search_disabled: Disable web search (use training data only)

        Returns:
            PerplexityResponse with content and citations

        Raises:
            PerplexityError: If chat fails
            ValueError: If message is empty
        """
        if not message or not message.strip():
            raise ValueError("message is required")

        # Build messages list
        if conversation:
            conversation.add_user_message(message.strip())
            messages = conversation.to_api_messages()
        else:
            messages = [{"role": "user", "content": message.strip()}]

        response = await self._chat_completion(
            messages=messages,
            model=model,
            search_mode=search_mode,
            max_tokens=max_tokens,
            temperature=temperature,
            response_language=response_language,
            search_disabled=search_disabled,
        )

        # Add assistant response to conversation
        if conversation:
            conversation.add_assistant_message(response.content)

        return response

    async def research_with_system_prompt(
        self,
        query: str,
        system_prompt: str,
        *,
        model: PerplexityModel | None = None,
        search_mode: PerplexitySearchMode = PerplexitySearchMode.WEB,
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> PerplexityResponse:
        """
        Perform research with a custom system prompt.

        Useful for specialized research personas (e.g., market analyst,
        competitor researcher, industry expert).

        Args:
            query: Research question
            system_prompt: Custom system instructions
            model: Model to use
            search_mode: Type of search
            max_tokens: Maximum tokens in response
            temperature: Response randomness

        Returns:
            PerplexityResponse with content and citations
        """
        if not query or not query.strip():
            raise ValueError("query is required")
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt is required")

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": query.strip()},
        ]

        return await self._chat_completion(
            messages=messages,
            model=model,
            search_mode=search_mode,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def academic_search(
        self,
        query: str,
        *,
        model: PerplexityModel | None = None,
        max_tokens: int | None = None,
    ) -> PerplexityResponse:
        """
        Search academic papers and research.

        Specialized method for scholarly research that uses
        the academic search mode.

        Args:
            query: Academic research question
            model: Model to use
            max_tokens: Maximum tokens in response

        Returns:
            PerplexityResponse with academic sources
        """
        return await self.research(
            query,
            model=model,
            search_mode=PerplexitySearchMode.ACADEMIC,
            max_tokens=max_tokens,
            temperature=0.1,  # More deterministic for academic
        )

    async def financial_research(
        self,
        query: str,
        *,
        model: PerplexityModel | None = None,
        max_tokens: int | None = None,
    ) -> PerplexityResponse:
        """
        Search SEC filings for financial research.

        Specialized method for financial research that uses
        the SEC search mode.

        Args:
            query: Financial research question
            model: Model to use
            max_tokens: Maximum tokens in response

        Returns:
            PerplexityResponse with SEC filing sources
        """
        return await self.research(
            query,
            model=model,
            search_mode=PerplexitySearchMode.SEC,
            max_tokens=max_tokens,
            temperature=0.1,  # More deterministic for financial
        )

    async def deep_research(
        self,
        query: str,
        *,
        reasoning_effort: str = "medium",
        max_tokens: int | None = None,
    ) -> PerplexityResponse:
        """
        Perform exhaustive multi-step research.

        Uses the sonar-deep-research model for comprehensive
        research that requires multiple search iterations.

        Args:
            query: Research topic or question
            reasoning_effort: Effort level ("low", "medium", "high")
            max_tokens: Maximum tokens in response

        Returns:
            PerplexityResponse with comprehensive analysis
        """
        if reasoning_effort not in ("low", "medium", "high"):
            raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")

        messages = [{"role": "user", "content": query.strip()}]

        return await self._chat_completion(
            messages=messages,
            model=PerplexityModel.SONAR_DEEP_RESEARCH,
            max_tokens=max_tokens,
            temperature=0.1,
            reasoning_effort=reasoning_effort,
        )

    async def _chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: PerplexityModel | None = None,
        search_mode: PerplexitySearchMode | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.2,
        response_language: str | None = None,
        search_recency_filter: str | None = None,
        search_after_date: str | None = None,
        search_disabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> PerplexityResponse:
        """
        Make a chat completion request to Perplexity API.

        Internal method used by all public methods.

        Args:
            messages: List of conversation messages
            model: Model to use
            search_mode: Search mode (web, academic, sec)
            max_tokens: Maximum completion tokens
            temperature: Response randomness
            response_language: Preferred language
            search_recency_filter: Time filter for search
            search_after_date: Date filter (MM/DD/YYYY)
            search_disabled: Disable web search
            reasoning_effort: For deep-research model

        Returns:
            PerplexityResponse with parsed content and citations
        """
        use_model = model or self.default_model

        payload: dict[str, Any] = {
            "model": use_model.value,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Search options
        web_search_options: dict[str, Any] = {}

        if search_mode and search_mode != PerplexitySearchMode.WEB:
            web_search_options["search_mode"] = search_mode.value

        if search_recency_filter:
            web_search_options["search_recency_filter"] = search_recency_filter

        if search_after_date:
            web_search_options["search_after_date_filter"] = search_after_date

        if web_search_options:
            payload["web_search_options"] = web_search_options

        if search_disabled:
            payload["search_disabled"] = True

        # Language preference (sonar and sonar-pro only)
        if response_language and use_model in (
            PerplexityModel.SONAR,
            PerplexityModel.SONAR_PRO,
        ):
            payload["response_language"] = response_language

        # Reasoning effort (deep-research only)
        if reasoning_effort and use_model == PerplexityModel.SONAR_DEEP_RESEARCH:
            payload["reasoning_effort"] = reasoning_effort

        try:
            response = await self.post("/chat/completions", json=payload)
            return self._parse_response(response)
        except IntegrationError as e:
            raise PerplexityError(
                message=f"Chat completion failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    async def stream_research(
        self,
        query: str,
        *,
        model: PerplexityModel | None = None,
        search_mode: PerplexitySearchMode = PerplexitySearchMode.WEB,
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """
        Stream research response in real-time.

        Yields content chunks as they are generated.

        Args:
            query: Research question
            model: Model to use
            search_mode: Type of search
            max_tokens: Maximum tokens
            temperature: Response randomness

        Yields:
            Content chunks as strings

        Note:
            This is a simplified streaming implementation.
            For full streaming with SSE, use the raw API.
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        use_model = model or self.default_model

        payload: dict[str, Any] = {
            "model": use_model.value,
            "messages": [{"role": "user", "content": query.strip()}],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if search_mode != PerplexitySearchMode.WEB:
            payload["web_search_options"] = {"search_mode": search_mode.value}

        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()

        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code >= 400:
                    # Read error response
                    error_body = await response.aread()
                    try:
                        error_data = response.json() if error_body else {}
                    except Exception:
                        error_data = {"raw": error_body.decode()}
                    raise PerplexityError(
                        message="Streaming failed",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data = line[6:]  # Remove "data: " prefix

                    if data == "[DONE]":
                        break

                    try:
                        import json

                        chunk = json.loads(data)
                        choices = chunk.get("choices", [])
                        if (
                            choices
                            and (delta := choices[0].get("delta", {}))
                            and (content := delta.get("content"))
                        ):
                            yield content
                    except Exception:
                        continue  # Skip malformed chunks

        except PerplexityError:
            raise
        except Exception as e:
            raise PerplexityError(
                message=f"Streaming failed: {e}",
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Perplexity API health and connectivity.

        Performs a minimal request to verify API connectivity.

        Returns:
            Dictionary with health status
        """
        try:
            # Simple query to check connectivity
            await self.research("test", max_tokens=10)
            return {
                "name": "perplexity",
                "healthy": True,
                "base_url": self.BASE_URL,
                "default_model": self.default_model.value,
            }
        except Exception as e:
            return {
                "name": "perplexity",
                "healthy": False,
                "error": str(e),
                "base_url": self.BASE_URL,
            }

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "POST",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Call any Perplexity API endpoint directly.

        Useful for new endpoints not yet wrapped by this client.

        Args:
            endpoint: API endpoint path (e.g., "/chat/completions")
            method: HTTP method (default POST)
            **kwargs: Additional arguments passed to the request

        Returns:
            Raw API response as dictionary

        Raises:
            PerplexityError: If request fails
        """
        try:
            return await self._request_with_retry(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
        except IntegrationError as e:
            raise PerplexityError(
                message=f"API call failed: {e.message}",
                status_code=e.status_code,
                response_data=e.response_data,
            ) from e

    def _parse_response(self, response: dict[str, Any]) -> PerplexityResponse:
        """
        Parse API response into PerplexityResponse.

        Args:
            response: Raw API response

        Returns:
            PerplexityResponse with parsed data
        """
        # Extract content from choices
        content = ""
        finish_reason = None
        choices = response.get("choices", [])
        if choices and (first_choice := choices[0]):
            if message := first_choice.get("message", {}):
                content = message.get("content", "")
            finish_reason = first_choice.get("finish_reason")

        # Parse citations from search_results
        citations: list[PerplexityCitation] = []
        for result in response.get("search_results", []):
            citations.append(
                PerplexityCitation(
                    url=result.get("url", ""),
                    title=result.get("title"),
                    date=result.get("date"),
                    snippet=result.get("snippet"),
                    raw=result,
                )
            )

        # Parse usage
        usage_data = response.get("usage", {})
        usage = PerplexityUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            citation_tokens=usage_data.get("citation_tokens", 0),
            num_search_queries=usage_data.get("num_search_queries", 0),
        )

        return PerplexityResponse(
            id=response.get("id", ""),
            model=response.get("model", ""),
            content=content,
            citations=citations,
            usage=usage,
            finish_reason=finish_reason,
            created=response.get("created", 0),
            raw_response=response,
        )
