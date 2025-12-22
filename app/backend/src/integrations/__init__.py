"""
Third-party API integrations.

This module exports all integration clients for external services.
Each client extends BaseIntegrationClient and provides:
- Async HTTP operations with connection pooling
- Exponential backoff retry logic
- Structured error handling
- Health check capabilities

Integration Clients (Email Finding - Waterfall Order):
    1. AnymailfinderClient: Email finding and verification (best for C-level executives)
    2. FindymailClient: Email finding for tech companies
    3. TombaClient: Domain-wide email discovery
    4. VoilaNorbertClient: Email finding (best for common names)
    5. IcypeasClient: Email finding (best for European contacts)
    6. MuraenaClient: B2B lead discovery and email verification
    7. NimblerClient: B2B contact enrichment
    8. MailVerifyClient: Email verification and deliverability checking

Orchestrator:
    - LeadEnrichmentWaterfall: Cascading email finder using all services

Data Management:
    - AirtableClient: Database management for leads, contacts, campaigns

Other Integrations:
    - InstantlyClient: Cold email automation and campaign management
    - ReoonClient: Email verification and deliverability monitoring

Example:
    >>> from src.integrations import LeadEnrichmentWaterfall
    >>> waterfall = LeadEnrichmentWaterfall(
    ...     anymailfinder_key="key1",  # pragma: allowlist secret
    ...     findymail_key="key2",  # pragma: allowlist secret
    ...     tomba_key="key3",  # pragma: allowlist secret
    ...     tomba_secret="secret3",  # pragma: allowlist secret
    ... )
    >>> result = await waterfall.find_email(
    ...     first_name="John",
    ...     last_name="Smith",
    ...     domain="company.com"
    ... )
    >>> if result.found:
    ...     print(f"Found via {result.source}: {result.email}")
"""

from src.integrations.airtable import (
    AirtableClient,
    AirtableError,
    AirtableNotFoundError,
    AirtableRecord,
    AirtableTable,
    AirtableValidationError,
    BatchResult,
    CellFormat,
    ListRecordsResult,
    SortConfig,
    SortDirection,
    UpsertResult,
)
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
from src.integrations.brave import (
    BraveClient,
    BraveError,
    BraveFaq,
    BraveFreshness,
    BraveImageResult,
    BraveImageSafesearch,
    BraveInfobox,
    BraveNewsResult,
    BraveSafesearch,
    BraveSearchResponse,
    BraveSearchType,
    BraveSuggestResponse,
    BraveVideoResult,
    BraveWebResult,
)
from src.integrations.findymail import (
    FindymailClient,
    FindymailEmailResult,
    FindymailEmailStatus,
    FindymailError,
    FindymailPhoneResult,
    FindymailVerificationResult,
)
from src.integrations.firecrawl import (
    CrawlJob,
    FirecrawlClient,
    FirecrawlError,
    ScrapedPage,
)
from src.integrations.icypeas import (
    IcypeasClient,
    IcypeasCreditsInfo,
    IcypeasEmailResult,
    IcypeasError,
    IcypeasSearchStatus,
    IcypeasVerificationResult,
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
from src.integrations.lead_enrichment import (
    EnrichmentResult,
    EnrichmentSource,
    LeadEnrichmentWaterfall,
    ServiceStats,
    WaterfallStats,
)
from src.integrations.mailverify import (
    MailVerifyBulkResult,
    MailVerifyClient,
    MailVerifyError,
    MailVerifyResult,
    MailVerifyStatus,
)
from src.integrations.muraena import (
    MuraenaClient,
    MuraenaContactResult,
    MuraenaCreditsInfo,
    MuraenaError,
    MuraenaVerificationResult,
)
from src.integrations.nimbler import (
    NimblerClient,
    NimblerCompanyResult,
    NimblerContactResult,
    NimblerError,
)
from src.integrations.perplexity import (
    PerplexityCitation,
    PerplexityClient,
    PerplexityConversation,
    PerplexityError,
    PerplexityMessage,
    PerplexityModel,
    PerplexityResponse,
    PerplexitySearchMode,
    PerplexityUsage,
)
from src.integrations.reddit import (
    RedditAuthError,
    RedditClient,
    RedditComment,
    RedditError,
    RedditPost,
    RedditRateLimitError,
    RedditSearchResult,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
    RedditUser,
    SubredditAnalysis,
)
from src.integrations.reoon import (
    ReoonAccountBalance,
    ReoonBulkTaskResult,
    ReoonBulkTaskStatus,
    ReoonBulkVerificationStatus,
    ReoonClient,
    ReoonError,
    ReoonVerificationMode,
    ReoonVerificationResult,
    ReoonVerificationStatus,
)
from src.integrations.serper import (
    SerperAnswerBox,
    SerperAutocompleteResult,
    SerperClient,
    SerperError,
    SerperImageResult,
    SerperKnowledgeGraph,
    SerperNewsResult,
    SerperOrganicResult,
    SerperPeopleAlsoAsk,
    SerperPlaceResult,
    SerperRelatedSearch,
    SerperScholarResult,
    SerperSearchResult,
    SerperSearchType,
    SerperShoppingResult,
    SerperVideoResult,
)
from src.integrations.tavily import (
    TavilyAnswer,
    TavilyCitationFormat,
    TavilyClient,
    TavilyContentFormat,
    TavilyCrawlResponse,
    TavilyCrawlResult,
    TavilyError,
    TavilyExtractDepth,
    TavilyImage,
    TavilyMapResponse,
    TavilyResearchModel,
    TavilyResearchTask,
    TavilySearchDepth,
    TavilySearchResponse,
    TavilySearchResult,
    TavilyTimeRange,
    TavilyTopic,
    TavilyUsageResponse,
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
from src.integrations.voilanorbert import (
    VoilaNorbertAccountInfo,
    VoilaNorbertClient,
    VoilaNorbertEmailResult,
    VoilaNorbertEmailStatus,
    VoilaNorbertError,
    VoilaNorbertVerificationResult,
)

__all__ = [
    # Base
    "BaseIntegrationClient",
    "IntegrationError",
    "AuthenticationError",
    "PaymentRequiredError",
    "RateLimitError",
    # Brave Search (Privacy-Focused Web Search)
    "BraveClient",
    "BraveError",
    "BraveSafesearch",
    "BraveImageSafesearch",
    "BraveFreshness",
    "BraveSearchType",
    "BraveSearchResponse",
    "BraveSuggestResponse",
    "BraveWebResult",
    "BraveNewsResult",
    "BraveImageResult",
    "BraveVideoResult",
    "BraveInfobox",
    "BraveFaq",
    # Airtable
    "AirtableClient",
    "AirtableError",
    "AirtableNotFoundError",
    "AirtableValidationError",
    "AirtableRecord",
    "AirtableTable",
    "BatchResult",
    "CellFormat",
    "ListRecordsResult",
    "SortConfig",
    "SortDirection",
    "UpsertResult",
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
    # VoilaNorbert
    "VoilaNorbertClient",
    "VoilaNorbertError",
    "VoilaNorbertEmailResult",
    "VoilaNorbertEmailStatus",
    "VoilaNorbertVerificationResult",
    "VoilaNorbertAccountInfo",
    # Icypeas
    "IcypeasClient",
    "IcypeasError",
    "IcypeasEmailResult",
    "IcypeasSearchStatus",
    "IcypeasVerificationResult",
    "IcypeasCreditsInfo",
    # Muraena
    "MuraenaClient",
    "MuraenaError",
    "MuraenaContactResult",
    "MuraenaVerificationResult",
    "MuraenaCreditsInfo",
    # Nimbler
    "NimblerClient",
    "NimblerError",
    "NimblerContactResult",
    "NimblerCompanyResult",
    # MailVerify
    "MailVerifyClient",
    "MailVerifyError",
    "MailVerifyResult",
    "MailVerifyBulkResult",
    "MailVerifyStatus",
    # Lead Enrichment Waterfall
    "LeadEnrichmentWaterfall",
    "EnrichmentResult",
    "EnrichmentSource",
    "ServiceStats",
    "WaterfallStats",
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
    # Reoon
    "ReoonClient",
    "ReoonError",
    "ReoonVerificationResult",
    "ReoonVerificationStatus",
    "ReoonVerificationMode",
    "ReoonAccountBalance",
    "ReoonBulkTaskResult",
    "ReoonBulkTaskStatus",
    "ReoonBulkVerificationStatus",
    # Reddit (Research & Niche Analysis)
    "RedditClient",
    "RedditError",
    "RedditAuthError",
    "RedditRateLimitError",
    "RedditSortType",
    "RedditTimeFilter",
    "RedditSubreddit",
    "RedditPost",
    "RedditComment",
    "RedditUser",
    "RedditSearchResult",
    "SubredditAnalysis",
    # Serper (Google Search API)
    "SerperClient",
    "SerperError",
    "SerperSearchType",
    "SerperSearchResult",
    "SerperOrganicResult",
    "SerperKnowledgeGraph",
    "SerperAnswerBox",
    "SerperPeopleAlsoAsk",
    "SerperRelatedSearch",
    "SerperImageResult",
    "SerperNewsResult",
    "SerperPlaceResult",
    "SerperVideoResult",
    "SerperShoppingResult",
    "SerperScholarResult",
    "SerperAutocompleteResult",
    # Tavily (AI-Powered Search)
    "TavilyClient",
    "TavilyError",
    "TavilyTopic",
    "TavilySearchDepth",
    "TavilyTimeRange",
    "TavilySearchResponse",
    "TavilySearchResult",
    "TavilyAnswer",
    "TavilyImage",
    "TavilyCrawlResponse",
    "TavilyCrawlResult",
    "TavilyMapResponse",
    "TavilyUsageResponse",
    "TavilyResearchTask",
    "TavilyResearchModel",
    "TavilyCitationFormat",
    "TavilyExtractDepth",
    "TavilyContentFormat",
    # Perplexity (AI Research & Q&A)
    "PerplexityClient",
    "PerplexityError",
    "PerplexityModel",
    "PerplexitySearchMode",
    "PerplexityResponse",
    "PerplexityCitation",
    "PerplexityUsage",
    "PerplexityMessage",
    "PerplexityConversation",
    # Firecrawl (Web Scraping)
    "FirecrawlClient",
    "FirecrawlError",
    "ScrapedPage",
    "CrawlJob",
]
