"""Unit tests for Job Title Matcher."""

import pytest

from src.agents.lead_scoring.job_title_matcher import (
    JobTitleMatcher,
    calculate_similarity,
    expand_with_synonyms,
    extract_seniority_level,
    get_seniority_rank,
    normalize_title,
)


class TestNormalizeTitle:
    """Tests for normalize_title function."""

    def test_lowercase(self) -> None:
        assert normalize_title("VP Marketing") == "vp marketing"

    def test_removes_special_characters(self) -> None:
        result = normalize_title("Director, Marketing")
        assert "," not in result

    def test_handles_empty_string(self) -> None:
        assert normalize_title("") == ""

    def test_handles_none(self) -> None:
        assert normalize_title(None) == ""  # type: ignore

    def test_normalizes_whitespace(self) -> None:
        result = normalize_title("VP   of   Marketing")
        assert "   " not in result


class TestCalculateSimilarity:
    """Tests for calculate_similarity function."""

    def test_exact_match(self) -> None:
        assert calculate_similarity("VP Marketing", "VP Marketing") == 1.0

    def test_case_insensitive_match(self) -> None:
        assert calculate_similarity("VP Marketing", "vp marketing") == 1.0

    def test_similar_titles(self) -> None:
        score = calculate_similarity("VP Marketing", "VP of Marketing")
        assert score >= 0.8

    def test_different_titles(self) -> None:
        score = calculate_similarity("VP Marketing", "Software Engineer")
        assert score < 0.5

    def test_empty_strings(self) -> None:
        assert calculate_similarity("", "VP Marketing") == 0.0
        assert calculate_similarity("VP Marketing", "") == 0.0
        assert calculate_similarity("", "") == 0.0


class TestExtractSeniorityLevel:
    """Tests for extract_seniority_level function."""

    def test_c_suite(self) -> None:
        assert extract_seniority_level("CEO") == "c_suite"
        assert extract_seniority_level("Chief Marketing Officer") == "c_suite"
        assert extract_seniority_level("CFO") == "c_suite"

    def test_vp(self) -> None:
        assert extract_seniority_level("VP Marketing") == "vp"
        assert extract_seniority_level("Vice President of Sales") == "vp"
        assert extract_seniority_level("SVP Engineering") == "vp"

    def test_director(self) -> None:
        assert extract_seniority_level("Director of Marketing") == "director"
        assert extract_seniority_level("Marketing Director") == "director"
        assert extract_seniority_level("Head of Sales") == "director"

    def test_senior_manager(self) -> None:
        assert extract_seniority_level("Senior Manager, Marketing") == "senior_manager"

    def test_manager(self) -> None:
        assert extract_seniority_level("Marketing Manager") == "manager"

    def test_senior(self) -> None:
        assert extract_seniority_level("Senior Marketing Specialist") == "senior"
        assert extract_seniority_level("Lead Engineer") == "senior"

    def test_ic(self) -> None:
        assert extract_seniority_level("Marketing Analyst") == "ic"
        assert extract_seniority_level("Software Engineer") == "ic"

    def test_empty(self) -> None:
        assert extract_seniority_level("") == "ic"
        assert extract_seniority_level(None) == "ic"  # type: ignore


class TestGetSeniorityRank:
    """Tests for get_seniority_rank function."""

    def test_c_suite_highest(self) -> None:
        assert get_seniority_rank("c_suite") == 6

    def test_vp(self) -> None:
        assert get_seniority_rank("vp") == 5

    def test_director(self) -> None:
        assert get_seniority_rank("director") == 4

    def test_manager(self) -> None:
        assert get_seniority_rank("manager") == 2

    def test_ic_lowest(self) -> None:
        assert get_seniority_rank("ic") == 0

    def test_unknown(self) -> None:
        assert get_seniority_rank("unknown") == 0


class TestExpandWithSynonyms:
    """Tests for expand_with_synonyms function."""

    def test_expands_vp_marketing(self) -> None:
        result = expand_with_synonyms("VP Marketing")
        assert "VP Marketing" in result
        assert "Vice President Marketing" in result

    def test_finds_synonym_variant(self) -> None:
        result = expand_with_synonyms("Vice President Marketing")
        assert "VP Marketing" in result

    def test_unknown_title(self) -> None:
        result = expand_with_synonyms("Software Engineer")
        assert result == ["Software Engineer"]


class TestJobTitleMatcher:
    """Tests for JobTitleMatcher class."""

    @pytest.fixture
    def matcher(self) -> JobTitleMatcher:
        return JobTitleMatcher(threshold=0.80)

    @pytest.fixture
    def target_titles(self) -> list[str]:
        return [
            "VP Marketing",
            "Marketing Director",
            "Head of Growth",
            "CMO",
        ]

    @pytest.fixture
    def personas(self) -> list[dict]:
        return [
            {
                "name": "Marketing Leader",
                "job_titles": ["VP Marketing", "Marketing Director", "CMO"],
            },
            {
                "name": "Growth Leader",
                "job_titles": ["Head of Growth", "VP Growth", "Growth Director"],
            },
        ]

    def test_exact_match(self, matcher: JobTitleMatcher, target_titles: list[str]) -> None:
        result = matcher.match("VP Marketing", target_titles)
        assert result.matched is True
        assert result.score == 1.0
        assert result.matched_title == "VP Marketing"

    def test_similar_match(self, matcher: JobTitleMatcher, target_titles: list[str]) -> None:
        result = matcher.match("Vice President Marketing", target_titles)
        assert result.matched is True
        assert result.score >= 0.8
        assert result.matched_title is not None

    def test_no_match(self, matcher: JobTitleMatcher, target_titles: list[str]) -> None:
        result = matcher.match("Software Engineer", target_titles)
        assert result.matched is False
        assert result.score < 0.8

    def test_empty_title(self, matcher: JobTitleMatcher, target_titles: list[str]) -> None:
        result = matcher.match("", target_titles)
        assert result.matched is False
        assert result.score == 0.0

    def test_match_with_personas(
        self,
        matcher: JobTitleMatcher,
        target_titles: list[str],
        personas: list[dict],
    ) -> None:
        result = matcher.match("CMO", target_titles, personas)
        assert result.matched is True
        assert result.matched_persona == "Marketing Leader"

    def test_seniority_extraction(self, matcher: JobTitleMatcher, target_titles: list[str]) -> None:
        result = matcher.match("VP Marketing", target_titles)
        assert result.seniority_level == "vp"

        result = matcher.match("Marketing Director", target_titles)
        assert result.seniority_level == "director"

    def test_match_seniority_exact(self, matcher: JobTitleMatcher) -> None:
        score, matched = matcher.match_seniority("vp", ["vp", "director"])
        assert score == 20
        assert matched == "vp"

    def test_match_seniority_one_level_off(self, matcher: JobTitleMatcher) -> None:
        score, matched = matcher.match_seniority("vp", ["director"])
        assert score == 15  # One level off

    def test_match_seniority_two_levels_off(self, matcher: JobTitleMatcher) -> None:
        score, matched = matcher.match_seniority("vp", ["senior_manager"])
        assert score == 10  # Two levels off

    def test_match_seniority_no_lead_seniority(self, matcher: JobTitleMatcher) -> None:
        score, matched = matcher.match_seniority(None, ["director", "vp"])
        assert score == 5  # Partial points for unknown
