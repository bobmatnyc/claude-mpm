#!/bin/bash
# Development installation script for claude-mpm

echo "Installing claude-mpm in development mode..."

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

# Note: tree-sitter dependencies are automatically installed
# - tree-sitter>=0.21.0 for core parsing functionality
# - tree-sitter-language-pack>=0.8.0 for 41+ language support

echo ""
echo "✅ Development installation complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  python run_tests.py"
echo ""
echo "To run claude-mpm:"
echo "  claude-mpm --help"