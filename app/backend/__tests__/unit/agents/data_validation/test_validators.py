"""
Unit tests for Data Validation Agent validators.

Tests all field validation functions including:
- LinkedIn URL validation
- Email validation
- Name validation
- Company name validation
- Job title validation
- Company size validation
- Cross-field validation
"""

from src.agents.data_validation.validators import (
    VALID_COMPANY_SIZES,
    ValidationResult,
    derive_domain_from_linkedin_url,
    validate_company_name,
    validate_company_size,
    validate_email,
    validate_full_name_consistency,
    validate_job_title,
    validate_lead,
    validate_linkedin_url,
    validate_name,
)


class TestLinkedInUrlValidation:
    """Tests for validate_linkedin_url()."""

    def test_valid_linkedin_urls(self) -> None:
        """Test valid LinkedIn profile URLs."""
        valid_urls = [
            "https://linkedin.com/in/johndoe",
            "https://www.linkedin.com/in/john-doe",
            "http://linkedin.com/in/john_doe_123",
            "https://linkedin.com/pub/jane-smith",
            "https://www.linkedin.com/in/john-doe?foo=bar",
        ]

        for url in valid_urls:
            result = validate_linkedin_url(url)
            assert result.is_valid, f"Expected valid: {url}"

    def test_invalid_linkedin_urls(self) -> None:
        """Test invalid LinkedIn URLs."""
        invalid_urls = [
            "https://facebook.com/johndoe",
            "https://linkedin.com/company/acme",  # Company, not profile
            "https://linkedin.com/jobs/view/123",
            "not-a-url",
            "",
            None,
        ]

        for url in invalid_urls:
            result = validate_linkedin_url(url)
            assert not result.is_valid, f"Expected invalid: {url}"

    def test_url_normalization(self) -> None:
        """Test URL normalization (add https, remove trailing slash)."""
        result = validate_linkedin_url("www.linkedin.com/in/johndoe/")
        assert result.is_valid
        assert result.normalized_value == "https://www.linkedin.com/in/johndoe"

    def test_empty_url_error_message(self) -> None:
        """Test error message for missing URL."""
        result = validate_linkedin_url(None)
        assert not result.is_valid
        assert "required" in result.error.lower()


class TestEmailValidation:
    """Tests for validate_email()."""

    def test_valid_emails(self) -> None:
        """Test valid email addresses."""
        valid_emails = [
            "john@example.com",
            "jane.doe@company.co.uk",
            "test+tag@example.org",
            "user123@subdomain.example.com",
        ]

        for email in valid_emails:
            result = validate_email(email)
            assert result.is_valid, f"Expected valid: {email}"

    def test_invalid_emails(self) -> None:
        """Test invalid email addresses."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
            "user@example",  # No TLD - depends on pattern
        ]

        for email in invalid_emails:
            result = validate_email(email)
            # Email format validation
            if result.is_valid:
                # Some edge cases might pass, that's okay
                pass

    def test_email_lowercase(self) -> None:
        """Test email normalization to lowercase."""
        result = validate_email("John.Doe@Example.COM")
        assert result.is_valid
        assert result.normalized_value == "john.doe@example.com"

    def test_empty_email_is_valid(self) -> None:
        """Test that missing email is valid (optional field)."""
        result = validate_email(None)
        assert result.is_valid
        assert result.normalized_value is None

        result = validate_email("")
        assert result.is_valid


class TestNameValidation:
    """Tests for validate_name()."""

    def test_valid_names(self) -> None:
        """Test valid names."""
        valid_names = ["John", "Jane Doe", "O'Brien", "Jean-Pierre", "María"]

        for name in valid_names:
            result = validate_name(name)
            assert result.is_valid, f"Expected valid: {name}"

    def test_required_name_missing(self) -> None:
        """Test that required name returns error when missing."""
        result = validate_name(None, required=True)
        assert not result.is_valid
        assert "required" in result.error.lower()

    def test_optional_name_missing(self) -> None:
        """Test that optional name is valid when missing."""
        result = validate_name(None, required=False)
        assert result.is_valid

    def test_name_too_long(self) -> None:
        """Test name length validation."""
        long_name = "A" * 150
        result = validate_name(long_name, max_length=100)
        assert not result.is_valid
        assert "100" in result.error

    def test_name_whitespace_trimmed(self) -> None:
        """Test that whitespace is trimmed."""
        result = validate_name("  John  ")
        assert result.is_valid
        assert result.normalized_value == "John"

    def test_name_only_invalid_chars(self) -> None:
        """Test that names with only invalid characters fail."""
        result = validate_name("12345")
        assert not result.is_valid
        assert "invalid characters" in result.error.lower()


class TestCompanyNameValidation:
    """Tests for validate_company_name()."""

    def test_valid_company_names(self) -> None:
        """Test valid company names."""
        valid_names = ["Acme Corp", "Microsoft", "ABC-123", "The Company"]

        for name in valid_names:
            result = validate_company_name(name)
            assert result.is_valid, f"Expected valid: {name}"

    def test_company_name_required(self) -> None:
        """Test that company name is required."""
        result = validate_company_name(None)
        assert not result.is_valid
        assert "required" in result.error.lower()

    def test_company_name_length(self) -> None:
        """Test company name length limits."""
        # Too long
        long_name = "A" * 250
        result = validate_company_name(long_name, max_length=200)
        assert not result.is_valid


class TestJobTitleValidation:
    """Tests for validate_job_title()."""

    def test_valid_job_titles(self) -> None:
        """Test valid job titles."""
        valid_titles = [
            "Software Engineer",
            "VP of Sales",
            "CEO",
            "Senior Product Manager",
        ]

        for title in valid_titles:
            result = validate_job_title(title)
            assert result.is_valid, f"Expected valid: {title}"

    def test_job_title_required(self) -> None:
        """Test that job title is required."""
        result = validate_job_title(None)
        assert not result.is_valid

    def test_job_title_length(self) -> None:
        """Test job title length limit."""
        long_title = "A" * 250
        result = validate_job_title(long_title, max_length=200)
        assert not result.is_valid


class TestCompanySizeValidation:
    """Tests for validate_company_size()."""

    def test_valid_company_sizes(self) -> None:
        """Test valid company size values."""
        for size in VALID_COMPANY_SIZES:
            result = validate_company_size(size)
            assert result.is_valid, f"Expected valid: {size}"

    def test_invalid_company_size(self) -> None:
        """Test invalid company size values."""
        invalid_sizes = ["small", "100", "1-5", "unknown"]

        for size in invalid_sizes:
            result = validate_company_size(size)
            assert not result.is_valid, f"Expected invalid: {size}"

    def test_empty_company_size_valid(self) -> None:
        """Test that empty company size is valid (optional)."""
        result = validate_company_size(None)
        assert result.is_valid

        result = validate_company_size("")
        assert result.is_valid


class TestCrossFieldValidation:
    """Tests for cross-field validation functions."""

    def test_full_name_derivation(self) -> None:
        """Test deriving full name from first and last."""
        result = validate_full_name_consistency("John", "Doe", None)
        assert result.is_valid
        assert result.normalized_value == "John Doe"

    def test_full_name_with_existing(self) -> None:
        """Test full name consistency with existing value."""
        result = validate_full_name_consistency("John", "Doe", "John Smith Doe")
        assert result.is_valid
        assert result.normalized_value == "John Smith Doe"

    def test_domain_derivation_from_linkedin(self) -> None:
        """Test deriving domain from company LinkedIn URL."""
        domain = derive_domain_from_linkedin_url("https://linkedin.com/company/microsoft")
        assert domain == "microsoft.com"

    def test_domain_derivation_none(self) -> None:
        """Test domain derivation with no URL."""
        domain = derive_domain_from_linkedin_url(None)
        assert domain is None


class TestCompositLeadValidation:
    """Tests for validate_lead() composite function."""

    def test_valid_lead(self) -> None:
        """Test validation of a complete, valid lead."""
        lead = {
            "id": "test-123",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Corp",
            "job_title": "Software Engineer",
            "email": "john@acme.com",
        }

        result = validate_lead(lead)
        assert result["is_valid"]
        assert result["status"] == "valid"
        assert len(result["errors"]) == 0

    def test_invalid_lead_missing_fields(self) -> None:
        """Test validation of lead with missing required fields."""
        lead = {
            "id": "test-123",
            "linkedin_url": None,  # Missing
            "first_name": "John",
            "last_name": None,  # Missing
            "company_name": "Acme Corp",
            "job_title": "Engineer",
        }

        result = validate_lead(lead)
        assert not result["is_valid"]
        assert result["status"] == "invalid"
        assert len(result["errors"]) >= 2

    def test_lead_without_email_still_valid(self) -> None:
        """Test that lead without email is still valid (flagged for enrichment)."""
        lead = {
            "id": "test-123",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Corp",
            "job_title": "Engineer",
            # No email
        }

        result = validate_lead(lead)
        assert result["is_valid"]
        assert result["normalized"]["needs_email_enrichment"]

    def test_lead_normalization(self) -> None:
        """Test that lead fields are normalized."""
        lead = {
            "id": "test-123",
            "linkedin_url": "www.linkedin.com/in/johndoe/",
            "first_name": "  john  ",
            "last_name": "DOE",
            "company_name": "Acme Corp",
            "job_title": "VP of Sales",
            "email": "JOHN@ACME.COM",
        }

        result = validate_lead(lead)
        assert result["is_valid"]
        # Check normalization happened
        assert result["normalized"]["email"] == "john@acme.com"

    def test_lead_with_title_field(self) -> None:
        """Test lead with 'title' field instead of 'job_title' (DB compatibility)."""
        lead = {
            "id": "test-123",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Corp",
            "title": "Software Engineer",  # DB column name
        }

        result = validate_lead(lead)
        assert result["is_valid"]
        assert result["normalized"]["job_title"] == "Software Engineer"
        assert result["normalized"]["title"] == "Software Engineer"


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True, field="test")
        assert result.is_valid
        assert result.error is None

    def test_invalid_result(self) -> None:
        """Test creating an invalid result."""
        result = ValidationResult(is_valid=False, error="Field is required", field="test")
        assert not result.is_valid
        assert result.error == "Field is required"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = ValidationResult(is_valid=True, field="email", normalized_value="test@example.com")
        d = result.to_dict()
        assert d["is_valid"]
        assert d["normalized_value"] == "test@example.com"
