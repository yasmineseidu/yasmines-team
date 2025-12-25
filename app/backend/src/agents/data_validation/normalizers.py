"""
Field normalizers for Data Validation Agent.

Provides normalization functions for lead fields including names,
job titles, company names, and locations.

Normalization Philosophy:
- Trim whitespace
- Title case names
- Expand abbreviations (VP -> Vice President)
- Remove legal suffixes from company names
- Derive missing fields where possible
"""

import re
from typing import Any

# =============================================================================
# Job Title Mappings (from YAML spec)
# =============================================================================

# Original mappings (case-sensitive keys for display)
_JOB_TITLE_MAPPINGS_ORIGINAL: dict[str, str] = {
    "VP": "Vice President",
    "SVP": "Senior Vice President",
    "EVP": "Executive Vice President",
    "AVP": "Assistant Vice President",
    "Dir": "Director",
    "Sr Dir": "Senior Director",
    "Mgr": "Manager",
    "Sr Mgr": "Senior Manager",
    "CEO": "Chief Executive Officer",
    "CFO": "Chief Financial Officer",
    "CTO": "Chief Technology Officer",
    "CMO": "Chief Marketing Officer",
    "COO": "Chief Operating Officer",
    "CIO": "Chief Information Officer",
    "CHRO": "Chief Human Resources Officer",
    "CPO": "Chief Product Officer",
    "CRO": "Chief Revenue Officer",
    "CSO": "Chief Strategy Officer",
    "Sr": "Senior",
    "Jr": "Junior",
    "Assoc": "Associate",
    "Asst": "Assistant",
    "Exec": "Executive",
    "Eng": "Engineer",
    "Dev": "Developer",
    "Mktg": "Marketing",
    "Ops": "Operations",
    "HR": "Human Resources",
    "IT": "Information Technology",
    "R&D": "Research and Development",
}

# Uppercase keys for case-insensitive lookup
JOB_TITLE_MAPPINGS: dict[str, str] = {k.upper(): v for k, v in _JOB_TITLE_MAPPINGS_ORIGINAL.items()}

# Seniority patterns for detection (from YAML spec)
SENIORITY_PATTERNS: dict[str, list[str]] = {
    "c_suite": ["Chief", "CEO", "CFO", "CTO", "CMO", "COO", "CIO", "CHRO", "CPO", "CRO"],
    "vp": ["Vice President", "VP", "SVP", "EVP", "AVP"],
    "director": ["Director", "Dir", "Head of"],
    "manager": ["Manager", "Mgr", "Lead", "Team Lead"],
    "senior": ["Senior", "Sr", "Principal", "Staff"],
    "mid": ["Associate", "Specialist"],
    "entry": ["Junior", "Jr", "Analyst", "Coordinator"],
}

# Legal suffixes to remove from company names (from YAML spec)
LEGAL_SUFFIXES: list[str] = [
    ", Inc.",
    " Inc.",
    " Inc",
    ", LLC",
    " LLC",
    ", Ltd.",
    " Ltd.",
    " Ltd",
    ", Corp.",
    " Corp.",
    " Corp",
    ", Co.",
    " Co.",
    " Co",
    ", LP",
    " LP",
    ", LLP",
    " LLP",
    ", PLC",
    " PLC",
    ", GmbH",
    " GmbH",
    ", AG",
    " AG",
    ", SA",
    " SA",
    ", S.A.",
    " S.A.",
    ", Pty Ltd",
    " Pty Ltd",
    ", Pvt Ltd",
    " Pvt Ltd",
]

# Patterns for special character removal (keep letters, numbers, space, hyphen, apostrophe)
SPECIAL_CHAR_PATTERN = re.compile(r"[^\w\s\-\'\.]", re.UNICODE)
MULTIPLE_SPACES = re.compile(r"\s+")


# =============================================================================
# Name Normalizers
# =============================================================================


def normalize_name(name: str | None) -> str | None:
    """
    Normalize a name field (first_name, last_name).

    Operations:
    - Trim whitespace
    - Title case
    - Remove invalid special characters
    - Collapse multiple spaces

    Args:
        name: Name to normalize.

    Returns:
        Normalized name or None.

    Examples:
        >>> normalize_name("  john doe  ")
        "John Doe"
        >>> normalize_name("JANE O'BRIEN")
        "Jane O'Brien"
    """
    if not name:
        return None

    # Trim and collapse spaces
    name = MULTIPLE_SPACES.sub(" ", name.strip())

    # Remove invalid characters
    name = SPECIAL_CHAR_PATTERN.sub("", name)

    # Title case (handles McName, O'Name patterns)
    name = _smart_title_case(name)

    return name.strip() if name else None


def _smart_title_case(text: str) -> str:
    """
    Smart title case that handles special patterns.

    Handles:
    - McDonald, MacGregor (Mc/Mac prefixes)
    - O'Brien, D'Angelo (apostrophe patterns)
    - van der Berg, de la Cruz (lowercase particles)

    Args:
        text: Text to convert.

    Returns:
        Title-cased text.
    """
    words: list[str] = []
    lowercase_particles = {"van", "von", "de", "da", "del", "della", "der", "di", "du", "la", "le"}

    for word in text.split():
        lower_word = word.lower()

        # Keep particles lowercase (unless first word)
        if lower_word in lowercase_particles and words:
            words.append(lower_word)
            continue

        # Handle Mc/Mac prefixes
        if lower_word.startswith("mc") and len(word) > 2:
            words.append(f"Mc{word[2:].capitalize()}")
            continue
        if lower_word.startswith("mac") and len(word) > 3:
            words.append(f"Mac{word[3:].capitalize()}")
            continue

        # Handle O'Name pattern
        if "'" in word:
            parts = word.split("'")
            words.append("'".join(p.capitalize() for p in parts))
            continue

        # Handle hyphenated names
        if "-" in word:
            parts = word.split("-")
            words.append("-".join(p.capitalize() for p in parts))
            continue

        # Standard title case
        words.append(word.capitalize())

    return " ".join(words)


def derive_full_name(first_name: str | None, last_name: str | None) -> str | None:
    """
    Derive full name from first and last name.

    Args:
        first_name: First name.
        last_name: Last name.

    Returns:
        Full name or None.
    """
    if not first_name and not last_name:
        return None

    first = normalize_name(first_name) or ""
    last = normalize_name(last_name) or ""

    full_name = f"{first} {last}".strip()
    return full_name if full_name else None


# =============================================================================
# Job Title Normalizers
# =============================================================================


def normalize_job_title(job_title: str | None) -> str | None:
    """
    Normalize job title.

    Operations:
    - Trim whitespace
    - Expand abbreviations (VP -> Vice President)
    - Clean up formatting

    Args:
        job_title: Job title to normalize.

    Returns:
        Normalized job title or None.

    Examples:
        >>> normalize_job_title("VP of Sales")
        "Vice President of Sales"
        >>> normalize_job_title("Sr. Software Eng")
        "Senior Software Engineer"
    """
    if not job_title:
        return None

    job_title = job_title.strip()

    # Expand abbreviations
    words = job_title.split()
    normalized_words = []

    for word in words:
        # Check if word matches an abbreviation (case-insensitive)
        clean_word = word.rstrip(".,")
        upper_word = clean_word.upper()

        if upper_word in JOB_TITLE_MAPPINGS:
            normalized_words.append(JOB_TITLE_MAPPINGS[upper_word])
        else:
            normalized_words.append(word)

    return " ".join(normalized_words)


def detect_seniority(job_title: str | None) -> str | None:
    """
    Detect seniority level from job title.

    Uses word boundary matching to avoid false positives
    (e.g., "CTO" matching in "DIRECTOR").

    Args:
        job_title: Job title to analyze.

    Returns:
        Seniority level or None.
    """
    if not job_title:
        return None

    job_title_lower = job_title.lower()

    # Check patterns in priority order (most senior first)
    for seniority, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            # Use word boundary matching to avoid substring false positives
            # e.g., "CTO" should not match "Director"
            pattern_regex = re.compile(r"\b" + re.escape(pattern.lower()) + r"\b", re.IGNORECASE)
            if pattern_regex.search(job_title_lower):
                return seniority

    return None


# =============================================================================
# Company Name Normalizers
# =============================================================================


def normalize_company_name(company_name: str | None) -> str | None:
    """
    Normalize company name.

    Operations:
    - Trim whitespace
    - Remove legal suffixes (Inc., LLC, Ltd.)
    - Standardize formatting

    Args:
        company_name: Company name to normalize.

    Returns:
        Normalized company name or None.

    Examples:
        >>> normalize_company_name("Acme Inc.")
        "Acme"
        >>> normalize_company_name("  Tech Solutions, LLC  ")
        "Tech Solutions"
    """
    if not company_name:
        return None

    company_name = company_name.strip()

    # Remove legal suffixes
    for suffix in LEGAL_SUFFIXES:
        if company_name.endswith(suffix):
            company_name = company_name[: -len(suffix)].strip()
            break  # Only remove one suffix

    # Remove trailing punctuation
    company_name = company_name.rstrip(".,")

    # Collapse multiple spaces
    company_name = MULTIPLE_SPACES.sub(" ", company_name)

    return company_name.strip() if company_name else None


def derive_domain_from_company_name(company_name: str | None) -> str | None:
    """
    Derive domain from company name (simple heuristic).

    This is a fallback - prefer deriving from LinkedIn URL.

    Args:
        company_name: Company name.

    Returns:
        Derived domain or None.

    Examples:
        >>> derive_domain_from_company_name("Acme Corp")
        "acme.com"
    """
    if not company_name:
        return None

    # Normalize and clean
    clean_name = normalize_company_name(company_name)
    if not clean_name:
        return None

    # Convert to lowercase, replace spaces with nothing
    domain_base = clean_name.lower().replace(" ", "").replace("-", "")

    # Remove non-alphanumeric
    domain_base = re.sub(r"[^a-z0-9]", "", domain_base)

    if domain_base:
        return f"{domain_base}.com"

    return None


# =============================================================================
# Location Normalizers
# =============================================================================


def parse_location(location: str | None) -> dict[str, str | None]:
    """
    Parse location string into city, state, country components.

    Handles various formats:
    - "San Francisco, CA, USA"
    - "New York, NY"
    - "London, United Kingdom"
    - "Sydney, NSW, Australia"

    Args:
        location: Location string.

    Returns:
        Dictionary with city, state, country.
    """
    result: dict[str, str | None] = {
        "city": None,
        "state": None,
        "country": None,
    }

    if not location:
        return result

    location = location.strip()

    # Split by comma
    parts = [p.strip() for p in location.split(",")]

    if len(parts) == 1:
        # Just one component - assume city or country
        result["city"] = parts[0]
    elif len(parts) == 2:
        # Two components - city, state/country
        result["city"] = parts[0]
        # Check if second part looks like a US state
        if len(parts[1]) == 2 and parts[1].upper() == parts[1]:
            result["state"] = parts[1]
            result["country"] = "United States"
        else:
            result["country"] = parts[1]
    elif len(parts) >= 3:
        # Three or more - city, state, country
        result["city"] = parts[0]
        result["state"] = parts[1]
        result["country"] = parts[2]

    return result


# =============================================================================
# Composite Normalizer
# =============================================================================


def normalize_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize all fields of a lead.

    Args:
        lead: Lead data dictionary.

    Returns:
        Dictionary with normalized fields.
    """
    normalized: dict[str, Any] = {}

    # Copy ID fields
    if lead.get("id"):
        normalized["id"] = lead["id"]
    if lead.get("campaign_id"):
        normalized["campaign_id"] = lead["campaign_id"]

    # Normalize names
    normalized["first_name"] = normalize_name(lead.get("first_name"))
    normalized["last_name"] = normalize_name(lead.get("last_name"))
    normalized["full_name"] = derive_full_name(
        normalized["first_name"],
        normalized["last_name"],
    ) or normalize_name(lead.get("full_name"))

    # Normalize job title - handle both 'title' and 'job_title'
    job_title = lead.get("job_title") or lead.get("title")
    normalized["job_title"] = normalize_job_title(job_title)
    normalized["title"] = normalized["job_title"]  # DB compatibility

    # Detect seniority
    seniority = detect_seniority(normalized["job_title"])
    normalized["seniority"] = seniority or lead.get("seniority")

    # Normalize company name
    normalized["company_name"] = normalize_company_name(lead.get("company_name"))

    # Normalize LinkedIn URL
    linkedin_url = lead.get("linkedin_url")
    if linkedin_url:
        normalized["linkedin_url"] = linkedin_url.strip().rstrip("/")

    # Email - lowercase
    email = lead.get("email")
    if email:
        normalized["email"] = email.strip().lower()

    # Company domain - derive if missing
    company_domain = lead.get("company_domain")
    if not company_domain:
        # Try to derive from company LinkedIn URL first
        company_linkedin = lead.get("company_linkedin_url")
        if company_linkedin:
            from src.agents.data_validation.validators import derive_domain_from_linkedin_url

            company_domain = derive_domain_from_linkedin_url(company_linkedin)
        # Fallback to deriving from company name
        if not company_domain:
            company_domain = derive_domain_from_company_name(normalized["company_name"])
    normalized["company_domain"] = company_domain

    # Parse location
    location = lead.get("location")
    if location:
        location_parts = parse_location(location)
        normalized["location"] = location
        normalized["city"] = lead.get("city") or location_parts["city"]
        normalized["state"] = lead.get("state") or location_parts["state"]
        normalized["country"] = lead.get("country") or location_parts["country"]
    else:
        normalized["city"] = lead.get("city")
        normalized["state"] = lead.get("state")
        normalized["country"] = lead.get("country")

    # Pass through other fields
    passthrough_fields = [
        "company_linkedin_url",
        "company_size",
        "company_industry",
        "industry",
        "department",
        "phone",
        "headline",
        "source",
        "source_url",
        "linkedin_id",
    ]
    for field in passthrough_fields:
        if lead.get(field):
            normalized[field] = lead[field]

    return normalized
