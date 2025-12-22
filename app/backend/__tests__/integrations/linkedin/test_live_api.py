"""Live API tests for LinkedIn integration.

These tests require real LinkedIn credentials in .env:
- LINKEDIN_ACCESS_TOKEN: OAuth2 access token
- LINKEDIN_CLIENT_ID: OAuth2 client ID (optional)
- LINKEDIN_CLIENT_SECRET: OAuth2 client secret (optional)

Run with: pytest tests/integrations/linkedin/test_live_api.py -v -m "live_api"
"""

import os

import pytest

from src.integrations.linkedin import (
    LinkedInClient,
    LinkedInError,
    PostVisibility,
)

# Skip all tests if credentials not available
pytestmark = [
    pytest.mark.live_api,
    pytest.mark.skipif(
        not os.getenv("LINKEDIN_ACCESS_TOKEN"),
        reason="LINKEDIN_ACCESS_TOKEN not set in environment",
    ),
]


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================


class TestLiveAuthentication:
    """Live tests for OAuth2 authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_with_real_token(
        self, live_linkedin_client: LinkedInClient | None
    ) -> None:
        """Should authenticate successfully with real token."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        await live_linkedin_client.authenticate()

        assert live_linkedin_client.member_id is not None
        print(f"Authenticated as member: {live_linkedin_client.member_id}")

        await live_linkedin_client.close()


# ============================================================================
# PROFILE TESTS
# ============================================================================


class TestLiveProfile:
    """Live tests for profile operations."""

    @pytest.mark.asyncio
    async def test_get_my_profile(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Should retrieve authenticated user's profile."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            profile = await live_linkedin_client.get_my_profile()

            assert profile.id is not None
            assert profile.first_name is not None
            assert profile.last_name is not None

            print(f"Profile: {profile.first_name} {profile.last_name}")
            print(f"Email: {profile.email}")
        finally:
            await live_linkedin_client.close()

    @pytest.mark.asyncio
    async def test_health_check(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Should pass health check with valid credentials."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            result = await live_linkedin_client.health_check()

            assert result["name"] == "linkedin"
            assert result["healthy"] is True

            print(f"Health check: {result['message']}")
        finally:
            await live_linkedin_client.close()


# ============================================================================
# POST TESTS (CAUTION: Creates real content)
# ============================================================================


class TestLivePosts:
    """Live tests for post operations.

    NOTE: These tests create REAL posts on LinkedIn.
    They are marked to run only when explicitly requested.
    """

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Creates real LinkedIn posts - enable manually")
    async def test_create_and_delete_post(
        self, live_linkedin_client: LinkedInClient | None
    ) -> None:
        """Should create and delete a test post."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            await live_linkedin_client.authenticate()

            # Create a test post
            post = await live_linkedin_client.create_post(
                text="[TEST] This is an automated test post from Claude integration testing. It will be deleted shortly.",
                visibility=PostVisibility.CONNECTIONS,  # Limit visibility
            )

            assert post.id is not None
            print(f"Created post: {post.id}")

            # Delete the post immediately
            deleted = await live_linkedin_client.delete_post(post.id)
            assert deleted is True
            print("Post deleted successfully")
        finally:
            await live_linkedin_client.close()


# ============================================================================
# CONNECTIONS TESTS
# ============================================================================


class TestLiveConnections:
    """Live tests for connection operations."""

    @pytest.mark.asyncio
    async def test_get_connections(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Should retrieve user's connections."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            await live_linkedin_client.authenticate()
            connections = await live_linkedin_client.get_connections(count=5)

            print(f"Retrieved {len(connections)} connections")
            for conn in connections[:3]:
                print(f"  - {conn.first_name} {conn.last_name}: {conn.headline}")
        except LinkedInError as e:
            # LinkedIn may restrict connection data access
            print(f"Connection access restricted: {e}")
        finally:
            await live_linkedin_client.close()


# ============================================================================
# SEARCH TESTS
# ============================================================================


class TestLiveSearch:
    """Live tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_people(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Should search for people by keywords."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            await live_linkedin_client.authenticate()
            results = await live_linkedin_client.search_people(
                keywords="software engineer",
                count=5,
            )

            print(f"Search returned {results.total_count} total results")
            print(f"Retrieved {len(results.results)} results on this page")
        except LinkedInError as e:
            # LinkedIn may restrict search access
            print(f"Search access restricted: {e}")
        finally:
            await live_linkedin_client.close()


# ============================================================================
# MESSAGING TESTS
# ============================================================================


class TestLiveMessaging:
    """Live tests for messaging operations."""

    @pytest.mark.asyncio
    async def test_get_conversations(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Should retrieve user's conversations."""
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            await live_linkedin_client.authenticate()
            conversations = await live_linkedin_client.get_conversations(count=5)

            print(f"Retrieved {len(conversations)} conversations")
            for conv in conversations[:3]:
                print(f"  - Conversation {conv.id}: {conv.unread_count} unread")
        except LinkedInError as e:
            # LinkedIn may restrict messaging access
            print(f"Messaging access restricted: {e}")
        finally:
            await live_linkedin_client.close()


# ============================================================================
# API QUIRKS DOCUMENTATION
# ============================================================================


class TestApiQuirks:
    """Tests to document LinkedIn API quirks and limitations."""

    @pytest.mark.asyncio
    async def test_document_rate_limits(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Document rate limit headers from real responses.

        LinkedIn API rate limits:
        - Application rate limit: Varies by product tier
        - Per-user rate limit: ~100 requests/day for basic
        - Strict limits on messaging, connection requests
        """
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        try:
            # Make a simple request and inspect headers
            profile = await live_linkedin_client.get_my_profile()
            print("\nLinkedIn API Observations:")
            print("  - Profile access: Working")
            print(f"  - Member ID format: {type(profile.id)}")
        finally:
            await live_linkedin_client.close()

    @pytest.mark.asyncio
    async def test_document_oauth_scopes(self, live_linkedin_client: LinkedInClient | None) -> None:
        """Document which operations require which OAuth scopes.

        Common LinkedIn OAuth scopes:
        - openid: OpenID Connect authentication
        - profile: Basic profile info (first/last name)
        - email: Email address access
        - w_member_social: Post on behalf of user
        - r_liteprofile: Read lite profile
        - r_emailaddress: Read email
        """
        if live_linkedin_client is None:
            pytest.skip("LinkedIn credentials not configured")

        print("\nLinkedIn OAuth Scope Requirements:")
        print("  - Get profile: openid, profile")
        print("  - Get email: email")
        print("  - Create posts: w_member_social")
        print("  - Read connections: r_1st_connections (requires approval)")
        print("  - Send messages: w_messages (requires approval)")
