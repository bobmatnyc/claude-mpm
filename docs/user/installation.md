# Installation Guide

Complete installation instructions for Claude MPM across different environments and use cases.

**Last Updated**: 2025-08-29  
**Version**: 4.1.14

## Quick Install

### Basic Installation
```bash
# Quick install - all you need to get started
pip install claude-mpm
```

### Full Installation
```bash
# Install with all features and dependencies
pip install "claude-mpm[agents,dev,docs]"
```

## Installation Options

### Core Package
```bash
pip install claude-mpm
```

### Using pipx (Recommended for Isolated Installation)
```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install claude-mpm in isolated environment
pipx install claude-mpm

# Configure MCP for Claude Code (pipx users only)
claude-mpm mcp-pipx-config
```

The pipx installation method provides:
- **Isolated environment**: No dependency conflicts with other Python packages
- **Global command access**: claude-mpm commands available system-wide
- **Easy updates**: Simple upgrade with `pipx upgrade claude-mpm`
- **Clean uninstall**: Complete removal with `pipx uninstall claude-mpm`

**🎉 Pipx Now Fully Supported!** As of v4.1.14, all pipx installation issues have been resolved:

✅ **Resource Path Resolution**: Fixed Socket.IO daemon script access in pipx environments
✅ **Command Directory Access**: Resolved commands directory path resolution for pipx users  
✅ **Packaging Improvements**: All resource files (scripts, commands) now properly packaged
✅ **Python 3.13+ Compatibility**: Full support for latest Python versions in pipx

**Previous Issues Resolved:**
- **Issue**: "socketio_daemon_wrapper.py not found" error reported by users
- **Fix**: Implemented `get_package_resource_path()` for proper resource resolution
- **Issue**: Commands directory access failures in pipx environments  
- **Fix**: Enhanced path detection with `importlib.resources` fallback

For MCP configuration with pipx, see [MCP pipx Setup Guide](../MCP_PIPX_SETUP.md).

### With Agent Dependencies
```bash
# Includes tools for code analysis, testing, and development workflows
pip install "claude-mpm[agents]"
```

### With Development Tools
```bash
# Includes testing, linting, and development utilities
pip install "claude-mpm[dev]"
```

### With Documentation Tools
```bash
# Includes Sphinx and documentation building tools
pip install "claude-mpm[docs]"
```

### Complete Installation
```bash
# Everything - agents, development, and documentation tools
pip install "claude-mpm[agents,dev,docs]"
```

## Dependencies

All Claude MPM dependencies are pure Python packages - no Rust compilation or system dependencies required.

### Agent Dependencies

Claude MPM automatically manages Python dependencies required by agents. Agents can declare their dependencies in their configuration files:

```json
{
  "agent_id": "my_agent",
  "dependencies": {
    "python": ["pandas>=2.0.0", "numpy>=1.24.0"],
    "system": ["ripgrep", "git"]
  }
}
```

### View Agent Dependencies
```bash
# View current agent dependencies  
python scripts/aggregate_agent_dependencies.py --dry-run

# Update pyproject.toml with latest agent dependencies
python scripts/aggregate_agent_dependencies.py
```

Dependencies are automatically aggregated from all agent sources (PROJECT > USER > SYSTEM) with intelligent version conflict resolution.

## System Requirements

- Python 3.8+
- Claude API access (via Claude CLI)
- Git (for project management features)
- Optional: Node.js (for enhanced dashboard features)

## Platform-Specific Instructions

### macOS
```bash
# Using Homebrew (recommended)
brew install python git
pip install claude-mpm

# Using MacPorts
sudo port install python38 git
pip install claude-mpm
```

### Ubuntu/Debian
```bash
# System packages
sudo apt update
sudo apt install python3 python3-pip git

# Claude MPM
pip3 install claude-mpm
```

### Windows
```bash
# Using Chocolatey
choco install python git

# Using winget
winget install Python.Python.3 Git.Git

# Claude MPM
pip install claude-mpm
```

## Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv claude-mpm-env

# Activate (Linux/macOS)
source claude-mpm-env/bin/activate

# Activate (Windows)
claude-mpm-env\Scripts\activate

# Install
pip install "claude-mpm[agents,dev,docs]"
```

## Development Installation

For contributors and developers:

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[agents,dev,docs]"

# Run tests
./scripts/run_all_tests.sh
```

## Docker Installation

```bash
# Using Docker
docker pull claude-mpm:latest
docker run -it claude-mpm:latest

# Using docker-compose
cd docker/
docker-compose up
```

## Verification

After installation, verify everything is working:

```bash
# Check version
claude-mpm --version

# Show system information
claude-mpm info

# Quick test
claude-mpm run -i "test installation" --non-interactive
```

## Troubleshooting

### Common Issues

**Permission Errors**
```bash
# Use --user flag
pip install --user claude-mpm

# Or use virtual environment (recommended)
python -m venv venv && source venv/bin/activate
```

**Python Version Issues**
```bash
# Check Python version
python --version

# Use specific Python version
python3.9 -m pip install claude-mpm
```

**Network Issues**
```bash
# Use different index
pip install -i https://pypi.org/simple/ claude-mpm

# Upgrade pip first
pip install --upgrade pip
```

### Getting Help

- **Documentation**: [docs/user/troubleshooting.md](troubleshooting.md)
- **Issues**: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bobmatnyc/claude-mpm/discussions)

## Next Steps

After installation:

1. **Quick Start**: Follow [QUICKSTART.md](../../QUICKSTART.md) for your first session
2. **Basic Usage**: See [basic-usage.md](basic-usage.md) for common patterns
3. **Memory System**: Learn about [memory-system.md](memory-system.md) for persistent learning
4. **Configuration**: Customize with [configuration.md](../reference/configuration.md)

For comprehensive documentation, see [docs/AGENT_DEPENDENCIES.md](../AGENT_DEPENDENCIES.md).