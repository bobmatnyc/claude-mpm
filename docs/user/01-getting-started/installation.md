# Installation Guide

This guide covers installing Claude MPM on your system.

## System Requirements

- **Operating System**: macOS, Linux, or Windows (with WSL)
- **Python**: 3.8 or higher
- **Claude CLI**: Must be installed and accessible
- **Git**: For cloning the repository
- **Memory**: At least 4GB RAM recommended
- **Storage**: 500MB free space

## Quick Installation

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-mpm.git
cd claude-mpm

# Run the installation script
./install_dev.sh

# Activate the virtual environment
source venv/bin/activate
```

## Manual Installation

If you prefer manual setup or the script doesn't work:

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/claude-mpm.git
cd claude-mpm
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Claude MPM in development mode
pip install -e .

# This automatically installs:
# - pexpect (for interactive mode)
# - psutil (for process monitoring)
# - And other dependencies
```

### 4. Verify Installation

```bash
# Check Claude MPM is installed
claude-mpm --version

# Verify Claude CLI is available
which claude

# Test basic functionality
claude-mpm info
```

## Platform-Specific Notes

### macOS

If using Homebrew Python, you might encounter PEP 668 restrictions. Solutions:

1. **Use the virtual environment** (recommended):
   ```bash
   source venv/bin/activate
   ```

2. **Use pipx for global tools**:
   ```bash
   brew install pipx
   pipx install pexpect
   ```

### Linux

Most distributions work out of the box. Ensure Python 3.8+ is installed:

```bash
python3 --version
```

### Windows

Use WSL (Windows Subsystem for Linux) for the best experience:

1. Install WSL2
2. Install Ubuntu or your preferred distribution
3. Follow the Linux installation steps

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

## Troubleshooting Installation

### "claude: command not found"

Claude CLI must be installed separately. Visit [Claude's website](https://claude.ai) for installation instructions.

### "ModuleNotFoundError: No module named 'claude_mpm'"

Ensure you're in the virtual environment:
```bash
source venv/bin/activate
```

Or reinstall in development mode:
```bash
pip install -e .
```

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
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Updating Claude MPM

To update to the latest version:

```bash
cd claude-mpm
git pull
pip install -e . --upgrade
```

## Uninstalling

To remove Claude MPM:

```bash
# Deactivate virtual environment
deactivate

# Remove the directory
cd ..
rm -rf claude-mpm

# Remove any global aliases or PATH modifications
```

## Next Steps

- Continue to [First Run](first-run.md) to start using Claude MPM
- Read about [Core Concepts](concepts.md) to understand how it works
- Check out the [Basic Usage Guide](../02-guides/basic-usage.md) for common tasks