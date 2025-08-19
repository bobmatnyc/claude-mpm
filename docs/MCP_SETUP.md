# MCP Gateway Setup Guide

## Overview

The MCP (Model Context Protocol) Gateway enables Claude Desktop to interact with the claude-mpm system through a standardized protocol. This guide covers setup, configuration, and troubleshooting.

## Quick Setup

### 1. Verify Installation

Run the diagnostics script to check your setup:

```bash
python3 scripts/mcp_diagnostics.py
```

### 2. Configure Claude Desktop

The MCP server is configured in Claude Desktop's configuration file:
- **Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Configuration**: Already set to use the robust wrapper script

Current configuration:
```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "python3",
      "args": [
        "/Users/masa/Projects/claude-mpm/scripts/mcp_wrapper.py"
      ],
      "cwd": "/Users/masa/Projects/claude-mpm"
    }
  }
}
```

### 3. Restart Claude Desktop

After configuration changes, restart Claude Desktop to load the MCP server.

## Architecture

### Components

1. **MCP Wrapper Script** (`scripts/mcp_wrapper.py`)
   - Robust environment setup
   - Comprehensive error handling
   - Debug logging to stderr
   - Works from any working directory

2. **MCP Server** (`src/claude_mpm/services/mcp_gateway/server/stdio_server.py`)
   - Implements MCP protocol over stdio
   - JSON-RPC communication
   - Tool registration and execution
   - Backward compatibility patches

3. **Unified Ticket Tool** (`src/claude_mpm/services/mcp_gateway/tools/unified_ticket_tool.py`)
   - Ticket creation and management
   - Query and update operations
   - Integrated with claude-mpm ticket system

### How It Works

1. Claude Desktop spawns the MCP server process
2. The wrapper script sets up the Python environment
3. The server communicates via stdin/stdout using JSON-RPC
4. Claude Desktop can call registered tools through the MCP protocol
5. The server exits cleanly when the connection closes

## Testing

### Test the Wrapper

```bash
# Run the wrapper test
python3 scripts/test_mcp_wrapper.py

# Verify all invocation methods
python3 scripts/verify_mcp_setup.py
```

### Manual Testing

```bash
# Test the wrapper directly (will wait for stdin)
python3 scripts/mcp_wrapper.py

# Test with a simple request
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-01","clientInfo":{"name":"test","version":"1.0"}},"id":1}' | python3 scripts/mcp_wrapper.py
```

## Troubleshooting

### Common Issues

#### 1. MCP Icon Not Appearing in Claude Desktop

**Solution**: Restart Claude Desktop after configuration changes.

#### 2. Server Fails to Start

**Diagnosis**:
```bash
python3 scripts/mcp_diagnostics.py
```

**Common Fixes**:
- Ensure Python 3.8+ is installed
- Install claude-mpm: `pip install -e .`
- Check file permissions: `chmod +x scripts/mcp_wrapper.py`

#### 3. Import Errors

**Solution**: The wrapper script automatically sets up the Python path. If running manually, ensure you're in the project root directory.

#### 4. Connection Errors

**Check**:
- Claude Desktop logs (Developer Console)
- Server stderr output (logged by wrapper)
- Configuration syntax in `claude_desktop_config.json`

### Debug Logging

The MCP wrapper provides detailed debug logging to stderr:

```bash
# View logs when running manually
python3 scripts/mcp_wrapper.py 2>mcp_debug.log

# In another terminal, watch the logs
tail -f mcp_debug.log
```

Log information includes:
- Environment verification
- Python path setup
- Module import status
- Server startup status
- Runtime errors

### Diagnostic Tools

1. **MCP Diagnostics** (`scripts/mcp_diagnostics.py`)
   - System information
   - Python environment
   - Package installation
   - Configuration check
   - Startup test

2. **Setup Verification** (`scripts/verify_mcp_setup.py`)
   - Tests all invocation methods
   - Verifies file existence
   - Checks Claude Desktop config
   - Provides test summary

3. **Wrapper Test** (`scripts/test_mcp_wrapper.py`)
   - Tests wrapper functionality
   - Sends test requests
   - Captures stderr output
   - Verifies imports

## Advanced Configuration

### Environment Variables

The MCP server respects these environment variables:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
export MCP_LOG_LEVEL=DEBUG

# Set working directory
export MCP_WORKING_DIR=/path/to/project
```

### Custom Python Executable

To use a specific Python version, modify the Claude Desktop config:

```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "/usr/local/bin/python3.11",
      "args": ["/path/to/mcp_wrapper.py"],
      "cwd": "/path/to/project"
    }
  }
}
```

### Multiple Instances

You can run multiple MCP servers with different configurations:

```json
{
  "mcpServers": {
    "claude-mpm-dev": {
      "command": "python3",
      "args": ["/path/to/dev/mcp_wrapper.py"],
      "cwd": "/path/to/dev/project"
    },
    "claude-mpm-prod": {
      "command": "python3",
      "args": ["/path/to/prod/mcp_wrapper.py"],
      "cwd": "/path/to/prod/project"
    }
  }
}
```

## Development

### Adding New Tools

Tools are registered in the MCP server. To add a new tool:

1. Create tool class in `src/claude_mpm/services/mcp_gateway/tools/`
2. Register in `stdio_server.py`
3. Test with the wrapper script
4. Update Claude Desktop and restart

### Debugging the Server

1. Add debug statements using `logger.debug()`
2. Run with DEBUG logging: `export MCP_LOG_LEVEL=DEBUG`
3. Check stderr output for debug messages
4. Use the diagnostic scripts for environment issues

## Security Considerations

- The MCP server runs with the permissions of the user
- Input validation is performed on all tool parameters
- Sensitive operations require confirmation
- Logs are written to stderr to avoid protocol interference
- The server exits cleanly when stdin closes

## Performance

The wrapper script includes optimizations for:
- Fast startup with minimal imports
- Efficient error handling
- Clean subprocess management
- Proper resource cleanup

## Support

If you encounter issues:

1. Run `python3 scripts/mcp_diagnostics.py`
2. Check the troubleshooting section above
3. Review Claude Desktop's developer console
4. Check the project's issue tracker

## References

- [MCP Specification](https://spec.anthropic.com/mcp)
- [Claude Desktop Documentation](https://claude.ai/desktop)
- [claude-mpm Documentation](../README.md)