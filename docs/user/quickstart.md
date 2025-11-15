# 5-Minute Quick Start

Get Claude MPM running in 5 minutes or less.

## Prerequisites Check

```bash
# 1. Verify Claude Code CLI (required!)
claude --version
# Should show v1.0.92 or higher

# 2. Verify Python
python --version
# Should show 3.8 or higher (3.11+ recommended)
```

**Don't have Claude Code?** Install from: https://docs.anthropic.com/en/docs/claude-code

## Installation (1 minute)

```bash
# Install with monitoring (recommended)
pipx install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
```

## First Run (2 minutes)

```bash
# Run diagnostics
claude-mpm doctor

# Start interactive mode
claude-mpm

# Or start with monitoring dashboard
claude-mpm run --monitor
# Dashboard opens at http://localhost:5000
```

## Quick Configuration (1 minute)

```bash
# Auto-configure for your project
claude-mpm auto-configure

# Or use interactive configuration
claude-mpm configure
```

## Your First Task (1 minute)

```bash
# Start a session
claude-mpm run

# Example tasks to try:
# - "Analyze this codebase and suggest improvements"
# - "Create comprehensive tests for module X"
# - "Refactor function Y following best practices"
# - "Document the API endpoints"
```

## What's Next?

- **[Complete User Guide](user-guide.md)** - Learn all features
- **[Installation Guide](installation.md)** - Detailed installation options
- **[FAQ](../guides/FAQ.md)** - Common questions answered
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Quick Reference

```bash
# Core commands
claude-mpm run [--monitor]     # Start session
claude-mpm configure            # Interactive configuration
claude-mpm doctor               # System diagnostics
claude-mpm verify               # Verify MCP services

# Session management
claude-mpm mpm-init pause       # Pause session
claude-mpm mpm-init resume      # Resume session

# Memory management
claude-mpm memory init          # Initialize agent memory
claude-mpm cleanup-memory       # Clean conversation history

# Code search (installs mcp-vector-search on first use)
claude-mpm search "query"       # Semantic code search
```

## Recommended Partner Products

Install these for enhanced capabilities (optional but recommended):

```bash
# Advanced memory management
pipx install kuzu-memory

# Semantic code search
pipx install mcp-vector-search

# Verify installation
claude-mpm verify
```

## Getting Help

- **Quick answers**: [FAQ](../guides/FAQ.md)
- **Detailed guide**: [User Guide](user-guide.md)
- **Issues?**: [Troubleshooting](troubleshooting.md)
- **Diagnostics**: `claude-mpm doctor --verbose`

---

**Ready to dive deeper?** See the [Complete User Guide](user-guide.md) for comprehensive documentation.
