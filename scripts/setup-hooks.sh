#!/bin/bash
#
# Setup script for development environment
# Installs pre-commit hooks to prevent secrets from being committed
#
# Usage: ./scripts/setup-hooks.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Setting up development environment..."
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo -e "${YELLOW}pre-commit not found. Installing...${NC}"
    pip install pre-commit
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Verify installation
if [ -f ".git/hooks/pre-commit" ]; then
    echo -e "${GREEN}Pre-commit hooks installed successfully!${NC}"
else
    echo -e "${RED}Failed to install pre-commit hooks${NC}"
    exit 1
fi

# Run hooks against all files to check for existing issues
echo ""
echo "Running security checks on existing files..."
echo "(This may take a moment...)"
echo ""

if pre-commit run --all-files; then
    echo ""
    echo -e "${GREEN}All checks passed!${NC}"
else
    echo ""
    echo -e "${YELLOW}Some checks failed. Please fix the issues above.${NC}"
fi

echo ""
echo "Setup complete! The following protections are now active:"
echo ""
echo "  1. detect-secrets    - Catches API keys, tokens, passwords"
echo "  2. google-oauth      - Catches Google OAuth client IDs/secrets"
echo "  3. detect-private-key - Catches private key files"
echo "  4. bandit            - Python security scanning"
echo "  5. semgrep           - Additional security patterns"
echo ""
echo "These run automatically on every commit."
echo "To run manually: pre-commit run --all-files"
echo ""
