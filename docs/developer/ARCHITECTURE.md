# Claude MPM Architecture Overview

This document provides a comprehensive overview of the Claude MPM (Multi-Agent Project Manager) architecture, highlighting the service-oriented design, dependency injection system, and interface-based contracts introduced in v3.8.2.

**Last Updated**: 2025-08-22  
**Architecture Version**: 4.1.0  
**Recent Improvements**: Socket.IO stability, script organization, documentation consolidation

## Table of Contents

- [Overview](#overview)
- [Service Layer Architecture](#service-layer-architecture)
- [Project Structure](#project-structure)
- [Dependency Injection System](#dependency-injection-system)
- [Interface-Based Design](#interface-based-design)
- [Performance Features](#performance-features)
- [Security Framework](#security-framework)
- [Communication Layer](#communication-layer)
- [Event Emission Architecture](#event-emission-architecture)

## Overview

Claude MPM is built on a service-oriented architecture with clear separation of concerns, dependency injection, and interface-based contracts. The framework enables multi-agent workflows with extensible capabilities, real-time communication, and intelligent memory management.

### Core Principles

1. **Service-Oriented Architecture**: Business logic organized into specialized service domains
2. **Interface-Based Contracts**: All major components implement well-defined interfaces
3. **Dependency Injection**: Services are loosely coupled through dependency injection
4. **Lazy Loading**: Performance optimization through deferred resource initialization
5. **Extensibility**: Hook system and plugin architecture for customization
6. **Security First**: Comprehensive input validation and sanitization framework

### Architecture Benefits

- **50-80% Performance Improvement**: Through lazy loading and intelligent caching
- **Enhanced Security**: Defense-in-depth with input validation at all layers
- **Better Testability**: Interface-based design enables easy mocking and testing
- **Improved Maintainability**: Clear separation of concerns and service boundaries
- **Scalability**: Service-oriented design supports future growth and plugin architecture

## Service Layer Architecture

The service layer is organized into five main domains, each with clear responsibilities:

### 1. Core Services (`/src/claude_mpm/services/core/`)

**Purpose**: Foundation services providing base functionality and interfaces

**Key Components**:
- `interfaces.py`: Comprehensive interface definitions for all service contracts
- `base.py`: Base service classes (`BaseService`, `SyncBaseService`, `SingletonService`)

**Key Interfaces**:
- `IServiceContainer`: Dependency injection container
- `IAgentRegistry`: Agent discovery and management
- `IHealthMonitor`: Service health monitoring
- `IConfigurationManager`: Configuration management

### 2. Agent Services (`/src/claude_mpm/services/agents/`)

**Purpose**: Agent lifecycle management, deployment, and capabilities

**Key Components**:
- `deployment.py`: Agent deployment and lifecycle management
- `management.py`: Agent registry and service management
- `registry.py`: Agent discovery and hierarchical loading

**Capabilities**:
- Three-tier agent precedence (PROJECT > USER > SYSTEM)
- Dynamic agent capabilities and schema validation
- Agent versioning and semantic compatibility
- Hot-reloading and configuration updates

### 3. Communication Services (`/src/claude_mpm/services/communication/`)

**Purpose**: Real-time communication, WebSocket management, and event handling

**Key Components**:
- `socketio.py`: SocketIO server and client management
- `websocket.py`: WebSocket connection handling

**Features**:
- Real-time agent activity monitoring
- File operation tracking and git diff viewer
- Session management and state synchronization
- Multi-client support with connection pooling

### 4. Project Services (`/src/claude_mpm/services/project/`)

**Purpose**: Project analysis, workspace management, and context understanding

**Key Components**:
- `analyzer.py`: Project structure and technology stack analysis
- `registry.py`: Project-specific configuration and agent management

**Capabilities**:
- Automatic technology stack detection
- Architecture pattern recognition
- Dynamic documentation discovery
- Project-specific memory generation

### 5. Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)

**Purpose**: Cross-cutting concerns including logging, monitoring, and error handling

**Key Components**:
- `logging.py`: Structured logging and session management
- `monitoring.py`: Health monitoring and performance metrics

**Features**:
- Structured JSON logging with session correlation
- Performance monitoring and metrics collection
- Error handling and recovery mechanisms
- Circuit breaker patterns for resilience

## Project Structure

Claude MPM follows a standard Python project layout with clear separation of concerns:

```
claude-mpm/
├── .claude/                          # Claude-specific settings and hooks
├── .claude-mpm/                      # Project-specific Claude MPM directory
│   ├── agents/                       # PROJECT tier agent definitions (highest precedence)
│   ├── config/                       # Project configuration
│   ├── hooks/                        # Project-specific hooks
│   └── memories/                     # Agent memory files
│
├── src/claude_mpm/                   # Main package source
│   ├── core/                         # Core framework components
│   ├── services/                     # Service layer (5 domains)
│   ├── agents/                       # USER tier agents and instructions
│   ├── hooks/                        # Hook system implementation
│   ├── cli/                          # Command-line interface
│   └── utils/                        # Utilities and helpers
│
├── docs/                             # Documentation
│   ├── user/                         # User-facing documentation
│   ├── developer/                    # Developer documentation
│   ├── api/                          # API reference documentation
│   └── archive/                      # Historical documentation
│
├── tests/                            # Test suite
├── scripts/                          # Executable scripts and utilities
└── examples/                         # Example implementations
```

### Key Directory Guidelines

1. **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
2. **Tests**: ALL tests go in `/tests/`, NEVER in project root
3. **Python modules**: Always under `/src/claude_mpm/`
4. **Agent precedence**: PROJECT (`.claude-mpm/agents/`) > USER (`src/claude_mpm/agents/`) > SYSTEM (built-in)

## Dependency Injection System

The framework uses a sophisticated dependency injection container for loose coupling and testability:

### Service Container

```python
from claude_mpm.services.core.interfaces import IServiceContainer

# Register services
container.register(IAgentRegistry, AgentRegistryService, singleton=True)
container.register(IHealthMonitor, HealthMonitorService, singleton=True)

# Resolve dependencies
agent_registry = container.resolve(IAgentRegistry)
```

### Service Lifecycle

1. **Registration**: Services register their interfaces with the container
2. **Resolution**: Container resolves dependencies automatically
3. **Initialization**: Services initialize with their dependencies
4. **Lifecycle Management**: Container manages singleton lifecycles

### Best Practices

- Define clear interfaces for all services
- Use constructor injection for dependencies
- Prefer singleton registration for stateless services
- Implement proper cleanup in service destructors

## Interface-Based Design

All major framework components implement explicit interfaces for better testing and maintainability:

### Core Interface Pattern

```python
from abc import ABC, abstractmethod

class IAgentManager(ABC):
    @abstractmethod
    async def deploy_agent(self, agent_config: dict) -> bool:
        """Deploy an agent with the given configuration."""
        pass
    
    @abstractmethod
    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent."""
        pass

class AgentManager(BaseService, IAgentManager):
    async def deploy_agent(self, agent_config: dict) -> bool:
        # Implementation
        pass
    
    def get_agent_status(self, agent_id: str) -> AgentStatus:
        # Implementation
        pass
```

### Interface Compliance

- All services implement their corresponding interfaces
- Interface compliance is verified through automated testing
- Mock implementations are available for testing

## Performance Features

### Lazy Loading

Services and components are loaded only when needed:

```python
# Lazy import pattern
from claude_mpm.core.lazy import lazy_import

AgentManager = lazy_import('claude_mpm.services.agents.management', 'AgentManager')
```

### Multi-Level Caching

Intelligent caching with TTL and invalidation:

- **Memory Caches**: Fast in-memory caching for frequently accessed data
- **File System Caches**: Persistent caching for expensive operations
- **Cache Invalidation**: Smart invalidation based on file modifications and events

### Connection Pooling

WebSocket and database connections are pooled for efficiency:

- **SocketIO Pool**: Reuse connections across sessions
- **Database Pool**: Connection pooling for metadata storage
- **Resource Management**: Automatic cleanup and resource limits

## Security Framework

Comprehensive security measures implemented throughout the architecture:

### Input Validation

- **Schema Validation**: All inputs validated against JSON schemas
- **Type Checking**: Runtime type checking with proper error handling
- **Sanitization**: Input sanitization to prevent injection attacks

### Path Security

- **Path Traversal Prevention**: All file operations validate against allowed paths
- **Sandboxing**: Agent operations sandboxed to project directories
- **Permission Checks**: File system operations require appropriate permissions

### Secure Operations

- **Credential Management**: Secure storage and handling of API credentials
- **Audit Logging**: All security-relevant operations are logged
- **Error Handling**: Security errors handled without information disclosure

## Communication Layer

Real-time communication system built on WebSocket and SocketIO:

### WebSocket Architecture

```
Client (Dashboard) <-- WebSocket --> SocketIO Server <-- Events --> Agent System
                                         │
                                         ├── Session Management
                                         ├── Real-time Updates
                                         └── Connection Pooling
```

### Event Types

- **Agent Events**: Agent start, stop, delegation, completion
- **File Events**: File creation, modification, git operations
- **Session Events**: Session start, resume, pause, termination
- **System Events**: Health status, performance metrics

### Features

- **Real-time Monitoring**: Live dashboard showing agent activity
- **Session Persistence**: Sessions survive WebSocket disconnections
- **Multi-client Support**: Multiple dashboard connections per session
- **Event Filtering**: Configurable event filtering and routing

## Migration and Compatibility

### Backward Compatibility

The new architecture maintains backward compatibility through:

- **Lazy Imports**: Existing import paths continue to work
- **Legacy Service Wrappers**: Old service interfaces wrapped with new implementations
- **Configuration Migration**: Automatic migration of configuration files

### Migration Path

1. **Gradual Migration**: Services can be migrated incrementally
2. **Interface Adoption**: Existing services can adopt new interfaces progressively
3. **Testing Strategy**: Comprehensive test suite ensures compatibility

For detailed migration instructions, see [docs/MIGRATION.md](MIGRATION.md).

## Related Documentation

### User Documentation
- [Quick Start Guide](../QUICKSTART.md) - Get running in 5 minutes
- [Memory System](MEMORY.md) - Agent memory documentation
- [User Guide](user/) - Detailed usage documentation

### Developer Documentation
- [Service Layer Guide](developer/SERVICES.md) - Detailed service implementation guide
- [API Reference](api/) - Complete API documentation
- [Testing Guide](TESTING.md) - Testing strategies and patterns
- [Performance Guide](PERFORMANCE.md) - Optimization and performance monitoring
- [Security Guide](SECURITY.md) - Security framework and best practices

### Technical Documentation
- [Deployment Guide](DEPLOY.md) - Publishing and versioning
- [Migration Guide](MIGRATION.md) - Upgrading from previous versions

## Event Emission Architecture

**Version**: 4.0.25+
**Status**: Stable
**Documentation**: [EVENT_EMISSION_ARCHITECTURE.md](EVENT_EMISSION_ARCHITECTURE.md)

### Overview

Claude MPM implements a **single-path event emission architecture** for hook events to eliminate duplicate events and improve performance. This architecture replaced the previous EventBus-based multi-path system.

### Architecture Pattern

```
Hook Handler → ConnectionManager → Direct Socket.IO → Dashboard
                                ↓ (fallback only)
                              HTTP POST → Monitor Server → Dashboard
```

### Key Principles

1. **Single Emission Path**: Events flow through ONE primary path with ONE fallback
2. **No EventBus**: EventBus removed to prevent duplicate emissions
3. **Direct Socket.IO**: Ultra-low latency direct async calls
4. **HTTP Fallback**: Reliable cross-process communication when direct fails
5. **Event Normalization**: Consistent event schema across all paths

### Performance Characteristics

- **Direct Path**: ~0.1ms latency, 10,000+ events/second
- **Fallback Path**: ~2-5ms latency, 1,000+ events/second
- **Memory Usage**: Minimal (no event buffering)
- **Duplicate Rate**: 0% (eliminated by single-path design)

### Implementation

The `ConnectionManagerService` implements this architecture:

```python
def emit_event(self, namespace: str, event: str, data: dict):
    # PRIMARY: Direct Socket.IO
    if self.connection_pool:
        try:
            self.connection_pool.emit("claude_event", event_data)
            return  # Success - no fallback needed
        except Exception:
            pass  # Fall through to HTTP fallback

    # FALLBACK: HTTP POST
    self._try_http_fallback(event_data)
```

### Stability Guidelines

- **NEVER** add EventBus emission paths
- **NEVER** add parallel emission paths
- **ALWAYS** use single primary + single fallback pattern
- **ALWAYS** reference EVENT_EMISSION_ARCHITECTURE.md for changes

---

**Note**: The former STRUCTURE.md content has been consolidated into this document. SERVICES.md provides detailed implementation guidance for developers.