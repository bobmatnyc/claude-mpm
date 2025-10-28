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
- Python 3.8 or higher
- Claude Code CLI (not Claude Desktop app)
- Install Claude Code from https://claude.ai/code

**Recommended:**
- pipx for isolated installation
- Git for version control features

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
