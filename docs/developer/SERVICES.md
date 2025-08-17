# Service Layer Guide

This guide provides comprehensive documentation for the Claude MPM service layer, including service domains, interfaces, implementations, usage examples, and lifecycle management.

**Last Updated**: 2025-08-16
**Architecture Version**: 3.8.3
**Related Documents**: [ARCHITECTURE.md](../ARCHITECTURE.md), [TESTING.md](../TESTING.md)

> **Note**: As of v3.8.3, the service layer has been fully consolidated to eliminate duplicate modules and enforce strict domain-driven organization. All legacy duplicate files have been removed.

## Table of Contents

- [Overview](#overview)
- [Service Domains](#service-domains)
- [Service Interfaces](#service-interfaces)
- [Service Implementations](#service-implementations)
- [Usage Examples](#usage-examples)
- [Service Lifecycle](#service-lifecycle)
- [Dependency Injection](#dependency-injection)
- [Best Practices](#best-practices)

## Overview

The Claude MPM service layer is organized into five main domains, each responsible for specific aspects of the framework:

1. **Core Services**: Foundation interfaces and base classes
2. **Agent Services**: Agent lifecycle, deployment, and management
3. **Communication Services**: Real-time communication and WebSocket management
4. **Project Services**: Project analysis and workspace management
5. **Infrastructure Services**: Logging, monitoring, and cross-cutting concerns

## Service Domains

### 1. Core Services (`/src/claude_mpm/services/core/`)

**Purpose**: Provides foundation services and contracts for the entire framework.

#### Key Components

- **`interfaces.py`**: Comprehensive interface definitions for all service contracts
- **`base.py`**: Base service classes providing common functionality

#### Core Interfaces

```python
# Service container for dependency injection
class IServiceContainer(ABC):
    def register(self, service_type: type, implementation: type, singleton: bool = True) -> None
    def resolve(self, service_type: type) -> Any
    def is_registered(self, service_type: type) -> bool

# Configuration management
class IConfigurationManager(ABC):
    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any) -> None
    def get_section(self, section: str) -> Dict[str, Any]

# Health monitoring
class IHealthMonitor(ABC):
    async def check_health(self, service_name: str) -> HealthStatus
    async def get_system_health(self) -> HealthStatus
    def register_health_check(self, service_name: str, check_func: callable) -> None
```

#### Base Service Classes

```python
# Asynchronous base service
class BaseService(ABC):
    async def initialize(self) -> bool
    async def shutdown(self) -> None
    def get_config(self, key: str, default: Any = None) -> Any

# Synchronous base service
class SyncBaseService(ABC):
    def initialize(self) -> bool
    def shutdown(self) -> None

# Singleton service pattern
class SingletonService(SyncBaseService):
    @classmethod
    def get_instance(cls) -> 'SingletonService'
```

### 2. Agent Services (`/src/claude_mpm/services/agent/`)

**Purpose**: Manages agent lifecycle, deployment, and operations.

#### Service Structure

```
agent/
├── deployment.py     # Agent deployment operations
├── management.py     # Agent lifecycle management  
└── registry.py       # Agent discovery and registration
```

#### Agent Deployment Service

```python
class AgentDeploymentService(AgentDeploymentInterface):
    """Handles complete agent deployment lifecycle"""
    
    def deploy_agents(self, force: bool = False, include_all: bool = False) -> Dict[str, Any]:
        """Deploy agents to target environment"""
        
    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration and structure"""
        
    def clean_deployment(self, preserve_user_agents: bool = True) -> bool:
        """Clean up deployed agents"""
```

**Key Features**:
- Idempotent deployment (safe to run multiple times)
- Version checking prevents unnecessary rebuilds
- Supports force rebuild for troubleshooting
- Maintains backward compatibility
- User-created agent preservation during cleanup

#### Agent Management Service

```python
class AgentManagementService(BaseService):
    """Comprehensive agent lifecycle management"""
    
    async def create_agent(self, agent_config: Dict[str, Any]) -> str:
        """Create new agent from configuration"""
        
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing agent configuration"""
        
    async def delete_agent(self, agent_id: str) -> bool:
        """Remove agent and cleanup resources"""
```

#### Agent Registry Service

```python
class AgentRegistry(IAgentRegistry):
    """Agent discovery and metadata management"""
    
    async def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Discover all available agents"""
        
    async def get_specialized_agents(self, agent_type: str) -> List[AgentMetadata]:
        """Get agents of specific specialized type"""
        
    async def search_by_capability(self, capability: str) -> List[AgentMetadata]:
        """Search agents by capability"""
```

### 3. Communication Services (`/src/claude_mpm/services/communication/`)

**Purpose**: Provides real-time communication and WebSocket management.

#### Service Structure

```
communication/
├── socketio.py       # SocketIO server implementation
└── websocket.py      # WebSocket client management
```

#### SocketIO Service

```python
class SocketIOService(SocketIOServiceInterface):
    """Real-time WebSocket communication service"""
    
    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the WebSocket server"""
        
    async def emit(self, event: str, data: Any, room: Optional[str] = None) -> None:
        """Emit event to connected clients"""
        
    async def broadcast(self, event: str, data: Any) -> None:
        """Broadcast event to all clients"""
```

**Key Features**:
- Real-time dashboard updates
- Bidirectional client-server communication
- Event-driven architecture
- Connection management with automatic reconnection

### 4. Project Services (`/src/claude_mpm/services/project/`)

**Purpose**: Project analysis and workspace management.

#### Service Structure

```
project/
├── analyzer.py       # Project structure and technology detection
└── registry.py       # Project registration and metadata
```

#### Project Analyzer Service

```python
class ProjectAnalyzer(ProjectAnalyzerInterface):
    """Comprehensive project analysis service"""
    
    def analyze_project(self, project_path: Optional[Path] = None) -> ProjectCharacteristics:
        """Analyze project characteristics and structure"""
        
    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in project"""
        
    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions"""
```

**Analysis Capabilities**:
- Technology stack detection (Python, JavaScript, Java, etc.)
- Code pattern analysis and conventions
- Project structure mapping
- Entry point identification
- Dependency analysis

### 5. Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)

**Purpose**: Cross-cutting concerns like logging, monitoring, and error handling.

#### Service Structure

```
infrastructure/
├── logging.py        # Structured logging service
└── monitoring.py     # Health monitoring and metrics
```

#### Logging Service

```python
class LoggingService(IStructuredLogger):
    """Structured logging with context management"""
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""
        
    def set_context(self, **kwargs) -> None:
        """Set logging context for subsequent messages"""
```

#### Health Monitoring Service

```python
class HealthMonitor(IHealthMonitor):
    """Service health monitoring and metrics collection"""
    
    async def check_health(self, service_name: str) -> HealthStatus:
        """Check health of specific service"""
        
    async def get_system_health(self) -> HealthStatus:
        """Get overall system health status"""
```

## Service Interfaces

### Interface Design Principles

1. **Single Responsibility**: Each interface has focused purpose
2. **Dependency Inversion**: High-level modules depend on abstractions  
3. **Interface Segregation**: Clients depend only on methods they use
4. **Liskov Substitution**: Implementations are interchangeable

### Core Interface Categories

#### 1. Service Infrastructure Interfaces

```python
# Foundation interfaces
IServiceContainer       # Dependency injection container
IConfigurationManager   # Configuration management
IHealthMonitor         # Service health monitoring
IServiceLifecycle      # Service lifecycle management
```

#### 2. Agent Management Interfaces

```python
# Agent-specific interfaces  
IAgentRegistry           # Agent discovery and management
AgentDeploymentInterface # Agent deployment operations
MemoryServiceInterface   # Agent memory management
```

#### 3. Communication Interfaces

```python
# Communication interfaces
SocketIOServiceInterface # WebSocket communication
IEventBus               # Event-driven communication
```

#### 4. Performance Interfaces

```python
# Performance-focused interfaces
IPromptCache            # High-performance prompt caching
ICacheService           # General caching operations
IPerformanceMonitor     # Performance metrics collection
```

## Service Implementations

### Implementation Patterns

#### 1. Base Service Implementation

```python
class ExampleService(BaseService):
    """Example service implementation"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ExampleService", config)
        self._resource = None
    
    async def initialize(self) -> bool:
        """Initialize service resources"""
        try:
            self.log_info("Initializing service")
            self._resource = await self._setup_resource()
            self._initialized = True
            return True
        except Exception as e:
            self.log_error(f"Initialization failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Cleanup service resources"""
        if self._resource:
            await self._resource.close()
        self._shutdown = True
        self.log_info("Service shutdown complete")
```

#### 2. Singleton Service Implementation

```python
class CacheService(SingletonService, ICacheService):
    """Singleton cache service implementation"""
    
    def __init__(self):
        super().__init__("CacheService")
        self._cache = {}
        self._metrics = {'hits': 0, 'misses': 0}
    
    def get(self, key: str) -> Any:
        """Get value from cache with metrics tracking"""
        if key in self._cache:
            self._metrics['hits'] += 1
            return self._cache[key]
        else:
            self._metrics['misses'] += 1
            return None
```

#### 3. Interface-Based Implementation

```python
class SocketIOServer(SocketIOServiceInterface):
    """SocketIO service implementing communication interface"""
    
    def __init__(self, app=None):
        self.sio = socketio.AsyncServer(cors_allowed_origins="*")
        self.app = app or web.Application()
        self.sio.attach(self.app)
        self._running = False
    
    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start SocketIO server"""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host, port)
        await site.start()
        self._running = True
```

## Usage Examples

### 1. Service Registration and Resolution

```python
from claude_mpm.services.core import IServiceContainer
from claude_mpm.services.agent import AgentDeploymentService

# Register service with container
container = ServiceContainer()
container.register(
    AgentDeploymentInterface, 
    AgentDeploymentService, 
    singleton=True
)

# Resolve service from container
deployment_service = container.resolve(AgentDeploymentInterface)
```

### 2. Agent Deployment

```python
from claude_mpm.services.agent import AgentDeploymentService

# Initialize deployment service
deployment_service = AgentDeploymentService()

# Deploy agents with options
result = deployment_service.deploy_agents(
    force=False,           # Don't force rebuild existing agents
    include_all=False      # Respect exclusion configuration
)

# Check deployment results
if result['success']:
    print(f"Deployed {result['deployed_count']} agents")
else:
    print(f"Deployment failed: {result['error']}")
```

### 3. Agent Discovery and Management

```python
from claude_mpm.services.agent import AgentRegistry

# Initialize agent registry
registry = AgentRegistry()

# Discover all agents
agents = await registry.discover_agents(force_refresh=True)

# Find specialized agents
qa_agents = await registry.get_specialized_agents("qa")

# Search by capability
test_agents = await registry.search_by_capability("testing")
```

### 4. Real-Time Communication

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

# Broadcast to all clients
await socketio_service.broadcast("system_update", {
    "message": "Agent deployment completed",
    "timestamp": datetime.now().isoformat()
})
```

### 5. Project Analysis

```python
from claude_mpm.services.project import ProjectAnalyzer

# Initialize project analyzer
analyzer = ProjectAnalyzer()

# Analyze current project
characteristics = analyzer.analyze_project()

print(f"Project type: {characteristics.project_type}")
print(f"Technologies: {characteristics.technologies}")
print(f"Entry points: {characteristics.entry_points}")

# Detect technology stack
technologies = analyzer.detect_technology_stack()
print(f"Detected technologies: {technologies}")
```

### 6. Memory Management

```python
from claude_mpm.services.agents.memory import AgentMemoryManager

# Initialize memory manager
memory_manager = AgentMemoryManager()

# Load agent memory
memory_content = memory_manager.load_memory("engineer")

# Save updated memory
success = memory_manager.save_memory("engineer", updated_content)

# Optimize memory for better performance
optimized = memory_manager.optimize_memory("engineer")
```

## Service Lifecycle

### Service States

1. **Uninitialized**: Service created but not initialized
2. **Initializing**: Service initialization in progress
3. **Running**: Service fully operational
4. **Shutting Down**: Service cleanup in progress
5. **Shutdown**: Service stopped and resources cleaned up

### Lifecycle Management

```python
class ServiceManager:
    """Manages service lifecycle across the framework"""
    
    def __init__(self):
        self._services = {}
        self._initialization_order = []
    
    async def initialize_services(self) -> bool:
        """Initialize all registered services in dependency order"""
        for service_name in self._initialization_order:
            service = self._services[service_name]
            if not await service.initialize():
                self.log_error(f"Failed to initialize {service_name}")
                return False
        return True
    
    async def shutdown_services(self) -> None:
        """Shutdown all services in reverse order"""
        for service_name in reversed(self._initialization_order):
            service = self._services[service_name]
            await service.shutdown()
```

### Service Health Monitoring

```python
from claude_mpm.services.infrastructure import HealthMonitor

# Register health checks
health_monitor = HealthMonitor()
health_monitor.register_health_check("agent_registry", check_agent_registry_health)
health_monitor.register_health_check("memory_service", check_memory_service_health)

# Check system health
system_health = await health_monitor.get_system_health()
print(f"System status: {system_health.status}")
print(f"Health checks: {system_health.checks}")
```

## Dependency Injection

### Container Registration

```python
from claude_mpm.services.core import ServiceContainer

# Create service container
container = ServiceContainer()

# Register services
container.register(IAgentRegistry, AgentRegistry, singleton=True)
container.register(IHealthMonitor, HealthMonitor, singleton=True)
container.register(SocketIOServiceInterface, SocketIOServer, singleton=False)

# Register instances
cache_service = CacheService.get_instance()
container.register_instance(ICacheService, cache_service)
```

### Service Resolution

```python
# Resolve single service
agent_registry = container.resolve(IAgentRegistry)

# Resolve all implementations
cache_services = container.resolve_all(ICacheService)

# Check registration
is_registered = container.is_registered(IHealthMonitor)
```

### Dependency Injection Patterns

#### 1. Constructor Injection

```python
class AgentDeploymentService:
    def __init__(self, registry: IAgentRegistry, cache: ICacheService):
        self._registry = registry
        self._cache = cache
```

#### 2. Method Injection

```python
class ServiceOrchestrator:
    def set_dependencies(self, container: IServiceContainer):
        self._registry = container.resolve(IAgentRegistry)
        self._cache = container.resolve(ICacheService)
```

#### 3. Property Injection

```python
class ConfigurableService:
    @property
    def config_manager(self) -> IConfigurationManager:
        return self._container.resolve(IConfigurationManager)
```

## Best Practices

### 1. Service Design

- **Single Responsibility**: Each service has one clear purpose
- **Interface Contracts**: All public services implement interfaces
- **Error Handling**: Comprehensive error handling with logging
- **Resource Management**: Proper cleanup in shutdown methods

### 2. Performance Optimization

- **Lazy Initialization**: Initialize resources only when needed
- **Connection Pooling**: Reuse connections and expensive resources
- **Caching Strategy**: Cache expensive operations appropriately
- **Async Operations**: Use async/await for I/O-bound operations

### 3. Testing Strategies

- **Mock Interfaces**: Use interfaces for easy mocking in tests
- **Dependency Injection**: Inject test doubles for isolated testing
- **Service Isolation**: Test services independently
- **Integration Testing**: Test service interactions

### 4. Monitoring and Observability

- **Structured Logging**: Use consistent logging patterns
- **Health Checks**: Implement health checks for all services
- **Metrics Collection**: Track performance and usage metrics
- **Error Tracking**: Log and monitor service errors

### 5. Configuration Management

- **Environment-Specific Config**: Support different environments
- **Configuration Validation**: Validate configuration on startup
- **Runtime Configuration**: Support configuration updates
- **Secure Secrets**: Handle sensitive configuration securely

## Service Organization Policy

**Effective**: v3.8.3 (2025-08-16)

To prevent future duplication and maintain clean architecture, the following policies are enforced:

### Domain-Driven Structure

All services MUST be organized into their appropriate domain directories:

```
src/claude_mpm/services/
├── core/                  # Foundation interfaces and base classes
├── agents/               # Agent lifecycle, deployment, management
├── communication/        # Real-time communication, WebSocket
├── project/             # Project analysis, workspace management
├── infrastructure/      # Logging, monitoring, cross-cutting concerns
├── memory/              # Memory management and caching
├── mcp_gateway/         # MCP protocol gateway services
├── socketio/            # SocketIO event handlers
└── version_control/     # Git operations and versioning
```

### Strict Anti-Duplication Rules

1. **Single Source of Truth**: Each service implementation MUST exist in exactly one location
2. **No Root-Level Services**: New services MUST NOT be placed directly in `/services/` root
3. **Domain Alignment**: Services MUST be placed in the domain that best matches their primary responsibility
4. **Import Consolidation**: All imports MUST use the canonical domain-specific paths

### Backward Compatibility

- The `/services/__init__.py` provides backward compatibility through lazy imports
- Legacy import paths are supported but deprecated
- New code MUST use domain-specific import paths

### Enforcement

- **Code Reviews**: All PRs adding services must follow domain structure
- **Automated Checks**: CI validates no duplicate modules exist
- **Documentation**: This policy must be updated when domains change

### Migration Process

When refactoring existing services:

1. **Identify Domain**: Determine the correct domain for the service
2. **Move Implementation**: Move to appropriate domain directory
3. **Update Imports**: Update all direct imports to use new path
4. **Update __init__.py**: Update lazy import to point to new location
5. **Remove Duplicates**: Delete old implementation after verification
6. **Test**: Ensure all imports work and tests pass

This service layer guide provides the foundation for understanding and working with Claude MPM's service architecture. Each service is designed to be maintainable, testable, and performant while providing clear contracts through well-defined interfaces.