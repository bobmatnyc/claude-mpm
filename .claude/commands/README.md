# Claude MPM Slash Commands

This directory contains slash command definitions for Claude MPM.

## Overview

Slash commands allow you to execute specific actions without going through the LLM. They are processed directly by the claude-mpm framework.

## Available Commands

### `/mpm:test`
- **Description**: A simple test command that returns "Hello World"
- **Usage**: `/mpm:test`
- **Purpose**: Demonstrates the slash command system

## Implementation

Commands are handled in two ways:

1. **Command Router** (`.claude/scripts/command_router.py`): A standalone Python script that can execute commands independently
2. **Simple Runner Integration** (`src/claude_mpm/core/simple_runner.py`): Intercepts `/mpm:` commands before they reach Claude

## Adding New Commands

To add a new slash command:

1. Add the command handler to the command router
2. Create a markdown file in the appropriate subdirectory (e.g., `.claude/commands/mpm/mycommand.md`)
3. Optionally update the `_handle_mpm_command` method in simple_runner.py for direct integration

## Future Enhancements

- Hook-based command processing for better modularity
- Command discovery and auto-registration
- Rich command output formatting
- Command history and logging