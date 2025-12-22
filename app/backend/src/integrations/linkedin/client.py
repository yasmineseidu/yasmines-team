"""
LinkedIn API client for social selling and B2B outreach.

Provides OAuth2 authentication and methods for:
- Profile management
- Post creation and engagement
- Connection management
- Direct messaging
- Search functionality

LinkedIn API Rate Limits:
- Application rate limit: 500 requests per day (varies by app type)
- Per-user rate limit: 100 requests per day
- Some endpoints have stricter limits (e.g., messaging)
- 429 = Rate limited, check Retry-After header

Example:
    >>> async with LinkedInClient() as client:
    ...     await client.authenticate()
    ...     profile = await client.get_my_profile()
    ...     print(f"Hello, {profile.first_name}!")
"""

import json
import logging
import os
from typing import Any, cast

import httpx

from src.integrations.base import BaseIntegrationClient
from src.integrations.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInForbiddenError,
    LinkedInNotFoundError,
    LinkedInRateLimitError,
    LinkedInValidationError,
)
from src.integrations.linkedin.models import (
    LinkedInComment,
    LinkedInConnection,
    LinkedInConversation,
    LinkedInMessage,
    LinkedInPost,
    LinkedInProfile,
    LinkedInSearchResponse,
    LinkedInSearchResult,
    PostVisibility,
)

logger = logging.getLogger(__name__)


class LinkedInClient(BaseIntegrationClient):
    """
    LinkedIn API client with OAuth2 authentication.

    Supports:
    - Profile operations (view, update)
    - Post creation and engagement (like, comment, share)
    - Connection management
    - Direct messaging
    - People search

    Attributes:
        access_token: OAuth2 access token for API authentication.
        member_id: LinkedIn member ID (URN) of authenticated user.
    """

    # API endpoints
    API_BASE = "https://api.linkedin.com/v2"
    OAUTH_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    OAUTH_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"

    # OAuth2 scopes for different functionality
    DEFAULT_SCOPES = [
        "openid",
        "profile",
        "email",
        "w_member_social",
    ]

    # Environment variable names
    ENV_CLIENT_ID = "LINKEDIN_CLIENT_ID"
    ENV_CLIENT_SECRET = "LINKEDIN_CLIENT_SECRET"
    ENV_ACCESS_TOKEN = "LINKEDIN_ACCESS_TOKEN"
    ENV_REFRESH_TOKEN = "LINKEDIN_REFRESH_TOKEN"

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        credentials_json: dict[str, Any] | str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize LinkedIn client.

        Credentials can be provided directly or via environment variables:
        - LINKEDIN_ACCESS_TOKEN: OAuth2 access token
        - LINKEDIN_CLIENT_ID: OAuth2 client ID
        - LINKEDIN_CLIENT_SECRET: OAuth2 client secret

        Args:
            access_token: OAuth2 access token (or from env).
            client_id: OAuth2 client ID for token refresh.
            client_secret: OAuth2 client secret for token refresh.
            credentials_json: JSON string or dict with OAuth2 credentials.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        # Parse credentials JSON if provided
        if credentials_json:
            creds = self._parse_credentials(credentials_json)
            access_token = access_token or creds.get("access_token")
            client_id = client_id or creds.get("client_id")
            client_secret = client_secret or creds.get("client_secret")

        # Fall back to environment variables
        self.access_token: str = access_token or os.getenv(self.ENV_ACCESS_TOKEN) or ""
        self.client_id: str = client_id or os.getenv(self.ENV_CLIENT_ID) or ""
        self.client_secret: str = client_secret or os.getenv(self.ENV_CLIENT_SECRET) or ""
        self.refresh_token: str = os.getenv(self.ENV_REFRESH_TOKEN) or ""

        # Member URN will be populated after authentication
        self.member_id: str | None = None

        super().__init__(
            name="linkedin",
            base_url=self.API_BASE,
            api_key=self.access_token,
            timeout=timeout,
            max_retries=max_retries,
        )

        logger.debug("LinkedInClient initialized")

    def _parse_credentials(self, credentials: dict[str, Any] | str) -> dict[str, Any]:
        """Parse credentials from JSON string or dict."""
        if isinstance(credentials, str):
            try:
                return cast(dict[str, Any], json.loads(credentials))
            except json.JSONDecodeError as e:
                raise LinkedInAuthError(f"Invalid credentials JSON: {e}") from e
        return credentials

    def _get_headers(self) -> dict[str, str]:
        """Get headers for LinkedIn API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
        }

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable.

        Extends base class to handle LinkedIn-specific rate limit errors.

        Args:
            error: The exception to check.

        Returns:
            True if the error is retryable, False otherwise.
        """
        # Check base class retryable errors first, then LinkedIn-specific rate limit
        return super()._is_retryable_error(error) or isinstance(error, LinkedInRateLimitError)

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle LinkedIn API response with specific error handling.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON response data.

        Raises:
            LinkedInAuthError: For 401 responses.
            LinkedInForbiddenError: For 403 responses.
            LinkedInNotFoundError: For 404 responses.
            LinkedInRateLimitError: For 429 responses.
            LinkedInValidationError: For 400 responses.
            LinkedInError: For other error responses.
        """
        data: dict[str, Any]
        try:
            data = response.json() if response.text else {}
        except Exception:
            data = {"raw_response": response.text}

        status = response.status_code

        if status == 401:
            message = data.get("message", "Authentication failed")
            raise LinkedInAuthError(
                message=f"LinkedIn authentication failed: {message}",
                response_data=data,
            )

        if status == 403:
            message = data.get("message", "Access forbidden")
            raise LinkedInForbiddenError(
                message=f"LinkedIn access forbidden: {message}",
                response_data=data,
            )

        if status == 404:
            message = data.get("message", "Resource not found")
            raise LinkedInNotFoundError(
                message=f"LinkedIn resource not found: {message}",
                response_data=data,
            )

        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise LinkedInRateLimitError(
                message="LinkedIn API rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                response_data=data,
            )

        if status == 400:
            message = data.get("message", "Request validation failed")
            raise LinkedInValidationError(
                message=f"LinkedIn validation error: {message}",
                response_data=data,
            )

        if status >= 500:
            message = data.get("message", "Server error")
            raise LinkedInError(
                message=f"LinkedIn server error: {message}",
                status_code=status,
                response_data=data,
            )

        if status >= 400:
            message = data.get("message", "Unknown error")
            raise LinkedInError(
                message=f"LinkedIn API error: {message}",
                status_code=status,
                response_data=data,
            )

        return data

    async def authenticate(self) -> None:
        """
        Validate authentication and fetch member ID.

        Raises:
            LinkedInAuthError: If credentials are missing or invalid.
        """
        if not self.access_token:
            raise LinkedInAuthError("No access token provided")

        try:
            # Validate token by fetching user profile
            profile = await self.get_my_profile()
            self.member_id = profile.id
            logger.info(
                f"Successfully authenticated with LinkedIn as {profile.first_name} "
                f"{profile.last_name}"
            )
        except LinkedInAuthError:
            raise
        except Exception as e:
            raise LinkedInAuthError(f"Failed to authenticate with LinkedIn: {e}") from e

    async def refresh_access_token(self, refresh_token: str | None = None) -> str:
        """
        Refresh OAuth2 access token.

        Args:
            refresh_token: Refresh token (uses stored token if not provided).

        Returns:
            New access token.

        Raises:
            LinkedInAuthError: If refresh fails.
        """
        token = refresh_token or self.refresh_token
        if not token:
            raise LinkedInAuthError("No refresh token available")

        if not self.client_id or not self.client_secret:
            raise LinkedInAuthError("Client credentials required for token refresh")

        try:
            response = await self.client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )

            if response.status_code != 200:
                raise LinkedInAuthError(f"Token refresh failed: {response.text}")

            data = response.json()
            new_token: str = data["access_token"]
            self.access_token = new_token
            self.api_key = new_token  # Update base class

            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]

            logger.info("Successfully refreshed LinkedIn access token")
            return new_token

        except LinkedInAuthError:
            raise
        except Exception as e:
            raise LinkedInAuthError(f"Failed to refresh token: {e}") from e

    # ========================================================================
    # Profile Operations
    # ========================================================================

    async def get_my_profile(self) -> LinkedInProfile:
        """
        Get authenticated user's profile.

        Returns:
            LinkedInProfile with user's profile data.

        Raises:
            LinkedInError: If request fails.
        """
        data = await self.get("/userinfo")

        # Map userinfo endpoint response to LinkedInProfile
        return LinkedInProfile(
            id=data.get("sub", ""),
            firstName=data.get("given_name", ""),
            lastName=data.get("family_name", ""),
            email=data.get("email"),
            headline=None,  # Not available from userinfo
            profilePicture=None,
        )

    async def get_profile(self, profile_id: str) -> LinkedInProfile:
        """
        Get LinkedIn profile by ID.

        Note: LinkedIn API v2 has strict access controls on profile data.
        Only first-degree connections may be accessible.

        Args:
            profile_id: LinkedIn profile ID or URN.

        Returns:
            LinkedInProfile with profile data.

        Raises:
            LinkedInNotFoundError: If profile not found.
            LinkedInForbiddenError: If profile not accessible.
        """
        # Ensure URN format
        if not profile_id.startswith("urn:"):
            profile_id = f"urn:li:person:{profile_id}"

        data = await self.get(f"/people/{profile_id}")

        return LinkedInProfile(
            id=data.get("id", profile_id),
            firstName=data.get("firstName", {}).get("localized", {}).get("en_US", ""),
            lastName=data.get("lastName", {}).get("localized", {}).get("en_US", ""),
            headline=data.get("headline", {}).get("localized", {}).get("en_US"),
        )

    # ========================================================================
    # Post Operations
    # ========================================================================

    async def create_post(
        self,
        text: str,
        visibility: PostVisibility = PostVisibility.PUBLIC,
        media_ids: list[str] | None = None,
    ) -> LinkedInPost:
        """
        Create a new LinkedIn post.

        Args:
            text: Post content (max 3000 characters).
            visibility: Post visibility (PUBLIC, CONNECTIONS, LOGGED_IN).
            media_ids: List of media asset URNs to attach.

        Returns:
            LinkedInPost with created post data.

        Raises:
            LinkedInValidationError: If content validation fails.
            LinkedInError: If post creation fails.
        """
        if not self.member_id:
            raise LinkedInError("Must authenticate before creating posts")

        if len(text) > 3000:
            raise LinkedInValidationError("Post text exceeds 3000 character limit")

        # Build post payload per LinkedIn API spec
        author_urn = f"urn:li:person:{self.member_id}"

        payload: dict[str, Any] = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE" if not media_ids else "IMAGE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility.value},
        }

        if media_ids:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {"status": "READY", "media": media_id} for media_id in media_ids
            ]

        data = await self.post("/ugcPosts", json=payload)

        return LinkedInPost(
            id=data.get("id", ""),
            text=text,
            visibility=visibility,
            createdAt=None,
        )

    async def get_post(self, post_id: str) -> LinkedInPost:
        """
        Get a specific post by ID.

        Args:
            post_id: LinkedIn post ID or URN.

        Returns:
            LinkedInPost with post data.
        """
        if not post_id.startswith("urn:"):
            post_id = f"urn:li:ugcPost:{post_id}"

        data = await self.get(f"/ugcPosts/{post_id}")

        text = ""
        specific_content = data.get("specificContent", {})
        share_content = specific_content.get("com.linkedin.ugc.ShareContent", {})
        if share_content:
            text = share_content.get("shareCommentary", {}).get("text", "")

        return LinkedInPost(
            id=data.get("id", post_id),
            text=text,
            visibility=PostVisibility.PUBLIC,
        )

    async def delete_post(self, post_id: str) -> bool:
        """
        Delete a LinkedIn post.

        Args:
            post_id: LinkedIn post ID or URN.

        Returns:
            True if deletion successful.

        Raises:
            LinkedInNotFoundError: If post not found.
            LinkedInForbiddenError: If not authorized to delete.
        """
        if not post_id.startswith("urn:"):
            post_id = f"urn:li:ugcPost:{post_id}"

        await self.delete(f"/ugcPosts/{post_id}")
        logger.info(f"Deleted LinkedIn post: {post_id}")
        return True

    async def like_post(self, post_id: str) -> bool:
        """
        Like a LinkedIn post.

        Args:
            post_id: LinkedIn post ID or URN.

        Returns:
            True if like successful.
        """
        if not self.member_id:
            raise LinkedInError("Must authenticate before liking posts")

        if not post_id.startswith("urn:"):
            post_id = f"urn:li:ugcPost:{post_id}"

        actor_urn = f"urn:li:person:{self.member_id}"

        payload = {
            "actor": actor_urn,
            "object": post_id,
        }

        await self.post("/socialActions/{post_id}/likes", json=payload)
        logger.info(f"Liked LinkedIn post: {post_id}")
        return True

    async def comment_on_post(self, post_id: str, text: str) -> LinkedInComment:
        """
        Comment on a LinkedIn post.

        Args:
            post_id: LinkedIn post ID or URN.
            text: Comment text (max 1250 characters).

        Returns:
            LinkedInComment with created comment data.
        """
        if not self.member_id:
            raise LinkedInError("Must authenticate before commenting")

        if len(text) > 1250:
            raise LinkedInValidationError("Comment text exceeds 1250 character limit")

        if not post_id.startswith("urn:"):
            post_id = f"urn:li:ugcPost:{post_id}"

        actor_urn = f"urn:li:person:{self.member_id}"

        payload = {
            "actor": actor_urn,
            "message": {"text": text},
        }

        data = await self.post(f"/socialActions/{post_id}/comments", json=payload)

        return LinkedInComment(
            id=data.get("id", ""),
            postId=post_id,
            text=text,
        )

    # ========================================================================
    # Connection Operations
    # ========================================================================

    async def get_connections(
        self,
        start: int = 0,
        count: int = 50,
    ) -> list[LinkedInConnection]:
        """
        Get user's LinkedIn connections.

        Note: LinkedIn API restricts connection data access.
        Only basic information is available.

        Args:
            start: Starting index for pagination.
            count: Number of connections to return (max 50).

        Returns:
            List of LinkedInConnection objects.
        """
        params = {
            "start": start,
            "count": min(count, 50),
            "q": "viewer",
        }

        data = await self.get("/connections", params=params)

        connections = []
        for element in data.get("elements", []):
            connections.append(
                LinkedInConnection(
                    id=element.get("id", ""),
                    firstName=element.get("firstName", ""),
                    lastName=element.get("lastName", ""),
                    headline=element.get("headline"),
                )
            )

        return connections

    async def send_connection_request(
        self,
        profile_id: str,
        message: str | None = None,
    ) -> bool:
        """
        Send a connection request to a LinkedIn member.

        Args:
            profile_id: Target profile ID or URN.
            message: Optional personalized message (max 300 chars).

        Returns:
            True if request sent successfully.

        Raises:
            LinkedInValidationError: If message too long.
        """
        if message and len(message) > 300:
            raise LinkedInValidationError("Connection request message exceeds 300 character limit")

        if not profile_id.startswith("urn:"):
            profile_id = f"urn:li:person:{profile_id}"

        payload: dict[str, Any] = {
            "invitee": profile_id,
        }

        if message:
            payload["message"] = message

        await self.post("/invitations", json=payload)
        logger.info(f"Sent connection request to: {profile_id}")
        return True

    # ========================================================================
    # Messaging Operations
    # ========================================================================

    async def send_message(
        self,
        recipient_id: str,
        body: str,
        subject: str | None = None,
    ) -> LinkedInMessage:
        """
        Send a direct message to a LinkedIn member.

        Note: Message sending requires specific API permissions
        and is restricted to first-degree connections.

        Args:
            recipient_id: Recipient's profile ID or URN.
            body: Message body text.
            subject: Optional message subject.

        Returns:
            LinkedInMessage with sent message data.

        Raises:
            LinkedInForbiddenError: If messaging not permitted.
        """
        if not self.member_id:
            raise LinkedInError("Must authenticate before sending messages")

        if not recipient_id.startswith("urn:"):
            recipient_id = f"urn:li:person:{recipient_id}"

        payload: dict[str, Any] = {
            "recipients": [recipient_id],
            "subject": subject,
            "body": body,
        }

        data = await self.post("/messages", json=payload)

        return LinkedInMessage(
            id=data.get("id", ""),
            conversationId=data.get("conversationId", ""),
            body=body,
            subject=subject,
        )

    async def get_conversations(
        self,
        start: int = 0,
        count: int = 20,
    ) -> list[LinkedInConversation]:
        """
        Get user's message conversations.

        Args:
            start: Starting index for pagination.
            count: Number of conversations to return.

        Returns:
            List of LinkedInConversation objects.
        """
        params = {
            "start": start,
            "count": count,
        }

        data = await self.get("/messaging/conversations", params=params)

        conversations = []
        for element in data.get("elements", []):
            conversations.append(
                LinkedInConversation(
                    id=element.get("id", ""),
                    lastActivityAt=element.get("lastActivityAt"),
                    unreadCount=element.get("unreadCount", 0),
                )
            )

        return conversations

    async def get_conversation_messages(
        self,
        conversation_id: str,
        start: int = 0,
        count: int = 20,
    ) -> list[LinkedInMessage]:
        """
        Get messages in a conversation.

        Args:
            conversation_id: Conversation ID.
            start: Starting index for pagination.
            count: Number of messages to return.

        Returns:
            List of LinkedInMessage objects.
        """
        params = {
            "start": start,
            "count": count,
        }

        data = await self.get(
            f"/messaging/conversations/{conversation_id}/events",
            params=params,
        )

        messages = []
        for element in data.get("elements", []):
            if element.get("eventContent", {}).get(
                "com.linkedin.voyager.messaging.event.MessageEvent"
            ):
                msg_data = element["eventContent"][
                    "com.linkedin.voyager.messaging.event.MessageEvent"
                ]
                messages.append(
                    LinkedInMessage(
                        id=element.get("id", ""),
                        conversationId=conversation_id,
                        body=msg_data.get("body", ""),
                        createdAt=element.get("createdAt"),
                    )
                )

        return messages

    # ========================================================================
    # Search Operations
    # ========================================================================

    async def search_people(
        self,
        keywords: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        title: str | None = None,
        start: int = 0,
        count: int = 10,
    ) -> LinkedInSearchResponse:
        """
        Search for LinkedIn profiles.

        Note: LinkedIn API search is limited and may require
        specific product tier access.

        Args:
            keywords: General search keywords.
            first_name: Filter by first name.
            last_name: Filter by last name.
            company: Filter by current company.
            title: Filter by job title.
            start: Starting index for pagination.
            count: Number of results to return.

        Returns:
            LinkedInSearchResponse with search results.
        """
        params: dict[str, Any] = {
            "start": start,
            "count": count,
            "q": "people",
        }

        if keywords:
            params["keywords"] = keywords
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        if company:
            params["company"] = company
        if title:
            params["title"] = title

        data = await self.get("/search", params=params)

        results: list[LinkedInSearchResult] = []
        for element in data.get("elements", []):
            profile_data = element.get("profile", {})
            results.append(
                LinkedInSearchResult(
                    profile=LinkedInProfile(
                        id=profile_data.get("id", ""),
                        firstName=profile_data.get("firstName", ""),
                        lastName=profile_data.get("lastName", ""),
                        headline=profile_data.get("headline"),
                    ),
                    connectionDegree=element.get("connectionDegree"),
                )
            )

        return LinkedInSearchResponse(
            results=results,
            totalCount=data.get("paging", {}).get("total", 0),
            pageSize=count,
            start=start,
            hasMore=len(results) == count,
        )

    # ========================================================================
    # Engagement Tracking
    # ========================================================================

    async def get_post_stats(self, post_id: str) -> dict[str, Any]:
        """
        Get engagement statistics for a post.

        Args:
            post_id: LinkedIn post ID or URN.

        Returns:
            Dictionary with engagement metrics.
        """
        if not post_id.startswith("urn:"):
            post_id = f"urn:li:ugcPost:{post_id}"

        data = await self.get(f"/socialActions/{post_id}")

        return {
            "likes": data.get("likesSummary", {}).get("totalLikes", 0),
            "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
            "shares": data.get("sharesSummary", {}).get("totalShares", 0),
        }

    # ========================================================================
    # Health Check
    # ========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check LinkedIn API connectivity and authentication.

        Returns:
            Health check status with authentication state.
        """
        try:
            if not self.access_token:
                return {
                    "name": "linkedin",
                    "healthy": False,
                    "message": "No access token configured",
                }

            await self.get_my_profile()
            return {
                "name": "linkedin",
                "healthy": True,
                "message": "LinkedIn API is accessible and authenticated",
            }
        except LinkedInAuthError as e:
            return {
                "name": "linkedin",
                "healthy": False,
                "message": f"Authentication failed: {e}",
            }
        except Exception as e:
            return {
                "name": "linkedin",
                "healthy": False,
                "message": f"Health check failed: {e}",
            }
