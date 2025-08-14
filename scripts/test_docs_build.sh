#!/bin/bash

# Test documentation build locally
# This simulates what GitHub Actions will do

set -e  # Exit on error

echo "Testing documentation build locally..."
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing documentation dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -e .[docs]

if [ -f "docs/api/requirements.txt" ]; then
    pip install -q -r docs/api/requirements.txt
fi

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
cd docs/api
make clean

# Build documentation
echo -e "${YELLOW}Building documentation...${NC}"
make html

# Check if build was successful
if [ -f "_build/html/index.html" ]; then
    echo -e "${GREEN}✓ Documentation build successful!${NC}"
    echo ""
    echo "Documentation built at: $(pwd)/_build/html/"
    echo ""
    echo "To view locally, run:"
    echo "  python -m http.server 8000 --directory _build/html"
    echo "  Then open: http://localhost:8000"
    
    # Check for warnings
    echo ""
    echo -e "${YELLOW}Checking for build warnings...${NC}"
    if make html 2>&1 | grep -i "warning:"; then
        echo -e "${YELLOW}⚠ Build contains warnings (see above)${NC}"
    else
        echo -e "${GREEN}✓ No warnings found${NC}"
    fi
else
    echo -e "${RED}✗ Documentation build failed!${NC}"
    echo "index.html not found in _build/html/"
    exit 1
fi

echo ""
echo -e "${GREEN}Local documentation test complete!${NC}"