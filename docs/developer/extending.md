# Extending Claude MPM

Build custom agents, hooks, services, and MCP tools.

## Table of Contents

- [Custom Agents](#custom-agents)
- [Custom Hooks](#custom-hooks)
- [Custom Services](#custom-services)
- [MCP Tools](#mcp-tools)
- [Best Practices](#best-practices)

## Custom Agents

Create project-specific or personal agents.

### Quick Start

```bash
# Create agent in PROJECT tier
claude-mpm agents create my-agent

# Edit agent file
vim .claude-agents/my-agent.md
```

### Agent Structure

```markdown
---
name: my-agent
model: claude-sonnet-4
capabilities:
  - my-capability
  - another-capability
specialization: my-domain
delegation: true
version: "1.0.0"
---

# My Agent Instructions

[Your agent instructions here]

## Capabilities

- Capability 1: Description
- Capability 2: Description

## Examples

Example usage...
```

### Agent Tiers

**PROJECT** (`.claude-mpm/agents/`):
- Highest priority
- Project-specific
- Overrides everything

**USER** (`~/.claude-agents/`):
- Personal customizations
- Shared across projects
- Overrides SYSTEM

**SYSTEM** (bundled):
- Default agents
- Lowest priority

### Agent Frontmatter

**Required Fields:**
- `name`: Unique agent identifier
- `model`: Claude model (e.g., `claude-sonnet-4`)
- `instructions`: Agent behavior (in body)

**Optional Fields:**
- `capabilities`: List of capabilities
- `specialization`: Domain specialization
- `delegation`: Enable task delegation
- `version`: Semantic version
- `temperature`: Model temperature (0.0-1.0)
- `max_tokens`: Maximum response tokens

### Agent Instructions

Write clear, focused instructions:

```markdown
# Engineer Agent

You are a senior software engineer specializing in Python and TypeScript.

## Core Responsibilities

- Implement features following best practices
- Refactor code for maintainability
- Debug and fix issues systematically

## Workflow

1. Analyze requirements
2. Plan implementation approach
3. Write clean, tested code
4. Document changes

## Delegation

Delegate to:
- **QA Agent**: For test creation and validation
- **Documentation Agent**: For documentation updates
```

### Memory Integration

Store learnings via JSON response:

```json
{
  "memory-update": {
    "Project Architecture": ["Key architectural insight"],
    "Implementation Guidelines": ["Coding standard or pattern"]
  }
}
```

### Validation

```bash
# Validate agent syntax
claude-mpm agents validate --agent my-agent

# Validate all agents
claude-mpm agents validate
```

## Custom Hooks

Create pre/post execution hooks for customization.

### Hook Types

**Pre-execution**: Before agent invocation
- Validate input
- Modify context
- Abort execution

**Post-execution**: After agent completion
- Process results
- Trigger actions
- Log metrics

### Hook Creation

Create `.claude-mpm/hooks/my_hook.py`:

```python
from claude_mpm.hooks import HookContext, HookResult

async def pre_execution_hook(context: HookContext) -> HookResult:
    """Validate input before execution."""

    # Validation logic
    if not context.input.is_valid():
        return HookResult(
            abort=True,
            reason="Invalid input format"
        )

    # Modify context
    context.metadata["validated"] = True

    return HookResult(success=True)

async def post_execution_hook(context: HookContext) -> HookResult:
    """Process results after execution."""

    # Log completion
    logger.info(f"Task {context.task_id} completed")

    # Update metrics
    metrics.record(context.duration)

    return HookResult(success=True)
```

### Hook Registration

In `.claude-mpm/config.yaml`:

```yaml
hooks:
  pre_execution:
    enabled: true
    hooks:
      - my_hook.pre_execution_hook
  post_execution:
    enabled: true
    hooks:
      - my_hook.post_execution_hook
```

### Hook Context

Available context properties:

```python
class HookContext:
    task_id: str              # Unique task identifier
    agent_id: str             # Agent executing task
    input: str                # User input
    metadata: Dict[str, Any]  # Additional metadata
    timestamp: datetime       # Execution timestamp
    session_id: str           # Session identifier
```

### Hook Result

Return hook execution result:

```python
class HookResult:
    success: bool             # Hook succeeded
    abort: bool = False       # Abort execution
    reason: str = ""          # Failure/abort reason
    modified_context: Optional[HookContext] = None
```

## Custom Services

Extend framework with custom services.

### Service Interface

Create interface in `services/core/interfaces.py`:

```python
from abc import ABC, abstractmethod

class IMyService(ABC):
    @abstractmethod
    async def my_operation(self, param: str) -> Any:
        """Perform custom operation."""
        pass
```

### Service Implementation

Create implementation:

```python
from claude_mpm.services.core.base import BaseService
from claude_mpm.services.core.interfaces import IMyService

class MyService(BaseService, IMyService):
    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        """Initialize service resources."""
        self._client = await create_client()
        return True

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._client:
            await self._client.close()

    async def my_operation(self, param: str) -> Any:
        """Implement custom operation."""
        return await self._client.operation(param)
```

### Service Registration

Register with DI container:

```python
from claude_mpm.services.core import ServiceContainer

# Register service
container = ServiceContainer.get_instance()
container.register(
    IMyService,
    MyService,
    singleton=True
)

# Resolve service
my_service = container.resolve(IMyService)
```

### Service Best Practices

1. **Define Clear Interface**: Abstract base class with contracts
2. **Implement BaseService**: Use provided base classes
3. **Handle Initialization**: Proper setup and teardown
4. **Thread Safety**: Use locks for shared state
5. **Error Handling**: Graceful degradation
6. **Testing**: Mock interface for unit tests

## MCP Tools

Create Model Context Protocol tools for external integrations.

### MCP Tool Structure

Create `mcp_tools/my_tool/`:

```
my_tool/
├── __init__.py
├── server.py      # MCP server implementation
├── tool.py        # Tool definitions
└── config.yaml    # Tool configuration
```

### Tool Definition

In `tool.py`:

```python
from mcp import Tool, ToolInput, ToolOutput

class MyTool(Tool):
    name = "my_tool"
    description = "Description of what tool does"

    class Input(ToolInput):
        param1: str
        param2: int = 0

    class Output(ToolOutput):
        result: str

    async def execute(self, input: Input) -> Output:
        """Execute tool operation."""
        # Tool logic here
        result = await process(input.param1, input.param2)
        return Output(result=result)
```

### MCP Server

In `server.py`:

```python
from mcp import MCPServer
from .tool import MyTool

def create_server():
    server = MCPServer(
        name="my-tool-server",
        version="1.0.0"
    )

    # Register tools
    server.register_tool(MyTool)

    return server

if __name__ == "__main__":
    server = create_server()
    server.run()
```

### Tool Configuration

In `config.yaml`:

```yaml
name: my-tool
version: "1.0.0"
description: "My custom MCP tool"

server:
  host: localhost
  port: 8080

capabilities:
  - capability1
  - capability2

settings:
  timeout: 30
  retries: 3
```

### Tool Registration

Register with MCP Gateway:

In `.claude-mpm/config.yaml`:

```yaml
mcp_gateway:
  enabled: true
  tools:
    - name: my-tool
      enabled: true
      server: "python -m mcp_tools.my_tool.server"
      auto_start: true
```

### Tool Usage

Tools are available to agents automatically:

```python
# In agent code
result = await mcp.execute_tool("my_tool", {
    "param1": "value",
    "param2": 42
})
```

## Best Practices

### Agent Development

1. **Clear Purpose**: Single, well-defined responsibility
2. **Explicit Capabilities**: List all capabilities clearly
3. **Good Instructions**: Detailed, actionable guidance
4. **Examples**: Include usage examples
5. **Delegation**: Delegate when appropriate
6. **Memory Integration**: Store learnings for continuity

### Hook Development

1. **Fast Execution**: Keep hooks lightweight
2. **Error Handling**: Fail gracefully
3. **Idempotency**: Safe to execute multiple times
4. **Clear Logging**: Debug-friendly logs
5. **Configuration**: Make behavior configurable
6. **Testing**: Unit test hook logic

### Service Development

1. **Interface First**: Define interface before implementation
2. **Dependency Injection**: Use DI for dependencies
3. **Async Operations**: Use async for I/O operations
4. **Resource Management**: Proper initialization/cleanup
5. **Thread Safety**: Protect shared state
6. **Error Recovery**: Handle failures gracefully

### MCP Tool Development

1. **Well-Defined Interface**: Clear input/output schemas
2. **Documentation**: Document capabilities and usage
3. **Error Handling**: Return meaningful errors
4. **Performance**: Optimize for latency
5. **Security**: Validate all inputs
6. **Testing**: Integration test with gateway

### Testing

```bash
# Test custom agent
claude-mpm agents validate --agent my-agent
claude-mpm run -i "Task for my-agent" --agent my-agent

# Test hook
pytest tests/hooks/test_my_hook.py

# Test service
pytest tests/services/test_my_service.py

# Test MCP tool
pytest tests/mcp_tools/test_my_tool.py
```

---

**Next Steps:**
- API Reference: See [api-reference.md](api-reference.md)
- Architecture: See [architecture.md](architecture.md)
- Agent Patterns: See [../agents/agent-patterns.md](../agents/agent-patterns.md)
