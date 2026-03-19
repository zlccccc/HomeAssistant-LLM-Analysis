#!/bin/bash
# Format code script
# Usage: ./scripts/format.sh [options]
# Options:
#   --check    Check formatting without making changes
#   --fix      Fix formatting issues (default)
#   --ruff     Use ruff for formatting (default)
#   --black    Use black for formatting

set -e

# Default options
CHECK_ONLY=false
FORMATTER="ruff"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --fix)
            CHECK_ONLY=false
            shift
            ;;
        --ruff)
            FORMATTER="ruff"
            shift
            ;;
        --black)
            FORMATTER="black"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --check    Check formatting without making changes"
            echo "  --fix      Fix formatting issues (default)"
            echo "  --ruff     Use ruff for formatting (default)"
            echo "  --black    Use black for formatting"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running code formatter...${NC}"

# Run formatter
if [ "$FORMATTER" = "ruff" ]; then
    echo -e "${YELLOW}Using Ruff formatter${NC}"

    # Run ruff check with auto-fix
    if [ "$CHECK_ONLY" = true ]; then
        echo "Checking code with ruff..."
        uv run ruff check backend/ frontend/ test/ frontend/tools/analyze_entities.py
        uv run ruff format --check backend/ frontend/ test/ frontend/tools/analyze_entities.py
    else
        echo "Fixing code with ruff..."
        uv run ruff check --fix backend/ frontend/ test/ frontend/tools/analyze_entities.py
        uv run ruff format backend/ frontend/ test/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Code formatted with ruff${NC}"
    fi
elif [ "$FORMATTER" = "black" ]; then
    echo -e "${YELLOW}Using Black formatter${NC}"

    if [ "$CHECK_ONLY" = true ]; then
        echo "Checking code with black..."
        uv run black --check backend/ frontend/ test/ frontend/tools/analyze_entities.py
    else
        echo "Formatting code with black..."
        uv run black backend/ frontend/ test/ frontend/tools/analyze_entities.py
        echo -e "${GREEN}✓ Code formatted with black${NC}"
    fi
fi

# Run isort separately (if not using ruff)
if [ "$FORMATTER" = "black" ]; then
    echo "Sorting imports with isort..."
    if [ "$CHECK_ONLY" = true ]; then
        uv run ruff check --select I --check backend/ frontend/ test/ frontend/tools/analyze_entities.py
    else
        uv run ruff check --select I --fix backend/ frontend/ test/ frontend/tools/analyze_entities.py
    fi
fi

echo -e "${GREEN}Formatting complete!${NC}"
