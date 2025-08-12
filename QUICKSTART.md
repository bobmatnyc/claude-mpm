# Claude MPM Quick Start Guide

Get up and running with Claude Multi-agent Project Manager in 5 minutes!

## Prerequisites

- Python 3.8+
- Claude API access (via Claude CLI)

## Installation

```bash
# Install from PyPI
pip install claude-mpm

# Install with development dependencies
pip install "claude-mpm[dev]"
```

## Basic Usage

### 1. Interactive Mode (Default)
Start an interactive session with Claude:

```bash
claude-mpm
```

### 2. Non-Interactive Mode
Run a single command:

```bash
claude-mpm run -i "analyze this codebase and suggest improvements"
```

### 3. Resume Previous Session
Continue where you left off:

```bash
# Resume last session
claude-mpm run --resume

# Resume specific session
claude-mpm run --resume SESSION_ID
```

## Key Features

### Multi-Agent System
Claude MPM automatically delegates tasks to specialized agents:
- **PM Agent**: Orchestrates and manages tasks
- **Research Agent**: Analyzes codebases and gathers information
- **Engineer Agent**: Implements code changes
- **QA Agent**: Tests and validates changes
- **Documentation Agent**: Creates and updates documentation
- **Security Agent**: Security analysis and compliance
- **Ops Agent**: Deployment and infrastructure
- **Data Engineer Agent**: Data pipelines and AI integrations
- **Test Integration Agent**: E2E testing and cross-system validation
- **Version Control Agent**: Git workflows and release management

### Session Management
- All work is tracked in sessions
- Resume sessions anytime with `--resume`
- View session history with `claude-mpm sessions`

### Monitoring Dashboard (Optional)
View real-time activity with the monitoring dashboard:

```bash
claude-mpm run --monitor
```

This opens a web dashboard showing:
- Live agent activity
- File operations
- Tool usage
- Session management

## Common Commands

```bash
# Start with monitoring
claude-mpm run --monitor

# Non-interactive with input
claude-mpm run -i "your task here" --non-interactive

# Show system information
claude-mpm info

# Show version
claude-mpm --version

# Get help
claude-mpm --help
```

## Working with Multiple Projects

The monitoring dashboard supports per-session working directories:
1. Start with `--monitor`
2. Select a session from the dropdown
3. Click the 📁 icon to change working directory
4. Git operations will use the session's directory

## Agent Memory System

Claude MPM agents learn and improve over time with persistent memory:

```bash
# Initialize project-specific memories
claude-mpm memory init

# View memory status
claude-mpm memory status

# Add specific learning
claude-mpm memory add engineer pattern "Use src/ layout for Python packages"
```

See [docs/MEMORY.md](docs/MEMORY.md) for comprehensive memory documentation.

## Next Steps

- Read the full [README](README.md) for detailed documentation
- Explore [Agent Memory System](docs/MEMORY.md) for persistent learning
- Check out [monitoring guide](docs/developer/11-dashboard/README.md) for dashboard features
- See [architecture docs](docs/STRUCTURE.md) for project structure
- Review [deployment guide](docs/DEPLOY.md) for publishing

## Troubleshooting

### Connection Issues
If you see connection errors with `--monitor`:
- Check if port 8765 is available
- Try a different port: `--websocket-port 8080`
- Socket.IO dependencies are included by default

### Session Issues
If sessions aren't resuming properly:
- Use full session ID: `claude-mpm run --resume <session-id>`
- Check that the session directory exists
- Sessions are stored in working directory

### Git Diff Not Working
If git diff viewer shows "No git history":
- Ensure you're in a git repository
- Check the working directory is set correctly
- Verify the file is tracked by git

## Getting Help

- Report issues: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- Read docs: [Documentation](docs/)
- Check examples: [Examples](examples/)