"""Unit tests for Lead Enrichment Waterfall orchestrator."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.lead_enrichment import (
    EnrichmentResult,
    EnrichmentSource,
    LeadEnrichmentWaterfall,
    ServiceStats,
    WaterfallStats,
)


class TestLeadEnrichmentWaterfallInitialization:
    """Tests for LeadEnrichmentWaterfall initialization."""

    def test_waterfall_initializes_with_no_keys(self) -> None:
        """Waterfall should initialize with no configured services."""
        waterfall = LeadEnrichmentWaterfall()
        assert len(waterfall._clients) == 0

    def test_waterfall_initializes_with_single_key(self) -> None:
        """Waterfall should initialize with single service key."""
        waterfall = LeadEnrichmentWaterfall(anymailfinder_key="test-key")
        assert EnrichmentSource.ANYMAILFINDER in waterfall._clients

    def test_waterfall_initializes_with_all_keys(self) -> None:
        """Waterfall should initialize with all service keys."""
        waterfall = LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            findymail_key="key2",
            tomba_key="key3",
            tomba_secret="secret3",  # pragma: allowlist secret
            voilanorbert_key="key4",
            icypeas_key="key5",
            muraena_key="key6",
            nimbler_key="key7",
            mailverify_key="key8",
        )
        assert len(waterfall._clients) == 8

    def test_tomba_requires_both_key_and_secret(self) -> None:
        """Tomba should only be configured if both key and secret provided."""
        waterfall = LeadEnrichmentWaterfall(tomba_key="key")
        assert EnrichmentSource.TOMBA not in waterfall._clients

        waterfall = LeadEnrichmentWaterfall(
            tomba_key="key",
            tomba_secret="secret",  # pragma: allowlist secret
        )
        assert EnrichmentSource.TOMBA in waterfall._clients

    def test_default_settings(self) -> None:
        """Should have correct default settings."""
        waterfall = LeadEnrichmentWaterfall()
        assert waterfall.verify_results is True
        assert waterfall.cache_enabled is True
        assert waterfall.cache_ttl_days == 30

    def test_custom_settings(self) -> None:
        """Should accept custom settings."""
        waterfall = LeadEnrichmentWaterfall(
            verify_results=False,
            cache_enabled=False,
            cache_ttl_days=7,
        )
        assert waterfall.verify_results is False
        assert waterfall.cache_enabled is False
        assert waterfall.cache_ttl_days == 7


class TestFindEmail:
    """Tests for LeadEnrichmentWaterfall.find_email()."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall fixture with mocked clients."""
        waterfall = LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            findymail_key="key2",
            verify_results=False,
        )
        return waterfall

    @pytest.mark.asyncio
    async def test_find_email_success_first_service(
        self, waterfall: LeadEnrichmentWaterfall
    ) -> None:
        """find_email should return on first successful service."""
        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            result = await waterfall.find_email(
                first_name="John", last_name="Smith", domain="company.com"
            )

            assert result.found is True
            assert result.email == "john@company.com"
            assert result.source == EnrichmentSource.ANYMAILFINDER
            assert len(result.services_tried) == 1

    @pytest.mark.asyncio
    async def test_find_email_cascades_on_failure(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """find_email should cascade to next service on failure."""
        # First service returns no result
        mock_result_empty = MagicMock()
        mock_result_empty.found = False

        # Second service returns result
        mock_result_found = MagicMock()
        mock_result_found.is_valid = True
        mock_result_found.email = "john@company.com"

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_first:
            mock_first.return_value = mock_result_empty

            with patch.object(
                waterfall._clients[EnrichmentSource.FINDYMAIL],
                "find_work_email",
                new_callable=AsyncMock,
            ) as mock_second:
                mock_second.return_value = mock_result_found

                result = await waterfall.find_email(
                    first_name="John", last_name="Smith", domain="company.com"
                )

                assert result.found is True
                assert result.source == EnrichmentSource.FINDYMAIL
                assert len(result.services_tried) == 2

    @pytest.mark.asyncio
    async def test_find_email_not_found(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """find_email should return NOT_FOUND when all services fail."""
        mock_result_empty = MagicMock()
        mock_result_empty.found = False
        mock_result_empty.is_valid = False

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_first:
            mock_first.return_value = mock_result_empty

            with patch.object(
                waterfall._clients[EnrichmentSource.FINDYMAIL],
                "find_work_email",
                new_callable=AsyncMock,
            ) as mock_second:
                mock_second.return_value = mock_result_empty

                result = await waterfall.find_email(
                    first_name="John", last_name="Smith", domain="company.com"
                )

                assert result.found is False
                assert result.source == EnrichmentSource.NOT_FOUND
                assert result.email is None

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_first_name(
        self, waterfall: LeadEnrichmentWaterfall
    ) -> None:
        """find_email should raise ValueError if first_name is missing."""
        with pytest.raises(ValueError, match="first_name is required"):
            await waterfall.find_email(first_name="", last_name="Smith", domain="company.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_last_name(
        self, waterfall: LeadEnrichmentWaterfall
    ) -> None:
        """find_email should raise ValueError if last_name is missing."""
        with pytest.raises(ValueError, match="last_name is required"):
            await waterfall.find_email(first_name="John", last_name="", domain="company.com")

    @pytest.mark.asyncio
    async def test_find_email_raises_on_missing_domain_and_company(
        self, waterfall: LeadEnrichmentWaterfall
    ) -> None:
        """find_email should raise ValueError if domain and company missing."""
        with pytest.raises(ValueError, match="Either domain or company is required"):
            await waterfall.find_email(first_name="John", last_name="Smith")

    @pytest.mark.asyncio
    async def test_find_email_accepts_company_instead_of_domain(
        self, waterfall: LeadEnrichmentWaterfall
    ) -> None:
        """find_email should accept company when domain is not provided."""
        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            result = await waterfall.find_email(
                first_name="John", last_name="Smith", company="Company Inc"
            )

            assert result.found is True

    @pytest.mark.asyncio
    async def test_find_email_skip_services(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """find_email should skip specified services."""
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.email = "john@company.com"

        with patch.object(
            waterfall._clients[EnrichmentSource.FINDYMAIL],
            "find_work_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            result = await waterfall.find_email(
                first_name="John",
                last_name="Smith",
                domain="company.com",
                skip_services=[EnrichmentSource.ANYMAILFINDER],
            )

            # Anymailfinder should not be in services_tried
            assert EnrichmentSource.ANYMAILFINDER not in result.services_tried
            assert result.source == EnrichmentSource.FINDYMAIL


class TestCaching:
    """Tests for result caching."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall with caching enabled."""
        return LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            cache_enabled=True,
            verify_results=False,
        )

    @pytest.mark.asyncio
    async def test_cache_hit(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """Should return cached result on second lookup."""
        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            # First call
            await waterfall.find_email(first_name="John", last_name="Smith", domain="company.com")

            # Second call - should use cache
            result2 = await waterfall.find_email(
                first_name="John", last_name="Smith", domain="company.com"
            )

            # find_person_email should only be called once
            assert mock_find.call_count == 1
            assert result2.source == EnrichmentSource.CACHE
            assert result2.email == "john@company.com"

    @pytest.mark.asyncio
    async def test_cache_disabled(self) -> None:
        """Should not cache when caching is disabled."""
        waterfall = LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            cache_enabled=False,
            verify_results=False,
        )

        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            await waterfall.find_email(first_name="John", last_name="Smith", domain="company.com")
            await waterfall.find_email(first_name="John", last_name="Smith", domain="company.com")

            # Should be called twice since caching is disabled
            assert mock_find.call_count == 2

    def test_cache_key_generation(self) -> None:
        """Should generate consistent cache keys."""
        waterfall = LeadEnrichmentWaterfall()

        key1 = waterfall._get_cache_key("John", "Smith", "company.com", None)
        key2 = waterfall._get_cache_key("john", "smith", "company.com", None)
        key3 = waterfall._get_cache_key("John", "Smith", None, "Company Inc")

        # Keys should be case-insensitive
        assert key1 == key2
        # Keys should differ by company/domain
        assert key1 != key3

    def test_clear_cache(self) -> None:
        """Should clear all cached results."""
        waterfall = LeadEnrichmentWaterfall()
        waterfall._cache["test:key"] = (MagicMock(), datetime.now())

        waterfall.clear_cache()

        assert len(waterfall._cache) == 0


class TestStatistics:
    """Tests for statistics tracking."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall fixture."""
        return LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            verify_results=False,
        )

    @pytest.mark.asyncio
    async def test_stats_track_requests(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """Should track total requests."""
        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            await waterfall.find_email(first_name="John", last_name="Smith", domain="company.com")

            stats = waterfall.get_stats()
            assert stats.total_requests == 1
            assert stats.total_found == 1

    @pytest.mark.asyncio
    async def test_stats_track_not_found(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """Should track not found results."""
        mock_result = MagicMock()
        mock_result.found = False

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            await waterfall.find_email(first_name="John", last_name="Smith", domain="company.com")

            stats = waterfall.get_stats()
            assert stats.total_not_found == 1

    def test_reset_stats(self) -> None:
        """Should reset all statistics."""
        waterfall = LeadEnrichmentWaterfall()
        waterfall._stats.total_requests = 100
        waterfall._stats.total_found = 50

        waterfall.reset_stats()

        assert waterfall._stats.total_requests == 0
        assert waterfall._stats.total_found == 0


class TestServiceStats:
    """Tests for ServiceStats dataclass."""

    def test_success_rate_calculation(self) -> None:
        """Should calculate correct success rate."""
        stats = ServiceStats(
            name="test",
            requests=100,
            successes=75,
            failures=25,
        )
        assert stats.success_rate == 0.75

    def test_success_rate_zero_requests(self) -> None:
        """Should handle zero requests."""
        stats = ServiceStats(name="test", requests=0)
        assert stats.success_rate == 0.0


class TestWaterfallStats:
    """Tests for WaterfallStats dataclass."""

    def test_overall_success_rate(self) -> None:
        """Should calculate overall success rate."""
        stats = WaterfallStats(
            total_requests=100,
            total_found=80,
            total_not_found=20,
        )
        assert stats.overall_success_rate == 0.8

    def test_overall_success_rate_zero_requests(self) -> None:
        """Should handle zero requests."""
        stats = WaterfallStats(total_requests=0)
        assert stats.overall_success_rate == 0.0


class TestEnrichmentResultProperties:
    """Tests for EnrichmentResult properties."""

    def test_found_true(self) -> None:
        """found should be True when email exists."""
        result = EnrichmentResult(
            email="test@company.com",
            source=EnrichmentSource.ANYMAILFINDER,
            confidence=0.9,
            is_verified=True,
            first_name="Test",
            last_name="User",
            domain="company.com",
            company=None,
            phone=None,
            services_tried=[EnrichmentSource.ANYMAILFINDER],
            total_cost=1.0,
            duration_ms=100,
            raw_responses={},
        )
        assert result.found is True

    def test_found_false_not_found_source(self) -> None:
        """found should be False when source is NOT_FOUND."""
        result = EnrichmentResult(
            email=None,
            source=EnrichmentSource.NOT_FOUND,
            confidence=0.0,
            is_verified=False,
            first_name="Test",
            last_name="User",
            domain="company.com",
            company=None,
            phone=None,
            services_tried=[],
            total_cost=0.0,
            duration_ms=100,
            raw_responses={},
        )
        assert result.found is False

    def test_is_high_confidence_true(self) -> None:
        """is_high_confidence should be True for confidence >= 0.8."""
        result = EnrichmentResult(
            email="test@company.com",
            source=EnrichmentSource.ANYMAILFINDER,
            confidence=0.85,
            is_verified=True,
            first_name=None,
            last_name=None,
            domain=None,
            company=None,
            phone=None,
            services_tried=[],
            total_cost=0.0,
            duration_ms=0,
            raw_responses={},
        )
        assert result.is_high_confidence is True

    def test_is_high_confidence_false(self) -> None:
        """is_high_confidence should be False for confidence < 0.8."""
        result = EnrichmentResult(
            email="test@company.com",
            source=EnrichmentSource.ANYMAILFINDER,
            confidence=0.7,
            is_verified=False,
            first_name=None,
            last_name=None,
            domain=None,
            company=None,
            phone=None,
            services_tried=[],
            total_cost=0.0,
            duration_ms=0,
            raw_responses={},
        )
        assert result.is_high_confidence is False


class TestBatchProcessing:
    """Tests for batch email finding."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall fixture."""
        return LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            verify_results=False,
            cache_enabled=False,
        )

    @pytest.mark.asyncio
    async def test_find_emails_batch(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """Should process multiple leads in batch."""
        mock_result = MagicMock()
        mock_result.found = True
        mock_result.email = "john@company.com"
        mock_result.is_verified = True

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_result

            leads = [
                {"first_name": "John", "last_name": "Smith", "domain": "company1.com"},
                {"first_name": "Jane", "last_name": "Doe", "domain": "company2.com"},
            ]

            results = await waterfall.find_emails_batch(leads, concurrency=2)

            assert len(results) == 2
            assert all(r.found for r in results)


class TestHealthCheck:
    """Tests for health check."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall fixture."""
        return LeadEnrichmentWaterfall(anymailfinder_key="key1")

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """health_check should return healthy when all services are up."""
        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "health_check",
            new_callable=AsyncMock,
        ) as mock_health:
            mock_health.return_value = {"healthy": True}

            result = await waterfall.health_check()

            assert result["healthy"] is True
            assert "services" in result

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_service(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """health_check should return unhealthy if any service is down."""
        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "health_check",
            new_callable=AsyncMock,
        ) as mock_health:
            mock_health.return_value = {"healthy": False, "error": "Connection failed"}

            result = await waterfall.health_check()

            assert result["healthy"] is False


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_clients(self) -> None:
        """Context manager should close all clients on exit."""
        waterfall = LeadEnrichmentWaterfall(anymailfinder_key="key1")

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "close",
            new_callable=AsyncMock,
        ) as mock_close:
            async with waterfall:
                pass

            mock_close.assert_called_once()


class TestEmailVerification:
    """Tests for email verification during waterfall."""

    @pytest.fixture
    def waterfall(self) -> LeadEnrichmentWaterfall:
        """Create waterfall with verification enabled."""
        return LeadEnrichmentWaterfall(
            anymailfinder_key="key1",
            mailverify_key="key2",
            verify_results=True,
        )

    @pytest.mark.asyncio
    async def test_verifies_unverified_email(self, waterfall: LeadEnrichmentWaterfall) -> None:
        """Should verify email when not already verified."""
        mock_email_result = MagicMock()
        mock_email_result.found = True
        mock_email_result.email = "john@company.com"
        mock_email_result.is_verified = False

        mock_verify_result = MagicMock()
        mock_verify_result.is_valid = True
        mock_verify_result.is_deliverable = True
        mock_verify_result.is_catch_all = False

        with patch.object(
            waterfall._clients[EnrichmentSource.ANYMAILFINDER],
            "find_person_email",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = mock_email_result

            with patch.object(
                waterfall._clients[EnrichmentSource.MAILVERIFY],
                "verify_email",
                new_callable=AsyncMock,
            ) as mock_verify:
                mock_verify.return_value = mock_verify_result

                result = await waterfall.find_email(
                    first_name="John", last_name="Smith", domain="company.com"
                )

                mock_verify.assert_called_once_with("john@company.com")
                assert result.is_verified is True


class TestEnrichmentSource:
    """Tests for EnrichmentSource enum."""

    def test_all_sources_defined(self) -> None:
        """Should have all expected sources."""
        sources = [
            EnrichmentSource.ANYMAILFINDER,
            EnrichmentSource.FINDYMAIL,
            EnrichmentSource.TOMBA,
            EnrichmentSource.VOILANORBERT,
            EnrichmentSource.ICYPEAS,
            EnrichmentSource.MURAENA,
            EnrichmentSource.NIMBLER,
            EnrichmentSource.MAILVERIFY,
            EnrichmentSource.CACHE,
            EnrichmentSource.NOT_FOUND,
        ]
        assert len(sources) == 10
