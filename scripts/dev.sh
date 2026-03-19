#!/bin/bash
# Development helper script
# Provides shortcuts for common development tasks

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print usage
print_usage() {
    echo -e "${BLUE}HomeAssistant LLM Analysis - Development Helper${NC}"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install      Install dependencies"
    echo "  install-dev  Install development dependencies"
    echo "  format       Format code (ruff)"
    echo "  format-check Check code formatting"
    echo "  lint         Run linter (ruff)"
    echo "  type-check   Run type checker (mypy)"
    echo "  test         Run all tests"
    echo "  test-unit    Run unit tests only"
    echo "  test-int     Run integration tests only"
    echo "  test-cov     Run tests with coverage report"
    echo "  test-html    Run tests with HTML coverage"
    echo "  test-fast    Run fast tests only"
    echo "  test-watch   Run tests in watch mode"
    echo "  clean        Clean cache and build files"
    echo "  pre-commit   Install pre-commit hooks"
    echo "  run          Run the main application"
    echo "  analyze      Run entity analysis"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/dev.sh test-fast      Run fast tests"
    echo "  ./scripts/dev.sh format         Format all code"
    echo "  ./scripts/dev.sh test-cov       Run tests with coverage"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Parse command
case "$1" in
    install)
        echo -e "${YELLOW}Installing dependencies...${NC}"
        uv sync
        echo -e "${GREEN}✓ Dependencies installed${NC}"
        ;;

    install-dev)
        echo -e "${YELLOW}Installing development dependencies...${NC}"
        uv sync --extra dev
        echo -e "${GREEN}✓ Development dependencies installed${NC}"
        ;;

    format)
        echo -e "${YELLOW}Formatting code...${NC}"
        uv run ruff check --fix backend/ frontend/ test/ frontend/tools/analyze_entities.py
        uv run ruff format backend/ frontend/ test/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Code formatted${NC}"
        ;;

    format-check)
        echo -e "${YELLOW}Checking code formatting...${NC}"
        uv run ruff check backend/ frontend/ test/ frontend/tools/analyze_entities.py
        uv run ruff format --check backend/ frontend/ test/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Formatting check passed${NC}"
        ;;

    lint)
        echo -e "${YELLOW}Running linter...${NC}"
        uv run ruff check backend/ frontend/ test/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Lint check passed${NC}"
        ;;

    type-check)
        echo -e "${YELLOW}Running type checker...${NC}"
        uv run mypy backend/ frontend/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Type check passed${NC}"
        ;;

    test)
        echo -e "${YELLOW}Running all tests...${NC}"
        uv run pytest -v
        echo -e "${GREEN}✓ All tests passed${NC}"
        ;;

    test-unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        uv run pytest -v -m "unit"
        echo -e "${GREEN}✓ Unit tests passed${NC}"
        ;;

    test-int)
        echo -e "${YELLOW}Running integration tests...${NC}"
        uv run pytest -v -m "integration"
        echo -e "${GREEN}✓ Integration tests passed${NC}"
        ;;

    test-cov)
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        uv run pytest -v --cov=backend --cov=frontend --cov-report=term-missing
        echo -e "${GREEN}✓ Tests passed${NC}"
        ;;

    test-html)
        echo -e "${YELLOW}Running tests with HTML coverage...${NC}"
        uv run pytest -v --cov=backend --cov=frontend --cov-report=html:coverage/html --cov-report=term
        echo -e "${GREEN}✓ Tests passed${NC}"
        echo -e "${YELLOW}Starting HTTP server for coverage report...${NC}"
        echo -e "${YELLOW}Coverage report: http://localhost:9090${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
        cd coverage/html && python3 -m http.server 9090
        ;;

    test-fast)
        echo -e "${YELLOW}Running fast tests...${NC}"
        uv run pytest -v -m "not slow"
        echo -e "${GREEN}✓ Fast tests passed${NC}"
        ;;

    test-watch)
        echo -e "${YELLOW}Running tests in watch mode...${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        if command -v pytest-watch &> /dev/null; then
            uv run pytest-watch -v
        else
            echo -e "${RED}pytest-watch not installed. Install with: uv pip install pytest-watch${NC}"
            exit 1
        fi
        ;;

    clean)
        echo -e "${YELLOW}Cleaning cache and build files...${NC}"
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        rm -rf coverage/ htmlcov/ .coverage 2>/dev/null || true
        echo -e "${GREEN}✓ Clean complete${NC}"
        ;;

    pre-commit)
        echo -e "${YELLOW}Installing pre-commit hooks...${NC}"
        uv run pre-commit install
        echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
        echo -e "${YELLOW}Run hooks manually: uv run pre-commit run --all-files${NC}"
        ;;

    run)
        echo -e "${YELLOW}Running main application...${NC}"
        uv run python frontend/ha_chat_assistant.py
        ;;

    analyze)
        echo -e "${YELLOW}Running entity analysis...${NC}"
        uv run python frontend/tools/analyze_entities.py
        ;;

    help|--help|-h)
        print_usage
        ;;

    "")
        print_usage
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
