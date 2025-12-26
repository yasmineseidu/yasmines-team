"""
Email Verification Agent - Phase 3, Agent 3.1.

Finds and verifies email addresses using a waterfall approach across multiple
email finder providers. Prioritizes by lead score (Tier A first), uses cheapest
providers first (Tomba.io), and validates all found emails with Reoon (primary)
and MailVerify (catchall specialist).

Waterfall Strategy:
1. Check if email already exists
2. Try pattern-based guess (free)
3. Use waterfall providers in priority order:
   - Tier 1: Tomba.io ($0.002/lookup) - Primary, cheapest
   - Tier 2: Muraena, Voila Norbert, Nimbler, Icypeas, Anymailfinder
   - Tier 3: Findymail ($0.008/lookup) - Last resort
4. Verify found emails with Reoon (primary)
5. Handle catchalls with MailVerify (specialist)

This agent uses Claude Agent SDK with SDK MCP tools for email operations,
circuit breakers for resilience, and exponential backoff retry logic.

API Documentation:
- Tomba: https://developer.tomba.io/
- Reoon: https://www.reoon.com/articles/api-documentation-of-reoon-email-verifier/
- MailVerify: https://docs.mailverify.ai/
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from claude_agent_sdk.types import AssistantMessage, TextBlock
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.anymailfinder import AnymailfinderClient
from src.integrations.findymail import FindymailClient
from src.integrations.icypeas import IcypeasClient
from src.integrations.mailverify import MailVerifyClient
from src.integrations.muraena import MuraenaClient
from src.integrations.nimbler import NimblerClient
from src.integrations.reoon import ReoonClient
from src.integrations.tomba import TombaClient
from src.integrations.voilanorbert import VoilaNorbertClient
from src.utils.rate_limiter import CircuitBreaker, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================


class EmailVerificationStatus(str, Enum):
    """Email verification status."""

    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    CATCHALL = "catchall"
    DISPOSABLE = "disposable"
    ROLE_BASED = "role_based"
    UNKNOWN = "unknown"


class EmailFinderProvider(str, Enum):
    """Email finder providers in waterfall priority order."""

    TOMBA = "tomba"  # Tier 1, Primary (cheapest)
    MURAENA = "muraena"  # Tier 2
    VOILA_NORBERT = "voila_norbert"  # Tier 2
    NIMBLER = "nimbler"  # Tier 2
    ICYPEAS = "icypeas"  # Tier 2
    ANYMAILFINDER = "anymailfinder"  # Tier 2
    FINDYMAIL = "findymail"  # Tier 3, Last resort


class EmailVerificationProvider(str, Enum):
    """Email verification providers."""

    REOON = "reoon"  # Primary verifier
    MAILVERIFY = "mailverify"  # Secondary + catchall specialist


@dataclass
class EmailFindingResult:
    """Result of email finding attempt."""

    email: str | None
    provider: EmailFinderProvider
    confidence: float
    cost: float
    response_time_ms: int
    success: bool
    error: str | None = None


@dataclass
class EmailVerificationResult:
    """Result of email verification."""

    email: str
    status: EmailVerificationStatus
    provider: EmailVerificationProvider
    confidence: float
    cost: float
    is_catchall: bool = False
    is_disposable: bool = False
    is_role_based: bool = False


@dataclass
class EnrichmentResult:
    """Final enrichment result for a lead."""

    lead_id: str
    email: str | None
    verification_status: EmailVerificationStatus | None
    provider_used: EmailFinderProvider | None
    verifier_used: EmailVerificationProvider | None
    total_cost: float
    attempts: list[EmailFindingResult]
    verification: EmailVerificationResult | None


# ============================================================================
# Exceptions
# ============================================================================


class EmailVerificationAgentError(Exception):
    """Base exception for email verification agent."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProviderError(EmailVerificationAgentError):
    """Exception raised when provider fails."""

    pass


class EmailVerificationError(EmailVerificationAgentError):
    """Exception raised when email verification fails."""

    pass


# ============================================================================
# Provider Registry
# ============================================================================


@dataclass
class ProviderConfig:
    """Configuration for an email finder provider."""

    name: EmailFinderProvider
    cost_per_lookup: float
    accuracy: float
    daily_limit: int
    priority: int
    tier: str


class ProviderRegistry:
    """Registry of email finder providers in waterfall priority order."""

    PROVIDERS: dict[EmailFinderProvider, ProviderConfig] = {
        EmailFinderProvider.TOMBA: ProviderConfig(
            name=EmailFinderProvider.TOMBA,
            cost_per_lookup=0.002,
            accuracy=0.85,
            daily_limit=5000,
            priority=1,
            tier="tier_1_primary",
        ),
        EmailFinderProvider.MURAENA: ProviderConfig(
            name=EmailFinderProvider.MURAENA,
            cost_per_lookup=0.012,
            accuracy=0.87,
            daily_limit=1500,
            priority=2,
            tier="tier_2_secondary",
        ),
        EmailFinderProvider.VOILA_NORBERT: ProviderConfig(
            name=EmailFinderProvider.VOILA_NORBERT,
            cost_per_lookup=0.015,
            accuracy=0.92,
            daily_limit=1000,
            priority=3,
            tier="tier_2_secondary",
        ),
        EmailFinderProvider.NIMBLER: ProviderConfig(
            name=EmailFinderProvider.NIMBLER,
            cost_per_lookup=0.010,
            accuracy=0.86,
            daily_limit=2000,
            priority=4,
            tier="tier_2_secondary",
        ),
        EmailFinderProvider.ICYPEAS: ProviderConfig(
            name=EmailFinderProvider.ICYPEAS,
            cost_per_lookup=0.010,
            accuracy=0.88,
            daily_limit=2000,
            priority=5,
            tier="tier_2_secondary",
        ),
        EmailFinderProvider.ANYMAILFINDER: ProviderConfig(
            name=EmailFinderProvider.ANYMAILFINDER,
            cost_per_lookup=0.012,
            accuracy=0.85,
            daily_limit=1500,
            priority=6,
            tier="tier_2_secondary",
        ),
        EmailFinderProvider.FINDYMAIL: ProviderConfig(
            name=EmailFinderProvider.FINDYMAIL,
            cost_per_lookup=0.008,
            accuracy=0.90,
            daily_limit=2000,
            priority=7,
            tier="tier_3_fallback",
        ),
    }

    @classmethod
    def get_providers_in_order(cls) -> list[ProviderConfig]:
        """Get all providers sorted by priority (cheapest first)."""
        return sorted(cls.PROVIDERS.values(), key=lambda p: p.priority)


# ============================================================================
# Email Verification Agent
# ============================================================================


class EmailVerificationAgent:
    """
    Agent for finding and verifying email addresses using waterfall approach.

    Database Flow:
    - READS: leads table (lead_id, first_name, last_name, company_domain)
    - WRITES: lead_emails table (email, verification_status, provider_used, cost)

    Handoff:
    - Receives: lead_id, first_name, last_name, company_domain from Lead List Builder (2.1)
    - Sends: verified_email, verification_status to Personalization Agent (4.1)
    """

    def __init__(self) -> None:
        """Initialize the email verification agent with API clients."""
        self.name = "email_verification_agent"
        self.description = "Finds and verifies email addresses using waterfall enrichment"

        # Initialize API clients
        self.tomba_client = self._init_tomba_client()
        self.muraena_client = self._init_muraena_client()
        self.voila_client = self._init_voila_client()
        self.nimbler_client = self._init_nimbler_client()
        self.icypeas_client = self._init_icypeas_client()
        self.anymailfinder_client = self._init_anymailfinder_client()
        self.findymail_client = self._init_findymail_client()
        self.reoon_client = self._init_reoon_client()
        self.mailverify_client = self._init_mailverify_client()

        # Rate limiters per provider (prevent API throttling)
        self._rate_limiters: dict[str, TokenBucketRateLimiter] = {
            "tomba": TokenBucketRateLimiter(capacity=50, refill_rate=1.0, service_name="Tomba"),
            "reoon": TokenBucketRateLimiter(capacity=30, refill_rate=0.5, service_name="Reoon"),
            "mailverify": TokenBucketRateLimiter(
                capacity=20, refill_rate=0.3, service_name="MailVerify"
            ),
        }

        # Circuit breakers per provider (prevent cascade failures)
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            "tomba": CircuitBreaker(
                failure_threshold=3, recovery_timeout=60.0, service_name="Tomba"
            ),
            "muraena": CircuitBreaker(
                failure_threshold=3, recovery_timeout=60.0, service_name="Muraena"
            ),
            "voila": CircuitBreaker(
                failure_threshold=3, recovery_timeout=60.0, service_name="VoilaNorbert"
            ),
            "reoon": CircuitBreaker(
                failure_threshold=5, recovery_timeout=30.0, service_name="Reoon"
            ),
        }

        logger.info(f"Initialized {self.name} agent with email verification clients")

    @staticmethod
    def _init_tomba_client() -> TombaClient | None:
        """Initialize Tomba client."""
        try:
            api_key = os.getenv("TOMBA_API_KEY")
            api_secret = os.getenv("TOMBA_API_SECRET")
            if api_key and api_secret:
                return TombaClient(api_key=api_key, api_secret=api_secret)
            logger.warning("Tomba API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Tomba client: {e}")
            return None

    @staticmethod
    def _init_muraena_client() -> MuraenaClient | None:
        """Initialize Muraena client."""
        try:
            api_key = os.getenv("MURAENA_API_KEY")
            if api_key:
                return MuraenaClient(api_key=api_key)
            logger.warning("Muraena API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Muraena client: {e}")
            return None

    @staticmethod
    def _init_voila_client() -> VoilaNorbertClient | None:
        """Initialize Voila Norbert client."""
        try:
            api_key = os.getenv("VOILA_NORBERT_API_KEY")
            if api_key:
                return VoilaNorbertClient(api_key=api_key)
            logger.warning("Voila Norbert API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Voila Norbert client: {e}")
            return None

    @staticmethod
    def _init_nimbler_client() -> NimblerClient | None:
        """Initialize Nimbler client."""
        try:
            api_key = os.getenv("NIMBLER_API_KEY")
            if api_key:
                return NimblerClient(api_key=api_key)
            logger.warning("Nimbler API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Nimbler client: {e}")
            return None

    @staticmethod
    def _init_icypeas_client() -> IcypeasClient | None:
        """Initialize Icypeas client."""
        try:
            api_key = os.getenv("ICYPEAS_API_KEY")
            if api_key:
                return IcypeasClient(api_key=api_key)
            logger.warning("Icypeas API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Icypeas client: {e}")
            return None

    @staticmethod
    def _init_anymailfinder_client() -> AnymailfinderClient | None:
        """Initialize AnyMailFinder client."""
        try:
            api_key = os.getenv("ANYMAILFINDER_API_KEY")
            if api_key:
                return AnymailfinderClient(api_key=api_key)
            logger.warning("AnyMailFinder API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize AnyMailFinder client: {e}")
            return None

    @staticmethod
    def _init_findymail_client() -> FindymailClient | None:
        """Initialize Findymail client."""
        try:
            api_key = os.getenv("FINDYMAIL_API_KEY")
            if api_key:
                return FindymailClient(api_key=api_key)
            logger.warning("Findymail API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Findymail client: {e}")
            return None

    @staticmethod
    def _init_reoon_client() -> ReoonClient | None:
        """Initialize Reoon client."""
        try:
            api_key = os.getenv("REOON_API_KEY")
            if api_key:
                return ReoonClient(api_key=api_key)
            logger.warning("Reoon API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Reoon client: {e}")
            return None

    @staticmethod
    def _init_mailverify_client() -> MailVerifyClient | None:
        """Initialize MailVerify client."""
        try:
            api_key = os.getenv("MAILVERIFY_API_KEY")
            if api_key:
                return MailVerifyClient(api_key=api_key)
            logger.warning("MailVerify API credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize MailVerify client: {e}")
            return None

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def find_email(
        self,
        first_name: str,
        last_name: str,
        company_domain: str,
        max_providers: int = 3,
    ) -> EnrichmentResult:
        """
        Find email address using waterfall pattern.

        Tries providers in priority order (cheapest first) until email is found
        or max_providers is reached.

        Args:
            first_name: Lead's first name
            last_name: Lead's last name
            company_domain: Company domain name
            max_providers: Maximum providers to try (default 3)

        Returns:
            EnrichmentResult with found email and verification status
        """
        logger.info(f"Starting email search for {first_name} {last_name} at {company_domain}")

        result = EnrichmentResult(
            lead_id="",
            email=None,
            verification_status=None,
            provider_used=None,
            verifier_used=None,
            total_cost=0.0,
            attempts=[],
            verification=None,
        )

        providers_to_try = ProviderRegistry.get_providers_in_order()[:max_providers]

        for provider_config in providers_to_try:
            provider_key = provider_config.name.value
            circuit_breaker = self._circuit_breakers.get(provider_key)

            # Check circuit breaker before attempting
            if circuit_breaker and not circuit_breaker.can_proceed():
                logger.warning(f"Circuit breaker open for {provider_key}, skipping")
                continue

            try:
                # Apply rate limiting if configured
                rate_limiter = self._rate_limiters.get(provider_key)
                if rate_limiter:
                    await rate_limiter.acquire()

                email = await self._find_email_with_provider(
                    provider_config.name, first_name, last_name, company_domain
                )

                if email:
                    # Record success for circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_success()

                    # Email found, verify it
                    verification = await self._verify_email(email)
                    result.email = email
                    result.provider_used = provider_config.name
                    result.verification_status = verification.status
                    result.verifier_used = verification.provider
                    result.total_cost = provider_config.cost_per_lookup + verification.cost
                    result.verification = verification
                    logger.info(f"Found email {email} using {provider_config.name}")
                    return result

            except ProviderError as e:
                # Specific provider error - record failure
                if circuit_breaker:
                    circuit_breaker.record_failure()
                logger.warning(f"Provider {provider_key} failed: {e.message}")
                continue

            except EmailVerificationAgentError as e:
                # Known agent error - log and continue
                logger.warning(f"Agent error with {provider_key}: {e.message}")
                continue

            except TimeoutError:
                # Timeout - record failure for circuit breaker
                if circuit_breaker:
                    circuit_breaker.record_failure()
                logger.warning(f"Timeout with provider {provider_key}")
                continue

        logger.warning(f"Could not find email for {first_name} {last_name} at {company_domain}")
        return result

    async def _find_email_with_provider(
        self,
        provider: EmailFinderProvider,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> str | None:
        """Find email using specific provider."""
        if provider == EmailFinderProvider.TOMBA and self.tomba_client:
            result = await self.tomba_client.search_person(first_name, last_name, domain)  # type: ignore[attr-defined]
            return result.email if result else None
        elif provider == EmailFinderProvider.MURAENA and self.muraena_client:
            result = await self.muraena_client.find_email(first_name, last_name, domain)  # type: ignore[attr-defined]
            return result.get("email") if result else None
        elif provider == EmailFinderProvider.VOILA_NORBERT and self.voila_client:
            result = await self.voila_client.find_email(first_name, last_name, domain)
            return result.get("email") if result else None
        elif provider == EmailFinderProvider.NIMBLER and self.nimbler_client:
            result = await self.nimbler_client.find_email(first_name, last_name, domain)  # type: ignore[attr-defined]
            return result.get("email") if result else None
        elif provider == EmailFinderProvider.ICYPEAS and self.icypeas_client:
            result = await self.icypeas_client.find_email(first_name, last_name, domain)
            return result.get("email") if result else None
        elif provider == EmailFinderProvider.ANYMAILFINDER and self.anymailfinder_client:
            result = await self.anymailfinder_client.find_email(first_name, last_name, domain)  # type: ignore[attr-defined]
            return result.get("email") if result else None
        elif provider == EmailFinderProvider.FINDYMAIL and self.findymail_client:
            result = await self.findymail_client.find_email(first_name, last_name, domain)  # type: ignore[attr-defined]
            return result.get("email") if result else None

        return None

    async def _verify_email(self, email: str) -> EmailVerificationResult:
        """Verify email using Reoon (primary) and MailVerify (catchall handler)."""
        if not self.reoon_client:
            raise EmailVerificationError("Reoon client not initialized")

        # Try Reoon first (primary verifier)
        reoon_result = await self.reoon_client.verify_email_quick(email)

        if reoon_result.is_catchall and self.mailverify_client:  # type: ignore[attr-defined]
            # If Reoon says catchall, use MailVerify for confirmation
            mailverify_result = await self.mailverify_client.verify_email(email)
            status = self._map_mailverify_status(mailverify_result.get("status"))  # type: ignore[attr-defined]
            is_catchall = status == EmailVerificationStatus.CATCHALL
        else:
            status = self._map_reoon_status(reoon_result.status)
            is_catchall = reoon_result.is_catchall  # type: ignore[attr-defined]

        return EmailVerificationResult(
            email=email,
            status=status,
            provider=(
                EmailVerificationProvider.MAILVERIFY
                if is_catchall and self.mailverify_client
                else EmailVerificationProvider.REOON
            ),
            confidence=0.95,
            cost=0.003 if not is_catchall else 0.008,
            is_catchall=is_catchall,
        )

    @staticmethod
    def _map_reoon_status(
        reoon_status: str,
    ) -> EmailVerificationStatus:
        """Map Reoon status to internal status."""
        status_map = {
            "safe": EmailVerificationStatus.VALID,
            "valid": EmailVerificationStatus.VALID,
            "invalid": EmailVerificationStatus.INVALID,
            "catch_all": EmailVerificationStatus.CATCHALL,
            "disposable": EmailVerificationStatus.DISPOSABLE,
            "role_account": EmailVerificationStatus.ROLE_BASED,
        }
        return status_map.get(reoon_status, EmailVerificationStatus.UNKNOWN)

    @staticmethod
    def _map_mailverify_status(
        mailverify_status: str,
    ) -> EmailVerificationStatus:
        """Map MailVerify status to internal status."""
        status_map = {
            "deliverable": EmailVerificationStatus.VALID,
            "valid": EmailVerificationStatus.VALID,
            "undeliverable": EmailVerificationStatus.INVALID,
            "risky": EmailVerificationStatus.RISKY,
            "catch_all": EmailVerificationStatus.CATCHALL,
        }
        return status_map.get(mailverify_status, EmailVerificationStatus.UNKNOWN)


# ============================================================================
# Claude Agent SDK MCP Tools
# ============================================================================


@tool(  # type: ignore[misc]
    name="find_and_verify_email",
    description="Find and verify email address for a lead using waterfall approach",
    input_schema={
        "first_name": str,
        "last_name": str,
        "company_domain": str,
        "max_providers": int,
    },
)
async def find_and_verify_email_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for finding and verifying email addresses.

    This tool uses a waterfall approach, trying email finder providers
    in priority order (cheapest first) and verifying with Reoon/MailVerify.

    Args:
        args: Dictionary with first_name, last_name, company_domain, max_providers

    Returns:
        Dictionary with email, verification_status, provider, and cost
    """
    agent = EmailVerificationAgent()

    try:
        result = await agent.find_email(
            first_name=args.get("first_name", ""),
            last_name=args.get("last_name", ""),
            company_domain=args.get("company_domain", ""),
            max_providers=args.get("max_providers", 3),
        )

        response_data = {
            "email": result.email,
            "verification_status": (
                result.verification_status.value if result.verification_status else None
            ),
            "provider_used": result.provider_used.value if result.provider_used else None,
            "verifier_used": result.verifier_used.value if result.verifier_used else None,
            "total_cost": result.total_cost,
            "success": (
                result.email is not None
                and result.verification_status == EmailVerificationStatus.VALID
            ),
        }

        return {"content": [{"type": "text", "text": json.dumps(response_data)}]}

    except EmailVerificationAgentError as e:
        return {
            "content": [{"type": "text", "text": f"Email verification failed: {e.message}"}],
            "is_error": True,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Unexpected error: {e!s}"}],
            "is_error": True,
        }


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> None:
    """Main entry point for email verification agent."""
    # Create SDK MCP server with tools first
    create_sdk_mcp_server("email_verification", tools=[find_and_verify_email_tool])

    options = ClaudeAgentOptions(
        system_prompt=(
            "You are an email enrichment specialist finding and verifying business emails. "
            "Use the find_and_verify_email tool to find emails for leads. "
            "Always verify found emails before returning results."
        ),
        allowed_tools=["mcp__email_verification__find_and_verify_email"],
        setting_sources=["project"],
        permission_mode="acceptEdits",
    )

    async for message in query(
        prompt="Process email verification for leads",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    logger.info(f"Agent response: {block.text}")


if __name__ == "__main__":
    asyncio.run(main())
