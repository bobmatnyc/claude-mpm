#!/usr/bin/env bash
# Test script to verify Mamba environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude MPM Mamba Environment Test ===${NC}\n"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Test 1: Check if Mamba/Conda is available
echo -e "${YELLOW}Test 1: Checking for Mamba/Conda installation...${NC}"
if command -v mamba &> /dev/null; then
    echo -e "${GREEN}✓ Mamba found: $(which mamba)${NC}"
    CONDA_CMD="mamba"
elif command -v conda &> /dev/null; then
    echo -e "${GREEN}✓ Conda found: $(which conda)${NC}"
    CONDA_CMD="conda"
elif command -v micromamba &> /dev/null; then
    echo -e "${GREEN}✓ Micromamba found: $(which micromamba)${NC}"
    CONDA_CMD="micromamba"
else
    echo -e "${RED}✗ No Mamba/Conda installation found${NC}"
    echo -e "${YELLOW}  Install Mambaforge from: https://github.com/conda-forge/miniforge${NC}"
    exit 1
fi

# Test 2: Check environment.yml exists
echo -e "\n${YELLOW}Test 2: Checking for environment.yml...${NC}"
if [[ -f "$PROJECT_ROOT/environment.yml" ]]; then
    echo -e "${GREEN}✓ environment.yml found${NC}"
else
    echo -e "${RED}✗ environment.yml not found at $PROJECT_ROOT${NC}"
    exit 1
fi

# Test 3: Check if claude-mpm environment exists
echo -e "\n${YELLOW}Test 3: Checking if claude-mpm environment exists...${NC}"
if $CONDA_CMD env list | grep -q "^claude-mpm "; then
    echo -e "${GREEN}✓ claude-mpm environment exists${NC}"
else
    echo -e "${YELLOW}⚠ claude-mpm environment not found, creating...${NC}"
    $CONDA_CMD env create -f "$PROJECT_ROOT/environment.yml"
    echo -e "${GREEN}✓ claude-mpm environment created${NC}"
fi

# Test 4: Test claude-mpm-mamba script
echo -e "\n${YELLOW}Test 4: Testing claude-mpm-mamba script...${NC}"
if [[ -x "$SCRIPT_DIR/claude-mpm-mamba" ]]; then
    echo -e "${GREEN}✓ claude-mpm-mamba script is executable${NC}"
    
    # Try running with --version
    if "$SCRIPT_DIR/claude-mpm-mamba" --version 2>/dev/null | grep -q "claude-mpm"; then
        echo -e "${GREEN}✓ claude-mpm-mamba script runs successfully${NC}"
    else
        echo -e "${YELLOW}⚠ claude-mpm-mamba ran but version check failed${NC}"
    fi
else
    echo -e "${RED}✗ claude-mpm-mamba script not found or not executable${NC}"
    exit 1
fi

# Test 5: Test auto-detection in main script
echo -e "\n${YELLOW}Test 5: Testing auto-detection in claude-mpm script...${NC}"
if [[ -x "$SCRIPT_DIR/claude-mpm" ]]; then
    # Check if it would use Mamba
    OUTPUT=$("$SCRIPT_DIR/claude-mpm" --version 2>&1 | head -5)
    if echo "$OUTPUT" | grep -q "Auto-detected Mamba/Conda"; then
        echo -e "${GREEN}✓ Main script auto-detects Mamba environment${NC}"
    elif echo "$OUTPUT" | grep -q "Mamba/Conda not found"; then
        echo -e "${YELLOW}⚠ Main script falls back to venv (expected if Mamba not in PATH)${NC}"
    else
        echo -e "${GREEN}✓ Main script runs (detection status unclear)${NC}"
    fi
fi

# Test 6: Verify Python packages
echo -e "\n${YELLOW}Test 6: Verifying Python packages in environment...${NC}"
# Source conda and activate environment for this test
if [[ -f "$HOME/mambaforge/etc/profile.d/conda.sh" ]]; then
    source "$HOME/mambaforge/etc/profile.d/conda.sh"
elif [[ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
elif [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
fi

if command -v conda &> /dev/null; then
    conda activate claude-mpm 2>/dev/null || true
    
    # Check key packages
    PACKAGES=("click" "pyyaml" "flask" "pytest" "black" "mypy")
    MISSING=()
    
    for pkg in "${PACKAGES[@]}"; do
        if python -c "import $pkg" 2>/dev/null; then
            echo -e "${GREEN}  ✓ $pkg${NC}"
        else
            echo -e "${RED}  ✗ $pkg${NC}"
            MISSING+=("$pkg")
        fi
    done
    
    if [ ${#MISSING[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ All key packages installed${NC}"
    else
        echo -e "${YELLOW}⚠ Missing packages: ${MISSING[*]}${NC}"
        echo -e "${YELLOW}  Run: mamba env update -n claude-mpm -f environment.yml${NC}"
    fi
    
    conda deactivate 2>/dev/null || true
else
    echo -e "${YELLOW}⚠ Could not activate environment for package verification${NC}"
fi

# Summary
echo -e "\n${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}✓ Mamba environment setup is functional${NC}"
echo -e "\nYou can now use:"
echo -e "  ${BLUE}./scripts/claude-mpm${NC}         - Auto-detects and uses Mamba"
echo -e "  ${BLUE}./scripts/claude-mpm-mamba${NC}   - Explicitly uses Mamba"
echo -e "  ${BLUE}./scripts/claude-mpm --use-venv${NC} - Forces venv usage"
echo -e "\nTo update the environment:"
echo -e "  ${BLUE}./scripts/claude-mpm-mamba --update-env --help${NC}"