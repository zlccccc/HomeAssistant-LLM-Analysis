#!/bin/bash
# Test runner script
# Usage: ./scripts/test.sh [options] [test_files]
# Options:
#   --unit             Run unit tests only
#   --integration      Run integration tests only
#   --fast             Skip slow tests
#   --cov              Generate coverage report
#   --html             Generate HTML coverage report
#   --no-cov           Skip coverage
#   --watch            Watch mode (re-run on file changes)
#   -v, --verbose      Verbose output
#   -k KEYWORD         Run tests matching keyword
#   --failed           Re-run failed tests only

set -e

# Default options
PYTEST_ARGS=()
COVERAGE="--cov=backend --cov=frontend --cov-report=term-missing"
COVERAGE_ENABLED=true
WATCH_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            PYTEST_ARGS+=("-m" "unit")
            shift
            ;;
        --integration)
            PYTEST_ARGS+=("-m" "integration")
            shift
            ;;
        --fast)
            PYTEST_ARGS+=("-m" "not slow")
            shift
            ;;
        --cov)
            COVERAGE_ENABLED=true
            shift
            ;;
        --html)
            COVERAGE="$COVERAGE --cov-report=html"
            shift
            ;;
        --no-cov)
            COVERAGE_ENABLED=false
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        -v|--verbose)
            PYTEST_ARGS+=("-v")
            shift
            ;;
        -k)
            PYTEST_ARGS+=("-k" "$2")
            shift 2
            ;;
        --failed)
            PYTEST_ARGS+=("--lf")
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options] [test_files]"
            echo "Options:"
            echo "  --unit             Run unit tests only"
            echo "  --integration      Run integration tests only"
            echo "  --fast             Skip slow tests"
            echo "  --cov              Generate coverage report (default)"
            echo "  --html             Generate HTML coverage report"
            echo "  --no-cov           Skip coverage"
            echo "  --watch            Watch mode (re-run on file changes)"
            echo "  -v, --verbose      Verbose output"
            echo "  -k KEYWORD         Run tests matching keyword"
            echo "  --failed           Re-run failed tests only"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                              Run all tests"
            echo "  $0 --unit --fast                Run fast unit tests"
            echo "  $0 test/test_llm_manager.py     Run specific test file"
            echo "  $0 -k test_asr                  Run tests matching 'test_asr'"
            echo "  $0 --html --no-cov              Run tests with HTML report, no coverage"
            exit 0
            ;;
        -*)
            # Pass through other pytest options
            PYTEST_ARGS+=("$1")
            shift
            ;;
        *)
            # Test file or directory
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Add coverage if enabled
if [ "$COVERAGE_ENABLED" = true ]; then
    PYTEST_ARGS+=($COVERAGE)
fi

# Add verbosity if not already specified
if [[ ! " ${PYTEST_ARGS[@]} " =~ " -v " ]]; then
    PYTEST_ARGS+=("-v")
fi

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}     Running Test Suite${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Print test command
echo -e "${YELLOW}Test command:${NC}"
echo "uv run pytest ${PYTEST_ARGS[@]}"
echo ""

# Run tests
if [ "$WATCH_MODE" = true ]; then
    echo -e "${YELLOW}Watch mode enabled. Press Ctrl+C to stop.${NC}"
    uv run pytest-watch "${PYTEST_ARGS[@]}"
else
    if uv run pytest "${PYTEST_ARGS[@]}"; then
        echo ""
        echo -e "${GREEN}======================================${NC}"
        echo -e "${GREEN}     All Tests Passed!${NC}"
        echo -e "${GREEN}======================================${NC}"

        # Open/serve HTML coverage report if generated
        if [ "$COVERAGE_ENABLED" = true ] && [[ " $COVERAGE " =~ " --cov-report=html " ]]; then
            echo ""
            echo -e "${YELLOW}======================================${NC}"
            echo -e "${YELLOW}     Coverage Report${NC}"
            echo -e "${YELLOW}======================================${NC}"
            echo -e "${YELLOW}Starting HTTP server at: http://localhost:9090${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
            echo ""
            cd coverage/html && python3 -m http.server 9090
        fi
    else
        echo ""
        echo -e "${RED}======================================${NC}"
        echo -e "${RED}     Tests Failed${NC}"
        echo -e "${RED}======================================${NC}"
        exit 1
    fi
fi
