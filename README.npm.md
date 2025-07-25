# @bobmatnyc/claude-mpm

Claude Multi-Agent Project Manager - NPM wrapper for the Python package.

This package provides a convenient way to install and run claude-mpm without manually installing the Python package.

## Requirements

- **Claude Code** 1.0.60 or later
- **Python** 3.8 or later  
- **pip** (Python package manager)

## Installation

```bash
npm install -g @bobmatnyc/claude-mpm
```

## Usage

After installation, you can run claude-mpm from any directory:

```bash
# Interactive mode
claude-mpm

# Non-interactive mode
claude-mpm -i "Your prompt here"

# With specific options
claude-mpm --help
```

## How it Works

This npm package is a wrapper that:
1. Checks for Python and Claude Code prerequisites
2. Automatically installs the Python `claude-mpm` package via pip on first run
3. Runs the Python package with your provided arguments

## Features

- **Multi-Agent Orchestration**: Delegate tasks to specialized agents
- **Native Claude Code Integration**: Works seamlessly with Claude Code's agent system
- **System Instruction Loading**: Automatically loads PM framework instructions
- **Agent Deployment**: Deploys specialized agents (engineer, qa, research, etc.)

## Documentation

For full documentation, visit: https://github.com/bobmatnyc/claude-mpm

## License

MIT © Bob Matsuoka