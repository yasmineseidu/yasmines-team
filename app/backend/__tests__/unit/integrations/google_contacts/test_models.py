"""Unit tests for Google Contacts API models.

Tests Pydantic models for data validation and serialization.
"""

from src.integrations.google_contacts.models import (
    Contact,
    ContactCreateRequest,
    ContactGroup,
    ContactGroupsListResponse,
    ContactsListResponse,
    ContactUpdateRequest,
    EmailAddress,
    Name,
    Organization,
    PhoneNumber,
    PostalAddress,
)


class TestEmailAddressModel:
    """Tests for EmailAddress model."""

    def test_email_address_creation(self) -> None:
        """Should create EmailAddress with required fields."""
        email = EmailAddress(value="john@example.com")
        assert email.value == "john@example.com"
        assert email.type is None

    def test_email_address_with_type(self) -> None:
        """Should create EmailAddress with type."""
        email = EmailAddress(value="john@example.com", type="work")
        assert email.value == "john@example.com"
        assert email.type == "work"

    def test_email_address_with_display_text(self) -> None:
        """Should create EmailAddress with display text."""
        email = EmailAddress(
            value="john@example.com",
            type="home",
            display_text="Home Email",
        )
        assert email.value == "john@example.com"
        assert email.display_text == "Home Email"


class TestPhoneNumberModel:
    """Tests for PhoneNumber model."""

    def test_phone_number_creation(self) -> None:
        """Should create PhoneNumber with value."""
        phone = PhoneNumber(value="+1-555-1234")
        assert phone.value == "+1-555-1234"

    def test_phone_number_with_type(self) -> None:
        """Should create PhoneNumber with type."""
        phone = PhoneNumber(value="+1-555-1234", type="mobile")
        assert phone.type == "mobile"

    def test_phone_number_with_canonical_form(self) -> None:
        """Should create PhoneNumber with canonical form."""
        phone = PhoneNumber(
            value="+1-555-1234",
            type="mobile",
            canonical_form="+15551234",
        )
        assert phone.canonical_form == "+15551234"


class TestNameModel:
    """Tests for Name model."""

    def test_name_with_given_and_family(self) -> None:
        """Should create Name with given and family names."""
        name = Name(given_name="John", family_name="Doe")
        assert name.given_name == "John"
        assert name.family_name == "Doe"

    def test_name_with_display_name(self) -> None:
        """Should create Name with display name."""
        name = Name(display_name="John Doe")
        assert name.display_name == "John Doe"

    def test_name_with_all_fields(self) -> None:
        """Should create Name with all fields."""
        name = Name(
            given_name="John",
            family_name="Doe",
            middle_name="Michael",
            prefix="Dr.",
            suffix="Jr.",
            display_name="Dr. John Michael Doe Jr.",
        )
        assert name.prefix == "Dr."
        assert name.suffix == "Jr."
        assert name.middle_name == "Michael"


class TestPostalAddressModel:
    """Tests for PostalAddress model."""

    def test_postal_address_creation(self) -> None:
        """Should create PostalAddress."""
        address = PostalAddress(
            street_address="123 Main St",
            city="Springfield",
            region="IL",
            postal_code="62701",
        )
        assert address.street_address == "123 Main St"
        assert address.city == "Springfield"

    def test_postal_address_with_country(self) -> None:
        """Should create PostalAddress with country."""
        address = PostalAddress(
            formatted_value="123 Main St, Springfield, IL 62701, USA",
            country="United States",
            country_code="US",
        )
        assert address.country == "United States"
        assert address.country_code == "US"


class TestOrganizationModel:
    """Tests for Organization model."""

    def test_organization_creation(self) -> None:
        """Should create Organization with name."""
        org = Organization(name="Acme Corp")
        assert org.name == "Acme Corp"

    def test_organization_with_title(self) -> None:
        """Should create Organization with title."""
        org = Organization(name="Acme Corp", title="Senior Developer")
        assert org.title == "Senior Developer"

    def test_organization_with_dates(self) -> None:
        """Should create Organization with start/end dates."""
        org = Organization(
            name="Acme Corp",
            title="Developer",
            start_date={"year": 2020},
            current=True,
        )
        assert org.current is True
        assert org.start_date is not None


class TestContactModel:
    """Tests for Contact model."""

    def test_contact_minimal_creation(self) -> None:
        """Should create Contact with minimal data."""
        contact = Contact(resource_name="people/c123")
        assert contact.resource_name == "people/c123"

    def test_contact_with_names(self) -> None:
        """Should create Contact with names."""
        contact = Contact(
            resource_name="people/c123",
            names=[Name(given_name="John", family_name="Doe")],
        )
        assert len(contact.names) == 1
        assert contact.names[0].given_name == "John"

    def test_contact_with_all_fields(self) -> None:
        """Should create Contact with all fields."""
        contact = Contact(
            resource_name="people/c123",
            etag="tag123",
            names=[Name(given_name="John", family_name="Doe")],
            email_addresses=[EmailAddress(value="john@example.com")],
            phone_numbers=[PhoneNumber(value="+1-555-1234")],
            addresses=[
                PostalAddress(
                    street_address="123 Main",
                    city="Springfield",
                )
            ],
            organizations=[Organization(name="Acme Corp")],
        )
        assert contact.etag == "tag123"
        assert len(contact.names) == 1
        assert len(contact.email_addresses) == 1
        assert len(contact.phone_numbers) == 1
        assert len(contact.addresses) == 1
        assert len(contact.organizations) == 1


class TestContactGroupModel:
    """Tests for ContactGroup model."""

    def test_contact_group_creation(self) -> None:
        """Should create ContactGroup with name."""
        group = ContactGroup(name="Friends")
        assert group.name == "Friends"

    def test_contact_group_with_all_fields(self) -> None:
        """Should create ContactGroup with all fields."""
        group = ContactGroup(
            resource_name="contactGroups/c123",
            name="Friends",
            group_type="USER_CONTACT_GROUP",
            member_count=5,
            member_resource_names=["people/p1", "people/p2"],
        )
        assert group.resource_name == "contactGroups/c123"
        assert group.member_count == 5
        assert len(group.member_resource_names) == 2


class TestContactsListResponseModel:
    """Tests for ContactsListResponse model."""

    def test_contacts_list_response_empty(self) -> None:
        """Should create empty ContactsListResponse."""
        response = ContactsListResponse()
        assert response.connections is None

    def test_contacts_list_response_with_contacts(self) -> None:
        """Should create ContactsListResponse with contacts."""
        contacts = [
            Contact(
                resource_name="people/c1",
                names=[Name(given_name="John")],
            ),
            Contact(
                resource_name="people/c2",
                names=[Name(given_name="Jane")],
            ),
        ]
        response = ContactsListResponse(connections=contacts)
        assert len(response.connections) == 2

    def test_contacts_list_response_with_pagination(self) -> None:
        """Should create ContactsListResponse with pagination tokens."""
        response = ContactsListResponse(
            next_page_token="token123",
            next_sync_token="sync456",
        )
        assert response.next_page_token == "token123"
        assert response.next_sync_token == "sync456"


class TestContactGroupsListResponseModel:
    """Tests for ContactGroupsListResponse model."""

    def test_contact_groups_list_response_empty(self) -> None:
        """Should create empty ContactGroupsListResponse."""
        response = ContactGroupsListResponse()
        assert response.contact_groups is None

    def test_contact_groups_list_response_with_groups(self) -> None:
        """Should create ContactGroupsListResponse with groups."""
        groups = [
            ContactGroup(name="Friends"),
            ContactGroup(name="Family"),
        ]
        response = ContactGroupsListResponse(contact_groups=groups)
        assert len(response.contact_groups) == 2


class TestContactCreateRequestModel:
    """Tests for ContactCreateRequest model."""

    def test_contact_create_request_minimal(self) -> None:
        """Should create ContactCreateRequest with minimal data."""
        request = ContactCreateRequest(given_name="John")
        assert request.given_name == "John"
        assert request.email_type == "work"

    def test_contact_create_request_with_all_fields(self) -> None:
        """Should create ContactCreateRequest with all fields."""
        request = ContactCreateRequest(
            given_name="John",
            family_name="Doe",
            email_address="john@example.com",
            phone_number="+1-555-1234",
            organization_name="Acme Corp",
            job_title="Developer",
        )
        assert request.family_name == "Doe"
        assert request.email_address == "john@example.com"
        assert request.organization_name == "Acme Corp"


class TestContactUpdateRequestModel:
    """Tests for ContactUpdateRequest model."""

    def test_contact_update_request_creation(self) -> None:
        """Should create ContactUpdateRequest with resource name."""
        request = ContactUpdateRequest(resource_name="people/c123")
        assert request.resource_name == "people/c123"

    def test_contact_update_request_with_updates(self) -> None:
        """Should create ContactUpdateRequest with update fields."""
        request = ContactUpdateRequest(
            resource_name="people/c123",
            given_name="Janet",
            family_name="Smith",
            email_address="janet@example.com",
        )
        assert request.given_name == "Janet"
        assert request.email_address == "janet@example.com"


class TestModelJsonSerialization:
    """Tests for JSON serialization of models."""

    def test_contact_to_dict(self) -> None:
        """Should convert Contact to dict."""
        contact = Contact(
            resource_name="people/c123",
            names=[Name(given_name="John", family_name="Doe")],
        )
        contact_dict = contact.model_dump()
        assert contact_dict["resource_name"] == "people/c123"
        assert contact_dict["names"][0]["given_name"] == "John"

    def test_contact_group_to_json(self) -> None:
        """Should convert ContactGroup to JSON."""
        group = ContactGroup(name="Friends")
        group_json = group.model_dump_json()
        assert "Friends" in group_json
        assert "name" in group_json
