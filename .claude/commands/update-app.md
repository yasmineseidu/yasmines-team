---
name: update-app
description: Update dependencies, fix deprecations and warnings across backend (Python) and frontend (JavaScript)
---

# Dependency Update & Deprecation Fix

This project has two components:
- **Backend**: Python with pip (`app/backend/`)
- **Frontend**: JavaScript with npm (`app/frontend/`)

---

## Backend (Python)

### Step 1: Check for Updates

```bash
cd app/backend && pip list --outdated
```

### Step 2: Update Dependencies

```bash
cd app/backend && pip install --upgrade -e ".[dev]"
```

### Step 3: Check for Deprecations & Warnings

```bash
cd app/backend && pip install -e ".[dev]" 2>&1
```

Read ALL output carefully. Look for:
- Deprecation warnings
- Security vulnerabilities
- Dependency conflicts
- Breaking changes

### Step 4: Fix Issues

For each warning/deprecation:
1. Research the recommended replacement or fix
2. Update `pyproject.toml` accordingly
3. Re-run installation
4. Verify no warnings remain

### Step 5: Run Quality Checks

```bash
cd app/backend && make check
```

This runs: lint, format-check, typecheck, and tests.

---

## Frontend (JavaScript)

### Step 1: Check for Updates

```bash
cd app/frontend && npm outdated
```

### Step 2: Update Dependencies

```bash
cd app/frontend && npm update
cd app/frontend && npm audit fix
```

### Step 3: Check for Deprecations & Warnings

```bash
cd app/frontend && rm -rf node_modules package-lock.json
cd app/frontend && npm install 2>&1
```

Read ALL output carefully. Look for:
- Deprecation warnings
- Security vulnerabilities
- Peer dependency warnings
- Breaking changes

### Step 4: Fix Issues

For each warning/deprecation:
1. Research the recommended replacement or fix
2. Update `package.json` accordingly
3. Re-run installation
4. Verify no warnings remain

### Step 5: Run Quality Checks

```bash
cd app/frontend && npm run lint
cd app/frontend && npm run typecheck
cd app/frontend && npm test
```

---

## Final Verification

### Step 6: Verify Clean Install (Both)

**Backend:**
```bash
cd app/backend && pip install -e ".[dev]"
```

**Frontend:**
```bash
cd app/frontend && rm -rf node_modules package-lock.json
cd app/frontend && npm install
```

Ensure ZERO warnings/errors in both components.

### Step 7: Run Full Test Suite

```bash
cd app/backend && make test
cd app/frontend && npm test
```

All tests must pass before completing.
