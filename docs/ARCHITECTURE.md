# Claude MPM Architecture Overview

This document provides a comprehensive overview of the Claude MPM (Multi-Agent Project Manager) architecture, highlighting the refactored service layer, dependency injection system, and interface-based design introduced in TSK-0053.

**Last Updated**: 2025-08-14  
**Architecture Version**: 3.7.8  
**Refactoring Reference**: TSK-0053

## Table of Contents

- [Overview](#overview)
- [Service Layer Architecture](#service-layer-architecture)
- [Dependency Injection System](#dependency-injection-system)
- [Interface-Based Design](#interface-based-design)
- [Component Relationships](#component-relationships)
- [Lazy Loading and Performance](#lazy-loading-and-performance)
- [Security and Validation](#security-and-validation)
- [Memory Management](#memory-management)
- [Communication Layer](#communication-layer)
- [Architecture Diagrams](#architecture-diagrams)

## Overview

Claude MPM is built on a service-oriented architecture with clear separation of concerns, dependency injection, and interface-based contracts. The framework enables multi-agent workflows with extensible capabilities, real-time communication, and intelligent memory management.

### Core Principles

1. **Service-Oriented Architecture**: Business logic organized into specialized service domains
2. **Interface-Based Contracts**: All major components implement well-defined interfaces
3. **Dependency Injection**: Services are loosely coupled through dependency injection
4. **Lazy Loading**: Performance optimization through deferred resource initialization
5. **Extensibility**: Hook system and plugin architecture for customization

## Service Layer Architecture

The service layer is organized into five main domains, each with clear responsibilities:

### 1. Core Services (`/src/claude_mpm/services/core/`)

**Purpose**: Foundation services providing base functionality and interfaces

**Components**:
- `interfaces.py`: Comprehensive interface definitions for all service contracts
- `base.py`: Base service classes (`BaseService`, `SyncBaseService`, `SingletonService`)

**Key Interfaces**:
- `IServiceContainer`: Dependency injection container
- `IAgentRegistry`: Agent discovery and management
- `IHealthMonitor`: Service health monitoring
- `IConfigurationManager`: Configuration management
- `IPromptCache`: High-performance caching
- `ITemplateManager`: Template processing

### 2. Agent Services (`/src/claude_mpm/services/agent/`)

**Purpose**: Agent lifecycle, management, and deployment operations

**Components**:
- `deployment.py`: Agent deployment operations (`AgentDeploymentService`)
- `management.py`: Agent lifecycle management (`AgentManagementService`)
- `registry.py`: Agent discovery and registration (`AgentRegistry`)

**Legacy Structure** (maintained for compatibility):
- `/src/claude_mpm/services/agents/`: Original nested structure with backward compatibility

### 3. Communication Services (`/src/claude_mpm/services/communication/`)

**Purpose**: Real-time communication and WebSocket management

**Components**:
- `socketio.py`: SocketIO server implementation
- `websocket.py`: WebSocket client management

**Features**:
- Real-time monitoring and dashboard updates
- Bidirectional communication with Claude Desktop
- Event-driven architecture for system updates

### 4. Project Services (`/src/claude_mpm/services/project/`)

**Purpose**: Project analysis and workspace management

**Components**:
- `analyzer.py`: Project structure and technology detection
- `registry.py`: Project registration and metadata management

**Capabilities**:
- Technology stack detection
- Code pattern analysis
- Project structure mapping
- Entry point identification

### 5. Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)

**Purpose**: Cross-cutting concerns like logging, monitoring, and error handling

**Components**:
- `logging.py`: Structured logging service
- `monitoring.py`: Health monitoring and metrics collection

## Dependency Injection System

The dependency injection system provides loose coupling and testability through the `IServiceContainer` interface.

### Service Container Features

```python
class IServiceContainer(ABC):
    def register(self, service_type: type, implementation: type, singleton: bool = True) -> None
    def register_instance(self, service_type: type, instance: Any) -> None
    def resolve(self, service_type: type) -> Any
    def resolve_all(self, service_type: type) -> List[Any]
    def is_registered(self, service_type: type) -> bool
```

### Service Registration Patterns

1. **Type Registration**: Register implementation for interface
2. **Instance Registration**: Register pre-configured instances
3. **Singleton Support**: Ensure single instance per type
4. **Multi-Implementation**: Support multiple implementations per interface

### Lifecycle Management

All services inherit from base classes that provide:
- Initialization and shutdown hooks
- Configuration management
- Structured logging
- Health status tracking

## Interface-Based Design

### Core Interface Categories

1. **Service Infrastructure**: `IServiceContainer`, `IConfigurationManager`, `IHealthMonitor`
2. **Agent Management**: `IAgentRegistry`, `AgentDeploymentInterface`, `MemoryServiceInterface`
3. **Communication**: `SocketIOServiceInterface`, `IEventBus`
4. **Performance**: `IPromptCache`, `ICacheService`, `IPerformanceMonitor`
5. **Project Management**: `ProjectAnalyzerInterface`, `TicketManagerInterface`
6. **Extensibility**: `HookServiceInterface`, `ITemplateManager`

### Interface Design Principles

- **Single Responsibility**: Each interface has a focused purpose
- **Dependency Inversion**: High-level modules depend on abstractions
- **Interface Segregation**: Clients depend only on methods they use
- **Liskov Substitution**: Implementations are interchangeable

### Example Interface Implementation

```python
class AgentDeploymentService(AgentDeploymentInterface):
    def deploy_agents(self, force: bool = False, include_all: bool = False) -> Dict[str, Any]:
        # Implementation details
        pass
    
    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        # Validation logic
        pass
```

## Component Relationships

### Service Dependencies

```
┌─────────────────┐     ┌─────────────────┐
│   Core Services │────▶│ Agent Services  │
└─────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│Infrastructure   │◀────│ Communication   │
│   Services      │     │   Services      │
└─────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Project Services│     │ Memory Services │
└─────────────────┘     └─────────────────┘
```

### Data Flow Architecture

1. **Request Flow**: CLI → Core Services → Specialized Services
2. **Event Flow**: Services → Event Bus → Subscribers
3. **Memory Flow**: Agent Services → Memory Services → Cache Layer
4. **Communication Flow**: SocketIO → Event Handlers → Service Layer

## Lazy Loading and Performance

### Lazy Import System

The service layer uses lazy imports to prevent circular dependencies and improve startup performance:

```python
def __getattr__(name):
    """Lazy import to prevent circular dependencies."""
    if name == "AgentDeploymentService":
        from .agent.deployment import AgentDeploymentService
        return AgentDeploymentService
    # ... other lazy imports
```

### Performance Optimizations

1. **Deferred Initialization**: Services initialize only when needed
2. **Connection Pooling**: Shared connections for database and external services
3. **Intelligent Caching**: Multi-level caching with TTL and invalidation
4. **Resource Management**: Automatic cleanup and resource pooling

### Caching Strategy

- **L1 Cache**: In-memory cache for frequently accessed data
- **L2 Cache**: Persistent cache for expensive computations
- **Cache Invalidation**: Event-driven invalidation on data changes
- **Cache Warming**: Preload critical data on startup

## Security and Validation

### Input Validation Framework

- **Schema Validation**: JSON Schema validation for structured data
- **Path Traversal Prevention**: Secure file path handling
- **Input Sanitization**: Automatic sanitization of user inputs
- **Type Safety**: Strong typing throughout the service layer

### Security Utilities

```python
from claude_mpm.utils.security import (
    validate_input,
    sanitize_path,
    check_permissions
)
```

## Memory Management

### Agent Memory System

- **Persistent Storage**: Agent learning and context retention
- **Memory Optimization**: Automatic deduplication and compression
- **Memory Routing**: Intelligent routing based on context
- **Memory Building**: Dynamic memory construction from interactions

### Memory Service Interface

```python
class MemoryServiceInterface(ABC):
    def load_memory(self, agent_id: str) -> Optional[str]
    def save_memory(self, agent_id: str, content: str) -> bool
    def validate_memory_size(self, content: str) -> Tuple[bool, Optional[str]]
    def optimize_memory(self, agent_id: str) -> bool
```

## Communication Layer

### Real-Time Communication

- **SocketIO Server**: WebSocket communication for dashboards
- **Event-Driven Updates**: Real-time status and progress updates
- **Bidirectional Communication**: Client-server message exchange
- **Connection Management**: Automatic reconnection and failover

### Dashboard Integration

- **File Operations**: Real-time file viewing and editing
- **Project Status**: Live project analysis and updates
- **Agent Status**: Real-time agent deployment and health monitoring
- **Memory Insights**: Memory usage and optimization metrics

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude MPM Framework                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │     CLI     │  │  Dashboard  │  │   Agents    │         │
│  │   Layer     │  │   WebApp    │  │   System    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                 │                 │              │
├─────────┼─────────────────┼─────────────────┼──────────────┤
│         ▼                 ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Service Layer                            │ │
│  │                                                         │ │
│  │ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ │ │
│  │ │   Core    │ │   Agent   │ │  Project  │ │Infrastructure│ │
│  │ │ Services  │ │ Services  │ │ Services  │ │ Services  │ │ │
│  │ └───────────┘ └───────────┘ └───────────┘ └───────────┘ │ │
│  │                                                         │ │
│  │ ┌─────────────────────────────────────────────────────┐ │ │
│  │ │              Communication Services                 │ │ │
│  │ └─────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     Data Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Memory    │  │    Cache    │  │   Config    │         │
│  │   Storage   │  │   Layer     │  │   Storage   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependency Graph

```
IServiceContainer
      │
      ├─▶ IConfigurationManager
      │         │
      │         ▼
      ├─▶ IAgentRegistry ─────▶ AgentDeploymentInterface
      │         │                       │
      │         ▼                       ▼
      ├─▶ IPromptCache ◀────────── MemoryServiceInterface
      │         │                       │
      │         ▼                       ▼
      ├─▶ IHealthMonitor ◀─────── HookServiceInterface
      │         │                       │
      │         ▼                       ▼
      └─▶ ITemplateManager ─────▶ SocketIOServiceInterface
```

### Agent Service Architecture

```
Agent Management Layer
├── AgentRegistry
│   ├── DeployedAgentDiscovery
│   ├── AgentModificationTracker
│   └── AgentCapabilitiesGenerator
├── AgentDeploymentService
│   ├── AgentLifecycleManager
│   ├── AgentVersionManager
│   └── AsyncAgentDeployment
└── AgentMemoryManager
    ├── AgentPersistenceService
    ├── MemoryBuilder
    ├── MemoryRouter
    └── MemoryOptimizer
```

## Key Benefits of the Refactored Architecture

### 1. Improved Maintainability
- Clear separation of concerns
- Well-defined interfaces and contracts
- Reduced coupling between components

### 2. Enhanced Testability
- Dependency injection enables easy mocking
- Interface-based testing reduces integration complexity
- Isolated service testing with clear boundaries

### 3. Better Performance
- Lazy loading reduces startup time
- Intelligent caching improves response times
- Connection pooling optimizes resource usage

### 4. Increased Extensibility
- Plugin architecture through interfaces
- Hook system for customization
- Service container for dynamic registration

### 5. Stronger Type Safety
- Interface contracts ensure consistent APIs
- Strong typing throughout the service layer
- Compile-time error detection

## Migration Impact

The refactoring provides backward compatibility while introducing modern architectural patterns:

- **Lazy imports** maintain existing import paths
- **Interface implementations** replace concrete dependencies
- **Service container** enables dependency injection
- **Performance optimizations** improve user experience

This architecture positions Claude MPM for future growth while maintaining stability and performance.