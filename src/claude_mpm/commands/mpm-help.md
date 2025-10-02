# Show help for available MPM commands

Display help information for Claude MPM slash commands and CLI capabilities.

## Usage

```
/mpm-help [command]
```

## Description

This slash command delegates to the **PM agent** to provide comprehensive help information about available MPM commands and capabilities.

## Implementation

This slash command delegates to the **PM agent** to show help information.

When you run `/mpm-help [command]`, the PM will:
1. List all available slash commands if no command specified
2. Show detailed help for a specific command if provided
3. Include usage examples and options
4. Explain what each command does and when to use it

## Examples

### Show All Commands
```
/mpm-help
```

Shows a complete list of all available MPM slash commands with brief descriptions.

### Show Command-Specific Help
```
/mpm-help doctor
/mpm-help agents
/mpm-help config
/mpm-help organize
```

Shows detailed help for a specific command including:
- Full description
- Available options and flags
- Usage examples
- Related commands

## Expected Output

### General Help
```
Claude MPM Slash Commands
=========================

Available Commands:

/mpm-help [command]
  Show this help or help for specific command

/mpm-status
  Display system status and environment information

/mpm-doctor [--fix] [--verbose]
  Diagnose and fix common issues

/mpm-agents [list|deploy|remove] [name]
  Manage agent deployment

/mpm-config [validate|view|status]
  Manage configuration settings

/mpm-tickets [list|create|update]
  Manage project tickets

/mpm-organize [--dry-run] [--force]
  Organize project file structure

/mpm-init
  Initialize or update project documentation

Use '/mpm-help <command>' for detailed help on a specific command.
```

### Command-Specific Help
```
/mpm-doctor - Diagnose and Fix Issues
======================================

Description:
  Runs comprehensive diagnostics on your Claude MPM installation
  and project setup. Can automatically fix common issues.

Usage:
  /mpm-doctor [options]

Options:
  --fix       Automatically fix detected issues
  --verbose   Show detailed diagnostic output

Examples:
  /mpm-doctor              # Run diagnostics
  /mpm-doctor --fix        # Run and fix issues
  /mpm-doctor --verbose    # Show detailed output

What it checks:
  - Python environment and dependencies
  - Configuration file validity
  - Agent deployment status
  - Service availability (WebSocket, Hooks)
  - Memory system integrity
  - Git repository status

Related Commands:
  /mpm-status   Show current system status
  /mpm-config   Manage configuration
```

## Related Commands

- All other `/mpm-*` commands - Access help for any command
- Standard Claude `--help` flag - CLI-level help