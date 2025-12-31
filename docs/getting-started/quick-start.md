---
title: Getting Started
version: 4.21.1
last_updated: 2025-11-09
status: current
---

# Getting Started

Get Claude MPM running in under 5 minutes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [First Run](#first-run)
- [Auto-Configuration](#auto-configuration)
- [Essential Commands](#essential-commands)
- [What's Next](#whats-next)

## Prerequisites

**Required:**

### 1. Python Environment
- **Python 3.11 or higher** (required for kuzu-memory dependency)
- Check version: `python --version`

### 2. Claude Code (CLI)

Claude MPM **requires** Claude Code CLI (not Claude Desktop app). Claude Code is Anthropic's official command-line interface that enables terminal-based AI interactions.

**Version Requirements:**
- **Minimum**: v1.0.92 (for hooks support)
- **Recommended**: v2.0.30+ (for latest features and stability)

**Installation:**
- Install from: https://docs.anthropic.com/en/docs/claude-code
- After installation, verify: `claude --version`

**Why Claude Code is Required:**
- Claude MPM extends Claude Code's CLI capabilities
- Provides multi-agent orchestration layer
- Integrates with Claude Code's command system
- All MCP integrations work through Claude Code

**Recommended:**
- **pipx** for isolated installation
- **Git** for version control features

## Installation

### Recommended: pipx with Monitor

```bash
# Install with full dashboard functionality
pipx install "claude-mpm[monitor]"

# Or install specific version
pipx install "claude-mpm[monitor]==4.15.4"

# Upgrade existing installation
pipx upgrade claude-mpm
```

**Why `[monitor]`?** Enables the real-time dashboard that shows agent collaboration. Without it, monitoring features won't work.

### Alternative: pip

```bash
# New installation
pip install claude-mpm

# Install specific version
pip install claude-mpm==4.15.4

# Upgrade
pip install --upgrade claude-mpm
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Install in editable mode with all extras
pip install -e ".[dev,monitor]"

# Verify installation
claude-mpm --version
```

### Verify Installation

After installing Claude MPM, verify both Claude MPM and Claude Code are properly set up:

```bash
# Check Claude MPM version
claude-mpm --version

# Check Claude Code version (must be v1.0.92+)
claude --version

# Run comprehensive diagnostics
claude-mpm doctor

# Check for available updates
claude-mpm doctor --checks updates
```

**Expected Output:**
- Claude MPM version should be 5.4.68 or higher
- Claude Code version should be v1.0.92 or higher (v2.0.30+ recommended)
- Doctor command should report no critical issues

**If Claude Code is Missing:**
See [Troubleshooting - Claude Code Issues](#claude-code-issues) below.

## First Run

### Interactive Mode (Recommended)

```bash
claude-mpm
```

This opens a Claude session with multi-agent orchestration enabled.

### With Monitoring Dashboard

```bash
claude-mpm run --monitor
```

Opens dashboard at http://localhost:8765 showing real-time agent activity.

### Try Your First Task

In the Claude session, type:

```
"Analyze this project structure"
"Help me improve this code"
"Create tests for this function"
```

Watch specialized agents (Research, Engineer, QA) work together!

## Auto-Configuration

Claude MPM can automatically detect your project stack and configure appropriate agents.

```bash
# Auto-configure current project
claude-mpm auto-configure

# Preview recommendations without applying
claude-mpm auto-configure --preview

# Use lower confidence threshold
claude-mpm auto-configure --threshold 60
```

**What it detects:**
- **Languages**: Python, JavaScript, TypeScript, Go, Rust, PHP, Ruby, Java
- **Frameworks**: FastAPI, Flask, Next.js, React, Express, Laravel, Rails
- **Tools**: Docker, Kubernetes, databases, testing frameworks

**Result**: Agents are automatically deployed to `.claude-agents/` based on your stack.

## Essential Commands

### Interactive Mode

```bash
# Start interactive session
claude-mpm

# With monitoring
claude-mpm run --monitor

# Resume previous session
claude-mpm run --resume
```

### Slash Commands (in Claude Code)

These work in any Claude Code session when Claude MPM is installed:

```bash
# Initialize project
/mpm-init

# System diagnostics
/mpm-doctor

# Manage agents
/mpm-agents

# Semantic code search
/mpm-search "authentication logic"

# Pause session
/pause

# Resume session
/resume
```

### CLI Commands

```bash
# Project initialization
claude-mpm init

# Auto-configure stack
claude-mpm auto-configure

# System diagnostics
claude-mpm doctor

# Agent management
claude-mpm agents list
claude-mpm agents deploy
claude-mpm agents create <name>

# Semantic search
claude-mpm search "database connection"

# Local process management
claude-mpm local-deploy start --command "npm run dev"
claude-mpm local-deploy list
claude-mpm local-deploy stop <deployment-id>
```

## Claude Code Issues

### Claude Code Not Installed

**Problem:** `claude: command not found` or `claude-mpm doctor` reports Claude Code missing.

**Solution:**

```bash
# Install Claude Code from Anthropic
# Visit: https://docs.anthropic.com/en/docs/claude-code

# After installation, verify
claude --version

# Ensure it's in PATH (add to ~/.bashrc or ~/.zshrc if needed)
export PATH="$PATH:/path/to/claude/bin"
source ~/.bashrc  # or ~/.zshrc

# Re-run diagnostics
claude-mpm doctor
```

### Claude Code Version Too Old

**Problem:** Claude Code version is below v1.0.92.

**Solution:**

```bash
# Check current version
claude --version

# Update Claude Code (method depends on installation)
# For Homebrew (macOS):
brew upgrade claude

# For other methods, download latest from:
# https://docs.anthropic.com/en/docs/claude-code

# Verify update
claude --version  # Should show v1.0.92 or higher

# Check Claude MPM compatibility
claude-mpm doctor --checks updates
```

### Update Checking

Claude MPM automatically checks for updates on startup and verifies Claude Code compatibility.

**Configure Update Checking:**

Edit `~/.claude-mpm/configuration.yaml`:

```yaml
updates:
  check_enabled: true          # Enable/disable update checks
  check_frequency: "daily"     # always|daily|weekly|never
  check_claude_code: true      # Verify Claude Code compatibility
  auto_upgrade: false          # Auto-upgrade (use with caution)
```

**Disable Temporarily:**

```bash
# Skip update check for single command
CLAUDE_MPM_SKIP_UPDATE_CHECK=1 claude-mpm run
```

**See Also:**
- [Update Checking Documentation](../../docs/update-checking.md)
- [Troubleshooting Guide](troubleshooting.md)

## What's Next

**New Users:**
1. Read [User Guide](user-guide.md) to learn key features
2. Try auto-configuration: `claude-mpm auto-configure`
3. Explore monitoring: `claude-mpm run --monitor`
4. Set up local deployments for your development servers

**Common Next Steps:**
- Configure auto-restart for dev servers: See [User Guide - Local Process Management](user-guide.md#local-process-management)
- Set up project-specific agents: See [User Guide - Agent System](user-guide.md#agent-system)
- Learn session pause/resume: See [User Guide - Session Management](user-guide.md#session-management)
- Explore memory system: See [User Guide - Memory System](user-guide.md#memory-system)

**Need Help?**
- Common issues: [Troubleshooting](troubleshooting.md)
- Feature documentation: [User Guide](user-guide.md)
- Developer resources: [../developer/architecture.md](../developer/architecture.md)
