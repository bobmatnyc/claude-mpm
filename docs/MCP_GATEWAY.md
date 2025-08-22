# MCP Gateway Server

## Overview

The MCP (Model Context Protocol) Gateway provides tool capabilities to Claude Code through a stdio-based server that follows the MCP specification.

## Architecture

The gateway consists of:

1. **Launcher Script** (`src/claude_mpm/scripts/mcp_server.py`)
   - Entry point for Claude Code
   - Handles Python path setup
   - Configures logging to stderr
   - Launches the MCP server

2. **MCP Server** (`src/claude_mpm/services/mcp_gateway/server/stdio_server.py`)
   - Implements MCP protocol over stdio
   - Provides tool registration and invocation
   - Includes backward compatibility patches
   - Lazy initialization for async components

## Features

### Built-in Tools

- **echo**: Echo back messages
- **calculator**: Perform arithmetic calculations
- **system_info**: Get system information
- **run_command**: Execute shell commands
- **summarize_document**: Summarize text content
- **ticket**: Unified ticket management (if available)

### Backward Compatibility

The server includes patches to handle older Claude Code versions that may not send `clientInfo` in initialize requests.

## Configuration

The server is configured in Claude Code's config file:

```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "python3",
      "args": [
        "/path/to/claude-mpm/src/claude_mpm/scripts/mcp_server.py"
      ],
      "cwd": "/path/to/claude-mpm"
    }
  }
}
```

## Verification

To verify the server is working correctly:

```bash
python3 scripts/verify_mcp_server.py
```

This will:
- Check the launcher script exists and is executable
- Start the server and test initialization
- Verify the backward compatibility patch is applied
- Confirm the server responds to protocol requests

## Troubleshooting

### Server won't start

1. Ensure Python 3 is installed: `python3 --version`
2. Check the script is executable: `chmod +x src/claude_mpm/scripts/mcp_server.py`
3. Verify Python path includes the src directory

### No tools available

1. Check server logs in stderr for initialization errors
2. Verify tool modules are importable
3. Ensure async initialization completes for dynamic tools

### Protocol errors

1. Server logs go to stderr, not stdout (to avoid protocol interference)
2. Use the verification script to test basic protocol flow
3. Check Claude Code logs for connection issues

## Development

### Adding New Tools

1. Define tool in `_register_tools()` method
2. Add handler in `handle_call_tool()` function
3. Include proper input schema validation
4. Test with verification script

### Async Initialization

For tools requiring async setup:
1. Defer initialization to avoid event loop issues
2. Use lazy initialization pattern
3. Initialize on first use in tool handlers

## Security Considerations

- Commands are executed with shlex parsing to prevent injection
- No shell expansion by default
- Timeout controls on command execution
- Logging configured to stderr only