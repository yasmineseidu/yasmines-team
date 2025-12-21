# Tech Stack Recommendations - Yasmine's Team

**Generated:** 2025-12-21
**Codebase:** Multi-agent AI system (76+ agents, 40+ integrations)

---

## Executive Summary

Your codebase has a **modern, well-chosen foundation** with FastAPI + SQLAlchemy 2.0 + Pydantic 2.x. The main opportunities are:

1. **Update dependencies to latest 2025 versions** - security patches, performance gains
2. **Add ty (Astral) as secondary type checker** - 10-60x faster feedback loop
3. **Consider Valkey** - if Redis licensing concerns matter to you
4. **Testing infrastructure is ready but empty** - need to write actual tests

---

## Current State Summary

### Backend Framework
| Component | Current Version | Status |
|-----------|-----------------|--------|
| Python | 3.11+ | ✅ Good (3.12 also supported) |
| FastAPI | 0.115.0 | ⚠️ Update available (0.115.x series, check for patches) |
| Uvicorn | 0.30.0 | ⚠️ Update to 0.32.x |
| Pydantic | 2.5.2 | ⚠️ Update to 2.10.x |
| pydantic-settings | 2.1.0 | ⚠️ Update to 2.7.x |

### Database & ORM
| Component | Current Version | Status |
|-----------|-----------------|--------|
| SQLAlchemy | 2.0.23 | ⚠️ Update to 2.0.36 |
| asyncpg | 0.29.0 | ✅ Good (0.30.0 available) |
| Alembic | 1.13.1 | ⚠️ Update to 1.14.x |

### Task Queue & Caching
| Component | Current Version | Status |
|-----------|-----------------|--------|
| Celery | 5.4.0 | ✅ Good (latest stable) |
| Redis | 5.0.0 | ⚠️ Update to 5.2.x |

### AI & Agent Framework
| Component | Current Version | Status |
|-----------|-----------------|--------|
| anthropic | 0.37.0 | ⚠️ Update to 0.52.x (major improvements) |
| claude-agent-sdk | 0.37.0 | ✅ Check for latest |
| pinecone-client | 3.0.0 | ⚠️ Update to 5.x (major version) |
| zep-python | 0.1.0 | ⚠️ Very early - monitor stability |

### Code Quality Tools
| Component | Current Version | Status |
|-----------|-----------------|--------|
| Ruff | 0.1.8 | ⚠️ Update to 0.8.x (major improvements) |
| mypy | 1.7.1 | ⚠️ Update to 1.14.x |
| Bandit | 1.7.5 | ⚠️ Update to 1.8.x |
| pre-commit | 3.5.0 | ⚠️ Update to 4.0.x |

### Testing Framework
| Component | Current Version | Status |
|-----------|-----------------|--------|
| pytest | 7.4.3 | ⚠️ Update to 8.3.x |
| pytest-asyncio | 0.23.2 | ⚠️ Update to 0.24.x |
| pytest-cov | 4.1.0 | ⚠️ Update to 6.0.x |
| pytest-mock | 3.12.0 | ⚠️ Update to 3.14.x |

### HTTP Clients
| Component | Current Version | Status |
|-----------|-----------------|--------|
| httpx | 0.27.0 | ⚠️ Update to 0.28.x |
| aiohttp | 3.9.1 | ⚠️ Update to 3.11.x |

---

## Research Findings (2025 Best Practices)

### 1. Backend Framework

**Research Finding:** FastAPI remains the best choice for async Python APIs in 2025. Major companies (Netflix, Uber, Microsoft) use it in production. Litestar is a newer alternative with slightly faster microbenchmarks, but FastAPI has better ecosystem maturity.

**Recommendation:** **KEEP FastAPI** - You made the right choice. Just update to latest patch version.

**Sources:**
- [JetBrains: Django, Flask, FastAPI Comparison](https://blog.jetbrains.com/pycharm/2025/02/django-flask-fastapi/)
- [Medium: Python Backend Frameworks 2025](https://medium.com/@pythonbyeli/the-5-python-backend-frameworks-that-are-actually-worth-your-time-in-2025-5e78e5c60796)
- [FastAPI vs Litestar 2025](https://medium.com/top-python-libraries/fastapi-vs-litestar-which-python-web-framework-will-dominate-2025-1e63428268f2)

---

### 2. Database ORM

**Research Finding:** SQLAlchemy 2.0 leads benchmarks when paired with FastAPI. SQLModel is a thin layer on top that improves DX but adds complexity. For your 76+ agent system, SQLAlchemy 2.0's full control is better.

**Recommendation:** **KEEP SQLAlchemy 2.0** - Update to 2.0.36. Consider SQLModel only for new simpler endpoints.

**Sources:**
- [SQLModel vs SQLAlchemy Benchmarks](https://medium.com/@sparknp1/10-sqlmodel-vs-sqlalchemy-choices-with-real-benchmarks-dde68459d88f)
- [FastAPI SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Modern ORM Frameworks 2025](https://www.nucamp.co/blog/coding-bootcamp-backend-with-python-2025-modern-orm-frameworks-in-2025-django-orm-sqlalchemy-and-beyond)

---

### 3. Task Queue

**Research Finding:** Celery remains the reference for large-scale production. ARQ is lighter for async-native apps but lacks Celery's ecosystem. Dramatiq has better defaults but works best with RabbitMQ, not Redis.

**Recommendation:** **KEEP Celery** - Battle-tested, scales to millions of tasks, your Redis backend is fine.

**Sources:**
- [Choosing the Right Python Task Queue](https://judoscale.com/blog/choose-python-task-queue)
- [ARQ vs Celery Comparison](https://www.bithost.in/blog/tech-2/how-to-run-fastapi-background-tasks-arq-vs-celery-96)
- [Celery vs ARQ Analysis](https://leapcell.io/blog/celery-versus-arq-choosing-the-right-task-queue-for-python-applications)

---

### 4. Caching (Redis)

**Research Finding:** Redis changed to restrictive licensing (RSAL/SSPL) in March 2024, then added AGPLv3 back in 2025. Valkey (Linux Foundation fork from Redis 7.2.4) is now backed by AWS, Google Cloud, Oracle. KeyDB has maintenance concerns (maintainer left Jan 2025).

**Recommendation:**
- **If licensing matters:** Consider migrating to **Valkey** (drop-in replacement, 100% compatible)
- **If licensing doesn't matter:** Keep Redis, update to 5.2.x

**Sources:**
- [Redis vs Valkey vs KeyDB 2025](https://blog.octabyte.io/topics/open-source-databases/redis-vs-valkey-vs-keydb/)
- [Valkey vs Redis Comparison](https://betterstack.com/community/comparisons/redis-vs-valkey/)
- [Top Redis Alternatives 2025](https://bullmq.io/articles/redis/top-redis-alternatives-2025/)

---

### 5. Linting & Formatting

**Research Finding:** Ruff has definitively won. It's 10-100x faster than Flake8, replaces Black + isort + pyupgrade + autoflake. Major projects (FastAPI, pandas, pydantic) have migrated.

**Recommendation:** **KEEP Ruff** - Update from 0.1.8 to **0.8.x** for major improvements (800+ rules now).

**Sources:**
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Why Replace Flake8/Black with Ruff](https://medium.com/@zigtecx/why-you-should-replace-flake8-black-and-isort-with-ruff-the-ultimate-python-code-quality-tool-a9372d1ddc1e)
- [Black vs Ruff Comparison](https://www.packetcoders.io/whats-the-difference-black-vs-ruff/)

---

### 6. Type Checking

**Research Finding:** New Rust-based type checkers emerged in 2025:
- **ty (Astral/Ruff team):** 10-60x faster than mypy/Pyright, now in beta
- **Pyrefly (Meta):** 14x faster than mypy, designed for million-line codebases

mypy remains the reference implementation with plugin support (important for Django/SQLAlchemy).

**Recommendation:**
- **Primary:** Keep **mypy** (update to 1.14.x) - stable, has plugins for SQLAlchemy
- **Secondary (optional):** Add **ty** for faster local feedback - it's in beta but Astral uses it exclusively

**Sources:**
- [ty: Astral's New Type Checker](https://astral.sh/blog/ty)
- [Pyrefly vs ty Comparison](https://blog.edward-li.com/tech/comparing-pyrefly-vs-ty/)
- [mypy vs Pyright Discussion](https://discuss.python.org/t/mypy-vs-pyright-in-practice/75984)

---

### 7. Security Scanning

**Research Finding:** Bandit achieves 92% accuracy for Python security issues. Semgrep is multi-language with custom rules. Best practice: use both together for 30% better coverage.

**Recommendation:** **KEEP Bandit** (update to 1.8.x), **ADD Semgrep** for custom rules and multi-language support.

**Sources:**
- [Bandit vs Semgrep Comparison](https://semgrep.dev/blog/2021/python-static-analysis-comparison-bandit-semgrep/)
- [Top Python Security Tools 2025](https://howik.com/top-security-tools-for-python)
- [Python Security Tools Guide](https://www.aikido.dev/blog/top-python-security-tools)

---

### 8. Testing Framework

**Research Finding:** pytest is the undisputed leader with 800+ plugins. unittest is only for legacy. Your current stack (pytest + pytest-asyncio + pytest-cov) is correct.

**Recommendation:** **KEEP pytest stack** - Update to latest versions. The bigger issue: **you have 0 tests written**.

**Sources:**
- [Top Python Testing Frameworks 2025](https://www.browserstack.com/guide/top-python-testing-frameworks)
- [pytest vs unittest Comparison](https://www.browserstack.com/guide/pytest-vs-unittest)
- [Python Testing Frameworks Overview](https://pytest-with-eric.com/comparisons/python-testing-frameworks/)

---

## Comprehensive Recommendations

### Priority 1: Dependency Updates (Low Risk, High Value)

Update all dependencies to latest stable versions. This is low-risk and gives security patches + performance improvements.

**Files to modify:**
1. `app/backend/pyproject.toml` - Update all dependency versions

**Estimated effort:** 2-3 hours (including testing)
**Risk:** Low

---

### Priority 2: Ruff Major Update (Low Risk, High Value)

Update Ruff from 0.1.8 to 0.8.x - major improvements in rules and speed.

**Files to modify:**
1. `app/backend/pyproject.toml` - Update ruff version
2. `.pre-commit-config.yaml` - Update ruff-pre-commit version

**Estimated effort:** 1 hour
**Risk:** Low (may flag new issues to fix)

---

### Priority 3: Anthropic SDK Update (Medium Risk, High Value)

Update from 0.37.0 to 0.52.x - significant improvements in Claude API handling.

**Files to modify:**
1. `app/backend/pyproject.toml` - Update anthropic version
2. Potentially: Any files using deprecated API patterns

**Estimated effort:** 2-4 hours
**Risk:** Medium (API changes may require code updates)

---

### Priority 4: Pinecone SDK Update (Medium Risk)

Update from 3.0.0 to 5.x - major version jump.

**Files to modify:**
1. `app/backend/pyproject.toml` - Update pinecone-client version
2. Any Pinecone integration code (API may have breaking changes)

**Estimated effort:** 2-4 hours
**Risk:** Medium (major version = potential breaking changes)

---

### Priority 5: Optional - Add ty Type Checker (Low Risk)

Add Astral's ty for faster local type checking feedback (10-60x faster than mypy).

**Files to modify:**
1. `app/backend/pyproject.toml` - Add ty to dev dependencies
2. `app/backend/Makefile` - Add `make type-fast` command

**Estimated effort:** 30 minutes
**Risk:** Low (additive, doesn't replace mypy)

---

### Priority 6: Optional - Valkey Migration (Low Risk)

If Redis licensing matters to you, migrate to Valkey (100% compatible drop-in).

**Files to modify:**
1. `app/backend/.env.example` - Document Valkey as alternative
2. Deployment configs (if any)

**Estimated effort:** 1-2 hours (mostly testing)
**Risk:** Low (protocol-compatible)

---

### Priority 7: Optional - Add Semgrep (Low Risk)

Add Semgrep for custom security rules alongside Bandit.

**Files to modify:**
1. `app/backend/pyproject.toml` - Add semgrep to dev dependencies
2. `.pre-commit-config.yaml` - Add semgrep hook
3. Create `.semgrep/` directory with custom rules

**Estimated effort:** 1-2 hours
**Risk:** Low (additive)

---

## Implementation Plan

### Phase 1: Core Dependency Updates
1. Update pyproject.toml with all new versions
2. Run `make install && make dev`
3. Run `make check` to verify linting/typing pass
4. Run tests (when written)

### Phase 2: Breaking Change Updates
1. Update anthropic SDK
2. Update pinecone-client
3. Fix any breaking changes in integration code

### Phase 3: Optional Enhancements
1. Add ty type checker
2. Add Semgrep security scanning
3. Consider Valkey if licensing matters

---

## Files Identified for Updates

| File | Changes |
|------|---------|
| `app/backend/pyproject.toml` | All dependency version updates |
| `.pre-commit-config.yaml` | Ruff version, optional Semgrep hook |
| `app/backend/Makefile` | Optional: add `make type-fast` for ty |
| `app/backend/.env.example` | Optional: document Valkey alternative |

**Total files:** 4 primary files (Phase 1-2)

---

## What NOT to Change

Based on research, these choices are already optimal:

1. ✅ **FastAPI** - Best async Python framework
2. ✅ **SQLAlchemy 2.0** - Best async ORM with full control
3. ✅ **Celery** - Battle-tested task queue
4. ✅ **pytest** - Undisputed testing leader
5. ✅ **Ruff** - Best linter/formatter (just update version)
6. ✅ **mypy** - Reference type checker with plugins

---

## Critical Note: Testing Gap

Your testing infrastructure is well-configured but **you have 0 tests written**:

- Test directories exist: `__tests__/unit/`, `__tests__/integration/`
- Fixtures are defined in `conftest.py`
- Coverage targets are set (>90% tools, >85% agents)
- **But no actual test files exist**

**Recommendation:** After dependency updates, prioritize writing tests. The tech stack is ready; the tests aren't.

---

## Summary

| Category | Action | Effort | Risk |
|----------|--------|--------|------|
| Dependencies | Update all to latest | 2-3 hrs | Low |
| Ruff | 0.1.8 → 0.8.x | 1 hr | Low |
| Anthropic SDK | 0.37.0 → 0.52.x | 2-4 hrs | Medium |
| Pinecone SDK | 3.0.0 → 5.x | 2-4 hrs | Medium |
| ty (optional) | Add for faster typing | 30 min | Low |
| Semgrep (optional) | Add security scanner | 1-2 hrs | Low |
| Valkey (optional) | If licensing matters | 1-2 hrs | Low |

**Total estimated effort:** 8-16 hours for full modernization

---

## Approval Required

**Do you approve implementing these changes?**

I will NOT implement anything until you explicitly say "yes, implement this" or "approved" or similar.

Please review and let me know:
1. Which priorities to implement (1-7 or subset)
2. Any concerns about specific changes
3. Whether licensing (Redis → Valkey) matters to you
