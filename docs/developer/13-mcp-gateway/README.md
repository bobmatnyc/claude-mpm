# MCP Gateway

Technical documentation for Model Context Protocol (MCP) integration.

## Overview

The MCP Gateway enables Claude MPM to integrate with external tools and services through the Model Context Protocol.

**Key Features:**
- External tool integration
- Custom tool development
- Protocol-based communication
- Extensible architecture
- Multiple MCP server support

## Architecture

### Components

```
MCP Gateway
├── Gateway Manager       # MCP server lifecycle
├── Tool Registry         # Available tools
├── Server Connectors     # MCP server communication
└── Protocol Handler      # MCP protocol implementation
```

### Supported MCP Servers

**Built-in:**
- **filesystem**: File system operations
- **github**: GitHub API integration
- **browser**: Web automation (mcp-browser)
- **ticketer**: Issue tracking (mcp-ticketer)

**Partner Products:**
- **kuzu-memory**: Advanced memory management
- **mcp-vector-search**: Semantic code search

**Custom:**
- Any MCP-compliant server

## Usage

### Starting MCP Gateway

```bash
# Start MCP gateway
claude-mpm mcp

# With specific servers
claude-mpm mcp --servers filesystem,github

# Verify MCP services
claude-mpm verify

# Auto-fix issues
claude-mpm verify --fix
```

### Verifying Services

```bash
# Verify all MCP services
claude-mpm verify

# Check specific service
claude-mpm verify --service kuzu-memory

# Get JSON output
claude-mpm verify --json

# Auto-fix issues
claude-mpm verify --fix
```

## Tool Development

### Creating Custom MCP Server

```python
from claude_mpm.mcp import MCPServer, Tool

class MyMCPServer(MCPServer):
    """Custom MCP server."""

    def __init__(self):
        super().__init__(name="my-server")
        self.register_tools()

    def register_tools(self):
        """Register available tools."""
        self.add_tool(Tool(
            name="my_tool",
            description="My custom tool",
            handler=self.my_tool_handler
        ))

    def my_tool_handler(self, params: dict) -> dict:
        """Handle tool invocation."""
        return {"result": "Tool executed successfully"}
```

### Registering Custom Server

```python
from claude_mpm.mcp import MCPGateway

# Initialize gateway
gateway = MCPGateway()

# Register custom server
gateway.register_server("my-server", MyMCPServer())

# Use tool
result = gateway.execute_tool("my-server", "my_tool", {"param": "value"})
```

## Configuration

### MCP Configuration

```yaml
# In configuration.yaml
mcp:
  enabled: true
  servers:
    filesystem:
      enabled: true
      allowed_directories:
        - /path/to/project
    github:
      enabled: true
      token: ${GITHUB_TOKEN}
    kuzu-memory:
      enabled: true
      auto_install: true
    mcp-vector-search:
      enabled: true
      auto_install: true
```

### Environment Variables

```bash
# GitHub integration
export GITHUB_TOKEN=your_token

# Custom MCP server config
export MCP_SERVER_URL=http://localhost:8000
```

## MCP Protocol

### Tool Execution

**Request:**
```json
{
  "server": "filesystem",
  "tool": "read_file",
  "params": {
    "path": "/path/to/file"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "content": "File contents here"
  }
}
```

### Error Handling

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "File does not exist",
    "details": {}
  }
}
```

## Built-in MCP Servers

### Filesystem Server

File system operations:

```python
# Read file
result = gateway.execute_tool("filesystem", "read_file", {
    "path": "/path/to/file"
})

# Write file
result = gateway.execute_tool("filesystem", "write_file", {
    "path": "/path/to/file",
    "content": "File content"
})

# List directory
result = gateway.execute_tool("filesystem", "list_directory", {
    "path": "/path/to/dir"
})
```

### GitHub Server

GitHub API integration:

```python
# Create issue
result = gateway.execute_tool("github", "create_issue", {
    "owner": "user",
    "repo": "repo",
    "title": "Issue title",
    "body": "Issue description"
})

# Create PR
result = gateway.execute_tool("github", "create_pull_request", {
    "owner": "user",
    "repo": "repo",
    "title": "PR title",
    "head": "feature-branch",
    "base": "main"
})
```

### Browser Server (mcp-browser)

Web automation:

```python
# Navigate to URL
result = gateway.execute_tool("browser", "navigate", {
    "url": "https://example.com"
})

# Screenshot
result = gateway.execute_tool("browser", "screenshot", {
    "selector": "#element"
})
```

## Partner Product Integration

### kuzu-memory

```bash
# Install
pipx install kuzu-memory

# Verify
claude-mpm verify --service kuzu-memory

# Usage is automatic
```

### mcp-vector-search

```bash
# Install
pipx install mcp-vector-search

# Use semantic search
claude-mpm search "authentication logic"
```

## Security

### Access Control

- Tool execution permissions
- Directory restrictions (filesystem)
- API token management (GitHub)
- Sandbox execution

### Validation

- Input parameter validation
- Output sanitization
- Error handling
- Resource limits

## Troubleshooting

### MCP Service Not Found

```bash
# Verify installation
claude-mpm verify

# Install missing service
pipx install kuzu-memory

# Auto-fix
claude-mpm verify --fix
```

### Connection Errors

```bash
# Check MCP configuration
claude-mpm doctor --checks mcp

# Restart gateway
claude-mpm mcp --restart

# Check logs
tail -f ~/.claude-mpm/logs/mcp.log
```

## Development

### Testing MCP Server

```python
import pytest
from claude_mpm.mcp import MCPGateway

def test_custom_server():
    """Test custom MCP server."""
    gateway = MCPGateway()
    gateway.register_server("test", MyMCPServer())

    result = gateway.execute_tool("test", "my_tool", {})
    assert result["success"]
```

### Debugging

```bash
# Enable debug logging
export MCP_DEBUG=1

# Run with verbose output
claude-mpm mcp --verbose

# Check MCP gateway status
curl http://localhost:5000/mcp/status
```

## See Also

- **[Extending Guide](../extending.md)** - Building custom tools
- **[Architecture](../ARCHITECTURE.md)** - System architecture
- **[API Reference](../api-reference.md)** - API documentation
- **[User Guide](../../user/user-guide.md)** - End-user features

---

**For MCP integration examples**: See [../extending.md](../extending.md)
