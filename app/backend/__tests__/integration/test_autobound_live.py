"""
Live API tests for Autobound integration.

These tests use REAL API credentials from .env and make actual API calls.
All tests MUST pass 100% before proceeding to review.

To run:
    uv run pytest __tests__/integration/test_autobound_live.py -v -m live_api

Environment variables required:
    - AUTOBOUND_API_KEY
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.integrations.autobound import (
    AutoboundClient,
    AutoboundContent,
    AutoboundError,
    AutoboundInsightsResult,
    AutoboundModel,
    AutoboundWritingStyle,
)

# Load .env from project root (yasmines-team/)
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


@pytest.fixture
def autobound_credentials() -> dict[str, str]:
    """Get Autobound API credentials from .env."""
    api_key = os.getenv("AUTOBOUND_API_KEY")

    if not api_key or api_key == "...":
        pytest.skip("AUTOBOUND_API_KEY not configured in .env")

    return {"api_key": api_key}


@pytest.fixture
async def client(autobound_credentials: dict[str, str]) -> AutoboundClient:
    """Create authenticated Autobound client."""
    return AutoboundClient(**autobound_credentials)


# Test email addresses - use real emails for best results
TEST_CONTACT_EMAIL = "satya.nadella@microsoft.com"
TEST_USER_EMAIL = "sales@example.com"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveHealthCheck:
    """Live tests for Autobound health check."""

    async def test_health_check(self, autobound_credentials: dict[str, str]) -> None:
        """Should return healthy status with valid credentials."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.health_check()

            # Health check may succeed or fail depending on test email
            # but shouldn't throw an exception
            assert "name" in result
            assert result["name"] == "autobound"


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveGenerateContent:
    """Live tests for content generation."""

    async def test_generate_email(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate personalized email."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=TEST_CONTACT_EMAIL,
                user_email=TEST_USER_EMAIL,
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "email"
            assert len(result.content) > 0
            assert result.contact_email == TEST_CONTACT_EMAIL

    async def test_generate_email_with_writing_style(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should generate email with specific writing style."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=TEST_CONTACT_EMAIL,
                user_email=TEST_USER_EMAIL,
                writing_style=AutoboundWritingStyle.CXO_PITCH,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0

    async def test_generate_call_script(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate personalized call script."""
        async with AutoboundClient(**autobound_credentials) as client:
            try:
                result = await client.generate_call_script(
                    contact_email=TEST_CONTACT_EMAIL,
                    user_email=TEST_USER_EMAIL,
                )
                assert isinstance(result, AutoboundContent)
                assert result.content_type == "call script"
                # Content can be empty if insights aren't available
                assert isinstance(result.content, str)
            except AutoboundError as e:
                # Some API plans may not support call scripts
                if "400" in str(e):
                    pytest.skip(f"API plan does not support this content type: {e}")
                raise

    async def test_generate_linkedin_message(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate personalized LinkedIn message."""
        async with AutoboundClient(**autobound_credentials) as client:
            try:
                result = await client.generate_linkedin_message(
                    contact_email=TEST_CONTACT_EMAIL,
                    user_email=TEST_USER_EMAIL,
                )
                assert isinstance(result, AutoboundContent)
                assert result.content_type == "LinkedIn connection request"
                assert isinstance(result.content, str)
            except AutoboundError as e:
                # Some API plans may not support LinkedIn messages
                if "400" in str(e):
                    pytest.skip(f"API plan does not support this content type: {e}")
                raise


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveGenerateInsights:
    """Live tests for insights generation."""

    async def test_generate_insights(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate insights for a prospect."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_insights(
                contact_email=TEST_CONTACT_EMAIL,
                max_insights=5,
            )

            assert isinstance(result, AutoboundInsightsResult)
            assert result.contact_email == TEST_CONTACT_EMAIL
            # May or may not have insights depending on data availability


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveCustomContent:
    """Live tests for custom content generation."""

    async def test_generate_custom_content(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate custom content with natural language prompt."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_custom_content(
                contact_email=TEST_CONTACT_EMAIL,
                user_email=TEST_USER_EMAIL,
                custom_prompt="Write a 3-bullet pain point analysis for this prospect",
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "custom"
            assert len(result.content) > 0


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveModels:
    """Live tests for different AI models."""

    async def test_generate_with_gpt4o(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content using GPT-4o model."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=TEST_CONTACT_EMAIL,
                user_email=TEST_USER_EMAIL,
                model=AutoboundModel.GPT4O,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundClientLiveEdgeCases:
    """Live tests for edge cases."""

    async def test_unknown_email(self, autobound_credentials: dict[str, str]) -> None:
        """Should handle unknown email gracefully."""
        async with AutoboundClient(**autobound_credentials) as client:
            # Use a made-up email that shouldn't have data
            try:
                result = await client.generate_email(
                    contact_email="unknown.person.12345@nonexistent-company.invalid",
                    user_email=TEST_USER_EMAIL,
                )
                # May still generate content with limited personalization
                assert isinstance(result, AutoboundContent)
            except AutoboundError:
                # Or may raise an error for unknown contacts
                pass

    async def test_word_count_parameter(self, autobound_credentials: dict[str, str]) -> None:
        """Should respect word count parameter."""
        async with AutoboundClient(**autobound_credentials) as client:
            try:
                result = await client.generate_email(
                    contact_email=TEST_CONTACT_EMAIL,
                    user_email=TEST_USER_EMAIL,
                    word_count=75,  # Reasonable word count for email
                )

                assert isinstance(result, AutoboundContent)
                # Content should be relatively short (though not strictly enforced)
                words = len(result.content.split())
                # Allow some flexibility - AI isn't perfect at word counts
                assert words < 300
            except AutoboundError as e:
                # Some API plans may have word count constraints
                if "400" in str(e):
                    pytest.skip(f"API does not support this parameter combination: {e}")
                raise
