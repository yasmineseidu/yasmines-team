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
from typing import Any

from src.integrations.base import BaseIntegrationClient, IntegrationError

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


class GoogleDocsClient(BaseIntegrationClient):
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

    def __init__(
        self,
        credentials_json: dict[str, Any] | None = None,
        credentials_str: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Google Docs client.

        Args:
            credentials_json: Service account credentials as dictionary
            credentials_str: Service account credentials as JSON string
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)

        Raises:
            GoogleDocsAuthError: If credentials are invalid or missing
        """
        super().__init__(
            name="google_docs",
            base_url=self.DOCS_API_BASE,
            api_key="",  # OAuth2 doesn't use simple API key
            timeout=timeout,
            max_retries=max_retries,
        )

        # Parse credentials
        if credentials_str and not credentials_json:
            credentials_json = json.loads(credentials_str)

        if not credentials_json:
            raise GoogleDocsAuthError("Credentials JSON is required")

        # Validate required credentials fields
        if "type" not in credentials_json:
            raise GoogleDocsAuthError("Credentials must include 'type' field")
        if "access_token" not in credentials_json:
            raise GoogleDocsAuthError("Credentials must include 'access_token' field")

        self.credentials_json = credentials_json
        self.access_token: str | None = credentials_json.get("access_token")
        self.project_id = credentials_json.get("project_id")
        self.scopes = [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.file",
        ]

        logger.info(f"Initialized {self.name} client (project: {self.project_id})")

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
        Authenticate with Google using service account credentials.

        Uses service account private key to obtain OAuth2 access token.

        Raises:
            GoogleDocsAuthError: If authentication fails
        """
        try:
            # In production, use google-auth library
            # For now, assume token is provided in credentials
            # This would be expanded with actual JWT flow
            if "access_token" in self.credentials_json:
                self.access_token = self.credentials_json["access_token"]
            else:
                # Would implement JWT bearer flow here
                raise GoogleDocsAuthError("No access_token in credentials")

            logger.info("Successfully authenticated with Google Docs API")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleDocsAuthError(f"Failed to authenticate: {e}") from e

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
        headers = self._get_headers()

        try:
            # Use Drive API to create document
            response = await self.post(
                f"{self.DRIVE_API_BASE}/files",
                headers=headers,
                json={
                    "name": title,
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [parent_folder_id] if parent_folder_id else [],
                },
            )

            document_id = response.get("id")
            logger.info(f"Created Google Doc: {document_id}")

            return {
                "documentId": document_id,
                "title": title,
                "mimeType": "application/vnd.google-apps.document",
            }

        except IntegrationError as e:
            if e.status_code == 429:
                raise GoogleDocsRateLimitError(str(e)) from e
            if e.status_code == 401:
                raise GoogleDocsAuthError(str(e)) from e
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
        headers = self._get_headers()

        try:
            response = await self.get(
                f"/documents/{document_id}",
                headers=headers,
            )

            logger.info(f"Retrieved document: {document_id}")
            return response

        except IntegrationError as e:
            if e.status_code == 429:
                raise GoogleDocsRateLimitError(str(e)) from e
            if e.status_code == 404:
                raise GoogleDocsError(f"Document not found: {document_id}") from e
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

        try:
            response = await self.batch_update(document_id, requests)
            logger.info(f"Inserted {len(text)} characters into {document_id}")
            return response

        except (GoogleDocsError, GoogleDocsRateLimitError):
            raise
        except IntegrationError as e:
            if e.status_code == 429:
                raise GoogleDocsRateLimitError(str(e)) from e
            raise GoogleDocsError(f"Failed to insert text: {e}") from e

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
        headers = self._get_headers()

        try:
            response = await self.post(
                f"/documents/{document_id}:batchUpdate",
                headers=headers,
                json={"requests": requests},
            )

            logger.info(f"Executed {len(requests)} batch operations on {document_id}")
            return response

        except IntegrationError as e:
            if e.status_code == 429:
                raise GoogleDocsRateLimitError(str(e)) from e
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
        headers = self._get_headers()

        try:
            response = await self.post(
                f"{self.DRIVE_API_BASE}/files/{document_id}/permissions",
                headers=headers,
                json={
                    "type": "user",
                    "emailAddress": email,
                    "role": role,
                },
            )

            logger.info(f"Shared document {document_id} with {email} ({role})")
            return response

        except IntegrationError as e:
            if e.status_code == 429:
                raise GoogleDocsRateLimitError(str(e)) from e
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
        headers = self._get_headers()

        try:
            response = await self.get(
                f"{self.DRIVE_API_BASE}/files/{document_id}/permissions",
                headers=headers,
            )

            permissions_data: list[dict[str, Any]] = response.get("permissions", [])
            logger.info(f"Retrieved {len(permissions_data)} permissions")
            return permissions_data

        except IntegrationError as e:
            raise GoogleDocsError(f"Failed to get permissions: {e}") from e
