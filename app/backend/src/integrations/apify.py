"""
Apify Integration Client - Lead scraping via Apify actors.

Provides async client for running Apify actors to scrape leads using a
cost-effective waterfall pattern:

1. Leads Finder Primary ($1.5/1k leads with emails) - IoSHqwTR9YGhzccez
2. Leads Scraper PPE (fallback) - T1XDXWc1L92AfIJtd
3. Leads Scraper Multi (last resort) - VYRyEF4ygTTkaIghe

Uses ApifyClientAsync for non-blocking operations with comprehensive
error handling, rate limiting, and retry logic.

Example:
    >>> client = ApifyLeadScraperClient(api_token=os.environ["APIFY_API_TOKEN"])
    >>> async with client:
    ...     result = await client.scrape_leads(
    ...         job_titles=["VP", "Director"],
    ...         industries=["Technology"],
    ...         max_leads=1000,
    ...     )
    ...     print(f"Scraped {len(result.leads)} leads")
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from apify_client import ApifyClientAsync
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class ApifyError(Exception):
    """Base exception for Apify errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class ApifyAuthenticationError(ApifyError):
    """Raised when Apify authentication fails."""

    def __init__(self, message: str = "Apify authentication failed") -> None:
        super().__init__(message, status_code=401)


class ApifyRateLimitError(ApifyError):
    """Raised when Apify rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Apify rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ApifyActorError(ApifyError):
    """Raised when an Apify actor fails."""

    def __init__(
        self,
        actor_id: str,
        run_id: str | None = None,
        status: str | None = None,
        message: str | None = None,
    ) -> None:
        self.actor_id = actor_id
        self.run_id = run_id
        self.status = status
        error_message = message or f"Actor {actor_id} failed"
        if run_id:
            error_message += f" (run_id={run_id})"
        if status:
            error_message += f" (status={status})"
        super().__init__(error_message)


class ApifyTimeoutError(ApifyError):
    """Raised when an Apify actor run times out."""

    def __init__(self, actor_id: str, run_id: str, timeout_secs: int) -> None:
        self.actor_id = actor_id
        self.run_id = run_id
        self.timeout_secs = timeout_secs
        super().__init__(f"Actor {actor_id} timed out after {timeout_secs}s (run_id={run_id})")


# =============================================================================
# Enums and Data Classes
# =============================================================================


class ApifyActorId(str, Enum):
    """Known Apify actor IDs for lead scraping.

    Lead Scraper Waterfall (in priority order):
    1. LEADS_FINDER_PRIMARY - $1.5/1k leads, best value
    2. LEADS_SCRAPER_PPE - Fallback option
    3. LEADS_SCRAPER_MULTI - Last resort (Apollo/ZoomInfo/Lusha alternative)
    """

    # Primary lead scraper - Leads Finder ($1.5/1k leads with emails)
    # https://console.apify.com/actors/IoSHqwTR9YGhzccez
    LEADS_FINDER_PRIMARY = "IoSHqwTR9YGhzccez"

    # Fallback - peakydev/leads-scraper-ppe
    # https://console.apify.com/actors/T1XDXWc1L92AfIJtd
    LEADS_SCRAPER_PPE = "T1XDXWc1L92AfIJtd"

    # Last resort - pipelinelabs/lead-scraper-apollo-zoominfo-lusha
    # https://console.apify.com/actors/VYRyEF4ygTTkaIghe
    LEADS_SCRAPER_MULTI = "VYRyEF4ygTTkaIghe"

    # LinkedIn profile/company scrapers (for enrichment)
    LINKEDIN_PROFILE_SCRAPER = "anchor/linkedin-profile-scraper"
    LINKEDIN_COMPANY_SCRAPER = "bebity/linkedin-company-scraper"

    # Generic scrapers
    GOOGLE_SEARCH_SCRAPER = "apify/google-search-scraper"
    WEBSITE_SCRAPER = "apify/website-content-crawler"


class ApifyRunStatus(str, Enum):
    """Apify actor run statuses."""

    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    TIMING_OUT = "TIMING-OUT"
    TIMED_OUT = "TIMED-OUT"


@dataclass
class ApifyLead:
    """Represents a lead scraped from Apify."""

    # Basic info
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None

    # LinkedIn
    linkedin_url: str | None = None
    linkedin_id: str | None = None
    headline: str | None = None

    # Job info
    title: str | None = None
    seniority: str | None = None
    department: str | None = None

    # Company info
    company_name: str | None = None
    company_linkedin_url: str | None = None
    company_domain: str | None = None
    company_size: str | None = None
    company_industry: str | None = None

    # Location
    location: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None

    # Source tracking
    source: str = "apify"
    source_url: str | None = None

    # Raw data for audit
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "linkedin_url": self.linkedin_url,
            "linkedin_id": self.linkedin_id,
            "headline": self.headline,
            "title": self.title,
            "seniority": self.seniority,
            "department": self.department,
            "company_name": self.company_name,
            "company_linkedin_url": self.company_linkedin_url,
            "company_domain": self.company_domain,
            "company_size": self.company_size,
            "company_industry": self.company_industry,
            "location": self.location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "source": self.source,
            "source_url": self.source_url,
        }


@dataclass
class ApifyScrapeResult:
    """Result of an Apify scraping run."""

    # Run info
    run_id: str
    actor_id: str
    status: str
    dataset_id: str | None = None

    # Results
    leads: list[ApifyLead] = field(default_factory=list)
    total_items: int = 0

    # Cost tracking
    cost_usd: float = 0.0
    compute_units: float = 0.0

    # Timing
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_secs: int = 0

    # Errors
    error: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "actor_id": self.actor_id,
            "status": self.status,
            "dataset_id": self.dataset_id,
            "total_items": self.total_items,
            "leads_count": len(self.leads),
            "cost_usd": self.cost_usd,
            "compute_units": self.compute_units,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_secs": self.duration_secs,
            "error": self.error,
        }


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for Apify API calls.

    Apify has rate limits per API endpoint. This limiter allows
    bursts up to capacity, then refills at refill_rate per second.
    """

    def __init__(
        self,
        capacity: int = 100,
        refill_rate: float = 10.0,
        service_name: str = "apify",
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            capacity: Maximum tokens (burst capacity)
            refill_rate: Tokens to add per second
            service_name: Service name for logging
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.service_name = service_name
        self.tokens = float(capacity)
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate,
            )
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Wait for tokens to be available
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            logger.debug(
                f"[{self.service_name}] Rate limit reached. "
                f"Waiting {wait_time:.2f}s for token refill"
            )

            await asyncio.sleep(wait_time)

            # Refill and acquire
            self.tokens = self.capacity
            self.tokens -= tokens


# =============================================================================
# Apify Lead Scraper Client
# =============================================================================


class ApifyLeadScraperClient:
    """
    Async client for Apify lead scraping.

    Provides methods to run various Apify actors for lead scraping,
    with comprehensive error handling, rate limiting, and retry logic.
    """

    def __init__(
        self,
        api_token: str | None = None,
        timeout_secs: int = 600,
        poll_interval_secs: int = 10,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Apify client.

        Args:
            api_token: Apify API token. If None, reads from APIFY_API_TOKEN env var.
            timeout_secs: Maximum time to wait for actor runs.
            poll_interval_secs: Interval for polling run status.
            max_retries: Maximum retry attempts for transient errors.
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN", "")
        if not self.api_token:
            raise ApifyAuthenticationError("APIFY_API_TOKEN not provided")

        self.timeout_secs = timeout_secs
        self.poll_interval_secs = poll_interval_secs
        self.max_retries = max_retries

        self._client: ApifyClientAsync | None = None
        self._rate_limiter = TokenBucketRateLimiter(
            capacity=100,  # 100 requests burst
            refill_rate=10.0,  # 10 requests/second
            service_name="apify",
        )

    @property
    def client(self) -> ApifyClientAsync:
        """Get or create async Apify client."""
        if self._client is None:
            self._client = ApifyClientAsync(self.api_token)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        # ApifyClientAsync doesn't have a close method,
        # but we clear the reference for consistency
        self._client = None
        logger.debug("[apify] Client closed")

    async def __aenter__(self) -> "ApifyLeadScraperClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # =========================================================================
    # Actor Run Methods
    # =========================================================================

    @retry(  # type: ignore[misc]
        retry=retry_if_exception_type(ApifyRateLimitError),  # Only retry on rate limits
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,  # Reraise original exception instead of RetryError
    )
    async def run_actor(
        self,
        actor_id: str | ApifyActorId,
        run_input: dict[str, Any],
        wait_for_finish: bool = True,
        timeout_secs: int | None = None,
    ) -> ApifyScrapeResult:
        """
        Run an Apify actor and optionally wait for completion.

        Args:
            actor_id: Apify actor ID or ApifyActorId enum.
            run_input: Input data for the actor.
            wait_for_finish: Whether to wait for the run to complete.
            timeout_secs: Override default timeout.

        Returns:
            ApifyScrapeResult with run info and optionally results.

        Raises:
            ApifyAuthenticationError: If API token is invalid.
            ApifyRateLimitError: If rate limit exceeded.
            ApifyActorError: If actor run fails.
            ApifyTimeoutError: If run times out.
        """
        await self._rate_limiter.acquire()

        actor_id_str = actor_id.value if isinstance(actor_id, ApifyActorId) else actor_id
        timeout = timeout_secs or self.timeout_secs

        logger.info(f"[apify] Starting actor run: {actor_id_str}")

        try:
            actor_client = self.client.actor(actor_id_str)

            if wait_for_finish:
                # call() waits for completion
                run_info = await actor_client.call(
                    run_input=run_input,
                    timeout_secs=timeout,
                )
            else:
                # start() returns immediately
                run_info = await actor_client.start(run_input=run_input)

            if run_info is None:
                raise ApifyActorError(
                    actor_id=actor_id_str,
                    message="Actor run returned None",
                )

            # Build result
            result = ApifyScrapeResult(
                run_id=run_info.get("id", ""),
                actor_id=actor_id_str,
                status=run_info.get("status", "UNKNOWN"),
                dataset_id=run_info.get("defaultDatasetId"),
                started_at=self._parse_datetime(run_info.get("startedAt")),
                finished_at=self._parse_datetime(run_info.get("finishedAt")),
            )

            # Calculate duration
            if result.started_at and result.finished_at:
                result.duration_secs = int((result.finished_at - result.started_at).total_seconds())

            # Extract cost info
            usage_info = run_info.get("usage", {})
            result.compute_units = usage_info.get("COMPUTE_UNITS", 0)
            result.cost_usd = usage_info.get("TOTAL_USD", 0.0)

            # Check status
            status = result.status
            if status == ApifyRunStatus.FAILED.value:
                raise ApifyActorError(
                    actor_id=actor_id_str,
                    run_id=result.run_id,
                    status=status,
                    message="Actor run failed",
                )
            if status in (ApifyRunStatus.TIMED_OUT.value, ApifyRunStatus.TIMING_OUT.value):
                raise ApifyTimeoutError(
                    actor_id=actor_id_str,
                    run_id=result.run_id,
                    timeout_secs=timeout,
                )

            logger.info(
                f"[apify] Actor run completed: {result.run_id} "
                f"(status={status}, duration={result.duration_secs}s)"
            )

            return result

        except ApifyError:
            raise
        except Exception as e:
            # Map common exceptions
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise ApifyAuthenticationError() from e
            if "429" in error_str or "rate limit" in error_str:
                raise ApifyRateLimitError() from e
            raise ApifyActorError(
                actor_id=actor_id_str,
                message=f"Unexpected error: {e}",
            ) from e

    async def get_dataset_items(
        self,
        dataset_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get items from an Apify dataset.

        Args:
            dataset_id: Dataset ID.
            limit: Maximum items to retrieve.
            offset: Offset for pagination.

        Returns:
            List of dataset items.
        """
        await self._rate_limiter.acquire()

        dataset_client = self.client.dataset(dataset_id)
        items_result = await dataset_client.list_items(
            limit=limit,
            offset=offset,
        )

        return items_result.items if items_result else []

    async def iterate_dataset_items(
        self,
        dataset_id: str,
        batch_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Iterate through all items in a dataset.

        Args:
            dataset_id: Dataset ID.
            batch_size: Number of items per batch.

        Returns:
            All items from the dataset.
        """
        all_items: list[dict[str, Any]] = []
        offset = 0

        while True:
            items = await self.get_dataset_items(
                dataset_id=dataset_id,
                limit=batch_size,
                offset=offset,
            )

            if not items:
                break

            all_items.extend(items)
            offset += len(items)

            # If we got fewer items than batch_size, we're done
            if len(items) < batch_size:
                break

        logger.info(f"[apify] Retrieved {len(all_items)} items from dataset {dataset_id}")
        return all_items

    # =========================================================================
    # Lead Scraping Methods - Waterfall Pattern
    # =========================================================================

    # Waterfall order for lead scraping actors
    LEAD_SCRAPER_WATERFALL: list[ApifyActorId] = [
        ApifyActorId.LEADS_FINDER_PRIMARY,  # $1.5/1k - best value
        ApifyActorId.LEADS_SCRAPER_PPE,  # Fallback
        ApifyActorId.LEADS_SCRAPER_MULTI,  # Last resort
    ]

    async def scrape_leads(
        self,
        job_titles: list[str] | None = None,
        seniority_levels: list[str] | None = None,
        industries: list[str] | None = None,
        company_sizes: list[str] | None = None,
        locations: list[str] | None = None,
        keywords: list[str] | None = None,
        max_leads: int = 1000,
        actor_id: str | ApifyActorId | None = None,
    ) -> ApifyScrapeResult:
        """
        Scrape leads using specified actor or waterfall pattern.

        Args:
            job_titles: Target job titles (e.g., ["VP", "Director", "CTO"]).
            seniority_levels: Seniority levels (e.g., ["VP", "Director", "CXO"]).
            industries: Target industries (e.g., ["Technology", "Software"]).
            company_sizes: Company size ranges (e.g., ["51-200", "201-500"]).
            locations: Geographic locations (e.g., ["San Francisco", "New York"]).
            keywords: Additional search keywords.
            max_leads: Maximum number of leads to scrape.
            actor_id: Specific actor to use (None = use waterfall).

        Returns:
            ApifyScrapeResult with scraped leads.
        """
        # Build search input for lead scrapers
        run_input: dict[str, Any] = {
            "maxResults": max_leads,
            "resultsLimit": max_leads,  # Some actors use this field
        }

        # Add search criteria
        if job_titles:
            run_input["jobTitles"] = job_titles
            run_input["titles"] = job_titles  # Alternative field name
        if seniority_levels:
            run_input["seniorityLevels"] = seniority_levels
            run_input["seniority"] = seniority_levels
        if industries:
            run_input["industries"] = industries
            run_input["industry"] = industries
        if company_sizes:
            run_input["companySizes"] = company_sizes
            run_input["employeeCount"] = company_sizes
        if locations:
            run_input["locations"] = locations
            run_input["location"] = locations
        if keywords:
            run_input["keywords"] = keywords
            run_input["query"] = " ".join(keywords)

        # Use specific actor or waterfall
        if actor_id:
            return await self._scrape_with_actor(actor_id, run_input)
        else:
            return await self.scrape_leads_waterfall(run_input)

    async def scrape_leads_waterfall(
        self,
        run_input: dict[str, Any],
    ) -> ApifyScrapeResult:
        """
        Scrape leads using waterfall pattern - try actors in order until success.

        Waterfall order:
        1. Leads Finder Primary ($1.5/1k) - IoSHqwTR9YGhzccez
        2. Leads Scraper PPE (fallback) - T1XDXWc1L92AfIJtd
        3. Leads Scraper Multi (last resort) - VYRyEF4ygTTkaIghe

        Args:
            run_input: Search parameters for actors.

        Returns:
            ApifyScrapeResult from first successful actor.

        Raises:
            ApifyActorError: If all actors in waterfall fail.
        """
        errors: list[str] = []

        for actor_id in self.LEAD_SCRAPER_WATERFALL:
            try:
                logger.info(f"[apify] Trying lead scraper: {actor_id.value}")
                result = await self._scrape_with_actor(actor_id, run_input)

                # Check if we got any leads
                if result.leads and len(result.leads) > 0:
                    logger.info(
                        f"[apify] Success with {actor_id.value}: "
                        f"{len(result.leads)} leads scraped"
                    )
                    return result
                else:
                    logger.warning(f"[apify] {actor_id.value} returned 0 leads, trying next")
                    errors.append(f"{actor_id.value}: 0 leads returned")

            except ApifyActorError as e:
                logger.warning(f"[apify] {actor_id.value} failed: {e}")
                errors.append(f"{actor_id.value}: {e}")
                continue
            except ApifyTimeoutError as e:
                logger.warning(f"[apify] {actor_id.value} timed out: {e}")
                errors.append(f"{actor_id.value}: timeout")
                continue

        # All actors failed
        raise ApifyActorError(
            actor_id="waterfall",
            message=f"All lead scrapers failed: {'; '.join(errors)}",
        )

    async def _scrape_with_actor(
        self,
        actor_id: str | ApifyActorId,
        run_input: dict[str, Any],
    ) -> ApifyScrapeResult:
        """
        Scrape leads with a specific actor.

        Args:
            actor_id: Apify actor ID.
            run_input: Input parameters for the actor.

        Returns:
            ApifyScrapeResult with scraped leads.
        """
        result = await self.run_actor(
            actor_id=actor_id,
            run_input=run_input,
            wait_for_finish=True,
        )

        # Fetch results from dataset
        if result.dataset_id:
            items = await self.iterate_dataset_items(result.dataset_id)
            result.total_items = len(items)
            result.leads = [self._parse_lead(item) for item in items]

        return result  # type: ignore[no-any-return]

    async def scrape_linkedin_profiles(
        self,
        profile_urls: list[str],
    ) -> ApifyScrapeResult:
        """
        Scrape LinkedIn profile data for specific profiles.

        Args:
            profile_urls: List of LinkedIn profile URLs.

        Returns:
            ApifyScrapeResult with profile data as leads.
        """
        run_input = {
            "startUrls": [{"url": url} for url in profile_urls],
        }

        result = await self.run_actor(
            actor_id=ApifyActorId.LINKEDIN_PROFILE_SCRAPER,
            run_input=run_input,
            wait_for_finish=True,
        )

        # Fetch results from dataset
        if result.dataset_id:
            items = await self.iterate_dataset_items(result.dataset_id)
            result.total_items = len(items)
            result.leads = [self._parse_linkedin_lead(item) for item in items]

        return result  # type: ignore[no-any-return]

    async def scrape_companies(
        self,
        company_urls: list[str],
    ) -> ApifyScrapeResult:
        """
        Scrape LinkedIn company data.

        Args:
            company_urls: List of LinkedIn company URLs.

        Returns:
            ApifyScrapeResult with company data.
        """
        run_input = {
            "startUrls": [{"url": url} for url in company_urls],
        }

        result = await self.run_actor(
            actor_id=ApifyActorId.LINKEDIN_COMPANY_SCRAPER,
            run_input=run_input,
            wait_for_finish=True,
        )

        return result  # type: ignore[no-any-return]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_linkedin_lead(self, item: dict[str, Any]) -> ApifyLead:
        """Parse LinkedIn scraper output into ApifyLead."""
        # Handle various field name variations from different actors
        first_name = item.get("firstName") or item.get("first_name") or ""
        last_name = item.get("lastName") or item.get("last_name") or ""
        full_name = (
            item.get("fullName")
            or item.get("full_name")
            or item.get("name")
            or f"{first_name} {last_name}".strip()
        )

        # Parse name if only full_name is provided
        if not first_name and full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        return ApifyLead(
            first_name=first_name or None,
            last_name=last_name or None,
            full_name=full_name or None,
            email=item.get("email") or item.get("workEmail"),
            linkedin_url=(item.get("linkedinUrl") or item.get("profileUrl") or item.get("url")),
            linkedin_id=item.get("linkedinId") or item.get("profileId"),
            headline=item.get("headline") or item.get("title"),
            title=(item.get("jobTitle") or item.get("title") or item.get("currentPosition")),
            seniority=item.get("seniority") or item.get("seniorityLevel"),
            department=item.get("department"),
            company_name=(
                item.get("companyName") or item.get("company") or item.get("currentCompany")
            ),
            company_linkedin_url=item.get("companyLinkedinUrl") or item.get("companyUrl"),
            company_domain=item.get("companyDomain") or item.get("domain"),
            company_size=item.get("companySize") or item.get("employeeCount"),
            company_industry=item.get("industry") or item.get("companyIndustry"),
            location=(item.get("location") or item.get("geoLocation") or item.get("city")),
            city=item.get("city"),
            state=item.get("state") or item.get("region"),
            country=item.get("country") or item.get("countryCode"),
            source="linkedin",
            source_url=item.get("url") or item.get("profileUrl"),
            raw_data=item,
        )

    def _parse_lead(self, item: dict[str, Any]) -> ApifyLead:
        """
        Unified lead parser for all Apify actor outputs.

        Handles field name variations from different actors:
        - Leads Finder Primary (IoSHqwTR9YGhzccez)
        - Leads Scraper PPE (T1XDXWc1L92AfIJtd)
        - Leads Scraper Multi (VYRyEF4ygTTkaIghe)

        Args:
            item: Raw item from Apify dataset.

        Returns:
            ApifyLead with normalized field names.
        """
        # Handle various field name variations from different actors
        first_name = item.get("firstName") or item.get("first_name") or item.get("FirstName") or ""
        last_name = item.get("lastName") or item.get("last_name") or item.get("LastName") or ""
        full_name = (
            item.get("fullName")
            or item.get("full_name")
            or item.get("name")
            or item.get("Name")
            or f"{first_name} {last_name}".strip()
        )

        # Parse name if only full_name is provided
        if not first_name and full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        # Handle organization/company nested structures
        org = item.get("organization") or item.get("company") or {}
        if isinstance(org, str):
            org = {"name": org}

        company_name = (
            item.get("companyName")
            or item.get("company_name")
            or item.get("company")
            or item.get("currentCompany")
            or org.get("name")
        )
        company_domain = (
            item.get("companyDomain")
            or item.get("company_domain")
            or item.get("domain")
            or org.get("primary_domain")
            or org.get("domain")
        )
        company_size = (
            item.get("companySize")
            or item.get("company_size")
            or item.get("employeeCount")
            or item.get("employees")
            or org.get("estimated_num_employees")
            or org.get("size")
        )
        company_industry = (
            item.get("industry")
            or item.get("companyIndustry")
            or item.get("company_industry")
            or org.get("industry")
        )

        return ApifyLead(
            first_name=first_name or None,
            last_name=last_name or None,
            full_name=full_name or None,
            email=(
                item.get("email")
                or item.get("workEmail")
                or item.get("work_email")
                or item.get("Email")
            ),
            linkedin_url=(
                item.get("linkedinUrl")
                or item.get("linkedin_url")
                or item.get("profileUrl")
                or item.get("url")
                or item.get("LinkedInUrl")
            ),
            linkedin_id=(
                item.get("linkedinId") or item.get("linkedin_id") or item.get("profileId")
            ),
            headline=(item.get("headline") or item.get("Headline") or item.get("title")),
            title=(
                item.get("jobTitle")
                or item.get("job_title")
                or item.get("title")
                or item.get("Title")
                or item.get("currentPosition")
            ),
            seniority=(
                item.get("seniority") or item.get("seniorityLevel") or item.get("Seniority")
            ),
            department=(item.get("department") or item.get("Department")),
            company_name=company_name if isinstance(company_name, str) else None,
            company_linkedin_url=(
                item.get("companyLinkedinUrl")
                or item.get("company_linkedin_url")
                or item.get("companyUrl")
            ),
            company_domain=company_domain if isinstance(company_domain, str) else None,
            company_size=str(company_size) if company_size else None,
            company_industry=company_industry if isinstance(company_industry, str) else None,
            location=(
                item.get("location")
                or item.get("geoLocation")
                or item.get("Location")
                or item.get("city")
            ),
            city=(item.get("city") or item.get("City")),
            state=(item.get("state") or item.get("region") or item.get("State")),
            country=(item.get("country") or item.get("countryCode") or item.get("Country")),
            source="apify",
            source_url=(item.get("url") or item.get("profileUrl") or item.get("linkedinUrl")),
            raw_data=item,
        )

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO datetime string."""
        if not value:
            return None
        try:
            # Handle various ISO formats
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check Apify API connectivity and credentials.

        Returns:
            Health check status.
        """
        try:
            user_info = await self.client.user().get()
            return {
                "name": "apify",
                "healthy": True,
                "user_id": user_info.get("id") if user_info else None,
                "username": user_info.get("username") if user_info else None,
            }
        except Exception as e:
            return {
                "name": "apify",
                "healthy": False,
                "error": str(e),
            }
