"""
Schemas for Duplicate Detection Agent.

Defines Pydantic models for input/output validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LeadRecord:
    """
    Lead record for duplicate detection.

    Represents a lead with fields needed for matching and merging.
    """

    id: str
    linkedin_url: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    title: str | None = None  # DB uses 'title', not 'job_title'
    phone: str | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRecord":
        """Create LeadRecord from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            linkedin_url=data.get("linkedin_url"),
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            company_name=data.get("company_name"),
            company_domain=data.get("company_domain"),
            title=data.get("title") or data.get("job_title"),
            phone=data.get("phone"),
            location=data.get("location"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "linkedin_url": self.linkedin_url,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "title": self.title,
            "phone": self.phone,
            "location": self.location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "created_at": self.created_at,
        }

    def count_populated_fields(self) -> int:
        """Count number of populated fields for completeness scoring."""
        fields = [
            self.linkedin_url,
            self.email,
            self.first_name,
            self.last_name,
            self.company_name,
            self.company_domain,
            self.title,
            self.phone,
            self.location,
            self.city,
            self.state,
            self.country,
        ]
        return sum(1 for f in fields if f)


@dataclass
class DedupInput:
    """Input for duplicate detection."""

    campaign_id: str
    total_valid_leads: int
    leads: list[LeadRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DedupInput":
        """Create DedupInput from dictionary."""
        leads_data = data.get("leads", [])
        leads = [LeadRecord.from_dict(lead) for lead in leads_data]
        return cls(
            campaign_id=str(data.get("campaign_id", "")),
            total_valid_leads=int(data.get("total_valid_leads", len(leads))),
            leads=leads,
        )


@dataclass
class DedupOutput:
    """Output from duplicate detection."""

    # Counts
    total_checked: int = 0
    exact_duplicates: int = 0
    fuzzy_duplicates: int = 0
    total_merged: int = 0
    unique_leads: int = 0
    duplicate_rate: float = 0.0

    # Details
    details: dict[str, Any] = field(default_factory=dict)

    # Duplicate groups for merge processing
    exact_duplicate_groups: list[list[str]] = field(default_factory=list)
    fuzzy_duplicate_groups: list[list[str]] = field(default_factory=list)

    # Merge results
    merge_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_checked": self.total_checked,
            "exact_duplicates": self.exact_duplicates,
            "fuzzy_duplicates": self.fuzzy_duplicates,
            "total_merged": self.total_merged,
            "unique_leads": self.unique_leads,
            "duplicate_rate": self.duplicate_rate,
            "details": self.details,
            "exact_duplicate_groups": self.exact_duplicate_groups,
            "fuzzy_duplicate_groups": self.fuzzy_duplicate_groups,
            "merge_results": self.merge_results,
        }
