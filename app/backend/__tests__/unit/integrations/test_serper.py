"""Unit tests for Serper API integration client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.serper import (
    SerperAnswerBox,
    SerperAutocompleteResult,
    SerperClient,
    SerperError,
    SerperImageResult,
    SerperKnowledgeGraph,
    SerperNewsResult,
    SerperOrganicResult,
    SerperPeopleAlsoAsk,
    SerperPlaceResult,
    SerperRelatedSearch,
    SerperSearchResult,
    SerperSearchType,
    SerperShoppingResult,
    SerperVideoResult,
)


class TestSerperClientInitialization:
    """Tests for SerperClient initialization."""

    def test_has_correct_name(self) -> None:
        """Client should have name 'serper'."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        assert client.name == "serper"

    def test_has_correct_base_url(self) -> None:
        """Client should have correct base URL."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        assert client.base_url == "https://google.serper.dev"

    def test_stores_api_key(self) -> None:
        """Client should store API key."""
        client = SerperClient(api_key="test-api-key")  # pragma: allowlist secret
        assert client.api_key == "test-api-key"  # pragma: allowlist secret

    def test_default_timeout(self) -> None:
        """Client should have 30s default timeout."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = SerperClient(api_key="test-key", timeout=60.0)  # pragma: allowlist secret
        assert client.timeout == 60.0

    def test_default_max_retries(self) -> None:
        """Client should have 3 default max retries."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        assert client.max_retries == 3

    def test_custom_max_retries(self) -> None:
        """Client should accept custom max retries."""
        client = SerperClient(api_key="test-key", max_retries=5)  # pragma: allowlist secret
        assert client.max_retries == 5


class TestSerperClientHeaders:
    """Tests for SerperClient header generation."""

    def test_uses_x_api_key_header(self) -> None:
        """Client should use X-API-KEY header instead of Bearer token."""
        client = SerperClient(api_key="test-api-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert "X-API-KEY" in headers
        assert headers["X-API-KEY"] == "test-api-key"  # pragma: allowlist secret
        assert "Authorization" not in headers

    def test_includes_content_type(self) -> None:
        """Client should include Content-Type header."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_includes_accept_header(self) -> None:
        """Client should include Accept header."""
        client = SerperClient(api_key="test-key")  # pragma: allowlist secret
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestSerperClientSearch:
    """Tests for SerperClient.search method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_search_response(self) -> dict:
        """Sample search response with all result types."""
        return {
            "searchParameters": {
                "q": "test query",
                "gl": "us",
                "hl": "en",
                "num": 10,
            },
            "organic": [
                {
                    "position": 1,
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "This is a test snippet for result 1.",
                    "displayedLink": "example.com",
                    "date": "2024-01-15",
                    "sitelinks": [{"title": "Subpage", "link": "https://example.com/sub"}],
                },
                {
                    "position": 2,
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "This is a test snippet for result 2.",
                },
            ],
            "knowledgeGraph": {
                "title": "Test Company",
                "type": "Organization",
                "description": "A test company description.",
                "website": "https://testcompany.com",
                "imageUrl": "https://example.com/image.jpg",
                "attributes": {"Founded": "2020", "CEO": "John Doe"},
            },
            "answerBox": {
                "title": "Quick Answer",
                "snippet": "This is the direct answer to your query.",
                "link": "https://example.com/answer",
            },
            "peopleAlsoAsk": [
                {
                    "question": "What is a test?",
                    "snippet": "A test is an examination.",
                    "title": "Test Definition",
                    "link": "https://example.com/test-def",
                },
                {
                    "question": "How to run tests?",
                    "snippet": "You can run tests using pytest.",
                    "title": "Running Tests",
                    "link": "https://example.com/run-tests",
                },
            ],
            "relatedSearches": [
                {"query": "related test query 1"},
                {"query": "related test query 2"},
            ],
        }

    @pytest.mark.asyncio
    async def test_search_success(self, client: SerperClient, mock_search_response: dict) -> None:
        """Search should return parsed SerperSearchResult."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert isinstance(result, SerperSearchResult)
            assert result.query == "test query"
            assert result.search_type == SerperSearchType.SEARCH

    @pytest.mark.asyncio
    async def test_search_parses_organic_results(
        self, client: SerperClient, mock_search_response: dict
    ) -> None:
        """Search should parse organic results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert len(result.organic) == 2
            assert isinstance(result.organic[0], SerperOrganicResult)
            assert result.organic[0].position == 1
            assert result.organic[0].title == "Test Result 1"
            assert result.organic[0].link == "https://example.com/1"
            assert result.organic[0].snippet == "This is a test snippet for result 1."
            assert result.organic[0].displayed_link == "example.com"
            assert result.organic[0].date == "2024-01-15"
            assert len(result.organic[0].sitelinks) == 1

    @pytest.mark.asyncio
    async def test_search_parses_knowledge_graph(
        self, client: SerperClient, mock_search_response: dict
    ) -> None:
        """Search should parse knowledge graph correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert result.knowledge_graph is not None
            assert isinstance(result.knowledge_graph, SerperKnowledgeGraph)
            assert result.knowledge_graph.title == "Test Company"
            assert result.knowledge_graph.type == "Organization"
            assert result.knowledge_graph.description == "A test company description."
            assert result.knowledge_graph.website == "https://testcompany.com"
            assert result.knowledge_graph.attributes["CEO"] == "John Doe"

    @pytest.mark.asyncio
    async def test_search_parses_answer_box(
        self, client: SerperClient, mock_search_response: dict
    ) -> None:
        """Search should parse answer box correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert result.answer_box is not None
            assert isinstance(result.answer_box, SerperAnswerBox)
            assert result.answer_box.title == "Quick Answer"
            assert result.answer_box.snippet == "This is the direct answer to your query."
            assert result.answer_box.link == "https://example.com/answer"

    @pytest.mark.asyncio
    async def test_search_parses_people_also_ask(
        self, client: SerperClient, mock_search_response: dict
    ) -> None:
        """Search should parse people also ask correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert len(result.people_also_ask) == 2
            assert isinstance(result.people_also_ask[0], SerperPeopleAlsoAsk)
            assert result.people_also_ask[0].question == "What is a test?"
            assert result.people_also_ask[0].snippet == "A test is an examination."

    @pytest.mark.asyncio
    async def test_search_parses_related_searches(
        self, client: SerperClient, mock_search_response: dict
    ) -> None:
        """Search should parse related searches correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_search_response

            result = await client.search("test query")

            assert len(result.related_searches) == 2
            assert isinstance(result.related_searches[0], SerperRelatedSearch)
            assert result.related_searches[0].query == "related test query 1"

    @pytest.mark.asyncio
    async def test_search_sends_correct_payload(self, client: SerperClient) -> None:
        """Search should send correct payload to API."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = {"organic": []}

            await client.search(
                "test query",
                num=20,
                page=2,
                country="uk",
                language="de",
                location="London",
                time_period="qdr:w",
                safe_search=False,
            )

            call_args = mock.call_args
            payload = call_args.kwargs["json"]

            assert payload["q"] == "test query"
            assert payload["num"] == 20
            assert payload["page"] == 2
            assert payload["gl"] == "uk"
            assert payload["hl"] == "de"
            assert payload["location"] == "London"
            assert payload["tbs"] == "qdr:w"
            assert payload["safe"] == "off"

    @pytest.mark.asyncio
    async def test_search_requires_query(self, client: SerperClient) -> None:
        """Search should require non-empty query."""
        with pytest.raises(ValueError, match="query is required"):
            await client.search("")

        with pytest.raises(ValueError, match="query is required"):
            await client.search("   ")

    @pytest.mark.asyncio
    async def test_search_validates_num_range(self, client: SerperClient) -> None:
        """Search should validate num is between 1 and 100."""
        with pytest.raises(ValueError, match="num must be between 1 and 100"):
            await client.search("test", num=0)

        with pytest.raises(ValueError, match="num must be between 1 and 100"):
            await client.search("test", num=101)

    @pytest.mark.asyncio
    async def test_search_validates_page(self, client: SerperClient) -> None:
        """Search should validate page is >= 1."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            await client.search("test", page=0)

    @pytest.mark.asyncio
    async def test_search_raises_serper_error_on_failure(self, client: SerperClient) -> None:
        """Search should raise SerperError on API failure."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.side_effect = IntegrationError("API error", status_code=500)

            with pytest.raises(SerperError) as exc_info:
                await client.search("test query")

            assert "Web search failed" in str(exc_info.value)


class TestSerperClientImageSearch:
    """Tests for SerperClient.search_images method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_image_response(self) -> dict:
        """Sample image search response."""
        return {
            "searchParameters": {"q": "test images", "type": "images"},
            "images": [
                {
                    "position": 1,
                    "title": "Test Image 1",
                    "imageUrl": "https://example.com/image1.jpg",
                    "source": "Example Site",
                    "link": "https://example.com/page1",
                    "thumbnailUrl": "https://example.com/thumb1.jpg",
                },
                {
                    "position": 2,
                    "title": "Test Image 2",
                    "imageUrl": "https://example.com/image2.jpg",
                    "source": "Another Site",
                    "link": "https://example.com/page2",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_image_search_success(
        self, client: SerperClient, mock_image_response: dict
    ) -> None:
        """Image search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_image_response

            result = await client.search_images("test images")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.IMAGES
            assert len(result.images) == 2

    @pytest.mark.asyncio
    async def test_image_search_parses_results(
        self, client: SerperClient, mock_image_response: dict
    ) -> None:
        """Image search should parse image results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_image_response

            result = await client.search_images("test images")

            assert isinstance(result.images[0], SerperImageResult)
            assert result.images[0].position == 1
            assert result.images[0].title == "Test Image 1"
            assert result.images[0].image_url == "https://example.com/image1.jpg"
            assert result.images[0].source == "Example Site"
            assert result.images[0].link == "https://example.com/page1"
            assert result.images[0].thumbnail_url == "https://example.com/thumb1.jpg"

    @pytest.mark.asyncio
    async def test_image_search_calls_correct_endpoint(self, client: SerperClient) -> None:
        """Image search should call /images endpoint."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = {"images": []}

            await client.search_images("test")

            call_args = mock.call_args
            assert call_args.kwargs["endpoint"] == "/images"


class TestSerperClientNewsSearch:
    """Tests for SerperClient.search_news method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_news_response(self) -> dict:
        """Sample news search response."""
        return {
            "searchParameters": {"q": "test news", "type": "news"},
            "news": [
                {
                    "position": 1,
                    "title": "Breaking News",
                    "link": "https://news.example.com/article1",
                    "snippet": "This is a breaking news story.",
                    "source": "News Source",
                    "date": "2 hours ago",
                    "imageUrl": "https://news.example.com/image1.jpg",
                },
                {
                    "position": 2,
                    "title": "Tech News",
                    "link": "https://tech.example.com/article2",
                    "snippet": "Latest technology updates.",
                    "source": "Tech Daily",
                    "date": "1 day ago",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_news_search_success(
        self, client: SerperClient, mock_news_response: dict
    ) -> None:
        """News search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_news_response

            result = await client.search_news("test news")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.NEWS
            assert len(result.news) == 2

    @pytest.mark.asyncio
    async def test_news_search_parses_results(
        self, client: SerperClient, mock_news_response: dict
    ) -> None:
        """News search should parse news results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_news_response

            result = await client.search_news("test news")

            assert isinstance(result.news[0], SerperNewsResult)
            assert result.news[0].position == 1
            assert result.news[0].title == "Breaking News"
            assert result.news[0].source == "News Source"
            assert result.news[0].date == "2 hours ago"
            assert result.news[0].image_url == "https://news.example.com/image1.jpg"


class TestSerperClientPlacesSearch:
    """Tests for SerperClient.search_places method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_places_response(self) -> dict:
        """Sample places search response."""
        return {
            "searchParameters": {"q": "coffee shops", "type": "places"},
            "places": [
                {
                    "position": 1,
                    "title": "Best Coffee Shop",
                    "address": "123 Main St, City, ST 12345",
                    "rating": 4.5,
                    "reviewsCount": 250,
                    "phone": "+1-555-123-4567",
                    "website": "https://bestcoffee.com",
                    "category": "Coffee Shop",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
                {
                    "position": 2,
                    "title": "Cozy Cafe",
                    "address": "456 Oak Ave, City, ST 12345",
                    "rating": 4.2,
                    "reviews": 150,
                    "phoneNumber": "+1-555-987-6543",
                    "type": "Cafe",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_places_search_success(
        self, client: SerperClient, mock_places_response: dict
    ) -> None:
        """Places search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_places_response

            result = await client.search_places("coffee shops")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.PLACES
            assert len(result.places) == 2

    @pytest.mark.asyncio
    async def test_places_search_parses_results(
        self, client: SerperClient, mock_places_response: dict
    ) -> None:
        """Places search should parse place results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_places_response

            result = await client.search_places("coffee shops")

            assert isinstance(result.places[0], SerperPlaceResult)
            assert result.places[0].position == 1
            assert result.places[0].title == "Best Coffee Shop"
            assert result.places[0].address == "123 Main St, City, ST 12345"
            assert result.places[0].rating == 4.5
            assert result.places[0].reviews_count == 250
            assert result.places[0].phone == "+1-555-123-4567"
            assert result.places[0].latitude == 40.7128
            assert result.places[0].longitude == -74.0060


class TestSerperClientVideoSearch:
    """Tests for SerperClient.search_videos method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_video_response(self) -> dict:
        """Sample video search response."""
        return {
            "searchParameters": {"q": "test videos", "type": "videos"},
            "videos": [
                {
                    "position": 1,
                    "title": "Test Video Tutorial",
                    "link": "https://youtube.com/watch?v=abc123",
                    "snippet": "Learn how to test in this tutorial.",
                    "duration": "10:30",
                    "channel": "Test Channel",
                    "date": "1 month ago",
                    "thumbnailUrl": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_video_search_success(
        self, client: SerperClient, mock_video_response: dict
    ) -> None:
        """Video search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_video_response

            result = await client.search_videos("test videos")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.VIDEOS
            assert len(result.videos) == 1

    @pytest.mark.asyncio
    async def test_video_search_parses_results(
        self, client: SerperClient, mock_video_response: dict
    ) -> None:
        """Video search should parse video results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_video_response

            result = await client.search_videos("test videos")

            assert isinstance(result.videos[0], SerperVideoResult)
            assert result.videos[0].position == 1
            assert result.videos[0].title == "Test Video Tutorial"
            assert result.videos[0].duration == "10:30"
            assert result.videos[0].channel == "Test Channel"


class TestSerperClientShoppingSearch:
    """Tests for SerperClient.search_shopping method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_shopping_response(self) -> dict:
        """Sample shopping search response."""
        return {
            "searchParameters": {"q": "laptop", "type": "shopping"},
            "shopping": [
                {
                    "position": 1,
                    "title": "Gaming Laptop",
                    "link": "https://store.example.com/laptop",
                    "price": "$999.99",
                    "source": "Example Store",
                    "rating": 4.7,
                    "reviewsCount": 1200,
                    "imageUrl": "https://store.example.com/laptop.jpg",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_shopping_search_success(
        self, client: SerperClient, mock_shopping_response: dict
    ) -> None:
        """Shopping search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_shopping_response

            result = await client.search_shopping("laptop")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.SHOPPING
            assert len(result.shopping) == 1

    @pytest.mark.asyncio
    async def test_shopping_search_parses_results(
        self, client: SerperClient, mock_shopping_response: dict
    ) -> None:
        """Shopping search should parse shopping results correctly."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_shopping_response

            result = await client.search_shopping("laptop")

            assert isinstance(result.shopping[0], SerperShoppingResult)
            assert result.shopping[0].position == 1
            assert result.shopping[0].title == "Gaming Laptop"
            assert result.shopping[0].price == "$999.99"
            assert result.shopping[0].source == "Example Store"
            assert result.shopping[0].rating == 4.7


class TestSerperClientScholarSearch:
    """Tests for SerperClient.search_scholar method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_scholar_response(self) -> dict:
        """Sample scholar search response."""
        return {
            "searchParameters": {"q": "machine learning", "type": "scholar"},
            "organic": [
                {
                    "position": 1,
                    "title": "Deep Learning: A Comprehensive Survey",
                    "link": "https://arxiv.org/abs/1234.5678",
                    "snippet": "This paper surveys deep learning techniques...",
                    "publicationInfo": "Journal of AI Research, 2023",
                    "citedByCount": 500,
                    "citedByLink": "https://scholar.google.com/cited_by",
                    "relatedArticlesLink": "https://scholar.google.com/related",
                    "pdfLink": "https://arxiv.org/pdf/1234.5678.pdf",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_scholar_search_success(
        self, client: SerperClient, mock_scholar_response: dict
    ) -> None:
        """Scholar search should return parsed results."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_scholar_response

            result = await client.search_scholar("machine learning")

            assert isinstance(result, SerperSearchResult)
            assert result.search_type == SerperSearchType.SCHOLAR

    @pytest.mark.asyncio
    async def test_scholar_search_with_year_filters(self, client: SerperClient) -> None:
        """Scholar search should accept year filters."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = {"organic": []}

            await client.search_scholar("test", year_low=2020, year_high=2024)

            call_args = mock.call_args
            payload = call_args.kwargs["json"]

            assert payload["as_ylo"] == 2020
            assert payload["as_yhi"] == 2024


class TestSerperClientAutocomplete:
    """Tests for SerperClient.autocomplete method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_autocomplete_response(self) -> dict:
        """Sample autocomplete response."""
        return {
            "suggestions": [
                {"value": "test query suggestion 1"},
                {"value": "test query suggestion 2"},
                "test query suggestion 3",
            ],
        }

    @pytest.mark.asyncio
    async def test_autocomplete_success(
        self, client: SerperClient, mock_autocomplete_response: dict
    ) -> None:
        """Autocomplete should return suggestions."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_autocomplete_response

            result = await client.autocomplete("test")

            assert isinstance(result, SerperAutocompleteResult)
            assert result.query == "test"
            assert len(result.suggestions) == 3

    @pytest.mark.asyncio
    async def test_autocomplete_parses_mixed_formats(
        self, client: SerperClient, mock_autocomplete_response: dict
    ) -> None:
        """Autocomplete should handle both dict and string suggestions."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = mock_autocomplete_response

            result = await client.autocomplete("test")

            # Dict format with "value" key
            assert result.suggestions[0] == "test query suggestion 1"
            # String format
            assert result.suggestions[2] == "test query suggestion 3"


class TestSerperClientHealthCheck:
    """Tests for SerperClient.health_check method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: SerperClient) -> None:
        """Health check should return healthy status on success."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock:
            mock.return_value = SerperSearchResult(
                query="test",
                search_type=SerperSearchType.SEARCH,
            )

            result = await client.health_check()

            assert result["name"] == "serper"
            assert result["healthy"] is True
            assert result["base_url"] == "https://google.serper.dev"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: SerperClient) -> None:
        """Health check should return unhealthy status on failure."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API error")

            result = await client.health_check()

            assert result["name"] == "serper"
            assert result["healthy"] is False
            assert "error" in result


class TestSerperClientCallEndpoint:
    """Tests for SerperClient.call_endpoint method."""

    @pytest.fixture
    def client(self) -> SerperClient:
        """Create SerperClient instance for testing."""
        return SerperClient(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_call_endpoint_success(self, client: SerperClient) -> None:
        """call_endpoint should make raw API calls."""
        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.return_value = {"result": "data"}

            result = await client.call_endpoint("/custom", method="POST", json={"q": "test"})

            assert result == {"result": "data"}
            call_args = mock.call_args
            assert call_args.kwargs["endpoint"] == "/custom"
            assert call_args.kwargs["method"] == "POST"

    @pytest.mark.asyncio
    async def test_call_endpoint_raises_serper_error(self, client: SerperClient) -> None:
        """call_endpoint should raise SerperError on failure."""
        from src.integrations.base import IntegrationError

        with patch.object(client, "_request_with_retry", new_callable=AsyncMock) as mock:
            mock.side_effect = IntegrationError("Request failed", status_code=400)

            with pytest.raises(SerperError) as exc_info:
                await client.call_endpoint("/custom")

            assert "API call failed" in str(exc_info.value)


class TestSerperDataClasses:
    """Tests for Serper dataclasses."""

    def test_organic_result_raw_response(self) -> None:
        """OrganicResult should store raw response."""
        result = SerperOrganicResult(
            position=1,
            title="Test",
            link="https://example.com",
            snippet="Test snippet",
            raw={"extra": "data"},
        )
        assert result.raw["extra"] == "data"

    def test_search_result_defaults(self) -> None:
        """SearchResult should have empty defaults."""
        result = SerperSearchResult(query="test", search_type=SerperSearchType.SEARCH)
        assert result.organic == []
        assert result.knowledge_graph is None
        assert result.answer_box is None
        assert result.people_also_ask == []
        assert result.related_searches == []
        assert result.images == []
        assert result.news == []
        assert result.places == []
        assert result.videos == []
        assert result.shopping == []
        assert result.scholar == []
        assert result.credits_used == 1

    def test_autocomplete_result_defaults(self) -> None:
        """AutocompleteResult should have empty defaults."""
        result = SerperAutocompleteResult(query="test")
        assert result.suggestions == []
        assert result.raw_response == {}
