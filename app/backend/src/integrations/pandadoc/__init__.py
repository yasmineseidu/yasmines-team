"""PandaDoc API client integration.

Provides async access to PandaDoc REST API including:
- Document template management
- Document creation and PDF generation
- E-signature workflows
- Recipient and signing status management
- Webhook management and verification

Rate Limits:
- 50 requests per minute for most endpoints
- Create Document from Template: 500/min
- Download Document: 100/min
- Sliding window approach (60-second window)
- 429 = Rate limited (retry with backoff)

API Key:
- Store as PANDADOC_API_KEY in .env
- Format: Bearer token in Authorization header

Example:
    >>> from src.integrations.pandadoc import PandaDocClient
    >>> client = PandaDocClient(api_key=os.environ["PANDADOC_API_KEY"])
    >>> templates = await client.list_templates()
    >>> doc = await client.create_document(
    ...     name="My Agreement",
    ...     template_id="template_123",
    ...     recipients=[{"email": "john@example.com", "name": "John Doe"}]
    ... )
    >>> await client.send_document(document_id=doc.id)
"""

from src.integrations.pandadoc.client import PandaDocClient
from src.integrations.pandadoc.exceptions import (
    PandaDocAPIError,
    PandaDocAuthError,
    PandaDocConfigError,
    PandaDocError,
    PandaDocNotFoundError,
    PandaDocRateLimitError,
)
from src.integrations.pandadoc.models import (
    Document,
    Recipient,
    Signature,
    Template,
)

__all__ = [
    "PandaDocClient",
    "PandaDocError",
    "PandaDocConfigError",
    "PandaDocAuthError",
    "PandaDocAPIError",
    "PandaDocNotFoundError",
    "PandaDocRateLimitError",
    "Document",
    "Template",
    "Recipient",
    "Signature",
]
