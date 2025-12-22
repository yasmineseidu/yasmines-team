"""
Unit tests for Autobound integration client.

Tests cover:
- Client initialization and configuration
- Header generation
- Content generation methods (email, call script, LinkedIn, custom)
- Insights generation
- Error handling
- Input validation
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.integrations.autobound import (
    AutoboundAuthError,
    AutoboundClient,
    AutoboundContent,
    AutoboundContentType,
    AutoboundError,
    AutoboundInsight,
    AutoboundInsightsResult,
    AutoboundModel,
    AutoboundRateLimitError,
    AutoboundWritingStyle,
)


@pytest.fixture
def api_key() -> str:
    """Sample API key for testing."""
    return "test_api_key_12345"  # pragma: allowlist secret


@pytest.fixture
def client(api_key: str) -> AutoboundClient:
    """Create an Autobound client for testing."""
    return AutoboundClient(api_key=api_key)


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    mock = MagicMock(spec=httpx.AsyncClient)
    mock.is_closed = False
    return mock


@pytest.mark.asyncio
class TestAutoboundClientInitialization:
    """Tests for AutoboundClient initialization."""

    def test_default_timeout(self, api_key: str) -> None:
        """Should have 60 second default timeout for AI generation."""
        client = AutoboundClient(api_key=api_key)
        assert client.timeout == 60.0

    def test_custom_timeout(self, api_key: str) -> None:
        """Should accept custom timeout."""
        client = AutoboundClient(api_key=api_key, timeout=120.0)
        assert client.timeout == 120.0

    def test_default_max_retries(self, api_key: str) -> None:
        """Should have 3 default max retries."""
        client = AutoboundClient(api_key=api_key)
        assert client.max_retries == 3

    def test_custom_max_retries(self, api_key: str) -> None:
        """Should accept custom max retries."""
        client = AutoboundClient(api_key=api_key, max_retries=5)
        assert client.max_retries == 5

    def test_api_key_stored(self, api_key: str) -> None:
        """Should store API key."""
        client = AutoboundClient(api_key=api_key)
        assert client.api_key == api_key

    def test_base_url(self, client: AutoboundClient) -> None:
        """Should have correct base URL."""
        assert client.base_url == "https://api.autobound.ai/api/external"

    def test_name(self, client: AutoboundClient) -> None:
        """Should have correct name."""
        assert client.name == "autobound"


@pytest.mark.asyncio
class TestAutoboundClientHeaders:
    """Tests for header generation."""

    def test_get_headers_includes_api_key(self, client: AutoboundClient) -> None:
        """Should include X-API-KEY header."""
        headers = client._get_headers()
        assert headers["X-API-KEY"] == client.api_key

    def test_get_headers_includes_content_type(self, client: AutoboundClient) -> None:
        """Should include Content-Type header."""
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_includes_accept(self, client: AutoboundClient) -> None:
        """Should include Accept header."""
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
class TestAutoboundClientGenerateContent:
    """Tests for content generation methods."""

    async def test_generate_content_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should successfully generate content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Generated email content"}'
        mock_response.json.return_value = {"content": "Generated email content"}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_content(
            contact_email="prospect@company.com",
            user_email="sales@mycompany.com",
            content_type=AutoboundContentType.EMAIL,
        )

        assert isinstance(result, AutoboundContent)
        assert result.content == "Generated email content"
        assert result.contact_email == "prospect@company.com"
        assert result.content_type == "email"

    async def test_generate_content_empty_contact_email_raises(
        self, client: AutoboundClient
    ) -> None:
        """Should raise ValueError for empty contact email."""
        with pytest.raises(ValueError, match="contact_email is required"):
            await client.generate_content(
                contact_email="",
                user_email="sales@mycompany.com",
            )

    async def test_generate_content_empty_user_email_raises(self, client: AutoboundClient) -> None:
        """Should raise ValueError for empty user email."""
        with pytest.raises(ValueError, match="user_email is required"):
            await client.generate_content(
                contact_email="prospect@company.com",
                user_email="",
            )

    async def test_generate_content_with_writing_style(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should include writing style in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Executive pitch"}'
        mock_response.json.return_value = {"content": "Executive pitch"}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        await client.generate_content(
            contact_email="ceo@company.com",
            user_email="sales@mycompany.com",
            writing_style=AutoboundWritingStyle.CXO_PITCH,
        )

        # Verify request was made
        mock_http_client.request.assert_called_once()
        call_kwargs = mock_http_client.request.call_args[1]
        payload = call_kwargs["json"]
        assert payload["writingStyle"] == "cxo_pitch"

    async def test_generate_content_with_model(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should include model in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "GPT-4 generated content"}'
        mock_response.json.return_value = {"content": "GPT-4 generated content"}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        await client.generate_content(
            contact_email="prospect@company.com",
            user_email="sales@mycompany.com",
            model=AutoboundModel.GPT4O,
        )

        call_kwargs = mock_http_client.request.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "gpt4o"


@pytest.mark.asyncio
class TestAutoboundClientGenerateEmail:
    """Tests for email generation convenience method."""

    async def test_generate_email_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should generate email successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Hi John, I noticed..."}'
        mock_response.json.return_value = {"content": "Hi John, I noticed..."}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_email(
            contact_email="john@company.com",
            user_email="sales@mycompany.com",
        )

        assert isinstance(result, AutoboundContent)
        assert result.content_type == "email"

    async def test_generate_email_with_word_count(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should include word count in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Short email"}'
        mock_response.json.return_value = {"content": "Short email"}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        await client.generate_email(
            contact_email="prospect@company.com",
            user_email="sales@mycompany.com",
            word_count=50,
        )

        call_kwargs = mock_http_client.request.call_args[1]
        payload = call_kwargs["json"]
        assert payload["wordCount"] == "50"


@pytest.mark.asyncio
class TestAutoboundClientGenerateCallScript:
    """Tests for call script generation."""

    async def test_generate_call_script_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should generate call script successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Hi, is this John? Great..."}'
        mock_response.json.return_value = {"content": "Hi, is this John? Great..."}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_call_script(
            contact_email="john@company.com",
            user_email="sales@mycompany.com",
        )

        assert isinstance(result, AutoboundContent)
        assert result.content_type == "call script"


@pytest.mark.asyncio
class TestAutoboundClientGenerateLinkedIn:
    """Tests for LinkedIn message generation."""

    async def test_generate_linkedin_message_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should generate LinkedIn message successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Hi John, I saw your post..."}'
        mock_response.json.return_value = {"content": "Hi John, I saw your post..."}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_linkedin_message(
            contact_email="john@company.com",
            user_email="sales@mycompany.com",
        )

        assert isinstance(result, AutoboundContent)
        assert result.content_type == "LinkedIn connection request"


@pytest.mark.asyncio
class TestAutoboundClientGenerateCustomContent:
    """Tests for custom content generation."""

    async def test_generate_custom_content_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should generate custom content successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"content": "Custom analysis..."}'
        mock_response.json.return_value = {"content": "Custom analysis..."}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_custom_content(
            contact_email="prospect@company.com",
            user_email="sales@mycompany.com",
            custom_prompt="Write a pain point analysis for this prospect",
        )

        assert isinstance(result, AutoboundContent)
        assert result.content_type == "custom"

    async def test_generate_custom_content_empty_prompt_raises(
        self, client: AutoboundClient
    ) -> None:
        """Should raise ValueError for empty custom prompt."""
        with pytest.raises(ValueError, match="custom_prompt is required"):
            await client.generate_custom_content(
                contact_email="prospect@company.com",
                user_email="sales@mycompany.com",
                custom_prompt="",
            )


@pytest.mark.asyncio
class TestAutoboundClientGenerateInsights:
    """Tests for insights generation."""

    async def test_generate_insights_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should generate insights successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """{
            "insights": [
                {
                    "type": "news",
                    "title": "Company Funding",
                    "description": "Company raised $10M Series A",
                    "relevanceScore": 0.95
                }
            ]
        }"""
        mock_response.json.return_value = {
            "insights": [
                {
                    "type": "news",
                    "title": "Company Funding",
                    "description": "Company raised $10M Series A",
                    "relevanceScore": 0.95,
                }
            ]
        }
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.generate_insights(contact_email="ceo@startup.com")

        assert isinstance(result, AutoboundInsightsResult)
        assert len(result.insights) == 1
        assert isinstance(result.insights[0], AutoboundInsight)
        assert result.insights[0].type == "news"
        assert result.insights[0].title == "Company Funding"
        assert result.insights[0].relevance_score == 0.95

    async def test_generate_insights_empty_email_raises(self, client: AutoboundClient) -> None:
        """Should raise ValueError for empty contact email."""
        with pytest.raises(ValueError, match="contact_email is required"):
            await client.generate_insights(contact_email="")

    async def test_generate_insights_max_capped_at_25(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should cap max_insights at 25."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"insights": []}'
        mock_response.json.return_value = {"insights": []}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        await client.generate_insights(
            contact_email="prospect@company.com",
            max_insights=50,  # Over the limit
        )

        call_kwargs = mock_http_client.request.call_args[1]
        payload = call_kwargs["json"]
        assert payload["maxInsights"] == 25  # Should be capped


@pytest.mark.asyncio
class TestAutoboundClientErrorHandling:
    """Tests for error handling."""

    async def test_handle_response_401_raises_auth_error(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should raise AutoboundAuthError for 401 responses."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        with pytest.raises(AutoboundAuthError, match="Invalid API key"):
            await client.generate_email(
                contact_email="prospect@company.com",
                user_email="sales@mycompany.com",
            )

    async def test_handle_response_403_raises_auth_error(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should raise AutoboundAuthError for 403 responses."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        with pytest.raises(AutoboundAuthError, match="Access forbidden"):
            await client.generate_email(
                contact_email="prospect@company.com",
                user_email="sales@mycompany.com",
            )

    async def test_handle_response_429_raises_rate_limit_error(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should raise AutoboundRateLimitError for 429 responses."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        with pytest.raises(AutoboundRateLimitError, match="Rate limit exceeded"):
            await client.generate_email(
                contact_email="prospect@company.com",
                user_email="sales@mycompany.com",
            )

    async def test_handle_response_500_raises_error(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should raise AutoboundError for 500 responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        def mock_json() -> None:
            raise ValueError("Not JSON")

        mock_response.json = mock_json
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        with pytest.raises(AutoboundError, match="API error"):
            await client.generate_email(
                contact_email="prospect@company.com",
                user_email="sales@mycompany.com",
            )


@pytest.mark.asyncio
class TestAutoboundClientHealthCheck:
    """Tests for health check."""

    async def test_health_check_success(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should return healthy status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"insights": []}'
        mock_response.json.return_value = {"insights": []}
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.health_check()

        assert result["healthy"] is True
        assert result["name"] == "autobound"

    async def test_health_check_auth_failure(
        self, client: AutoboundClient, mock_http_client: MagicMock
    ) -> None:
        """Should return unhealthy status on auth failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_http_client.request = AsyncMock(return_value=mock_response)
        client._client = mock_http_client

        result = await client.health_check()

        assert result["healthy"] is False
        assert "error" in result


@pytest.mark.asyncio
class TestAutoboundEnums:
    """Tests for Autobound enums."""

    def test_content_type_values(self) -> None:
        """Should have correct content type values."""
        assert AutoboundContentType.EMAIL.value == "email"
        assert AutoboundContentType.EMAIL_SEQUENCE.value == "email sequence"
        assert AutoboundContentType.CALL_SCRIPT.value == "call script"
        assert AutoboundContentType.LINKEDIN_CONNECTION.value == "LinkedIn connection request"
        assert AutoboundContentType.SMS.value == "SMS"
        assert AutoboundContentType.OPENER.value == "opener"
        assert AutoboundContentType.CUSTOM.value == "custom"

    def test_writing_style_values(self) -> None:
        """Should have correct writing style values."""
        assert AutoboundWritingStyle.CXO_PITCH.value == "cxo_pitch"
        assert AutoboundWritingStyle.FRIENDLY.value == "friendly"
        assert AutoboundWritingStyle.PROFESSIONAL.value == "professional"

    def test_model_values(self) -> None:
        """Should have correct model values."""
        assert AutoboundModel.GPT4O.value == "gpt4o"
        assert AutoboundModel.GPT4.value == "gpt4"
        assert AutoboundModel.OPUS.value == "opus"
        assert AutoboundModel.SONNET.value == "sonnet"
        assert AutoboundModel.FINE_TUNED.value == "fine_tuned"


@pytest.mark.asyncio
class TestAutoboundDataclasses:
    """Tests for Autobound dataclasses."""

    def test_autobound_content_creation(self) -> None:
        """Should create AutoboundContent correctly."""
        content = AutoboundContent(
            content="Hello John, I noticed your recent post...",
            content_type="email",
            contact_email="john@company.com",
            model_used="gpt4o",
            insights_used=["news", "social_media"],
        )

        assert content.content == "Hello John, I noticed your recent post..."
        assert content.content_type == "email"
        assert content.contact_email == "john@company.com"
        assert content.model_used == "gpt4o"
        assert content.insights_used == ["news", "social_media"]

    def test_autobound_insight_creation(self) -> None:
        """Should create AutoboundInsight correctly."""
        insight = AutoboundInsight(
            type="news",
            title="Company Funding",
            description="Company raised $10M Series A",
            relevance_score=0.95,
            source="TechCrunch",
            date="2024-01-15",
        )

        assert insight.type == "news"
        assert insight.title == "Company Funding"
        assert insight.description == "Company raised $10M Series A"
        assert insight.relevance_score == 0.95
        assert insight.source == "TechCrunch"
        assert insight.date == "2024-01-15"

    def test_autobound_insights_result_creation(self) -> None:
        """Should create AutoboundInsightsResult correctly."""
        insights = [
            AutoboundInsight(type="news", title="Title", description="Desc"),
            AutoboundInsight(type="social", title="Title2", description="Desc2"),
        ]

        result = AutoboundInsightsResult(
            contact_email="prospect@company.com",
            insights=insights,
            total_count=2,
        )

        assert result.contact_email == "prospect@company.com"
        assert len(result.insights) == 2
        assert result.total_count == 2
