# Installation Guide

This guide covers all methods for installing Claude MPM on your system.

## System Requirements

- **Operating System**: macOS, Linux, or Windows (with WSL)
- **Python**: 3.8 or higher
- **Claude Code**: Version 1.0.60 or later
- **Memory**: At least 4GB RAM recommended
- **Storage**: 500MB free space

## Installation Methods

Claude MPM can be installed in three ways, depending on your needs:

### Option 1: UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast Python package installer that handles virtual environments automatically.

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install claude-mpm
uv pip install claude-mpm

# Or for development
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
uv pip install -e .
```

### Option 2: pip (Traditional)

Using pip with a virtual environment:

```bash
# Create and activate virtual environment
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate  # On Windows: claude-mpm-env\Scripts\activate

# Install claude-mpm
pip install claude-mpm

# Or for development
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
pip install -e .
```

### Option 3: npm (Wrapper)

The npm package provides a convenient wrapper that will install the Python package on first run:

```bash
# Install globally
npm install -g @bobmatnyc/claude-mpm

# The wrapper will install Python dependencies on first run
claude-mpm
```

**Note**: The npm package is just a wrapper - it still requires Python 3.8+ to be installed on your system.

## Development Installation

For contributing or modifying Claude MPM:

```bash
# Clone the repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Run the development installation script
./install_dev.sh

# This script will:
# - Create a virtual environment
# - Install all dependencies
# - Set up development tools
```

## Verifying Installation

After installation, verify everything is working:

```bash
# Check Claude MPM version
claude-mpm --version

# Verify Claude Code is available
claude --version

# Test basic functionality
claude-mpm info

# Run a simple test
claude-mpm run -i "Say hello" --non-interactive
```

## Platform-Specific Notes

### macOS

If using Homebrew Python, you might encounter PEP 668 restrictions. Solutions:

1. **Use UV** (recommended):
   ```bash
   brew install uv
   uv pip install claude-mpm
   ```

2. **Use a virtual environment**:
   ```bash
   python -m venv claude-mpm-env
   source claude-mpm-env/bin/activate
   pip install claude-mpm
   ```

3. **Use pipx for global tools**:
   ```bash
   brew install pipx
   pipx install claude-mpm
   ```

### Linux

Most distributions work out of the box. Ensure Python 3.8+ is installed:

```bash
python3 --version
```

For UV installation on Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

Use WSL (Windows Subsystem for Linux) for the best experience:

1. Install WSL2
2. Install Ubuntu or your preferred distribution
3. Follow the Linux installation steps

Native Windows support requires:
- Python 3.8+ from python.org
- Git Bash or PowerShell
- Manual PATH configuration

## Post-Installation Setup

### 1. Configure Claude CLI Path

If Claude CLI isn't in your PATH:

```bash
# Add to your shell configuration (.bashrc, .zshrc, etc.)
export PATH="/path/to/claude:$PATH"
```

### 2. Set Up Aliases (Optional)

Add convenient aliases to your shell configuration:

```bash
# Quick access to claude-mpm
alias cmpm='claude-mpm'

# Interactive mode
alias claude-interactive='claude-mpm'
```

### 3. Python Version Management (Optional)

For consistent Python versions across projects, create a `.python-version` file:

```bash
echo "3.11" > ~/.python-version
```

UV and pyenv will respect this file automatically.

## Troubleshooting Installation

### "claude: command not found"

Claude CLI must be installed separately. Visit [Claude's website](https://claude.ai/code) for installation instructions.

### "ModuleNotFoundError: No module named 'claude_mpm'"

Ensure you're in the correct environment:

**UV users:**
```bash
uv pip list | grep claude-mpm
```

**pip users:**
```bash
source claude-mpm-env/bin/activate
pip list | grep claude-mpm
```

### Python Version Issues

Check your Python version:
```bash
python --version
```

If it's below 3.8, install a newer version:
- **macOS**: `brew install python@3.11`
- **Ubuntu/Debian**: `sudo apt install python3.11`
- **Other**: Download from [python.org](https://python.org)

### Permission Errors

Make scripts executable:
```bash
chmod +x install_dev.sh
chmod +x claude-mpm
chmod +x scripts/*
```

### Virtual Environment Issues

If the virtual environment is corrupted:
```bash
# Remove and recreate
rm -rf venv claude-mpm-env
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate
pip install claude-mpm
```

### UV-Specific Issues

If UV commands fail:
```bash
# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear UV cache
uv cache clean

# Try installation again
uv pip install claude-mpm
```

## Updating Claude MPM

### Using UV:
```bash
uv pip install --upgrade claude-mpm
```

### Using pip:
```bash
pip install --upgrade claude-mpm
```

### Using npm:
```bash
npm update -g @bobmatnyc/claude-mpm
```

### From source:
```bash
cd claude-mpm
git pull
pip install -e . --upgrade
```

## Uninstalling

### UV:
```bash
uv pip uninstall claude-mpm
```

### pip:
```bash
pip uninstall claude-mpm
```

### npm:
```bash
npm uninstall -g @bobmatnyc/claude-mpm
```

### Complete removal:
```bash
# Remove virtual environments
rm -rf venv claude-mpm-env

# Remove the cloned directory
cd ..
rm -rf claude-mpm

# Remove any global aliases or PATH modifications
```

## Next Steps

- Continue to [First Run](first-run.md) to start using Claude MPM
- Read about [Core Concepts](concepts.md) to understand how it works
- Check out the [Basic Usage Guide](../02-guides/basic-usage.md) for common tasks