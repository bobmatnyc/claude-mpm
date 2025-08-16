# MCP Gateway Tool Development Guide

## Overview

This guide covers how to develop custom tools for the MCP Gateway, including best practices, testing strategies, and deployment patterns.

## Tool Development Lifecycle

### 1. Planning Phase

Before implementing a tool, consider:

- **Purpose**: What specific problem does this tool solve?
- **Input/Output**: What parameters does it need and what does it return?
- **Dependencies**: What external libraries or services are required?
- **Performance**: Expected execution time and resource usage
- **Error Handling**: What can go wrong and how to handle it gracefully

### 2. Implementation Phase

#### Basic Tool Structure

```python
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter
from typing import Dict, Any

class MyCustomTool(BaseToolAdapter):
    """Custom tool implementation."""
    
    def __init__(self):
        super().__init__(
            name="my_custom_tool",
            description="Brief description of what this tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "required_param": {
                        "type": "string",
                        "description": "Description of required parameter"
                    },
                    "optional_param": {
                        "type": "integer",
                        "description": "Description of optional parameter",
                        "default": 42
                    }
                },
                "required": ["required_param"]
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Implement your tool logic here.
        
        Args:
            parameters: Validated parameters from input schema
            
        Returns:
            Tool result (can be any JSON-serializable type)
            
        Raises:
            Exception: Any exceptions will be caught and returned as errors
        """
        required_param = parameters["required_param"]
        optional_param = parameters.get("optional_param", 42)
        
        # Implement your tool logic
        result = f"Processed {required_param} with {optional_param}"
        
        return result
```

#### Advanced Tool Features

```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class AdvancedTool(BaseToolAdapter):
    """Advanced tool with additional features."""
    
    def __init__(self):
        super().__init__(
            name="advanced_tool",
            description="Advanced tool with caching and logging",
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "string"},
                    "cache_ttl": {"type": "integer", "default": 300}
                },
                "required": ["data"]
            }
        )
        self.logger = logging.getLogger(f"mcp.tool.{self.name}")
        self.cache = {}
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        data = parameters["data"]
        cache_ttl = parameters.get("cache_ttl", 300)
        
        # Check cache first
        cache_key = f"data:{hash(data)}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < cache_ttl:
                self.logger.info(f"Cache hit for {cache_key}")
                return {"result": cached_result, "cached": True}
        
        # Process data
        self.logger.info(f"Processing data: {data[:50]}...")
        
        # Simulate async processing
        await asyncio.sleep(0.1)
        
        result = f"Processed: {data.upper()}"
        
        # Cache result
        self.cache[cache_key] = (result, datetime.now())
        
        return {
            "result": result,
            "cached": False,
            "processed_at": datetime.now().isoformat()
        }
```

### 3. Testing Phase

#### Unit Testing

```python
import pytest
from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation

class TestMyCustomTool:
    """Test suite for MyCustomTool."""
    
    @pytest.fixture
    def tool(self):
        return MyCustomTool()
    
    @pytest.mark.asyncio
    async def test_basic_execution(self, tool):
        """Test basic tool execution."""
        invocation = MCPToolInvocation(
            name="my_custom_tool",
            parameters={"required_param": "test_value"}
        )
        
        result = await tool.invoke(invocation)
        
        assert result.success is True
        assert "test_value" in result.data
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, tool):
        """Test parameter validation."""
        # Missing required parameter
        invocation = MCPToolInvocation(
            name="my_custom_tool",
            parameters={}
        )
        
        result = await tool.invoke(invocation)
        
        assert result.success is False
        assert "required_param" in result.error
    
    @pytest.mark.asyncio
    async def test_optional_parameters(self, tool):
        """Test optional parameter handling."""
        invocation = MCPToolInvocation(
            name="my_custom_tool",
            parameters={
                "required_param": "test",
                "optional_param": 100
            }
        )
        
        result = await tool.invoke(invocation)
        
        assert result.success is True
        assert "100" in result.data
```

#### Integration Testing

```python
import pytest
from claude_mpm.services.mcp_gateway import ToolRegistry

class TestToolIntegration:
    """Integration tests for tool registration and execution."""
    
    @pytest.fixture
    async def registry(self):
        registry = ToolRegistry()
        await registry.initialize()
        return registry
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, registry):
        """Test tool registration in registry."""
        tool = MyCustomTool()
        
        success = registry.register_tool(tool, category="test")
        assert success is True
        
        # Verify tool is listed
        tools = registry.list_tools()
        tool_names = [t.name for t in tools]
        assert "my_custom_tool" in tool_names
    
    @pytest.mark.asyncio
    async def test_tool_invocation_via_registry(self, registry):
        """Test tool invocation through registry."""
        tool = MyCustomTool()
        registry.register_tool(tool, category="test")
        
        invocation = MCPToolInvocation(
            name="my_custom_tool",
            parameters={"required_param": "registry_test"}
        )
        
        result = await registry.invoke_tool(invocation)
        
        assert result.success is True
        assert "registry_test" in result.data
```

### 4. Deployment Phase

#### Tool Registration

```python
# In your application startup code
from claude_mpm.services.mcp_gateway import ToolRegistry

async def register_custom_tools():
    """Register all custom tools."""
    registry = ToolRegistry()
    await registry.initialize()
    
    # Register tools
    registry.register_tool(MyCustomTool(), category="custom")
    registry.register_tool(AdvancedTool(), category="custom")
    
    return registry
```

#### CLI Integration

```python
# Add to CLI command for testing
import click
from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation

@click.command()
@click.option('--tool', required=True, help='Tool name to test')
@click.option('--params', default='{}', help='JSON parameters')
def test_custom_tool(tool: str, params: str):
    """Test custom tool via CLI."""
    import json
    import asyncio
    
    async def run_test():
        registry = await register_custom_tools()
        
        invocation = MCPToolInvocation(
            name=tool,
            parameters=json.loads(params)
        )
        
        result = await registry.invoke_tool(invocation)
        
        if result.success:
            print(f"✅ Success: {result.data}")
        else:
            print(f"❌ Error: {result.error}")
    
    asyncio.run(run_test())
```

## Best Practices

### 1. Input Validation

Always define comprehensive JSON schemas:

```python
input_schema = {
    "type": "object",
    "properties": {
        "email": {
            "type": "string",
            "format": "email",
            "description": "Valid email address"
        },
        "age": {
            "type": "integer",
            "minimum": 0,
            "maximum": 150,
            "description": "Age in years"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 10,
            "description": "List of tags"
        }
    },
    "required": ["email"],
    "additionalProperties": False
}
```

### 2. Error Handling

Provide meaningful error messages:

```python
async def execute(self, parameters: Dict[str, Any]) -> Any:
    try:
        # Tool logic here
        pass
    except FileNotFoundError as e:
        raise Exception(f"Required file not found: {e.filename}")
    except requests.RequestException as e:
        raise Exception(f"Network request failed: {str(e)}")
    except Exception as e:
        # Log the full error for debugging
        self.logger.error(f"Unexpected error in {self.name}: {e}", exc_info=True)
        raise Exception(f"Tool execution failed: {str(e)}")
```

### 3. Performance Optimization

```python
import asyncio
from functools import lru_cache

class OptimizedTool(BaseToolAdapter):
    """Tool with performance optimizations."""
    
    def __init__(self):
        super().__init__(...)
        self._connection_pool = None
    
    @lru_cache(maxsize=128)
    def _expensive_computation(self, data: str) -> str:
        """Cache expensive computations."""
        # Expensive operation here
        return result
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        # Use connection pooling for HTTP requests
        if self._connection_pool is None:
            self._connection_pool = aiohttp.ClientSession()
        
        # Batch operations when possible
        tasks = []
        for item in parameters.get("items", []):
            tasks.append(self._process_item(item))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"results": results}
```

### 4. Logging and Monitoring

```python
import logging
import time
from functools import wraps

class MonitoredTool(BaseToolAdapter):
    """Tool with comprehensive monitoring."""
    
    def __init__(self):
        super().__init__(...)
        self.logger = logging.getLogger(f"mcp.tool.{self.name}")
        self.metrics = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "total_time": 0.0
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        start_time = time.time()
        self.metrics["invocations"] += 1
        
        try:
            self.logger.info(f"Starting execution with params: {parameters}")
            
            result = await self._do_work(parameters)
            
            self.metrics["successes"] += 1
            self.logger.info(f"Execution completed successfully")
            
            return result
            
        except Exception as e:
            self.metrics["failures"] += 1
            self.logger.error(f"Execution failed: {e}")
            raise
            
        finally:
            execution_time = time.time() - start_time
            self.metrics["total_time"] += execution_time
            self.logger.debug(f"Execution time: {execution_time:.3f}s")
```

### 5. Configuration Management

```python
import os
from typing import Optional

class ConfigurableTool(BaseToolAdapter):
    """Tool with external configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(...)
        
        # Load configuration from multiple sources
        self.config = self._load_config(config)
    
    def _load_config(self, override_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration from environment, files, and overrides."""
        config = {
            "api_key": os.getenv("MY_TOOL_API_KEY"),
            "timeout": int(os.getenv("MY_TOOL_TIMEOUT", "30")),
            "base_url": os.getenv("MY_TOOL_BASE_URL", "https://api.example.com")
        }
        
        # Override with provided config
        if override_config:
            config.update(override_config)
        
        # Validate required config
        if not config["api_key"]:
            raise ValueError("MY_TOOL_API_KEY environment variable is required")
        
        return config
```

## Tool Categories

### Built-in Tools
- Maintained by the core team
- High reliability and performance standards
- Comprehensive test coverage

### User Tools
- Created by end users
- Moderate complexity
- Basic validation and testing

### Custom Tools
- Organization-specific tools
- May have external dependencies
- Custom deployment and maintenance

## Packaging and Distribution

### Python Package Structure

```
my_mcp_tools/
├── __init__.py
├── tools/
│   ├── __init__.py
│   ├── weather_tool.py
│   └── database_tool.py
├── tests/
│   ├── test_weather_tool.py
│   └── test_database_tool.py
├── setup.py
└── README.md
```

### Setup.py Example

```python
from setuptools import setup, find_packages

setup(
    name="my-mcp-tools",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "claude-mpm>=3.9.10",
        "requests>=2.25.0",
        "aiohttp>=3.8.0"
    ],
    entry_points={
        "claude_mpm.mcp_tools": [
            "weather = my_mcp_tools.tools.weather_tool:WeatherTool",
            "database = my_mcp_tools.tools.database_tool:DatabaseTool"
        ]
    }
)
```

## Related Documentation

- [MCP Gateway API Reference](../04-api-reference/mcp-gateway-api.md)
- [MCP Gateway Developer Guide](README.md)
- [Testing Guide](../03-development/testing.md)
