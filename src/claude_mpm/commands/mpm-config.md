# View and validate claude-mpm configuration

Manage Claude MPM configuration settings through validation, viewing, and status checks.

## Usage

```
/mpm-config [subcommand] [options]
```

## Description

This slash command provides access to Claude MPM's configuration management capabilities through the actual CLI commands.

## Available Subcommands

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

## Expected Output

### Validation Output
```
Validating configuration files...

✓ .claude/config.yaml: Valid
✓ .claude/agents/config.yaml: Valid
✓ Configuration schema: Valid

Configuration is valid and ready to use.
```

### View Output
```yaml
agents:
  deploy_mode: project
  auto_reload: true

websocket:
  host: localhost
  port: 8765

logging:
  level: INFO
  format: detailed
```

### Status Output
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

## Related Commands

- `/mpm-status`: Show overall system status
- `/mpm-doctor`: Diagnose configuration issues
- `/mpm-init`: Initialize project configuration