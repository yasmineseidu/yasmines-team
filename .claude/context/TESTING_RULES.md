# Testing Rules

## Backend Testing (Pytest)

### Test Structure
```
app/backend/__tests__/
├── conftest.py              # Shared fixtures
├── fixtures/                # Test fixtures
│   ├── agent_fixtures.py    # MockAgent, mock agents
│   └── integration_fixtures.py  # Mock API clients
├── unit/                    # Unit tests
│   ├── agents/
│   │   └── test_base_agent.py
│   ├── integrations/
│   │   └── test_base_integration.py
│   └── test_main.py
└── integration/             # Integration tests
    ├── test_agent_handoff.py
    └── test_health_api.py
```

### Running Tests
```bash
# Run all tests with coverage
make test
# or: pytest --cov=src --cov-report=term-missing

# Run with HTML coverage report
make test-html

# Run specific test file
pytest __tests__/unit/agents/test_base_agent.py

# Run specific test class
pytest __tests__/unit/agents/test_base_agent.py::TestBaseAgentInitialization

# Run tests matching pattern
pytest -k "handoff"

# Verbose output
pytest -v
```

### Test Configuration (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["__tests__"]
asyncio_mode = "auto"  # Async tests run automatically
addopts = "-v --tb=short"
```

### Available Fixtures (agent_fixtures.py)
```python
# MockAgent - Concrete implementation for testing
class ConcreteAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are a test agent."

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        return {"status": "processed", "task": task}

# Usage in tests
@pytest.fixture
def agent():
    return ConcreteAgent(name="test_agent", description="Test agent")
```

### Test Patterns

**Unit Test Pattern:**
```python
"""Unit tests for [module]."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.module import MyClass


class TestMyClassInitialization:
    """Tests for MyClass initialization."""

    def test_has_required_attribute(self, instance):
        """Instance should have required attribute."""
        assert instance.attribute == expected_value


class TestMyClassMethod:
    """Tests for MyClass.method()."""

    @pytest.mark.asyncio
    async def test_method_returns_result(self, instance):
        """method() should return expected result."""
        result = await instance.method()
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_method_with_mock(self, instance):
        """method() should call dependency."""
        with patch("src.module.dependency") as mock:
            mock.return_value = MagicMock(id="123")
            result = await instance.method()
            mock.assert_called_once()
```

**Integration Test Pattern:**
```python
"""Integration tests for [feature]."""
import pytest
from httpx import AsyncClient

from src.main import app


class TestFeatureIntegration:
    """Integration tests for feature."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_success(self):
        """Endpoint should return 200 OK."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/endpoint")
            assert response.status_code == 200
```

### Mocking Patterns

**Mock Celery Tasks:**
```python
with patch("src.tasks.orchestration_tasks.agent_handoff") as mock_task:
    mock_task.delay.return_value = MagicMock(id="task-123")
    result = await agent.handoff_to("sales", payload)
    assert result == "task-123"
```

**Mock External APIs:**
```python
with patch.object(client, "_request", new_callable=AsyncMock) as mock:
    mock.return_value = {"data": "response"}
    result = await client.get("/endpoint")
    mock.assert_called_once_with("GET", "/endpoint")
```

## Frontend Testing (Vitest)

### Test Structure
```
app/frontend/__tests__/
├── setup.ts           # Global test setup
└── unit/
    └── page.test.tsx  # Component tests
```

### Running Tests
```bash
# Run tests
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Watch mode
npm test -- --watch
```

### Test Configuration (vitest.config.ts)
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./__tests__/setup.ts'],
  },
});
```

### Test Setup (__tests__/setup.ts)
```typescript
import '@testing-library/jest-dom';
```

### Component Test Pattern
```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Page from '../src/app/page';

describe('Page', () => {
  it('renders heading', () => {
    render(<Page />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });

  it('displays expected text', () => {
    render(<Page />);
    expect(screen.getByText(/expected text/i)).toBeInTheDocument();
  });
});
```

## E2E Testing (Playwright)

### Running E2E Tests
```bash
# Run E2E tests (Chromium)
npx playwright test --project=chromium

# Run with headed browser
npx playwright test --headed

# Run specific test file
npx playwright test tests/example.spec.ts
```

### Configuration (playwright.config.ts)
- Runs in CI only (not local development)
- Uses Chromium browser
- Base URL: `http://localhost:3000`
- Artifacts uploaded on failure (7-day retention)

## Coverage Requirements

| Category | Minimum Coverage |
|----------|------------------|
| Tools | >90% |
| Agents | >85% |
| Overall | >80% |

## Test Naming Conventions

### Backend (Python)
- File: `test_[module].py`
- Class: `Test[Feature][Aspect]` (e.g., `TestBaseAgentInitialization`)
- Method: `test_[action]_[expected_result]` (e.g., `test_handoff_returns_task_id`)

### Frontend (TypeScript)
- File: `[module].test.tsx`
- Describe block: Feature name
- It block: `[action] [expected result]` (e.g., `renders heading`)

## CI Integration

### Backend CI Steps
1. `ruff check src/ __tests__/` - Lint
2. `ruff format --check src/ __tests__/` - Format check
3. `mypy src/` - Type check
4. `pytest --cov=src --cov-report=xml` - Tests with coverage

**Environment variables for tests:**
```yaml
REDIS_URL: redis://localhost:6379/0
DATABASE_URL: sqlite+aiosqlite:///./test.db
SECRET_KEY: test-secret-key
ANTHROPIC_API_KEY: sk-ant-test
```

### Frontend CI Steps
1. `npm run lint` - ESLint
2. `npm run typecheck` - TypeScript
3. `npm test` - Vitest
