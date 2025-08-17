#!/bin/bash
# Setup pre-commit hooks for claude-mpm development
# This script installs and configures pre-commit hooks for code formatting and quality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up pre-commit hooks for claude-mpm${NC}"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -f ".pre-commit-config.yaml" ]; then
    echo -e "${RED}❌ Error: This script must be run from the claude-mpm root directory${NC}"
    echo "Expected files: pyproject.toml, .pre-commit-config.yaml"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 is required but not found${NC}"
    exit 1
fi

# Check if pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ Error: pip is required but not found${NC}"
    exit 1
fi

# Determine pip command
PIP_CMD="pip"
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
fi

echo -e "${YELLOW}📦 Installing pre-commit...${NC}"

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    $PIP_CMD install pre-commit
else
    echo "✅ pre-commit is already installed"
fi

# Install development dependencies if needed
echo -e "${YELLOW}📦 Installing development dependencies...${NC}"
$PIP_CMD install -e ".[dev]" || {
    echo -e "${YELLOW}⚠️  Warning: Could not install dev dependencies. Trying individual packages...${NC}"
    $PIP_CMD install black isort flake8 mypy bandit
}

echo -e "${YELLOW}🔗 Installing pre-commit hooks...${NC}"

# Install the pre-commit hooks
pre-commit install

# Install commit-msg hook for conventional commits (optional)
pre-commit install --hook-type commit-msg || echo -e "${YELLOW}⚠️  Note: commit-msg hook not configured${NC}"

echo -e "${YELLOW}🧪 Running pre-commit on all files (this may take a while)...${NC}"

# Run pre-commit on all files to ensure everything is set up correctly
if pre-commit run --all-files; then
    echo -e "${GREEN}✅ All pre-commit hooks passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Some pre-commit hooks failed. This is normal for the first run.${NC}"
    echo -e "${YELLOW}   The hooks have automatically fixed formatting issues.${NC}"
    echo -e "${YELLOW}   Please review the changes and commit them.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Pre-commit setup complete!${NC}"
echo ""
echo "What happens now:"
echo "• Code will be automatically formatted with Black and isort on commit"
echo "• Linting with flake8 will run on commit"
echo "• Type checking with mypy will run on commit"
echo "• Security scanning with bandit will run on commit"
echo ""
echo "To manually run pre-commit:"
echo "  pre-commit run --all-files    # Run on all files"
echo "  pre-commit run                # Run on staged files only"
echo ""
echo "To skip pre-commit hooks (not recommended):"
echo "  git commit --no-verify"
echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"
