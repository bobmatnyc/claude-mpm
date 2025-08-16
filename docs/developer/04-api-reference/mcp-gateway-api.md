# MCP Gateway API Reference

## Overview

This document provides comprehensive API documentation for the MCP Gateway components, including interfaces, data models, and implementation classes.

## Core Interfaces

### IMCPGateway

Main gateway interface for MCP protocol handling.

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPGateway

class IMCPGateway(IMCPLifecycle):
    """Main interface for MCP gateway implementation."""
    
    async def run(self) -> None:
        """
        Run the MCP gateway main loop.
        
        This method starts the stdio-based MCP protocol handler and processes
        incoming requests until shutdown.
        
        Raises:
            MCPGatewayError: If gateway fails to start or encounters fatal error
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get gateway capabilities.
        
        Returns:
            Dict containing gateway capabilities including:
            - tools: Tool execution capability
            - resources: Resource access capability (if supported)
            - prompts: Prompt template capability (if supported)
        """
        pass
    
    def set_tool_registry(self, registry: IMCPToolRegistry) -> None:
        """
        Set the tool registry for this gateway.
        
        Args:
            registry: Tool registry implementation
            
        Raises:
            ValueError: If registry is None or invalid
        """
        pass
```

### IMCPToolRegistry

Interface for managing and executing tools.

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPToolRegistry

class IMCPToolRegistry(IMCPLifecycle):
    """Interface for tool registry implementations."""
    
    def register_tool(self, tool: IMCPToolAdapter, category: str = "user") -> bool:
        """
        Register a tool with the registry.
        
        Args:
            tool: Tool adapter implementation
            category: Tool category (builtin, user, custom)
            
        Returns:
            True if registration successful, False otherwise
            
        Raises:
            ValueError: If tool is invalid or already registered
        """
        pass
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if unregistration successful, False if tool not found
        """
        pass
    
    def list_tools(self) -> List[MCPToolDefinition]:
        """
        List all registered tools.
        
        Returns:
            List of tool definitions for all registered tools
        """
        pass
    
    def get_tool(self, name: str) -> Optional[IMCPToolAdapter]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool adapter if found, None otherwise
        """
        pass
    
    async def invoke_tool(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke a tool by name.
        
        Args:
            invocation: Tool invocation request
            
        Returns:
            Tool execution result
            
        Raises:
            ToolNotFoundError: If tool doesn't exist
            ToolExecutionError: If tool execution fails
        """
        pass
```

### IMCPToolAdapter

Interface for individual tool implementations.

```python
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPToolAdapter

class IMCPToolAdapter(IMCPLifecycle):
    """Interface for tool adapter implementations."""
    
    def get_definition(self) -> MCPToolDefinition:
        """
        Get the tool definition.
        
        Returns:
            Tool definition including name, description, and input schema
        """
        pass
    
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the tool with given parameters.
        
        Args:
            invocation: Tool invocation request with parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool parameters against schema.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        pass
```

## Data Models

### MCPToolDefinition

Defines a tool's interface and capabilities.

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class MCPToolDefinition:
    """Tool definition for MCP protocol."""
    
    name: str
    """Tool name (must be unique within registry)"""
    
    description: str
    """Human-readable tool description"""
    
    input_schema: Dict[str, Any]
    """JSON schema for tool input parameters"""
    
    category: str = "user"
    """Tool category (builtin, user, custom)"""
    
    version: str = "1.0.0"
    """Tool version"""
    
    author: Optional[str] = None
    """Tool author"""
    
    tags: Optional[List[str]] = None
    """Tool tags for categorization"""
```

### MCPToolInvocation

Represents a tool invocation request.

```python
@dataclass
class MCPToolInvocation:
    """Tool invocation request."""
    
    name: str
    """Tool name to invoke"""
    
    parameters: Dict[str, Any]
    """Tool parameters"""
    
    invocation_id: Optional[str] = None
    """Unique invocation identifier"""
    
    timeout: Optional[float] = None
    """Execution timeout in seconds"""
```

### MCPToolResult

Represents the result of a tool execution.

```python
@dataclass
class MCPToolResult:
    """Tool execution result."""
    
    success: bool
    """Whether tool execution was successful"""
    
    data: Optional[Any] = None
    """Tool result data (if successful)"""
    
    error: Optional[str] = None
    """Error message (if failed)"""
    
    execution_time: float = 0.0
    """Execution time in seconds"""
    
    metadata: Optional[Dict[str, Any]] = None
    """Additional result metadata"""
```

## Implementation Classes

### MCPGateway

Main gateway implementation using Anthropic's MCP SDK.

```python
from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway

class MCPGateway(IMCPGateway):
    """MCP Gateway implementation using stdio protocol."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP Gateway.
        
        Args:
            config: Gateway configuration (optional)
        """
        pass
    
    async def run(self) -> None:
        """Run the MCP gateway stdio handler."""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get gateway capabilities."""
        pass
```

### ToolRegistry

Default tool registry implementation.

```python
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry

class ToolRegistry(IMCPToolRegistry):
    """Default tool registry implementation."""
    
    def __init__(self):
        """Initialize tool registry."""
        pass
    
    def register_tool(self, tool: IMCPToolAdapter, category: str = "user") -> bool:
        """Register a tool."""
        pass
    
    async def invoke_tool(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke a tool with timeout and error handling."""
        pass
```

### BaseToolAdapter

Base class for tool implementations.

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter

class BaseToolAdapter(IMCPToolAdapter):
    """Base class for tool adapter implementations."""
    
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        """
        Initialize base tool adapter.
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for input validation
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against schema."""
        pass
    
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke tool with error handling and timing."""
        pass
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute tool logic (to be implemented by subclasses).
        
        Args:
            parameters: Validated tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement execute method")
```

## Built-in Tool APIs

### EchoToolAdapter

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import EchoToolAdapter

class EchoToolAdapter(BaseToolAdapter):
    """Echo tool for testing and validation."""
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """
        Echo the input message with optional transformations.
        
        Args:
            parameters: Must contain 'message' key, optional 'uppercase' boolean
            
        Returns:
            Processed message string
        """
        pass
```

### CalculatorToolAdapter

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import CalculatorToolAdapter

class CalculatorToolAdapter(BaseToolAdapter):
    """Calculator tool for mathematical operations."""
    
    async def execute(self, parameters: Dict[str, Any]) -> float:
        """
        Perform mathematical calculation.
        
        Args:
            parameters: Must contain 'operation' and operands ('a', 'b' for binary ops)
            
        Returns:
            Calculation result
            
        Raises:
            ValueError: If operation is unsupported or parameters invalid
            ZeroDivisionError: If division by zero attempted
        """
        pass
```

### SystemInfoToolAdapter

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import SystemInfoToolAdapter

class SystemInfoToolAdapter(BaseToolAdapter):
    """System information tool."""
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get system information.
        
        Args:
            parameters: Optional 'info_type' to specify information category
            
        Returns:
            Dictionary containing requested system information
        """
        pass
```

## Error Classes

### MCPGatewayError

```python
class MCPGatewayError(Exception):
    """Base exception for MCP Gateway errors."""
    pass
```

### ToolNotFoundError

```python
class ToolNotFoundError(MCPGatewayError):
    """Raised when requested tool is not found."""
    pass
```

### ToolExecutionError

```python
class ToolExecutionError(MCPGatewayError):
    """Raised when tool execution fails."""
    
    def __init__(self, message: str, tool_name: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error
```

## Usage Examples

### Creating a Custom Tool

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter
from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation, MCPToolResult

class WeatherTool(BaseToolAdapter):
    """Weather information tool."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="Get weather information for a location",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
                },
                "required": ["location"]
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        location = parameters["location"]
        units = parameters.get("units", "celsius")
        
        # Implement weather API call here
        weather_data = await self.fetch_weather(location, units)
        
        return {
            "location": location,
            "temperature": weather_data["temp"],
            "conditions": weather_data["conditions"],
            "units": units
        }
    
    async def fetch_weather(self, location: str, units: str) -> Dict[str, Any]:
        # Weather API implementation
        pass
```

### Registering and Using Tools

```python
from claude_mpm.services.mcp_gateway import ToolRegistry

# Initialize registry
registry = ToolRegistry()
await registry.initialize()

# Register custom tool
weather_tool = WeatherTool()
registry.register_tool(weather_tool, category="external")

# Use tool
invocation = MCPToolInvocation(
    name="weather",
    parameters={"location": "San Francisco", "units": "fahrenheit"}
)

result = await registry.invoke_tool(invocation)
print(f"Weather result: {result.data}")
```

## Configuration API

### Gateway Configuration

```python
config = {
    "server": {
        "name": "my-mcp-gateway",
        "version": "1.0.0"
    },
    "tools": {
        "enabled": True,
        "timeout": 30.0,
        "categories": ["builtin", "user", "custom"]
    },
    "logging": {
        "level": "INFO",
        "format": "structured"
    }
}

gateway = MCPGateway(config)
```

## Related Documentation

- [MCP Gateway Developer Guide](../13-mcp-gateway/README.md)
- [Tool Development Guide](../13-mcp-gateway/tool-development.md)
- [MCP Protocol Specification](https://modelcontextprotocol.org)
