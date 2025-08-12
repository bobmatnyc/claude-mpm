# @bobmatnyc/claude-mpm

> **Note**: This project is a fork of [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm), enhanced to integrate with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) v1.0.60+'s native agent system. This integration enables seamless orchestration of Claude Code's built-in agents (research, engineer, qa, documentation, security, ops, version_control, data_engineer) through a unified project management interface.

Claude Multi-Agent Project Manager - NPM wrapper for the Python package.

## Important: Python Requirement

**This npm package is a wrapper that requires Python 3.8+ to be installed on your system.** The actual claude-mpm implementation is written in Python, and this npm package provides a convenient installer and launcher.

## Requirements

- **Claude Code** 1.0.60 or later
- **Python** 3.8 or later (REQUIRED)
- **Package Manager**: UV (recommended), pip, or pipx

## Installation

```bash
npm install -g @bobmatnyc/claude-mpm
```

On first run, the wrapper will automatically install the Python package using available package managers.

## What This Package Does

This npm package:
1. Checks for Python and Claude Code prerequisites
2. Automatically installs the Python `claude-mpm` package on first run
3. Provides a convenient `claude-mpm` command that runs the Python implementation
4. Handles UV, pipx, or pip installation based on your system

## Usage

After installation, you can run claude-mpm from any directory:

```bash
# Interactive mode
claude-mpm

# Non-interactive mode
claude-mpm run -i "Your prompt here" --non-interactive

# With specific options
claude-mpm --help
```

## Alternative Installation Methods

If you prefer to install the Python package directly:

### Using UV (Recommended)
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install claude-mpm
uv pip install claude-mpm
```

### Using pip
```bash
# Create virtual environment
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate

# Install claude-mpm
pip install claude-mpm
```

### Using pipx
```bash
pipx install claude-mpm
```

## Features

- **Multi-Agent Orchestration**: Delegate tasks to specialized agents
- **Native Claude Code Integration**: Works seamlessly with Claude Code's agent system
- **System Instruction Loading**: Automatically loads PM framework instructions
- **Agent Deployment**: Deploys specialized agents (engineer, qa, research, etc.)
- **Hook System**: Extensible architecture for custom functionality
- **Ticket Management**: Built-in issue tracking system

## Documentation

For full documentation, visit: https://github.com/bobmatnyc/claude-mpm

## Troubleshooting

### Python Not Found

If you see "Python not found" errors, install Python 3.8+:
- macOS: `brew install python@3.11`
- Ubuntu/Debian: `sudo apt install python3.11`
- Windows: Download from https://python.org

### Installation Fails

If automatic installation fails, install the Python package manually:
```bash
uv pip install claude-mpm  # or pip install claude-mpm
```

## License

MIT © Bob Matsuoka