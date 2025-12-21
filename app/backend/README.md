# Smarter Team Backend

Multi-agent AI system for business automation using Claude Agent SDK.

## Technology Stack

- **Framework**: FastAPI 0.115.0 (async Python web framework)
- **Task Queue**: Celery 5.4.0 (distributed task orchestration)
- **Cache/Broker**: Redis 5.0.0 (Upstash) for Celery and caching
- **Database**: PostgreSQL (Supabase) with SQLAlchemy 2.0 async ORM
- **AI/Agent**: Claude Agent SDK (Anthropic)
- **Vector DB**: Pinecone (embeddings and semantic search)
- **Agent Memory**: Zep (long-term context management)
- **40+ Integrations**: API clients for AI, lead generation, CRM, payments, etc.

## Project Structure

```
app/backend/
├── src/                          # Source code
│   ├── agents/                   # 76+ agent implementations
│   ├── integrations/             # 40+ API client implementations
│   ├── tasks/                    # Celery task definitions
│   ├── webhooks/                 # Webhook handlers (Stripe, etc.)
│   ├── middleware/               # FastAPI middleware
│   ├── models/                   # SQLAlchemy ORM models
│   ├── routes/                   # API route handlers
│   ├── security/                 # JWT, auth, permissions
│   ├── config.py                 # Settings from environment
│   └── main.py                   # FastAPI application (not yet created)
│
├── __tests__/                    # Test suite
│   ├── unit/                     # Unit tests
│   │   ├── agents/
│   │   ├── integrations/
│   │   └── tasks/
│   ├── integration/              # Integration tests
│   └── fixtures/                 # Shared test fixtures
│
├── config/                       # Configuration files
├── pyproject.toml                # Python dependencies and metadata
├── Makefile                      # Development commands
├── .env.example                  # Environment variables template
├── README.md                     # This file
└── .pre-commit-config.yaml       # Git hooks configuration
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (Supabase)
- Redis (Upstash)
- Pinecone account (optional, for vector search)

### 2. Setup

```bash
# Navigate to backend directory
cd app/backend

# Install dependencies
make install

# Install development dependencies
make dev

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required: DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY
```

### 3. Database Setup

```bash
# Apply migrations (when migrations are created)
make migrate

# Or manually with alembic:
alembic upgrade head
```

### 4. Run Development Server

```bash
# Start FastAPI server on http://localhost:8000
make run

# API will be available at:
# - OpenAPI docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

## Development Workflow

### Code Quality

This project enforces strict code quality standards:

```bash
# Run all checks (linting, formatting, type checking)
make check

# Or run individually:
make lint        # Ruff linting
make format      # Code formatting
make type        # MyPy type checking
```

**Requirements:**
- Linting: Ruff (E, W, F, I, B, C4, UP, ARG, SIM rules)
- Formatting: 100 character line length
- Type Checking: MyPy strict mode
- All functions must have type hints
- No `Any` types without justification

### Testing

```bash
# Run all tests
make test

# Run specific test categories
make test-unit       # Unit tests only
make test-int        # Integration tests only

# Run with coverage report
make test-cov        # Generates htmlcov/index.html

# Watch mode (re-run on file changes)
make test-watch
```

**Coverage Requirements:**
- Tools: >90%
- Agents: >85%
- Overall: >80%

### Testing Patterns

#### Unit Test Example
```python
# __tests__/unit/agents/test_base_agent.py

@pytest.mark.asyncio
async def test_agent_initialization() -> None:
    """Agent should initialize with name and description."""
    agent = BaseAgent(name="test", description="Test agent")
    assert agent.name == "test"
```

#### Integration Test Example
```python
# __tests__/integration/test_api_endpoints.py

@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Health endpoint should return 200 OK."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Critical Variables:**
- `DATABASE_URL` - PostgreSQL connection string (Supabase)
- `REDIS_URL` - Redis connection URL (Upstash)
- `ANTHROPIC_API_KEY` - Claude API key
- `SECRET_KEY` - Application secret (change in production)

See `.env.example` for all 40+ integration credentials.

### Configuration Management

Settings are loaded from environment variables via `src/config.py`:

```python
from src.config import settings

print(settings.database_url)
print(settings.anthropic_api_key)
```

## Architecture

### Agent Architecture

All agents inherit from `BaseAgent` (to be implemented):

```python
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are a specialized agent..."

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        # Agent logic here
        return {"result": "..."}
```

### Integration Pattern

All integrations inherit from `BaseIntegrationClient` (to be implemented):

```python
from src.integrations.base import BaseIntegrationClient

class MyServiceClient(BaseIntegrationClient):
    async def my_method(self, param: str) -> dict[str, Any]:
        return await self.post("/endpoint", json={"param": param})
```

### Database Access

Use SQLAlchemy async ORM (to be implemented):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Lead

async with AsyncSession(engine) as session:
    lead = await session.get(Lead, lead_id)
    await session.commit()
```

## API Endpoints (To Be Implemented)

Expected structure (endpoints to be created during implementation):

```
/api/
├── /health              # Health check
├── /agents/             # Agent management
├── /leads/              # Lead CRUD
├── /campaigns/          # Campaign management
├── /meetings/           # Meeting management
└── /webhooks/           # Webhook handlers
    ├── /stripe
    ├── /instantly
    └── /gohighlevel
```

## Task Management

Tasks are organized using Celery and Redis:

```python
# Celery task example (to be implemented)
from celery import shared_task

@shared_task
def process_lead(lead_id: str) -> dict[str, Any]:
    """Process a lead through qualification workflow."""
    # Task logic
    pass

# Execute task
process_lead.delay(lead_id="123")
```

## Monitoring & Logging

### Structured Logging

Logs are JSON-formatted and include context:

```python
import structlog

logger = structlog.get_logger()

logger.info("agent_started", agent_name="lead_qualifier", task_id="123")
logger.error("api_error", service="instantly", status_code=429, error="rate_limited")
```

### Database Monitoring Tables

- `audit_logs` - All agent actions and API calls
- `error_logs` - Error tracking and analysis
- `health_checks` - System health status
- `api_usage` - Rate limiting and quota tracking

## Pre-commit Hooks

Before committing, the following checks run automatically:

1. **Trailing whitespace** - Removed automatically
2. **Large files** - Blocked if >5MB
3. **Private keys** - Detected and blocked
4. **Ruff linting** - Fixed automatically
5. **Code formatting** - Fixed automatically
6. **Type checking** - MyPy strict mode
7. **Security scanning** - Bandit for vulnerabilities

Install hooks:
```bash
pre-commit install
```

Run manually:
```bash
pre-commit run --all-files
```

## Deployment

### Production Environment

Set these for production:

```bash
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com
SECRET_KEY=your-secure-random-key
```

### Docker (To Be Implemented)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY app/backend .
RUN pip install -e .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t smarter-team .
docker run -p 8000:8000 --env-file .env smarter-team
```

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError: No module named 'src'`**
- Solution: Install package in development mode: `make install`

**Issue: Database connection fails**
- Check `DATABASE_URL` in `.env`
- Verify Supabase is accessible
- Check PostgreSQL connectivity

**Issue: Redis connection fails**
- Check `REDIS_URL` in `.env`
- Verify Upstash Redis is accessible
- Check network connectivity

**Issue: API key errors**
- Verify `ANTHROPIC_API_KEY` is set
- Check integration API keys in `.env`
- Ensure keys have proper permissions

### Getting Help

1. Check the logs: `tail -f logs/app.log`
2. Run tests: `make test` to verify setup
3. Check configuration: `python -c "from src.config import settings; print(settings)"`

## Next Steps

1. **Create agent implementations** - Implement the 76+ agents from specs
2. **Build integration clients** - Create the 40+ API clients
3. **Set up database models** - Create SQLAlchemy models for all tables
4. **Implement API endpoints** - Create FastAPI routes
5. **Write tests** - Unit and integration tests (>85% coverage)
6. **Deploy** - Containerize and deploy to production

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Project Specifications](../../specs/)

## Contributing

See the main project [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - See LICENSE file for details
