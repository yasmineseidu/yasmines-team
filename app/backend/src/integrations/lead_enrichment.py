"""
Lead Enrichment Waterfall Orchestrator.

Implements a tiered cascade strategy for email finding services, maximizing
accuracy while minimizing costs by only calling expensive services if
cheaper ones fail.

Waterfall Order:
1. Anymailfinder - Best for C-level executives
2. Findymail - Best for tech companies
3. Tomba - Best for domain-wide search
4. VoilaNorbert - Best for common names
5. Icypeas - Best for European contacts
6. Muraena - B2B leads database
7. Nimbler - B2B contact enrichment
8. MailVerify - Final email verification

Features:
- Cascade through services by cost and success rate
- Result caching (30 days) to avoid duplicate lookups
- Cost tracking per service
- Success/failure tracking for optimization
- Batch processing for multiple leads
- Rate limiting per service

Example:
    >>> from src.integrations.lead_enrichment import LeadEnrichmentWaterfall
    >>> waterfall = LeadEnrichmentWaterfall(
    ...     anymailfinder_key="key1",
    ...     findymail_key="key2",
    ...     # ... other keys
    ... )
    >>> result = await waterfall.find_email(
    ...     first_name="John",
    ...     last_name="Smith",
    ...     domain="company.com"
    ... )
    >>> if result.found:
    ...     print(f"Found via {result.source}: {result.email}")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.integrations.anymailfinder import AnymailfinderClient, AnymailfinderError
from src.integrations.findymail import FindymailClient, FindymailError
from src.integrations.icypeas import IcypeasClient, IcypeasError
from src.integrations.mailverify import MailVerifyClient, MailVerifyError
from src.integrations.muraena import MuraenaClient, MuraenaError
from src.integrations.nimbler import NimblerClient, NimblerError
from src.integrations.tomba import TombaClient, TombaError
from src.integrations.voilanorbert import VoilaNorbertClient, VoilaNorbertError

logger = logging.getLogger(__name__)


class EnrichmentSource(str, Enum):
    """Source service that found the email."""

    ANYMAILFINDER = "anymailfinder"
    FINDYMAIL = "findymail"
    TOMBA = "tomba"
    VOILANORBERT = "voilanorbert"
    ICYPEAS = "icypeas"
    MURAENA = "muraena"
    NIMBLER = "nimbler"
    MAILVERIFY = "mailverify"
    CACHE = "cache"
    NOT_FOUND = "not_found"


@dataclass
class EnrichmentResult:
    """Result from lead enrichment waterfall."""

    email: str | None
    source: EnrichmentSource
    confidence: float  # 0-1 confidence score
    is_verified: bool
    first_name: str | None
    last_name: str | None
    domain: str | None
    company: str | None
    phone: str | None
    services_tried: list[EnrichmentSource]
    total_cost: float  # Estimated cost in credits/cents
    duration_ms: int
    raw_responses: dict[str, Any]

    @property
    def found(self) -> bool:
        """Check if email was found."""
        return self.email is not None and self.source != EnrichmentSource.NOT_FOUND

    @property
    def is_high_confidence(self) -> bool:
        """Check if result has high confidence (>= 0.8)."""
        return self.confidence >= 0.8


@dataclass
class ServiceStats:
    """Statistics for a single enrichment service."""

    name: str
    requests: int = 0
    successes: int = 0
    failures: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.requests == 0:
            return 0.0
        return self.successes / self.requests


@dataclass
class WaterfallStats:
    """Overall waterfall statistics."""

    total_requests: int = 0
    total_found: int = 0
    total_not_found: int = 0
    total_cost: float = 0.0
    services: dict[str, ServiceStats] = field(default_factory=dict)
    cache_hits: int = 0

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.total_found / self.total_requests


# Cost per lookup in credits (normalized)
SERVICE_COSTS = {
    EnrichmentSource.ANYMAILFINDER: 1.0,
    EnrichmentSource.FINDYMAIL: 1.0,
    EnrichmentSource.TOMBA: 1.0,
    EnrichmentSource.VOILANORBERT: 1.0,
    EnrichmentSource.ICYPEAS: 1.0,
    EnrichmentSource.MURAENA: 1.0,
    EnrichmentSource.NIMBLER: 1.0,
    EnrichmentSource.MAILVERIFY: 0.5,  # Verification only
}


class LeadEnrichmentWaterfall:
    """
    Orchestrates email finding across multiple services using waterfall pattern.

    The waterfall cascades through services in order of cost-effectiveness,
    stopping as soon as a verified email is found.

    Example:
        >>> waterfall = LeadEnrichmentWaterfall(
        ...     anymailfinder_key="key1",
        ...     findymail_key="key2",
        ...     tomba_key="key3",
        ...     tomba_secret="secret3", # pragma: allowlist secret
        ... )
        >>> async with waterfall:
        ...     result = await waterfall.find_email(
        ...         first_name="John",
        ...         last_name="Smith",
        ...         domain="techcompany.com"
        ...     )
        ...     if result.found:
        ...         print(f"Found: {result.email} via {result.source}")
    """

    def __init__(
        self,
        anymailfinder_key: str | None = None,
        findymail_key: str | None = None,
        tomba_key: str | None = None,
        tomba_secret: str | None = None,
        voilanorbert_key: str | None = None,
        icypeas_key: str | None = None,
        muraena_key: str | None = None,
        nimbler_key: str | None = None,
        mailverify_key: str | None = None,
        verify_results: bool = True,
        cache_enabled: bool = True,
        cache_ttl_days: int = 30,
    ) -> None:
        """
        Initialize the waterfall orchestrator.

        Args:
            anymailfinder_key: Anymailfinder API key
            findymail_key: Findymail API key
            tomba_key: Tomba API key
            tomba_secret: Tomba API secret
            voilanorbert_key: VoilaNorbert API key
            icypeas_key: Icypeas API key
            muraena_key: Muraena API key
            nimbler_key: Nimbler API key
            mailverify_key: MailVerify API key for final verification
            verify_results: Whether to verify found emails (default True)
            cache_enabled: Whether to cache results (default True)
            cache_ttl_days: Cache TTL in days (default 30)
        """
        self.verify_results = verify_results
        self.cache_enabled = cache_enabled
        self.cache_ttl_days = cache_ttl_days

        # Initialize clients for each configured service
        self._clients: dict[EnrichmentSource, Any] = {}

        if anymailfinder_key:
            self._clients[EnrichmentSource.ANYMAILFINDER] = AnymailfinderClient(
                api_key=anymailfinder_key
            )

        if findymail_key:
            self._clients[EnrichmentSource.FINDYMAIL] = FindymailClient(api_key=findymail_key)

        if tomba_key and tomba_secret:
            self._clients[EnrichmentSource.TOMBA] = TombaClient(
                api_key=tomba_key, api_secret=tomba_secret
            )

        if voilanorbert_key:
            self._clients[EnrichmentSource.VOILANORBERT] = VoilaNorbertClient(
                api_key=voilanorbert_key
            )

        if icypeas_key:
            self._clients[EnrichmentSource.ICYPEAS] = IcypeasClient(api_key=icypeas_key)

        if muraena_key:
            self._clients[EnrichmentSource.MURAENA] = MuraenaClient(api_key=muraena_key)

        if nimbler_key:
            self._clients[EnrichmentSource.NIMBLER] = NimblerClient(api_key=nimbler_key)

        if mailverify_key:
            self._clients[EnrichmentSource.MAILVERIFY] = MailVerifyClient(api_key=mailverify_key)

        # Simple in-memory cache (should use Redis in production)
        self._cache: dict[str, tuple[EnrichmentResult, datetime]] = {}

        # Statistics tracking
        self._stats = WaterfallStats()
        for source in EnrichmentSource:
            if source not in (EnrichmentSource.CACHE, EnrichmentSource.NOT_FOUND):
                self._stats.services[source.value] = ServiceStats(name=source.value)

    async def __aenter__(self) -> "LeadEnrichmentWaterfall":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def close(self) -> None:
        """Close all client connections."""
        for client in self._clients.values():
            if hasattr(client, "close"):
                await client.close()

    def _get_cache_key(
        self,
        first_name: str,
        last_name: str,
        domain: str | None,
        company: str | None,
    ) -> str:
        """Generate cache key for lookup."""
        parts = [
            first_name.lower().strip(),
            last_name.lower().strip(),
            (domain or "").lower().strip(),
            (company or "").lower().strip(),
        ]
        return ":".join(parts)

    def _check_cache(self, cache_key: str) -> EnrichmentResult | None:
        """Check if result is cached and not expired."""
        if not self.cache_enabled:
            return None

        cached = self._cache.get(cache_key)
        if cached is None:
            return None

        result, timestamp = cached
        age_days = (datetime.now() - timestamp).days
        if age_days > self.cache_ttl_days:
            del self._cache[cache_key]
            return None

        self._stats.cache_hits += 1
        return result

    def _cache_result(self, cache_key: str, result: EnrichmentResult) -> None:
        """Cache an enrichment result."""
        if self.cache_enabled and result.found:
            self._cache[cache_key] = (result, datetime.now())

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str | None = None,
        company: str | None = None,
        linkedin_url: str | None = None,
        skip_services: list[EnrichmentSource] | None = None,
    ) -> EnrichmentResult:
        """
        Find email using waterfall strategy.

        Cascades through configured services until an email is found.

        Args:
            first_name: First name of the person
            last_name: Last name of the person
            domain: Company domain (e.g., "company.com")
            company: Company name
            linkedin_url: LinkedIn profile URL (optional, used by some services)
            skip_services: Services to skip in this lookup

        Returns:
            EnrichmentResult with found email or NOT_FOUND status

        Raises:
            ValueError: If required parameters are missing
        """
        if not first_name or not first_name.strip():
            raise ValueError("first_name is required")
        if not last_name or not last_name.strip():
            raise ValueError("last_name is required")
        if not domain and not company:
            raise ValueError("Either domain or company is required")

        start_time = asyncio.get_event_loop().time()
        self._stats.total_requests += 1

        # Check cache first
        cache_key = self._get_cache_key(first_name, last_name, domain, company)
        cached_result = self._check_cache(cache_key)
        if cached_result:
            cached_result.source = EnrichmentSource.CACHE
            return cached_result

        skip_set = set(skip_services or [])
        services_tried: list[EnrichmentSource] = []
        raw_responses: dict[str, Any] = {}
        total_cost = 0.0
        full_name = f"{first_name.strip()} {last_name.strip()}"

        # Waterfall order
        waterfall_order = [
            EnrichmentSource.ANYMAILFINDER,
            EnrichmentSource.FINDYMAIL,
            EnrichmentSource.TOMBA,
            EnrichmentSource.VOILANORBERT,
            EnrichmentSource.ICYPEAS,
            EnrichmentSource.MURAENA,
            EnrichmentSource.NIMBLER,
        ]

        for source in waterfall_order:
            if source in skip_set:
                continue

            client = self._clients.get(source)
            if client is None:
                continue

            services_tried.append(source)
            service_stats = self._stats.services[source.value]
            service_stats.requests += 1
            total_cost += SERVICE_COSTS.get(source, 1.0)

            try:
                result = await self._try_service(
                    source=source,
                    client=client,
                    first_name=first_name,
                    last_name=last_name,
                    full_name=full_name,
                    domain=domain,
                    company=company,
                    linkedin_url=linkedin_url,
                )

                if result and result.get("email"):
                    service_stats.successes += 1

                    email = result["email"]
                    confidence = result.get("confidence", 0.8)
                    is_verified = result.get("verified", False)

                    # Optionally verify the email
                    if self.verify_results and not is_verified:
                        verified_result = await self._verify_email(email)
                        if verified_result:
                            is_verified = verified_result.get("verified", False)
                            if not verified_result.get("deliverable", True):
                                # Email not deliverable, continue waterfall
                                raw_responses[source.value] = result
                                continue

                    duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                    enrichment_result = EnrichmentResult(
                        email=email,
                        source=source,
                        confidence=confidence,
                        is_verified=is_verified,
                        first_name=first_name,
                        last_name=last_name,
                        domain=domain,
                        company=company,
                        phone=result.get("phone"),
                        services_tried=services_tried,
                        total_cost=total_cost,
                        duration_ms=duration_ms,
                        raw_responses=raw_responses,
                    )

                    self._stats.total_found += 1
                    self._cache_result(cache_key, enrichment_result)
                    return enrichment_result

                raw_responses[source.value] = result

            except Exception as e:
                service_stats.failures += 1
                raw_responses[source.value] = {"error": str(e)}
                logger.warning(f"Service {source.value} failed: {e}")
                continue

        # No email found
        duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        self._stats.total_not_found += 1

        return EnrichmentResult(
            email=None,
            source=EnrichmentSource.NOT_FOUND,
            confidence=0.0,
            is_verified=False,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            company=company,
            phone=None,
            services_tried=services_tried,
            total_cost=total_cost,
            duration_ms=duration_ms,
            raw_responses=raw_responses,
        )

    async def _try_service(
        self,
        source: EnrichmentSource,
        client: Any,
        first_name: str,
        last_name: str,
        full_name: str,
        domain: str | None,
        company: str | None,
        linkedin_url: str | None,
    ) -> dict[str, Any] | None:
        """
        Try a single service to find email.

        Args:
            source: The service source
            client: The client instance
            first_name: First name
            last_name: Last name
            full_name: Full name (first + last)
            domain: Company domain
            company: Company name
            linkedin_url: LinkedIn URL

        Returns:
            Dictionary with email and metadata if found, None otherwise
        """
        try:
            if source == EnrichmentSource.ANYMAILFINDER:
                result = await client.find_person_email(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain or "",
                )
                if result.found:
                    return {
                        "email": result.email,
                        "confidence": 1.0 if result.is_verified else 0.8,
                        "verified": result.is_verified,
                    }

            elif source == EnrichmentSource.FINDYMAIL:
                result = await client.find_work_email(
                    full_name=full_name,
                    domain=domain or company or "",
                )
                if result.is_valid:
                    return {
                        "email": result.email,
                        "confidence": 0.9 if result.is_valid else 0.7,
                        "verified": result.is_valid,
                    }

            elif source == EnrichmentSource.TOMBA:
                result = await client.find_email(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain or "",
                )
                if result.found:
                    return {
                        "email": result.email,
                        "confidence": result.confidence / 100 if result.confidence else 0.7,
                        "verified": result.confidence >= 90 if result.confidence else False,
                    }

            elif source == EnrichmentSource.VOILANORBERT:
                result = await client.find_email(
                    full_name=full_name,
                    domain=domain,
                    company=company,
                )
                if result.found:
                    return {
                        "email": result.email,
                        "confidence": result.score / 100 if result.score else 0.7,
                        "verified": result.is_verified,
                    }

            elif source == EnrichmentSource.ICYPEAS:
                result = await client.find_email(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                    company=company,
                )
                if result.found:
                    return {
                        "email": result.email,
                        "confidence": result.certainty,
                        "verified": result.certainty >= 0.9,
                    }

            elif source == EnrichmentSource.MURAENA:
                result = await client.find_contact(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                    company=company,
                    linkedin_url=linkedin_url,
                )
                if result.found:
                    return {
                        "email": result.email,
                        "phone": result.phone,
                        "confidence": 0.85 if result.is_verified else 0.7,
                        "verified": result.is_verified,
                    }

            elif source == EnrichmentSource.NIMBLER:
                result = await client.enrich_contact(
                    first_name=first_name,
                    last_name=last_name,
                    company=company,
                    linkedin_url=linkedin_url,
                )
                if result.found:
                    return {
                        "email": result.email,
                        "phone": result.mobile_phone,
                        "confidence": 0.8,
                        "verified": False,
                    }

        except (
            AnymailfinderError,
            FindymailError,
            TombaError,
            VoilaNorbertError,
            IcypeasError,
            MuraenaError,
            NimblerError,
        ) as e:
            logger.debug(f"Service {source.value} returned no result: {e}")

        return None

    async def _verify_email(self, email: str) -> dict[str, Any] | None:
        """
        Verify an email using MailVerify.

        Args:
            email: Email to verify

        Returns:
            Verification result dictionary or None if verification unavailable
        """
        mailverify = self._clients.get(EnrichmentSource.MAILVERIFY)
        if mailverify is None:
            return None

        try:
            result = await mailverify.verify_email(email)
            return {
                "verified": result.is_valid,
                "deliverable": result.is_deliverable,
                "catch_all": result.is_catch_all,
            }
        except MailVerifyError as e:
            logger.warning(f"Email verification failed: {e}")
            return None

    async def find_emails_batch(
        self,
        leads: list[dict[str, str]],
        concurrency: int = 5,
    ) -> list[EnrichmentResult]:
        """
        Find emails for multiple leads in parallel.

        Args:
            leads: List of lead dictionaries with keys:
                   first_name, last_name, domain (or company)
            concurrency: Maximum concurrent lookups (default 5)

        Returns:
            List of EnrichmentResult objects
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def process_lead(lead: dict[str, str]) -> EnrichmentResult:
            async with semaphore:
                return await self.find_email(
                    first_name=lead.get("first_name", ""),
                    last_name=lead.get("last_name", ""),
                    domain=lead.get("domain"),
                    company=lead.get("company"),
                    linkedin_url=lead.get("linkedin_url"),
                )

        tasks = [process_lead(lead) for lead in leads]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> WaterfallStats:
        """Get waterfall statistics."""
        return self._stats

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._stats = WaterfallStats()
        for source in EnrichmentSource:
            if source not in (EnrichmentSource.CACHE, EnrichmentSource.NOT_FOUND):
                self._stats.services[source.value] = ServiceStats(name=source.value)

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._cache.clear()

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of all configured services.

        Returns:
            Dictionary with health status of each service
        """
        results: dict[str, Any] = {
            "name": "lead_enrichment_waterfall",
            "healthy": True,
            "services": {},
        }

        for source, client in self._clients.items():
            try:
                health = await client.health_check()
                results["services"][source.value] = health
                if not health.get("healthy", False):
                    results["healthy"] = False
            except Exception as e:
                results["services"][source.value] = {
                    "healthy": False,
                    "error": str(e),
                }
                results["healthy"] = False

        return results
