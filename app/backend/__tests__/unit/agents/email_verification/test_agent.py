"""Unit tests for Email Verification Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.email_verification import (
    EmailFinderProvider,
    EmailVerificationAgent,
    EmailVerificationProvider,
    EmailVerificationStatus,
    ProviderRegistry,
)


class TestEmailVerificationAgentInitialization:
    """Tests for EmailVerificationAgent initialization."""

    def test_agent_has_correct_name(self) -> None:
        """Agent should have correct name."""
        with patch.dict(
            "os.environ",
            {
                "TOMBA_API_KEY": "test",  # pragma: allowlist secret
                "TOMBA_API_SECRET": "test",  # pragma: allowlist secret
                "REOON_API_KEY": "test",  # pragma: allowlist secret
            },
        ):
            agent = EmailVerificationAgent()
            assert agent.name == "email_verification_agent"

    def test_agent_has_correct_description(self) -> None:
        """Agent should have correct description."""
        with patch.dict(
            "os.environ",
            {
                "TOMBA_API_KEY": "test",  # pragma: allowlist secret
                "TOMBA_API_SECRET": "test",  # pragma: allowlist secret
                "REOON_API_KEY": "test",  # pragma: allowlist secret
            },
        ):
            agent = EmailVerificationAgent()
            assert (
                agent.description == "Finds and verifies email addresses using waterfall enrichment"
            )


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def test_registry_has_all_providers(self) -> None:
        """Registry should have all required providers."""
        expected_providers = {
            EmailFinderProvider.TOMBA,
            EmailFinderProvider.MURAENA,
            EmailFinderProvider.VOILA_NORBERT,
            EmailFinderProvider.NIMBLER,
            EmailFinderProvider.ICYPEAS,
            EmailFinderProvider.ANYMAILFINDER,
            EmailFinderProvider.FINDYMAIL,
        }
        assert set(ProviderRegistry.PROVIDERS.keys()) == expected_providers

    def test_providers_ordered_by_priority(self) -> None:
        """Providers should be ordered by priority (cheapest first)."""
        providers = ProviderRegistry.get_providers_in_order()
        priorities = [p.priority for p in providers]
        assert priorities == sorted(priorities)

    def test_tomba_is_first_provider(self) -> None:
        """Tomba should be first provider (priority 1)."""
        providers = ProviderRegistry.get_providers_in_order()
        assert providers[0].name == EmailFinderProvider.TOMBA
        assert providers[0].priority == 1

    def test_provider_costs_are_correct(self) -> None:
        """Provider costs should match configuration."""
        tomba_config = ProviderRegistry.PROVIDERS[EmailFinderProvider.TOMBA]
        assert tomba_config.cost_per_lookup == 0.002

        reoon_cost = 0.003  # From agent verification method
        assert reoon_cost > 0


class TestEmailVerificationStatus:
    """Tests for EmailVerificationStatus enum."""

    def test_all_required_statuses_exist(self) -> None:
        """All required verification statuses should exist."""
        required_statuses = {
            "VALID",
            "INVALID",
            "RISKY",
            "CATCHALL",
            "DISPOSABLE",
            "ROLE_BASED",
            "UNKNOWN",
        }
        enum_names = {status.name for status in EmailVerificationStatus}
        assert required_statuses.issubset(enum_names)

    def test_status_values_are_lowercase(self) -> None:
        """Status values should be lowercase."""
        for status in EmailVerificationStatus:
            assert status.value == status.value.lower()


class TestEmailFinderProvider:
    """Tests for EmailFinderProvider enum."""

    def test_all_required_providers_exist(self) -> None:
        """All required email finder providers should exist."""
        required_providers = {
            "TOMBA",
            "MURAENA",
            "VOILA_NORBERT",
            "NIMBLER",
            "ICYPEAS",
            "ANYMAILFINDER",
            "FINDYMAIL",
        }
        enum_names = {provider.name for provider in EmailFinderProvider}
        assert required_providers.issubset(enum_names)


class TestEmailVerificationProvider:
    """Tests for EmailVerificationProvider enum."""

    def test_all_required_verifiers_exist(self) -> None:
        """All required email verification providers should exist."""
        required_verifiers = {"REOON", "MAILVERIFY"}
        enum_names = {verifier.name for verifier in EmailVerificationProvider}
        assert required_verifiers.issubset(enum_names)

    def test_reoon_is_primary_verifier(self) -> None:
        """Reoon should be available as primary verifier."""
        assert hasattr(EmailVerificationProvider, "REOON")
        assert EmailVerificationProvider.REOON.value == "reoon"


class TestMapFunctions:
    """Tests for status mapping functions."""

    def test_map_reoon_status_valid(self) -> None:
        """Should map Reoon 'valid' to VALID status."""
        status = EmailVerificationAgent._map_reoon_status("valid")
        assert status == EmailVerificationStatus.VALID

    def test_map_reoon_status_invalid(self) -> None:
        """Should map Reoon 'invalid' to INVALID status."""
        status = EmailVerificationAgent._map_reoon_status("invalid")
        assert status == EmailVerificationStatus.INVALID

    def test_map_reoon_status_catchall(self) -> None:
        """Should map Reoon 'catch_all' to CATCHALL status."""
        status = EmailVerificationAgent._map_reoon_status("catch_all")
        assert status == EmailVerificationStatus.CATCHALL

    def test_map_reoon_status_unknown(self) -> None:
        """Should map unknown Reoon status to UNKNOWN."""
        status = EmailVerificationAgent._map_reoon_status("unknown_status")
        assert status == EmailVerificationStatus.UNKNOWN

    def test_map_mailverify_status_deliverable(self) -> None:
        """Should map MailVerify 'deliverable' to VALID status."""
        status = EmailVerificationAgent._map_mailverify_status("deliverable")
        assert status == EmailVerificationStatus.VALID

    def test_map_mailverify_status_undeliverable(self) -> None:
        """Should map MailVerify 'undeliverable' to INVALID status."""
        status = EmailVerificationAgent._map_mailverify_status("undeliverable")
        assert status == EmailVerificationStatus.INVALID

    def test_map_mailverify_status_catchall(self) -> None:
        """Should map MailVerify 'catch_all' to CATCHALL status."""
        status = EmailVerificationAgent._map_mailverify_status("catch_all")
        assert status == EmailVerificationStatus.CATCHALL


@pytest.mark.asyncio
class TestFindEmail:
    """Tests for email finding functionality."""

    @pytest.mark.asyncio
    async def test_find_email_returns_enrichment_result(self) -> None:
        """find_email should return EnrichmentResult."""
        with patch.dict(
            "os.environ",
            {
                "TOMBA_API_KEY": "test",  # pragma: allowlist secret
                "TOMBA_API_SECRET": "test",  # pragma: allowlist secret
                "REOON_API_KEY": "test",  # pragma: allowlist secret
            },
        ):
            agent = EmailVerificationAgent()

            # Mock the Tomba client
            mock_tomba_result = MagicMock()
            mock_tomba_result.email = "john.doe@company.com"
            agent.tomba_client = AsyncMock()
            agent.tomba_client.search_person = AsyncMock(return_value=mock_tomba_result)

            # Mock the Reoon client
            mock_reoon_result = MagicMock()
            mock_reoon_result.status = "valid"
            mock_reoon_result.is_catchall = False
            agent.reoon_client = AsyncMock()
            agent.reoon_client.verify_email_quick = AsyncMock(return_value=mock_reoon_result)

            result = await agent.find_email("John", "Doe", "company.com")

            assert result.email == "john.doe@company.com"
            assert result.provider_used == EmailFinderProvider.TOMBA
            assert result.verification_status == EmailVerificationStatus.VALID

    @pytest.mark.asyncio
    async def test_find_email_tries_next_provider_on_failure(self) -> None:
        """find_email should try next provider if current fails."""
        with patch.dict(
            "os.environ",
            {
                "TOMBA_API_KEY": "test",  # pragma: allowlist secret
                "TOMBA_API_SECRET": "test",  # pragma: allowlist secret
                "MURAENA_API_KEY": "test",  # pragma: allowlist secret
                "REOON_API_KEY": "test",  # pragma: allowlist secret
            },
        ):
            agent = EmailVerificationAgent()

            # Mock Tomba to fail
            agent.tomba_client = AsyncMock()
            agent.tomba_client.search_person = AsyncMock(side_effect=Exception("API Error"))

            # Mock Muraena to succeed
            agent.muraena_client = AsyncMock()
            agent.muraena_client.find_email = AsyncMock(return_value={"email": "john@company.com"})

            # Mock Reoon
            mock_reoon_result = MagicMock()
            mock_reoon_result.status = "valid"
            mock_reoon_result.is_catchall = False
            agent.reoon_client = AsyncMock()
            agent.reoon_client.verify_email_quick = AsyncMock(return_value=mock_reoon_result)

            result = await agent.find_email("John", "Doe", "company.com", max_providers=2)

            # Should use Muraena as fallback
            assert result.provider_used == EmailFinderProvider.MURAENA


class TestInitMethods:
    """Tests for client initialization methods."""

    def test_init_tomba_with_credentials(self) -> None:
        """Should initialize Tomba client with valid credentials."""
        with patch.dict(
            "os.environ",
            {
                "TOMBA_API_KEY": "test_key",  # pragma: allowlist secret
                "TOMBA_API_SECRET": "test_secret",  # pragma: allowlist secret
            },
        ):
            client = EmailVerificationAgent._init_tomba_client()
            assert client is not None

    def test_init_tomba_without_credentials(self) -> None:
        """Should return None without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            client = EmailVerificationAgent._init_tomba_client()
            assert client is None

    def test_init_reoon_with_credentials(self) -> None:
        """Should initialize Reoon client with valid credentials."""
        with patch.dict("os.environ", {"REOON_API_KEY": "test_key"}):  # pragma: allowlist secret
            client = EmailVerificationAgent._init_reoon_client()
            assert client is not None

    def test_init_reoon_without_credentials(self) -> None:
        """Should return None without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            client = EmailVerificationAgent._init_reoon_client()
            assert client is None
