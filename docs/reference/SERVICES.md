# Services Reference

Complete reference for Claude MPM's service-oriented architecture. For detailed technical documentation, see [../developer/ARCHITECTURE.md](../developer/ARCHITECTURE.md).

## Service Domains

Claude MPM uses five specialized service domains:

### 1. Core Services (`/src/claude_mpm/services/core/`)

**Purpose**: Foundation services and interfaces

**Key Interfaces:**
- `IServiceContainer` - Dependency injection container
- `IAgentRegistry` - Agent discovery and loading
- `IHealthMonitor` - Service health monitoring
- `IConfigurationManager` - Configuration management

**Components:**
- `interfaces.py` - Service contract definitions
- `base.py` - Base service classes
- `container.py` - DI container implementation

### 2. Agent Services (`/src/claude_mpm/services/agents/`)

**Purpose**: Agent lifecycle and management

**Components:**
- `deployment.py` - Agent deployment and lifecycle
- `management.py` - Agent registry and services
- `registry.py` - Agent discovery and loading

**Capabilities:**
- Three-tier agent precedence (PROJECT > USER > SYSTEM)
- Dynamic capabilities and schema validation
- Agent versioning and compatibility
- Hot-reloading and updates

### 3. Communication Services (`/src/claude_mpm/services/communication/`)

**Purpose**: Real-time communication and events

**Components:**
- `socketio.py` - SocketIO server management
- `websocket.py` - WebSocket connections

**Features:**
- Real-time agent activity monitoring
- File operation tracking
- Session state synchronization
- Multi-client connection pooling

### 4. Project Services (`/src/claude_mpm/services/project/`)

**Purpose**: Project analysis and workspace management

**Components:**
- `analyzer.py` - Stack and structure analysis
- `registry.py` - Project configuration

**Capabilities:**
- Automatic stack detection (Python, Node.js, Rust, etc.)
- Framework identification (FastAPI, Next.js, React)
- Project structure analysis
- Configuration management

### 5. Utility Services (`/src/claude_mpm/services/utility/`)

**Purpose**: Supporting functionality

**Components:**
- `logging.py` - Logging utilities
- `filesystem.py` - File operations
- `validation.py` - Input validation

**Features:**
- Structured logging
- Safe file operations
- Input sanitization

## Service Interfaces

### IServiceContainer

```python
class IServiceContainer:
    """Dependency injection container."""

    def get(self, interface: Type[T]) -> T:
        """Get service instance by interface."""

    def register(self, interface: Type, implementation: Type):
        """Register service implementation."""

    def singleton(self, interface: Type, instance: Any):
        """Register singleton instance."""
```

### IAgentRegistry

```python
class IAgentRegistry:
    """Agent discovery and management."""

    def discover_agents(self) -> List[Agent]:
        """Discover all available agents."""

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name."""

    def load_agent(self, path: Path) -> Agent:
        """Load agent from file."""
```

### IHealthMonitor

```python
class IHealthMonitor:
    """Service health monitoring."""

    def check_health(self) -> HealthStatus:
        """Check overall system health."""

    def register_service(self, name: str, checker: Callable):
        """Register health check for service."""
```

### IConfigurationManager

```python
class IConfigurationManager:
    """Configuration management."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""

    def set(self, key: str, value: Any):
        """Set configuration value."""

    def save(self):
        """Save configuration to disk."""
```

## Service Communication

Services communicate through:

1. **Direct Injection**: Constructor injection via DI container
2. **Event System**: Asynchronous event broadcasting
3. **Hook System**: Pre/post execution hooks
4. **REST API**: HTTP endpoints for monitoring

## Service Lifecycle

1. **Registration**: Services registered in DI container
2. **Initialization**: Lazy initialization on first use
3. **Execution**: Service methods invoked
4. **Health Checks**: Periodic health monitoring
5. **Cleanup**: Graceful shutdown on exit

## See Also

- **[Architecture](../developer/ARCHITECTURE.md)** - Detailed architecture
- **[API Reference](../developer/api-reference.md)** - Complete API documentation
- **[Extending](../developer/extending.md)** - Building custom services

---

**For detailed service documentation**: See [../developer/ARCHITECTURE.md](../developer/ARCHITECTURE.md)
