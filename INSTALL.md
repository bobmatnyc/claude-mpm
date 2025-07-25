# Installation Guide

Claude MPM can be installed via npm or pip. Both methods provide the same functionality.

## Prerequisites

- **Claude Code** 1.0.60 or later (required)
- **Python** 3.8 or later
- **pip** (Python package manager)

## Option 1: Install via npm (Recommended)

The npm package provides a wrapper that automatically installs the Python package:

```bash
npm install -g @bobmatnyc/claude-mpm
```

## Option 2: Install via pip

Direct Python installation:

```bash
pip install claude-mpm
```

## Verify Installation

After installation, verify it works:

```bash
# Show version and help
claude-mpm --help

# Test in interactive mode
claude-mpm
```

## Usage

### Interactive Mode (Default)

```bash
claude-mpm
```

This launches Claude Code with the PM framework loaded, including:
- System instructions for orchestration
- Deployed specialized agents (engineer, qa, research, etc.)
- Delegation-only operation mode

### Non-Interactive Mode

```bash
claude-mpm -i "Your task here"
```

### Common Options

```bash
# Disable agent deployment
claude-mpm --no-native-agents

# Enable debug logging
claude-mpm --logging DEBUG

# Disable hooks
claude-mpm --no-hooks
```

## Terminal UI Mode

Claude MPM includes a terminal UI that shows Claude output, ToDo lists, and tickets in separate panes:

```bash
# Launch with rich UI (requires pip install claude-mpm[ui])
claude-mpm --mpm:ui

# Launch with basic curses UI
claude-mpm --mpm:ui --mode curses
```

### Terminal UI Features

- **Claude Output Pane**: Live Claude interaction
- **ToDo List Pane**: Shows current tasks from Claude's todo system
- **Tickets Pane**: Browse and create tickets
- **Keyboard Shortcuts**:
  - `Tab`: Switch between panes
  - `F5`: Refresh ToDo and ticket lists
  - `N`: Create new ticket (when in tickets pane)
  - `Q`: Quit

### Installing UI Dependencies

For the best terminal UI experience:

```bash
pip install claude-mpm[ui]
```

## Troubleshooting

### "claude: command not found"

Install Claude Code 1.0.60+ from https://claude.ai/code

### "Python not found"

Install Python 3.8+ from https://python.org

### npm install fails

Ensure you have Node.js 14+ installed. The npm package is just a wrapper - the actual functionality requires Python.

## Uninstalling

### npm
```bash
npm uninstall -g @bobmatnyc/claude-mpm
```

### pip
```bash
pip uninstall claude-mpm
```