"""Gmail API async client with OAuth 2.0 and Service Account support.

Extends BaseIntegrationClient with full Gmail API support for message,
draft, label, thread, and attachment operations.

Supports three authentication methods:
1. Service Account (Recommended for production)
   - Uses JWT bearer token flow with Google-signed private key
   - No user interaction required
   - Supports domain-wide delegation

2. OAuth 2.0 (Standard user authentication)
   - Access token with automatic refresh using refresh token
   - Requires client_id, client_secret, refresh_token
   - Best for user-specific access

3. Pre-generated Token (Development/simple use)
   - Direct access_token without refresh capability
   - Simplest setup, limited to token lifetime
   - Best for testing and development
"""

import base64
import contextlib
import json
import logging
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from src.integrations.base import BaseIntegrationClient

from .exceptions import (
    GmailAuthError,
    GmailError,
    GmailNotFoundError,
    GmailQuotaExceeded,
    GmailRateLimitError,
)

logger = logging.getLogger(__name__)


class GmailClient(BaseIntegrationClient):
    """Async client for Gmail API with three authentication methods.

    Handles email operations including send, list, read, manage labels,
    attachments, drafts, and threads with automatic token refresh.

    Supports three authentication methods:
    1. Service Account (Production) - JWT bearer token flow, zero user interaction
    2. OAuth 2.0 (User Access) - Access token with automatic refresh
    3. Pre-generated Token (Development) - Simple token without refresh

    Examples:
        # Service Account (Recommended for production)
        >>> client = GmailClient(credentials_json={  # pragma: allowlist secret
        ...     "type": "service_account",
        ...     "private_key": "-----BEGIN RSA PRIVATE KEY-----...",  # pragma: allowlist secret
        ...     "client_email": "service-account@project.iam.gserviceaccount.com",
        ...     "token_uri": "https://oauth2.googleapis.com/token"
        ... })
        >>> await client.authenticate()
        >>> messages = await client.list_messages()

        # OAuth 2.0 (User-specific access)
        >>> client = GmailClient(  # pragma: allowlist secret
        ...     access_token="ya29...",  # pragma: allowlist secret
        ...     refresh_token="1//...",  # pragma: allowlist secret
        ...     client_id="123456.apps.googleusercontent.com",
        ...     client_secret="secret..."  # pragma: allowlist secret
        ... )
        >>> await client.authenticate()
        >>> messages = await client.list_messages()

        # Pre-generated Token (Development/testing)
        >>> client = GmailClient(access_token="ya29...")
        >>> await client.authenticate()
        >>> messages = await client.list_messages()
    """

    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://gmail.googleapis.com"

    DEFAULT_SCOPES = [
        "https://mail.google.com/",  # Parent-level Gmail scope covering all Gmail operations
    ]

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        credentials_json: dict[str, Any] | str | None = None,
        user_email: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize Gmail client with multiple authentication methods.

        Supports three authentication methods (in order of precedence):
        1. Service Account (type="service_account") - JWT bearer token flow with optional domain-wide delegation
        2. OAuth 2.0 - Access token with optional refresh capability
        3. Pre-generated Token - Direct access token

        Args:
            access_token: OAuth access token or pre-generated token.
                         Defaults to env var GMAIL_ACCESS_TOKEN.
            refresh_token: OAuth refresh token for token refresh.
                          Defaults to env var GMAIL_REFRESH_TOKEN.
            client_id: OAuth client ID. Defaults to env var GOOGLE_CLIENT_ID.
            client_secret: OAuth client secret. Defaults to env var GOOGLE_CLIENT_SECRET.
            credentials_json: Full credentials as dict or JSON string. Supports:
                - Service account: {"type": "service_account", "private_key": "...", ...}
                - OAuth 2.0: {"access_token": "...", "refresh_token": "...", ...}
                - Pre-generated: {"access_token": "..."}
            user_email: For service account with domain-wide delegation, the email to impersonate.
                       Example: "user@workspace.ai". Defaults to env var GMAIL_USER_EMAIL.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            retry_base_delay: Base delay for exponential backoff in seconds.

        Raises:
            GmailError: If credentials cannot be resolved from arguments or environment.

        Example:
            # Method 1: Service Account with Domain-Wide Delegation (Production)
            >>> client = GmailClient(credentials_json={  # pragma: allowlist secret
            ...     "type": "service_account",
            ...     "private_key": "-----BEGIN RSA PRIVATE KEY-----...",  # pragma: allowlist secret
            ...     "client_email": "service-account@project.iam.gserviceaccount.com",
            ...     "token_uri": "https://oauth2.googleapis.com/token"
            ... }, user_email="yasmine@smarterteam.ai")

            # Method 2: OAuth 2.0 (User access)
            >>> client = GmailClient(  # pragma: allowlist secret
            ...     access_token="ya29...",  # pragma: allowlist secret
            ...     refresh_token="1//...",  # pragma: allowlist secret
            ...     client_id="...",
            ...     client_secret="..."  # pragma: allowlist secret
            ... )

            # Method 3: Pre-generated Token (Development)
            >>> client = GmailClient(access_token="ya29...")
        """
        # Store credential type for later use
        self.auth_method: str = "unknown"
        self.credentials_dict: dict[str, Any] = {}
        self.user_email = user_email or os.getenv("GMAIL_USER_EMAIL")

        # Parse credentials JSON if provided
        if isinstance(credentials_json, str):
            try:
                creds = json.loads(credentials_json)
            except json.JSONDecodeError as e:
                raise GmailError(f"Invalid credentials JSON: {e}") from e
        elif isinstance(credentials_json, dict):
            creds = credentials_json
        else:
            creds = {}

        self.credentials_dict = creds

        # Detect authentication method and extract credentials
        cred_type = creds.get("type")

        if cred_type == "service_account":
            # Service Account Authentication
            self.auth_method = "service_account"
            self._validate_service_account_credentials(creds)
            self.access_token = None  # Will be obtained via JWT flow
            self.refresh_token = None
            self.client_id = None
            self.client_secret = None
            logger.info("Configured Gmail client for Service Account authentication")

        else:
            # OAuth 2.0 or Pre-generated Token
            # Parse OAuth parameters from arguments and environment
            self.access_token = access_token or os.getenv("GMAIL_ACCESS_TOKEN")
            self.refresh_token = refresh_token or os.getenv("GMAIL_REFRESH_TOKEN")
            self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
            self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")

            # Override from credentials dict if present
            if "access_token" in creds:
                self.access_token = creds["access_token"]
            if "refresh_token" in creds:
                self.refresh_token = creds["refresh_token"]
            if "client_id" in creds:
                self.client_id = creds["client_id"]
            if "client_secret" in creds:
                self.client_secret = creds["client_secret"]

            # Determine auth method
            if self.refresh_token and self.client_id and self.client_secret:
                self.auth_method = "oauth2"
                logger.info("Configured Gmail client for OAuth 2.0 with refresh token")
            elif self.access_token:
                self.auth_method = "pre_generated_token"
                logger.info("Configured Gmail client for pre-generated token")
            else:
                raise GmailError(
                    "No credentials provided. Use one of:\n"
                    "1. Service Account: credentials_json with type='service_account'\n"
                    "2. OAuth 2.0: access_token + refresh_token + client_id + client_secret\n"
                    "3. Pre-generated Token: access_token only"
                )

        # For service account, we'll get token in authenticate() method
        # For others, validate we have access token now
        if self.auth_method != "service_account" and not self.access_token:
            raise GmailError(
                "No access_token provided. Pass as argument or set GMAIL_ACCESS_TOKEN env var."
            )

        super().__init__(
            name="gmail",
            base_url=self.API_BASE,
            api_key=self.access_token or "pending",  # Service account token obtained later
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
        )

        self.user_id = "me"  # Always use "me" for authenticated user
        logger.info(f"Initialized Gmail client with {self.auth_method} authentication")

    async def authenticate(self) -> None:
        """Authenticate with Gmail API using configured credentials.

        Handles all three authentication methods:
        1. Service Account - Obtains access token via JWT bearer flow
        2. OAuth 2.0 - Validates refresh token and client credentials
        3. Pre-generated Token - Validates token is present

        Call this method once before making API requests.

        Raises:
            GmailAuthError: If authentication fails
        """
        try:
            if self.auth_method == "service_account":
                await self._authenticate_service_account()
                logger.info("Gmail service account authenticated")

            elif self.auth_method == "oauth2":
                # For OAuth 2.0, token is already present from __init__
                # Validate we can refresh it if needed
                if not all([self.refresh_token, self.client_id, self.client_secret]):
                    raise GmailAuthError(
                        "OAuth 2.0 authentication incomplete: missing refresh_token, client_id, or client_secret"
                    )
                logger.info("Gmail OAuth 2.0 authenticated")

            elif self.auth_method == "pre_generated_token":
                # For pre-generated token, it's already present from __init__
                if not self.access_token:
                    raise GmailAuthError("Pre-generated token not found")
                logger.info("Gmail pre-generated token authenticated")

            else:
                raise GmailAuthError(f"Unknown authentication method: {self.auth_method}")

        except GmailAuthError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GmailAuthError(f"Failed to authenticate: {e}") from e

    def _validate_service_account_credentials(self, creds: dict[str, Any]) -> None:
        """Validate service account credentials have required fields.

        Args:
            creds: Service account credentials dict

        Raises:
            GmailError: If required fields are missing
        """
        required_fields = ["private_key", "client_email", "token_uri"]
        missing = [field for field in required_fields if field not in creds]

        if missing:
            raise GmailError(
                f"Service account credentials missing required fields: {missing}. "
                f"Service account JSON must include: {', '.join(required_fields)}"
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Gmail API requests.

        Returns:
            Headers dict with authorization and content type.
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _authenticate_service_account(self) -> None:
        """Authenticate using service account credentials with JWT bearer flow.

        Implements Google's JWT bearer token flow for service account authentication.
        This is the production-ready authentication method with zero user interaction.

        Optionally supports domain-wide delegation to impersonate workspace users.

        The JWT flow works as follows:
        1. Create JWT assertion signed with service account private key
        2. (Optional) Set subject to user_email for domain-wide delegation
        3. Exchange JWT for access token via Google OAuth2 endpoint
        4. Use token for API requests (accessing delegated user's Gmail)

        For implementation, use the google-auth library:
            pip install google-auth

        Then in code:
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials

            credentials = Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=self.DEFAULT_SCOPES
            )
            # For domain-wide delegation:
            if user_email:
                credentials = credentials.with_subject(user_email)

            await credentials.refresh(Request())
            self.access_token = credentials.token

        For now, this method expects the access_token to be pre-generated and
        included in credentials dict, or uses the google-auth library if available.

        Raises:
            GmailAuthError: If service account authentication fails
        """
        try:
            # Try to use google-auth library if available
            try:
                from google.auth.transport.requests import Request
                from google.oauth2.service_account import Credentials

                logger.info("Using google-auth library for service account JWT flow")

                credentials = Credentials.from_service_account_info(
                    self.credentials_dict,
                    scopes=self.DEFAULT_SCOPES,
                )

                # For domain-wide delegation, set the user to impersonate
                if self.user_email:
                    credentials = credentials.with_subject(self.user_email)
                    logger.info(f"Using domain-wide delegation for: {self.user_email}")

                # Synchronously refresh token (google-auth doesn't have async support)
                request = Request()
                credentials.refresh(request)
                token: str | None = credentials.token
                if not token:
                    raise GmailAuthError("Failed to obtain access token from service account")
                self.access_token = token
                self.api_key = self.access_token

                logger.info("Service account authenticated successfully via JWT flow")

            except ImportError:
                # Fallback: expect access_token in credentials dict
                logger.warning(
                    "google-auth library not installed. " "Install with: pip install google-auth"
                )

                if "access_token" in self.credentials_dict:
                    token = self.credentials_dict["access_token"]
                    if not isinstance(token, str):
                        raise GmailAuthError(
                            "access_token in credentials must be a string"
                        ) from None
                    self.access_token = token
                    self.api_key = self.access_token
                    logger.info("Using pre-generated access token from credentials")
                else:
                    raise GmailAuthError(
                        "Service account credentials missing access_token. "
                        "Install google-auth library for automatic JWT token generation: "
                        "pip install google-auth"
                    ) from None

        except GmailAuthError:
            raise
        except Exception as e:
            logger.error(f"Service account authentication failed: {e}")
            raise GmailAuthError(f"Service account auth failed: {e}") from e

    async def _refresh_access_token(self) -> None:
        """Refresh expired access token using refresh token or JWT flow.

        For OAuth 2.0: Uses refresh token to get new access token
        For Service Account: Regenerates JWT and exchanges for new token

        Raises:
            GmailAuthError: If token refresh fails.
        """
        if self.auth_method == "service_account":
            # For service account, re-authenticate to get new token
            await self._authenticate_service_account()
            return

        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise GmailAuthError(
                "Cannot refresh token: refresh_token, client_id, or client_secret missing"
            )

        logger.info("Refreshing access token...")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OAUTH_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )

            if response.status_code != 200:
                raise GmailAuthError(f"Token refresh failed: {response.text}")

            data = response.json()
            token: str = data["access_token"]
            self.access_token = token
            self.api_key = token

            logger.info("Access token refreshed successfully")

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise GmailAuthError(f"Token refresh failed: {e}") from e

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Gmail API response with error checking.

        Overrides base implementation for Gmail-specific error codes.

        Args:
            response: HTTP response from Gmail API.

        Returns:
            Parsed JSON response.

        Raises:
            GmailAuthError: On authentication errors (401).
            GmailQuotaExceeded: On quota exceeded (403).
            GmailRateLimitError: On rate limit (429).
            GmailError: On other errors.
        """
        if response.status_code == 401:
            raise GmailAuthError("Unauthorized: Access token expired or invalid")

        if response.status_code == 403:
            try:
                error_data = response.json()
                reason = error_data.get("error", {}).get("reason", "unknown")
                if "quotaExceeded" in reason:
                    raise GmailQuotaExceeded(f"Quota exceeded: {reason}")
            except Exception:
                pass
            raise GmailQuotaExceeded("Daily quota exceeded")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_seconds: int | None = None
            if retry_after:
                with contextlib.suppress(ValueError):
                    retry_after_seconds = int(retry_after)
            raise GmailRateLimitError("Rate limit exceeded", retry_after=retry_after_seconds)

        if response.status_code == 404:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", response.text)
                logger.error(f"Gmail 404 error - Full response: {error_data}")
                resource_type = message.split("'")[0].strip() if "'" in message else "resource"
                raise GmailNotFoundError(resource_type, message)
            except Exception as e:
                logger.error(f"Failed to parse 404 error: {response.text}")
                raise GmailNotFoundError("resource", response.text or "unknown")

        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise GmailError(f"API error: {message}", status_code=response.status_code)

        return response.json()  # type: ignore[no-any-return]

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable.

        Overrides base to handle token refresh on 401.

        Args:
            error: Exception to check.

        Returns:
            True if error should be retried.
        """
        # Retry on rate limit
        if isinstance(error, GmailRateLimitError):
            return True

        # Try token refresh on auth error
        if isinstance(error, GmailAuthError):
            try:
                # Note: Token refresh should be handled at a higher level
                # For now, we just indicate retry is possible
                logger.warning("Auth error - consider refreshing token")
                return False  # Don't retry here, let caller handle token refresh
            except Exception as e:
                logger.error(f"Token check failed: {e}")
                return False

        # Use base class logic for other errors
        return super()._is_retryable_error(error)

    # ==================== MESSAGES ====================

    async def list_messages(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        page_size: int = 10,
        page_token: str | None = None,
        include_spam_trash: bool = False,
    ) -> dict[str, Any]:
        """List messages from user's mailbox.

        Args:
            query: Gmail search query (e.g., "from:user@example.com", "has:attachment").
            label_ids: List of label IDs to filter by.
            page_size: Number of results per page (1-500, default 10).
            page_token: Page token for pagination.
            include_spam_trash: Include messages in SPAM and TRASH labels.

        Returns:
            Dict with messages list and pagination token.

        Raises:
            GmailError: If request fails.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 500)}

        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if page_token:
            params["pageToken"] = page_token
        if include_spam_trash:
            params["includeSpamTrash"] = True

        return await self.get(f"/v1/users/{self.user_id}/messages", params=params)

    async def get_message(self, message_id: str, format_type: str = "full") -> dict[str, Any]:
        """Get full message content and metadata.

        Args:
            message_id: Message ID to retrieve.
            format_type: Format for message content ("minimal", "full", "raw").

        Returns:
            Message dict with full content.

        Raises:
            GmailError: If request fails.
        """
        params = {"format": format_type}
        return await self.get(f"/v1/users/{self.user_id}/messages/{message_id}", params=params)

    async def send_message(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html: bool = False,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send email message.

        Args:
            to: Recipient email(s) as string or list.
            subject: Email subject line.
            body: Email body text or HTML.
            html: If True, body is treated as HTML. Defaults to plain text.
            cc: CC recipient(s).
            bcc: BCC recipient(s).
            reply_to: Reply-To header value.

        Returns:
            Dict with sent message ID.

        Raises:
            GmailError: If send fails.
        """
        # Convert lists to comma-separated strings
        to_str = ", ".join(to) if isinstance(to, list) else to
        cc_str = ", ".join(cc) if isinstance(cc, list) else (cc or "")
        bcc_str = ", ".join(bcc) if isinstance(bcc, list) else (bcc or "")

        # Create MIME message
        message = MIMEText(body, "html" if html else "plain")
        message["to"] = to_str
        message["subject"] = subject

        if cc_str:
            message["cc"] = cc_str
        if bcc_str:
            message["bcc"] = bcc_str
        if reply_to:
            message["reply-to"] = reply_to

        # Encode as base64url for Gmail API
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return await self.post(
            f"/v1/users/{self.user_id}/messages/send",
            json={"raw": raw_message},
        )

    async def send_message_with_attachment(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: str,
        html: bool = False,
    ) -> dict[str, Any]:
        """Send email with file attachment.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body text.
            attachment_path: Path to file to attach.
            html: If True, body is HTML.

        Returns:
            Dict with sent message ID.

        Raises:
            GmailError: If send fails or file cannot be read.
        """
        # Create multipart message
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject

        # Add body
        body_part = MIMEText(body, "html" if html else "plain")
        message.attach(body_part)

        # Add attachment
        try:
            with open(attachment_path, "rb") as attachment:
                attachment_data = attachment.read()
                filename = attachment_path.split("/")[-1]

                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                message.attach(part)
        except FileNotFoundError as e:
            raise GmailError(f"Attachment file not found: {attachment_path}") from e

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return await self.post(
            f"/v1/users/{self.user_id}/messages/send",
            json={"raw": raw_message},
        )

    async def delete_message(self, message_id: str) -> dict[str, Any]:
        """Permanently delete message.

        Args:
            message_id: ID of message to delete.

        Returns:
            Empty response.

        Raises:
            GmailError: If delete fails.
        """
        return await self.delete(f"/v1/users/{self.user_id}/messages/{message_id}")

    async def trash_message(self, message_id: str) -> dict[str, Any]:
        """Move message to trash.

        Args:
            message_id: ID of message to trash.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(f"/v1/users/{self.user_id}/messages/{message_id}/trash")

    async def untrash_message(self, message_id: str) -> dict[str, Any]:
        """Restore message from trash.

        Args:
            message_id: ID of message to restore.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(f"/v1/users/{self.user_id}/messages/{message_id}/untrash")

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        """Mark message as read.

        Args:
            message_id: ID of message to mark as read.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"removeLabelIds": ["UNREAD"]},
        )

    async def mark_as_unread(self, message_id: str) -> dict[str, Any]:
        """Mark message as unread.

        Args:
            message_id: ID of message to mark as unread.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"addLabelIds": ["UNREAD"]},
        )

    async def star_message(self, message_id: str) -> dict[str, Any]:
        """Star/flag message.

        Args:
            message_id: ID of message to star.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"addLabelIds": ["STARRED"]},
        )

    async def unstar_message(self, message_id: str) -> dict[str, Any]:
        """Remove star from message.

        Args:
            message_id: ID of message to unstar.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"removeLabelIds": ["STARRED"]},
        )

    async def archive_message(self, message_id: str) -> dict[str, Any]:
        """Archive message (remove from INBOX).

        Args:
            message_id: ID of message to archive.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"removeLabelIds": ["INBOX"]},
        )

    async def unarchive_message(self, message_id: str) -> dict[str, Any]:
        """Restore archived message to INBOX.

        Args:
            message_id: ID of message to restore.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"addLabelIds": ["INBOX"]},
        )

    # ==================== LABELS ====================

    async def list_labels(self) -> dict[str, Any]:
        """List all available labels.

        Returns:
            Dict with labels list.

        Raises:
            GmailError: If request fails.
        """
        return await self.get(f"/v1/users/{self.user_id}/labels")

    async def get_label(self, label_id: str) -> dict[str, Any]:
        """Get label details.

        Args:
            label_id: ID of label to retrieve.

        Returns:
            Label dict with details.

        Raises:
            GmailError: If request fails.
        """
        return await self.get(f"/v1/users/{self.user_id}/labels/{label_id}")

    async def create_label(
        self,
        name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show",
    ) -> dict[str, Any]:
        """Create new label.

        Args:
            name: Label name.
            label_list_visibility: Visibility in label list ("labelShow", "labelHide").
            message_list_visibility: Visibility in message list ("show", "hide").

        Returns:
            New label dict.

        Raises:
            GmailError: If creation fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/labels",
            json={
                "name": name,
                "labelListVisibility": label_list_visibility,
                "messageListVisibility": message_list_visibility,
            },
        )

    async def delete_label(self, label_id: str) -> dict[str, Any]:
        """Delete label.

        Args:
            label_id: ID of label to delete.

        Returns:
            Empty response.

        Raises:
            GmailError: If deletion fails.
        """
        return await self.delete(f"/v1/users/{self.user_id}/labels/{label_id}")

    async def add_label(self, message_id: str, label_id: str) -> dict[str, Any]:
        """Apply label to message.

        Args:
            message_id: ID of message to label.
            label_id: ID of label to apply.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"addLabelIds": [label_id]},
        )

    async def remove_label(self, message_id: str, label_id: str) -> dict[str, Any]:
        """Remove label from message.

        Args:
            message_id: ID of message.
            label_id: ID of label to remove.

        Returns:
            Updated message dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(
            f"/v1/users/{self.user_id}/messages/{message_id}/modify",
            json={"removeLabelIds": [label_id]},
        )

    # ==================== DRAFTS ====================

    async def list_drafts(
        self, page_size: int = 10, page_token: str | None = None
    ) -> dict[str, Any]:
        """List draft messages.

        Args:
            page_size: Number of results per page.
            page_token: Page token for pagination.

        Returns:
            Dict with drafts list.

        Raises:
            GmailError: If request fails.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 500)}
        if page_token:
            params["pageToken"] = page_token

        return await self.get(f"/v1/users/{self.user_id}/drafts", params=params)

    async def get_draft(self, draft_id: str) -> dict[str, Any]:
        """Get draft message details.

        Args:
            draft_id: ID of draft to retrieve.

        Returns:
            Draft dict with message content.

        Raises:
            GmailError: If request fails.
        """
        return await self.get(f"/v1/users/{self.user_id}/drafts/{draft_id}")

    async def create_draft(
        self, to: str, subject: str, body: str, html: bool = False
    ) -> dict[str, Any]:
        """Create draft message.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.
            html: If True, body is HTML.

        Returns:
            New draft dict.

        Raises:
            GmailError: If creation fails.
        """
        message = MIMEText(body, "html" if html else "plain")
        message["to"] = to
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return await self.post(
            f"/v1/users/{self.user_id}/drafts",
            json={"message": {"raw": raw_message}},
        )

    async def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send existing draft.

        Args:
            draft_id: ID of draft to send.

        Returns:
            Dict with sent message ID.

        Raises:
            GmailError: If send fails.
        """
        return await self.post(f"/v1/users/{self.user_id}/drafts/{draft_id}/send")

    async def delete_draft(self, draft_id: str) -> dict[str, Any]:
        """Delete draft message.

        Args:
            draft_id: ID of draft to delete.

        Returns:
            Empty response.

        Raises:
            GmailError: If deletion fails.
        """
        return await self.delete(f"/v1/users/{self.user_id}/drafts/{draft_id}")

    # ==================== THREADS ====================

    async def list_threads(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        page_size: int = 10,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List conversation threads.

        Args:
            query: Gmail search query to filter threads.
            label_ids: Filter by label IDs.
            page_size: Number of results per page.
            page_token: Page token for pagination.

        Returns:
            Dict with threads list.

        Raises:
            GmailError: If request fails.
        """
        params: dict[str, Any] = {"pageSize": min(page_size, 500)}

        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if page_token:
            params["pageToken"] = page_token

        return await self.get(f"/v1/users/{self.user_id}/threads", params=params)

    async def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Get complete thread with all messages.

        Args:
            thread_id: ID of thread to retrieve.

        Returns:
            Thread dict with all messages.

        Raises:
            GmailError: If request fails.
        """
        return await self.get(f"/v1/users/{self.user_id}/threads/{thread_id}")

    async def delete_thread(self, thread_id: str) -> dict[str, Any]:
        """Permanently delete thread.

        Args:
            thread_id: ID of thread to delete.

        Returns:
            Empty response.

        Raises:
            GmailError: If deletion fails.
        """
        return await self.delete(f"/v1/users/{self.user_id}/threads/{thread_id}")

    async def trash_thread(self, thread_id: str) -> dict[str, Any]:
        """Move thread to trash.

        Args:
            thread_id: ID of thread to trash.

        Returns:
            Updated thread dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(f"/v1/users/{self.user_id}/threads/{thread_id}/trash")

    async def untrash_thread(self, thread_id: str) -> dict[str, Any]:
        """Restore thread from trash.

        Args:
            thread_id: ID of thread to restore.

        Returns:
            Updated thread dict.

        Raises:
            GmailError: If request fails.
        """
        return await self.post(f"/v1/users/{self.user_id}/threads/{thread_id}/untrash")

    async def modify_thread(
        self,
        thread_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add or remove labels from thread.

        Args:
            thread_id: ID of thread to modify.
            add_labels: List of label IDs to add.
            remove_labels: List of label IDs to remove.

        Returns:
            Updated thread dict.

        Raises:
            GmailError: If request fails.
        """
        payload: dict[str, Any] = {}
        if add_labels:
            payload["addLabelIds"] = add_labels
        if remove_labels:
            payload["removeLabelIds"] = remove_labels

        return await self.post(f"/v1/users/{self.user_id}/threads/{thread_id}/modify", json=payload)

    # ==================== USER ====================

    async def get_user_profile(self) -> dict[str, Any]:
        """Get authenticated user's Gmail profile.

        Returns:
            User profile dict with email and message counts.

        Raises:
            GmailError: If request fails.
        """
        return await self.get(f"/v1/users/{self.user_id}/profile")

    # ==================== ATTACHMENTS ====================

    async def get_message_attachments(self, message_id: str) -> list[dict[str, Any]]:
        """Get list of attachments in message.

        Args:
            message_id: ID of message to check for attachments.

        Returns:
            List of attachment metadata dicts.

        Raises:
            GmailError: If request fails.
        """
        message = await self.get_message(message_id)
        attachments = []

        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        for part in parts:
            if part.get("filename"):
                attachments.append(
                    {
                        "id": part.get("partId"),
                        "filename": part.get("filename"),
                        "mimeType": part.get("mimeType"),
                    }
                )

        return attachments

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download attachment content.

        Args:
            message_id: ID of message containing attachment.
            attachment_id: ID of attachment to download.

        Returns:
            Binary content of attachment.

        Raises:
            GmailError: If download fails.
        """
        result = await self.get(
            f"/v1/users/{self.user_id}/messages/{message_id}/attachments/{attachment_id}"
        )

        data = result.get("data", "")
        # Decode base64url
        return base64.urlsafe_b64decode(data)
