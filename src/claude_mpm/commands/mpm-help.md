---
namespace: mpm/system
command: help
aliases: [mpm-help]
migration_target: /mpm/system:help
category: system
deprecated_aliases: []
description: Display help information for Claude MPM slash commands and CLI capabilities
---
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

/mpm-postmortem [--auto-fix] [--create-prs]
  Analyze session errors and suggest improvements

/mpm-agents [list|deploy|remove] [name]
  Manage agent deployment

/mpm-configure
  🤖 Unified configuration interface for agents, skills, and project settings

/mpm-config [validate|view|status]
  Manage configuration settings

/mpm-ticket [organize|proceed|status|update|project]
  High-level ticketing workflows and project management

/mpm-organize [--dry-run] [--force]
  Organize project file structure

/mpm-init [update]
  Initialize or update project documentation

/mpm-resume
  Create session resume files for easy work resumption

/mpm-monitor [start|stop|restart|status|port]
  Manage Socket.IO monitoring server and dashboard

/mpm-version
  Display comprehensive version information including project version, all agents with versions, and all skills with versions

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

## Auto-Configuration Commands (NEW!)

### /mpm-auto-configure - Automatic Agent Configuration

**Description:**
Automatically detects your project's toolchain and frameworks, then recommends and optionally deploys the most appropriate agents for your stack.

**Usage:**
```
/mpm-auto-configure [options]
```

**Options:**
- `--preview` - Show what would be configured without making changes
- `--yes` - Skip confirmation prompts and apply automatically
- `--force` - Force reconfiguration even if agents already deployed

**Examples:**
```
/mpm-auto-configure --preview    # Preview recommendations
/mpm-auto-configure              # Interactive configuration
/mpm-auto-configure --yes        # Auto-apply recommendations
```

**What it detects:**
- Programming languages (Python, Node.js, Rust, Go, Java)
- Frameworks (FastAPI, Flask, Next.js, React, Vue, Express)
- Testing tools (pytest, Jest, Vitest, Playwright)
- Build tools (Vite, Webpack, Rollup)
- Package managers (npm, yarn, pnpm, pip, poetry)
- Deployment platforms (Vercel, Railway, Docker)

**Recommended agents by stack:**
- **Python + FastAPI**: fastapi-engineer, python-engineer, api-qa
- **Next.js**: nextjs-engineer, react-engineer, web-qa
- **React**: react-engineer, web-qa
- **Full-stack**: Combination of backend + frontend agents
- **Testing**: playwright-qa, api-qa based on detected test tools

## Quick Start with Configuration

For new projects or first-time setup, use the unified `/mpm-configure` command which provides:
- Toolchain detection
- Agent recommendations
- Skills management
- Auto-configuration

**Usage:**
```
/mpm-configure
```

The interactive menu will guide you through:
1. Detecting your project's toolchain
2. Viewing recommended agents
3. Deploying agents and skills
4. Managing configuration settings

## Supported Technology Stacks

**Python:**
- FastAPI, Flask, Django, Starlette
- pytest, unittest
- uvicorn, gunicorn

**JavaScript/TypeScript:**
- Next.js, React, Vue, Svelte
- Express, Nest.js, Fastify
- Jest, Vitest, Playwright
- Vite, Webpack, Rollup

**Other:**
- Rust (Cargo, Actix, Rocket)
- Go (modules, Gin, Echo)
- Java (Maven, Gradle, Spring Boot)

## Related Commands

- All other `/mpm-*` commands - Access help for any command
- Standard Claude `--help` flag - CLI-level help