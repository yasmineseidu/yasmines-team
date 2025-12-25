"""Unit tests for Cross-Campaign Dedup Agent."""

import pytest

from src.agents.cross_campaign_dedup import (
    CrossCampaignDedupAgent,
    CrossCampaignDedupError,
    CrossCampaignDedupResult,
    ExclusionResult,
    cross_campaign_dedup,
    fuzzy_match_score,
    name_company_match,
    normalize_string,
)

# Note: SDK MCP tools (check_linkedin_url_history_tool, etc.) are not directly
# callable as the @tool decorator returns SdkMcpTool objects. The core dedup
# logic is tested through the agent's run() method which calls _process_leads_directly().

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_leads() -> list[dict]:
    """Sample leads for testing."""
    return [
        {
            "id": "lead-001",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "company_name": "Acme Corp",
        },
        {
            "id": "lead-002",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@test.com",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "company_name": "Tech Inc",
        },
        {
            "id": "lead-003",
            "first_name": "Bob",
            "last_name": "Wilson",
            "email": "bob@widgets.com",
            "linkedin_url": "https://linkedin.com/in/bobwilson",
            "company_name": "Widgets LLC",
        },
        {
            "id": "lead-004",
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@startup.io",
            "linkedin_url": None,
            "company_name": "Startup.io",
        },
    ]


@pytest.fixture
def historical_data() -> list[dict]:
    """Historical leads from other campaigns."""
    return [
        {
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Corp",
            "campaign_id": "campaign-old-001",
            "email_status": None,
            "last_contacted_at": "2024-01-15T10:00:00Z",
        },
        {
            "linkedin_url": "https://linkedin.com/in/bounced-user",
            "email": "bounced@company.com",
            "first_name": "Bounced",
            "last_name": "User",
            "company_name": "Old Company",
            "campaign_id": "campaign-old-002",
            "email_status": "bounced",
            "last_contacted_at": "2024-02-01T10:00:00Z",
        },
        {
            "linkedin_url": "https://linkedin.com/in/unsubscribed",
            "email": "unsub@company.com",
            "first_name": "Unsub",
            "last_name": "Person",
            "company_name": "Some Company",
            "campaign_id": "campaign-old-003",
            "email_status": "unsubscribed",
            "last_contacted_at": "2024-02-10T10:00:00Z",
        },
    ]


@pytest.fixture
def suppression_list() -> list[str]:
    """Global suppression list."""
    return [
        "alice@startup.io",  # Matches lead-004
        "noreply@example.com",
        "donotcontact@company.com",
    ]


@pytest.fixture
def agent() -> CrossCampaignDedupAgent:
    """Create agent instance for testing."""
    return CrossCampaignDedupAgent(
        lookback_days=90,
        fuzzy_threshold=0.85,
    )


# =============================================================================
# Test Utility Functions
# =============================================================================


class TestNormalizeString:
    """Tests for normalize_string function."""

    def test_normalizes_to_lowercase(self) -> None:
        assert normalize_string("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self) -> None:
        assert normalize_string("  hello  ") == "hello"

    def test_collapses_multiple_spaces(self) -> None:
        assert normalize_string("hello   world") == "hello world"

    def test_handles_none(self) -> None:
        assert normalize_string(None) == ""

    def test_handles_empty_string(self) -> None:
        assert normalize_string("") == ""


class TestFuzzyMatchScore:
    """Tests for fuzzy_match_score function."""

    def test_identical_strings_score_1(self) -> None:
        score = fuzzy_match_score("John Doe", "John Doe")
        assert score == 1.0

    def test_similar_strings_high_score(self) -> None:
        score = fuzzy_match_score("John Doe", "John D.")
        assert score > 0.7

    def test_different_strings_low_score(self) -> None:
        score = fuzzy_match_score("John Doe", "Alice Smith")
        assert score < 0.5

    def test_case_insensitive(self) -> None:
        score = fuzzy_match_score("JOHN DOE", "john doe")
        assert score == 1.0

    def test_handles_none_first(self) -> None:
        assert fuzzy_match_score(None, "John") == 0.0

    def test_handles_none_second(self) -> None:
        assert fuzzy_match_score("John", None) == 0.0

    def test_handles_both_none(self) -> None:
        assert fuzzy_match_score(None, None) == 0.0

    def test_handles_empty_strings(self) -> None:
        assert fuzzy_match_score("", "") == 0.0


class TestNameCompanyMatch:
    """Tests for name_company_match function."""

    def test_exact_match_returns_true(self) -> None:
        is_match, score = name_company_match(
            "John",
            "Doe",
            "Acme Corp",
            "John",
            "Doe",
            "Acme Corp",
            threshold=0.85,
        )
        assert is_match is True
        assert score == 1.0

    def test_similar_name_same_company_matches(self) -> None:
        is_match, score = name_company_match(
            "John",
            "Doe",
            "Acme Corp",
            "Johnny",
            "Doe",
            "Acme Corp",
            threshold=0.85,
        )
        # Similar name, same company should match
        assert score > 0.80

    def test_different_name_different_company_no_match(self) -> None:
        is_match, score = name_company_match(
            "John",
            "Doe",
            "Acme Corp",
            "Alice",
            "Smith",
            "Tech Inc",
            threshold=0.85,
        )
        assert is_match is False
        assert score < 0.5

    def test_threshold_respected(self) -> None:
        # With high threshold, slight differences fail
        is_match, _ = name_company_match(
            "John",
            "Doe",
            "Acme Corp",
            "John",
            "Dough",
            "Acme Corporation",
            threshold=0.95,
        )
        assert is_match is False

        # With lower threshold, same comparison passes
        is_match, _ = name_company_match(
            "John",
            "Doe",
            "Acme Corp",
            "John",
            "Dough",
            "Acme Corporation",
            threshold=0.70,
        )
        assert is_match is True

    def test_missing_first_name(self) -> None:
        is_match, score = name_company_match(
            None,
            "Doe",
            "Acme Corp",
            "John",
            "Doe",
            "Acme Corp",
            threshold=0.85,
        )
        # Should still attempt match with available data
        assert isinstance(score, float)


# =============================================================================
# Test Agent Initialization
# =============================================================================


class TestCrossCampaignDedupAgentInit:
    """Tests for agent initialization."""

    def test_default_initialization(self) -> None:
        agent = CrossCampaignDedupAgent()
        assert agent.name == "cross_campaign_dedup"
        assert agent.lookback_days == 90
        assert agent.fuzzy_threshold == 0.85

    def test_custom_lookback_days(self) -> None:
        agent = CrossCampaignDedupAgent(lookback_days=30)
        assert agent.lookback_days == 30

    def test_custom_fuzzy_threshold(self) -> None:
        agent = CrossCampaignDedupAgent(fuzzy_threshold=0.90)
        assert agent.fuzzy_threshold == 0.90

    def test_system_prompt_contains_lookback(self) -> None:
        agent = CrossCampaignDedupAgent(lookback_days=60)
        assert "60" in agent.system_prompt

    def test_system_prompt_contains_threshold(self) -> None:
        agent = CrossCampaignDedupAgent(fuzzy_threshold=0.90)
        assert "90%" in agent.system_prompt


# =============================================================================
# Test Agent Run - Exclusion Scenarios
# =============================================================================


class TestCrossCampaignDedupAgentRun:
    """Tests for agent run method."""

    @pytest.mark.asyncio
    async def test_empty_leads_returns_completed(self, agent: CrossCampaignDedupAgent) -> None:
        result = await agent.run(
            campaign_id="test-campaign",
            leads=[],
            historical_data=[],
            suppression_list=[],
        )

        assert result.success is True
        assert result.status == "completed"
        assert result.total_checked == 0
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_no_exclusions_when_no_matches(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "new-lead-001",
                "first_name": "New",
                "last_name": "Person",
                "email": "new@fresh.com",
                "linkedin_url": "https://linkedin.com/in/newperson",
                "company_name": "Fresh Company",
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=[],
            suppression_list=[],
        )

        assert result.success is True
        assert result.total_checked == 1
        assert result.remaining_leads == 1
        assert len(result.exclusions) == 0
        assert "new-lead-001" in result.passed_lead_ids

    @pytest.mark.asyncio
    async def test_excludes_suppression_list_email(
        self,
        agent: CrossCampaignDedupAgent,
        sample_leads: list[dict],
        suppression_list: list[str],
    ) -> None:
        result = await agent.run(
            campaign_id="test-campaign",
            leads=sample_leads,
            historical_data=[],
            suppression_list=suppression_list,
        )

        assert result.success is True
        assert result.suppression_list_excluded == 1

        # Find the exclusion for lead-004 (alice@startup.io)
        suppression_exclusion = next(
            (e for e in result.exclusions if e.lead_id == "lead-004"), None
        )
        assert suppression_exclusion is not None
        assert suppression_exclusion.exclusion_reason == "suppression_list"
        assert "lead-004" not in result.passed_lead_ids

    @pytest.mark.asyncio
    async def test_excludes_linkedin_url_match(
        self,
        agent: CrossCampaignDedupAgent,
        sample_leads: list[dict],
        historical_data: list[dict],
    ) -> None:
        result = await agent.run(
            campaign_id="test-campaign",
            leads=sample_leads,
            historical_data=historical_data,
            suppression_list=[],
        )

        assert result.success is True
        assert result.previously_contacted >= 1

        # lead-001 has LinkedIn URL that matches historical
        linkedin_exclusion = next((e for e in result.exclusions if e.lead_id == "lead-001"), None)
        assert linkedin_exclusion is not None
        assert linkedin_exclusion.exclusion_reason == "previously_contacted"
        assert linkedin_exclusion.excluded_due_to_campaign == "campaign-old-001"

    @pytest.mark.asyncio
    async def test_excludes_email_match(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "email-match-lead",
                "first_name": "Different",
                "last_name": "Name",
                "email": "john.doe@example.com",  # Same email as historical
                "linkedin_url": "https://linkedin.com/in/differentperson",
                "company_name": "Different Company",
            }
        ]

        historical = [
            {
                "linkedin_url": "https://linkedin.com/in/original",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Original Co",
                "campaign_id": "old-campaign",
                "email_status": None,
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.previously_contacted == 1
        exclusion = result.exclusions[0]
        assert exclusion.exclusion_reason == "previously_contacted"

    @pytest.mark.asyncio
    async def test_excludes_bounced_email(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "bounced-lead",
                "first_name": "Bounced",
                "last_name": "User",
                "email": "bounced@company.com",
                "linkedin_url": None,
                "company_name": "Some Co",
            }
        ]

        historical = [
            {
                "linkedin_url": None,
                "email": "bounced@company.com",
                "first_name": "Bounced",
                "last_name": "User",
                "company_name": "Old Company",
                "campaign_id": "old-campaign",
                "email_status": "bounced",
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.bounced_excluded == 1
        exclusion = result.exclusions[0]
        assert exclusion.exclusion_reason == "bounced"

    @pytest.mark.asyncio
    async def test_excludes_unsubscribed_email(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "unsub-lead",
                "first_name": "Unsub",
                "last_name": "Person",
                "email": "unsub@company.com",
                "linkedin_url": None,
                "company_name": "Test Co",
            }
        ]

        historical = [
            {
                "linkedin_url": None,
                "email": "unsub@company.com",
                "first_name": "Unsub",
                "last_name": "Person",
                "company_name": "Some Company",
                "campaign_id": "old-campaign",
                "email_status": "unsubscribed",
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.unsubscribed_excluded == 1
        exclusion = result.exclusions[0]
        assert exclusion.exclusion_reason == "unsubscribed"

    @pytest.mark.asyncio
    async def test_excludes_fuzzy_name_company_match(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "fuzzy-lead",
                "first_name": "Jonathan",  # Similar to John
                "last_name": "Doe",
                "email": "different@email.com",
                "linkedin_url": "https://linkedin.com/in/different",
                "company_name": "Acme Corporation",  # Similar to Acme Corp
            }
        ]

        historical = [
            {
                "linkedin_url": "https://linkedin.com/in/original",
                "email": "john@acme.com",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "campaign_id": "old-campaign",
                "email_status": None,
            }
        ]

        # Use a lower threshold to ensure fuzzy match triggers
        agent_low_threshold = CrossCampaignDedupAgent(fuzzy_threshold=0.75)
        result = await agent_low_threshold.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.fuzzy_match_excluded == 1
        exclusion = result.exclusions[0]
        assert exclusion.exclusion_reason == "fuzzy_match"
        assert exclusion.match_confidence > 0.75


# =============================================================================
# Test Exclusion Priority
# =============================================================================


class TestExclusionPriority:
    """Tests for exclusion priority ordering."""

    @pytest.mark.asyncio
    async def test_suppression_takes_priority_over_linkedin(self) -> None:
        """Suppression list should be checked before LinkedIn match."""
        leads = [
            {
                "id": "priority-lead",
                "first_name": "John",
                "last_name": "Doe",
                "email": "suppressed@example.com",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "company_name": "Acme Corp",
            }
        ]

        historical = [
            {
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "email": "john@acme.com",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "campaign_id": "old-campaign",
                "email_status": None,
            }
        ]

        suppression = ["suppressed@example.com"]

        agent = CrossCampaignDedupAgent()
        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=suppression,
        )

        # Should be excluded as suppression (checked first)
        assert result.suppression_list_excluded == 1
        assert result.previously_contacted == 0
        exclusion = result.exclusions[0]
        assert exclusion.exclusion_reason == "suppression_list"

    @pytest.mark.asyncio
    async def test_linkedin_takes_priority_over_fuzzy(self) -> None:
        """LinkedIn match should be used before falling back to fuzzy."""
        leads = [
            {
                "id": "priority-lead",
                "first_name": "John",
                "last_name": "Doe",
                "email": "new@example.com",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "company_name": "Acme Corp",
            }
        ]

        historical = [
            {
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "email": "different@acme.com",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp",
                "campaign_id": "old-campaign",
                "email_status": None,
            }
        ]

        agent = CrossCampaignDedupAgent()
        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        # Should be excluded as previously_contacted (LinkedIn match)
        assert result.previously_contacted == 1
        assert result.fuzzy_match_excluded == 0
        exclusion = result.exclusions[0]
        assert exclusion.matched_identifier == "https://linkedin.com/in/johndoe"


# =============================================================================
# Test Result Object
# =============================================================================


class TestCrossCampaignDedupResult:
    """Tests for CrossCampaignDedupResult dataclass."""

    def test_default_values(self) -> None:
        result = CrossCampaignDedupResult()
        assert result.success is True
        assert result.status == "completed"
        assert result.total_checked == 0
        assert result.remaining_leads == 0
        assert result.lookback_days == 90
        assert result.fuzzy_threshold == 0.85

    def test_to_dict(self) -> None:
        result = CrossCampaignDedupResult(
            total_checked=100,
            previously_contacted=10,
            bounced_excluded=5,
            remaining_leads=85,
        )
        result.exclusions.append(
            ExclusionResult(
                lead_id="test-lead",
                exclusion_reason="previously_contacted",
                excluded_due_to_campaign="old-campaign",
            )
        )

        d = result.to_dict()
        assert d["total_checked"] == 100
        assert d["previously_contacted"] == 10
        assert d["bounced_excluded"] == 5
        assert d["remaining_leads"] == 85
        assert len(d["exclusions"]) == 1
        assert d["exclusions"][0]["lead_id"] == "test-lead"


class TestExclusionResult:
    """Tests for ExclusionResult dataclass."""

    def test_required_fields(self) -> None:
        result = ExclusionResult(
            lead_id="lead-001",
            exclusion_reason="bounced",
        )
        assert result.lead_id == "lead-001"
        assert result.exclusion_reason == "bounced"
        assert result.excluded_due_to_campaign is None
        assert result.match_confidence == 1.0

    def test_all_fields(self) -> None:
        result = ExclusionResult(
            lead_id="lead-001",
            exclusion_reason="fuzzy_match",
            excluded_due_to_campaign="old-campaign",
            matched_identifier="John Doe @ Acme",
            match_confidence=0.92,
        )
        assert result.match_confidence == 0.92
        assert result.matched_identifier == "John Doe @ Acme"


# =============================================================================
# Test Convenience Function
# =============================================================================


class TestConvenienceFunction:
    """Tests for cross_campaign_dedup convenience function."""

    @pytest.mark.asyncio
    async def test_convenience_function_works(self) -> None:
        leads = [
            {
                "id": "lead-001",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "linkedin_url": None,
                "company_name": "Test Co",
            }
        ]

        result = await cross_campaign_dedup(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=[],
            suppression_list=[],
            lookback_days=30,
            fuzzy_threshold=0.80,
        )

        assert result.success is True
        assert result.total_checked == 1
        assert result.remaining_leads == 1
        assert result.lookback_days == 30
        assert result.fuzzy_threshold == 0.80


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_cross_campaign_dedup_error(self) -> None:
        error = CrossCampaignDedupError("Test error", {"key": "value"})
        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    @pytest.mark.asyncio
    async def test_agent_handles_exception_gracefully(self, agent: CrossCampaignDedupAgent) -> None:
        # Leads with invalid data shouldn't crash the agent
        leads = [
            {
                "id": "invalid-lead",
                # Missing most fields
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=[],
            suppression_list=[],
        )

        # Should still complete, just not match anything
        assert result.success is True
        assert result.remaining_leads == 1


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_case_insensitive_email_matching(self, agent: CrossCampaignDedupAgent) -> None:
        leads = [
            {
                "id": "lead-001",
                "first_name": "Test",
                "last_name": "User",
                "email": "TEST@EXAMPLE.COM",
                "linkedin_url": None,
                "company_name": "Test Co",
            }
        ]

        suppression = ["test@example.com"]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=[],
            suppression_list=suppression,
        )

        assert result.suppression_list_excluded == 1

    @pytest.mark.asyncio
    async def test_linkedin_url_trailing_slash_normalized(
        self, agent: CrossCampaignDedupAgent
    ) -> None:
        leads = [
            {
                "id": "lead-001",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "linkedin_url": "https://linkedin.com/in/testuser/",  # With slash
                "company_name": "Test Co",
            }
        ]

        historical = [
            {
                "linkedin_url": "https://linkedin.com/in/testuser",  # Without slash
                "email": "different@email.com",
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Co",
                "campaign_id": "old-campaign",
                "email_status": None,
            }
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.previously_contacted == 1

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, agent: CrossCampaignDedupAgent) -> None:
        """Test processing a large batch of leads."""
        # Use unique first names that won't fuzzy match
        # "Alpha0" vs "Bravo100" are completely different
        first_names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]

        # Create 500 leads with distinct names
        leads = [
            {
                "id": f"lead-{i:04d}",
                "first_name": f"{first_names[i % 5]}{i}",  # Alpha0, Bravo1, etc.
                "last_name": "Smith",
                "email": f"user{i}@example.com",
                "linkedin_url": f"https://linkedin.com/in/user{i}",
                "company_name": f"UniqueCompany{i}",  # Each lead has unique company
            }
            for i in range(500)
        ]

        # Create historical matches for first 100 (by LinkedIn URL)
        historical = [
            {
                "linkedin_url": f"https://linkedin.com/in/user{i}",
                "email": f"historical{i}@different.com",  # Different email
                "first_name": f"Different{i}",  # Different name
                "last_name": "Person",
                "company_name": f"DifferentCompany{i}",  # Different company
                "campaign_id": "old-campaign",
                "email_status": None,
            }
            for i in range(0, 100)  # First 100 LinkedIn URLs match
        ]

        result = await agent.run(
            campaign_id="test-campaign",
            leads=leads,
            historical_data=historical,
            suppression_list=[],
        )

        assert result.success is True
        assert result.total_checked == 500
        assert result.previously_contacted == 100
        assert result.remaining_leads == 400
        assert result.fuzzy_match_excluded == 0  # No fuzzy matches expected
