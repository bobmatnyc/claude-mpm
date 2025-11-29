# Architecture Overview

## System Design Philosophy

Claude MPM follows a **Service-Oriented Architecture (SOA)** with:
- Interface-based contracts for loose coupling
- Dependency injection via `DIContainer`
- Lazy initialization for performance
- Hook-based extensibility

## Core Architectural Layers

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer                          │
│  (commands/, parsers/, interactive/)                │
├─────────────────────────────────────────────────────┤
│                 Service Layer                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  Agent  │ │  Hook   │ │  MCP    │ │ Project │  │
│  │Services │ │ System  │ │ Gateway │ │Services │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
├─────────────────────────────────────────────────────┤
│                 Core Layer                           │
│  (DI Container, Interfaces, Configuration)          │
├─────────────────────────────────────────────────────┤
│               Infrastructure                         │
│  (Logging, Monitoring, SocketIO, Events)            │
└─────────────────────────────────────────────────────┘
```

## Five Service Domains

### 1. Core Services (`services/core/`)
- **Purpose**: Foundation services and dependency injection
- **Key Components**:
  - `DIContainer` - Service registration and resolution
  - `IServiceContainer` - DI interface contract
  - `BaseService` - Common service functionality
  - `ServiceLifetime` - Singleton/Transient/Scoped management

### 2. Agent Services (`services/agents/`)
- **Purpose**: Agent lifecycle and management
- **Sub-modules**:
  - `deployment/` - Agent deployment and versioning
  - `loading/` - Agent profile and template loading
  - `management/` - Agent capabilities and operations
  - `memory/` - Agent memory persistence
  - `registry/` - Agent discovery (3-tier: PROJECT > USER > SYSTEM)

### 3. Communication Services (`services/communication/`, `services/socketio/`)
- **Purpose**: Real-time event streaming and dashboard
- **Key Components**:
  - `SocketIOServer` - WebSocket server for monitoring
  - `EventBus` - Internal event distribution
  - `DashboardServer` - Web dashboard integration

### 4. Project Services (`services/project/`)
- **Purpose**: Project analysis and workspace management
- **Key Components**:
  - `ProjectAnalyzer` - Technology stack detection
  - `ToolchainAnalyzer` - Framework identification
  - `ProjectRegistry` - Project configuration storage

### 5. Infrastructure Services (`services/infrastructure/`)
- **Purpose**: Cross-cutting concerns
- **Key Components**:
  - `LoggingService` - Structured logging
  - `HealthMonitor` - Service health checks
  - `ResumeLogGenerator` - Session context preservation

## Dependency Injection Pattern

```python
# Registration (typically in startup)
container = DIContainer()
container.register_singleton(IAgentRegistry, AgentRegistry)
container.register_factory(IHookService, lambda c: HookService(c.get(IAgentRegistry)))

# Resolution (in service code)
agent_registry = container.get(IAgentRegistry)
```

## Interface Contracts

All major services implement interfaces defined in `services/core/interfaces.py`:

| Interface | Purpose | Implementation |
|-----------|---------|----------------|
| `IServiceContainer` | DI container | `DIContainer` |
| `IAgentRegistry` | Agent discovery | `AgentRegistry` |
| `IHealthMonitor` | Health checks | `AdvancedHealthMonitor` |
| `IPromptCache` | Caching | `SimpleCacheService` |
| `IEventBus` | Event distribution | `EventBus` |

## Configuration Hierarchy

Configuration follows a precedence order (highest to lowest):
1. **CLI Arguments** - Runtime overrides
2. **Project Config** - `.claude-mpm/configuration.yaml`
3. **User Config** - `~/.claude-mpm/configuration.yaml`
4. **System Defaults** - Built-in defaults

## Agent Three-Tier Hierarchy

Agents are discovered with precedence:
1. **PROJECT** - `.claude-mpm/agents/` - Project-specific customizations
2. **USER** - `~/.claude/agents/` - User personal agents
3. **SYSTEM** - `src/claude_mpm/agents/templates/` - Bundled defaults

## Hook Execution Flow

```
Request → Pre-Tool Hooks → Tool Execution → Post-Tool Hooks → Response
              │                                     │
              └── Memory Hooks                      └── Learning Hooks
                  Enrichment Hooks                      Response Hooks
```

## Key Design Patterns

### Factory Pattern
Used for service creation with configuration:
```python
# services/shared/service_factory.py
class ServiceFactory:
    def create(self, service_type, **kwargs) -> Any
```

### Strategy Pattern
Used for pluggable behaviors:
```python
# services/unified/strategies.py
# Detection strategies for project analysis
```

### Observer Pattern
Used for event handling:
```python
# services/agents/observers.py
# Agent lifecycle observers
```

### Singleton Pattern
Managed by DI container for shared state:
```python
container.register_singleton(IConfigurationManager, ConfigManager)
```

## Performance Optimizations

1. **Lazy Loading** - Services initialized on-demand
2. **Caching** - Git branch caching (5-min TTL), agent discovery caching
3. **Async Operations** - Non-blocking I/O for external calls
4. **Connection Pooling** - Reused HTTP/WebSocket connections

## Security Model

1. **Input Validation** - All CLI inputs validated
2. **Path Sanitization** - Prevents directory traversal
3. **Command Injection Prevention** - Subprocess argument escaping
4. **Filesystem Restrictions** - Sandboxed operations

---
See also:
- [SERVICE-LAYER.md](SERVICE-LAYER.md) for detailed service documentation
- [CODE-PATHS.md](CODE-PATHS.md) for execution flow tracing
