# Claude MPM Architecture

**Version**: 4.2.2  
**Last Updated**: September 2, 2025

Claude MPM (Multi-Agent Project Manager) is built on a service-oriented architecture that extends Claude Code with multi-agent orchestration capabilities.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)  
- [Service Layer](#service-layer)
- [Agent System](#agent-system)
- [Communication Layer](#communication-layer)
- [Performance Features](#performance-features)
- [Security Framework](#security-framework)
- [Development Patterns](#development-patterns)

## Overview

### Core Principles

1. **Service-Oriented Architecture**: Business logic organized into 5 specialized service domains
2. **Interface-Based Contracts**: All services implement explicit interfaces
3. **Dependency Injection**: Loose coupling through service container
4. **Lazy Loading**: 50-80% performance improvement through deferred initialization
5. **Security First**: Comprehensive input validation and sanitization
6. **Agent Hierarchy**: 3-tier precedence system (PROJECT > USER > SYSTEM)

### Architecture Benefits

- **Performance**: 50-80% improvement through lazy loading and caching
- **Security**: Defense-in-depth with multi-layer validation
- **Testability**: Interface-based design enables easy mocking
- **Maintainability**: Clear service boundaries and separation of concerns
- **Scalability**: Service-oriented design supports future growth

## Project Structure

```
claude-mpm/
├── .claude/                          # Claude Code configuration
├── .claude-mpm/                      # Project-specific configuration
│   ├── agents/                       # PROJECT tier agents (highest precedence)
│   ├── config/                       # Project configuration
│   ├── hooks/                        # Project hooks
│   └── memories/                     # Agent memory files
│
├── src/claude_mpm/                   # Main package source
│   ├── core/                         # Core framework components
│   ├── services/                     # Service layer (5 domains)
│   ├── agents/                       # USER tier agents
│   ├── hooks/                        # Hook system
│   ├── cli/                          # Command-line interface
│   └── utils/                        # Utilities and helpers
│
├── docs/                             # Documentation
├── tests/                            # Test suite
├── scripts/                          # Executable scripts
└── examples/                         # Example implementations
```

### Key Directory Guidelines

1. **Scripts**: ALL scripts in `/scripts/`, NEVER in project root
2. **Tests**: ALL tests in `/tests/`, NEVER in project root  
3. **Python modules**: Always under `/src/claude_mpm/`
4. **Agent precedence**: PROJECT > USER > SYSTEM

## Service Layer

### Service Domains

The service layer is organized into 5 main domains:

#### 1. Core Services (`/src/claude_mpm/services/core/`)
**Purpose**: Foundation interfaces and base classes

**Key Components**:
- `interfaces.py`: Service contracts and interface definitions
- `base.py`: Base service classes with lifecycle management

**Key Interfaces**:
- `IServiceContainer`: Dependency injection container
- `IAgentRegistry`: Agent discovery and management
- `IHealthMonitor`: Service health monitoring
- `IConfigurationManager`: Configuration management

#### 2. Agent Services (`/src/claude_mpm/services/agents/`)
**Purpose**: Agent lifecycle, deployment, and capabilities

**Key Components**:
- `deployment.py`: Agent deployment and lifecycle
- `management.py`: Agent registry and service management
- `registry.py`: Agent discovery with 3-tier precedence

**Capabilities**:
- Three-tier precedence (PROJECT > USER > SYSTEM)
- Dynamic capability generation and schema validation
- Hot-reloading and configuration updates
- Agent versioning and semantic compatibility

#### 3. Communication Services (`/src/claude_mpm/services/communication/`)
**Purpose**: Real-time communication and WebSocket management

**Key Components**:
- `socketio.py`: SocketIO server and client management
- `websocket.py`: WebSocket connection handling

**Features**:
- Real-time agent activity monitoring
- File operation tracking and git diff viewer
- Session management and multi-client support
- Connection pooling and automatic reconnection

#### 4. Project Services (`/src/claude_mpm/services/project/`)
**Purpose**: Project analysis and workspace management

**Key Components**:
- `analyzer.py`: Technology stack and architecture detection
- `registry.py`: Project-specific configuration

**Capabilities**:
- Automatic technology stack detection
- Architecture pattern recognition
- Dynamic documentation discovery
- Project-specific memory generation

#### 5. Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)
**Purpose**: Cross-cutting concerns (logging, monitoring, error handling)

**Key Components**:
- `logging.py`: Structured logging with session correlation
- `monitoring.py`: Health monitoring and performance metrics

**Features**:
- Structured JSON logging with session correlation
- Performance monitoring and metrics collection
- Error handling and recovery mechanisms
- Circuit breaker patterns for resilience

### Service Implementation Pattern

```python
# 1. Define interface
class IMyService(ABC):
    @abstractmethod
    def my_operation(self, param: str) -> bool:
        pass

# 2. Implement service
class MyService(BaseService, IMyService):
    def __init__(self, dependency: IDependency):
        super().__init__("MyService")
        self.dependency = dependency
    
    async def initialize(self) -> bool:
        # Initialize service
        return True
    
    def my_operation(self, param: str) -> bool:
        # Implementation
        return True

# 3. Register in container
container.register(IMyService, MyService, singleton=True)

# 4. Use service
service = container.resolve(IMyService)
```

## Agent System

### Agent Hierarchy

Three-tier precedence system ensures proper customization:

1. **PROJECT Tier** (`.claude-mpm/agents/`)
   - Highest precedence
   - Project-specific agents and customizations
   - Supports `.md`, `.json`, `.yaml` formats
   - Can override USER and SYSTEM agents

2. **USER Tier** (`~/.claude-mpm/agents/` or `src/claude_mpm/agents/`)
   - User-level customizations across projects
   - Personal preferences and workflows
   - Can override SYSTEM agents

3. **SYSTEM Tier** (built-in framework agents)
   - Framework built-in agents
   - Lowest precedence (fallback)
   - Maintained by framework developers

### Agent Discovery Process

```python
from claude_mpm.services.agents import AgentRegistry

registry = AgentRegistry()

# Discover all agents with precedence
agents = await registry.discover_agents(force_refresh=True)

# Find specialized agents
qa_agents = await registry.get_specialized_agents("qa")

# Search by capability
test_agents = await registry.search_by_capability("testing")
```

### Agent Schema (v2.0.0)

All agents must conform to the standardized schema:

```json
{
  "id": "engineer",
  "version": "2.0.0",
  "metadata": {
    "name": "Engineer Agent",
    "description": "Full-stack development agent",
    "author": "Claude MPM",
    "tags": ["development", "coding", "engineering"]
  },
  "capabilities": {
    "resource_tier": "intensive",
    "max_concurrent_tasks": 3,
    "supported_languages": ["python", "javascript", "typescript"]
  },
  "instructions": "# Agent Instructions\n..."
}
```

## Communication Layer

### Real-Time Architecture

```
Client (Dashboard) <-- WebSocket --> SocketIO Server <-- Events --> Agent System
                                         │
                                         ├── Session Management  
                                         ├── Real-time Updates
                                         └── Connection Pooling
```

### Event Types

- **Agent Events**: start, stop, delegation, completion
- **File Events**: creation, modification, git operations
- **Session Events**: start, resume, pause, termination
- **System Events**: health status, performance metrics

### Usage Example

```python
from claude_mpm.services.communication import SocketIOServer

# Initialize SocketIO service
socketio_service = SocketIOServer()

# Start server
await socketio_service.start(host="localhost", port=8765)

# Emit events
await socketio_service.emit("deployment_status", {
    "status": "in_progress",
    "agent": "engineer", 
    "progress": 75
})
```

## Performance Features

### Lazy Loading

Services and components load only when needed:

```python
from claude_mpm.core.lazy import lazy_import

AgentManager = lazy_import('claude_mpm.services.agents.management', 'AgentManager')
```

### Multi-Level Caching

Intelligent caching with TTL and invalidation:

- **Memory Caches**: Fast in-memory caching for frequent data
- **File System Caches**: Persistent caching for expensive operations  
- **Cache Invalidation**: Smart invalidation based on file modifications

### Connection Pooling

Efficient resource management:

- **SocketIO Pool**: Reuse connections across sessions
- **Database Pool**: Connection pooling for metadata storage
- **Resource Management**: Automatic cleanup and limits

## Security Framework

### Input Validation

- **Schema Validation**: All inputs validated against JSON schemas
- **Type Checking**: Runtime type checking with error handling
- **Sanitization**: Input sanitization to prevent injection attacks

### Path Security

- **Path Traversal Prevention**: All file operations validate allowed paths
- **Sandboxing**: Agent operations sandboxed to project directories
- **Permission Checks**: File system operations require appropriate permissions

### Secure Operations

- **Credential Management**: Secure storage and handling of API credentials
- **Audit Logging**: All security-relevant operations logged
- **Error Handling**: Security errors handled without information disclosure

## Development Patterns

### Dependency Injection

```python
from claude_mpm.services.core import IServiceContainer

# Register services
container.register(IAgentRegistry, AgentRegistry, singleton=True)
container.register(IHealthMonitor, HealthMonitor, singleton=True)

# Resolve dependencies
agent_registry = container.resolve(IAgentRegistry)
```

### Service Lifecycle

Services follow a standard lifecycle:

1. **Registration**: Register interfaces with container
2. **Resolution**: Container resolves dependencies automatically
3. **Initialization**: Services initialize with dependencies
4. **Operation**: Service handles requests
5. **Shutdown**: Proper cleanup in shutdown methods

### Testing Strategy

- **Interface Compliance**: All services implement interfaces
- **Mock Implementation**: Easy mocking for isolated testing
- **Integration Testing**: Test service interactions
- **Performance Testing**: Verify caching and optimization

### Error Handling

- **Comprehensive Logging**: Structured logging at all levels
- **Graceful Degradation**: System continues operating during partial failures
- **Health Monitoring**: Services report health status
- **Recovery Mechanisms**: Automatic recovery where possible

---

## Related Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflows and patterns
- [AGENTS.md](AGENTS.md) - Agent development guide  
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment and operations
- [API.md](API.md) - API reference documentation