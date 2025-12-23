"""PandaDoc API client implementation.

Async HTTP client for PandaDoc REST API with comprehensive error handling,
retry logic, rate limiting, and webhook support.
"""

import asyncio
import logging
import os
import random
from typing import Any

import httpx

from src.integrations.pandadoc.exceptions import (
    PandaDocAPIError,
    PandaDocAuthError,
    PandaDocConfigError,
    PandaDocNotFoundError,
    PandaDocRateLimitError,
)
from src.integrations.pandadoc.models import (
    Document,
    DocumentsListResponse,
    Recipient,
    Signature,
    Template,
    TemplatesListResponse,
)

logger = logging.getLogger(__name__)


class PandaDocClient:
    """Async client for PandaDoc REST API.

    Provides methods for managing documents, templates, recipients,
    e-signatures, and webhooks with comprehensive error handling
    and exponential backoff retry logic.

    Attributes:
        api_key: PandaDoc API key for authentication.
        base_url: Base URL for PandaDoc API.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts for transient errors.
        retry_base_delay: Base delay for exponential backoff.
    """

    BASE_URL = "https://api.pandadoc.com/public/v1"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize PandaDoc client.

        Args:
            api_key: PandaDoc API key. If not provided, uses PANDADOC_API_KEY env var.
            timeout: Request timeout in seconds (default: 30).
            max_retries: Maximum retry attempts (default: 3).
            retry_base_delay: Base delay for exponential backoff (default: 1.0).

        Raises:
            PandaDocConfigError: If API key is not provided and env var not set.
        """
        if not api_key:
            api_key = os.getenv("PANDADOC_API_KEY")

        if not api_key:
            raise PandaDocConfigError(
                "API key required. Provide api_key parameter or set PANDADOC_API_KEY "
                "environment variable."
            )

        self.name = "pandadoc"
        self.api_key = api_key
        self.base_url = self.BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

        logger.info("Initialized PandaDoc client")

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy HTTP client creation with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get default headers for API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        return {
            "Authorization": f"API-Key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            endpoint: API endpoint path.
            **kwargs: Additional arguments for httpx request.

        Returns:
            Parsed JSON response.

        Raises:
            PandaDocRateLimitError: If rate limit exceeded (429).
            PandaDocAuthError: If authentication fails (401, 403).
            PandaDocNotFoundError: If resource not found (404).
            PandaDocAPIError: For other API errors.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        delay = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                        delay = min(delay, retry_after)
                        logger.warning(
                            f"Rate limited. Retrying in {delay:.2f}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    raise PandaDocRateLimitError(
                        "Rate limit exceeded",
                        retry_after=retry_after,
                        status_code=429,
                        response_data=response.json() if response.text else {},
                    )

                # Handle authentication errors
                if response.status_code in (401, 403):
                    raise PandaDocAuthError(
                        f"Authentication failed: {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.json() if response.text else {},
                    )

                # Handle not found errors
                if response.status_code == 404:
                    raise PandaDocNotFoundError(
                        "Resource not found",
                        status_code=404,
                        response_data=response.json() if response.text else {},
                    )

                # Handle other HTTP errors
                if response.status_code >= 400:
                    if attempt < self.max_retries and response.status_code >= 500:
                        delay = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Server error {response.status_code}. Retrying in {delay:.2f}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    raise PandaDocAPIError(
                        f"API request failed: {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.json() if response.text else {},
                    )

                # Success
                response.raise_for_status()
                return response.json() if response.text else {}

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Connection error: {e}. Retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue

                raise PandaDocAPIError(
                    f"Connection failed: {str(e)}",
                ) from e

        return {}

    # ============== TEMPLATE OPERATIONS ==============

    async def list_templates(
        self,
        query: str | None = None,
    ) -> TemplatesListResponse:
        """List available templates.

        Args:
            query: Search query for templates (optional).

        Returns:
            TemplatesListResponse with templates list.

        Raises:
            PandaDocAPIError: If API request fails.
        """
        params: dict[str, Any] = {}
        if query:
            params["q"] = query

        response = await self._request(
            "GET",
            "/templates",
            params=params if params else None,
        )

        return TemplatesListResponse(**response)

    async def get_template(self, template_id: str) -> Template:
        """Get template details.

        Args:
            template_id: ID of the template to retrieve.

        Returns:
            Template details.

        Raises:
            PandaDocNotFoundError: If template not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            f"/templates/{template_id}",
        )

        return Template(**response)

    async def create_template(
        self,
        name: str,
        source: dict[str, Any],
        tags: list[str] | None = None,
    ) -> Template:
        """Create a new template.

        Args:
            name: Template name.
            source: Template source (PDF URL, image, etc.).
            tags: Optional list of tags for organization.

        Returns:
            Created template.

        Raises:
            PandaDocAPIError: If API request fails.
        """
        data = {
            "name": name,
            "source": source,
        }
        if tags:
            data["tags"] = tags

        response = await self._request(
            "POST",
            "/templates",
            json=data,
        )

        return Template(**response)

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: ID of the template to delete.

        Returns:
            True if successful.

        Raises:
            PandaDocNotFoundError: If template not found.
            PandaDocAPIError: If API request fails.
        """
        await self._request(
            "DELETE",
            f"/templates/{template_id}",
        )

        return True

    # ============== DOCUMENT OPERATIONS ==============

    async def create_document(
        self,
        name: str,
        template_id: str,
        recipients: list[Recipient] | list[dict[str, Any]],
        fields: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Create a document from template.

        Args:
            name: Document name.
            template_id: ID of template to use.
            recipients: List of recipients (email, name, role, etc.).
            fields: Template field values (optional).
            metadata: Custom metadata (optional).

        Returns:
            Created document.

        Raises:
            PandaDocNotFoundError: If template not found.
            PandaDocAPIError: If API request fails.
        """
        # Convert Recipient models to dict if needed
        recipients_data: list[dict[str, Any]] = []
        for r in recipients:
            if hasattr(r, "model_dump"):
                recipients_data.append(r.model_dump(by_alias=True, exclude_none=True))
            else:
                recipients_data.append(r)

        data: dict[str, Any] = {
            "name": name,
            "template_uuid": template_id,
            "recipients": recipients_data,
        }

        if fields:
            data["fields"] = fields

        if metadata:
            data["metadata"] = metadata

        response = await self._request(
            "POST",
            "/documents",
            json=data,
        )

        doc = Document(**response)

        # Poll until document is processed from "uploaded" to "draft" status
        if doc.id and doc.status == "document.uploaded":
            max_attempts = 30
            interval = 1.0
            for attempt in range(max_attempts):
                await asyncio.sleep(interval)
                try:
                    status_doc = await self.get_document(doc.id)
                    if status_doc.status == "document.draft":
                        doc = status_doc
                        break
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    continue

        return doc

    async def get_document(self, document_id: str) -> Document:
        """Get document details.

        Args:
            document_id: ID of the document to retrieve.

        Returns:
            Document details.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            f"/documents/{document_id}",
        )

        return Document(**response)

    async def list_documents(
        self,
        status: str | None = None,
    ) -> DocumentsListResponse:
        """List documents.

        Args:
            status: Filter by status (e.g., document.draft, document.sent, document.completed).

        Returns:
            DocumentsListResponse with documents list.

        Raises:
            PandaDocAPIError: If API request fails.
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status

        response = await self._request(
            "GET",
            "/documents",
            params=params if params else None,
        )

        return DocumentsListResponse(**response)

    async def send_document(
        self,
        document_id: str,
        message: str | None = None,
        subject: str | None = None,
    ) -> Document:
        """Send document to recipients.

        Args:
            document_id: ID of document to send.
            message: Optional message to include in email.
            subject: Optional email subject.

        Returns:
            Updated document.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        data: dict[str, Any] = {}
        if message:
            data["message"] = message
        if subject:
            data["subject"] = subject

        response = await self._request(
            "POST",
            f"/documents/{document_id}/send",
            json=data if data else {},
        )

        return Document(**response)

    async def download_document(self, document_id: str) -> bytes:
        """Download document as PDF.

        Args:
            document_id: ID of document to download.

        Returns:
            PDF file content as bytes.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self.client.get(
            f"{self.base_url}/documents/{document_id}/download",
            headers=self._get_headers(),
        )

        if response.status_code >= 400:
            raise PandaDocAPIError(
                f"Failed to download document: {response.status_code}",
                status_code=response.status_code,
            )

        return response.content

    async def get_document_status(self, document_id: str) -> dict[str, Any]:
        """Get document signing status.

        Args:
            document_id: ID of document.

        Returns:
            Document status and recipient signing status.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            f"/documents/{document_id}/status",
        )

        return response

    # ============== RECIPIENT OPERATIONS ==============

    async def add_recipient(
        self,
        document_id: str,
        email: str,
        name: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Add recipient to document.

        Args:
            document_id: ID of document.
            email: Recipient email address.
            name: Recipient name (optional).
            role: Recipient role like signer, approver (optional).

        Returns:
            Updated recipient data.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        data: dict[str, Any] = {"email": email}
        if name:
            data["name"] = name
        if role:
            data["role"] = role

        response = await self._request(
            "POST",
            f"/documents/{document_id}/recipients",
            json=data,
        )

        return response

    async def update_recipient(
        self,
        document_id: str,
        recipient_email: str,
        name: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Update document recipient.

        Args:
            document_id: ID of document.
            recipient_email: Email of recipient to update.
            name: New recipient name (optional).
            role: New recipient role (optional).

        Returns:
            Updated recipient data.

        Raises:
            PandaDocNotFoundError: If document or recipient not found.
            PandaDocAPIError: If API request fails.
        """
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if role:
            data["role"] = role

        response = await self._request(
            "PUT",
            f"/documents/{document_id}/recipients/{recipient_email}",
            json=data,
        )

        return response

    async def remove_recipient(
        self,
        document_id: str,
        recipient_email: str,
    ) -> bool:
        """Remove recipient from document.

        Args:
            document_id: ID of document.
            recipient_email: Email of recipient to remove.

        Returns:
            True if successful.

        Raises:
            PandaDocNotFoundError: If document or recipient not found.
            PandaDocAPIError: If API request fails.
        """
        await self._request(
            "DELETE",
            f"/documents/{document_id}/recipients/{recipient_email}",
        )

        return True

    async def get_recipient_status(
        self,
        document_id: str,
        recipient_email: str,
    ) -> Signature:
        """Get recipient signing status.

        Args:
            document_id: ID of document.
            recipient_email: Email of recipient.

        Returns:
            Recipient signature status.

        Raises:
            PandaDocNotFoundError: If document or recipient not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            f"/documents/{document_id}/recipients/{recipient_email}/status",
        )

        return Signature(**response)

    # ============== E-SIGNATURE OPERATIONS ==============

    async def get_signature_requests(
        self,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """Get signature requests for a document.

        Args:
            document_id: ID of document.

        Returns:
            List of signature requests.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            f"/documents/{document_id}/signature_requests",
        )

        # Handle both list and dict responses
        if isinstance(response, dict):
            requests_data: Any = response.get("requests", [])
            if isinstance(requests_data, list):
                return requests_data
            return []
        return response if isinstance(response, list) else []

    async def update_signature_request(
        self,
        document_id: str,
        recipient_email: str,
        status: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update signature request status.

        Args:
            document_id: ID of document.
            recipient_email: Email of recipient.
            status: New status (e.g., "completed", "declined").
            **kwargs: Additional data for the update.

        Returns:
            Updated signature request.

        Raises:
            PandaDocNotFoundError: If document or recipient not found.
            PandaDocAPIError: If API request fails.
        """
        data = {"status": status, **kwargs}

        response = await self._request(
            "PUT",
            f"/documents/{document_id}/signature_requests/{recipient_email}",
            json=data,
        )

        return response

    async def cancel_signature_request(
        self,
        document_id: str,
        recipient_email: str,
    ) -> bool:
        """Cancel signature request for recipient.

        Args:
            document_id: ID of document.
            recipient_email: Email of recipient.

        Returns:
            True if successful.

        Raises:
            PandaDocNotFoundError: If document or recipient not found.
            PandaDocAPIError: If API request fails.
        """
        await self._request(
            "DELETE",
            f"/documents/{document_id}/signature_requests/{recipient_email}",
        )

        return True

    # ============== WEBHOOK OPERATIONS ==============

    async def create_webhook(
        self,
        url: str,
        events: list[str],
    ) -> dict[str, Any]:
        """Create webhook subscription.

        Args:
            url: Webhook URL for callbacks.
            events: List of events to subscribe to
                   (e.g., ["document.sent", "document.completed"]).

        Returns:
            Created webhook configuration.

        Raises:
            PandaDocAPIError: If API request fails.
        """
        data = {
            "url": url,
            "events": events,
        }

        response = await self._request(
            "POST",
            "/webhooks",
            json=data,
        )

        return response

    async def list_webhooks(self) -> list[dict[str, Any]]:
        """List all webhook subscriptions.

        Returns:
            List of webhook configurations.

        Raises:
            PandaDocAPIError: If API request fails.
        """
        response = await self._request(
            "GET",
            "/webhooks",
        )

        # Handle both list and dict responses
        if isinstance(response, dict):
            webhooks_data: Any = response.get("webhooks", [])
            if isinstance(webhooks_data, list):
                return webhooks_data
            return []
        return response if isinstance(response, list) else []

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook subscription.

        Args:
            webhook_id: ID of webhook to delete.

        Returns:
            True if successful.

        Raises:
            PandaDocNotFoundError: If webhook not found.
            PandaDocAPIError: If API request fails.
        """
        await self._request(
            "DELETE",
            f"/webhooks/{webhook_id}",
        )

        return True

    # ============== FUTURE-PROOF DYNAMIC ENDPOINT CALLING ==============

    async def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call any endpoint dynamically - future-proof for new API releases.

        This method allows calling new endpoints that may be released in the future
        without requiring code changes to the client.

        Args:
            endpoint: Endpoint path (e.g., "/v1/new-feature")
            method: HTTP method (default: "GET")
            **kwargs: Request parameters (json, params, headers, etc.)

        Returns:
            API response as dictionary.

        Raises:
            PandaDocAPIError: If API request fails.

        Example:
            >>> # Call a new endpoint released in the future
            >>> result = await client.call_endpoint(
            ...     "/v1/new-feature",
            ...     method="POST",
            ...     json={"param": "value"}
            ... )
            >>> # Call with query parameters
            >>> result = await client.call_endpoint(
            ...     "/v1/documents",
            ...     params={"status": "completed", "limit": 100}
            ... )
        """
        return await self._request(method, endpoint, **kwargs)

    # ============== UTILITY OPERATIONS ==============

    async def poll_document_status(
        self,
        document_id: str,
        max_attempts: int = 30,
        interval: float = 2.0,
    ) -> dict[str, Any]:
        """Poll document status until completion.

        Polls document status with exponential backoff until document
        is no longer in processing state.

        Args:
            document_id: ID of document to monitor.
            max_attempts: Maximum polling attempts (default: 30).
            interval: Initial polling interval in seconds (default: 2.0).

        Returns:
            Final document status.

        Raises:
            PandaDocNotFoundError: If document not found.
            PandaDocAPIError: If API request fails.
        """
        for attempt in range(max_attempts):
            status = await self.get_document_status(document_id)

            # Check if processing is complete
            doc_status = status.get("status", "unknown")
            if doc_status not in ("draft", "processing"):
                return status

            # Exponential backoff
            wait_time = interval * (1.5**attempt)
            logger.debug(
                f"Document still processing. Waiting {wait_time:.2f}s "
                f"(attempt {attempt + 1}/{max_attempts})"
            )
            await asyncio.sleep(wait_time)

        # Max attempts reached
        logger.warning(f"Document {document_id} still processing after {max_attempts} attempts")
        return status

    async def close(self) -> None:
        """Close HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "PandaDocClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
