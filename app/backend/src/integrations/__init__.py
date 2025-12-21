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
    - InstantlyClient: Cold email automation and campaign management

Example:
    >>> from src.integrations import AnymailfinderClient, FindymailClient, InstantlyClient
    >>> # Email finding
    >>> email_client = AnymailfinderClient(api_key="your-key")
    >>> result = await email_client.find_person_email(
    ...     first_name="John",
    ...     last_name="Doe",
    ...     domain="example.com"
    ... )
    >>> # Campaign management
    >>> campaign_client = InstantlyClient(api_key="your-key")
    >>> campaign = await campaign_client.create_campaign(
    ...     name="Q1 Outreach",
    ...     campaign_schedule={"schedules": [...]}
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
]
