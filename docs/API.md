# API Reference

Complete API documentation for Claude MPM services and interfaces.

## Overview

This document provides a high-level overview of Claude MPM's APIs. For detailed technical documentation, see [developer/api-reference.md](developer/api-reference.md).

## Quick Reference

### Command-Line Interface

```bash
# Core commands
claude-mpm run [--monitor] [--resume]  # Start session
claude-mpm configure                    # Interactive configuration
claude-mpm doctor [--verbose]          # System diagnostics
claude-mpm verify [--fix]              # MCP service verification

# Session management
claude-mpm mpm-init pause              # Pause current session
claude-mpm mpm-init resume             # Resume paused session

# Memory management
claude-mpm memory init                 # Initialize agent memory
claude-mpm cleanup-memory [--days 7]   # Clean conversation history

# Code search
claude-mpm search "query"              # Semantic code search

# MCP gateway
claude-mpm mcp                         # Start MCP gateway
```

See [user/getting-started.md](user/getting-started.md) for usage examples.

### Python API

```python
from claude_mpm.services import ServiceContainer
from claude_mpm.agents import AgentRegistry

# Initialize service container
container = ServiceContainer()

# Get agent registry
registry = container.get(AgentRegistry)

# Load agents
agents = registry.discover_agents()

# Get specific agent
pm_agent = registry.get_agent("pm")
```

See [developer/api-reference.md](developer/api-reference.md) for complete API.

## Service Architecture

Claude MPM uses a service-oriented architecture with five domains:

1. **Core Services** - Foundation interfaces and base classes
2. **Agent Services** - Agent lifecycle and management
3. **Communication Services** - Real-time monitoring and events
4. **Project Services** - Project analysis and workspace
5. **Utility Services** - Supporting functionality

See [developer/ARCHITECTURE.md](developer/ARCHITECTURE.md) for architectural details.

## Service Interfaces

### IServiceContainer

Dependency injection container:

```python
class IServiceContainer:
    def get(self, interface: Type[T]) -> T: ...
    def register(self, interface: Type, implementation: Type): ...
    def singleton(self, interface: Type, instance: Any): ...
```

### IAgentRegistry

Agent discovery and management:

```python
class IAgentRegistry:
    def discover_agents(self) -> List[Agent]: ...
    def get_agent(self, name: str) -> Optional[Agent]: ...
    def load_agent(self, path: Path) -> Agent: ...
```

### IHealthMonitor

Service health monitoring:

```python
class IHealthMonitor:
    def check_health(self) -> HealthStatus: ...
    def register_service(self, name: str, checker: Callable): ...
```

### IConfigurationManager

Configuration management:

```python
class IConfigurationManager:
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any): ...
    def save(self): ...
```

See [developer/api-reference.md](developer/api-reference.md) for complete interface documentation.

## Hook System API

Hooks enable event-driven extensions:

```python
from claude_mpm.hooks import HookManager

# Register hook
@hook_manager.register("pre_tool_use")
def my_hook(context: HookContext) -> HookResult:
    # Hook logic here
    return HookResult(success=True)

# Hook types
# - pre_tool_use: Before tool execution
# - post_tool_use: After tool execution
# - session_start: Session initialization
# - session_end: Session cleanup
```

See [developer/pretool-use-hooks.md](developer/pretool-use-hooks.md) for hook development.

## MCP Gateway API

Model Context Protocol integration:

```python
from claude_mpm.mcp import MCPGateway

# Initialize gateway
gateway = MCPGateway()

# Register MCP server
gateway.register_server("my-server", config)

# Execute tool
result = gateway.execute_tool("server", "tool", params)
```

See [developer/13-mcp-gateway/README.md](developer/13-mcp-gateway/README.md) for MCP integration.

## Agent API

Agent frontmatter schema:

```yaml
---
name: string          # Required, unique identifier
version: string       # Required, semantic version
capabilities: array   # Required, list of capabilities
description: string   # Optional, brief description
priority: number      # Optional, selection priority
---
```

Agent memory API:

```json
{
  "remember": ["Learning 1", "Learning 2"],
  "MEMORIES": ["Complete replacement"]
}
```

See [agents/creating-agents.md](agents/creating-agents.md) for agent development.

## Configuration API

Configuration YAML structure:

```yaml
# Session management
session:
  auto_save:
    enabled: true
    interval: 300

# Context management
context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.70
    warning: 0.85
    critical: 0.95

# Agent configuration
agents:
  pm:
    enabled: true
    capabilities:
      - orchestration
```

See [configuration.md](configuration.md) for complete reference.

## REST API (Monitoring)

Real-time monitoring endpoints:

```
GET  /health              # Health check
GET  /status              # Current status
GET  /agents              # Agent list
POST /agents/:name/invoke # Invoke agent
```

See [developer/11-dashboard/README.md](developer/11-dashboard/README.md) for monitoring API.

## WebSocket API

Real-time event streaming:

```javascript
// Connect to monitoring
socket.connect('http://localhost:5000');

// Event types
socket.on('agent_activity', data => { ... });
socket.on('file_operation', data => { ... });
socket.on('session_update', data => { ... });
```

See [developer/11-dashboard/README.md](developer/11-dashboard/README.md) for WebSocket protocol.

## Error Handling

Standard error types:

```python
from claude_mpm.exceptions import (
    ClaudeMPMError,          # Base exception
    AgentNotFoundError,      # Agent lookup failed
    ConfigurationError,      # Invalid configuration
    ValidationError,         # Input validation failed
    ServiceError,            # Service operation failed
)
```

## Testing API

Testing utilities:

```python
from claude_mpm.testing import (
    MockAgent,           # Mock agent for testing
    MockServiceContainer, # Mock DI container
    TestFixtures,        # Test data fixtures
)
```

See [developer/extending.md](developer/extending.md) for testing patterns.

## See Also

- **[Developer API Reference](developer/api-reference.md)** - Complete technical documentation
- **[Architecture](developer/ARCHITECTURE.md)** - System design details
- **[Extending](developer/extending.md)** - Building extensions
- **[Agent System](AGENTS.md)** - Agent development
- **[Configuration](configuration.md)** - Configuration options
- **[User Guide](user/user-guide.md)** - End-user documentation

---

**For detailed API documentation**: See [developer/api-reference.md](developer/api-reference.md)
