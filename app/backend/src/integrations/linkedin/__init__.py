"""LinkedIn API integration for social selling and B2B outreach."""

from src.integrations.linkedin.client import LinkedInClient
from src.integrations.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInForbiddenError,
    LinkedInNotFoundError,
    LinkedInRateLimitError,
    LinkedInValidationError,
)
from src.integrations.linkedin.models import (
    ConnectionDegree,
    LinkedInComment,
    LinkedInConnection,
    LinkedInConversation,
    LinkedInMessage,
    LinkedInPost,
    LinkedInProfile,
    LinkedInSearchResponse,
    LinkedInSearchResult,
    MessageDeliveryStatus,
    PostVisibility,
)
from src.integrations.linkedin.tools import LINKEDIN_TOOLS

__all__ = [
    # Client
    "LinkedInClient",
    # Exceptions
    "LinkedInError",
    "LinkedInAuthError",
    "LinkedInRateLimitError",
    "LinkedInForbiddenError",
    "LinkedInNotFoundError",
    "LinkedInValidationError",
    # Models
    "LinkedInProfile",
    "LinkedInPost",
    "LinkedInComment",
    "LinkedInMessage",
    "LinkedInConnection",
    "LinkedInConversation",
    "LinkedInSearchResult",
    "LinkedInSearchResponse",
    # Enums
    "PostVisibility",
    "ConnectionDegree",
    "MessageDeliveryStatus",
    # Tools
    "LINKEDIN_TOOLS",
]
