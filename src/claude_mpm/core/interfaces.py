"""
Core Service Interfaces for Claude PM Framework
==============================================

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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import asyncio

# Type variables for generic interfaces
T = TypeVar('T')
ServiceType = TypeVar('ServiceType')


# Core dependency injection interfaces
class IServiceContainer(ABC):
    """Service container interface for dependency injection"""
    
    @abstractmethod
    def register(self, service_type: type, implementation: type, singleton: bool = True) -> None:
        """Register a service implementation"""
        pass
    
    @abstractmethod
    def register_instance(self, service_type: type, instance: Any) -> None:
        """Register a service instance"""
        pass
    
    @abstractmethod
    def resolve(self, service_type: type) -> Any:
        """Resolve a service by type"""
        pass
    
    @abstractmethod
    def resolve_all(self, service_type: type) -> List[Any]:
        """Resolve all implementations of a service type"""
        pass
    
    @abstractmethod
    def is_registered(self, service_type: type) -> bool:
        """Check if a service type is registered"""
        pass


# Configuration management interfaces
class IConfigurationService(ABC):
    """Interface for configuration service (legacy compatibility)"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize configuration service"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown configuration service"""
        pass

class IConfigurationManager(ABC):
    """Interface for configuration management and validation"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        pass
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        pass
    
    @abstractmethod
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate configuration against schema"""
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from sources"""
        pass
    
    @abstractmethod
    def watch_changes(self, callback: callable) -> None:
        """Watch for configuration changes"""
        pass


# Cache service interface
class ICacheService(ABC):
    """Interface for cache service operations"""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        """Get value from cache"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching pattern"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        pass


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
        pass
    
    @abstractmethod
    async def get_system_health(self) -> HealthStatus:
        """Get overall system health"""
        pass
    
    @abstractmethod
    def register_health_check(self, service_name: str, check_func: callable) -> None:
        """Register a health check function"""
        pass
    
    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start health monitoring"""
        pass
    
    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        pass


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
    async def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Discover all available agents"""
        pass
    
    @abstractmethod
    async def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get specific agent metadata"""
        pass
    
    @abstractmethod
    async def list_agents(self, agent_type: Optional[str] = None, tier: Optional[str] = None) -> List[AgentMetadata]:
        """List agents with optional filtering"""
        pass
    
    @abstractmethod
    async def get_specialized_agents(self, agent_type: str) -> List[AgentMetadata]:
        """Get agents of a specific specialized type"""
        pass
    
    @abstractmethod
    async def search_by_capability(self, capability: str) -> List[AgentMetadata]:
        """Search agents by capability"""
        pass
    
    @abstractmethod
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        pass


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
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set cached value with optional TTL"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value"""
        pass
    
    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate cached values matching pattern"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        pass


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
    async def render_template(self, template_content: str, context: TemplateRenderContext) -> str:
        """Render template with given context"""
        pass
    
    @abstractmethod
    async def load_template(self, template_id: str) -> Optional[str]:
        """Load template by ID"""
        pass
    
    @abstractmethod
    async def validate_template(self, template_content: str) -> Tuple[bool, List[str]]:
        """Validate template syntax and variables"""
        pass
    
    @abstractmethod
    def register_template_function(self, name: str, func: callable) -> None:
        """Register custom template function"""
        pass


# Service factory interface
class IServiceFactory(Generic[ServiceType], ABC):
    """Generic interface for service factories"""
    
    @abstractmethod
    def create(self, **kwargs) -> ServiceType:
        """Create service instance"""
        pass
    
    @abstractmethod
    def create_with_config(self, config: Dict[str, Any]) -> ServiceType:
        """Create service instance with configuration"""
        pass
    
    @abstractmethod
    def supports_type(self, service_type: type) -> bool:
        """Check if factory supports service type"""
        pass


# Logging interface
class IStructuredLogger(ABC):
    """Interface for structured logging"""
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data"""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data"""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data"""
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with structured data"""
        pass
    
    @abstractmethod
    def set_context(self, **kwargs) -> None:
        """Set logging context for all subsequent messages"""
        pass


# Service lifecycle interface
class IServiceLifecycle(ABC):
    """Interface for service lifecycle management"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the service"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the service"""
        pass
    
    @abstractmethod
    async def restart(self) -> None:
        """Restart the service"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if service is running"""
        pass


# Error handling interface
class IErrorHandler(ABC):
    """Interface for centralized error handling"""
    
    @abstractmethod
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle error with context"""
        pass
    
    @abstractmethod
    def register_error_handler(self, error_type: type, handler: callable) -> None:
        """Register error handler for specific error type"""
        pass
    
    @abstractmethod
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        pass


# Performance monitoring interface
class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""
    
    @abstractmethod
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        pass
    
    @abstractmethod
    def stop_timer(self, timer_id: str) -> float:
        """Stop timing and return duration"""
        pass
    
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a performance metric"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        pass


# Event system interface
class IEventBus(ABC):
    """Interface for event-driven communication"""
    
    @abstractmethod
    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event"""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> str:
        """Subscribe to events"""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events"""
        pass
    
    @abstractmethod
    async def publish_async(self, event_type: str, data: Any) -> None:
        """Publish an event asynchronously"""
        pass


# Interface registry for dependency injection discovery
class InterfaceRegistry:
    """Registry of all core interfaces for dependency injection"""
    
    _interfaces = {
        'service_container': IServiceContainer,
        'configuration_manager': IConfigurationManager,
        'health_monitor': IHealthMonitor,
        'agent_registry': IAgentRegistry,
        'prompt_cache': IPromptCache,
        'template_manager': ITemplateManager,
        'structured_logger': IStructuredLogger,
        'service_lifecycle': IServiceLifecycle,
        'error_handler': IErrorHandler,
        'performance_monitor': IPerformanceMonitor,
        'event_bus': IEventBus,
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