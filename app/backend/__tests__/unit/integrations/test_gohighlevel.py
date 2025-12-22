"""Unit tests for GoHighLevel CRM API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.gohighlevel import (
    Contact,
    Deal,
    GoHighLevelClient,
    GoHighLevelError,
)


class TestGoHighLevelClientInitialization:
    """Tests for GoHighLevel client initialization."""

    def test_initialization_with_valid_credentials(self) -> None:
        """Client should initialize with valid API key and location ID."""
        client = GoHighLevelClient(
            api_key="test_api_key_12345",  # pragma: allowlist secret
            location_id="location_123",
        )
        assert client.api_key == "test_api_key_12345"  # pragma: allowlist secret
        assert client.location_id == "location_123"
        assert client.name == "gohighlevel"
        assert client.base_url == "https://rest.gohighlevel.com/v1"

    def test_initialization_with_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = GoHighLevelClient(
            api_key="test_api_key",  # pragma: allowlist secret
            location_id="location_123",
            timeout=60.0,
        )
        assert client.timeout == 60.0

    def test_initialization_raises_on_empty_api_key(self) -> None:
        """Client should raise ValueError for empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            GoHighLevelClient(api_key="", location_id="location_123")

    def test_initialization_raises_on_empty_location_id(self) -> None:
        """Client should raise ValueError for empty location ID."""
        with pytest.raises(ValueError, match="Location ID cannot be empty"):
            GoHighLevelClient(
                api_key="test_api_key",  # pragma: allowlist secret
                location_id="",
            )

    def test_initialization_strips_whitespace(self) -> None:
        """Client should strip whitespace from credentials."""
        client = GoHighLevelClient(
            api_key="  test_api_key  ",  # pragma: allowlist secret
            location_id="  location_123  ",
        )
        assert client.location_id == "location_123"


class TestGoHighLevelClientHeaders:
    """Tests for HTTP headers generation."""

    def test_headers_include_authorization_and_token(self) -> None:
        """Headers should include both Authorization and X-GHL-Token."""
        client = GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_key"  # pragma: allowlist secret
        assert headers["X-GHL-Token"] == "test_key"  # pragma: allowlist secret
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestGoHighLevelClientCreateContact:
    """Tests for create_contact method."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_create_contact_minimal(self, client: GoHighLevelClient) -> None:
        """Should create contact with minimal fields."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "lastName": "Doe",
                "createdAt": "2025-12-22T00:00:00Z",
            }

            result = await client.create_contact(first_name="John", last_name="Doe")

            assert result.id == "contact_123"
            assert result.first_name == "John"
            assert result.last_name == "Doe"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_contact_with_all_fields(self, client: GoHighLevelClient) -> None:
        """Should create contact with all fields."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "status": "lead",
                "source": "api",
                "tags": ["important", "vip"],
                "customFields": {"field1": "value1"},
            }

            result = await client.create_contact(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                phone="+1234567890",
                status="lead",
                source="api",
                tags=["important", "vip"],
                custom_fields={"field1": "value1"},
            )

            assert result.id == "contact_123"
            assert result.email == "john@example.com"
            assert result.phone == "+1234567890"
            assert result.tags == ["important", "vip"]

    @pytest.mark.asyncio
    async def test_create_contact_error(self, client: GoHighLevelClient) -> None:
        """Should raise GoHighLevelError on creation failure."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")

            with pytest.raises(GoHighLevelError, match="Failed to create contact"):
                await client.create_contact(first_name="John")


class TestGoHighLevelClientGetContact:
    """Tests for get_contact method."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_get_contact_success(self, client: GoHighLevelClient) -> None:
        """Should retrieve contact by ID."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
            }

            result = await client.get_contact("contact_123")

            assert result.id == "contact_123"
            assert result.first_name == "John"
            assert result.email == "john@example.com"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_error(self, client: GoHighLevelClient) -> None:
        """Should raise GoHighLevelError if contact not found."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Not found")

            with pytest.raises(GoHighLevelError, match="Failed to get contact"):
                await client.get_contact("contact_123")


class TestGoHighLevelClientUpdateContact:
    """Tests for update_contact method."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_update_contact_success(self, client: GoHighLevelClient) -> None:
        """Should update contact fields."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "lastName": "Smith",
                "email": "john.smith@example.com",
            }

            result = await client.update_contact(
                "contact_123", lastName="Smith", email="john.smith@example.com"
            )

            assert result.id == "contact_123"
            assert result.last_name == "Smith"
            assert result.email == "john.smith@example.com"
            mock_put.assert_called_once()


class TestGoHighLevelClientTags:
    """Tests for tag operations."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_add_tag(self, client: GoHighLevelClient) -> None:
        """Should add tag to contact."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "tags": ["vip", "important"],
            }

            result = await client.add_tag("contact_123", "vip")

            assert result.id == "contact_123"
            assert "vip" in result.tags
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_tag(self, client: GoHighLevelClient) -> None:
        """Should remove tag from contact."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {
                "id": "contact_123",
                "firstName": "John",
                "tags": [],
            }

            result = await client.remove_tag("contact_123", "vip")

            assert result.id == "contact_123"
            mock_delete.assert_called_once()


class TestGoHighLevelClientDeals:
    """Tests for deal/opportunity operations."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_create_deal(self, client: GoHighLevelClient) -> None:
        """Should create deal."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "deal_123",
                "name": "Big Sale",
                "value": 10000.00,
                "status": "open",
                "contactId": "contact_123",
            }

            result = await client.create_deal(
                name="Big Sale", contact_id="contact_123", value=10000.00
            )

            assert result.id == "deal_123"
            assert result.name == "Big Sale"
            assert result.value == 10000.00
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_deal(self, client: GoHighLevelClient) -> None:
        """Should retrieve deal by ID."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "deal_123",
                "name": "Big Sale",
                "value": 10000.00,
                "status": "open",
            }

            result = await client.get_deal("deal_123")

            assert result.id == "deal_123"
            assert result.name == "Big Sale"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_deal(self, client: GoHighLevelClient) -> None:
        """Should update deal."""
        with patch.object(client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {
                "id": "deal_123",
                "name": "Big Sale",
                "value": 15000.00,
                "status": "won",
            }

            result = await client.update_deal("deal_123", value=15000.00, status="won")

            assert result.value == 15000.00
            assert result.status == "won"
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_deal(self, client: GoHighLevelClient) -> None:
        """Should delete deal."""
        with patch.object(client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            result = await client.delete_deal("deal_123")

            assert result is True
            mock_delete.assert_called_once()


class TestGoHighLevelClientListOperations:
    """Tests for list operations."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_list_contacts(self, client: GoHighLevelClient) -> None:
        """Should list contacts with pagination."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "contacts": [
                    {"id": "c1", "firstName": "John", "lastName": "Doe"},
                    {"id": "c2", "firstName": "Jane", "lastName": "Smith"},
                ],
                "total": 2,
            }

            result = await client.list_contacts(limit=100, offset=0)

            assert len(result["contacts"]) == 2
            assert result["total"] == 2
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_deals(self, client: GoHighLevelClient) -> None:
        """Should list deals with pagination."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "deals": [
                    {"id": "d1", "name": "Deal 1", "value": 1000},
                    {"id": "d2", "name": "Deal 2", "value": 2000},
                ],
                "total": 2,
            }

            result = await client.list_deals(limit=100, offset=0)

            assert len(result["deals"]) == 2
            assert result["total"] == 2
            mock_get.assert_called_once()


class TestGoHighLevelClientCommunication:
    """Tests for communication methods."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_send_email(self, client: GoHighLevelClient) -> None:
        """Should send email to contact."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "messageId": "msg_123",
            }

            result = await client.send_email(
                contact_id="contact_123", subject="Test Email", body="<p>Hello</p>"
            )

            assert result["success"] is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_sms(self, client: GoHighLevelClient) -> None:
        """Should send SMS to contact."""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "success": True,
                "messageId": "sms_123",
            }

            result = await client.send_sms(
                contact_id="contact_123", message="Hello from GoHighLevel"
            )

            assert result["success"] is True
            mock_post.assert_called_once()


class TestGoHighLevelClientHealthCheck:
    """Tests for health check method."""

    @pytest.fixture
    def client(self) -> GoHighLevelClient:
        """Create test client."""
        return GoHighLevelClient(
            api_key="test_key",  # pragma: allowlist secret
            location_id="loc_123",
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: GoHighLevelClient) -> None:
        """Health check should return healthy status."""
        with patch.object(client, "get_me", new_callable=AsyncMock) as mock_get_me:
            mock_get_me.return_value = {
                "id": "loc_123",
                "name": "My Location",
            }

            result = await client.health_check()

            assert result["healthy"] is True
            assert "My Location" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: GoHighLevelClient) -> None:
        """Health check should return unhealthy status on error."""
        with patch.object(client, "get_me", new_callable=AsyncMock) as mock_get_me:
            mock_get_me.side_effect = Exception("Connection error")

            result = await client.health_check()

            assert result["healthy"] is False


class TestGoHighLevelDataClasses:
    """Tests for data class parsing."""

    def test_contact_creation(self) -> None:
        """Contact should be created with all fields."""
        contact = Contact(
            id="c1",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["vip"],
        )

        assert contact.id == "c1"
        assert contact.first_name == "John"
        assert contact.tags == ["vip"]

    def test_deal_creation(self) -> None:
        """Deal should be created with all fields."""
        deal = Deal(
            id="d1",
            name="Big Sale",
            value=10000.00,
            status="open",
        )

        assert deal.id == "d1"
        assert deal.name == "Big Sale"
        assert deal.value == 10000.00
