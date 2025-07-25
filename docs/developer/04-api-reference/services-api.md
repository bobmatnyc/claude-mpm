# Services API Reference

This document provides a comprehensive API reference for the service layer components of Claude MPM.

## Table of Contents

1. [Overview](#overview)
2. [Hook Service](#hook-service)
3. [Agent Management Service](#agent-management-service)
4. [Ticket Manager](#ticket-manager)
5. [Shared Prompt Cache](#shared-prompt-cache)
6. [Framework Agent Loader](#framework-agent-loader)

---

## Overview

The services layer provides business logic and integration capabilities for Claude MPM. Services handle cross-cutting concerns like hooks, agent lifecycle, ticket management, and caching.

---

## Hook Service

The hook service provides a centralized system for managing pre/post hooks and event handling.

### Location
`src/claude_mpm/services/hook_service.py`

### HookRegistry Class

```python
class HookRegistry:
    """Registry for managing hooks."""
```

### Constructor

```python
def __init__(self)
```

### Key Methods

#### register()

```python
def register(self, hook: BaseHook, hook_type: Optional[HookType] = None) -> bool
```

Register a hook instance.

**Parameters:**
- `hook` (BaseHook): Hook instance to register
- `hook_type` (Optional[HookType]): Optional hook type override

**Returns:** True if registered successfully

**Example:**
```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext

class MyHook(SubmitHook):
    def execute(self, context: HookContext) -> HookResult:
        # Hook implementation
        pass

registry = HookRegistry()
hook = MyHook(name="my-hook", priority=10)
registry.register(hook)
```

#### unregister()

```python
def unregister(self, hook_name: str) -> bool
```

Unregister a hook by name.

#### get_hooks()

```python
def get_hooks(self, hook_type: HookType) -> List[BaseHook]
```

Get all hooks of a specific type, sorted by priority.

#### execute_hooks()

```python
async def execute_hooks(
    self, 
    hook_type: HookType, 
    context: HookContext
) -> List[HookResult]
```

Execute all hooks of a given type.

**Example:**
```python
context = HookContext(
    hook_type=HookType.SUBMIT,
    data={"message": "User input"},
    metadata={"session_id": "123"}
)

results = await registry.execute_hooks(HookType.SUBMIT, context)
```

### HookService Class

Web service wrapper for hook registry.

```python
class HookService:
    """Flask-based hook service."""
    
    def __init__(self, port: int = 8080)
```

### REST API Endpoints

#### POST /hooks/register
Register a new hook.

**Request Body:**
```json
{
    "name": "my-hook",
    "type": "submit",
    "priority": 10,
    "module": "my_module.MyHook"
}
```

#### DELETE /hooks/{name}
Unregister a hook.

#### GET /hooks
List all registered hooks.

#### POST /hooks/execute
Execute hooks of a specific type.

**Request Body:**
```json
{
    "type": "submit",
    "context": {
        "data": {"message": "Hello"},
        "metadata": {"session_id": "123"}
    }
}
```

---

## Agent Management Service

Manages agent lifecycle and orchestration.

### Location
`src/claude_mpm/services/agent_management_service.py`

### AgentManagementService Class

```python
class AgentManagementService:
    """Service for managing agent lifecycle and delegation."""
    
    def __init__(self, registry: AgentRegistryAdapter)
```

### Key Methods

#### delegate_task()

```python
async def delegate_task(
    self,
    agent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None
) -> Dict[str, Any]
```

Delegate a task to an agent.

**Parameters:**
- `agent_name` (str): Name of the agent
- `task` (str): Task description
- `context` (Optional[Dict]): Additional context
- `timeout` (Optional[float]): Execution timeout

**Returns:** Result dictionary with execution details

**Example:**
```python
service = AgentManagementService(registry)
result = await service.delegate_task(
    "engineer",
    "Implement user authentication",
    context={"framework": "FastAPI"}
)
```

#### get_agent_status()

```python
def get_agent_status(self, agent_name: str) -> Dict[str, Any]
```

Get current status of an agent.

**Returns:**
```python
{
    "name": "engineer",
    "status": "available",
    "current_task": None,
    "last_active": "2024-01-15T10:30:00Z"
}
```

#### list_active_delegations()

```python
def list_active_delegations(self) -> List[Dict[str, Any]]
```

List all active agent delegations.

### AgentLifecycleManager Class

```python
class AgentLifecycleManager:
    """Manages agent lifecycle events."""
    
    def __init__(self, service: AgentManagementService)
```

### Lifecycle Methods

```python
def on_agent_start(self, agent_name: str)
def on_agent_complete(self, agent_name: str, result: Any)
def on_agent_error(self, agent_name: str, error: Exception)
```

---

## Ticket Manager

Manages ticket creation and tracking.

### Location
`src/claude_mpm/services/ticket_manager.py`

### TicketManager Class

```python
class TicketManager:
    """Service for managing tickets."""
    
    def __init__(self, backend: str = "file")
```

### Key Methods

#### create_ticket()

```python
def create_ticket(
    self,
    title: str,
    ticket_type: str = "TASK",
    description: str = "",
    source: str = "claude-mpm",
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

Create a new ticket.

**Parameters:**
- `title` (str): Ticket title
- `ticket_type` (str): Type (TASK, BUG, FEATURE)
- `description` (str): Detailed description
- `source` (str): Source system
- `metadata` (Optional[Dict]): Additional metadata

**Returns:** Ticket ID

**Example:**
```python
manager = TicketManager()
ticket_id = manager.create_ticket(
    title="Add user authentication",
    ticket_type="FEATURE",
    description="Implement OAuth2 authentication"
)
```

#### get_ticket()

```python
def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]
```

Retrieve ticket by ID.

#### update_ticket()

```python
def update_ticket(
    self,
    ticket_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    **kwargs
) -> bool
```

Update ticket properties.

#### list_tickets()

```python
def list_tickets(
    self,
    ticket_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]
```

List tickets with optional filters.

### Ticket Structure

```python
{
    "id": "TSK-001",
    "title": "Implement feature",
    "type": "TASK",
    "status": "open",
    "description": "...",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z",
    "source": "claude-mpm",
    "metadata": {}
}
```

---

## Shared Prompt Cache

Caching service for prompts and responses.

### Location
`src/claude_mpm/services/shared_prompt_cache.py`

### SharedPromptCache Class

```python
class SharedPromptCache:
    """LRU cache for prompts and responses."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600)
```

**Parameters:**
- `max_size` (int): Maximum cache entries
- `ttl` (int): Time-to-live in seconds

### Key Methods

#### get()

```python
def get(self, key: str) -> Optional[Any]
```

Retrieve value from cache.

#### set()

```python
def set(self, key: str, value: Any, ttl: Optional[int] = None)
```

Store value in cache.

**Parameters:**
- `key` (str): Cache key
- `value` (Any): Value to cache
- `ttl` (Optional[int]): Override default TTL

#### invalidate()

```python
def invalidate(self, pattern: Optional[str] = None)
```

Invalidate cache entries.

**Parameters:**
- `pattern` (Optional[str]): Glob pattern for keys to invalidate

### Usage Example

```python
cache = SharedPromptCache(max_size=500, ttl=1800)

# Cache a prompt response
cache.set("prompt:greeting", "Hello! How can I help?")

# Retrieve from cache
response = cache.get("prompt:greeting")

# Invalidate related entries
cache.invalidate("prompt:*")
```

---

## Framework Agent Loader

Loads and manages agent definitions from the framework.

### Location
`src/claude_mpm/services/framework_agent_loader.py`

### FrameworkAgentLoader Class

```python
class FrameworkAgentLoader:
    """Loader for framework agent definitions."""
    
    def __init__(
        self,
        framework_path: Path,
        cache_enabled: bool = True
    )
```

### Key Methods

#### load_agent()

```python
def load_agent(self, agent_name: str) -> Optional[Dict[str, Any]]
```

Load an agent definition.

**Returns:**
```python
{
    "name": "engineer",
    "template": "agent content...",
    "metadata": {
        "specializations": ["backend", "api"],
        "version": "1.0.0"
    }
}
```

#### load_all_agents()

```python
def load_all_agents() -> Dict[str, Dict[str, Any]]
```

Load all available agent definitions.

#### refresh_cache()

```python
def refresh_cache()
```

Refresh the agent definition cache.

---

## Service Integration

### Combining Services

```python
from claude_mpm.services import (
    HookRegistry,
    AgentManagementService,
    TicketManager,
    SharedPromptCache
)
from claude_mpm.core.agent_registry import AgentRegistryAdapter

# Initialize services
registry = AgentRegistryAdapter()
hook_registry = HookRegistry()
agent_service = AgentManagementService(registry)
ticket_manager = TicketManager()
cache = SharedPromptCache()

# Create delegation hook
class DelegationHook(PreDelegationHook):
    def __init__(self, ticket_manager):
        super().__init__(name="ticket-creator", priority=5)
        self.ticket_manager = ticket_manager
    
    async def execute(self, context: HookContext) -> HookResult:
        # Create ticket for delegation
        ticket_id = self.ticket_manager.create_ticket(
            title=f"Delegation: {context.data['task']}",
            ticket_type="TASK",
            metadata={"agent": context.data['agent']}
        )
        
        return HookResult(
            success=True,
            data={"ticket_id": ticket_id}
        )

# Register hook
hook = DelegationHook(ticket_manager)
hook_registry.register(hook)
```

### Service Lifecycle Management

```python
class ServiceManager:
    """Manages service lifecycle."""
    
    def __init__(self):
        self.services = {}
    
    def register_service(self, name: str, service: Any):
        self.services[name] = service
    
    def start_all(self):
        for name, service in self.services.items():
            if hasattr(service, 'start'):
                service.start()
    
    def stop_all(self):
        for name, service in self.services.items():
            if hasattr(service, 'stop'):
                service.stop()

# Usage
manager = ServiceManager()
manager.register_service("hooks", hook_registry)
manager.register_service("agents", agent_service)
manager.register_service("tickets", ticket_manager)

# Start all services
manager.start_all()

# ... application logic ...

# Cleanup
manager.stop_all()
```

---

## Error Handling

Services implement consistent error handling:

1. **Service Errors**: Logged and return error responses
2. **Validation Errors**: Return 400-level errors with details
3. **System Errors**: Return 500-level errors with safe messages
4. **Async Errors**: Properly propagated through async chains

### Example Error Handling

```python
try:
    result = await agent_service.delegate_task(
        "unknown_agent",
        "Some task"
    )
except AgentNotFoundError as e:
    logger.error(f"Agent not found: {e}")
    # Handle gracefully
except DelegationTimeoutError as e:
    logger.error(f"Delegation timeout: {e}")
    # Retry or escalate
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Generic error handling
```

---

## Best Practices

1. **Service Initialization**:
   - Initialize services once and reuse
   - Use dependency injection for service dependencies
   - Configure services through environment or config files

2. **Caching**:
   - Use SharedPromptCache for expensive operations
   - Set appropriate TTLs based on data volatility
   - Implement cache warming for critical data

3. **Hook Management**:
   - Keep hooks lightweight and fast
   - Use appropriate priorities for execution order
   - Implement timeout handling for long-running hooks

4. **Ticket Tracking**:
   - Create tickets for significant events
   - Use consistent ticket types and metadata
   - Implement ticket lifecycle (open → in_progress → closed)