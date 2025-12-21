"""
Pytest configuration and shared fixtures for all tests.

This file is automatically loaded by pytest and provides:
- Async test support via pytest-asyncio
- Shared fixtures for agents, integrations, and database
- Test database configuration
- Mock utilities
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest

# Configure asyncio for async tests
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_session() -> AsyncGenerator[Any, None]:
    """
    Fixture providing an async SQLAlchemy session for testing.

    Usage:
        @pytest.mark.asyncio
        async def test_database_operation(async_session):
            # Use async_session for database operations
            pass
    """
    # TODO: Implement when SQLAlchemy models are created
    # from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    # from sqlalchemy.orm import sessionmaker
    #
    # engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # SessionLocal = sessionmaker(
    #     engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    # )
    #
    # async with SessionLocal() as session:
    #     yield session

    yield None  # Placeholder until models are created


@pytest.fixture
def mock_anthropic_response() -> dict[str, Any]:
    """
    Mock response from Anthropic Claude API.

    Returns:
        Dictionary representing a Claude API response
    """
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Mock response"}],
        "model": "claude-opus-4",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


@pytest.fixture
def mock_agent_config() -> dict[str, Any]:
    """
    Mock configuration for agent instantiation.

    Returns:
        Dictionary with agent configuration
    """
    return {
        "name": "test_agent",
        "description": "Test agent for unit tests",
        "model": "claude-opus-4",
        "timeout": 300,
    }


@pytest.fixture
def mock_integration_response() -> dict[str, Any]:
    """
    Mock response from third-party integration.

    Returns:
        Dictionary representing a successful API response
    """
    return {
        "status": "success",
        "data": {"id": "123", "created_at": "2024-01-01T00:00:00Z"},
        "meta": {"pagination": {"page": 1, "limit": 10, "total": 100}},
    }


@pytest.fixture
def mock_integration_error_response() -> dict[str, Any]:
    """
    Mock error response from third-party integration.

    Returns:
        Dictionary representing an error response
    """
    return {
        "status": "error",
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded",
            "retry_after": 60,
        },
    }


@pytest.fixture
def mock_database_record() -> dict[str, Any]:
    """
    Mock database record.

    Returns:
        Dictionary representing a lead or other database record
    """
    return {
        "id": "lead_123",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Acme Corp",
        "status": "qualified",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }


# Markers for test categorization
def pytest_configure(config: Any) -> None:
    """Register pytest markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as an async test (requires pytest-asyncio)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )
    config.addinivalue_line(
        "markers",
        "live_api: mark test as live API test requiring real credentials",
    )
