#!/bin/bash
# =============================================================================
# The Original Body - Claude MPM Setup Script
# =============================================================================
# One-liner install:
#   curl -fsSL https://raw.githubusercontent.com/the-original-body/claude-mpm/main/scripts/tob-setup.sh | bash
#
# Prerequisites:
#   - Python 3.11+
#   - Git
#
# Note: pipx will be installed automatically if not present
# Note: WSL users must enable Developer Mode in Windows for symlinks to work
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TOB_ORG="the-original-body"
TOB_REPO="https://github.com/$TOB_ORG/claude-mpm"
UPSTREAM_ORG="bobmatnyc"
MCP_SERVICES=(kuzu-memory mcp-vector-search mcp-ticketer mcp-skillset)

# Error tracking
ERRORS=0
WARNINGS=0
declare -a FAILED_ITEMS=()
declare -a WARNED_ITEMS=()

# =============================================================================
# Helper Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
    WARNED_ITEMS+=("$1")
}
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((ERRORS++))
    FAILED_ITEMS+=("$1")
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed"
        return 1
    fi
    log_success "$1 found"
}

# =============================================================================
# Prerequisites Check
# =============================================================================

echo ""
echo "=============================================="
echo "  The Original Body - Claude MPM Setup"
echo "=============================================="
echo ""

log_info "Checking prerequisites..."

check_command python3 || exit 1
check_command git || exit 1

# Check/install pipx
if ! command -v pipx &> /dev/null; then
    log_info "pipx not found. Installing..."
    if command -v brew &> /dev/null; then
        if brew install pipx && pipx ensurepath; then
            log_success "pipx installed via Homebrew"
        else
            log_error "Failed to install pipx via Homebrew"
            exit 1
        fi
    elif command -v apt-get &> /dev/null; then
        if sudo apt-get update && sudo apt-get install -y pipx && pipx ensurepath; then
            log_success "pipx installed via apt"
        else
            log_error "Failed to install pipx via apt"
            exit 1
        fi
    else
        log_info "Installing pipx via pip..."
        if python3 -m pip install --user pipx && python3 -m pipx ensurepath; then
            log_success "pipx installed via pip"
        else
            log_error "Failed to install pipx via pip"
            exit 1
        fi
    fi
    export PATH="$HOME/.local/bin:$PATH"
else
    log_success "pipx found"
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    log_success "Python $PYTHON_VERSION meets requirement (3.11+)"
else
    log_error "Python $PYTHON_VERSION is too old. Need 3.11+"
    exit 1
fi

# Detect WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    log_warn "WSL detected - ensure Developer Mode is enabled in Windows Settings for symlinks"
fi

echo ""

# =============================================================================
# 1. Install Claude MPM (TOB Fork)
# =============================================================================

log_info "=== Installing Claude MPM (TOB Fork) ==="

log_info "Installing from $TOB_REPO..."
if pipx install "git+$TOB_REPO.git" --force; then
    log_success "claude-mpm installed"
    CLAUDE_MPM_OK=true
else
    log_error "Failed to install claude-mpm"
    CLAUDE_MPM_OK=false
fi

echo ""

# Only continue if claude-mpm installed successfully
if [ "$CLAUDE_MPM_OK" != "true" ]; then
    log_error "Cannot continue without claude-mpm. Exiting."
    exit 1
fi

# =============================================================================
# 2. Add TOB Skills Source
# =============================================================================

log_info "=== Adding TOB Skills Source ==="

# Use SSH URL for private repo (requires SSH key configured with GitHub)
TOB_SKILLS_URL="git@github.com:$TOB_ORG/tob-skills.git"

if claude-mpm skill-source add "$TOB_SKILLS_URL" 2>/dev/null; then
    log_success "TOB skills source added"
    TOB_SKILLS_OK=true
else
    log_warn "Could not add TOB skills source (may already exist or need SSH keys)"
    TOB_SKILLS_OK=false
fi

echo ""

# =============================================================================
# 3. Install and Enable MCP Services
# =============================================================================

log_info "=== Installing MCP Services ==="

MCP_INSTALLED=0
MCP_ENABLED=0

for service in "${MCP_SERVICES[@]}"; do
    log_info "Installing $service..."
    if pipx install "git+https://github.com/$UPSTREAM_ORG/$service.git" --force 2>/dev/null; then
        log_success "$service installed"
        ((MCP_INSTALLED++))
    else
        log_warn "$service installation failed"
    fi
done

log_info "=== Enabling MCP Services ==="

for service in "${MCP_SERVICES[@]}"; do
    log_info "Enabling $service..."
    if claude-mpm mcp enable "$service" --global 2>/dev/null; then
        log_success "$service enabled"
        ((MCP_ENABLED++))
    else
        log_warn "$service could not be enabled"
    fi
done

echo ""

# =============================================================================
# 4. Sync Agents and Skills
# =============================================================================

log_info "=== Syncing Agents and Skills ==="

log_info "Syncing agents..."
if claude-mpm agent sync 2>/dev/null; then
    log_success "Agents synced"
    AGENTS_OK=true
else
    log_warn "Agent sync had issues"
    AGENTS_OK=false
fi

log_info "Syncing skills..."
if claude-mpm skill sync 2>/dev/null; then
    log_success "Skills synced"
    SKILLS_OK=true
else
    log_warn "Skill sync had issues"
    SKILLS_OK=false
fi

echo ""

# =============================================================================
# Summary
# =============================================================================

echo "=============================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "  ${GREEN}Setup Complete!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "  ${YELLOW}Setup Complete with Warnings${NC}"
else
    echo -e "  ${RED}Setup Complete with Errors${NC}"
fi
echo "=============================================="
echo ""

# Claude MPM status
if [ "$CLAUDE_MPM_OK" = "true" ]; then
    log_success "Claude MPM installed from TOB fork"
else
    log_error "Claude MPM installation failed"
fi

# Skills status
echo ""
echo "Skill sources:"
echo "  - bobmatnyc/claude-mpm-skills (default)"
echo "  - anthropics/skills (default)"
if [ "$TOB_SKILLS_OK" = "true" ]; then
    echo -e "  - ${GREEN}$TOB_ORG/tob-skills (added)${NC}"
else
    echo -e "  - ${YELLOW}$TOB_ORG/tob-skills (not added - SSH keys required)${NC}"
fi

# MCP status
echo ""
echo "MCP services: ${MCP_INSTALLED}/${#MCP_SERVICES[@]} installed, ${MCP_ENABLED}/${#MCP_SERVICES[@]} enabled"
for service in "${MCP_SERVICES[@]}"; do
    echo "  - $service"
done

# Sync status
echo ""
echo "Sync status:"
if [ "$AGENTS_OK" = "true" ]; then
    echo -e "  - ${GREEN}Agents: OK${NC}"
else
    echo -e "  - ${YELLOW}Agents: Issues (run: claude-mpm agent sync)${NC}"
fi
if [ "$SKILLS_OK" = "true" ]; then
    echo -e "  - ${GREEN}Skills: OK${NC}"
else
    echo -e "  - ${YELLOW}Skills: Issues (run: claude-mpm skill sync)${NC}"
fi

# Summary counts
echo ""
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Errors: $ERRORS${NC}"
fi
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
fi

echo ""
echo "Next steps:"
echo "  1. Run 'claude-mpm doctor' to verify installation"
echo "  2. Restart Claude Code to load new agents/skills"
if [ $WARNINGS -gt 0 ] || [ $ERRORS -gt 0 ]; then
    echo "  3. Review warnings/errors above and fix manually if needed"
fi
echo ""
echo "Useful commands:"
echo "  claude-mpm --help          Show all commands"
echo "  claude-mpm agent list      List available agents"
echo "  claude-mpm skill list      List available skills"
echo "  claude-mpm mcp list        List MCP services"
echo "  claude-mpm doctor          Check installation health"
echo ""
