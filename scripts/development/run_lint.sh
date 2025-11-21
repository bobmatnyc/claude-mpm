#!/bin/bash
# Comprehensive linting script for claude-mpm
# Catches duplicate imports, scope issues, and other code quality problems

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Running comprehensive code quality checks"
echo "========================================="

# Change to project root
cd "$(dirname "$0")/../.."

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Attempting to activate .venv..."
    if [[ -f .venv/bin/activate ]]; then
        source .venv/bin/activate
    elif [[ -f venv/bin/activate ]]; then
        source venv/bin/activate
    else
        echo -e "${RED}Error: Could not find virtual environment${NC}"
        exit 1
    fi
fi

# Function to run a check and report results
run_check() {
    local name=$1
    local command=$2

    echo ""
    echo "Running $name..."
    echo "----------------------------------------"

    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        return 1
    fi
}

# Track overall status
FAILED_CHECKS=()

# 1. Run Ruff for fast, comprehensive linting (includes duplicate import detection)
if command -v ruff &> /dev/null; then
    if ! run_check "Ruff (fast linter with duplicate import detection)" "ruff check src/"; then
        FAILED_CHECKS+=("Ruff")
    fi
else
    echo -e "${YELLOW}Ruff not installed. Install with: pip install ruff${NC}"
fi

# 2. Run Flake8 with plugins for additional checks
if command -v flake8 &> /dev/null; then
    if ! run_check "Flake8 (with import checking)" "flake8 src/"; then
        FAILED_CHECKS+=("Flake8")
    fi
else
    echo -e "${YELLOW}Flake8 not installed. Install with: pip install flake8 flake8-import-order flake8-tidy-imports${NC}"
fi

# 3. Run Pylint for duplicate code detection
if command -v pylint &> /dev/null; then
    if ! run_check "Pylint (duplicate code detection)" "pylint src/claude_mpm --errors-only --disable=all --enable=duplicate-code,reimported,import-self"; then
        FAILED_CHECKS+=("Pylint duplicate detection")
    fi
else
    echo -e "${YELLOW}Pylint not installed. Install with: pip install pylint${NC}"
fi

# 4. Check for specific duplicate import patterns that caused the bug
echo ""
echo "Checking for specific duplicate import patterns..."
echo "----------------------------------------"

# Check for duplicate imports in different scopes (the exact bug pattern)
DUPLICATE_PATTERN_FOUND=false

# Pattern 1: Import at module level and then again in function
echo "Checking for imports duplicated in functions..."
if grep -r "^import\|^from .* import" src/ --include="*.py" | grep -v "__pycache__" > /tmp/module_imports.txt; then
    while IFS= read -r file; do
        # Extract filename from grep output
        filename=$(echo "$file" | cut -d: -f1)

        # Check if this file has imports inside functions
        if grep -E "^[[:space:]]+import |^[[:space:]]+from .* import" "$filename" 2>/dev/null | grep -v "^#"; then
            echo -e "${RED}Warning: $filename has imports inside functions (potential scope issue)${NC}"
            DUPLICATE_PATTERN_FOUND=true
        fi
    done < /tmp/module_imports.txt
fi

if [ "$DUPLICATE_PATTERN_FOUND" = false ]; then
    echo -e "${GREEN}✓ No duplicate import patterns found${NC}"
fi

# 5. Run Black in check mode
if command -v black &> /dev/null; then
    if ! run_check "Black (formatting check)" "black --check src/"; then
        FAILED_CHECKS+=("Black formatting")
        echo -e "${YELLOW}Tip: Run 'black src/' to auto-format${NC}"
    fi
else
    echo -e "${YELLOW}Black not installed. Install with: pip install black${NC}"
fi

# 6. Run isort in check mode
if command -v isort &> /dev/null; then
    if ! run_check "isort (import sorting)" "isort --check-only --profile=black src/"; then
        FAILED_CHECKS+=("Import sorting")
        echo -e "${YELLOW}Tip: Run 'isort --profile=black src/' to auto-sort imports${NC}"
    fi
else
    echo -e "${YELLOW}isort not installed. Install with: pip install isort${NC}"
fi

# 7. Run MyPy for type checking (can catch some scope issues)
if command -v mypy &> /dev/null; then
    echo ""
    echo "Running MyPy type checking..."
    echo "----------------------------------------"
    # Run mypy but don't fail the script if it has issues (too strict for now)
    mypy src/claude_mpm --ignore-missing-imports --no-error-summary 2>/dev/null || true
    echo -e "${YELLOW}MyPy check complete (informational only)${NC}"
else
    echo -e "${YELLOW}MyPy not installed. Install with: pip install mypy${NC}"
fi

# Summary
echo ""
echo "========================================="
echo "Linting Summary"
echo "========================================="

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
    echo "Please fix the issues above before committing."
    exit 1
fi