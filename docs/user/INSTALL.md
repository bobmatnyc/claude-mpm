# Installation Guide

Complete installation instructions for Claude MPM v4.4.x across different environments and use cases.

> **⚠️ Important**: Claude MPM extends **Claude Code (CLI)**, not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.

**Version**: 4.4.x
**Last Updated**: 2025-09-28

## System Requirements

- **Operating System**: macOS, Linux, or Windows (WSL recommended)
- **Python**: 3.8 or higher (3.11+ recommended)
- **Claude Code (CLI)**: Version 1.0.60 or later (required)
- **Memory**: At least 4GB RAM recommended
- **Storage**: 500MB free space

## Quick Start

### Recommended: UV Installation

[UV](https://github.com/astral-sh/uv) is the fastest and most reliable installation method:

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Basic installation
uv pip install claude-mpm

# Install with optional MCP services (recommended)
uv pip install "claude-mpm[mcp]"

# Verify installation
claude-mpm --version
```

### Alternative: pipx (Isolated Global Installation)

For isolated package management without virtual environment hassles:

```bash
# Install pipx if not already installed
python -m pip install --user pipx
python -m pipx ensurepath

# Basic installation
pipx install claude-mpm

# Install with all optional features (recommended)
pipx install "claude-mpm[mcp,monitor]"

# Configure MCP for pipx users
claude-mpm mcp-pipx-config
```

## Optional Dependencies

Claude MPM offers several optional dependency groups that can be combined:

| Dependency Group | Description | Packages Included | Auto-Install |
|-----------------|-------------|------------------|--------------|
| `[mcp]` | MCP services for external tool integration | mcp, mcp-vector-search, mcp-browser, mcp-ticketer | ✅ Interactive on first use |
| `[monitor]` | Real-time monitoring dashboard | python-socketio, aiohttp, websockets, aiofiles | ❌ Manual install only |
| `[dev]` | Development tools | pytest, black, flake8, mypy, ruff | ❌ Manual install only |
| `[docs]` | Documentation building | sphinx, sphinx-rtd-theme | ❌ Manual install only |

**Note**:
- kuzu-memory is now a required dependency and is installed automatically with Claude MPM
- mcp-vector-search offers interactive installation on first use when not pre-installed
- Other optional MCP services install automatically without prompts (legacy behavior)

### Installing Multiple Optional Groups

You can combine multiple optional dependency groups using comma separation:

```bash
# Install with MCP services only
pip install "claude-mpm[mcp]"

# Install with monitoring only
pip install "claude-mpm[monitor]"

# Install with BOTH MCP and monitoring (recommended for full features)
pip install "claude-mpm[mcp,monitor]"

# Install with all development dependencies
pip install "claude-mpm[mcp,monitor,dev,docs]"

# Using pipx (recommended for global installation)
pipx install "claude-mpm[mcp,monitor]"

# Using UV (fastest)
uv pip install "claude-mpm[mcp,monitor]"
```

### Common Installation Scenarios

| Use Case | Installation Command | What You Get |
|----------|---------------------|--------------|
| Basic CLI only | `pip install claude-mpm` | Core Claude MPM functionality + kuzu-memory |
| With AI tools | `pip install "claude-mpm[mcp]"` | + MCP services, vector search |
| With dashboard | `pip install "claude-mpm[monitor]"` | + Real-time monitoring web interface |
| **Full features** | `pip install "claude-mpm[mcp,monitor]"` | All features enabled (recommended) |
| Development | `pip install "claude-mpm[mcp,monitor,dev]"` | + Testing and linting tools |

## Installation Methods

### Method 1: UV (Recommended)

**Best for**: Most users, handles virtual environments automatically

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Basic installation
uv pip install claude-mpm

# Install with optional MCP services (recommended)
uv pip install "claude-mpm[mcp]"

# Install with all features
uv pip install "claude-mpm[mcp,monitor]"

# For development
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
uv pip install -e ".[mcp,monitor,dev]"
```

**Advantages**:
- Fastest installation
- Automatic virtual environment management
- Best dependency resolution
- Works across all platforms

### Method 2: pipx (Isolated Installation)

**Best for**: Global tools, avoiding dependency conflicts

```bash
# Install pipx
python -m pip install --user pipx
python -m pipx ensurepath

# Basic installation
pipx install claude-mpm

# Install with MCP services (recommended)
pipx install "claude-mpm[mcp]"

# Install with all features
pipx install "claude-mpm[mcp,monitor]"

# Configure MCP services
claude-mpm mcp-pipx-config
```

**Advantages**:
- Clean isolation from other Python packages
- Global command access
- Easy updates with `pipx upgrade claude-mpm`
- Complete removal with `pipx uninstall claude-mpm`

### Method 3: pip (Traditional)

**Best for**: Existing Python workflows, custom environments

```bash
# Create virtual environment (recommended)
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate  # Windows: claude-mpm-env\Scripts\activate

# Basic installation
pip install claude-mpm

# Install with MCP services (recommended)
pip install "claude-mpm[mcp]"

# Install with all features
pip install "claude-mpm[mcp,monitor,agents,dev,docs]"
```

**Optional Dependencies**:
- `claude-mpm[mcp]`: Include MCP services (mcp-vector-search, mcp-browser, mcp-ticketer)
- `claude-mpm[monitor]`: Include real-time monitoring features
- `claude-mpm[agents]`: Include agent analysis tools
- `claude-mpm[dev]`: Include development and testing tools
- `claude-mpm[docs]`: Include documentation tools

**Note**: kuzu-memory is now a required dependency, installed automatically with all installation methods.

### Method 4: npm (Wrapper)

**Best for**: Node.js-centric workflows

```bash
# Install globally
npm install -g @bobmatnyc/claude-mpm

# The wrapper installs Python dependencies on first run
claude-mpm
```

**Note**: This is a wrapper around the Python package. Python 3.8+ must be installed separately.

## Platform-Specific Instructions

### macOS

**Homebrew users (PEP 668 restrictions)**:

```bash
# Option 1: Use UV (recommended)
brew install uv
uv pip install claude-mpm

# Option 2: Use pipx
brew install pipx
pipx install "claude-mpm[monitor]"

# Option 3: Virtual environment
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate
pip install claude-mpm
```

### Linux

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip git

# Install via UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install claude-mpm

# Or via pip
pip3 install claude-mpm
```

### Windows

**WSL (Recommended)**:
1. Install WSL2 with Ubuntu
2. Follow Linux instructions above

**Native Windows**:
```powershell
# Install Python from python.org
# Install Git from git-scm.com

# Install claude-mpm
pip install claude-mpm
```

## Development Installation

For contributors and developers:

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Auto-install with environment detection
./install_dev.sh

# Manual setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[agents,dev,docs,monitor]"

# Run tests
make quality
./scripts/run_all_tests.sh
```

## Verification

After installation, verify everything works:

```bash
# Check version
claude-mpm --version

# Verify Claude Code is available
claude --version

# Show system information
claude-mpm info

# Quick test
claude-mpm run -i "test installation" --non-interactive

# Interactive mode
claude-mpm
```

## Usage Overview

### Interactive Mode (Default)

```bash
claude-mpm
```

Launches Claude Code (CLI) with:
- Project Manager orchestration framework
- Deployed specialized agents (engineer, qa, researcher, etc.)
- Automatic MCP service installation and configuration
- Persistent knowledge management with project-specific databases
- Real-time monitoring and event tracking

### Non-Interactive Mode

```bash
claude-mpm run -i "Your task description" --non-interactive
```

### Common Options

```bash
# Disable agent deployment
claude-mpm --no-native-agents

# Enable debug logging
claude-mpm --logging DEBUG

# Disable hooks and monitoring
claude-mpm --no-hooks

# Show all available commands
claude-mpm --help
```

## MCP Services Overview

Claude MPM v4.4.x includes optional MCP (Model Context Protocol) services that enhance functionality:

### Available MCP Services

#### mcp-vector-search
- **Purpose**: Intelligent code search and project indexing
- **Features**: Semantic code search, project analysis, similarity detection
- **Database**: Project-specific vector indices
- **Installation**: Optional - auto-installs on first use with interactive prompt
- **Auto-Install**: On first use of search features, you'll be prompted to choose:
  - Install via pip (recommended for this project)
  - Install via pipx (isolated, system-wide)
  - Skip (use traditional grep/glob instead)

#### kuzu-memory
- **Purpose**: Persistent knowledge management with graph database
- **Features**: Project context storage, conversation history, learning retention
- **Database**: Project-specific graph database
- **Installation**: Now included as required dependency with Claude MPM

### Installation Options

#### Option 1: Include MCP Services (Recommended)
```bash
# Install with MCP services as dependencies (includes kuzu-memory automatically)
pip install "claude-mpm[mcp]"
# or
pipx install "claude-mpm[mcp]"
# or
uv pip install "claude-mpm[mcp]"
```

**Benefits**: All features ready immediately, no installation prompts during work

#### Option 2: Basic Installation with Interactive Auto-Install
```bash
# Basic installation - includes kuzu-memory, mcp-vector-search installs on first use
pip install claude-mpm
```

**First-Use Experience**: When you first use search features (e.g., `/mpm-search`), you'll see:

```
⚠️  mcp-vector-search not found
This package enables semantic code search (optional feature).

Installation options:
  1. Install via pip (recommended for this project)
  2. Install via pipx (isolated, system-wide)
  3. Skip (use traditional grep/glob instead)

Choose option (1/2/3) [3]:
```

**How It Works**:
- Claude MPM automatically detects missing services when you try to use them
- Interactive prompt offers installation choices
- pip installation: Installs in current Python environment
- pipx installation: Creates isolated environment (better for global tools)
- Skip: Falls back gracefully to grep/glob search methods
- kuzu-memory is always available (required dependency)

**Fallback Behavior**: Without mcp-vector-search, the system uses traditional search:
- Research agent uses grep and glob for code discovery
- Search command suggests grep alternatives
- All core functionality continues to work

### Troubleshooting MCP Installation

#### Auto-Install Issues

If the interactive auto-install prompt doesn't appear or fails:

```bash
# Check MCP service status
claude-mpm doctor --checks mcp

# Manual installation via pip (current environment)
pip install mcp-vector-search

# Manual installation via pipx (isolated environment)
pipx install mcp-vector-search

# Configure MCP services for pipx users
claude-mpm mcp-pipx-config

# Verify installation
claude-mpm doctor --checks mcp --verbose
```

**Common Auto-Install Problems**:

1. **"Installation failed" during auto-install**
   - Try manual installation: `pip install mcp-vector-search`
   - Check pip/pipx is up to date: `pip install --upgrade pip`
   - Verify network connectivity and PyPI access

2. **"pipx is not installed" when choosing option 2**
   - Install pipx first: `python -m pip install --user pipx`
   - Then run: `pipx ensurepath`
   - Restart terminal and try again

3. **Auto-install prompt not appearing**
   - Feature may already be installed: `pip list | grep mcp-vector-search`
   - Try running `/mpm-search --status` to trigger detection
   - Check if search is working without prompts

4. **"Installation timed out"**
   - Network may be slow or blocked
   - Try manual installation with longer timeout
   - Check corporate firewall/proxy settings

5. **Prefer to skip auto-install entirely**
   - Choose option 3 when prompted
   - System will use grep/glob fallback methods
   - Functionality continues without vector search

## Troubleshooting

### Common Issues

**"claude: command not found"**
- Install Claude Code (CLI) 1.0.60+ from https://claude.ai/code
- Ensure Claude Code CLI is in your PATH

**"Python not found"**
- **macOS**: `brew install python@3.11`
- **Ubuntu/Debian**: `sudo apt install python3.11`
- **Windows**: Download from https://python.org

**PEP 668 "externally managed environment" error**
1. Use UV (handles virtual environments automatically)
2. Use pipx for isolated installation
3. Create a virtual environment manually

**"ModuleNotFoundError: No module named 'claude_mpm'"**
- Ensure correct environment is activated
- Verify installation: `pip list | grep claude-mpm`
- Try reinstalling: `pip install --force-reinstall claude-mpm`

**Permission errors**
- Use `--user` flag: `pip install --user claude-mpm`
- Or use pipx/UV for better isolation
- Make scripts executable: `chmod +x scripts/*`

**"claude-mpm: command not found" with pipx**
- Ensure pipx PATH is configured: `pipx ensurepath`
- Restart terminal or reload shell: `source ~/.bashrc` (Linux) or `source ~/.zshrc` (macOS)
- Check pipx installation: `pipx list`
- Alternative: Use full path: `~/.local/bin/claude-mpm`

**MCP services not installing automatically**
- Check pipx is available: `which pipx`
- Install pipx if missing: `python -m pip install --user pipx`
- Manual service installation: `pipx install mcp-vector-search mcp-browser mcp-ticketer`
- Use diagnostic command: `claude-mpm doctor --checks mcp --verbose`
- Note: kuzu-memory is included with Claude MPM (no separate installation needed)

**Network/firewall issues**
- Try different index: `pip install -i https://pypi.org/simple/ claude-mpm`
- Update pip first: `pip install --upgrade pip`
- Check corporate firewall settings

### Platform-Specific Issues

**macOS Monterey+ Security**
- Allow terminal full disk access in System Preferences
- Use `sudo` for global installations if needed

**Windows WSL**
- Ensure WSL2 is enabled
- Install Windows Terminal for better experience
- Set WSL as default for better performance

**Linux Package Conflicts**
- Use virtual environments or pipx
- Update system packages: `sudo apt update && sudo apt upgrade`

## Updates

### UV
```bash
uv pip install --upgrade claude-mpm
```

### pipx
```bash
pipx upgrade claude-mpm
```

### pip
```bash
pip install --upgrade claude-mpm
```

### npm
```bash
npm update -g @bobmatnyc/claude-mpm
```

### Development
```bash
cd claude-mpm
git pull
pip install -e . --upgrade
```

## Uninstalling

### UV
```bash
uv pip uninstall claude-mpm
```

### pipx
```bash
pipx uninstall claude-mpm
```

### pip
```bash
pip uninstall claude-mpm
```

### npm
```bash
npm uninstall -g @bobmatnyc/claude-mpm
```

### Complete Removal
```bash
# Remove virtual environments
rm -rf venv claude-mpm-env

# Remove optional MCP services
pipx uninstall mcp-vector-search mcp-browser mcp-ticketer
# Note: kuzu-memory is part of Claude MPM and uninstalled with it

# Remove project databases (optional)
rm -rf ~/.claude-mpm
```

## Next Steps

1. **Quick Start**: Follow the [Getting Started Guide](01-getting-started/README.md)
2. **First Run**: See [First Run Guide](01-getting-started/first-run.md) for initial setup
3. **Basic Usage**: Learn common patterns in [Basic Usage](02-guides/basic-usage.md)
4. **Memory System**: Understand [Kuzu-Memory Integration](03-features/kuzu-memory.md)
5. **Configuration**: Customize with [Configuration Guide](04-reference/configuration.md)

## Getting Help

- **Documentation**: [User Guide](README.md) | [Troubleshooting](04-reference/troubleshooting.md)
- **Issues**: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bobmatnyc/claude-mpm/discussions)
- **Support**: Check [FAQ](faq.md) for common questions