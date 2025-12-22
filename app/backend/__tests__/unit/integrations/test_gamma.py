"""Unit tests for Gamma API integration client.

Comprehensive test coverage for:
- Client initialization and configuration
- API request methods (GET, POST, PATCH, DELETE)
- Presentation creation (from text and templates)
- Slide management (add, update, retrieve)
- Theme management
- Error handling (auth, rate limits, API errors)
- Retry logic with exponential backoff
- Rate limit detection and handling
"""
# ruff: noqa: F841 - Unused variables in mock test return values are intentional

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.gamma import (
    GammaAuthError,
    GammaClient,
    GammaError,
    GammaPresentation,
    GammaRateLimitError,
    GammaSlide,
    GammaTheme,
)


class TestGammaClientInitialization:
    """Tests for GammaClient initialization."""

    def test_client_initializes_with_valid_api_key(self) -> None:
        """Client should initialize with valid API key."""
        client = GammaClient(api_key="sk_gamma_test_key_12345")  # pragma: allowlist secret
        assert client.api_key == "sk_gamma_test_key_12345"  # pragma: allowlist secret
        assert client.name == "gamma"
        assert client.base_url == "https://api.gamma.app/v1.0"

    def test_client_strips_whitespace_from_api_key(self) -> None:
        """Client should strip whitespace from API key."""
        client = GammaClient(api_key="  sk_gamma_test  ")  # pragma: allowlist secret
        assert client.api_key == "sk_gamma_test"  # pragma: allowlist secret

    def test_client_raises_on_empty_api_key(self) -> None:
        """Client should raise ValueError on empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            GammaClient(api_key="")

    def test_client_raises_on_whitespace_only_api_key(self) -> None:
        """Client should raise ValueError on whitespace-only API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            GammaClient(api_key="   ")

    def test_client_initializes_with_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = GammaClient(api_key="sk_gamma_test", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_initializes_with_retry_settings(self) -> None:
        """Client should accept custom retry settings."""
        client = GammaClient(
            api_key="sk_gamma_test",
            max_retries=5,
            retry_base_delay=2.0,
        )
        assert client.max_retries == 5
        assert client.retry_base_delay == 2.0

    def test_get_headers_uses_x_api_key(self) -> None:
        """Headers should use X-API-KEY instead of Authorization."""
        client = GammaClient(api_key="sk_gamma_test_key")
        headers = client._get_headers()
        assert headers["X-API-KEY"] == "sk_gamma_test_key"
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestCreatePresentation:
    """Tests for presentation creation."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_create_presentation_with_text(self, client: GammaClient) -> None:
        """Should create presentation from text content."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "pres_123",
                "title": "Generated Presentation",
                "state": "draft",
                "created_at": 1672531200,
                "updated_at": 1672531200,
                "url": "https://gamma.app/pres_123",
            }

            result = await client.create_presentation(
                input_text="Meeting notes: Q4 goals, timeline, budget"
            )

            assert result["id"] == "pres_123"
            assert result["title"] == "Generated Presentation"
            assert result["state"] == "draft"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_presentation_with_theme(self, client: GammaClient) -> None:
        """Should create presentation with specified theme."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "pres_456", "theme_id": "theme_modern"}

            await client.create_presentation(
                input_text="Content",
                theme_id="theme_modern",
            )

            # Verify theme_id was passed in payload
            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get("json", {})
            assert json_payload.get("themeId") == "theme_modern"

    @pytest.mark.asyncio
    async def test_create_presentation_with_title(self, client: GammaClient) -> None:
        """Should create presentation with specified title."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "pres_789", "title": "Custom Title"}

            await client.create_presentation(
                input_text="Content",
                title="Custom Title",
            )

            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get("json", {})
            assert json_payload.get("title") == "Custom Title"

    @pytest.mark.asyncio
    async def test_create_presentation_with_different_types(self, client: GammaClient) -> None:
        """Should support different presentation types."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "pres_doc", "type": "document"}

            for content_type in ["slides", "document", "webpage", "social"]:
                await client.create_presentation(
                    input_text="Content",
                    presentation_type=content_type,
                )

                call_args = mock_post.call_args
                json_payload = call_args.kwargs.get("json", {})
                assert json_payload.get("outputFormat") == content_type

    @pytest.mark.asyncio
    async def test_create_presentation_handles_error(self, client: GammaClient) -> None:
        """Should handle errors when creating presentation."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = GammaError("API error")

            with pytest.raises(GammaError):
                await client.create_presentation(input_text="Content")


class TestCreateFromTemplate:
    """Tests for template-based presentation creation."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_create_from_template(self, client: GammaClient) -> None:
        """Should create presentation from template."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "pres_template", "template_id": "tmpl_123"}

            result = await client.create_presentation_from_template(
                template_id="tmpl_123",
                title="Sales Deck",
                content={"sections": ["Intro", "Product", "Pricing", "CTA"]},
            )

            assert result["id"] == "pres_template"
            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get("json", {})
            assert json_payload.get("templateId") == "tmpl_123"
            assert json_payload.get("title") == "Sales Deck"


class TestSlideManagement:
    """Tests for slide operations."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_add_slides_to_presentation(self, client: GammaClient) -> None:
        """Should add slides to presentation."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "pres_123",
                "slide_count": 3,
            }

            slides = [
                {"title": "Agenda", "content": "• Goal 1\n• Goal 2\n• Goal 3"},
                {"title": "Timeline", "content": "Q1 2024 - Project start"},
            ]

            result = await client.add_slides(
                presentation_id="pres_123",
                slides_content=slides,
            )

            assert result["slide_count"] == 3
            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get("json", {})
            assert len(json_payload.get("slides", [])) == 2

    @pytest.mark.asyncio
    async def test_add_slides_with_speaker_notes(self, client: GammaClient) -> None:
        """Should add slides with speaker notes."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "pres_123"}

            slides = [
                {
                    "title": "Introduction",
                    "content": "Welcome",
                    "notes": "Start with a friendly greeting",
                }
            ]

            await client.add_slides(
                presentation_id="pres_123",
                slides_content=slides,
            )

            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get("json", {})
            slide = json_payload.get("slides", [])[0]
            assert slide.get("notes") == "Start with a friendly greeting"

    @pytest.mark.asyncio
    async def test_update_slide(self, client: GammaClient) -> None:
        """Should update existing slide."""
        with patch.object(client, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = {
                "id": "pres_123",
                "slide_index": 0,
                "title": "Updated Title",
            }

            result = await client.update_slide(
                presentation_id="pres_123",
                slide_index=0,
                title="Updated Title",
            )

            assert result["title"] == "Updated Title"
            call_args = mock_patch.call_args
            assert "/slides/0" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_update_slide_partial(self, client: GammaClient) -> None:
        """Should update slide with partial fields."""
        with patch.object(client, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = {"id": "pres_123"}

            # Update only content
            await client.update_slide(
                presentation_id="pres_123",
                slide_index=1,
                content="New content",
            )

            call_args = mock_patch.call_args
            json_payload = call_args.kwargs.get("json", {})
            assert "content" in json_payload
            assert "title" not in json_payload

    @pytest.mark.asyncio
    async def test_update_slide_requires_at_least_one_field(self, client: GammaClient) -> None:
        """Should require at least one field to update."""
        with pytest.raises(ValueError, match="At least one of"):
            await client.update_slide(
                presentation_id="pres_123",
                slide_index=0,
            )


class TestPresentationRetrieval:
    """Tests for retrieving presentation data."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_get_presentation(self, client: GammaClient) -> None:
        """Should retrieve presentation details."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "pres_123",
                "title": "Q4 Planning",
                "state": "draft",
                "slide_count": 5,
                "created_at": 1672531200,
                "updated_at": 1672531200,
                "url": "https://gamma.app/pres_123",
            }

            result = await client.get_presentation("pres_123")

            assert result["id"] == "pres_123"
            assert result["title"] == "Q4 Planning"
            assert result["slide_count"] == 5
            mock_get.assert_called_once_with("/presentations/pres_123")

    @pytest.mark.asyncio
    async def test_list_presentations(self, client: GammaClient) -> None:
        """Should list user's presentations."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "presentations": [
                    {"id": "pres_1", "title": "Presentation 1"},
                    {"id": "pres_2", "title": "Presentation 2"},
                ],
                "total": 10,
                "limit": 2,
                "skip": 0,
            }

            result = await client.list_presentations(limit=2, skip=0)

            assert len(result["presentations"]) == 2
            assert result["total"] == 10
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_presentations_with_pagination(self, client: GammaClient) -> None:
        """Should support pagination in listing."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"presentations": [], "total": 100}

            await client.list_presentations(limit=50, skip=50)

            call_args = mock_get.call_args
            params = call_args.kwargs.get("params", {})
            assert params["limit"] == 50
            assert params["skip"] == 50


class TestThemeManagement:
    """Tests for theme operations."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_list_themes(self, client: GammaClient) -> None:
        """Should list available themes."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "themes": [
                    {"id": "theme_modern", "name": "Modern", "description": "Clean design"},
                    {"id": "theme_classic", "name": "Classic", "description": "Traditional"},
                ],
                "total": 2,
            }

            result = await client.list_themes()

            assert len(result["themes"]) == 2
            assert result["themes"][0]["id"] == "theme_modern"
            mock_get.assert_called_once_with("/themes")


class TestPresentationDeletion:
    """Tests for presentation deletion."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_delete_presentation(self, client: GammaClient) -> None:
        """Should delete presentation."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"id": "pres_123", "deleted": True}

            result = await client.delete_presentation("pres_123")

            assert result["deleted"] is True
            mock_delete.assert_called_once_with("/presentations/pres_123")


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client."""
        return GammaClient(api_key="sk_gamma_test")

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self, client: GammaClient) -> None:
        """Should raise GammaAuthError on 401."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GammaAuthError("Invalid API key")

            with pytest.raises(GammaAuthError):
                await client.get("/presentations")

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, client: GammaClient) -> None:
        """Should raise GammaRateLimitError on 429."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GammaRateLimitError("Rate limit exceeded", retry_after=60)

            with pytest.raises(GammaRateLimitError):
                await client.get("/presentations")

    @pytest.mark.asyncio
    async def test_handles_generic_error(self, client: GammaClient) -> None:
        """Should raise GammaError for other errors."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GammaError("Unknown error")

            with pytest.raises(GammaError):
                await client.get("/presentations")


class TestRetryLogic:
    """Tests for retry logic with exponential backoff."""

    @pytest.fixture
    def client(self) -> GammaClient:
        """Create a test client with max 2 retries for faster testing."""
        return GammaClient(api_key="sk_gamma_test", max_retries=2)

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self, client: GammaClient) -> None:
        """Should retry on 5xx errors."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            # Fail twice, succeed on third
            mock_request.side_effect = [
                GammaError("Server error", status_code=500),
                GammaError("Server error", status_code=503),
                {"id": "pres_123"},
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._request_with_retry("GET", "/presentations")

            assert result["id"] == "pres_123"
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_auth_error(self, client: GammaClient) -> None:
        """Should not retry authentication errors."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GammaAuthError("Invalid API key")

            with pytest.raises(GammaAuthError):
                await client._request_with_retry("GET", "/presentations")

            # Should only call once, no retries
            assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_does_not_retry_client_error(self, client: GammaClient) -> None:
        """Should not retry 4xx client errors."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GammaError("Not found", status_code=404)

            with pytest.raises(GammaError):
                await client._request_with_retry("GET", "/presentations")

            # Should only call once, no retries
            assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_rate_limit_with_jitter(self, client: GammaClient) -> None:
        """Should retry rate limit with backoff and jitter."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                GammaRateLimitError("Rate limited", retry_after=60),
                {"id": "pres_123"},
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._request_with_retry("GET", "/presentations")

            assert result["id"] == "pres_123"
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, client: GammaClient) -> None:
        """Should raise error when max retries exhausted."""
        with (
            patch.object(client, "_request", new_callable=AsyncMock) as mock_request,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_request.side_effect = GammaError("Server error", status_code=500)

            with pytest.raises(GammaError, match="All retry attempts failed"):
                await client._request_with_retry("GET", "/presentations")

            # Should retry: initial + 2 retries + 1 final = attempt count
            assert mock_request.call_count == 3


class TestDataModels:
    """Tests for data model classes."""

    def test_gamma_presentation_dataclass(self) -> None:
        """Should create GammaPresentation instance."""
        pres = GammaPresentation(
            id="pres_123",
            title="Q4 Planning",
            state="draft",
            updated_at=1672531200,
            created_at=1672531200,
            slide_count=5,
            theme_id="theme_modern",
        )

        assert pres.id == "pres_123"
        assert pres.title == "Q4 Planning"
        assert pres.slide_count == 5

    def test_gamma_slide_dataclass(self) -> None:
        """Should create GammaSlide instance."""
        slide = GammaSlide(
            id="slide_1",
            title="Agenda",
            content="• Goal 1\n• Goal 2",
            slide_number=0,
            notes="Start with agenda",
        )

        assert slide.id == "slide_1"
        assert slide.title == "Agenda"
        assert slide.slide_number == 0

    def test_gamma_theme_dataclass(self) -> None:
        """Should create GammaTheme instance."""
        theme = GammaTheme(
            id="theme_modern",
            name="Modern",
            description="Clean and minimal design",
        )

        assert theme.id == "theme_modern"
        assert theme.name == "Modern"
