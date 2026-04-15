# Setup Command Improvements

## Overview

Claude MPM v6.3.2 enhances the `setup` command with open-world service support and idempotent configuration. Services are no longer limited to a fixed enumeration — any tool with a `setup` subcommand can be configured, and setup checks prevent unnecessary re-runs.

## Key Improvements

### 1. Open-World Service Names

The `claude-mpm setup` command now accepts **any binary name** that has a `setup` subcommand, not just predefined services.

#### Before (Limited Enum)

```bash
# Only these services were supported:
claude-mpm setup anthropic
claude-mpm setup kuzu-memory
# Other services would fail: "Invalid service"
```

#### After (Open-World)

```bash
# Any tool with a setup subcommand works:
claude-mpm setup langgraph          # ✅ Works!
claude-mpm setup my-custom-tool     # ✅ Works!
claude-mpm setup anthropic          # ✅ Still works
claude-mpm setup kuzu-memory        # ✅ Still works
```

### 2. Idempotent by Default

Setup automatically checks `SetupRegistry` before running, skipping if already configured.

#### Behavior

**First run:**
```bash
$ claude-mpm setup langgraph
✓ langgraph setup completed
Registered in SetupRegistry
```

**Second run (automatic skip):**
```bash
$ claude-mpm setup langgraph
✓ langgraph already configured, skipping
(checks SetupRegistry, prevents re-run)
```

**No unnecessary re-execution** — Setup is safe to run multiple times.

### 3. Force Flag

Use `--force` to re-run setup even if already configured:

```bash
# Force re-run setup
claude-mpm setup --force langgraph

# Useful for:
# - Reconfiguring a tool
# - Fixing failed setup
# - Updating configuration
```

## Command Syntax

### Basic Usage

```bash
# Setup a service (idempotent)
claude-mpm setup <service-name>

# Setup with force re-run
claude-mpm setup --force <service-name>

# Setup with verbose output
claude-mpm setup --verbose <service-name>
```

### Examples

#### Example 1: Setup LangGraph

```bash
$ claude-mpm setup langgraph
Running setup for langgraph...
✓ Installation complete
✓ Configuration: ~/.langraph/config.json
✓ Registered in SetupRegistry
```

#### Example 2: Setup Custom Tool

```bash
$ claude-mpm setup my-custom-tool
Running setup for my-custom-tool...
✓ Setup successful
✓ Binary: my-custom-tool
✓ Registered in SetupRegistry
```

#### Example 3: Force Re-run

```bash
$ claude-mpm setup --force kuzu-memory
[Force flag detected]
Running setup for kuzu-memory (force re-run)...
✓ Reconfiguration complete
✓ Registry updated
```

## SetupRegistry

All setup operations are tracked in `SetupRegistry`:

### Location

`.claude/setup_registry.json` (project-level)

### Content

```json
{
  "registered_services": [
    {
      "name": "langgraph",
      "command": "langgraph",
      "timestamp": "2026-04-15T15:30:00Z",
      "status": "completed",
      "force_run": false
    },
    {
      "name": "my-custom-tool",
      "command": "my-custom-tool",
      "timestamp": "2026-04-15T15:32:00Z",
      "status": "completed",
      "force_run": false
    }
  ]
}
```

### Check Logic

Before running setup:

1. **Check registry**: Is service already registered?
2. **If yes**: Skip setup (idempotent behavior)
3. **If no**: Run setup and register
4. **Force flag**: Bypass registry check, always run

## How It Works

### Step-by-Step

1. **Parse command**: `claude-mpm setup <service> [--force]`
2. **Check registry**:
   ```python
   if not force and registry.is_registered(service):
       print(f"✓ {service} already configured, skipping")
       return
   ```
3. **Find service**: Locate binary in PATH
4. **Check capability**: Verify `<service> setup --help` works
5. **Run setup**: Execute `<service> setup` subcommand
6. **Register**: Add to SetupRegistry with timestamp
7. **Report**: Show completion status

### Example Flow

```
User runs: claude-mpm setup langgraph
    ↓
Parser extracts: service="langgraph", force=False
    ↓
SetupRegistry check: Is "langgraph" registered?
    ↓ (No)
Find binary: which langgraph → /usr/local/bin/langgraph
    ↓
Check capability: /usr/local/bin/langgraph setup --help
    ↓
Run setup: /usr/local/bin/langgraph setup
    ↓
Register: Add "langgraph" to .claude/setup_registry.json
    ↓
Report: ✓ langgraph setup completed
```

## Service Discovery

The setup command automatically discovers services:

### Discovery Order

1. **User PATH**: Check standard PATH directories
2. **Virtual environments**: Check venv/conda if active
3. **Package managers**: Check installed packages (pip, npm, cargo)
4. **System paths**: Check /usr/local/bin, /opt, etc.

### Examples

```bash
# Services discovered from different sources:
claude-mpm setup python      # From PATH
claude-mpm setup npm         # From PATH
claude-mpm setup uv          # From venv
claude-mpm setup langgraph   # From pip
claude-mpm setup my-tool     # From custom location
```

## Error Handling

### Service Not Found

```bash
$ claude-mpm setup nonexistent-tool
Error: Service 'nonexistent-tool' not found in PATH
Try: which nonexistent-tool
```

### Service Missing Setup Subcommand

```bash
$ claude-mpm setup some-tool
Error: 'some-tool' does not support 'setup' subcommand
Try: some-tool setup --help
```

### Setup Failed

```bash
$ claude-mpm setup langgraph
Running setup for langgraph...
Error: Setup failed with exit code 1
Details: Permission denied
Try: claude-mpm setup --force langgraph
```

## Registry Management

### View Registered Services

```bash
cat .claude/setup_registry.json
```

### Manually Remove Registration

```bash
# Edit registry
vim .claude/setup_registry.json

# Or remove entry:
jq 'del(.registered_services[] | select(.name=="langgraph"))' \
   .claude/setup_registry.json > temp && mv temp .claude/setup_registry.json
```

### Clear Registry

```bash
rm .claude/setup_registry.json
# All services will re-run setup on next invocation
```

## Common Workflows

### Setting Up New Project

```bash
# Setup all tools for a new project
claude-mpm setup anthropic
claude-mpm setup kuzu-memory
claude-mpm setup mcp-vector-search
claude-mpm setup langgraph
```

### Fixing Broken Setup

```bash
# Re-run setup with force flag
claude-mpm setup --force anthropic

# Check registry was updated
cat .claude/setup_registry.json | grep anthropic
```

### Reconfiguring Service

```bash
# Use force flag to reconfigure
claude-mpm setup --force kuzu-memory

# This will:
# 1. Run setup again
# 2. Update configuration
# 3. Update timestamp in registry
```

## Troubleshooting

### Service Not Found in PATH

Ensure the service is installed and in PATH:

```bash
# Check if service exists
which <service-name>

# Add to PATH if needed
export PATH="/path/to/service:$PATH"
```

### Setup Fails with Permissions

Some services require elevated permissions:

```bash
# Try with sudo (if service requires it)
sudo claude-mpm setup <service>

# Or fix permissions
chmod +x /path/to/<service>
```

### Registry Corrupted

```bash
# Validate JSON
jq empty .claude/setup_registry.json

# If corrupted, remove and regenerate
rm .claude/setup_registry.json
claude-mpm setup <service>  # Will recreate registry
```

## Related Files

- **Implementation**: `src/claude_mpm/cli/setup.py`
- **Registry**: `.claude/setup_registry.json` (created per project)
- **Configuration**: `.claude/settings.json`

## Related Documentation

- [MCP Server Setup](../setup/mcp-servers.md)
- [Configuration Guide](../guides/configuration.md)
- [CLI Reference](../reference/cli.md)
