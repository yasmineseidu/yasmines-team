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
    - FindymailClient: Email finding for tech companies (second in waterfall)
    - TombaClient: Domain-wide email discovery (third in waterfall)
    - InstantlyClient: Cold email automation and campaign management

Example:
    >>> from src.integrations import AnymailfinderClient, FindymailClient, TombaClient
    >>> # Email finding
    >>> email_client = AnymailfinderClient(api_key="your-key")
    >>> result = await email_client.find_person_email(
    ...     first_name="John",
    ...     last_name="Doe",
    ...     domain="example.com"
    ... )
    >>> # Domain-wide search
    >>> tomba_client = TombaClient(api_key="ta_xxx", api_secret="ts_xxx")
    >>> result = await tomba_client.search_domain("stripe.com")
    >>> for email in result.emails:
    ...     print(f"{email.email} - {email.position}")
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
from src.integrations.findymail import (
    FindymailClient,
    FindymailEmailResult,
    FindymailEmailStatus,
    FindymailError,
    FindymailPhoneResult,
    FindymailVerificationResult,
)
from src.integrations.instantly import (
    BackgroundJob,
    BulkAddResult,
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    InstantlyClient,
    InstantlyError,
    Lead,
    LeadInterestStatus,
)
from src.integrations.tomba import (
    TombaAccountInfo,
    TombaClient,
    TombaDomainSearchResult,
    TombaEmail,
    TombaEmailCountResult,
    TombaEmailFinderResult,
    TombaEmailType,
    TombaError,
    TombaVerificationResult,
    TombaVerificationStatus,
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
    # Findymail
    "FindymailClient",
    "FindymailError",
    "FindymailEmailResult",
    "FindymailEmailStatus",
    "FindymailVerificationResult",
    "FindymailPhoneResult",
    # Instantly
    "InstantlyClient",
    "InstantlyError",
    "Campaign",
    "CampaignStatus",
    "CampaignAnalytics",
    "Lead",
    "LeadInterestStatus",
    "BulkAddResult",
    "BackgroundJob",
    # Tomba
    "TombaClient",
    "TombaError",
    "TombaAccountInfo",
    "TombaEmail",
    "TombaEmailType",
    "TombaEmailFinderResult",
    "TombaEmailCountResult",
    "TombaDomainSearchResult",
    "TombaVerificationResult",
    "TombaVerificationStatus",
]
