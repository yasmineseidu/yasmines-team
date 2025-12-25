"""
Unit tests for Data Validation Agent normalizers.

Tests all field normalization functions including:
- Name normalization (title case, special patterns)
- Job title normalization (abbreviation expansion)
- Company name normalization (legal suffix removal)
- Location parsing
"""

from src.agents.data_validation.normalizers import (
    derive_domain_from_company_name,
    derive_full_name,
    detect_seniority,
    normalize_company_name,
    normalize_job_title,
    normalize_lead,
    normalize_name,
    parse_location,
)


class TestNameNormalization:
    """Tests for normalize_name()."""

    def test_basic_normalization(self) -> None:
        """Test basic name normalization."""
        assert normalize_name("john") == "John"
        assert normalize_name("JANE") == "Jane"
        assert normalize_name("  john  ") == "John"

    def test_title_case(self) -> None:
        """Test title case conversion."""
        assert normalize_name("john doe") == "John Doe"
        assert normalize_name("JANE SMITH") == "Jane Smith"

    def test_hyphenated_names(self) -> None:
        """Test hyphenated name handling."""
        assert normalize_name("mary-jane") == "Mary-Jane"
        assert normalize_name("JEAN-PIERRE") == "Jean-Pierre"

    def test_apostrophe_names(self) -> None:
        """Test names with apostrophes."""
        assert normalize_name("o'brien") == "O'Brien"
        assert normalize_name("d'angelo") == "D'Angelo"

    def test_mc_mac_names(self) -> None:
        """Test Mc/Mac prefix handling."""
        assert normalize_name("mcdonald") == "McDonald"
        assert normalize_name("MACGREGOR") == "MacGregor"

    def test_lowercase_particles(self) -> None:
        """Test lowercase particles (van, de, etc.)."""
        assert normalize_name("ludwig van beethoven") == "Ludwig van Beethoven"
        assert normalize_name("LEONARDO DA VINCI") == "Leonardo da Vinci"

    def test_empty_name(self) -> None:
        """Test empty name handling."""
        assert normalize_name(None) is None
        assert normalize_name("") is None
        assert normalize_name("   ") is None

    def test_multiple_spaces(self) -> None:
        """Test collapsing multiple spaces."""
        assert normalize_name("john    doe") == "John Doe"


class TestDeriveFullName:
    """Tests for derive_full_name()."""

    def test_derive_from_parts(self) -> None:
        """Test deriving full name from first and last."""
        assert derive_full_name("John", "Doe") == "John Doe"
        assert derive_full_name("  jane  ", "  smith  ") == "Jane Smith"

    def test_missing_parts(self) -> None:
        """Test handling missing name parts."""
        assert derive_full_name(None, None) is None
        assert derive_full_name("John", None) == "John"
        assert derive_full_name(None, "Doe") == "Doe"


class TestJobTitleNormalization:
    """Tests for normalize_job_title()."""

    def test_abbreviation_expansion(self) -> None:
        """Test job title abbreviation expansion."""
        assert normalize_job_title("VP of Sales") == "Vice President of Sales"
        assert normalize_job_title("SVP Engineering") == "Senior Vice President Engineering"
        assert normalize_job_title("Dir of Marketing") == "Director of Marketing"
        assert normalize_job_title("Sr Mgr") == "Senior Manager"

    def test_c_suite_expansion(self) -> None:
        """Test C-suite title expansion."""
        assert normalize_job_title("CEO") == "Chief Executive Officer"
        assert normalize_job_title("CFO") == "Chief Financial Officer"
        assert normalize_job_title("CTO") == "Chief Technology Officer"

    def test_no_expansion_needed(self) -> None:
        """Test titles that don't need expansion."""
        assert normalize_job_title("Software Engineer") == "Software Engineer"
        assert normalize_job_title("Product Manager") == "Product Manager"

    def test_empty_title(self) -> None:
        """Test empty title handling."""
        assert normalize_job_title(None) is None
        assert normalize_job_title("") is None

    def test_mixed_case(self) -> None:
        """Test that abbreviations are case-insensitive."""
        assert normalize_job_title("vp of sales") == "Vice President of sales"
        assert normalize_job_title("ceo") == "Chief Executive Officer"


class TestDetectSeniority:
    """Tests for detect_seniority()."""

    def test_c_suite_detection(self) -> None:
        """Test C-suite seniority detection."""
        assert detect_seniority("Chief Executive Officer") == "c_suite"
        assert detect_seniority("CEO") == "c_suite"

    def test_vp_detection(self) -> None:
        """Test VP seniority detection."""
        assert detect_seniority("Vice President of Sales") == "vp"
        assert detect_seniority("SVP Engineering") == "vp"

    def test_director_detection(self) -> None:
        """Test Director seniority detection."""
        assert detect_seniority("Director of Marketing") == "director"
        assert detect_seniority("Head of Product") == "director"

    def test_manager_detection(self) -> None:
        """Test Manager seniority detection."""
        assert detect_seniority("Product Manager") == "manager"
        assert detect_seniority("Engineering Lead") == "manager"

    def test_senior_detection(self) -> None:
        """Test Senior seniority detection."""
        assert detect_seniority("Senior Software Engineer") == "senior"
        assert detect_seniority("Principal Architect") == "senior"

    def test_no_seniority(self) -> None:
        """Test titles with no clear seniority."""
        assert detect_seniority("Software Engineer") is None
        assert detect_seniority(None) is None


class TestCompanyNameNormalization:
    """Tests for normalize_company_name()."""

    def test_legal_suffix_removal(self) -> None:
        """Test removal of legal suffixes."""
        assert normalize_company_name("Acme Inc.") == "Acme"
        assert normalize_company_name("Tech Solutions, LLC") == "Tech Solutions"
        assert normalize_company_name("Global Corp.") == "Global"
        assert normalize_company_name("Startup Ltd.") == "Startup"

    def test_no_suffix(self) -> None:
        """Test company names without suffixes."""
        assert normalize_company_name("Microsoft") == "Microsoft"
        assert normalize_company_name("Google") == "Google"

    def test_whitespace_handling(self) -> None:
        """Test whitespace handling."""
        assert normalize_company_name("  Acme Corp  ") == "Acme"
        assert normalize_company_name("  Tech  Solutions  ") == "Tech Solutions"

    def test_empty_name(self) -> None:
        """Test empty name handling."""
        assert normalize_company_name(None) is None
        assert normalize_company_name("") is None

    def test_only_one_suffix_removed(self) -> None:
        """Test that only one suffix is removed."""
        # Edge case: company named "Inc Ltd" should keep "Inc"
        result = normalize_company_name("Inc Ltd")
        assert result == "Inc"


class TestDomainFromCompanyName:
    """Tests for derive_domain_from_company_name()."""

    def test_simple_derivation(self) -> None:
        """Test simple domain derivation."""
        assert derive_domain_from_company_name("Acme") == "acme.com"
        assert derive_domain_from_company_name("Microsoft") == "microsoft.com"

    def test_spaces_removed(self) -> None:
        """Test that spaces are removed."""
        assert derive_domain_from_company_name("Tech Solutions") == "techsolutions.com"

    def test_special_chars_removed(self) -> None:
        """Test that special characters are removed.

        Note: Company name is normalized first (removing legal suffixes),
        so "Acme Corp." becomes "Acme" -> "acme.com"
        """
        # Corp. is a legal suffix, so it gets removed during normalization
        assert derive_domain_from_company_name("Acme Corp.") == "acme.com"
        # Test actual special char removal with a name that won't be normalized
        # "&" is removed as a special character
        assert derive_domain_from_company_name("My&Company") == "mycompany.com"

    def test_empty_name(self) -> None:
        """Test empty name handling."""
        assert derive_domain_from_company_name(None) is None
        assert derive_domain_from_company_name("") is None


class TestLocationParsing:
    """Tests for parse_location()."""

    def test_full_location(self) -> None:
        """Test parsing full location (city, state, country)."""
        result = parse_location("San Francisco, CA, USA")
        assert result["city"] == "San Francisco"
        assert result["state"] == "CA"
        assert result["country"] == "USA"

    def test_city_state(self) -> None:
        """Test parsing city and state."""
        result = parse_location("New York, NY")
        assert result["city"] == "New York"
        assert result["state"] == "NY"
        assert result["country"] == "United States"

    def test_city_country(self) -> None:
        """Test parsing city and country."""
        result = parse_location("London, United Kingdom")
        assert result["city"] == "London"
        assert result["country"] == "United Kingdom"

    def test_city_only(self) -> None:
        """Test parsing city only."""
        result = parse_location("Tokyo")
        assert result["city"] == "Tokyo"
        assert result["state"] is None
        assert result["country"] is None

    def test_empty_location(self) -> None:
        """Test empty location handling."""
        result = parse_location(None)
        assert result["city"] is None
        assert result["state"] is None
        assert result["country"] is None


class TestNormalizeLead:
    """Tests for normalize_lead() composite function."""

    def test_full_normalization(self) -> None:
        """Test normalizing a complete lead."""
        lead = {
            "id": "test-123",
            "campaign_id": "campaign-456",
            "first_name": "  john  ",
            "last_name": "DOE",
            "job_title": "VP of Sales",
            "company_name": "Acme Inc.",
            "linkedin_url": "https://linkedin.com/in/johndoe/",
            "email": "JOHN@ACME.COM",
            "location": "San Francisco, CA, USA",
        }

        result = normalize_lead(lead)

        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["full_name"] == "John Doe"
        assert result["job_title"] == "Vice President of Sales"
        assert result["company_name"] == "Acme"
        assert result["linkedin_url"] == "https://linkedin.com/in/johndoe"
        assert result["email"] == "john@acme.com"
        assert result["city"] == "San Francisco"
        assert result["state"] == "CA"
        assert result["country"] == "USA"

    def test_seniority_detection(self) -> None:
        """Test that seniority is detected."""
        lead = {
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "CEO",
            "company_name": "Acme",
            "linkedin_url": "https://linkedin.com/in/johndoe",
        }

        result = normalize_lead(lead)
        assert result["seniority"] == "c_suite"

    def test_domain_derivation(self) -> None:
        """Test domain derivation when not provided."""
        lead = {
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "Engineer",
            "company_name": "Acme",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "company_linkedin_url": "https://linkedin.com/company/acme-corp",
        }

        result = normalize_lead(lead)
        # Domain derived from company LinkedIn URL
        assert result["company_domain"] == "acme-corp.com"

    def test_title_field_compatibility(self) -> None:
        """Test handling 'title' field (DB column name)."""
        lead = {
            "first_name": "John",
            "last_name": "Doe",
            "title": "Software Engineer",  # DB uses 'title'
            "company_name": "Acme",
            "linkedin_url": "https://linkedin.com/in/johndoe",
        }

        result = normalize_lead(lead)
        assert result["job_title"] == "Software Engineer"
        assert result["title"] == "Software Engineer"

    def test_passthrough_fields(self) -> None:
        """Test that passthrough fields are preserved."""
        lead = {
            "id": "test-123",
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "Engineer",
            "company_name": "Acme",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "company_size": "51-200",
            "company_industry": "Technology",
            "phone": "+1-555-1234",
            "source": "linkedin",
        }

        result = normalize_lead(lead)
        assert result["company_size"] == "51-200"
        assert result["company_industry"] == "Technology"
        assert result["phone"] == "+1-555-1234"
        assert result["source"] == "linkedin"
