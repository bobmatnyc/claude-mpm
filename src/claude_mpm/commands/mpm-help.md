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

/mpm-auto-configure [--preview] [--yes]
  🤖 NEW! Automatically configure agents based on your project

/mpm-agents-detect
  🤖 NEW! Detect project toolchain and frameworks

/mpm-agents-recommend
  🤖 NEW! Show recommended agents for your project

/mpm-config [validate|view|status]
  Manage configuration settings

/mpm-tickets [list|create|update]
  Manage project tickets

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

### /mpm-agents-detect - Toolchain Detection

**Description:**
Scans your project to detect programming languages, frameworks, tools, and configuration files.

**Usage:**
```
/mpm-agents-detect
```

**Output:**
- Detected languages and versions
- Frameworks and their configurations
- Testing tools and test frameworks
- Build tools and bundlers
- Package managers
- Deployment configurations

**Example:**
```
/mpm-agents-detect

Detected Project Stack:
======================
Languages: Python 3.11, Node.js 20.x
Frameworks: FastAPI 0.104.0, React 18.2.0
Testing: pytest, Playwright
Build: Vite 5.0.0
Package Manager: poetry, npm
Deployment: Docker, Vercel
```

### /mpm-agents-recommend - Agent Recommendations

**Description:**
Based on detected toolchain, shows which agents are recommended for your project with explanations.

**Usage:**
```
/mpm-agents-recommend
```

**Output:**
- Recommended agents with rationale
- Agent capabilities and when to use them
- Suggested deployment order
- Complementary agent combinations

**Example:**
```
/mpm-agents-recommend

Recommended Agents for Your Project:
===================================

Essential Agents:
✓ fastapi-engineer - Detected FastAPI framework
✓ python-engineer - Python 3.11 project
✓ api-qa - API testing and validation

Recommended Agents:
○ react-engineer - React frontend detected
○ web-qa - Web UI testing
○ playwright-qa - Playwright tests found

Optional Agents:
○ docker-ops - Docker configuration found
○ vercel-ops - Vercel deployment detected
```

## Quick Start with Auto-Configuration

For new projects or first-time setup:

1. **Preview what would be configured:**
   ```
   /mpm-auto-configure --preview
   ```

2. **Review recommendations:**
   ```
   /mpm-agents-recommend
   ```

3. **Apply configuration:**
   ```
   /mpm-auto-configure
   ```

Or skip straight to auto-apply:
```
/mpm-auto-configure --yes
```

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