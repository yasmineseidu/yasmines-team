"""Unit tests for Cal.com models."""

from datetime import datetime

from src.integrations.cal_com.models import (
    Availability,
    BookingConfirmation,
    CalComEvent,
    EventType,
    Team,
    User,
)


class TestUserModel:
    """Test User model."""

    def test_user_creation(self) -> None:
        """Test creating user model."""
        user = User(
            id="user_123",
            email="test@example.com",
            name="Test User",
            username="testuser",
            timezone="UTC",
            locale="en-US",
            created_at=datetime.now(),
        )
        assert user.id == "user_123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_user_with_minimal_fields(self) -> None:
        """Test creating user with only required fields."""
        now = datetime.now()
        user = User(
            id="user_123",
            email="test@example.com",
            name="Test",
            username="test",
            timezone="UTC",
            created_at=now,
        )
        assert user.locale is None


class TestEventTypeModel:
    """Test EventType model."""

    def test_event_type_creation(self) -> None:
        """Test creating event type model."""
        et = EventType(
            id="evt_123",
            title="1:1 Meeting",
            slug="1-1-meeting",
            description="One on one",
            length=30,
            owner_id="user_123",
            is_active=True,
            scheduling_type="collective",
        )
        assert et.id == "evt_123"
        assert et.length == 30
        assert et.is_active

    def test_event_type_defaults(self) -> None:
        """Test EventType with default values."""
        et = EventType(
            id="evt_123",
            title="Meeting",
            slug="meeting",
            length=60,
            owner_id="user_123",
        )
        assert et.is_active is True
        assert et.scheduling_type == "collective"


class TestCalComEventModel:
    """Test CalComEvent model."""

    def test_event_creation(self) -> None:
        """Test creating event model."""
        now = datetime.now()
        event = CalComEvent(
            id="evt_123",
            title="Team Meeting",
            description="Weekly sync",
            start_time=now,
            end_time=now,
            location="Zoom",
            organizer_id="user_123",
            attendees=["user@example.com"],
            event_type_id="evt_type_123",
            status="confirmed",
            created_at=now,
            updated_at=now,
        )
        assert event.id == "evt_123"
        assert event.title == "Team Meeting"
        assert len(event.attendees) == 1

    def test_event_with_defaults(self) -> None:
        """Test CalComEvent with default values."""
        now = datetime.now()
        event = CalComEvent(
            id="evt_123",
            title="Meeting",
            start_time=now,
            end_time=now,
            organizer_id="user_123",
            created_at=now,
            updated_at=now,
        )
        assert event.status == "confirmed"
        assert event.attendees == []


class TestTeamModel:
    """Test Team model."""

    def test_team_creation(self) -> None:
        """Test creating team model."""
        team = Team(
            id="team_123",
            name="Engineering",
            slug="engineering",
            logo="https://example.com/logo.png",
            bio="Our team",
            members=["user_1", "user_2"],
        )
        assert team.id == "team_123"
        assert team.name == "Engineering"
        assert len(team.members) == 2

    def test_team_with_defaults(self) -> None:
        """Test Team with default values."""
        team = Team(
            id="team_123",
            name="Sales",
            slug="sales",
        )
        assert team.logo is None
        assert team.bio is None
        assert team.members == []


class TestAvailabilityModel:
    """Test Availability model."""

    def test_availability_creation(self) -> None:
        """Test creating availability model."""
        now = datetime.now()
        avail = Availability(
            user_id="user_123",
            start_time=now,
            end_time=now,
            is_available=True,
        )
        assert avail.user_id == "user_123"
        assert avail.is_available is True

    def test_availability_not_available(self) -> None:
        """Test availability when not available."""
        now = datetime.now()
        avail = Availability(
            user_id="user_123",
            start_time=now,
            end_time=now,
            is_available=False,
        )
        assert avail.is_available is False


class TestBookingConfirmationModel:
    """Test BookingConfirmation model."""

    def test_booking_confirmation_creation(self) -> None:
        """Test creating booking confirmation model."""
        now = datetime.now()
        conf = BookingConfirmation(
            event_id="evt_123",
            booking_id="booking_123",
            confirmed_at=now,
            confirmation_url="https://example.com/confirm",
        )
        assert conf.event_id == "evt_123"
        assert conf.booking_id == "booking_123"
        assert conf.confirmation_url is not None

    def test_booking_confirmation_minimal(self) -> None:
        """Test BookingConfirmation with minimal fields."""
        now = datetime.now()
        conf = BookingConfirmation(
            event_id="evt_123",
            booking_id="booking_123",
            confirmed_at=now,
        )
        assert conf.confirmation_url is None
