"""Unit tests for Perplexity AI integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.base import IntegrationError, RateLimitError
from src.integrations.perplexity import (
    PerplexityCitation,
    PerplexityClient,
    PerplexityConversation,
    PerplexityError,
    PerplexityMessage,
    PerplexityModel,
    PerplexityResponse,
    PerplexitySearchMode,
    PerplexityUsage,
)


class TestPerplexityClientInitialization:
    """Tests for PerplexityClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have perplexity name."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret
        assert client.name == "perplexity"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret
        assert client.base_url == "https://api.perplexity.ai"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        api_key = "pplx-test-key-123"  # pragma: allowlist secret
        client = PerplexityClient(api_key=api_key)
        assert client.api_key == api_key

    def test_has_default_timeout(self) -> None:
        """Client should have default timeout of 60s for research."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_has_default_max_retries(self) -> None:
        """Client should have default max retries."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_has_default_model(self) -> None:
        """Client should have sonar as default model."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret
        assert client.default_model == PerplexityModel.SONAR

    def test_can_customize_timeout(self) -> None:
        """Client should allow custom timeout."""
        client = PerplexityClient(
            api_key="pplx-test",  # pragma: allowlist secret
            timeout=120.0,
        )
        assert client.timeout == 120.0

    def test_can_customize_default_model(self) -> None:
        """Client should allow custom default model."""
        client = PerplexityClient(
            api_key="pplx-test",  # pragma: allowlist secret
            default_model=PerplexityModel.SONAR_PRO,
        )
        assert client.default_model == PerplexityModel.SONAR_PRO


class TestPerplexityClientResearch:
    """Tests for PerplexityClient.research()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.fixture
    def mock_response(self) -> dict:
        """Mock API response."""
        return {
            "id": "chatcmpl-123",
            "model": "sonar",
            "created": 1234567890,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Top SaaS pricing models include...",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 200,
                "total_tokens": 250,
                "citation_tokens": 30,
                "num_search_queries": 3,
            },
            "search_results": [
                {
                    "url": "https://example.com/saas-pricing",
                    "title": "SaaS Pricing Guide",
                    "date": "2024-12-15",
                    "snippet": "Learn about pricing models...",
                },
                {
                    "url": "https://example.com/pricing-strategies",
                    "title": "Pricing Strategies for SaaS",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_research_returns_response(
        self, client: PerplexityClient, mock_response: dict
    ) -> None:
        """research() should return parsed response."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.research("What are top SaaS pricing models?")

            assert isinstance(result, PerplexityResponse)
            assert result.id == "chatcmpl-123"
            assert result.model == "sonar"
            assert result.content == "Top SaaS pricing models include..."
            assert result.finish_reason == "stop"
            assert len(result.citations) == 2
            assert result.citations[0].url == "https://example.com/saas-pricing"
            assert result.citations[0].title == "SaaS Pricing Guide"

    @pytest.mark.asyncio
    async def test_research_sends_correct_payload(self, client: PerplexityClient) -> None:
        """research() should send correct request payload."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research(
                "test query",
                model=PerplexityModel.SONAR_PRO,
                max_tokens=500,
                temperature=0.5,
            )

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs["json"]

            assert payload["model"] == "sonar-pro"
            assert payload["temperature"] == 0.5
            assert payload["max_tokens"] == 500
            assert len(payload["messages"]) == 1
            assert payload["messages"][0]["role"] == "user"
            assert payload["messages"][0]["content"] == "test query"

    @pytest.mark.asyncio
    async def test_research_with_search_mode(self, client: PerplexityClient) -> None:
        """research() should handle search mode."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research("test", search_mode=PerplexitySearchMode.ACADEMIC)

            payload = mock_post.call_args.kwargs["json"]
            assert payload["web_search_options"]["search_mode"] == "academic"

    @pytest.mark.asyncio
    async def test_research_with_recency_filter(self, client: PerplexityClient) -> None:
        """research() should handle recency filter."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research("test", search_recency_filter="month")

            payload = mock_post.call_args.kwargs["json"]
            assert payload["web_search_options"]["search_recency_filter"] == "month"

    @pytest.mark.asyncio
    async def test_research_with_date_filter(self, client: PerplexityClient) -> None:
        """research() should handle date filter."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research("test", search_after_date="12/01/2024")

            payload = mock_post.call_args.kwargs["json"]
            assert payload["web_search_options"]["search_after_date_filter"] == "12/01/2024"

    @pytest.mark.asyncio
    async def test_research_with_response_language(self, client: PerplexityClient) -> None:
        """research() should handle response language (sonar models)."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research(
                "test",
                model=PerplexityModel.SONAR,
                response_language="Spanish",
            )

            payload = mock_post.call_args.kwargs["json"]
            assert payload["response_language"] == "Spanish"

    @pytest.mark.asyncio
    async def test_research_validates_empty_query(self, client: PerplexityClient) -> None:
        """research() should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.research("")

    @pytest.mark.asyncio
    async def test_research_validates_whitespace_query(self, client: PerplexityClient) -> None:
        """research() should raise ValueError for whitespace-only query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.research("   ")

    @pytest.mark.asyncio
    async def test_research_raises_perplexity_error_on_failure(
        self, client: PerplexityClient
    ) -> None:
        """research() should raise PerplexityError on API failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(PerplexityError, match="Chat completion failed"):
                await client.research("test")


class TestPerplexityClientChat:
    """Tests for PerplexityClient.chat()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.fixture
    def mock_response(self) -> dict:
        """Mock API response."""
        return {
            "id": "chatcmpl-456",
            "model": "sonar",
            "created": 1234567890,
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Response content"},
                    "finish_reason": "stop",
                }
            ],
            "search_results": [],
        }

    @pytest.mark.asyncio
    async def test_chat_returns_response(
        self, client: PerplexityClient, mock_response: dict
    ) -> None:
        """chat() should return parsed response."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.chat("Hello")

            assert isinstance(result, PerplexityResponse)
            assert result.content == "Response content"

    @pytest.mark.asyncio
    async def test_chat_with_conversation(
        self, client: PerplexityClient, mock_response: dict
    ) -> None:
        """chat() should include conversation context."""
        conv = PerplexityConversation(system_prompt="You are a helpful assistant.")
        conv.add_user_message("First question")
        conv.add_assistant_message("First answer")

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.chat("Second question", conversation=conv)

            payload = mock_post.call_args.kwargs["json"]
            messages = payload["messages"]

            assert len(messages) == 4  # system + 2 previous + new
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "First question"
            assert messages[2]["role"] == "assistant"
            assert messages[3]["role"] == "user"
            assert messages[3]["content"] == "Second question"

    @pytest.mark.asyncio
    async def test_chat_updates_conversation(
        self, client: PerplexityClient, mock_response: dict
    ) -> None:
        """chat() should add assistant response to conversation."""
        conv = PerplexityConversation()

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.chat("Hello", conversation=conv)

            assert len(conv.messages) == 2
            assert conv.messages[0].role == "user"
            assert conv.messages[0].content == "Hello"
            assert conv.messages[1].role == "assistant"
            assert conv.messages[1].content == "Response content"

    @pytest.mark.asyncio
    async def test_chat_with_search_disabled(
        self, client: PerplexityClient, mock_response: dict
    ) -> None:
        """chat() should handle search_disabled option."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.chat("test", search_disabled=True)

            payload = mock_post.call_args.kwargs["json"]
            assert payload["search_disabled"] is True

    @pytest.mark.asyncio
    async def test_chat_validates_empty_message(self, client: PerplexityClient) -> None:
        """chat() should raise ValueError for empty message."""
        with pytest.raises(ValueError, match="message is required"):
            await client.chat("")


class TestPerplexityClientResearchWithSystemPrompt:
    """Tests for PerplexityClient.research_with_system_prompt()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_research_with_system_prompt_sends_messages(
        self, client: PerplexityClient
    ) -> None:
        """research_with_system_prompt() should include system message."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.research_with_system_prompt(
                "What is Python?",
                "You are a programming expert.",
            )

            payload = mock_post.call_args.kwargs["json"]
            messages = payload["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a programming expert."
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "What is Python?"

    @pytest.mark.asyncio
    async def test_research_with_system_prompt_validates_query(
        self, client: PerplexityClient
    ) -> None:
        """research_with_system_prompt() should validate query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.research_with_system_prompt("", "system prompt")

    @pytest.mark.asyncio
    async def test_research_with_system_prompt_validates_prompt(
        self, client: PerplexityClient
    ) -> None:
        """research_with_system_prompt() should validate system_prompt."""
        with pytest.raises(ValueError, match="system_prompt is required"):
            await client.research_with_system_prompt("query", "")


class TestPerplexityClientAcademicSearch:
    """Tests for PerplexityClient.academic_search()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_academic_search_uses_academic_mode(self, client: PerplexityClient) -> None:
        """academic_search() should use academic search mode."""
        with patch.object(client, "research", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = PerplexityResponse(
                id="test", model="sonar", content="", citations=[]
            )

            await client.academic_search("machine learning research")

            mock_research.assert_called_once()
            call_kwargs = mock_research.call_args.kwargs
            assert call_kwargs["search_mode"] == PerplexitySearchMode.ACADEMIC
            assert call_kwargs["temperature"] == 0.1


class TestPerplexityClientFinancialResearch:
    """Tests for PerplexityClient.financial_research()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_financial_research_uses_sec_mode(self, client: PerplexityClient) -> None:
        """financial_research() should use SEC search mode."""
        with patch.object(client, "research", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = PerplexityResponse(
                id="test", model="sonar", content="", citations=[]
            )

            await client.financial_research("Apple quarterly earnings")

            mock_research.assert_called_once()
            call_kwargs = mock_research.call_args.kwargs
            assert call_kwargs["search_mode"] == PerplexitySearchMode.SEC
            assert call_kwargs["temperature"] == 0.1


class TestPerplexityClientDeepResearch:
    """Tests for PerplexityClient.deep_research()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_deep_research_uses_deep_model(self, client: PerplexityClient) -> None:
        """deep_research() should use sonar-deep-research model."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.deep_research("comprehensive AI analysis")

            payload = mock_post.call_args.kwargs["json"]
            assert payload["model"] == "sonar-deep-research"
            assert payload["reasoning_effort"] == "medium"

    @pytest.mark.asyncio
    async def test_deep_research_with_reasoning_effort(self, client: PerplexityClient) -> None:
        """deep_research() should accept reasoning_effort."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": ""}}]}

            await client.deep_research("test", reasoning_effort="high")

            payload = mock_post.call_args.kwargs["json"]
            assert payload["reasoning_effort"] == "high"

    @pytest.mark.asyncio
    async def test_deep_research_validates_reasoning_effort(self, client: PerplexityClient) -> None:
        """deep_research() should validate reasoning_effort."""
        with pytest.raises(ValueError, match="reasoning_effort must be"):
            await client.deep_research("test", reasoning_effort="invalid")


class TestPerplexityClientHealthCheck:
    """Tests for PerplexityClient.health_check()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: PerplexityClient) -> None:
        """health_check() should return healthy status on success."""
        with patch.object(client, "research", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = PerplexityResponse(
                id="test", model="sonar", content="", citations=[]
            )

            result = await client.health_check()

            assert result["name"] == "perplexity"
            assert result["healthy"] is True
            assert result["base_url"] == "https://api.perplexity.ai"
            assert result["default_model"] == "sonar"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: PerplexityClient) -> None:
        """health_check() should return unhealthy status on failure."""
        with patch.object(client, "research", new_callable=AsyncMock) as mock_research:
            mock_research.side_effect = PerplexityError("Connection failed")

            result = await client.health_check()

            assert result["name"] == "perplexity"
            assert result["healthy"] is False
            assert "error" in result


class TestPerplexityClientCallEndpoint:
    """Tests for PerplexityClient.call_endpoint()."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: PerplexityClient) -> None:
        """call_endpoint() should call endpoint directly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"result": "success"}

            result = await client.call_endpoint("/custom", method="GET")

            assert result == {"result": "success"}
            mock_request.assert_called_once_with(method="GET", endpoint="/custom")

    @pytest.mark.asyncio
    async def test_call_endpoint_raises_perplexity_error(self, client: PerplexityClient) -> None:
        """call_endpoint() should raise PerplexityError on failure."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(PerplexityError, match="API call failed"):
                await client.call_endpoint("/custom")


class TestPerplexityConversation:
    """Tests for PerplexityConversation."""

    def test_conversation_initialization(self) -> None:
        """Conversation should initialize with empty messages."""
        conv = PerplexityConversation()
        assert conv.messages == []
        assert conv.system_prompt is None

    def test_conversation_with_system_prompt(self) -> None:
        """Conversation should store system prompt."""
        conv = PerplexityConversation(system_prompt="You are helpful.")
        assert conv.system_prompt == "You are helpful."

    def test_add_user_message(self) -> None:
        """add_user_message() should add user message."""
        conv = PerplexityConversation()
        conv.add_user_message("Hello")

        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"

    def test_add_assistant_message(self) -> None:
        """add_assistant_message() should add assistant message."""
        conv = PerplexityConversation()
        conv.add_assistant_message("Hi there!")

        assert len(conv.messages) == 1
        assert conv.messages[0].role == "assistant"
        assert conv.messages[0].content == "Hi there!"

    def test_to_api_messages_without_system(self) -> None:
        """to_api_messages() should return messages without system prompt."""
        conv = PerplexityConversation()
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi")

        messages = conv.to_api_messages()

        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi"}

    def test_to_api_messages_with_system(self) -> None:
        """to_api_messages() should include system prompt first."""
        conv = PerplexityConversation(system_prompt="Be helpful")
        conv.add_user_message("Hello")

        messages = conv.to_api_messages()

        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "Be helpful"}
        assert messages[1] == {"role": "user", "content": "Hello"}

    def test_clear_conversation(self) -> None:
        """clear() should empty messages list."""
        conv = PerplexityConversation()
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi")

        conv.clear()

        assert conv.messages == []


class TestPerplexityDataClasses:
    """Tests for Perplexity dataclasses."""

    def test_perplexity_citation_creation(self) -> None:
        """PerplexityCitation should be created correctly."""
        citation = PerplexityCitation(
            url="https://example.com/article",
            title="Article Title",
            date="2024-12-15",
            snippet="Article excerpt...",
        )

        assert citation.url == "https://example.com/article"
        assert citation.title == "Article Title"
        assert citation.date == "2024-12-15"
        assert citation.snippet == "Article excerpt..."

    def test_perplexity_usage_defaults(self) -> None:
        """PerplexityUsage should have correct defaults."""
        usage = PerplexityUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.citation_tokens == 0
        assert usage.num_search_queries == 0

    def test_perplexity_message_creation(self) -> None:
        """PerplexityMessage should be created correctly."""
        msg = PerplexityMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_perplexity_response_creation(self) -> None:
        """PerplexityResponse should be created correctly."""
        response = PerplexityResponse(
            id="resp-123",
            model="sonar-pro",
            content="Answer content",
            citations=[PerplexityCitation(url="https://example.com")],
            finish_reason="stop",
            created=1234567890,
        )

        assert response.id == "resp-123"
        assert response.model == "sonar-pro"
        assert response.content == "Answer content"
        assert len(response.citations) == 1
        assert response.finish_reason == "stop"
        assert response.created == 1234567890


class TestPerplexityModelEnum:
    """Tests for PerplexityModel enum."""

    def test_model_values(self) -> None:
        """PerplexityModel should have correct values."""
        assert PerplexityModel.SONAR.value == "sonar"
        assert PerplexityModel.SONAR_PRO.value == "sonar-pro"
        assert PerplexityModel.SONAR_REASONING_PRO.value == "sonar-reasoning-pro"
        assert PerplexityModel.SONAR_DEEP_RESEARCH.value == "sonar-deep-research"


class TestPerplexitySearchModeEnum:
    """Tests for PerplexitySearchMode enum."""

    def test_search_mode_values(self) -> None:
        """PerplexitySearchMode should have correct values."""
        assert PerplexitySearchMode.WEB.value == "web"
        assert PerplexitySearchMode.ACADEMIC.value == "academic"
        assert PerplexitySearchMode.SEC.value == "sec"


class TestPerplexityClientResponseParsing:
    """Tests for response parsing edge cases."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_parses_response_without_citations(self, client: PerplexityClient) -> None:
        """Should handle response without search_results."""
        response = {
            "id": "resp-123",
            "model": "sonar",
            "choices": [{"message": {"content": "Answer"}, "finish_reason": "stop"}],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = response

            result = await client.research("test")

            assert result.content == "Answer"
            assert result.citations == []

    @pytest.mark.asyncio
    async def test_parses_response_without_usage(self, client: PerplexityClient) -> None:
        """Should handle response without usage stats."""
        response = {
            "id": "resp-123",
            "model": "sonar",
            "choices": [{"message": {"content": "Answer"}}],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = response

            result = await client.research("test")

            assert result.usage.total_tokens == 0

    @pytest.mark.asyncio
    async def test_parses_empty_choices(self, client: PerplexityClient) -> None:
        """Should handle response with empty choices."""
        response = {
            "id": "resp-123",
            "model": "sonar",
            "choices": [],
        }

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = response

            result = await client.research("test")

            assert result.content == ""


class TestPerplexityClientContextManager:
    """Tests for PerplexityClient context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Context manager should close client on exit."""
        client = PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass

            mock_close.assert_called_once()


class TestPerplexityClientErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def client(self) -> PerplexityClient:
        """Create PerplexityClient instance."""
        return PerplexityClient(api_key="pplx-test")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, client: PerplexityClient) -> None:
        """Should propagate rate limit errors."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RateLimitError("Rate limit exceeded", retry_after=60)

            with pytest.raises(PerplexityError, match="Chat completion failed"):
                await client.research("test")

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self, client: PerplexityClient) -> None:
        """Should propagate authentication errors."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = IntegrationError("Invalid API key", status_code=401)

            with pytest.raises(PerplexityError):
                await client.research("test")
