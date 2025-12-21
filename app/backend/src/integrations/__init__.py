"""
Third-party API integrations.

This module exports all integration clients for external services.
Each client extends BaseIntegrationClient and provides:
- Async HTTP operations with connection pooling
- Exponential backoff retry logic
- Structured error handling
- Health check capabilities

Integration Clients:
    - AnymailfinderClient: Email finding and verification (first in waterfall)

Example:
    >>> from src.integrations import AnymailfinderClient
    >>> client = AnymailfinderClient(api_key="your-key")
    >>> result = await client.find_person_email(
    ...     first_name="John",
    ...     last_name="Doe",
    ...     domain="example.com"
    ... )
"""

from src.integrations.anymailfinder import (
    AccountInfo,
    AnymailfinderClient,
    AnymailfinderError,
    EmailResult,
    EmailStatus,
    VerificationResult,
)
from src.integrations.base import (
    AuthenticationError,
    BaseIntegrationClient,
    IntegrationError,
    PaymentRequiredError,
    RateLimitError,
)

__all__ = [
    # Base
    "BaseIntegrationClient",
    "IntegrationError",
    "AuthenticationError",
    "PaymentRequiredError",
    "RateLimitError",
    # Anymailfinder
    "AnymailfinderClient",
    "AnymailfinderError",
    "EmailResult",
    "EmailStatus",
    "VerificationResult",
    "AccountInfo",
]
