# Architecture Overview

High-level architecture guide for Claude MPM. For detailed technical documentation, see [developer/ARCHITECTURE.md](developer/ARCHITECTURE.md).

## System Design

Claude MPM is built on a service-oriented architecture with:

- **Service-Oriented Design**: Five specialized service domains
- **Interface-Based Contracts**: Well-defined component interfaces
- **Dependency Injection**: Loose coupling through DI container
- **Lazy Loading**: Deferred resource initialization for performance
- **Hook System**: Event-driven extensibility
- **MCP Integration**: Model Context Protocol support

## Architecture Benefits

- **50-80% Performance Improvement**: Lazy loading and intelligent caching
- **Enhanced Security**: Defense-in-depth with input validation
- **Better Testability**: Interface-based design enables easy mocking
- **Improved Maintainability**: Clear separation of concerns
- **Scalability**: Supports future growth and extensions

## Five Service Domains

### 1. Core Services
Foundation services and interfaces for the entire system.

**Key Components:**
- Service container (dependency injection)
- Base service classes
- Interface definitions

**Location**: `/src/claude_mpm/services/core/`

### 2. Agent Services
Agent lifecycle, discovery, and management.

**Key Components:**
- Agent registry and discovery
- Three-tier agent precedence (PROJECT > USER > SYSTEM)
- Agent deployment and lifecycle
- Capabilities and schema validation

**Location**: `/src/claude_mpm/services/agents/`

### 3. Communication Services
Real-time communication and event streaming.

**Key Components:**
- SocketIO server management
- WebSocket connections
- Event broadcasting
- Multi-client connection pooling

**Location**: `/src/claude_mpm/services/communication/`

### 4. Project Services
Project analysis and workspace management.

**Key Components:**
- Stack detection and analysis
- Project configuration
- Workspace management

**Location**: `/src/claude_mpm/services/project/`

### 5. Utility Services
Supporting functionality across the system.

**Key Components:**
- Logging and diagnostics
- File operations
- System utilities

**Location**: `/src/claude_mpm/services/utility/`

## Three-Tier Agent System

Agents are loaded with precedence (highest to lowest):

1. **PROJECT** (`.claude-mpm/agents/`) - Project-specific agents
2. **USER** (`~/.claude-agents/`) - User customizations
3. **SYSTEM** (bundled) - Default agents

This allows project-specific customization while maintaining defaults.

## Hook System

Event-driven extension points:

- **pre_tool_use**: Before tool execution
- **post_tool_use**: After tool execution
- **session_start**: Session initialization
- **session_end**: Session cleanup

See [developer/pretool-use-hooks.md](developer/pretool-use-hooks.md) for details.

## Memory System

Persistent, project-specific knowledge:

- Simple list format for learnings
- JSON response fields for updates
- Cross-session persistence
- Agent-specific memory isolation

See [developer/memory-integration.md](developer/memory-integration.md) for implementation.

## MCP Gateway

Model Context Protocol integration:

- External tool integration
- Custom tool development
- Protocol-based communication
- Extensible architecture

See [developer/13-mcp-gateway/README.md](developer/13-mcp-gateway/README.md) for details.

## Performance Optimizations

**v4.8.2+ Improvements:**
- 91% latency reduction in hook system
- Git branch caching with 5-minute TTL
- Non-blocking HTTP fallback
- 50-80% overall performance improvement

**Lazy Loading:**
- Services instantiated on-demand
- Deferred resource initialization
- Reduced startup time

**Caching:**
- Git branch caching (5-minute TTL)
- Agent discovery caching
- Configuration caching

## Security Framework

**Defense-in-Depth:**
- Input validation at all layers
- Filesystem restrictions
- Path traversal prevention
- Command injection protection

**Validation Layers:**
1. CLI argument validation
2. Service input validation
3. Agent parameter validation
4. Tool execution validation

## Communication Layer

**Real-Time Monitoring:**
- WebSocket-based event streaming
- Live agent activity tracking
- File operation monitoring
- Session state synchronization

**Event Types:**
- Agent activity events
- File operation events
- Session update events
- Health status events

## Data Flow

```
User Request
     ↓
CLI Interface
     ↓
Service Container (DI)
     ↓
Agent Registry → Agent Selection
     ↓
Hook System (pre_tool_use)
     ↓
Tool Execution
     ↓
Hook System (post_tool_use)
     ↓
Communication Layer (events)
     ↓
Response to User
```

## Component Diagram

```
┌─────────────────────────────────────┐
│          CLI Interface              │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│      Service Container (DI)         │
├─────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐ │
│  │ Core Services│  │Agent Services│ │
│  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐ │
│  │Comm Services │  │Proj Services │ │
│  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐                   │
│  │Util Services │                   │
│  └──────────────┘                   │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         Hook System                 │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         MCP Gateway                 │
└─────────────────────────────────────┘
```

## Configuration

Configuration follows a hierarchy:

1. **System defaults**: Built-in configuration
2. **User config**: `~/.claude-mpm/configuration.yaml`
3. **Project config**: `.claude-mpm/configuration.yaml`
4. **CLI arguments**: Runtime overrides

See [configuration.md](configuration.md) for options.

## See Also

- **[Developer Architecture](developer/ARCHITECTURE.md)** - Detailed technical architecture
- **[Service Reference](developer/api-reference.md)** - API documentation
- **[Agent System](AGENTS.md)** - Multi-agent orchestration
- **[Extending](developer/extending.md)** - Building extensions
- **[User Guide](user/user-guide.md)** - End-user features

---

**For detailed architecture documentation**: See [developer/ARCHITECTURE.md](developer/ARCHITECTURE.md)
