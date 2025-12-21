.PHONY: help install dev test lint format type type-fast security check clean run migrate

help:
	@echo "Smarter Team Backend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies"
	@echo "  make dev           Install dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run           Run development server (localhost:8000)"
	@echo "  make migrate       Run database migrations"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linting (ruff check)"
	@echo "  make format        Format code (ruff format)"
	@echo "  make format-check  Check formatting without changes"
	@echo "  make type          Run type checking (mypy - comprehensive)"
	@echo "  make type-fast     Run type checking (ty - 10-60x faster)"
	@echo "  make security      Run security scans (bandit + semgrep)"
	@echo "  make check         Run all quality checks (lint + format + type)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-int      Run integration tests only"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make test-watch    Run tests in watch mode"
	@echo ""
	@echo "Cleaning:"
	@echo "  make clean         Remove build artifacts and cache"
	@echo "  make clean-all     Remove all including .venv"

# ============================================================================
# Setup
# ============================================================================

install:
	pip install -e .

dev:
	pip install -e ".[dev,test]"

# ============================================================================
# Development
# ============================================================================

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

# ============================================================================
# Code Quality
# ============================================================================

lint:
	ruff check src/ __tests__/

format:
	ruff format src/ __tests__/

format-check:
	ruff format --check src/ __tests__/

type:
	mypy src/

type-fast:
	ty check src/
	@echo "✓ Fast type checking complete (ty)"

security:
	bandit -r src/ -ll
	semgrep --config auto src/ --error
	@echo "✓ Security scans complete (bandit + semgrep)"

check: lint format-check type
	@echo "✓ All quality checks passed!"

# ============================================================================
# Testing
# ============================================================================

test:
	pytest __tests__/ -v --tb=short

test-unit:
	pytest __tests__/unit/ -v --tb=short

test-int:
	pytest __tests__/integration/ -v --tb=short

test-cov:
	pytest __tests__/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	pytest __tests__/ -v --tb=short --looponfail

# ============================================================================
# Cleaning
# ============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Clean complete"

clean-all: clean
	rm -rf .venv/
	@echo "✓ Full clean complete"
