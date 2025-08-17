#!/bin/bash
# Development installation script for claude-mpm

echo "Installing claude-mpm in development mode..."

# Check if UV is available
if command -v uv &> /dev/null; then
    echo "✅ UV detected - using UV for installation (recommended)"

    # Install with UV in development mode
    uv pip install -e ".[dev]"

    # Install ai-trackdown-pytools if available
    uv pip install ai-trackdown-pytools || echo "Warning: ai-trackdown-pytools not available"

    echo ""
    echo "✅ Development installation complete with UV!"
    echo ""
    echo "UV automatically manages virtual environments."
    echo "No need to activate a venv - just run:"
    echo "  claude-mpm --help"

elif command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    echo "⚠️  UV not found - falling back to pip"
    echo "   Consider installing UV for better performance:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install in editable mode with dev dependencies
    pip install -e ".[dev]"

    # Install ai-trackdown-pytools if available
    pip install ai-trackdown-pytools || echo "Warning: ai-trackdown-pytools not available"

    echo ""
    echo "✅ Development installation complete!"
    echo ""
    echo "To activate the virtual environment:"
    echo "  source venv/bin/activate"

else
    echo "❌ Error: Neither UV nor pip found!"
    echo ""
    echo "Please install Python package management:"
    echo "  Option 1 (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  Option 2: Ensure Python 3.8+ is installed with pip"
    exit 1
fi

# Note: tree-sitter dependencies are automatically installed
# - tree-sitter>=0.21.0 for core parsing functionality
# - tree-sitter-language-pack>=0.8.0 for 41+ language support

echo ""
echo "To run tests:"
echo "  python run_tests.py"
echo ""
echo "To run claude-mpm:"
echo "  claude-mpm --help"
echo ""
echo "For more information:"
echo "  See docs/user/01-getting-started/installation.md"
