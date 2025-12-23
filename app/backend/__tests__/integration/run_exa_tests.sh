#!/bin/bash
# Helper script to run Exa live integration tests
# Usage: ./run_exa_tests.sh [api_key]

set -e

if [ -n "$1" ]; then
    # API key provided as argument
    export EXA_API_KEY="$1"
    echo "Using provided API key (length: ${#EXA_API_KEY})"
elif [ -n "$EXA_API_KEY" ]; then
    # API key already in environment
    echo "Using EXA_API_KEY from environment (length: ${#EXA_API_KEY})"
else
    # Try to load from .env
    ENV_FILE="../../.env"
    if [ -f "$ENV_FILE" ]; then
        EXA_KEY=$(grep "^EXA_API_KEY=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [ "$EXA_KEY" != "..." ] && [ -n "$EXA_KEY" ] && [ ${#EXA_KEY} -gt 10 ]; then
            export EXA_API_KEY="$EXA_KEY"
            echo "Loaded EXA_API_KEY from .env (length: ${#EXA_KEY})"
        else
            echo "ERROR: EXA_API_KEY not found or invalid in .env"
            echo "Please set EXA_API_KEY in .env file or provide as argument:"
            echo "  ./run_exa_tests.sh your_api_key_here"
            exit 1
        fi
    else
        echo "ERROR: .env file not found and EXA_API_KEY not set"
        echo "Please set EXA_API_KEY in environment or provide as argument:"
        echo "  EXA_API_KEY=your_key ./run_exa_tests.sh"
        echo "  ./run_exa_tests.sh your_api_key_here"
        exit 1
    fi
fi

echo "Running Exa live integration tests..."
cd "$(dirname "$0")/../.."
uv run pytest __tests__/integration/test_exa_live.py -v --tb=short
