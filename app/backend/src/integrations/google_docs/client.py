"""
Google Docs API integration client for document generation and management.

Provides async access to Google Docs REST API including:
- OAuth2 authentication with Google Workspace
- Document creation and retrieval
- Text insertion and formatting
- Batch update operations
- Table management
- Document sharing and permissions

Rate Limits:
- 300 read requests/min per user
- 60 write requests/min per user
- Batch operations count as 1 request regardless of subrequests

Example:
    >>> from src.integrations.google_docs.client import GoogleDocsClient
    >>> client = GoogleDocsClient(
    ...     credentials_json={
    ...         "type": "service_account",
    ...         "project_id": "...",
    ...         "private_key": "..."
    ...     }
    ... )
    >>> doc = await client.create_document(
    ...     title="My Proposal",
    ...     template_id="standard_proposal"
    ... )
    >>> await client.insert_text(doc.document_id, "Hello World")
"""

import json
import logging
import os
from typing import Any

import httpx

from src.integrations.base import IntegrationError

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class GoogleDocsError(IntegrationError):
    """Base exception for Google Docs API errors."""

    pass


class GoogleDocsAuthError(GoogleDocsError):
    """Raised when Google Docs authentication fails."""

    def __init__(
        self,
        message: str = "Google Docs authentication failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class GoogleDocsRateLimitError(GoogleDocsError):
    """Raised when Google Docs API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Docs API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class GoogleDocsQuotaError(GoogleDocsError):
    """Raised when quota exceeded or project limits reached."""

    pass


# ============================================================================
# CLIENT
# ============================================================================


class GoogleDocsClient:
    """
    Async client for Google Docs API v1.

    Supports document creation, content insertion, formatting, batch operations,
    and sharing with comprehensive error handling and retry logic.

    Attributes:
        credentials_json: Service account credentials dictionary
        scopes: OAuth2 scopes (documents, documents.readonly, drive.file)
        access_token: Current OAuth2 access token (set by authenticate method)
    """

    # Google API endpoints
    DOCS_API_BASE = "https://docs.googleapis.com/v1"
    DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"

    # Required OAuth2 scopes
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        access_token: str | None = None,
        delegated_user: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """
        Initialize Google Docs client.

        Args:
            credentials_json: Service account credentials as dictionary
            credentials_str: Service account credentials as JSON string
            access_token: Pre-obtained OAuth2 access token (optional)
            delegated_user: Email of user to impersonate (domain-wide delegation)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)

        Raises:
            GoogleDocsAuthError: If credentials are invalid or missing
        """
        # Parse credentials
        if credentials_str and not credentials_json:
            credentials_json = json.loads(credentials_str)

        if not credentials_json and not access_token:
            # Try to load from environment
            env_creds = os.getenv("GOOGLE_DOCS_CREDENTIALS_JSON")
            if env_creds:
                # Check if it's a file path or JSON string
                if env_creds.startswith("{"):
                    credentials_json = json.loads(env_creds)
                elif os.path.exists(env_creds):
                    with open(env_creds) as f:
                        credentials_json = json.load(f)
                else:
                    raise GoogleDocsAuthError(f"Credentials file not found: {env_creds}")
            else:
                raise GoogleDocsAuthError(
                    "Credentials JSON or access token required. "
                    "Set GOOGLE_DOCS_CREDENTIALS_JSON environment variable or pass credentials."
                )

        self.name = "google_docs"
        self.base_url = self.DOCS_API_BASE
        self.credentials_json = credentials_json or {}
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None
        self.scopes = self.DEFAULT_SCOPES
        self.project_id = self.credentials_json.get("project_id")

        logger.info(f"Initialized {self.name} client (project: {self.project_id})")

    @property
    def client(self) -> httpx.AsyncClient:
        """
        Lazy HTTP client creation with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with OAuth2 bearer token.

        Returns:
            Dictionary with Authorization and Content-Type headers
        """
        if not self.access_token:
            raise GoogleDocsAuthError("Not authenticated. Call authenticate() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def authenticate(self) -> None:
        """
        Authenticate with Google using credentials.

        For service account: obtains OAuth2 access token using JWT flow.
        For user credentials: uses existing token or refresh token.

        Raises:
            GoogleDocsAuthError: If authentication fails
        """
        try:
            if "type" not in self.credentials_json and not self.access_token:
                raise GoogleDocsAuthError(
                    "Credentials must include 'type' field or access_token must be provided"
                )

            cred_type = self.credentials_json.get("type")

            if cred_type == "service_account":
                # Service account JWT flow
                await self._authenticate_service_account()
            elif "access_token" in self.credentials_json:
                # Use provided access token
                self.access_token = self.credentials_json["access_token"]
            elif self.access_token:
                # Already have access token
                pass
            else:
                raise GoogleDocsAuthError("Missing access_token or incomplete credentials")

            logger.info("Successfully authenticated with Google Docs API")

        except GoogleDocsAuthError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleDocsAuthError(f"Failed to authenticate: {e}") from e

    async def _authenticate_service_account(self) -> None:
        """
        Authenticate using service account credentials.

        Implements JWT bearer token flow for service account authentication.
        Supports domain-wide delegation when delegated_user is specified.

        Raises:
            GoogleDocsAuthError: If JWT generation or token exchange fails
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            # Use both Docs and Drive scopes for domain-wide delegation
            # (needed because create_document uses Drive API)
            # or full scopes for service account's own documents
            if self.delegated_user:
                scopes = [
                    "https://www.googleapis.com/auth/documents",
                    "https://www.googleapis.com/auth/drive.file",
                ]
            else:
                scopes = self.DEFAULT_SCOPES

            # Create credentials from service account JSON
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scopes,
            )

            # Apply domain-wide delegation if delegated_user is specified
            if self.delegated_user:
                credentials = credentials.with_subject(self.delegated_user)
                logger.info(f"Using domain-wide delegation for: {self.delegated_user}")

            # Refresh to get access token
            request = Request()
            credentials.refresh(request)
            self.access_token = credentials.token

            logger.info("Service account authenticated successfully")

        except ImportError as e:
            raise GoogleDocsAuthError(
                "google-auth library required for service account authentication. "
                "Install with: pip install google-auth"
            ) from e
        except Exception as e:
            raise GoogleDocsAuthError(f"Service account auth failed: {e}") from e

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Implements truncated exponential backoff with jitter for rate limiting.
        Detects 403 (quota exceeded) and 429 (rate limited) errors specifically.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL for the request
            headers: Custom headers (merged with default headers)
            **kwargs: Additional arguments for httpx request

        Returns:
            Parsed JSON response

        Raises:
            GoogleDocsError: After all retries exhausted
        """
        import asyncio
        import random
        from typing import cast

        if headers is None:
            headers = {}
        headers.update(self._get_headers())

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )

                # Handle response
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_response": response.text}

                # Specific error handling for Google Docs
                if response.status_code == 401:
                    raise GoogleDocsAuthError(
                        f"Authentication failed: {data.get('error', 'Unknown')}",
                    )

                if response.status_code == 403:
                    # Check if it's quota exceeded or permission error
                    error_msg = data.get("error", {})
                    if isinstance(error_msg, dict):
                        error_reason = error_msg.get("message", "")
                    else:
                        error_reason = str(error_msg)

                    if "quota" in error_reason.lower() or "limit" in error_reason.lower():
                        raise GoogleDocsQuotaError(
                            f"Quota exceeded: {error_reason}",
                        )
                    raise GoogleDocsError(f"Permission denied: {error_reason}")

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise GoogleDocsRateLimitError(
                        message=f"Rate limited: {data.get('error', 'Too many requests')}",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code == 404:
                    raise GoogleDocsError(f"Not found: {data.get('error', 'Resource not found')}")

                if response.status_code >= 400:
                    error_msg = data.get("error", "Unknown error")
                    raise GoogleDocsError(f"API error ({response.status_code}): {error_msg}")

                return cast(dict[str, Any], data)

            except (GoogleDocsAuthError, GoogleDocsQuotaError):
                # Don't retry auth or quota errors
                raise
            except Exception as error:
                last_error = error

                # Check if retryable
                is_retryable = isinstance(
                    error,
                    httpx.TimeoutException | httpx.NetworkError | GoogleDocsRateLimitError,
                )

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[google_docs] Request failed: {error}",
                        extra={
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Exponential backoff with jitter
                delay = self.retry_base_delay * (2**attempt)
                jitter = random.uniform(0, delay * 0.1)  # 0-10% jitter
                delay += jitter

                logger.warning(
                    f"[google_docs] Request failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {error}",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "delay": delay,
                    },
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise GoogleDocsError(f"Request failed after {self.max_retries} retries")

    async def create_document(
        self,
        title: str,
        parent_folder_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Google Doc.

        Args:
            title: Document title
            parent_folder_id: Google Drive folder ID (optional)

        Returns:
            Document metadata including documentId

        Raises:
            GoogleDocsError: If document creation fails
            GoogleDocsRateLimitError: If rate limited
        """
        try:
            # Use Drive API to create document
            body: dict[str, Any] = {
                "name": title,
                "mimeType": "application/vnd.google-apps.document",
            }
            if parent_folder_id:
                body["parents"] = [parent_folder_id]

            response = await self._request_with_retry(
                "POST",
                f"{self.DRIVE_API_BASE}/files",
                json=body,
            )

            document_id = response.get("id")
            logger.info(f"Created Google Doc: {document_id}")

            return {
                "documentId": document_id,
                "title": title,
                "mimeType": "application/vnd.google-apps.document",
            }

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Failed to create document: {e}") from e

    async def get_document(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve document metadata and content.

        Args:
            document_id: Google Doc ID

        Returns:
            Document structure including body, title, and metadata

        Raises:
            GoogleDocsError: If retrieval fails
            GoogleDocsRateLimitError: If rate limited
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.DOCS_API_BASE}/documents/{document_id}",
            )

            logger.info(f"Retrieved document: {document_id}")
            return response

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Failed to get document: {e}") from e

    async def insert_text(
        self,
        document_id: str,
        text: str,
        index: int = 1,
    ) -> dict[str, Any]:
        """
        Insert text into document.

        Args:
            document_id: Google Doc ID
            text: Text to insert
            index: Position in document (1-based)

        Returns:
            Batch update response

        Raises:
            GoogleDocsError: If insertion fails
            GoogleDocsRateLimitError: If rate limited
        """
        requests = [
            {
                "insertText": {
                    "text": text,
                    "location": {"index": index},
                }
            }
        ]

        response = await self.batch_update(document_id, requests)
        logger.info(f"Inserted {len(text)} characters into {document_id}")
        return response

    async def batch_update(
        self,
        document_id: str,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute batch update operations on document.

        Batch operations allow multiple updates in a single request:
        - Insert text/images
        - Format text (bold, italic, colors)
        - Create tables
        - Manage styles
        - Update permissions

        Args:
            document_id: Google Doc ID
            requests: List of update request objects

        Returns:
            Batch update response with applied changes

        Raises:
            GoogleDocsError: If batch update fails
            GoogleDocsRateLimitError: If rate limited

        Example:
            >>> requests = [
            ...     {
            ...         "insertText": {
            ...             "text": "Hello ",
            ...             "location": {"index": 1}
            ...         }
            ...     },
            ...     {
            ...         "updateTextStyle": {
            ...             "range": {"startIndex": 1, "endIndex": 6},
            ...             "textStyle": {"bold": True},
            ...             "fields": "bold"
            ...         }
            ...     }
            ... ]
            >>> result = await client.batch_update(doc_id, requests)
        """
        try:
            response = await self._request_with_retry(
                "POST",
                f"{self.DOCS_API_BASE}/documents/{document_id}:batchUpdate",
                json={"requests": requests},
            )

            logger.info(f"Executed {len(requests)} batch operations on {document_id}")
            return response

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Batch update failed ({len(requests)} operations): {e}") from e

    async def format_text(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        font_size: int | None = None,
        text_color: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Format text in document (bold, italic, color, etc).

        Args:
            document_id: Google Doc ID
            start_index: Start position of text to format
            end_index: End position of text to format
            bold: Make text bold
            italic: Make text italic
            underline: Underline text
            font_size: Font size in points
            text_color: RGB color dict {"red": 0.0, "green": 0.0, "blue": 0.0}

        Returns:
            Batch update response

        Raises:
            GoogleDocsError: If formatting fails
        """
        text_style: dict[str, Any] = {}
        fields: list[str] = []

        if bold is not None:
            text_style["bold"] = bold
            fields.append("bold")
        if italic is not None:
            text_style["italic"] = italic
            fields.append("italic")
        if underline is not None:
            text_style["underline"] = underline
            fields.append("underline")
        if font_size is not None:
            text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
            fields.append("fontSize")
        if text_color is not None:
            text_style["foregroundColor"] = text_color
            fields.append("foregroundColor")

        requests = [
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "textStyle": text_style,
                    "fields": ",".join(fields),
                }
            }
        ]

        return await self.batch_update(document_id, requests)

    async def create_table(
        self,
        document_id: str,
        rows: int,
        columns: int,
        index: int = 1,
    ) -> dict[str, Any]:
        """
        Create a table in the document.

        Args:
            document_id: Google Doc ID
            rows: Number of rows
            columns: Number of columns
            index: Position in document

        Returns:
            Batch update response

        Raises:
            GoogleDocsError: If table creation fails
        """
        requests = [
            {
                "insertTable": {
                    "rows": rows,
                    "columns": columns,
                    "location": {"index": index},
                }
            }
        ]

        return await self.batch_update(document_id, requests)

    async def share_document(
        self,
        document_id: str,
        email: str,
        role: str = "reader",
    ) -> dict[str, Any]:
        """
        Share document with user.

        Args:
            document_id: Google Doc ID
            email: Email address to share with
            role: "reader", "commenter", or "writer"

        Returns:
            Share response

        Raises:
            GoogleDocsError: If sharing fails
        """
        try:
            response = await self._request_with_retry(
                "POST",
                f"{self.DRIVE_API_BASE}/files/{document_id}/permissions",
                json={
                    "type": "user",
                    "emailAddress": email,
                    "role": role,
                },
            )

            logger.info(f"Shared document {document_id} with {email} ({role})")
            return response

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Failed to share document: {e}") from e

    async def get_document_permissions(
        self,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get document sharing permissions.

        Args:
            document_id: Google Doc ID

        Returns:
            List of permission objects

        Raises:
            GoogleDocsError: If retrieval fails
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.DRIVE_API_BASE}/files/{document_id}/permissions",
            )

            permissions_data: list[dict[str, Any]] = response.get("permissions", [])
            logger.info(f"Retrieved {len(permissions_data)} permissions")
            return permissions_data

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Failed to get permissions: {e}") from e

    async def delete_document(
        self,
        document_id: str,
        permanently: bool = False,
    ) -> None:
        """
        Delete document from Google Drive.

        By default, moves to trash. Set permanently=True to delete permanently.

        Args:
            document_id: Google Doc ID
            permanently: If True, delete permanently; if False, move to trash

        Raises:
            GoogleDocsError: If deletion fails
        """
        try:
            if permanently:
                # Permanent deletion
                await self._request_with_retry(
                    "DELETE",
                    f"{self.DRIVE_API_BASE}/files/{document_id}",
                )
                logger.info(f"Permanently deleted document: {document_id}")
            else:
                # Soft delete (trash)
                await self._request_with_retry(
                    "PATCH",
                    f"{self.DRIVE_API_BASE}/files/{document_id}",
                    json={"trashed": True},
                )
                logger.info(f"Moved document to trash: {document_id}")

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDocsRateLimitError):
            raise
        except Exception as e:
            raise GoogleDocsError(f"Failed to delete document: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Google Docs API connectivity and authentication.

        Returns:
            Health check status

        Raises:
            GoogleDocsError: If health check fails
        """
        try:
            if not self.access_token:
                return {
                    "name": "google_docs",
                    "healthy": False,
                    "message": "Not authenticated",
                }

            # Simple about API call to verify auth
            response = await self._request_with_retry(
                "GET",
                f"{self.DRIVE_API_BASE}/about",
                params={"fields": "user"},
            )

            return {
                "name": "google_docs",
                "healthy": True,
                "message": "Google Docs API is accessible",
                "user": response.get("user", {}).get("emailAddress", "unknown"),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "name": "google_docs",
                "healthy": False,
                "message": f"Health check failed: {e}",
            }

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("[google_docs] HTTP client closed")

    async def __aenter__(self) -> "GoogleDocsClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        await self.close()
