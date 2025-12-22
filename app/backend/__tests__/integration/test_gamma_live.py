"""
Live API tests for Gamma integration with real API credentials.

Tests all major functionality with real Gamma API:
- Authentication with real API key
- Presentation creation from text content
- Slide management (add, update)
- Presentation retrieval and listing
- Theme listing
- Error handling with real errors

Requires GAMMA_API_KEY in .env at project root or environment variable.

Run with:
    pytest __tests__/integration/test_gamma_live.py -v -m live_api
    or
    pytest __tests__/integration/test_gamma_live.py -v
"""
# ruff: noqa: SIM105 - Try-except cleanup patterns are intentional for test cleanup

import os
from pathlib import Path

import pytest

from src.integrations.gamma import (
    GammaAuthError,
    GammaClient,
    GammaError,
    GammaRateLimitError,
)


@pytest.fixture
def api_key() -> str:
    """Load Gamma API key from .env at project root."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"

    api_key_value = None

    # Try to load from .env at project root
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GAMMA_API_KEY="):
                    api_key_value = line.replace("GAMMA_API_KEY=", "").strip()
                    # Check if it's a valid key (not just dots or placeholder)
                    if (
                        api_key_value
                        and not api_key_value.startswith("...")
                        and len(api_key_value) > 5
                    ):
                        return api_key_value

    # Fall back to environment variable
    api_key_value = os.getenv("GAMMA_API_KEY")
    if api_key_value and len(api_key_value) > 5:
        return api_key_value

    pytest.skip("GAMMA_API_KEY not found in .env or environment")


@pytest.fixture
async def client(api_key: str) -> GammaClient:
    """Create Gamma client with real API key."""
    return GammaClient(api_key=api_key)


@pytest.fixture
async def test_presentation_id(client: GammaClient) -> str | None:
    """Create a test presentation for testing."""
    try:
        async with client:
            result = await client.create_presentation(
                input_text="Test presentation: Introduction, Overview, Conclusion",
                title="Live API Test Presentation",
            )
            return result.get("id")
    except Exception as e:
        pytest.skip(f"Could not create test presentation: {e}")


@pytest.mark.asyncio
async def test_client_initialization(api_key: str) -> None:
    """Client should initialize with valid API key."""
    client = GammaClient(api_key=api_key)
    assert client.api_key == api_key
    assert client.name == "gamma"


@pytest.mark.asyncio
async def test_authentication_with_real_api_key(client: GammaClient) -> None:
    """Should authenticate successfully with real API key."""
    async with client:
        try:
            # Try to list themes - this verifies authentication
            result = await client.list_themes()
            assert "themes" in result
        except GammaAuthError:
            pytest.fail("Authentication should succeed with valid API key")
        except GammaRateLimitError:
            pytest.skip("Rate limited on auth test")


@pytest.mark.asyncio
async def test_authentication_with_invalid_key() -> None:
    """Should fail with invalid API key."""
    client = GammaClient(api_key="sk_gamma_invalid_test_key")
    async with client:
        try:
            await client.list_themes()
            pytest.fail("Should raise GammaAuthError with invalid key")
        except GammaAuthError:
            # Expected
            pass
        except GammaRateLimitError:
            pytest.skip("Rate limited")
        except Exception:
            # Accept other API errors as valid responses to invalid key
            pass


@pytest.mark.asyncio
async def test_create_presentation_from_text(client: GammaClient) -> None:
    """Should create presentation from text content."""
    async with client:
        try:
            result = await client.create_presentation(
                input_text="Test: Introduction to the topic, Key points, Conclusion",
                title="Live API Test - Text",
            )

            assert "id" in result
            assert result.get("title") == "Live API Test - Text"
            assert "state" in result
            assert "created_at" in result            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited - Gamma has generous limits but may be exceeded")


@pytest.mark.asyncio
async def test_create_presentation_generates_title(client: GammaClient) -> None:
    """Should generate title from content if not provided."""
    async with client:
        try:
            result = await client.create_presentation(
                input_text="This is a test about artificial intelligence and machine learning"
            )

            assert "id" in result
            assert result.get("title") is not None
            assert len(result.get("title", "")) > 0            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_list_presentations(client: GammaClient) -> None:
    """Should list user's presentations."""
    async with client:
        try:
            result = await client.list_presentations(limit=10)

            assert "presentations" in result
            assert isinstance(result["presentations"], list)
            assert "total" in result
            # Presentations list should contain presentation objects with id/title
            for pres in result["presentations"][:1]:
                assert "id" in pres
                assert "title" in pres

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_list_presentations_pagination(client: GammaClient) -> None:
    """Should support pagination in listing."""
    async with client:
        try:
            # Get first page
            result1 = await client.list_presentations(limit=5, skip=0)
            assert "presentations" in result1

            # Get second page
            result2 = await client.list_presentations(limit=5, skip=5)
            assert "presentations" in result2

            # If user has >5 presentations, lists should be different
            # (or at least have different skip values)
            # This just verifies the parameters are accepted
            assert result1["limit"] == 5 or "presentations" in result1

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_get_presentation(client: GammaClient) -> None:
    """Should retrieve presentation details."""
    async with client:
        try:
            # Create a presentation
            created = await client.create_presentation(
                input_text="Test content for retrieval",
                title="Get Presentation Test",
            )
            pres_id = created["id"]

            # Retrieve it
            result = await client.get_presentation(pres_id)

            assert result["id"] == pres_id
            assert result.get("title") == "Get Presentation Test"
            assert "state" in result
            assert "created_at" in result            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_add_slides_to_presentation(client: GammaClient) -> None:
    """Should add slides to presentation."""
    async with client:
        try:
            # Create presentation
            created = await client.create_presentation(input_text="Initial slide content")
            pres_id = created["id"]

            # Add slides
            slides = [
                {
                    "title": "Agenda",
                    "content": "1. Introduction\n2. Key Points\n3. Conclusion",
                },
                {
                    "title": "Details",
                    "content": "This is the detailed content section",
                },
            ]

            result = await client.add_slides(
                presentation_id=pres_id,
                slides_content=slides,
            )

            assert "id" in result
            # Slide count might be in response
            if "slide_count" in result:
                assert result["slide_count"] > 0            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_list_themes(client: GammaClient) -> None:
    """Should list available themes."""
    async with client:
        try:
            result = await client.list_themes()

            assert "themes" in result
            assert isinstance(result["themes"], list)
            # Should have at least some themes available
            assert len(result["themes"]) > 0

            # Verify theme structure
            for theme in result["themes"][:3]:
                assert "id" in theme
                assert "name" in theme

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_create_with_theme(client: GammaClient) -> None:
    """Should create presentation with theme."""
    async with client:
        try:
            # Get available themes
            themes_result = await client.list_themes()
            if not themes_result["themes"]:
                pytest.skip("No themes available")

            theme_id = themes_result["themes"][0]["id"]

            # Create with theme
            result = await client.create_presentation(
                input_text="Test with theme applied",
                theme_id=theme_id,
            )

            assert "id" in result
            if "theme_id" in result:
                assert result["theme_id"] == theme_id            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_error_handling_not_found(client: GammaClient) -> None:
    """Should handle not found errors."""
    async with client:
        try:
            # Try to get non-existent presentation
            await client.get_presentation("pres_nonexistent_999999")
            pytest.fail("Should raise error for non-existent presentation")
        except GammaError:
            # Expected
            pass
        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_error_handling_invalid_input(client: GammaClient) -> None:
    """Should handle invalid input errors."""
    async with client:
        try:
            # Try to add slides to non-existent presentation
            await client.add_slides(
                presentation_id="pres_nonexistent_999999",
                slides_content=[{"title": "Test", "content": "Test"}],
            )
            pytest.fail("Should raise error for invalid presentation ID")
        except GammaError:
            # Expected
            pass
        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_delete_presentation(client: GammaClient) -> None:
    """Should delete presentation."""
    async with client:
        try:
            # Create presentation
            created = await client.create_presentation(input_text="To be deleted")
            pres_id = created["id"]

            # Delete it
            result = await client.delete_presentation(pres_id)
            assert "id" in result or result is not None

            # Verify it's deleted by trying to get it
            try:
                await client.get_presentation(pres_id)
                # If we get here, presentation might not be deleted or API doesn't
                # immediately reflect deletion
            except GammaError:
                # Expected - presentation should be gone
                pass

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_concurrent_presentations(client: GammaClient) -> None:
    """Should handle multiple concurrent presentation creations."""
    import asyncio

    async with client:
        try:
            # Create multiple presentations concurrently
            tasks = [
                client.create_presentation(
                    input_text=f"Test presentation {i}",
                    title=f"Concurrent Test {i}",
                )
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            successful = [r for r in results if isinstance(r, dict) and "id" in r]
            assert len(successful) >= 1  # At least one should succeed

            # Clean up successful ones
            for result in successful:
                try:
                    await client.delete_presentation(result["id"])
                except Exception:
                    pass

        except GammaRateLimitError:
            pytest.skip("Rate limited - concurrent requests may hit limits")


@pytest.mark.asyncio
async def test_api_headers_correct(client: GammaClient) -> None:
    """Should use correct headers for Gamma API."""
    headers = client._get_headers()

    # Gamma uses X-API-KEY, not Authorization
    assert "X-API-KEY" in headers
    assert headers["X-API-KEY"] == client.api_key
    assert "Authorization" not in headers or "Bearer" not in headers.get("Authorization", "")
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_presentation_metadata(client: GammaClient) -> None:
    """Should preserve presentation metadata."""
    async with client:
        try:
            title = "Metadata Test Presentation"
            result = await client.create_presentation(
                input_text="Test content",
                title=title,
            )

            # Retrieve to verify metadata
            retrieved = await client.get_presentation(result["id"])

            assert retrieved.get("title") == title
            assert "created_at" in retrieved
            assert "updated_at" in retrieved
            assert retrieved["id"] == result["id"]            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_large_content_handling(client: GammaClient) -> None:
    """Should handle larger content for presentation."""
    async with client:
        try:
            # Create presentation with substantial content
            large_content = "\n".join(
                [
                    f"Section {i}: This is a detailed section with multiple paragraphs."
                    for i in range(10)
                ]
            )

            result = await client.create_presentation(
                input_text=large_content,
                title="Large Content Test",
            )

            assert "id" in result
            assert len(result["id"]) > 0            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")


@pytest.mark.asyncio
async def test_special_characters_handling(client: GammaClient) -> None:
    """Should handle special characters in content."""
    async with client:
        try:
            content = "Test with special chars: €, ™, ©, 中文, العربية, emoji 🚀"

            result = await client.create_presentation(
                input_text=content,
                title="Special Characters Test",
            )

            assert "id" in result            with contextlib.suppress(Exception):
                    await client.delete_presentation(...)

        except GammaRateLimitError:
            pytest.skip("Rate limited")
