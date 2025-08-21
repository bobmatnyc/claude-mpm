# CLI Commands Reference

## Overview

Claude MPM provides a comprehensive command-line interface for managing agents, memory, configuration, and project workflows. All commands follow consistent patterns for arguments, output formatting, and error handling.

## Common Arguments

All CLI commands support these common arguments:

### Logging Control
- `--verbose, -v`: Enable verbose output
- `--quiet, -q`: Suppress non-error output  
- `--debug`: Enable debug logging

### Output Formatting
- `--format, -f {text,json,yaml,table}`: Output format (default: text)
- `--output, -o FILE`: Write output to file instead of stdout

### Configuration
- `--config, -c FILE`: Use specific configuration file

## Command Categories

### Configuration Management

#### `claude-mpm config`

Manage Claude MPM configuration settings.

**Subcommands:**
- `validate`: Validate configuration file
- `view`: Display current configuration
- `status`: Show configuration status

**Examples:**
```bash
# View current configuration
claude-mpm config view

# View configuration in JSON format
claude-mpm config view --format json

# Validate configuration file
claude-mpm config validate

# Check configuration status
claude-mpm config status
```

**Output Formats:**
- **text**: Human-readable configuration display
- **json**: Structured configuration data
- **yaml**: YAML-formatted configuration
- **table**: Tabular view of configuration keys

### Memory Management

#### `claude-mpm memory`

Manage the Claude MPM memory system.

**Subcommands:**
- `init`: Initialize memory system
- `view`: Display stored memories
- `add`: Add new learning/memory
- `clean`: Clean up old memories
- `optimize`: Optimize memory storage
- `build`: Build memory indices
- `cross-ref`: Cross-reference memories
- `route`: Route memory commands

**Examples:**
```bash
# Initialize memory system
claude-mpm memory init

# View all memories
claude-mpm memory view

# View memories in JSON format
claude-mpm memory view --format json

# Add a new memory
claude-mpm memory add --content "Important learning"

# Clean up old memories
claude-mpm memory clean --days 30
```

**Memory Directory Options:**
- `--memory-dir DIR`: Specify memory directory location

### Agent Management

#### `claude-mpm agents`

Manage Claude MPM agents.

**Examples:**
```bash
# List available agents
claude-mpm agents list

# Deploy an agent
claude-mpm agents deploy --agent my-agent

# Show agent information
claude-mpm agents info --agent my-agent
```

**Agent Directory Options:**
- `--agent-dir DIR`: Specify agent directory location
- `--agent PATTERN`: Filter agents by pattern

### Data Aggregation

#### `claude-mpm aggregate`

Aggregate and analyze project data.

**Subcommands:**
- `start`: Start data aggregation
- `stop`: Stop aggregation process
- `status`: Show aggregation status
- `sessions`: List aggregation sessions
- `view`: View aggregated data
- `export`: Export aggregation results

**Examples:**
```bash
# Start aggregation
claude-mpm aggregate start

# Check aggregation status
claude-mpm aggregate status

# View aggregated data
claude-mpm aggregate view --format table

# Export results
claude-mpm aggregate export --output results.json
```

## Output Formats

### Text Format (Default)

Human-readable output with colors and formatting:

```
✅ Configuration is valid
📁 Loaded from: .claude-mpm/configuration.yaml
🔧 Total keys: 15
```

### JSON Format

Structured data for programmatic use:

```json
{
  "success": true,
  "message": "Configuration is valid",
  "data": {
    "config_file": ".claude-mpm/configuration.yaml",
    "valid": true,
    "key_count": 15
  }
}
```

### YAML Format

YAML-formatted output:

```yaml
success: true
message: Configuration is valid
data:
  config_file: .claude-mpm/configuration.yaml
  valid: true
  key_count: 15
```

### Table Format

Tabular display for structured data:

```
┌─────────────┬─────────────────────────────────┐
│ Key         │ Value                           │
├─────────────┼─────────────────────────────────┤
│ config_file │ .claude-mpm/configuration.yaml  │
│ valid       │ true                            │
│ key_count   │ 15                              │
└─────────────┴─────────────────────────────────┘
```

## Error Handling

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Usage error (invalid arguments)
- `130`: Interrupted by user (Ctrl+C)

### Error Output

Errors are displayed consistently across all commands:

```bash
# Text format error
❌ Configuration file not found: config.yaml
→ Create with: touch config.yaml

# JSON format error
{
  "success": false,
  "exit_code": 1,
  "message": "Configuration file not found: config.yaml",
  "data": {
    "suggestion": "Create with: touch config.yaml"
  }
}
```

## Configuration

### Configuration Files

Commands look for configuration in these locations (in order):
1. File specified with `--config`
2. `.claude-mpm/configuration.yaml` (project-specific)
3. `~/.claude-mpm/configuration.yaml` (user-specific)
4. System defaults

### Environment Variables

Override configuration with environment variables:
- `CLAUDE_MPM_*`: General configuration
- `CLAUDE_MPM_AGENT_*`: Agent-specific settings
- `CLAUDE_MPM_MEMORY_*`: Memory-specific settings

Examples:
```bash
export CLAUDE_MPM_DEBUG=true
export CLAUDE_MPM_AGENT_TIMEOUT=60
export CLAUDE_MPM_MEMORY_MAX_ENTRIES=1000
```

## Advanced Usage

### Piping and Redirection

Commands support standard Unix piping and redirection:

```bash
# Pipe JSON output to jq
claude-mpm config view --format json | jq '.data.key_count'

# Redirect output to file
claude-mpm memory view --format yaml > memories.yaml

# Use in scripts
if claude-mpm config validate --quiet; then
    echo "Configuration is valid"
fi
```

### Batch Operations

Use JSON/YAML output for batch processing:

```bash
# Get all agent names
claude-mpm agents list --format json | jq -r '.data[].name'

# Export configuration for backup
claude-mpm config view --format yaml --output backup-config.yaml
```

### Integration with Other Tools

Commands are designed to integrate well with other tools:

```bash
# Use with make
make deploy: validate-config
validate-config:
	claude-mpm config validate

# Use with CI/CD
- name: Validate Configuration
  run: claude-mpm config validate --format json
```

## Troubleshooting

### Common Issues

1. **Configuration not found**
   ```bash
   # Check configuration status
   claude-mpm config status
   
   # Create default configuration
   mkdir -p .claude-mpm
   claude-mpm config view --format yaml > .claude-mpm/configuration.yaml
   ```

2. **Permission errors**
   ```bash
   # Check file permissions
   ls -la .claude-mpm/
   
   # Fix permissions
   chmod 644 .claude-mpm/configuration.yaml
   ```

3. **Memory system issues**
   ```bash
   # Reinitialize memory system
   claude-mpm memory init --force
   
   # Check memory status
   claude-mpm memory status
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Enable debug logging
claude-mpm --debug config validate

# Combine with verbose output
claude-mpm --debug --verbose memory view
```

### Getting Help

- Use `--help` with any command for detailed usage information
- Check the configuration with `claude-mpm config status`
- Enable debug mode for detailed error information
- Review log files in `.claude-mpm/logs/`

## Examples

### Daily Workflow

```bash
# Morning setup
claude-mpm config validate
claude-mpm memory status
claude-mpm agents list

# Work session
claude-mpm aggregate start
# ... do work ...
claude-mpm aggregate stop

# End of day
claude-mpm memory optimize
claude-mpm aggregate export --output daily-summary.json
```

### Configuration Management

```bash
# Backup current configuration
claude-mpm config view --format yaml --output config-backup.yaml

# Validate after changes
claude-mpm config validate

# View specific configuration sections
claude-mpm config view --format json | jq '.data.memory'
```

### Memory Operations

```bash
# Initialize new project memory
claude-mpm memory init

# Add project-specific learning
claude-mpm memory add --content "Project uses React with TypeScript"

# View recent memories
claude-mpm memory view --recent 10

# Clean up old memories
claude-mpm memory clean --days 90
```
