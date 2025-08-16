# MCP Gateway Service

## Overview

The MCP Gateway is a service module for Claude MPM that implements the Model Context Protocol (MCP), enabling integration with MCP-compatible tools and services through a standardized interface.

## Architecture

The MCP Gateway follows the claude-mpm service-oriented architecture with:

- **Interface-based contracts** for all components
- **Dependency injection** for service resolution
- **Lazy loading** for performance optimization
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

### Implemented (ISS-0034)
- ✅ Service-oriented architecture foundation
- ✅ Core interfaces for MCP services
- ✅ Base service class with lifecycle management
- ✅ Configuration management system
- ✅ YAML-based configuration with schema validation
- ✅ Environment variable overrides
- ✅ Comprehensive exception handling

### Planned
- 🔄 MCP server implementation (ISS-0035)
- 🔄 Tool registry and discovery (ISS-0036)
- 🔄 stdio communication handler (ISS-0037)
- 🔄 Tool adapter framework (ISS-0038)
- 🔄 WebSocket/HTTP communication support
- 🔄 Resource and prompt capabilities

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