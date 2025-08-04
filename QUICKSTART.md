# Claude MPM Quick Start Guide

Get up and running with Claude Multi-agent Project Manager in 5 minutes!

## Prerequisites

- Python 3.8+
- Claude API access (via Claude CLI)

## Installation

```bash
# Install from PyPI
pip install claude-mpm

# Or install with monitoring support
pip install "claude-mpm[monitor]"
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

# List recent sessions
claude-mpm sessions

# Show version
claude-mpm version

# Get help
claude-mpm --help
```

## Working with Multiple Projects

The monitoring dashboard supports per-session working directories:
1. Start with `--monitor`
2. Select a session from the dropdown
3. Click the 📁 icon to change working directory
4. Git operations will use the session's directory

## Next Steps

- Read the full [README](README.md) for detailed documentation
- Check out [monitoring guide](docs/monitoring.md) for dashboard features
- See [architecture docs](docs/STRUCTURE.md) for project structure
- Review [deployment guide](docs/DEPLOY.md) for publishing

## Troubleshooting

### Connection Issues
If you see connection errors with `--monitor`:
- Check if port 8765 is available
- Try a different port: `--websocket-port 8080`
- Ensure Socket.IO dependencies are installed: `pip install "claude-mpm[monitor]"`

### Session Issues
If sessions aren't resuming properly:
- Check session exists: `claude-mpm sessions`
- Use full session ID if needed
- Sessions are stored in `~/.claude-mpm/sessions/`

### Git Diff Not Working
If git diff viewer shows "No git history":
- Ensure you're in a git repository
- Check the working directory is set correctly
- Verify the file is tracked by git

## Getting Help

- Report issues: [GitHub Issues](https://github.com/Anthropic/claude-mpm/issues)
- Read docs: [Documentation](docs/)
- Check examples: [Examples](examples/)