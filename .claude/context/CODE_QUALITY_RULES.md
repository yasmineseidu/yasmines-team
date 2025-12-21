# Code Quality Rules

## Backend (Python)

### Linting & Formatting
```bash
# Check linting
ruff check src/ __tests__/

# Auto-fix linting
ruff check --fix src/ __tests__/

# Format code
ruff format src/ __tests__/

# Check formatting only
ruff format --check src/ __tests__/

# Type checking
mypy src/

# Run all checks
make check
```

### Ruff Configuration (from pyproject.toml)
```toml
target-version = "py311"
line-length = 100

[lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]
ignore = ["E501", "B008", "ARG002"]

[format]
quote-style = "double"
indent-style = "space"
```

### Type Safety (MyPy Strict)
```toml
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

**Required patterns:**
- Full type hints on all functions
- Return type annotations mandatory
- Use `dict[str, Any]` not `Dict[str, Any]` (Python 3.11+)
- Async functions must have async return type hints

### Import Order (isort via Ruff)
```python
# Standard library
import os
from typing import Any

# Third-party
import httpx
from fastapi import FastAPI

# Local
from src.config import Settings
from src.agents.base_agent import BaseAgent
```

### Python Style Guide
| Rule | Example |
|------|---------|
| Line length | 100 characters max |
| Quotes | Double quotes for strings |
| Naming (files/functions) | `snake_case` |
| Naming (classes) | `PascalCase` |
| Naming (constants) | `SCREAMING_SNAKE_CASE` |
| All I/O | Must be async |

### Pre-commit Hooks
Configured in `.pre-commit-config.yaml`:
- `ruff` - Lint + auto-fix + format
- `mypy` - Type checking
- `detect-private-key` - Security
- `check-added-large-files` - Max 1MB

## Frontend (TypeScript/React)

### Linting & Formatting
```bash
# Lint
npm run lint

# Type check
npm run typecheck

# Format (Prettier)
npx prettier --write .
```

### ESLint Configuration
- Uses `eslint-config-next` for Next.js 15
- React 19 JSX transform (no React import needed)

### TypeScript (Strict Mode)
```json
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true
  }
}
```

### Frontend Style Guide
| Rule | Example |
|------|---------|
| Components | `PascalCase.tsx` |
| Hooks | `useCamelCase.ts` |
| Utilities | `camelCase.ts` |
| Types | `PascalCase` |
| React import | Not needed (React 19 JSX transform) |

## Quality Gates (CI Pipeline)

### Backend Pipeline
1. `ruff check src/ __tests__/` - Linting
2. `ruff format --check src/ __tests__/` - Formatting
3. `mypy src/` - Type checking
4. `pytest --cov=src --cov-report=xml` - Tests + coverage

### Frontend Pipeline
1. `npm run lint` - ESLint
2. `npm run typecheck` - TypeScript
3. `npm test` - Vitest

### E2E Pipeline (after backend + frontend pass)
- Playwright with Chromium
- Artifacts uploaded on failure

## Coverage Requirements

| Category | Minimum |
|----------|---------|
| Tools | >90% |
| Agents | >85% |
| Overall | >80% |

## Common Mistakes to Avoid

### Python
```python
# ❌ Wrong: Untyped function
def process_lead(lead):
    return lead["status"]

# ✅ Correct: Full type hints
def process_lead(lead: dict[str, Any]) -> str:
    return lead["status"]

# ❌ Wrong: Sync I/O
def get_lead(lead_id: str) -> dict:
    return database.query(lead_id)

# ✅ Correct: Async I/O
async def get_lead(lead_id: str) -> dict[str, Any]:
    return await database.query(lead_id)
```

### TypeScript
```typescript
// ❌ Wrong: No types
function processLead(lead) {
  return lead.status;
}

// ✅ Correct: Full types
function processLead(lead: Lead): string {
  return lead.status;
}

// ❌ Wrong: React import (not needed in React 19)
import React from 'react';

// ✅ Correct: No React import needed
export function MyComponent() {
  return <div>Hello</div>;
}
```
