---
namespace: mpm/config
command: config
aliases: [mpm-config]
migration_target: /mpm/config
category: config
deprecated_aliases: [mpm-config-view]
description: Unified configuration management with auto-detection and manual viewing
---
# Unified configuration management

Manage Claude MPM configuration with auto-detection, manual viewing, validation, and status checks.

## Usage

```
/mpm-config [subcommand] [options]
/mpm-config              # No args = auto (detect + recommend + preview)
/mpm-config view         # Show current config
/mpm-config auto         # Auto-configure: detect → recommend → deploy (with confirmation)
/mpm-config auto --yes   # Auto-deploy without confirmation
```

## Description

This unified command provides comprehensive configuration management:

1. **Auto-configuration** (default): Detect toolchain and recommend agents/skills
2. **Manual viewing**: Display current configuration settings
3. **Validation**: Ensure configuration correctness
4. **Status checks**: Show system health

## Subcommands

### Auto-Configure (Default)

Automatically detect project toolchain and configure appropriate agents and skills.

```
/mpm-config              # Preview recommendations (default)
/mpm-config auto         # Same as no args - detect and preview
/mpm-config auto --yes   # Auto-deploy without confirmation
```

**What it does:**
1. Scans project to detect programming languages, frameworks, and tools
2. Recommends agents for your stack (e.g., fastapi-engineer, react-engineer)
3. Recommends skills based on agent types
4. Shows preview of what will be configured
5. Deploys with confirmation (unless `--yes` is used)

**Options:**
- `--yes`: Automatically deploy without prompting
- `--preview`: Show recommendations without deploying (default when no args)
- `--min-confidence FLOAT`: Minimum confidence threshold (default: 0.8)
- `--agents-only`: Only configure agents, skip skills
- `--skills-only`: Only configure skills, skip agents
- `--json`: Output results in JSON format

**Examples:**
```
/mpm-config                    # Preview auto-configuration
/mpm-config auto               # Same as above
/mpm-config auto --yes         # Deploy automatically
/mpm-config auto --min-confidence 0.7  # Lower threshold
```

**Detection Capabilities:**

**Languages:**
- Python (CPython, PyPy)
- JavaScript/TypeScript (Node.js, Deno, Bun)
- Rust, Go, Java

**Python Frameworks:**
- FastAPI, Flask, Django, Starlette, Pyramid

**JavaScript/TypeScript Frameworks:**
- Next.js, React, Vue, Svelte, Angular
- Express, Nest.js, Fastify

**Testing Tools:**
- pytest, unittest (Python)
- Jest, Vitest (JavaScript)
- Playwright, Cypress (Browser)

**Example Output:**
```
📊 Detected Toolchain:
  ✓ Python 3.11 (100% confidence)
  ✓ FastAPI 0.104.0 (95% confidence)
  ✓ pytest 7.4.0 (90% confidence)

🤖 Recommended Agents:
  ✓ fastapi-engineer (95% confidence)
    Reason: FastAPI framework detected
  ✓ python-engineer (90% confidence)
    Reason: Python project support
  ✓ api-qa (85% confidence)
    Reason: API testing and validation

🎯 Recommended Skills:
  ✓ toolchains-python-frameworks-fastapi
  ✓ toolchains-python-testing-pytest
  ✓ toolchains-universal-api-testing

Deploy 3 agent(s) and 3 skill(s)? (y/n/s for select):
```

### View Configuration

Display current configuration settings.

```
/mpm-config view [--section SECTION] [--format FORMAT] [--show-defaults]
```

**Options:**
- `--section SECTION`: Specific configuration section to view
- `--format FORMAT`: Output format (yaml, json, table)
- `--show-defaults`: Include default values in output

**Examples:**
```
/mpm-config view
/mpm-config view --section agents --format json
/mpm-config view --show-defaults
```

### Validate Configuration

Validate configuration files for correctness and completeness.

```
/mpm-config validate [--config-file PATH] [--strict] [--fix]
```

**Options:**
- `--config-file PATH`: Validate specific config file (default: all)
- `--strict`: Use strict validation rules
- `--fix`: Attempt to fix validation errors automatically

**Example:**
```
/mpm-config validate --strict
/mpm-config validate --config-file .claude/config.yaml --fix
```

**Expected Output:**
```
Validating configuration files...

✓ .claude/config.yaml: Valid
✓ .claude/agents/config.yaml: Valid
✓ Configuration schema: Valid

Configuration is valid and ready to use.
```

### Configuration Status

Show configuration health and status.

```
/mpm-config status [--verbose]
```

**Options:**
- `--verbose`: Show detailed status information

**Example:**
```
/mpm-config status --verbose
```

**Expected Output:**
```
Configuration Status
====================

Files Found: 2
  ✓ .claude/config.yaml
  ✓ .claude/agents/config.yaml

Validation: Passed
Schema Version: 4.5
Last Modified: 2025-01-15 14:30:22

Active Settings:
  - WebSocket Port: 8765
  - Agent Deploy Mode: project
  - Logging Level: INFO
```

## Implementation

This command executes:
```bash
claude-mpm config [subcommand] [options]
```

The slash command passes through to the actual CLI configuration management system.

## Configuration Categories

Configuration is organized into sections:

- **agents**: Agent deployment and management settings
- **memory**: Memory system configuration
- **websocket**: WebSocket server settings (port, host)
- **hooks**: Hook service configuration
- **logging**: Logging levels and output
- **tickets**: Ticket tracking settings
- **monitor**: Dashboard and monitoring settings

## Workflow Examples

### Quick Start (New Project)
```
/mpm-config                    # Preview recommendations
# Review output, then:
/mpm-config auto --yes         # Deploy recommended agents and skills
```

### Check Current State
```
/mpm-config view               # See current settings
/mpm-config status             # Verify health
```

### Validate After Manual Edits
```
/mpm-config validate --strict
```

### Reconfigure After Stack Changes
```
/mpm-config auto --force       # Re-run auto-detection
```

## Default Configuration Fallback

When auto-configuration cannot detect your project's toolchain, it falls back to sensible defaults:

**Default Agents** (moderate confidence 0.7):
- engineer (general-purpose)
- research (code exploration)
- qa (testing)
- ops (infrastructure)
- documentation (technical writing)

**Disable defaults:**
Edit `.claude-mpm/config/agent_capabilities.yaml`:
```yaml
default_configuration:
  enabled: false  # Disable default fallback
```

## Related Commands

- `/mpm-status`: Show overall system status
- `/mpm-doctor`: Diagnose configuration issues
- `/mpm-init`: Initialize project configuration
- `/mpm-agents`: Manually manage agents
- `/mpm-agents-detect`: View detected toolchain only
- `/mpm-agents-recommend`: Show recommendations only
