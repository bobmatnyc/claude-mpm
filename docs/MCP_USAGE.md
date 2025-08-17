# MCP Gateway Usage Guide

## Overview

The Claude MPM MCP Gateway is now a proper stdio-based JSON-RPC server that integrates seamlessly with Claude Desktop/Code. It follows the MCP (Model Context Protocol) specification for tool invocation.

## Key Changes from Previous Implementation

### ✅ What's Fixed

1. **No More Background Services**: The MCP server no longer runs as a persistent background service
2. **No Lock Files**: Removed all lock file management (gateway.lock, gateway.json, etc.)
3. **Proper Stdio Communication**: Uses stdin/stdout for JSON-RPC communication as per MCP spec
4. **On-Demand Spawning**: Server is spawned by Claude when needed and exits when done
5. **Clean Architecture**: Simplified implementation following MCP best practices

### 🗑️ What's Removed

- `MCPGatewayManager` singleton pattern (no longer needed)
- Lock file management code
- PID file tracking
- Background service logic
- `cleanup_mcp_locks.py` script (obsolete)
- `mcp_control.sh` script (not applicable)

## Installation

```bash
# Install claude-mpm with MCP support
pip install -e .

# This creates the claude-mpm-mcp command
which claude-mpm-mcp
```

## Configuration for Claude Desktop

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "claude-mpm": {
      "command": "claude-mpm-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

Or if using the full path:

```json
{
  "mcpServers": {
    "claude-mpm": {
      "command": "/path/to/your/venv/bin/claude-mpm-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

## Available Tools

The MCP server provides the following tools:

### 1. **echo**
Echo back a message.
```json
{
  "name": "echo",
  "arguments": {
    "message": "Hello, World!"
  }
}
```

### 2. **calculator**
Perform mathematical calculations.
```json
{
  "name": "calculator",
  "arguments": {
    "expression": "2 + 2 * 3"
  }
}
```

### 3. **system_info**
Get system information.
```json
{
  "name": "system_info",
  "arguments": {
    "info_type": "platform"  // or "python_version", "cwd"
  }
}
```

### 4. **run_command**
Execute shell commands securely.

**⚠️ Security Note**: This tool uses secure subprocess execution to prevent command injection attacks. Commands are parsed using `shlex.split()` and executed without shell interpretation, which means shell metacharacters (`;`, `|`, `&`, `$()`, etc.) are treated as literal text rather than shell operators.

```json
{
  "name": "run_command",
  "arguments": {
    "command": "ls -la",
    "timeout": 30
  }
}
```

**Security Features**:
- Commands are parsed safely using `shlex.split()` to prevent injection
- No shell interpretation of metacharacters
- Timeout protection to prevent hanging processes
- Proper error handling for malformed commands

### 5. **agent_task**
Delegate tasks to Claude MPM agents.
```json
{
  "name": "agent_task",
  "arguments": {
    "agent": "engineer",
    "task": "Review the authentication module",
    "context": {
      "priority": "high",
      "module": "auth"
    }
  }
}
```

## Testing

### Manual Testing

Run the server interactively:

```bash
# Start the server (it will wait for stdin input)
claude-mpm mcp start

# Or directly:
claude-mpm-mcp
```

### Automated Testing

Use the provided test script:

```bash
python scripts/test_mcp_stdio.py
```

This script simulates Claude Desktop's communication with the server.

### Command Line Testing

You can also test individual commands:

```bash
# Check status
claude-mpm mcp status

# List tools
claude-mpm mcp tools

# Test a specific tool
claude-mpm mcp test echo --args '{"message": "test"}'
```

## How It Works

1. **Spawning**: Claude Desktop spawns the `claude-mpm-mcp` process when needed
2. **Communication**: Uses JSON-RPC 2.0 protocol over stdin/stdout
3. **Tool Invocation**: Claude sends `tools/call` requests, server executes and returns results
4. **Shutdown**: Server exits when stdin is closed (Claude disconnects)

## Architecture

```
Claude Desktop/Code
       |
       | (spawns process)
       v
claude-mpm-mcp
       |
       | (stdio: JSON-RPC)
       |
   SimpleMCPServer
       |
       +-- echo tool
       +-- calculator tool
       +-- system_info tool
       +-- run_command tool
       +-- agent_task tool (integrates with Claude MPM agents)
```

## Troubleshooting

### Server Not Starting

1. Check installation:
   ```bash
   which claude-mpm-mcp
   claude-mpm-mcp --version
   ```

2. Test manually:
   ```bash
   claude-mpm mcp start
   ```

3. Check logs (written to stderr):
   ```bash
   claude-mpm-mcp 2>server.log
   ```

### Legacy Lock Files

If you have lock files from the old implementation:

```bash
# Clean up legacy files
claude-mpm mcp cleanup

# Or manually remove:
rm -f ~/.claude-mpm/mcp/gateway.lock
rm -f ~/.claude-mpm/mcp/gateway.json
rm -f ~/.claude-mpm/mcp_server.pid
```

### Communication Issues

- Ensure the server outputs to stdout only (logs go to stderr)
- Verify JSON-RPC format is correct
- Check that tools are properly registered

## Development

### Adding New Tools

Edit `src/claude_mpm/services/mcp_gateway/server/stdio_server.py`:

```python
@self.server.list_tools()
async def handle_list_tools() -> List[Tool]:
    tools = [
        # ... existing tools ...
        Tool(
            name="my_new_tool",
            description="Description of the tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )
    ]
    return tools

@self.server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]):
    if name == "my_new_tool":
        # Implement tool logic
        result = do_something(arguments["param1"])
        return [TextContent(type="text", text=result)]
```

### Debugging

Enable debug logging:

```python
# In stdio_server.py
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    stream=sys.stderr
)
```

## Migration from Old Implementation

If you were using the old persistent service implementation:

1. **Remove old configurations** that started the MCP server as a daemon
2. **Update Claude Desktop config** to use the new `claude-mpm-mcp` command
3. **Clean up lock files** using `claude-mpm mcp cleanup`
4. **No longer need to "start" or "stop"** the server - it's managed by Claude

## Benefits of the New Implementation

1. **Simpler**: No complex state management or lock files
2. **More Reliable**: No stale locks or orphaned processes
3. **Standards Compliant**: Follows MCP specification exactly
4. **Better Integration**: Works seamlessly with Claude Desktop's process management
5. **Easier Debugging**: Clear stdio communication, logs to stderr

## Future Enhancements

- Additional tool implementations
- Integration with more Claude MPM features
- Tool configuration via environment variables
- Dynamic tool loading from plugins