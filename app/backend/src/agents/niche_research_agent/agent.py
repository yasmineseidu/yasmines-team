"""
Niche Research Agent - Phase 1, Agent 1.1.

Uses Reddit API, web search (Brave/Tavily), and Claude Agent SDK for
multi-strategy niche discovery and pain point extraction.

Phase 1 Research Steps:
1. Parallel Web Research: Reddit search, web search, trend analysis
2. Data Aggregation: Combine findings from all sources
3. Subreddit Scoring: Score by relevance and engagement
4. Pain Point Extraction: Extract common pain points
5. Opportunity Identification: Identify business opportunities

Database Interactions:
- INPUT: Reads from campaigns table (via campaign_setup_agent)
  - campaign_id, target_audience, product_type
- OUTPUT: Writes to niche_research table
  - niche_research_id, subreddits, pain_points, opportunities
- HANDOFF: Direct handoff to persona_research_agent (next in Phase 1)
"""

import asyncio
import logging
import math
import os
from collections import Counter
from datetime import datetime
from typing import Any

from src.integrations.brave import BraveClient
from src.integrations.reddit import (
    RedditClient,
    RedditSortType,
    RedditSubreddit,
    RedditTimeFilter,
)
from src.integrations.tavily import TavilyClient
from src.models.niche_research import (
    NicheAnalysisConfig,
    NicheOpportunity,
    NichePainPoint,
    NicheResearchResult,
    NicheSubreddit,
)

logger = logging.getLogger(__name__)


class NicheResearchAgentError(Exception):
    """Exception raised for niche research agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NicheResearchAgent:
    """
    Agent for discovering and analyzing market niches.

    Uses Reddit API for community discovery, web search for market validation,
    and AI analysis for pain point extraction and opportunity identification.

    Example:
        >>> agent = NicheResearchAgent()
        >>> result = await agent.research_niche("AI tools for solopreneurs")
        >>> print(f"Found {len(result.subreddits)} relevant subreddits")
        >>> print(f"Identified {len(result.pain_points)} pain points")
    """

    def __init__(
        self,
        reddit_client_id: str | None = None,
        reddit_client_secret: str | None = None,
        brave_api_key: str | None = None,
        tavily_api_key: str | None = None,
    ) -> None:
        """
        Initialize the Niche Research Agent.

        Args:
            reddit_client_id: Reddit app client ID (from environment if not provided)
            reddit_client_secret: Reddit app client secret (from environment if not provided)
            brave_api_key: Brave Search API key (from environment if not provided)
            tavily_api_key: Tavily Search API key (from environment if not provided)
        """
        # Get API keys from environment if not provided
        self.reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY", "")
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")

        self.name = "niche_research_agent"
        logger.info(f"Initialized {self.name}")

    async def _get_reddit_client(self) -> RedditClient:
        """Get or create Reddit client."""
        if not self.reddit_client_id or not self.reddit_client_secret:
            raise NicheResearchAgentError(
                "Reddit credentials required",
                {"missing": ["reddit_client_id", "reddit_client_secret"]},
            )
        return RedditClient(
            client_id=self.reddit_client_id,
            client_secret=self.reddit_client_secret,
            user_agent="smarter-team-niche-research/1.0",
        )

    async def _get_brave_client(self) -> BraveClient:
        """Get or create Brave Search client."""
        if not self.brave_api_key:
            raise NicheResearchAgentError(
                "Brave API key required",
                {"missing": ["brave_api_key"]},
            )
        return BraveClient(api_key=self.brave_api_key)

    async def _get_tavily_client(self) -> TavilyClient:
        """Get or create Tavily Search client."""
        if not self.tavily_api_key:
            raise NicheResearchAgentError(
                "Tavily API key required",
                {"missing": ["tavily_api_key"]},
            )
        return TavilyClient(api_key=self.tavily_api_key)

    async def _parallel_web_research(
        self,
        query: str,
        config: NicheAnalysisConfig,
    ) -> dict[str, Any]:
        """
        Phase 1.1: Parallel web research using multiple sources.

        Searches Reddit, Brave, and Tavily in parallel for maximum speed.

        Args:
            query: Niche search query
            config: Analysis configuration

        Returns:
            Dictionary with research findings from all sources
        """
        logger.info(f"Starting parallel web research for query: {query}")

        results: dict[str, Any] = {
            "reddit_findings": [],
            "web_findings": [],
            "trend_findings": [],
            "errors": [],
        }

        # Create tasks for parallel execution
        tasks = []

        # Reddit search task
        if self.reddit_client_id and self.reddit_client_secret:
            tasks.append(self._search_reddit_parallel(query, config))

        # Brave web search task
        if self.brave_api_key:
            tasks.append(self._search_web_parallel(query, config))

        # Tavily research task
        if self.tavily_api_key:
            tasks.append(self._search_tavily_parallel(query, config))

        # Execute all tasks in parallel
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    logger.warning(f"Research task {i} failed: {result}")
                    results["errors"].append(str(result))
                elif isinstance(result, dict):
                    # Merge results
                    results.update(result)

        logger.info(
            f"Parallel research complete. Found {len(results.get('subreddits', []))} subreddits"
        )
        return results

    async def _search_reddit_parallel(
        self,
        query: str,
        config: NicheAnalysisConfig,
    ) -> dict[str, Any]:
        """
        Search Reddit for relevant subreddits and posts.

        Args:
            query: Search query
            config: Analysis configuration

        Returns:
            Dictionary with subreddit findings
        """
        logger.info("Searching Reddit for relevant subreddits")
        results: dict[str, Any] = {"subreddits": [], "posts": [], "errors": []}

        try:
            async with await self._get_reddit_client() as reddit:
                # Search for subreddits using search_subreddits
                subreddits_list = await reddit.search_subreddits(  # type: ignore[attr-defined]
                    query=query,
                    limit=config.max_subreddits,
                    include_over18=config.include_nsfw,
                )

                # Filter by subscriber count
                seen_subreddits: set[str] = set()
                for subreddit in subreddits_list:
                    if (
                        subreddit.subscribers >= config.min_subscribers
                        and subreddit.name not in seen_subreddits
                    ):
                        seen_subreddits.add(subreddit.name)
                        results["subreddits"].append(subreddit)

                    if len(results["subreddits"]) >= config.max_subreddits:
                        break

                # Get top posts from each subreddit
                for subreddit in results["subreddits"][:5]:  # Limit to top 5
                    try:
                        posts = await reddit.get_subreddit_posts(  # type: ignore[attr-defined]
                            subreddit.name,
                            sort=RedditSortType.HOT,
                            time_filter=RedditTimeFilter.MONTH,
                            limit=config.posts_per_subreddit,
                        )
                        results["posts"].extend(posts)
                    except Exception as e:
                        logger.warning(f"Failed to get posts from r/{subreddit.name}: {e}")

        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _search_web_parallel(
        self,
        query: str,
        config: NicheAnalysisConfig,
    ) -> dict[str, Any]:
        """
        Search the web using Brave for market validation.

        Args:
            query: Search query
            config: Analysis configuration

        Returns:
            Dictionary with web search findings
        """
        logger.info("Searching web with Brave for market validation")
        results: dict[str, Any] = {"web_results": []}

        try:
            async with await self._get_brave_client() as brave:
                # Search for niche validation
                search_queries = [
                    f"{query} market size",
                    f"{query} business opportunities",
                    f"{query} problems challenges",
                    f"{query} community forum",
                ]

                for search_query in search_queries:
                    try:
                        response = await brave.search(  # type: ignore[attr-defined]
                            query=search_query,
                            count=10,
                            freshness="month",
                        )
                        results["web_results"].extend(response.results)
                    except Exception as e:
                        logger.warning(f"Brave search failed for '{search_query}': {e}")
                        continue

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            results["errors"] = [str(e)]

        return results

    async def _search_tavily_parallel(
        self,
        query: str,
        config: NicheAnalysisConfig,
    ) -> dict[str, Any]:
        """
        Search using Tavily for deep research.

        Args:
            query: Search query
            config: Analysis configuration

        Returns:
            Dictionary with Tavily research findings
        """
        logger.info("Searching with Tavily for deep research")
        results: dict[str, Any] = {"research_results": []}

        try:
            async with await self._get_tavily_client() as tavily:
                # Perform deep research
                response = await tavily.research(  # type: ignore[attr-defined]
                    query=f"{query} niche market business opportunities",
                    max_iterations=3,
                )
                results["research_results"] = response.results

        except Exception as e:
            logger.error(f"Tavily research failed: {e}")
            results["errors"] = [str(e)]

        return results

    async def _aggregate_findings(
        self,
        research_data: dict[str, Any],
        config: NicheAnalysisConfig,
    ) -> dict[str, Any]:
        """
        Phase 1.2: Aggregate findings from all research sources.

        Combines data from Reddit, web search, and Tavily into unified results.

        Args:
            research_data: Raw research data from all sources
            config: Analysis configuration

        Returns:
            Dictionary with aggregated findings
        """
        logger.info("Aggregating findings from all sources")

        aggregated = {
            "subreddits": research_data.get("subreddits", []),
            "posts": research_data.get("posts", []),
            "web_results": research_data.get("web_results", []),
            "research_results": research_data.get("research_results", []),
            "trend_keywords": [],
        }

        # Extract trend keywords from web results
        keywords: Counter[str] = Counter()
        for result in aggregated["web_results"][:20]:
            # Simple keyword extraction from titles
            words = result.title.lower().split()
            for word in words:
                if len(word) > 4:  # Only meaningful words
                    keywords[word] += 1

        aggregated["trend_keywords"] = [kw for kw, _ in keywords.most_common(20)]

        logger.info(f"Aggregated {len(aggregated['subreddits'])} subreddits")
        return aggregated

    async def _score_subreddits(
        self,
        aggregated_data: dict[str, Any],
        config: NicheAnalysisConfig,
    ) -> list[NicheSubreddit]:
        """
        Phase 1.3: Score subreddits by relevance and engagement.

        Args:
            aggregated_data: Aggregated research findings
            config: Analysis configuration

        Returns:
            List of scored niche subreddits
        """
        logger.info("Scoring subreddits by relevance and engagement")

        scored_subreddits: list[NicheSubreddit] = []

        for subreddit in aggregated_data.get("subreddits", []):
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(subreddit)

            # Calculate relevance score based on keyword matching
            relevance_score = self._calculate_relevance_score(
                subreddit,
                aggregated_data.get("trend_keywords", []),
            )

            niche_sub = NicheSubreddit(
                name=subreddit.name,
                title=subreddit.title,
                description=subreddit.public_description,
                subscriber_count=subreddit.subscribers,
                active_users=subreddit.active_users,
                engagement_score=engagement_score,
                relevance_score=relevance_score,
                url=subreddit.url,
                created_at=datetime.fromtimestamp(subreddit.created_utc),
                raw=subreddit.raw if hasattr(subreddit, "raw") else {},
            )

            scored_subreddits.append(niche_sub)

        # Sort by combined score (descending)
        scored_subreddits.sort(
            key=lambda s: s.engagement_score * config.engagement_weight
            + s.relevance_score * config.relevance_weight,
            reverse=True,
        )

        logger.info(f"Scored {len(scored_subreddits)} subreddits")
        return scored_subreddits

    def _calculate_engagement_score(
        self,
        subreddit: RedditSubreddit,
    ) -> float:
        """
        Calculate engagement score for a subreddit.

        Score based on:
        - Active user ratio (active_users / subscribers)
        - Subscriber count (logarithmic scale)
        - Base score of 1.0

        Args:
            subreddit: RedditSubreddit object

        Returns:
            Engagement score (0.0 to 10.0)
        """
        # Active user ratio (higher is better)
        if subreddit.subscribers > 0:
            active_ratio = subreddit.active_users / subreddit.subscribers
        else:
            active_ratio = 0.0

        # Normalize active ratio (typically 0.01 to 0.10)
        active_score = min(active_ratio * 20, 5.0)

        # Subscriber score (logarithmic, max 5.0)
        if subreddit.subscribers > 0:
            sub_score = min(math.log10(subreddit.subscribers) / 2, 5.0)
        else:
            sub_score = 0.0

        return active_score + sub_score

    def _calculate_relevance_score(
        self,
        subreddit: RedditSubreddit,
        keywords: list[str],
    ) -> float:
        """
        Calculate relevance score based on keyword matching.

        Args:
            subreddit: RedditSubreddit object
            keywords: List of trend keywords

        Returns:
            Relevance score (0.0 to 10.0)
        """
        description_lower = subreddit.title.lower() + " " + subreddit.public_description.lower()

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in description_lower)

        # Normalize score (max 10.0 for 10+ matches)
        return min(matches, 10.0)

    async def _extract_pain_points(
        self,
        aggregated_data: dict[str, Any],
        scored_subreddits: list[NicheSubreddit],
    ) -> list[NichePainPoint]:
        """
        Phase 1.4: Extract pain points from discussions.

        Analyzes post titles and content to identify common pain points.

        Args:
            aggregated_data: Aggregated research findings
            scored_subreddits: List of scored subreddits

        Returns:
            List of identified pain points
        """
        logger.info("Extracting pain points from discussions")

        pain_points: list[NichePainPoint] = []

        # Analyze post titles for pain point indicators
        pain_indicators = [
            "problem",
            "issue",
            "struggle",
            "difficult",
            "hard",
            "challenge",
            "frustrated",
            "annoying",
            "help",
            "how to",
            "need",
            "want",
            "looking for",
            "any advice",
            "solutions",
            "fix",
            "workaround",
        ]

        posts = aggregated_data.get("posts", [])

        # Count pain point mentions
        pain_counter: Counter[str] = Counter()
        source_posts: dict[str, list[str]] = {}

        for post in posts:
            title_lower = post.title.lower()

            # Check for pain indicators
            for indicator in pain_indicators:
                if indicator in title_lower:
                    # Extract the pain context (simple approach)
                    pain_context = self._extract_pain_context(post.title, indicator)
                    if pain_context:
                        pain_counter[pain_context] += 1
                        if pain_context not in source_posts:
                            source_posts[pain_context] = []
                        source_posts[pain_context].append(post.permalink)

        # Create pain point objects
        for pain, freq in pain_counter.most_common(10):
            severity = "high" if freq >= 5 else "medium" if freq >= 3 else "low"

            pain_point = NichePainPoint(
                description=pain,
                severity=severity,
                frequency=freq,
                source_posts=source_posts.get(pain, [])[:3],  # Top 3 sources
                source_subreddits=[s.name for s in scored_subreddits[:3]],
            )
            pain_points.append(pain_point)

        logger.info(f"Extracted {len(pain_points)} pain points")
        return pain_points

    def _extract_pain_context(self, title: str, indicator: str) -> str | None:
        """
        Extract pain context from post title.

        Args:
            title: Post title
            indicator: Pain indicator word found in title

        Returns:
            Pain context description or None
        """
        # Simple extraction: return the title with the indicator highlighted
        if indicator in title.lower():
            # Return a cleaned version of the title
            return title.strip()

        return None

    async def _identify_opportunities(
        self,
        pain_points: list[NichePainPoint],
        scored_subreddits: list[NicheSubreddit],
    ) -> list[NicheOpportunity]:
        """
        Phase 1.5: Identify business opportunities from pain points.

        For each pain point, identifies potential solutions/business opportunities.

        Args:
            pain_points: List of identified pain points
            scored_subreddits: List of scored subreddits

        Returns:
            List of identified opportunities
        """
        logger.info("Identifying business opportunities")

        opportunities: list[NicheOpportunity] = []

        # Total potential reach across all subreddits
        total_reach = sum(s.subscriber_count for s in scored_subreddits)

        for pain_point in pain_points[:5]:  # Top 5 pain points
            # Generate opportunity description
            opp_description = f"Solve {pain_point.description.lower()}"

            # Estimate potential reach
            potential_reach = min(total_reach, pain_point.frequency * 1000)

            # Confidence based on pain point severity and frequency
            severity_scores = {"high": 0.9, "medium": 0.6, "low": 0.3}
            confidence = severity_scores.get(pain_point.severity, 0.5) * min(
                pain_point.frequency / 10, 1.0
            )

            opportunity = NicheOpportunity(
                description=opp_description,
                pain_point=pain_point.description,
                target_audience=", ".join(s.name for s in scored_subreddits[:3]),
                potential_reach=potential_reach,
                confidence_score=confidence,
                supporting_evidence=pain_point.source_posts[:2],
            )
            opportunities.append(opportunity)

        logger.info(f"Identified {len(opportunities)} opportunities")
        return opportunities

    async def research_niche(
        self,
        query: str,
        *,
        max_subreddits: int = 10,
        posts_per_subreddit: int = 25,
        min_subscribers: int = 1000,
        include_nsfw: bool = False,
        engagement_weight: float = 0.5,
        relevance_weight: float = 0.5,
    ) -> NicheResearchResult:
        """
        Perform complete niche research analysis.

        This is the main entry point for niche research. It orchestrates
        all phases of the research pipeline:
        1. Parallel web research
        2. Data aggregation
        3. Subreddit scoring
        4. Pain point extraction
        5. Opportunity identification

        Args:
            query: Niche search query (e.g., "AI tools for solopreneurs")
            max_subreddits: Maximum number of subreddits to analyze
            posts_per_subreddit: Number of posts to analyze per subreddit
            min_subscribers: Minimum subscriber count for subreddits
            include_nsfw: Whether to include NSFW subreddits
            engagement_weight: Weight for engagement score (0.0 to 1.0)
            relevance_weight: Weight for relevance score (0.0 to 1.0)

        Returns:
            NicheResearchResult with complete analysis

        Raises:
            NicheResearchAgentError: If research fails
        """
        if not query or not query.strip():
            raise NicheResearchAgentError("Query is required and cannot be empty")

        logger.info(f"Starting niche research for: {query}")

        # Create analysis configuration
        config = NicheAnalysisConfig(
            search_query=query.strip(),
            max_subreddits=max_subreddits,
            posts_per_subreddit=posts_per_subreddit,
            min_subscribers=min_subscribers,
            include_nsfw=include_nsfw,
            engagement_weight=engagement_weight,
            relevance_weight=relevance_weight,
        )

        try:
            # Phase 1.1: Parallel web research
            research_data = await self._parallel_web_research(query, config)

            # Phase 1.2: Aggregate findings
            aggregated_data = await self._aggregate_findings(research_data, config)

            # Phase 1.3: Score subreddits
            scored_subreddits = await self._score_subreddits(aggregated_data, config)

            # Phase 1.4: Extract pain points
            pain_points = await self._extract_pain_points(aggregated_data, scored_subreddits)

            # Phase 1.5: Identify opportunities
            opportunities = await self._identify_opportunities(pain_points, scored_subreddits)

            # Calculate totals
            total_subscribers = sum(s.subscriber_count for s in scored_subreddits)
            total_active_users = sum(s.active_users for s in scored_subreddits)

            # Build result
            result = NicheResearchResult(
                niche=query,
                subreddits=scored_subreddits,
                pain_points=pain_points,
                opportunities=opportunities,
                total_subscribers=total_subscribers,
                total_active_users=total_active_users,
                research_metadata={
                    "max_subreddits": max_subreddits,
                    "posts_analyzed": len(aggregated_data.get("posts", [])),
                    "web_results": len(aggregated_data.get("web_results", [])),
                    "research_timestamp": datetime.now().isoformat(),
                },
                raw_responses={
                    "research_data": research_data,
                    "aggregated_data": aggregated_data,
                },
            )

            logger.info(
                f"Niche research complete: {len(result.subreddits)} subreddits, "
                f"{len(result.pain_points)} pain points, {len(result.opportunities)} opportunities"
            )

            return result

        except NicheResearchAgentError:
            raise
        except Exception as e:
            logger.error(f"Niche research failed: {e}")
            raise NicheResearchAgentError(f"Research failed: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health of the niche research agent.

        Verifies connectivity to all required services.

        Returns:
            Dictionary with health status for each service
        """
        services: dict[str, dict[str, Any]] = {}
        healthy = True

        # Check Reddit
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                async with await self._get_reddit_client() as reddit:
                    await reddit.search_posts("test", limit=1)  # type: ignore[attr-defined]
                services["reddit"] = {"healthy": True}
            except Exception as e:
                services["reddit"] = {"healthy": False, "error": str(e)}
                healthy = False
        else:
            services["reddit"] = {"healthy": False, "error": "No credentials"}
            healthy = False

        # Check Brave
        if self.brave_api_key:
            try:
                async with await self._get_brave_client() as brave:
                    await brave.search("test", count=1)  # type: ignore[attr-defined]
                services["brave"] = {"healthy": True}
            except Exception as e:
                services["brave"] = {"healthy": False, "error": str(e)}
        else:
            services["brave"] = {"healthy": False, "error": "No API key"}

        # Check Tavily
        if self.tavily_api_key:
            try:
                async with await self._get_tavily_client() as tavily:
                    await tavily.search("test", max_results=1)  # type: ignore[attr-defined]
                services["tavily"] = {"healthy": True}
            except Exception as e:
                services["tavily"] = {"healthy": False, "error": str(e)}
        else:
            services["tavily"] = {"healthy": False, "error": "No API key"}

        return {
            "agent": self.name,
            "services": services,
            "healthy": healthy,
        }

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return """You are a Niche Research Agent specializing in market discovery and analysis.

Your capabilities include:
- Discovering relevant communities (subreddits) for any niche
- Analyzing engagement and relevance metrics
- Extracting common pain points from community discussions
- Identifying business opportunities based on pain points

You use Reddit, web search, and AI analysis to provide comprehensive insights."""
