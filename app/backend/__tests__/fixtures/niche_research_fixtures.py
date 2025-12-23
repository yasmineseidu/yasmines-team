"""
Test fixtures for Niche Research Agent tests.

Provides mock data and factory functions for testing the niche research functionality.
"""

from datetime import datetime

from src.integrations.reddit import RedditPost, RedditSubreddit
from src.models.niche_research import (
    NicheAnalysisConfig,
    NicheOpportunity,
    NichePainPoint,
    NicheResearchResult,
    NicheSubreddit,
)


def mock_reddit_subreddit(
    name: str = "test_subreddit",
    subscribers: int = 10000,
    active_users: int = 500,
    over18: bool = False,
) -> RedditSubreddit:
    """Create a mock RedditSubreddit for testing."""
    return RedditSubreddit(
        name=name,
        display_name=f"r/{name}",
        title=f"Test {name} community",
        description=f"A community for {name} discussions",
        public_description=f"Public description for {name}",
        subscribers=subscribers,
        active_users=active_users,
        created_utc=1609459200.0,
        over18=over18,
        subreddit_type="public",
        url=f"https://www.reddit.com/r/{name}",
        icon_url=None,
        banner_url=None,
        raw={},
    )


def mock_reddit_post(
    subreddit: str = "test",
    title: str = "Test post",
    score: int = 100,
    num_comments: int = 50,
) -> RedditPost:
    """Create a mock RedditPost for testing."""
    return RedditPost(
        id="test_post_id",
        subreddit=subreddit,
        title=title,
        selftext="Test post content",
        author="test_user",
        score=score,
        upvote_ratio=0.9,
        num_comments=num_comments,
        created_utc=1609459200.0,
        url="https://www.reddit.com/r/test/comments/test",
        permalink="/r/test/comments/test/",
        is_self=True,
        is_video=False,
        over_18=False,
        spoiler=False,
        stickied=False,
        locked=False,
        raw={},
    )


def mock_niche_subreddit(
    name: str = "test_subreddit",
    subscriber_count: int = 10000,
    engagement_score: float = 5.0,
    relevance_score: float = 7.0,
) -> NicheSubreddit:
    """Create a mock NicheSubreddit for testing."""
    return NicheSubreddit(
        name=name,
        title=f"r/{name}",
        description=f"Test description for {name}",
        subscriber_count=subscriber_count,
        active_users=500,
        engagement_score=engagement_score,
        relevance_score=relevance_score,
        url=f"https://www.reddit.com/r/{name}",
        created_at=datetime.fromtimestamp(1609459200.0),
        raw={},
    )


def mock_niche_pain_point(
    description: str = "Test pain point",
    severity: str = "medium",
    frequency: int = 5,
) -> NichePainPoint:
    """Create a mock NichePainPoint for testing."""
    return NichePainPoint(
        description=description,
        severity=severity,
        frequency=frequency,
        source_posts=["/r/test/post1", "/r/test/post2"],
        source_subreddits=["test", "test2"],
        raw={},
    )


def mock_niche_opportunity(
    description: str = "Test opportunity",
    confidence_score: float = 0.7,
) -> NicheOpportunity:
    """Create a mock NicheOpportunity for testing."""
    return NicheOpportunity(
        description=description,
        pain_point="Test pain point",
        target_audience="r/test, r/test2",
        potential_reach=50000,
        confidence_score=confidence_score,
        supporting_evidence=["/r/test/post1"],
        raw={},
    )


def mock_niche_research_result(
    niche: str = "AI tools for solopreneurs",
) -> NicheResearchResult:
    """Create a mock NicheResearchResult for testing."""
    return NicheResearchResult(
        niche=niche,
        subreddits=[
            mock_niche_subreddit("entrepreneur", 50000, 7.0, 8.0),
            mock_niche_subreddit("solopreneur", 30000, 6.0, 9.0),
            mock_niche_subreddit("sideproject", 20000, 5.0, 7.0),
        ],
        pain_points=[
            mock_niche_pain_point("Finding customers", "high", 10),
            mock_niche_pain_point("Time management", "medium", 7),
            mock_niche_pain_point("Marketing on budget", "medium", 5),
        ],
        opportunities=[
            mock_niche_opportunity("AI-powered lead generation", 0.85),
            mock_niche_opportunity("Automated marketing assistant", 0.75),
        ],
        total_subscribers=100000,
        total_active_users=5000,
        research_metadata={
            "max_subreddits": 10,
            "posts_analyzed": 100,
            "web_results": 50,
        },
        raw_responses={},
    )


def mock_niche_analysis_config(
    search_query: str = "AI tools for solopreneurs",
) -> NicheAnalysisConfig:
    """Create a mock NicheAnalysisConfig for testing."""
    return NicheAnalysisConfig(
        search_query=search_query,
        max_subreddits=10,
        posts_per_subreddit=25,
        min_subscribers=1000,
        include_nsfw=False,
        engagement_weight=0.5,
        relevance_weight=0.5,
    )


# Sample pain point indicator words for testing
PAIN_INDICATORS = [
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


# Sample posts with pain points for testing
SAMPLE_POSTS_WITH_PAIN_POINTS = [
    "Struggling to find customers for my SaaS",
    "How do you manage time as a solopreneur?",
    "Need help with marketing on a tight budget",
    "Frustrated with cold email outreach",
    "Looking for solutions to automate lead generation",
    "Any advice on pricing my product?",
    "Problem with user retention",
    "Issue with payment processing",
    "Challenge of scaling without team",
    "Hard to balance development and sales",
]
