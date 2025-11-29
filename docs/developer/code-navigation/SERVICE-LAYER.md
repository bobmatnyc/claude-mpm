# Service Layer Documentation

## Service Directory Structure

```
src/claude_mpm/services/
├── core/                    # Foundation services
│   ├── base.py             # BaseService, SyncBaseService
│   ├── interfaces.py       # All service interfaces
│   ├── service_container.py # DI helpers
│   └── cache_manager.py    # Caching utilities
├── agents/                  # Agent lifecycle services
│   ├── deployment/         # Deploy, version management
│   ├── loading/            # Template, profile loading
│   ├── management/         # Capabilities, operations
│   ├── memory/             # Agent memory persistence
│   └── registry/           # Discovery, tracking
├── communication/          # Real-time communication
├── project/                # Project analysis
├── infrastructure/         # Logging, monitoring
├── local_ops/              # Local process management
├── mcp_gateway/            # MCP protocol services
├── memory/                 # Memory caching
├── model/                  # Model routing
├── monitor/                # Dashboard backend
├── shared/                 # Base classes
├── socketio/               # WebSocket services
├── ticket_services/        # Ticketing CRUD
├── unified/                # Strategy implementations
└── version_control/        # Git operations
```

## Core Service Interfaces

### Primary Interfaces (`services/core/interfaces.py`)

| Interface | Purpose | Key Methods |
|-----------|---------|-------------|
| `IServiceContainer` | Dependency injection | `register()`, `resolve()`, `get()` |
| `IAgentRegistry` | Agent discovery | `discover_agents()`, `get_agent()`, `list_agents()` |
| `IHealthMonitor` | Health checks | `check_health()`, `get_system_health()` |
| `IConfigurationManager` | Config management | `get()`, `set()`, `get_section()` |
| `IPromptCache` | Prompt caching | `get()`, `set()`, `invalidate()` |
| `IEventBus` | Event distribution | `publish()`, `subscribe()` |

### Domain Interfaces

| Interface | Domain | Implementation |
|-----------|--------|----------------|
| `AgentDeploymentInterface` | Agents | `AgentDeploymentService` |
| `MemoryServiceInterface` | Memory | `AgentMemoryManager` |
| `HookServiceInterface` | Hooks | `HookService` |
| `SocketIOServiceInterface` | Communication | `SocketIOServer` |
| `ProjectAnalyzerInterface` | Project | `ProjectAnalyzer` |
| `TicketManagerInterface` | Tickets | `TicketManager` |

## Agent Services Detail

### Registry Services (`services/agents/registry/`)

```python
# AgentRegistry - Primary discovery service
class AgentRegistry(IAgentRegistry):
    async def discover_agents(self, force_refresh=False) -> Dict[str, AgentMetadata]
    async def get_agent(self, agent_name: str) -> Optional[AgentMetadata]
    async def list_agents(self, agent_type=None, tier=None) -> List[AgentMetadata]
    async def search_by_capability(self, capability: str) -> List[AgentMetadata]

# DeployedAgentDiscovery - Finds deployed agents
class DeployedAgentDiscovery:
    def discover_project_agents() -> List[AgentMetadata]
    def discover_user_agents() -> List[AgentMetadata]
    def discover_system_agents() -> List[AgentMetadata]

# AgentModificationTracker - Change tracking
class AgentModificationTracker:
    def track_modification(agent_id, change_type)
    def get_recent_modifications(agent_id) -> List[Modification]
```

### Deployment Services (`services/agents/deployment/`)

```python
# AgentDeploymentService - Deploy agents
class AgentDeploymentService(AgentDeploymentInterface):
    def deploy_agents(force=False, include_all=False) -> Dict[str, Any]
    def validate_agent(agent_path: Path) -> Tuple[bool, List[str]]
    def clean_deployment(preserve_user_agents=True) -> bool
    def get_deployment_status() -> Dict[str, Any]

# AgentVersionManager - Version control
class AgentVersionManager:
    def get_current_version(agent_id) -> str
    def bump_version(agent_id, bump_type) -> str
    def compare_versions(v1, v2) -> int

# AgentLifecycleManager - Lifecycle operations
class AgentLifecycleManager:
    async def initialize_agent(agent_id)
    async def start_agent(agent_id)
    async def stop_agent(agent_id)
    async def restart_agent(agent_id)
```

### Memory Services (`services/agents/memory/`)

```python
# AgentMemoryManager - Memory CRUD
class AgentMemoryManager(MemoryServiceInterface):
    def load_memory(agent_id: str) -> Optional[str]
    def save_memory(agent_id: str, content: str) -> bool
    def validate_memory_size(content: str) -> Tuple[bool, Optional[str]]
    def optimize_memory(agent_id: str) -> bool
    def get_memory_metrics(agent_id=None) -> Dict[str, Any]

# AgentPersistenceService - Persistence layer
class AgentPersistenceService:
    def persist_state(agent_id, state)
    def restore_state(agent_id) -> Optional[Dict]
```

## Hook Services

### Hook Service (`services/hook_service.py`)

```python
class HookService(HookServiceInterface):
    def register_hook(hook: Any) -> bool
    def execute_pre_delegation_hooks(context: Any) -> Any
    def execute_post_delegation_hooks(context: Any) -> Any
    def get_registered_hooks() -> Dict[str, List[Any]]
    def clear_hooks(hook_type=None) -> None
```

### Hook Manager (`core/hook_manager.py`)

```python
class HookManager:
    def __init__(self, container: DIContainer)
    async def execute_pre_tool_hooks(context: HookContext) -> HookResult
    async def execute_post_tool_hooks(context: HookContext) -> HookResult
    def register_hook(hook: BaseHook, priority: int = 0)
```

## Project Services

### Project Analyzer (`services/project/analyzer.py`)

```python
class ProjectAnalyzer(ProjectAnalyzerInterface):
    def analyze_project(project_path=None) -> ProjectCharacteristics
    def detect_technology_stack() -> List[str]
    def analyze_code_patterns() -> Dict[str, Any]
    def get_project_structure() -> Dict[str, Any]
    def identify_entry_points() -> List[Path]
```

### Toolchain Analyzer (`services/project/toolchain_analyzer.py`)

```python
class ToolchainAnalyzer:
    def detect_frameworks() -> List[str]
    def detect_package_manager() -> str
    def detect_testing_framework() -> str
    def get_build_commands() -> Dict[str, str]
```

## Communication Services

### SocketIO Server (`services/socketio_server.py`)

```python
class SocketIOServer(SocketIOServiceInterface):
    async def start(host="localhost", port=8765) -> None
    async def stop() -> None
    async def emit(event: str, data: Any, room=None) -> None
    async def broadcast(event: str, data: Any) -> None
    def get_connection_count() -> int
    def is_running() -> bool
```

### Event Bus (`services/event_bus/event_bus.py`)

```python
class EventBus(IEventBus):
    def publish(event_type: str, data: Any) -> None
    def subscribe(event_type: str, handler: callable) -> str
    def unsubscribe(subscription_id: str) -> None
    async def publish_async(event_type: str, data: Any) -> None
```

## MCP Gateway Services

### MCP Server (`services/mcp_gateway/server/mcp_server.py`)

```python
class MCPServer:
    def start(port: int) -> None
    def stop() -> None
    def register_tool(tool: MCPTool) -> None
    def handle_request(request: MCPRequest) -> MCPResponse
```

### MCP Tool Registry (`services/mcp_gateway/tools/tool_registry.py`)

```python
class MCPToolRegistry:
    def register_tool(name: str, handler: callable, schema: dict) -> None
    def get_tool(name: str) -> Optional[MCPTool]
    def list_tools() -> List[MCPTool]
    def execute_tool(name: str, args: dict) -> Any
```

## Infrastructure Services

### Health Monitor (`services/infrastructure/monitoring/`)

```python
class AdvancedHealthMonitor(IHealthMonitor):
    async def check_health(service_name: str) -> HealthStatus
    async def get_system_health() -> HealthStatus
    def register_health_check(service_name: str, check_func: callable) -> None
    async def start_monitoring() -> None
    async def stop_monitoring() -> None
```

### Logging Service (`services/infrastructure/logging.py`)

```python
class LoggingService(IStructuredLogger):
    def debug(message: str, **kwargs) -> None
    def info(message: str, **kwargs) -> None
    def warning(message: str, **kwargs) -> None
    def error(message: str, **kwargs) -> None
    def set_context(**kwargs) -> None
```

## Shared Base Classes

### Service Bases (`services/shared/`)

```python
# AsyncServiceBase - For async services
class AsyncServiceBase:
    async def start() -> None
    async def stop() -> None
    async def health_check() -> bool

# ConfigServiceBase - For config-dependent services
class ConfigServiceBase:
    def get_config(key: str, default=None) -> Any
    def reload_config() -> None

# LifecycleServiceBase - For managed lifecycle
class LifecycleServiceBase:
    def initialize() -> None
    def start() -> None
    def stop() -> None
    def is_running() -> bool

# ManagerBase - For manager patterns
class ManagerBase:
    def register(item) -> None
    def unregister(item_id) -> None
    def get(item_id) -> Optional[Any]
    def list_all() -> List[Any]
```

## Service Dependencies Graph

```
DIContainer
    │
    ├── IConfigurationManager (no deps)
    │
    ├── IAgentRegistry
    │   └── depends on: ConfigurationManager
    │
    ├── IHealthMonitor
    │   └── depends on: ConfigurationManager, EventBus
    │
    ├── IHookService
    │   └── depends on: AgentRegistry, EventBus
    │
    ├── IEventBus
    │   └── depends on: ConfigurationManager
    │
    ├── SocketIOServer
    │   └── depends on: EventBus, ConfigurationManager
    │
    └── MCPServer
        └── depends on: ToolRegistry, ConfigurationManager
```

## Service Initialization Order

1. `ConfigurationManager` - Configuration must be first
2. `EventBus` - Event distribution infrastructure
3. `AgentRegistry` - Agent discovery
4. `HookService` - Hook registration
5. `HealthMonitor` - Health monitoring
6. `SocketIOServer` - Real-time communication (optional)
7. `MCPServer` - MCP gateway (optional)

---
See also:
- [CODE-PATHS.md](CODE-PATHS.md) for execution flows
- [HOOKS-AND-EXTENSIONS.md](HOOKS-AND-EXTENSIONS.md) for hook system
