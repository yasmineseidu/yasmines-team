"""
Reddit Miner for Persona Research.

Specialized module for extracting pain points, exact quotes, and language
patterns from Reddit posts and comments. Uses both Reddit API and Claude SDK
WebSearch for comprehensive coverage.

Key Features:
- Pain point extraction with emotional indicators
- Exact quote preservation (never paraphrase)
- Language pattern detection
- Engagement-weighted scoring
- Rate-limited, resilient API calls
"""

import asyncio
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.persona_research.schemas import (
    LanguagePattern,
    PainPointQuote,
)
from src.integrations.reddit import (
    RedditClient,
    RedditComment,
    RedditPost,
    RedditSortType,
    RedditTimeFilter,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class RedditMinerError(Exception):
    """Base exception for Reddit miner errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RateLimitExceededError(RedditMinerError):
    """Raised when Reddit API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        message = "Reddit rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after}s"
        super().__init__(message, {"retry_after": retry_after})


class AuthenticationFailedError(RedditMinerError):
    """Raised when Reddit authentication fails."""

    pass


class ServiceUnavailableError(RedditMinerError):
    """Raised when Reddit API is unavailable (5xx errors)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(
            f"Reddit service unavailable (status {status_code})",
            {"status_code": status_code},
        )


# ============================================================================
# Token Bucket Rate Limiter
# ============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for Reddit API calls.

    Reddit allows 60 requests/minute per OAuth client ID.
    """

    # Reddit API limit: 60 requests/minute (conservative)
    RATE_LIMIT = 60
    RATE_WINDOW = 60.0  # seconds

    def __init__(self, service_name: str = "Reddit") -> None:
        """Initialize rate limiter."""
        self.capacity = self.RATE_LIMIT
        self.refill_rate = self.RATE_LIMIT / self.RATE_WINDOW
        self.service_name = service_name
        self.tokens = float(self.capacity)
        self.last_update = time.time()  # Use time.time() instead of event loop
        self._lock: asyncio.Lock | None = None  # Lazily initialized

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary."""
        # Lazily initialize the lock in async context
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            now = time.time()
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

            # Refill based on actual elapsed time (not full capacity!)
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate,
            )
            self.last_update = now
            self.tokens -= tokens


# ============================================================================
# Reddit Mining Results
# ============================================================================


@dataclass
class RedditMiningResult:
    """Results from Reddit mining operation."""

    pain_points: list[PainPointQuote]
    language_patterns: list[LanguagePattern]
    quotes: list[dict[str, Any]]
    subreddit_relevance: dict[str, float]
    emotional_indicators: list[str]
    posts_analyzed: int = 0
    comments_analyzed: int = 0
    errors: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Reddit Miner
# ============================================================================


class RedditMiner:
    """
    Specialized miner for extracting persona data from Reddit.

    Extracts:
    - Pain points with exact quotes
    - Language patterns (phrases, jargon)
    - Emotional indicators
    - Engagement-weighted content
    """

    # Pain point indicator phrases
    PAIN_INDICATORS = [
        "struggling with",
        "frustrated by",
        "frustrated with",
        "biggest challenge",
        "biggest problem",
        "hate when",
        "hate it when",
        "wish i could",
        "wish we could",
        "if only",
        "anyone else deal with",
        "drives me crazy",
        "nightmare",
        "pain in the",
        "waste of time",
        "so annoying",
        "can't stand",
        "fed up with",
        "sick of",
        "tired of",
        "help me",
        "need advice",
        "any advice",
        "how do you handle",
        "how do you deal with",
        "rant",
        "vent",
    ]

    # Emotional intensity words
    EMOTIONAL_WORDS = [
        "frustrated",
        "annoying",
        "nightmare",
        "hate",
        "terrible",
        "awful",
        "ridiculous",
        "insane",
        "crazy",
        "impossible",
        "exhausting",
        "overwhelming",
        "stressful",
        "painful",
        "miserable",
        "desperate",
        "urgent",
        "critical",
    ]

    # Subreddits by industry
    SUBREDDITS_BY_INDUSTRY: dict[str, list[str]] = {
        "saas": ["SaaS", "startups", "sales", "marketing", "Entrepreneur", "smallbusiness"],
        "technology": ["technology", "programming", "sysadmin", "ITManagers", "devops"],
        "marketing": ["marketing", "digital_marketing", "PPC", "SEO", "content_marketing"],
        "sales": ["sales", "salesforce", "B2Bsales", "InsideSales"],
        "finance": ["finance", "FinancialCareers", "CFO", "accounting"],
        "healthcare": ["healthcare", "healthIT", "nursing", "medicine"],
        "ecommerce": ["ecommerce", "shopify", "FulfillmentByAmazon", "dropship"],
        "default": ["business", "Entrepreneur", "smallbusiness", "startups", "careerguidance"],
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "smarter-team-persona-research/1.0",
    ) -> None:
        """
        Initialize Reddit miner.

        Args:
            client_id: Reddit app client ID
            client_secret: Reddit app client secret
            user_agent: User agent string for Reddit API
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._rate_limiter = TokenBucketRateLimiter("Reddit")
        self._client: RedditClient | None = None

    async def _get_client(self) -> RedditClient:
        """Get or create Reddit client."""
        if self._client is None:
            self._client = RedditClient(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
        return self._client

    def get_subreddits_for_industry(self, industry: str) -> list[str]:
        """
        Get relevant subreddits for an industry.

        Args:
            industry: Industry name

        Returns:
            List of subreddit names
        """
        industry_lower = industry.lower()
        return self.SUBREDDITS_BY_INDUSTRY.get(
            industry_lower,
            self.SUBREDDITS_BY_INDUSTRY["default"],
        )

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search_posts(
        self,
        query: str,
        subreddits: list[str] | None = None,
        sort: RedditSortType = RedditSortType.HOT,
        time_filter: RedditTimeFilter = RedditTimeFilter.MONTH,
        limit: int = 25,
    ) -> list[RedditPost]:
        """
        Search Reddit posts with retry and rate limiting.

        Args:
            query: Search query
            subreddits: List of subreddits to search (None for all)
            sort: Sort type
            time_filter: Time filter
            limit: Maximum posts to return

        Returns:
            List of Reddit posts
        """
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                # Search each subreddit if specified
                all_posts: list[RedditPost] = []

                if subreddits:
                    for subreddit in subreddits[:5]:  # Limit to 5 subreddits
                        try:
                            await self._rate_limiter.acquire()
                            posts = await client.get_subreddit_posts(
                                subreddit=subreddit,
                                sort=sort,
                                time_filter=time_filter,
                                limit=min(limit, 25),
                            )
                            all_posts.extend(posts)
                        except Exception as e:
                            logger.warning(f"Failed to get posts from r/{subreddit}: {e}")
                            continue
                else:
                    # Search all Reddit
                    results = await client.search_posts(
                        query=query,
                        sort=sort.value,
                        time_filter=time_filter,
                        limit=limit,
                    )
                    all_posts = results.posts

                return all_posts

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                raise RateLimitExceededError(retry_after) from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Reddit authentication failed") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError(e.response.status_code) from e
            raise RedditMinerError(f"Reddit API error: {e}") from e

        except httpx.TimeoutException as e:
            raise RedditMinerError("Reddit request timed out") from e

        except httpx.NetworkError as e:
            raise RedditMinerError(f"Reddit network error: {e}") from e

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2.0, max=60.0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, ServiceUnavailableError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_post_comments(
        self,
        post_id: str,
        subreddit: str,
        limit: int = 50,
    ) -> list[RedditComment]:
        """
        Get comments for a post with retry and rate limiting.

        Args:
            post_id: Reddit post ID
            subreddit: Subreddit name
            limit: Maximum comments to return

        Returns:
            List of Reddit comments
        """
        await self._rate_limiter.acquire()

        try:
            client = await self._get_client()
            async with client:
                comments = await client.get_post_comments(
                    post_id=post_id,
                    subreddit=subreddit,
                    sort="top",
                    limit=limit,
                )
                return comments

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                raise RateLimitExceededError(retry_after) from e
            if e.response.status_code == 401:
                raise AuthenticationFailedError("Reddit authentication failed") from e
            if 500 <= e.response.status_code < 600:
                raise ServiceUnavailableError(e.response.status_code) from e
            raise RedditMinerError(f"Reddit API error: {e}") from e

        except httpx.TimeoutException as e:
            raise RedditMinerError("Reddit request timed out") from e

        except httpx.NetworkError as e:
            raise RedditMinerError(f"Reddit network error: {e}") from e

    def extract_pain_points(
        self,
        posts: list[RedditPost],
        comments: list[RedditComment] | None = None,
        max_quotes: int = 20,
    ) -> list[PainPointQuote]:
        """
        Extract pain points with exact quotes from posts and comments.

        Args:
            posts: List of Reddit posts
            comments: List of Reddit comments (optional)
            max_quotes: Maximum quotes to extract

        Returns:
            List of pain point quotes
        """
        pain_points: list[PainPointQuote] = []

        # Process posts
        for post in posts:
            text = f"{post.title} {post.selftext}".lower()

            for indicator in self.PAIN_INDICATORS:
                if indicator in text:
                    # Extract the sentence containing the indicator
                    quote = self._extract_quote_context(
                        f"{post.title}\n\n{post.selftext}",
                        indicator,
                    )

                    if quote and len(quote) >= 50:
                        # Calculate intensity based on engagement
                        intensity = self._calculate_intensity(
                            text,
                            post.score,
                            post.num_comments,
                        )

                        pain_point = PainPointQuote(
                            pain=self._extract_pain_description(quote, indicator),
                            intensity=intensity,
                            quote=quote[:500],  # Limit quote length
                            source=f"https://reddit.com{post.permalink}",
                            source_type="reddit",
                            frequency=self._estimate_frequency(post.score),
                            engagement_score=post.score,
                            raw={
                                "post_id": post.id,
                                "subreddit": post.subreddit,
                                "title": post.title,
                                "num_comments": post.num_comments,
                            },
                        )
                        pain_points.append(pain_point)

                        if len(pain_points) >= max_quotes:
                            break

            if len(pain_points) >= max_quotes:
                break

        # Process comments
        if comments:
            for comment in comments:
                if len(pain_points) >= max_quotes:
                    break

                text_lower = comment.body.lower()

                for indicator in self.PAIN_INDICATORS:
                    if indicator in text_lower:
                        quote = self._extract_quote_context(comment.body, indicator)

                        if quote and len(quote) >= 50:
                            intensity = self._calculate_intensity(
                                text_lower,
                                comment.score,
                                comment.replies_count,
                            )

                            pain_point = PainPointQuote(
                                pain=self._extract_pain_description(quote, indicator),
                                intensity=intensity,
                                quote=quote[:500],
                                source=f"https://reddit.com{comment.permalink}",
                                source_type="reddit",
                                frequency=self._estimate_frequency(comment.score),
                                engagement_score=comment.score,
                                raw={
                                    "comment_id": comment.id,
                                    "subreddit": comment.subreddit,
                                    "post_id": comment.post_id,
                                },
                            )
                            pain_points.append(pain_point)
                            break

        # Sort by intensity and engagement
        pain_points.sort(
            key=lambda p: (p.intensity, p.engagement_score),
            reverse=True,
        )

        return pain_points[:max_quotes]

    def extract_language_patterns(
        self,
        posts: list[RedditPost],
        comments: list[RedditComment] | None = None,
        max_patterns: int = 30,
    ) -> list[LanguagePattern]:
        """
        Extract language patterns from posts and comments.

        Args:
            posts: List of Reddit posts
            comments: List of Reddit comments (optional)
            max_patterns: Maximum patterns to extract

        Returns:
            List of language patterns
        """
        # Collect all text
        all_text: list[str] = []
        for post in posts:
            all_text.append(post.title)
            all_text.append(post.selftext)

        if comments:
            for comment in comments:
                all_text.append(comment.body)

        # Count phrase frequencies
        phrase_counter: Counter[str] = Counter()
        phrase_sources: dict[str, str] = {}

        for text in all_text:
            phrases = self._extract_phrases(text)
            for phrase in phrases:
                phrase_counter[phrase] += 1
                if phrase not in phrase_sources:
                    phrase_sources[phrase] = text[:100]

        # Create language pattern objects
        patterns: list[LanguagePattern] = []

        for phrase, count in phrase_counter.most_common(max_patterns):
            if count >= 2:  # Only include phrases seen 2+ times
                category = self._categorize_phrase(phrase)

                pattern = LanguagePattern(
                    phrase=phrase,
                    context=phrase_sources.get(phrase, ""),
                    category=category,
                    source="reddit",
                    frequency=count,
                )
                patterns.append(pattern)

        return patterns

    def extract_emotional_indicators(
        self,
        posts: list[RedditPost],
        comments: list[RedditComment] | None = None,
    ) -> list[str]:
        """
        Extract emotional indicators from content.

        Args:
            posts: List of Reddit posts
            comments: List of Reddit comments (optional)

        Returns:
            List of emotional indicator phrases
        """
        indicators: list[str] = []

        # Process posts
        for post in posts:
            text = f"{post.title} {post.selftext}".lower()

            for word in self.EMOTIONAL_WORDS:
                if word in text:
                    # Find the sentence containing the word
                    sentences = re.split(r"[.!?]", post.selftext or post.title)
                    for sentence in sentences:
                        if word in sentence.lower() and len(sentence.strip()) > 20:
                            indicators.append(sentence.strip())
                            break

        # Process comments
        if comments:
            for comment in comments:
                text_lower = comment.body.lower()

                for word in self.EMOTIONAL_WORDS:
                    if word in text_lower:
                        sentences = re.split(r"[.!?]", comment.body)
                        for sentence in sentences:
                            if word in sentence.lower() and len(sentence.strip()) > 20:
                                indicators.append(sentence.strip())
                                break

        # Remove duplicates and limit
        unique_indicators = list(dict.fromkeys(indicators))
        return unique_indicators[:50]

    async def mine_for_persona(
        self,
        job_titles: list[str],
        industry: str,
        pain_points_hint: list[str] | None = None,
        max_subreddits: int = 5,
        posts_per_subreddit: int = 25,
    ) -> RedditMiningResult:
        """
        Complete Reddit mining operation for persona research.

        Args:
            job_titles: Target job titles
            industry: Target industry
            pain_points_hint: Hints from niche research
            max_subreddits: Maximum subreddits to search
            posts_per_subreddit: Posts per subreddit

        Returns:
            RedditMiningResult with all extracted data
        """
        logger.info(f"Starting Reddit mining for {job_titles} in {industry}")

        result = RedditMiningResult(
            pain_points=[],
            language_patterns=[],
            quotes=[],
            subreddit_relevance={},
            emotional_indicators=[],
        )

        try:
            # Get relevant subreddits
            subreddits = self.get_subreddits_for_industry(industry)[:max_subreddits]

            # Build search queries
            queries = self._build_search_queries(job_titles, pain_points_hint)

            # Search posts
            all_posts: list[RedditPost] = []
            all_comments: list[RedditComment] = []

            for subreddit in subreddits:
                try:
                    posts = await self.search_posts(
                        query=queries[0],  # Primary query
                        subreddits=[subreddit],
                        limit=posts_per_subreddit,
                    )
                    all_posts.extend(posts)

                    # Calculate subreddit relevance
                    if posts:
                        avg_score = sum(p.score for p in posts) / len(posts)
                        result.subreddit_relevance[subreddit] = min(avg_score / 100, 10.0)

                except RedditMinerError as e:
                    logger.warning(f"Failed to search r/{subreddit}: {e}")
                    result.errors.append(str(e))
                    continue

            # Get comments from top posts
            top_posts = sorted(all_posts, key=lambda p: p.score, reverse=True)[:10]

            for post in top_posts:
                try:
                    comments = await self.get_post_comments(
                        post_id=post.id,
                        subreddit=post.subreddit,
                        limit=30,
                    )
                    all_comments.extend(comments)
                except RedditMinerError as e:
                    logger.warning(f"Failed to get comments for {post.id}: {e}")
                    continue

            # Extract pain points
            result.pain_points = self.extract_pain_points(
                posts=all_posts,
                comments=all_comments,
                max_quotes=20,
            )

            # Extract language patterns
            result.language_patterns = self.extract_language_patterns(
                posts=all_posts,
                comments=all_comments,
                max_patterns=30,
            )

            # Extract emotional indicators
            result.emotional_indicators = self.extract_emotional_indicators(
                posts=all_posts,
                comments=all_comments,
            )

            # Build quotes list for raw storage
            result.quotes = [
                {
                    "quote": pp.quote,
                    "source": pp.source,
                    "intensity": pp.intensity,
                    "engagement": pp.engagement_score,
                }
                for pp in result.pain_points
            ]

            result.posts_analyzed = len(all_posts)
            result.comments_analyzed = len(all_comments)

            logger.info(
                f"Reddit mining complete: {len(result.pain_points)} pain points, "
                f"{len(result.language_patterns)} patterns, "
                f"{len(result.quotes)} quotes"
            )

        except Exception as e:
            logger.error(f"Reddit mining failed: {e}")
            result.errors.append(str(e))

        return result

    def _extract_quote_context(self, text: str, indicator: str) -> str:
        """Extract quote context around a pain indicator."""
        text_lower = text.lower()
        idx = text_lower.find(indicator)

        if idx == -1:
            return ""

        # Find sentence boundaries
        start = max(0, text.rfind(".", 0, idx) + 1)
        end = text.find(".", idx)
        end = min(len(text), idx + 200) if end == -1 else min(end + 1, len(text))

        return text[start:end].strip()

    def _extract_pain_description(self, quote: str, indicator: str) -> str:
        """Extract a short pain description from a quote."""
        # Clean up and shorten for pain description
        words = quote.split()[:15]
        return " ".join(words) + "..." if len(words) == 15 else " ".join(words)

    def _calculate_intensity(
        self,
        text: str,
        score: int,
        replies: int,
    ) -> int:
        """Calculate pain intensity from 1-10."""
        # Base intensity
        intensity = 5

        # Adjust by emotional words
        emotional_count = sum(1 for word in self.EMOTIONAL_WORDS if word in text)
        intensity += min(emotional_count, 3)

        # Adjust by engagement
        if score > 100:
            intensity += 1
        if replies > 20:
            intensity += 1

        return min(max(intensity, 1), 10)

    def _estimate_frequency(self, score: int) -> str:
        """Estimate pain point frequency from engagement."""
        if score > 200:
            return "very_common"
        if score > 50:
            return "common"
        if score > 10:
            return "occasional"
        return "rare"

    def _build_search_queries(
        self,
        job_titles: list[str],
        pain_points_hint: list[str] | None = None,
    ) -> list[str]:
        """Build search queries for Reddit."""
        queries = []
        title = job_titles[0] if job_titles else "manager"

        # Pain point queries
        queries.append(f"{title} struggling frustrated help")
        queries.append(f"{title} biggest challenge problem")
        queries.append(f"{title} advice needed")

        # Add hints if provided
        if pain_points_hint:
            for hint in pain_points_hint[:3]:
                queries.append(f"{title} {hint}")

        return queries

    def _extract_phrases(self, text: str) -> list[str]:
        """Extract meaningful phrases from text."""
        # Clean text
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\'-]", "", text)

        # Extract 3-5 word phrases
        words = text.split()
        phrases: list[str] = []

        for i in range(len(words) - 2):
            phrase = " ".join(words[i : i + 3]).lower()
            if len(phrase) > 10 and not self._is_stop_phrase(phrase):
                phrases.append(phrase)

        return phrases

    def _is_stop_phrase(self, phrase: str) -> bool:
        """Check if phrase is a stop phrase (not useful)."""
        stop_phrases = [
            "the and",
            "and the",
            "is the",
            "in the",
            "to the",
            "of the",
            "i don't",
            "you can",
            "it is",
        ]
        return any(stop in phrase for stop in stop_phrases)

    def _categorize_phrase(self, phrase: str) -> str:
        """Categorize a phrase."""
        phrase_lower = phrase.lower()

        if any(word in phrase_lower for word in self.EMOTIONAL_WORDS):
            return "emotional"
        if any(word in phrase_lower for word in self.PAIN_INDICATORS):
            return "pain"
        if any(word in phrase_lower for word in ["want", "need", "goal", "achieve"]):
            return "goal"

        return "jargon"
