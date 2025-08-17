# MCP Gateway Implementation

## Overview

The Claude MPM MCP Gateway is properly configured to use the official MCP protocol from the Anthropic MCP package. This ensures full protocol compliance and compatibility with Claude Code.

**NOTE: MCP integration is ONLY for Claude Code - NOT for Claude Desktop.**
Claude Desktop uses a different system for agent deployment via the `.claude/agents/` directory.

## Architecture

### Core Components

1. **MCPGateway** (`src/claude_mpm/services/mcp_gateway/server/mcp_gateway.py`)
   - Main server class implementing the official MCP Server protocol
   - Uses `mcp.server.Server` from the official MCP package
   - Handles stdio-based communication via `mcp.server.stdio.stdio_server`
   - Manages tool registration and invocation through handlers

2. **ToolRegistry** (`src/claude_mpm/services/mcp_gateway/registry/tool_registry.py`)
   - Thread-safe registry for managing MCP tools
   - Provides registration, discovery, and invocation capabilities
   - Supports pattern-based search and metrics tracking

3. **Tool Adapters** (`src/claude_mpm/services/mcp_gateway/tools/`)
   - Base adapters for echo, calculator, and system info tools
   - Document summarizer tool
   - Ticket management tools (create, list, update, view, search)

### Entry Points

1. **bin/claude-mpm-mcp** (Primary)
   - Full-featured entry point with all tools registered
   - Uses ToolRegistry for proper tool management
   - Includes error handling and graceful fallbacks

2. **bin/claude-mpm-mcp-simple** (Simplified)
   - Minimal implementation with fallback capabilities
   - Works even if some dependencies are missing
   - Uses MinimalToolRegistry as fallback

## Key Features

### Official MCP Protocol Support

The implementation uses the official MCP package components:
- `mcp.server.Server` - Core server implementation
- `mcp.server.stdio.stdio_server` - Stdio transport for JSON-RPC
- `mcp.types.Tool` - Tool definition types
- `mcp.types.TextContent` - Response content types

### Tool Registration

Tools are registered through the server's decorators:
```python
@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    # Return available tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict) -> List[TextContent]:
    # Handle tool invocation
```

### Available Tools

1. **Basic Tools**
   - `echo` - Echo back messages
   - `calculator` - Perform arithmetic calculations
   - `system_info` - Get system information

2. **Document Tools**
   - `summarize_document` - Summarize text with various styles

3. **Ticket Management Tools**
   - `ticket_create` - Create new tickets
   - `ticket_list` - List existing tickets
   - `ticket_update` - Update ticket status/details
   - `ticket_view` - View ticket details
   - `ticket_search` - Search tickets

## Configuration for Claude Code

Add to your Claude Code configuration (~/.claude.json):

```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "python",
      "args": ["-m", "claude_mpm.cli", "mcp", "start"],
      "cwd": "/path/to/claude-mpm"
    }
  }
}
```

Or use the registration script:
```bash
python scripts/register_mcp_gateway.py
```

## Protocol Flow

1. Claude Code spawns the MCP server process
2. Server initializes with stdio communication
3. Claude sends initialization request
4. Server responds with capabilities and available tools
5. Claude can then invoke tools via `tools/call` requests
6. Server processes requests and returns results
7. Server exits cleanly when stdio connection closes

## Design Decisions

### Why MCPGateway over SimpleMCPServer?

- **Protocol Compliance**: MCPGateway uses the official MCP Server class, ensuring full protocol compliance
- **Extensibility**: Proper architecture with interfaces and dependency injection
- **Tool Management**: Full-featured ToolRegistry with thread safety and metrics
- **Error Handling**: Comprehensive error handling and logging
- **Production Ready**: Designed for production use with proper lifecycle management

### Graceful Fallbacks

The implementation includes multiple fallback mechanisms:
- Registry fallback from full to minimal implementation
- Tool registration with individual error handling
- Optional components that don't break core functionality

## Testing

Test the implementation:

```bash
# Run the server directly (will connect to stdio)
./bin/claude-mpm-mcp

# Or use Python
python3 bin/claude-mpm-mcp

# Test with simplified version
python3 bin/claude-mpm-mcp-simple
```

The server will:
1. Log to stderr (doesn't interfere with stdio protocol)
2. Register all available tools
3. Wait for JSON-RPC requests on stdin
4. Send responses on stdout
5. Exit cleanly on disconnect

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed:
   ```bash
   pip install -e .
   ```

2. **Tool Registration Failures**: Check logs on stderr for specific tool errors

3. **Protocol Errors**: Ensure using latest version of MCP package:
   ```bash
   pip install --upgrade mcp
   ```

### Debug Logging

Enable debug logging by modifying the logging level in the entry point:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

## Future Enhancements

1. **Dynamic Tool Loading**: Support for loading tools from plugins
2. **Tool Categories**: Better organization of tools by category
3. **Metrics Dashboard**: Web UI for monitoring tool usage
4. **Custom Tool Development**: SDK for creating custom tools
5. **Performance Optimization**: Caching and connection pooling for tools