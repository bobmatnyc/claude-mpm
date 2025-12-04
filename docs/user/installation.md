# Installation Guide

Complete installation guide for Claude MPM across all supported platforms and methods.

## Prerequisites

### Required

1. **Claude Code CLI v1.0.92+** (NOT Claude Desktop)
   ```bash
   # Check version
   claude --version

   # Install if needed
   # https://docs.anthropic.com/en/docs/claude-code
   ```

2. **Python 3.11+** (required for kuzu-memory dependency)
   ```bash
   # Check version
   python --version
   ```

### Optional (Recommended)

- **pipx** for isolated installation
- **kuzu-memory** for advanced memory management
- **mcp-vector-search** for semantic code search

## Installation Methods

### Method 1: pipx (Recommended)

**Best for**: Most users, isolated environments

```bash
# Install pipx if not already installed
python -m pip install pipx
python -m pipx ensurepath

# Install Claude MPM with monitoring
pipx install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
claude-mpm doctor
```

**Advantages:**
- ✅ Isolated environment prevents conflicts
- ✅ Automatic PATH configuration
- ✅ Easy upgrades: `pipx upgrade claude-mpm`
- ✅ Clean uninstall: `pipx uninstall claude-mpm`

### Method 2: pip

**Best for**: Virtual environments, development

```bash
# Install with monitoring (recommended)
pip install "claude-mpm[monitor]"

# Or basic installation
pip install claude-mpm

# Verify installation
claude-mpm --version
claude-mpm doctor
```

**Advantages:**
- ✅ Works in virtual environments
- ✅ Compatible with requirements.txt
- ✅ Standard Python workflow

### Method 3: Homebrew (macOS)

**Best for**: macOS users preferring Homebrew

```bash
# Install from official tap
brew tap bobmatnyc/tools
brew install claude-mpm

# Verify installation
claude-mpm --version
claude-mpm doctor
```

**Advantages:**
- ✅ Native macOS package management
- ✅ Automatic dependency resolution
- ✅ Easy updates: `brew upgrade claude-mpm`

### Method 4: From Source

**Best for**: Developers, contributors

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Install in development mode
pip install -e ".[dev,monitor]"

# Run tests
make test

# Verify installation
claude-mpm --version
```

**Advantages:**
- ✅ Latest development version
- ✅ Contribute to project
- ✅ Custom modifications

## Optional Dependencies

### Monitoring Dashboard

```bash
# Install with monitoring (recommended)
pipx install "claude-mpm[monitor]"
```

**Includes:**
- Socket.IO for real-time events
- Web dashboard for live monitoring
- Performance metrics tracking

### MCP Services (Advanced)

```bash
# Most users don't need this
pipx install "claude-mpm[mcp]"
```

**Includes:**
- Additional MCP servers
- mcp-browser for web automation
- mcp-ticketer for issue tracking

## Recommended Partner Products

### kuzu-memory (Strongly Recommended)

Advanced memory management with knowledge graphs:

```bash
pipx install kuzu-memory
```

**Benefits:**
- 🧠 Persistent project knowledge
- 🎯 Intelligent prompt enrichment
- 📊 Structured storage
- 🔄 Seamless integration

### mcp-vector-search (Strongly Recommended)

Semantic code search:

```bash
pipx install mcp-vector-search
```

**Benefits:**
- 🔍 Search by intent, not keywords
- 🎯 Context-aware discovery
- ⚡ Fast indexing
- 📊 Pattern recognition

### Verify Installation

```bash
# Verify all MCP services
claude-mpm verify

# Auto-fix issues
claude-mpm verify --fix
```

## Post-Installation

### 1. Run Diagnostics

```bash
# Comprehensive health check
claude-mpm doctor

# Verbose output
claude-mpm doctor --verbose

# Generate report
claude-mpm doctor --verbose --output-file doctor-report.md
```

### 2. Initial Configuration

```bash
# Auto-configure for your project
claude-mpm auto-configure

# Or interactive configuration
claude-mpm configure
```

### 3. Initialize Memory

```bash
# Initialize agent memory
claude-mpm memory init
```

### 4. Test Run

```bash
# Start interactive session
claude-mpm

# Or with monitoring
claude-mpm run --monitor
```

## Platform-Specific Notes

### macOS

**Recommended Installation:**
```bash
# Using pipx (recommended)
pipx install "claude-mpm[monitor]"

# Or using Homebrew
brew install bobmatnyc/tools/claude-mpm
```

**Common Issues:**
- Permission errors: Use pipx or `--user` flag
- PATH issues: Run `pipx ensurepath`

### Linux

**Recommended Installation:**
```bash
# Install pipx first
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Claude MPM
pipx install "claude-mpm[monitor]"
```

**Required System Packages:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# RHEL/CentOS
sudo yum install python3-devel

# Arch
sudo pacman -S python
```

### Windows

**Recommended Installation:**
```bash
# Using pipx (recommended)
python -m pip install pipx
python -m pipx ensurepath

# Install Claude MPM
pipx install "claude-mpm[monitor]"
```

**Common Issues:**
- PATH issues: Add Python Scripts to PATH
- Permission errors: Run as administrator or use `--user`

## Upgrading

### From PyPI (pipx)

```bash
# Upgrade Claude MPM
pipx upgrade claude-mpm

# Upgrade with new optional dependencies
pipx install --force "claude-mpm[monitor]"
```

### From PyPI (pip)

```bash
# Upgrade Claude MPM
pip install --upgrade claude-mpm

# Or with monitoring
pip install --upgrade "claude-mpm[monitor]"
```

### From Homebrew

```bash
# Update formula
brew update

# Upgrade package
brew upgrade claude-mpm
```

### From Source

```bash
# Pull latest changes
git pull origin main

# Reinstall
pip install -e ".[dev,monitor]"
```

## Uninstallation

### Using pipx

```bash
pipx uninstall claude-mpm
```

### Using pip

```bash
pip uninstall claude-mpm
```

### Using Homebrew

```bash
brew uninstall claude-mpm
brew untap bobmatnyc/tools
```

### Clean Up Configuration

```bash
# Remove user configuration (optional)
rm -rf ~/.claude-mpm/

# Remove project configuration
rm -rf .claude-mpm/
```

## Troubleshooting Installation

### Claude Code Not Found

```bash
# Install Claude Code CLI
# https://docs.anthropic.com/en/docs/claude-code

# Verify installation
claude --version
```

### Permission Errors

```bash
# Use pipx (recommended)
pipx install "claude-mpm[monitor]"

# Or install in user directory
pip install --user "claude-mpm[monitor]"
```

### Import Errors

```bash
# Reinstall with dependencies
pipx install --force "claude-mpm[monitor]"

# Or clear cache
pip cache purge
pip install --force-reinstall "claude-mpm[monitor]"
```

### PATH Issues

```bash
# Add to PATH (pipx)
pipx ensurepath

# Add to PATH (manual)
export PATH="$HOME/.local/bin:$PATH"
```

See [Troubleshooting Guide](troubleshooting.md) for more solutions.

## Verification Checklist

After installation, verify:

- [ ] `claude-mpm --version` shows version
- [ ] `claude-mpm doctor` passes all checks
- [ ] `claude --version` shows v1.0.92+
- [ ] `claude-mpm verify` shows MCP services
- [ ] `claude-mpm run` starts successfully

## Next Steps

- **[Quick Start](quickstart.md)** - Get running in 5 minutes
- **[User Guide](user-guide.md)** - Learn all features
- **[Configuration](../configuration.md)** - Configure for your needs
- **[FAQ](../guides/FAQ.md)** - Common questions

---

**Need help?** See [Troubleshooting Guide](troubleshooting.md) or run `claude-mpm doctor --verbose`
