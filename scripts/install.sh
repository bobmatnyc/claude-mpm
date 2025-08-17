#!/bin/bash
# Local installation script for claude-mpm

set -e

echo "🚀 Installing claude-mpm locally..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Python not found. Please install Python 3.8 or higher.${NC}"
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        echo -e "${RED}❌ Python 3.8 or higher is required (found $PYTHON_VERSION)${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"
}

# Check Claude CLI
check_claude() {
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}✓ Found Claude CLI${NC}"
    else
        echo -e "${YELLOW}⚠️  Claude CLI not found. Please install it to use claude-mpm.${NC}"
        echo "  Visit: https://docs.anthropic.com/claude/docs/claude-cli"
    fi
}

# Create virtual environment
create_venv() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --quiet --upgrade pip
}

# Install package
install_package() {
    echo "Installing claude-mpm in development mode..."
    pip install -e ".[dev]"

    echo -e "${GREEN}✓ Installed claude-mpm${NC}"
}

# Create symlinks
create_symlinks() {
    # Get the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Create local bin directory if it doesn't exist
    mkdir -p "$HOME/.local/bin"

    # Create claude-mpm symlink
    if [ -f "$HOME/.local/bin/claude-mpm" ]; then
        rm "$HOME/.local/bin/claude-mpm"
    fi
    ln -s "$SCRIPT_DIR/claude-mpm" "$HOME/.local/bin/claude-mpm"
    chmod +x "$HOME/.local/bin/claude-mpm"

    # Create ticket symlink
    if [ -f "$HOME/.local/bin/ticket" ]; then
        rm "$HOME/.local/bin/ticket"
    fi
    ln -s "$SCRIPT_DIR/ticket" "$HOME/.local/bin/ticket"
    chmod +x "$HOME/.local/bin/ticket"

    echo -e "${GREEN}✓ Created command symlinks${NC}"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo -e "${YELLOW}⚠️  Add $HOME/.local/bin to your PATH:${NC}"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "    Add this to your ~/.bashrc or ~/.zshrc"
    fi
}

# Initialize directories
initialize_directories() {
    echo "Initializing directories..."
    $PYTHON_CMD -c "from claude_mpm.init import ensure_directories; ensure_directories()"
    echo -e "${GREEN}✓ Initialized directories${NC}"
}

# Main installation
main() {
    echo "===================================="
    echo "Claude MPM Local Installation"
    echo "===================================="
    echo

    # Change to script directory
    cd "$( dirname "${BASH_SOURCE[0]}" )"

    # Run checks
    check_python
    check_claude

    # Install
    create_venv
    install_package
    create_symlinks
    initialize_directories

    echo
    echo -e "${GREEN}✨ Installation complete!${NC}"
    echo
    echo "Usage:"
    echo "  claude-mpm              # Interactive mode"
    echo "  claude-mpm -i \"prompt\"  # Non-interactive mode"
    echo "  ticket create \"Fix bug\" # Create a ticket"
    echo
    echo "Documentation: https://github.com/claude-mpm/claude-mpm"
}

# Run main
main "$@"
