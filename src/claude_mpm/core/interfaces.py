"""
Core Service Interfaces for Claude PM Framework
==============================================

DEPRECATED: This file has been moved to services/core/interfaces.py

This file is maintained for backward compatibility only.
All new code should import from claude_mpm.services.core.interfaces

Part of TSK-0046: Service Layer Architecture Reorganization

Original description:
This module defines the core service interfaces that establish contracts for
dependency injection, service discovery, and framework orchestration.

Phase 1 Refactoring: Interface extraction and dependency injection foundation
- IServiceContainer: Dependency injection container
- IAgentRegistry: Agent discovery and management
- IPromptCache: Performance-critical caching
- IHealthMonitor: Service health monitoring
- IConfigurationManager: Configuration management
- ITemplateManager: Template processing and rendering
- IServiceFactory: Service creation patterns

These interfaces reduce cyclomatic complexity and establish clean separation of concerns.
"""

# Keep original imports to prevent any parsing issues
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

# Re-export everything from the new location for backward compatibility
from claude_mpm.services.core.interfaces import *

# Type variables for generic interfaces
T = TypeVar("T")
ServiceType = TypeVar("ServiceType")


# Core dependency injection interfaces
class IServiceContainer(ABC):
    """Service container interface for dependency injection"""

    @abstractmethod
    def register(
        self, service_type: type, implementation: type, singleton: bool = True
    ) -> None:
        """Register a service implementation"""

    @abstractmethod
    def register_instance(self, service_type: type, instance: Any) -> None:
        """Register a service instance"""

    @abstractmethod
    def resolve(self, service_type: type) -> Any:
        """Resolve a service by type"""

    @abstractmethod
    def resolve_all(self, service_type: type) -> List[Any]:
        """Resolve all implementations of a service type"""

    @abstractmethod
    def is_registered(self, service_type: type) -> bool:
        """Check if a service type is registered"""


# Configuration management interfaces
class IConfigurationService(ABC):
    """Interface for configuration service (legacy compatibility)"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize configuration service"""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown configuration service"""


class IConfigurationManager(ABC):
    """Interface for configuration management and validation"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""

    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""

    @abstractmethod
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate configuration against schema"""

    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from sources"""

    @abstractmethod
    def watch_changes(self, callback: callable) -> None:
        """Watch for configuration changes"""


# Cache service interface
class ICacheService(ABC):
    """Interface for cache service operations"""

    @abstractmethod
    def get(self, key: str) -> Any:
        """Get value from cache"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache"""

    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching pattern"""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""

    @abstractmethod
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""


# Health monitoring interface
@dataclass
class HealthStatus:
    """Health status data structure"""

    status: str  # healthy, degraded, unhealthy, unknown
    message: str
    timestamp: datetime
    checks: Dict[str, bool]
    metrics: Dict[str, Any]


class IHealthMonitor(ABC):
    """Interface for service health monitoring"""

    @abstractmethod
    async def check_health(self, service_name: str) -> HealthStatus:
        """Check health of a specific service"""

    @abstractmethod
    async def get_system_health(self) -> HealthStatus:
        """Get overall system health"""

    @abstractmethod
    def register_health_check(self, service_name: str, check_func: callable) -> None:
        """Register a health check function"""

    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start health monitoring"""

    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""


# Agent registry interface
@dataclass
class AgentMetadata:
    """Enhanced agent metadata with specialization and model configuration support"""

    name: str
    type: str
    path: str
    tier: str
    description: Optional[str] = None
    version: Optional[str] = None
    capabilities: List[str] = None
    specializations: List[str] = None
    frameworks: List[str] = None
    domains: List[str] = None
    roles: List[str] = None
    is_hybrid: bool = False
    validation_score: float = 0.0
    last_modified: Optional[float] = None
    # Model configuration fields
    preferred_model: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values for list fields"""
        if self.capabilities is None:
            self.capabilities = []
        if self.specializations is None:
            self.specializations = []
        if self.frameworks is None:
            self.frameworks = []
        if self.domains is None:
            self.domains = []
        if self.roles is None:
            self.roles = []
        if self.model_config is None:
            self.model_config = {}


class IAgentRegistry(ABC):
    """Interface for agent discovery and management"""

    @abstractmethod
    async def discover_agents(
        self, force_refresh: bool = False
    ) -> Dict[str, AgentMetadata]:
        """Discover all available agents"""

    @abstractmethod
    async def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get specific agent metadata"""

    @abstractmethod
    async def list_agents(
        self, agent_type: Optional[str] = None, tier: Optional[str] = None
    ) -> List[AgentMetadata]:
        """List agents with optional filtering"""

    @abstractmethod
    async def get_specialized_agents(self, agent_type: str) -> List[AgentMetadata]:
        """Get agents of a specific specialized type"""

    @abstractmethod
    async def search_by_capability(self, capability: str) -> List[AgentMetadata]:
        """Search agents by capability"""

    @abstractmethod
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""


# Prompt cache interface
@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0.0
    size_bytes: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IPromptCache(ABC):
    """Interface for high-performance prompt caching"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key"""

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Set cached value with optional TTL"""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value"""

    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate cached values matching pattern"""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values"""

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""


# Template management interface
@dataclass
class TemplateRenderContext:
    """Context for template rendering"""

    variables: Dict[str, Any]
    metadata: Dict[str, Any]
    target_path: Optional[Path] = None
    template_id: Optional[str] = None


class ITemplateManager(ABC):
    """Interface for template processing and rendering"""

    @abstractmethod
    async def render_template(
        self, template_content: str, context: TemplateRenderContext
    ) -> str:
        """Render template with given context"""

    @abstractmethod
    async def load_template(self, template_id: str) -> Optional[str]:
        """Load template by ID"""

    @abstractmethod
    async def validate_template(self, template_content: str) -> Tuple[bool, List[str]]:
        """Validate template syntax and variables"""

    @abstractmethod
    def register_template_function(self, name: str, func: callable) -> None:
        """Register custom template function"""


# Service factory interface
class IServiceFactory(Generic[ServiceType], ABC):
    """Generic interface for service factories"""

    @abstractmethod
    def create(self, **kwargs) -> ServiceType:
        """Create service instance"""

    @abstractmethod
    def create_with_config(self, config: Dict[str, Any]) -> ServiceType:
        """Create service instance with configuration"""

    @abstractmethod
    def supports_type(self, service_type: type) -> bool:
        """Check if factory supports service type"""


# Logging interface
class IStructuredLogger(ABC):
    """Interface for structured logging"""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data"""

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data"""

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data"""

    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with structured data"""

    @abstractmethod
    def set_context(self, **kwargs) -> None:
        """Set logging context for all subsequent messages"""


# Service lifecycle interface
class IServiceLifecycle(ABC):
    """Interface for service lifecycle management"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service"""

    @abstractmethod
    async def start(self) -> None:
        """Start the service"""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service"""

    @abstractmethod
    async def restart(self) -> None:
        """Restart the service"""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if service is running"""


# Error handling interface
class IErrorHandler(ABC):
    """Interface for centralized error handling"""

    @abstractmethod
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle error with context"""

    @abstractmethod
    def register_error_handler(self, error_type: type, handler: callable) -> None:
        """Register error handler for specific error type"""

    @abstractmethod
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""


# Performance monitoring interface
class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""

    @abstractmethod
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""

    @abstractmethod
    def stop_timer(self, timer_id: str) -> float:
        """Stop timing and return duration"""

    @abstractmethod
    def record_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a performance metric"""

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""


# Event system interface
class IEventBus(ABC):
    """Interface for event-driven communication"""

    @abstractmethod
    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event"""

    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> str:
        """Subscribe to events"""

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events"""

    @abstractmethod
    async def publish_async(self, event_type: str, data: Any) -> None:
        """Publish an event asynchronously"""


# Agent deployment interface
class AgentDeploymentInterface(ABC):
    """Interface for agent deployment operations.

    WHY: Agent deployment needs to be decoupled from concrete implementations
    to enable different deployment strategies (local, remote, containerized).
    This interface ensures consistency across different deployment backends.

    DESIGN DECISION: Methods return deployment status/results to enable
    proper error handling and rollback operations when deployments fail.
    """

    @abstractmethod
    def deploy_agents(
        self, force: bool = False, include_all: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents to target environment.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """

    @abstractmethod
    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration and structure.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    @abstractmethod
    def clean_deployment(self, preserve_user_agents: bool = True) -> bool:
        """Clean up deployed agents.

        Args:
            preserve_user_agents: Whether to keep user-created agents

        Returns:
            True if cleanup successful
        """

    @abstractmethod
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics.

        Returns:
            Dictionary with deployment status information
        """


# Memory service interface
class MemoryServiceInterface(ABC):
    """Interface for memory management operations.

    WHY: Memory management is crucial for agent learning and context retention.
    This interface abstracts memory storage, retrieval, and optimization to
    enable different backends (file-based, database, distributed cache).

    DESIGN DECISION: Memory operations return success/failure status to enable
    proper error handling and fallback strategies when memory is unavailable.
    """

    @abstractmethod
    def load_memory(self, agent_id: str) -> Optional[str]:
        """Load memory for a specific agent.

        Args:
            agent_id: Identifier of the agent

        Returns:
            Memory content as string or None if not found
        """

    @abstractmethod
    def save_memory(self, agent_id: str, content: str) -> bool:
        """Save memory for a specific agent.

        Args:
            agent_id: Identifier of the agent
            content: Memory content to save

        Returns:
            True if save successful
        """

    @abstractmethod
    def validate_memory_size(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate memory content size and structure.

        Args:
            content: Memory content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """

    @abstractmethod
    def optimize_memory(self, agent_id: str) -> bool:
        """Optimize memory by removing duplicates and consolidating entries.

        Args:
            agent_id: Identifier of the agent

        Returns:
            True if optimization successful
        """

    @abstractmethod
    def get_memory_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory usage metrics.

        Args:
            agent_id: Optional specific agent ID, or None for all

        Returns:
            Dictionary with memory metrics
        """


# Hook service interface
class HookServiceInterface(ABC):
    """Interface for hook execution operations.

    WHY: Hooks provide extensibility points for the framework, allowing plugins
    and extensions to modify behavior. This interface ensures consistent hook
    registration, priority handling, and execution across different hook systems.

    DESIGN DECISION: Separate pre/post delegation methods for clarity and
    performance - no runtime type checking needed during execution.
    """

    @abstractmethod
    def register_hook(self, hook: Any) -> bool:
        """Register a hook with the service.

        Args:
            hook: Hook instance to register

        Returns:
            True if registration successful
        """

    @abstractmethod
    def execute_pre_delegation_hooks(self, context: Any) -> Any:
        """Execute all pre-delegation hooks.

        Args:
            context: Hook execution context

        Returns:
            Hook execution result
        """

    @abstractmethod
    def execute_post_delegation_hooks(self, context: Any) -> Any:
        """Execute all post-delegation hooks.

        Args:
            context: Hook execution context

        Returns:
            Hook execution result
        """

    @abstractmethod
    def get_registered_hooks(self) -> Dict[str, List[Any]]:
        """Get all registered hooks by type.

        Returns:
            Dictionary mapping hook types to lists of hooks
        """

    @abstractmethod
    def clear_hooks(self, hook_type: Optional[str] = None) -> None:
        """Clear registered hooks.

        Args:
            hook_type: Optional specific hook type to clear, or None for all
        """


# WebSocket/SocketIO service interface
class SocketIOServiceInterface(ABC):
    """Interface for WebSocket communication.

    WHY: Real-time communication is essential for monitoring and interactive
    features. This interface abstracts WebSocket/SocketIO implementation to
    enable different transport mechanisms and fallback strategies.

    DESIGN DECISION: Async methods for non-blocking I/O operations, with
    support for both broadcast and targeted messaging.
    """

    @abstractmethod
    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the WebSocket server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the WebSocket server."""

    @abstractmethod
    async def emit(self, event: str, data: Any, room: Optional[str] = None) -> None:
        """Emit an event to connected clients.

        Args:
            event: Event name
            data: Event data
            room: Optional room to target
        """

    @abstractmethod
    async def broadcast(self, event: str, data: Any) -> None:
        """Broadcast event to all connected clients.

        Args:
            event: Event name
            data: Event data
        """

    @abstractmethod
    def get_connection_count(self) -> int:
        """Get number of connected clients.

        Returns:
            Number of active connections
        """

    @abstractmethod
    def is_running(self) -> bool:
        """Check if server is running.

        Returns:
            True if server is active
        """


# Project analyzer interface
class ProjectAnalyzerInterface(ABC):
    """Interface for project analysis operations.

    WHY: Understanding project structure and characteristics is essential for
    context-aware agent behavior. This interface abstracts project analysis
    to support different project types and structures.

    DESIGN DECISION: Returns structured data classes for type safety and
    clear contracts between analysis and consumption components.
    """

    @abstractmethod
    def analyze_project(self, project_path: Optional[Path] = None) -> Any:
        """Analyze project characteristics.

        Args:
            project_path: Optional path to project, defaults to current

        Returns:
            ProjectCharacteristics or similar structured data
        """

    @abstractmethod
    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in the project.

        Returns:
            List of detected technologies
        """

    @abstractmethod
    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions.

        Returns:
            Dictionary of pattern analysis results
        """

    @abstractmethod
    def get_project_structure(self) -> Dict[str, Any]:
        """Get project directory structure analysis.

        Returns:
            Dictionary representing project structure
        """

    @abstractmethod
    def identify_entry_points(self) -> List[Path]:
        """Identify project entry points.

        Returns:
            List of entry point paths
        """


# Ticket manager interface
class TicketManagerInterface(ABC):
    """Interface for ticket management operations.

    WHY: Ticket management provides work tracking and organization. This
    interface abstracts ticket operations to support different backend
    systems (file-based, API-based, database).

    DESIGN DECISION: Uses string IDs for flexibility across different
    ticketing systems, with structured data returns for consistency.
    """

    @abstractmethod
    def create_task(self, title: str, description: str, **kwargs) -> Optional[str]:
        """Create a new task ticket.

        Args:
            title: Task title
            description: Task description
            **kwargs: Additional task properties

        Returns:
            Task ID if created successfully, None otherwise
        """

    @abstractmethod
    def update_task(self, task_id: str, **updates) -> bool:
        """Update an existing task.

        Args:
            task_id: ID of task to update
            **updates: Fields to update

        Returns:
            True if update successful
        """

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details.

        Args:
            task_id: ID of task to retrieve

        Returns:
            Task data dictionary or None if not found
        """

    @abstractmethod
    def list_tasks(
        self, status: Optional[str] = None, **filters
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering.

        Args:
            status: Optional status filter
            **filters: Additional filter criteria

        Returns:
            List of task dictionaries
        """

    @abstractmethod
    def close_task(self, task_id: str, resolution: Optional[str] = None) -> bool:
        """Close a task.

        Args:
            task_id: ID of task to close
            resolution: Optional resolution description

        Returns:
            True if close successful
        """


# Interface registry for dependency injection discovery
class InterfaceRegistry:
    """Registry of all core interfaces for dependency injection"""

    _interfaces = {
        "service_container": IServiceContainer,
        "configuration_manager": IConfigurationManager,
        "health_monitor": IHealthMonitor,
        "agent_registry": IAgentRegistry,
        "prompt_cache": IPromptCache,
        "template_manager": ITemplateManager,
        "structured_logger": IStructuredLogger,
        "service_lifecycle": IServiceLifecycle,
        "error_handler": IErrorHandler,
        "performance_monitor": IPerformanceMonitor,
        "event_bus": IEventBus,
        "agent_deployment": AgentDeploymentInterface,
        "memory_service": MemoryServiceInterface,
        "hook_service": HookServiceInterface,
        "socketio_service": SocketIOServiceInterface,
        "project_analyzer": ProjectAnalyzerInterface,
        "ticket_manager": TicketManagerInterface,
    }

    @classmethod
    def get_interface(cls, name: str) -> Optional[type]:
        """Get interface by name"""
        return cls._interfaces.get(name)

    @classmethod
    def get_all_interfaces(cls) -> Dict[str, type]:
        """Get all registered interfaces"""
        return cls._interfaces.copy()

    @classmethod
    def register_interface(cls, name: str, interface: type) -> None:
        """Register a new interface"""
        cls._interfaces[name] = interface
