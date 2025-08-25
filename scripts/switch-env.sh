#!/usr/bin/env bash
# Quick environment switcher for claude-mpm development

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

show_help() {
    echo -e "${CYAN}Claude MPM Environment Switcher${NC}"
    echo ""
    echo "Usage: ./switch-env.sh [option]"
    echo ""
    echo "Options:"
    echo "  mamba    - Switch to Mamba environment (creates if needed)"
    echo "  venv     - Switch to Python venv"
    echo "  status   - Show current environment status"
    echo "  clean    - Remove all environments (careful!)"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./switch-env.sh mamba   # Switch to Mamba"
    echo "  ./switch-env.sh venv    # Switch to venv"
    echo "  ./switch-env.sh status  # Check current setup"
}

check_status() {
    echo -e "${CYAN}=== Environment Status ===${NC}\n"
    
    # Check Mamba/Conda
    echo -e "${YELLOW}Mamba/Conda:${NC}"
    if command -v mamba &> /dev/null; then
        echo -e "  ${GREEN}✓ Mamba installed${NC} at $(which mamba)"
        if mamba env list | grep -q "^claude-mpm "; then
            echo -e "  ${GREEN}✓ claude-mpm environment exists${NC}"
        else
            echo -e "  ${YELLOW}○ claude-mpm environment not created${NC}"
        fi
    elif command -v conda &> /dev/null; then
        echo -e "  ${GREEN}✓ Conda installed${NC} at $(which conda)"
        if conda env list | grep -q "^claude-mpm "; then
            echo -e "  ${GREEN}✓ claude-mpm environment exists${NC}"
        else
            echo -e "  ${YELLOW}○ claude-mpm environment not created${NC}"
        fi
    else
        echo -e "  ${RED}✗ Not installed${NC}"
    fi
    
    # Check venv
    echo -e "\n${YELLOW}Python venv:${NC}"
    if [[ -d "$PROJECT_ROOT/venv" ]]; then
        echo -e "  ${GREEN}✓ venv exists${NC} at $PROJECT_ROOT/venv"
    else
        echo -e "  ${YELLOW}○ venv not created${NC}"
    fi
    
    # Check environment.yml
    echo -e "\n${YELLOW}Configuration files:${NC}"
    if [[ -f "$PROJECT_ROOT/environment.yml" ]]; then
        echo -e "  ${GREEN}✓ environment.yml exists${NC}"
    else
        echo -e "  ${RED}✗ environment.yml missing${NC}"
    fi
    
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        echo -e "  ${GREEN}✓ pyproject.toml exists${NC}"
    else
        echo -e "  ${RED}✗ pyproject.toml missing${NC}"
    fi
    
    # Check which would be used
    echo -e "\n${YELLOW}Default behavior:${NC}"
    if (command -v mamba &> /dev/null || command -v conda &> /dev/null) && \
       [[ -f "$PROJECT_ROOT/environment.yml" ]]; then
        echo -e "  ${BLUE}→ ./scripts/claude-mpm would use Mamba${NC}"
    else
        echo -e "  ${BLUE}→ ./scripts/claude-mpm would use venv${NC}"
    fi
}

setup_mamba() {
    echo -e "${CYAN}Setting up Mamba environment...${NC}\n"
    
    # Check if Mamba/Conda is installed
    if ! (command -v mamba &> /dev/null || command -v conda &> /dev/null); then
        echo -e "${RED}Error: Mamba/Conda not installed${NC}"
        echo -e "${YELLOW}Install Mambaforge from:${NC}"
        echo "  https://github.com/conda-forge/miniforge"
        exit 1
    fi
    
    # Check environment.yml
    if [[ ! -f "$PROJECT_ROOT/environment.yml" ]]; then
        echo -e "${RED}Error: environment.yml not found${NC}"
        exit 1
    fi
    
    # Determine conda command
    if command -v mamba &> /dev/null; then
        CONDA_CMD="mamba"
    else
        CONDA_CMD="conda"
    fi
    
    # Create or update environment
    if $CONDA_CMD env list | grep -q "^claude-mpm "; then
        echo -e "${YELLOW}Updating existing environment...${NC}"
        $CONDA_CMD env update -n claude-mpm -f "$PROJECT_ROOT/environment.yml" --prune
    else
        echo -e "${YELLOW}Creating new environment...${NC}"
        $CONDA_CMD env create -f "$PROJECT_ROOT/environment.yml"
    fi
    
    echo -e "\n${GREEN}✓ Mamba environment ready${NC}"
    echo -e "Use: ${BLUE}./scripts/claude-mpm-mamba${NC} or just ${BLUE}./scripts/claude-mpm${NC}"
}

setup_venv() {
    echo -e "${CYAN}Setting up Python venv...${NC}\n"
    
    # Create venv if it doesn't exist
    if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "$PROJECT_ROOT/venv"
    fi
    
    # Activate and install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
    pip install --upgrade pip --quiet
    pip install -e "$PROJECT_ROOT[dev]" --quiet
    deactivate
    
    echo -e "\n${GREEN}✓ venv ready${NC}"
    echo -e "Use: ${BLUE}./scripts/claude-mpm --use-venv${NC}"
}

clean_all() {
    echo -e "${RED}Warning: This will remove all environments!${NC}"
    echo -n "Are you sure? (y/N): "
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cleaning environments...${NC}"
        
        # Remove venv
        if [[ -d "$PROJECT_ROOT/venv" ]]; then
            echo "  Removing venv..."
            rm -rf "$PROJECT_ROOT/venv"
        fi
        
        # Remove Mamba environment
        if command -v mamba &> /dev/null && mamba env list | grep -q "^claude-mpm "; then
            echo "  Removing Mamba environment..."
            mamba env remove -n claude-mpm -y
        elif command -v conda &> /dev/null && conda env list | grep -q "^claude-mpm "; then
            echo "  Removing Conda environment..."
            conda env remove -n claude-mpm -y
        fi
        
        echo -e "${GREEN}✓ All environments removed${NC}"
    else
        echo -e "${YELLOW}Cancelled${NC}"
    fi
}

# Main logic
case "${1:-help}" in
    mamba)
        setup_mamba
        ;;
    venv)
        setup_venv
        ;;
    status)
        check_status
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_help
        exit 1
        ;;
esac