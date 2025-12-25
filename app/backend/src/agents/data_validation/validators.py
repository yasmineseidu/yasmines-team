"""
Field validators for Data Validation Agent.

Provides validation functions for lead fields including LinkedIn URLs,
emails, names, and company data.

Validation Philosophy:
- Critical fields (linkedin_url, first_name, last_name, company_name, job_title)
  must be present and valid
- Email is optional - validate format if present, flag for enrichment if missing
- All validators return (is_valid, error_message) tuples
"""

import re
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# LinkedIn URL pattern from YAML spec
LINKEDIN_URL_PATTERN = re.compile(
    r"^https?://(www\.)?linkedin\.com/(in|pub)/[a-zA-Z0-9_%-]+/?(\?.*)?$",
    re.IGNORECASE,
)

# Email pattern (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    re.IGNORECASE,
)

# Valid company size values from YAML spec
VALID_COMPANY_SIZES = frozenset(
    [
        "1-10",
        "11-50",
        "51-200",
        "201-500",
        "501-1000",
        "1001-5000",
        "5001-10000",
        "10000+",
    ]
)

# Characters to strip from names
INVALID_NAME_CHARS = re.compile(r"[^a-zA-Z\s\-'\.\,]")


# =============================================================================
# Validation Result Type
# =============================================================================


class ValidationResult:
    """Result of a field validation."""

    __slots__ = ("is_valid", "error", "field", "normalized_value")

    def __init__(
        self,
        is_valid: bool,
        error: str | None = None,
        field: str | None = None,
        normalized_value: Any = None,
    ) -> None:
        """
        Initialize validation result.

        Args:
            is_valid: Whether the field is valid.
            error: Error message if invalid.
            field: Field name that was validated.
            normalized_value: Optionally, the normalized value.
        """
        self.is_valid = is_valid
        self.error = error
        self.field = field
        self.normalized_value = normalized_value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"is_valid": self.is_valid}
        if self.error:
            result["error"] = self.error
        if self.field:
            result["field"] = self.field
        if self.normalized_value is not None:
            result["normalized_value"] = self.normalized_value
        return result


# =============================================================================
# Field Validators
# =============================================================================


def validate_linkedin_url(url: str | None, field_name: str = "linkedin_url") -> ValidationResult:
    """
    Validate LinkedIn profile URL.

    Args:
        url: LinkedIn URL to validate.
        field_name: Name of field for error messages.

    Returns:
        ValidationResult with is_valid and normalized URL.

    Examples:
        >>> validate_linkedin_url("https://linkedin.com/in/johndoe").is_valid
        True
        >>> validate_linkedin_url("https://facebook.com/johndoe").is_valid
        False
    """
    if not url:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} is required",
            field=field_name,
        )

    url = url.strip()

    # Normalize URL
    if url.startswith("www."):
        url = f"https://{url}"
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Remove trailing slash for consistency
    url = url.rstrip("/")

    # Validate pattern
    if not LINKEDIN_URL_PATTERN.match(url):
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} is not a valid LinkedIn profile URL",
            field=field_name,
            normalized_value=url,
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=url,
    )


def validate_email(email: str | None, field_name: str = "email") -> ValidationResult:
    """
    Validate email address format.

    Note: Email is optional. This validator only checks format if present.
    Missing email should be flagged for enrichment, not rejected.

    Args:
        email: Email address to validate.
        field_name: Name of field for error messages.

    Returns:
        ValidationResult with is_valid and lowercase email.
    """
    if not email:
        # Email is optional - return valid with None
        return ValidationResult(
            is_valid=True,
            field=field_name,
            normalized_value=None,
        )

    email = email.strip().lower()

    if not EMAIL_PATTERN.match(email):
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} has invalid format",
            field=field_name,
            normalized_value=email,
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=email,
    )


def validate_name(
    name: str | None,
    field_name: str = "name",
    min_length: int = 1,
    max_length: int = 100,
    required: bool = True,
) -> ValidationResult:
    """
    Validate a name field (first_name, last_name).

    Args:
        name: Name to validate.
        field_name: Name of field for error messages.
        min_length: Minimum length.
        max_length: Maximum length.
        required: Whether the field is required.

    Returns:
        ValidationResult with is_valid.
    """
    if not name:
        if required:
            return ValidationResult(
                is_valid=False,
                error=f"{field_name} is required",
                field=field_name,
            )
        return ValidationResult(is_valid=True, field=field_name)

    name = name.strip()

    # Check length
    if len(name) < min_length:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be at least {min_length} character(s)",
            field=field_name,
            normalized_value=name,
        )

    if len(name) > max_length:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be at most {max_length} characters",
            field=field_name,
            normalized_value=name[:max_length],
        )

    # Check for completely invalid content (only numbers/symbols)
    clean_name = INVALID_NAME_CHARS.sub("", name)
    if not clean_name.strip():
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} contains only invalid characters",
            field=field_name,
            normalized_value=name,
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=name,
    )


def validate_company_name(
    company_name: str | None,
    field_name: str = "company_name",
    min_length: int = 1,
    max_length: int = 200,
) -> ValidationResult:
    """
    Validate company name.

    Args:
        company_name: Company name to validate.
        field_name: Name of field for error messages.
        min_length: Minimum length.
        max_length: Maximum length.

    Returns:
        ValidationResult with is_valid.
    """
    if not company_name:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} is required",
            field=field_name,
        )

    company_name = company_name.strip()

    if len(company_name) < min_length:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be at least {min_length} character(s)",
            field=field_name,
            normalized_value=company_name,
        )

    if len(company_name) > max_length:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be at most {max_length} characters",
            field=field_name,
            normalized_value=company_name[:max_length],
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=company_name,
    )


def validate_job_title(
    job_title: str | None,
    field_name: str = "job_title",
    max_length: int = 200,
) -> ValidationResult:
    """
    Validate job title.

    Args:
        job_title: Job title to validate.
        field_name: Name of field for error messages.
        max_length: Maximum length.

    Returns:
        ValidationResult with is_valid.
    """
    if not job_title:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} is required",
            field=field_name,
        )

    job_title = job_title.strip()

    if len(job_title) > max_length:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be at most {max_length} characters",
            field=field_name,
            normalized_value=job_title[:max_length],
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=job_title,
    )


def validate_company_size(
    company_size: str | None,
    field_name: str = "company_size",
) -> ValidationResult:
    """
    Validate company size against allowed values.

    Args:
        company_size: Company size to validate.
        field_name: Name of field for error messages.

    Returns:
        ValidationResult with is_valid.
    """
    if not company_size:
        # Company size is optional
        return ValidationResult(
            is_valid=True,
            field=field_name,
        )

    company_size = company_size.strip()

    if company_size not in VALID_COMPANY_SIZES:
        return ValidationResult(
            is_valid=False,
            error=f"{field_name} must be one of: {', '.join(sorted(VALID_COMPANY_SIZES))}",
            field=field_name,
            normalized_value=company_size,
        )

    return ValidationResult(
        is_valid=True,
        field=field_name,
        normalized_value=company_size,
    )


# =============================================================================
# Cross-Field Validation
# =============================================================================


def validate_full_name_consistency(
    first_name: str | None,
    last_name: str | None,
    full_name: str | None,
) -> ValidationResult:
    """
    Validate that full_name is consistent with first_name and last_name.

    If full_name is missing, it will be derived from first_name + last_name.

    Args:
        first_name: First name.
        last_name: Last name.
        full_name: Full name.

    Returns:
        ValidationResult with derived or validated full_name.
    """
    if not first_name or not last_name:
        if full_name:
            return ValidationResult(
                is_valid=True,
                field="full_name",
                normalized_value=full_name.strip(),
            )
        return ValidationResult(
            is_valid=False,
            error="Cannot derive full_name without first_name and last_name",
            field="full_name",
        )

    derived_name = f"{first_name.strip()} {last_name.strip()}"

    if not full_name:
        # Derive full_name
        return ValidationResult(
            is_valid=True,
            field="full_name",
            normalized_value=derived_name,
        )

    # Both exist - just use what we have
    return ValidationResult(
        is_valid=True,
        field="full_name",
        normalized_value=full_name.strip(),
    )


def derive_domain_from_linkedin_url(
    company_linkedin_url: str | None,
) -> str | None:
    """
    Derive company domain from company LinkedIn URL.

    Args:
        company_linkedin_url: Company LinkedIn profile URL.

    Returns:
        Derived domain or None.

    Example:
        >>> derive_domain_from_linkedin_url("https://linkedin.com/company/microsoft")
        "microsoft.com"
    """
    if not company_linkedin_url:
        return None

    # Pattern: https://linkedin.com/company/{company-name}
    pattern = re.compile(
        r"linkedin\.com/company/([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    )
    match = pattern.search(company_linkedin_url)

    if match:
        company_slug = match.group(1).lower()
        # Simple heuristic: add .com suffix
        return f"{company_slug}.com"

    return None


# =============================================================================
# Composite Validation
# =============================================================================


def validate_lead(
    lead: dict[str, Any],
    strict_mode: bool = False,
) -> dict[str, Any]:
    """
    Validate all fields of a lead.

    Critical fields (must be valid):
    - linkedin_url
    - first_name
    - last_name
    - company_name
    - job_title

    Optional fields (validate if present):
    - email
    - company_size
    - company_domain
    - location

    Args:
        lead: Lead data dictionary.
        strict_mode: If True, require email field.

    Returns:
        Dictionary with validation results, normalized fields, and errors.
    """
    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, Any] = {}

    # Validate critical fields
    linkedin_result = validate_linkedin_url(lead.get("linkedin_url"))
    if not linkedin_result.is_valid:
        errors.append(linkedin_result.error or "linkedin_url is invalid")
    else:
        normalized["linkedin_url"] = linkedin_result.normalized_value

    first_name_result = validate_name(
        lead.get("first_name"),
        field_name="first_name",
        required=True,
    )
    if not first_name_result.is_valid:
        errors.append(first_name_result.error or "first_name is invalid")
    else:
        normalized["first_name"] = first_name_result.normalized_value

    last_name_result = validate_name(
        lead.get("last_name"),
        field_name="last_name",
        required=True,
    )
    if not last_name_result.is_valid:
        errors.append(last_name_result.error or "last_name is invalid")
    else:
        normalized["last_name"] = last_name_result.normalized_value

    company_result = validate_company_name(lead.get("company_name"))
    if not company_result.is_valid:
        errors.append(company_result.error or "company_name is invalid")
    else:
        normalized["company_name"] = company_result.normalized_value

    # Handle job_title field - DB uses 'title', agent may use 'job_title'
    job_title_value = lead.get("job_title") or lead.get("title")
    title_result = validate_job_title(job_title_value)
    if not title_result.is_valid:
        errors.append(title_result.error or "job_title is invalid")
    else:
        normalized["job_title"] = title_result.normalized_value
        normalized["title"] = title_result.normalized_value  # For DB compatibility

    # Validate optional fields
    email_result = validate_email(lead.get("email"))
    if lead.get("email"):
        if not email_result.is_valid:
            errors.append(email_result.error or "email format is invalid")
        else:
            normalized["email"] = email_result.normalized_value
    else:
        # Flag missing email for enrichment
        warnings.append("email missing - flagged for enrichment")
        normalized["needs_email_enrichment"] = True

    size_result = validate_company_size(lead.get("company_size"))
    if lead.get("company_size") and not size_result.is_valid:
        # Company size is optional, so just warn
        warnings.append(size_result.error or "company_size is invalid")
    elif size_result.is_valid and size_result.normalized_value:
        normalized["company_size"] = size_result.normalized_value

    # Cross-field validation
    full_name_result = validate_full_name_consistency(
        normalized.get("first_name") or lead.get("first_name"),
        normalized.get("last_name") or lead.get("last_name"),
        lead.get("full_name"),
    )
    if full_name_result.is_valid and full_name_result.normalized_value:
        normalized["full_name"] = full_name_result.normalized_value

    # Derive domain if not present
    if not lead.get("company_domain"):
        derived_domain = derive_domain_from_linkedin_url(lead.get("company_linkedin_url"))
        if derived_domain:
            normalized["company_domain"] = derived_domain
    else:
        normalized["company_domain"] = lead.get("company_domain")

    # Copy through non-validated fields
    passthrough_fields = [
        "id",
        "campaign_id",
        "company_linkedin_url",
        "company_industry",
        "location",
        "city",
        "state",
        "country",
        "source",
        "source_url",
        "seniority",
        "department",
        "phone",
        "headline",
    ]
    for field in passthrough_fields:
        if lead.get(field):
            normalized[field] = lead[field]

    # Determine overall validation status
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "status": "valid" if is_valid else "invalid",
        "new_status": "validated" if is_valid else "invalid",
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }
