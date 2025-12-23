"""Data models for Google Contacts API (People API v1).

Defines Pydantic models for contact resources, groups, and API responses
aligned with the People API v1 schema.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailAddress(BaseModel):
    """Email address model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    value: str
    type: str | None = None  # e.g., "home", "work"
    display_text: str | None = None
    metadata: dict[str, Any] | None = None


class PhoneNumber(BaseModel):
    """Phone number model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    value: str
    type: str | None = None  # e.g., "home", "work", "mobile"
    canonical_form: str | None = None
    metadata: dict[str, Any] | None = None


class Name(BaseModel):
    """Name model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    display_name: str | None = Field(default=None, alias="displayName")
    family_name: str | None = Field(default=None, alias="familyName")
    given_name: str | None = Field(default=None, alias="givenName")
    middle_name: str | None = Field(default=None, alias="middleName")
    prefix: str | None = None
    suffix: str | None = None
    phonetic_family_name: str | None = Field(default=None, alias="phoneticFamilyName")
    phonetic_given_name: str | None = Field(default=None, alias="phoneticGivenName")
    phonetic_middle_name: str | None = Field(default=None, alias="phoneticMiddleName")
    phonetic_full_name: str | None = Field(default=None, alias="phoneticFullName")
    metadata: dict[str, Any] | None = None


class PostalAddress(BaseModel):
    """Postal address model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    formatted_value: str | None = None
    type: str | None = None  # e.g., "home", "work"
    street_address: str | None = None
    extended_address: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    country_code: str | None = None
    metadata: dict[str, Any] | None = None


class Organization(BaseModel):
    """Organization model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str | None = None
    title: str | None = None
    type: str | None = None
    start_date: dict[str, Any] | None = None
    end_date: dict[str, Any] | None = None
    current: bool | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None


class Metadata(BaseModel):
    """Contact metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sources: list[dict[str, Any]] | None = None
    primary_sources: list[dict[str, Any]] | None = None
    linked_people_resource_names: list[str] | None = None
    deleted: bool | None = None


class Contact(BaseModel):
    """Contact resource from People API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    resource_name: str | None = Field(default=None, alias="resourceName")
    etag: str | None = None
    names: list[Name] | None = None
    email_addresses: list[EmailAddress] | None = Field(default=None, alias="emailAddresses")
    phone_numbers: list[PhoneNumber] | None = Field(default=None, alias="phoneNumbers")
    addresses: list[PostalAddress] | None = None
    organizations: list[Organization] | None = None
    biographies: list[dict[str, Any]] | None = None
    birthdays: list[dict[str, Any]] | None = None
    events: list[dict[str, Any]] | None = None
    relations: list[dict[str, Any]] | None = None
    urls: list[dict[str, Any]] | None = None
    photos: list[dict[str, Any]] | None = None
    memberships: list[dict[str, Any]] | None = None
    user_defined: list[dict[str, Any]] | None = Field(default=None, alias="userDefined")
    misckeyed_fields: list[dict[str, Any]] | None = None
    group_resources: list[str] | None = Field(default=None, alias="groupResourceNames")
    im_clients: list[dict[str, Any]] | None = Field(default=None, alias="imClients")
    nicknames: list[dict[str, Any]] | None = None
    occupations: list[dict[str, Any]] | None = None
    interests: list[dict[str, Any]] | None = None
    skills: list[dict[str, Any]] | None = None
    metadata: Metadata | None = None


class ContactGroup(BaseModel):
    """Contact group resource."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    resource_name: str | None = Field(default=None, alias="resourceName")
    etag: str | None = None
    name: str
    group_type: str | None = Field(default=None, alias="groupType")
    member_count: int | None = Field(default=None, alias="memberCount")
    member_resource_names: list[str] | None = Field(default=None, alias="memberResourceNames")
    formatted_name: str | None = Field(default=None, alias="formattedName")
    metadata: dict[str, Any] | None = None


class ContactsListResponse(BaseModel):
    """Response from list contacts endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    connections: list[Contact] | None = None
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    next_sync_token: str | None = Field(default=None, alias="nextSyncToken")


class ContactSearchResponse(BaseModel):
    """Response from search contacts endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    results: list[dict[str, Any]] | None = None
    next_page_token: str | None = None


class ContactGroupsListResponse(BaseModel):
    """Response from list contact groups endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    contact_groups: list[ContactGroup] | None = Field(default=None, alias="contactGroups")
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    next_sync_token: str | None = Field(default=None, alias="nextSyncToken")


class BatchCreateContactsRequest(BaseModel):
    """Request for batch creating contacts."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    contacts: list[dict[str, Any]]
    read_mask: str | None = None


class BatchCreateContactsResponse(BaseModel):
    """Response from batch create contacts."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    contact_people: list[Contact] | None = None


class ContactCreateRequest(BaseModel):
    """Request to create a single contact."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    given_name: str | None = None
    family_name: str | None = None
    display_name: str | None = None
    email_address: str | None = None
    email_type: str = "work"
    phone_number: str | None = None
    phone_type: str = "mobile"
    organization_name: str | None = None
    job_title: str | None = None
    street_address: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None


class ContactUpdateRequest(BaseModel):
    """Request to update a contact."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    resource_name: str
    etag: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    display_name: str | None = None
    email_address: str | None = None
    email_type: str | None = None
    phone_number: str | None = None
    phone_type: str | None = None
    organization_name: str | None = None
    job_title: str | None = None
    street_address: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
