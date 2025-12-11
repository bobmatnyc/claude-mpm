# MCP Gateway Service

## Overview

The MCP Gateway is a standards-compliant implementation of the Model Context Protocol (MCP) for Claude MPM. It provides a simple, stdio-based server that enables seamless integration with Claude Code.

**NOTE: MCP is ONLY for Claude Code - NOT for Claude Code.**
Claude Code uses a different system for agent deployment via the `.claude/agents/` directory.

## Architecture

The MCP Gateway uses the official Anthropic MCP Python SDK with:

- **Standards compliance** with the official MCP specification
- **Stdio-based communication** for Claude Code integration
- **Simple JSON-RPC protocol** over stdin/stdout
- **Tool registry system** for extensible functionality
- **Comprehensive error handling** and logging

## Structure

```
mcp_gateway/
├── core/           # Core interfaces and base classes
│   ├── interfaces.py    # MCP service interfaces
│   ├── base.py         # Base MCP service class
│   └── exceptions.py   # MCP-specific exceptions
├── config/         # Configuration management
│   ├── configuration.py    # Main configuration service
│   ├── config_loader.py   # Configuration discovery and loading
│   └── config_schema.py   # Configuration validation
├── server/         # MCP server implementation (ISS-0035)
├── tools/          # Tool registry and adapters (ISS-0036)
└── registry/       # Service discovery and registration
```

## Features

### Implemented
- ✅ **Official MCP Server** - Standards-compliant implementation using Anthropic's MCP SDK
- ✅ **Tool Registry System** - Extensible tool management and discovery
- ✅ **Stdio Communication** - Standard MCP protocol over stdin/stdout
- ✅ **Configuration Management** - YAML-based configuration with validation
- ✅ **Built-in Tools** - Echo, calculator, and system info tools
- ✅ **CLI Integration** - Complete command-line interface for management
- ✅ **Error Handling** - Comprehensive error handling and logging

### Key Features
- **Protocol Handler** - Stdio-based MCP protocol handler, not a background service
- **Claude Code Ready** - Direct integration with Claude Code MCP client
- **Extensible** - Easy to add new tools and capabilities
- **Standards Compliant** - Follows official MCP specification exactly

## Quick Start

### 1. Check Status
```bash
claude-mpm mcp status
```

### 2. Test Tools
```bash
# Test echo tool
claude-mpm mcp test echo --args '{"message": "Hello MCP!"}'

# Test calculator
claude-mpm mcp test calculator --args '{"operation": "add", "a": 5, "b": 3}'

# Test system info
claude-mpm mcp test system_info
```

### 3. Start MCP Gateway Handler
```bash
# Start gateway handler for Claude Code integration
claude-mpm mcp start
```

The gateway handler will listen for MCP protocol messages via stdin/stdout. This is typically invoked by Claude Code, not run directly by users.

### 4. Claude Code Integration
Add to your Claude Code configuration (~/.claude.json):
```json
{
  "mcpServers": {
    "claude-mpm": {
      "command": "python",
      "args": ["-m", "claude_mpm.cli", "mcp", "start"],
      "cwd": "/path/to/claude-mpm"
    }
  }
}
```

## Configuration

The MCP Gateway uses a hierarchical configuration system with the following priority:

1. Default configuration (built-in)
2. Configuration file (YAML)
3. Environment variables (highest priority)

### Configuration File Locations

The system searches for configuration in these locations (in order):
- `~/.claude/mcp/config.yaml` (user-specific)
- `~/.claude/mcp_gateway.yaml`
- `~/.config/claude-mpm/mcp_gateway.yaml`
- `./mcp_gateway.yaml` (project-specific)
- `./config/mcp_gateway.yaml`
- `./.claude/mcp_gateway.yaml`
- `/etc/claude-mpm/mcp_gateway.yaml` (system-wide)

### Environment Variables

Override configuration using environment variables:
```bash
export MCP_GATEWAY_SERVER_NAME=my-gateway
export MCP_GATEWAY_TOOLS_TIMEOUT_DEFAULT=60
export MCP_GATEWAY_LOGGING_LEVEL=DEBUG
```

## Usage

### Basic Setup

```python
from claude_mpm.services.mcp_gateway import MCPConfiguration, MCPConfigLoader

# Load configuration
config_loader = MCPConfigLoader()
config = MCPConfiguration()
await config.initialize()

# Access configuration
server_name = config.get("mcp.server.name")
tools_enabled = config.get("mcp.tools.enabled")
```

### Service Registration

The MCP Gateway services are automatically registered with the claude-mpm service container:

```python
from claude_mpm.services import MCPConfiguration, BaseMCPService

# Services are available through lazy loading
config = MCPConfiguration()
```

## Development

### Adding New MCP Services

1. Define the interface in `core/interfaces.py`
2. Create base implementation in appropriate module
3. Register in service container if needed
4. Add lazy import to `__init__.py`
5. Update documentation

### Testing

Run tests with:
```bash
pytest tests/services/mcp_gateway/
```

## Dependencies

- Python 3.8+
- mcp>=0.1.0 (Anthropic's MCP package)
- PyYAML for configuration
- asyncio for async operations

## Related Issues

- ISS-0034: Infrastructure Setup (this implementation)
- ISS-0035: MCP Server Core Implementation
- ISS-0036: Tool Registry & Discovery System
- ISS-0037: stdio Communication Handler
- ISS-0038: Tool Adapter Framework

## Notes

This is the foundation implementation for the MCP Gateway. The actual server functionality, tool registry, and communication handlers will be implemented in subsequent tickets as part of the EP-0007 epic.