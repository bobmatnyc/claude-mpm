# MCP Services Integration

This document describes how Model Context Protocol (MCP) services are integrated into Claude MPM, including automatic installation, configuration, and development patterns.

## Overview

Claude MPM v4.4.1+ includes seamless integration with MCP services that extend the framework's capabilities. These services are automatically installed and configured to provide advanced functionality like code search and persistent memory management.

## Automatic Installation Pattern

### Installation Detection

The MCP service integration follows this detection pattern:

1. **Check Pipx Installation**: Look for pipx-installed packages first
2. **Check System PATH**: Fall back to system-wide installations
3. **Auto-Install**: Install via pipx if not found
4. **Graceful Degradation**: Continue without the service if installation fails

### Implementation Pattern

```python
async def _check_installation(self) -> bool:
    """Check if service is installed via pipx or system PATH."""
    # Check pipx installation first
    pipx_path = (
        Path.home()
        / ".local"
        / "pipx"
        / "venvs"
        / self.package_name
        / "bin"
        / self.service_name
    )
    if pipx_path.exists():
        self.service_cmd = str(pipx_path)
        return True

    # Check system PATH
    import shutil
    service_cmd = shutil.which(self.service_name)
    if service_cmd:
        self.service_cmd = service_cmd
        return True

    return False

async def _install_package(self) -> bool:
    """Install service using pipx (preferred over pip)."""
    try:
        # Check if pipx is available
        if not shutil.which("pipx"):
            self.log_warning(
                "pipx not found. Install it first: python -m pip install --user pipx"
            )
            return False

        self.log_info(f"Installing {self.package_name} via pipx...")
        result = subprocess.run(
            ["pipx", "install", self.package_name],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode == 0:
            self.log_info(f"Successfully installed {self.package_name} via pipx")
            return await self._check_installation()

        self.log_error(f"Failed to install {self.package_name}: {result.stderr}")
        return False

    except Exception as e:
        self.log_error(f"Error installing {self.package_name}: {e}")
        return False
```

## Available MCP Services

### mcp-vector-search

**Purpose**: Intelligent code search and project indexing
**Package**: `mcp-vector-search`
**Command**: `mcp-vector-search`

#### Features
- Semantic code search using vector embeddings
- Automatic project indexing on startup
- File pattern filtering and language detection
- Similarity-based code discovery
- Context-aware search results

#### Available Tools
- `search_code`: Search for code using semantic similarity
- `search_similar`: Find code similar to a specific file/function
- `search_context`: Search based on contextual description
- `get_project_status`: Check indexing status and statistics
- `index_project`: Force reindexing of the project

#### Usage Example
```python
# Search for authentication-related code
result = await invoke_mcp_tool("mcp_vector_search", {
    "action": "search_code",
    "query": "user authentication and login handling",
    "limit": 10
})
```

### kuzu-memory

**Purpose**: Persistent knowledge management with graph database
**Package**: `kuzu-memory`
**Command**: `kuzu-memory`

#### Features
- Project-specific memory databases
- Graph-based knowledge storage
- Semantic memory retrieval
- Automatic conversation learning
- Context enrichment for prompts

#### Available Tools
- `store`: Store a memory with optional tags
- `recall`: Retrieve relevant memories for a query
- `search`: Search memories by content
- `context`: Get enriched context for a topic

#### Usage Example
```python
# Store a memory
result = await invoke_mcp_tool("kuzu_memory", {
    "action": "store",
    "content": "User prefers TypeScript for this project",
    "tags": ["preferences", "technology"]
})

# Recall relevant memories
result = await invoke_mcp_tool("kuzu_memory", {
    "action": "recall",
    "query": "typescript preferences",
    "limit": 5
})
```

## Service Integration Architecture

### BaseToolAdapter Pattern

All MCP services extend `BaseToolAdapter` which provides:

```python
class BaseToolAdapter(ABC):
    """Base class for MCP tool adapters."""

    def __init__(self, definition: MCPToolDefinition):
        self.definition = definition
        self._initialized = False
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service."""
        pass

    @abstractmethod
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke the tool."""
        pass

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service."""
        pass
```

### Service Registration

Services are automatically registered with the MCP gateway:

```python
# In src/claude_mpm/services/mcp_gateway/tools/__init__.py
from .kuzu_memory_service import KuzuMemoryService
from .external_mcp_services import VectorSearchService

# Services are auto-discovered and registered
AVAILABLE_SERVICES = [
    KuzuMemoryService,
    VectorSearchService,
    # Add new services here
]
```

## Adding New MCP Services

### 1. Create Service Class

Create a new service class extending `BaseToolAdapter`:

```python
# src/claude_mpm/services/mcp_gateway/tools/my_service.py
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter
from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)

class MyService(BaseToolAdapter):
    """My custom MCP service."""

    def __init__(self):
        definition = MCPToolDefinition(
            name="my_service",
            description="Description of my service",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["action1", "action2"],
                        "description": "The action to perform",
                    },
                    # Add other parameters
                },
                "required": ["action"],
            },
        )
        super().__init__(definition)

        self.service_name = "my-service"
        self.package_name = "my-service-package"

    async def initialize(self) -> bool:
        """Initialize the service."""
        # Check installation and auto-install if needed
        self._is_installed = await self._check_installation()

        if not self._is_installed:
            await self._install_package()
            self._is_installed = await self._check_installation()

        if not self._is_installed:
            self.log_error(f"Failed to install {self.package_name}")
            return False

        self._initialized = True
        return True

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """Invoke the service tool."""
        params = invocation.parameters
        action = params.get("action")

        try:
            if action == "action1":
                result = await self.handle_action1(params)
            elif action == "action2":
                result = await self.handle_action2(params)
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )

            return MCPToolResult(
                success=result.get("success", False),
                data=result,
                error=result.get("error")
            )

        except Exception as e:
            return MCPToolResult(
                success=False,
                error=str(e)
            )

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters."""
        return True  # Implement validation logic

    async def shutdown(self) -> None:
        """Shutdown the service."""
        pass  # Cleanup if needed
```

### 2. Register Service

Add the service to the registry:

```python
# src/claude_mpm/services/mcp_gateway/tools/__init__.py
from .my_service import MyService

AVAILABLE_SERVICES = [
    KuzuMemoryService,
    VectorSearchService,
    MyService,  # Add your service here
]
```

### 3. Test Integration

Create tests for your service:

```python
# tests/test_my_service.py
import pytest
from claude_mpm.services.mcp_gateway.tools.my_service import MyService

@pytest.mark.asyncio
async def test_my_service_initialization():
    """Test service initialization."""
    service = MyService()
    result = await service.initialize()
    assert result is True or result is False  # Should not raise

@pytest.mark.asyncio
async def test_my_service_invoke():
    """Test service invocation."""
    service = MyService()
    await service.initialize()

    from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation

    invocation = MCPToolInvocation(
        parameters={"action": "action1"}
    )

    result = await service.invoke(invocation)
    assert hasattr(result, "success")
```

## Service Development Best Practices

### Error Handling

1. **Graceful Degradation**: Services should fail gracefully if not available
2. **Informative Logging**: Provide clear error messages and warnings
3. **Timeout Management**: Use reasonable timeouts for external commands
4. **Exception Handling**: Catch and handle specific exceptions appropriately

### Performance Considerations

1. **Lazy Initialization**: Only initialize when first used
2. **Connection Pooling**: Reuse connections where possible
3. **Caching**: Cache results when appropriate
4. **Async Operations**: Use async/await for I/O operations

### Security

1. **Input Validation**: Validate all parameters before use
2. **Command Injection Prevention**: Sanitize command arguments
3. **Path Traversal Protection**: Validate file paths
4. **Subprocess Security**: Use safe subprocess execution patterns

### Testing

1. **Unit Tests**: Test individual service methods
2. **Integration Tests**: Test service integration with MCP gateway
3. **Installation Tests**: Test auto-installation functionality
4. **Error Scenario Tests**: Test failure modes and recovery

## Configuration

### Service-Specific Configuration

Services can be configured via environment variables or config files:

```python
# Environment variables
KUZU_MEMORY_ENABLED=true
VECTOR_SEARCH_ENABLED=true
MCP_SERVICE_TIMEOUT=30

# Configuration in .claude-mpm/config.json
{
    "mcp_services": {
        "kuzu_memory": {
            "enabled": true,
            "auto_install": true
        },
        "vector_search": {
            "enabled": true,
            "auto_install": true,
            "index_on_startup": true
        }
    }
}
```

### Global MCP Configuration

MCP gateway configuration is handled in:
- `src/claude_mpm/services/mcp_config_manager.py`
- `.mcp.json` (project-level configuration)

## Troubleshooting

### Installation Issues

1. **Pipx Not Found**: Install pipx first: `python -m pip install --user pipx`
2. **Permission Errors**: Ensure proper permissions for installation directories
3. **Network Issues**: Check internet connectivity for package downloads
4. **Platform Issues**: Some packages may not be available on all platforms

### Runtime Issues

1. **Command Not Found**: Verify service installation and PATH
2. **Timeout Errors**: Increase timeout values in configuration
3. **Database Issues**: Check database permissions and disk space
4. **Memory Issues**: Monitor memory usage for large operations

### Debug Mode

Enable debug logging for detailed service information:

```bash
claude-mpm --logging DEBUG
```

This will show:
- Service detection and installation attempts
- Command execution details
- Error messages and stack traces
- Performance metrics

## Future Enhancements

### Planned Improvements

1. **Service Health Monitoring**: Real-time health checks and metrics
2. **Dynamic Service Loading**: Hot-reload services without restart
3. **Service Dependencies**: Manage dependencies between services
4. **Configuration UI**: Web-based service configuration interface
5. **Service Marketplace**: Discover and install community services

### Extension Points

1. **Custom Protocols**: Support for non-MCP protocols
2. **Service Mesh**: Distributed service architecture
3. **Authentication**: Service-level authentication and authorization
4. **Rate Limiting**: Per-service rate limiting and quotas
5. **Monitoring Integration**: Prometheus/Grafana integration

## See Also

- [MCP Gateway Documentation](13-mcp-gateway/README.md) - Core MCP gateway architecture
- [Kuzu-Memory Feature Guide](../user/03-features/kuzu-memory.md) - User-facing kuzu-memory documentation
- [Tool Development Guide](13-mcp-gateway/tool-development.md) - Developing MCP tools
- [Configuration Guide](13-mcp-gateway/configuration.md) - MCP configuration details