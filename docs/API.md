# Claude MPM API Reference

**Version**: 4.2.2  
**Last Updated**: September 2, 2025

Complete API reference for Claude MPM's service interfaces, agent management, and core functionality.

## Table of Contents

- [Core Service Interfaces](#core-service-interfaces)
- [Agent Management API](#agent-management-api)
- [Communication Services](#communication-services)
- [Project Services](#project-services)
- [Infrastructure Services](#infrastructure-services)
- [CLI API](#cli-api)
- [Usage Examples](#usage-examples)

## Core Service Interfaces

### IServiceContainer

Primary dependency injection interface for service management.

```python
from claude_mpm.services.core.interfaces import IServiceContainer

class IServiceContainer(ABC):
    @abstractmethod
    def register(self, service_type: type, implementation: type, singleton: bool = True) -> None:
        """Register a service implementation for an interface."""
        
    @abstractmethod  
    def resolve(self, service_type: type) -> Any:
        """Resolve a service by its interface type."""
        
    @abstractmethod
    def is_registered(self, service_type: type) -> bool:
        """Check if a service type is registered."""
        
    @abstractmethod
    def resolve_all(self, service_type: type) -> List[Any]:
        """Resolve all implementations of a service type."""
```

**Usage:**
```python
from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.agents import AgentRegistry, IAgentRegistry

container = ServiceContainer()
container.register(IAgentRegistry, AgentRegistry, singleton=True)
agent_registry = container.resolve(IAgentRegistry)
```

### IConfigurationManager

Configuration management interface for application settings.

```python
from claude_mpm.services.core.interfaces import IConfigurationManager

class IConfigurationManager(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        
    @abstractmethod  
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        
    @abstractmethod
    def load_from_file(self, file_path: str) -> None:
        """Load configuration from file."""
```

### IHealthMonitor

Service health monitoring interface.

```python
from claude_mpm.services.core.interfaces import IHealthMonitor

class IHealthMonitor(ABC):
    @abstractmethod
    async def check_health(self, service_name: str) -> HealthStatus:
        """Check health of specific service."""
        
    @abstractmethod
    async def get_system_health(self) -> HealthStatus:
        """Get overall system health status."""
        
    @abstractmethod
    def register_health_check(self, service_name: str, check_func: Callable) -> None:
        """Register custom health check function."""
```

**HealthStatus Data Structure:**
```python
@dataclass
class HealthStatus:
    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, Any]
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
```

## Agent Management API

### IAgentRegistry

Core agent discovery and management interface.

```python
from claude_mpm.services.core.interfaces import IAgentRegistry

class IAgentRegistry(ABC):
    @abstractmethod
    async def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Discover all available agents across tiers."""
        
    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[AgentData]:
        """Get specific agent by ID."""
        
    @abstractmethod
    async def get_specialized_agents(self, agent_type: str) -> List[AgentMetadata]:
        """Get agents of specific type."""
        
    @abstractmethod
    async def search_by_capability(self, capability: str) -> List[AgentMetadata]:
        """Search agents by capability."""
        
    @abstractmethod
    def get_agent_tier(self, agent_id: str) -> Optional[str]:
        """Get tier (PROJECT/USER/SYSTEM) of agent."""
```

**AgentMetadata Structure:**
```python
@dataclass
class AgentMetadata:
    id: str
    name: str
    description: str
    version: str
    tier: str  # "project", "user", "system"
    file_path: str
    capabilities: Dict[str, Any]
    metadata: Dict[str, Any]
```

### AgentDeploymentInterface

Agent deployment and lifecycle management.

```python
from claude_mpm.services.agents.deployment import AgentDeploymentInterface

class AgentDeploymentInterface(ABC):
    @abstractmethod
    def deploy_agents(self, force: bool = False, include_all: bool = False) -> Dict[str, Any]:
        """Deploy agents to target environment."""
        
    @abstractmethod
    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration."""
        
    @abstractmethod
    def clean_deployment(self, preserve_user_agents: bool = True) -> bool:
        """Clean up deployed agents."""
```

**Deployment Result Structure:**
```python
{
    "success": bool,
    "deployed_count": int,
    "failed_count": int,
    "deployed_agents": List[str],
    "failed_agents": List[Dict[str, str]],
    "warnings": List[str]
}
```

### Agent Loader API

High-level agent access functions.

```python
from claude_mpm.agents.agent_loader import (
    get_agent_prompt,
    list_available_agents,
    list_agents_by_tier,
    get_agent_tier
)

def get_agent_prompt(
    agent_name: str,
    task_description: Optional[str] = None,
    context_size: Optional[int] = None,
    return_model_info: bool = False,
    **kwargs
) -> Union[str, Tuple[str, str, Dict]]:
    """
    Get agent prompt with optional model selection.
    
    Args:
        agent_name: Name of the agent
        task_description: Optional task description for model selection
        context_size: Context size hint for model selection  
        return_model_info: Whether to return model and config info
        **kwargs: Additional arguments passed to agent
        
    Returns:
        Agent prompt string, or tuple with (prompt, model, config)
    """

def list_available_agents() -> Dict[str, Dict[str, Any]]:
    """Get metadata for all available agents."""

def list_agents_by_tier() -> Dict[str, List[str]]:
    """Get agents organized by tier."""

def get_agent_tier(agent_name: str) -> Optional[str]:
    """Get tier of specific agent."""
```

## Communication Services

### SocketIOServiceInterface

Real-time communication interface.

```python
from claude_mpm.services.communication.socketio import SocketIOServiceInterface

class SocketIOServiceInterface(ABC):
    @abstractmethod
    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the SocketIO server."""
        
    @abstractmethod
    async def stop(self) -> None:
        """Stop the SocketIO server."""
        
    @abstractmethod
    async def emit(self, event: str, data: Any, room: Optional[str] = None) -> None:
        """Emit event to clients."""
        
    @abstractmethod
    async def broadcast(self, event: str, data: Any) -> None:
        """Broadcast event to all clients."""
        
    @abstractmethod
    def register_handler(self, event: str, handler: Callable) -> None:
        """Register event handler."""
```

**Event Types:**
```python
# Agent events
{
    "type": "agent_start",
    "agent_id": "engineer",
    "timestamp": "2025-09-02T14:30:00Z",
    "data": {"task": "code review"}
}

# File events  
{
    "type": "file_modified",
    "file_path": "/src/module.py",
    "timestamp": "2025-09-02T14:30:00Z",
    "data": {"lines_changed": 15}
}

# System events
{
    "type": "system_health",
    "status": "healthy",
    "timestamp": "2025-09-02T14:30:00Z",
    "data": {"cpu": 25.5, "memory": 1024}
}
```

### WebSocket Client API

```python
from claude_mpm.services.communication.websocket import WebSocketClient

class WebSocketClient:
    def __init__(self, url: str):
        """Initialize WebSocket client."""
        
    async def connect(self) -> bool:
        """Connect to WebSocket server."""
        
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        
    async def send(self, data: Dict[str, Any]) -> None:
        """Send data to server."""
        
    def on_message(self, handler: Callable[[Dict], None]) -> None:
        """Register message handler."""
```

## Project Services

### ProjectAnalyzerInterface

Project analysis and technology detection.

```python
from claude_mpm.services.project.analyzer import ProjectAnalyzerInterface

class ProjectAnalyzerInterface(ABC):
    @abstractmethod
    def analyze_project(self, project_path: Optional[Path] = None) -> ProjectCharacteristics:
        """Analyze project structure and characteristics."""
        
    @abstractmethod
    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in project."""
        
    @abstractmethod
    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions."""
        
    @abstractmethod
    def get_project_metadata(self) -> Dict[str, Any]:
        """Get project metadata and configuration."""
```

**ProjectCharacteristics Structure:**
```python
@dataclass
class ProjectCharacteristics:
    project_type: str  # "python", "javascript", "mixed", etc.
    technologies: List[str]
    entry_points: List[str]
    structure_patterns: List[str]
    configuration_files: List[str]
    documentation_files: List[str]
    test_patterns: List[str]
    build_tools: List[str]
```

## Infrastructure Services

### IStructuredLogger

Structured logging interface with context management.

```python
from claude_mpm.services.infrastructure.logging import IStructuredLogger

class IStructuredLogger(ABC):
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data."""
        
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data."""
        
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data."""
        
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data."""
        
    @abstractmethod
    def set_context(self, **kwargs) -> None:
        """Set logging context for subsequent messages."""
```

### IPerformanceMonitor

Performance monitoring and metrics collection.

```python
from claude_mpm.services.infrastructure.monitoring import IPerformanceMonitor

class IPerformanceMonitor(ABC):
    @abstractmethod
    def start_timer(self, operation: str) -> str:
        """Start timing an operation."""
        
    @abstractmethod
    def stop_timer(self, timer_id: str) -> float:
        """Stop timer and return duration."""
        
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict] = None) -> None:
        """Record a metric value."""
        
    @abstractmethod
    def get_metrics(self, time_range: Optional[int] = None) -> Dict[str, Any]:
        """Get collected metrics."""
```

## CLI API

### Command Interface

Base interface for CLI commands.

```python
from claude_mpm.cli.base import BaseCommand

class BaseCommand:
    def __init__(self, name: str, description: str):
        """Initialize command with name and description."""
        
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to parser."""
        
    def execute(self, args: argparse.Namespace) -> int:
        """Execute command with parsed arguments. Return exit code."""
        
    def setup_logging(self, verbose: bool = False) -> None:
        """Setup logging for command execution."""
```

### Agent Commands API

```python
from claude_mpm.cli.commands.agents import AgentCommands

class AgentCommands:
    @staticmethod
    def list_agents(by_tier: bool = False, deployed: bool = False, system: bool = False) -> None:
        """List available agents with various filters."""
        
    @staticmethod
    def view_agent(agent_name: str) -> None:
        """Display detailed information about specific agent."""
        
    @staticmethod
    def fix_agents(agent_name: Optional[str] = None, dry_run: bool = False, 
                   all_agents: bool = False) -> None:
        """Fix frontmatter issues in agent files."""
        
    @staticmethod
    def deploy_agents(target: Optional[str] = None, force: bool = False) -> None:
        """Deploy agents to target directory."""
```

## Usage Examples

### Service Container Usage

```python
from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.agents import AgentRegistry, IAgentRegistry
from claude_mpm.services.infrastructure import LoggingService, IStructuredLogger

# Create container and register services
container = ServiceContainer()
container.register(IStructuredLogger, LoggingService, singleton=True)
container.register(IAgentRegistry, AgentRegistry, singleton=True)

# Resolve services
logger = container.resolve(IStructuredLogger)
agent_registry = container.resolve(IAgentRegistry)

# Use services
logger.info("Application started", component="main")
agents = await agent_registry.discover_agents()
```

### Agent Management Example

```python
from claude_mpm.agents.agent_loader import get_agent_prompt, list_agents_by_tier

# Get agent prompt with model selection
prompt, model, config = get_agent_prompt(
    "engineer",
    task_description="Complex refactoring task",
    context_size=50000,
    return_model_info=True
)

print(f"Using model: {model}")
print(f"Prompt length: {len(prompt)} characters")

# List agents by tier
agents_by_tier = list_agents_by_tier()
for tier, agents in agents_by_tier.items():
    print(f"{tier.upper()} tier: {', '.join(agents)}")
```

### Communication Service Example

```python
from claude_mpm.services.communication import SocketIOServer

# Initialize SocketIO service
socketio_service = SocketIOServer()

# Register event handlers
@socketio_service.on('client_message')
async def handle_message(sid, data):
    print(f"Received from {sid}: {data}")
    await socketio_service.emit('response', {'status': 'received'}, room=sid)

# Start server
await socketio_service.start(host="localhost", port=8765)

# Emit events
await socketio_service.broadcast('system_update', {
    'message': 'System updated successfully',
    'timestamp': datetime.now().isoformat()
})
```

### Project Analysis Example

```python
from claude_mpm.services.project import ProjectAnalyzer

# Analyze current project
analyzer = ProjectAnalyzer()
characteristics = analyzer.analyze_project()

print(f"Project type: {characteristics.project_type}")
print(f"Technologies: {', '.join(characteristics.technologies)}")
print(f"Entry points: {', '.join(characteristics.entry_points)}")

# Get code patterns
patterns = analyzer.analyze_code_patterns()
print(f"Code patterns: {patterns}")
```

### Performance Monitoring Example

```python
from claude_mpm.services.infrastructure import PerformanceMonitor

monitor = PerformanceMonitor()

# Time an operation
timer_id = monitor.start_timer("agent_deployment")
# ... perform deployment ...
duration = monitor.stop_timer(timer_id)

# Record metrics
monitor.record_metric("deployment_time", duration, {"agent": "engineer"})
monitor.record_metric("agents_deployed", 5)

# Get metrics
metrics = monitor.get_metrics(time_range=3600)  # Last hour
print(f"Average deployment time: {metrics['deployment_time']['avg']:.2f}s")
```

### Error Handling Patterns

```python
from claude_mpm.services.core.exceptions import ServiceError, AgentError

try:
    agent_registry = container.resolve(IAgentRegistry)
    agents = await agent_registry.discover_agents()
except ServiceError as e:
    logger.error("Service error occurred", error=str(e), service="agent_registry")
except AgentError as e:
    logger.error("Agent error occurred", error=str(e), agent=e.agent_id)
except Exception as e:
    logger.error("Unexpected error", error=str(e), type=type(e).__name__)
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Service architecture and design patterns
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflows and service creation
- [AGENTS.md](AGENTS.md) - Agent management and development
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures and operations