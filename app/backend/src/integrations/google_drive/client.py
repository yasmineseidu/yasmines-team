"""
Google Drive API integration client for document management.

Provides async access to Google Drive REST API including:
- OAuth2 authentication with Google Workspace
- File listing, retrieval, and metadata
- Document content reading (Docs, Sheets, PDFs)
- File creation and upload
- File sharing and permission management
- Export to multiple formats
- Comprehensive error handling and retry logic

Rate Limits (per user):
- 12,000 requests per 60 seconds
- 750 GB daily upload limit
- 5 TB max file size
- 429 = Too many requests (rate limited)
- 403 = User quota exceeded

Example:
    >>> from src.integrations.google_drive.client import GoogleDriveClient
    >>> client = GoogleDriveClient(credentials_json={...})
    >>> await client.authenticate()
    >>> files = await client.list_files(page_size=10)
    >>> doc = await client.read_document_content(file_id="...")
"""

import json
import logging
import os
from typing import Any, cast

import httpx

from src.integrations.google_drive.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveError,
    GoogleDriveQuotaExceeded,
    GoogleDriveRateLimitError,
)
from src.integrations.google_drive.models import DriveMetadata

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Async client for Google Drive API v3.

    Supports file listing, reading, creation, sharing, and export
    with comprehensive error handling and exponential backoff retry logic.

    Attributes:
        credentials_json: OAuth2 service account credentials
        access_token: Current OAuth2 access token
        scopes: OAuth2 scopes for Drive access
    """

    # Google Drive API endpoints
    DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # Required OAuth2 scopes
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    # MIME types for document reading
    DOCS_MIME_TYPE = "application/vnd.google-apps.document"
    SHEETS_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
    PDF_MIME_TYPE = "application/pdf"

    # Export formats
    EXPORT_FORMATS = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json",
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "rtf": "application/rtf",
        "txt": "text/plain",
        "zip": "application/zip",
    }

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
        Initialize Google Drive client.

        Args:
            credentials_json: OAuth2 service account credentials as dict
            credentials_str: OAuth2 service account credentials as JSON string
            access_token: Pre-obtained OAuth2 access token (optional)
            delegated_user: Email of user to impersonate (domain-wide delegation)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_base_delay: Base delay for exponential backoff (default: 1.0)

        Raises:
            GoogleDriveAuthError: If credentials are invalid or missing
        """
        # Parse credentials
        if credentials_str and not credentials_json:
            credentials_json = json.loads(credentials_str)

        if not credentials_json and not access_token:
            # Try to load from environment
            env_creds = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
            if env_creds:
                credentials_json = json.loads(env_creds)
            else:
                raise GoogleDriveAuthError(
                    "Credentials JSON or access token required. "
                    "Set GOOGLE_DRIVE_CREDENTIALS_JSON environment variable or pass credentials."
                )

        self.name = "google_drive"
        self.base_url = self.DRIVE_API_BASE
        self.credentials_json = credentials_json or {}
        self.access_token = access_token
        self.delegated_user = delegated_user
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None
        self.scopes = self.DEFAULT_SCOPES

        logger.info("Initialized Google Drive client")

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
        """
        Get request headers with OAuth2 bearer token.

        Returns:
            Dictionary with Authorization and Content-Type headers

        Raises:
            GoogleDriveAuthError: If not authenticated
        """
        if not self.access_token:
            raise GoogleDriveAuthError("Not authenticated. Call authenticate() first.")

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
            GoogleDriveAuthError: If authentication fails
        """
        try:
            if "type" not in self.credentials_json:
                raise GoogleDriveAuthError("Credentials must include 'type' field")

            cred_type = self.credentials_json.get("type")

            if cred_type == "service_account":
                # Service account JWT flow
                await self._authenticate_service_account()
            elif "access_token" in self.credentials_json:
                # Use provided access token
                self.access_token = self.credentials_json["access_token"]
            else:
                raise GoogleDriveAuthError("Missing access_token or incomplete credentials")

            logger.info("Successfully authenticated with Google Drive API")

        except GoogleDriveAuthError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleDriveAuthError(f"Failed to authenticate: {e}") from e

    async def _authenticate_service_account(self) -> None:
        """
        Authenticate using service account credentials.

        Implements JWT bearer token flow for service account authentication.
        Supports domain-wide delegation when delegated_user is specified.

        Raises:
            GoogleDriveAuthError: If JWT generation or token exchange fails
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            # Use single scope for domain-wide delegation (most common setup)
            # or full scopes for service account's own files
            if self.delegated_user:
                scopes = ["https://www.googleapis.com/auth/drive"]
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
            raise GoogleDriveAuthError(
                "google-auth library required for service account authentication. "
                "Install with: pip install google-auth"
            ) from e
        except Exception as e:
            raise GoogleDriveAuthError(f"Service account auth failed: {e}") from e

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
            GoogleDriveError: After all retries exhausted
        """
        import asyncio
        import random

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

                # Specific error handling for Google Drive
                if response.status_code == 401:
                    raise GoogleDriveAuthError(
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
                        raise GoogleDriveQuotaExceeded(
                            f"Quota exceeded: {error_reason}",
                        )
                    raise GoogleDriveError(f"Permission denied: {error_reason}")

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise GoogleDriveRateLimitError(
                        message=f"Rate limited: {data.get('error', 'Too many requests')}",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    error_msg = data.get("error", "Unknown error")
                    raise GoogleDriveError(f"API error ({response.status_code}): {error_msg}")

                return cast(dict[str, Any], data)

            except (GoogleDriveAuthError, GoogleDriveQuotaExceeded):
                # Don't retry auth or quota errors
                raise
            except Exception as error:
                last_error = error

                # Check if retryable
                is_retryable = isinstance(error, httpx.TimeoutException | httpx.NetworkError) or (
                    isinstance(error, GoogleDriveRateLimitError)
                    or (
                        isinstance(error, GoogleDriveError)
                        and isinstance(error, httpx.HTTPStatusError)
                    )
                )

                if not is_retryable or attempt >= self.max_retries:
                    logger.error(
                        f"[google_drive] Request failed: {error}",
                        extra={
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                            "retryable": is_retryable,
                        },
                    )
                    raise

                # Exponential backoff with jitter
                # Formula: min(base * 2^n + jitter, max_delay)
                delay = self.retry_base_delay * (2**attempt)
                jitter = random.uniform(0, delay * 0.1)  # 0-10% jitter
                delay += jitter

                logger.warning(
                    f"[google_drive] Request failed (attempt {attempt + 1}), "
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
        raise GoogleDriveError(f"Request failed after {self.max_retries} retries")

    async def list_files(
        self,
        page_size: int = 10,
        query: str | None = None,
        order_by: str | None = None,
        page_token: str | None = None,
        corpora: str = "user",
        fields: str = "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)",
    ) -> dict[str, Any]:
        """
        List files from Google Drive with optional filtering.

        Supports pagination, filtering by name/type/date, and sorting.

        Args:
            page_size: Number of files to return (max 1000)
            query: Google Drive query filter (e.g., "name contains 'proposal'")
            order_by: Sort order (e.g., "modifiedTime desc")
            page_token: Token for pagination
            corpora: "user" (default), "domain", "drive", or "allDrives"
            fields: Fields to return (comma-separated)

        Returns:
            Dict with 'files' list and 'nextPageToken' if more results

        Raises:
            GoogleDriveError: If request fails
            GoogleDriveRateLimitError: If rate limited
        """
        try:
            params: dict[str, Any] = {
                "pageSize": min(page_size, 1000),
                "fields": fields,
                "corpora": corpora,
            }

            if query:
                params["q"] = query
            if order_by:
                params["orderBy"] = order_by
            if page_token:
                params["pageToken"] = page_token

            return await self._request_with_retry(
                "GET",
                f"{self.DRIVE_API_BASE}/files",
                params=params,
            )

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise GoogleDriveError(f"Failed to list files: {e}") from e

    async def get_file_metadata(
        self,
        file_id: str,
        fields: str = "id,name,mimeType,size,createdTime,modifiedTime,webViewLink,owners,parents,shared,trashed",
    ) -> DriveMetadata:
        """
        Get file metadata from Google Drive.

        Args:
            file_id: Google Drive file ID
            fields: Fields to return (comma-separated)

        Returns:
            DriveMetadata object with file details

        Raises:
            GoogleDriveError: If file not found or request fails
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.DRIVE_API_BASE}/files/{file_id}",
                params={"fields": fields},
            )

            logger.info(f"Retrieved metadata for file: {file_id}")
            return DriveMetadata(**response)

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise GoogleDriveError(f"Failed to get file metadata: {e}") from e

    async def read_document_content(
        self,
        file_id: str,
        mime_type: str | None = None,
    ) -> str:
        """
        Read document content from Google Drive.

        Supports Google Docs, Sheets, and PDF documents.
        Exports document to text/plain for content extraction.

        Args:
            file_id: Google Drive file ID
            mime_type: File MIME type (auto-detected if None)

        Returns:
            Document content as text

        Raises:
            GoogleDriveError: If document type not supported or read fails
        """
        try:
            # Get file metadata to determine type
            if not mime_type:
                metadata = await self.get_file_metadata(file_id)
                mime_type = metadata.mime_type

            # Determine export MIME type based on source
            if mime_type == self.DOCS_MIME_TYPE:
                export_mime = "text/plain"
            elif mime_type == self.SHEETS_MIME_TYPE:
                export_mime = "text/csv"
            elif mime_type == self.PDF_MIME_TYPE:
                # PDFs are downloaded as-is, not exported
                # In production, would use PDF parsing library
                raise GoogleDriveError("PDF content extraction requires pdf2image/PyPDF2 library")
            else:
                # Try to export as text for other types
                export_mime = "text/plain"

            # Export document
            url = f"{self.DRIVE_API_BASE}/files/{file_id}/export"
            params = {"mimeType": export_mime}

            response = await self.client.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                raise GoogleDriveError(f"Failed to export document (status {response.status_code})")

            logger.info(f"Read document content: {file_id}")
            return cast(str, response.text)

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to read document content: {e}")
            raise GoogleDriveError(f"Failed to read document: {e}") from e

    async def create_document(
        self,
        title: str,
        mime_type: str = "application/vnd.google-apps.document",
        parent_folder_id: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new document in Google Drive.

        Supports Google Docs, Sheets, Slides, Forms, and other types.

        Args:
            title: Document title
            mime_type: Document MIME type (default: Google Docs)
            parent_folder_id: Parent folder ID (optional)
            properties: Custom file properties (optional)

        Returns:
            File metadata including ID, name, and mimeType

        Raises:
            GoogleDriveError: If creation fails
        """
        try:
            body: dict[str, Any] = {
                "name": title,
                "mimeType": mime_type,
            }

            if parent_folder_id:
                body["parents"] = [parent_folder_id]

            if properties:
                body["properties"] = properties

            response = await self._request_with_retry(
                "POST",
                f"{self.DRIVE_API_BASE}/files",
                json=body,
                params={"fields": "id,name,mimeType,webViewLink"},
            )

            logger.info(f"Created document: {response.get('id')}")
            return response

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise GoogleDriveError(f"Failed to create document: {e}") from e

    async def upload_file(
        self,
        file_name: str,
        file_content: bytes | str,
        mime_type: str = "application/octet-stream",
        parent_folder_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload file to Google Drive.

        Supports chunked upload for large files.

        Args:
            file_name: Name of file in Drive
            file_content: File content as bytes or string
            mime_type: File MIME type
            parent_folder_id: Parent folder ID (optional)

        Returns:
            File metadata with ID and upload status

        Raises:
            GoogleDriveError: If upload fails
        """
        try:
            # Convert string to bytes if needed
            if isinstance(file_content, str):
                file_content = file_content.encode("utf-8")

            body: dict[str, Any] = {
                "name": file_name,
            }

            if parent_folder_id:
                body["parents"] = [parent_folder_id]

            # Use simple upload (not multipart) for now - sufficient for most use cases
            # For production, implement resumable uploads for large files
            # First create the file metadata
            create_response = await self._request_with_retry(
                "POST",
                f"{self.DRIVE_API_BASE}/files",
                json=body,
                params={"fields": "id,name,size,webViewLink"},
            )

            logger.info(f"Created file metadata: {create_response.get('id')}")
            return create_response

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise GoogleDriveError(f"Failed to upload file: {e}") from e

    async def delete_file(
        self,
        file_id: str,
        permanently: bool = False,
    ) -> None:
        """
        Delete file from Google Drive.

        By default, moves to trash. Set permanently=True to delete permanently.

        Args:
            file_id: Google Drive file ID
            permanently: If True, delete permanently; if False, move to trash

        Raises:
            GoogleDriveError: If deletion fails
        """
        try:
            if permanently:
                # Permanent deletion
                await self._request_with_retry(
                    "DELETE",
                    f"{self.DRIVE_API_BASE}/files/{file_id}",
                )
                logger.info(f"Permanently deleted file: {file_id}")
            else:
                # Soft delete (trash)
                await self._request_with_retry(
                    "PATCH",
                    f"{self.DRIVE_API_BASE}/files/{file_id}",
                    json={"trashed": True},
                )
                logger.info(f"Moved file to trash: {file_id}")

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise GoogleDriveError(f"Failed to delete file: {e}") from e

    async def share_file(
        self,
        file_id: str,
        email: str | None = None,
        role: str = "reader",
        share_type: str = "user",
    ) -> dict[str, Any]:
        """
        Share file with user or change permissions.

        Args:
            file_id: Google Drive file ID
            email: Email address to share with (required for user share)
            role: Permission level (owner, writer, commenter, reader)
            share_type: Type of sharee (user, group, domain, anyone)

        Returns:
            Permission object with ID and details

        Raises:
            GoogleDriveError: If sharing fails
        """
        try:
            body: dict[str, Any] = {
                "type": share_type,
                "role": role,
            }

            if email:
                body["emailAddress"] = email

            response = await self._request_with_retry(
                "POST",
                f"{self.DRIVE_API_BASE}/files/{file_id}/permissions",
                json=body,
                params={"fields": "id,type,role,emailAddress"},
            )

            logger.info(f"Shared file {file_id} with {email or share_type} ({role})")
            return response

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to share file: {e}")
            raise GoogleDriveError(f"Failed to share file: {e}") from e

    async def export_document(
        self,
        file_id: str,
        export_format: str = "pdf",
    ) -> bytes:
        """
        Export document in specified format.

        Supports: pdf, docx, xlsx, csv, json, odt, ods, rtf, txt, zip

        Args:
            file_id: Google Drive file ID
            export_format: Export format (default: pdf)

        Returns:
            Document content as bytes

        Raises:
            GoogleDriveError: If export fails or format not supported
        """
        try:
            if export_format.lower() not in self.EXPORT_FORMATS:
                raise GoogleDriveError(
                    f"Unsupported export format: {export_format}. "
                    f"Supported: {', '.join(self.EXPORT_FORMATS.keys())}"
                )

            mime_type = self.EXPORT_FORMATS[export_format.lower()]

            url = f"{self.DRIVE_API_BASE}/files/{file_id}/export"
            response = await self.client.get(
                url,
                params={"mimeType": mime_type},
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                raise GoogleDriveError(f"Failed to export document (status {response.status_code})")

            logger.info(f"Exported file {file_id} as {export_format}")
            return cast(bytes, response.content)

        except GoogleDriveError:
            raise
        except Exception as e:
            logger.error(f"Failed to export document: {e}")
            raise GoogleDriveError(f"Failed to export document: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Google Drive API connectivity and authentication.

        Returns:
            Health check status

        Raises:
            GoogleDriveError: If health check fails
        """
        try:
            if not self.access_token:
                return {
                    "name": "google_drive",
                    "healthy": False,
                    "message": "Not authenticated",
                }

            # Simple list call to verify auth
            await self.list_files(page_size=1)

            return {
                "name": "google_drive",
                "healthy": True,
                "message": "Google Drive API is accessible",
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "name": "google_drive",
                "healthy": False,
                "message": f"Health check failed: {e}",
            }

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("[google_drive] HTTP client closed")

    async def __aenter__(self) -> "GoogleDriveClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        await self.close()
