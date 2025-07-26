#!/usr/bin/env bash
# Enhanced local deployment script for claude-mpm
# Provides comprehensive setup, verification, and convenience features

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "\n${BOLD}${BLUE}===================================="
    echo -e "$1"
    echo -e "====================================${NC}\n"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_step() {
    echo -e "${CYAN}→${NC} $1"
}

# Detect shell type
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_TYPE="zsh"
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_TYPE="bash"
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_TYPE="unknown"
        SHELL_RC=""
    fi
}

# Check Python version
check_python() {
    print_step "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
    
    print_success "Found Python $PYTHON_VERSION"
}

# Check Claude CLI
check_claude() {
    print_step "Checking Claude CLI..."
    
    if command -v claude &> /dev/null; then
        print_success "Found Claude CLI"
    else
        print_warning "Claude CLI not found. You'll need it to use claude-mpm."
        echo "         Visit: https://docs.anthropic.com/claude/docs/claude-cli"
        echo -e "         Or run: ${CYAN}pip install claude-cli${NC}"
    fi
}

# Check if already installed
check_existing_installation() {
    print_step "Checking for existing installation..."
    
    if [ -d "$PROJECT_ROOT/venv" ] && [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
        # Check if claude-mpm is installed in the venv
        if "$PROJECT_ROOT/venv/bin/python" -c "import claude_mpm" 2>/dev/null; then
            print_warning "claude-mpm is already installed in virtual environment"
            
            # Skip prompt if --force flag is set
            if [ "${FORCE_INSTALL:-false}" = "true" ]; then
                print_info "Force flag set, reinstalling..."
                return 0
            fi
            
            echo -n "Would you like to reinstall? [y/N] "
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                echo "Skipping installation."
                return 1
            fi
        fi
    fi
    
    return 0
}

# Create or update virtual environment
setup_virtual_environment() {
    print_step "Setting up virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists"
        # Ensure it's using the correct Python version
        VENV_PYTHON_VERSION=$("$PROJECT_ROOT/venv/bin/python" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if [ "$VENV_PYTHON_VERSION" != "$PYTHON_VERSION" ]; then
            print_warning "Virtual environment Python version ($VENV_PYTHON_VERSION) differs from system ($PYTHON_VERSION)"
            
            if [ "${FORCE_INSTALL:-false}" = "true" ]; then
                print_info "Force flag set, recreating virtual environment..."
                rm -rf venv
                $PYTHON_CMD -m venv venv
                print_success "Recreated virtual environment with Python $PYTHON_VERSION"
            else
                echo -n "Would you like to recreate the virtual environment? [y/N] "
                read -r response
                if [[ "$response" =~ ^[Yy]$ ]]; then
                    rm -rf venv
                    $PYTHON_CMD -m venv venv
                    print_success "Recreated virtual environment with Python $PYTHON_VERSION"
                fi
            fi
        fi
    else
        $PYTHON_CMD -m venv venv
        print_success "Created virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_step "Upgrading pip..."
    pip install --quiet --upgrade pip
    print_success "Upgraded pip to $(pip --version | awk '{print $2}')"
}

# Install claude-mpm
install_claude_mpm() {
    print_step "Installing claude-mpm in development mode..."
    
    cd "$PROJECT_ROOT"
    
    # Install with all optional dependencies
    if pip install -e ".[dev]" > /tmp/claude_mpm_install.log 2>&1; then
        print_success "Installed claude-mpm and all dependencies"
    else
        print_warning "Some optional dependencies failed to install (this is usually fine)"
        echo "         Check /tmp/claude_mpm_install.log for details"
    fi
    
    # Verify installation
    if python -c "import claude_mpm; print(f'Version: {claude_mpm.__version__}')" 2>/dev/null; then
        print_success "Verified claude-mpm installation"
    else
        print_error "Failed to verify installation"
        exit 1
    fi
}

# Setup PATH and create convenience scripts
setup_path_and_scripts() {
    print_step "Setting up PATH and convenience scripts..."
    
    # Ensure ~/.local/bin exists
    mkdir -p "$HOME/.local/bin"
    
    # Create symlink to main script
    if [ -f "$HOME/.local/bin/claude-mpm" ]; then
        rm "$HOME/.local/bin/claude-mpm"
    fi
    ln -s "$PROJECT_ROOT/claude-mpm" "$HOME/.local/bin/claude-mpm"
    chmod +x "$HOME/.local/bin/claude-mpm"
    print_success "Created claude-mpm command"
    
    # Create ticket command if it exists
    if [ -f "$PROJECT_ROOT/ticket" ]; then
        if [ -f "$HOME/.local/bin/ticket" ]; then
            rm "$HOME/.local/bin/ticket"
        fi
        ln -s "$PROJECT_ROOT/ticket" "$HOME/.local/bin/ticket"
        chmod +x "$HOME/.local/bin/ticket"
        print_success "Created ticket command"
    fi
    
    # Check if ~/.local/bin is in PATH
    PATH_UPDATED=false
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "$HOME/.local/bin is not in your PATH"
        
        if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
            if [ "${FORCE_INSTALL:-false}" = "true" ] || { echo -n "Would you like to add it to $SHELL_RC? [Y/n] "; read -r response; [[ ! "$response" =~ ^[Nn]$ ]]; }; then
                echo "" >> "$SHELL_RC"
                echo "# Added by claude-mpm deploy_local.sh" >> "$SHELL_RC"
                echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
                print_success "Added PATH to $SHELL_RC"
                PATH_UPDATED=true
            fi
        fi
    else
        print_success "$HOME/.local/bin is already in PATH"
    fi
}

# Create shell aliases
create_aliases() {
    print_step "Setting up shell aliases..."
    
    if [ -z "$SHELL_RC" ] || [ ! -f "$SHELL_RC" ]; then
        print_warning "Could not determine shell configuration file"
        return
    fi
    
    if [ "${FORCE_INSTALL:-false}" != "true" ]; then
        echo -n "Would you like to create helpful aliases? [Y/n] "
        read -r response
        if [[ "$response" =~ ^[Nn]$ ]]; then
            return
        fi
    else
        print_info "Force flag set, creating aliases..."
    fi
    
    # Check if aliases already exist
    ALIASES_EXIST=false
    if grep -q "alias mpm=" "$SHELL_RC" 2>/dev/null; then
        ALIASES_EXIST=true
    fi
    
    if [ "$ALIASES_EXIST" = true ]; then
        print_info "Aliases already exist in $SHELL_RC"
    else
        echo "" >> "$SHELL_RC"
        echo "# claude-mpm aliases" >> "$SHELL_RC"
        echo "alias mpm='claude-mpm'" >> "$SHELL_RC"
        echo "alias mpm-run='claude-mpm run'" >> "$SHELL_RC"
        echo "alias mpm-debug='claude-mpm --debug'" >> "$SHELL_RC"
        echo "alias mpm-agents='claude-mpm agents'" >> "$SHELL_RC"
        print_success "Added aliases to $SHELL_RC"
    fi
}

# Initialize claude-mpm directories
initialize_claude_mpm() {
    print_step "Initializing claude-mpm directories..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    if python -c "from claude_mpm.init import ensure_directories; ensure_directories()" 2>/dev/null; then
        print_success "Initialized claude-mpm directories"
    else
        print_warning "Could not initialize directories (will be created on first run)"
    fi
}

# Run post-installation verification
verify_installation() {
    print_header "Verifying Installation"
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Check Python imports
    print_step "Checking Python imports..."
    IMPORTS_OK=true
    for module in "claude_mpm" "click" "pydantic"; do
        if python -c "import $module" 2>/dev/null; then
            print_success "Can import $module"
        else
            print_error "Cannot import $module"
            IMPORTS_OK=false
        fi
    done
    
    # Check claude-mpm command
    print_step "Checking claude-mpm command..."
    if "$PROJECT_ROOT/claude-mpm" --version >/dev/null 2>&1; then
        VERSION=$("$PROJECT_ROOT/claude-mpm" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        print_success "claude-mpm command works (version: $VERSION)"
    else
        print_error "claude-mpm command failed"
        IMPORTS_OK=false
    fi
    
    if [ "$IMPORTS_OK" = false ]; then
        print_error "Some verification checks failed"
        return 1
    fi
    
    return 0
}

# Show usage instructions
show_usage_instructions() {
    print_header "Installation Complete! 🎉"
    
    echo -e "${BOLD}Quick Start:${NC}"
    echo
    
    # If PATH wasn't updated in this session
    if [ "$PATH_UPDATED" = true ]; then
        echo -e "${YELLOW}Note: Reload your shell or run:${NC}"
        echo -e "  ${CYAN}source $SHELL_RC${NC}"
        echo
    fi
    
    echo -e "${BOLD}Option 1: Use the wrapper script (recommended)${NC}"
    echo -e "  ${CYAN}./claude-mpm${NC}                    # Interactive mode"
    echo -e "  ${CYAN}./claude-mpm run -i \"prompt\"${NC}    # Non-interactive mode"
    echo
    
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
        echo -e "${BOLD}Option 2: Use from anywhere${NC}"
        echo -e "  ${CYAN}claude-mpm${NC}                      # Interactive mode"
        echo -e "  ${CYAN}claude-mpm run -i \"prompt\"${NC}      # Non-interactive mode"
        echo
    fi
    
    echo -e "${BOLD}Option 3: Activate venv and use Python module${NC}"
    echo -e "  ${CYAN}source venv/bin/activate${NC}"
    echo -e "  ${CYAN}python -m claude_mpm${NC}"
    echo
    
    if grep -q "alias mpm=" "$SHELL_RC" 2>/dev/null; then
        echo -e "${BOLD}Using aliases:${NC}"
        echo -e "  ${CYAN}mpm${NC}                             # Short for claude-mpm"
        echo -e "  ${CYAN}mpm-run -i \"prompt\"${NC}             # Run command"
        echo -e "  ${CYAN}mpm-debug${NC}                       # Run with debug output"
        echo
    fi
    
    echo -e "${BOLD}Common Commands:${NC}"
    echo -e "  ${CYAN}claude-mpm agents${NC}               # List available agents"
    echo -e "  ${CYAN}claude-mpm --help${NC}               # Show help"
    echo -e "  ${CYAN}claude-mpm run --help${NC}           # Show run command options"
    echo
    
    echo -e "${BOLD}Documentation:${NC}"
    echo -e "  ${BLUE}https://github.com/claude-mpm/claude-mpm${NC}"
    echo
    
    echo -e "${BOLD}Tips:${NC}"
    echo -e "  • The virtual environment is automatically activated by the wrapper"
    echo -e "  • Use ${CYAN}--debug${NC} flag for detailed logging"
    echo -e "  • Check ${CYAN}docs/QA.md${NC} for testing guidelines"
}

# Main installation flow
main() {
    print_header "Claude MPM Enhanced Local Deployment"
    
    # Detect shell
    detect_shell
    print_info "Detected shell: $SHELL_TYPE"
    
    # Pre-flight checks
    check_python
    check_claude
    
    # Check existing installation
    if ! check_existing_installation; then
        # User chose not to reinstall
        show_usage_instructions
        exit 0
    fi
    
    # Installation steps
    setup_virtual_environment
    install_claude_mpm
    setup_path_and_scripts
    create_aliases
    initialize_claude_mpm
    
    # Verification
    if verify_installation; then
        show_usage_instructions
    else
        print_error "Installation completed with errors"
        echo "Please check the error messages above and try again"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Claude MPM Enhanced Local Deployment Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --force        Force reinstallation without prompting"
        echo ""
        echo "This script will:"
        echo "  • Check Python and Claude CLI installation"
        echo "  • Create/update virtual environment"
        echo "  • Install claude-mpm in development mode"
        echo "  • Set up PATH and create convenient aliases"
        echo "  • Verify the installation"
        echo "  • Provide usage instructions"
        exit 0
        ;;
    --force)
        # Skip confirmation prompts
        export FORCE_INSTALL=true
        ;;
esac

# Run main installation
main "$@"