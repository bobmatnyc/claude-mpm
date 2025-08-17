# MCP Configuration Management Tools

Safe tools for managing Claude Desktop MCP server configurations with automatic backup and restoration capabilities.

## Overview

These scripts provide a safe way to register, manage, and restore MCP server configurations for Claude Desktop without losing existing configurations. They feature automatic backup creation, configuration merging, and validation to ensure your MCP setup remains intact.

## Scripts

### 1. `register_mcp_gateway.py`

Safely registers the claude-mpm MCP gateway with Claude Desktop.

**Features:**
- Preserves all existing MCP server configurations
- Creates timestamped backups before modifications
- Validates JSON structure before and after changes
- Dry-run mode for previewing changes
- Can register or unregister the claude-mpm gateway

**Usage:**
```bash
# Register claude-mpm gateway (creates backup first)
python scripts/register_mcp_gateway.py

# Preview changes without applying them
python scripts/register_mcp_gateway.py --dry-run

# Show current MCP server registration status
python scripts/register_mcp_gateway.py --status

# Unregister claude-mpm gateway
python scripts/register_mcp_gateway.py --remove

# Use custom config path
python scripts/register_mcp_gateway.py --config-path /path/to/config.json
```

**What it registers:**
```json
{
  "claude-mpm-gateway": {
    "command": "python",
    "args": ["-m", "claude_mpm.cli", "mcp", "start"],
    "cwd": "/Users/masa/Projects/claude-mpm"
  }
}
```

### 2. `restore_mcp_config.py`

Intelligent restoration of MCP configurations from backups.

**Features:**
- Finds all available backup files automatically
- Can merge configurations from multiple backups
- Shows preview before restoration
- Creates backup of current config before restoring
- Interactive mode for easy selection

**Usage:**
```bash
# Interactive restoration (shows menu of available backups)
python scripts/restore_mcp_config.py

# List all available backups
python scripts/restore_mcp_config.py --list

# Compare current config with backups
python scripts/restore_mcp_config.py --compare

# Restore from specific backup
python scripts/restore_mcp_config.py --from /path/to/backup.json

# Merge all available backups into one config
python scripts/restore_mcp_config.py --merge

# Use custom config path
python scripts/restore_mcp_config.py --config-path /path/to/config.json
```

**Backup locations searched:**
- `~/.config/Claude/backups/` (created by register script)
- `~/.config/claude-desktop/claude_desktop_config.json.backup`
- `~/.config/Claude/config.json.backup`
- Legacy backup locations

### 3. `test_mcp_config_scripts.py`

Test suite for verifying the configuration scripts work correctly.

**Usage:**
```bash
python scripts/test_mcp_config_scripts.py
```

## Backup Strategy

### Automatic Backups
- **register_mcp_gateway.py** creates backups in `~/.config/Claude/backups/` with timestamp
- Format: `config_YYYYMMDD_HHMMSS.json`
- Backups are created before ANY modification

### Manual Backups
You can manually backup your configuration:
```bash
cp ~/.config/Claude/config.json ~/.config/Claude/config.json.backup
```

### Restoration Priority
When merging configurations, the tool:
1. Combines all unique MCP servers from all backups
2. For duplicates, keeps the most complete configuration
3. Preserves all server-specific settings (env vars, cwd, etc.)

## Safety Features

1. **Never Overwrites Without Backup**: Always creates a backup before any modification
2. **JSON Validation**: Validates JSON structure before and after operations
3. **Dry-Run Mode**: Preview changes without applying them
4. **Merge Conflicts**: When merging, keeps the most complete version of each server
5. **Interactive Confirmation**: Requires user confirmation for destructive operations

## Common Scenarios

### Scenario 1: Fresh Installation
```bash
# Register claude-mpm for the first time
python scripts/register_mcp_gateway.py
```

### Scenario 2: Lost Configurations
```bash
# See what backups are available
python scripts/restore_mcp_config.py --list

# Compare with current config
python scripts/restore_mcp_config.py --compare

# Restore interactively
python scripts/restore_mcp_config.py
```

### Scenario 3: Combining Multiple Setups
```bash
# Merge all available backups to get all servers
python scripts/restore_mcp_config.py --merge
```

### Scenario 4: Testing Changes
```bash
# Preview registration without making changes
python scripts/register_mcp_gateway.py --dry-run

# If happy, apply for real
python scripts/register_mcp_gateway.py
```

## Troubleshooting

### Issue: "Config file not found"
**Solution**: The script will create a new config structure if none exists.

### Issue: "Invalid JSON" error
**Solution**: Check if the config file has valid JSON syntax. The restore script can help recover from backups.

### Issue: "Gateway already registered"
**Solution**: The script will show the current configuration and only update if different.

### Issue: Lost all MCP servers
**Solution**: Use `restore_mcp_config.py --merge` to combine all backups and recover all servers.

## Configuration File Location

The standard Claude Desktop configuration is located at:
- **macOS/Linux**: `~/.config/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json` (scripts may need path adjustment)

## Requirements

- Python 3.8+
- No external dependencies (uses standard library only)
- Write permissions to Claude Desktop config directory

## Notes

- These scripts do NOT use the MCP package's `update_claude_config` function
- They implement their own safe merge and backup logic
- All operations are atomic - either fully succeed or fully fail
- Backups are never deleted automatically - manage them manually if needed