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
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TOB_ORG="the-original-body"
TOB_REPO="https://github.com/$TOB_ORG/claude-mpm"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
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

check_command python3
check_command git

# Check/install pipx
if ! command -v pipx &> /dev/null; then
    log_warn "pipx not found. Installing..."
    if command -v brew &> /dev/null; then
        brew install pipx
        pipx ensurepath
        log_success "pipx installed via Homebrew"
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y pipx
        pipx ensurepath
        log_success "pipx installed via apt"
    else
        log_info "Installing pipx via pip..."
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
        log_success "pipx installed via pip"
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

echo ""

# =============================================================================
# 1. Install Claude MPM (TOB Fork)
# =============================================================================

log_info "=== Installing Claude MPM (TOB Fork) ==="

log_info "Installing from $TOB_REPO..."
if pipx install "git+$TOB_REPO.git" --force; then
    log_success "claude-mpm installed"
else
    log_error "Failed to install claude-mpm"
    exit 1
fi

echo ""

# =============================================================================
# 2. Add TOB Skills Source
# =============================================================================

log_info "=== Adding TOB Skills Source ==="

if claude-mpm skill-source add "https://github.com/$TOB_ORG/tob-skills" 2>/dev/null; then
    log_success "TOB skills source added"
else
    log_warn "Could not add TOB skills source - may already exist"
fi

echo ""

# =============================================================================
# 3. Enable MCP Services
# =============================================================================

log_info "=== Enabling MCP Services ==="

for service in kuzu-memory mcp-vector-search mcp-ticketer mcp-skillset; do
    log_info "Enabling $service..."
    if claude-mpm mcp enable "$service" --global 2>/dev/null; then
        log_success "$service enabled"
    else
        log_warn "$service could not be enabled - may need manual setup"
    fi
done

echo ""

# =============================================================================
# 4. Sync Agents and Skills
# =============================================================================

log_info "=== Syncing Agents and Skills ==="

log_info "Syncing agents..."
claude-mpm agent sync 2>/dev/null || log_warn "Agent sync failed - run: claude-mpm agent sync"

log_info "Syncing skills..."
claude-mpm skill sync 2>/dev/null || log_warn "Skill sync failed - run: claude-mpm skill sync"

echo ""

# =============================================================================
# Summary
# =============================================================================

echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
log_success "Claude MPM installed from TOB fork"
log_success "Skill sources configured:"
echo "         - bobmatnyc/claude-mpm-skills (default)"
echo "         - anthropics/skills (default)"
echo "         - $TOB_ORG/tob-skills (TOB custom)"
log_success "MCP services enabled:"
echo "         - kuzu-memory"
echo "         - mcp-vector-search"
echo "         - mcp-ticketer"
echo "         - mcp-skillset"
echo ""
echo "Next steps:"
echo "  1. Run 'claude-mpm doctor' to verify installation"
echo "  2. Restart Claude Code to load new agents/skills"
echo ""
echo "Useful commands:"
echo "  claude-mpm --help          Show all commands"
echo "  claude-mpm agent list      List available agents"
echo "  claude-mpm skill list      List available skills"
echo "  claude-mpm mcp list        List MCP services"
echo "  claude-mpm doctor          Check installation health"
echo ""
