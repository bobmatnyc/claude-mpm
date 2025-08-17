# MCP Configuration Fix for Claude Code on macOS

## Problem Identified
Claude Code on macOS uses a different configuration location than previously assumed:
- **Expected:** `~/.config/Claude/config.json` (Linux-style path)
- **Actual:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS standard)

## Solution Implemented

### 1. Configuration Location Fixed
- The correct configuration file at `~/Library/Application Support/Claude/claude_desktop_config.json` already contained all 5 MCP servers
- Created a symbolic link from `~/.config/Claude/config.json` to the actual location for consistency

### 2. Scripts Updated for Platform Awareness
Updated the following scripts to automatically detect the platform and use the correct configuration path:

#### `scripts/register_mcp_gateway.py`
- Now detects the operating system (macOS, Linux, Windows)
- Uses the appropriate configuration path for each platform:
  - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
  - **Linux:** `~/.config/Claude/config.json`
  - **Windows:** `~/AppData/Roaming/Claude/claude_desktop_config.json`

#### `scripts/restore_mcp_config.py`
- Updated with the same platform detection logic
- Searches for backups in platform-specific locations
- Properly handles configuration restoration across different OS environments

### 3. New Verification Script Created
Created `scripts/verify_mcp_config.py` to:
- Verify MCP configuration is correctly set up
- Check all required servers are configured
- Validate working directories exist
- Provide clear status and next steps

## Verification Results

All 5 MCP servers are correctly configured:
1. ✅ **claude-mpm-gateway** - Claude MPM gateway server
2. ✅ **terminal** - Terminal access MCP server
3. ✅ **mcp-cloud-bridge** - Cloud bridge MCP server
4. ✅ **mem0ai-memory** - Memory management server
5. ✅ **context7** - Context management server

## Platform-Specific Paths

### macOS (Darwin)
```
Configuration: ~/Library/Application Support/Claude/claude_desktop_config.json
Symlink: ~/.config/Claude/config.json -> [Configuration]
```

### Linux
```
Configuration: ~/.config/Claude/config.json
```

### Windows
```
Configuration: ~/AppData/Roaming/Claude/claude_desktop_config.json
```

## Next Steps

1. **Restart Claude Code** if it's currently running
2. **Test the /mcp command** in Claude Code to verify servers appear
3. **All MCP servers should be visible** in the MCP menu

## Testing Commands

```bash
# Verify configuration
python scripts/verify_mcp_config.py

# Check registration status
python scripts/register_mcp_gateway.py --status

# List available backups
python scripts/restore_mcp_config.py --list
```

## Notes

- The symlink ensures both paths work on macOS for backward compatibility
- Scripts now work across all major platforms (macOS, Linux, Windows)
- Configuration backups are preserved in the Application Support directory
- Some server working directories may not exist if projects aren't cloned (terminal, mem0ai-memory)