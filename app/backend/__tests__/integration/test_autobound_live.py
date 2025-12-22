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

# Import test fixtures
from __tests__.fixtures.autobound_fixtures import (
    CUSTOM_PROMPTS,
    DEFAULT_TEST_CONTACT,
    DEFAULT_TEST_SENDER,
    TEST_CONTACTS,
    TEST_SENDERS,
)
from src.integrations.autobound import (
    AutoboundClient,
    AutoboundContent,
    AutoboundContentType,
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


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundHealthCheck:
    """Live tests for Autobound health check."""

    async def test_health_check_returns_status(self, autobound_credentials: dict[str, str]) -> None:
        """Should return health status with valid credentials."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.health_check()

            assert "name" in result
            assert result["name"] == "autobound"
            assert "api_url" in result


# =============================================================================
# EMAIL GENERATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundGenerateEmail:
    """Live tests for email generation."""

    async def test_generate_basic_email(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate a basic personalized email."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "email"
            assert len(result.content) > 0
            assert result.contact_email == DEFAULT_TEST_CONTACT

    async def test_generate_email_cxo_pitch_style(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should generate email with CXO pitch writing style."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=TEST_CONTACTS["tech_ceo"]["email"],
                user_email=TEST_SENDERS["founder"],
                writing_style=AutoboundWritingStyle.CXO_PITCH,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0

    async def test_generate_email_with_word_count(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should respect word count parameter."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                word_count=50,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0
            # Word count is approximate - AI isn't perfect
            words = len(result.content.split())
            assert words < 150  # Should be relatively short

    async def test_generate_email_with_context(self, autobound_credentials: dict[str, str]) -> None:
        """Should incorporate additional context."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                additional_context="We met at the SaaS conference last week",
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# CALL SCRIPT GENERATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundGenerateCallScript:
    """Live tests for call script generation."""

    async def test_generate_call_script(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate personalized call script."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_call_script(
                contact_email=TEST_CONTACTS["sales_leader"]["email"],
                user_email=TEST_SENDERS["account_exec"],
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "call script"
            assert len(result.content) > 0

    async def test_generate_call_script_with_context(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should generate call script with meeting context."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_call_script(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                additional_context="This is a follow-up call after they downloaded our whitepaper",
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# LINKEDIN MESSAGE GENERATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundGenerateLinkedIn:
    """Live tests for LinkedIn message generation."""

    async def test_generate_linkedin_message(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate personalized LinkedIn connection request."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_linkedin_message(
                contact_email=TEST_CONTACTS["startup_founder"]["email"],
                user_email=TEST_SENDERS["bdr"],
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "LinkedIn connection request"
            assert len(result.content) > 0
            # LinkedIn messages should be concise
            assert len(result.content) < 1000


# =============================================================================
# CUSTOM CONTENT GENERATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundGenerateCustomContent:
    """Live tests for custom content generation."""

    async def test_generate_pain_point_analysis(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should generate custom pain point analysis."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_custom_content(
                contact_email=TEST_CONTACTS["finance_exec"]["email"],
                user_email=DEFAULT_TEST_SENDER,
                custom_prompt=CUSTOM_PROMPTS["pain_point_analysis"]["prompt"],
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "custom"
            assert len(result.content) > 0

    async def test_generate_value_proposition(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate custom value proposition."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_custom_content(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                custom_prompt=CUSTOM_PROMPTS["value_proposition"]["prompt"],
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# INSIGHTS GENERATION TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundGenerateInsights:
    """Live tests for insights generation."""

    async def test_generate_insights(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate insights for a well-known executive."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_insights(
                contact_email=DEFAULT_TEST_CONTACT,
                max_insights=10,
            )

            assert isinstance(result, AutoboundInsightsResult)
            assert result.contact_email == DEFAULT_TEST_CONTACT
            # Well-known executives should have insights
            # But we don't require them as API may not always find data

    async def test_generate_insights_max_limit(self, autobound_credentials: dict[str, str]) -> None:
        """Should respect max_insights parameter."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_insights(
                contact_email=TEST_CONTACTS["tech_ceo"]["email"],
                max_insights=5,
            )

            assert isinstance(result, AutoboundInsightsResult)
            assert result.total_count <= 5


# =============================================================================
# AI MODEL TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundAIModels:
    """Live tests for different AI models."""

    async def test_generate_with_gpt4o(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content using GPT-4o model."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                model=AutoboundModel.GPT4O,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0

    async def test_generate_with_sonnet(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content using Claude Sonnet model."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                model=AutoboundModel.SONNET,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# CALL_ENDPOINT TESTS (Future-Proofing)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundCallEndpoint:
    """Live tests for generic endpoint calling (future-proofing)."""

    async def test_call_generate_content_endpoint(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should call generate-content endpoint directly."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.call_endpoint(
                "/generate-content/v3.6",
                method="POST",
                json={
                    "contactEmail": DEFAULT_TEST_CONTACT,
                    "userEmail": DEFAULT_TEST_SENDER,
                    "contentType": "email",
                },
            )

            assert isinstance(result, dict)
            # Response should have content
            assert "content" in result or len(result) > 0

    async def test_call_generate_insights_endpoint(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should call generate-insights endpoint directly."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.call_endpoint(
                "/generate-insights/v1.4",
                method="POST",
                json={
                    "contactEmail": DEFAULT_TEST_CONTACT,
                    "maxInsights": 5,
                },
            )

            assert isinstance(result, dict)


# =============================================================================
# WRITING STYLE TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundWritingStyles:
    """Live tests for different writing styles."""

    async def test_friendly_style(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content with friendly style."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                writing_style=AutoboundWritingStyle.FRIENDLY,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0

    async def test_professional_style(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content with professional style."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_email(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                writing_style=AutoboundWritingStyle.PROFESSIONAL,
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundEdgeCases:
    """Live tests for edge cases and error handling."""

    async def test_unknown_contact_still_generates(
        self, autobound_credentials: dict[str, str]
    ) -> None:
        """Should handle unknown email gracefully and still generate content."""
        async with AutoboundClient(**autobound_credentials) as client:
            try:
                result = await client.generate_email(
                    contact_email="unknown.person.xyz123@nonexistent-domain-test.invalid",
                    user_email=DEFAULT_TEST_SENDER,
                )
                # Should still generate something even without personalization data
                assert isinstance(result, AutoboundContent)
            except AutoboundError:
                # Or API may reject unknown contacts - both are acceptable
                pass

    async def test_different_contact_types(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate content for various contact types."""
        async with AutoboundClient(**autobound_credentials) as client:
            # Test with a different well-known contact
            result = await client.generate_email(
                contact_email=TEST_CONTACTS["tech_founder"]["email"],
                user_email=TEST_SENDERS["founder"],
            )

            assert isinstance(result, AutoboundContent)
            assert len(result.content) > 0


# =============================================================================
# CONTENT TYPE TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.live_api
class TestAutoboundContentTypes:
    """Live tests for all content types."""

    async def test_generate_sms(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate SMS content."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_content(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                content_type=AutoboundContentType.SMS,
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "SMS"
            assert len(result.content) > 0
            # SMS should be short
            assert len(result.content) < 500

    async def test_generate_opener(self, autobound_credentials: dict[str, str]) -> None:
        """Should generate conversation opener."""
        async with AutoboundClient(**autobound_credentials) as client:
            result = await client.generate_content(
                contact_email=DEFAULT_TEST_CONTACT,
                user_email=DEFAULT_TEST_SENDER,
                content_type=AutoboundContentType.OPENER,
            )

            assert isinstance(result, AutoboundContent)
            assert result.content_type == "opener"
            assert len(result.content) > 0
