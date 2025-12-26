"""
Unit tests for Company Research Agent tools.

Tests all @tool decorated functions with mocked dependencies.
Coverage target: >90%

Note: The @tool decorator wraps functions in SdkMcpTool objects.
To test them directly, we access the .handler attribute which is the async function.
"""

import os
from unittest.mock import patch

import pytest

from src.agents.company_research.tools import (
    COMPANY_RESEARCH_TOOLS,
    SCORING_WEIGHTS,
    TOOL_COSTS,
    _calculate_recency_score,
    _calculate_total_score,
    _get_current_year,
    aggregate_company_research_tool,
    extract_and_score_facts_tool,
    search_company_funding_tool,
    search_company_hiring_tool,
    search_company_news_tool,
    search_company_tech_tool,
)

# Access the handler functions from SdkMcpTool objects
# The @tool decorator wraps the function in SdkMcpTool, so we need to access .handler
_search_company_news = search_company_news_tool.handler
_search_company_funding = search_company_funding_tool.handler
_search_company_hiring = search_company_hiring_tool.handler
_search_company_tech = search_company_tech_tool.handler
_extract_and_score_facts = extract_and_score_facts_tool.handler
_aggregate_company_research = aggregate_company_research_tool.handler


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_calculate_recency_score_recent(self) -> None:
        """Test recency score for very recent facts."""
        score = _calculate_recency_score(0)
        assert score == 1.0

    def test_calculate_recency_score_old(self) -> None:
        """Test recency score for old facts."""
        score = _calculate_recency_score(90)
        assert score == 0.0

    def test_calculate_recency_score_midpoint(self) -> None:
        """Test recency score for facts at midpoint."""
        score = _calculate_recency_score(45, decay_days=90)
        assert score == 0.5

    def test_calculate_recency_score_unknown(self) -> None:
        """Test recency score for unknown recency."""
        score = _calculate_recency_score(None)
        assert score == 0.5

    def test_calculate_total_score(self) -> None:
        """Test total score calculation with weights."""
        total = _calculate_total_score(
            recency_score=1.0,
            specificity_score=1.0,
            business_relevance_score=1.0,
            emotional_hook_score=1.0,
        )
        assert total == 1.0

    def test_calculate_total_score_partial(self) -> None:
        """Test total score with partial scores."""
        total = _calculate_total_score(
            recency_score=0.5,
            specificity_score=0.5,
            business_relevance_score=0.5,
            emotional_hook_score=0.5,
        )
        assert total == 0.5

    def test_get_current_year(self) -> None:
        """Test getting current year."""
        year = _get_current_year()
        assert isinstance(year, int)
        assert year >= 2025


class TestScoringWeights:
    """Tests for scoring weight configuration."""

    def test_weights_sum_to_one(self) -> None:
        """Verify scoring weights sum to 1.0."""
        total = sum(SCORING_WEIGHTS.values())
        assert total == 1.0

    def test_all_weights_present(self) -> None:
        """Verify all required weights are present."""
        assert "recency" in SCORING_WEIGHTS
        assert "specificity" in SCORING_WEIGHTS
        assert "business_relevance" in SCORING_WEIGHTS
        assert "emotional_hook" in SCORING_WEIGHTS


class TestToolCosts:
    """Tests for tool cost configuration."""

    def test_serper_cost(self) -> None:
        """Verify Serper cost."""
        assert TOOL_COSTS["serper_search"] == 0.001

    def test_tavily_cost(self) -> None:
        """Verify Tavily cost."""
        assert TOOL_COSTS["tavily_search"] == 0.001

    def test_perplexity_cost(self) -> None:
        """Verify Perplexity cost."""
        assert TOOL_COSTS["perplexity_search"] == 0.005

    def test_web_search_free(self) -> None:
        """Verify web search is free."""
        assert TOOL_COSTS["web_search"] == 0.0


class TestSearchCompanyNewsTool:
    """Tests for search_company_news tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _search_company_news(
            {
                "company_domain": "acme.com",
                "max_results": 5,
            }
        )
        assert result["is_error"] is True
        assert "required" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_empty_company_name_returns_error(self) -> None:
        """Test that empty company_name returns error."""
        result = await _search_company_news(
            {
                "company_name": "",
                "company_domain": "acme.com",
                "max_results": 5,
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty_results(self) -> None:
        """Test that missing API key returns empty results (not error)."""
        with patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False):
            result = await _search_company_news(
                {
                    "company_name": "Acme Corp",
                    "company_domain": "acme.com",
                    "max_results": 5,
                }
            )

            assert "is_error" not in result or result.get("is_error") is False
            assert "data" in result
            assert result["data"]["result_count"] == 0


class TestSearchCompanyFundingTool:
    """Tests for search_company_funding tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _search_company_funding(
            {
                "company_domain": "acme.com",
                "max_results": 5,
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_query_contains_funding_keywords(self) -> None:
        """Test that funding query contains relevant keywords."""
        with patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False):
            result = await _search_company_funding(
                {
                    "company_name": "Acme Corp",
                    "company_domain": "acme.com",
                    "max_results": 5,
                }
            )
            assert "data" in result
            assert "funding" in result["data"]["query"] or "investment" in result["data"]["query"]


class TestSearchCompanyHiringTool:
    """Tests for search_company_hiring tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _search_company_hiring(
            {
                "company_domain": "acme.com",
                "max_results": 5,
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_query_contains_hiring_keywords(self) -> None:
        """Test that hiring query contains relevant keywords."""
        with patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False):
            result = await _search_company_hiring(
                {
                    "company_name": "Acme Corp",
                    "company_domain": "acme.com",
                    "max_results": 5,
                }
            )
            assert "data" in result
            query = result["data"]["query"].lower()
            assert "hiring" in query or "careers" in query or "jobs" in query


class TestSearchCompanyTechTool:
    """Tests for search_company_tech tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _search_company_tech(
            {
                "company_domain": "acme.com",
                "max_results": 5,
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_query_contains_tech_keywords(self) -> None:
        """Test that tech query contains relevant keywords."""
        with patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False):
            result = await _search_company_tech(
                {
                    "company_name": "Acme Corp",
                    "company_domain": "acme.com",
                    "max_results": 5,
                }
            )
            assert "data" in result
            query = result["data"]["query"].lower()
            assert "product" in query or "technology" in query or "launch" in query


class TestExtractAndScoreFactsTool:
    """Tests for extract_and_score_facts tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _extract_and_score_facts(
            {
                "company_domain": "acme.com",
                "search_results": [],
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_missing_search_results_returns_error(self) -> None:
        """Test that missing search_results returns error."""
        result = await _extract_and_score_facts(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_extracts_facts_from_results(self) -> None:
        """Test that facts are extracted from search results."""
        search_results = [
            {
                "title": "Acme Corp Raises $50M",
                "snippet": "Funding round led by top investors",
                "url": "https://example.com/news",
                "date": "2025-01-15",
                "category": "funding",
            },
            {
                "title": "Acme Corp Hires New CTO",
                "snippet": "Exciting new leadership",
                "url": "https://example.com/news2",
                "category": "news",
            },
        ]

        result = await _extract_and_score_facts(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "search_results": search_results,
            }
        )

        assert "is_error" not in result or result.get("is_error") is False
        assert "data" in result
        assert result["data"]["fact_count"] == 2
        assert len(result["data"]["facts"]) == 2

    @pytest.mark.asyncio
    async def test_facts_are_sorted_by_score(self) -> None:
        """Test that facts are sorted by total score descending."""
        search_results = [
            {
                "title": "Old news",
                "snippet": "Not very specific",
                "url": "https://example.com/old",
                "date": "2024-01-01",
                "category": "news",
            },
            {
                "title": "Acme Corp Raises $100M Series D",
                "snippet": "Major milestone reached",
                "url": "https://example.com/funding",
                "date": "2025-01-20",
                "category": "funding",
            },
        ]

        result = await _extract_and_score_facts(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "search_results": search_results,
            }
        )

        facts = result["data"]["facts"]
        # Facts should be sorted by score descending
        assert facts[0]["total_score"] >= facts[1]["total_score"]

    @pytest.mark.asyncio
    async def test_specificity_score_increases_with_numbers(self) -> None:
        """Test that specificity score increases when text contains numbers."""
        search_results = [
            {
                "title": "Acme raised $50 million",
                "snippet": "150% growth year over year",
                "url": "https://example.com",
                "category": "funding",
            },
        ]

        result = await _extract_and_score_facts(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "search_results": search_results,
            }
        )

        facts = result["data"]["facts"]
        # Should have higher specificity due to $50 million and 150%
        assert facts[0]["specificity_score"] > 0.5


class TestAggregateCompanyResearchTool:
    """Tests for aggregate_company_research tool."""

    @pytest.mark.asyncio
    async def test_missing_company_name_returns_error(self) -> None:
        """Test that missing company_name returns error."""
        result = await _aggregate_company_research(
            {
                "company_domain": "acme.com",
                "news_results": {},
                "funding_results": {},
                "hiring_results": {},
                "tech_results": {},
                "extracted_facts": [],
            }
        )
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_aggregates_costs(self) -> None:
        """Test that costs are aggregated from all search results."""
        news_results = {
            "data": {"cost": 0.001, "tool_used": "serper_search", "result_count": 2, "results": []},
        }
        funding_results = {
            "data": {"cost": 0.001, "tool_used": "serper_search", "result_count": 1, "results": []},
        }
        hiring_results = {
            "data": {"cost": 0.001, "tool_used": "serper_search", "result_count": 1, "results": []},
        }
        tech_results = {
            "data": {"cost": 0.001, "tool_used": "serper_search", "result_count": 1, "results": []},
        }

        result = await _aggregate_company_research(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "news_results": news_results,
                "funding_results": funding_results,
                "hiring_results": hiring_results,
                "tech_results": tech_results,
                "extracted_facts": [],
            }
        )

        assert "is_error" not in result or result.get("is_error") is False
        assert result["data"]["total_cost"] == 0.004

    @pytest.mark.asyncio
    async def test_determines_categories_found(self) -> None:
        """Test that categories are correctly determined."""
        news_results = {"data": {"result_count": 5, "results": []}}
        funding_results = {"data": {"result_count": 0, "results": []}}
        hiring_results = {"data": {"result_count": 3, "results": []}}
        tech_results = {"data": {"result_count": 0, "results": []}}

        result = await _aggregate_company_research(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "news_results": news_results,
                "funding_results": funding_results,
                "hiring_results": hiring_results,
                "tech_results": tech_results,
                "extracted_facts": [],
            }
        )

        assert result["data"]["has_recent_news"] is True
        assert result["data"]["has_funding"] is False
        assert result["data"]["has_hiring"] is True
        assert result["data"]["has_product_launch"] is False

    @pytest.mark.asyncio
    async def test_generates_primary_hook_from_best_fact(self) -> None:
        """Test that primary hook is generated from best fact."""
        extracted_facts = [
            {
                "fact_text": "This is the best fact with highest score",
                "total_score": 0.9,
                "category": "funding",
            },
            {
                "fact_text": "This is a lower scored fact",
                "total_score": 0.5,
                "category": "news",
            },
        ]

        result = await _aggregate_company_research(
            {
                "company_name": "Acme Corp",
                "company_domain": "acme.com",
                "news_results": {},
                "funding_results": {},
                "hiring_results": {},
                "tech_results": {},
                "extracted_facts": extracted_facts,
            }
        )

        assert result["data"]["primary_hook"] == "This is the best fact with highest score"
        assert result["data"]["relevance_score"] == 0.9


class TestCompanyResearchToolsList:
    """Tests for COMPANY_RESEARCH_TOOLS list."""

    def test_tools_list_contents(self) -> None:
        """Test that COMPANY_RESEARCH_TOOLS contains expected tools."""
        tool_functions = COMPANY_RESEARCH_TOOLS

        assert len(tool_functions) == 6
        assert search_company_news_tool in tool_functions
        assert search_company_funding_tool in tool_functions
        assert search_company_hiring_tool in tool_functions
        assert search_company_tech_tool in tool_functions
        assert extract_and_score_facts_tool in tool_functions
        assert aggregate_company_research_tool in tool_functions

    def test_tools_have_callable_handlers(self) -> None:
        """Test that all tools have callable handlers."""
        for tool in COMPANY_RESEARCH_TOOLS:
            assert hasattr(tool, "handler")
            assert callable(tool.handler)

    def test_tools_have_required_attributes(self) -> None:
        """Test that all tools have required SdkMcpTool attributes."""
        for tool in COMPANY_RESEARCH_TOOLS:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "input_schema")
            assert hasattr(tool, "handler")
