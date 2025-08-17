# MCP Gateway Developer Documentation

## Overview

The MCP Gateway is a production-ready implementation of the Model Context Protocol (MCP) that enables seamless integration between Claude Code and Claude MPM tools. It provides a stdio-based protocol handler that acts as a bridge between MCP clients and internal tool implementations.

**NOTE: MCP integration is ONLY for Claude Code - NOT for Claude Desktop.**
Claude Desktop uses a different system for agent deployment via the `.claude/agents/` directory.

## Architecture

### Core Components

```
MCP Gateway Architecture
├── MCPGateway (Protocol Handler)
├── ToolRegistry (Tool Management)
├── Tool Adapters (Tool Implementations)
├── Service Registry (Dependency Injection)
├── Configuration (YAML-based Config)
└── Manager (Singleton Coordination)
```

### Key Design Principles

1. **Protocol Compliance**: Full adherence to MCP specification using Anthropic's official package
2. **Stdio-based Communication**: No network ports, pure stdin/stdout communication
3. **Singleton Coordination**: One gateway instance per installation
4. **Extensible Architecture**: Easy tool addition and customization
5. **Production Ready**: Comprehensive error handling and testing

## Quick Start

### Basic Usage

```bash
# Check gateway status
claude-mpm mcp status

# Test built-in tools
claude-mpm mcp test echo --args '{"message": "Hello MCP!"}'
claude-mpm mcp test calculator --args '{"operation": "add", "a": 5, "b": 3}'

# Start gateway for Claude Code
claude-mpm mcp start
```

### Claude Code Integration

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

## Core Interfaces

### IMCPGateway

Main gateway interface for protocol handling:

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPGateway

class IMCPGateway(IMCPLifecycle):
    """Main interface for MCP gateway implementation."""
    
    async def run(self) -> None:
        """Run the MCP gateway main loop."""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get gateway capabilities."""
        pass
    
    def set_tool_registry(self, registry: IMCPToolRegistry) -> None:
        """Set the tool registry."""
        pass
```

### IMCPToolRegistry

Tool management interface:

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPToolRegistry

class IMCPToolRegistry(IMCPLifecycle):
    """Interface for tool registry implementations."""
    
    def register_tool(self, tool: IMCPToolAdapter, category: str = "user") -> bool:
        """Register a tool with the registry."""
        pass
    
    def list_tools(self) -> List[MCPToolDefinition]:
        """List all registered tools."""
        pass
    
    async def invoke_tool(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke a tool by name."""
        pass
```

### IMCPToolAdapter

Tool implementation interface:

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPToolAdapter

class IMCPToolAdapter(IMCPLifecycle):
    """Interface for tool adapter implementations."""
    
    def get_definition(self) -> MCPToolDefinition:
        """Get the tool definition."""
        pass
    
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke the tool with given parameters."""
        pass
```

## Built-in Tools

### Echo Tool

Simple message echoing with optional transformations:

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import EchoToolAdapter

# Usage via CLI
claude-mpm mcp test echo --args '{"message": "Hello", "uppercase": true}'
```

### Calculator Tool

Basic mathematical operations:

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import CalculatorToolAdapter

# Supported operations: add, subtract, multiply, divide, power, sqrt
claude-mpm mcp test calculator --args '{"operation": "add", "a": 10, "b": 5}'
```

### System Info Tool

System information retrieval:

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import SystemInfoToolAdapter

# Available info types: platform, python, memory, disk, network
claude-mpm mcp test system_info --args '{"info_type": "platform"}'
```

## Creating Custom Tools

### Step 1: Implement Tool Adapter

```python
from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPToolAdapter, MCPToolDefinition, MCPToolInvocation, MCPToolResult
)

class MyCustomTool(IMCPToolAdapter):
    """Custom tool implementation."""
    
    def get_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="my_custom_tool",
            description="Description of what this tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter description"},
                    "param2": {"type": "integer", "description": "Another parameter"}
                },
                "required": ["param1"]
            }
        )
    
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        try:
            # Extract parameters
            param1 = invocation.parameters.get("param1")
            param2 = invocation.parameters.get("param2", 0)
            
            # Implement tool logic
            result = f"Processed {param1} with {param2}"
            
            return MCPToolResult(
                success=True,
                data=result,
                execution_time=0.1
            )
        except Exception as e:
            return MCPToolResult(
                success=False,
                error=str(e),
                execution_time=0.0
            )
```

### Step 2: Register Tool

```python
from claude_mpm.services.mcp_gateway import ToolRegistry

# Get registry instance
registry = ToolRegistry()
await registry.initialize()

# Register custom tool
custom_tool = MyCustomTool()
registry.register_tool(custom_tool, category="custom")
```

## Configuration

### Default Configuration

The gateway uses sensible defaults but can be customized via YAML:

```yaml
# .claude-mpm/mcp_config.yaml
mcp:
  server:
    name: "claude-mpm-gateway"
    version: "1.0.0"
  tools:
    enabled: true
    categories:
      - builtin
      - user
      - custom
  logging:
    level: "INFO"
    format: "structured"
```

### Environment Variables

```bash
export CLAUDE_MPM_MCP_SERVER_NAME="my-gateway"
export CLAUDE_MPM_MCP_TOOLS_ENABLED="true"
export CLAUDE_MPM_MCP_LOG_LEVEL="DEBUG"
```

## Testing

### Unit Testing

The gateway includes comprehensive unit tests:

```bash
# Run MCP-specific tests
python -m pytest tests/services/test_mcp_tool_adapters_unit.py -v
python -m pytest tests/services/test_mcp_registry_simple.py -v

# Run all MCP tests
python scripts/run_mcp_tests.py
```

### Integration Testing

```bash
# Test MCP server integration
python scripts/test_mcp_server.py

# Test standards compliance
python scripts/test_mcp_standards_compliance.py
```

### Manual Testing

```bash
# Test individual tools
claude-mpm mcp test echo --args '{"message": "test"}'

# Test gateway startup
timeout 3 claude-mpm mcp start || echo "Gateway started successfully"
```

## Troubleshooting

### Common Issues

1. **Gateway Not Starting**
   ```bash
   # Check status
   claude-mpm mcp status
   
   # Check logs
   claude-mpm mcp start --debug
   ```

2. **Tool Not Found**
   ```bash
   # List available tools
   claude-mpm mcp tools
   
   # Check tool registration
   python -c "from claude_mpm.services.mcp_gateway import ToolRegistry; r = ToolRegistry(); print(r.list_tools())"
   ```

3. **Claude Desktop Integration Issues**
   - Verify MCP configuration syntax
   - Check file paths and permissions
   - Restart Claude Desktop after configuration changes

### Debug Mode

```bash
# Enable debug logging
export CLAUDE_MPM_MCP_LOG_LEVEL="DEBUG"
claude-mpm mcp start
```

## Performance Considerations

### Memory Usage

- Gateway baseline: <50MB
- Per-tool overhead: ~1-5MB
- Tool result caching: Configurable

### Execution Time

- Tool invocation overhead: <1ms
- Network communication: N/A (stdio-based)
- Startup time: <500ms

## Security

### Input Validation

All tool inputs are validated against JSON schemas:

```python
# Tools automatically validate inputs
def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
    # Schema validation happens automatically
    # Tool receives validated parameters
```

### Sandboxing

Tools run in the same process but with:
- Parameter validation
- Timeout protection
- Error isolation
- Resource monitoring

## Extension Points

### Custom Tool Categories

```python
# Register tools in custom categories
registry.register_tool(tool, category="ai-analysis")
registry.register_tool(tool, category="data-processing")
```

### Custom Error Handlers

```python
class CustomErrorHandler:
    def handle_tool_error(self, error: Exception, tool_name: str):
        # Custom error handling logic
        pass
```

### Custom Caching

```python
class CustomCache:
    def get(self, key: str) -> Optional[Any]:
        # Custom cache implementation
        pass
    
    def set(self, key: str, value: Any, ttl: int = 300):
        # Custom cache storage
        pass
```

## Related Documentation

- [MCP Gateway Service README](../../src/claude_mpm/services/mcp_gateway/README.md)
- [MCP Gateway Singleton Implementation](../mcp_gateway_singleton.md)
- [MCP Protocol Specification](https://modelcontextprotocol.org)
- [Claude Code MCP Configuration](https://claude.ai/docs/mcp)

## API Reference

For detailed API documentation, see:
- [Core Interfaces](../04-api-reference/mcp-gateway-api.md)
- [Tool Development Guide](tool-development.md)
- [Configuration Reference](configuration.md)
